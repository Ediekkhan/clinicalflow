from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/documents/upload-url")
async def document_upload_url(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    payload = await request.json()
    try:
        application_id = uuid.UUID(str(payload.get("application_id")))
        filename = str(payload.get("filename") or "")
        content_type = str(payload.get("content_type") or "")
        size_bytes = int(payload.get("size_bytes") or 0)
        validate_document(
            filename=filename, content_type=content_type, size_bytes=size_bytes
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=422, detail="Invalid verification document"
        ) from error
    application = await session.scalar(
        select(SignupApplication).where(
            SignupApplication.id == application_id,
            (
                SignupApplication.account_id == account.id
                if account.role != "admin"
                else True
            ),
        )
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    key = private_object_key(
        tenant_id=str(account.tenant_id),
        application_id=str(application_id),
        filename=filename,
    )
    try:
        url = signed_upload_url(object_key=key, content_type=content_type)
    except StorageNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    document = VerificationDocument(
        signup_application_id=application_id,
        document_type=str(payload.get("document_type") or "OTHER"),
        private_storage_key=key,
        original_name=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        verification_status="UPLOAD_PENDING",
    )
    session.add(document)
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.DOCUMENT_UPLOADED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="VerificationDocument",
        resource_id=str(document.id),
        metadata={"phase": "URL_ISSUED"},
    )
    await session.commit()
    return {
        "document_id": str(document.id),
        "upload_url": url,
        "expires_in": settings.signed_url_ttl_seconds,
    }


@router.post("/documents/confirm")
async def confirm_document_upload(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, document = await _verification_document_access(
        request, session, str((await request.json()).get("document_id"))
    )
    try:
        metadata = object_metadata(object_key=document.private_storage_key)
    except Exception as error:
        raise HTTPException(
            status_code=422, detail="Uploaded object could not be verified"
        ) from error
    if (
        metadata["size_bytes"] != document.size_bytes
        or metadata["content_type"] != document.content_type
    ):
        raise HTTPException(
            status_code=422,
            detail="Uploaded object metadata does not match the declaration",
        )
    document.verification_status = "PENDING_VERIFICATION"
    await write_audit_log(
        session,
        AuditAction.DOCUMENT_UPLOADED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="VerificationDocument",
        resource_id=str(document.id),
        metadata={"phase": "CONFIRMED"},
    )
    await session.commit()
    return {"document_id": str(document.id), "status": document.verification_status}


@router.get("/documents/{document_id}/download-url")
async def document_download_url(
    document_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, document = await _verification_document_access(
        request, session, document_id
    )
    try:
        url = signed_download_url(object_key=document.private_storage_key)
    except StorageNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    await write_audit_log(
        session,
        AuditAction.DOCUMENT_DOWNLOADED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="VerificationDocument",
        resource_id=str(document.id),
    )
    await session.commit()
    return {"download_url": url, "expires_in": settings.signed_url_ttl_seconds}


@router.get("/documents/{document_id}")
async def get_verification_document(
    document_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _, document = await _verification_document_access(request, session, document_id)
    return {
        "id": str(document.id),
        "application_id": str(document.signup_application_id),
        "document_type": document.document_type,
        "original_name": document.original_name,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "checksum_sha256": document.checksum_sha256,
        "verification_status": document.verification_status,
        "created_at": document.created_at.isoformat(),
    }


@router.post("/documents/{document_id}/replace")
async def replace_verification_document(
    document_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, previous = await _verification_document_access(
        request, session, document_id
    )
    payload = await request.json()
    try:
        filename = str(payload.get("filename") or "")
        content_type = str(payload.get("content_type") or "")
        size_bytes = int(payload.get("size_bytes") or 0)
        validate_document(
            filename=filename, content_type=content_type, size_bytes=size_bytes
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=422, detail="Invalid replacement document"
        ) from error
    key = private_object_key(
        tenant_id=str(account.tenant_id),
        application_id=str(previous.signup_application_id),
        filename=filename,
    )
    try:
        url = signed_upload_url(object_key=key, content_type=content_type)
    except StorageNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    replacement = VerificationDocument(
        signup_application_id=previous.signup_application_id,
        document_type=previous.document_type,
        private_storage_key=key,
        original_name=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        replaced_by_id=previous.id,
        verification_status="UPLOAD_PENDING",
    )
    previous.verification_status = "REPLACED"
    session.add(replacement)
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.DOCUMENT_REPLACED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="VerificationDocument",
        resource_id=str(replacement.id),
        metadata={"replaced_document_id": str(previous.id)},
    )
    await session.commit()
    return {
        "document_id": str(replacement.id),
        "replaced_document_id": str(previous.id),
        "upload_url": url,
        "expires_in": settings.signed_url_ttl_seconds,
    }


@router.delete("/documents/{document_id}")
async def delete_verification_document(
    document_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    account, document = await _verification_document_access(
        request, session, document_id
    )
    try:
        delete_object(object_key=document.private_storage_key)
    except Exception as error:
        raise HTTPException(
            status_code=502, detail="Document storage deletion failed"
        ) from error
    document.verification_status = "DELETED"
    await write_audit_log(
        session,
        AuditAction.DOCUMENT_DELETED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="VerificationDocument",
        resource_id=str(document.id),
    )
    await session.commit()
    return {"document_id": str(document.id), "status": "DELETED"}
