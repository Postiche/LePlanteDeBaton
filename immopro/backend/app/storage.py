"""Stockage sécurisé des fichiers téléversés.

- liste blanche d'extensions ET vérification de la signature binaire (magic bytes) ;
- taille maximale configurable ; contrôle des archives OOXML (zip bomb, macros) ;
- images ré-encodées avec Pillow (supprime les métadonnées EXIF, dont la position GPS) ;
- noms de stockage aléatoires, hors de toute ressource publique ; téléchargement uniquement
  via une route authentifiée.
"""
from __future__ import annotations

import hashlib
import io
import secrets
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .config import get_settings

ALLOWED = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


@dataclass
class StoredFile:
    stored_name: str
    original_name: str
    mime_type: str
    size: int
    sha256: str
    ext: str
    kind: str  # photo | document


def upload_root() -> Path:
    p = Path(get_settings().upload_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_name(name: str) -> str:
    name = Path(name or "fichier").name
    return "".join(c for c in name if c.isprintable() and c not in '<>:"/\\|?*')[:200] or "fichier"


def _check_signature(ext: str, data: bytes) -> None:
    head = data[:16]
    ok = True
    if ext in (".jpg", ".jpeg"):
        ok = head.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        ok = head.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext == ".webp":
        ok = head[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif ext == ".heic":
        ok = data[4:8] == b"ftyp"
    elif ext == ".pdf":
        ok = b"%PDF-" in data[:1024]
    elif ext in (".docx", ".xlsx"):
        ok = head.startswith(b"PK\x03\x04")
        if ok:
            _check_ooxml(ext, data)
    elif ext in (".csv", ".txt"):
        if b"\x00" in data[:8192]:
            ok = False
    if not ok:
        raise HTTPException(400, "Le contenu du fichier ne correspond pas à son extension.")


def _check_ooxml(ext: str, data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            if len(infos) > 5000:
                raise HTTPException(400, "Archive Office suspecte (trop d'éléments).")
            total = sum(i.file_size for i in infos)
            if total > 200 * 1024 * 1024 or total > 100 * max(len(data), 1):
                raise HTTPException(400, "Archive Office suspecte (taux de compression anormal).")
            names = {i.filename.lower() for i in infos}
            if any("vbaproject.bin" in n for n in names):
                raise HTTPException(400, "Les documents contenant des macros ne sont pas acceptés.")
            expected = "word/document.xml" if ext == ".docx" else "xl/workbook.xml"
            if expected not in names:
                raise HTTPException(400, "Document Office invalide.")
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Document Office corrompu.") from exc


def _sanitize_image(ext: str, data: bytes) -> tuple[bytes, str, str]:
    if ext == ".heic":
        return data, ext, ALLOWED[ext]  # non ré-encodable sans dépendance supplémentaire
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 80_000_000
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        if max(img.size) > 3000:
            img.thumbnail((3000, 3000))
        out = io.BytesIO()
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(out, format="JPEG", quality=86, optimize=True)
        return out.getvalue(), ".jpg", "image/jpeg"
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Image illisible ou corrompue.") from exc


async def save_upload(file: UploadFile, allowed_ext: set[str] | None = None) -> StoredFile:
    original = _safe_name(file.filename or "fichier")
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED or (allowed_ext and ext not in allowed_ext):
        raise HTTPException(400, f"Type de fichier non autorisé ({ext or 'sans extension'}).")
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"Fichier trop volumineux (maximum {get_settings().max_upload_mb} Mo).")
    if not data:
        raise HTTPException(400, "Fichier vide.")
    return store_bytes(original, data)


def store_bytes(original: str, data: bytes) -> StoredFile:
    original = _safe_name(original)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "Type de fichier non autorisé.")
    _check_signature(ext, data)
    mime = ALLOWED[ext]
    kind = "document"
    if ext in IMAGE_EXT:
        data, ext, mime = _sanitize_image(ext, data)
        kind = "photo"
    stored = secrets.token_hex(16) + ext
    (upload_root() / stored).write_bytes(data)
    return StoredFile(stored, original, mime, len(data), hashlib.sha256(data).hexdigest(), ext, kind)


def file_path(stored_name: str) -> Path:
    root = upload_root().resolve()
    p = (root / Path(stored_name).name).resolve()
    if root not in p.parents:
        raise HTTPException(404, "Fichier introuvable.")
    return p


def read_bytes(stored_name: str) -> bytes:
    return file_path(stored_name).read_bytes()
