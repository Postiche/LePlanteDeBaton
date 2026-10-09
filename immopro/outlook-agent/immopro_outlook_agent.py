"""Agent Outlook local (facultatif) pour ImmoPro — Windows + Outlook classique uniquement.

- écoute UNIQUEMENT sur 127.0.0.1 (jamais exposé sur le réseau ni sur Internet) ;
- exige un jeton d'appairage (affiché au démarrage, à saisir dans ImmoPro › Paramètres › Outlook) ;
- n'accepte que l'origine de votre instance ImmoPro (variable IMMOPRO_ORIGIN) ;
- crée des BROUILLONS (MailItem.Save + Display) : il n'appelle jamais Send().

Le nouvel Outlook (« Outlook for Windows ») ne fournit pas d'automatisation COM : dans ce cas
l'agent renvoie une erreur explicite et il faut utiliser le fichier .eml ou « Ouvrir dans la messagerie ».

Lancement :  set IMMOPRO_ORIGIN=https://immo.mondomaine.fr
             python immopro_outlook_agent.py
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import re
import secrets
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = int(os.environ.get("IMMOPRO_AGENT_PORT", "8765"))
ORIGINS = {o.strip().rstrip("/") for o in os.environ.get("IMMOPRO_ORIGIN", "http://localhost:5173,http://127.0.0.1:8000").split(",") if o.strip()}
MAX_BODY = 40 * 1024 * 1024
CONF_DIR = Path(os.environ.get("APPDATA", Path.home())) / "ImmoProOutlookAgent"


def load_token() -> str:
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    f = CONF_DIR / "token.txt"
    if not f.exists():
        f.write_text(secrets.token_urlsafe(24), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


TOKEN = load_token()


def outlook_app():
    try:
        import win32com.client  # type: ignore  (pywin32)
    except ImportError as exc:
        raise RuntimeError("pywin32 n'est pas installé (pip install pywin32).") from exc
    try:
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as exc:
        raise RuntimeError("Outlook classique introuvable ou non automatisable (le nouvel Outlook n'est pas compatible).") from exc


def outlook_status() -> str:
    if sys.platform != "win32":
        return "indisponible (Windows requis)"
    try:
        app = outlook_app()
        return f"Outlook {getattr(app, 'Version', '?')}"
    except RuntimeError as exc:
        return f"indisponible : {exc}"


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name or "piece-jointe.pdf")[:120]
    return name if name.lower().endswith(".pdf") else name + ".pdf"


def create_draft(data: dict) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Cet agent fonctionne uniquement sous Windows avec Outlook classique.")
    app = outlook_app()
    mail = app.CreateItem(0)  # olMailItem
    mail.To = str(data.get("to") or "")[:1000]
    if data.get("cc"):
        mail.CC = str(data["cc"])[:1000]
    mail.Subject = str(data.get("subject") or "")[:300]
    mail.Body = str(data.get("body") or "")
    with tempfile.TemporaryDirectory() as tmp:
        for att in (data.get("attachments") or [])[:10]:
            raw = base64.b64decode(att.get("content_base64", ""), validate=True)
            if not raw.startswith(b"%PDF-"):
                raise RuntimeError("Seules les fiches PDF générées par ImmoPro sont acceptées en pièce jointe.")
            p = Path(tmp) / safe_filename(att.get("filename"))
            p.write_bytes(raw)
            mail.Attachments.Add(str(p))
        mail.Save()  # brouillon dans « Brouillons » — JAMAIS d'envoi automatique
    mail.Display(False)


class Handler(BaseHTTPRequestHandler):
    server_version = "ImmoProOutlookAgent/1.0"

    def _origin_ok(self) -> str | None:
        origin = (self.headers.get("Origin") or "").rstrip("/")
        return origin if origin in ORIGINS else None

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        origin = self._origin_ok()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        return self._origin_ok() is not None and hmac.compare_digest(self.headers.get("X-Agent-Token", ""), TOKEN)

    def do_OPTIONS(self):  # pré-vol CORS / Private Network Access
        self.send_response(204)
        origin = self._origin_ok()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Agent-Token")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self):
        if self.path != "/status":
            return self._send(404, {"ok": False, "error": "Inconnu"})
        if not self._authorized():
            return self._send(403, {"ok": False, "error": "Origine ou jeton d'appairage refusé."})
        self._send(200, {"ok": True, "outlook": outlook_status()})

    def do_POST(self):
        if self.path != "/draft":
            return self._send(404, {"ok": False, "error": "Inconnu"})
        if not self._authorized():
            return self._send(403, {"ok": False, "error": "Origine ou jeton d'appairage refusé."})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._send(413, {"ok": False, "error": "Requête trop volumineuse."})
        try:
            create_draft(json.loads(self.rfile.read(length)))
        except Exception as exc:  # message renvoyé à l'utilisateur
            return self._send(500, {"ok": False, "error": str(exc)})
        self._send(200, {"ok": True})

    def log_message(self, fmt, *args):  # pas de journalisation du contenu des emails
        sys.stderr.write("%s %s\n" % (self.command, self.path))


def main() -> None:
    print("Agent Outlook ImmoPro — écoute sur http://%s:%d (local uniquement)" % (HOST, PORT))
    print("Origines autorisées :", ", ".join(sorted(ORIGINS)))
    print("Outlook :", outlook_status())
    print("\nJETON D'APPAIRAGE (à saisir dans ImmoPro › Paramètres › Outlook) :\n  " + TOKEN + "\n")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
