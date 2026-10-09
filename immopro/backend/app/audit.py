from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog, User
from .security import client_ip


def log_action(
    db: Session,
    user: User | None,
    action: str,
    entity: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
    request: Request | None = None,
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details,
            ip=client_ip(request) if request else None,
        )
    )
    if commit:
        db.commit()
