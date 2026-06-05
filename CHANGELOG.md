# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — unreleased

First public release: a standalone, DOI-publishable governance pattern library
for autonomous AI agents at SEC-registered investment advisers.

### Added

- **Five corrected Autonomy Ladder primitives**, each with a committed
  adversarial probe under `tests/adversarial/`:
  - P1 `AutonomyLadder` — level gate with independent attestation; advisory /
    production modes.
  - P2 `SovereignVeto` — un-self-clearable kill switch; authenticated,
    non-agent-principal clears in production mode.
  - P3 `AuditChain` — deployer-keyed genesis event; branched verify seed so
    hardened and legacy chains both verify; witness-anchored regeneration
    resistance, non-optional in production mode.
  - P4 `DEFCONMachine` — immediate escalation, one-step authorized
    de-escalation; a single call cannot move `HALT → NORMAL`.
  - P5 `EffectiveChallengeHarness` — rejects self-challenge; records an operator
    independence attestation; no self-validation to `ACCEPT_PRIMARY`.
- **Seven adviser-native controls**: best execution, MNPI/market-abuse
  surveillance, custody rule, marketing rule, cross-client allocation fairness
  (anti-cherry-picking), books-and-records / off-channel-communications capture,
  and independent-valuation governance.
- **Obligation map** (`obligation_map`) — the sub-vertical → obligation
  surface, every citation primary-source verified 2026-06-05.
- **Test suite**: unit + contract, property-based (`hypothesis`), the five
  AL-PROBES, a golden corpus of real public SEC enforcement actions, a
  combinatorial matrix, and a deterministic mutation pass
  (`scripts/mutation_check.py`). CI coverage gate `--cov-fail-under=90`.
- Zero runtime dependencies; `ruff` + `mypy --strict` clean; MIT OR Apache-2.0.

[0.1.0]: https://github.com/linus10x/private-capital-agent-audit/releases/tag/v0.1.0
