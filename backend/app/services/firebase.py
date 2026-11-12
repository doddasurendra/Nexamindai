"""Firebase Admin SDK and Firestore client service for NexaMind AI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import get_settings

settings = get_settings()

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    _FIREBASE_OK = True
except Exception:  # noqa: BLE001
    _FIREBASE_OK = False


@dataclass
class FirebaseClient:
    db: Any | None = None
    bucket: Any | None = None

    def get_db(self):
        return self.db

    def get_bucket(self):
        return self.bucket


def is_available() -> bool:
    return _FIREBASE_OK and settings.firebase_enabled


def initialize() -> FirebaseClient:
    """Initialize Firebase Admin and return a client."""
    if not is_available():
        raise RuntimeError(
            "Firebase is not configured. Set FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS_PATH, "
            "and install firebase-admin."
        )
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        firebase_admin.initialize_app(cred, {"storageBucket": settings.firebase_bucket or None})
    return FirebaseClient(db=firestore.client(), bucket=storage.bucket() if settings.firebase_bucket else None)


class FirebaseDB:
    """Thin wrapper around Firestore for NexaMind AI document storage."""

    def __init__(self, client: FirebaseClient):
        self.client = client

    def create(self, collection: str, document_id: str | None, data: dict) -> str:
        doc_ref = self.client.db.collection(collection).document(document_id)
        doc_ref.set(data)
        return doc_ref.id

    def get(self, collection: str, document_id: str) -> dict | None:
        snapshot = self.client.db.collection(collection).document(document_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def query(self, collection: str, filters: list[tuple] | None = None, limit: int = 50) -> list[dict]:
        query_ref = self.client.db.collection(collection)
        if filters:
            for field, op, value in filters:
                query_ref = query_ref.where(field, op, value)
        return [item.to_dict() for item in query_ref.limit(limit).stream()]

    def update(self, collection: str, document_id: str, data: dict) -> bool:
        self.client.db.collection(collection).document(document_id).update(data)
        return True

    def delete(self, collection: str, document_id: str) -> bool:
        self.client.db.collection(collection).document(document_id).delete()
        return True
