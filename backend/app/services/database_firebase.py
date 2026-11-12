"""Firestore-backed database service for NexaMind AI.

When FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS_PATH are set, the app uses
Firestore as its primary database. Otherwise it falls back to SQLite/PostgreSQL
via the existing SQLAlchemy layer.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from ..config import get_settings
from .firebase import is_available, initialize

settings = get_settings()


async def firebase_available() -> bool:
    return is_available()


class FirestoreDB:
    """Generic Firestore CRUD for NexaMind AI collections."""

    def __init__(self):
        self._client = None

    def _client(self) -> Any:
        if self._client is None:
            self._client = initialize().db
        return self._client

    async def create(self, collection: str, doc_id: str | None, data: dict) -> str:
        doc_ref = self._client().collection(collection).document(doc_id)
        doc_ref.set(data)
        return doc_ref.id

    async def get(self, collection: str, doc_id: str) -> dict | None:
        snap = self._client().collection(collection).document(doc_id).get()
        return snap.to_dict() if snap.exists else None

    async def list(self, collection: str, limit: int = 50, order_by: str | None = None) -> list[dict]:
        query_ref = self._client().collection(collection)
        if order_by:
            query_ref = query_ref.order_by(order_by, direction="DESCENDING")
        return [item.to_dict() for item in query_ref.limit(limit).stream()]

    async def update(self, collection: str, doc_id: str, data: dict) -> bool:
        self._client().collection(collection).document(doc_id).update(data)
        return True

    async def delete(self, collection: str, doc_id: str) -> bool:
        self._client().collection(collection).document(doc_id).delete()
        return True

    async def set_merge(self, collection: str, doc_id: str, data: dict) -> bool:
        self._client().collection(collection).document(doc_id).set(data, merge=True)
        return True


db = FirestoreDB()
