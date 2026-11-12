"""Knowledge bases, document ingestion, RAG retrieval and grounded answers."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import Document, DocumentChunk, KnowledgeBase, MediaItem, UploadedFile, User
from ..schemas import (
    DocumentOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    RagQuery,
    RagResponse,
)
from ..services import rag
from ..services.docs import extract_text
from ..services.media import delete_file, kind_for_extension, save_upload

router = APIRouter(prefix="/api", tags=["knowledge"])


async def _own_kb(db: AsyncSession, kb_id: int, user: User) -> KnowledgeBase:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None or kb.user_id != user.id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.post("/knowledge-bases", response_model=KnowledgeBaseOut, status_code=201)
async def create_kb(
    payload: KnowledgeBaseCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> KnowledgeBaseOut:
    kb = KnowledgeBase(user_id=user.id, name=payload.name, description=payload.description)
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return KnowledgeBaseOut.model_validate(kb)


@router.get("/knowledge-bases")
async def list_kbs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (
        await db.execute(
            select(KnowledgeBase, func.count(Document.id))
            .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
            .where(KnowledgeBase.user_id == user.id)
            .group_by(KnowledgeBase.id)
            .order_by(KnowledgeBase.id.desc())
        )
    ).all()
    return [
        {**KnowledgeBaseOut.model_validate(kb).model_dump(), "document_count": count}
        for kb, count in rows
    ]


@router.delete("/knowledge-bases/{kb_id}", status_code=204)
async def delete_kb(kb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    kb = await _own_kb(db, kb_id, user)
    documents = (await db.execute(select(Document).where(Document.knowledge_base_id == kb.id))).scalars().all()
    for document in documents:
        delete_file(document.stored_path)
    await db.delete(kb)
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)


@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    await _own_kb(db, kb_id, user)
    path, digest, size = await save_upload(user.id, file, "document")
    document = Document(
        knowledge_base_id=kb_id,
        user_id=user.id,
        filename=file.filename or path.name,
        stored_path=str(path),
        mime_type=file.content_type or "application/octet-stream",
        size=size,
        status="processing",
        meta={"sha256": digest},
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    try:
        text, meta = extract_text(Path(document.stored_path), document.filename, document.mime_type)
        chunks = await rag.index_document(db, document, text)
        document.status = "ready"
        document.meta = {**(document.meta or {}), **meta, "chunks": chunks, "characters": len(text)}
    except Exception as exc:  # noqa: BLE001
        document.status = "error"
        document.error = str(exc)
    await db.commit()
    await db.refresh(document)
    db.add(
        UploadedFile(
            user_id=user.id,
            filename=document.filename,
            stored_path=document.stored_path,
            mime_type=document.mime_type,
            size=size,
            sha256=digest,
            kind="document",
        )
    )
    await db.commit()
    return DocumentOut.model_validate(document)


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    kb_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[DocumentOut]:
    await _own_kb(db, kb_id, user)
    documents = (
        await db.execute(select(Document).where(Document.knowledge_base_id == kb_id).order_by(Document.id.desc()))
    ).scalars().all()
    return [DocumentOut.model_validate(d) for d in documents]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_file(document.stored_path)
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    await db.delete(document)
    await db.commit()
    from fastapi import Response

    return Response(status_code=204)


@router.post("/documents/extract")
async def extract_upload(
    file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Extract text from a document without adding it to a knowledge base."""
    path, digest, size = await save_upload(user.id, file, "document")
    db.add(
        UploadedFile(
            user_id=user.id,
            filename=file.filename or path.name,
            stored_path=str(path),
            mime_type=file.content_type or "",
            size=size,
            sha256=digest,
            kind="document",
        )
    )
    await db.commit()
    text, meta = extract_text(Path(path), file.filename or path.name, file.content_type or "")
    return {
        "filename": file.filename,
        "characters": len(text),
        "text": text[:20000],
        "meta": meta,
        "uploaded_file_id": None,
    }


@router.post("/rag/query", response_model=RagResponse)
async def rag_query(payload: RagQuery, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> RagResponse:
    await _own_kb(db, payload.knowledge_base_id, user)
    hits = await rag.retrieve(db, payload.knowledge_base_id, payload.query, payload.top_k, payload.mode)
    return RagResponse(query=payload.query, hits=hits, mode=payload.mode)


@router.post("/rag/answer")
async def rag_answer(payload: RagQuery, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    await _own_kb(db, payload.knowledge_base_id, user)
    return await rag.answer_with_rag(
        db, payload.knowledge_base_id, payload.query, top_k=payload.top_k, mode=payload.mode
    )
