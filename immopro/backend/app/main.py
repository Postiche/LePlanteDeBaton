from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, backup
from .config import get_settings
from .routers import admin, auth, crm, dashboard, documents, emails, external, imports, matches, properties, requests, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("immopro")

FIELD_LABELS = {"body": "", "query": "paramètre "}


async def _backup_loop(hours: int) -> None:
    while True:
        await asyncio.sleep(hours * 3600)
        try:
            await asyncio.to_thread(backup.create_backup, "auto")
        except Exception:  # pragma: no cover
            log.exception("Échec de la sauvegarde automatique")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    Path(s.upload_dir).mkdir(parents=True, exist_ok=True)
    task = None
    if s.backup_interval_hours > 0 and s.app_env != "test":
        task = asyncio.create_task(_backup_loop(s.backup_interval_hours))
    yield
    if task:
        task.cancel()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title=s.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url=None if s.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if s.is_production else "/api/openapi.json",
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault("Permissions-Policy", "camera=(self), geolocation=(self), microphone=()")
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; "
            "font-src 'self' data:; connect-src 'self' http://127.0.0.1:* http://localhost:*; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'; object-src 'none'; worker-src 'self'; manifest-src 'self'",
        )
        if s.cookie_secure:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            h.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        msgs = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e["loc"][1:]) if len(e["loc"]) > 1 else str(e["loc"][0])
            msg = e["msg"].replace("Value error, ", "")
            msgs.append(f"{loc} : {msg}" if loc else msg)
        return JSONResponse({"detail": "Données invalides — " + " ; ".join(msgs[:6])}, status_code=422)

    for r in (auth, users, dashboard, properties, requests, matches, crm, emails, documents, imports, external, admin):
        app.include_router(r.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def api_not_found(path: str):
        raise HTTPException(404, "Ressource introuvable.")

    # Frontend compilé (aucune donnée privée : toutes les données passent par l'API authentifiée)
    dist = Path(s.frontend_dist)
    if dist.exists():

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            target = (dist / path).resolve()
            if path and target.is_file() and dist.resolve() in target.parents:
                headers = {}
                if path.startswith("assets/"):
                    headers["Cache-Control"] = "public, max-age=31536000, immutable"
                elif path in ("sw.js", "manifest.webmanifest"):
                    headers["Cache-Control"] = "no-cache"
                return FileResponse(target, headers=headers)
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
