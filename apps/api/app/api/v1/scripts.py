"""Discovery-script catalogue endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...domain import entities as e
from ..deps import Services, get_services

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("", response_model=list[e.ScriptDefinition])
def list_scripts(svc: Services = Depends(get_services)) -> list[e.ScriptDefinition]:
    return svc.scripts.list_scripts()


@router.get("/{script_id}", response_model=e.ScriptDefinition)
def get_script(script_id: str, svc: Services = Depends(get_services)) -> e.ScriptDefinition:
    return svc.scripts.get_script(script_id)
