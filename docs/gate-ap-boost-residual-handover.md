# HANDOVER — GATE AP's Boost residual, and whether AP3a is broken or is telling the truth

> Written at session 191, at the user's request, to be picked up as its own session.
> ⛔ **Read `.claude/rules/reference-sources.md` and `.claude/rules/measurement-discipline.md`
> first, as always.** Then `docs/session-log.md` SESSION 191 (continued) §3, which is where this
> defect was found and what the numbers below come from.

---

## 0. The one-paragraph version

`analysis/null_depth_censor_gate.py` (GATE AP) converts the pedal's notch depth into the shipped
`OdToneRestore` table's own unit by solving, per cell, for the biquad cut at which the composite's
depth equals the pedal's. **AP3a is its load-bearing known answer**: that solve, run in the POINT
metric, must return the SHIPPED table, because the shipped table was fitted in the point metric —
and without it, any disagreement between AP3's two metric columns is equally consistent with the
solve simply being wrong. At session 152 AP3a passed at **0.57 dB rms**. It now reads **6.62 dB**
(bar 2.49 = 3× the fit's own ±0.83 residual), **worst 12.87 dB**, and the gate correctly refuses to
let AP3 or AP5 be read. Session 191 found and fixed one real defect inside it — which repaired the
**Cut** row to within ±1 dB — and the residual is now concentrated almost entirely on **Boost**
(−10.10 / −12.87 / −10.38 dB across DRIVE 0 / 0.5 / 1.0). **This session's job is to find out why,
and in particular to decide whether AP3a is a broken check or a correct report that the shipped
table no longer matches the model.**

⚠ **Nothing here blocks anything that has shipped.** No DSP constant is implicated. What it blocks
is **step 5 of the action list** (item 10's `OdToneRestore` re-fit), because the tool that would
price that re-fit cannot currently certify its own solve.

---

## 1. What is already fixed, and must not be re-done

**GATE AP was internally inconsistent from s156 to s191.** AP3 subtracted the stage using
`F.current_response(..., clean_frac_of(fname))` — the FULL mix-keyed curve, correct — and compared
its solve against `F.lerp5(T["kNotchGainDb"][gpos], drv, T["kX"])`, **the base table alone**. Since
s156 the cut is `kNotchGainDb + kNotchMixK · S(cleanFrac)`, so the gate subtracted one stage and
compared against a different one.

✅ Fixed by extracting **`od_tone_restore_fit.cut_db(T, grunt, drive, clean_frac)`** as the single
resolver both call — asserted bit-identical to the retired inline expression at 9/9 (grunt × drive)
cells, with `clean_frac=None` preserving `current_response`'s documented default so every pre-s191
call is unchanged.

⭐ **The fix is corroborated by WHICH rows it moved**, and this is worth understanding before
touching anything:

| row | `kNotchMixK` | effect of the fix on `ship` | AP3a diff before → after |
|---|---|---|---|
| Cut | **−7.87 … −9.65** | pushes `ship` DOWN ~9 dB | −8.51 / −8.46 / −9.86 → **−1.03 / +0.43 / −0.68** |
| Flat | −1.56 … +2.97 | barely moves it | −1.49 / −0.88 / +2.95 → −0.00 / −3.71 / +2.03 |
| Boost | **+3.40 … +5.81** | pushes `ship` UP ~5.5 dB | −6.86 / −7.34 / −4.85 → **−10.10 / −12.87 / −10.38** |

(`S(bleed-free corner) = 0.951`, cf = 0.02418 — s185's re-anchor, so the mix term is near full
value at exactly the membership AP's default grades.)

⇒ the fix is unambiguously right as arithmetic (`ship` is now the cut the build actually applies),
it repaired the row where it pushed toward the solve, and it enlarged the row where it pushed away.
**That is the expected behaviour of a correct fix on top of a second, independent problem — not a
reason to revert it.**

---

## 2. ⛔ ONE CANDIDATE IS ALREADY REFUTED — do not spend the session on it

s191 named three candidates for the Boost residual. **The most attractive one is dead.**

**REFUTED: s156's DEPTH CEILING.** The hypothesis was that past a certain cut the composite's
measured depth saturates (extra depth averaged away by the 1/48-oct grid), so a point solve returns
the smallest gain reaching the target rather than the shipped one. Measured directly — the composite
depth evaluated against gain at every Boost cell, bleed-free, stage subtracted:

```
Boost d0.00 sweep_drv_-18   ship=20.38  pedal_pt=20.62  Q=16.71
    gain  0:  9.75   5: 13.66  10: 17.41  15: 20.88  20: 24.92
         25: 29.66  30: 34.26  40: 42.81  60: 55.59
```

**Monotone and essentially linear from 0 to 60 dB, at every Boost cell, on every sweep.** No
saturation, no plateau, no ceiling. ⚠ That does NOT contradict s156 — s156's ceiling was measured at
the **listening mix**, where the clean tap floors the null's bottom. Bleed-free there is no floor,
so there is nothing to saturate against. ⇒ **the ceiling is a MIX property**, which is the same
scoping s191 found for the point-vs-area distinction itself (see §5).

⚠ It does leave AP3's `NONMONO` flag unexplained (1 cell bleed-free, 18 mixed, "3 sign changes").
Those are almost certainly the *root-finder* seeing multiple crossings on a noisy `err(gain)`, not
the depth being non-monotone. **Check that before assuming it is a second defect.**

---

## 3. ⭐ THE LEADING HYPOTHESIS, and it reframes the whole question

**AP3a may not be broken. It may be correctly reporting that the SHIPPED TABLE IS STALE.**

AP3a's premise is stated in its own docstring: *"the shipped table was fitted in the point metric by
iterating a rebuild-and-re-measure loop, so an independent analytic solve in the same metric has a
right answer that already exists."* That premise carries an unstated clause — **against the model
that was shipping at the time**. Since AP3a last passed (s152, 0.57 dB) the following have landed:

- **s156** — the table itself was re-fitted as a **MIX-KEYED law**, and `kNotchGainDb` **changed
  meaning** (it is now the cut at `kMixCfRef`, not the bleed-free cut).
- **s172** `OdMakeup` (+6 dB OD-branch makeup, two shelves, `odNotchDepthDb` +3.0) · **s173** the
  mix-keyed HF term + a taper re-fit · **s177** C31 · **s180** the bass shelf · **s181**
  `blendEndStop` · **s185** the mix-law re-anchor · **s187** the GRUNT-keyed LF pair (⚠ **Cut
  only** — which is interesting given that Cut is the row that now agrees) · **s190** the LEVEL
  taper.

Every one of those moves the model's own null depth and therefore the cut the model needs.
⇒ **the solve returns what the CURRENT model needs; the table records what s156 fitted.** A
disagreement is then a *measurement of staleness*, not an instrument fault — and the per-row
pattern (**Cut ~1 dB, Flat ~2–4, Boost ~10**) becomes a directly useful input to item 10.

⚠⚠ **This is a hypothesis, not a finding. Do not write it into `CLAUDE.md` as a conclusion until
§4's test has run.** In particular it does not yet explain why Boost specifically is the worst row,
and one obvious sub-hypothesis has already failed (see below).

**Sub-hypothesis that does NOT survive on its own — the per-sweep spread.** AP averages the three
per-sweep solved gains, and the pedal's own point depth spans a lot across stimulus at fixed
(GRUNT, DRIVE):

| cell | pedal depth per sweep (−18 / −12 / −6) | span | AP3a diff |
|---|---|---|---|
| Cut 0.00 | 10.04 / 8.59 / 6.18 | 3.86 | −1.03 |
| Cut 0.50 | 21.79 / 13.92 / 8.47 | **13.31** | **+0.43** |
| Flat 1.00 | 12.17 / 27.70 / 30.22 | **18.05** | +2.03 |
| Boost 0.00 | 20.62 / 24.91 / 7.52 | **17.40** | **−10.10** |
| Boost 0.50 | 14.11 / 25.19 / 7.28 | **17.91** | **−12.87** |
| Boost 1.00 | 13.31 / — / 10.04 | **3.27** | **−10.38** |

⇒ **span does not explain it**: Cut 0.50 has a 13.3 dB span and agrees to 0.43 dB, and Boost 1.00
has the second-SMALLEST span in the table and is 10.38 dB out. ⛔ Do not build the session on it.
It is still worth carrying as a *caveat on the statistic* — s154's AR6 (*"the residual that survives
shape-matching changes sign across the stimulus ladder; no single (gain, Q) entry can be right at
all three rungs"*) and s153's AQ2b (*"the pedal's Q spans 1.29×–2.93× at fixed (GRUNT, DRIVE)"*)
both say a mean over sweeps is a lossy target — but it is not the carrier.

---

## 4. ⭐⭐ THE ONE TEST THAT DECIDES IT, pre-registered

**Compare AP3's solved POINT column against a FRESH `od_tone_restore_fit` fit on the current
build.** Both answer *"what cut does the model need now?"*, by completely different routes — AP3 by
an analytic per-cell solve on the rendered curve, the fit tool by its own converged optimisation.

- **If they AGREE** ⇒ the solve is sound and AP3a is correctly reporting a stale table. The repair
  is to **re-scope AP3a's premise** — it must reproduce a CURRENTLY-fitted table, not the shipped
  one — and the residual becomes item 10's input rather than a gate defect. ⛔ Do NOT loosen AP3a's
  bar to make it green; that is the concession `measurement-discipline.md` §3 warns about, and it
  would delete the staleness signal the check is now producing.
- **If they DISAGREE** ⇒ the solve is wrong, and Boost is where it shows. Then look at the solve
  itself (`solve_gain`, its bracket, and the `NONMONO` sign-change flag).

⚠ **Run it on BOTH memberships** (`--rows bleedfree` and `--rows mixed`) — s191's whole point was
that a bleed-free-only reading is one setting, and the user's standing steer is that `ref-od` (the
Cut × DRIVE 0.5 cell of the mixed set) is the baseline that matters. The mixed arm already reads
**3.19 dB** rms against bleed-free's 6.62.

**Cheap checks worth doing first, in this order:**

1. **`NONMONO` is a root-finder property or a curve property?** Print `err(gain)` on the flagged
   cell and look for whether it genuinely crosses zero three times or whether the crossings are
   sub-0.1 dB wobble. One plot's worth of numbers; it decides whether there is a second defect.
2. **Does Boost's disagreement track a SHIPPED change?** s187's GRUNT-keyed LF fix is **Cut-only**,
   and Cut is the row that now agrees — worth checking whether that is causal or a coincidence, by
   rendering Boost with `--fit clipC15Cut=...`-style overrides that cannot reach it. ⚠ This is the
   kind of "an implausible coincidence is a bug report" lead that is cheap to kill and expensive to
   leave hanging.
3. **Is `kNotchMixK`'s Boost row an EXTRAPOLATION at the corner?** s156 defined K from a
   `cleanFrac = 0` endpoint that s181 removed, and s185 re-anchored **only `kMixCf[0]`**, noting
   explicitly: *"Do NOT 'finish the job' by re-mapping the other seven nodes — that is a RE-FIT
   wearing a re-anchor's name."* Boost's K is the only POSITIVE row, so it is the row where the
   extrapolation direction differs from the other two. **Measure, do not assume.**

---

## 5. Context you need that is NOT in this file's subject

- ⛔⛔ **No AP3/AP5 number is quotable right now**, on either membership — including anything
  attributed to `analysis/reports/s152_null_depth_censor.json`. ⚠ That artefact is **not even on
  disk** (`analysis/reports/*.json` is gitignored), so the s152 figures survive only as prose in
  `CLAUDE.md` and `docs/session-log.md`. Treat them as an epoch record, not as data.
- ⭐⭐ **GATE AP's PREMISE is bleed-free-only** — s191's other finding, and it changes what a fixed
  AP3 would even be for. The area estimator's censoring robustness is **4.1× at the corner and 1.0×
  at all 12 mixed cells**, so at a played setting the point-vs-area choice does not exist. ⇒ if you
  fix AP3, be clear about what question it then answers: *"how far is the shipped table from what
  the model now needs"*, **not** *"does the censoring move the table"*, which is a corner-only
  question. See its CLOSED/REFUTED row.
- ⚠ **`--rows` is an AXIS now, and `ROWS` itself must NOT be re-pointed.** `notch_shape_gate` (AQ),
  `notch_residual_gate` (AR) and `notch_shoulder_gate` (AX) all do `ROWS = AP.ROWS` at import, so
  swapping the default silently moves five gates' stored numbers.
- ⚠ **GATE AP has no mutation runner.** It is one of the few gates without one, and it is about to
  be edited. Writing `analysis/_mutate_gate_ap.py` is probably the right first act of the session —
  s191 wrote one for GATE BR and it found three defects in its own arms plus a missing guard in the
  gate, and s182's `_mutate_gate_k.py` found two defects inside the very fix it was testing.
- ⚠ The mixed arm's DRIVE ladders are **asymmetric and it is a capture fact**: Cut [0, .25, .5, .75,
  1.0], Flat [0, .25, .5], Boost [0, .25, .5, 1.0] — `drive-1430_grunt-*` and `drive-1700_grunt-flat`
  are not on disk, and **capture access is ending** (`reference-sources.md` §0), so this is a
  permanent bound. Match on DRIVE before any across-row comparison.

---

## 6. Exact starting commands

```bash
/opt/homebrew/bin/python3.11 analysis/null_depth_censor_gate.py                 # bleed-free, RED at AP3a
/opt/homebrew/bin/python3.11 analysis/null_depth_censor_gate.py --rows mixed    # mixed twin, RED at AP1b + AP3a
```

Key source: `analysis/null_depth_censor_gate.py` — `ROW_SETS`, `solve_gain`, `ap3`, `ap3a`,
`NONMONO`; `analysis/od_tone_restore_fit.py` — `cut_db`, `current_response`, `mix_shape`,
`shipped_tables`, `SETS` / `SET_META`.

⛔ **Nothing in this session should need a rebuild or a matrix re-render.** If it appears to, stop
and re-read — GATE AP works on capture WAVs and cached renders, and `CLAUDE.md`'s cache note says a
full matrix render is ~50 min and that any relink invalidates it.
