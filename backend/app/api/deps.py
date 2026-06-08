from uuid import UUID

from fastapi import Request


def current_tenant_id(request: Request) -> UUID:
    return request.state.tenant_id


def current_staff_id(request: Request) -> UUID | None:
    return request.state.staff_id

