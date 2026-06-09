# Worked example — allocation fairness (§206 anti-cherry-picking)

One Advisers Act §206 control, walked end to end against a real enforcement
matter. The runnable script is
[`examples/worked_example_allocation_fairness.py`](examples/worked_example_allocation_fairness.py);
it uses the public API only and exits `0`.

```bash
python examples/worked_example_allocation_fairness.py
```

The matter: **SEC v. J.S. Oliver Capital Management, L.P. / Ian O. Mausner** —
charged PR 2013-168; **settled May 16, 2019 (Release 33-10639), ~$669,965
disgorgement**, neither admitting nor denying. The conduct the SEC penalized:
favorably-priced post-close fills steered to affiliated funds while unaffiliated
clients absorbed the worse fills. That is the exact shape this control catches.

## The five beats

### 1. The decision class — a block-trade allocation

A single block executes, then its fills are split across client accounts. Each
fill is tagged favorable / unfavorable versus the block's average execution, and
each account is tagged **favored** (affiliated / proprietary) or **other**
(unaffiliated client). Cherry-picking is favorable fills disproportionately
routed to the favored accounts.

### 2. The agent acting

An autonomous allocation agent (running at A3 — supervised-autonomous) proposes
an allocation that hands all three favorable fills to the affiliated funds and
leaves the clients the unfavorable ones — the J.S. Oliver shape.

### 3. The envelope catching the out-of-envelope case

`AllocationFairnessMonitor.assess(...)` computes the favorable-fill rate per
group. Favored accounts: **100%**. Other accounts: **33%**. Disparity **67%**,
far past the deployer-set 20% tolerance — so the assessment returns
`fair=False` with a §206 cherry-picking reason. The envelope is mechanical: the
agent does not get to argue the result away.

### 4. The audit entry

The flag is appended to the hardened, tamper-evident hash-chain ledger as an
`ALLOCATION_FAIRNESS_FLAG` event carrying the block id and the measured
disparity. `chain.verify()` stays `True` — the record is immutable and
replayable.

### 5. The demotion

The sovereign veto fires (`VetoReason.ALLOCATION_FAIRNESS`), so
`veto.allow_execution()` returns `False` — the agent's authority to keep
allocating is withdrawn. DEFCON escalates off NORMAL. Critically, **the agent
cannot clear its own veto**: restoring authority is a human-oversight act
(EU AI Act Art. 14), and DEFCON de-escalation is one level at a time. The whole
episode — allocation, flag, veto, escalation — is one internally consistent
audit trail.

## Output (verbatim)

```console
$ python examples/worked_example_allocation_fairness.py
WORKED EXAMPLE — Allocation fairness (§206 anti-cherry-picking)
Enforcement backdrop: SEC v. J.S. Oliver Capital Management / Mausner
  charged PR 2013-168; SETTLED 2019-05-16 (Release 33-10639), ~$669,965
  disgorgement. The conduct: favorably-priced post-close fills steered
  to affiliated funds. Below, the control catches that exact shape.

────────────────────────────────────────────────────────────────────────
1. Decision class — a block trade allocated across client accounts
────────────────────────────────────────────────────────────────────────
A single block executes, then its fills are split across accounts.
Each fill is tagged favorable/unfavorable vs the block's average
execution, and accounts are tagged favored (affiliated/proprietary)
or other (unaffiliated client). Cherry-picking = favorable fills
disproportionately routed to the favored accounts.

────────────────────────────────────────────────────────────────────────
2. The agent acting — an autonomous allocation agent at A3
────────────────────────────────────────────────────────────────────────
Agent 'allocation-agent' proposes this allocation of the block's fills:
    favored  affiliated-fund-A  FAVORABLE
    favored  affiliated-fund-B  FAVORABLE
    favored  affiliated-fund-C  FAVORABLE
    client   client-001         unfavorable
    client   client-002         unfavorable
    client   client-003         FAVORABLE

────────────────────────────────────────────────────────────────────────
3. The envelope — AllocationFairnessMonitor flags the asymmetry
────────────────────────────────────────────────────────────────────────
    fair                    : False
    favored favorable rate  : 100%
    other   favorable rate  : 33%
    disparity               : 67%  (tolerance 20%)
    reason                  : favored accounts received favorable fills at 100% vs 33% for others (disparity 67% > tolerance 20%) — possible cherry-picking (§206)

────────────────────────────────────────────────────────────────────────
4. The audit entry — the flag is on the tamper-evident ledger
────────────────────────────────────────────────────────────────────────
    chain length            : 2 events
    allocation-fairness flags recorded : 1
    flagged block_id        : BLOCK-2026-0420
    flagged disparity       : 67%
    chain verifies clean    : True

────────────────────────────────────────────────────────────────────────
5. Demotion — the veto fires and DEFCON escalates
────────────────────────────────────────────────────────────────────────
    agent may keep allocating: False  (False = halted)
    DEFCON level            : ALERT  (NORMAL=1 … HALT=5)
    An agent CANNOT clear its own veto; a human-oversight act
    (EU AI Act Art. 14) is required to restore authority, and
    de-escalation is one level at a time.

────────────────────────────────────────────────────────────────────────
Result
────────────────────────────────────────────────────────────────────────
    Full audit trail: 4 events, chain.verify() = True
    The control caught the J.S. Oliver allocation shape, recorded
    it immutably, and withdrew the agent's authority. That is the
    §206 control layer doing its one job.
```

## What this is, and is not

This is a *reference control* exercised on a *constructed* allocation in the
shape of a public enforcement matter — it is not an adjudication of J.S. Oliver,
and a flag is a review signal, not a finding. The favorable/favored tags are
deployer-asserted, structured inputs; the control does not independently observe
your order flow. Wiring it in does not make a firm compliant — the compliance
function owns the judgment. See [`LIMITATIONS.md`](LIMITATIONS.md) and
[`FAILURE-MODES.md`](FAILURE-MODES.md).
