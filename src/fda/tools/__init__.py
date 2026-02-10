from fda.tools.logger import setup_logger
from fda.tools.singleton import Singleton

logger = setup_logger()

__all__ = [
    "logger",
    "Singleton",
]
