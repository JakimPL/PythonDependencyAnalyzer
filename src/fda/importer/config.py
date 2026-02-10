from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ImportConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scan_external: bool = Field(default=True, description="Include stdlib/site-packages")
    scan_uninstalled: bool = Field(default=True, description="Try to analyze missing modules")
    resolve_wildcards: bool = Field(default=True, description="Expand wildcard imports")
    max_depth: Optional[int] = Field(default=None, description="Limit recursion depth")
    follow_conditional: bool = Field(default=True, description="Analyze try/except branches")
