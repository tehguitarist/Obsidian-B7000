# HANDOVER — split the CLEAN release-gate row (decided with the user, session 95, 2026-08-01)

> ✅ **STATUS: EXECUTED IN SESSION 96 (2026-08-01). This document is now the DERIVATION OF RECORD,
> not a work item.** Landed in `analysis/release_gate.py`; `CLAUDE.md`'s convenience copy updated in
> the same change. All five §4 acceptance checks passed, including the load-bearing one — the s90
> baseline stops failing retroactively. Measured after the change:
>
> | | midband 100 Hz–8 kHz (≤0.30/≤0.80) | HF 8–16.3 kHz (≤0.40/≤1.40) |
> |---|---|---|
> | **s91_shipped** | 0.215 / 0.719 ✅ | 0.340 / 1.308 ✅ |
> | **s90_baseline129_h1** | 0.226 / 0.727 ✅ | 0.347 / 1.309 ✅ |
>
> Every OD row and the THD row reproduced to the digit (0.742 / 5.089 / 1.024 / 6.065 / 0.662 /
> 8.076 / p99 14.408 / band-RMS 2.664 / THD 4.279), so the change touched CLEAN and nothing else.
> Gated rows over SHIP went 9 → 8; the script still exits non-zero on the remaining OD/THD rows.
>
> **Two things were done BEYOND this spec, both strengthening §4:**
> 1. §4.4's "assert it, do not eyeball it" is implemented as `check_clean_partition()`, sharing one
>    `region_sel()` resolver with `pool()` so the check cannot pass against logic the pool does not
>    use — then **mutation-tested three ways** (dropped band / overlapping regions / extra band
>    below the pool). Known answer passes, all three mutations caught. 19 + 4 = 23 bands.
> 2. §3's robustness check was re-run at VERDICT level rather than spread level: all **24** CLEAN
>    verdicts (4 rows × `csd`/`h1`/`h1band` × both baselines) read SHIP.
>
> The original spec follows unchanged, as the record of what was decided and why.

---

> **Status at hand-over: DECIDED, NOT EXECUTED.** The user chose the split and asked for it to be
> handed over rather than done in session 95. Everything needed to execute it is below, including the
> measured numbers, their derivation, the robustness checks already run, and the traps.
>
> **Scope: `analysis/release_gate.py` only.** No DSP constant, no render, no re-baseline. The
> existing reports (`s90_baseline129_h1.json`, `s91_shipped.json`) are sufficient — this is a
> re-grade of data already on disk, so it costs seconds, not the ~25 min a matrix run costs.

---

## 1. Why — the row as written fails the baseline it exists to guard

`CLEAN` is gated as **one pooled row over 100 Hz – 16.3 kHz**, `median ≤0.30 / p90 ≤0.80`.
Measured on the H1-band read, 168 CLEAN rows, membership identical between the two baselines:

| CLEAN region | bands | s90 median / p90 | s91 median / p90 |
|---|---|---|---|
| **100 Hz – 8 kHz** | 19 | 0.226 / 0.727 | **0.215 / 0.719** (improved) |
| **8 – 16.3 kHz** | 4 | 0.347 / 1.309 | **0.340 / 1.308** (unchanged) |
| *pooled, as gated* | 23 | 0.235 / **0.802** | 0.234 / **0.808** |
| 25 – 100 Hz *(excluded, hardware-governed)* | 6 | 0.233 / 0.669 | 0.323 / 0.843 |

Three things follow, and all three are the reason for the split:

1. ⛔ **The bar fails BOTH baselines.** 0.802 and 0.808 against ≤0.80. A gate that fails the
   shipped baseline it was written to protect is a false alarm, not a regression detector.
2. ⭐ **Session 91 did not cause it.** The two shipped constants moved the gated p90 by **0.006 dB**;
   the 8–16.3 kHz region is unchanged to 3 dp and the midband *improved*. The 0.80 bar was agreed in
   session 89 against a hand-transcribed **0.66** that session 90 re-measured at **0.77** on the same
   file — so its intended 0.14 dB of headroom was really 0.03 dB, and the pool change consumed it.
3. ⭐⭐ **The pooled number is an average of a fine midband and a bad 4-band tail.** 0.719 and 1.308
   average to 0.808 and neither is readable from it. This is exactly the criticism `CLAUDE.md`
   already makes of the OD 8–16.3 kHz row ("the tail explodes… a subset of rows failing badly, not a
   noise floor") — the same structure, unfixed, on the CLEAN side.

---

## 2. What to change

In `analysis/release_gate.py`:

**(a) `COMPOSITES`** — the CLEAN pool `100 Hz-16.3 kHz` is no longer needed as a gated region. Keep
it defined (the side-by-side pool print at the end of `print_report` uses it, and it is the only
thing that makes the session-91 pool change visible), but stop gating on it.

**(b) `GATE`** — replace the two CLEAN rows with four:

```python
GATE = [
    ("CLEAN", "100 Hz-8 kHz",  "median", 0.30, None),
    ("CLEAN", "100 Hz-8 kHz",  "p90",    0.80, None),
    ("CLEAN", "8-16.3 kHz",    "median", 0.40, None),
    ("CLEAN", "8-16.3 kHz",    "p90",    1.40, None),
    ...                      # every OD row and the THD row unchanged
]
```

**Derivation of each bar — none of these is a round number picked to make the row pass:**

| bar | now (s91) | headroom | why that headroom |
|---|---|---|---|
| midband median ≤0.30 | 0.215 | 0.085 (40 %) | **unchanged from session 89.** It finally has real headroom because it is now measured on the pool it was meant for. |
| midband p90 ≤0.80 | 0.719 | 0.081 (11 %) | **unchanged from session 89** — same reason. The originally agreed number survives the split intact, which is the strongest argument that the split is a correction and not a concession. |
| HF median ≤0.40 | 0.340 | 0.060 (18 %) | new row; set by the same rule as the midband's — roughly 1.5–2× the statistic's drift under unrelated shipped work (see below). |
| HF p90 ≤1.40 | 1.308 | 0.092 (7 %) | new row; same rule. Deliberately the tightest of the four, because this band is the one under suspicion and the bar should fire if it moves. |

**Where "drift under unrelated shipped work" comes from** — the only honest headroom scale available:
between s90 and s91 (two shipped DSP constants, neither CLEAN-directed) the gated CLEAN p90 moved
**0.006 dB**, the midband p90 **0.008**, the HF p90 **0.001**. On the *ungated* pool the same change
moved p90 **0.053 dB**. So ~0.01–0.05 dB is what this statistic does when something unrelated ships;
the bars above sit 0.06–0.09 dB clear of that.

**(c) The verdict text.** `print_report` prints a paragraph about the session-91 CLEAN pool change
and the un-re-derived 0.80 bar. That paragraph becomes stale the moment this lands — rewrite it to
state the split and its derivation, and keep printing the old pooled figure as a labelled CONTROL so
the pre-split history stays diff-able (`computed-verdicts-not-narrated`, and the reason `release_gate`
exists at all).

---

## 3. Checks already run — do not redo these, but do not skip §4 either

⭐ **The split bars are NOT brittle to the FR read.** Re-graded from the same renders through all
three stored reads (`--method csd|h1|h1band`), both baselines:

| region | statistic | spread across the 3 reads × 2 baselines |
|---|---|---|
| 100 Hz – 8 kHz | median | 0.215 … 0.226 (**0.011**) |
| 100 Hz – 8 kHz | p90 | 0.719 … 0.729 (**0.010**) |
| 8 – 16.3 kHz | median | 0.331 … 0.347 (**0.016**) |
| 8 – 16.3 kHz | p90 | 1.295 … 1.309 (**0.014**) |

Every spread is well inside every proposed headroom, so no bar above is an artefact of which
estimator the report happened to be graded on. (This mattered: a bar 0.09 dB above the value would
be indefensible if the value itself moved 0.05 dB with the read.)

---

## 4. Acceptance — what must be true after the change

1. `release_gate.py analysis/reports/s91_shipped.json` → **all four CLEAN rows read SHIP.**
2. `release_gate.py analysis/reports/s90_baseline129_h1.json` → **also all four SHIP.** ⚠ This is the
   load-bearing check and it is the whole point: the pre-session-91 baseline must stop failing
   retroactively. If it does not pass, the split has been mis-derived — do not loosen a bar to make
   it pass, come back and re-read §1.
3. **Every OD row and the THD row must reproduce to the digit** — 0.742 / 5.089 / 1.024 / 6.065 /
   0.662 / 8.076 / p99 14.408 / band-RMS 2.664 / THD 4.279 on `s91_shipped.json`. This change touches
   only CLEAN; anything else moving means `COMPOSITES`/`REGIONS` was edited wrongly.
4. `check_partition` must still pass — the four CLEAN bands plus the nineteen midband bands must
   account for exactly the 23 bands the old pooled row covered, with none double-counted and none
   dropped. **Assert it, do not eyeball it**; a silently dropped band would make every bar look
   better and is exactly `aggregate-moved-check-membership-first`.
5. `--compare csd h1 h1band` must still run and must print all four CLEAN rows.

---

## 5. Traps specific to this change

- ⚠ **The HF median bar is ABOVE the midband's (0.40 vs 0.30), and that is the honest outcome, not a
  fudge.** CLEAN's top four bands genuinely are worse than its midband (0.340 vs 0.215 median, 1.308
  vs 0.719 p90). The split makes that visible for the first time; a single bar for both would either
  hide it (pooled) or fail a region nothing is currently working on. **Say so in the gate's own
  output** rather than letting the two different numbers read as an inconsistency.
- ⚠ **Do NOT also exclude 8–16.3 kHz from CLEAN the way 25–100 Hz was excluded.** `reference-sources.md`
  §1's "HF corners" clause would arguably justify it and `CLAUDE.md` already flags the temptation —
  but nothing in sessions 91–95 touched HF, and bundling that exclusion in behind an unrelated,
  justified change is precisely the move that would make the gate untrustworthy. The split is a
  *readability* fix; it must not quietly become an *authority* change.
- ⚠ **`CLAUDE.md` carries a convenience copy of the gate table and it will rot.** Update the CLEAN
  rows there in the same commit, and keep the standing note that `release_gate.py` is the definition.
- ⚠ Re-read `.claude/rules/measurement-discipline.md` §2's entry on this exact row before starting —
  "EXCLUDING A REGION FROM AN AGGREGATE CAN MAKE IT WORSE" is the s91 lesson that produced this
  handover, and the same reflex (assume a pool change is a loosening) is what to guard against here.
  **Compute both baselines, both ways, before describing this split as a loosening or a tightening.**

---

## 6. What this does NOT close

Splitting the row does not improve CLEAN by one dB — it makes two honest verdicts out of one
misleading average. **CLEAN's 8–16.3 kHz band remains its worst region (p90 1.308, max 3.148) and is
now explicitly gated rather than diluted.** Whether that band is worth work is a separate question
and belongs with the OD 8–16.3 kHz item, which is the same four bands and the same open suspicion
(`CLAUDE.md`: "is the residual ND's artefact or our Sallen-Keys?").
