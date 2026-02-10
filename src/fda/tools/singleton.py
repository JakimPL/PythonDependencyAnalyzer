"""Singleton metaclass implementation following Python best practices."""

import threading
from typing import Any, Dict, Type


class Singleton(type):
    _instances: Dict[Type[Any], Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance

        return cls._instances[cls]

    @classmethod
    def clear_instances(mcs) -> None:
        with mcs._lock:
            mcs._instances.clear()
