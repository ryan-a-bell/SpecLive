"""Discovery-script catalogue endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...domain import entities as e
from ..deps import Services, get_services
from ..schemas import ScriptDefinitionWrite

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("", response_model=list[e.ScriptDefinition])
def list_scripts(
    include_archived: bool = False, svc: Services = Depends(get_services)
) -> list[e.ScriptDefinition]:
    return svc.scripts.list_scripts(include_archived=include_archived)


@router.post("", response_model=e.ScriptDefinition, status_code=201)
def create_script(
    body: ScriptDefinitionWrite, svc: Services = Depends(get_services)
) -> e.ScriptDefinition:
    return svc.scripts.create(**body.model_dump())


@router.get("/{script_id}", response_model=e.ScriptDefinition)
def get_script(script_id: str, svc: Services = Depends(get_services)) -> e.ScriptDefinition:
    return svc.scripts.get_script(script_id)


@router.put("/{script_id}", response_model=e.ScriptDefinition)
def update_script(
    script_id: str,
    body: ScriptDefinitionWrite,
    svc: Services = Depends(get_services),
) -> e.ScriptDefinition:
    return svc.scripts.update(script_id, **body.model_dump())


@router.post("/{script_id}/archive", response_model=e.ScriptDefinition)
def archive_script(script_id: str, svc: Services = Depends(get_services)) -> e.ScriptDefinition:
    return svc.scripts.archive(script_id)
