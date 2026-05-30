"""MRDS command-line entrypoint.

This is the single, CLI-first entrypoint used both locally and in CI. The four
planned subcommands (``evaluate``, ``compare``, ``report``, ``promote-baseline``)
are scaffolded here; their behaviour is implemented in later sprints. For now they
are registered so the command surface is stable, and they exit with a clear
"not implemented yet" message.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from mrds import __version__
from mrds.config.settings import get_settings
from mrds.observability.logging import configure_logging, get_logger

logger = get_logger(__name__)

# Planned commands mapped to the sprint that implements them (architecture §11).
_PLANNED_COMMANDS: dict[str, str] = {
    "evaluate": "Sprint 5",
    "compare": "Sprint 6",
    "report": "Sprint 7",
    "promote-baseline": "Sprint 6",
}


def _not_implemented(args: argparse.Namespace) -> int:
    """Placeholder handler for commands not yet implemented."""
    logger.warning("Command '%s' is not implemented yet (%s).", args.command, args.sprint)
    print(
        f"`mrds {args.command}` is not implemented yet — planned for {args.sprint}.",
        file=sys.stderr,
    )
    return 2


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with planned subcommands registered."""
    parser = argparse.ArgumentParser(
        prog="mrds",
        description="Model Regression Detection System — AI evaluation & deployment-safety CLI.",
    )
    parser.add_argument("--version", action="version", version=f"mrds {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, sprint in _PLANNED_COMMANDS.items():
        sub = subparsers.add_parser(name, help=f"(not implemented yet — {sprint})")
        sub.set_defaults(func=_not_implemented, sprint=sprint)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.json_logs)

    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
