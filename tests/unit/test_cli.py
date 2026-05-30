"""Tests for the CLI entrypoint scaffolding."""

from __future__ import annotations

import pytest

from mrds.cli.main import build_parser, main


def test_no_command_prints_help_and_succeeds() -> None:
    assert main([]) == 0


def test_planned_command_is_registered_but_not_implemented() -> None:
    # Each planned command parses successfully and exits with the
    # "not implemented yet" code (2).
    assert main(["evaluate"]) == 2


def test_parser_exposes_all_planned_commands() -> None:
    parser = build_parser()
    # Force argparse to surface the registered subcommand names.
    subactions = [a for a in parser._actions if a.dest == "command"]
    assert subactions, "expected a subcommand action"
    choices = set(subactions[0].choices or {})
    assert {"evaluate", "compare", "report", "promote-baseline"} <= choices


def test_version_flag_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
