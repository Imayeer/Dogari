"""Point d'entrée de l'application web FastAPI de Dogari."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dogari import __version__
from dogari.core.config import settings
from dogari.storage.database import initialize_database
from dogari.web.routes import access, monitoring, reports, search, status, users

WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def create_app() -> FastAPI:
    """Construit et configure l'application FastAPI (factory)."""
    app = FastAPI(title="Dogari", version=__version__)

    @app.on_event("startup")
    def _on_startup() -> None:
        settings.ensure_directories()
        initialize_database()

    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    app.include_router(status.router)
    app.include_router(users.router)
    app.include_router(access.router)
    app.include_router(reports.router)
    app.include_router(search.router)
    app.include_router(monitoring.router)

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("index.html", {"request": request, "version": __version__})

    return app


app = create_app()


def main() -> None:
    """Lance le serveur de développement (équivalent à `python -m dogari.web.app`)."""
    import uvicorn

    uvicorn.run("dogari.web.app:app", host=settings.web_host, port=settings.web_port, reload=True)


if __name__ == "__main__":
    main()
