from pathlib import Path
from typing import Dict, TypeAlias

from pydepgraph.nodes.paths.node import PathNode

PathMapping: TypeAlias = Dict[Path, PathNode]
