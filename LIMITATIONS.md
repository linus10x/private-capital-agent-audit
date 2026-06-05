# Limitations

This library is **reference IP for adoption**, not a control operating in
production. Read these limits before relying on any part of it.

## Claim layer

- The five primitives are **real, tested reference patterns**. The seven adviser
  controls are **implemented and tested reference controls**. None of them is a
  deployed system at any firm, and none has been examined by a regulator.
- Nothing here is legal advice. The regulatory characterizations are engineering
  summaries; confirm every obligation against the primary source and a qualified
  compliance/legal function before relying on it.

## What the controls do and do not decide

- **The deployer supplies the judgment.** The MNPI control does not infer what
  is or is not material nonpublic information — the compliance function curates
  the restricted/watch lists; the control enforces the consequence (a
  restricted-name order is blocked). The best-execution control does not measure
  execution quality for you — it gates on deployer-supplied factors and a
  deployer-set benchmark and tolerance. The marketing control gates on structured
  attributes a reviewer asserts, not on reading advertisement prose.
- **Allocation fairness** surfaces a statistical asymmetry (favored vs. other
  accounts receiving favorable fills); it does **not** adjudicate intent, and a
  flag is a signal for review, not a finding of cherry-picking.
- **Independence is attested, not detected.** The effective-challenge harness
  enforces `challenger != primary` in code, but vendor-family and
  prompt-template independence are an **operator attestation** — no detector is
  fabricated. A false attestation is the operator's risk, recorded to the chain.

## What the audit chain does and does not prove

- The hash chain is **internally consistent** by construction: it detects
  after-the-fact mutation and chain-splice on replay, **within the trust
  boundary**. It does **not** prevent a privileged in-process actor from
  rewriting the store, and it does not, by itself, make end-to-end regeneration
  detectable.
- **End-to-end regeneration** (rebuilding the whole chain with internally
  consistent hashes) is only caught when chain heads have been anchored to an
  **external witness register** the deployer does not control alone
  (OpenTimestamps, a transparency log, a regulator-side log). Production mode
  requires one and fails closed without it. The bundled `InMemoryWitnessRegister`
  is a **reference for tests only** — it is not durable and is not external.

## Advisory vs. production mode

- The default `advisory` mode is backward-compatible and **labeled advisory** —
  it records honestly (`authenticated=false`, `mode="advisory"`) but does not
  fail closed. Only `production` mode enforces the fail-closed contracts (a wired
  Authorizer / attestation verifier / witness register). Choosing advisory mode
  in a real deployment is the deployer's risk.

## Depth boundaries (0.1.0)

These are reference controls at reference depth. Known shallowness an examiner
would extend, by design for 0.1.0:

- **Best execution** is reviewed *per order* against a deployer benchmark — a
  pre-trade/at-trade TCA check, not the periodic-and-systematic, across-venue
  review the regular-and-rigorous obligation also requires. Treat the per-order
  gate as one input to a periodic review the deployer runs.
- **MNPI surveillance** matches on the normalized symbol of the named instrument.
  It does not expand an issuer to its instrument family (bonds, options, ADRs,
  single-name CDS, index/ETF constituents); a deployer who needs family coverage
  supplies the expanded restricted set.
- **Allocation fairness** models trade-level block-fill cherry-picking. PE/credit
  conflicts that turn on **deal/co-investment allocation** across funds and LPs,
  and on **fee-and-expense allocation** (broken-deal, monitoring, expense
  shifting), are not modeled here and are the deployer's to extend.
- **Marketing review** gates the rule's headline conditions (hypothetical-
  performance policies, testimonial disclosure, net-of-fees). It does not cover
  every 206(4)-1 sub-condition (predecessor / related / extracted performance,
  third-party ratings, per-period gross-and-net).
- **Controls record and surface; they do not orchestrate enforcement.** A BLOCKED
  screen or an unapproved review is recorded — wiring that result to a sovereign
  veto (so the order/communication is actually stopped) is the deployer's
  integration, not an automatic side effect.

## Scope boundaries

- This library models the investment-adviser fiduciary regime only. It does not
  model the obligations of any other regulated actor, and it is not a substitute
  for a firm's compliance program, Form ADV, or its written §206(4)/Rule 206(4)-7
  policies and procedures.
- The DEFCON thresholds are **illustrative examples**, not calibrated values.
  Calibrate them to the program's strategy, capital base, and risk appetite.
