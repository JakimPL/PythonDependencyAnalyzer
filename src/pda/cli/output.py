from pathlib import Path
from typing import Dict, Optional, Tuple

from pda.config import LayoutMode, Theme
from pda.models import ModuleGraph, module_pyvis_converter
from pda.tools.logger import logger
from pda.tools.serialization import save_html

_EXTENSIONS: Dict[str, str] = {".json": "json", ".html": "html", ".htm": "html"}


def resolve_format(output: Path, fmt: Optional[str]) -> str:
    suffix = output.suffix.lower()
    extension_format = _EXTENSIONS.get(suffix) if suffix else None
    if suffix and extension_format is None:
        raise ValueError(f"Unsupported output extension '{output.suffix}'; expected .json, .html or .htm.")

    if fmt is not None:
        if extension_format is not None and extension_format != fmt:
            logger.warning("Output extension '%s' does not match --format %s; writing %s.", suffix, fmt, fmt)

        return fmt

    return extension_format or "json"


def resolve_output(output: Optional[Path], fmt: Optional[str], stem: str) -> Tuple[Path, str]:
    if output is not None:
        return output, resolve_format(output, fmt)

    resolved = fmt or "json"
    return Path(f"{stem}.{resolved}"), resolved


def _render_html(graph: ModuleGraph, *, theme: Theme, layout: Optional[LayoutMode]) -> str:
    converter = module_pyvis_converter(theme=theme, layout=layout)
    network = {**(converter.config.network or {}), "cdn_resources": "in_line"}
    converter.config = converter.config.model_copy(update={"network": network})
    return converter(graph, html=True)


def export(graph: ModuleGraph, output: Path, fmt: str, *, theme: Theme, layout: Optional[LayoutMode]) -> int:
    match fmt:
        case "html":
            save_html(_render_html(graph, theme=theme, layout=layout), output)
        case _:
            graph.save(output)

    logger.info("Wrote %d nodes and %d edges to %s", len(graph), len(graph.edges), output)
    return 0
