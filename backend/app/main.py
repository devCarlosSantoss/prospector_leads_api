from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LeadFinder - Prospecção B2B",
    description="Ferramenta de prospecção comercial B2B",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Register routers (must come before catch-all)
from app.routers import search, leads, campaigns, export

app.include_router(search.router)
app.include_router(leads.router)
app.include_router(campaigns.router)
app.include_router(export.router)

# Register collectors
from app.collectors.google_maps import GoogleMapsCollector
from app.collectors.duckduckgo_search import DuckDuckGoCollector
from app.collectors.directories import ApontadorCollector, ListaBrasilCollector
search.register_collector("google_maps", GoogleMapsCollector)
search.register_collector("duckduckgo", DuckDuckGoCollector)
search.register_collector("apontador", ApontadorCollector)
search.register_collector("lista_brasil", ListaBrasilCollector)


# Catch-all for SPA - serves frontend for all non-API routes
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "Frontend not found"}
