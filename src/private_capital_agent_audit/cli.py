"""Minimal CLI for private-capital-agent-audit.

Exposes the regulatory-accuracy surface for quick inspection without importing
the package programmatically. Intentionally tiny — the library's value is its
API and tests, not a command surface.

Usage::

    private-capital-audit version
    private-capital-audit obligations            # all obligations
    private-capital-audit obligations buy_side_quant   # one sub-vertical
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from private_capital_agent_audit import __version__
from private_capital_agent_audit.governance.obligation_map import (
    ALL_OBLIGATIONS,
    SubVertical,
    obligations_for,
)


def _print_obligations(args: Sequence[str]) -> int:
    if args:
        try:
            sub = SubVertical(args[0])
        except ValueError:
            valid = ", ".join(s.value for s in SubVertical)
            print(f"unknown sub-vertical {args[0]!r}; valid: {valid}", file=sys.stderr)
            return 2
        obligations = obligations_for(sub)
    else:
        obligations = tuple(ALL_OBLIGATIONS.values())

    for o in obligations:
        mark = "" if o.verified else " [UNVERIFIED]"
        print(f"{o.obligation_id}: {o.title}{mark}")
        print(f"    cite: {o.citation}")
        print(f"    src:  {o.primary_source_url}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    command, rest = argv[0], argv[1:]
    if command == "version":
        print(__version__)
        return 0
    if command == "obligations":
        return _print_obligations(rest)
    print(f"unknown command {command!r}; try 'help'", file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
