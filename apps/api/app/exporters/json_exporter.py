"""JSON discovery-package exporter."""

from __future__ import annotations

import json

from ..providers.base import ArtifactExporter


class JsonExporter(ArtifactExporter):
    format_id = "json"
    media_type = "application/json"

    def export(self, package: dict) -> str:
        return json.dumps(package, indent=2, ensure_ascii=False, default=str)
