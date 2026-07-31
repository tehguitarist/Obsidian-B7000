# Phase 9 — Reference validation (plugin vs the capture matrix)

> **The GATE-9 report: numbers, not adjectives.** How the plugin is A/B'd against the captures, the
> gaps found (with dB), the fixes shipped, and what is left.
>
> **Rewritten in session 89 (2026-07-31).** This file had reached 10,981 lines and its method and
> backlog were unreadable under ~9,000 lines of session narrative. That narrative is now
> **`docs/phase9-gap-log.md`** (verbatim, nothing deleted); the per-session handovers are
> **`docs/session-log.md`**; the generalisable traps are
> **`.claude/rules/measurement-discipline.md`**. Keep this file about METHOD and STATUS.
>
> **Read with:** `CLAUDE.md` (status + the release gate + next steps),
> `.claude/rules/reference-sources.md` (what the captures are),
> `docs/validation-and-capture.md` (measurement method), `.claude/rules/dsp.md` (fix rules).

> ⚠⚠⚠ **`analysis/captures/` IS A RECORDING OF THE NEURAL DSP DARKGLASS PLUGIN, NOT HARDWARE**
> (user-confirmed, session 71). Every "the pedal" in this file and in the gap log means the ND
> emulation. ND tracks hardware to ≤1.4 dB on the clean linear path — so the EQ, taper, level and
> topology work here is sound — but three things are aimed at the wrong target:
> **(a)** the "0.144 dB take-to-take floor" quoted throughout is not a physical noise floor;
> **(b)** session 70's rejection of the §2 repeatability set used a discriminator that is invalid
> against a deterministic renderer; **(c)** ⛔ **the even-order harmonic target is ~27 dB low.**
> ⇒ **a candidate that moves AWAY from the captures toward a documented hardware trend is a PASS,
> not a regression.** The matrix keeps authority only inside `reference-sources.md` §1's ND domains.

---

## 0. Status and backlog — START HERE

**The live status block, the agreed release gate and the ordered next steps are in `CLAUDE.md`
"Current step".** They are deliberately kept in one place; this section is the Phase-9-specific
detail behind them.

### Current grade (129 captures, shipped defaults, `analysis/reports/s74_baseline129.json`)

| subset | rows | band-RMS | median \|Δ\| | p90 | max |
|---|---|---|---|---|---|
| OD ex gain-n12 | 320 | **2.743** | 0.85 | 5.87 | 36.2 |
| CLEAN | 168 | **0.408** | 0.21 | 0.66 | 1.99 |
| THD (OD) | 228 | 9.292 | — | — | level term **6.202** |

Reproduce with:

```bash
/opt/homebrew/bin/python3.11 analysis/matrix_grade.py analysis/reports/s74_baseline129.json
```

⭐ **CLEAN is finished** (97.1 % of band values within ±1 dB). Regression-guard it, do not fit it.

### The work, in order

Full detail in `CLAUDE.md` "Open work, in order". In brief:

1. `c21R` 220k → ~130–150k (hardware-authoritative; we are matched to ND).
2. `jfetSatNeg` → ≈1.9 — blocked on a weighting judgement, **not** on more matrix runs.
3. The THD `level` term (6.2 dB) — the largest number on the board, never had its own session.
4. Re-fit the two-pole ATTACK against session 70's **corrected** spec, then ship-or-park.
5. **A3** — one timeboxed carrier hunt inside/before the clipper, then a fitted correction network.
6. A4 re-grade + the GATE-9 report → the `OSValidationTest` decision → Phase 10.

### What is CLOSED

See §4's index. The short version: GAP #1, #1b (twice), #3a, #3b, #4, A2c, A2d, A5, the "63 % LOCAL"
lead, the reference chart's harmonic columns, the `2·a·cn = 1` question, the H4 disagreement and
A3's apparent shape disagreement are all **closed**. Do not re-open them without new evidence —
several were re-opened once already and closed again at the cost of a session each.

### Known-bad rows (excluded explicitly, never silently)

The **16 `gain-n12` OD rows** are a CAPTURE defect, localised session 48: their THD turnover — which
no input or output gain can move — differs from their normal-gain twins' by up to 15.6 dB, and the
input pad their turnover position implies is 3–9 dB, not the 12.07 the harness renders them at. They
are **broken out in every `matrix_grade` print, not dropped.** The fix is a re-capture of 4 files.

## 1. Method

`analysis/comprehensive_report.py` renders the shipped plugin (`OfflineRender`, which now applies
the same `FitParams` the plugin does — session-17 wiring) through `analysis/test_signal_48k.wav`
at every capture's knob/switch settings, then grades plugin-vs-pedal per 1/3-octave band and per
THD anchor. `analysis/gap_audit.py` (and the session-18 aggregation probes) turn the JSON into a
prioritized gap list.

- **Deltas are SHAPE, not loudness.** Each capture is gain-matched to the plugin before
  differencing (`fr_at_bands` applies `null_depth`'s best-fit gain), so a band Δ is a voicing/FR
  error, not a level error. Absolute level is a separate axis (calibration §2 / makeup).
- **Grading thresholds** (`gap_audit.py`): `|Δ| > 3 dB` = real problem, `> 1.5 dB` = worth
  improving, `<= 1 dB` = good. Graded band 25 Hz–12.9 kHz (outside that the sweep energy / cab
  rolloff put both signals near the noise floor).
- **Trust anchors.** `bypass.wav` matches the plugin to **0.2 dB across all bands** — proof the
  pipeline (align, transfer, band extraction) is sound and resolves even 25 Hz correctly.

## 2. Running it cheaply (do NOT do full serial runs to iterate)

**The full 63-capture matrix now runs in ~6 min, not ~30** — `comprehensive_report.py` analyses
captures in a **process pool** (session 28). Captures are independent (one render + one analysis
against a shared read-only reference), so it is embarrassingly parallel. `--jobs N` / `-j N`,
default `min(8, cores−2)` = 8 here; each worker peaks ~600 MB. **Measured: 63 captures 768 % CPU,
5 m 42 s (was ~30 min serial); a 4-capture A/B went 116 s → 39 s.** `--jobs 1` restores the old
serial path for debugging. **Verified bit-identical** to serial output including capture ORDER
(the reference is loaded once per worker by the pool initialiser rather than pickled per task, and
results are re-indexed into capture order). The cache write is now atomic (tmp + `os.replace`) so
concurrent workers and Ctrl-C can't leave a truncated record that later reads as valid.

> ⚠ **Wall-clock is NOT runtime on this machine — check for sleep before diagnosing a "slowdown".**
> Session 28 killed a perfectly healthy full run after reading 10 captures in 87 minutes as a
> 9–17× regression. It was not: `pmset -g log` showed **`Entering Sleep state due to 'Clamshell
> Sleep'`** at 08:16 (lid closed, on battery) through 09:38, with only ~2 s DarkWake blips. The
> cache-file mtimes showed the true cadence — an exact **29 s per capture before AND after** the
> sleep window. Diagnose with per-capture cache mtimes (`find analysis/reports/cache -newermt ...
> -exec stat -f "%Sm %N" -t "%H:%M:%S" {} \;`) and `pmset -g log`, not elapsed wall-clock. Prefix
> long runs with `caffeinate -ims` (note: that still won't stop *clamshell* sleep on battery).

For iteration, use these (all `comprehensive_report.py`):

- **Per-capture result CACHE** — keyed by `(capture file identity + render args + OS factor +
  OfflineRender binary mtime)`. Captures are static, so a record only recomputes when the *plugin*
  output for those settings changes: a rebuild (new baked-in FitParams) or a `--fit` override busts
  only the affected records. Measured: 8-cap subset **189 s uncached → 0.83 s fully cached**. Cache
  lives in `analysis/reports/cache/` (gitignored).
- `--only SUBSTR[,SUBSTR]` — run just the captures whose filename matches (fast subset).
- `--fit K=V` (repeatable) — pass a `FitParams` override to EVERY render, so a candidate value can
  be tested **across the matrix without rebuilding** (the override is in the cache key).
- `--out PATH` — write to a scratch JSON so a subset/candidate run doesn't clobber the baseline
  `reports/comprehensive_data.json`.

Typical iterate loop: `python3.11 analysis/comprehensive_report.py --os 4 --only ref,bass,drive
--fit c21R=100000 --out /tmp/cand.json` → seconds after the first render, then aggregate.

Cache-key caveat: because the key includes the *binary* mtime, a `--fit c21R=X` render (old binary)
and a no-fit render from a rebuilt binary with that same value baked in get **different keys** even
though the output is identical — a rebuild won't reuse pre-rebuild `--fit` results. It never returns
stale data (the safe direction); it just occasionally re-renders what it could have reused. Key on
the *effective* FitParams (via `OfflineRender --print-fit`) if this ever becomes worth it.

**Session-23 tools.** `analysis/matrix_grade.py A.json [B.json ...]` prints the OD / CLEAN / ALL
band-RMS + tilt aggregate this document's tables quote (silent zero-knob rows excluded, graded
25 Hz–12.9 kHz), and with two reports the **row movement** (how many rows better/worse by >0.5 dB,
biggest mover each way, `--rows N` to list them) — the acceptance evidence to record beside any
aggregate, since an aggregate win built from a few big gains and many small losses is a different
result. `analysis/grunt_span_probe.py A.json [B.json ...]` prints the GRUNT **matched-pair span**
(position minus cut, per band, pedal vs plugin) at every drive setting, including the boost-vs-flat
ordering check — the GAP #4 span method generalised, and the metric that rejected C13 = 22n. It
un-applies the report's per-capture `gain_db_applied` before differencing, which a naive cross-capture
diff must also do. Both need no captures beyond the existing reports.

**Session-20 tools.** `analysis/od_tilt_metric.py <report.json>...` prints the GAP #3 tilt / low-band
RMS / mid-band RMS per OD capture and the mean, for any number of report JSONs side by side — the
metric every candidate above was scored on. `analysis/od_level_probe.cpp` (standalone:
`c++ -std=c++17 -O2 -I libs/chowdsp_wdf/include analysis/od_level_probe.cpp -o od_level`) measures
the OD chain's own transfer over an amplitude ladder, i.e. how the model's internal voicing moves as
it is driven — the gate that separated GAP #3a from #3b. Both need no captures.

## 3. Tooling caveats (must-know)

- **✅ HARNESS DEFECT — FIXED (session 21).** `render_args()` now emits
  `--input-trim -<measured dB>` whenever `gainSessionDb != 0` (the MEASURED
  `gain_correction_db`, −12.071, not the nominal dial), and the baseline
  `reports/comprehensive_data.json` was regenerated on it. Effect exactly as predicted: the 15
  `base-clean` n12 rows moved **< 0.05 dB** (linear ⇒ a level change is invisible after
  gain-matching) while the OD n12 rows moved a lot — `level-1700_gain-n12` drv−6 **18.27 → 5.80 dB**
  band-RMS, drv−12 12.04 → 6.76, `ref-od_gain-n12` drv−18 8.96 → 5.27; two rows got *worse*
  (`ref-od_gain-n12` drv−6 4.34 → 10.25, `level-0930_gain-n12` drv−6 2.50 → 4.19) — real
  drive-dependence error now measured honestly rather than accidentally cancelled. All-240-row mean
  band-RMS 4.386 → 4.298. **The rail-clamp verdict flipped on this fix — see GAP #3a.**
  The original defect, for the record: `render_args()` emitted every pot and switch but **never
  `--input-trim` for `gainSessionDb`**, so `OfflineRender` always ran at full test-signal level.
  The report then gain-matches the *output* by a scalar, which hides it completely for a linear
  capture — and silently invalidates **every nonlinear comparison** on those files.
  **Proof the SEND was lowered (the pedal saw less), not the record gain** — this is the one thing
  the fix depends on, so session 21 re-derived it from the raw WAVs and added a third, stronger leg:
  1. **cal_1k anchor, re-measured:** ref-clean → ref-clean_gain-n12 = **−12.071 dB**, but
     ref-od → ref-od_gain-n12 = **−2.854 dB**. A record-gain change is a scalar on the file and
     *must* give the same number on both; only compression INSIDE the pedal can shrink it.
  2. **Same pair on the quieter `sweep_clean` segment:** clean −12.146, OD **−9.362** — i.e. the OD
     shortfall tracks level (more compression at the hotter cal tone), the signature of a real
     input-level change.
  3. **⭐ Within-file, immune to session/take noise:** the pedal's own level-dependence collapses in
     the n12 file. The normalised band shape moves **2.59 dB RMS** across the drv−18→drv−6 sweep step
     in `ref-od.wav` but only **0.86 dB** in `ref-od_gain-n12.wav`. Under a record-gain change the
     pedal is driven identically in both files and those two numbers would be equal.
  **⚠ A tempting test that does NOT work (don't repeat it):** comparing the pedal's normalised band
  SHAPE of `ref-od_gain-n12` @drv−6 against `ref-od` @drv−18 (nominally the same absolute level).
  It appears to favour the wrong answer (@drv−6 matches at 1.89 dB, @drv−18 at 3.76) but it has **no
  discriminating power** — leg 3 shows a full 12 dB level step only moves the shape 2.6 dB, which is
  *below* the 3–4 dB take-to-take spread between the two capture sessions. Level anchors (high SNR,
  absolute) beat shape correlations here.
  **Scope:** ~15 of the 20 are `base-clean` (DIST disengaged → genuinely linear → unaffected); the
  exposed ones are `ref-od_gain-n12` and the four `level-*_gain-n12`, **plus any clean capture the
  model drives into a nonlinearity that the real pedal never reached** — which is exactly what the
  GAP #3a rail-clamp trial did (see below). **Fix: emit `--input-trim` from `render_args()`** (the
  flag exists) and re-baseline; this busts the cache for those 20 records only.
- **`gap_audit.py` does NOT exclude zero-knob SILENT captures.** `master-0700` (master=0),
  `level-0700` (OD volume=0) render to true silence → empty FFT bins → −640 dB → a **635 dB
  aggregate spread** that swamps `gap_audit`'s raw mean. Aggregate over VALID captures with a
  `min(plugin_db) > -60` filter (as the session-18 probes do), not `gap_audit`'s mean.
- **`gap_audit.py` / `cascade_analysis.py` DOCSTRINGS are template cruft** from a *different*
  pedal the template shipped with (they mention "PRESENCE", a "twin-T ~800 Hz notch", "V1/V2/V1E
  revisions", `phase10-gap-audit.md`). The **grading math is generic and correct**; ignore the
  topology narrative. `cascade_analysis.py`'s BLEND-discriminator logic is still valid for us.
- **`find_captures` skips non-matrix `.wav`** — the session-13 `jfet_ladder_*` diagnostic captures
  use underscore stimulus names (not `key-value`), so they're skipped with a note (a real matrix
  typo still surfaces as a skipped-file line).
- **The 320 Hz band dip in the OD captures is REAL, not an artifact — do NOT exclude it** (session 20
  checked, having first assumed the opposite). Across all 240 valid rows the pedal's 320 Hz band sits
  **−5.5 dB median** below the mean of its 254/403 Hz neighbours in **DIST-engaged (`base-od`)
  captures** and **0.00 dB median** in clean ones (min −1.3). Present only in the OD path, at the
  frequency of the TrebleAttack two-path cancellation notch → this is that notch (GAP #2), measured.
  **The plugin does not reproduce it** (its own 320 Hz dev is ~0 in the same OD captures). Useful as
  a *bleed-sensitive* probe: an OD-path notch only survives into the output if the OD sits above the
  clean bleed there, so "pedal shows its notch, plugin doesn't" says the plugin's OD is too weak
  relative to bleed in the mids — consistent with GAP #3b.
- **Driven low-band FR is contaminated by clipping harmonics** — sub-knee fundamentals get clipped,
  so the driven sweep's low bands are NOT a clean measure of a *linear* filter. Fit linear
  low-frequency shaping (e.g. coupling caps) on the CLEAN sweep; use driven only as a cross-check.
- **⚠ THE REPORT'S BROADBAND GAIN-MATCH CAN MANUFACTURE A FAKE "INCREASING HF ROLLOFF" WHILE A3 IS
  OPEN — read any chart with this in mind (session 30, 2026-07-26).** `fr_at_bands()` computes ONE
  scalar `gain_db` per capture via `null_depth()` (a broadband time-domain least-squares fit over the
  WHOLE sweep) and bakes it into every `plugin_db` value before it ever reaches a chart. On `ref-od`,
  re-anchoring that scalar to bands ≥200 Hz instead of the whole sweep collapses an apparent −3…−6 dB
  "rolloff" above 300 Hz down to ≤~1 dB — i.e. the LF excess from the still-open A3 cancellation null
  (below) drags the *one* broadband scalar down, which then reads as a phantom mid/high shortfall on
  every band above it, even though the mid/high match is actually fine. **Any "the plugin is quieter
  and quieter as frequency rises" read on a current chart should be re-checked with an LF-excluded
  gain-match before it's treated as a real, separate error** — most of it should evaporate once A3
  ships. See §4 "A3 chart-review corroboration" for the worked numbers (both `ref-od` and
  `ref-od_gain-n12`).

## 4. Gap log — INDEX

> ⚠ **The full narrative moved to `docs/phase9-gap-log.md` in session 89** (it was ~9,000 of this
> file's 11,000 lines). Nothing was deleted. This is the index: what was found, what state it is in,
> and where the evidence lives. **Search the gap-log file by the section titles below.**

### Closed — do not re-open without new evidence

| Gap | Verdict | Closed |
|---|---|---|
| **GAP #1** — low end 6–15 dB light | FIXED, `c21R` 10k → 100k (later 220k) | s18 |
| **GAP #1b** — bridged-T ~717 Hz notch | NOT A GAP. Closed s19, re-opened s20, re-closed s21 on 116 OD rows; re-opened s64 on a 6.2 dB shape error and **re-closed s65 — that was a missing `--grunt` flag**, not a circuit error | s21 / s65 |
| **GAP #3a** — drive-dependent bass tilt | FIXED, rail clamp enabled (`railNeg` 2.9 / `railPos` 2.7, DERIVED not fitted) | s21 |
| **GAP #3b** — GRUNT bump-vs-shelf | DISSOLVED — the premise was 14 sessions stale; the BLEND sum turns a monotone OD shelf into an output bump for free | s23 / s38 |
| **GAP #4** — mid positions over-deliver range | FIXED, `midWiperR` + cap table | s22 |
| **A2c** — clean-baseline accuracy | **CLOSED, TARGET MET.** The mid selector is a 2-POLE switched cap PAIR (`midCapRatioLo/Hi = 10`) | s27 |
| **A2d** — sub-60 Hz clean deficit | FIXED, `c21R` → 220k | s28 |
| **A5** — clean path distorts at hot levels | FIXED, `kInputRef` 3.377 → 1.2596 + the whole clipper/JFET family re-fitted | s44 |
| **"63 % LOCAL" lead** | ANSWERED, negatively — not one unexplored feature; 18.5 % is a polynomial edge artefact, 16.4 % is 320 Hz, the rest is incoherent per-row spread | s69 |
| **The reference chart's H2−H3 columns** | DEMOTED — neither column survives a test against the real ND device at the chart's own tone | s78 |
| **`2·a·cn = 1` identity** | AFFORDABLE but NOT FREE — costs the authoritative odd column in both drive regimes | s83 / s84 |
| **The H4 disagreement** | NOT A DISAGREEMENT — both halves are medians over 30–40 dB spreads | s83 |
| **A3's "shape disagreement"** | NOT REAL — the two instruments describe ONE curve; quote A3 as ≈5–7 dB over 100–400 Hz | s86 |

### Open

| Gap | State | Next move |
|---|---|---|
| **A3** — OD too weak vs the clean bleed, ≈5–7 dB over 100–400 Hz | MEASURED to death by two corroborating instruments; **no carrier found in ~20 sessions.** No single element (s50) and no post-clipper linear element of any order (s52) can supply it. Only region not ruled out: **inside/before the clipper** | ONE timeboxed session, then fall back to a fitted correction network |
| **GAP #2 / ATTACK** — the ~320 Hz notch, +26 dB, largest single-band error | Two-pole topology BUILT in `src/` (defaults to a no-op), but its spec was **corrected in s70** and it has not been re-fitted since | Re-fit against the corrected spec, then ship-or-park |
| **Even-order, low drive** — `jfetSatNeg` | LOCATED (≈1.9) and matrix-judged. ⛔ Stop rendering `a` candidates — the matrix has said all it can | A weighting judgement, not a measurement |
| **THD `level` term, 6.2 dB** | The largest single number in the project. Never had a dedicated session | Own pass, from the THD decomposition |
| **`c21R`** | We sit at 7.2 Hz, matched to ND; hardware wants ~11–12 Hz ≈ 130–150k | One constant + one matrix run |
| **A2e** — >10 kHz mid-boost skirt | QUANTIFIED (−6.03 dB @16 kHz at HI-MID 3k), element NOT identified. Bilinear warp RULED OUT by measurement | after A3 |
| **A2f** — ±0.2 dB clean tilt | CHARACTERISED, PARKED. ~3× the take-to-take floor | park |
| **A3-adjacent** — `gain-n12` HF collapse | Localised s48 as a **capture defect** (THD turnover differs by up to 15.6 dB, which no gain can move) | re-capture 4 files |
| **>8 kHz OD error** | ⭐ NEW s89 — probably **ND's aliasing, not ours** (see `CLAUDE.md`). Reported, not gated | verify before any work |

## 5. Performance / HQ pass (not started)

`PerfBenchmark` / `FeatureProfile` / `OSFidelity` → the `hq` toggle decision (omega4 vs
AccurateOmega is usually the only real lever) + README perf table. Plus the deferred OS-fidelity
work: the session-17 4× narrow-band aliasing residual at the amp-0.5 extreme corner (8× is pristine;
recommend 8× for extreme high-drive) — see the OSValidationTest header.

**⚠ Also required (added 2026-07-27, per user request): explicit NO-OS and LOW-OS sweeps, with a
documented compensation decision — not just the 8×-reference OSFidelity comparison already planned.**
`dsp.md`'s "Low-OS top-octave restore" pattern is written up as a design option but has never been
run or decided on for this pedal. Before GATE 9 closes the perf pass:
1. Run `OSFidelity` (or extend it) at **OS = 1× (no oversampling) and 2×**, not only the existing
   1×/2×/4× vs 8× comparison implied by its description — read both the aliasing/harmonic-vs-clean
   picture (its existing job) AND the plain linear-stage top-octave droop from bilinear cap warping
   (`dsp.md` "Top-octave accuracy") at each factor, since a low-CPU/low-latency user may run the
   plugin at 1× or 2× routinely, not just transiently.
2. **Decide, in writing, whether the droop measured at 1×/2× is large enough to need the low-OS
   shelf compensation** `dsp.md` describes (a single fixed-shape high-shelf biquad at base rate,
   gain set per OS factor, ~0 at 4×/8× so the default is untouched) — implement it if so, or record
   the measured droop and an explicit "accepted, not worth the extra stage" if not. Do not leave
   this an open design note; GATE 9 needs a decision, not just the option on record.
3. Keep A5 (above) in view while doing this: A5 is NOT an OS-dependent defect. **Verified directly
   (session 39): `ref-clean.wav`'s `lvl_-3` render is bit-identical across OS 1×/2×/4×/8×
   (THD = 22.8546% and H2/H3 to 4 decimal places at every factor)** — confirming it lives entirely
   in the base-rate EQ block, so fixing it will not appear in, and should not be conflated with,
   this OS-fidelity/compensation work.

## 6. Carry-forward from Phase 8

Re-verify the **VU idle-noise gate threshold against the new makeup** (0.9 → 3.684 shifted the idle
floor ~4×; calibration §7 / build-plan Phase-8 item 3). The meter may show idle noise as activity
until the threshold is re-checked.

---

