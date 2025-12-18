import concurrent.futures
from typing import Dict, List, Optional, Set

from agents.critic import Critic
from agents.executor import Executor
from agents.planner import Planner
from agents.reviewer import Reviewer
from agents.prompt_optimizer import PromptOptimizer
from agents.responder import Responder
from agents.searcher import Searcher
from agents.self_correction import SelfCorrection
from clients.ollama_client import OllamaClient
from clients.search_client import WebSearchClient
from models.tasks import CriticFeedback, ExecutionOutput, FileEdit, Task, TaskReview, parse_task_review
from utils.cost_logger import CostLogger
from utils.memory import MemoryStore


def _serialize_execution_output(output: ExecutionOutput) -> Dict[str, object]:
    return {
        "status": output.status,
        "notes": output.notes,
        "files": [{"path": f.path, "content": f.content} for f in output.files],
        "review": _serialize_review(output.review),
    }


def _serialize_feedback(feedback: CriticFeedback) -> Dict[str, object]:
    return {
        "score": feedback.score,
        "problems": feedback.problems,
        "recommendations": feedback.recommendations,
        "raw": feedback.raw,
    }


def _serialize_review(review: TaskReview | None) -> Dict[str, object] | None:
    if review is None:
        return None
    return {
        "summary": review.summary,
        "problems": review.problems,
        "recommendations": review.recommendations,
        "raw": review.raw,
    }


class Orchestrator:
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        planner_model: str = "llama3.1:8b",
        executor_model: str = "codellama:13b",
        critic_model: str = "qwen2.5",
        review_model: str = "qwen2.5",
        self_correction_model: str | None = None,
        optimizer_model: str = "gemma3:4b",
        optimizer_enabled: bool = True,
        response_model: str = "gemma3:4b",
        max_workers: int = 2,
        verbose: bool = True,
        memory_store: MemoryStore | None = None,
        memory_enabled: bool = True,
        enable_search: bool = False,
        search_timeout: int = 30,
        costs_path: str = "costs.csv",
        ollama_timeout: int = 300,
    ) -> None:
        self.cost_logger = CostLogger(path=costs_path)
        client = OllamaClient(
            base_url=ollama_base_url,
            timeout=ollama_timeout,
            cost_logger=self.cost_logger,
            costs_path=costs_path,
        )
        self.client = client
        self.planner = Planner(client=client, model=planner_model)
        self.executor = Executor(client=client, model=executor_model)
        self.critic = Critic(client=client, model=critic_model)
        self.reviewer = Reviewer(client=client, model=review_model)
        self.self_correction = SelfCorrection(client=client, model=self_correction_model or executor_model)
        self.optimizer_enabled = optimizer_enabled
        self.prompt_optimizer = PromptOptimizer(client=client, model=optimizer_model) if optimizer_enabled else None
        self.responder = Responder(client=client, model=response_model)
        self.max_workers = max(1, max_workers)
        self.verbose = verbose
        self.memory_enabled = memory_enabled
        self.memory = memory_store or (MemoryStore() if memory_enabled else None)
        self.searcher = Searcher(client=WebSearchClient(timeout=search_timeout)) if enable_search else None
        self.current_scenario_id = "unknown"

    def run(
        self,
        goal: str,
        context: str = "",
        constraints: str = "",
        use_memory: bool = True,
        history: List[dict] | None = None,
        conversation_id: str | None = None,
        enable_search: bool = False,
        search_query: str | None = None,
        search_results_limit: int = 5,
        scenario_id: Optional[str] = None,
    ) -> Dict[str, object]:
        scenario_label = self._normalize_scenario_id(scenario_id or conversation_id)
        self.current_scenario_id = scenario_label
        self.client.set_default_scenario(scenario_label)
        base_context = context or ""
        formatted_history = ""
        if history:
            try:
                if self.memory:
                    normalized = self.memory._normalize_history(history)  # type: ignore[attr-defined]
                    formatted_history = self.memory.format_history(normalized)
                else:
                    formatted_history = self._format_history(history)
            except Exception:
                formatted_history = self._format_history(history)
        context_with_history = base_context
        if formatted_history:
            context_with_history = "\n\n".join(
                part for part in [base_context.strip(), f"Historique de discussion (session):\n{formatted_history}"] if part
            ).strip()
        context_used = context_with_history
        memory_context = ""
        memory_entries: list = []

        response_context = context_with_history
        search_results: list[dict] = []

        if enable_search and self.searcher:
            search_text = search_query or goal
            try:
                search_payload = self.searcher.search(search_text, max_results=search_results_limit)
                search_results = search_payload["results"]
                if search_payload["context"]:
                    context_used = "\n\n".join(
                        part for part in [context_used, f"Resultats de recherche Web:\n{search_payload['context']}"] if part
                    ).strip()
            except Exception as exc:  # pragma: no cover - defensive
                self._log(f"[Search] Echec recherche web: {exc}")

        if use_memory and self.memory_enabled and self.memory:
            try:
                context_used, memory_context, memory_entries = self.memory.build_context(
                    goal=goal,
                    context=context_used,
                    history=history or [],
                    conversation_id=conversation_id,
                )

                if memory_entries:
                    self._log(f"[Memory] {len(memory_entries)} rappel(s) ajoutes au contexte.")
            except Exception as exc:  # pragma: no cover - defensive
                self._log(f"[Memory] Echec enrichissement contexte: {exc}")
                context_used = base_context
                memory_context = ""
        else:
            # Pas de memoire active -> ne pas polluer la reponse finale avec des traces de memoire.
            context_used = response_context

        self._log(f"[Planner] Goal: {goal}")
        tasks = self.planner.plan(goal=goal, context=context_used, scenario_id=scenario_label)
        self._log(f"[Planner] {len(tasks)} task(s) generated.")
        tasks_by_id: Dict[int, Task] = {task.id: task for task in tasks}
        remaining_ids: Set[int] = set(tasks_by_id.keys())
        completed: Set[int] = set()
        results: List[Dict[str, object]] = []
        futures: Dict[concurrent.futures.Future, int] = {}

        def ready_ids() -> List[int]:
            return [
                tid
                for tid in remaining_ids
                if set(tasks_by_id[tid].dependencies or []).issubset(completed)
            ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while remaining_ids or futures:
                for tid in ready_ids():
                    if len(futures) >= self.max_workers:
                        break
                    task = tasks_by_id[tid]
                    future = pool.submit(
                        self._run_single_task,
                        task,
                        context_used,
                        constraints,
                        scenario_label,
                    )
                    futures[future] = tid
                    remaining_ids.remove(tid)
                    self._log(f"[Executor] Scheduled task {tid} ({task.title})")

                if not futures:
                    break

                done, _ = concurrent.futures.wait(
                    futures.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                for finished in done:
                    task_id = futures.pop(finished)
                    try:
                        result = finished.result()
                    except Exception as exc:  # pragma: no cover - defensive
                        self._log(f"[Executor] Task {task_id} raised an exception: {exc}")
                        result = {
                            "task": tasks_by_id[task_id].__dict__,
                            "execution": {
                                "status": "failure",
                                "notes": f"Exception during execution: {exc}",
                                "files": [],
                            },
                        }

                    results.append(result)
                    completed.add(task_id)

        results.sort(key=lambda item: item.get("task", {}).get("id", 0))
        unresolved = [tasks_by_id[tid].__dict__ for tid in remaining_ids]

        initial_feedback = self.critic.evaluate_final(
            goal=goal,
            context=context_used,
            constraints=constraints,
            task_results=results,
            unresolved_tasks=unresolved,
            scenario_id=scenario_label,
        )
        self._log(f"[Critic] Score initial {initial_feedback.score}")

        results_corrected = results
        corrections_applied = False
        if initial_feedback.recommendations or initial_feedback.problems:
            try:
                results_corrected, corrections_applied = self._apply_self_corrections(
                    results,
                    initial_feedback,
                    context_used,
                    constraints,
                    scenario_label,
                )
                if corrections_applied:
                    results_corrected.sort(key=lambda item: item.get("task", {}).get("id", 0))
                    self._log("[SelfCorrection] Corrections appliquees suite aux recommandations du critic.")
            except Exception as exc:  # pragma: no cover - defensive
                self._log(f"[SelfCorrection] Echec des corrections: {exc}")

        final_feedback = (
            initial_feedback
            if not corrections_applied
            else self.critic.evaluate_final(
                goal=goal,
                context=context_used,
                constraints=constraints,
                task_results=results_corrected,
                unresolved_tasks=unresolved,
                scenario_id=scenario_label,
            )
        )
        self._log(f"[Critic] Score final {final_feedback.score}")
        final_feedback_data = _serialize_feedback(final_feedback)

        response = self._build_final_response(
            goal=goal,
            # Le contexte pour la reponse finale ne doit pas inclure le texte d'enrichissement memoire,
            # sinon le modele a tendance a dupliquer ou paraphraser ces traces.
            context=response_context,
            tasks=results_corrected,
            unresolved_tasks=unresolved,
            final_critic=final_feedback_data,
            scenario_id=scenario_label,
        )

        if use_memory and self.memory_enabled and self.memory:
            try:
                self.memory.remember_run(
                    goal=goal,
                    context=base_context,
                    context_used=context_used,
                    constraints=constraints,
                    tasks=results_corrected,
                    unresolved=unresolved,
                    final_critic=final_feedback_data,
                    response=response,
                    history=history or [],
                    conversation_id=conversation_id,
                )
            except Exception as exc:  # pragma: no cover - defensive
                self._log(f"[Memory] Echec enregistrement memoire: {exc}")

        return {
            "goal": goal,
            "context": base_context,
            "context_used": context_used,
            "scenario_id": scenario_label,
            "completed_tasks": len(completed),
            "tasks": results_corrected,
            "unresolved_tasks": unresolved,
            "memory_context": memory_context,
            "search_results": search_results,
            "final_critic": final_feedback_data,
            "response": response,
        }

    def optimize_prompt(self, prompt: str, context: str = "", scenario_id: Optional[str] = None) -> Dict[str, str]:
        if not self.optimizer_enabled or not self.prompt_optimizer:
            return {"optimized_prompt": prompt, "raw": prompt}
        scenario_label = self._normalize_scenario_id(scenario_id or self.current_scenario_id)
        optimized, raw = self.prompt_optimizer.optimize(prompt=prompt, context=context, scenario_id=scenario_label)
        return {"optimized_prompt": optimized, "raw": raw}

    def _run_single_task(self, task: Task, context: str, constraints: str, scenario_id: str) -> Dict[str, object]:
        self._log(f"[Executor] Running task {task.id}: {task.title}")
        exec_output = self.executor.execute(
            task=task,
            project_context=context,
            constraints=constraints,
            scenario_id=scenario_id,
        )
        exec_output.review = self.reviewer.review(
            task=task,
            execution=exec_output,
            context=context,
            constraints=constraints,
            scenario_id=scenario_id,
        )

        return {
            "task": task.__dict__,
            "execution": _serialize_execution_output(exec_output),
        }

    def _apply_self_corrections(
        self,
        results: List[Dict[str, object]],
        critic_feedback: CriticFeedback,
        context: str,
        constraints: str,
        scenario_id: str,
    ) -> tuple[List[Dict[str, object]], bool]:
        corrected_results: List[Dict[str, object]] = []
        changed = False

        for item in results:
            task_data = item.get("task") or {}
            execution_data = item.get("execution") or {}
            try:
                task_obj = Task(
                    id=int(task_data.get("id", 0)),
                    title=str(task_data.get("title", "")),
                    description=str(task_data.get("description", "")),
                    input=str(task_data.get("input", "")),
                    output=str(task_data.get("output", "")),
                    dependencies=list(task_data.get("dependencies") or []),
                )
                exec_output = ExecutionOutput(
                    status=str(execution_data.get("status", "failure")),
                    notes=str(execution_data.get("notes", "")),
                    files=[
                        FileEdit(path=str(f["path"]), content=str(f["content"]))
                        for f in execution_data.get("files", [])
                        if isinstance(f, dict) and "path" in f and "content" in f
                    ],
                    review=parse_task_review(execution_data.get("review")) if execution_data.get("review") else None,
                )
                corrected_output = self.self_correction.correct(
                    task_obj,
                    exec_output,
                    critic_feedback,
                    scenario_id=scenario_id,
                )
                if corrected_output.status == "success" and corrected_output.files:
                    corrected_output.review = self.reviewer.review(
                        task=task_obj,
                        execution=corrected_output,
                        context=context,
                        constraints=constraints,
                        scenario_id=scenario_id,
                    )
                    corrected_serialized = _serialize_execution_output(corrected_output)
                    changed = changed or corrected_serialized != execution_data
                    corrected_results.append({"task": task_data, "execution": corrected_serialized})
                else:
                    # Ignore empty/failed corrections to keep prior result stable.
                    corrected_results.append(item)
            except Exception as exc:  # pragma: no cover - defensive
                self._log(f"[SelfCorrection] Erreur sur la tache {task_data.get('id')}: {exc}")
                corrected_results.append(item)

        return corrected_results, changed

    def _build_final_response(
        self,
        goal: str,
        context: str,
        tasks: List[Dict[str, object]],
        unresolved_tasks: List[Dict[str, object]],
        final_critic: Dict[str, object],
        scenario_id: str,
    ) -> str:
        try:
            draft = self.responder.build_markdown_response(
                goal=goal,
                context=context,
                tasks=tasks,
                unresolved_tasks=unresolved_tasks,
                final_critic=final_critic,
                scenario_id=scenario_id,
            )
            if draft.strip():
                return draft.strip()
            self._log("[Responder] Reponse vide recue, utilisation du fallback.")
            return self._fallback_response(goal, context, tasks, unresolved_tasks, final_critic)
        except Exception as exc:  # pragma: no cover - defensive
            self._log(f"[Responder] Echec generation Markdown: {exc}")
            return self._fallback_response(goal, context, tasks, unresolved_tasks, final_critic)

    def _fallback_response(
        self,
        goal: str,
        context: str,
        tasks: List[Dict[str, object]],
        unresolved_tasks: List[Dict[str, object]],
        final_critic: Dict[str, object],
    ) -> str:
        lines: List[str] = [
            f"# Objectif\n{goal}",
            f"## Contexte\n{context or 'Non precise'}",
            "## Progression",
        ]

        if not tasks:
            lines.append("- Aucune tache terminee.")
        else:
            for item in tasks:
                task_data = item.get("task", {}) if isinstance(item, dict) else {}
                execution_data = item.get("execution", {}) if isinstance(item, dict) else {}
                status = execution_data.get("status", "inconnu")
                title = task_data.get("title", f"Tache {task_data.get('id', '')}")
                note = execution_data.get("notes") or ""
                lines.append(f"- [{status}] {title}: {note if note else 'Pas de note fournie.'}")

        if unresolved_tasks:
            lines.append("## Bloquages")
            for task in unresolved_tasks:
                title = task.get("title", f"Tache {task.get('id', '')}") if isinstance(task, dict) else "Tache non definie"
                lines.append(f"- {title}")

        lines.append("## Code")
        has_files = False
        for item in tasks:
            if not isinstance(item, dict):
                continue
            execution_data = item.get("execution", {}) if isinstance(item, dict) else {}
            files = execution_data.get("files", []) if isinstance(execution_data, dict) else []
            for f in files:
                if not isinstance(f, dict):
                    continue
                has_files = True
                path = f.get("path", "chemin/inconnu")
                content = f.get("content", "")
                lines.append(f"- Fichier: {path}")
                lines.append("```")
                lines.append(content)
                lines.append("```")
        if not has_files:
            lines.append("- Aucun fichier fourni.")

        score = final_critic.get("score", "N/A") if isinstance(final_critic, dict) else "N/A"
        recommendations = final_critic.get("recommendations", []) if isinstance(final_critic, dict) else []
        lines.append("## Recommandations")
        if recommendations:
            for rec in recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("- Aucune recommandation fournie.")
        lines.append(f"Score global: {score}")

        return "\n".join(lines)

    def _format_history(self, history: List[object]) -> str:
        formatted: List[str] = []
        for turn in history[-12:]:
            try:
                if isinstance(turn, dict):
                    role = turn.get("role", "user")
                    content = turn.get("content", "")
                else:
                    role = getattr(turn, "role", "user")
                    content = getattr(turn, "content", "")
                role_str = str(role or "user").lower()
                content_str = str(content or "").strip()
            except Exception:
                continue
            if not content_str:
                continue
            label = "Utilisateur" if role_str == "user" else "Assistant"
            snippet = content_str[-600:] if len(content_str) > 600 else content_str
            formatted.append(f"{label}: {snippet}")
        return "\n".join(formatted)

    def _normalize_scenario_id(self, scenario_id: Optional[str]) -> str:
        label = (scenario_id or "").strip()
        return label or "default"

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message, flush=True)
