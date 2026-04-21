# @module models.common — Helpers compartilhados entre todos os modelos
from datetime import datetime
import uuid


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()
