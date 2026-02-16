from collections import defaultdict
from typing import Any, DefaultDict, Dict, Optional, TypeAlias

from pda.types.typehints import AnyT

NestedDefaultDict: TypeAlias = DefaultDict[str, Dict[str, AnyT]]


def nested_defaultdict(default: Optional[Dict[str, Dict[str, Any]]] = None) -> NestedDefaultDict[Any]:
    return defaultdict(lambda: defaultdict(dict), default if default is not None else {})
