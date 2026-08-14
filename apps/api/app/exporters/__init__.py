"""Discovery-package exporters.

The :class:`ArtifactExporter` interface (in ``app.providers.base``) lets new
formats — CSV, DOCX, ReqIF, Jira, DOORS, SysML — be added without touching the
export service. This increment ships JSON and Markdown.
"""

from ..providers.base import ArtifactExporter
from .json_exporter import JsonExporter
from .markdown_exporter import MarkdownExporter

_EXPORTERS: dict[str, ArtifactExporter] = {
    "json": JsonExporter(),
    "markdown": MarkdownExporter(),
}


def get_exporter(format_id: str) -> ArtifactExporter:
    if format_id not in _EXPORTERS:
        raise KeyError(f"Unknown export format '{format_id}'. Available: {list(_EXPORTERS)}")
    return _EXPORTERS[format_id]


def available_formats() -> list[str]:
    return list(_EXPORTERS)


__all__ = [
    "ArtifactExporter",
    "JsonExporter",
    "MarkdownExporter",
    "get_exporter",
    "available_formats",
]
