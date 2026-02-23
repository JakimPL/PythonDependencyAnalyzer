"""
Test file for imports at different scope levels: module, function, class.
"""

import json
import sys
from pathlib import Path
from typing import Any, DefaultDict, List

import_alias = sys
from collections import defaultdict as default_dict


def import_in_function_scope() -> None:
    import json as json_alias
    from pathlib import Path as PathAlias

    json_local = json_alias.dumps({})
    path_local = PathAlias(".")


def nested_imports() -> None:
    def outer_function() -> None:
        import re
        from datetime import datetime as DateTimeAlias

        regex_local = re.compile(r"\d+")
        datetime_local = DateTimeAlias.now()

        def inner_function() -> None:
            import hashlib
            from base64 import b64encode

            hash_object = hashlib.sha256(b"test")
            encoded = b64encode(b"data")


class ClassWithImports:
    import itertools
    from functools import lru_cache as class_level_lru_cache  # type: ignore[misc]

    @class_level_lru_cache(maxsize=None)  # type: ignore[misc]
    def cached_method(self, argument: int) -> int:
        method_local = argument
        return next(self.itertools.count(argument))


def global_import_usage() -> None:
    path_object = Path("/tmp")
    json_string = json.dumps({"key": "value"})
    default_dict_instance: DefaultDict[Any, List[Any]] = default_dict(list)


def local_import_usage() -> None:
    import hashlib
    from base64 import b64encode

    hash_object = hashlib.sha256(b"test")
    encoded = b64encode(b"data")


if __name__ == "__main__":
    main_guard_variable = "main"
    import argparse
    from pprint import pprint

    parser = argparse.ArgumentParser()
    pprint({"main": True})
