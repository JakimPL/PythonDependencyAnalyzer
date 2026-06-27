from typing import Optional, Sequence

from pda.cli.parser import build_parser
from pda.exceptions import PDAException
from pda.tools.logger import logger


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (PDAException, ValueError, OSError) as error:
        logger.error("%s", error)
        return 1
