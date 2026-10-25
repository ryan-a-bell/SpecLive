"""Workspace-level context aggregation for external consumers.

A workspace groups the discovery conversations that share a customer (derived
from the sessions list, mirroring the web app's grouping). These endpoints let
an external app — or an LLM architecting in another tool — pull all the
requirements and surrounding context gathered in SpecLive as one bundle.

``scope=baseline`` returns only human-confirmed items; ``scope=all`` also
includes still-unconfirmed candidates, each tagged with its validation state
and confidence.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response

from ...domain.enums import ContextScope
from ..deps import Services, get_services
from ..schemas import WorkspaceCreate, WorkspacePatch

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("")
def list_workspaces(svc: Services = Depends(get_services)) -> list[dict[str, Any]]:
    """List workspaces (customer groupings) and their conversations."""

    return svc.workspaces.list_workspaces()


@router.post("", status_code=201)
def create_workspace(
    body: WorkspaceCreate, svc: Services = Depends(get_services)
) -> dict[str, Any]:
    return svc.workspaces.create(**body.model_dump())


@router.patch("/{workspace_id}")
def patch_workspace(
    workspace_id: str,
    body: WorkspacePatch,
    svc: Services = Depends(get_services),
) -> dict[str, Any]:
    return svc.workspaces.patch(workspace_id, **body.model_dump(exclude_unset=True))


@router.get("/{workspace_id}/context", response_model=None)
def workspace_context(
    workspace_id: str,
    scope: ContextScope = ContextScope.ALL,
    format: str = "json",
    svc: Services = Depends(get_services),
) -> Response | dict[str, Any]:
    """Aggregate every conversation in the workspace into one context bundle."""

    package = svc.workspaces.build_context(workspace_id, scope=scope)
    if format in ("markdown", "md"):
        return Response(content=svc.workspaces.render_markdown(package), media_type="text/markdown")
    return package
