import argparse
import json
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orchestrator import Orchestrator
from utils.memory import MemoryStore

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_PLANNER_MODEL = "qwen2.5"
DEFAULT_EXECUTOR_MODEL = "codellama:13b"
DEFAULT_CRITIC_MODEL = "qwen2.5"
DEFAULT_REVIEW_MODEL = DEFAULT_CRITIC_MODEL
DEFAULT_SELF_CORRECTION_MODEL = DEFAULT_EXECUTOR_MODEL
DEFAULT_OPTIMIZER_MODEL = "gemma3:4b"
DEFAULT_RESPONSE_MODEL = "gemma3:4b"
DEFAULT_MAX_WORKERS = 2
DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 5000
DEFAULT_OLLAMA_TIMEOUT = 600


class MessageModel(BaseModel):
    role: str
    content: str


class RunPayload(BaseModel):
    goal: str = Field(..., description="Objectif global a realiser.")
    context: str = ""
    constraints: str = ""
    optimize: bool = True
    enable_search: bool = False
    search_query: Optional[str] = None
    use_memory: bool = True
    history: List[MessageModel] = Field(default_factory=list)
    scenario_id: Optional[str] = Field(default=None, description="Identifiant du scenario pour le suivi de couts/tokens.")
    session_id: Optional[str] = Field(
        default=None,
        description="Identifiant de discussion pour isoler la memoire par chat. Absent => memoire desactivee.",
    )


class FileEditModel(BaseModel):
    path: str
    content: str


class TaskReviewModel(BaseModel):
    summary: str = ""
    problems: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)


class ExecutionModel(BaseModel):
    status: str
    files: List[FileEditModel] = Field(default_factory=list)
    notes: str = ""
    review: Optional[TaskReviewModel] = None


class TaskModel(BaseModel):
    id: int
    title: str
    description: str
    input: str
    output: str
    dependencies: List[int] = Field(default_factory=list)


class TaskResultModel(BaseModel):
    task: TaskModel
    execution: ExecutionModel


class CriticModel(BaseModel):
    score: int
    problems: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    goal: str
    context: str
    context_used: str = Field("", exclude=True)
    memory_context: str = Field("", exclude=True)
    scenario_id: str = ""
    search_results: List[Dict[str, str]] = Field(default_factory=list)
    completed_tasks: int
    tasks: List[TaskResultModel]
    unresolved_tasks: List[TaskModel]
    final_critic: CriticModel
    response: str


class MemoryEntryModel(BaseModel):
    id: str
    goal: str
    context: str
    constraints: str
    notes: str
    response: str
    conversation_id: str
    timestamp: float


class OptimizePayload(BaseModel):
    prompt: str = Field(..., description="Prompt a optimiser.")
    context: str = ""


class OptimizeResponse(BaseModel):
    optimized_prompt: str
    raw: str


def build_orchestrator(config: Optional[argparse.Namespace] = None) -> Orchestrator:
    disable_memory = bool(getattr(config, "disable_memory", False))
    memory_store = None if disable_memory else MemoryStore(path=getattr(config, "memory_path", "memory_store.json"))
    orchestrator = Orchestrator(
        ollama_base_url=getattr(config, "ollama_url", DEFAULT_OLLAMA_URL),
        planner_model=getattr(config, "planner_model", DEFAULT_PLANNER_MODEL),
        executor_model=getattr(config, "executor_model", DEFAULT_EXECUTOR_MODEL),
        critic_model=getattr(config, "critic_model", DEFAULT_CRITIC_MODEL),
        review_model=getattr(config, "review_model", DEFAULT_REVIEW_MODEL),
        self_correction_model=getattr(config, "self_correction_model", DEFAULT_SELF_CORRECTION_MODEL),
        optimizer_model=getattr(config, "optimizer_model", DEFAULT_OPTIMIZER_MODEL),
        optimizer_enabled=not bool(getattr(config, "disable_optimizer", False)),
        response_model=getattr(config, "response_model", DEFAULT_RESPONSE_MODEL),
        max_workers=max(1, int(getattr(config, "max_workers", DEFAULT_MAX_WORKERS))),
        verbose=not bool(getattr(config, "no_verbose", False)),
        memory_store=memory_store,
        memory_enabled=not disable_memory,
        enable_search=bool(getattr(config, "enable_search", False)),
        search_timeout=int(getattr(config, "search_timeout", 30)),
        costs_path=getattr(config, "costs_path", "costs.csv"),
        ollama_timeout=int(getattr(config, "ollama_timeout", DEFAULT_OLLAMA_TIMEOUT)),
    )
    orchestrator.memory_disabled = disable_memory
    return orchestrator


def create_app(orchestrator: Optional[Orchestrator] = None) -> FastAPI:
    app = FastAPI(
        title="MyCodex Agent API",
        version="0.1.0",
        description="API FastAPI pour piloter l'agent MyCodex via l'extension VS Code.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.orchestrator = orchestrator or build_orchestrator()

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/run", response_model=RunResponse)
    async def run_endpoint(payload: RunPayload) -> RunResponse:
        current = app.state.orchestrator
        goal_to_use = payload.goal
        scenario_id = payload.scenario_id or payload.session_id or "default"
        # Optimize when requested; frontend sends prior history so we no longer block on history length.
        should_optimize = payload.optimize and current.optimizer_enabled
        if should_optimize:
            try:
                optimized = await run_in_threadpool(
                    current.optimize_prompt,
                    payload.goal,
                    payload.context,
                    scenario_id,
                )
                goal_to_use = optimized.get("optimized_prompt", goal_to_use)
                if current.verbose:
                    print("[Optimizer] Prompt optimise applique (API).", flush=True)
            except Exception as exc:  # pragma: no cover - resilience
                if current.verbose:
                    print(f"[Optimizer] Echec optimisation du prompt: {exc}", flush=True)
                goal_to_use = payload.goal
        # Pas d'ID de session => memoire desactivee pour eviter le mode global implicite.
        use_memory = payload.use_memory and bool(payload.session_id)
        try:
            result = await run_in_threadpool(
                current.run,
                goal_to_use,
                payload.context,
                payload.constraints,
                use_memory and not getattr(current, "memory_disabled", False),
                payload.history,
                payload.session_id,
                payload.enable_search,
                payload.search_query,
                scenario_id=scenario_id,
            )
            return RunResponse(**result)
        except Exception as exc:  # pragma: no cover - API safety
            raise HTTPException(status_code=500, detail=f"Echec de l'agent: {exc}") from exc

    @app.get("/api/memory", response_model=List[MemoryEntryModel])
    async def list_memory(conversation_id: Optional[str] = None) -> List[MemoryEntryModel]:
        current = app.state.orchestrator
        if not current.memory_enabled or not current.memory:
            raise HTTPException(status_code=400, detail="Memoire desactivee.")
        entries = current.memory.list_entries(conversation_id)
        return [
            MemoryEntryModel(
                id=str(entry.timestamp),
                goal=entry.goal,
                context=entry.context,
                constraints=entry.constraints,
                notes=entry.notes,
                response=entry.response,
                conversation_id=entry.conversation_id,
                timestamp=entry.timestamp,
            )
            for entry in entries
        ]

    @app.delete("/api/memory/{entry_id}")
    async def delete_memory(entry_id: str) -> Dict[str, bool]:
        current = app.state.orchestrator
        if not current.memory_enabled or not current.memory:
            raise HTTPException(status_code=400, detail="Memoire desactivee.")
        removed = current.memory.delete_entry(entry_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Entree non trouvee.")
        return {"ok": True}

    @app.post("/api/optimize", response_model=OptimizeResponse)
    async def optimize_endpoint(payload: OptimizePayload) -> OptimizeResponse:
        current = app.state.orchestrator
        if not current.optimizer_enabled:
            raise HTTPException(status_code=400, detail="L'optimisation de prompt est desactivee sur ce serveur.")
        try:
            result = await run_in_threadpool(
                current.optimize_prompt,
                payload.prompt,
                payload.context,
            )
            return OptimizeResponse(**result)
        except Exception as exc:  # pragma: no cover - API safety
            raise HTTPException(status_code=500, detail=f"Echec de l'optimizer: {exc}") from exc

    return app


app = create_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent MyCodex en mode FastAPI ou CLI")
    parser.add_argument(
        "--mode",
        choices=["api", "cli", "optimize"],
        default="api",
        help="api = lance le serveur FastAPI (defaut), cli = execution unique, optimize = optimise un prompt unique.",
    )
    parser.add_argument("--host", default=DEFAULT_API_HOST, help="Adresse d'ecoute du serveur FastAPI.")
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT, help="Port d'ecoute du serveur FastAPI.")
    parser.add_argument("--reload", action="store_true", help="Active le rechargement auto (dev uniquement).")
    parser.add_argument("--goal", help="Objectif global a realiser (mode CLI).")
    parser.add_argument("--context", default="", help="Contexte technique ou notes supplementaires.")
    parser.add_argument("--constraints", default="", help="Contraintes supplementaires a transmettre a l'executor.")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="URL de base du serveur Ollama.")
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=DEFAULT_OLLAMA_TIMEOUT,
        help="Timeout en secondes pour les appels Ollama (par defaut 300).",
    )
    parser.add_argument("--planner-model", default=DEFAULT_PLANNER_MODEL, help="Modele utilise pour la planification.")
    parser.add_argument("--executor-model", default=DEFAULT_EXECUTOR_MODEL, help="Modele utilise pour l'execution.")
    parser.add_argument("--critic-model", default=DEFAULT_CRITIC_MODEL, help="Modele utilise pour la critique.")
    parser.add_argument("--review-model", default=DEFAULT_REVIEW_MODEL, help="Modele utilise pour la revision par tache.")
    parser.add_argument("--optimizer-model", default=DEFAULT_OPTIMIZER_MODEL, help="Modele utilise pour l'optimisation de prompt.")
    parser.add_argument("--response-model", default=DEFAULT_RESPONSE_MODEL, help="Modele utilise pour formater la reponse Markdown.")
    parser.add_argument(
        "--self-correction-model",
        default=DEFAULT_SELF_CORRECTION_MODEL,
        help="Modele utilise pour appliquer les recommandations du critic.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help="Nombre de taches sans dependances traitees en parallele.",
    )
    parser.add_argument(
        "--no-verbose",
        action="store_true",
        help="Desactive les affichages de progression.",
    )
    parser.add_argument("--prompt", help="Prompt a optimiser (mode optimize).")
    parser.add_argument(
        "--disable-optimizer",
        action="store_true",
        help="Desactive l'optimisation automatique du prompt en mode cli/api.",
    )
    parser.add_argument(
        "--disable-memory",
        action="store_true",
        help="Desactive le module de memoire (contexte non enrichi et pas de persistance).",
    )
    parser.add_argument(
        "--memory-path",
        default="memory_store.json",
        help="Chemin du fichier JSON de memoire persistante.",
    )
    parser.add_argument("--costs-path", default="costs.csv", help="Chemin du fichier CSV de suivi des couts/tokens.")
    parser.add_argument("--scenario-id", default=None, help="Identifiant scenario pour logger les couts/tokens.")
    parser.add_argument(
        "--enable-search",
        action="store_true",
        help="Active les recherches web (DuckDuckGo) pour enrichir le contexte avant execution.",
    )
    parser.add_argument(
        "--search-timeout",
        type=int,
        default=10,
        help="Timeout HTTP en secondes pour les recherches web.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode == "cli":
        if not args.goal:
            raise SystemExit("--goal est requis en mode cli.")
        orchestrator = build_orchestrator(args)
        goal = args.goal
        scenario_id = args.scenario_id or "cli"
        if orchestrator.optimizer_enabled:
            try:
                optimized = orchestrator.optimize_prompt(
                    prompt=args.goal,
                    context=args.context,
                    scenario_id=scenario_id,
                )
                goal = optimized.get("optimized_prompt", goal)
                if orchestrator.verbose:
                    print("[Optimizer] Prompt optimise applique.", flush=True)
            except Exception as exc:  # pragma: no cover - resilience
                if orchestrator.verbose:
                    print(f"[Optimizer] Echec optimisation du prompt: {exc}", flush=True)
        result = orchestrator.run(
            goal=goal,
            context=args.context,
            constraints=args.constraints,
            use_memory=not args.disable_memory,
            history=[],
            conversation_id="cli",
            enable_search=bool(getattr(args, "enable_search", False)),
            search_query=None,
            scenario_id=scenario_id,
        )
        if isinstance(result, dict) and result.get("response"):
            print("Response markdown:")
            print(result["response"])
            print("")
        print(json.dumps(result, ensure_ascii=False, indent=2))

        """
        tasks = result["tasks"]
        for task in tasks:
            execution = task["execution"]
            print("notes: " + execution["notes"])
            
            files = execution["files"]
            for file in files:
                print("")
                print(f"Fichier: {file['path']}")
                print("```")
                print(file["content"])
                print("```")

        print("Unresolved tasks: ", end="") 
        print(result["unresolved_tasks"])
        
        recommendations = result["final_critic"]["recommendations"]
        print("Recommendations:")
        for recommendation in recommendations:
            print(recommendation)"""

        return

    if args.mode == "optimize":
        if not args.prompt:
            raise SystemExit("--prompt est requis en mode optimize.")
        orchestrator = build_orchestrator(args)
        if not orchestrator.optimizer_enabled:
            raise SystemExit("L'optimisation de prompt est desactivee (--disable-optimizer).")
        optimized = orchestrator.optimize_prompt(
            prompt=args.prompt,
            context=args.context,
            scenario_id=args.scenario_id or "optimize",
        )
        print("Optimized prompt:")
        print("")
        print(optimized["optimized_prompt"])
        return

    app.state.orchestrator = build_orchestrator(args)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
