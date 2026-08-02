# Obsidian-B7000 — Project Memory  (from the pedal-plugin template)

> Obsidian-B7000 is a circuit-level emulation of the **Darkglass B7K Ultra** bass overdrive/DI preamp,
> built as an AU/VST3 plugin using JUCE 8+ and chowdsp_wdf. The schematic we have ("Black Mirror VII"
> by PCB Guitar Mania, rev 1.1v) is the ORIGINAL B7K clone; the Ultra-only features (Master volume,
> 3-way Attack, switchable mid frequencies) are **engineered on top of it** — see circuit.md [ENG] tags.
> Author/Company: Leigh Pierce

This project was scaffolded from a reusable template. The generic, hard-won engineering lives in
the rules + docs below — read them before writing DSP or UI. Replace every `<...>` placeholder.

## Quick reference

```
Build:  cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
AU:     cmake --build build --target <Pedal>_AU     (auto-installs; bump VERSION to force Logic rescan)
Format: clang-format -i src/**/*.{cpp,h}
```

## Schematics

Put the schematic images in `schematics/` and load them whenever verifying a circuit detail.
`.claude/rules/circuit.md` is the source of truth for values/topology — fill it in first.

**Use the `schematic-checker` agent any time a circuit value or topology is in doubt; use
`dsp-validator` after any DSP stage change.** Both read `.claude/rules/circuit.md`/`dsp.md` —
keep those current and the agents stay useful with no extra setup.

> ⚠⚠ **BEFORE READING ANY CAPTURE-DERIVED NUMBER IN THIS FILE OR ANY DOC: `analysis/captures/` is a
> recording of the NEURAL DSP Darkglass plugin, NOT of a hardware B7K Ultra** (confirmed 2026-07-29).
> Every "the pedal" / "the real pedal" / "the captured unit" below and in `docs/phase9-validation.md`,
> `docs/phase7-calibration-handover.md`, `circuit.md` and the memory files means **the ND emulation**.
> ND is very close on the linear path (≤1.4 dB) and **~27 dB low on even-order harmonics**.
> **`.claude/rules/reference-sources.md` is the authority rule — read it before treating a capture as
> ground truth, and before calling a move away from the captures a regression.**

@.claude/rules/reference-sources.md
@.claude/rules/measurement-discipline.md
@.claude/rules/circuit.md
@.claude/rules/dsp.md
@.claude/rules/architecture.md
@.claude/rules/ui.md
@.claude/rules/build.md

## Delegation & model tiering

Plan with a high-end model, delegate execution down to cheaper ones — reserve the expensive
reasoning for the step that's actually hard to get right. As of July 2026 that means:

- **Planning** (build-sequence ordering, schematic-topology judgement calls, deciding what a
  session should tackle next) — a top-tier model at high effort (e.g. **Fable 5**, high effort).
- **Important thinking work** (circuit/DSP correctness: the `schematic-checker` and
  `dsp-validator` agents, anything cross-checking values/topology/taper against `circuit.md` or
  `dsp.md`) — a strong reasoning model at high effort (e.g. **Opus 4.8**, high effort). Both
  agents' frontmatter (`.claude/agents/schematic-checker.md`, `.claude/agents/dsp-validator.md`)
  are pinned to this tier — don't downgrade them to save cost, they're exactly the "important"
  category this policy protects.
- **Routine work** (mechanical edits, boilerplate scaffolding, formatting, running builds/tests)
  — a fast mid-tier model at medium effort (e.g. **Sonnet 5**, medium effort).

Re-evaluate the concrete model names as new ones ship; the tiering principle (plan high, validate
high, execute routine work cheap) is what should persist.

## Essential reading (template learnings — do not skip)

- **`docs/nonlinear-component-modeling.md`** — the ONLY two non-WDF-native parts are the **CD4049UBE
  clipper** and the **J201 JFET stage**; this doc has the datasheets/papers/SPICE + recommended
  modeling approach + the pre-DSP capture list for both (source PDFs in `docs/refs/`). Read before
  the nonlinear-stage build steps.

- **`docs/calibration-and-gain-staging.md`** — input-load (`kInputRef`) calibration, output-makeup
  calibration (level-match to captures — NOT a ~0.9 headroom pad; see §2), the DRIVE taper-floor
  bug, output-load (negligible), internal-vs-output clipping, op-amp rails, VU idle gate. This is
  where the non-obvious time-sinks are documented.
- **`docs/validation-and-capture.md`** — how to measure how close the plugin is to the real pedal
  (1/3-oct FR, continuous Farina swept-THD, sub-sample null, knob-tracking pass/fail) and how to
  CAPTURE the pedal so the measurement is trustworthy (bypass anchor, one-knob-at-a-time, sweep
  Volume, no truncation). The capture MATRIX, not the signal, is the usual limitation.
- **`analysis/`** — the reusable harness: `gen_test_signal.py` (comprehensive A/B signal) +
  `analyze.py` (load/align, FR, THD, Farina swept-THD, sub-sample null, filename parser).
- **`docs/ui-peripheral-spec.md`** — full visual spec for the reusable UI elements.
- **`src/ui/`** — drop-in `PedalLookAndFeel`, `VUMeter`, `ThreePositionSwitch`, `LEDIndicator`.
- **`src/utils/TaperUtils.h`** — taper helpers (note `audioTaperR0` for large gain pots).

## Build sequence (validate each step before the next — do not skip ahead)

1. **Schematic analysis** → fill `circuit.md`. Heed the schematic-reading gotchas there. Use the
   `schematic-checker` agent to cross-check any value/topology question against what's already
   captured, rather than re-reading the schematic image from scratch each time.
2. **CMake scaffold** — APVTS + AU/VST3 targets loading in a DAW.
3. **chowdsp_wdf smoke test** — trivial RC lowpass, confirm −3 dB point within 1% (offline/unit
   test, not a visual guess).
4. **Stage-by-stage DSP**, validated at each step:
   - Linear stages: frequency response vs expected transfer function.
   - Nonlinear stage: sine-clipping behaviour; confirm output polarity with a DC-step test.
   - Run the `dsp-validator` agent against each stage before moving to the next — it cross-checks
     component values, taper curves, and WDF topology against `circuit.md`/`dsp.md` for you.
5. **Switch topologies** — verify each position independently (precomputed scattering matrices).
   `dsp-validator` covers this too (topology + `setSMatrixData()` usage).
6. **Oversampling + ADAA** on the nonlinear stage — verify aliasing reduction. Use AccurateOmega
   (not chowdsp's default omega4). Add a separate render-time OS factor.
7. **Full-chain integration + level calibration** — anchor `kInputRef` from a real measurement;
   **calibrate output makeup to the reference captures** (may exceed 1.0; don't pad for headroom —
   calibration doc §2). Build an `OfflineRender` console exe mirroring `processBlock` for A/B.
8. **UI** — reuse the peripheral elements; design the centre pedal face per this pedal.
9. **Reference validation** — generate the comprehensive signal (`analysis/gen_test_signal.py`),
   capture the pedal per `docs/validation-and-capture.md`, and A/B with the harness: FR (1/3-oct),
   continuous swept-THD, null depth, knob-tracking pass/fail. Decompose any level deficit (§4)
   before changing constants.
10. **Final sweep** — all controls full range: no instability, clicks, or NaN/Inf. (Output > 0 dBFS
    at extreme drive+volume is faithful, not a fault — the output trim manages it.)

## Current step

> **RESET at session 89 (2026-07-31), at the user's request.** The previous version of this section
> was 6,914 lines of stacked per-session handovers; it is archived verbatim in
> **`docs/session-log.md`** and nothing was deleted. Keep this block SHORT — if it grows past ~120
> lines again, archive it and rewrite the summary.
>
> **Read order for a fresh session:** this block → `.claude/rules/reference-sources.md` (what the
> captures actually are) → `.claude/rules/measurement-discipline.md` (the hard-won traps) →
> `docs/phase9-validation.md` §0 (backlog). Per-session detail: `docs/session-log.md` and
> `docs/phase9-gap-log.md`.
>
> ⛔⛔ **CAPTURE ACCESS IS ENDING (session 111, 2026-08-02) — READ `reference-sources.md` §0's
> re-instated row AND "Project-specific carry-forwards" → "Capture access status" BEFORE assuming
> any capture not already on disk is obtainable.** If this session needs one, ask the user
> immediately, not "when convenient".

### Where we are

**Phases 1–8 are COMPLETE.** The plugin builds, loads in a DAW, is fully playable, and the UI is
done. **Phase 9 (reference validation) is the only phase in progress**, and Phase 10 (perf pass +
release) has not started. ctest **16/17** — the single failure is the pre-existing session-44
`OSValidationTest`, and ⭐⭐ **SESSION 92 SETTLED WHAT IT MEASURES: IT IS GENUINE ALIASING, THE
INSTRUMENT IS REBUILT, AND `jfetSatNeg = 1.9` DOES CARRY A REAL COST.** See item 6 below — the
answer is not the one the "instrument defect" hypothesis expected, the failing row is a real defect
owned by Phase 10 B, and the pre-session-92 numbers in this file are **not comparable** to the
current ones because two of the three things the old metric reported were artefacts of the metric.
Repaired figures at `amp 0.35` (bin-exact f0, 4 s settle): `2x −28.6 / 4x −30.8 / 8x −17.1`.

⭐⭐⭐ **SESSION 100 SHIPPED THE s99 ATTACK/TREBLE-LADDER CANDIDATE — 17 FITTED CONSTANTS, ON THE
USER'S EXPLICIT RE-AUTHORISATION TO BREAK FROM THE SCHEMATIC ("we're now breaking from the schematic
where we need to to get everything together. that guidance holds moving forward").** This is the
largest single departure-from-the-drawn-network in the project — five schematic-verified, BOM-
reconciled ladder values at once (C6 by 16×) plus the tap, the C5 trims, the three damping resistors
and C8 → 0. It was session 99's open DECISION, not a new fit; the fit was already converged, gated
and matrix-accepted, and what was missing was a judgement call.

| | s91 shipped | **s100 shipped** | |
|---|---|---|---|
| OD band-RMS ex gain-n12 | 2.664 | **2.409** | ⭐ |
| THD (OD) level term | 4.279 | **3.663** | ⭐ |
| OD 25–100 Hz median / p90 | 1.024 / 6.065 | **0.860 / 4.971** | ⭐ |
| OD 100 Hz–8 kHz median / p90 | 0.742 / 5.089 | **0.568 / 4.458** | ⭐ |
| OD 8–16.3 kHz median / p90 | 0.662 / 8.076 | **0.566 / 8.058** | ⭐ |
| OD p99 | 14.408 | 14.661 | ⚠ the ONLY gated statistic worse |
| CLEAN band-RMS | 0.453 | **0.453** | bit-identical |
| rows better >0.5 dB / worse | — | **111 / 36** | |

⛔⛔ **READ WHAT IT FIXED BEFORE BOOKING IT AGAINST GAP #2 — IT IS NOT THE NOTCH.** The 320 Hz band,
GAP #2's own headline, barely moves (mean |Δ| 9.54 → 9.21 dB over the same 320 OD rows) and the notch
requirement it was built for is **still UNMET** (width 1.28/1.46/1.38×, depth +4 dB). What it actually
repairs is that the prior default sat **9–12 dB light at every sub-band on the ATTACK BOOST throw**
(cut was already right and stays so; flat improves). **It is an OD-path ABSOLUTE-LEVEL fix that
happens to live in the ATTACK ladder.** Full provenance: `FitParams.h`'s session-100 block, which is
the fullest record.

⭐ **ACCEPTANCE CHECK RUN AND PASSED**: the shipped defaults render **bit-identically** to the
explicit 17-flag `--fit` list at **all three ATTACK throws**, with a mutation control
(`attackDampCut ×2`) proving the check is not vacuous — so `s99_attack_cand.json`'s matrix numbers
carry to the shipped build with **no re-render**. ⚠ The one-throw version of that check would have
left `attackC5TrimCut` and `attackDampCut` unexercised; per-throw constants need a per-throw check.

⚠ **ctest is 16/17 — the same single pre-existing `OSValidationTest` failure, no new ones.** But its
numbers MOVED, which is a cost living entirely outside the matrix: at `amp 0.35`, **8× −17.1 → −23.1
(better by 6 dB), 4× −30.8 → −28.6 (worse)**. The test still fails for the session-92 reason (genuine
fold-down from the un-ADAA'd CD4049 VTC, owned by Phase 10 B) — not for a new one.

⚠ **`docs/session-log.md` §"Session 100" holds the per-value table.** Every "the drawn X" comment in
`FitParams.h`'s treble/ATTACK region now describes the PRIOR default, not what ships — the
session-100 block says so at the top, and one stale claim ("Defaults are the drawn values…") was
corrected in place rather than left to mislead.

⭐⭐⭐ **SESSION 102 LOCALISED WHAT IS LEFT OF THE OD ERROR, AND THE ANSWER RE-ORDERS THE BACKLOG:
IT IS NOT A3, IT IS NOT THE ATTACK LADDER, AND IT IS NOT BROADBAND-UNIFORM — IT IS *LEVEL* AND
*GRUNT*, AND BOTH SURVIVE A CROSS-TAB.** `analysis/od_residual_localise.py` (**GATE J**, 6 computed
sub-gates, exits non-zero, **no render** — a re-read of `s99_attack_cand.json`, the shipped grade).
Session 101 established the HF region is ND's artefact and that the remainder is "genuinely
broadband"; it did not say *where*. This does.

⛔ **First, the thing that makes every previous marginal in this project suspect: `blend` dominates
everything, and nothing had been conditioned on it.** Raw over the 320 OD rows, band-RMS ex HF:

| blend | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---|---|---|---|---|---|
| band-RMS | 0.200 | 0.280 | 0.598 | 1.438 | **3.120** |

⇒ a **15.6× monotone span**, so any axis whose rows carry more blend-max looks bad for that reason
alone. **Conditioned on bleed-free (`blend = 1.0`, n = 172) the picture changes:**

| axis | spread, marginal | spread, **conditioned** | verdict |
|---|---|---|---|
| `attackIdx` | 1.60× | **1.23×** | ⭐ mostly the mix — **the ATTACK ladder is no longer a lever** (s100 worked) |
| `drive` | 2.09× | 2.08×, non-monotone | weak |
| **`level`** | 5.78× | **2.08×** (2.343 → 4.873) | ⭐⭐ **REAL** |
| **`gruntIdx`** | 2.32× | **1.85× / 1.68×** off-flat | ⭐⭐ **REAL** |

⭐⭐ **AND THE CROSS-TAB SEPARATES THEM — both hold WITHIN every cell of the other, so they are two
main effects, not one seen twice.** Grunt composition of the two level buckets is proportionally
identical (20/65/15 % vs 20/60/20 %), which is what kills the obvious confound:

| bleed-free, band-RMS ex HF | grunt 0 | grunt 1 (flat) | grunt 2 |
|---|---|---|---|
| **LEVEL 0.5** | 3.207 [16] | **1.937** [52] | 2.949 [12] |
| **LEVEL 1.0** | 6.649 [12] | **4.056** [36] | 5.546 [12] |
| *level ratio* | 2.07× | 2.09× | 1.88× |

⛔⛔ **THE BLOCK IMMEDIATELY BELOW IS SUPERSEDED — ITS PREMISE IS REFUTED BY SESSION 103 (GATE K2).
`blend = 1.0` IS NOT BLEED-FREE EXCEPT AT LEVEL MAX, SO LEVEL IS NOT A PLAIN POST-OD ATTENUATOR AND
THE "STRUCTURAL IMPOSSIBILITY" DOES NOT EXIST.** The BLEND pot's body bridges the LEVEL wiper to the
clean source at every BLEND position; bleed vanishes only where the wiper's source impedance is zero.
At LEVEL noon / BLEND max the clean coefficient sits **2.05 dB below** the OD coefficient, and at
LEVEL 0.125 it is **−0.08 dB** — half the output. ⇒ LEVEL and bleed exposure are **collinear
(r = −0.961)** inside the set GATE J called bleed-free, so J10/J11 measure LEVEL *and* dilution
together. **Kept below verbatim as the superseded record — do not quote its conclusion.** Session
103's replacement finding is larger and better founded; see the SESSION 103 block.

⭐⭐⭐ **THE LEVEL RESULT IS THE ONE TO ACT ON, BECAUSE IT IS STRUCTURALLY IMPOSSIBLE AS DRAWN.**
At `blend = 1.0` the clean tap is fully out of circuit, so **LEVEL is a plain post-OD attenuator**,
and `comprehensive_report` gain-matches every row before differencing — **a pure gain is invisible
to this statistic by construction, so band-RMS must not depend on LEVEL at all.** It doubles.
Split into a level term and a shape term (rows re-anchored on their own non-HF mean):

| cell | band-RMS | shape | level |
|---|---|---|---|
| LEVEL 0.5, grunt flat | 1.937 | 1.855 | **0.382** |
| LEVEL 1.0, grunt flat | 4.056 | 3.164 | **2.304** |

⇒ **both halves grow, and the absolute-level term grows 6×.** Signed, at LEVEL max the model is
**−2.30 dB** across the non-HF band (worst −4.2…−5.0 dB over 254 Hz–1 kHz, and −7.6 dB at 25 Hz)
and **−10.13 dB** at HF, against **−0.16 dB** non-HF at LEVEL noon — i.e. **at LEVEL noon the model
sits essentially ON the pedal and at LEVEL max it is uniformly too quiet.**
⚠ **The level term is an UPPER BOUND, not a clean reading**: `gain_db_applied` is a broadband
*time-domain* null gain (`analyze.null_depth` over the whole sweep), so it is dragged by the HF
artefact region GATE I identified. Part of the 2.304 is that drag. **Re-anchor before fitting
anything to it.**
⚠ **And do NOT read J10 as a rail/nonlinearity signature** — the LEVEL-max penalty *ratio* rises
1.49 → 1.66 → 2.65 → 3.26 with stimulus level, but the LEVEL-max column is **flat at 4.5–5.5 dB**
and the growth is entirely the LEVEL-noon column improving 3.03 → 1.51. The defect is
stimulus-INDEPENDENT, which points at a linear/level-scaling error, not at the TL07x rails.

⭐⭐ **AND THE s91 CONTROL SAYS THE LEVEL EFFECT PREDATES SESSION 100 — BUT THAT SESSION 100 WIDENED
IT, WHICH THE MATRIX HEADLINE COULD NOT SHOW.** Same tool, same cells, on `s91_shipped.json`
(grunt flat, bleed-free):

| | s91 shipped | **s100 shipped (s99 cand)** | |
|---|---|---|---|
| LEVEL 0.5 band-RMS | 2.443 | **1.937** | ⭐ better |
| LEVEL 1.0 band-RMS | 3.825 | **4.056** | ⚠ **worse** |
| level ratio | 1.57× | **2.09×** | ⚠ |
| level term at LEVEL 1.0 | 1.521 | **2.304** | ⚠ |

⇒ session 100's 17 constants — explicitly an **OD-path absolute-level fix** — bought their headline
at LEVEL noon and **paid a little at LEVEL max**, and the absolute-level term there grew 1.5×. That
is coherent with what it was: a level correction helps where the path was light and can overshoot
where it was not. ⭐ It also means the LEVEL defect is **not** something s100 introduced (it is
1.57× at s91), so this is a pre-existing lever that s100 has just leaned on — which is exactly why
it should be the next target rather than another pass at the same ladder.

⭐ **Supporting decomposition (J4/J5).** HF (≥8 kHz, 4 bands) carries **48.1 % of the pooled mean
square** — but only 0.403 dB of the 2.409 headline, because the gated headline is a mean of
per-row RMS and does *not* decompose into shares. Both are printed, labelled, and J1/J2 check the
decomposition recombines with a dropped-band mutation control. ⭐⭐ **J5 independently reproduces
GATE I's G4 through a different code path** — median 0.625 → 0.636 (WORSE), p90 4.805 → 4.552,
p99 14.661 → 10.281, band-RMS 2.409 → 2.005 — so session 101's exclusion arithmetic is now
corroborated, not single-sourced.

▶ **NEXT — SUPERSEDED BY SESSION 103, see that block for the current order.** *(The session-102
list read: (1) the LEVEL-max deficit, on the structural-impossibility argument now refuted; (2)
GRUNT off-flat; (3) A3 demoted. Item (2) survives; (1) is replaced by the LEVEL **law**, which is a
different and larger finding; (3) is **reversed** — A3 is re-promoted by GATE K7.)* ⛔ Do not
re-open the ATTACK ladder on OD-residual grounds: conditioned, it is a 1.23× effect.

---

⭐⭐⭐ **SESSION 103 — THE LEVEL CONTROL *LAW* IS WRONG BY UP TO 9.3 dB, IT IS STRUCTURALLY INVISIBLE
TO EVERY STATISTIC THE PROJECT GRADES ON, AND FIXING THE TAPER CANNOT CLOSE IT — THE LEVER IS A3.**
`analysis/level_law_gate.py` (**GATE K**, 7 computed sub-gates, exits non-zero, **no render** — a
re-read of `s99_attack_cand.json`, the shipped grade, plus a closed-form evaluation of the shipped
`LevelBlend` stage).

⛔ **First, the correction that had to come before anything else could be read: session 102's
"structural impossibility" does not exist.** GATE K2 evaluates the shipped stage instead of quoting
its header, and derives the coefficients **twice by different algebra** (the C++ closed form, and an
independent 2×2 nodal solve from the explicit 100k resistances) — agreeing to **5.6e−17**. At
BLEND max:

| LEVEL | 0.125 | 0.25 | 0.375 | **0.5** | 0.625 | 0.75 | 0.875 | 1.0 |
|---|---|---|---|---|---|---|---|---|
| clean re OD, dB | **−0.08** | −0.39 | −1.01 | **−2.05** | −3.71 | −6.44 | −11.72 | **−inf** |

⇒ **`blend = 1.0` is bleed-free ONLY at LEVEL max**, because the BLEND pot's body bridges the LEVEL
wiper to the clean source at every BLEND position and the bleed vanishes only where the wiper's
source impedance is zero (LEVEL max on the op-amp output, LEVEL min on ground). Pearson
**r(LEVEL, clean fraction) = −0.961** over the 49 blend-max OD captures (**K6**) ⇒ inside that set
LEVEL and dilution are collinear **by construction**, and no cross-tab restricted to it can separate
them. **J10's ratio and J11's LEVEL×GRUNT cells must be re-scoped.** ⛔ K6 does **not** claim the
whole J10 effect is dilution — separating them needs rows with equal bleed and different LEVEL, and
the matrix has none, so the gate reports the confound and **refuses a verdict on the size**.

⭐⭐ **Second, the data that had been sitting unread: the matrix holds a NINE-POINT LEVEL LADDER**
(`level-0700 … level-1700`, one capture per detent, blend max) **plus 14 further groups differing in
ONLY the LEVEL setting.** J9/J10/J11 bucket LEVEL into {0.5, 1.0} and the seven intermediate detents
fall out. (`check-for-unread-data-first`, **seventh occurrence**.)

⭐⭐⭐ **Read as a matched pair with NO gain match on either side** — `plugin_db − gain_db_applied`
against raw `pedal_db`, so the HF drag that makes J11's level term an upper bound cannot enter and
there is no anchor to choose. dB **relative to noon**, non-HF band mean:

| LEVEL | PEDAL (clean/−18/−12/−6) | MODEL | **MODEL − PEDAL** |
|---|---|---|---|
| 0.000 | −25.9 / −23.9 / −22.4 / −18.8 | **−inf (mutes)** | — |
| **0.125** | −16.5 / −14.8 / −14.3 / −13.7 | −24.7 / −24.2 / −24.1 / −24.0 | **−8.2 / −9.3 / −9.7 / −10.2** |
| 0.250 | −8.7 / −8.1 / −7.9 / −7.7 | −11.6 / −11.2 / −11.1 / −11.0 | −2.9 / −3.1 / −3.2 / −3.3 |
| 0.375 | −3.0 / −2.7 / −2.6 / −2.5 | −4.5 / −4.2 / −4.2 / −4.1 | −1.5 / −1.5 / −1.5 / −1.6 |
| 0.750 | +5.4 / +4.8 / +4.1 / +3.7 | +5.0 / +4.2 / +3.5 / +3.2 | −0.4 / −0.7 / −0.6 / −0.5 |
| **1.000** | +10.1 / +9.3 / +7.2 / +4.5 | +8.5 / +6.8 / +4.2 / **+0.1** | **−1.6 / −2.5 / −3.0 / −4.5** |

⭐ **K4 corroborates it out of sample**: the 14 other matched groups (different drive / grunt /
attack) reproduce the ladder's 0.5→1.0 step to **0.56 dB** at the worst stimulus level, so this is a
property of the LEVEL control, not of one capture pair. Two >5 dB outlier cells are **printed and
kept**, both drive-max/grunt-boost; they cannot move a median.
⭐ **K5**: at the worst detent the error is **−9.34 dB of OFFSET against 2.22 dB rms of SHAPE (24 %)**
— this is a level error, not a frequency-response error.
⚠ **K3's known answers are what make it readable**: the PEDAL's law is monotone at every stimulus
level and BOTH laws are monotone at/below noon — checks that break on a mis-mapped detent. Below noon
the defect spans **1.5–10.2 dB at every stimulus level and varies by only 2.06 dB**, i.e. by less than
its own size ⇒ **not a rail and not a compressor; a linear level-scaling error.**

⚠⚠ **AND IT IS INVISIBLE BY CONSTRUCTION, WHICH IS WHY 102 SESSIONS DID NOT SEE IT.**
`comprehensive_report` fits a per-row broadband null gain: at LEVEL 0.125 that gain is **+9.03 dB**,
i.e. it removes the 9.3 dB defect exactly. **A per-row gain match cannot see a pot-law error.** Every
graded statistic in the project — band-RMS, the region medians/p90s, the THD terms — is downstream of
that match.

⭐⭐ **A SECOND, SEPARATE DEFECT falls out of the same table: at LEVEL = 0 the model MUTES and the
reference does not** (it floors 19–26 dB below noon). Both LEVEL-min captures sit under
`release_gate`'s `SILENT_DB`, so **the matrix has never graded them.** And **above** noon at hot
stimulus the model's H1 transfer *falls* with rising LEVEL (−2.20 dB at `drv_-6`) where the pedal's
does not — read as H1, not loudness: a stage downstream of LEVEL saturates harder in the model. That
one is stimulus-DEPENDENT and distinct from the taper error.

⛔⛔ **THE TAPER CANNOT FIX IT, AND THAT IS THE LOAD-BEARING RESULT.** The stage's closed form
predicts its own rendered law to **0.002 dB rms below noon** (so the taper is fittable with no
render, and re-fitting the model's own law recovers **p = 2.240** against the shipped 2.25 — the
known answer). But with the clean/OD ratio held at the model's own value, the best exponent reaches
only **rms 1.85 dB** and lands **3.8 dB short at LEVEL max**. The law's *shape* is set by the bleed
ratio, because bleed varies with LEVEL through the loading network.

⭐⭐⭐ **SO THE LEVER IS THE OD-vs-CLEAN BALANCE — AND GATE K7 MEASURES IT DIRECTLY, WHICH MAKES THIS
A THIRD INDEPENDENT INSTRUMENT ON A3.** At BLEND 0 the output is the clean tap with coefficient 1; at
BLEND 1 + LEVEL 1 it is the OD path with coefficient 1 (K2's two exact zeros). Both traverse the same
downstream chain, so the difference of the two absolute readings **IS** the mixed ratio — no fit, no
gain match:

| stimulus | clean | −18 | −12 | −6 |
|---|---|---|---|---|
| r MODEL, dB | +6.86 | +10.94 | +14.03 | +17.77 |
| r PEDAL, dB | +3.71 | +6.82 | +9.43 | +12.92 |
| **MODEL − PEDAL** | **+3.15** | **+4.12** | **+4.60** | **+4.85** |

⇒ **the model's clean bleed runs 3.1–4.9 dB hot relative to its own OD path.** Sign and size match A3
as recorded in `reference-sources.md` §1 (≈5–7 dB over 100–400 Hz; k ≈ −6.5 dB on the harmonic axis),
and this instrument **shares no machinery** with the harmonic axis (s85) or the drive axis (s86).
⚠ Broadband non-HF mean here vs a 100–400 Hz figure there — **same defect, different statistic; do
not diff the two numbers.** K7's known answer: both sides' ratio must RISE with stimulus level (the
OD path contains the clipper and must compress, the clean tap does not) — it does, monotonically.
⚠ **A first pass fitted the ratio from the 8-point law and got 0.14 where the direct measurement says
1.53** — a two-parameter fit to one curve does not identify it, and the coherent-sum assumption is
wrong besides. **Quote K7's direct number, never the fitted one.**

⭐⭐ **AND THE s91 CONTROL SAYS SESSION 100 MADE THE LEVEL LAW WORSE — ON AN INSTRUMENT WITH NO GAIN
MATCH, WHICH IS WHY IT IS WORTH HAVING.** Same tool on `s91_shipped.json`:

| | s91 shipped | **s100 shipped** | |
|---|---|---|---|
| ladder step at LEVEL max (clean/−18/−12/−6) | −1.27 / −1.85 / −2.32 / −3.57 | −1.58 / −2.50 / −3.01 / **−4.47** | ⚠ worse at all four |
| clean/OD excess, dB | +4.09 / +4.09 / +4.31 / +4.17 | **+3.15** / +4.12 / +4.60 / **+4.85** | ⭐ better at clean, ⚠ worse driven |

⇒ session 100's 17 constants — explicitly an **OD-path absolute-level fix** — moved the balance the
right way at the clean stimulus and the wrong way under drive, and cost 0.3–0.9 dB on the LEVEL law
at every stimulus level. This independently confirms session 102's "s100 widened it" through an
instrument that shares no anchor with the matrix.
⭐ **Free known answer**: the PEDAL column is **bit-identical** across the two reports
(+3.71 / +6.82 / +9.43 / +12.92), as it must be — same captures — so any movement is the model's.

▶ **NEXT — SUPERSEDED BY SESSION 104 (GATE L).** *(The session-103 list read: (1) A3 as the lever
for the LEVEL law; (2) GRUNT off-flat; (3) the LEVEL-min mute, "check whether the divider needs an
end resistance". Item (2) survives untouched. Item (1) is **re-scoped** — A3 itself stands, but it
is NOT the lever that closes the LEVEL law. Item (3) is **answered NO**: the required L(0) is ~1.5 %
of full, ~30 dB too large for any end resistance.)* See the SESSION 104 block below for the current
order.

---

⭐⭐⭐ **SESSION 104 — THE SHIPPED `LevelBlend` NETWORK CANNOT PRODUCE THE PEDAL'S LEVEL LAW UNDER
*ANY* TAPER AND *ANY* BLEED. THIS IS A STRUCTURAL REFUTATION, NOT A FIT SHORTFALL — AND IT RETIRES
BOTH OF SESSION 103's PROPOSED LEVERS FOR THAT LAW.** `analysis/level_taper_gate.py` (**GATE L**,
8 computed sub-gates, exits non-zero, **no render** — a re-read of `s99_attack_cand.json`, the
shipped grade, plus a closed-form evaluation of the shipped stage). It **imports** `level_law_gate`
(GATE K) rather than re-deriving anything, so the two cannot drift.

⭐ **The enabling algebra.** At BLEND = 1 the stage reduces to a single elegant form —
**`a(L) = L/(1+L−L²)`, `b(L) = a(L)·(1−L)`** — i.e. *the clean-re-OD ratio the stage mixes is
exactly `(1−L)`*. **L1** gates that against K2's own `coef_closed` to **3.33e−16** over 1001 points,
so it is a **third** independent derivation of those coefficients, not a retyping. Because
`plugin_db`/`pedal_db` are band-averaged **power**, the mixed output is *exactly*
`a²P_od[1 + t² + 2tc]` with `t = (1−L)ρ` and `c` the normalised cross-spectrum in [−1,1] — so
**s103's coherent-vs-incoherent worry is retired, not assumed away**: `c` is carried as one free
parameter per band and nothing is assumed about phase.

⭐⭐ **THE KNOWN ANSWER IS THE WHOLE REASON THIS IS QUOTABLE, AND MY FIRST VERSION OF IT WAS
WORTHLESS.** The inverse recovers a taper shared across 25 bands from 8–9 detents (200–225
equations, 34 parameters). Run on the MODEL it must return the shipped `L = x^2.25`. It did — to
±0.000000 — while being **initialised at `x^2.25`**, i.e. a **fixed point, not a test**. Re-run from
**7 starts** spanning p = 0.5…4.0 plus three random monotone vectors, it recovers to **4.3e−10 with
the starts agreeing to 3.8e−11**. ⇒ **L is globally identified**, and the pedal's recovered curve is
a measurement rather than an initialisation artefact.

⛔⛔ **AND THE PEDAL'S LADDER IS NOT REACHABLE.** Same machinery, same freedom:

| stimulus | MODEL rms | **PEDAL rms** | MODEL, ρ free | **PEDAL, ρ free** |
|---|---|---|---|---|
| clean | 0.000 | **2.120** | 0.000 | 1.568 |
| drv_−18 | 0.000 | **2.394** | 0.000 | 1.713 |
| drv_−12 | 0.000 | **2.248** | 0.000 | 1.762 |
| drv_−6 | 0.000 | **1.626** | 0.000 | 1.497 |

⭐ **L5, the control that makes this a topology result rather than a capture complaint:** freeing
|ρ| **per band** — 25 extra parameters, i.e. discarding the endpoint measurement entirely — moves
the pedal only **1.626 → 1.497 dB**. It does *not* collapse. ⚠ And the control has its own control:
freeing ρ leaves the MODEL still recovering `x^2.25` exactly, so it is not too loose to arbitrate.

⭐⭐⭐ **L6 IS THE CLEAN KILL, BECAUSE IT NEEDS NO THRESHOLD: A POT'S TAPER CANNOT DEPEND ON THE
STIMULUS.** Recovered `L(0.625)` across the four stimulus levels — **MODEL 0.00000 spread** (the
floor, at machine precision), **PEDAL 0.503 / 0.631 / 0.377 / 0.341, spread 0.290.** ⇒ the recovered
curve is absorbing something the model form omits. ⛔ **Do NOT fit a taper to any single column.**

⇒ **Neither a taper re-fit NOR the A3 balance correction can close the LEVEL law**, because the
network cannot express the pedal's ladder at all. ⚠⚠ **A3 ITSELF IS UNTOUCHED AND STILL STANDS** —
K7 measures it at the two **exact-zero endpoints**, where the coefficients are exactly 1 and 0 and
no model form is involved. What falls is only s103's *inference* that A3 is the lever **for this
law**. Two candidate causes remain, and GATE L does **not** discriminate them: (a) the pedal's mix
network differs structurally (pot values, or no bridging), (b) something downstream of LEVEL in the
pedal is level-dependent, which the form assumes away.

⭐⭐ **L8 — AND IT REFUTES A RECORDED K3 CONCLUSION, WHICH RE-UNIFIES TWO "SEPARATE" DEFECTS.** K3
flagged that the model's H1 **falls** above noon where the pedal's does not, and read it as *"a
stage downstream of LEVEL is saturating harder in the model"* — a second, distinct,
stimulus-dependent defect. It is neither. **`b(L)` peaks at exactly L = 0.5 and is exactly 0 at
LEVEL max**, so raising LEVEL past halfway *removes* the clean signal; with a clean tap hotter than
the OD path the sum genuinely falls — **in a strictly linear network with no saturating element**.
The tell was already on the bench: the linear inverse reproduces the model's law **at that same
stimulus** to ~1e−10. Measured against the purely linear prediction, at `drv_-6`, step 0.875 → 1.0:

| | measured | **LINEAR prediction** |
|---|---|---|
| MODEL | **−2.20** | **−2.74** |
| PEDAL | **+0.84** | **+0.28** |

⇒ the linear network predicts **the sign split itself** from each side's own measured clean/OD
ratio — the model falls only because its ρ is 4.85 dB hotter there. **The above-noon fall IS A3,
seen through the network's bleed turnover**, and it shrinks when A3 is corrected.

⭐ **L7 — the LEVEL-min mute, quantified, and s103's proposed next step answered NO.** The pedal
floors **19–26 dB** below noon; the shipped stage sets the wiper hard on VD (`if (L <= 0.0) vw = 0`)
so both coefficients vanish and the output is **exactly** zero. The inverse puts the pedal's
residual wiper at **L(0) = 0.0118–0.0176, i.e. ~1.5 % of full** — which is **far too large to be an
end resistance** (a 100k pot with a 50 Ω end stop reads about −66 dB, not −20). ⛔ Both LEVEL-min
captures sit under `release_gate`'s `SILENT_DB`, so the matrix has never graded this row and cannot
arbitrate any fix to it.

⚠ **Two membership defects in my own scratch work had to be fixed before any of this was believed,
and the first is a new trap.** A hand-built 4-key settings match pulled in the `gain-n12` rows (the
session-48 capture defect) **and** duplicate detents a dict silently overwrote — and **the band-MEAN
law still reproduced K3's table to the digit**, so the usual check passed. It surfaced only per band,
as a **7.5 dB** residual where correct membership gives 0.000, and was briefly mistaken for a failure
of the physics. **L2 now asserts membership** (exact endpoint counts, 12 matched settings, `gain-n12`
excluded by name). ⇒ this is the mirror of `aggregate-moved-check-membership-first`: the aggregate
did **not** move and membership was still the cause.

▶ **NEXT — SUPERSEDED BY SESSION 105 (GATE M) ON ITEM 1 ONLY.** *(The session-104 list read: (1) A3
as the head item at "3.1–4.9 dB"; (2) GRUNT off-flat; (3) the LEVEL law as a topology question.
Items (2) and (3) survive **untouched**. Item (1) survives as the head item but its SIZE and its
SCOPE both change — the number is contaminated by a known-defective capture and the "it is a level
error" reading does not survive a per-band read.)* See the SESSION 105 block below.
⚠ **Whatever moves, re-run GATE K *and* GATE L**: no gain-matched statistic can confirm or refute
any of this, so the 129-capture matrix is **not** the arbiter here and must not be quoted as one.

---

⭐⭐⭐ **SESSION 105 — A3's HEADLINE NUMBER INCLUDES A CAPTURE THE PROJECT HAS A STANDING RULE
AGAINST FITTING TO, AND ITS RECORDED SCOPE NOTE ("the defect is a LEVEL one") IS REFUTED BY A
PER-BAND READ OF K7's OWN DATA. A3 IS TWO DEFECTS, NOT ONE.** `analysis/a3_balance_gate.py`
(**GATE M**, 6 computed sub-gates, exits non-zero, **no render** — a re-read of
`s99_attack_cand.json`, the shipped grade). It **imports** `level_law_gate` (GATE K) and through it
`matrix_grade`, so the two cannot drift, and **M1 reproduces K7's shipped headline to 1.3e−15**
through its own code path before anything else is read.

⛔ **First, the contamination.** K7 pairs the mixing network's two exact-zero endpoints and pools
**5** pairs. One of them is **`level-1700_gain-n12`** — the session-48 capture defect, i.e. 20 % of
the headline. K7 filters on `blend`/`level`/`is_od` and never excludes it by name.

| | clean | drv_−18 | drv_−12 | drv_−6 |
|---|---|---|---|---|
| as K7 ships (n = 5) | 3.15 | 4.12 | 4.60 | 4.85 |
| **defect excluded (n = 4)** | **3.36** | **4.39** | **4.80** | **5.05** |

⭐ **The sign is the reassuring part: excluding it makes A3 LARGER at every stimulus level, so
session 103's promotion is not at risk** — but **quote 3.4–5.1 dB, not 3.1–4.9**.
⚠ `defective-rows-must-not-vote`, inside the one instrument the whole A3 case rests on.

⛔⛔ **Second, and the load-bearing one: K7 reports a MEAN over 25 bands, and the curve under it
spans 9–14 dB.** The scope note in item 5 — *"K7 says the defect is a level one. Do not re-run those
[frequency-shaping] searches"* — is a claim **about frequency**, inferred from a statistic that is
blind to frequency by construction. Measured, against GATE K5's own bar (shape/offset ≤ 0.25 is what
justified that phrase for the LEVEL law):

| selection | n | clean | drv_−6 | shape/offset |
|---|---|---|---|---|
| all non-HF | 25 | 3.36 | 5.05 | **0.90 / 0.66** |
| drop lowest band | 24 | 3.07 | 4.86 | 0.89 / 0.68 |
| drop lowest + >5 k | 22 | 3.47 | 5.49 | 0.71 / 0.47 |
| **100–400 Hz** (§1's band) | 6 | **5.54** | **5.14** | 0.56 / **0.18** |

⇒ **broadband it is 0.47–0.90 on EVERY selection — 2–4× over the bar. A3 is not a level error.**
⭐ The shape is **real, not a 4-row artefact**: M5's leave-one-out correlation of each pair's
de-meaned curve against the mean of the others is **+0.64 … +0.89** at both stimulus extremes.
⭐ Floor guard clears (worst absolute reading model −40.8 / pedal −32.8 dB against a −60 floor), and
the headline moves only 0.2–0.4 dB under band-edge removal.

⭐⭐⭐ **AND THE SPLIT THAT RE-SCOPES THE ITEM — M6. A3 IS A CONSTANT PLUS A MOVING TERM, AND ONLY
THE CONSTANT IS THE ONE §1 RECORDS.**

| | clean | drv_−18 | drv_−12 | drv_−6 | spread |
|---|---|---|---|---|---|
| **100–400 Hz** | 5.54 | 5.38 | 5.07 | 5.14 | **0.47 dB** |
| **508–1016 Hz** | 3.58 | 5.23 | 6.53 | **9.00** | **5.42 dB** |
| peak of the shape | 320 Hz | 320 Hz | 254 Hz | **640 Hz** | — |

⇒ **(A) a stimulus-INDEPENDENT ≈5.1–5.5 dB imbalance over 100–400 Hz** — which reproduces
`reference-sources.md` §1's recorded "≈5–7 dB over 100–400 Hz" on a **third** instrument with no
fit and no gain match, and is offset-dominated there (ratio 0.18 under drive) ⇒ §1's figure is
**right, and IS a level statement, within its own band**; and **(B) a stimulus-DEPENDENT term
centred at 508–1016 Hz that swings 5.4 dB with drive**, with the shape's peak migrating
**254 → 640 Hz**. **(B) is not in §1, is not a level error, and is not a fixed linear network.**
⇒ **K7's broadband mean rising 3.36 → 5.05 is the MIXTURE of (A) and (B), not A3 growing.** Do not
read that rise as a compression-law error in the OD path's level.

⚠⚠ **THIS DOES NOT RE-OPEN SESSIONS 50/52/53, AND MUST NOT BE QUOTED AS DOING SO.** Those ruled out
single elements and all **post-clipper LINEAR** elements of any order. A **drive-dependent**
frequency structure is outside what either search covered — so (B) is a region neither ruled out
**nor** searched, which is coherent with item 5's standing "the only region not ruled out is
inside/before the clipper". What falls is only s103's instruction not to look for frequency shaping
at all. ⭐ A third term is visible and flagged, not diagnosed: **25 Hz reads +10 dB,
stimulus-independent**, on the least trustworthy band (largest pair-to-pair spread) — M4/M6 both
exclude it from any verdict.

▶ **NEXT, in order.**
1. ⭐⭐ **A3 — still the head item, and now with a target instead of a number.** The timeboxed attempt
   (item 5) should aim at **(A)**, the stimulus-independent 100–400 Hz term: it is the one §1
   corroborates, the one that is genuinely a level error, and the one a single element can carry.
   ⛔ Do **not** aim a static gain at K7's broadband mean — 0.9 of that number is shape, and ~1.7 dB
   of its rise is term (B). ⚠ Gate any candidate on leaving 508–1016 Hz's *drive dependence* alone,
   or (A) and (B) will be traded against each other exactly as `one-knob-two-jobs-is-compensating`
   describes.
2. **GRUNT off-flat** — 1.68–1.85×, GAP #3b, already characterised. Untouched by sessions 103–105.
3. ⭐ **The LEVEL law is a TOPOLOGY question** — unchanged from s104; discriminate L4's (a) vs (b),
   the data is on disk. ⛔ Do not point an optimiser at the taper (L3/L6).
4. ⚠ **Term (B) is a new, unclaimed item.** Do not open it in the same session as (A) — it is
   drive-dependent, so it lives in or before the clipper, and it needs its own instrument.

---

⭐⭐⭐ **SESSION 106 — THE 16 `gain-n12` OD ROWS ARE HEALED. THE EXCLUSION EVERY PROJECT HEADLINE
CARRIES HAS BEEN STALE FOR 35 SESSIONS, AND RETIRING IT COSTS 0.020 dB.**
`analysis/gain_session_gate.py` (**GATE N**, 5 computed sub-gates, exits non-zero, **no render** —
a re-read of `s99_attack_cand.json`, the shipped grade).

Session 48 localised the defect: the `gain-n12` session ran with the interface **SEND** 12.071 dB
down (the pedal saw less), the harness rendered the model at full level, and every *nonlinear*
comparison on those files was invalid. Both halves of the fix have since landed and **nobody
checked**: `captures.render_args` now emits `--input-trim` whenever `gainSessionDb` is non-zero,
and the four exposed files were **re-captured 2026-07-29** (session 70 §1). Session 70's own
next-step (c) — "re-run the s48 THD-turnover test; if they pass, the 16-row group is healed" — was
queued and never run.

⭐ **The instrument is session 48's own: THD turnover, which no record or output gain can move.**
If the send really was 12.071 dB down, the pedal in an n12 file at `drv_-6` saw what its twin saw
at `drv_-18.07`, so inverting the twin's own THD-vs-level curve must return 12.071:

| pair | power | implied pad | vs harness | n | verdict |
|---|---|---|---|---|---|
| `level-0930_gain-n12` | 5.70 | **12.376** | +0.305 | 20 | HEALED |
| `level-1430_gain-n12` | 7.97 | **11.412** | −0.659 | 24 | HEALED |
| `level-1700_gain-n12` | 11.46 | **12.016** | −0.055 | 27 | HEALED |
| `ref-od_gain-n12` | 6.50 | **12.012** | −0.059 | 24 | HEALED |

⇒ **session 48's "implied pad 3–9 dB" does not reproduce. 4 of 4 discriminating pairs recover the
harness's own figure.**

⭐⭐ **The known answer is what makes it quotable, and it is a strong one.** The harness renders the
MODEL side of an n12 file with `--input-trim -12.071`, so the model is a deterministic 12.071 dB pad
of its own twin — the identical inversion on `plugin_pct` **must** return 12.071. It returns
**12.068–12.072, worst error 0.003 dB**. Plus a pedal-side ladder (twin against itself = 0 dB; its
`drv_-12` curve declared at −6 = exactly 6 dB), both recovered to **0.0000/6.0000** ⇒ the inversion
is calibrated at **0 / 6 / 12.071**, not at one value.
⭐ **N1 independently confirms the documented count**: 5 `gain-n12` OD captures, `level-0700`
excluded (the MODEL mutes at LEVEL 0 — GATE L7 — so it is below `SILENT_DB` and never graded),
leaving **4 pairs × 4 sweeps = exactly the 16 rows**.
⛔ **What GATE N cannot do: reproduce session 48's original finding.** The four defective files were
overwritten by the re-capture. This certifies the CURRENT files; it is **not** evidence that session
48 was wrong.

▶ **DECISION FOR THE USER, not taken unilaterally** (same class as the s96 CLEAN split): retiring the
exclusion moves **OD band-RMS 2.409 → 2.429 (+0.020 dB, n 320 → 336)**, against a 2.0 SHIP bar. It
changes every quoted headline by a rounding error and makes the OD matrix judgeable on the full set
for the first time since s30. ⚠ If taken, `matrix_grade`/`release_gate`'s split and
`docs/phase9-validation.md` "Known-bad rows" must be updated together, and **every pre-s106 headline
stays quoted against `ex gain-n12`** or the two are not comparable.

⚠⚠ **TWO DEFECTS IN SESSION 106's OWN GATE, BOTH FOUND ONLY BECAUSE THE OUTPUT LOOKED TOO GOOD.**
(1) `power` printed **`nan`** — the report carries 3 non-finite THD entries per record, `nan <= floor`
is False so they passed the band guard, and `nan < MIN_POWER_DB` is *also* False, which **silently
disabled the UNDERPOWERED branch entirely**. The gate was reporting a PASS on a check that could
never fire (`empty-gate-must-fail`). (2) N5's floor sweep printed **four identical columns** across
0.02–0.20 %, reading as strong robustness — but the lowest real THD here is ~0.25 %, so no band was
ever excluded and the knob was not turning (`an implausible coincidence is a bug report`, s105 M4).
Both fixed; the sweep now spans 0.05–2.0 %, prints band counts, and **asserts** the count changes
(95 → 49). ⭐ Note the direction again: **both broken versions were the flattering ones.**

⭐⭐ **AND A SEPARATE, LARGER FINDING CAME OUT OF THE A3 WORK — MEASURED, NOT YET GATED, DO NOT QUOTE
AS FACT.** GATE M's excess is `(mc − mo) − (qc − qo)`; regrouped it is `(mc − qc) − (mo − qo)`, i.e.
**the clean path's absolute error minus the OD path's**. Nobody had split it. Anchored by
`bypass.wav` at **+0.030 dB** non-HF (identical at all four stimulus levels, so the render-vs-capture
absolute scale is sound and there is no common offset to absorb anything):

| | 100–400 Hz | broadband non-HF |
|---|---|---|
| model CLEAN path | **+1.86** | +1.64 |
| model OD path | **−3.3** | −1.7 … −3.4 |

⇒ and the clean-side figure turned out to be **the MASTER pot's taper law**, not a signal-path error:

| master | 0.125 | 0.25 | 0.375 | 0.5 | 0.625 | 0.75 | 0.875 | **1.0** |
|---|---|---|---|---|---|---|---|---|
| model−pedal, dB | −6.50 | −0.83 | +0.87 | +1.65 | +1.65 | −0.65 | −2.31 | **+0.007** |

At master **0.0** the model mutes (−220 dB) and the pedal does not — GATE L7's LEVEL finding repeating
on the second `[ENG]` divider. ⭐ **`kOutputMakeup = 2.599` is CONFIRMED RIGHT and must not be
touched**: session 41 calibrated it at `master-1700`, and that point still reads **+0.007 dB**.
⭐ Every capture passes a free known answer — the clean path is linear, so its absolute error must be
stimulus-invariant, and the `base-clean` files return **exactly 0.000 dB** spread across all four
sweeps. The `gain-n12` provenance split in the ladder is covered by an internal control:
`ref-clean.wav` vs `ref-clean_gain-n12.wav` at identical settings agree to **0.107 dB**.

⛔⛔ **PRIORITY DECIDED WITH THE USER, SESSION 106: MASTER IS LAST, AND THIS IS CORRECT.** MASTER is a
post-EQ divider → IC6_B unity buffer → C37 → R47 → out, with nothing nonlinear downstream and
attenuation-only. **A MASTER law error changes no FR shape, no THD and no harmonic structure** — it
is a volume-knob calibration error. Filed to **Phase 10 C** beside the VU idle gate. ⚠ **LEVEL is NOT
in the same bucket**: it sits *before* BLEND, so its law sets the OD-vs-clean mix ratio — an error
there is a tone error. Same class of defect, opposite consequence; do not merge the two items.

⭐⭐ **WHAT THE MASTER WORK ACTUALLY BOUGHT — and it is an A3 result, not a volume one.** MASTER is
matched within every A3 pair, so it is common-mode and cancels in the excess: **A3's size is
unchanged at 5.1–5.5 dB.** But subtracting it resolves the split — clean branch ≈ 0 (the clean tap is
IC1_A's unity buffer straight to BLEND pin 1, no gain element by topology, and the mix coefficient is
exactly 1 there by K2), so **the OD path is ~5.1 dB quiet over 100–400 Hz, absolutely.**
⇒ A3 stops being *"a balance error between two paths, either could be at fault"* and becomes *"the OD
path is 5.1 dB quiet; the clean side is exonerated to 0.007 dB."* ⚠ That exoneration is **new
information the matrix could never supply** — CLEAN band-RMS 0.453 is downstream of the per-row gain
match and structurally cannot certify an absolute level.

▶ **NEXT — item 2 is DONE (session 107, GATE O) and item 1's premise SURVIVES; see the SESSION 107
block below for the current order.** *(The session-106 list read: (1) A3 term (A) at "≈5.1 dB",
(2) gate the decomposition, (3) GRUNT, (4) LEVEL topology, (5) term (B), (6) MASTER → Phase 10 C.
Items (3)–(6) survive **untouched**. Item (2) is executed. Item (1) survives with its target
**unchanged in size** but its exoneration **re-quoted**: 0.007 → 0.41 dB.)*

⚠ **Loose end, one line, unexplained:** at master 0.5 the two routes to pure clean disagree by
**0.28 dB** — `ref-clean.wav` (DIST off) reads +1.92, `blend-0700_base-od.wav` (BLEND 0) reads +1.65.
Both should be the same signal. ✅ **RESOLVED SESSION 107 (GATE O7) — it is entirely the
REFERENCE's, and our model is exactly right.** See below.

---

⭐⭐⭐ **SESSION 107 — THE A3 DECOMPOSITION IS GATED AND IT HOLDS: A3 IS *NOT* A TWO-SIDED BALANCE.
THE OD PATH IS QUIET, ABSOLUTELY, BY 5.1–5.5 dB OVER 100–400 Hz, AND THE CLEAN SIDE IS BOUNDED AT
0.41 dB — NOT 0.007.** `analysis/a3_decomposition_gate.py` (**GATE O**, 8 computed sub-gates, exits
non-zero, **no render** — a re-read of `s99_attack_cand.json`, the shipped grade). It **imports**
`a3_balance_gate` (GATE M) and through it `level_law_gate` (GATE K) and `matrix_grade`, so the pair
selection and the absolute reconstruction cannot drift.

This was session 106's own item 2 — its decomposition was recorded as **"MEASURED, NOT YET GATED, DO
NOT QUOTE AS FACT"**. It is now gated, the headline survives, and **three of its supporting numbers
did not survive in the form they were written.**

⭐ **What the gate is FOR, in one line.** GATE M's excess `(mc − mo) − (qc − qo)` reads as a
*balance* — either path could be at fault. Regrouped as `(mc − qc) − (mo − qo)` it reads as *the
clean path's absolute error minus the OD path's*. Same number, different question — and the whole
content is whether the clean side can be shown to be ≈0. **O1 asserts the regrouping is an identity
elementwise (2.2e−15) with a mutation control**, so nothing below is an arithmetic slip.

⭐⭐ **THE LEDGER, and it RECONSTRUCTS THE MEASUREMENT TO 2e−16 — which is what makes it a
decomposition rather than three numbers side by side.** Contributions to the clean side's absolute
error as it actually enters every A3 pair (route B, master noon), 100–400 Hz:

| term | dB | what it is |
|---|---|---|
| MASTER law | **+2.024** | **common-mode** — downstream of BLEND, cancels in A3's excess |
| DIST-engage transparency gap (O7) | −0.174 | reference-side; our model is exactly transparent |
| clean SIGNAL-PATH residual | **+0.008** | at master unity, provenance-corrected |
| **= sum** | **1.859** | **= measured, to 2.2e−16** |

⇒ **clean-branch bound (conservative: residual + route gap + provenance transfer) = 0.407 dB against
an OD deficit of 5.28 dB — 8 %, and the deficit is 13× the bound.**

⛔ **CORRECTION 1 — "the clean side is exonerated to 0.007 dB" IS AN OVERCLAIM AND MUST NOT BE
QUOTED.** 0.007 dB is the master-unity reading alone. That capture sits on a **different capture
route** *and* a **different capture session** from the A3 pairs, and O7/O5 size both at 0.174 and
0.225 dB. **Quote 0.41 dB.** Nothing about the conclusion changes — it is still 13× clear — but the
exoneration is resolved to ~0.4 dB, not to 7 millidecibels.

⭐⭐ **CORRECTION 2 — THE `gain-n12` PROVENANCE OFFSET IS A *TILT*, NOT THE FLAT 0.107 dB RECORDED,
AND IT IS ENTIRELY THE REFERENCE'S.** Session 106 recorded "`ref-clean.wav` vs
`ref-clean_gain-n12.wav` agree to 0.107 dB". That is the **broadband mean** of a curve running
**+0.247 dB below 100 Hz → −0.067 dB over 1–8 kHz, span 0.334** — it **understates the low end by
2.3×**, and 100–400 Hz (A3's own band) reads **+0.225**, not 0.107. ⭐ **And O5's known answer says
whose it is: the clean path is linear, so the MODEL side of an n12 capture must be its twin shifted
by exactly the harness pad — measured `−12.0710 dB, span 1.8e−08`, i.e. exact at every band, with
the pad READ from `captures.gain_correction_db`.** ⇒ our side is perfect and the residue is **ND's
own clean path failing to be level-invariant across a 12 dB input change** (it scales by 12.178, not
12.071). GATE O corrects **per band** from here on.

⭐⭐⭐ **AND THE FREE KNOWN ANSWER THAT VALIDATES THE WHOLE INSTRUMENT — O6.** MASTER is a post-EQ,
attenuation-only divider into a unity buffer with nothing nonlinear downstream (C36 corners at
0.72 Hz), so **a MASTER law error is a PURE GAIN and must be flat in frequency.** Measured
**same-session it is 2.0240 dB at every band, span 0.0002 dB over 25 Hz–16 kHz.** Measured
**cross-session it spans 0.334 dB** — and that tilt **IS** O5's provenance residue. ⇒ one comparison
simultaneously confirms the absolute reconstruction, the band mapping, the provenance handling, and
circuit.md's claim that MASTER is a pure level control. ⚠ It also means the raw cross-session ladder
must not be read as the taper: use the same-session pair.

✅ **CORRECTION 3 / THE LOOSE END, RESOLVED — AND OUR MODEL IS THE ONE THAT IS RIGHT.** The two
routes to pure clean (`ref-clean.wav`, DIST off vs `blend-0700_base-od.wav`, BLEND min) disagree by
0.28 dB. **The MODEL renders them BIT-IDENTICALLY (3.6e−15) — asserted, because GATE K2 puts the
clean coefficient at exactly 1 at BLEND 0, so this is a topological requirement, not an
expectation.** The entire disagreement is on the **reference** side, and it is
frequency-structured: **in ND, route B (BLEND min) reads LOWER than route A (DIST off) by 0.11 dB
below 100 Hz, rising to 0.46 dB over 1–8 kHz.** ⇒ in ND, engaging DIST at BLEND minimum is **not
transparent**; in ours it is exactly so. ⛔ Not diagnosed and **not
folded into A3** — it is carried as part of the error bar, because the A3 pairs use route B while
the ladder and the makeup calibration use route A.

⚠ **A3's SIZE IS UNTOUCHED BY ALL OF THIS — 5.1–5.5 dB over 100–400 Hz, exactly as GATE M left it.**
O2 **asserts** MASTER is matched within every pair (and refuses if `a3_balance_gate.PAIR_KEYS` ever
stops containing it), so the master law is common-mode and cancels. **What changed is the
ATTRIBUTION, not the number.**

⚠⚠ **FLAG ON THE USER'S PENDING `gain-n12` DECISION (session 106), NOT A RECOMMENDATION.** GATE N
certified those rows on **THD turnover**, a nonlinear statistic. On the **absolute/linear** axis the
clean twin bounds the provenance residue at a **0.334 dB span**, which the matrix's per-row gain
match removes the *mean* of but not the *tilt*. ⛔ **And the OD twins CANNOT be read as provenance**:
they span 2.6–4.0 dB, but that is confounded with the model's own drive-dependent error (term (B))
changing at a 12 dB lower operating point, and nothing here separates the two. ⇒ session 106's
measured cost (+0.020 dB on the OD headline) stands; what this adds is that the rows are **cheap,
not clean**.

▶ **NEXT — ITEM 1 IS SUPERSEDED BY SESSION 108 (GATE P); items 2–6 survive untouched.**
1. ⛔ **SUPERSEDED — see the SESSION 108 block below. The premise stands, the TARGET does not.**
   ⭐⭐ **A3 term (A) — the timeboxed attempt (item 5). Premise now GATED, target unchanged**: the
   OD path's **5.1–5.5 dB absolute deficit over 100–400 Hz**, offset-dominated there (GATE M
   shape/offset 0.18), stimulus-independent to 0.47 dB, with the clean side bounded at 0.41 dB.
   ⛔ Not a two-sided balance — do **not** spend the attempt on the clean tap. ⛔ Not aimed at K7's
   broadband mean (0.9 of that is shape; ~1.7 dB of its rise is term (B)). ⚠ Gate any candidate on
   leaving 508–1016 Hz's drive dependence alone.
2. **GRUNT off-flat** — 1.68–1.85×, GAP #3b. Untouched by sessions 103–107.
3. ⭐ **The LEVEL law is a TOPOLOGY question** — unchanged from s104; discriminate L4's (a) vs (b).
   ⛔ Do not point an optimiser at the taper (L3/L6).
4. ⚠ **Term (B)** — drive-dependent, lives in or before the clipper, needs its own instrument.
5. **MASTER taper → Phase 10 C.** Not now. ⚠ When it IS opened, read the law from the
   **same-session** pair (O6): the cross-session ladder carries a 0.33 dB tilt that is not the pot.
6. ⚠ **Unclaimed, found in passing:** ND's DIST-engage at BLEND min is not transparent (O7) and
   ND's clean path is not level-invariant (O5). Both are ~0.2–0.3 dB **reference-side** properties
   our model does not reproduce. Neither is worth a session on its own; both bound how tightly any
   absolute clean-path claim can ever be made.

---

⛔⛔⛔ **SESSION 108 — THE HEAD ITEM'S TARGET DOES NOT SURVIVE MEASUREMENT. A3's 5.1–5.5 dB IS A
WINDOW MEAN OVER A MIGRATING FEATURE, ITS TWO DOMINANT BANDS ARE ITS LEAST REPRODUCIBLE, AND IT
CARRIES ±1.10 dB OF OPERATING-POINT SPREAD THAT HAS NEVER BEEN PRINTED. DO NOT FIT A CONSTANT TO
IT.** `analysis/a3_pedestal_gate.py` (**GATE P**, 6 computed sub-gates, exits non-zero, **no
render** — a re-read of `s99_attack_cand.json`, the shipped grade). It **imports**
`a3_balance_gate` (GATE M) and through it `level_law_gate` / `matrix_grade`, so the pair selection
and the absolute reconstruction cannot drift; **P1 re-pools the per-pair rows to GATE M's own curve
elementwise at 0.00e+00** before anything else is read.

⭐ **This IS the timeboxed attempt (item 5) being spent — on its first step, establishing the
target.** The target does not survive, so no constant was fitted and none is proposed.

⛔ **(i) It is a window mean over a peak, and the peak is where the measurement is worst.** Over
100–400 Hz at the clean stimulus:

| Hz | 101 | 127 | 160 | 202 | **254** | **320** | mean |
|---|---|---|---|---|---|---|---|
| excess, dB | 1.96 | 2.51 | 3.77 | 5.94 | **8.96** | **10.10** | **5.54** |
| across-pair sd, clean | 0.57 | 0.49 | 0.69 | 1.12 | **1.51** | **1.85** | |
| across-pair sd, drv_−6 | 1.85 | 1.22 | 0.63 | 0.76 | **2.27** | **5.17** | |

⇒ the two bands that carry the headline are ~2 dB above their neighbours **and** the two the four
capture pairs agree on least. Only **5 of 25** bands reproduce at sd ≤ 1.25 dB at both stimulus
extremes (127, 160, 202, 403, 508 Hz).

⛔⛔ **(ii) The headline pools over the pedal's OWN CONTROLS, and that spread is 5× the one it is
quoted with.** GATE M's 4 pairs differ in DRIVE (0.0, 0.5, 1.0) and ATTACK; it varies the STIMULUS
LEVEL and pools the rest. Per pair, the (A)-window mean:

| drive | attack | clean | drv_−6 |
|---|---|---|---|
| 0.5 | flat | 5.12 | 4.58 |
| 0.0 | boost | 6.09 | 4.56 |
| 0.0 | cut | 6.48 | **6.68** |
| 1.0 | flat | **4.48** | 4.73 |

⇒ **4.48 … 6.68 dB, a 2.21 dB span (±1.10 about the pooled 5.34)**, against the 0.47 dB
stimulus-level spread session 105 quotes. ⚠ **And which knob is NOT resolvable**: the two drive-0
pairs give a free ATTACK-at-fixed-DRIVE control, and DRIVE beats it **4.6×** at clean (span 1.80 vs
0.39) but **loses** at drv_−6 (1.04 vs 2.12). So "operating-point dependent" is supported;
"drive-dependent" is **not**, at n = 2/1/1. Do not attribute it.

⛔⛔⛔ **(iii) AND THE PEDESTAL IS NOT SMALL — IT IS UNMEASURED.** Separating a level term from the
feature needs a band that is both clear of the feature and agreed on by the pairs. **Those two sets
are disjoint**: the quiet bands (40–101, 2560–3225 Hz) are exactly the ones the pairs disagree on
(sd 1.6–4.3 dB), and every band they agree on (127–508 Hz) sits on the feature. **P6 sweeps BOTH
thresholds — 13 of 20 combinations give an EMPTY intersection**, and both knobs are asserted to
turn (band counts move 2→8 and 2→13). ⚠ Honestly stated: at the two loosest settings up to 3 bands
qualify, so this is quoted with its bars, not as absolute.

⭐⭐ **WHAT A STATIC CORRECTION COULD ACTUALLY BUY, measured (session work, not a sub-gate).** Over
the whole 40–3300 Hz band a real element acts on, the per-pair mean is **2.90–6.24 dB, pooled
4.66** — **not 5.1**, which is the window figure. A static +4.66 dB moves the A3 residual
**5.48 → 2.86 dB rms (48 %)** and **does not close it**. ⇒ this **corroborates session 52's "no
post-clipper linear element of any order closes A3"** through an instrument sharing none of its
machinery — and it quantifies what session 52 only excluded.

⚠⚠ **NONE OF THIS TOUCHES A3's SIZE OR ITS ATTRIBUTION.** GATE O's ledger — clean side bounded at
0.41 dB against a 5.28 dB OD deficit, reconstructed to 2e−16 — is untouched, and GATE M's headline
is reproduced exactly by P1. **The OD path is still quiet.** What falls is only that its size is a
*fittable constant*.

⚠ **Two defects in session 108's own gate, both caught by the gate refusing, and BOTH BROKEN
VERSIONS CONFIRMED THE HEAD ITEM.** (1) The first P5 measured the pedestal from "reproducible bands
OUTSIDE the (A) window" and reported it as **146 % of the window mean** — a share over 100 % is
arithmetically impossible for a component of a mean; the cause is that the only qualifying bands
(403, 508 Hz) sit on the feature's *upper flank*. **"Outside the window" is not "outside the
feature"** when the feature is wider than the window. (2) An earlier P5 `sys.exit`ed on "the
per-pair pedestal spreads 3.38 dB" — which is *the finding*, not a malfunction, and exiting on it
suppressed the threshold sweep entirely. Hard-exits now cover only the gate's own validity; physics
outcomes get computed verdicts. Both are in the discipline file.

⛔⛔⛔ **AND THE NEXT ITEM DOWN WAS ABOUT TO COST A WHOLE SESSION ON A PREMISE DISSOLVED 70 SESSIONS
AGO. "GRUNT off-flat — 1.68–1.85×, GAP #3b" IS NOT AN INDEPENDENT LEVER AND MUST NOT BE OPENED AS
ONE.** With A3 stood down, GRUNT was the next matrix-visible item; checking it before starting found
two independent disqualifications, both already on disk (`check-for-unread-data-first`, **seventh
occurrence** — and `verify-the-PREMISE`, **seventh**):

⭐ **(a) `docs/phase9-gap-log.md` §"GAP #3b DISSOLVED (session 38)" already closed it, and proved the
GRUNT caps cannot reach the target.** Session 23's framing — the pedal's GRUNT span is a *bump*, the
model's a monotone *shelf* — **expired**: `trebleC7` (s34/35) and `clipC15` (s36/37) turned the model
into a bump as a side effect, with nobody working on GRUNT. What remains is **0.89–1.04 octaves low
and 4.0–5.2 dB tall**, flat and boost agreeing to 0.15 oct / 1.2 dB ⇒ **ONE coherent error**, and it
is a property of the **OD/bleed crossover — i.e. A3** — not of the GRUNT network. ⛔ The decisive
part is the **locus**: sweeping C12 moves the peak **right and DOWN** (90 Hz/+10.28 → 147 Hz/+0.65)
while the pedal sits at **178 Hz/+6.27 — right and UP**, i.e. off the curve in *both* coordinates at
once, so **no value of any GRUNT cap reaches it.** Same for C13 on boost.

⭐ **(b) And the 1.68–1.85× number itself is confounded.** GATE J conditioned on `blend = 1.0`,
asserting in `od_residual_localise.py`'s own comments that this is "bleed-free BY TOPOLOGY". **GATE
K2 (session 103) refuted exactly that** — the BLEND pot's body bridges the LEVEL wiper to the clean
source at every blend position, so inside that set r(LEVEL, clean fraction) = **−0.961**. Session 103
re-scoped J10/J11 and **the GRUNT marginal was left standing**. ⇒ the number measures GRUNT *and*
bleed exposure together, which is A3 again. ⚠ The two stale comments in `od_residual_localise.py`
are **corrected in place** this session rather than left to mislead; GATE J still passes.

⭐⭐ **⇒ THE SYNTHESIS, which is the session's most useful output: what is LEFT of the OD error is
essentially ONE defect seen through four switches.** ~38 % of the headline is HF and is ND's artefact
(GATE I, not ours). Most of the rest is the **OD/bleed balance = A3**, and it is what the GRUNT axis
(s38), the LEVEL axis (s103 K7), the drive axis (s86) and the harmonic axis (s85) are each measuring.
The exclusions now compose into a single statement: **no single element (s50), no post-clipper linear
element of ANY order (s52), and no GRUNT-side cap (s38) reaches it** — and GATE P adds that **its
level is not a fittable constant** while GATE M5 shows **its shape IS coherent across pairs
(loo r = +0.64…+0.89) but MIGRATES with stimulus (254 → 640 Hz)**. ⛔ **A migrating shape cannot be
produced by a fixed linear network**, so the authorised fallback — a fitted *linear* correction
network — is ruled out by the same argument that ruled out s52's search. ⇒ **the remaining region is
inside/before the clipper and the correction must be drive-dependent**, exactly where item 5 has
always pointed. That is now an intersection of five independent exclusions, not a hunch.

▶ **NEXT — and the first is a DECISION for the user, not a measurement.**
1. ⭐⭐ **Should the A3 timeboxed attempt be stood down in its current form?** GATE P says the
   specified fix (a static level correction at 5.1–5.5 dB over 100–400 Hz) is aimed at a number
   that is not determined well enough to fit. The measured alternatives are: **(a)** stand it down
   and move to item 4 (term (B), the drive-dependent feature — which is what actually dominates the
   (A) window); **(b)** spend it anyway on a broadband **+4.66 dB** OD-path gain, accepting ±1.7 dB
   of operating-point dependence for a measured 48 % reduction that leaves 2.86 dB rms; or **(c)**
   fall back now to the fitted correction network item 5 already authorises. ⭐ **(b) IS judgeable**
   — a static OD gain is invisible at BLEND 0 and BLEND 1 by topology but changes the mix ratio at
   every intermediate BLEND, so the 129-capture matrix can arbitrate it there (GATE J: blend spans
   band-RMS 0.200 → 3.120). **My recommendation is (a)**: (b) fits one constant to a quantity
   measured to ±1.1 dB and would spend the one authorised attempt on the smaller half of the defect.
2. ⚠ **Term (B) is now the better-posed item, and GATE P weakens (A)/(B)'s separation.** What
   dominates (A)'s window is a feature at 254–320 Hz (clean) migrating to 640 Hz (drv_−6) — i.e. it
   behaves like (B). ⛔ **Not claimed as identical**: unifying them needs the feature's own shape
   identified, which GATE P does not do. But the split was made with two FIXED windows straddling a
   MOVING feature, which produces "one side stimulus-independent, the other swinging" as a property
   of the windows.
3. ⛔ **GRUNT off-flat — CLOSED as an independent item, session 108. Do not open it.** Session 38
   dissolved GAP #3b and proved no GRUNT cap reaches the target (the C12 locus runs right-and-down,
   the pedal is right-and-up); and GATE J's 1.68–1.85× is confounded with bleed via the refuted
   `blend = 1.0` premise. It is A3 seen through the GRUNT switch. **Fold it into item 1/5.**
4. ⭐ **The LEVEL law is a TOPOLOGY question** — unchanged from s104. ⛔ Do not point an optimiser
   at the taper (L3/L6). ⚠ Also A3-adjacent (K7 is the balance instrument), but the topology
   question is genuinely separate and is the one open item that is NOT A3.
5. **MASTER taper → Phase 10 C.** Read the law from the **same-session** pair (O6).
6. ⚠ **If the HF region is ever to be excluded, the pre-registered trigger is "everything else
   closed"** (session 101 GATE I / the gate table's fallback). It is not close, and G4 measured that
   excluding all four HF bands closes **one** of the eight failing rows and makes the OD median
   *worse*. Do not reach for it as a shortcut.

---

⭐⭐⭐ **SESSION 109 SHIPPED `kInputRef` 1.2596 → 0.90 — ONE CONSTANT, AND IT IS THE FIRST CHANGE IN
THE PROJECT TO CLOSE AN OD GATE ROW.** `src/dsp/GainStaging.h`. The 129-capture matrix accepts it,
**8 of the 9 gated OD/THD statistics improve**, CLEAN is **bit-identical**, and ctest is unchanged at
16/17. Baseline: **`analysis/reports/s109_k090_cand.json`** (129 captures, 504 shared rows,
membership identical to s99/s91/s90 — all four ARE comparable).

| | s100 shipped | **s109 shipped** | |
|---|---|---|---|
| **OD 100 Hz–8 kHz median** | 0.568 ⚠ over | **0.480 ✅ SHIP *and* STRETCH** | ⭐⭐ **the first OD gate row the project has ever closed** |
| OD band-RMS ex gain-n12 | 2.409 | **2.289** | ⭐ |
| OD tilt | 1.43 | **0.98** | ⭐ |
| THD (OD) level term | 3.663 | **3.096** | ⭐ (bar 3.0 — 0.096 away) |
| OD 8–16.3 kHz p90 | 8.058 | **7.100** | ⭐ |
| OD p99 | 14.661 | **14.314** | ⭐ |
| OD 25–100 Hz median / p90 | 0.860 / 4.971 | **0.824 / 4.947** | ⭐ |
| OD 100 Hz–8 kHz p90 | 4.458 | **4.192** | ⭐ |
| OD 8–16.3 kHz median | 0.566 ✅ | 0.578 ✅ | ⚠ the ONLY gated row worse, by 0.012 dB, still SHIP |
| **CLEAN, all four rows** | 0.453 | **0.453 bit-identical** | ✅ |
| rows better >0.5 dB / worse | — | **38 / 22** | |
| ALL band-RMS | 1.771 | **1.694** | ⭐ |

⚠ **Costs, stated:** THD **tilt** worsens 2.708 → 3.415 (not a gated row) and 22 of 504 rows regress
by >0.5 dB. **7 gated rows remain over SHIP** (was 8) — Phase 9 is still open on the model.

⭐⭐ **WHY IT WORKS, AND WHY NOBODY HAD TRIED IT: `kInputRef` WAS FILED UNDER "cannot be measured"
AND THEREFORE NEVER UNDER "can be used".** The source has documented since session 17 that K is
**degenerate with the clip ceiling** and **cancels exactly through the linear path**; sessions 17/43/44
each asked how to *choose* it (s43 measured that the harmonic objective does not identify it at all;
s44 fenced it with an arithmetic clean-headroom bound). Nobody asked what it *does*. Because it
cancels in the linear path, K is the **only** knob that moves every nonlinear operating point at once
— the CD4049 ceiling, both J201 ceilings, the TL07x rails and the D1/D2 window — while provably
changing nothing linear. ⭐ **GENERAL: when a constant is recorded as unidentifiable, write down what
it is INVARIANT on — that invariance is usually why it is a clean lever somewhere else.**

⭐ **IT IS A MOVE TOWARD PHYSICS, NOT AWAY FROM IT.** K is degenerate with the ceilings, so 1.2596 →
0.90 is *exactly equivalent* to raising every OD-path ceiling by **2.92 dB**, and every one lands
inside its own bound: clipSat sum **1.036 → 1.449 V** against the self-consistent R19-dropped
**5.636 V** rail (18 % → 26 %, where `FitParams.h` flagged 18 % as a soft-low), TL07x rails
**2.7/2.9 → 3.78/4.06 V** against the ±4.325 V the 8.65 V supply allows, and the implied input stays
ordinary at **0.45 V peak** at the −6 dBFS rung (s44's was 0.63 V). 0.90 is far inside the ≤ 1.509
V/FS clean-headroom bound, which is the only hard constraint. ⇒ **the user's authorisation to break
from the schematic was not needed for this one.**

⭐ **ACCEPTANCE CHECK RUN AND PASSED**: the shipped default renders **bit-identically** to an explicit
`--input-ref 0.90` at **all three ATTACK throws**, with a mutation control (`--input-ref 1.2596` must
change the render) proving the check is not vacuous — so `s109_k090_cand.json` IS the shipped grade
with no re-render. ⚠ The first attempt used wrong flag names (`--loMid`, not `--lo-mid`); the check
**refused** rather than printing a verdict on absent files, which is the s100 lesson applied.

⚠ **ctest 16/17, same single pre-existing `OSValidationTest` failure, and its numbers are UNCHANGED**
— verified, not assumed: that test feeds `PedalDSP` directly in **chain-domain volts**, so K (a
DAW-domain scalar) never enters it. Its comment claiming the probe amp tracks `kInputRef 3.377` was
**corrected in place** rather than left to mislead.

---

⭐⭐⭐ **AND THE MEASUREMENT THAT FOUND IT — `analysis/od_absolute_gate.py` (GATE Q), 7 computed
sub-gates, no render. THE OD PATH'S ABSOLUTE ERROR IS TWO DEFECTS, AND THE BIGGER ONE IS A
*SATURATION* ERROR NO LINEAR ELEMENT CAN CARRY. THAT IS WHY EVERY LINEAR SEARCH SINCE SESSION 50 HAS
FAILED.** GATE O made the OD path's own absolute error readable (clean side bounded at 0.41 dB); GATE
Q reads it **directly** off the **15** pure-OD endpoints — BLEND = 1 and LEVEL = 1, where the mix
coefficient is exactly 1 (GATE K2) — instead of through GATE M's 4 settings-matched pairs. Split by
what it depends on instead of pooled (which is what GATE P's finding actually called for):

| | rms | what can carry it |
|---|---|---|
| **L(f)** = error at −30 dBFS | **2.72 dB** | a LINEAR element |
| **D(f)** = error(−6) − error(−30) | **3.01 dB** | only a NONLINEARITY |

⭐ **The mechanism, measured three ways that share no arithmetic:**
**(a)** the **compression law** — from −30 to −6 dBFS the model's OD path loses **4.17 / 3.25 /
1.00 dB MORE** than the reference over 500 Hz–8 kHz at DRIVE 0 / 0.5 / 1;
**(b)** the **320 Hz null**, referred to each side's own 202/508 Hz shoulders so it is immune to any
absolute-level error *and* to the matrix's gain match — the model's **washes out** with level
(9.63 → 4.36 dB) while the reference's **DEEPENS** (6.00 → 8.06). A fixed network's null depth cannot
depend on stimulus, and compression is exactly what fills a cancellation null;
**(c)** **THD on those same bleed-free endpoints runs +2.94 dB** — the model **over-distorts**, the
same sign as over-compressing.
⇒ **the model's OD path saturates too early**, one statement explaining the level deficit, the null
behaviour and the THD excess at once. ⛔ **This does NOT contradict sessions 50/52** — they ruled out
single elements and post-clipper LINEAR elements against a pooled residual that *contained* D. It is
the reason they could not have succeeded.

⭐ **The lever was SELECTED BY MEASUREMENT, not by argument** — `analysis/od_lever_screen.py` renders
**21 single-constant perturbations** over GATE Q's own endpoints and scores each by how much of the
target it moves *and by the cosine between what it moved and what needs moving*:

| lever | GATE Q score | note |
|---|---|---|
| (shipped) | 4.663 | |
| **kInputRef 0.90** | **3.973** | ⭐ interior (0.80 → 4.031, 1.00 → 4.094) |
| clipSat ×1.5 | 4.045 | interior, but breaks DRIVE max (excess −1.00 → −4.34) |
| clipA0 15 | 4.487 | |
| rail ×1.5 | 4.529 | |
| **jfetCeil ×1.5 / ×2.5 / ×4** | **4.629 / 4.623 / 4.649** | ⛔ **inert — the J201 ceilings are NOT the binding element**, which refutes the obvious "the pre-DRIVE stage over-compresses" reading |
| jfetExpandBeta 0.2 / 0.8 | 4.666 / 4.637 | inert |

After the change the residual excess compression is **−1.78 / −1.72 / −2.33 dB** and, notably,
**DRIVE-INDEPENDENT to 0.60 dB** (it spanned 3.17 dB before) — a much better-posed remainder.

⛔⛔ **TWO CORRECTIONS FELL OUT, AND BOTH CHANGE WHAT THE NEXT SESSION SHOULD DO.**
**(1) THE GATED "THD level term" IS AN UNSIGNED RMS AND ITS SIGN IS THE OPPOSITE OF WHAT THIS FILE
HAS SAID FOR EIGHTEEN SESSIONS.** `shape_gate` computes `abs(c[0])/sqrt(n)`; the **signed** mean of
the same decomposition — already computed, already stored as `level_signed` — is **+1.263 dB**, i.e.
**the model distorts MORE than the reference, not less.** Open-work item 3 is written around "the
model's distortion *amount* being systematically low" and that premise is **wrong**; every candidate
reasoned about as "we need more distortion" was pointed backwards. Corroborated independently at
**+2.94 dB** on the bleed-free OD endpoints. ⇒ **item 3 must be re-scoped again, and this time on
the sign, not just the size.** (At s109 the signed term reads +1.412 — slightly further from zero
while the gated unsigned rms improves 3.663 → 3.096, because the change removes spread, not offset.)
**(2) A PREVIOUSLY-UNRECORDED REFERENCE DROPOUT — AND IT IS THE WORST SINGLE ROW IN THE MATRIX.**
The four sweeps are the SAME sweep at −30/−18/−12/−6 dBFS, so the reference's band-median must be
monotone. Testing exactly that over all 258 interior rungs found **one** violation:
**`drive-1700_level-1700_grunt-boost_base-od.wav @ sweep_drv_-12`**, reading a band-median of
**+3.5 dB against +15…+23 at BOTH neighbours**. It is the **worst FR row** (band-RMS 20.08) and the
**second-worst THD row** of the shipped `shape_gate` decomposition, it carried **0.96 dB of GATE Q's
score on its own**, and it is worth **+0.055 dB of the shipped OD headline** (2.409 → 2.354 without
it). ⚠ It is **NOT** the session-48 `gain-n12` defect — different file, session and signature — so
the standing "one known-bad group" framing was incomplete. ⛔ **NOT excluded from the matrix
unilaterally** (that is the same class of decision as s106's `gain-n12` retirement); GATE Q excludes
it from its own statistics and prints what it was worth. **A USER DECISION.**

⚠ **The bar for that exclusion is placed on measured evidence, not chosen**: over the 258 rungs the
statistic is cleanly **bimodal** — worst healthy sag **−0.35 dB**, the defect at **+11.59**, an
**11.94 dB gap with nothing between** — so GATE Q asserts the SEPARATION rather than a count, and
refuses if the population ever stops being bimodal. ⚠ A first draft used "12 dB, deliberately
generous" and **missed the defect by 0.41 dB while printing a clean pass.**

▶ **NEXT, in order.**
1. ⛔ **SUPERSEDED BY SESSION 110 (GATE R). The premise is CONFIRMED, the "either/or" is REFUTED,
   and the target is narrowed from "the null's stimulus dependence" to "the null's depth at DRIVE
   MAX".** See the SESSION 110 block below.
   *(The session-109 text read:)* ⭐⭐ **The remaining OD error is now well-posed and has a NAME: the
   320 Hz null's stimulus dependence.** After s109 the model's null still runs **+4.31 dB too deep at
   −30 dBFS and −3.67 dB too shallow at −6** — it washes out where the reference's deepens. In our
   model that null is formed **pre-clipper** (the treble/ATTACK ladder), so compression fills it; for
   the reference's to survive drive, its null must either sit **post-clipper** or see a far gentler
   nonlinearity. ⇒ this is a **TOPOLOGY question about where the null lives**, and it is the natural
   successor to session 99's "the missing degree of freedom" — which is exactly where the user's
   add-a-component authorisation pays. ⛔ Do NOT point another optimiser at the ATTACK ladder's
   damping: s99 measured the saturation (width rms 4.07–4.66 across a 100×/3× sweep) and s109 shows
   the depth defect changes SIGN with stimulus, which no damping resistor can do.
2. ⚠ **Re-scope open-work item 3 on the SIGN** — see correction (1). The model over-distorts.
3. **DECISION for the user: exclude the `drive-1700_level-1700_grunt-boost @ drv_-12` dropout?**
   Worth +0.055 dB on the OD headline, and it is the matrix's worst row. Same class as s106's still-
   open `gain-n12` decision; the two should probably be taken together.
4. ⭐ **The LEVEL law is a TOPOLOGY question** — unchanged from s104. ⛔ Not the taper (L3/L6).
5. **MASTER taper → Phase 10 C.** Read the law from the **same-session** pair (O6).
6. ⚠ Unclaimed: ND's DIST-engage at BLEND min is not transparent (O7); ND's clean path is not
   level-invariant (O5). Both ~0.2–0.3 dB reference-side.
⚠ **Every OD number measured before session 109 is superseded** — K is upstream of every
nonlinearity. Quote against `s109_k090_cand.json`.

---

⭐⭐⭐ **SESSION 110 — THE 320 Hz NULL IS *OURS* WHERE WE THOUGHT IT WAS, THE HARMONICS AT IT COME
FROM THE J201 AND NOT THE CLIPPER, AND GATE Q's "THE REFERENCE'S NULL DEEPENS" IS A **DRIVE-MAX-ONLY
PROPERTY THAT POOLING TURNED INTO A DEVICE PROPERTY**.** `analysis/null_locus_gate.py` (**GATE R**,
8 computed sub-gates, exits non-zero). It **imports** `od_absolute_gate` (GATE Q) and through it
`a3_balance_gate` / `level_law_gate` / `matrix_grade`, so the endpoint selection, the `gain-n12`
exclusion and the s109 dropout exclusion cannot drift. ⚠ Unlike GATES J–Q this one **does render** —
15 endpoints + 20 arm/candidate renders, all argv-stamped — but **no DSP constant moved and no
baseline moved**.

⭐ **This is session 109's head item being spent on its first step: establishing the target. Two of
the three load-bearing clauses in that item had never been measured.**

⭐⭐ **(1) OUR NULL IS THE PRE-CLIPPER TREBLE LADDER — CONFIRMED BY MEASUREMENT, NOT ASSERTED FROM
TOPOLOGY (R2).** Both candidate networks are R-C, so scaling all of one network's caps by k moves
*its own* notch by exactly 1/k and nothing else — which gives R1 a real known answer rather than a
bare perturbation:

| | 320 Hz null | bridged-T notch |
|---|---|---|
| shipped | **329.7 Hz** | **712.0 Hz** |
| treble-ladder caps ×2 (PRE-clipper) | **164.2 Hz** (ratio **2.008**) | 715.9 (moved 3.8 Hz) |
| bridged-T caps ×0.5 (POST-clipper) | 329.2 (moved **0.5 Hz**) | **1440.0** (ratio **2.022**) |

⇒ the null follows the ladder and ignores the bridged-T, and the control network does the opposite.
**CLAUDE.md's standing premise is right.**

⭐⭐⭐ **(2) AND THE MECHANISM NOBODY HAD NAMED: THIS CHAIN HAS TWO NONLINEARITIES AND THE NULL SITS
BETWEEN THEM.** The J201 is at the JFET drain, the ladder hangs off that drain, the CD4049 is
downstream of both. Measured at the null (R5), H2/H1 re its own shoulders:

| arm | H2/H1 at the null | re shoulders | moved by |
|---|---|---|---|
| shipped | −16.46 | **+19.36** | — |
| `jfetSatNeg = 0` (J201 even generator removed) | −75.47 | **−32.55** | **+59.011 dB** |
| clipper made SYMMETRIC | −16.46 | +14.14 | **+0.001 dB** |

⇒ **the H2 at the null is made ENTIRELY by the J201, upstream of the null; the clipper contributes
one thousandth of a dB.** Both arms are shown non-vacuous (each moves ≥21 dB elsewhere on the probe
row) before their non-movement at the null is read. ⚠ **This inverts the obvious reading**: a
pre-clipper null does NOT give a "starved source" dip here, it gives a **PEAK**, because the source
is upstream of it. With the J201's even term off it *does* dip (−32.55), which is the derivation
recovering once the second nonlinearity is removed. **`verify-the-PREMISE`, applied to my own
algebra.**

⭐⭐ **(3) THE WASH-OUT IS COMPRESSION, PROVEN BY DOSE-RESPONSE ON OUR OWN MODEL (R6).** A
pre-clipper null feeds a compressor, and a compressor squashes any dip fed into it — so the model's
null must wash out, and the wash-out must grow with DRIVE. DRIVE is the dose and DRIVE min is the
built-in null case. Null prominence (dB, 1/6-oct power-integrated), median over the 5 endpoints at
each DRIVE:

| DRIVE | side | clean | drv−18 | drv−12 | drv−6 | **wash-out** |
|---|---|---|---|---|---|---|
| 0.0 | model | 15.78 | 15.45 | 15.34 | 14.23 | **+1.54** |
| 0.0 | pedal | 14.87 | 11.46 | 10.56 | 9.26 | +5.61 |
| 0.5 | model | 15.46 | 15.08 | 12.63 | 8.83 | **+6.63** |
| 0.5 | pedal | 14.39 | 9.94 | 11.22 | 9.70 | +4.69 |
| 1.0 | model | 13.67 | 4.92 | 2.26 | 3.84 | **+9.83** |
| 1.0 | pedal | 4.99 | 6.81 | 11.01 | **12.37** | **−7.38** |

⇒ **MODEL +1.54 → +6.63 → +9.83, monotone in DRIVE — the prediction holds.** ⭐ Corroborated
independently by **R6b**: the 320 Hz null (pre-clipper) and the bridged-T (post-clipper) straddle
the compressor, so drive must change their RANK, and it does — the bridged-T becomes the deeper
feature at DRIVE ≥ 0.5 under stimulus. A prediction with no free parameter.

⛔⛔ **(4) AND THE CORRECTION TO GATE Q: THE REFERENCE WASHES OUT TOO, EVERYWHERE EXCEPT DRIVE MAX.**
At DRIVE 0 and 0.5 the pedal's null washes out **+5.61 / +4.69 dB**, i.e. it behaves like ours. Only
at DRIVE max does it reverse (**−7.38**). GATE Q pooled the 15 endpoints, which span DRIVE {0, .5,
1}, and reported one number. ⇒ **"the reference's null DEEPENS with level" is a property of the
DRIVE-max rows, not of the device** — s108's P4 trap (pooling over the pedal's own controls) in a
second place, and this time it set the whole next-step framing. ⚠ The conclusion is robust to the
estimator even though the magnitudes are not: on the point-sample control the same three cells read
+20.45 / +16.78 / −4.06 — same signs, same reversal, very different sizes.

⛔ **(5) R8 — BOTH OBVIOUS EXPLANATIONS FOR THE DRIVE-MAX GAP WERE RENDERED, AND NEITHER CLOSES IT.**

| arm (DRIVE max, n=5) | clean | drv−18 | drv−12 | drv−6 | wash-out |
|---|---|---|---|---|---|
| shipped | 13.67 | 4.92 | 2.26 | **3.84** | +9.83 |
| `kInputRef` 1.2596 (pre-s109) | 10.94 | 2.96 | 2.59 | 4.30 | +6.64 |
| bridged-T moved to 320 Hz | 22.22 | 13.99 | 11.33 | **12.79** | +9.43 |
| **PEDAL** | **4.99** | 6.81 | 11.01 | **12.37** | **−7.38** |

**(a) The global saturation lever does NOT touch it.** ⚠ And read WHICH END moved before calling
that a regression: the shipped K **improved the quiet end** (10.94 → 13.67) and left the driven end
alone (4.30 → 3.84); the wash-out grew because its *other* end did.
**(b) A post-clipper null at 320 Hz reproduces the reference's DRIVEN depth almost exactly**
(12.79 vs 12.37, **0.42 dB**, from a shipped gap of 8.53) — but it also deepens the quiet end to
22.22 where the reference is only **4.99**, so the wash-out is unchanged.
⇒ **the reference's null DEPTH GROWS with stimulus, which no fixed linear network at ANY position
can do**, because a fixed cancellation's depth does not depend on level. ⭐⭐ **So the missing degree
of freedom is not a null in a different PLACE — it is a null whose DEPTH IS LEVEL-DEPENDENT.** That
is a much sharper target than "topology", and it is coherent with the standing finding that our OD
path saturates too early. ⚠ n = 5 captures at ONE drive setting: a **located** target, not a
characterised one.

⛔⛔⛔ **AND THE SESSION'S LAST FINDING IS THE ONE THAT BLOCKS QUOTING ANY OF IT AS FINAL: THE
s109 BASELINE IS STALE, BECAUSE THREE CAPTURES WERE RE-RECORDED *AFTER* IT WAS RENDERED — AND THE
s109 DROPOUT DID NOT GO AWAY, IT MOVED RUNG.** Found only because the pending user decision prompted
a look at the capture directory's own timestamps:

| file | mtime (2026-08-02) | |
|---|---|---|
| `analysis/reports/s109_k090_cand.json` | **09:29** | the shipped baseline |
| `drive-1700_level-1700_grunt-boost_gain-n12_base-od.wav` | 09:45 | re-captured |
| **`drive-1700_level-1700_grunt-boost_base-od.wav`** | **09:46** | **the s109 dropout file, re-captured 17 min AFTER the baseline** |
| `drive-1700_level-1700_master-1100_grunt-boost_base-od.wav` | 09:50 | **a NEW condition, not in the s109 matrix at all** |

⛔⛔ **THE RE-CAPTURE DID NOT FIX THE DROPOUT — IT REPRODUCED IT AT THE SAME RUNG, AND SO DOES THE
NEW `master-1100` CAPTURE. THE `gain-n12` TWIN, RECORDED 12 dB QUIETER, IS CLEAN.** Reference ladder
band-medians from the re-rendered baseline (the report's own 29-band read):

| capture | clean | drv−18 | **drv−12** | drv−6 |
|---|---|---|---|---|
| `drive-1700_level-1700_grunt-boost_base-od` (re-captured) | 13.43 | 13.73 | **−0.47** | 14.39 |
| `drive-1700_level-1700_master-1100_grunt-boost_base-od` (NEW) | 12.60 | 12.90 | **−1.30** | 13.55 |
| `..._grunt-boost_gain-n12_base-od` (send 12 dB down) | 12.54 | 15.52 | **15.62** | 15.82 |
| `drive-1700_level-1700_grunt-flat_base-od` (control) | 14.88 | 16.04 | 16.04 | 14.66 |

⇒ **three captures of the same condition, two MASTER settings, same rung, same ~14 dB hole — and the
one recorded 12 dB quieter does not have it.** That is not a capture accident: it is a
**reproducible, level-dependent ND behaviour at DRIVE max × LEVEL max × GRUNT boost**, and it is now
much better evidenced than s109's single occurrence. ⚠ It remains EXCLUDED rather than explained;
whether it is worth a session of its own is an open question, but it is no longer "one bad take".

⛔⛔ **CORRECTION — AN EARLIER CLAIM IN THIS SESSION THAT THE DEFECT "MOVED RUNG" WAS WRONG, AND THE
CAUSE IS AN ENTRY ALREADY IN THE DISCIPLINE FILE.** A scratch read said the re-captured file now
broke at `drv_-18` and its twin at `drv_-6`. That statistic was a median of the full-resolution
Farina H1 curve over a **LINEARLY-spaced rfft grid** from 25 Hz–16.3 kHz — thousands of points,
overwhelmingly at HF, i.e. **a high-frequency statistic wearing a broadband name**
(`median-over-linear-bins`, s98 GATE H4, committed again here). Measured both ways on the same file:

| sweep | median over the LINEAR rfft grid | median over the 29 LOG BANDS *(the real instrument)* |
|---|---|---|
| clean | 0.71 | 13.38 |
| drv−18 | **−19.70** ← the artefact | 13.65 |
| drv−12 | −0.06 | **3.34** ← the real dropout |
| drv−6 | −0.60 | 14.38 |

⇒ **the rung never moved.** ⭐ The "detect, never name" design is still the right call and still
proved its worth — not because the cell moved, but because a **NEW capture with the same defect
appeared**, which a hardcoded filename would have missed entirely.

⚠⚠ **THE STRUCTURAL TRAP, WHICH IS NEW: GATE R TAKES ITS MEMBERSHIP AND ITS DROPOUT EXCLUSIONS FROM
A STORED REPORT AND READS THE PEDAL SIDE STRAIGHT OFF THE CAPTURE WAVS — TWO DIFFERENT EPOCHS.** So
it was excluding a cell that no longer exists while reading a file the report has never seen. **New
sub-gate R3b** compares every endpoint capture's mtime against the report's and **refuses**;
`analysis/null_locus_gate.py` currently **exits non-zero on exactly that**, which is the honest
state. ⇒ **RE-RENDER THE 129-CAPTURE BASELINE BEFORE RE-QUOTING ANY OD HEADLINE.**

✅ **DECIDED WITH THE USER, SESSION 110 — THE DROPOUT IS EXCLUDED AS A *CELL*, RE-DETECTED PER
RENDER RATHER THAN NAMED, AND IT NOW LIVES IN THE SHARED GRADING PATH.** `matrix_grade.find_dropouts`
is the single definition (moved out of GATE Q, which had it first); `release_gate.subsets()` takes
the detected set and breaks it out as its own printed `ref dropout [bad]` subset, exactly as the
`gain-n12` split has always been handled — **excluded, never silent** (s40). ⭐ Detection is a
property of the LADDER, not a filename, which is precisely what this session's re-capture proved
necessary: a hardcoded `(file, sweep)` pair would have silently stopped matching when the defect
moved rung. ⚠ `subsets(rows)` still defaults to excluding nothing, so GATE I / GATE J and every
pre-s110 quote stay reproducible.

⭐⭐ **THE NEW BASELINE — `analysis/reports/s110_baseline.json`, 131 captures, 512 graded rows.**
Membership is a strict SUPERSET of s109's (all 504 shared rows present, 0 lost), so the two ARE
comparable on the shared set. Two things moved at once and must not be read as one: **+2 captures**
(the user's `master-1100`, and a re-captured `grunt-boost_gain-n12` twin) and **the dropout
exclusion**. Isolated:

| | s109 as published (129 caps, cell IN) | s109 re-graded (cell OUT) | **s110 baseline (131 caps, cell OUT)** |
|---|---|---|---|
| OD band-RMS | 2.289 | 2.232 | **2.265** |
| **OD p99** | 14.314 | 12.559 | **12.893** ⭐ |
| THD (OD) level | 3.096 | 3.067 | **3.065** ⭐ (bar 3.0 — 0.065 away) |
| OD 100 Hz–8 kHz median / p90 | 0.480 / 4.192 | 0.478 / 4.129 | **0.489 / 4.195** |
| OD 25–100 Hz median / p90 | 0.824 / 4.947 | 0.818 / 4.896 | **0.825 / 4.888** |
| OD 8–16.3 kHz median / p90 | 0.578 / 7.100 | 0.569 / 6.759 | **0.581 / 7.101** |
| CLEAN, all four rows | 0.453 | 0.453 | **0.453** |

⇒ the exclusion buys most of it (p99 **−1.755**) and the two new captures give a little back. **7
rows remain over SHIP; none closes.** ⚠ Every pre-s110 OD number is now quoted against a different
membership AND a different exclusion set — re-quote against `s110_baseline.json`, and never diff a
pre-s110 figure against it without saying which of the two changes is responsible.

**Measured cost of the exclusion alone, on the s109 report** — one cell, and it was carrying more
than s109's estimate:

| | with the cell | **cell excluded** | |
|---|---|---|---|
| OD band-RMS | 2.289 | **2.232** | ⭐ (s109 predicted 0.055; measured 0.057) |
| **OD p99** | 14.314 | **12.559** | ⭐⭐ **−1.755 dB** — that row carried much of the extremes tail |
| OD 8–16.3 kHz p90 | 7.100 | 6.759 | ⭐ |
| OD 100 Hz–8 kHz median / p90 | 0.480 / 4.192 | 0.478 / 4.129 | |
| OD 25–100 Hz median / p90 | 0.824 / 4.947 | 0.818 / 4.896 | |
| **THD (OD) level term** | 3.096 (n 228) | **3.067** (n 227) | ⭐ 0.067 from its 3.0 bar, was 0.096 |
| CLEAN, all rows | 0.453 | **0.453** | unchanged |
| the excluded cell itself | — | band-RMS **20.413**, max │Δ│ 39.08 dB | the matrix's worst row |

⚠ **The THD gate row excludes the same detected set** — that cell is the second-worst THD row of
the shipped decomposition, and excluding it from the FR rows while leaving it in the THD row would
have made the two halves of the gate disagree about which data exists.

⚠ **No gated row closes** — still 7 over SHIP. And the threshold is defensible on this report
because the sag population is still cleanly bimodal: measured separation **14.92 dB** against a
3.0 dB minimum, asserted by `check_dropout_separation` rather than assumed.

⭐ **The session's headline is UNCHANGED on the re-rendered baseline, and GATE R now passes on it.**
Condition-pooled, the DRIVE-max pedal wash-out is **−7.38 dB** and the model's dose-response is
**+1.54 → +6.63 → +9.83, monotone** — the same figures as before the re-capture, which is what the
MASTER-inertness result predicts. R8 prints the per-file spread s108's P4 rule demands:
**−12.46 … +2.41 dB across the 6 captures, 5 of 6 individually reversing.** ⇒ **quote the SIGN of
the reversal, never its size**; the 15 dB spread is exactly why item 2 below is "characterise",
not "fit".

⚠⚠ **THREE DEFECTS IN SESSION 110's OWN GATE, AND TWO OF THEM WOULD HAVE SUPPRESSED THE FINDING.**
(1) The prominence was an `argmin` over a 200–520 Hz window; at high drive the pre-clipper null
washes out so far that the **post-clipper bridged-T becomes the deepest point** and argmin walked
onto it in **18 of 120 cells, all model cells**. Naming the notch frequency buys nothing if the
estimator may then leave it. The window is now 290–370 Hz — and the rank swap it exposed is kept as
**R6b**, a measurement rather than a bug. (2) **Two successive FLOOR guards were both wrong.** The
first took the 5th percentile of the H1 curve — **self-referential**, since the null *is* that
curve's bottom — and flagged 101/120 cells. The second used the sub-20 Hz deconvolution residue,
which **tracks the stimulus almost 1:1** (model −35.4 → −15.1 dB re the in-band level across the
ladder) and is therefore signal-proportional residue, **not a floor** — and it deleted exactly the
DRIVE-max pedal cells carrying the headline. **There is no noise floor here: both sides are
deterministic renders.** The scored statistic is now a 1/6-octave power-integrated deficit, set by
the notch's *area* rather than its bottom, with the point sample kept as the control.
(3) A `nan` from that dead-end exclusion silently flipped R7's verdict to "no sign reversal" —
`nan < 0` is False — which is the s106 GATE N3 trap in this gate's own code. `isfinite` is now
checked first and explicitly.

⭐ **All eight guards were mutation-tested with an unmutated control; 7 mutations fire, the control
passes.** ⚠ **The first mutation run returned 7-of-7 "PASS" and every one was a `FileNotFoundError`**
— s107's trap in a new costume: the patched copy must *live* in `analysis/` (so its sibling imports
resolve) but must *run* from the repo root (so repo-relative data paths resolve). Getting only the
first half right is what s107 recorded, and the CONTROL is the only reason it was caught. ⚠ And one
mutation was itself vacuous: patching a module constant inside `main()` never reaches the
`ProcessPoolExecutor` workers, which re-import the module fresh — it read as a broken guard when the
guard was fine.

▶ **NEXT, in order.**
1. ⭐⭐ **The head item is now "a null whose depth grows with level", at DRIVE MAX specifically.**
   R8 gives it a number to hit: the driven depth is **3.84 dB against the reference's 12.37**, and a
   post-clipper 320 Hz null closes that to **0.42 dB** while overshooting the quiet end by ~17 dB.
   ⇒ what is wanted is something contributing a 320 Hz cancellation **that engages with level**.
   ⛔ Do NOT ship the bridged-T move — it is a mechanism probe, and relocating the recovery network
   would wreck everything it currently does. ⛔ Do NOT point an optimiser at the ATTACK ladder
   (s99's saturation) or at `kInputRef` (R8a says it does not reach this).
2. ⚠ **Characterise before fitting.** R8 is n = 5 at one DRIVE setting. Before anything is proposed,
   the level-dependence needs measuring across the drive/stimulus plane — GATE P's lesson about
   fitting a constant to a quantity whose spread was never printed applies directly here.
3. ⚠ **Re-scope open-work item 3 on the SIGN** — unchanged from s109. The model over-distorts.
4. ✅ **DONE, SESSION 110 — THE BASELINE IS RE-RENDERED: `analysis/reports/s110_baseline.json`,
   131 captures, 512 rows.** `s109_k090_cand.json` is superseded and must not be quoted. The
   user's `master-1100` capture is graded (it needed no code change — `find_captures()` globs the
   directory and it parses as `master` 0.4). ⚠ **Quote every OD number against `s110_baseline.json`
   from here**, and see the grade table in the session-110 block for what moved and why.
5. ✅ **DONE, SESSION 111 — THE `gain-n12` EXCLUSION IS RETIRED, on the user's decision. Those rows
   are GRADED.** ⚠ The cost is **NOT** the +0.020 dB / n 320 → 336 quoted here: that was measured on
   the s109 report, and at s110 the group is **20 rows, not 16**. See the SESSION 111 block below.
6. ⭐ **The LEVEL law is a TOPOLOGY question** — unchanged from s104. ⛔ Not the taper (L3/L6).
7. **MASTER taper → Phase 10 C.** Read the law from the **same-session** pair (O6).
8. ⚠ Unclaimed: ND's DIST-engage at BLEND min is not transparent (O7); ND's clean path is not
   level-invariant (O5). Both ~0.2–0.3 dB reference-side.

---

⭐⭐⭐ **SESSION 111 — THE `gain-n12` EXCLUSION IS RETIRED (USER DECISION). THE 20 ROWS ARE GRADED,
THE COST IS 3× THE RECORDED ESTIMATE, IT RE-OPENS THE ONE OD GATE ROW SESSION 109 CLOSED — AND THE
ROWS TURN OUT TO BE THE ONLY THING IN THE MATRIX THAT CAN SEE THE *SLOPE* OF THE DISTORTION LAW.**
No render, no DSP constant moved: a re-grade of `s110_baseline.json` plus a membership change in the
shared grading path (`matrix_grade.EXCLUDE_GAIN_N12`, now `False`, with the full provenance in its
block). ⭐ **ACCEPTANCE CHECK PASSED: `--ex-gain-n12` reproduces every pre-s111 gated cell EXACTLY**
(diffed against a run made before the change — identical, not "close"), so every older quote stays
reproducible on demand and the movement below is attributable to the membership alone.

| | ex `gain-n12` (pre-s111) | **graded (s111)** | |
|---|---|---|---|
| OD rows | 322 | **342** | |
| OD band-RMS | 2.265 | **2.327** | ⚠ +0.062 |
| **OD 100 Hz–8 kHz median** | **0.489 ✅ STRETCH** | **0.531 ⚠ over** | ⛔⛔ **re-opens the only OD row the project has ever closed** |
| OD 25–100 Hz median / p90 | 0.825 / 4.888 | 0.917 / 4.875 | ⚠ / ⭐ |
| OD 100 Hz–8 kHz p90 | 4.195 | 4.242 | ⚠ |
| OD 8–16.3 kHz median / p90 | 0.581 / 7.101 | 0.625 / 7.451 | ⚠ |
| OD p99 | 12.893 | **12.809** | ⭐ |
| **THD (OD) level term** | 3.065 ⚠ over | **2.986 ✅ SHIP** | ⛔ **NOT a model improvement — see below** |
| CLEAN, all four rows | 0.453 | **0.453** | ✅ bit-identical (n12 CLEAN rows were never excluded) |
| rows over SHIP | 7 | **7** | the composition changed, the count did not |

⚠⚠ **THE RECORDED COST WAS WRONG BY 3×, AND THE REASON IS A MEMBERSHIP CHANGE INSIDE THE ESTIMATE
ITSELF.** Session 106 measured "+0.020 dB, n 320 → 336" on the **s109** report. Session 110 added a
re-captured `drive-1700_level-1700_grunt-boost_gain-n12` twin, so the group is **20 rows, not 16** —
and that twin is by far the worst of it (per-row band-RMS **3.41 / 4.29 / 4.90 / 8.95** against a
group mean of 3.33). ⇒ **+0.062 dB, n 322 → 342.** `aggregate-moved-check-membership-first`, this
time inside a *cost estimate* carried forward across a baseline change.

⭐ **IN ITS FAVOUR, and this is not bookkeeping:** that same twin is the **only healthy capture of
DRIVE max × LEVEL max × GRUNT boost at the `drv_-12` rung** — both full-send captures of that
condition are reference dropouts there (s110) — so retiring the exclusion **restores coverage the
dropout exclusion had removed.** The condition is the hardest in the matrix and it now has a graded
row again.

⛔⛔ **DO NOT BOOK THE THD ROW'S NEW `SHIP` AS PROGRESS. IT IS A TWO-POPULATION MIXTURE.** The gated
term is `abs(c[0])/sqrt(n)` RMS'd over rows — an UNSIGNED magnitude — and the two populations now
pooled have **opposite signs**:

| | n | rms | **SIGNED mean** |
|---|---|---|---|
| OD (gated, s111) | 244 | **2.986** | +1.279 |
| ex `gain-n12` (pre-s111) | 229 | 3.065 | **+1.414** (model over-distorts) |
| `gain-n12` only | 15 | 1.286 | **−0.772** (model UNDER-distorts) |

⇒ an rms over the union is **smaller than either population's own error**, so the row met its bar
for a membership reason. `release_gate.py` now prints this three-way split under the THD row on every
run, so the mixture cannot be misread. ⚠ **Whether that row should keep pooling two operating points
is the same class of question as the session-96 CLEAN split, and is NOT taken here.**

⭐⭐⭐ **AND THE MIXTURE IS ITSELF THE SESSION'S REAL FINDING: THESE ROWS ARE THE ONLY ONES IN THE
MATRIX AT A SECOND OPERATING POINT, SO THEY ARE THE ONLY ROWS THAT CAN SEE THE *SLOPE* OF THE
DISTORTION-VS-INPUT LAW — WHICH IS EXACTLY THE AXIS THE HEAD ITEM NEEDS.** Paired against their own
full-send twins (identical settings, send 12.071 dB apart, so every nuisance cancels — no fit, no
anchor):

**dropping the send moves the model's signed THD level term by −1.106 dB mean / −1.039 median,
11 of 14 pairs same-signed.**

⇒ **the model's distortion rises with input level FASTER than the reference's** — too little at low
input, too much at high input. That is GATE Q's "the OD path saturates too early" measured on an
**independent axis**: GATE Q varies the sweep's own level, this varies the *interface send*, and the
two share no machinery. ⚠ **Quote the SIGN, not the size** — per-pair scatter runs −3.1 … +2.4 dB and
GATE N's own send calibration carries up to 0.66 dB of error on one pair (s110 R8's lesson applied).
⚠ **MEASURED, NOT GATED** — same status as session 106's MASTER finding; do not quote as fact.

⚠ **WHAT GATE N DOES NOT CERTIFY, restated because retiring an exclusion is where an overclaim goes
unchallenged:** it certifies the CURRENT files (the defective ones were overwritten by the
re-capture, so it is **not** evidence session 48 was wrong) and it certifies them on a **nonlinear**
statistic. On the absolute/linear axis GATE O5 bounds the residual provenance offset at a **0.334 dB
span** — a *tilt*, which the per-row gain match does not remove — and that residue is the
**reference's** (our model side is a pure 12.0710 dB shift to 1.8e-08). **These rows are cheap, not
clean**, and the FR movement above is consistent with that.

⭐ **`analysis/a3_balance_gate.py` (GATE M) STILL EXCLUDES ITS `gain-n12` PAIR — BUT THE
JUSTIFICATION IS CORRECTED IN PLACE, NOT LEFT TO MISLEAD.** It excluded it as "the session-48 capture
defect"; that premise is retired. The exclusion survives on **session 108's P4** instead — do not
pool over an operating point the pedal itself sets, and that pair sits 12.071 dB down the compression
curve from the other four. M3 keeps printing the headline both ways, and re-including it would
**shrink** A3 (5.05 → 4.85 dB at `drv_-6`), so nothing there is chosen to flatter it. **A3's size is
untouched: 5.1–5.5 dB over 100–400 Hz.**

⛔⛔ **AND A PRE-EXISTING FAILURE FOUND WHILE RE-RUNNING THE GATES, WHICH IS NOT MINE AND IS NOT
SMALL: GATE I FAILS ON THE SHIPPED BASELINE, AND IT HAS DONE SINCE SESSION 109.** `hf_artefact_gate`
exits non-zero on `s110_baseline.json`. Bisected across four reports, with the s111 membership change
shown inert (s110 fails identically under `--ex-gain-n12`):

| report | rc | model rate span | worst \|model − (−18.25)\| |
|---|---|---|---|
| s91_shipped | 1 | 16.0 dB/oct | 14.6 |
| **s99_attack_cand** *(the report GATE I was written against)* | **0** | 8.4 | 4.8 |
| **s109_k090_cand** | **1** | **9.4** | **7.9** |
| **s110_baseline** | **1** | **9.4** | **7.9** |

⇒ **session 109's `kInputRef` change broke it and session 109 never re-ran it** (s110 is identical, so
the new captures and the dropout exclusion contribute nothing). The mechanism is coherent: K moves
every nonlinear operating point at once, so the MODEL's own HF rolloff rate stopped being a single
filter rate and now spans 9.4 dB/oct with drive — which is the very property G2 uses to argue the
pedal's HF excess cannot be a filter. ⭐ **The load-bearing directional claim SURVIVES**: G2c is still
OK (the pedal's OD path GAINS with frequency at the hottest stimulus, **+3.5 dB/oct**, where ours
runs −20.5), and the pedal's span is still ~2× ours. ⛔ **What falls is GATE I's two quantitative
guards, so "the HF region is ND's artefact" must now be quoted from G2c and the table, not from a
passing gate.** Nothing was changed — this is a threshold/re-scoping question and it is flagged, not
patched.

⛔⛔ **SUPERSEDED BY SESSION 114 — THIS DIAGNOSIS IS REFUTED AND MUST NOT BE CARRIED FORWARD. THE
MODEL NEVER BROKE GATE I; THE GUARD DID.** The rebuilt gate passes on **s91, s99, s109, s110, s112
AND s113** — i.e. on every report in the table above, including the two this block reads as
"session 109 broke it". The bisection was sound arithmetic on an unsound statistic: G2a required the
**whole OD path** to hold the rate of **two of its elements** (the Sallen-Keys' −18.25 dB/oct), and
the path also contains the treble/ATTACK ladder, C7, C10, C14 and the recovery bridged-T — with
**ATTACK literally an HF control** (C8 220 pF). Measured, the model's rate spans **18.9 dB/oct within
a single cell** across ATTACK and GRUNT, so "does the model hold ONE rate?" was never a question this
path could answer. ⇒ **"the HF region is ND's artefact" is quotable from a PASSING GATE again.** See
the SESSION 114 block for what replaced the two guards and for the three membership defects fixed
alongside them.

⭐ **Every other gate re-run PASSES on the new membership**: GATE Q (rc 0), GATE M (rc 0), GATE R
(rc 0), GATE J (rc 0), plus `matrix_grade` and `shape_gate`. `release_gate` exits 1 for the expected
reason, **7 rows over SHIP**.

▶ **NEXT — unchanged from session 110's list except that item 5 is now DONE.** The head item is still
**"a null whose depth grows with level", at DRIVE MAX** (s110 R8), and item 2 (**characterise before
fitting**) is now better resourced than it was: the `gain-n12` twins give a **second operating point
on the interface-send axis**, which is exactly the "measure the level-dependence across the
drive/stimulus plane" that item asks for, and it costs no captures. ⚠ Two new items: **(a) GATE I's
guards need re-scoping or the model's own drive-dependent HF rate needs explaining** — it is a
session-109 consequence nobody priced; **(b) whether the THD gate row should keep pooling two
operating points** is a user decision of the session-96 class.

---

⭐⭐⭐ **SESSION 112 — THE BASELINE IS RE-RENDERED ONTO ALL 153 CAPTURES (`analysis/reports/s112_baseline.json`),
AND THE HEADLINE "IMPROVEMENT" IS 100 % MEMBERSHIP. THE `gain-n12` SEND IS **12.000 dB, NOT 12.071**,
MEASURED TO 0.0003 dB ON TWO INSTRUMENTS — WHICH REFUTES GATE O5's ATTRIBUTION THAT ND's CLEAN PATH
IS NOT LEVEL-INVARIANT.** No DSP constant moved; `src/` and `tests/` are untouched.

⭐ **The re-render is PROVEN INERT, which is what makes everything below readable.** Restricted to the
127 captures s110 and s112 share, **every gated cell is byte-identical** (OD band-RMS 2.327, p99
12.809, 100 Hz–8 kHz median 0.531, CLEAN 0.250/0.742 — the s111 column to the digit). So the binary,
the cache, the args and the bands are all unchanged and s112 is a valid successor baseline.
⭐ **And it clears session 110's own blocker**: GATE R's epoch guard (R3b) now reports **0 captures
newer than the report**, where on s110 it exited non-zero by design. Every gate re-runs clean —
matrix_grade / shape_gate / GATE J / K / M / N / O / P / Q / R all rc=0. **GATE I still fails**, for
the pre-existing session-109 `kInputRef` reason session 111 bisected; it is not new and not mine.

⛔⛔ **THE HEADLINE MOVED THE FLATTERING WAY AND IT IS NOT THE MODEL.** Full s112 (153 captures) reads
OD band-RMS **2.154** and OD 100 Hz–8 kHz median **0.469 = STRETCH** — i.e. the one OD row session 111
re-opened appears to close again. It does not. Decomposed:

| group | caps | rows | band-RMS |
|---|---|---|---|
| shared 127 (= the s110/s111 set) | 127 | 344 | **2.432** |
| **NEW level × blend** | 12 | 48 | **0.798** ⬅ dilutes |
| NEW drive ladder `gain-n12` | 5 | 20 | 2.456 (neutral) |
| full s112 | 153 | 412 | 2.243 |

⇒ the 12 new captures sit at **intermediate BLEND**, where the clean bleed dilutes the OD path's
error, and they pull the pooled number down on their own. `aggregate-moved-check-membership-first`,
**ninth occurrence**, in its most flattering form yet — a gate row appearing to close.

✅ **DECIDED WITH THE USER, SESSION 112: GRADE THEM, AND PRINT THE BLEND COMPOSITION ON EVERY RUN.**
Excluding valid data to protect a bar is backwards; the fix is to make the pool's composition
impossible to miss. New `release_gate.blend_composition()`, printed under the membership block:

| BLEND | captures | rows | band-RMS |
|---|---|---|---|
| 0.00 | 4 | 16 | 0.225 |
| 0.25 | 15 | 60 | 0.318 |
| 0.50 | 15 | 60 | 0.561 |
| 0.75 | 15 | 60 | 1.300 |
| **1.00** | **54** | **214** | **3.499** |
| pooled | 103 | 410 | **2.154** |

⭐ It independently reproduces GATE J's recorded **15.6× BLEND span** through a different code path.
⇒ **the OD headline is a weighted average whose weights are nothing but the capture inventory** —
session 108's P4 rule (do not pool over an operating point the pedal itself sets) applied to the
headline gate rather than to a one-off instrument. ⚠ Guarded: the table must account for **every**
graded OD row or the gate exits (a partial table would under-report exactly the bucket whose
settings failed to parse — the flattering direction). Mutation-tested: dropping one capture's
`blend` makes it exit with "covers 406 of 410"; the unmutated control passes. ⚠ The first mutation
attempt was **vacuous** — it selected on `settings['base']`, a key the stored settings do not carry,
so it matched nothing and the guard "failed to fire". s110's lesson applied: suspect the mutation
before the guard.

⭐⭐⭐ **THE SEND PAD IS 12.000 dB, AND THE HARNESS'S 12.071 CAME FROM THE ONE PAIR THAT MISBEHAVES.**
`captures.py`'s `_GAIN_SESSION_MEASURED_DB = {-12: -12.071}` is annotated "measured 2026-07-22 …
ref-clean.wav vs ref-clean_gain-n12.wav" — a **single cross-session pair**. Session 111's batch added
four fresh clean twins, and the clean path is LINEAR, so old−new must be flat *and* equal to the send:

| twin (full-send vs `gain-n12`) | pad dB | span over 29 bands |
|---|---|---|
| `bass-0700` | **12.000** | **0.0003** |
| `treble-0700` | **12.000** | **0.0002** |
| `lomid-0700` | **12.000** | **0.0001** |
| `himid-0700` | **12.000** | **0.0001** |
| *`ref-clean` (the constant's own source)* | *12.158* | ***0.3343*** |

⭐ **Corroborated on a second instrument sharing no machinery** — GATE N's THD turnover (nonlinear,
immune to any record or output gain) returns **12.000 / 12.000 / 12.001** on the three new
full-send-twinned DRIVE pairs.
⛔⛔ **CONSEQUENCE: GATE O5's ATTRIBUTION IS REFUTED.** O5 recorded the `ref-clean` pair's 0.334 dB
tilt as *"ND's own clean path failing to be level-invariant across a 12 dB input change (it scales by
12.178, not 12.071)"*. Four independent pairs say ND's clean path **is** level-invariant to
**0.0003 dB**. The tilt is a property of **that pair**, not of the device. ⚠ What survives untouched
is O5's *model-side* known answer (our render is a pure 12.0710 dB shift to 1.8e−08) and the
*practice* of correcting per band. What falls is whose residue it is. ⚠ **NOT changed this session**:
the constant is used to pad the MODEL, and `comprehensive_report` gain-matches every row, so a
0.071 dB pure gain is **removed by the gain match** and the matrix is blind to it — but GATE K/M/O/Q's
absolute ledgers are not. Fixing it is a small, well-founded change and it is **flagged, not taken**.

⛔ **AND THE MASTER LADDER IS STILL PROVENANCE-SPLIT — IT MOVED, IT DID NOT GO AWAY.** The four
full-send low detents the s110 baseline graded (`master-0700/0815/0930/1045_base-clean.wav`) are no
longer in `analysis/captures/`; they are in **`analysis/captures/_archive/`** (nothing lost), and
`gain-n12` twins replaced them. Measured — flat offset, sd **0.000** at every band, the pure-gain
signature GATE O6 requires — they are genuine re-captures, **not renames**. But:

| detent | old(full-send) − new(`gain-n12`) | vs the 12.071 pad |
|---|---|---|
| master-0700 | +12.000 | −0.07 |
| **master-0815** | **+10.455** | **−1.62** |
| master-0930 | +12.612 | +0.54 |
| master-1045 | +12.330 | +0.26 |

⇒ **the MASTER knob was re-set by hand between takes, and at the steep low end that costs ~1.55 dB.**
⚠ **NOT a session effect** — corrected in-session by the user and then checked: the rig is **reamped
identically** across sessions (four clean twins spanning 12 days read **12.000 dB flat to
0.0003 dB**), and the errors do not group by session anyway (07-21 gives 12.000 and 12.612; 07-29
gives 10.455 and 12.330). It is knob position on a steep taper.

⛔⛔ **AND THE MASTER LADDER'S REAL DEFECT WAS AT THE TOP, IN DATA THAT PREDATES THIS SESSION:
`master-1545_gain-n12` AND `master-1700_gain-n12` CARRY THE SAME SIGNAL.** Both peak at exactly
**0.98850 (−0.10 dBFS)**; both read **+14.053 dB re noon, step +0.000**; the two files differ by
**1.5e−04 (−76 dBFS)**. Two takes of one output, not two detents ⇒ **the n12 ladder had no
resolution above `master-1430`** — a full-send ladder is impossible (it clips — which is why
`gain-n12` exists), and even n12 clips at the top two.

✅✅ **RESOLVED IN THIS SESSION with two fresh `gain-n18` captures, and it took a second wrong turn to
get there** — the first replacement candidate (an archived `master-1700_gain-n18`, peak −8.90 dBFS)
looked like it confirmed the escape from the ceiling (**+15.5 dB**, above the pinned +14.053) and was
nearly accepted on that alone. It was itself contaminated (an 11 dB, ±5 dB-ripple non-flat "gain
difference" against a genuinely clean capture — impossible for MASTER's asserted pure-gain topology,
GATE O6), sharing whatever broke the already-known-bad archived `ref-clean_gain-n18` (12.3 dB span)
from the same session. Two properly cross-validated fresh captures gave the real ladder top:
**master-1545 = +16.480 dB, master-1700 = +18.500 dB re noon**, monotone, with the final step
decelerating (+2.02 dB) exactly as an A-taper approaching full CW should. Full derivation and both
consistency checks in "Capture access status" below, and in `.claude/rules/measurement-discipline.md`
(the entry on a saturated capture reading as a flat law, and its follow-on about validating the
escape check's own data).

⭐ **TAKE-TO-TAKE, MEASURED — AND IT IS NOT THE SAME QUANTITY AS THE ABOVE.** GATE N's new twin
resolution exposed that `drive-1200_gain-n12_base-od.wav` and `ref-od_gain-n12.wav` are the **same
condition captured twice**, four days apart (settings dicts identical). Difference: **+0.010 dB mean,
sd 0.000–0.004, worst band 0.026 dB** across all four sweeps. ⇒ the RECORDING side is essentially
deterministic, ~14× better than the "0.144 dB take-to-take floor" quoted for ~40 sessions
(`reference-sources.md` §0 already demoted that figure; this measures it). ⛔ **It does NOT bound
knob repositioning** — both captures are the matrix default, so nothing was necessarily re-dialled.
**Recording repeatability 0.010 dB and re-dialling repeatability ≤1.6 dB are two different numbers;
do not quote one for the other.**

⚠⚠ **TWO GATES FALSE-FAILED ON THE NEW DATA, BOTH FROM THE SAME ROOT CAUSE, AND BOTH ARE FIXED:
IDENTITY WAS BEING RESOLVED BY FILENAME.**
**(1) GATE N1** hard-exited on `drive-1200_gain-n12_base-od.wav` "has no normal-gain twin". It has
one — **`ref-od.wav`** — because DRIVE noon *is* the reference baseline, so one condition has two
legitimate names and a name transform can only ever see one. `gain_session_gate.find_twin()` now
tries the name transform **first** (so every pre-s112 pairing resolves identically and old quotes
stay reproducible) and falls back to matching **settings** apart from `gainSessionDb`; an ambiguous
match is a hard failure, never a pick-the-first. ⭐ GATE N now runs on **10 pairs, was 4**, and all 10
read HEALED.
**(2) GATE O2** hard-exited on "two captures at master=0.5" — the new `master-1200_gain-n12` collides
with `ROUTE_A` (`ref-clean.wav`) at noon, at a *different send*. The duplicate check was right to
fire (it is session 104's L2 lesson) but the two are not the same capture. `master_ladder()` now
dedupes per detent, **refuses only when the duplicate is at the SAME send**, and prints every
discarded alternative. ⛔ **Which capture serves noon is a real choice and it re-bases the ledger**, so
it is a named constant, `PREFER_FULL_SEND_NOON = True` — pre-s112 behaviour exactly — with the
trade-off documented at the constant. **Acceptance check: GATE O returns bit-identical numbers on
s110 and s112** (clean bound **0.407**, OD deficit **4.396**), so the change is inert and A3's ledger
is untouched by the 26 new captures.

⭐ **GATE R's headline is unchanged on the new baseline**: MODEL wash-out **+1.54 → +6.63 → +9.83**,
monotone in DRIVE; PEDAL **+5.61 → +4.69 → −7.38**, reversing only at DRIVE max. The head item's
target is intact and now sits on a report nothing is newer than.

⭐⭐ **AND THE 12 NEW `level × blend` CAPTURES DO *NOT* DECORRELATE LEVEL FROM BLEED — BUT THEY DO
SUPPLY WHAT GATE K6 ACTUALLY ASKED FOR.** Computing the clean fraction from the shipped stage's own
closed form over the new 4 × 3 grid (LEVEL {0.25, 0.5, 0.75, 1.0} × BLEND {0.25, 0.5, 0.75}):
r(LEVEL, clean fraction) = **−0.920 within the grid, −0.863 over all 105 OD captures** (GATE K6
recorded −0.961 at blend-max). ⇒ **a regression on the pooled set still cannot separate them.** What
the grid *does* give is **matched-bleed pairs at different LEVEL**, which is the design K6 said the
matrix lacked — e.g. clean fraction **0.4286 (L=1.00, B=0.25) vs 0.4375 (L=0.75, B=0.75)**, and
**0.8462 (L=0.50, B=0.25) vs 0.8333 (L=0.25, B=0.75)**. ⚠ **Two tight pairs is a matched-pair
instrument, not a decorrelated design** — build it as pairs, and do not quote the correlation as
having improved, because it has not.

▶ **NEXT, in order.**
1. ⭐⭐ **Unchanged head item: "a null whose depth grows with level", at DRIVE MAX** (s110 R8), with
   item 2 (**characterise before fitting**) still the required first step. ⭐ It is now much better
   resourced: the new DRIVE ladder at `gain-n12` gives a **second operating point at all five DRIVE
   settings**, and the twin transfer is already suggestive — a 12.000 dB input drop produces
   **11.99 / 12.02 / … / 9.33 / 7.27 dB** of output drop as DRIVE goes min → max, i.e. **4.73 dB of
   compression at DRIVE max, measured with no fit, no gain match and no model.** Build the model side
   of that and it is the compression law on an axis GATE Q does not share. ⚠ MEASURED, NOT GATED.
2. ⭐ **Build the matched-bleed LEVEL instrument** from the two tight pairs above — GATE K6's refused
   verdict is now answerable. ⛔ Not by regression on the grid; the collinearity is untouched.
3. ⚠ **The send-pad constant: 12.071 → 12.000, per session.** Well-founded (0.0003 dB on four linear
   pairs, corroborated by GATE N's turnover) and invisible to the matrix by construction, but it
   moves GATE K/M/O/Q's absolute ledgers. Not taken unilaterally.
4. ⚠ **GATE I's guards need re-scoping** — pre-existing since s109, unchanged. And **whether the THD
   gate row should keep pooling two operating points** is still an open user decision (s111).
5. **MASTER taper → Phase 10 C**, and take `PREFER_FULL_SEND_NOON` there with the fresh ladder.
6. ⚠ Unclaimed: ND's DIST-engage at BLEND min is not transparent (O7). ⛔ Its sibling — "ND's clean
   path is not level-invariant" (O5) — is **REFUTED**, see above; do not carry it forward.
⚠ **Quote every number against `s112_baseline.json` from here**, and never diff a pre-s112 OD figure
against it without saying whether the blend composition or the model is responsible.
⚠⚠ **SUPERSEDED BY `s113_baseline.json` (162 captures) — AND ITS OD/THD HEADLINE MOVED BY
MEMBERSHIP, NOT MODEL, EXACTLY AS THIS PARAGRAPH WARNS.** See the SESSION 113 block below and the
"Capture access status" carry-forward: 9 new captures landed, the THD level row crossed to SHIP on
dilution from 8 of them, and the requested capture alone barely moved anything. **Do not quote the
`s113_baseline.json` THD row as progress without reading that decomposition first.**

---

⭐⭐⭐ **SESSION 113 — THE COMPRESSION LAW IS BUILT ON THE SEND AXIS, AND THE FIRST THING IT MEASURES
IS THAT *TWO OF THE FIVE DRIVE-LADDER TWINS ARE NOT THE SAME CONDITION*. THE HEAD ITEM'S OWN CELL
TURNS OUT TO BE UNTESTABLE HERE — REPORTED AS UNTESTED, NOT AS REFUTED.**
`analysis/compression_law_gate.py` (**GATE S**, 8 computed sub-gates, exits non-zero, **no render** —
a re-read of `s112_baseline.json`, the current baseline, plus `captures.gain_correction_db`). It
**imports** `level_law_gate` (K), `gain_session_gate` (N), `od_absolute_gate` (Q) and through them
`matrix_grade`, so the absolute reconstruction, the twin resolution, the stimulus map and the
dropout detection cannot drift.

⭐ **This is session 110's item 2 — "characterise before fitting" — being spent, on the resource
session 112 created and did not use.** GATE Q varies the *sweep's own level within one recording*;
GATE S varies the **interface SEND between two recordings of one condition**, so the two share no
stimulus, no anchor and no arithmetic. Each side is differenced against ITSELF across the send
change, so MASTER, the EQ, the makeup and the record gain cancel exactly — **no fit, no gain match,
no free parameter anywhere.**

⭐⭐⭐ **THE FINDING THAT RE-SCOPES EVERYTHING BELOW IT — THE LADDER INTERLOCK (S3).** The stimulus
rungs are 12 dB apart and the send is 12 dB, so an n12 capture at `drv_-6` and its full-send twin at
`drv_-18` put the **same absolute level into the same device**: their outputs must agree *however
nonlinear the path is*. No linearity is assumed, which is why this reaches the OD path where a
clean-path argument cannot. Pedal side, worst |residual| per pair:

| pair | residual dB | |
|---|---|---|
| `drive-1200_gain-n12` (DRIVE noon) | **0.00000** | MATCHED |
| `drive-0700_gain-n12` (DRIVE min) | **0.00000** | MATCHED |
| `drive-1700_gain-n12` (DRIVE max) | **0.00002** | MATCHED |
| `level-1700_gain-n12` | 0.00900 | MATCHED (within the floor) |
| `ref-od_gain-n12` | 0.00909 | MATCHED (within the floor) |
| `drive-0930_gain-n12` (DRIVE 0.25) | **0.06576** | ⛔ MIS-DIALLED |
| `drive-1430_gain-n12` (DRIVE 0.75) | **0.32172** | ⛔ MIS-DIALLED |
| `level-1430_gain-n12` | 0.42206 | ⛔ MIS-DIALLED |
| `level-0930_gain-n12` | 1.16744 | ⛔ MIS-DIALLED |
| **`drive-1700_level-1700_grunt-boost_gain-n12`** | **2.08371** | ⛔ MIS-DIALLED |
| `level-0700_gain-n12` | — | SILENT one side (GATE L7's mute), not classifiable |

⇒ **the knob reproduced EXACTLY where the pot has a mechanical reference — both hard stops and the
centre detent — and NOT at the intermediate clock positions.** That is session 112's "re-dialling
repeatability ≤1.6 dB" **localised to the settings it actually hits**, measured with no model
involved. ⛔ A mis-dialled pair's `out(F) − out(N)` mixes the send step with a *knob* step and no
averaging removes it, so those cells are printed everywhere and vote nowhere (s40).
⚠ **The bar is a MEASURED FLOOR, not a chosen number**: S1b compares the two takes of DRIVE noon
(`drive-1200_gain-n12` vs `ref-od_gain-n12`, which is the duplicate detent the ladder contains) and
gets **0.0099 dB** of recording repeatability — reproducing s112's 0.010 dB through a different code
path — and anything at or below that is indistinguishable from re-recording the same thing.

⭐⭐ **AND THE MODEL SIDE OF THE SAME INTERLOCK IS A KNOWN ANSWER WITH NO FREE PARAMETER.** The
harness pads the model by 12.071 while the ladder step is 12.000, so the model's n12 rung sits
0.071 dB quieter than its twin's lower rung and at DRIVE min (slope 1) the residual **must** be
**−0.0710**. Measured **−0.0705 / −0.0640, worst error 0.0070 dB.** One subtraction simultaneously
certifies the absolute reconstruction, the rung mapping, the harness pad, and s112's 12.000 dB send
— on a **third** instrument.

⭐⭐ **S2 RE-DERIVES SESSION 112's `ref-clean` CONTAMINATION FROM PHYSICS RATHER THAN FROM A NAME,
AND LOCALISES IT ONE STEP FURTHER.** The admissibility criterion is **flatness**: the clean path is
linear, so full-minus-n12 is a pure gain and is *forbidden* to have frequency structure (GATE O6's
argument). Four EQ pairs read **12.0000 dB with span 0.0000**; the two pairs that read 12.1776 with
span 0.1399 are rejected **by that measurement**, and both share the same full-send member ⇒ **the
contamination is in `ref-clean.wav` itself**, not in "that pair". s112 said which pair; this says
which file. ⭐ Because the criterion is physics, it would catch a NEW contaminated pair too.

⭐⭐⭐ **THE LAW (S4), matched detents only.** `slope` = dOut/dIn over the send step (1.000 = linear):

| DRIVE | stimulus | slope MODEL | slope PEDAL | comp M | comp Q | **M−Q** |
|---|---|---|---|---|---|---|
| 0.00 | clean | 0.998 ±0.004 | 0.999 ±0.004 | 0.025 | 0.015 | +0.009 |
| 0.00 | drv_−6 | 0.950 ±0.188 | 0.932 ±0.174 | 0.605 | 0.820 | **−0.214** |
| 0.50 | clean | 0.956 ±0.069 | 0.969 ±0.044 | 0.534 | 0.375 | +0.159 |
| 0.50 | drv_−6 | 0.913 ±0.222 | 0.844 ±0.260 | 1.046 | 1.870 | **−0.825** |
| 1.00 | clean | 0.639 ±0.418 | 0.598 ±0.396 | 4.352 | 4.830 | −0.478 |
| 1.00 | drv_−6 | 0.686 ±0.314 | 0.511 ±0.356 | 3.786 | 5.871 | **−2.086** |

⇒ **the model UNDER-compresses on this axis and the deficit grows monotonically with DRIVE**, to
−2.09 dB at DRIVE max. Both sides' compression is monotone in DRIVE (a free validity check that
breaks loudly on a mis-paired twin). ⚠ **The across-band spreads are as large as the means** (±0.3–0.4
on slope at high drive) — this is a mean over a curve, and S5 says so explicitly: shape/offset runs
**1.49–4.42 on every matched cell** against GATE K5's own 0.25 bar ⇒ **the compression error is NOT
a level error and no single compression constant can carry it.** Same answer GATE P gave for A3, on
a different defect.
⚠ **The step-mismatch is bounded, not waved away**: the two sides' input steps differ by 0.071 dB
and the deepest slope is 0.438, so ≤ **0.0399 dB** of any cell is the mismatch — **52× smaller** than
the largest effect. Gated: the gate refuses if that ratio ever falls below 2.

⛔⛔ **AND THE ONE THAT INVALIDATES DIRECT COMPARISON WITH GATE Q: THE DRIVE LADDER IS NOT
BLEED-FREE, AND THE BLEED IS FAR BIGGER THAN ANYONE HAS PRICED.** Every ladder capture sits at LEVEL
noon / BLEND max. Evaluating the **shipped** `LevelBlend` closed form (GATE K2, imported) **with the
LEVEL taper applied**, the output there is **44.1 % clean signal**. The clean tap is a unity buffer
to the BLEND pin and does not compress, so it dilutes the law:

| DRIVE noon, drv_−6 | compression (pedal) |
|---|---|
| bleed-free (`level-1700`, K2 coefficient exactly 0) | **6.662 dB** |
| the ladder's own LEVEL noon | **1.870 dB** |

⇒ **3.6×.** S4's table is the **mixed output's** law, not the OD path's. ⛔ Do not diff a GATE S
ladder cell against GATE Q (which uses the 15 bleed-free endpoints) without saying which mix each
was measured at. ⭐ At the one matched bleed-free cell available, DRIVE noon, the model sits within
**+0.17 dB** of the pedal at the hottest stimulus.

⛔⛔⛔ **THE HEAD ITEM'S OWN CELL IS NOW MEASURED, ON THE CAPTURE THE USER TOOK AT SESSION 113's
REQUEST — AND ON THE SEND AXIS THE REVERSAL DOES NOT REPRODUCE.** S7 measures the 320 Hz null's
prominence (referred to its own 202/508 Hz shoulders, **named**, so a candidate that moves the null
cannot re-point the statistic — GATE R4's trap) at both sends. GATE R's finding is bleed-free at
DRIVE max; the clean tap carries **no** 320 Hz null (GATE R2 puts it in the pre-clipper treble
ladder, OD-path only), so any bleed **fills** exactly the feature under test — which is why the
grunt-boost twin (interlock 2.08 dB, condition-mismatched, full-send member the s110 dropout)
could not serve, and why `drive-1700_level-1700_gain-n12_base-od.wav` was the one capture worth
asking for: bleed-free by K2's exact zero, matched (interlock 0.00009 dB), DRIVE max.

| axis | condition | MODEL d | PEDAL d |
|---|---|---|---|
| GATE R (sweep-level, within one recording) | bleed-free, DRIVE max | washes out | **DEEPENS** |
| **GATE S (send, between two recordings)** | bleed-free, DRIVE max | **washes out (−4.06)** | **washes out (−0.19)** |

⇒ **NOT corroborated.** Both sides move the same way on the send axis — the model washes out hard,
the pedal is essentially flat (−0.19, barely a wash-out, nowhere near GATE R's deepening). ⚠ **n = 1
pair — this LOCATES the answer, it does not settle it** (the same caveat s110 R8 stated about its
own n = 5). Read together with the DRIVE-noon bleed-free row (model −1.36, pedal −0.66, both wash
out, matching GATE R's own DRIVE-0.5 finding) the send axis is **consistent with "the pedal's null
just doesn't deepen much on this axis"**, not with GATE R's reversal. The bled control at DRIVE max
(model −2.67, pedal −1.55, also both wash out) must **not** be quoted against GATE R either — 44 %
clean fill flattens exactly this statistic regardless of what the OD path does.
⇒ **the reversal GATE R found is either specific to the sweep-level axis (a property of how a
single recording's level changes, not of the device), or it needs more than one send-axis point to
see.** Either way, "a null whose depth grows with level" is no longer a clean target for a
static correction — the one instrument built to corroborate it on an independent axis did not.

⚠⚠ **THREE DEFECTS IN SESSION 113's OWN GATE, ALL CAUGHT, AND THE FIRST TWO PRINTED PLAUSIBLE WRONG
NUMBERS.**
**(1) The admissibility bar was a GAP-HUNT, which is not a bimodality test.** The first S3 took the
largest ratio between adjacent sorted residuals and required ≥ 20×. **Any** population with one big
step satisfies that, and it duly split at 0.00002/0.00900 and classified a **0.009 dB** pair as
mis-dialled — *below* the take-to-take floor the same gate had already measured at 0.0099. Fixed by
taking the bar from a quantity measured **independently of the thing being classified**.
**(2) A SHIPPED STAGE'S CLOSED FORM TAKES THE STAGE'S INPUT, NOT THE UI's.** `coef_closed` expects
the **tapered** level; capture settings store the **knob**. Passing the knob gave clean/OD = −6.02 dB
at LEVEL noon where the shipped stage delivers **−2.05** (GATE K2's own recorded table), i.e. every
clean fraction was wrong. Caught only by diffing against K2's table. The taper exponent is now read
via `level_law_gate`, which validates it against `FitParams.h`.
**(3) S6 was first framed as "out of sample MUST reproduce the ladder".** That premise is wrong: a
capture at a different LEVEL is at a different MIX, so a departure is the **dilution being
measured**, not a failure — and scoring it as one would have reported the bleed as a model defect.

⭐ **All 9 guards were mutation-tested with an unmutated control** (`analysis/_mutate_gate_s.py`);
the control passes and all 9 mutations exit non-zero with their own messages. The runner asserts
each mutation's needle is present **exactly once** — a vacuous mutation is reported as vacuous
rather than as a dead guard (s110's lesson).

⭐ **Gate sweep re-run TWICE — once on `s112_baseline.json` before the capture landed, once on
`s113_baseline.json` (162 captures) after**: `matrix_grade`, `shape_gate`, GATE J, K, L, M, N, O, P,
Q, R all **rc=0** on both. **GATE I still fails** for the pre-existing session-109 `kInputRef`
reason session 111 bisected. GATE R's epoch guard (R3b) reports clean on `s113_baseline.json` — the
new captures are not newer than the report that grades them. GATE S touches no shared module — it
is purely additive — so nothing in that list moved *because of GATE S*.
⚠⚠ **`release_gate` still exits 1, but the row composition CHANGED — read this before quoting
either report.** On `s112_baseline.json`, restricted to its own 153 captures, 7 rows are over SHIP.
On the full `s113_baseline.json` the THD level term crosses to SHIP (**6 rows over**) — but that is
**dilution from the 8 unrelated hedge captures**, confirmed by the shared-membership acceptance
check (see the "Capture access status" block): byte-identical on the shared 153, and the 8 hedge
captures' own OD rows average band-RMS 1.778 against the population's 2.243. **Do not book the THD
row's SHIP as progress.**

▶ **NEXT, in order.**
1. ✅ **DONE, SESSION 113 — the head item's own cell is measured (see the block above) and the
   reversal does NOT corroborate on the send axis.** `drive-1700_level-1700_gain-n12_base-od.wav`
   landed, matched (interlock 0.00009 dB), and is now in `s113_baseline.json`. ⚠ n = 1 pair — a
   second bleed-free DRIVE-max send-axis point (a different DRIVE/LEVEL cell, or a genuine repeat)
   would turn "locates" into "settles"; not requested this session on the strength of one point.
2. ✅ **DONE, SESSION 113 — the THD dilution IS just dilution, not a sign mixture, checked before
   the SHIP verdict was quoted anywhere.** Signed mean over the gated OD THD population:

   | | n | rms | signed mean |
   |---|---|---|---|
   | full `s113_baseline.json` | 322 | 2.975 | **+1.387** |
   | ex the 8 EQ hedge captures | 298 | 3.056 | +1.389 |
   | the 8 EQ hedge captures alone | 24 | 1.669 | +1.356 |

   ⇒ **unlike session 111's `gain-n12` split (opposite-signed populations averaging to a smaller
   number), this is same-signed all the way through** — the model over-distorts by essentially the
   same +1.35–1.39 dB in both the hedge captures and everywhere else. The hedge rows just have
   smaller absolute THD ERRORS (rms 1.669 vs 3.056), consistent with them being mild EQ
   perturbations rather than the matrix's extreme settings. ⛔ **The pooled rms crossing to SHIP is
   still not model progress** — it is the unsigned statistic being pulled down by lower-magnitude
   (not oppositely-signed) rows — but it is a more benign dilution than session 111's, and the
   underlying signed defect (the model over-distorts) is unchanged to two decimals.
3. ⭐ **GATE S's interlock is the acceptance test for ANY future twin-pair capture** — it costs
   nothing, needs no model, and would have caught every one of the five mis-dialled pairs at capture
   time. **Run it before that twin is used for anything.**
4. ⚠ **Re-scope the head item on what S5 says**: the compression error is shape-dominated
   (1.49–4.42 against a 0.25 bar) at every matched cell, so a single saturation constant cannot
   close it — the same verdict GATE P delivered for A3, now on the drive axis too.
5. ⚠ **The send-pad constant, 12.071 → 12.000** (s112 item 3) is now **triply** corroborated —
   four linear twins, GATE N's THD turnover, and GATE S's model-side interlock known answer. Still
   not taken unilaterally; it moves GATE K/M/O/Q's absolute ledgers and is invisible to the matrix.
6. ✅ **DONE, SESSION 114 — GATE I's guards are re-scoped and the gate PASSES on every report from
   s91 to s113.** The premise was wrong, not the threshold: G2a asked the whole OD path to hold the
   rate of two of its elements. ⛔ Session 111's "session 109's `kInputRef` broke GATE I" is
   **REFUTED** — see the SESSION 114 block. ⚠ The THD-row pooling question (s111) is still an open
   user decision.
7. **MASTER taper → Phase 10 C**, with `PREFER_FULL_SEND_NOON` and the fresh ladder.
⚠ **The two mis-dialled DRIVE detents are a property of the CAPTURES, not of the model** — they do
not affect the 162-capture matrix (which never differences two captures against each other), only
twin-pair instruments. Do not "fix" anything in `src/` on their account.

---

⭐⭐⭐ **SESSION 114 — GATE I NEVER FAILED BECAUSE OF THE MODEL. IT FAILED BECAUSE ITS OWN GUARD ASKED
THE OD PATH TO HOLD THE ROLLOFF RATE OF TWO OF ITS ELEMENTS, AND BECAUSE THREE CAPTURE BATCHES HAD
SILENTLY RE-POPULATED ITS CLASSES THROUGH A FILENAME SUBSTRING. THE REBUILT GATE PASSES ON EVERY
REPORT FROM s91 TO s113, AND ITS CONCLUSION GETS STRONGER, NOT WEAKER.** `analysis/hf_artefact_gate.py`
rewritten (**GATE I**, now 10 guards + a new asserted-membership G0, exits non-zero, **no render** —
a re-read of `s113_baseline.json` plus the capture wavs). **No DSP constant moved; `src/` and
`tests/` are untouched.**

⛔ **The standing item was "GATE I's guards need re-scoping — pre-existing since s109" (s111 item a,
carried by s112 and s113). Session 111's bisection is REFUTED, not merely refined.** It ran the real
gate across four reports and read the pattern correctly; what it could not see is that the statistic
was invalid on all of them. Rebuilt and re-bisected:

| report | model worst rate | pedal/model gap at drv_−6 | dose-response | rc |
|---|---|---|---|---|
| s91_shipped | −15.07 | **+17.49** | monotone | **0** |
| s99_attack_cand | −12.90 | **+15.23** | monotone | **0** |
| s109_k090_cand | −16.76 | **+17.44** | monotone | **0** |
| s110 / s112 / s113 | −16.76 | **+17.44** | monotone | **0** |

⇒ **the model never broke it.** Membership is identical (5 conditions per OD class) at every report
and the pedal side is bit-identical, as it must be — same captures.

⭐⭐ **WHY THE OLD GUARD COULD NOT HOLD, and it is a physics point, not a threshold one.** G2a
required `worst |model − (−18.25)| ≤ 6 dB/oct`, where −18.25 is the **two post-clipper Sallen-Keys**.
But the OD path also contains the **treble/ATTACK ladder, C7, C10, C14 and the recovery bridged-T**,
and **ATTACK is literally an HF control** (C8 220 pF bridging R8 or shunting node P). Measured, the
model's own rate spans **18.9 dB/oct WITHIN one cell** across ATTACK and GRUNT — e.g. at DRIVE max /
`drv_-12`: attack-cut **−36.6**, attack-flat −27.5, attack-boost **−17.7**. ⇒ *"does the model hold
ONE rate?"* is not a question this path can answer. ⛔ **This is NOT a bar that wanted loosening** —
the quantity it constrained is not required to hold, so it was deleted rather than widened.

⭐⭐⭐ **WHAT REPLACED IT NEEDS NO THRESHOLD AT ALL, AND IS STRICTLY HARDER THAN THE MEDIAN
COMPARISON IT SUPERSEDES.** The load-bearing property is that **no chain of fixed lowpass elements
can GAIN with frequency**, whatever its HF switches are set to:

| | new guard | measured (s113) |
|---|---|---|
| **G2a** | the model never gains, at any condition or stimulus | worst **−16.76** dB/oct over 60 cells ✅ |
| **G2b** | at drv_−6, *every* pedal condition gains and *every* model condition rolls off | pedal **[+0.68, +9.77]** vs model **[−32.24, −16.76]**, gap **+17.44**, **zero overlap** ✅ |
| **G2c** | the separation GROWS with stimulus (a drive-generated artefact must; a fixed filter difference cannot) | **−0.67 → +7.46 → +11.92 → +17.44**, monotone ✅ |

⭐ **G2b is a MIN-vs-MAX over all 15 conditions per side**, i.e. the strictest form of the
comparison — the repair does not buy its pass by weakening the test, which is the tell that this is a
correction and not a concession (the s95/s96 CLEAN-split lesson). ⭐ **G2c is a free dose-response
check with no parameter**, and the clean-stimulus cell *correctly* overlaps (−0.67): with the OD path
barely driven the pedal's excess has not appeared yet. That is the control, not a failure.

⛔⛔ **AND THE THREE MEMBERSHIP DEFECTS, EVERY ONE OF THEM ARRIVING WITH A CAPTURE BATCH WRITTEN
AFTER THE GATE, EVERY ONE INVISIBLE BECAUSE THE CLASSES WERE RESOLVED BY FILENAME SUBSTRING.**
`classify()` read `"level-1700" in fname` and called the result *"LEVEL max, where the clean bleed is
exactly ZERO by topology"*:

1. ⛔ **GATE K2 (s103) refuted that premise, and s112's captures walked straight into it.** Bleed
   vanishes only where **BOTH** BLEND and LEVEL are max. `level-1700_blend-0930/1200/1430` therefore
   joined the *bleed-free OD* classes carrying 25–75 % **clean** signal — and read a rate of
   **+0.53 / −1.36 / −8.25 dB/oct**, i.e. they ARE the clean path, sitting in the OD row.
2. ⛔ **`gain-n12` twins pooled with full-send captures** in the same rate cell — a second operating
   point 12 dB down the compression curve (s108 P4). 3 of them, incl. session 113's new capture.
3. ⛔ **`master-1100_grunt-boost` is a MODEL-SIDE DUPLICATE** of `grunt-boost`, double-weighting one
   condition — **exactly the trap s110 R7 found and fixed in GATE R, never propagated here.**

⭐ **And (3) turns into a free known answer rather than a discard:** MASTER is a post-EQ pure gain and
a *rate* is a contrast, so duplicates **must** agree — measured, they agree to **1.16e−07 dB/oct**
across the 9-capture MASTER ladder. The gate now **asserts** it (and refuses if they ever disagree,
which would mean `condition_key()` is missing a setting or circuit.md is wrong). That is the **fourth**
independent confirmation of circuit.md's pure-gain claim, after GATE O6, s110 R7 and s114's G0.

⚠ **G1 had the same root defect and its repair is the more embarrassing one: `ref-clean.wav` was
EXCLUDED while 36 EQ-swept captures were INCLUDED.** The class was `"base-clean" in fname`, which
misses `ref-clean.wav` entirely (no `base-clean` token) and admits the whole EQ ladder — **TREBLE at
full cut and full boost** — so "is our clean HF right?" was a median over a set whose spread is
**4.3 dB and is the EQ knob**. Selected properly (DIST-off **and** EQ-flat), the answer is unchanged
and now homogeneous: **worst 0.54 dB, invariance spread 0.000**.
⭐ **gain-session captures are admitted HERE and nowhere else, and the asymmetry is physical:** this
path is LINEAR (GATE O5 measured our side of a send change as a pure 12.0710 dB shift to 1.8e−08) and
G1's statistic is a contrast, so a send change cancels exactly. There is no "operating point" on a
path with no nonlinearity in it. ⚠ Note the residue: `ref-clean.wav` reads −0.50 where the nine
`gain-n12` EQ-flat captures all read **−0.57**, spread 0.000 — a 0.07 dB odd-one-out that is
**consistent with GATE S2's finding that `ref-clean.wav` is the contaminated member** of its own
twin pair. Corroboration from a statistic that shares nothing with S2; not chased.

⚠⚠ **TWO DEFECTS IN SESSION 114's OWN WORK, BOTH CAUGHT, AND THE FIRST IS A NEW TRAP.**
**(1) The dedup picked its representative ALPHABETICALLY and landed on the one capture whose model is
SILENT.** `master-0700_gain-n12_base-clean.wav` sorts first — and at MASTER min the **model mutes**
(max plugin **−640 dB**, GATE L7's finding on the second `[ENG]` divider). The silent-row guard then
dropped all four sweeps and **the entire condition vanished from G1, leaving n=1 with nothing
printed to say anything had been lost.** Which capture represents a condition is a real choice
(s112's `PREFER_FULL_SEND_NOON`); it is now made on **usable data**, not on filename order.
**(2) Two of the ten mutations were BACKWARDS** — they wrote `if False:` over a guard's predicate,
which *disables* it rather than making it fire, and duly reported two "GUARD DEAD" results against
two perfectly good guards. s110's rule applied: **suspect the mutation before the guard.** Replaced
with data-level mutations (make the class genuinely empty).

⭐ **All 10 guards mutation-tested with an unmutated CONTROL** (`analysis/_mutate_gate_i.py`): the
control passes and all 10 fire with their own messages, each needle asserted present exactly once so
a vacuous mutation reports as vacuous.

⭐ **Full gate sweep on `s113_baseline.json`: `matrix_grade`, `shape_gate`, GATE I, J, K, L, M, N, O,
P, Q, R, S all rc=0.** `release_gate` exits 1 for the expected reason — **6 rows over SHIP**, composition
unchanged. ⚠ **GATE I is no longer on the "still fails" list**, which it had been on since session 109.

---

⭐⭐⭐ **SESSION 114 (part 2) — BOTH OPEN USER DECISIONS TAKEN, ON THE USER'S "WHATEVER INCREASES
ACCURACY" CRITERION. THE SEND PAD IS CORRECTED TO 12.000 dB AND THE THD GATE ROW IS SPLIT BY
OPERATING POINT. NEW BASELINE: `analysis/reports/s114_baseline.json` (162 captures).**
No DSP constant moved; `src/` and `tests/` are still untouched.

⭐ **(1) `captures._GAIN_SESSION_MEASURED_DB[-12]` 12.071 → 12.000 dB.** The constant pads the MODEL
(`--input-trim`) so it sees what the pedal saw; at 12.071 the model was rendered **0.071 dB quieter
than the pedal was driven** on every gain-session capture. The old value came from ONE pair whose
full-send member is the contaminated file — and the paragraph justifying that choice is what convicts
it: the clean path is LINEAR, so full-minus-n12 is a pure gain and is *forbidden* to have frequency
structure, yet the `ref-clean` pair reads 12.158 dB with a **0.334 dB span**. Four fresh linear twins
read **12.000 ± 0.0003**; GATE N's THD turnover (nonlinear) returns 12.000/12.000/12.001; GATE S's
model-side interlock predicts −(pad − 12.000) with no free parameter.

⭐⭐ **ACCEPTANCE CHECK — THE CHANGE IS EXACTLY SCOPED, AND THAT IS THE LOAD-BEARING RESULT.**
Against `s113_baseline.json` on identical membership (162 both): **122 captures bit-identical on the
model side, 40 `gain-n12` moved, 0 non-n12 moved.** Median worst-band move across the 40 × 4 cells is
**0.0000 dB** — it is inert almost everywhere. The three outliers (2.27 / 1.42 / 1.31 dB) are all at
**DRIVE max × the hottest stimulus** in the HF/null region, i.e. exactly where a compressing chain
amplifies a small input change and where a cancellation null is level-sensitive (s110 GATE R). ⚠ A
32× amplification of a 0.071 dB input looks alarming and is not; it was checked rather than assumed.
⚠ **The matrix is blind to this by construction** (per-row gain match removes a pure gain) — the
headline moves 2.149 → 2.149. It is a correctness fix for GATE K/M/O/Q's **absolute** ledgers, which
are not gain-matched. **Re-quote any absolute figure on a `gain-n12` row against s114.**

⛔⛔ **(2) THE THD GATE ROW IS SPLIT BY OPERATING POINT — AND THE SPLIT COSTS A ROW, WHICH IS THE
POINT.** Measured on `s114_baseline.json`:

| population | rms | SIGNED mean | n | vs the 3.0 bar |
|---|---|---|---|---|
| pooled (what was gated) | **2.974** | +1.380 | 322 | SHIP |
| **full send** | **3.084** | **+1.534** | 289 | ⛔ **over** |
| **`gain-n12`** | **1.748** | **+0.032** | 33 | ✅ STRETCH |

⇒ **pooling flips the verdict on the population the 3.0 bar was agreed against** (session 89, when
`gain-n12` was excluded outright). ⭐ And the 1.5 dB disagreement is **signal, not noise**: GATE S
(s113) measured the model's distortion rising with input FASTER than the reference's, so 12 dB down
the send the model's excess distortion very nearly vanishes (+1.53 → +0.03). Averaging the two
destroys exactly the second-operating-point information that made those rows worth grading (s111).
⇒ **neither pooling nor excluding is the accurate move — splitting is**, and it is the session-96
CLEAN row split applied to THD: nothing is excluded, and the mixture stops hiding the defect.
⚠ **Both rows carry the SAME 3.0 bar deliberately** — it expresses how much THD level error is
acceptable, which is a property of the model, not of the send level. **No new threshold was
invented**; inventing one is how a split quietly becomes a concession.
⚠ **s111's "two OPPOSITE-signed populations" framing is STALE and is corrected in place**: at n=15 the
`gain-n12` group read −0.772, at s114 it is n=33 and reads **+0.032** — near zero, not negative. The
split stands on the *disagreement* and the *flipped verdict*, not on a sign cancellation.
⭐ **`--ex-gain-n12` still reproduces the pre-s114 single row exactly** (3.084, n 289), so every older
quote stays reproducible on demand.

⚠⚠ **CONSEQUENCE: 7 ROWS OVER SHIP, was 6.** The THD row was reading SHIP on a mixture; it now reads
what its own population says. **That is the gate getting more accurate, not the model getting worse**
— nothing in `src/` changed this session.

▶ **NEXT, in order — unchanged from session 113 except that its item 6 is half DONE.**
1. ⭐⭐ **Head item: "a null whose depth grows with level", at DRIVE MAX** (s110 R8) — but read
   session 113's S7 first: on the **send axis it did not corroborate** (both sides wash out), so it
   is *located, not settled*, on n = 1 pair. ⚠ And s113's S5 says the compression error is
   **shape-dominated** (1.49–4.42 against GATE K5's 0.25 bar) at every matched cell, so **no single
   saturation constant can close it** — the same verdict GATE P gave for A3, now on the drive axis.
2. ⭐ **Build the matched-bleed LEVEL instrument** from s112's two tight pairs — GATE K6's refused
   verdict is answerable. ⛔ Not by regression on the grid; the collinearity is untouched.
3. ✅ **DONE, SESSION 114 — the send-pad constant is 12.000 dB** (user decision, "whatever increases
   accuracy"). See the session-114 part-2 block: exactly scoped (0 non-`gain-n12` captures moved),
   inert on the matrix by construction, a correctness fix for the absolute ledgers.
4. ✅ **DONE, SESSION 114 — the THD gate row is SPLIT by operating point, not pooled** (same user
   decision). Pooling was flipping the verdict on the population the bar was written for. Costs a
   row: **7 over SHIP, was 6.**
5. **MASTER taper → Phase 10 C**, with `PREFER_FULL_SEND_NOON` and s112's fresh ladder. ⚠ And check
   session 41's `kOutputMakeup` anchor against it — it was calibrated at `master-1700`, which s112
   found **pinned** in the `gain-n12` ladder.
⚠ **Quote every OD number against `s114_baseline.json`** (162 captures; membership identical
to s113, and 122 of its captures are bit-identical to it).

---

⭐⭐ **SESSION 91 BROKE THE 46-SESSION DROUGHT — TWO CONSTANTS SHIPPED, AND `src/` IS NO LONGER CLEAN
vs HEAD.** Sessions 45–90 changed nothing audible; the reset's whole diagnosis was that *decision*
steps kept being deferred to more measurement. Both of session 91's moves were long-located and
blocked only on judgement, and both were taken with the user in the loop:

| constant | was → now | what it is | authority |
|---|---|---|---|
| **`c21R`** | 220k → **130k** | C21 corner 7.2 → 12.2 Hz. Backlog item 1, flagged since s71. | **HARDWARE** (`reference-sources.md` §2) — a deliberate, priced departure FROM the ND captures |
| **`jfetSatNeg`** | 0.76054 → **1.9** | the J201 small-signal even coefficient `a`. Backlog item 2, located s80, matrix-judged s81/82/84. | HW even-order structure (§4); ND has none |

⚠ **Neither is a bug fix and neither should be read as one.** `c21R` = 220k is still the correct fit
*to ND*; what changed is which reference governs LF corners. See both fields' comments in
`FitParams.h` — they are the fullest record.

**Current grade** — 129 captures, **shipped defaults as of session 91**,
`analysis/reports/s91_shipped.json` (`release_gate.py` + `matrix_grade.py` + `shape_gate.py`).
Graded **25 Hz – 16.3 kHz** on the **H1-only band-averaged** FR read (session 90's instrument).
Membership is identical to the s90 and s74 baselines (504 shared rows, 0 exclusive), so all three
ARE comparable.

⚠⚠ **SUPERSEDED BY SESSION 100 — the table below is the s91 baseline, kept as the diff-against
control. The SHIPPED grade is `analysis/reports/s99_attack_cand.json`** (same 129 captures, 504
shared rows, membership identical, and the shipped build renders bit-identically to it):

| subset | rows | band-RMS | decomposition (level/tilt/curv/LOCAL) |
|---|---|---|---|
| **OD** ex gain-n12 | 320 | **2.409** | 1.953 / 1.593 / 1.312 / **2.327** |
| **CLEAN** | 168 | **0.453** | 0.195 / 0.304 / 0.213 / 0.281 *(bit-identical to s91)* |
| **THD** (OD) | 228 | 6.944 | **3.663** / 2.708 / 2.600 / 4.904 |
| OD gain-n12 [bad] | 16 | 2.837 | capture defect, session 48 — do not fit to it |

*s91 shipped, the control:*

| subset | rows | band-RMS | median \|Δ\| | p90 | max | decomposition (level/tilt/curv/LOCAL) |
|---|---|---|---|---|---|---|
| **OD** ex gain-n12 | 320 | **2.664** | 0.79 | 5.49 | 40.8 | 1.909 / 1.774 / 1.302 / **2.460** |
| **CLEAN** | 168 | **0.453** | 0.26 | 0.82 | 3.15 | 0.195 / 0.304 / 0.213 / 0.281 |
| **THD** (OD) | 228 | 7.520 | — | — | — | **4.279** / 2.847 / 2.832 / 4.703 |
| OD gain-n12 [bad] | 16 | 3.042 | — | — | — | capture defect, session 48 — do not fit to it |

s90 shipped, for the diff: OD **2.697** / 0.81 / 5.62 / 40.2 · CLEAN **0.432** / 0.23 / 0.77 ·
THD **6.202** / 4.281 / 3.257. (s74, a DIFFERENT read and range — 25 Hz–12.9 kHz on CSD — was
2.743 / 0.408 / 3.621; never diff against it without saying so.)

⭐⭐⭐ **THE BIG RESULT: THE THD `level` TERM FELL 6.202 → 4.279 dB, AND IT WAS `jfetSatNeg`, NOT A
THD-DIRECTED FIX.** All three THD terms moved together (tilt 4.281 → 2.847, curv 3.257 → 2.832,
rms(q) 9.292 → 7.520), on identical membership, n=228 throughout. `c21R` contributes almost none of
it (6.202 → 6.158); the even-order move contributes the rest. ⇒ **backlog item 3 — "the largest
single number in the project", which had never had a dedicated session — was substantially closed as
a SIDE EFFECT of item 2.** That is mechanistically sensible: the THD `level` term measures the
model's distortion *amount* being systematically low, and item 2 restored a missing low-drive
even-order generator. ⚠ It is **not** finished — 4.279 is still well over the 3.0 SHIP bar — but it
is no longer the untouched headline, and **item 3 must now be re-scoped against 4.279, not 6.2**.

⭐ **OD improved too, though modestly**: band-RMS 2.697 → 2.664, median 0.81 → 0.79, p90 5.62 → 5.49.
Almost all of that is `c21R` (2.697 → 2.652); `jfetSatNeg` costs a little back (+0.012), concentrated
at HF — OD 8–16.3 kHz p99 29.68 → 31.56, max 40.24 → 40.78.

⚠ **CLEAN PAID, DELIBERATELY: band-RMS 0.432 → 0.453, median 0.23 → 0.26, p90 0.77 → 0.82.** This is
the priced cost of `c21R` and is confined to 25–100 Hz (that region's p90 0.67 → 0.84); CLEAN
100 Hz–8 kHz actually IMPROVED 0.73 → 0.72 and 8–16.3 kHz is unchanged. `jfetSatNeg` moves CLEAN not
at all (the J201 is in the OD path). **CLEAN is still essentially finished — keep regression-guarding
it, do not fit it — but it is no longer "bit-identical to ND at LF", and that is on purpose.**

### THE RELEASE GATE (agreed with the user, session 89)

Phase 9 closes and Phase 10 begins when the SHIP column is met. Percentiles are over band values,
OD ex gain-n12.

⚠ **The graded range is now 25 Hz – 16.3 kHz, widened from 12.9 kHz in session 89.** `matrix_grade`'s
`GRADE_HI = 12901.6` was justified by a comment claiming the 16 kHz band "sits in the sweep/cab noise
floor" — there is no cab in this pedal (leftover template text) and it had never been measured.
Measured: **CLEAN at 16255 Hz reads median 0.62 / p90 1.70 / max 3.14 dB.** It is perfectly readable.
The sweep is 20 Hz – 20 kHz, so the stimulus supports it. ⚠ **Shipped in session 90, and the band it
was excluding turns out to be the WORST in the matrix** — 11 of the 12 worst OD band values, p90
16.6 dB, max 40.2. Widening the range cost ~0.25 dB of OD headline; that is a correction, not a
regression, but every pre-session-90 OD number is missing it.

⭐⭐ **THE GATE IS NOW A SCRIPT, NOT A TRANSCRIBED TABLE — `analysis/release_gate.py`.** The SHIP and
stretch columns live in its `GATE` constant and every "now" cell is computed:

```bash
/opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s112_baseline.json
```

It exits non-zero while any gated row is over, prints `n` beside every statistic, breaks the
reference dropouts and the `gain-n12` group out as printed subsets rather than hiding them, and
takes `--method csd|h1|h1band` / `--compare` to re-grade from the SAME renders (all three FR reads
are stored per row). **Quote it, do not retype it.** The column below is a CONVENIENCE COPY and will
rot; the script is the definition.

⚠⚠ **THE `now` COLUMN IS ON A MEMBERSHIP NO OTHER COLUMN SHARES, AND AT s112 THAT MATTERS MORE THAN
IT EVER HAS.** Session 110 excluded 2 reference-dropout cells; session 111 retired the `gain-n12`
exclusion (**+20 OD rows**); **session 112 added 26 captures, 12 of them at intermediate BLEND, and
those alone move the OD headline 2.327 → 2.154 with the model UNCHANGED.** All of it is printed by
the script every run, including the new **BLEND composition** table. **`--ex-gain-n12` reproduces the
s111→s110 step exactly**; there is no flag that undoes the dropout exclusion or the s112 captures, so
**the honest control for any pre-s112 comparison is the 127-capture shared set** (which reproduces
the s111 column byte-for-byte — verified).

| subset | region | statistic | **SHIP** | stretch | **now (s112, 153 caps)** | s112 on the shared 127 (= s111) | s110 (n12 out) | was (s100) |
|---|---|---|---|---|---|---|---|---|
| CLEAN | **100 Hz – 8 kHz** | median / p90 | ≤0.30 / ≤0.80 | — | **0.221 ✅ / 0.732 ✅** | 0.250 / 0.742 | 0.215 / 0.719 | 0.215 / 0.719 |
| CLEAN | **8 – 16.3 kHz** | median / p90 | ≤0.40 / ≤1.40 | — | **0.340 ✅ / 1.289 ✅** | 0.340 / 1.324 | 0.340 / 1.308 | 0.340 / 1.308 |
| **OD** | 100 Hz – 8 kHz | median / p90 | **≤0.5 / ≤2.0** | ≤0.5 / ≤1.0 | **0.469 ⚠ STRETCH-by-dilution** / 3.908 | 0.531 over / 4.242 | 0.489 / 4.195 | 0.568 / 4.458 |
| **OD** | 25 – 100 Hz | median / p90 | **≤0.7 / ≤2.5** | ≤0.5 / ≤1.5 | **0.804 / 4.877** | 0.917 / 4.875 | 0.825 / 4.888 | 0.860 / 4.971 |
| **OD** | 8 – 16.3 kHz | median / p90 | **≤0.7 / ≤2.5** | ≤0.5 / ≤1.5 | **0.615** ✅ / **6.792** | 0.625 ✅ / 7.451 | 0.581 ✅ / 7.101 | 0.566 ✅ / 8.058 |
| **OD** | any region | p99 ("extremes") | **≤4.0** | ≤3.0 | **11.801** | 12.809 | 12.893 | 14.661 |
| **THD** | OD | level term | **≤3.0 dB** | ≤2.0 | **3.064 ⚠ over** | 2.986 SHIP ⛔ | 3.065 | 3.663 |
| headline | OD band-RMS | band-RMS | **≤2.0 dB** | ≤1.5 | **2.154** | 2.327 | 2.265 | 2.409 |
| notches (320 Hz &c.) | — | best effort, reported per band, not gated | — | — | +26 dB | +26 dB | +26 dB | +26 dB |

⛔⛔ **DO NOT READ THE s112 COLUMN AS PROGRESS. THE MODEL DID NOT CHANGE THIS SESSION** — every gated
cell is byte-identical on the shared 127 captures, which is the acceptance check. OD 100 Hz–8 kHz
median reading STRETCH again is **dilution by 12 intermediate-BLEND captures** (band-RMS 0.798 against
the existing set's 2.432), and the THD row going back over its bar is the same mechanism in reverse.
**7 rows remain over SHIP on both memberships**; only which 7, and by how much, moved.

⭐⭐ **SESSION 109 CLOSED THE FIRST OD ROW IN THE PROJECT'S HISTORY** — OD 100 Hz–8 kHz median
0.568 → **0.480** (0.489 on the s110 baseline), meeting SHIP *and* STRETCH.
⛔ **SESSION 111 RE-OPENED IT AT 0.531**, because the 20 retired `gain-n12` rows are worse than the
OD mean. That is a **membership** change, not a regression in the model — the s109 constant is
untouched and `--ex-gain-n12` still returns 0.489. **7 rows remain over SHIP either way**; only
which 7 changed.

⛔⛔ **AND THE THD ROW'S `SHIP` AT 2.986 MUST NOT BE READ AS PROGRESS — IT IS A TWO-POPULATION
MIXTURE OF AN UNSIGNED STATISTIC.** Signed means: **+1.414 dB** over the 229 full-send rows (the
model over-distorts) against **−0.772 dB** over the 15 retired rows (it under-distorts, 12.071 dB
further down the compression curve). The rms of the union is smaller than either. The script prints
the three-way split under the row on every run. ⚠ The THD **level** term is an UNSIGNED rms
throughout — its signed mean is +1.263 dB at s100 / +1.412 at s109 — so the gated number never
carried a direction. Do not read it as one.

⚠ **8 rows still over SHIP** (every OD row plus THD level 3.663 vs ≤3.0) — session 100 moved 7 of
them the right way and **p99 the wrong way**, but closed none. **Phase 9 remains open on the model.**

⚠⚠ **THE TWO OD 8–16.3 kHz ROWS ARE KNOWN ARTEFACT-CONTAMINATED AND ARE GATED ANYWAY — DECIDED WITH
THE USER, SESSION 101: "leave the gate alone, but flag that we may need to split it later on if we
can't improve elsewhere."** GATE I (`analysis/hf_artefact_gate.py`) establishes the region is ND's
aliasing, not our Sallen-Keys — full detail in the standing-rules block below. Nothing was changed;
the note exists so the number is READ correctly, not so it is excused.
▶ **PRE-REGISTERED FALLBACK, not to be taken yet:** if the other OD rows close and these two are the
last blocker, **split the region the way session 96 split CLEAN** — 8127.5 Hz (a real, drive-
INDEPENDENT defect) graded apart from 12901.6/16255 Hz (artefact-dominated) — rather than loosening
either bar. The trigger is "everything else closed", not "this row is annoying". Re-run GATE I and
reproduce its numbers before acting. The fallback and its measured consequences are also recorded in
`release_gate.py` beside the two rows themselves, so the script carries them, not just this table.
⭐ **Meanwhile the actionable conclusion is independent of the gate: STOP AIMING MODEL WORK AT
8–16.3 kHz.** ~38 % of the OD headline sits there and is not ours to fix; p99 is **10.28 even with
all four HF bands dropped**, so the remaining OD error is genuinely broadband and that is where work
pays.

✅✅ **SESSION 96 — THE CLEAN ROW SPLIT IS EXECUTED AND ALL FOUR ROWS SHIP ON BOTH BASELINES. THE ONE
OPEN GATE DECISION IS NOW CLOSED, AND CLEAN NO LONGER BLOCKS "PHASE 9 CLOSED".** Decided with the
user in session 95, spec'd in `docs/clean-gate-split-handover.md`, landed in `analysis/release_gate.py`.
Scope was the gate script only — **no DSP constant, no render, no re-baseline**; the numbers are a
re-grade of `s91_shipped.json` / `s90_baseline129_h1.json` already on disk.

| | midband 100 Hz–8 kHz | HF 8–16.3 kHz | (pooled, superseded) |
|---|---|---|---|
| **bar** | ≤0.30 / ≤0.80 | ≤0.40 / ≤1.40 | ≤0.30 / ≤0.80 |
| **s91** | 0.215 / 0.719 ✅ | 0.340 / 1.308 ✅ | 0.234 / **0.808 over** |
| **s90** | 0.226 / 0.727 ✅ | 0.347 / 1.309 ✅ | 0.235 / **0.802 over** |

⭐⭐ **The load-bearing acceptance check passed: the s90 baseline stops failing retroactively.** That
was the whole defect — a gate that fails the shipped baseline it exists to protect is a false alarm,
not a regression detector, and session 91's two constants had moved the failing statistic by
**0.006 dB**, so it was never about them. ⭐ **The session-89 midband bars survive UNCHANGED at
0.30/0.80**, which is the strongest evidence this is a correction and not a concession: the
originally agreed numbers pass the moment they are measured on the pool they were meant for.
⭐ **And the verdicts are not brittle to the FR read** — all **24** CLEAN verdicts (4 rows × 3 reads
× 2 baselines) read SHIP; the statistics themselves spread only 0.010–0.016 dB across `csd`/`h1`/
`h1band`, well inside every bar's 0.06–0.09 dB headroom.
⭐ Headroom was derived, not chosen: between s90 and s91 (two shipped constants, neither
CLEAN-directed) the midband p90 moved 0.008 dB, the HF p90 0.001, the ungated pool 0.053 — so
~0.01–0.05 dB is this statistic's drift under unrelated work, and every bar sits clear of it.
⚠ **The HF bars are LOOSER than the midband's (0.40/1.40 vs 0.30/0.80) and that is the honest
outcome, not a fudge** — CLEAN's top four bands genuinely are worse (0.340/1.308 vs 0.215/0.719).
The split makes that visible for the first time instead of averaging it away; the gate says so in
its own output.
⛔ **8–16.3 kHz is GATED, not excluded.** §1's "HF corners" clause would arguably justify excluding
it as 25–100 Hz was excluded, but nothing in sessions 91–95 touched HF. **The split is a READABILITY
fix and must not quietly become an AUTHORITY change.**
⭐ `check_clean_partition()` now ASSERTS the two gated regions tile the old pooled composite exactly
(19 + 4 = 23 bands) — mutation-tested three ways (dropped band / overlap / extra band, all caught),
because a silently dropped band would improve every CLEAN bar at once
(`aggregate-moved-check-membership-first` in its most flattering form). All three superseded pools
still print as labelled CONTROLS, so pre-s91 and s91–95 quotes stay diff-able.
⚠ **This closes the row's READABILITY, not the region.** CLEAN 8–16.3 kHz remains its worst region
and is now explicitly gated rather than diluted; whether it deserves work is the same open question
as the OD 8–16.3 kHz row — same four bands, same suspicion ("ND's artefact or our Sallen-Keys?").

*Why the row was unsound, kept short because the handover holds the derivation:* the pool changed in
session 91 from 25 Hz–16.3 k to **100 Hz–16.3 k** (`reference-sources.md` §1 makes HARDWARE the
authority for LF corners, and `c21R` was deliberately moved away from ND there). ⚠ **That exclusion
made the gate HARDER, not easier** — the 25–100 Hz bands carried *smaller* errors and were diluting
the pooled p90 downward, so the 0.80 bar had been passing on dilution. On top of that it was agreed
in session 89 against a hand-transcribed **0.66** that session 90 re-measured at **0.77** on the same
file, so its intended 0.14 dB of headroom was really 0.03. Session 91 correctly refused to retune it
silently; session 95 put the split to the user; session 96 executed it.

⚠ The session-89 OD cells all reproduced to the digit (at the old range: median 0.85 / p90 5.87 /
max 36.18, band-RMS 2.743). Only CLEAN's did not.

⚠ **The OD p90 ≤2.0 dB bar depends on A3 closing.** If the timeboxed A3 attempt fails AND the
fallback correction network underdelivers, that number has to move to ~3.0 — flagged now rather than
discovered later. ⚠ Departures from the ND captures TOWARD a documented hardware trend are a **PASS**
(`reference-sources.md` §1), so the gate is a target, never a veto on a hardware-directed fix.

### Open work, in order

0. ✅ **DONE, SESSION 90 — the FR instrument is repaired, validated and re-baselined, AND IT DID NOT
   EXPLAIN THE ERROR.** `analyze.transfer_h1()` is an H1-only Farina read (harmonics rejected by
   time-gating, not by coherence), gated by known-answer self-test in `analysis/h1_fr_gate.py`;
   `matrix_grade.GRADE_HI` is 16255; the gate is re-baselined above. ⛔ **The conclusion is the
   opposite of what item 0 was written expecting, so read the next bullet before acting on the HF
   error.**
1. ✅ **DONE, SESSION 91 — `c21R` 220k → 130k SHIPPED.** Derived over all three §2 LF anchors by
   `analysis/c21_hw_anchor.py` (6 known-answer gates + a `--verify` acceptance check that runs
   against the RENDER), **not** off the one frequency the old bullet used. ⚠ The target is
   `HW − MODEL`, not §2's published `HW − ND`: the model was already 0.40 dB below ND at 20 Hz, so
   the raw delta gives 121k and OVERSHOOTS. Landed 0.70 → **0.17 dB** from the hardware anchor.
   150k was rendered and rejected (outside what either anchor asks for). Full record:
   `FitParams::c21R` and `reference-sources.md` §2 consequence 1.
2. ✅ **DONE, SESSION 91 — `jfetSatNeg` 0.76054 → 1.9 SHIPPED**, on the user's weighting decision
   (low-drive even-order gain judged to outweigh ≤0.75 dB on the authoritative odd columns).
   Monotonicity gated against the real header first. ⚠ **It carries a cost the matrix cannot see —
   see the `OSValidationTest` note in "Where we are" and item 6.**
3. ⛔⛔ **READ THIS FIRST — SESSION 109 REFUTED THIS ITEM'S PREMISE. THE MODEL DISTORTS *MORE* THAN
   THE REFERENCE, NOT LESS.** The gated "THD level term" is `abs(c[0])/sqrt(n)`, an **UNSIGNED** rms:
   it never said which direction. The **signed** mean of the same decomposition — already computed
   and already stored by `shape_gate.py` as `level_signed` — is **+1.263 dB at s100 (+1.412 at
   s109)**, and an independent read on the bleed-free OD endpoints gives **+2.94 dB**, same sign.
   ⇒ the sentence below ("the model's distortion *amount* being systematically low") is **wrong**,
   and any candidate reasoned about as "we need more distortion" was pointed backwards. ⭐ It is also
   coherent with GATE Q's mechanism — over-compressing and over-distorting are the same defect (the
   OD path saturates too early), which is why one constant moved both. **Re-scope this item on the
   SIGN, then the size: 3.096 against a 3.0 bar.** ⚠ Note the s109 change improved the gated
   *unsigned* rms (3.663 → 3.096) while moving the *signed* mean slightly further from zero — it
   removed spread, not offset, so the two must be read together.
   *(The superseded text follows, kept because its history is still the record of how the term got
   from 6.202 to 4.279.)*
   3. ⭐ **The THD `level` term — NOW 4.279 dB, WAS 6.202, AND IT WAS NOT A THD-DIRECTED FIX.** Item 2
   closed most of it as a side effect (see "Where we are"); `c21R` contributed ~0.04. **Re-scope this
   item against 4.279 before starting** — the remaining deficit is a different, smaller animal than
   the one this bullet was written about, and the obvious next lever (more even-order) has just been
   spent to the edge of its free region. Still over its 3.0 SHIP bar. Start from `shape_gate.py`'s
   THD decomposition and the drive/level axes, not from FR. ⚠ Note tilt (4.281 → 2.847) and curv
   (3.257 → 2.832) fell too, so this was a broad THD gain, not a level-only one.
4. ⛔⛔ **START AT THE SESSION-99 BLOCK BELOW (search "SESSION 99"). IT SUPERSEDES THE HEADLINE OF
   THIS BULLET.** Sessions 94 and 97 both reported the corrected ATTACK requirement REACHED; session
   99 measured that both results were bought by spending the OD path's absolute low-end level (−42 dB
   and −22 dB respectively), and that with a level-visible objective **the notch width/depth and the
   absolute level are in CONFLICT in this topology**. ⭐ The session-99 candidate is nonetheless the
   first the 129-capture matrix has ever ACCEPTED (OD band-RMS 2.664 → **2.409**, THD level 4.279 →
   **3.663**) — but as an OD-LEVEL fix, not a notch fix, and it is **awaiting a user decision**.
   *The sessions 93–98 narrative below is kept because it is what made all of that measurable.*

   ⭐⭐ **SESSION 94 DID THE RE-FIT. THE REQUIREMENT IS REACHABLE AND THE POINT THAT REACHES IT IS
   UNSHIPPABLE — read this whole bullet before touching item 4 again.** *(⚠ superseded — see above.)*
   **The instrument swap shipped**: `attack_shape_screen.py --instrument stepped` is now the
   DEFAULT. It solves on the stimulus's own 2 Hz tone grid with `read_notch_sweep.locate`, so the
   model, the calibration anchor and the pedal share ONE instrument; the target is MEASURED from
   the three drive-min captures and gated against session 70's published spec (reproduced to
   **0.03**); the f0 residual is normalised by 2.0 Hz instead of 5.86. `--instrument swept`
   reproduces sessions 64–66 exactly and is kept as the control (verified: its targets and
   calibration table reproduce to the digit).
   ⭐ **GATE C PASSES NOW, WHERE IT USED TO READ "CHECK".** Out-of-sample, both directions, between
   two very different ladders: f0 ≤0.72 Hz, depth ≤0.21 dB, width ≤10.4 % (swept: 6.9 Hz / 2.6 dB /
   15.7 %). Removing the instrument mismatch is what did it — the calibration now carries only the
   python-vs-chain difference. And the screen's proposal-point width ratios (1.66 / 2.70 / 2.00)
   equal the render's stepped-vs-stepped ratios to 2 dp, which nothing in the fit arranged.
   ⭐⭐ **THE REACHABILITY ANSWER IS POSITIVE, AND SESSION 64's CONFLICT DOES NOT SURVIVE THE
   CORRECTED REQUIREMENT.** The frontier reaches all nine numbers AT ONCE at box ±1 decade —
   f0 rms **0.08** of a 2 Hz step (spread 6.7 Hz against the pedal's 6.81), width rms 0.34, depth
   rms 0.17 — and freeing the J201 drain pole `Cp` changes the cost by **0.0000**, i.e. there is no
   conflict left for it to relieve. ⚠ The NEGATIVE outcome this bullet warned was live did not
   happen; the corrected spec is EASIER for this topology, because it asks for a 6.81 Hz f0 spread,
   not 17.58.
   ⭐ **AND IT LANDS ON THE REAL RENDER, UNDER BOTH INSTRUMENTS.** `attack_stepped_gate.py
   --fits-json` (new flag) on `analysis/reports/s94_attack_best_stepped.json`: Δf0 **−0.17 / −0.26 /
   −0.72 Hz**, Δdepth **−0.20 / +0.18 / +0.03 dB**, width ratio **0.90 / 1.02 / 0.91×**, f0 spread
   **6.59** vs the pedal's 7.13 (the s62 proposal: −6.18/+1.46/+4.41, −0.98/−5.73/−0.03,
   1.66/2.70/2.00×, spread 17.72). The swept control agrees independently — f0 to the bin, depths
   14.97/31.65/16.00 vs 14.93/32.70/16.01, widths 0.86/1.06/0.93×.
   ⛔⛔ **AND THE 129-CAPTURE MATRIX REFUSES IT, BY A MILE. OD band-RMS 2.664 → 6.174, THD level
   4.279 → 18.685, worst row +27.04 dB** (`analysis/reports/s94_attack_cand.json`, 504 shared rows,
   membership identical, CLEAN **bit-identical** at 0.453 — the control passes, the treble ladder is
   OD-only). 178 rows worse by >0.5 dB against 6 better. **Every large regression is a `level-1700`
   row** — LEVEL max, where the clean bleed is exactly zero by topology, i.e. exactly where the raw
   OD path is exposed. Measured on the worst row, the OD path is **40–47 dB DOWN below 400 Hz**.
   ⭐⭐ **THE CAUSE IS A GATE GAP AND IT IS THE ACTIONABLE FINDING: the screen's objective is
   ENTIRELY RELATIVE, so it cannot see absolute OD magnitude at all.** The notch triple is referred
   to each throw's own shoulder and `h` is a throw-to-throw ratio, so a change shared by all three
   throws is invisible to the whole objective — and the fit spent exactly that, re-scaling the
   shared ladder (R7 ×5.16, C6 ×9.92, C7 ×0.1, C5 ×0.33, C9 ×0.25; C6/C7/Ra ON A BOUND, i.e.
   unidentified). ⚠ **Not one element**: pinning C7 back to 680 pF alone recovers 28.87 → **15.18**
   dB on the worst row, so C7 is the largest single contributor and about half is the rest.
   ⭐⭐ **SESSION 95 BUILT THAT TERM, GATED IT, AND FOUND THE DEGENERACY IS OLDER AND MORE SPECIFIC
   THAN "SESSION 94 WENT WRONG" — read this before re-fitting.** `attack_shape_screen.py` now carries
   an absolute, bleed-free OD-magnitude term `g` (`--no-absgain` restores the pre-95 objective as the
   control), in **both** fit stages, with a new **GATE F**.
   ⭐ **The enabling fact, measured first:** the downstream transfer `D(f) = render − ladder` is
   INVARIANT between the two very different C8=0 ladders GATE C already uses — worst
   |D_cal − D_prop| = **0.183 dB** over the whole band and all three throws. So an absolute LADDER
   target CAN be derived from an absolute RENDER measurement; without that the term would be
   unfounded, which is why F1 runs first and refuses.
   ⭐⭐ **AND THE FINDING: `h` CANNOT TELL "RAISE BOOST 10 dB" FROM "LOWER CUT AND FLAT 8 dB", AND
   SESSION 62 TOOK THE SECOND BRANCH.** Measured bleed-free (drive min / LEVEL max / BLEND max, clean
   bleed exactly zero by topology), `pedal − render` median over 100 notch-remote bins:

   | render | cut | boost | flat |
   |---|---|---|---|
   | **DRAWN default** | **+0.47** | **+10.30** | +2.51 |
   | **session 62 PROPOSAL** | +8.66 | +9.18 | +8.73 |

   ⇒ the drawn model is already absolutely RIGHT at cut and 2.5 dB low at flat; the whole real defect
   is **BOOST, 10.3 dB light**. The proposal reached h-correct-to-0.45 dB by pulling cut and flat
   DOWN ~8.7 dB instead, and **no ATTACK objective since session 57 could see the difference.**
   Both soundness gates pass: present in all three throws (8.66/9.18/8.73, spread 0.52 dB) and
   level-independent (worst 0.29 dB between −36 and −30 dBFS).
   ⭐ **GATE F3b demonstrates the blind spot on the tool's own code path**, rather than arguing it
   from session 94's matrix run: a tap `Ra ×10` mutation moves `g` by **14.88 dB** while the notch
   triple — *the only term scoring stage 1, where the candidate is selected* — absorbs **1.4 %** of it
   (7.30 → 7.51) and `h` 23 %. ⚠ F3's first draft used `R7 ×10` and FAILED for its own reason: R7 ×3
   and beyond destroy the null (width → nan), `full_stats` returns None, and the draft scored that as
   `dg = 0.0` — `empty-gate-must-fail` committed *inside* the gate written to enforce it. A None
   mutation is now a distinct hard failure.
   ⛔ **THE RE-FIT RUNS AND THE RESULT IS NOT PROPOSABLE — DO NOT SEND IT TO THE MATRIX AS IT STANDS**
   (`analysis/reports/s95_attack_best_absg.json`). With `g` in, the nine notch numbers AND the
   absolute level are reachable together — f0 within **0.12 Hz**, depth within **0.76 dB**, width
   within **8.1 %**, `g` within **0.26 dB** at every throw — but the winning point rests **three of
   thirteen values on their bounds (C5, C9, Ra)**, i.e. unidentified, and still moves
   **C7 ×0.243** (680 → 166 pF), the element session 94 attributed about half its matrix regression to.
   ⭐⭐ **SESSION 97 DID THE RANKING-KEY FIX AND IT UNCOVERED TWO FURTHER DEFECTS BEHIND IT — THE
   SELECTION NOW SCORES WHAT IT EMITS, AND THE BEST POINT IS THE BEST OF THE PROJECT SO FAR, BUT IT
   IS STILL NOT PROPOSABLE.** Analysis only: **no DSP constant moved, no render, no matrix run.**
   The key is now `(realisable, g, f0, width, n_on_bound, box)`, and each of the three fixes was
   gated before it was believed.
   ⭐ **(1) `n_on_bound` now outranks `box`** — the carried-forward TODO, executed. Verified OFFLINE
   against the stored s95 rows *before* any re-fit: the old key reproduces s95's recorded winner, the
   new one selects an identified point, and the two tie on every preceding term, so the new term alone
   moved the selection. ⭐ GENERAL: rank identifiability ahead of any plausibility tie-break.
   ⚠⚠ **(2) AND IT WALKED STRAIGHT INTO A SECOND BLIND SPOT THE TOOL HAD BEEN *PRINTING* FOR 35
   SESSIONS: THE POINT IT SELECTED IS ONE `FitParams` CANNOT EXPRESS.** The C++ realisation is one
   base `trebleC5` plus `attackC5TrimBoost`/`attackC5TrimCut` — there is **no `attackC5TrimFlat`** —
   so flat must BE the smallest of the three throws. **2 of the 10 rows fail that, and the new key
   picked one** (flat off by 0.25 nF, ~4 %). The screen has printed "recorded not hidden" since
   session 62 and never RANKED on it. `realisable()` is now the **first** term: feasibility is not a
   quality term, and a point that cannot be rendered cannot be judged by the render OR the matrix.
   ⚠⚠ **(3) AND `build()`'s C5-trim mapping was normalised by the module default `BOX`, not the
   SWEPT `box`.** Its own docstring promises a codomain of `[0, 0.3·C5]`; at box 3.0 it delivered
   `[−0.3·C5, +0.6·C5]` — half of it a NEGATIVE additive parallel cap. Invisible for 31 sessions
   because every winner since session 66 was a box-1.0 row, where `box == BOX` and the two agree
   **exactly**; the moment the key first selected a box-3.0 row, **3 of the 5 box-3.0 rows were
   sitting outside the documented range** (trims 0.322 / 0.312 / 0.465 × C5). Fixed, along with the
   same hardcoded `BOX` in `show()`'s bound check. ⭐ GENERAL: when a search SETTING is swept, every
   mapping that reads it must read the swept value — a hardcoded copy of the default is invisible
   until the sweep first wins.
   ⛔⛔ **(4) THE BIGGEST ONE: THE RANKING WAS SCORING STAGE-1 NUMBERS THAT STAGE 2 DOES NOT
   DELIVER.** `best_point` ranked all ten rows on their stage-1 ladder statistics and re-fitted the
   tap ONCE, on the winner, justified in its own docstring by *"the tap moves width by ≤0.5 Hz and f0
   by 0.00 Hz, so it cannot undo stage 1"*. That is a **CENSUS number measured at PROP** and it does
   not survive at the fitted points — measured, the tap moves cut/flat width by **2.3–2.5 Hz** at the
   s95 winner and **6.9–8.5 Hz (up to 17×the quoted bound)** at others. And the perturbation is
   **candidate-dependent, so it reorders the field**: box 1.0 / w_f0 30 goes width rms 1.19 → **0.41**
   while box 3.0 / w_f0 100 goes 0.40 → **1.19**. Stage 2 now runs **per row**, the key ranks its
   output, both columns print per row, and the scored residuals live in ONE `resid()` shared by the
   objective and the ranking. ⭐ GENERAL: score the candidate you will actually EMIT; a two-stage fit
   whose second stage is argued harmless must PRINT the harm, not cite a census taken elsewhere.
   ⭐ **The result is the best ATTACK point the project has had** (box 1.0 / w_f0 10,
   `analysis/reports/s97_attack_best_posttap.json`): Δf0 **−0.08 / −0.02 / −0.10 Hz**, Δdepth
   **−0.59 / −0.29 / −0.39 dB**, width **−6.9 / +1.1 / −0.8 %**, `g` within **0.26 dB** at every
   throw — better than the s95 point on every depth and on cut+flat width — and it asks the mildest
   shared re-scale of any winner so far, **worst ×7.28** (s95 ×9.97; the intermediate, pre-fix-(4)
   winner wanted **R7 ×119 / R12 ×402**, i.e. session 94's signature with `g` merely holding the
   level). ⚠ It still moves **C7 ×0.244** (680 → 166 pF), the element session 94 attributed about
   half its matrix regression to.
   ⛔ **STILL NOT PROPOSABLE, and the reason is now precise rather than diffuse: 2 of 17 values rest
   on their bounds — `C9` at the ladder box floor (×0.1) and `Ra` at the tap floor (×0.1).** Both are
   pinned at the SMALL end, i.e. the search wants them smaller than the box allows, so the **box is
   the missing equation** (`bound-resting-means-unidentified`). ⭐ The fully-identified alternatives
   all exist and are all box-3.0 rows: the best is **box 3.0 / w_f0 10 — 0 on bound, post-tap f0 0.07
   / width 0.60 / g 0.26, worst shared ×30.1**, which loses only at the width term.
   ⭐ **AND `Ra` IS CORROBORATED AS UNIDENTIFIED BY A PATH THAT SHARES NO SEARCH WITH `--best`:** in
   the `--fit` census (7 independent `shared`-set variants, tap free, run as the session's smoke
   test) **`Ra` rests on its bound in 7 of 7**. So `Ra` at the floor is a property of the TAP
   PARAMETERISATION, not an artefact of the box sweep — which is what makes the next step a search
   -setting question rather than a "this candidate happened to rail" one.
   ⭐⭐⭐ **SESSION 98 TESTED THAT PRE-REGISTERED NEXT STEP INSTEAD OF EXECUTING IT, AND IT IS
   REFUTED: NEITHER VALUE IS BOX-LIMITED, SO BOTH ARE IDENTIFIED AND THE IDENTIFIABILITY OBJECTION
   TO PROPOSING THE POINT IS GONE.** (Whether it SHIPS is the matrix's call, below — identified is
   a precondition for being judged, not a verdict.)
   Session 97 read the two bound-resters as unidentified and pre-registered a per-dimension floor
   sweep; `bound-resting-means-unidentified` says the outside bound is the missing equation. **That
   is a HYPOTHESIS about the objective, and it has a decisive test that the sweep does not** —
   `attack_shape_screen.py --floor-probe` (new; GATE G, 4 computed sub-gates). It profiles each
   coordinate straight THROUGH its bound to −3 decades, **twice**: as a 1-D slice, and again with
   **every other coordinate RE-FITTED**, which is the only form that can settle it.

   | pin (decades) | ×mult | post-tap f0 | width | depth | g dB | on bound |
   |---|---|---|---|---|---|---|
   | **C9** −1.00 *(the rail)* | 0.1 | 0.040 | 0.466 | 0.514 | 0.191 | 1 |
   | C9 −1.25 | 0.056 | 0.034 | 0.448 | 0.477 | 0.203 | 2 |
   | C9 −1.50 | 0.032 | 0.048 | 0.557 | 0.266 | 0.214 | 4 |
   | C9 −2.00 | 0.01 | **5.84** | **24.69** | **25.09** | 0.892 | 2 |
   | C9 −3.00 | 0.001 | **23.08** | **32.06** | **25.46** | 0.208 | 2 |
   | **Ra** −1.00 *(the rail)* | 0.1 | 0.039 | 0.406 | 0.438 | **0.190** | 1 |
   | Ra −1.50 | 0.032 | 0.049 | 0.459 | 0.580 | **0.911** | 3 |
   | Ra −3.00 | 0.001 | 0.053 | 0.484 | 0.640 | **1.698** | 3 |

   ⇒ **outside the box NOTHING dominates the reference, in either dimension.** `C9` collapses beyond
   ×0.03 and `Ra` degrades monotonically on the absolute-level term `g`. The optimum simply
   **COINCIDES** with the bound. ⭐ A rail caused by the box shows a LOWER cost outside; a coincident
   optimum shows a HIGHER one — and the two are indistinguishable from the fitted point alone, which
   is exactly why the heuristic exists and exactly why it had to be measured. **Note which way the
   error ran: the heuristic was about to make the project discard a good point and spend a session
   widening a box that does not bind.**
   ⭐ Both known-answer checks pass — pinned at the record's own value the re-fit reproduces the
   record to f0 0.040/0.039, w 0.466/0.406, g 0.191/0.190 — and G1 reproduces the stored s97 row
   **to 0.000e+00** under the new per-dimension code path, with G2 asserting `build()`'s C5-trim
   mapping is **BIT-IDENTICAL** to the session-97 line at symmetric bounds. The slice agrees with
   the re-optimised profile (every dimension AT-OPTIMUM, G3 OK); ⚠ that is a result, not a licence —
   only the re-optimised column may carry a verdict, because a slice through a rail holds the other
   15 coordinates at values chosen *while* it was railed.
   ⚠ **Three defects in session 98's own gate had to be fixed before any of the above was believed,
   and two of them had already printed a WRONG verdict** — see the session-98 block below. The first
   draft reported "the floor BINDS -- widen C9" off a rounding boundary.

   ⭐⭐ **AND IT LANDS ON THE REAL RENDER — the s97 point through `attack_stepped_gate.py
   --fits-json` (`analysis/reports/s98_attack_stepped_cand.json`), stepped instrument both sides:**
   Δf0 **−0.37 / −0.03 / −0.80 Hz**, Δdepth **−0.55 / −0.35 / −0.42 dB**, width ratio
   **0.88 / 1.01 / 0.89×**, f0 spread **6.71** vs the pedal's **7.13** (session 62's proposal:
   −6.18/+1.46/+4.41, −0.98/−5.73/−0.03, 1.66/2.70/2.00×, spread 17.72). All five of that tool's
   gates pass, including the instrument-swap control, whose verdict is scored over the reference
   variants only. ⚠ The stale-artefact guard fired first and refused the run — session 94's
   `cand_*.wav` were on disk under the same names with different `--fit` args
   (`rebaseline-all-derived-artefacts`, caught by the `.args.json` stamp, exactly as designed).

   ⛔⛔ **AND THE 129-CAPTURE MATRIX STILL REFUSES IT — BUT BY LESS THAN HALF OF SESSION 94's
   DAMAGE, AND SESSION 98 LOCALISED THE REMAINDER TO A SPECIFIC, FIXABLE BLIND SPOT IN `g` ITSELF**
   (`analysis/reports/s98_attack_cand.json`, 129 captures, 504 shared rows, **0 from cache**):

   | | s91 shipped | **s94** cand (no `g`) | **s98** cand (with `g`) |
   |---|---|---|---|
   | OD band-RMS ex gain-n12 | **2.664** | 6.174 | **4.314** |
   | THD (OD) level term | **4.279** | 18.685 | **9.466** |
   | OD 25–100 Hz p90 | **6.065** | — | **20.958** |
   | CLEAN band-RMS | 0.453 | 0.453 | **0.453** (bit-identical) |
   | worst single row | — | +27.04 | **+17.46** |
   | rows worse >0.5 dB / better | — | 178 / 6 | **142 / 25** |

   ⭐ **CLEAN is bit-identical again and all four CLEAN gate rows still SHIP** — the control passes,
   the treble ladder is OD-only, exactly as in session 94. ⭐ Every large regression is a
   **`level-1700`** row again (LEVEL max, clean bleed zero by topology = the raw OD path exposed);
   `ref-od`, where the bleed is present, moves only 1–4 dB.

   ⭐⭐⭐ **THE CAUSE, MEASURED IN THREE STEPS BY THE NEW `analysis/attack_d_extrapolation_gate.py`
   (GATE H, 4 sub-gates, H1 a known answer against GATE F's own `D_prop` = +30.65/+30.62/+30.65):**
   **(H2)** GATE F's D-invariance premise **does NOT extend to the fitted ladder** —
   worst |D_cand − D_prop| = **3.84 dB** at boost against GATE F's 1.0 limit and its 0.183 measured
   between PROP and CAL. ⚠ Real, and **NOT sufficient**: the medians move only 0.03–0.52 dB, and the
   regression is 26–47 dB. *A defect that is REAL and a defect that is SUFFICIENT are two different
   claims* — H3 exists to stop H2 being quoted as the answer.
   **(H3)** `g` **DID its job at its own condition**: the render moved **+8.98 / +8.12 / +9.09 dB**
   against the **+8.66 / +9.18 / +8.73** asked, worst shortfall **1.06 dB**.
   **(H4) ⛔⛔ AND THE SAME MEASUREMENT PER SUB-BAND SHOWS WHAT THAT POOLED MEDIAN AVERAGED AWAY:**

   | sub-band | bins | cut | boost | flat |
   |---|---|---|---|---|
   | **87.9–200 Hz** | **8** | **+21.31** | **+23.11** | **+22.30** |
   | 500–800 Hz | 23 | +3.70 | +4.08 | +3.58 |
   | 800–1600 Hz | 69 | −1.43 | +0.86 | −1.42 |

   ⇒ **`g` is `median(gabs[G_BAND])` over 100 LINEARLY-spaced bins from 87.9 to 1599.6 Hz — 8 below
   200 Hz, 69 above 800 — so its median bin sits at 1019.5 Hz. It is a ~1 kHz statistic wearing a
   broadband name, and it cannot register a low-frequency collapse at all.** It reads "satisfied to
   1.06 dB" while the render is **23 dB short at 88–200 Hz**, which is precisely the matrix's
   OD 25–100 Hz p90 going 6.065 → 20.958.
   ⚠ **The source comment beside `G_BAND` asserts the opposite** — *"a 40 dB collapse below 400 Hz
   is still fully visible in the 88-175 Hz bins"*. True **of the bins**, false **of the median over
   them**: 8 bins in 100 cannot move it. **A claim about what a band CONTAINS is not a claim about
   what a STATISTIC computed over it can see.**
   ⭐⭐ **This is session 94's failure repeating one level down, and that is the encouraging
   reading, not the discouraging one:** s94's objective was blind to a shared re-scale, `g` closed
   that (6.174 → 4.314, worst row +27.04 → +17.46), and `g` is in turn blind to WHERE that level
   sits in frequency. Each closed blind spot has roughly halved the damage.

   ✅ **SESSION 98's THREE-STEP PLAN IS EXECUTED (session 99): `g` is per-sub-band, GATE F measures
   its region of validity, and the candidate was re-fitted and re-landed.** ⛔ **AND IT PRODUCED A
   STRUCTURAL NEGATIVE THAT RE-SCOPES THE WHOLE ITEM — read the next block before doing any more
   ATTACK work.**

   ⛔⛔ **SESSION 99 — THE ATTACK REQUIREMENT AND THE OD PATH'S ABSOLUTE LOW-END LEVEL ARE IN
   CONFLICT IN THIS TOPOLOGY, AND EVERY PREVIOUS "REACHABLE" RESULT WAS BOUGHT BY SPENDING THE
   LEVEL.** This is the single most important thing on this item. Each winner scored on BOTH
   objectives, same targets, same instrument, same box sweep (the g-term change is the only
   difference, and the refactor is proven inert — see below):

   | winner | f0 rms | **width rms** | depth rms | **g rms** | LF residual cut/boost/flat dB |
   |---|---|---|---|---|---|
   | **s94** (no `g` at all) | 0.08 | **0.34** | 0.16 | 27.42 | **−42.4 / −41.9 / −41.5** |
   | **s97** (POOLED `g`) | 0.04 | **0.41** | 0.44 | 11.78 | **−22.8 / −22.4 / −21.9** |
   | **s99** (PER-SUB-BAND `g`) | 0.05 | **4.25** | 3.96 | **1.42** | **−1.4 / −0.5 / +0.0** |

   ⭐ **The conflict is SATURATED, not a weight choice: width rms is 4.07–4.66 in ALL TEN rows of
   the sweep — a span of 0.58 across a 100× range of `w_f0` AND a 3× wider box.** That is session
   57 item 4's own definition of unreachability, and `f0` is simultaneously excellent (0.05–0.93)
   and `g` simultaneously reachable (1.38–1.78), so it is specifically WIDTH+DEPTH that gives way.
   ⇒ **session 94's "the frontier reaches all nine numbers AT ONCE" and session 97's "the best
   ATTACK point the project has had" were both measurements of what a level-blind objective was
   willing to spend, not of what the topology can do.** ⚠ Do not read this as the new term being
   too strict — it is the earlier results being corrected.

   ⭐⭐ **AND THE REPAIR WORKS, ON THE RENDER, BY ITS OWN PRE-REGISTERED ACCEPTANCE TEST.** GATE H
   (`attack_d_extrapolation_gate.py`, re-run on the new candidate): the render's per-sub-band LF
   shortfall goes **+22.75 / +22.39 / +21.84 dB (s97) → +1.42 / +0.53 / −0.03 dB (s99)**. D-invariance
   at the candidate also improves, worst |D_cand − D_prop| **3.84 → 2.35 dB** (still over GATE F1's
   1.0 limit, so `g` is still an extrapolation here and GATE H stays a REQUIRED step).
   ⭐ The candidate is also the cleanest the project has produced on the identifiability axes:
   **0 of 17 values on a bound, realisable, worst shared ×15.8** — and **`C7` comes back to ×1.11**,
   i.e. essentially its drawn value, from s97's ×0.244 (the element session 94 attributed about half
   its matrix regression to). The tap is mild too (Ra ×0.835 against s97's ×0.1).

   **On the real render, stepped instrument both sides** (`analysis/reports/s99_attack_stepped_cand.json`):

   | | Δf0 Hz | Δdepth dB | width ratio | f0 spread (pedal 7.13) |
   |---|---|---|---|---|
   | s62 proposal | −6.18 / +1.46 / +4.41 | −0.98 / −5.73 / −0.03 | 1.66 / 2.70 / 2.00× | 17.72 |
   | s98 (s97 point) | −0.37 / −0.03 / −0.80 | −0.55 / −0.35 / −0.42 | 0.88 / 1.01 / 0.89× | 6.71 |
   | **s99** | **−0.40 / −0.10 / −0.76** | **+3.99 / +3.73 / +4.15** | **1.28 / 1.46 / 1.38×** | **6.78** |

   ⇒ f0 and its spread hold (the statistic the whole ATTACK spec rests on); **width and depth are
   what the level constraint costs**, confirmed independently of the screen.

   ⭐⭐⭐ **AND THE 129-CAPTURE MATRIX ACCEPTS IT — THE FIRST ATTACK CANDIDATE IN THE PROJECT'S
   HISTORY THAT IT HAS NOT REFUSED, AND IT BEATS THE SHIPPED BASELINE ON 8 OF THE 9 GATED
   OD/THD STATISTICS** (`analysis/reports/s99_attack_cand.json`, 504 shared rows, membership
   identical, CLEAN **bit-identical**):

   | | s91 shipped | s94 cand | s98 cand | **s99 cand** |
   |---|---|---|---|---|
   | OD band-RMS ex gain-n12 | 2.664 | 6.174 | 4.314 | **2.409** ⭐ |
   | THD (OD) level term | 4.279 | 18.685 | 9.466 | **3.663** ⭐ |
   | OD 25–100 Hz median / p90 | 1.024 / 6.065 | — | — / 20.958 | **0.860 / 4.971** ⭐ |
   | OD 100 Hz–8 kHz median / p90 | 0.742 / 5.089 | — | — | **0.568 / 4.458** ⭐ |
   | OD 8–16.3 kHz median / p90 | 0.662 / 8.076 | — | — | **0.566 / 8.058** ⭐ |
   | OD p99 | 14.408 | — | — | 14.661 ⚠ *(the only one worse)* |
   | CLEAN band-RMS | 0.453 | 0.453 | 0.453 | **0.453** (bit-identical) |
   | rows better >0.5 dB / worse | — | 6 / 178 | 25 / 142 | **111 / 36** ⭐ |

   ⛔⛔ **BUT READ WHAT IT ACTUALLY FIXED BEFORE CALLING GAP #2 CLOSED — IT IS NOT THE NOTCH.**
   The **320 Hz band, GAP #2's own headline, barely moves: mean |Δ| 9.54 → 9.21 dB** over the same
   320 OD rows. The gain is BROADBAND (biggest per-band moves: 4064 Hz −0.57, 32 Hz −0.54,
   3225 Hz −0.48, 160 Hz −0.47, 50 Hz −0.42). Measured bleed-free per sub-band, `pedal − render`:

   | render | LF 88–170 | LM 533–793 | M 805–1125 | HM 1137–1600 |
   |---|---|---|---|---|
   | **DRAWN default (SHIPPED)**, cut / boost / flat | +0.67 / **+10.90** / +2.33 | +2.78 / **+11.68** / +4.88 | +0.78 / **+10.69** / +2.77 | +0.12 / **+9.19** / +2.30 |
   | **s99 candidate** | +1.42 / **+0.53** / −0.03 | +2.48 / **+1.36** / +2.59 | −0.65 / **+0.50** / −0.56 | −1.83 / **+0.64** / −1.29 |

   ⇒ **the shipped default's real defect is that the ATTACK BOOST throw sits 9–12 dB light at every
   sub-band, and that is what this candidate fixes** (cut was already right and stays roughly so;
   flat improves). ⇒ **this is an OD-path ABSOLUTE-LEVEL fix that happens to live in the ATTACK
   ladder — it is NOT a 320 Hz notch fix, and item 4's notch requirement is still unmet** (width
   1.28–1.46×, depth +4 dB). Do not book it against GAP #2.

   ⚠⚠ **NOT SHIPPED — THIS IS A USER DECISION AND IT IS A BIG ONE.** It moves **17 fitted
   constants** in the treble ladder (R7 ×8.23, R12 ×3.99, R14 ×2.20, C5 ×0.40, C9 ×0.58,
   **C6 ×0.063**, C7 ×1.11, plus the tap and the three damping resistors) for a **0.255 dB**
   headline gain plus **0.62 dB of THD level**, while *failing* the requirement it was built for.
   That is squarely "breaking the schematic" (authorised in principle, session 51) and is the same
   class of judgement call session 91's two constants were — so it goes to the user, not in
   unilaterally. ⭐ In its favour: it is the cleanest candidate the project has produced —
   **0 of 17 values on a bound, realisable, worst shared ×15.8**, C7 essentially back at its drawn
   value — and every gate it has been put through passes.

   ⭐ **WHAT CHANGED IN THE TOOL, and every piece of it is gated.** `g_of`/`g_targets`/
   `abs_gain_record` now return one value per throw **per sub-band** — 4 bands tiling `G_BAND`
   exactly (8 + 23 + 28 + 41 = 100 bins), cut on the real line so the tiling is by construction.
   `--g-pooled` restores the pre-99 single median as a ONE-element partition, i.e. the control runs
   the same code path rather than being a second implementation.
   ⚠ **The TARGET is per-sub-band too, and that was not optional**: measured, Delta runs
   **+8.3…+12.4 dB** across the four bands (4.55 dB spread against the term's 1.0 dB floor), so
   re-using the pooled figure would have injected up to 3.7 dB of systematic error into exactly the
   LF band the repair exists to expose.
   **Gates, all computed:** `--g-selftest` mutation-tests the partition four ways (dropped band /
   overlap / extra band / gap — all refused) and then proves the refactor **INERT**: `--g-pooled`
   re-scores the stored s97 winner through the rewritten vectorised path at **g_rms 0.189629 against
   the stored 0.189624 (|diff| 4.83e-06)**, while the sub-band partition reads **11.78 — 62.1×** on
   the same ladder. **GATE F2** is now per sub-band; **F5** is new and demonstrates the blind spot on
   a KNOWN ANSWER rather than a synthetic mutation (the pooled median absorbs **1.6 %** of what the
   sub-band residual sees on the very ladder the matrix rejected).
   **GATE F4** is new (session 98's item 3): F1 compares two MILD ladders, so it is an
   INTERPOLATION check that was being relied on as an EXTRAPOLATION guarantee. F4 measures the
   envelope against the one WILD ladder already rendered and prints it — invariance holds to
   **0.183 dB out to 0.23 decades** and degrades to **3.84 dB at 1.00** — and `best_point` now
   reports its winner's ladder distance against that limit **at selection time**. ⛔ **F4 does NOT
   close the hole and says so in its own output**: the complete check needs a render of the actual
   candidate, which is GATE H, and that stays required before any matrix run.
   ⚠ GATE H's H3/H4 have SWAPPED ROLES to match: H3 now tests the per-sub-band promise (the shipped
   term) and the pooled median is kept as a labelled CONTROL, so pre-99 quotes stay reproducible.
   Its duplicate `FIT_MAP`/`parse_fits` and ad-hoc sub-bands are gone — both now come from
   `attack_shape_screen` (`ladder_from_fits`, `G_SUBS`), one definition.

   ▶ **NEXT — and the first one is a DECISION, not a measurement.**
   (1) ✅✅ **DONE, SESSION 100 — SHIPPED.** The user re-authorised breaking from the schematic, which
   was the whole objection, and the 17 constants are in `FitParams.h` with full provenance. Acceptance
   check passed (shipped defaults bit-identical to the `--fit` list at all three ATTACK throws, with a
   mutation control); ctest still 16/17, same pre-existing failure. See the session-100 block in
   "Where we are". ⚠ **Item 4's NOTCH requirement is still UNMET and this did not close GAP #2** —
   the 320 Hz band moved 9.54 → 9.21 dB. Do not book it there.
   (2) ⭐ **THIS IS NOW THE HEAD OF ITEM 4.** If the notch itself is still wanted, **it is a TOPOLOGY
   question, not a fitting one** — the conflict table above says no point in this family reaches both
   the notch shape and the absolute level, so the next move is the **missing degree of freedom**, not
   another search. ⛔ Do not point another optimiser at this topology expecting a different answer;
   the saturation is measured (width rms 4.07–4.66 in all ten rows of a 100×/3× sweep).
   (3) ⚠ `g` remains an EXTRAPOLATION at any winner this search produces (ladder distance 1.20 dec
   against F4's tested 0.23), so **GATE H stays a required step before any matrix run** — it is
   cheap (6 renders) and it is what caught the s97 point.
   ⛔ Do NOT reach for `--floor`: session 98 measured that the box does not bind (GATE G), and
   session 99's winner rests **nothing** on a bound, which retires that line of enquiry entirely.
   ⚠ Two tool defects were found and fixed in session 98 in passing, both of which had CHANGED a
   printed conclusion: `best_point`'s ranking key quantised f0 but not width (picked R7 ×28.6 /
   C6 ×200 over R7 ×5.2 / C6 ×9.9 on a 0.1 %-of-width difference), and `attack_stepped_gate`'s swap
   verdict scored the candidate, so a SUCCESSFUL fit printed "the prediction is REFUTED, re-scope
   item 4". The verdict is now scored over the reference variants only.

   ---
   *Session 93's re-scoping, kept because it is what made the above measurable:*
   ⭐⭐ **RE-SCOPED SESSION 93 — the two-pole ATTACK re-fit.**
   The topology is already in `src/` (defaults to the drawn network). Addresses the **+26 dB @ 320 Hz**
   band, the largest single-band error in the matrix.
   ⛔⛔ **THE ARBITER WAS MEASURING THE TWO SIDES WITH TWO DIFFERENT INSTRUMENTS, AND NO RE-FIT COULD
   HAVE BEEN TRUSTED UNTIL THAT WAS FIXED.** Session 70's corrected spec is a **stepped-sine** read;
   `attack_render_gate.py` reads the RENDER with the old **swept** one (5.86 Hz CSD). The
   instrument-only delta at boost is **−29.1 % width / +5.28 dB depth** — the whole size of the
   residual being fitted. **New `analysis/attack_stepped_gate.py`** renders through the stepped
   stimulus and reads it with the stepped locator, so both sides share an instrument; 5 computed
   gates, and its pre-registered prediction held (pedal boost narrows −29.1 %, reproducing s70 to
   0.1 %; the render **WIDENS +11.1 %**, because smearing scales with how narrow the feature is).
   ⭐ **It changes a CONCLUSION, not just a scale:** width ratio worst throw is **flat (1.98×)** under
   swept-vs-swept and **boost (2.70×)** under stepped-vs-stepped — and that is exactly what selects a
   SHARED ladder element vs a per-throw one. Corroborates s70 item (5)(b) on unshared machinery.
   ⭐⭐ **AND THE BIGGEST MISS IS f0 SPREAD, WHICH WAS CONSIDERED CLOSED.** In matched units the s62/63
   proposal reads **spread 17.72 Hz against the pedal's 7.13 (2.49× too wide)**; depth cut/flat
   −0.98 / −0.03 dB (fine), depth boost **−5.73 dB**; widths 1.66 / **2.70** / 2.00×. Session 63's
   "met the requirement TO THE BIN" was true only against the superseded 17.58 spec — a 0.14 Hz
   match, which is why it read as solved. ⇒ **this is not a width-only problem and never was.**
   ▶ **Next:** point `attack_shape_screen.py`'s `screen_targets` at the stepped record **and
   re-derive its calibration** (`render_cal` currently maps screen units onto the SWEPT render; the
   CAL ladder point needs 3 renders through the notch stimulus), then `--fit --best` → land on
   `attack_stepped_gate.py` → the 129-capture matrix. ⚠ Session 64 recorded f0-spread and width as in
   CONFLICT inside this topology at fixed f0, and the corrected spec **tightens both at once**, so a
   NEGATIVE reachability result is a live outcome — report it, do not fit around it. ⚠ The shipped
   DEFAULT has no null at all (3.1–3.3 dB deep, width `nan` by construction, f0 railed at the 380 Hz
   window edge — a bound, not a measurement), which is session 57's finding, not a bug.
5. **A3 — ONE timeboxed attempt (user decision, session 89).** ≈5–7 dB OD-vs-bleed imbalance over
   100–400 Hz, corroborated by two instruments sharing no machinery (sessions 85/86). Session 50
   proved no single element closes it; session 52 proved no *post-clipper linear* element of any order
   does; session 53 inverted the post-clipper restriction. **The only region not ruled out is
   inside/before the clipper** (`Clipper.h:309` — `a0` has no frequency dependence and the inverter no
   output impedance, both derivable from the DAFx-2020 two-MOSFET model). **Hard stop at one session**,
   then fall back to a fitted correction network (the user authorised breaking the schematic in
   session 51).

   ⛔⛔ **RE-SCOPED AGAIN IN SESSION 108 (GATE P) — AND THIS TIME IT IS THE *TARGET* THAT FALLS,
   NOT THE SCOPE. THE TIMEBOXED ATTEMPT HAS BEEN PARTLY SPENT, ON ESTABLISHING THAT TARGET.**
   A3's 5.1–5.5 dB is a **window mean over a migrating feature**: its two dominant bands (320, 254
   Hz) are also its two least reproducible, it carries **±1.10 dB** of never-printed operating-point
   spread, and no band is both feature-free and agreed on by the four pairs, so the pedestal/feature
   split is **unmeasured**. A static broadband gain (+4.66 dB, *not* 5.1) buys **5.48 → 2.86 dB rms**
   and cannot close it — corroborating session 50/52's exclusions rather than escaping them.
   ⛔ **Do not fit a constant to 5.1–5.5 dB.** ⚠ A3's SIZE and GATE O's ATTRIBUTION are untouched;
   the OD path is still quiet. Full detail and the three-way decision in the SESSION 108 block.
   *(The session-105 re-scope below stands and is what GATE P refines.)*

   ⭐⭐⭐ **RE-SCOPED AGAIN IN SESSION 105 (GATE M) — AND THIS IS THE ONE THAT CHANGES WHAT THE
   TIMEBOXED ATTEMPT SHOULD AIM AT. READ IT BEFORE OPENING THIS ITEM.** Two corrections to what is
   recorded below, both measured, full detail in the SESSION 105 block in "Where we are":
   **(i) the SIZE.** K7's headline pools 5 pairs and **one of them is `level-1700_gain-n12`**, the
   session-48 capture defect. Excluded, A3 reads **3.4 / 4.4 / 4.8 / 5.1 dB** (was 3.1/4.1/4.6/4.9)
   — **larger**, so nothing is at risk, but quote the excluded figure.
   **(ii) ⛔ the SCOPE NOTE BELOW ("K7 says the defect is a level one … do not re-run those
   searches") IS REFUTED.** K7 means over 25 bands; the curve under it spans 9–14 dB and its
   shape/offset ratio is **0.47–0.90 on every band selection**, against the 0.25 bar GATE K5 itself
   used to justify that phrase. The shape is coherent across all four pairs (leave-one-out
   r = +0.64…+0.89), so it is structure, not noise.
   ⭐⭐ **A3 is TWO defects: (A) a stimulus-INDEPENDENT ≈5.1–5.5 dB term over 100–400 Hz** (spread
   0.47 dB across four stimulus levels — this IS §1's recorded figure, corroborated now by a third
   instrument, and it IS offset-dominated in its own band); **and (B) a stimulus-DEPENDENT term at
   508–1016 Hz swinging 5.4 dB with drive**, peak migrating 254 → 640 Hz. K7's mean rising with
   stimulus is the **mixture**, not A3 growing.
   ▶ **Aim the timeboxed attempt at (A) only**, and gate the candidate on leaving (B)'s drive
   dependence alone. ⚠ **Sessions 50/52/53 are NOT re-opened** — they ruled out single elements and
   all *post-clipper linear* elements; a drive-dependent structure is outside both searches, and is
   consistent with this item's own "the only region not ruled out is inside/before the clipper".

   ⭐⭐ **RE-SCOPED AGAIN IN SESSION 104 (GATE L), AND THE NET EFFECT IS THAT A3 GETS *STRONGER*
   EVIDENCE AND A *SMALLER* CLAIM.** Stronger: L8 shows the model's above-noon H1 fall — which K3
   had booked as a separate downstream-saturation defect — is A3 seen through the mixing network's
   bleed turnover, predicted by a strictly linear network from each side's own measured ratio
   (model −2.74 predicted vs −2.20 measured; pedal +0.28 vs +0.84). So A3 now has **two**
   independent absolute consequences, not one. Smaller: A3 is **NOT** the lever that closes the
   LEVEL law — GATE L4/L5/L6 measured that the shipped network cannot express the pedal's ladder
   under any taper and any bleed, so no balance correction can close it. ⚠ **Do not sell an A3 fix
   on the LEVEL law.** A3 itself is untouched: K7 measures it at the two exact-zero endpoints where
   no model form is involved.

   ⭐⭐⭐ **RE-PROMOTED IN SESSION 103 — THE SESSION-102 DEMOTION BELOW IS NOT WRONG, BUT IT
   ANSWERED A DIFFERENT QUESTION.** GATE K7 measures the OD-vs-clean balance **directly and
   absolutely** (pure-clean vs pure-OD captures, no fit, no gain match) at **3.1–4.9 dB hot**, on a
   third instrument sharing no machinery with sessions 85/86 — and it is the lever the LEVEL control
   law needs, which a taper cannot supply. ⚠ **Read the two results as compatible, because they
   are:** session 102 decomposed the **gain-matched** midband residual and correctly found A3's
   100–400 Hz band the best of three; A3's real signature is an **absolute level** error, and a
   per-row gain match removes exactly that. ⇒ the demotion measured A3's contribution to a statistic
   that is blind to it. ⚠ **And the SCOPE changes with the promotion:** sessions 50/52/53 ruled out
   single elements, all post-clipper linear elements, and inverted the restriction — all searches
   for a *frequency-shaping* fix. K7 says the defect is a level one. Do not re-run those searches.
   *The session-102 text is kept below because its measurement stands; only its priority verdict is
   reversed.*

   ⛔⛔ **SESSION 102 MEASURED WHETHER THIS IS STILL THE RIGHT NEXT SPEND, AND IT IS NOT — A3's OWN
   BAND IS THE BEST OF THE THREE MIDBAND SUB-BANDS, NOT THE WORST. DO NOT OPEN ITEM 5 EXPECTING IT TO
   BE THE REMAINING STORY.** GATE J (`analysis/od_residual_localise.py`, no render — a re-read of
   `s99_attack_cand.json`) decomposed the shipped OD residual. Inside the widest failing gate row
   (OD 100 Hz–8 kHz), pooled RMS by sub-band:

   | sub-band | bands | median | p90 | rms |
   |---|---|---|---|---|
   | **100–400 Hz** *(A3's own region)* | 6 | 0.614 | 4.069 | **2.321** |
   | 400–1600 Hz | 6 | 0.255 | 5.010 | **2.978** |
   | 1.6–8 kHz | 7 | 0.888 | 4.490 | **2.922** |

   ⇒ the midband residual is **flat-to-slightly-better** at 100–400 Hz. ⚠ And the bleed
   discriminator (J8) says the same thing: the bleed-free/blended error ratio is **3.70 at
   100–400 Hz against 9.94 at 400–1600 Hz** — i.e. the OD-vs-bleed imbalance A3 describes is real
   but is **broadband and largest OUTSIDE A3's band**, so "≈5–7 dB over 100–400 Hz" is a correct
   description of a *sub-region* of a wider defect, not a localisation of it.
   ⭐ This does not retract sessions 85/86 — those measured A3 on the harmonic and drive axes and
   their corroboration stands. What has changed is **priority**: two better-localised effects now
   outrank it (see the session-102 block in "Where we are").
6. ⭐⭐ **DONE, SESSION 92 — IT IS GENUINE ALIASING. The instrument was rebuilt and gated first, and
   the "instrument defect" hypothesis is REFUTED.** `analysis/alias_gate.py` (6 known-answer gates,
   `--selftest`); `tests/OSValidationTest.cpp` rebuilt on the same geometry and the two agree to
   **0.1 dB** across the whole amp × factor table without sharing any code.
   ⭐ **Two of the three things the old metric reported WERE artefacts, and neither was the movement.**
   (a) The **−40.5 dB "floor"** printed in twelve cells for 46 sessions is the metric's own window
   leakage: f0 = 2500 Hz against a 2.9297 Hz bin is 853.33 bins, so off-grid harmonics leaked past
   the ±3-bin mask. On a synthetic signal with ZERO alias content, bin-exact reads −99 dB and
   off-grid reads **−40.65**. True floor at those points: **−86 dB**. (b) The 0.3 s settle left
   `MasterOut`'s 0.72 Hz high-passes ringing, but measured, that LF bucket sits **12–15 dB below**
   the alias bucket everywhere — a real trap that happened not to be the culprit here.
   ⭐⭐ **(c) What is left is fold-down, established three ways.** The dominant inharmonic bins land on
   `|N·f0 − m·(factor·fs)|` **to the bin** at three different f0 (H152–156 at 2499 Hz, H190/193 at
   2001 Hz, H117–120 at 3249 Hz) — moving f0 is what breaks the degeneracy with a beat note, which
   predicts the same bins at any single f0. A **192 kHz-base render** (1.536 MHz internal) reads
   **−65.9 dB** where 48 kHz/8× reads −17.1. And `railEnabled=0` moves it 1.5 dB, so the rails are
   not the carrier — the **un-ADAA'd CD4049 VTC** is (the J201 already carries closed-form ADAA,
   `PedalChain.h:139`).
   ⚠⚠ **⇒ `jfetSatNeg = 1.9` HAS A MEASURED COST OUTSIDE THE MATRIX, AND IT IS NOT CONFINED TO ONE
   UNLUCKY TONE.** Over 21 bin-exact fundamentals at amp 0.35: **8× median +1.87 dB, worst +13.6 dB**
   of extra fold-down; **2× median +0.05 dB** (free). At the reverted value the same rows read
   −69.7 median / −15.7 worst, i.e. **the defect long predates session 91** — 1.9 makes an existing
   problem worse, it does not create one.
   ⭐ **The saving grace is where it lives:** at 8× the alias floor is **−85…−115 dB for every
   fundamental below 1.5 kHz** — the whole of a bass guitar's fundamental range — and collapses to
   −17…−26 dB only above ~2.3 kHz. At the shipped realtime default of **2× it is −15…−28 dB
   everywhere above 600 Hz regardless**, so 2× is the bigger exposure and the constant is irrelevant
   there. ⚠ Single-tone stress test, not programme material: do not quote −17 dB as "what the plugin
   does to a bass note".
   ⚠⚠ **AND A SECOND, UNRELATED DEFECT FELL OUT OF A CONTROL: AT 8× THE CHAIN IS APERIODIC AT 4 OF
   21 TONES.** A tone bin-exact in M through a time-invariant chain must give an output that repeats
   exactly every M samples. Measured (`--periodicity`): **2× is exactly periodic at 21/21 tones at
   both constants**; **8× is not, at 4/21, all above 2.8 kHz, worst 0.69 (69 % RMS non-repetition)** —
   and 4/21 at the PRIOR constant too, so session 91 did not cause it. At those points the spectrum
   **cannot be read as aliasing** and more oversampling makes it worse, not better. ⚠ 8× is the
   offline-render default and **the 129-capture matrix renders at OS = 8** — check this before the
   next matrix baseline. ⭐ The gate row (f0 = 2499 Hz) is periodic to 5.3e−9, so the fold
   attribution above is unaffected exactly where the failing test sits.
   ✅ **DECIDED WITH THE USER, SESSION 92 — `jfetSatNeg = 1.9` STAYS.** The cost is 8×-only and
   confined above 2.3 kHz where no bass fundamental lives; it is free at the shipped 2× realtime
   default; the benefit (THD level 6.202 → 4.279, plus the low-drive even-order structure hardware
   demands) is on the authoritative axis; and the defect predates it. **Do not re-open this on the
   alias number alone.**
   ✅ **AND THE PHASE 10 B ORDER IS SET: (1) the aperiodic regime, (2) ADAA the CD4049 VTC.** Raising
   the OS defaults was considered and rejected — 2× is uniformly −15…−28 dB above 600 Hz and 8× is
   the factor carrying the aperiodicity, so "more oversampling" is not monotonically better here.
   ⭐⭐ **ITEM 1 IS ALREADY LOCALISED TO `Clipper::process`, WITH TWO NAMED CAUSES** (session 92,
   bisected then confirmed by temporary edits that were measured and **reverted** — `git diff
   src/dsp/Clipper.h` is clean). It needs high loop gain AND high drive: `clipA0` 24.871 → 18 or
   below is exactly periodic at every tone, `--drive` 0.6 or below likewise, `clipK` is irrelevant,
   and `--blend 0` (clipper out of circuit) is the 0.00e+00 control.
   **(a) `kNewtonIters = 6` is not converged at the 384 kHz internal rate** — at 60 iterations two of
   the four aperiodic tones become exactly periodic and the gate tone's alias figure moves
   −17.05 → −17.40 dB. **(b) The D1/D2 clamp fires and is applied OUTSIDE the solve**
   (`Clipper.h:270–273` hard-clips the solved node, then feeds it to the companion-cap state update):
   at 60 iterations *with the clamp disabled*, **20 of 21 tones are exactly periodic** and f0 = 3000
   collapses to −3069 dB, the degenerate value the arithmetic demands. ⚠ That contradicts the stage
   header's "D1/D2 essentially never fire (the test asserts it)" — `ClipperTest` must be probing a
   gentler point. ⛔ Deleting the clamp is not the fix (D1/D2 are real parts); folding the diodes
   INTO the Newton system is. Both fixes change every rendered sample ⇒ matrix re-baseline required.
   Artefacts: `analysis/reports/s92_alias_gate.json`, `s92_alias_sweep.json`,
   `s92_alias_periodicity.json`.
7. ✅ **The CLEAN bar re-derivation is DONE (session 96 — the row split; see the gate section).** It
   was the one open gate DECISION and it no longer blocks a clean "Phase 9 closed". Remaining here:
   **A4 re-grade + the GATE-9 report**, then **Phase 10**: B (perf/HQ pass, which now owns item 6),
   C (carry-forwards incl. the VU idle gate vs makeup 2.599), D (release).
   ⚠ **Phase 9 is still open on the MODEL, not on the gate** — 8 gated rows remain over SHIP (every
   OD row plus THD level 4.279 vs ≤3.0). CLEAN passing is not Phase 9 closing.

### Standing rules that must not be lost

- ⚠⚠ **`analysis/captures/` is a recording of the NEURAL DSP plugin, not hardware.**
  `.claude/rules/reference-sources.md` is the authority rule — read it before treating any capture
  number as ground truth, and before calling a move away from the captures a regression.
- ⭐ **The generalisable measurement traps are collected in
  `.claude/rules/measurement-discipline.md`.** ~40 of them, each one paid for by a real session.
- ⭐⭐ **Session 89 — the HF OD error is REAL, LOCALISED and TRACTABLE.** All twelve worst OD rows are
  the same band, all on `level-1700` rows where the clean bleed is exactly zero by topology, so the
  measurement IS the raw OD path. There ND's OD path *gains* 24 dB at 12.9 kHz as drive rises
  (−15.3 clean → +9.0 at `sweep_drv_-6`) while ours rolls off — which is what the two
  schematic-verified Sallen-Key LPFs (10.7 kHz, 3.3 kHz) must do. On `ref-od` (bleed present) the two
  sides agree to **0.4 dB**, because the bleed masks it on both sides.
  ⛔ **DO NOT dismiss this as "ND aliasing" — that is not established and it is not a reason to skip
  the band** (user, session 89).
  ⛔⛔ **SESSION 90 SETTLED HALF OF IT, AND THE ANSWER IS NEGATIVE: PREMISE (a) IS REFUTED — THE FR
  INSTRUMENT WAS NOT LYING, AND "our instrument is contaminated" IS NO LONGER AN ALTERNATIVE TO
  "the model is wrong here".** Session 89 argued that because `transfer()` is a CSD estimate rather
  than a Farina H1 separation, "ND aliases" and "our FR read is contaminated" were indistinguishable.
  Measured, on the same 129 renders, with all three reads stored per row so membership is identical
  by construction (`release_gate.py --compare csd h1 h1band`):

  | statistic | CSD (old) | H1 (harmonics rejected) | H1 band-avg (shipped) |
  |---|---|---|---|
  | OD band-RMS | 2.95 | **2.99** | 2.70 |
  | OD 8–16.3 kHz p90 | 8.73 | **8.50** | 8.07 |
  | 12901.6 Hz max, OD | 36.18 | **35.32** | 33.23 |

  ⇒ **rejecting the harmonics changes the HF tail by 0.1–0.9 dB and makes the headline slightly
  WORSE.** What little improvement there is comes from BAND-AVERAGING, a sampling choice, not from
  order separation. ⭐ And the known-answer gate says why, which is the generalisable part: an
  exponential sweep already separates orders **in time** (~1 s per octave here) against a 170 ms
  Welch window, so a harmonic and the fundamental at the same bin never share an analysis window.
  `h1_fr_gate.py`'s KA-2 puts H2/H3 at a brutal −10/−14 dB re the fundamental and **the CSD passes
  it too**. ⚠ The one mechanism that does defeat both instruments is an alias folding **onto** the
  fundamental at f = FS/(N+1) — 16.0 kHz (H2) and 12.0 kHz (H3), i.e. exactly the top two graded
  bands — which is coincident with the fundamental in BOTH time and frequency and is a limit of the
  STIMULUS, not of either estimator (KA-5). That is the only surviving measurement-side explanation
  and it cannot be fixed by a better read.
  ⇒ **Session 89's step (b) is now the whole question: is the residual ND's artefact or our
  Sallen-Keys?** Do not spend another session on the FR instrument.

  ⭐⭐⭐ **ANSWERED, SESSION 101 — IT IS ND's, NOT OUR SALLEN-KEYS, AND THE ARGUMENT IS A RATE, NOT A
  LEVEL.** `analysis/hf_artefact_gate.py` (**GATE I**, 4 sub-gates, exits non-zero, no render — it
  reads the stored `h1band` values plus the capture wavs). The user's session-89 instruction ("DO NOT
  dismiss this as ND aliasing — that is not established") is now discharged by measurement.
  ⭐ **G1, the control that makes the rest readable:** on the CLEAN path (BLEND 0, OD out of circuit)
  our 16255 Hz response matches the pedal to **0.57 dB** and is **bit-invariant across all four
  stimulus levels** (spread 0.00). So our linear HF response is already right, and nothing nonlinear
  being engaged means the instrument is not level-dependent.
  ⭐⭐ **G2, the finding — the ROLLOFF RATE over the 8127.5 → 16255 Hz octave** (a rate is immune to
  the per-row gain match, to the anchor band, and to how hard the clipper is working — and **a linear
  filter has exactly ONE rate**):

  | condition | clean stimulus | drv_-6 |
  |---|---|---|
  | CLEAN path (BLEND 0) | pedal +0.4 / model −0.1 | pedal +0.4 / model −0.1 |
  | OD, LEVEL max, DRIVE min | pedal −7.1 / model −22.2 | pedal **+3.5** / model −21.4 |
  | OD, LEVEL max, DRIVE noon | pedal −13.1 / model −20.1 | pedal **+4.8** / model −22.3 |
  | OD, LEVEL max, DRIVE max | pedal −13.7 / model −18.9 | pedal **+3.4** / model −18.7 |

  ⇒ the pedal's rate spans **18.5 dB/oct** with drive and turns **POSITIVE** — its OD path *gains*
  with frequency across an octave where two post-clipper 2nd-order LPFs are in circuit. Ours holds
  −14.7…−23.1, i.e. the drawn network. **A drive-dependent rate is not a filter**, so no Sallen-Key
  value can be the cause. ⇒ ND fills its top octave with drive-generated non-harmonic content that
  survives Farina H1 gating — the "dense inharmonic content that reads as aliasing" already recorded
  in `reference-sources.md` §4 for high drive, now measured on the **FR** axis and quantified.
  ⚠ **The reference rate is DERIVED, not asserted: −18.25 dB/oct**, computed from the two
  schematic-verified Sallen-Keys (IC4_B 10.7 kHz, IC4_A 3.3 kHz). The textbook **−24** asymptote is
  WRONG here — at 8127.5 Hz the pair is not yet past the 10.7 kHz corner — and asserting it gave G2a
  a **false FAIL** on its first run against a correct model.
  ⭐ **G3 refutes session 90's own KA-5 mechanism at H2**, the only place it could explain the 16255
  band: the drive-induced excess passes through 16000 Hz with prominence **−0.03 dB** (30th
  percentile of a non-locus null), inside a plateau flat to **0.73 dB over 6 kHz**. ⚠ NOT tested at
  H3/H4 — thin null, curvature-biased — so that is OPEN, not negative.
  ⛔ **NOT claimed: that the region is ENTIRELY artefact.** At the *lowest* stimulus level the pedal
  reads −13.7 dB/oct against our −18.9, a real ~5 dB/oct gap; and the **8127.5 Hz band's error is
  drive-INDEPENDENT** (≈ −6 dB at every level), i.e. a separate genuine linear defect that a blanket
  8–16.3 kHz exclusion would excuse.
  ⚠⚠ **AND THE GATE CONSEQUENCE IS SMALLER THAN IT LOOKS — G4 computed it on BOTH baselines.**
  Dropping all four HF bands moves OD band-RMS **2.409 → 2.005** (bar 2.0 — still over), p99
  **14.661 → 10.281** (bar 4.0 — still far over), and the OD **median gets WORSE, 0.625 → 0.636**,
  because the HF bands were diluting it downward — session 91's exclusion trap, second occurrence.
  ⇒ **excluding the region closes ONE of the eight failing rows, not Phase 9**, and p99 is
  emphatically *not* an HF story. **Whether the gate should still grade these bands is a USER
  DECISION** (same class as the session-91 CLEAN pool change and the session-96 row split) and was
  NOT taken unilaterally.
  ⚠⚠ **AND WIDENING THE RANGE MADE THE TAIL WORSE, NOT BETTER** — 11 of the 12 worst OD band values
  are now **16255 Hz**, not 12901.6: p90 **16.6 dB**, max **40.2**. The 8–16.3 kHz p90 of 8.07 is an
  average of a fine 12.9 kHz and a bad 16.3 kHz. Session 89 expected the repair to shrink this row;
  it did the opposite, and the newly-graded band is now the single worst in the matrix.
  ⭐ The OD **median** at 8–16.3 kHz is **0.68 dB** and MEETS its SHIP bar — it is the TAIL that
  explodes, so this is a subset of rows failing badly, not a noise floor.
- ⚠ Never quote a matrix total without its capture count; membership changes have faked a regression
  seven times (`aggregate-moved-check-membership-first`).
- ⭐⭐ **THE 129-CAPTURE MATRIX IS BLIND TO ANY PURE LEVEL ERROR, AND SESSION 103 MEASURED HOW BIG
  ONE CAN BE: 9.3 dB.** `comprehensive_report` fits a per-row broadband null gain and adds it to
  `plugin_db` before anything is differenced, so band-RMS, every region median/p90, and the THD
  terms are all downstream of it. At LEVEL 0.125 that gain is **+9.03 dB** — it removes the defect
  exactly. ⇒ **a control-LAW question (pot taper, divider end-stop, path-to-path balance) must be
  asked with GATE K's matched-pair, no-gain-match instrument, and the matrix must not be quoted as
  the arbiter.** The captures have full authority here (`reference-sources.md` §1: absolute level,
  gain staging).

### Uncommitted at session 114

⚠ **SESSION 114 touched NEITHER `src/` NOR `tests/`** — one analysis tool rewritten, one new mutation
runner, and docs, so ctest is untouched and still 16/17 (the same pre-existing `OSValidationTest`
failure) and **no DSP constant moved**. `git diff --stat -- src tests` is exactly sessions
91/92/100/109's four files, unchanged. **No render was run and no baseline moved**:
`analysis/reports/s113_baseline.json` is still the grade, and every number is a re-read of it plus
the capture wavs.

⚠ **It DID re-render**, because the send-pad correction is in the per-capture cache key:
**`analysis/reports/s114_baseline.json` (162 captures) is THE NEW BASELINE** and supersedes
`s113_baseline.json`. 120 of 165 came from cache; only the gain-session captures re-rendered.
⚠ Three `_gain-n18` captures still FAIL `comprehensive_report` with "no measured delta for gain
session −18 dB" — **pre-existing**, unchanged by this session (`_GAIN_SESSION_MEASURED_DB` has no
−18 entry). They are the MASTER-ladder-top probe files from s112, outside the matrix grammar's
grading path; flagged for whoever opens the MASTER taper item (Phase 10 C). ⭐ Session 112 measured
that pad at **6.000 dB exactly**, so the entry is available when someone wants it.

Changed: **`analysis/captures.py`** — `_GAIN_SESSION_MEASURED_DB[-12]` 12.071 → **12.000**, with the
full provenance at the constant (why the old pair is inadmissible, the three corroborating
instruments, and why the matrix cannot see the change).
**`analysis/release_gate.py`** — the THD row **split by operating point**: new `THD_ROWS`,
`thd_level()` now returns a list of `(label, rms, n)` and hard-exits on an empty sub-population
(`empty-gate-must-fail`), `print_report()` grades both rows against the same unchanged 3.0 bar and
prints why the split exists; the stale "two OPPOSITE-signed populations" caption is corrected in
place (at s114 the group reads +0.032, not −0.772). `--ex-gain-n12` still reproduces the pre-s114
single row exactly.
**`analysis/hf_artefact_gate.py`** — GATE I rebuilt (see the session-114 block in "Where we
are"). New `gate_membership()` = **G0**, asserted membership that exits rather than warns;
`classify()` resolves classes from **SETTINGS** instead of a filename substring (fixing the three
defects: intermediate-BLEND rows in the bleed-free OD classes, `gain-n12` twins pooled with
full-send, and a MASTER-only duplicate double-weighting one condition); new `condition_key()` +
`DUP_TOL` and a rewritten `collect()` that collapses MASTER-only duplicates to one vote, **asserts
they agree** (1.16e−07 dB/oct — a free known answer), and picks the representative by **usable data**
rather than filename order; `RATE_TOL` **retired** with its provenance recorded at the constant;
`gate_rate()`'s G2a/G2b/G2c replaced by the never-gains / complete-separation / dose-response trio,
with the per-cell spread printed beside every median (s108 P4); the module docstring's G2 paragraph
and the two stale VERDICT lines corrected in place rather than left to narrate the retired claim
(`computed-verdicts-not-narrated`).
**NEW `analysis/_mutate_gate_i.py`** — 10 mutations plus an unmutated CONTROL, each needle asserted
present exactly once.
**`CLAUDE.md`** (the session-114 block; the session-111 GATE I diagnosis marked SUPERSEDED with its
original text kept; session 113's NEXT item 6 marked DONE; this block) and
**`.claude/rules/measurement-discipline.md`** (four entries).

New artefacts, gitignored/regenerable: **`analysis/reports/s114_baseline.json` (THE NEW BASELINE,
162 captures)**, `analysis/fit_logs/s114_baseline.log`, `analysis/reports/s114_hf_artefact.json`.

⭐ **Full gate sweep re-run on the NEW `s114_baseline.json`**: `matrix_grade`, `shape_gate`, GATE I,
J, K, L, M, N, O, P, Q, R, S all **rc=0**; `release_gate` exits 1 for the expected reason —
**7 rows over SHIP, was 6**, the extra one being the THD split telling the truth about its own
population rather than the model regressing.
⚠ **GATE I comes OFF the "still fails" list** it has been on since session 109 — and the reason is
that the guard was wrong, not that anything was fixed in the model.
⚠ `analysis/null_locus_gate.py` (GATE R) takes `--report PATH`, not a positional argument; a sweep
that passes the report positionally gets rc=2 from argparse and it is **not** a gate failure.

---

### Uncommitted at session 113

⚠ **SESSION 113 touched NEITHER `src/` NOR `tests/`** — two new analysis tools and docs only, so
ctest is untouched and still 16/17 (the same pre-existing `OSValidationTest` failure) and **no DSP
constant moved**. GATE S **modifies no shared module** — it imports `level_law_gate`,
`gain_session_gate`, `od_absolute_gate` and `matrix_grade` and changes none of them, so it is
purely additive.

⚠ **UNLIKE MOST GATE-ONLY SESSIONS, THIS ONE DID RENDER — the user captured a file mid-session at
this session's own request.** `analysis/reports/s113_baseline.json` (**THE NEW BASELINE, 162
captures**) supersedes `s112_baseline.json`. Membership is a strict superset: **+9 captures, 0
lost** — `drive-1700_level-1700_gain-n12_base-od.wav` (the requested one, GATE S's own blocker) plus
8 EQ captures (`bass`/`himid`/`lomid`/`treble` at 9-o'clock/3-o'clock, `_base-od`) the user added
independently as a hedge against the closing capture window (their words: "an EQ affecting
distortion capture in case we ever needed them after I lost access to more captures") — nobody has
used those 8 yet and no claim is made about what they show.
⭐ **Acceptance check, run before anything else was trusted**: GATE S's own S3 interlock on the
requested capture reads **0.00009 dB** — inside the 0.0099 dB take-to-take floor, i.e. genuinely
matched, not another mis-dialled pair.
⭐ **Full gate sweep re-run on `s113_baseline.json`**: `matrix_grade`, `shape_gate`, GATE J, K, L, M,
N, O, P, Q, R all rc=0 (R's epoch guard R3b clean — no capture is newer than the report grading it);
`release_gate` exits 1 for the expected reason (7 rows over SHIP, unchanged); GATE I still fails,
pre-existing.

Changed: **NEW `analysis/compression_law_gate.py`** — **GATE S**, the compression law on the
interface-SEND axis (see the session-113 block in "Where we are"). Eight computed sub-gates: S1
asserted membership (five DRIVE-ladder detents, `ref-od.wav` asserted as DRIVE noon's twin, ≥ 4
clean twins, dropouts by DETECTION), S1b the duplicate-detent take-to-take control (0.0099 dB, which
becomes S3's bar), S2 the two input steps with the model-side pad as a known answer and the pedal's
measured from pairs admitted on **flatness** rather than by name, S3 the ladder interlock — the
model-side no-free-parameter prediction **and** the per-pair condition-match classification, S4 the
law over the DRIVE × stimulus plane with the across-band spread beside every mean and the
step-mismatch bound computed, S5 offset-vs-shape against GATE K5's own bar, S6 the bleed dilution
from the shipped `LevelBlend` closed form (taper applied, exponent validated against `FitParams.h`),
S7 the 320 Hz null on the send axis, run TWICE (before the capture landed, when it correctly
refused; after, when it printed the head-item verdict).
**NEW `analysis/_mutate_gate_s.py`** — the mutation runner: 9 mutations plus an unmutated CONTROL,
each needle asserted present exactly once so a vacuous mutation reports as vacuous.
**`CLAUDE.md`** (the session-113 block, session 112's NEXT list superseded on its head item, this
block) and **`.claude/rules/measurement-discipline.md`** (four entries).

New artefacts, gitignored/regenerable: **`analysis/reports/s113_baseline.json` (THE NEW BASELINE,
162 captures)**, `analysis/fit_logs/s113_baseline.log`, `analysis/reports/s113_compression_law.json`
(GATE S on the new baseline).

⚠ **MEASURED, NOT SHIPPED, and it is a CAPTURE fact rather than a model one:** two of the five
DRIVE-ladder twins (`drive-0930`, `drive-1430`) and three further OD twins are **condition-mismatched
by 0.07–2.08 dB** — the DRIVE/LEVEL knob was re-dialled between capture sessions and reproduced
exactly only at the pot's mechanical references. This affects **twin-pair instruments only**; the
162-capture matrix never differences two captures against each other and is untouched.

⚠ **Three `_gain-n18` captures FAIL `comprehensive_report` with "no measured delta for gain session
−18 dB"** — pre-existing, not caused by this session (the constant table `_GAIN_SESSION_MEASURED_DB`
in `captures.py` only has an entry for −12). These are the MASTER-ladder-top probe files from
session 112's "Capture access status", outside the matrix grammar's grading path; not fixed here,
flagged for whoever next opens the MASTER taper item (Phase 10 C).

### Uncommitted at session 112

⚠ **SESSION 112 touched NEITHER `src/` NOR `tests/`** — analysis and docs only, so ctest is untouched
and still 16/17 (the same pre-existing `OSValidationTest` failure) and **no DSP constant moved**.
It DID re-render the matrix: **`analysis/reports/s112_baseline.json` (153 captures, 412 OD rows) is
the new baseline and supersedes `s110_baseline.json`**, which is stale (it predates 26 captures).
127 of the 153 came from cache; only the new ones rendered.

⭐ **THE LOAD-BEARING ACCEPTANCE CHECK:** s112 restricted to the 127 captures it shares with s110
reproduces **every gated cell byte-for-byte** (OD band-RMS 2.327, p99 12.809, 100 Hz–8 kHz median
0.531, CLEAN 0.250 / 0.742). So the re-render is provably inert and 100 % of the headline movement is
membership. The two shared-membership control reports live in the session scratchpad, not the repo.

Changed: **`analysis/release_gate.py`** — new `blend_composition()` (the OD subset's BLEND
composition, printed under the membership block on every run, on the user's decision) with a guard
that exits unless the table accounts for every graded OD row, and the printing in `print_report()`;
`measure()` carries it in its output dict.
**`analysis/gain_session_gate.py`** — new `find_twin()`: the name transform is tried FIRST (so every
pre-s112 pairing resolves identically) and falls back to matching SETTINGS apart from
`gainSessionDb`, because `drive-1200_gain-n12`'s twin is `ref-od.wav` — DRIVE noon *is* the baseline,
so one condition has two names. An ambiguous settings match is a hard failure. GATE N now runs on
**10 pairs, was 4**, all HEALED.
**`analysis/a3_decomposition_gate.py`** — `master_ladder()` dedupes per detent and refuses only when
the duplicate is at the SAME send, printing every discarded alternative; new module constant
`PREFER_FULL_SEND_NOON = True` (pre-s112 behaviour, with the trade-off documented at the constant)
because the new `master-1200_gain-n12` capture makes master-noon a real choice that re-bases the
ledger. **Inert: GATE O returns identical numbers on s110 and s112** (bound 0.407, deficit 4.396).
**`CLAUDE.md`** (the session-112 block, the gate table + its membership warning, the capture-access
status, this block) and **`.claude/rules/measurement-discipline.md`** / **`reference-sources.md`**
(the refuted O5 attribution and the measured send pad).

⭐ **Gate sweep on the new baseline, all re-run:** `matrix_grade`, `shape_gate`, GATE J, K, M, N, O,
P, Q, R all **rc=0** — including GATE R, whose epoch guard (R3b) now reports **0 captures newer than
the report**, resolving the state session 110 deliberately left failing. `release_gate` exits 1 for
the expected reason (7 rows over SHIP). ⛔ **`hf_artefact_gate` (GATE I) still exits non-zero** — the
pre-existing session-109 `kInputRef` consequence session 111 bisected. Not caused by this session and
not patched in passing.

⚠ **MEASURED, NOT GATED, do not quote as fact:** the send pad is **12.000 dB** (four linear twins,
span ≤0.0003 dB; corroborated at 12.000/12.000/12.001 by GATE N's THD turnover) against the harness's
12.071; OD recording repeatability is **0.010 dB** across two sessions; the DRIVE-max twin transfer
shows **4.73 dB of compression** over a 12 dB input drop. See the session-112 block.

New artefacts, gitignored/regenerable: **`analysis/reports/s112_baseline.json` (THE NEW BASELINE)**,
`analysis/fit_logs/s112_baseline.log`, `analysis/fit_logs/s112_null_locus.log`.

---

### Uncommitted at session 111

⚠ **SESSION 111 touched NEITHER `src/` NOR `tests/`** — analysis and docs only, so ctest is
untouched and still 16/17 (the same pre-existing `OSValidationTest` failure) and **no DSP constant
moved**. **No render was run and no baseline moved**: `analysis/reports/s110_baseline.json` is still
the shipped grade; every number is a re-grade of it with a different OD membership.

Changed: **`analysis/matrix_grade.py`** — `EXCLUDE_GAIN_N12` (now `False`, full provenance in its
own block), `is_gain_n12()`, `n12_split()` (asserts the group is non-empty —
`empty-gate-must-fail`), `aggregate()` now grades the union by default and keeps both sub-reads
printed, `--ex-gain-n12` CLI flag as the reproducibility control.
**`analysis/release_gate.py`** — `subsets()` grades the union by default (`ex_n12` param), the
`gain-n12` line is relabelled `[control]` (a SUB-SET of OD now, not disjoint), `thd_split()` (new —
the three-way rms/signed-mean/n table so the THD row's two-population mixture cannot be misread as
one number), `measure()`/`main()` thread `ex_n12` through, `print_report()` states the active
membership on every run and prints the THD split unconditionally, `--ex-gain-n12` CLI flag.
**`analysis/shape_gate.py`** — `report()` adds an `"OD"` aggregate (gated) alongside the `"OD ex
gain-n12"` / `"OD gain-n12"` controls; the PNG panel-3 label list updated to match.
**`analysis/a3_balance_gate.py`** (GATE M) — `DEFECT_TOKEN`'s justification corrected in place: it
no longer cites the retired "session-48 capture defect" premise, and now stands on session 108's P4
(do not pool over an operating point the pedal itself sets) — GATE M's own exclusion and behaviour
are UNCHANGED, only the comment. `od_absolute_gate.py` / `null_locus_gate.py` inherit the corrected
token via `DEFECT_TOKEN = M.DEFECT_TOKEN` / the import chain, so nothing there needed a direct edit.
**`CLAUDE.md`** (the session-111 block above; the gate table; open-work item 5 marked DONE; this
block) and **`docs/phase9-validation.md`** ("Known-bad rows", rewritten — the exclusion is retired,
its cost measured, the THD-mixture warning stated, and the paired-twin finding recorded as
*measured, not gated*).

⭐ **ACCEPTANCE CHECK, the load-bearing one:** `release_gate.py REPORT --ex-gain-n12` was diffed
against a run captured **before any code in this session changed** — every gated cell (CLEAN, OD,
THD) is byte-identical. So the control is not merely "close", and every number this session reports
as the s111 movement is attributable to the membership change alone, not to an incidental refactor.

⭐ **Every gate that reads the OD subset was re-run, not just the two the change directly touches**:
`matrix_grade.py` (rc 0), `shape_gate.py` (rc 0), `od_absolute_gate.py` GATE Q (rc 0),
`a3_balance_gate.py` GATE M (rc 0), `null_locus_gate.py` GATE R (rc 0),
`od_residual_localise.py` GATE J (rc 0). `release_gate.py` exits 1 for the expected reason (7 rows
over SHIP, unchanged in count from s110, changed in composition).

⚠⚠ **ONE PRE-EXISTING FAILURE SURFACED BY THE RE-RUN, NOT CAUSED BY IT:** `hf_artefact_gate.py`
(GATE I) exits non-zero on `s110_baseline.json`, **including under `--ex-gain-n12`** — so the s111
membership change is not the cause. Bisected to session 109's `kInputRef` move (GATE I passes on
`s99_attack_cand.json`, fails on both `s109_k090_cand.json` and `s110_baseline.json`, which nobody
re-ran GATE I against). See the SESSION 111 block above for the table and what survives (G2c, the
directional claim). ⚠ Nothing was changed to fix this — it is flagged as an open item, not patched
in passing, per this session's own scope (a membership decision, not a general gate-repair pass).

New artefacts, gitignored/regenerable: none — every command in this session read
`analysis/reports/s110_baseline.json` and wrote nothing but stdout (`--json` was not used).

---

### Uncommitted at session 110

⚠ **SESSION 110 touched NEITHER `src/` NOR `tests/`** — `git diff --stat -- src tests` is exactly
sessions 91/92/100/109's four files, byte-identical, so **no DSP constant moved** and ctest is
unchanged at **16/17** (the same pre-existing `OSValidationTest` failure) *by construction*; it was
not re-run. **No matrix baseline moved** — the shipped grade is still
`analysis/reports/s109_k090_cand.json`.

⚠ **Unlike GATES J–Q, session 110 DID render** — 15 pure-OD endpoints plus 20 arm/candidate renders,
all carrying an argv `.args.json` stamp that the gate checks before reuse
(`rebaseline-all-derived-artefacts`). Nothing was rendered through the 129-capture matrix.

⚠ **SESSION 110 DID change three shared analysis tools, on the user's decision** (the first change
to the grading path since s96): **`analysis/matrix_grade.py`** gains `LADDER` / `DROPOUT_DB` /
`MIN_SEPARATION_DB` / `find_dropouts()` / `check_dropout_separation()` — the reference-side ladder
dropout detector, moved here from GATE Q so there is ONE definition;
**`analysis/release_gate.py`**'s `subsets()` takes the detected set and breaks it out as a printed
`ref dropout [bad]` subset, with `measure()` computing it, `thd_level()` applying the SAME exclusion
(that cell is the second-worst THD row, so the two halves of the gate must agree about which data
exists), and the report printing it; **`analysis/od_absolute_gate.py`** gains
`cross_check_dropouts()`, which asserts GATE Q's own detector agrees with the grading path's and
refuses if not (there are deliberately TWO, on different inputs — they may not drift), and
`EXPECT_DROPOUTS` 1 → 2. ⭐ `subsets()` defaults to excluding nothing, so every pre-s110 caller and
quote is unaffected.

⚠⚠ **AND A TRAP THE NEW CAPTURE SPRANG IMMEDIATELY, WORTH READING BEFORE ADDING ANY CAPTURE:
`master-1100` IS A MODEL-SIDE DUPLICATE, AND POOLING BY FILE DOUBLE-WEIGHTED ITS CONDITION.** MASTER
is a post-EQ attenuation-only divider into a unity buffer with nothing nonlinear downstream, i.e. a
**pure gain** — and a null PROMINENCE is a CONTRAST, which a pure gain cannot move. Measured: the
shipped and `master-1100` grunt-boost renders give **bit-identical** prominences at all four
stimulus levels (3.10 / 0.71 / 0.14 / 1.99), a third independent confirmation of circuit.md's claim
and GATE O6's known answer. So the two files are ONE condition, and pooling them as two swung GATE
R's DRIVE-max model median 13.67 → 8.55 dB at the quiet end and **broke R6's monotonicity** — a
composition change presenting as a physics result (`aggregate-moved-check-membership-first`, eighth
occurrence). Every GATE R statistic now pools over **CONDITIONS** (MASTER-only duplicates averaged
first) with the by-file figure printed beside it as a labelled control; the condition-pooled numbers
reproduce the pre-`master-1100` values exactly. ⭐ The pedal side corroborates the inertness
independently: both grunt-boost files give a wash-out of **−6.51 dB** to the digit.

Changed: **NEW `analysis/null_locus_gate.py`** — **GATE R**, where the 320 Hz null lives, what
generates the harmonics at it, and why it moves with stimulus (see the session-110 block in "Where
we are"). Nine computed sub-gates: R1 the cap-scaling known answer with its own control network,
R2 the locus, R3 asserted membership (endpoint count, `gain-n12` by name and asserted FOUND, the
s109 dropout, and the DRIVE spread printed), **R3b the EPOCH guard** (endpoint captures must not be
newer than the report supplying the membership), R4 the resolution/residue honesty section plus the
band-vs-point control, R5 the harmonic-source attribution with per-arm vacuity controls, R6 the
compression dose-response, R6b the pre/post rank swap, R7 the pooling correction, R8 the two
rendered candidate explanations for the DRIVE-max gap plus the per-file spread.

✅ **GATE R PASSES on `s110_baseline.json`** (rc=0), as do GATE Q (with its new dropout
cross-check) and GATE M; `release_gate` exits 1 for the expected reason, 7 rows over SHIP.
⚠ Its `EXPECT_ENDPOINTS` (15 → 16) and GATE Q's `EXPECT_DROPOUTS` (1 → 2) were **bumped
deliberately** — both assertions fired on the new capture set, which is exactly what they exist
for; they are not inferred from the report, or they would stop catching anything.
**`CLAUDE.md`** (the session-110 block; session 109's NEXT item 1 marked superseded with the
original text kept; this block) and **`.claude/rules/measurement-discipline.md`** (five entries).

New artefacts, gitignored/regenerable: **`analysis/reports/s110_baseline.json` (THE NEW BASELINE,
131 captures — replaces `s109_k090_cand.json`, which is stale)**, `analysis/fit_logs/s110_baseline.log`,
`analysis/reports/s110_null_locus.json`, `analysis/fit_logs/s110_null_locus.log`, and the stamped
renders in `build/s110_null_arms/` (20) and `build/s110_null_endpoints/` (15). ⚠ Session 110's exploratory scratch renders and reports
(`build/s110_null_locus`, `build/s110_locus_*`, `build/s110_k_old`, `build/s110_bt320`,
`analysis/reports/s110_locus_*.json`, `s110_endpoint_renders.json`) were **deleted deliberately**:
they predate the gate's stamping and would read as gate output to a later session.

### Uncommitted at session 109

⭐⭐ **SESSION 109 IS THE THIRD SESSION TO TOUCH `src/` IN THIS RUN (after 91 and 100), AND IT SHIPPED
ONE CONSTANT: `src/dsp/GainStaging.h` `kInputRefNominal` 1.2596 → 0.90**, with the full provenance in
its comment block (why it works, why it is a move toward physics, the matrix result, and the stated
costs). `src/dsp/FitParams.h` and every other source file are untouched. **`tests/OSValidationTest.cpp`
is a COMMENT-ONLY change** — its probe-amp rationale still cited `kInputRef 3.377`, two constant
changes stale; the note now records that the test feeds `PedalDSP` in chain-domain volts and is
therefore K-independent **by construction**, verified by the amp × factor table being unchanged across
the move. **ctest 16/17**, the same single pre-existing `OSValidationTest` failure, no new ones.

**NEW `analysis/od_absolute_gate.py`** — **GATE Q**, the OD path's ABSOLUTE error surface and its
L / D split (see the session-109 block in "Where we are"). Seven computed sub-gates: Q1 the known
answer against GATE M elementwise (2.2e−15) with a mutation control, Q2 asserted membership with the
`gain-n12` defect excluded by name and asserted found plus a drive/switch confounding check, Q3 the
floor guard + the stimulus map read from `gen_test_signal` + the reference-dropout guard (bar placed
in a measured 11.94 dB bimodal gap, with the SEPARATION asserted rather than a count), Q4 the surface
with the across-capture spread beside every mean, Q5 the compression law per DRIVE, Q6 the 320 Hz null
referred to each side's own shoulders, Q7 the score plus its mutation control. It **imports**
`a3_balance_gate` (GATE M) and through it `level_law_gate` / `matrix_grade`, so the A3 chain cannot
drift. **NEW `analysis/od_lever_screen.py`** — the 21-perturbation lever screen that SELECTED
`kInputRef` by measurement rather than by argument, scoring each candidate by both magnitude and the
cosine against the target.
**`analysis/comprehensive_report.py`** — new `--render-arg`, a raw OfflineRender passthrough (the two
GainStaging scalars live outside `FitParams` by design and `--fit` cannot reach them). It takes ONE
quoted `'--flag value'` and `shlex`-splits it, because argparse swallows a value beginning with `--`
as an option of its own — the mirror image of the zsh word-splitting trap, now in the discipline file.
It flows into the per-capture cache key like any other arg.
**`CLAUDE.md`** (the session-109 block, the gate table's new column + the closed row, this block),
**`.claude/rules/reference-sources.md`** (the A3 row's L/D decomposition and the saturation
attribution) and **`.claude/rules/measurement-discipline.md`** (five entries: unsigned-aggregates-
have-no-sign, measure-the-distribution-before-placing-a-threshold, a-designed-monotone-axis-is-a-free-
validity-check, a-degeneracy-is-a-lever-on-the-axis-it-is-not-degenerate-on, and the argparse
leading-`--` trap appended to the zsh entry).

⭐ **All seven guards were mutation-tested with an unmutated control, run from the tool's own
directory** (s107's entry is why). The control PASSes; all seven mutations exit non-zero with their
own messages. ⚠ The first mutation attempt targeted `od_error`'s return — a function Q1 does not
call — so it changed Q4/Q7's numbers and **no guard fired**. A mutation must land on the code path
the guard actually reads, or it tests nothing.

New artefacts, gitignored/regenerable: **`analysis/reports/s109_k090_cand.json` (THE NEW BASELINE,
129 captures)**, `s109_od_absolute.json` (GATE Q on the s100 grade), `s109_od_absolute_k090.json`,
`s109_lever_screen.json`, `analysis/reports/s109_screen/*.json` (25 subset renders — the screen's
cache) and `analysis/fit_logs/s109_k090_matrix.log`.

⚠ **`docs/phase9-validation.md` "Known-bad rows" now understates the problem by one row** — session
106's `gain-n12` retire-or-keep decision is still open and untaken, and session 109 adds a SECOND,
unrelated bad row (the `grunt-boost @ drv_-12` dropout). Both are user decisions and they should
probably be taken together; the prose is deliberately left alone until then so it cannot disagree with
`matrix_grade`/`release_gate`.

### Uncommitted at session 108

⚠ **SESSION 108 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. **No render was run and no baseline
moved**: every number is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped grade).
Changed: **NEW `analysis/a3_pedestal_gate.py`** — **GATE P**, which tests whether A3's headline is a
sound target for a static correction (see the session-108 block in "Where we are"). Six computed
sub-gates: P1 the per-pair decomposition re-pooled to GATE M elementwise (0.00e+00) with a
vacuous-mutation control, P2 asserted membership plus an assertion that DRIVE and ATTACK are **not
perfectly confounded** (without which no trend is attributable), P3 per-band across-pair
reproducibility with a floor guard, P4 the operating-point spread with the ATTACK-at-fixed-DRIVE
control evaluated at BOTH stimulus extremes, P5 the reproducible ∩ feature-free intersection, P6 a
2-D sweep of both thresholds with both knobs asserted to turn.
**`analysis/od_residual_localise.py`** — comments only, no behaviour change (GATE J re-run, still
passes): the two blocks asserting "bleed-free BY TOPOLOGY is blend == 1.0" are **corrected in place**
against GATE K2's refutation, since that stale claim is what left the GRUNT item standing.
**`CLAUDE.md`** (the session-108 block incl. the GRUNT closure and the synthesis; session 107's NEXT
item 1 marked superseded with items 2–6 surviving; open-work item 5's re-scope; this block),
**`.claude/rules/reference-sources.md`** (the A3 row's "not a fit target" caveat) and
**`.claude/rules/measurement-discipline.md`** (six entries).
New artefact, gitignored/regenerable: `analysis/reports/s108_a3_pedestal.json`.

⭐ **All six guards were mutation-tested with an unmutated control, run from the tool's own
directory** — session 107's entry is why: patched copies in `/tmp` return "FAIL" for a
`ModuleNotFoundError` that never reaches a guard. Control PASSes; all six mutations exit non-zero
with their own messages.

### Uncommitted at session 107

⚠ **SESSION 107 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. **No render was run and no baseline
moved**: every number is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped grade).
Changed: **NEW `analysis/a3_decomposition_gate.py`** — **GATE O**, which gates session 106's A3
decomposition (see the session-107 block in "Where we are"). Eight computed sub-gates: O1 the
regrouping identity against GATE M elementwise (2.2e−15) with a mutation control, O2 asserted
membership including MASTER-matched-within-every-pair and one-capture-per-detent, O3 the bypass
anchor, O4 the stimulus-invariance known answer with an asserted-binding floor guard, O5 provenance
per band with the model-side known answer (the pad READ from `captures.gain_correction_db`), O6 the
MASTER-law flatness known answer the topology supplies for free, O7 the two-routes check that
resolves session 106's loose end, O8 the self-reconstructing ledger and a computed, conservative
verdict. It **imports** `a3_balance_gate` (and through it `level_law_gate` / `matrix_grade`), so the
tools cannot drift.
**`CLAUDE.md`** (the session-107 block; session 106's NEXT list superseded on items 1–2 with what
survives; the loose end marked RESOLVED; this block), **`.claude/rules/reference-sources.md`** (the
A3 row's re-attribution and the two reference-side properties) and
**`.claude/rules/measurement-discipline.md`** (five entries).
New artefact, gitignored/regenerable: `analysis/reports/s107_a3_decomposition.json`.

⭐ **All five of GATE O's guards were mutation-tested with an unmutated control, and the first
attempt at that test was worthless** — patched copies written to `/tmp` returned 5 of 5 "PASS", every
one of them a `ModuleNotFoundError` that never reached a guard. See the discipline file; it is
`empty-gate-must-fail` committed inside the mutation test written to enforce it.

⚠ **`docs/phase9-validation.md` "Known-bad rows" still states the s48 exclusion as current**, and
session 106's retire-or-keep DECISION is still open and untaken. GATE O adds one input to it and
does **not** resolve it: on the linear/absolute axis the clean twin bounds the provenance residue at
a **0.334 dB span** (mean removed by the per-row gain match, tilt not), while the **OD twins cannot
be read as provenance at all** — their 2.6–4.0 dB spans are confounded with the model's own
drive-dependent error at a 12 dB lower operating point.

### Uncommitted at session 106

⚠ **SESSION 106 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. **No render was run and no baseline
moved**: every number is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped grade).
Changed: **NEW `analysis/gain_session_gate.py`** — **GATE N**, the `gain-n12` turnover re-test (see
the session-106 block in "Where we are"). Five computed sub-gates: N1 asserted membership with the
harness pad READ from `captures.gain_correction_db` and the count reproducing the documented 16 rows,
N2 the model-side known answer (12.071 recovered to 0.003) plus a 0/6/12.071 calibration ladder, N3
power per pair, N4 the measurement, N5 floor robustness with an asserted-binding sweep.
**`CLAUDE.md`** (the session-106 block; session 105's NEXT list superseded; this block) and
**`.claude/rules/measurement-discipline.md`** (three entries).
New artefact, gitignored/regenerable: `analysis/reports/s106_gain_session.json`.

⚠ **`docs/phase9-validation.md` "Known-bad rows" still states the s48 exclusion as current** — it is
left in place deliberately until the user takes the retire-or-keep decision, because editing it
without also moving `matrix_grade`/`release_gate` would leave the prose and the code disagreeing.

### Uncommitted at session 105

⚠ **SESSION 105 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. `git diff --name-only src/ tests/` is
exactly sessions 91/92/100's three files, unchanged. **No render was run and no baseline moved**:
every number is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped grade). Changed:
**NEW `analysis/a3_balance_gate.py`** — **GATE M**, the per-band decomposition of A3 (see the
session-105 block in "Where we are"). Six computed sub-gates: M1 the known answer against GATE K7's
own arithmetic (1.3e−15) **with a dropped-band mutation control**, M2 asserted membership with the
`gain-n12` row named and the drive×attack confound stated, M3 the de-contamination, M4 the
offset/shape decomposition with a floor guard and band-edge robustness and a **computed** verdict
against GATE K5's own 0.25 bar, M5 the leave-one-out shape-coherence check, M6 the stimulus
migration. It **imports** `level_law_gate` (and through it `matrix_grade`), so the tools cannot
drift.
**`CLAUDE.md`** (the session-105 block; session 104's NEXT list marked superseded on item 1 with
what survives; item 5's re-scope; this block) and **`.claude/rules/measurement-discipline.md`** /
**`.claude/rules/reference-sources.md`** (the A3 row's corrected size and the (A)/(B) split).
New artefact, gitignored/regenerable: `analysis/reports/s105_a3_balance.json`.

⚠ **A membership check silently did not run, and it took noticing an implausible coincidence to
catch it.** A first pass at the band-edge robustness column selected with `f > 25` — the lowest band
is **25.2 Hz**, so it dropped nothing, and the "drop 25 Hz" row printed a value **identical to the
all-bands row**. It read as a reassuring robustness result. ⭐ The tell was that identity: dropping a
band whose value is 10.25 dB from a 25-band mean of 3.36 cannot leave the mean unchanged. M4 now
**asserts the selection holds exactly one fewer band** and exits if not. Same family as
`empty-gate-must-fail` — a check that silently never runs — and note the direction: the broken
version was **flattering**.

### Uncommitted at session 104

⚠ **SESSION 104 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. `git diff --name-only src/ tests/` is
exactly sessions 91/92/100's three files, unchanged. **No render was run and no baseline moved**:
every number is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped grade) plus a
closed-form evaluation of the shipped `LevelBlend` stage. Changed:
**NEW `analysis/level_taper_gate.py`** — **GATE L**, the structural reachability of the LEVEL law
(see the session-104 block in "Where we are"). Eight computed sub-gates: L1 the reduced closed form
against `level_law_gate.coef_closed` (3.33e−16) plus a mutation, L2 asserted membership, L3 the
multi-start known answer (recovers `x^2.25` to 4.3e−10, starts agree to 3.8e−11), L4 the pedal
recovery, L5 the free-ρ control *with its own known-answer control*, L6 stimulus invariance, L7 the
LEVEL-min mute quantified, L8 the refutation of K3's saturation reading. It **imports**
`level_law_gate` (and through it `release_gate`/`matrix_grade`), so the tools cannot drift.
**`CLAUDE.md`** (the session-104 block; session 103's NEXT list marked superseded with what survives;
this block) and **`.claude/rules/measurement-discipline.md`** (five entries: the fixed-point known
answer, membership contamination invisible in the aggregate, free-the-nuisance-as-a-control,
invariance-as-refutation, and non-monotone-network-coefficient-is-not-saturation).
New artefact, gitignored/regenerable: `analysis/reports/s104_level_taper.json`.

⚠ **The load-bearing defect was in session 104's OWN gate and it printed a PERFECT result before
being caught**: L3's known answer recovered `L = x^2.25` to ±0.000000 while being *initialised* at
`x^2.25` — a fixed point, not a test. Only re-running from 7 starts far from the answer (p = 0.5…4.0
plus three random monotone vectors) turned it into evidence. ⭐ Note which way the error ran: the
broken check was **flattering**, so nothing would have prompted a second look at it.

### Uncommitted at session 103

⚠ **SESSION 103 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. **No render was run and no baseline
moved**: every number is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped grade)
plus a closed-form evaluation of the shipped `LevelBlend` stage. Changed:
**NEW `analysis/level_law_gate.py`** — **GATE K**, the LEVEL control law (see the session-103 block
in "Where we are"). Seven computed sub-gates: K1 the absolute-reconstruction known answer against
`release_gate` (imports it, so the two cannot drift), K2 the bleed premise with two independent
derivations of the stage coefficients plus a mutation control, K3 the 9-point ladder with two
known answers, K4 out-of-sample over the 14 other matched groups, K5 the offset/shape split, K6 the
LEVEL↔bleed collinearity, K7 the direct clean/OD balance.
**`CLAUDE.md`** (the session-103 block; the session-102 LEVEL block marked SUPERSEDED and kept
verbatim; item 5's A3 re-promotion; the standing-rules entry above; this block) and
**`.claude/rules/measurement-discipline.md`** (four entries).
New artefact, gitignored/regenerable: `analysis/reports/s103_level_law.json`.

⚠ **Two defects in session 103's own gate had to be fixed before anything was read off it, and one
had already printed a WRONG verdict.** (1) K3's first draft asserted "a pot law is monotone, so both
columns must be" and **FAILED the gate against correct data** — what is tabulated is the end-to-end
**H1 transfer**, which falls when a stage downstream of LEVEL saturates, so monotonicity holds only
in the linear region. Same error as GATE I's asserted −24 dB/oct: a textbook property quoted outside
its conditions. (2) K3's summary line narrated "stimulus-INDEPENDENT" above its own numbers, which
show the pedal spreading **2.80 dB**; the verdict now states the spread and the defect size and
draws the conclusion from their RATIO (`computed-verdicts-not-narrated`).

### Uncommitted at session 96

⚠ **SESSION 96 touched NEITHER `src/` NOR `tests/`** — analysis and docs only, so ctest is untouched
and still 16/17 and no DSP constant moved. **No render was run and no baseline moved**; every number
it quotes is a re-grade of reports already on disk. Changed:
**`analysis/release_gate.py`** — the CLEAN row split (`GATE` now carries four CLEAN rows;
`CLEAN_GATED_REGIONS`/`CLEAN_POOL_CONTROL`; the `100 Hz-16.3 kHz` composite is kept and printed but
**no longer gated**; new `region_sel()` is the single region resolver shared by `pool()` and the new
`check_clean_partition()`, which is called from `deltas()`; the stale session-91 verdict paragraph is
replaced by a three-pool CONTROL block). **`CLAUDE.md`** (gate table + the CLEAN block + open-work
item 7) and **`docs/clean-gate-split-handover.md`** (marked EXECUTED, with the measured results).

✅ **The TODO carried forward from session 95 — `best_point`'s ranking key tie-breaking on the
smaller BOX ahead of `n_on_bound` — is DONE in session 97**, together with three further defects it
uncovered. See item 4. The attack candidate is still **not** matrix-ready, but for a precise and
different reason (2 of 17 values on their bounds, both at the box floor).

### Uncommitted at session 102

⚠ **SESSION 102 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. **No render was run and no baseline
moved**: every number it quotes is a re-read of `analysis/reports/s99_attack_cand.json` (the shipped
grade) already on disk. Changed:
**NEW `analysis/od_residual_localise.py`** — **GATE J**, the localisation of the remaining OD error
(see the session-102 block in "Where we are"). Six computed sub-gates: J1 the decomposition
known-answer + reproduction of `release_gate`'s region statistics, J2 its dropped-band mutation
control, J3 the midband sub-partition tiling assertion, J8 the A3 bleed discriminator, J10 the
LEVEL × stimulus cross-tab, J12 the signed-loader check. It **imports** `release_gate.deltas` /
`subsets` / `region_sel` rather than re-implementing them, so the two tools cannot drift.
**`CLAUDE.md`** (the session-102 block, open-work item 5's demotion, and this block) and
**`.claude/rules/measurement-discipline.md`** (four entries: conditional-vs-marginal with its
cross-tab corollary, mean-of-square-roots-does-not-decompose, a-ratio-can-move-because-its-
denominator-moved, and the signed-vs-magnitude loader trap).
New artefact, gitignored/regenerable: `analysis/reports/s102_localise.json`.

⚠ **One defect in session 102's own gate had to be fixed before anything was read off it, and it had
already printed WRONG numbers**: J11's level/shape split was computed from `release_gate.deltas`,
which returns **|delta|** — so `mean(|d|)` was being used as an offset and the "level term" column
was plausible, monotone and wrong by up to 2.6 dB. It was caught **only** because an independent
one-off shell read had been done first and the two disagreed; the fix adds a separate signed loader
and **J12**, which gates it against `release_gate`'s own array elementwise. ⭐ The general form is in
the discipline file: reusing a shared loader is right, assuming its contract is not.

### Uncommitted at session 101

⚠ **SESSION 101 touched NEITHER `src/` NOR `tests/`** — one new analysis tool and docs only, so ctest
is untouched and still 16/17 and **no DSP constant moved**. **No render was run and no baseline
moved**: every number it quotes is a re-read of `s99_attack_cand.json` / `s91_shipped.json` already on
disk plus the capture wavs. Changed:
**NEW `analysis/hf_artefact_gate.py`** — **GATE I**, which answers session 89's step (b) (see the
standing-rules block above). Four sub-gates: G1 the CLEAN-path control (runs first, refuses if our
linear HF is already wrong), G2 the rolloff-RATE comparison against a **derived** −18.25 dB/oct, G3
the `fs/(N+1)` fold-locus test scored against a non-locus null, G4 the pool-restriction consequence
computed on candidate AND baseline. **`CLAUDE.md`** (the standing-rules HF block + this block) and
**`.claude/rules/measurement-discipline.md`** (two entries: rate-discriminates-where-level-cannot
with its derived-reference and clean-control corollaries, and localised-feature-tests-on-a-sigmoid).
New artefact, gitignored/regenerable: `analysis/reports/s101_hf_artefact.json`.

⚠ **Three defects in session 101's own gate had to be fixed before anything was read off it, and two
of them had already printed a WRONG verdict** — all three are in the discipline file: an asserted
−24 dB/oct reference that false-FAILed a correct model, and two successive "localised feature" tests
that fired on a sigmoid's own inflection. ⭐ The gate was written to refuse, and it refused me three
times before it agreed; that is the only reason its OK is worth anything.

### Uncommitted at session 100

⭐⭐ **SESSION 100 IS THE SECOND SESSION TO TOUCH `src/` IN THIS RUN (after 91), AND THE LARGEST
DSP CHANGE OF THE PROJECT SO FAR — 17 constants in one block.** Changed: **`src/dsp/FitParams.h`**
only (no other source file, no `tests/` change, so ctest is 16/17 with the same single pre-existing
`OSValidationTest` failure). The 17 values, all in the treble/ATTACK region:

| | shipped s100 | was | ×drawn |
|---|---|---|---|
| `attackTapRa` / `Rb` / `Rc` / `R11` | 392663 / 420440 / 77481 / 163933 | 470k / 0 / 0 / 470k | — |
| `trebleR7` | 1.64563e6 | 200k | ×8.23 |
| `trebleLadderR12` / `R14` | 27131 / 48500.9 | 6.8k / 22k | ×3.99 / ×2.20 |
| `trebleC9` / `C6` | 1.28153e-8 / 1.39228e-9 | 22n / 22n | ×0.583 / **×0.0633** |
| `trebleC7` | 755.764p | 680p | ×1.11 *(of the s35 value)* |
| `trebleC5` + trims boost/cut | 7.95747n + 100.053p / 319.622p | 22n + 0 / 0 | — |
| `trebleLadderDampR` (flat) | 15372.9 | 30k | — |
| `attackDampBoost` / `Cut` | 7055.36 / 118.022 | −1 / −1 *(inherit)* | — |
| `trebleC8` | **0** | 220p | removed |

⚠ **Two stale comments were CORRECTED in place rather than left to mislead**, both in `FitParams.h`:
the shared-ladder block's "Defaults are the drawn values and a default render is BIT-IDENTICAL to the
pre-session-64 stage" (first clause now false; the second was never about `FitParams` — Test 10
compares the **stage's** own `kR7…kC6` defaults, so it still passes and still means something), and
`trebleC8`'s "0 removes it (the proposal's condition)", which is now the shipped condition.
⚠ Every remaining "the drawn X" comment in that region describes the **prior default**; the
session-100 block says so at the top.

**`CLAUDE.md`**: the session-100 headline, the grade table (s91 kept as a labelled control), the gate
table's "now" column + a `was (s91)` column, item 4's decision (1) marked DONE with the notch caveat,
and this block.

⛔ **NO NEW RENDER AND NO NEW MATRIX RUN WAS NEEDED**, and that is a measured claim, not an
assumption: the shipped defaults render **bit-identically** to the explicit 17-flag `--fit` list at
**all three ATTACK throws**, so `analysis/reports/s99_attack_cand.json` IS the shipped grade. ⚠ The
mutation control (`attackDampCut ×2` must change the render) is what makes that check non-vacuous —
without it, a constant silently landing in the wrong field would still have "passed".
⚠ Paid for again: **zsh does not word-split unquoted `$var`** — the first bit-identity attempt sent
the whole arg string as ONE argv, both renders failed with rc=2, and my own check printed "❌ DIFFER"
from its else-branch on two **missing files**. A red light with the wrong label (`empty-gate-must-
fail` in miniature). Use `ARGS=(...)` arrays and `"${ARGS[@]}"`, and print the argv count.

### Uncommitted at session 99

⚠ **SESSION 99 touched NEITHER `src/` NOR `tests/`** — two analysis tools and docs only, so ctest is
untouched and still 16/17 and **no DSP constant moved**. `git diff --stat src/ tests/` is exactly
session 91's two constants + session 92's `OSValidationTest` rebuild, unchanged. It DID run the
129-capture matrix (a render, **no baseline move**), six GATE-H renders and three stepped renders.
Changed:
**`analysis/attack_shape_screen.py`** — `g` is now scored PER SUB-BAND: new `G_SUBS` (the shipped
4-band partition) / `G_POOL` (the pre-99 control as a 1-element partition) / `G_ACTIVE` / `G_SEL`,
`check_g_partition()` (tiling assertion), `set_g_partition()`, `g_labels()`, `print_g_table()` (ONE
printer, so a caller cannot re-collapse the vector), `g_json()`; `abs_gain_record()`, `g_of()` and
`g_targets()` all return per-sub-band vectors; `gate_absgain` F2 is per sub-band and gains **F4**
(`gate_region_of_validity`) and **F5** (`gate_pooled_blind`) plus `_pooled_delta()`; new
`ladder_from_fits()` / `FIT_MAP` / `RD_MAP` / `C5T_MAP` / `ladder_distance()` (ONE definition, now
imported by GATE H); `best_point()` takes `rov` and prints the winner's ladder distance against
F4's **measured** envelope (⚠ a first draft transcribed those figures into the format string —
`computed-verdicts-not-narrated` in the one line that tells the next session whether to trust the
term); new `gate_g_partition()` = `--g-selftest`; new `--g-pooled` and `--g-selftest` flags.
**`analysis/attack_d_extrapolation_gate.py`** — H3 and H4 swap roles (H3 = the per-sub-band promise,
H4 = the superseded pooled median as a labelled control); its duplicate `FIT_MAP`/`parse_fits` and
ad-hoc sub-bands are replaced by the screen's; new `--json` (the output path was hardcoded to the
s98 name).
**`CLAUDE.md`** (item 4 + this block) and **`.claude/rules/measurement-discipline.md`** (five
entries: reachability-under-a-blind-objective, decompose-the-target-too, few-bins-is-not-unreliable,
repair-inverts-headline-and-control, and measure-your-region-of-validity).

⭐ **The refactor is proven inert BEFORE anything was read off it**, which is what makes the
session's conclusion readable: `--g-selftest` re-scores the stored s97 winner under `--g-pooled`
through the entirely rewritten vectorised path and reproduces `post_g_rms` to **4.83e-06**, and the
pooled GATE F run reproduces every recorded session-95 number to the digit (Delta +8.66/+9.18/+8.73,
F3 14.88 dB, F3b notch 7.30 → 7.51 = 1.4 %, h 23 %). ⭐ And GATE F4 independently reproduces GATE H2's
**3.844 dB** through a completely different code path from the one that first measured it.

New artefacts, gitignored/regenerable: `analysis/reports/s99_attack_best_subband.json` (the fit),
`s99_attack_stepped_cand.json`, `s99_d_extrapolation.json` (GATE H at the new candidate),
`s99_d_extrap_s97control.json` (GATE H re-run at the s97 point, the control),
`s99_attack_cand.json` (the 129-capture matrix run), `s99_smoke.json`, and
`analysis/fit_logs/s99_*.log`. ⚠ `build/attack_stepped_gate/cand_*.wav` and
`build/attack_d_extrap/cand_*.wav` were DELETED and re-rendered — they were session 98's, for a
different candidate (`rebaseline-all-derived-artefacts`).

### Uncommitted at session 98

⚠ **SESSION 98 touched NEITHER `src/` NOR `tests/`** — one analysis tool and docs only, so ctest is
untouched and still 16/17 and **no DSP constant moved**. It DID run the 129-capture matrix (a render,
no baseline move) and three stepped renders. Changed:
**`analysis/attack_shape_screen.py`** — the search box is now **PER-DIMENSION**: new `dim_names()`
(one definition of the x-vector's coordinate labels, which three call sites used to build inline),
`dim_bounds()` (⛔ refuses a floor on a LINEAR `C5t` coordinate — moving that bound redefines
`build()`'s codomain rather than widening a search, the session-97 defect in a new costume),
`on_bound_mask()`, and `TAP_BOX` (stage 2's box, previously hardcoded inside `tap_stage`). `build()`,
`realisable()`, `Cost`, `run()`, `tap_stage()` and `best_point()` all take the bounds; `show()` and
`frontier()` now share the two helpers. New `bound_profile()` = **GATE G** (`--floor-probe`), new
`profile_refit()`, `rank_key()` and `dominates()`, and `--floor DIM=DEC` on `--best` (⚠ retained
but currently UNJUSTIFIED — the probe says no box binds; the CLI help says so).
**NEW `analysis/attack_d_extrapolation_gate.py`** — GATE H, the four-step localisation of the
matrix regression (H1 known answer vs GATE F's own `D_prop`, H2 D-invariance at the fitted ladder,
H3 the sufficiency check, H4 the per-sub-band decomposition that found the cause).
**`CLAUDE.md`** (item 4 + this block) and **`.claude/rules/measurement-discipline.md`** (seven
entries: the two under `bound-resting-means-unidentified`, quantise-to-compare-candidates-not-
references, the pinned-coordinate/wrong-vector one, the median-over-linear-bins one, the
invariance-is-only-local one, real-vs-sufficient, and a fourth occurrence appended to the zsh
word-splitting entry).

⭐ **The refactor is proven inert before anything was read off it**, which is what makes the whole
session's conclusion readable: **G1** re-scores the stored s97 winner under the new code path and
reproduces its stage-1 AND post-tap statistics to **0.000e+00**; **G2** asserts `build()`'s C5-trim
expression is **bit-identical** (`==`, not `isclose`) to the session-97 line at symmetric bounds —
which it is by construction, since `mid = 0.0` and `half = box` exactly for `(-box, box)`. ⭐ And a
third, independent control fell out of the session's smoke test (`--fit --quick`,
`analysis/reports/s98_smoke.json`): it reproduces session 97's census finding **exactly** —
**`Ra` rests on its bound in 7 of the 7** non-over-parameterised `shared`-set variants — through
the entirely rewritten bounds/`show()` path.

⚠⚠ **THREE DEFECTS IN SESSION 98's OWN GATE, AND TWO OF THEM PRINTED A WRONG VERDICT BEFORE BEING
CAUGHT.** Recorded because each is a general trap, not a typo:
**(1) The reference index was read from the wrong vector.** `TAP.index("Ra")` applied to the
**stage-1** x returned R7's coordinate, so the entire `Ra` profile was centred on **+0.86** instead
of −1.00 and every row of it measured a point nobody asked about — printing a plausible, monotone,
completely irrelevant column. ⭐ The tell was that the KNOWN-ANSWER row **never fired**, which is
`empty-gate-must-fail` wearing a disguise: a self-check that silently never runs. The
"reference row identified" line is now printed explicitly.
**(2) The pinned coordinate was excluded by `n_on_bound - 1`, not by index.** The 1e-9 pin window
trips `on_bound_mask` when the polish lands on the window edge and not when it lands mid-window, so
the column was off by one on *some* rows and right on others — and `n_on_bound` is the one statistic
the whole gate exists to move.
**(3) ⭐⭐ The verdict compared ROUNDED ranking keys.** The first run reported the C9 known-answer
check as a **FAILURE** and concluded **"the floor BINDS — widen this dimension"**, both of which
were the opposite of the truth: the re-fit had reproduced its reference to **0.06 of width rms**,
well inside the **0.10** tie scale the tool itself declares, but 0.406 rounds to 0.4 and 0.466 to
0.5. ⭐ GENERAL: **quantise to compare CANDIDATES, and use the raw statistic against an explicit
per-term tolerance to compare a MEASUREMENT with its own reference.** A rounding boundary is not a
finding. The gate now uses `dominates()` for every reproduce-or-improve question and keeps
`rank_key()` strictly for ordering the field.

⚠ Also paid for once more: **zsh does not word-split `$var`** — the 17-flag `--fit` list reached
`comprehensive_report.py` as ONE argv, and **argparse's own error hides it**, because it prints the
unrecognised list space-joined so one bad argv looks like many. Now written one token per line and
`xargs`-ed, with a `print(sys.argv)` probe run first (38 argv, 17 `--fit` pairs) before spending the
render.

⚠ **A fourth defect, in the NEW gate H and worth its own line because the error message LIED about
whose fault it was:** `RG.check_stamp(path, expect)` takes argv **minus** the binary and the two
paths and `sys.exit`s on a mismatch rather than returning a bool. Called with the full `cmd` and
used as a cache-hit test, it printed a **stale-artefact** report — the two argv forms side by side,
which reads exactly like a genuinely stale render — for what was purely the caller's slice bug.
⭐ A red light with a misleading label sends the next session after the wrong defect (same family
as session 95's GATE F3 draft).

New artefacts, gitignored/regenerable: `analysis/reports/s98_floor_probe.json`,
`s98_attack_stepped_cand.json`, `s98_attack_cand.json` (the 129-capture matrix run),
`s98_d_extrapolation.json`, `s98_smoke.json`, `analysis/fit_logs/s98_floor_probe.log` /
`s98_stepped_gate.log` / `s98_matrix_cand.log` / `s98_smoke.log`, and `build/attack_d_extrap/`
(6 renders).
⚠ `build/attack_stepped_gate/cand_*.wav` were DELETED and re-rendered (session 94's, stale).

### Uncommitted at session 97

⚠ **SESSION 97 touched NEITHER `src/` NOR `tests/`** — one analysis tool and docs only, so ctest is
untouched and still 16/17 and no DSP constant moved. **No render was run and no matrix baseline
moved.** Changed: **`analysis/attack_shape_screen.py`** — the ranking key is now
`(realisable, g, f0, width, n_on_bound, box)`; new `realisable()` (the `attackC5TrimFlat` feasibility
test) and `resid()` (ONE definition of the five scored residuals, shared by `Cost.parts` and the
ranking); new `tap_stage()` and stage 2 now runs PER ROW with the key scoring its output; `build()`,
`Cost` and `show()` take the ACTIVE `box` instead of reading the module default; `run()` resolves
`box` before constructing `Cost`. **`CLAUDE.md`** (item 4 + this block) and
**`.claude/rules/measurement-discipline.md`** (three new entries).

⭐ **Every fix was gated against a known answer before it was believed**, and the controls are worth
keeping: `build()` at the default box is **bit-identical** to the old line, so all five box-1.0 rows
reproduce across all three runs — which is what makes the box-3.0 movement readable as the fix and
not as search noise. `realisable()` was checked against a hand-computed 8-YES/2-NO census and
mutation-tested (a point with flat's trim largest must be refused). The `resid()` refactor is proven
inert by the stage-1 columns reproducing a third time.

New artefacts, gitignored/regenerable, kept as the attribution chain (one per fix, in order):
`analysis/reports/s97_attack_best_absg.json` (key fix alone), `s97_attack_best_fixed.json` (+ the box
and realisability fixes), **`s97_attack_best_posttap.json` (the current best point)**, and
`analysis/fit_logs/s97_best_absg.log` / `s97_best_fixed.log` / `s97_best_posttap.log`.

### Uncommitted at session 95

⚠ **SESSION 95 touched NEITHER `src/` NOR `tests/`** — analysis and docs only, so ctest is untouched
and still 16/17 and no DSP constant moved. Changed:
**`analysis/attack_shape_screen.py`** (the absolute OD-magnitude term `g` and everything it binds:
`G_BAND`/`G_FLOOR_DB`/`G_TIE_RMS`, `abs_gain_record()`, `g_of()`, `g_targets()`, `gate_absgain()` =
GATE F, `full_stats` now returns `gabs`, `Cost`/`TapCost`/`run` take `tgt_g`/`wt_g`, the term is in
the `best_point` ranking key and printed by `show()`/`frontier()`/stage 2, and `--no-absgain` is the
control). New: **`docs/clean-gate-split-handover.md`** (the CLEAN row split — decided-not-executed at
the time; ✅ **executed in session 96**). New artefacts, gitignored/regenerable:
`analysis/reports/s95_attack_best_absg.json`, `analysis/fit_logs/s95_best_absg.log`.

### Uncommitted at session 94

⚠ **SESSION 94 touched NEITHER `src/` NOR `tests/`** — analysis and docs only, so ctest is
untouched and still 16/17 and no DSP constant moved. Changed:
**`analysis/attack_shape_screen.py`** (the `--instrument stepped|swept` switch and everything it
binds; a measured-not-transcribed `pedal_record()`; GATE B on the stepped grid; GATE E's second
clause — a non-finite notch stat is now a PATHOLOGY, which it had to become because a nan cost is
not ORDERED against anything and the first run random-walked; the width half of the ranking key;
`--render-cal` parallelised), **`analysis/read_notch_sweep.py`** (`locate(..., fit_depth=False)` —
skips only the parametric depth, which is pure cost inside an optimiser loop), and
**`analysis/attack_stepped_gate.py`** (`--fits-json`, and the swap verdict is now scored over the
REFERENCE variants only). New artefacts, all gitignored/regenerable:
`analysis/reports/s94_attack_shape_stepped.json`, `s94_attack_best_stepped.json`,
`s94_attack_stepped_cand.json`, `s94_attack_cand.json` (the 129-capture matrix run),
`s94_c7pin_onerow.json` (the attribution control), `analysis/fit_logs/s94_*.log`, and
`build/attack_shape_screen_stepped/` (the stepped calibration anchor, 3 renders).

### Uncommitted at session 93

Sessions 55–94 are uncommitted: `CLAUDE.md`, `docs/phase9-validation.md`,
`.claude/rules/reference-sources.md`, ~20 new `analysis/*.py` tools, and
`docs/session-log.md` / `docs/phase9-gap-log.md` / `.claude/rules/measurement-discipline.md`.

⚠ **SESSION 93 touched NEITHER `src/` NOR `tests/`** — analysis and docs only. New:
**`analysis/attack_stepped_gate.py`** (+ `analysis/reports/s93_attack_stepped.json` and
`build/attack_stepped_gate/`, both gitignored/regenerable). ctest is untouched and still 16/17.

⚠ **SESSION 92 IS THE FIRST TO TOUCH `tests/` IN THIS RUN** — `tests/OSValidationTest.cpp`'s
aliasing measurement is rebuilt (bin-exact f0, rectangular window, 4 s settle, LF bucket reported
separately) and its header now carries the derivation. **No DSP constant changed**; `src/` is
exactly as session 91 left it, and ctest is still 16/17 with the same single failure — which is now
a documented real defect rather than an unexplained one. New: **`analysis/alias_gate.py`**.

⚠⚠ **SESSION 91 IS THE FIRST TO TOUCH `src/` SINCE SESSION 44 — `git diff HEAD -- src/` IS NO LONGER
CLEAN, and the note that said it was is now WRONG.** Two constants in
**`src/dsp/FitParams.h`** (`c21R` 220k → 130k, `jfetSatNeg` 0.76054 → 1.9, both with full
provenance in their field comments) plus a corrected bound comment in **`src/dsp/JfetStage.h`**
(`|a|*s < 2.598` is the bump in isolation; the combined shape folds at 2.431). `tests/` and
`analysis/captures/` are still untouched.

Session 91 also added **`analysis/c21_hw_anchor.py`** (new) and changed
**`analysis/release_gate.py`** (`COMPOSITES`; the CLEAN pool is now 100 Hz–16.3 kHz; values print
to 3 dp; both pools printed side by side every run).

Gitignored but regenerable: `analysis/reports/*.json` — **`s91_shipped.json` is the new baseline**
(129 captures, ~25 min at `-j 8`), with `s91_c21_130k.json` (c21R alone, the attribution artefact
for item 1), `s91_c21_150k.json` (the rejected alternative) and `s91_shipped_mixedbin.json` (a
control: rendered across a binary relink, and **504/504 rows bit-identical to `s91_shipped.json`**,
which is what proves the comment-only rebuild was inert). Also `analysis/fit_logs/*.log`, `build/**`.
Session 92 adds `analysis/reports/s92_alias_gate.json` (the amp × factor grid under all three
analyses) and `s92_alias_sweep.json` (the 21-tone sweep + the fold-locus attribution).

## Project-specific carry-forwards

> Record decisions, measured constants (kInputRef, rail voltages, makeup), and open questions here
> as you go, so the next session resumes cleanly.

- ⛔⛔ **CAPTURE ACCESS STATUS, SESSION 111 (2026-08-02): THE USER IS LOSING ACCESS TO THE ND PLUGIN
  (the capture source). `reference-sources.md` §0's "captures are unlimited, do not ration" claim
  is RE-INSTATED to its pre-2026-07-29 scarce framing until this note says otherwise — read that row
  before assuming any capture is obtainable on demand.**
  ⚠ **IF A FUTURE SESSION FINDS IT NEEDS A CAPTURE THAT IS NOT ALREADY ON DISK
  (`analysis/captures/`, 179 `.wav` files as of this note) OR NOT IN THE INVENTORY BELOW, ASK THE
  USER IMMEDIATELY.** Do not defer the question to "when convenient" and do not silently work around
  a missing capture with an assumption — the user said explicitly they need to know ASAP if more are
  needed, because the window may already be closed by the time a later session reads this.
  ⭐ **What IS decoupled and safe to do at any time, no plugin access needed:** re-rendering
  `comprehensive_report.py` / any gate against the WAV files already on disk. Only NEW captures need
  the plugin.
  ✅ **DONE, SESSION 112 — the re-render is executed: `analysis/reports/s112_baseline.json`, 153
  matrix captures (179 `.wav` on disk minus the 26 deliberately-outside-the-grammar probe files).**
  `s110_baseline.json` is superseded.

  ✅ **DONE, SESSION 113 — the head item's blocker capture landed and PASSED its own acceptance
  test.** `drive-1700_level-1700_gain-n12_base-od.wav` (DRIVE max, LEVEL max, BLEND max, GRUNT
  flat, ATTACK flat, EQ noon, MASTER noon, DIST on, send 12 dB down) is on disk; its full-send twin
  was already present and clean. Re-rendered onto **`analysis/reports/s113_baseline.json`** (162
  captures — see that block for what else came in). GATE S's S3 interlock reads **0.00009 dB** —
  deep inside the 0.0099 dB take-to-take floor, i.e. a genuinely matched pair, not another
  mis-dialled one. See the SESSION 113 block for the null-axis result this unblocks.

  ⭐ **AND EIGHT MORE CAPTURES ARRIVED IN THE SAME RENDER, PURPOSE STATED BY THE USER:**
  `bass-0900`/`-1500`, `himid-0900`/`-1500`, `lomid-0900`/`-1500`, `treble-0900`/`-1500`
  (`_base-od`, i.e. driven, not clean) — each EQ pot at 9-o'clock/3-o'clock (≈0.2/0.8, not the
  extremes) with the other three at noon. **Purpose, in the user's own words: "an EQ affecting
  distortion capture in case we ever needed them after I lost access to more captures."** ⇒ these
  are a hedge against the closing capture window, not aimed at any open item — nobody has used them
  yet and no claim is made about what they show. If a future session wants an intermediate-EQ×OD
  read (the kind of thing GAP #4's per-position mid work or A3's EQ-interaction questions might
  want), these exist; check `s113_baseline.json` before asking for a re-capture.

  ⛔⛔ **AND THEY MOVE THE RELEASE-GATE HEADLINE, INCLUDING ONE ROW ACROSS ITS OWN BAR — AND IT IS
  DILUTION, NOT MODEL IMPROVEMENT, SESSION 112's TRAP A SECOND TIME IN THE VERY SESSION THAT NAMED
  IT.** Checked with the same acceptance test session 112 used on itself: `s113_baseline.json`
  restricted to the 153 captures it shares with `s112_baseline.json` reproduces **every gated cell
  byte-for-byte**, so the render is inert and 100 % of the movement below is membership.

  | | s112 (153 caps) | **s113 full (162 caps)** | |
  |---|---|---|---|
  | OD 25–100 Hz median | 0.804 | **0.944** | ⚠ worse |
  | OD 100 Hz–8 kHz median | 0.469 STRETCH | 0.492 STRETCH | ⚠ worse, same verdict |
  | OD p99 | 11.801 | 11.442 | better |
  | **THD (OD) level term** | 3.064 ⚠ over | **2.975 ✅ SHIP** | ⛔ **do not book this** |

  The requested capture ALONE moves almost nothing (THD level 3.064 → 3.056, still over). **The 8 EQ
  hedge captures carry the movement**: isolated, their own 32 OD rows read band-RMS **mean 1.778,
  median 1.723** against the existing 412-row population's **mean 2.243** — i.e. they are
  *quieter-than-average* rows (9-o'clock/3-o'clock EQ settings are mild perturbations, not the
  extremes the matrix is built from) and their addition pulls the pooled THD statistic under its bar
  the same way session 112's 12 intermediate-BLEND captures pulled the OD median under STRETCH.
  ⭐ GENERAL, and now the **tenth** occurrence of `aggregate-moved-check-membership-first`: adding
  valid, correctly-captured data can still move a gated verdict for a reason that has nothing to do
  with the model, and the only defence is checking the shared-membership subset before quoting
  anything. ⭐ **CHECKED (see SESSION 113's NEXT item 2): unlike session 111's `gain-n12` split, this
  is NOT a sign mixture** — the 8 hedge captures' own signed THD mean (+1.356 dB) matches the rest of
  the population (+1.389 dB) to two decimals; they just carry smaller absolute errors. **Still do not
  book the pooled rms crossing to SHIP as model progress** — it is the unsigned statistic diluted by
  lower-magnitude, same-signed rows, not by a compensating population.
  ⭐ **Acceptance test for any future twin-pair capture is free and immediate**:
  `analysis/compression_law_gate.py`'s S3 interlock (the 12 dB rung/send coincidence). A matched
  pair reads ~0.00000 dB; every re-dialled
  pair in the current set reads 0.066–2.08. **Run GATE S on it before using it for anything.**

  ⭐⭐ **A SAME-SESSION FULL-SEND MASTER LADDER IS IMPOSSIBLE AND WAS THE WRONG THING TO ASK FOR
  (session 112, corrected by the user): the high MASTER detents CLIP at full send — that is why the
  `gain-n12` captures exist at all.** And **different capture sessions ARE compatible: the rig is
  reamped identically**, which session 112 then confirmed independently — four clean twins spanning
  a 12-day gap read **12.000 dB flat to 0.0003 dB**. ⇒ a mixed-session ladder is fine, and the
  NOMINAL send dial is exact (it is the harness's 12.071 that is wrong, see the session-112 block).

  ⛔⛔ **THE LADDER'S TOP WAS PINNED, AND IT IS IN DATA THE PROJECT HAS BEEN USING:
  `master-1545_gain-n12` AND `master-1700_gain-n12` CARRY THE SAME SIGNAL.** Both peak at exactly
  **0.98850 (−0.10 dBFS)**, their band-mean levels are **+14.053 dB re noon for BOTH — step +0.000**,
  and the two files differ by only **1.5e−04 (−76 dBFS)**, i.e. they are two takes of one output, not
  two detents. Even at `gain-n12` the chain is pinned above `master-1430` (which is fine at
  −4.43 dBFS). ⇒ **the ladder had NO RESOLUTION above 1430**, and this is not new data — both files
  predate session 112 (07-25 and 07-29) and were in the s110 baseline.

  ✅✅ **RESOLVED, SESSION 112 — TWO FRESH `gain-n18` CAPTURES (`master-1545_gain-n18_base-clean.wav`,
  `master-1700_gain-n18_base-clean.wav`) CLOSE THE LADDER. Both are clean and cross-validated by TWO
  independent checks before either number was trusted.** (1) Each fresh n18 file, divided by its own
  pinned n12 twin, is **flat to 0.0002 dB** — exactly what a pure-gain relationship predicts, and the
  falsifying case is right there: an EARLIER `_archive/master-1700_gain-n18` capture from a
  contaminated 07-22 session gave an **11 dB, ±5 dB-ripple** "gain difference" against the fresh
  1545 capture, which is physically impossible for MASTER (asserted pure-gain, GATE O6) and is what
  flagged that whole archived batch (also containing the already-known-broken archived
  `ref-clean_gain-n18`, 12.3 dB span) as unusable. (2) Direct fresh-n18-vs-fresh-n18, no pad needed:
  **1545 − 1700 = −2.020 dB, span 0.0002.** Both checks agree.

  **THE COMPLETE, RESOLVED MASTER LADDER re noon** (n18 pad measured fresh at **6.000 dB** exactly,
  from `ref-clean.wav` vs the new `ref-clean_gain-n18.wav`, matching the nominal to 3 decimals):

  | detent | 0700 | 0815 | 0930 | 1045 | **1200** | 1315 | 1430 | 1545 | 1700 |
  |---|---|---|---|---|---|---|---|---|---|
  | dB re noon | −20.500 | −13.915 | −9.712 | −4.090 | **0.000** | +4.259 | +9.721 | **+16.480** | **+18.500** |
  | step | — | +6.59 | +4.20 | +5.62 | +4.09 | +4.26 | +5.46 | **+6.76** | **+2.02** |

  ⇒ **monotone throughout, and the top-end deceleration (+2.02 dB for the last detent, against
  ~4.5–6.8 dB per step everywhere else) is exactly the shape an A-taper pot approaching full CW is
  expected to have** — physically sensible for the first time. Session 106's MASTER-law table, built
  on the pinned +14.053 for both top detents, needs re-deriving from this ladder before it is quoted
  again.
  ⚠⚠ **CONSEQUENCE TO CHECK BEFORE TRUSTING ANY MASTER NUMBER:** session 41 calibrated
  **`kOutputMakeup = 2.599` at `master-1700`**, and session 106 re-confirmed it as "+0.007 dB" there.
  If that reading came from a pinned capture, the anchor was measuring the ceiling, not the pedal.
  **Not resolved here**; establish which capture session 41 actually used before acting on it — this
  is now checkable with a correct top-end value in hand.
  ⭐ **Nothing was lost:** the four full-send low detents that left `analysis/captures/` are in
  **`analysis/captures/_archive/`** (along with the contaminated `gain-n18` session), so the s110
  membership is recoverable if it is ever needed.
  ⚠ Separately, and NOT a session effect: the four archived full-send low detents differ from their
  `gain-n12` re-captures by **12.000 / 10.455 / 12.612 / 12.330 dB** — flat (sd 0.000, so pure gain,
  and peak ratios agree), but **not grouped by session** (07-21 gives 12.000 and 12.612; 07-29 gives
  10.455 and 12.330). ⇒ that is **MASTER knob position on a steep taper, up to 1.55 dB**, which is a
  different quantity from reamp level and does not contradict the identical-reamp fact above.

  **Session 111 capture inventory — 26 new matrix-grammar `.wav` files, none yet in any report**
  (`analysis/captures.py`'s self-validator: all parse cleanly against the filename grammar; the
  pre-existing `a3tones_*`/`jfet_ladder_*`/`notch_*` probe files are deliberately outside that
  grammar and unaffected):
  - **DRIVE ladder at `gain-n12`** (5, twins of the existing full-send `drive-XXXX_base-od.wav`
    ladder, no MASTER token so they pair with zero other confound): `drive-0700_gain-n12_base-od`,
    `drive-0930_gain-n12_base-od`, `drive-1200_gain-n12_base-od`, `drive-1430_gain-n12_base-od`,
    `drive-1700_gain-n12_base-od`.
  - **LEVEL × BLEND 3×3 matrix** (9, full send, fills GATE K6's flagged gap — "no rows with equal
    bleed and different LEVEL, the matrix has none"): `level-{0930,1200,1430}_blend-{0930,1200,
    1430}_base-od`, all 9 combinations.
  - **MASTER ladder at `gain-n12`, the remaining 5 of 9 detents** (1315/1430/1545/1700 already
    existed): `master-0700_gain-n12_base-clean`, `master-0815`, `master-0930`, `master-1045`,
    `master-1200` (same suffix `_gain-n12_base-clean.wav`). Full 9-point ladder now complete.
  - **EQ 0700 pairs, all four bands** (genuine full-send/`gain-n12` twins at ONE knob position per
    band — the belt-and-suspenders check on GATE O4/O5's clean-path-linearity extrapolation):
    `bass-0700_gain-n12_base-clean`, `treble-0700_gain-n12_base-clean`,
    `lomid-0700_gain-n12_base-clean`, `himid-0700_gain-n12_base-clean`.
  ⚠ Deliberately NOT captured, and not needed: `gain-n12` twins of the lomidfreq/himidfreq
  switch-combo captures (250/1k, 750/3k) at 0700 — the plain-band pairs above already test the only
  claim at stake (DIST-off linearity), which does not depend on which mid corner is selected.

- **BUG FIXED 2026-07-23: bypass-engage produced a constant click train, louder with more DRIVE.**
  Root cause in `PluginProcessor::processBlock` (nothing DSP/circuit-related — a plugin-level
  smoothing bug): `bypassMix`/`inputGain`/`outputGain` were copied into a per-channel local, and
  only that **copy** ever called `.getNextValue()`; the processor's own member `currentValue` never
  advanced. `SmoothedValue::setTargetValue()` no-ops once the target stops changing (true for every
  block after the first following a bypass press, since the target then just sits at 0 or 1), so
  the member stayed frozen at whatever `currentValue` it had when the target last changed — and
  every following block re-ramped from that same stale point instead of continuing. That produced a
  periodic partial wet/dry blend-in at every block boundary forever after the first bypass toggle
  (not just during the ~5 ms transition) — the click, louder at higher DRIVE because the "wet" side
  briefly blended in is the gain-boosted/distorted signal. **Fix:** step each smoother exactly once
  per sample into a shared per-block ramp buffer (`inGainRamp`/`outGainRamp`/`bypassMixRamp`, sized
  in `prepareToPlay`) and have both channels read that same array, instead of each channel owning
  and advancing a throwaway copy. Preserves "both channels step identically"; the member's real
  state now persists correctly across blocks. `src/PluginProcessor.{h,cpp}`; ctest still 16/16 (no
  console test exercises the plugin-level `AudioProcessor::processBlock` path, which is why this
  didn't trip a gate — worth keeping in mind for any future `SmoothedValue` usage in this file:
  never let a per-channel/per-voice **copy** be the only thing that calls `getNextValue()`).
- **FIXED 2026-07-23 (same session, user follow-up): rapid knob turns produced zipper clicks,
  worst on DRIVE.** Not a bug like the above — `PedalChain::applyParams()` is deliberately called
  once per block, not per sample (PedalChain.h: the MNA-based stages, Baxandall/MidBand, only
  re-invert their matrix on a dirty flag; doing that per sample would be a real CPU regression). So
  a fast knob sweep (or automation) could still jump the raw APVTS value a lot between one block and
  the next, and every stage recomputed its coefficients from whatever value it got with zero
  interpolation — audible as a step in signal amplitude at the block boundary, worst on DRIVE
  because its gain range is 4x-78x. **Fix:** smooth the 8 continuous pots (master/blend/level/drive/
  lo/loMid/hiMid/hi) at KNOB-VALUE level via `SmoothedValue::skip(numSamples)` called once per block
  directly on the member (not a per-channel copy — see the bypass fix above; the member itself is
  what advances this time, so the same bug class doesn't recur). This bounds how far a stage's
  coefficients can move in one block without adding any per-sample cost or touching the "recompute
  once per block" architecture — still exactly one MNA re-invert per block, just fed a value that
  can't jump arbitrarily far. `~20 ms` smoothing time (`kPotSmoothingSeconds`), matching the existing
  `inputGain`/`outputGain` constant. `readParams()` signature changed to take the 8 pre-smoothed pot
  values as params (switches — attack/grunt/mid-freq/bypass/dist_engage — still read raw; they're
  discrete topology swaps, not a smoothing gap). **Deliberately NOT fixed here:** clicks from
  flipping ATTACK/GRUNT/mid-freq switches — those are a separate, already-flagged, harder problem
  (glitch-free crossfade between two precomputed topologies, not a value-smoothing fix; see
  circuit.md/TrebleAttack.h "Phase 5 adds the glitch-free crossfade on top of this" and the GRUNT
  "deferred to Phase 6" note) — still open. `src/PluginProcessor.{h,cpp}`; ctest 16/16.
- **Target = Darkglass B7K Ultra** (schematic is the original-B7K "Black Mirror VII" clone; Ultra
  extras engineered on top). **8 pots**: MASTER[ENG], BLEND, LEVEL, DRIVE, LO, HI, LO-MID, HI-MID.
  Plus 3-way ATTACK[ENG] + 3-way GRUNT switches, and 3-position Lo-Mid/Hi-Mid freq selectors[ENG].
- **Engineered (not schematic-verified) parts** — flagged [ENG] in circuit.md: MASTER volume stage
  (post-EQ divider → IC6_B, also DI level); 3-way ATTACK (2-pos ULTRA-HI + centre Flat); switchable
  mid caps — Lo-Mid 47n/10n/2n2 (250/500/1k), Hi-Mid 15n/3n3/820pF (750/1.5k/3k). ✅ All six
  positions validated by nodal sim (±8.5% worst) AND the sim cross-checks against the p.3 measured
  tables (~3% / ±2.5 dB) — see circuit.md mid-band note. **Plus a 2nd DIST-engage
  footswitch** (real Ultra has 2 footswitches; ours only has 1 in the BOM) — model as a bool that
  overrides the BLEND crossfade to 100% clean, not a second bypass loop.
- **Web-confirmed 2026-07-19** (real Darkglass manual + reviews): Master/Attack wording and both
  mid-frequency sets match our `info.txt`/computed values exactly — high confidence. The DIST
  footswitch was new information, not previously in any doc.
- **Supply: single 9V, no charge pump.** 9V → D3 (1N5817) → +9V rail ≈ 8.6V. **VD = 4.5V**
  (R30/R31 10k/10k divider + 100µF, unbuffered). Op-amps TL072ACP/TL074ACN, clipper CD4049**UBE**.
- **Clipping = CMOS inverter (CD4049UBE) overdrive**, NOT diodes. D1/D2 (1N4148) are input rail
  clamps (~[−0.6, +9.6]V), rarely conduct. Model the 4049 transfer curve as the nonlinearity.
- **JFET stage (Q1/Q2 J201)** is an active gain stage (Q1 common-source + Q2 active load), not
  switches — needs a JFET device model or fitted gain+waveshaper. (See circuit.md / dsp.md.)
- **Non-WDF-native parts = ONLY the CD4049UBE clipper + the J201 JFET stage** (everything else is
  R/C/ideal-op-amp/diode). Modeling sources gathered 2026-07-19 → `docs/nonlinear-component-modeling.md`
  (+ 4 PDFs in `docs/refs/`: TI CD4049 datasheet, DAFx-2020 "Red Llama" CD4049-overdrive model,
  Fairchild J201 datasheet, DAFx-2024 JFET-WDF). Recommended: fit an asymmetric-tanh VTC waveshaper
  for the 4049 (DAFx params as ground-truth), and fit gain+soft-waveshaper for the J201 (part spread
  ~5:1 → must fit-to-capture, nominal SPICE won't match). **Pre-DSP capture plan is §4 of that doc**
  — do it in one matched session; it also resolves the IC2_B ~720 Hz bridged-T notch question.
- **Capture unit CONFIRMED = a real B7K Ultra, audio-only (¼" in→out, no internal probing).** Big
  win: we capture & VALIDATE all [ENG] features directly (Master, 3-way Attack, DIST footswitch,
  switchable mids incl. the 750 Hz Hi-Mid). Nonlinear models + the IC2_B notch are
  inferred from composite in→out (control-isolation + matched-pair diff). Finalized capture MATRIX
  (29 Tier-1 essential + 20 Tier-2 extended, explicit `key-value`-token filenames — no implicit
  state, see the grammar) = `docs/nonlinear-component-modeling.md` §4.
- **CORRECTED 2026-07-21 (pre-capture check):** the prior note here claiming `parse_capture()` was
  "added to `analysis/analyze.py`, tested against the whole matrix" was stale/wrong — that function
  didn't exist yet (still the template's `NotImplementedError` stub). **Now actually implemented in
  `analysis/captures.py`** (not `analyze.py`), against a fully explicit filename grammar (every
  filename = `key-value` tokens joined by `_`, ending in a required `base-od`/`base-clean` token;
  no parenthetical/implied state). Also fixed a real naming bug the old matrix had: `grunt-lo`/
  `grunt-hi` didn't correspond to any of GRUNT's actual three positions (`boost`/`cut`/`flat` per
  circuit.md's UI map) — corrected to `grunt-boost`/`grunt-flat` (baseline already covers `cut`).
  `python3 analysis/captures.py` (via `/opt/homebrew/bin/python3.11` — `python3` on this machine
  resolves to 3.13, which lacks numpy/scipy; pip installs against 3.11) self-validates all 49
  documented filenames with no captures on disk yet: 49/49 PASS. **`render_args()` ✅ IMPLEMENTED
  2026-07-22** against the now-existing `OfflineRender` CLI — emits every control explicitly (never
  leans on the binary's defaults), leaves `--in/--out/--os` to the orchestrators, special-cases
  `bypass.wav`, appends `extra_args` verbatim (how a `--fit` sweep varies one constant across a
  batch), and **does NOT pre-invert the EQ pots** (the dict is knob-space; OfflineRender applies
  `readParams()`'s `1-x` itself — inverting in both places mirrors every EQ fit while looking
  entirely plausible). Missing DC/rail values → take nominal from datasheets,
  calibrate the clip ceiling to the bypass+drive captures.
- **Value discrepancies resolved:** C33 = 22n (primary+BOM; backup's 2200pF is a different rev).
  GRUNT C13 = 220n (primary; backup 22n). Using primary values throughout. Both re-confirmed against
  BOM + schematic in the 2026-07-19 verification pass.
- **IC2_B recovery is a UNITY BUFFER, not a +12 dB active shelf** (verified in BOTH schematics —
  pin6 tied to pin7). The 100k/33k/680pF/22n parts are a passive bridged-T on the buffer output, not
  a feedback/gain leg. Consequence: **no recovery makeup gain exists** — do not budget +12 dB into
  gain-staging. Ideal sim of the bridged-T = deep ~720 Hz notch/scoop (tolerance-sensitive, surprising)
  → capture the real unit before finalising this section. Classic "same values ≠ same topology" trap.
- **C4 (JFET Q2)** connects gate→source(output) as a bootstrap, NOT gate→GND (was mis-stated).
- **R19 (1k)** is in the BOM but not yet located in the traced path — minor, non-critical, find it later.
- **Reusable crop tool** for the dense p.4 schematic: `schematics/crop.py` (see circuit.md crop index).
- **R19 (1k) RESOLVED (2026-07-19):** it's the CD4049's +9V supply dropper (only IC with one) —
  clipper clip-ceiling is BELOW the 8.6V op-amp rail and sags with signal. Calibrate the ceiling to
  captures, don't hardcode 8.6V. BOM fully reconciles (R1–R54 all located).
- **Tone stack fully node-verified (2026-07-19):** Baxandall (both wipers sum into IC5_C virtual gnd
  via R35/R36; C25/C26 run lug→wiper; R37 fb is 1 MΩ, schematic label "1m") and both mid stages
  (R41/R44 in→(−), R40/R45 (−)→out flat-unity legs; wiper→series-cap→(−)). Node graphs in circuit.md.
  Nodal sim validates all six [ENG] mid-cap positions (±8.5% worst) — per-position boost range varies
  (±14.5–28 dB), confirm against captures. GRUNT corners need the 4049's finite gain (~20–30) — model
  the clipper input as a coupled network, not ideal-virtual-ground.
- **C36 = 2u2 is schematic-verified** (EQ out coupling). Stock board has NO bias R on IC6_B(+) after
  C36; the [ENG] Master pot's VD leg supplies the DC path — cleaner than stock, no extra part.
- **UI assets ready in `ui/`** (knobs, footswitch, LEDs, switches, textures, VU trim — PNG with
  alpha, noon-position, rotation-safe) with prep guidelines in `ui/ui-replacements.md` (2x-resolution
  policy, crop-don't-stretch, resize-to-minimise). Use these for the Step 8 pedal face instead of
  procedural drawing where they fit; keep `src/ui/` LookAndFeel for the peripheral chrome.
- **UI assets + layout CSV LANDED (2026-07-20)** — base image `ui/b7k_texture_base.png` (1960×1540,
  no alpha), layout `ui/component positions.csv`, reference photo `ui/B7K ORIGINAL.jpg`. Full spec
  now in `ui.md` "Centre pedal face". Key facts: **CSV coords are base-texture pixel space** (origin
  top-left, X/Y = element centre, Width target, **blank Height = scale proportionally to Width**) —
  map every coord through one base-px→face-px scale. **Asset map:** knobs=`T_Knob.png`, footswitches
  =`Footswitch_up`/`footswitch_down`, LEDs=`blue_led_off`/`blue_led_on`, switches=`switch_up`/`_Mid`/
  `_down`, peripheral trims=`vol_trim.png` (NOT the old `Trim knob.png`). Two footswitches + two LEDs
  in the CSV (distortion + bypass) — confirms the [ENG] 2nd DIST footswitch. **ATTACK/GRUNT icon
  glyphs = render procedurally** (`juce::Path`, shelf lines/curves; CSV reserves 110×77 boxes) — I
  can draw these, no artwork needed from the user unless an exact match is wanted. LO-MID/HI-MID use
  text labels. **Switch-position→value mappings CONFIRMED by user 2026-07-20** (top/up→bottom/down),
  now in circuit.md: **ATTACK** up=Flat(C8 pole open)/mid=Boost(C8 bridges R8)/down=Cut(C8 shunts
  P→GND) — note centre=Boost, not the schematic's centre=Flat. ⚠ **CORRECTED 2026-07-20:** Cut is
  a C8→GND *shunt* (treble rolloff), NOT "R7-R8 junc→GND" (that earlier reading grounded node M and
  MUTED the path — wrong pole assignment; see circuit.md "ATTACK-SWITCH CORRECTION"). No position
  mutes; UI up/mid/down order unchanged. **LO-MID** up=500Hz(10n)/mid=1k(2n2)/
  down=250Hz(47n); **HI-MID** up=1.5k(3n3)/mid=3k(820pF)/down=750Hz(15n); **GRUNT** ✅VERIFIED at
  capture 2026-07-22: up/Boost=4n7∥220n(most)/mid/Cut=4n7 alone(least)/down/Flat=4n7∥47n(medium). That text: **font = Lexend Exa** (embed as binary data, this pedal's face text
  ONLY — peripheral chrome keeps its existing font), **colour = white**, opaque when selected,
  semi-opaque when not — replaces `PedalLookAndFeel`'s current `cSWLabelActive`/`cSWLabelInactive`
  light-/dark-blue constants. Full spec in `ui.md` "Centre pedal face"; plan updated in
  `docs/build-plan.md` Phase 8. Further pedal-face elements TBD until the assets land.
- **Full build plan: `docs/build-plan.md`** (2026-07-19) — step-by-step from submodules to release,
  with per-step validation gates and the capture-session checklist folded in.
- **UI pulled forward to Phase 4b (decided 2026-07-20 with user):** build a functional, APVTS-bound
  pedal face at the END of Phase 4 (before the Phase 5 clipper), so all Phase 5+ human-in-the-loop
  checks are done on real knobs/switches instead of the DAW's generic slider editor. Safe because
  APVTS is frozen at Phase 2 + UI is DSP-decoupled. Calibration-dependent polish (VU idle-gate
  threshold, final label opacity, headless scale gate) STAYS at Phase 8 — a second UI touch there is
  expected, not rework. Full rationale + scope in `docs/build-plan.md` "UI timing" + "Phase 4b".
- **Build-plan review pass (2026-07-20):** thorough gap analysis of the plan against calibration/
  validation/nonlinear docs + circuit.md; fixes applied to `docs/build-plan.md`. Biggest catch:
  **TL07x op-amp rail clamps were never scheduled anywhere** (calibration §6 requires them on every
  op-amp output; IC2_A at ×78 rails BEFORE the 4049 at max DRIVE; mids boost +28 dB) — now a Phase 4
  paragraph + gate item + risk #9. Also added: **LEVEL→BLEND pot loading** (not independent
  dividers; ≈3.5 dB crossfade imbalance at noon/noon — model the resistive network exactly, Phase 4
  item 6 + risk #10); bridged-T test-oracle caveats (oracle is unloaded; assert notch freq tight /
  depth loose, not ±0.25 dB at a notch bottom); treble/ATTACK stage-boundary decision (its input
  node is the JFET drain — pick one source-impedance convention for oracle AND WDF stage); `hq`
  APVTS-ID gotcha (can't "reserve" by omission — no audio/CPU impact, purely AU session-recall
  compatibility; **resolved: do BOTH** — version-hint every param `ParameterID{"id",1}` AND add
  `hq` now as a default-true no-op, decided with the user 2026-07-20); Phase 2 additions (bus
  layout, `ScopedNoDenormals`, `getBypassParameter()`); Phase 6 host
  `setLatencySamples()` on OS-factor change (distinct from the internal delay line); Phase 7 TL07x
  rail confirmation from captures; Phase 8 VU idle-gate recheck vs final makeup + don't-stall-on-
  assets fallback; interim `kInputRef` (~1–3 V/FS bass level) for Phases 4–6. `eq_reference.py`
  `bridged_t_tf` dead `Rload` param made functional (default None/unloaded — documented 717 Hz/
  −28.1 dB numbers unchanged, verified by re-run).
- **BLEND/bypass dry-wet phase-alignment gotcha added (2026-07-20, user's own hard-won lesson from
  another project) — covers BOTH delay and polarity, not delay alone:** (a) the clean BLEND tap
  splits off pre-JFET, i.e. before the oversampled region — an uncompensated crossfade against the
  OD path (which picks up the oversampler's FIR latency) comb-filters at every BLEND position; (b)
  independent of delay, the OD path reaching BLEND already carries one confirmed inversion (the
  clipper, ≈−48.5) plus an UNCONFIRMED one (the J201 stage's sign — needs its own DC-step test),
  so a per-stage-only test regime can miss an aggregate sign error at the BLEND node itself. Both
  fixes + null-test signatures (comb notches that shift with OS factor = delay bug; broadband/
  wrong-setting nulls that don't shift = polarity bug) now in `dsp.md` ("Dry/wet phase alignment
  across the oversampled region"), cross-referenced from `architecture.md` (Bypass), `circuit.md`
  (BLEND note), and `docs/build-plan.md` (Phase 4/6 + risk #8). Build the delay line AND run the
  end-to-end DC-step test in Phase 6; don't ship Phase 4's BLEND stage without both.
