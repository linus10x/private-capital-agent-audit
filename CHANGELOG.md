# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Repository-uplift documentation pass (no source/API changes):

- **README top locked to the family template** — one-line description under the
  title; badge row extended with **Tests** and **Autonomy Ladder family**
  (→ meta-repo) badges; claim-layer blockquote restated as What this is / What
  this is not / Who this is for; added a **30-second tour** and a **Read me
  first** section (golden-corpus test → `WORKED_EXAMPLE.md` →
  autonomy-ladder.io). Install pinned to `v0.1.3`. Sibling list added at the
  bottom; family sections cross-reference the
  [autonomy-ladder-libraries](https://github.com/linus10x/autonomy-ladder-libraries)
  meta-repo.
- **`WORKED_EXAMPLE.md` + runnable script** — `examples/worked_example_allocation_fairness.py`
  walks the allocation-fairness (§206 anti-cherry-picking) control end to end
  against the J.S. Oliver enforcement shape: decision class → agent acting →
  envelope catch → audit entry → veto/DEFCON demotion. Runs on the public API;
  verbatim output pasted into the doc.
- **`AUTONOMY_LADDER.md`** — maps the five primitives and seven adviser controls
  (best_execution, mnpi_surveillance, custody_rule, marketing_rule,
  allocation_fairness, books_and_records, valuation_governance) onto the A0→A4
  rungs, with the demotion mechanism and a cross-reference to autonomy-ladder.io.

## [0.1.3] — 2026-06-09

Frontier-autonomy README section + 'for reviewers & safety teams' note; links the framework and the non-financial agent-coordination demo. No source changes.

## [0.1.2] — 2026-06-09

Documentation release: README upgraded to the conversion standard (buyer hook, CI/coverage/license badges, real-enforcement proof section); reconciled __init__ version. No source/API changes.

## [0.1.1] — 2026-06-06

Zenodo-archived release (DOI). No API changes.

### Changed

- Independent primary-source fact-check of the public surface: all statutory/CFR
  citations confirmed; every named-party enforcement matter in the golden corpus
  verified against its SEC primary source. The September 2023 nine-adviser
  marketing-rule sweep is now anchored to its confirmed release (PR 2023-173);
  the Hi2 custody finding was tightened to the order's exact language.
- Added `.zenodo.json` (native Zenodo deposit metadata) and a CFF-list `license`
  so Zenodo archives the release with correct metadata.

## [0.1.0] — 2026-06-05

First public release: a standalone, DOI-publishable governance pattern library
for autonomous AI agents at SEC-registered investment advisers. All
statutory/CFR citations are primary-source verified.

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
