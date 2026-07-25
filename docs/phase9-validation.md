# Phase 9 — Reference validation (plugin vs real-pedal captures)

> **The GATE-9 report: numbers, not adjectives.** Records HOW the plugin is A/B'd against the
> captured Darkglass B7K Ultra, the gaps found (with dB), the fixes shipped, and what's left.
> Read this + `docs/validation-and-capture.md` (method) + `.claude/rules/dsp.md` (fix rules).
>
> **Status (2026-07-25, session 25):** Phase 7 calibration shipped (session 17); Phase 8 UI done.
> Phase 9 in progress. FIXED + committed: GAP #1 (low end), GAP #1b (bridged-T — investigated twice,
> closed both times, non-issue), GAP #2 (treble notch), GAP #3a (rail clamp), GAP #4 (mid-band range),
> **A2c-1 (TREBLE range, session 25)**, plus the gain-n12 harness defect. GAP #3b is CLOSED as
> mis-attributed (session 23): it is not a GRUNT-cap gap, and neither the ÷4 nor the `C13 = 22n`
> candidate was shipped — see §4 "3b CLOSED".
> **User-initiated detour (session 24-25): before resuming A3, nail the base-clean path** (no
> nonlinearity, so a clean-path error is a confound sitting under every OD comparison) — see §4
> "A2c". Session 24 fixed two bad captures + a grading bug and agreed the target; session 25 shipped
> the first fit (`trebleWiperR`, R36 3.3k → 4.7k). **Two voicing items remain open: A2c (clean
> tightening — target ≤0.7 dB mean NOT yet met at 1.168, and the entire remaining residual is the
> mid-band group) and A3 (the OD/clean BLEND balance below ~200 Hz, quantified — §4 "A3 handover").**
> Current grade (240 rows, re-baselined session 25): **OD 5.965 / CLEAN 1.152 / ALL 3.558 dB**
> band-RMS.

---

## 0. Backlog — prioritized TODO (START HERE on a fresh session)

Ordered by impact on "sounds like the real pedal" first, then release-readiness. Each links to the
detail section below. Check off + move to the Gap log (§4) as they land.

**A. Close the remaining voicing gaps (Phase 9 core — highest impact on the sound):**
- [x] **A0. Regenerate the full 63-cap baseline report at the shipped c21R=100k** (session 19). Confirmed GAP #1 holds (clean low end ~0 dB). Cache seeded.
- [x] **A1. Bridged-T ~717 Hz notch** — INVESTIGATED, **CLOSED, non-issue** (session 19, re-opened and re-closed session 20/21). Tested like-for-like in the OUTPUT: plugin's mid dip matches the pedal's to ~0.5 dB over 116 OD rows (median −2.45 vs −3.02 dB). Topology re-verified pixel-zoom on both schematics, identical. Do NOT reshape `bt*`, no `schematic-checker` pass needed. See §4 GAP #1b.
- [x] **A1b/c/d. TREBLE ~322 Hz notch too deep — the real root gap. FIXED + shipped** (session 19, GAP #2 below). Found while chasing A1: the OD low-mids (100–500 Hz) are scooped by the treble-ladder two-path cancellation notch (~28 dB model vs −3.4 dB capture). New `trebleLadderDampR=30k` shallows it. This is the root of the "backwards GRUNT" + the 254 Hz BLEND null.
- [~] **A3 STARTED (session 20) — DECOMPOSED into two independent gaps, see §4 GAP #3.** The
  residual is NOT one thing: **3a** is a DRIVE-DEPENDENT bass tilt (the DRIVE op-amp's rail clamp
  has never been enabled) and **3b** is a STATIC ~19-23 dB bass tilt that only GRUNT flat/boost
  expose. Levers tested and **refuted**: `clipA0` (null), `clipC11` (−1 dB), bridged-T series
  damping (no efficient element exists), R24/SK loading of the bridged-T (deepens it). Levers with
  a real hit: `railEnabled=1` (−5…−8 dB tilt at drive-1430/1700, its predicted domain) and the
  GRUNT caps `clipC12/C13` ÷4 (−2.1 dB mean, −8 dB on grunt-flat) — **neither shipped yet.**
- [x] **A2. Mid-band deviations > 1.5 dB — MINED (session 21). No broadband mid EQ error exists**
  (clean rows median −0.31 dB; EQ pots band-RMS 1.70; ref/attack 0.31). The uniform mid deficit on OD
  rows is GAP #3b's bass excess seen through the gain-match. **But it surfaced a NEW, larger gap:**
- [x] **A2b / GAP #4. The switchable MID positions over-deliver RANGE — FIXED + shipped (session 22).**
  `schematic-checker` returned **TOPOLOGY CONFIRMED FAITHFUL** (MidBand.h matches circuit.md node for
  node; the full R1–R54 BOM census leaves no spare resistor), so the decision tree's fit-to-capture
  branch applied. Shipped: **`midWiperRLo = 33k` / `midWiperRHi = 22k`** (a fitted series R in the
  wiper leg, `MidBand::setWiperR`, Norton-reduced like `trebleLadderDampR` — no new MNA node) and
  **`midLoCap250 = 47n → 22n`** (the capture's 320 Hz centre = the STOCK board's C33; the one cap
  value the captures actually contradict). Span band-RMS **9.66 → 4.68 dB**, 4-point POT LAW RMS
  **5.31 → 0.87 dB**. ctest 16/16. Rail compression and knob under-travel were both explicitly
  killed first. **⚠ Two residuals:** the two SMALLEST caps are slightly over-corrected (one resistor
  serves all three positions of a band — accepted trade), and Rw pulls the LO-MID 500 / HI-MID 750
  centres a band low. §4 GAP #4.
- [x] **A2c-2. Mid-band SHAPE — FIXED + shipped (session 26); A2c then CAPPED.** The A2c residual was
  neither centre nor range error but peak **WIDTH**, caused by GAP #4's own `midWiperR` (a damping R
  buys range by lowering Q, and the SPAN objective GAP #4 fitted is blind to width). Re-fitted Rw and
  the whole switched-cap table together against the pedal's full stage shape: **`midWiperRLo` 33k→22k,
  `midWiperRHi` 22k→18k, caps 15n/6.8n/1.8n and 10n/2.7n/0.68n.** Peak-frequency error **13.0 %→3.1 %**
  mean (the 1/3-oct grid had been hiding it — all six positions were 9–20 % low, not the two recorded);
  bandwidth ratio 1.54×→1.31×; CLEAN **1.152→1.023**, per capture **1.168→1.045 dB**, 5 rows better
  >0.5 dB / 0 worse, OD bit-identical. All 8 values at interior minima. **A2c's ≤0.7 / ≤1.5 target is
  NOT reachable** — the remaining width error needs C32 (schematic-verified, fixed) to vary per switch
  position. Achievable floor recorded as ~1.0 dB mean / ~3.3 dB worst. §4 A2c-2.
- [ ] **A3. OD/clean BLEND balance — now the BIGGEST residual.** The `grunt-boost`/`grunt-flat` captures stay 12–26 dB off after the notch fix: a sub-bass excess (20–40 Hz) where the pedal has a low-mid bump. Session 19 proved the 254 Hz null is NOT a polarity bug (OD/clean in-phase at LF) and C12/C13 don't fix it (level, not corner). Root suspect = the clean-bleed level/shape + grunt coupling in the clipping regime (kInputRef 0.87→3.377 move). **Start here for the next voicing gain.** Probes: `blend_null_probe.cpp`, `od_taps_probe.cpp`.
- [x] **A3-next (0). `render_args()` now emits `--input-trim`** for `gainSessionDb`; baseline
  regenerated (session 21). Send-vs-record-gain settled three ways. §3.
- [x] **A3-next (i). IC2_B recovery network — CLOSED, not a gap** (session 21). Topology re-verified
  at pixel zoom on BOTH schematics (identical, dot for dot) and, tested like-for-like in the OUTPUT,
  the plugin's mid dip matches the pedal's to ~0.5 dB across 116 OD rows (and is *shallower*, not
  deeper). Session 20's re-opening compared a stage transfer against an output shape. No
  `schematic-checker` pass needed. §4 GAP #1b.
- [x] **A3-next (ii). SHIP the rail clamp — DONE (session 21).** `railEnabled = true`,
  `railNeg = 2.9`, `railPos = 2.7` (physically derived from the +9V/D3/VD chain, not fitted — the
  fit objective is monotone with no interior minimum, a known degeneracy). All 240 rows band-RMS
  4.298 → 4.057 dB, 31 rows better by >0.5 dB vs 4 worse. ctest 16/16. §4 GAP #3a.
- [x] **A3-next (iii). GRUNT caps — CLOSED (session 23). NOT the lever; nothing shipped.** The
  `schematic-checker` pass ran and **confirmed 220n on the primary** (unambiguous at 900 DPI, symbol +
  BOM — but they are ONE CAD source, and neither schematic describes the Ultra we captured). The fix
  was **rejected anyway**, because the excess it appeared to fix is mis-attributed: it is **fully
  present at GRUNT *cut*** with C12/C13 out of circuit (+12.8 dB at 40 Hz), it **tracks the BLEND
  knob** not GRUNT (−0.47 dB at pure clean → +9.51 at full OD, clean path 0.32 dB), the `clipC13` 1-D
  scan is **monotone to 0.5 nF** (best "fit" = delete the cap — the known degeneracy), and 22n
  **inverts** the switch's measured boost-over-flat ordering (−3.8 dB vs the pedal's +5.9) — the same
  trap that got GAP #4's joint fit rejected. The pedal's GRUNT span is a 127–202 Hz **bump**, the
  model's a monotone **shelf**: no cap value converts one into the other. §4 "3b CLOSED".
- [ ] **A3. OD/clean BLEND balance — THE remaining voicing gap, now QUANTIFIED.** Target: at GRUNT
  cut / drive noon / BLEND max the OD position needs **~13–15 dB less 40–64 Hz**, tapering to 0 by
  ~200 Hz (mids already right to ~1 dB). **⛔ Hard constraint: attenuating the OD path cannot be
  sufficient** — muting its LF entirely still leaves the model 3.6 dB above the pedal's *total* 40 Hz
  output, because the `LevelBlend` B=1.0 residual bleed floor sits there. So the bleed's LF
  level/phase is necessarily part of the fix; gate any OD-only candidate against that number first.
  Leading hypothesis is frequency-dependent OD-vs-bleed **phase** near the ~896 Hz GRUNT-cut coupling
  corner (which would explain the bump-vs-shelf shape, not just the level) — `blend_null_probe.cpp`.
  ⚠ Not a polarity/sign bug; session 19 settled that. **START HERE.** §4 "A3 handover".
- [ ] **A4. Write final GATE-9 numbers into §4.** GATE-9 should wait for A3, which is the last
  documented gap materially moving these numbers.
- [~] **A2c. Clean-baseline accuracy pass — STARTED (session 24, 2026-07-25), user-initiated.**
  Nail base-clean (BLEND=0, no nonlinearity) to a tight tolerance BEFORE resuming A3, on the theory
  that a clean-path error is a confound sitting underneath every OD comparison. Two bad captures
  found + fixed (`master-1700_gain-n12`/`bass-1700_gain-n12` re-recorded) and a real grading bug
  fixed (`matrix_grade.py::is_od()` mis-classified `ref-od_gain-n12.wav` as CLEAN). Target
  **≤0.7 dB mean / ≤1.5 dB worst-case** over 29 independent captures (not 124 "rows" — see caveat
  below). **Session 25: first fit shipped — `trebleWiperR` (R36 3.3k → 4.7k) closes the TREBLE range
  error** (`treble-1700` 2.11 → 0.65 dB; 6 rows better >0.5, 0 worse; OD untouched). Mean clean
  **1.235 → 1.168 dB**, **21/29** captures ≤1.5. **Target still not met**; the whole remaining
  residual is the mid-band group, which GAP #4's `midWiperR` trade already touched — establish
  whether those can move before spending more budget. See §4 "A2c" + "A2c-1".
  Baseline: **OD 5.965 / CLEAN 1.152 / ALL 3.558 dB** band-RMS over 240 rows.

**B. Performance / quality pass (Phase 9 part 2):**
- [ ] **B1. PerfBenchmark / FeatureProfile / OSFidelity probes** → the `hq` toggle decision (omega4 vs AccurateOmega is usually the only real lever) + README perf table. See §5.
- [ ] **B2. Deferred OS-fidelity residual** — the 4× narrow-band aliasing at the amp-0.5 extreme corner (8× pristine; recommend 8× for extreme high-drive). See §5 + the OSValidationTest header.

**C. Carry-forwards:**
- [ ] **C1. VU idle-gate threshold vs the new makeup** (0.9 → 3.684 shifted the idle floor ~4×; the meter may show idle noise as activity). Phase-8 carry-forward, §6.
- [ ] **C2. `schematic-checker` pass on C21** — attribute the measured ~10× corner shift to the cap value (>100n?) vs the stack-input impedance (>10k?). The capture is authoritative on the corner regardless; this is provenance. §4 GAP #1.

**D. Release (Phase 10):**
- [ ] **D1. Full control-sweep soak** — all 8 pots × switches × OS × bypass/DIST transitions: no instability/clicks/NaN/Inf (output > 0 dBFS at extremes is faithful — trim manages it).
- [ ] **D2. Installers + `release.yml` dry-run + signing** when certs exist. (build.md "Installers".)

**E. Housekeeping (optional / low-priority):**
- [ ] **E1. Merge `phase9-kickoff` → `main`** (`git checkout main && git merge --ff-only phase9-kickoff`) — 4 Phase-8/9 commits are on the branch.
- [ ] **E2. Cache-key on effective FitParams** (via `OfflineRender --print-fit`) so a `--fit` result is reused after that value is baked in + rebuilt. Nice-to-have; current key is safe (never stale), just occasionally re-renders. §2 caveat.

---

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

## 2. Running it cheaply (do NOT do 25-min full runs to iterate)

The full 63-capture matrix is ~20-25 min. For iteration, use these (all `comprehensive_report.py`):

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

## 4. Gap log

### ✅ GAP #1 — Low end 6–15 dB light (the "too thin" sound). FIXED, committed `21e91d2`.

**Symptom.** Over all valid captures, median Δ (plugin−pedal), clean AND driven (identical → a
shared post-BLEND linear filter):

| band | Δ before | band | Δ before |
|---|---|---|---|
| 25 Hz | −15.6 dB | 320 Hz | −4.1 |
| 40 Hz | −12.5 | 500 Hz | −1.8 |
| 63 Hz | −9.0 | 800 Hz | −0.7 |
| 100 Hz | −6.0 | 1 kHz | −0.7 |
| 160 Hz | −3.5 | 2 kHz | −0.5 |
| 250 Hz | −4.8 | 5–10 kHz | ~0.0 |

**Above ~500 Hz the plugin already matches the pedal to ~1 dB median** — the session-17 drive
calibration + the EQ voicing are correct. The deficit is a textbook first-order high-pass at
~159 Hz (predicted −16.2/−12.3/−8.7/−5.5/−3.0 at 25/40/63/100/160 Hz — matches to <1 dB).

**Cause.** The only post-BLEND element at that corner: **C21 (100 nF) against the tone-stack input
impedance**, modeled as the nominal `c21R = 10 kΩ` → fc = 159 Hz. That impedance estimate was never
validated (flagged in `FitParams.h` as "a real fit knob").

**Fix.** `c21R 10k → 100k` (corner → 16 Hz). Fit on `ref-clean` (flat EQ), then validated across 34
EQ/blend captures with `--fit c21R=100000`:

| | before (10k) | after (100k) |
|---|---|---|
| CLEAN low-band RMS (25–400 Hz) | 9.79 dB | **0.69 dB** |
| DRIVEN low-band RMS | 9.84 dB | **0.71 dB** |

No overshoot (an earlier single-capture `ref-od` overshoot was a clipping-contamination artifact;
the aggregate driven median is clean). Residual ~1 dB at the noisy 25 Hz band edge only.

**Physical note.** A 16 Hz corner implies C21's effective RC is ~10× the nominal — either C21 > 100n
or the stack-input Z > 10k. `c21R` is the sanctioned model knob for this corner and the capture is
authoritative (dsp.md "fit the corner"), but **C21's exact schematic value/placement is worth a
`schematic-checker` pass** to attribute the ~10× to the cap vs the impedance.

### ✅ GAP #1b — Bridged-T ~717 Hz notch (risk #1). INVESTIGATED, NOT A GAP (session 19).

No unmatched notch: across all OD-path captures, bands 508/640/806/1016 Hz sit flat together
(~−1.5 dB) with no local dip at 717 Hz. The bridged-T is fine as-is; `btR22/btR23/btC16/btC17` were
left at their schematic values. (The isolated model notch is filled by the clean bleed in the full
output, so it never surfaced as a capture gap.)

### ✅ GAP #2 — Treble ~322 Hz notch too deep → OD low-mids scooped. FIXED (session 19).

**Symptom.** The OD path's low-mids (100–500 Hz) are scooped: the plugin's OD peaks ~50–60 Hz and
falls off a cliff above, while the pedal has a low-mid bump at ~180 Hz. This made GRUNT look
"backwards" (the pedal's GRUNT is a ~180 Hz growl bump; the plugin's was a sub-bass shelf) and
exposed a 254 Hz null in `grunt-boost` (the OD low-mids drop to the flat clean-bleed level, so the
ordinary OD-vs-clean phase cancellation becomes visible — NOT a polarity bug: OD/clean are in-phase
at LF, +8.9° @40 Hz).

**Localised** (`runOdSampleTapped` + `analysis/od_taps_probe.cpp`) to ONE stage: the **TrebleAttack**
network (JFET→treble transimpedance). Its ~322 Hz two-path cancellation notch (R7 vs the C5/C9/C6
ladder) is **~37 dB deep in the assembled model but −3.4 dB in the capture** — the parked risk
register #1 item ("Monte Carlo tolerance can't explain it"). Downstream stages just add gain,
preserving the scoop.

**Cause.** The ideal two-path cancellation is far more perfect than the real circuit's — a series
loss the ideal model omits (cap ESR / PCB / an unmodelled damping R).

**Fix.** New `trebleLadderDampR` (`FitParams`): a series damping R on the C5 ladder cap, modelled as
a lossy cap (Norton reduction, no new MNA node; Rd=0 = ideal exactly). Fit to the clean OD captures:

| | before (Rd=0) | after (Rd=30k) |
|---|---|---|
| low-mid RMS (127–640 Hz), 6 flat-EQ OD caps | 3.64 dB | **1.96 dB** |
| HF cost (1–6 kHz) | — | +0.11 dB (the knee; 40k trades +0.12 HF for −0.09 more low-mid) |

Validated: the C++ lossy-C5 matches the independent Python oracle (`treble_attack_tf(RdampC5=...)`)
to <0.05 dB at Rd=30k across all ATTACK positions (`TrebleAttackTest` Tests 6/7). ctest 16/16.

**Physical note.** 30k is large for literal cap ESR — the origin (why the ideal notch is far too
deep; tolerance ruled out) is a `schematic-checker` follow-up, but dsp.md makes the capture
authoritative on the notch depth (same posture as c21R's 10× corner).

**Payoff is modest (~1.7 dB low-mid)** because the flat clean bleed already fills the isolated 37 dB
notch in the full output (it cost only ~2–4 dB in captures). The BIG residual — the `grunt-boost`
sub-bass — is a SEPARATE issue (A3 / GAP #3, not yet fixed).

### ✅ GAP #1b — CLOSED (session 21). The bridged-T is correct; session 20's re-opening was itself the wrong test.

**Session 21 verdict: the IC2_B network is NOT a gap and the file needs no further work on it.**
Session 20 re-opened it (kept below for the record) by comparing the *model's isolated stage
transfer* (−28.1 dB at 717 Hz) against the *pedal's OUTPUT band shape* (~4 dB dip) — two different
quantities. Compared like-for-like, in the OUTPUT, the plugin and the pedal agree, and the residual
sign is the **opposite** of the hypothesis:

| dip at 640/806 Hz vs the mean of its 403/1613 Hz neighbours | plugin | pedal | plugin − pedal |
|---|---|---|---|
| all 116 valid OD rows (median) | −2.45 dB | −3.02 dB | **+0.41 dB** (mean +0.48) |
| all 120 clean rows (median) | +0.01 | −0.03 | +0.04 |
| `drive-0700_grunt-boost` sweep_clean (session 20's own exhibit) | −4.1 | −5.3 | +1.2 |

The plugin's mid dip is if anything ~0.5 dB **shallower** than the pedal's — the clean bleed fills
the isolated 28 dB scoop in BOTH, identically. There is no excess scoop to remove. (The small
remaining sign — pedal slightly deeper — is the same bleed-sensitive signature as the 320 Hz notch
note in §3: the plugin's OD is a little weak vs the bleed in the mids, which is GAP #3b, not this
network.)

**Topology independently re-verified at pixel zoom (session 21, both sources).** Primary p.4 and the
backup schematic draw the SAME network, junction dot for junction dot: buffer out = {pin7, C16 left,
R22 left}; C16 → node Nout (dot) which also feeds R24 → SK; R23 hangs from Nout down to Nmid;
Nmid = {R22 right, R23 bottom, C17 top}; C17 → GND. Backup designators U2B/C18 680pF/R25 100k/R24
33k/C19 0.022µF map 1:1 onto primary IC2_B/C16/R22/R23/C17 with identical values. `RecoveryBridgedT`
implements exactly this. **No `schematic-checker` follow-up is needed and no topology question
remains open.** (What the network does is not really a "notch" but a broad mid scoop — 0 dB below
the R22·C17 corner at 72 Hz, floor through the mids, back to 0 dB above the R23·C16 corner at
7.1 kHz — which is why a *local-dip* test (session 19) and a *stage-transfer-vs-output* test
(session 20) both mis-read it. The output test above is the one that answers the question.)

<details><summary>Session 20's re-opening (superseded — kept for the reasoning trail)</summary>

#### ⚠ GAP #1b REVISITED — the bridged-T verdict was reached with the WRONG TEST (session 20)

A1 (session 19) cleared the bridged-T by checking whether bands 508/640/806/1016 Hz show a **local
dip** at 717 Hz in the final output. They don't — but that test is **structurally blind to this
network's actual shape**. The IC2_B bridged-T is not a narrow notch; it is an enormous *broad*
scoop, and neighbouring 1/3-oct bands share it, so "the bands track flat together" is exactly what
a too-deep broad scoop looks like:

| Hz | 40 | 100 | 202 | 400 | 640 | **717** | 1016 | 2560 | 8000 |
|---|---|---|---|---|---|---|---|---|---|
| model (= ideal oracle, exact) | −1.3 | −5.0 | −10.3 | −18.1 | −26.9 | **−28.1** | −22.0 | −10.3 | −2.7 |

The C++ `RecoveryBridgedT` reproduces the unloaded oracle to 0.01 dB (verified via the new OD taps),
so this is the shipped OD path: **−18 dB at 400 Hz** in a bass preamp. The capture disagrees — in
`drive-0700_grunt-boost` (near-linear, GRUNT boost moves the coupling corner out of the way so the
OD path's own shape is exposed) the pedal shows a smooth ~**4 dB** dip at 640–806 Hz against its
403/1613 Hz neighbours, not 28 dB. Same pathology as GAP #2's treble notch (−37 model / −3.4
capture), one stage later. In the GRUNT-**cut** captures it stays invisible because the clean bleed
fills it, which is why every earlier pass missed it.

**Ruled out as the explanation (session 20):** the deferred **R24 → Sallen-Key loading**
carry-forward (circuit.md "real notch DEPTH is loaded ... capture-validate"). The SK input impedance
is 222 kΩ at 717 Hz (hand-derived and numerically confirmed), and loading the oracle with it moves
the notch −28.1 → −29.2 dB — it **deepens** the notch and adds a ~1 dB broadband loss. Loading is
not the missing mechanism; the unloaded approximation is fine. **This carry-forward is closed.**

Also ruled out: a GAP #2-style series damping R. A scan over series damping on C16 and on C17, and
over R22/R23/C16 individually, finds **no efficient damping element** — 100 kΩ in series with C16
buys 4 dB of notch depth; the R22 reductions that do flatten the skirt move the notch to 1.2 kHz and
leave it 25 dB deep. Unlike the treble ladder, this network's null is not shallowed by a lossy cap.

**Therefore the open question is the TOPOLOGY, not a fit constant** — the same "same VALUES ≠ same
TOPOLOGY" trap circuit.md already caught once here (IC2_B was read as a +12 dB active shelf before
it was re-read as unity buffer + bridged-T). A `schematic-checker` pass on the IC2_B recovery
network is now evidence-driven, not speculative: the modelled topology predicts a 28 dB scoop where
the pedal measures ~4 dB.

*(Session 21: the premise of this whole section is the category error above — "the modelled topology
predicts 28 dB" is the STAGE transfer, "the pedal measures ~4 dB" is the OUTPUT. The plugin's own
output also measures ~4 dB. Ruled-out items below — SK loading, series damping — remain valid
negative results.)*
</details>

### ▶ GAP #3 — the OD path is too bass-heavy (A3). DECOMPOSED, not yet fixed (session 20).

**Symptom, stated precisely.** Define `tilt = mean(Δ over 20–50 Hz) − mean(Δ over 202–1613 Hz)`
(Δ = plugin − pedal per band, already gain-matched, so pure shape; no bands excluded). Over 44
valid OD rows the mean tilt is **16.7 dB** — but it is not spread evenly:

| captures | tilt |
|---|---|
| `drive-0700`, GRUNT **cut** | **0.9 – 1.2 dB** (essentially correct) |
| `drive-1430` / `drive-1700`, GRUNT cut | **13.3 – 20.6 dB** |
| any GRUNT **flat** / **boost** | **8.6 – 33.2 dB** |

So the OD path is right at low drive with GRUNT cut, and goes wrong along **two independent axes**.

**3a — drive-dependent (the rail clamp).** A new probe, `analysis/od_level_probe.cpp`, measures the
OD chain's own transfer (skA tap) over an amplitude ladder. The model's internal LF-vs-mid tilt
**grows 4.4 → 19.5 dB** as level rises (GRUNT cut, drive max): single tones, so this is per-frequency
compression, not intermodulation — the mids saturate the clipper and the LF, attenuated by the GRUNT
coupling before it, sails through uncompressed. Cross-checked against the captures: from drive-min to
drive-max the **pedal** gains ~11 dB in the mids and ~4 dB in the low bass (mid-weighted), while the
**plugin** gains ~9.7 dB in the bass and ~0.9 dB in the mids (bass-weighted) — a 15 dB divergence.

The missing mechanism is almost certainly **IC2_A's output rail clamp, which has never been enabled**
(`railEnabled = false`; calibration §6 makes it a GATE item on every op-amp output, and
`DriveStage.h` says IC2_A at ×78 rails *before* the 4049). It sits **upstream** of the GRUNT coupling
and its input is bass-heavy (+10 dB at 40 Hz vs 254 Hz at the DRIVE output), so it limits LF
preferentially — exactly the missing compression. Session 16's `drive_rail_gate.py` "REFUTED" verdict
was about the drive-min/9:30/**noon** harmonic ramp and explicitly recorded that **2:30/max DO
respond**; the high-drive domain was never tested. Measured with `--fit railEnabled=1`:

| capture / sweep | tilt before | after |
|---|---|---|
| `drive-1700` drv−18 / −12 / −6 | 19.4 / 16.9 / 17.6 | **11.4 / 8.8 / 11.9** |
| `drive-1430` drv−12 / −6 | 18.3 / 13.3 | **12.2 / 8.3** |
| `ref-od` drv−6 | 7.3 | **4.1** |
| `drive-0700` (all), and every `sweep_clean` row | — | unchanged (below the rail) |
| `drive-1700_grunt-boost` drv−6 | 21.5 | 23.6 (small regression) |

**Full-matrix trial of `railEnabled=1` (all 63 captures, `--os 4`).** Aggregate band-RMS
|plugin−pedal| (25 Hz–12.9 kHz) improves on both halves: **clean 2.26 → 2.07 dB, OD 6.51 → 6.21 dB**;
OD tilt 9.49 → 8.78 dB over 92 rows. 14 of 240 rows get worse by >0.5 dB — and **12 of those 14 are
`gain-n12` clean captures at the hottest sweep** (`bass-1700` 2.47 → 6.97, `treble-1700` 2.14 → 6.08,
…), i.e. precisely the rows the harness renders 12 dB too hot (§3). So the model rails there at a
level the real pedal never reached, and those regressions are **not** evidence against the clamp.

**⇒ NOT SHIPPED yet, deliberately.** Two things must land first: (1) the `--input-trim` harness fix,
so the trial can be judged on a level-honest matrix; (2) a real rail voltage — ±3.3 V is the
`FitParams` placeholder and the note there already says the TL07x is asymmetric around VD with the
positive side clipping first. Enabling it also switches on the clamp for *every* op-amp stage at
once (`PedalChain::setFitParams`), including the ±28 dB mid stages; per-stage enables may be wanted.

### ✅ 3a — SHIPPED (session 21). Both blockers cleared.

**(1) Harness fix landed (§3), full matrix re-judged.** With the level-honest matrix, `railEnabled=1`
at the (still-placeholder) symmetric ±3.3 V is a clean win across the whole 63-capture set — no
longer contaminated by the 12-dB-hot `gain-n12` false regressions:

| | band-RMS (25 Hz–12.9 kHz) | rows better by >0.5 dB | rows worse by >0.5 dB |
|---|---|---|---|
| OD (120 rows) | 6.336 → 6.091 dB | — | — |
| CLEAN (116 rows) | 2.335 → 2.090 dB | — | — |
| ALL (240 rows) | **4.298 → 4.057 dB** | **31** | **4** |

The 4 remaining regressions are all small (largest +2.21 dB, `drive-1700_grunt-boost` drv−6) and none
are the EQ-boost `gain-n12` rows that falsely flagged the trial before the harness fix — those are
now among the *biggest improvements* (`lomidfreq-250_lomid-1700_gain-n12` drv−6: −5.38 dB).

**(2) Rail voltage — derived physically, not fitted.** A voltage sweep on the high-drive subset
(`drive-1430/1700`, `grunt-*`, `lomid/himid-1700_gain-n12`, `ref-od`, `level-1700`; 80 rows) found the
objective **monotone all the way down** — 3.8 V → 7.71, 3.3 V → 7.64, 2.9 V → 7.53, 2.6 V → 7.42,
2.3 V → 7.30, 2.0 V → 7.22 dB band-RMS, vs 8.25 V at rail-off — with **no interior minimum**. That is
the same "make the clipper see less" degeneracy that killed the session-5/6 clipper fits (dsp.md), so
the voltage was **not** fit to the floor of that curve. Instead: +9 V → D3 (1N5817, ~0.35 V drop) →
rail ≈ 8.65 V; VD = rail/2 ≈ 4.32 V; a TL07x swings to within ~1.5–1.8 V of each rail (datasheet
typical) ⇒ **±2.7–2.9 V around VD**, positive side clipping first per the existing FitParams note.
Landed as **`railNeg = 2.9 V`, `railPos = 2.7 V`** — captures ~0.8 of the available −1.0 dB gain at
the physical point without chasing the unphysical floor. A quick asymmetric-vs-symmetric check at
matched mean (2.9/2.3 vs 2.6/2.6) confirmed the asymmetry direction helps (−0.12 dB further, band-RMS
7.42 → 7.29 on the subset), small but consistent with the physical picture.

**Shipped:** `FitParams.h` — `railEnabled = true`, `railNeg = 2.9`, `railPos = 2.7` (was
`false`/3.3/3.3). Applies to every op-amp stage via the existing `PedalChain::setFitParams` wiring
(no per-stage split — the full-matrix trial above already reflects that). **ctest 16/16.**

**3b — static, GRUNT-dependent.** At *small signal* the model's OD path is already 4.4 dB bass-tilted
with GRUNT cut and **23.3 dB** with GRUNT boost. The correction the captures ask for is a high-pass:
0 dB above ~250 Hz falling at ~13 dB/oct below it, ~31 dB deep by 40 Hz for boost, ~24 dB for flat,
~5 dB for cut — i.e. **its depth scales with the GRUNT cap**. Levers tested:

| candidate | mean tilt (44 rows) | note |
|---|---|---|
| shipped baseline | 16.74 | |
| `clipA0 = 100` (small-signal Zin ÷4) | 16.55 | **null — Zin is not the lever** |
| `clipC11 = 2.35 nF` (÷2) | 16.36* | −1.0 dB only (*320-excluded metric) |
| `clipC12/C13 ÷ 4` (11.75 n / 55 n) | **14.65** | −7.4 dB on `drive-0700_grunt-flat`, `ref-od`/`drive-*` cut untouched, no regressions |
| `railEnabled = 1` | 15.98 | 3a's lever; −5…−8 dB in its own domain |

The GRUNT caps ARE a lever (session 19's "C12/C13 are NOT the lever" note was assessed against a
*different* symptom — the OD bass-peak frequency, before the GAP #2 notch fix landed — and should be
read as scoped to that, not as a general verdict). But ÷4 on two schematic-verified caps is not a
physical answer and recovers only ~7–9 dB of a 25–35 dB gap. **3b is still open**, and the leading
structural suspect is the bridged-T depth above (which the GRUNT-cut coupling corner masks and GRUNT
boost exposes — precisely the observed GRUNT dependence).

#### 3b re-run against the session-22 rails-on baseline (session 22)

The open question was whether part of what `clipC12/C13 ÷ 4` was compensating for was the **missing
rail clamp**, now shipped. **Answer: no.** Re-measured on the rails-on, mid-fixed baseline, ÷4 is
still worth nearly as much as before, so it is an INDEPENDENT lever, not a proxy for the clamp:

| candidate | OD band-RMS (116 OD rows*) | tilt | rows better >0.5 dB | worse | physical? |
|---|---|---|---|---|---|
| **baseline** (C12 47n / C13 220n) | 6.014 | 8.48 | — | — | primary schematic + BOM |
| C12/C13 ÷2 (23.5n / 110n) | 5.725 | 8.18 | 10 | 0 | no |
| **C13 = 22n only** | **5.527** | **7.79** | 12 | 1 | **YES — backup schematic rev** |
| C12/C13 ÷4 (11.75n / 55n) | **5.355** | **7.60** | 18 | 0 | no |

\* Row-count correction (session 23): the band-RMS values in this table are over **all 116 OD rows**
(reproduced exactly by `analysis/matrix_grade.py`); the "92 rows" originally written here was
`od_tilt_metric.py`'s narrower capture subset, which is where the *tilt* column comes from. Two
different row sets, one label — the values are right, the count was not.

Clean rows are bit-identical in every candidate (0.000) — this lever is OD-only, as expected.
Biggest ÷4 wins are exactly the GRUNT-dependent rows: `drive-0700_grunt-boost` sweep_clean
**20.61 → 12.62**, `grunt-flat` sweep_clean **15.79 → 8.83**, `drive-0930_grunt-flat` drv−18
**14.81 → 7.70**.

**⭐ The new finding is the third row.** Changing ONLY `C13` to **22n** — which is not a fudge but the
value the **backup schematic** actually shows — recovers **~74 %** of ÷4's benefit while leaving
`C12` at its verified 47n. circuit.md already flagged exactly this and even named the trigger:
*"GRUNT cap C13: primary = 220n; backup = 22n. Different revision. Using primary (220n); **re-zoom
the primary GRUNT symbol if the modelled bass-into-clip corner looks wrong**."* The corner does look
wrong, in precisely the GRUNT-dependent way that note anticipated.

**▶ NOT SHIPPED — and deliberately NOT blind-fitted, unlike GAP #4.** The two cases are different in
kind and the distinction matters: GAP #4's mid-cap table is `[ENG]`-computed with **no ground truth to
defer to**, so fitting was correct. `C13` is **schematic- AND BOM-verified on the primary**, and there
is a **documented conflicting value on the backup** — so there IS a ground truth to establish, and a
`schematic-checker` pass can adjudicate it (re-zoom the primary GRUNT cap symbol + the BOM line for
C13). Do that BEFORE changing the constant. If the primary's 220n is confirmed, then and only then
does this become a fit-to-capture like the others; if the primary actually reads 22n (or the board
was built to the backup rev), this stops being a fit at all and becomes a **bug fix**.

> ⚠ **The "fit's ideal C13 sits near 55n" claim above is WRONG and was never measured** — 55n was
> simply 220/4 from the ÷4 candidate, not the optimum of a scan. Session 23 ran the actual 1-D scan;
> it is monotone with no interior minimum. Corrected below.

### ✅ 3b — CLOSED (session 23, 2026-07-25). NOT a GRUNT-cap gap; the C13 change was REJECTED.

The `schematic-checker` pass ran and **220n is confirmed on the primary** — but the fix was rejected
anyway, because the measurement that motivated it turned out to be mis-attributed. Nothing shipped;
`clipC12`/`clipC13` stay at 47n/220n. **ctest 16/16.**

**(1) The schematic verdict** (full detail now in `circuit.md` "GRUNT cap C13", which is the durable
record). Primary p.4's symbol reads `220n` unambiguously at 900 DPI (vector, not a scan; three
evenly-kerned digits at the same offset as C11's `4n7`/C12's `47n`, and the same page renders C14's
`220pf` identically two symbols away); primary BOM p.1 reads `C13 | 220n`. Three refinements matter
more than the reading itself:
- **Symbol + BOM are ONE source, not two** — the BOM carries the schematic's own idiosyncratic value
  notation verbatim, has no independently-sourced column, and shows zero symbol↔BOM disagreement
  across ~100 parts. So "schematic + BOM verified" = one data point. (The same PDF's hand-authored
  p.3 *does* dissent on C33, which is what a genuinely separate voice looks like.)
- **The backup's designators are shuffled**: backup C15 `4700pF` = primary C11, backup C14 `0.047uF` =
  primary C12, backup C13 `0.022uF` = primary C13. Topology identical node-for-node; a single
  one-decade delta on one part. That is equally consistent with a deliberate revision and with a
  `0.022uF`→`0.22uF` re-entry slip — **the 10× factor is evidence for neither.**
- 🚩 **Neither schematic describes the unit we captured** (a real Ultra; the primary is a clone of the
  *original* B7K). So the pre-registered two-branch decision tree was incomplete — there is always a
  third branch, "the document is right AND the captured unit differs", the same situation as the
  `[ENG]` mid caps. This is the third time in three sessions.

**(2) Why the fix was rejected anyway — the excess is not in the GRUNT caps.** New tool
`analysis/grunt_span_probe.py` applies GAP #4's matched-pair SPAN method to GRUNT (three captures
differing in nothing but the switch, so the whole rest of the chain cancels exactly), and
`analysis/matrix_grade.py` reproduces the §4 aggregate tables. Four independent strands:

| # | evidence | result |
|---|---|---|
| i | **The excess is fully present at GRUNT *Cut*** — C12 and C13 out of circuit entirely. `ref-od` vs `blend-0700` (full-OD vs full-clean, matched otherwise) | plugin is **+12.8 dB at 40 Hz, +14.8 at 50 Hz** hotter than the pedal; →0 by 202 Hz |
| ii | **The error tracks BLEND, not GRUNT.** Mean Δ over 25–64 Hz along the blend ladder | pure clean **−0.47** → 0.25 **−0.16** → 0.50 **+0.64** → 0.75 **+2.59** → full OD **+9.51 dB**; clean path band-RMS **0.32** |
| iii | **A proper 1-D `clipC13` scan is MONOTONE, no interior minimum** (grunt-boost rows, band-RMS) | 220n 11.25 / 47n 9.76 / 22n 8.18 / 10n 6.72 / 3n 5.55 / **0.5n 5.09** — the best "fit" is to DELETE the cap |
| iv | **22n inverts the switch's measured ordering.** boost-minus-flat span at 100 Hz | pedal **+5.55 / +6.07 / +5.93 dB** (drive min/0930/noon, consistent); plugin at 220n **+3.62 / +2.75 / +0.48** (right sign); at 22n **−3.82 / −2.80** (**inverted**) |

Strand (iii) is the same *"make the clipper see less"* degeneracy that killed the session-5/6 clipper
fits and forced the rail voltages to be derived rather than fitted (`CLAUDE.md`) — the objective is
not identifying a capacitance, it is asking for less bass anywhere it can get it. Strand (iv) is the
GAP #4 trap exactly: an aggregate win bought by collapsing a switch position onto its neighbour, the
same reason GAP #4's joint mid-cap fit was rejected for collapsing LO-MID "250" onto the 500 Hz cap.

**(3) The SHAPE is wrong, so no cap value could have worked.** Pedal vs plugin GRUNT span (flat−cut,
drive-min, per 1/3-oct band, dB):

| band Hz | 25 | 32 | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **pedal** | −1.1 | −2.0 | −3.1 | −2.7 | +0.5 | +3.5 | +5.2 | **+6.0** | **+6.2** | **+6.2** | +5.6 | +3.5 | +3.8 | +3.2 |
| **plugin** | +12.8 | +13.4 | **+13.8** | +13.8 | +13.5 | +13.0 | +12.2 | +11.0 | +9.3 | +7.0 | +4.6 | +2.3 | +1.6 | +1.4 |

The pedal's span is a **bump centred 127–202 Hz** that goes to ~0/slightly negative below 50 Hz and
holds a ~+3 dB plateau to 640 Hz. The plugin's is a **monotone high-pass shelf, maximal at DC**. A
first-order coupling cap can only move a shelf's corner — **it can never turn a shelf into a bump**,
at any value. Note the two AGREE at 202–254 Hz (+6.2/+7.0, +5.6/+4.6): where the OD path dominates
the model's GRUNT is right, and it is only where the LF collapses that they part company. Note also
the flat position's span error (9.49 dB RMS) is nearly as large as boost's (14.23) — **C12 is
mis-tracking too, and C12 has no conflicting documentation at all**, which alone should have ruled
out a C13-specific explanation.

⇒ **3b is GAP #3/A3 seen through the GRUNT switch, not a gap of its own.** Both the ÷4 and the 22n
candidates are degenerate proxies for the real error and neither should be shipped. Fold 3b into A3.

#### ▶ A3 handover — the target is now QUANTIFIED, and one whole family of fixes is already ruled out

Closing 3b handed A3 a precise target and a decisive constraint. **Measure at GRUNT cut / drive noon /
BLEND max, against the `blend-0700` full-clean capture as the reference** (both are matched in
everything but BLEND, so this is a clean differential — and the clean path itself is trustworthy at
0.32 dB band-RMS, so the reference is sound).

**The target.** `ref-od` minus `blend-0700`, per band, pedal vs plugin:

| band Hz | 20 | 25 | 32 | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pedal | −17.8 | −18.2 | −19.1 | **−20.5** | **−21.2** | −19.2 | −15.7 | −12.8 | −10.7 | −9.4 | −8.8 | −9.9 |
| plugin | −12.8 | −11.6 | −9.7 | **−7.7** | **−6.4** | −5.6 | −5.4 | −5.8 | −6.7 | −8.0 | −9.5 | −10.8 |
| **Δ** | +5.0 | +6.6 | +9.4 | **+12.8** | **+14.8** | +13.6 | +10.3 | +7.0 | +4.0 | +1.4 | −0.7 | −1.0 |

So the OD position needs **~13–15 dB less 40–64 Hz**, tapering to 0 by ~200 Hz and slightly NEGATIVE
above it (i.e. do not simply attenuate the OD path broadband — the mids are already right to ~1 dB).
Note the pedal's own curve is a **bump peaking at 202 Hz** with the deep bass 12 dB below it; the
model's is nearly **flat** across 40–254 Hz. Same shape mismatch as the GRUNT span above, which is
expected — they are two views of one error.

**⛔ The constraint that rules out a whole family of fixes: attenuating the OD path CANNOT be
sufficient.** Gate run (`--fit clipC11=0.01e-9`, i.e. mute the OD path's LF entirely at ref-od):
killing it drops the model's 40 Hz by only **9.2 dB** (50 Hz by 10.5), leaving a flat residual floor
at −13.5 dB — that floor is the **BLEND clean bleed** (`LevelBlend` at B = 1.0 still passes clean
through the 100k track; sessions 7/8). Expressed against the full-clean reference that floor is
**−16.9 dB, still 3.6 dB ABOVE the pedal's TOTAL 40 Hz output of −20.5 dB.** So even an infinitely
aggressive OD-path LF cut overshoots: **the residual bleed's LF level (or its phase relative to the
OD path) is necessarily part of A3.** Any candidate that only touches the OD path is
*necessary-not-sufficient* — gate it against this number before building it.

**Two live hypotheses, and how to separate them.** (a) The bleed's LF magnitude is too high — but the
bleed is resistive/frequency-flat in the model, so a pure magnitude error would show at ALL
frequencies, and the mids match to ~1 dB (it would have to be hidden by the OD path dominating
there — check this explicitly rather than assuming). (b) The OD path and the bleed **cancel partially
at LF in the real pedal** and add in the model — session 19's `blend_null_probe.cpp` measured them
**in phase** in the model (+8.9° at 40 Hz), while the pedal's OD path picks up ~+87° of lead from its
~896 Hz GRUNT-cut coupling corner, so the real sum could be substantially below either term.
`blend_null_probe.cpp` is the right tool and (b) is the more interesting hypothesis, because it would
explain the *shape* (a bump, not a shelf) rather than just the level. ⚠ Do NOT re-open the polarity
question as a *sign* bug — session 19 settled that (OD/clean in-phase at LF is not a bug); this is
about frequency-dependent phase near the coupling corner, which is a different claim.

**Tools:** `analysis/grunt_span_probe.py` (matched-pair span, any position pair, any sweep),
`analysis/matrix_grade.py` (OD/CLEAN/ALL band-RMS + row-movement counts), `analysis/od_tilt_metric.py`,
`analysis/blend_null_probe.cpp`, `analysis/od_taps_probe.cpp`.

### ✅ GAP #4 — the switchable MID positions over-deliver RANGE. FOUND session 21, **FIXED session 22**.

**Outcome (session 22, 2026-07-25).** `schematic-checker` returned **TOPOLOGY CONFIRMED FAITHFUL**,
so the pre-registered decision tree's second branch applied and the range limiter was **fitted to the
capture**: `midWiperRLo = 33k`, `midWiperRHi = 22k` (a series R in the wiper leg, `MidBand::setWiperR`)
plus the one cap value the captures actually contradict, `midLoCap250 = 47n → 22n`. ctest 16/16.

| metric (all six switch positions) | shipped | fitted |
|---|---|---|
| boost-to-cut span, band-RMS 160 Hz–4.1 kHz | **9.66 dB** | **4.68 dB** |
| 4-point POT LAW RMS (the knob response a player feels) | **5.31 dB** | **0.87 dB** |

Per position (span peak dB @ Hz; the ±range is half the span):

| position | pedal | shipped | fitted | RMS ship → fit |
|---|---|---|---|---|
| LO-MID 250 (C33 47n→**22n**) | 25.2 @ 320 | 51.8 @ 254 | 27.9 @ **320** | 17.42 → **6.44** |
| LO-MID 500 (10n) | 24.8 @ 508 | 42.5 @ 508 | 26.2 @ 403 | 10.20 → **5.61** |
| LO-MID 1k (2n2) | 21.8 @ 1016 | 24.6 @ 1016 | 18.7 @ 1016 | 1.64 → 2.91 |
| HI-MID 750 (15n) | 24.7 @ 806 | 39.9 @ 806 | 22.4 @ 640 | 10.92 → **5.83** |
| HI-MID 1.5k (3n3) | 18.6 @ 1613 | 29.8 @ 1613 | 18.2 @ 1280 | 5.30 → **3.04** |
| HI-MID 3k (820p) | −19.5 @ 160\* | −20.9 @ 160\* | −16.9 @ 160\* | 1.38 → 2.63 |

\* the 3 kHz row's peak search lands on the 5.12 kHz renormalisation artefact, not the stage's peak —
treat it as "no strong evidence" either way, as session 21 already flagged.

**⚠ ACCEPTED TRADE, not a fit artefact:** ONE resistor must serve all three switch positions of a
band, so the two SMALLEST caps are slightly over-corrected (LO-MID 1k 1.64 → 2.91, HI-MID 3k 1.38 →
2.63). The net is decisive (the two large-cap positions improve by 10–11 dB RMS) and the pot law goes
near-exact, so this was taken deliberately. A per-position limiter would fit better and be physically
meaningless.

**⚠ RESIDUAL — CLOSED by A2c-2 (session 26), and it was worse than recorded here.** Rw pulls each
peak's CENTRE down. This entry says only LO-MID 500 and HI-MID 750 moved and that LO-MID 250's centre
was recovered by the cap — both readings came off the **1/3-octave grid, which locates a peak only to
+-1/6 octave**. Re-measured with sub-band interpolation, **all six positions were 9-20 % low**,
LO-MID 250 included. A2c-2 also found the deeper consequence this gap could not see: Rw buys range by
DAMPING, so it pays for height with **Q**, and the SPAN objective used here is a height metric that is
nearly blind to width. Rw and the whole cap table were re-fitted together against the pedal's full
stage SHAPE — see "A2c-2" below. (The rejection of the session-22 all-six-cap joint fit still stands
on its own terms: it collapsed LO-MID "250" onto ~10n, the 500 Hz position's own cap. A2c-2's table
keeps the positions 2.2x/3.8x and 3.7x/4.0x apart.)

#### How the element was identified (six independent checks — reusable method)

Sessions 19/20 both mis-read a stage by testing the wrong quantity, so each step here is a separate
measurement, and three plausible explanations were **killed** before the fit:

1. **The DSP is not at fault.** The plugin reproduces the modelled network's span to **~0.5 dB** at
   all six positions ⇒ the error is in the NETWORK MODEL, not `MidBand.h`'s solve.
2. **`schematic-checker`: TOPOLOGY CONFIRMED FAITHFUL.** `MidBand.h` matches circuit.md node for
   node; the full **R1–R54 BOM census** leaves no spare resistor (each mid band uses exactly 4 R +
   2 C), so no unmodelled range-limiting part exists on the board.
3. **✗ Rail compression — KILLED.** The rail clamp is **bit-inert** on these captures (0.0000 dB vs
   an explicit `railEnabled=0` render), so the session-21 clamp is not involved.
4. **✗ Knob under-travel — KILLED.** pedal/model ratio **RISES 0.49 → 0.93** toward the small caps.
   Under-travel would give a CONSTANT ratio; a rising one is a *ceiling* the small caps never reach.
5. **The excess tracks the ABSOLUTE switched-cap size** (47n +26.6 dB, 15n +15.2, 10n +17.7, 3n3
   +11.2, 2n2 +2.8, 820p +1.5) — the signature of a series R in the wiper leg: negligible while Xc
   dominates (small caps), dominant once the cap is a short (large caps).
6. **The measured 4-point POT LAW confirms it from the other side.** At 25%/75% travel the model
   already matched the pedal to ~1 dB; the ENTIRE error was in the last of the travel, symmetrically
   at both ends — exactly where the pot's own series resistance stops masking the wiper leg.

Levers scanned and **rejected** (none reproduces the pattern across all six positions): R38/R39 end
resistors (RMS 9.66 → 9.42, wrong direction), R40/R41 flat legs (→ 8.22), the across-lug cap C32/C34
(→ 10.49, worse), a uniform cap-table scale (→ 8.63), and pot end-travel (best 4.03 but it
over-suppresses every small-cap position).

**Two things worth carrying forward.** (a) The **boost-to-cut SPAN is the right metric** for any
symmetric EQ control — a matched-pair differential in which the whole rest of the chain cancels
exactly, immune to the report's gain-match, the clean/OD balance, and the other EQ bands. (b) The
**pot LAW** (a control measured at ≥3 knob points, not just its extremes) is what separated "the
network's range is wrong" from "the ends of the travel are wrong" — the extremes alone are ambiguous.
`analysis/mid_range_probe.py`, `mid_range_fit.py`, `mid_range_final_fit.py` implement all of this.

**⚠ One fact this fit does NOT explain, recorded honestly.** circuit.md's nodal sim was previously
cross-validated against the **manufacturer's own measured table on p.3**, which shows the SAME varying
range our model had (26→18 dB lo-mid, 23→12.6 dB hi-mid). So our capture contradicts p.3's
real-hardware measurements as well as our sim — the fitted 33k/22k has no physical counterpart on this
board and is a behavioural match to *the unit we captured*, nothing more. That is the accepted posture
here (the cap table is `[ENG]`-computed and never schematic-verified, so there is no ground truth to
defer to), but it should not be described as having found the real circuit.

---

#### Original session-21 finding (kept for context)


**A2 as originally framed ("mid-band deviations > 1.5 dB → fix via the Baxandall/mid FitParams") is
answered: there is no broadband mid-band EQ error.** Mining all 236 valid rows, every 1/3-oct band
250 Hz–6 kHz sits at a median Δ of −1.0 to −2.2 dB — but that is uniform across the whole mid band,
and it splits cleanly by path: **CLEAN rows median −0.31 dB, OD rows median −3.55 dB**. Since the
deltas are gain-matched, a uniform mid *deficit* on the OD rows is the mirror image of GAP #3b's bass
*excess*, not an independent problem. Per clean-path control group:

| group | n | median mid Δ | band-RMS |
|---|---|---|---|
| EQ pots (bass/treble/lomid/himid) | 64 | −0.30 dB | 1.70 dB |
| master / level / blend | 12 | −0.04 | 0.93 |
| ref-clean / attack | 8 | −0.04 | **0.31** |
| **mid-frequency switch positions** | 32 | −0.92 | **3.68** ← the one outlier |

**The real finding.** Reading each mid-freq position's own peak, renormalised at 5.1 kHz (immune to
the report's broadband gain-match), the model's boost/cut RANGE tracks the [ENG] cap table's
±14.5…±28 dB while **the real pedal's range is roughly CONSTANT at ~±11–13 dB at every position**:

| position | plugin peak | @Hz | pedal peak | @Hz | excess |
|---|---|---|---|---|---|
| `lomidfreq-250` BOOST | +25.9 | 254 | +11.1 | **320** | **+14.8 dB** |
| `lomidfreq-250` CUT | −26.0 | 254 | −14.1 | **320** | **+11.9 dB** |
| `himidfreq-750` BOOST | +20.3 | 806 | +11.8 | 806 | **+8.5 dB** |
| `himidfreq-750` CUT | −20.3 | 806 | −12.9 | 806 | **+7.4 dB** |
| `lomidfreq-1k` BOOST / CUT | +12.5 / −12.5 | 1016 | +10.6 / −11.3 | 1016 | +1.9 / +1.2 |
| `himidfreq-3k` BOOST / CUT | +5.4 / −5.4 | 3225 | +4.6 / −3.0 | 2560/3225 | +0.8 / +2.4 * |

\* the 3 kHz row understates both sides — the 5.1 kHz renormalisation reference sits too close to a
3.2 kHz peak. Treat it as "no evidence of a problem", not as a measurement.

So the error is confined to the **two large-cap (low-frequency) positions** — C33 = 47n (LO-MID
"250 Hz") and C35 = 15n (HI-MID "750 Hz") — is **symmetric** (boost and cut over-deliver equally, so
it is the stage's range, not an asymmetry), and at LO-MID the **centre is wrong too**: the pedal
peaks at **320 Hz**, not the computed 229. Note 320 Hz is essentially the STOCK board's C33 = 22n
centre (335 Hz).

**This is exactly the test `circuit.md` left open** ("the per-position boost RANGE genuinely varies
±14.5…±28 dB … confirm against captures", plus the parked "constant-range alternative — switching
BOTH caps as a scaled pair — exists if the real Ultra ever contradicts this"). The captures now
contradict it. **But the parked alternative is NOT the fix as stated:** scaling both caps together
was checked against the oracle here and keeps the range at ~24 dB (best variant RMS 6.46 dB vs the
pedal's curve; shipped 47n/22n is 8.78) — it moves the centre, not the range. No single cap pair
reproduces a ~±12 dB, position-independent range.

**⇒ Next step is a topology question, so this one IS a genuine `schematic-checker` candidate** (unlike
GAP #1b): what limits the real mid stage's range to ~±12 dB regardless of the switched cap? Prime
suspects are the R38/R39 (2k2) end resistors and the R40/R41 (220k) flat-unity legs around the pot —
the range in this topology is set by the wiper leg's authority against those, and a larger series
resistance in the wiper/cap leg would cap the range position-independently, which is precisely the
observed signature. Do this BEFORE touching the [ENG] cap values: the LO-MID centre error
(229 model / 320 pedal ≈ the stock 22n value) hints the engineered cap table itself may not match the
real unit, and both questions should be answered from the same evidence.

**⇒ Decision tree for the `schematic-checker` result (user call, 2026-07-25 — captures outrank the
schematic here):** if it finds a genuine topology bug (a misread node, a bridging part modelled as
series/shunt wrong, etc. — the GAP #1b/#2 pattern), fix the topology and re-derive the range from the
corrected network, same as every prior `schematic-checker` catch. **But if it confirms the modelled
topology is faithful to the schematic** — i.e. the ±14.5…±28 dB spread really is what this network's
values imply — **do NOT block on finding a physical explanation for the discrepancy. Fit a
range-limiting element (or retune R38/39, R40/41, or a new wiper-leg series R) directly to the
capture's ~±12 dB target,** exactly the posture already used for `c21R` (GAP #1),
`trebleLadderDampR` (GAP #2), and the rail voltages (GAP #3a) — dsp.md "fit the corner", the capture
is authoritative. This pedal's `[ENG]` mid-cap table was itself only ever a computed *approximation*
of the real Ultra's response (never schematic-verified — see circuit.md's `[ENG-caps]` tag), so there
is no schematic ground truth to defer to here even in principle; a clean fit-to-capture is not a
concession, it's the correct source of truth for this stage.

### ▶ A2c — Clean-baseline accuracy pass. STARTED (session 24, 2026-07-25), user-initiated.

**Why, before A3:** A3's target derivation (above) is itself computed *against* `blend-0700`, a
clean capture, as the reference. If the clean path carries an uncorrected error, it leaks into every
OD/clean differential built on it — A3's target table, GAP #4's span method, GAP #3b's strand (ii).
User's framing: nail base-clean first so later distortion-side work isn't chasing a target computed
against a wobbly reference. Agreed premise, not yet a fix.

**⚠ Row-counting correction (methodology, applies to all past clean grading in this doc).** Each
capture carries 4 sweep levels, but for a linear (undistorted) chain they are the IDENTICAL shape
offset by exactly the level step — verified: post-normalisation band spread is 0.000 dB across all
4 sweeps on every checked linear capture. So **the clean set is 29 independent captures (30 minus
the silent `master-0700` zero-knob capture), not "124 rows"** — a `matrix_grade.py`-style row count
is ~4× inflated for the clean subset (it's the right unit for OD rows, which really do differ across
drive level). Grade clean captures by capture, not by row, from here on.

**(1) Two bad captures found + fixed.** Diagnostic: does the residual go somewhere the knob under
test can't physically reach, and does the anomaly shape repeat across unrelated captures (the
session-8 "bad take" signature). A blunter sign-flip-count heuristic was tried first and rejected —
it flags any ordinary peaking-filter residual (which legitimately crosses zero twice) as "bad", so it
over-flagged half the mid-band captures.
- **`master-1700_gain-n12_base-clean.wav`** (master=1.0, straight resistive divider, pot fully out of
  circuit per circuit.md — the same physical situation as master=0.25/0.75, which both graded 0.31 dB).
  Pre-fix: 3.41 dB, a 4-lobe wiggle including an isolated **+6.1/+5.4 dB spike at 4–5 kHz** nothing
  else in the set shows. A passive unity divider cannot develop that at one tap point and not the
  other two.
- **`bass-1700_gain-n12_base-clean.wav`** (BASS pot, a ~100 Hz Baxandall shelf). Pre-fix: 3.78 dB,
  with a **−8.1 dB dip centred at 2.5 kHz** and a rise to +3.2 dB at 8–13 kHz — two-plus octaves from
  anything the BASS control touches, and sharing its odd-shaped ripple with `master-1700`'s.
- User re-recorded both. Post-fix: **master-1700 → 0.31 dB** (now bit-similar in shape to its own
  0.25/0.75 siblings), **bass-1700 → 0.70 dB** (single smooth monotone tilt, same shape family as the
  other bass captures). Re-rendered with `--only master-1700,bass-1700` first to confirm before the
  full re-baseline (cache correctly bypassed both times — "0 from cache").
- **Checked and cleared** (real fittable single/double-lobe residuals, NOT bad takes — do not
  recapture these): `himidfreq-750_himid-0700`/`_1700`, `lomidfreq-250_lomid-0700`/`_1700`,
  `himid-0700`, `lomid-0700`, `lomid-1700_gain-n12`, `himid-1700_gain-n12`. Each shows ONE coherent
  lobe centred on the frequency its own control affects (mirrored in sign between a cut- and a
  boost-direction pair, exactly what a fixed-frequency/Q mismatch under a variable-gain peak should
  look like) — this is GAP #4-shaped range/centre error on the mid-freq switch and mid pots, the next
  real fitting target, not noise. `himidfreq-750_himid-0700` (3.53 dB) and `lomidfreq-250_lomid-1700`
  (2.79 dB) are currently the two worst captures in the set.

**(2) Real grading bug fixed: `matrix_grade.py::is_od()`.** `"base-od" in fname or fname ==
"ref-od.wav"` — but `ref-od_gain-n12.wav` contains neither substring, so it was silently graded as
CLEAN (at 6.23 dB, the worst "clean" row pre-fix). Fixed to `fname.startswith("ref-od")`. This
retroactively means every CLEAN/OD split number quoted in sessions 18–23 included one mislabelled OD
capture in the CLEAN bucket — **relative deltas within a single session's before/after comparison are
unaffected** (the bug was present on both sides of every such diff), but the absolute CLEAN number
those sessions quote was slightly inflated and the OD number slightly deflated. Not worth
retroactively editing old entries; flagging here so a future reader doesn't over-trust the exact
historical split.

**(3) Full re-baseline (session 24, `--no-cache`, ~30 min — OfflineRender was freshly rebuilt so the
render-binary-mtime cache key busted anyway):** **OD 5.963 / CLEAN 1.194 / ALL 3.578 dB** band-RMS,
240 rows (down from OD 6.014 / CLEAN 1.495 / ALL 3.680 — the two recaptures plus the `is_od()` fix
together account for the whole move; nothing in `src/` changed). ctest 16/16 confirmed post-rebuild.

**(4) The ±0.5 dB target, evaluated against the actual data — agreed, with a correction.** User
proposed ±0.5 dB (±1.5 min, ±1.0 preferred) across 20 Hz–20 kHz. Measurement floor supports the
ambition: pedal take-to-take repeatability (`ref-clean` vs `ref-clean_gain-n12`, shape-normalised) is
**0.144 dB RMS / 0.173 dB max**, and the bypass round-trip is **0.07 dB** — so ±0.5 dB is ~3× the
noise floor, a real target, not noise-chasing. But two things the raw ±0.5 spec doesn't survive
contact with:
- **The band edges aren't capturable.** The grade already stops at 25 Hz–12.9 kHz (`matrix_grade.py`
  `GRADE_LO/HI`) because 20 Hz and 16 kHz sit in the sweep/cab noise floor — even the near-perfect
  `ref-clean` capture is −1.3 dB at 25 Hz. Spec the target over **30 Hz–10 kHz**, accept looser
  (±1.5) outside it.
- **Knob-position repeatability is not free.** On a ±28 dB mid-band range, a couple of degrees of
  physical pointer error is worth >1 dB — visible in the `himid-0700`/`lomid-0700` interior-position
  residuals. The GAP #4 fix method (a 5-point pot law through 0700/0930/flat/1430/1700, not
  per-position) is the only way to separate "wrong range" from "wrong knob-position error", same
  reasoning as that gap.

**Agreed target (supersedes the raw ±0.5 spec): mean clean band-RMS ≤ 0.7 dB, no capture over
1.5 dB, graded over 30 Hz–10 kHz.** Tiered by capture type: ±0.5 on flat/interior settings (already
met — `ref-clean`, `master-*`, `bass/treble/lomid/himid` at 9:30/2:30 all sit at 0.3–0.9 dB), ±1.0 on
single-knob full extremes, ±1.5 worst-case on the mid-freq switch extremes (the hardest captures,
`himidfreq-750`/`lomidfreq-250`, given GAP #4 already spent one range-fit trade on these bands).

**State at session 24 close vs target:** mean 1.235 dB (target ≤0.7), 20/29 captures ≤1.5 dB (target
29/29). Not met; no fitting work had started.

#### ✅ A2c-1 — TREBLE range. FIXED + shipped (session 25, 2026-07-25).

**Shipped: `trebleWiperR` = R36 3.3k → 4.7k** (`FitParams::trebleWiperR`, new
`Baxandall::setTrebleWiperR`). ctest **16/16**, AU + VST3 build clean.

`treble-1700_gain-n12`'s residual was a single smooth monotone tilt (−3.8 dB at 25 Hz → +0.7 dB at
12.9 kHz), the signature of a Baxandall treble RANGE error rather than a corner/shape error. Fit with
GAP #4's method — the **matched-pair boost-to-cut SPAN** (dsp.md's isolation technique: everything
else in the chain cancels exactly) plus the **5-point pot law** through 0700/0930/flat/1430/1700, so
the fit cannot buy the extremes by wrecking mid-travel. R36 (Wt → IC5_C virtual ground) is the
treble leg's **own** series element, which is why it moves the range without touching BASS.

| metric | shipped (R36 3.3k) | fitted (R36 4.7k) | pedal |
|---|---|---|---|
| boost-to-cut span, band-RMS 25 Hz–12.9 kHz | **2.44 dB** | **0.59 dB** | — |
| 4-point pot-law RMS (5 bands × 4 knob points) | **0.62 dB** | **0.27 dB** | — |
| span end-to-end tilt, 25 Hz → 12.9 kHz | 38.4 dB | **33.8 dB** | **33.6 dB** |

Real `OfflineRender` A/B (not the oracle — the shipped chain, full 63-capture re-baseline):

| capture | before | after |
|---|---|---|
| `treble-1700_gain-n12_base-clean` | **2.106** | **0.651** |
| `treble-0700_base-clean` | **0.948** | **0.418** |
| `treble-0930_base-clean` | 0.440 | 0.482 |
| `treble-1430_gain-n12_base-clean` | 0.342 | 0.383 |

**Surgical, by construction and by measurement.** R36 carries only the treble leg's contribution to
the shared virtual-ground node, so at treble-flat the change is **<0.004 dB at every band** — the
four BASS captures and both `ref-clean` takes move by ≤0.024 dB, and the whole OD half of the matrix
is unchanged (**OD 5.963 → 5.965**, i.e. nil). Full matrix: **CLEAN 1.194 → 1.152**, **ALL 3.578 →
3.558** (240 rows); **6 rows better by >0.5 dB, 0 worse.** Per capture (the correct unit for the
clean subset — see the row-counting note above): **mean 1.235 → 1.168 dB, 20/29 → 21/29 ≤1.5 dB.**

**Why this element, and why it is a real minimum rather than a degeneracy.** A 1-D scan of R36
against the measured span has a clean **interior minimum** — 3.3k **2.44** / 4.4k **0.89** / 4.7k
**0.59** / 5.0k **0.54** / 6.0k **1.60** / 10k **5.86** dB — i.e. the objective pushes back from
*both* sides. That is the specific check that failed for the GAP #3b C13 candidate and the
session-5/6 clipper fits (both were monotone "make it see less" degeneracies with the best score at
the degenerate end), so it was run first. The raw fit lands at **4.86k**; 4.7k is the E12 round
(4.7k and 5.0k are indistinguishable in practice, 0.645 vs 0.633 combined). The pot law is the
independent second axis — GAP #4's lesson that extremes alone cannot separate "wrong range" from
"wrong end-of-travel".

**⚠ HONEST CAVEATS — read before quoting this as "found the real circuit".**
- **R36 = 3.3k is schematic-verified** (pixel-zoom node redraw 2026-07-19, and the R1–R54 BOM
  reconciliation covers it). So this is a capture-vs-document disagreement, and it lands on exactly
  the **third branch session 23 flagged**: the captured unit is a real Darkglass B7K Ultra, while the
  primary schematic is PCB Guitar Mania's clone of the *original* B7K. "The document is right AND the
  captured unit differs" is now the **fourth** time in five sessions. 4.7k is a behavioural match to
  *the unit we captured*, not a claim about what is on either board.
- **No `schematic-checker` pass was run**, unlike GAP #4 — a deliberate, stated choice, not an
  oversight. GAP #4 needed one because it hypothesised a **new** element and required a BOM census to
  prove no spare resistor existed; R36 already exists in both the model and the schematic at a
  verified value, so the only live question is topology, not the reading (and session 23 established
  that re-confirming a reading does not settle a capture disagreement — C13 confirmed 220n and
  changed nothing). The evidence that the **topology** is right is that a pure value change flattens
  the span residual across the *whole* band (2.44 → 0.59 dB over 25 Hz–12.9 kHz): a wrong topology
  would leave a frequency-dependent shape residual, not a uniform range error. If that residual ever
  becomes the binding constraint, a checker pass on the treble leg (C28/C29 lug wiring, R36's node)
  is the next step.
- The two interior knob points regress by **+0.04 dB** — inside the 0.144 dB take-to-take
  repeatability floor, so this is noise, not a trade.

**Current state vs target:** mean **1.168** dB (target ≤0.7), **21/29** captures ≤1.5 dB (target
29/29). **Still not met** — the residual is now almost entirely the mid-band group.

**▶ ANSWERED BY A2c-2 BELOW (session 26): the residual was neither centre nor range — it is peak
WIDTH, and it is `midWiperR`'s own doing. A2c is now capped; see the end of A2c-2.**

The nine captures still >1.5 dB are **all** LO-MID/HI-MID gain or mid-freq-switch
captures (worst: `himidfreq-750_himid-0700` 3.53, `himidfreq-750_himid-1700` 3.27,
`lomidfreq-250_lomid-1700` 2.79, `lomidfreq-250_lomid-0700` 2.55, `lomid-1700` 2.31, `himid-1700`
2.22, `himid-0700` 2.07, `lomid-0700` 1.87, `lomidfreq-1k_lomid-0700` 1.45). These are **already
touched by GAP #4's `midWiperR` range-limiter trade**, whose two documented residuals (one resistor
serving all three switch positions; Rw pulling peak CENTRES down — LO-MID 500 508→403 Hz, HI-MID 750
806→640 Hz) plausibly *are* this residual. So the first question is not "fit harder" but **"can these
move at all without reopening that trade?"** — check whether the residual is centre error (which
`midWiperR` caused and a cap could fix) or range error (already spent), per position, before
committing fitting budget. Note the mid-cap table is `[ENG]`-computed and never schematic-verified,
so unlike R36 there is no ground truth to defer to there. Tools: `matrix_grade.py`,
`analysis/mid_range_probe.py`.

#### ✅ A2c-2 — mid-band SHAPE. FIXED + shipped (session 26, 2026-07-25). A2c then CAPPED.

**Shipped:** `midWiperRLo` 33k → **22k**, `midWiperRHi` 22k → **18k**, and the whole switched-cap
table — LO-MID **15n / 6.8n / 1.8n** (was 22n/10n/2n2), HI-MID **10n / 2.7n / 0.68n** (was
15n/3n3/820p). Five new `FitParams` fields (`midLoCap500/1k`, `midHiCap750/1500/3k`) plus the
existing `midLoCap250`; `PedalChain::loMidCap()/hiMidCap()` now read all six. ctest **17/17**,
AU + VST3 clean.

**The residual was neither of the two things the handover pre-registered.** Decomposing each failing
capture against the pedal's own stage contribution (`analysis/mid_centre_range_decompose.py`) put
LO-MID 250 at a **3.38 dB** residual while its peak depth and 1/3-oct centre band matched the pedal
*exactly* (−14.0 dB @ 320 Hz both). Neither a pure range correction (residual only → 2.05) nor a pure
centre correction (→ 3.33) explained it. The actual error is **WIDTH**: half-depth bandwidth 4.10
octaves against the pedal's 2.19, and 1.54× too broad averaged over all twelve curves.

**And the width error is GAP #4's own fix.** A series R in the wiper leg buys range by DAMPING the
resonance, so it pays for peak height with Q — the oracle's LO-MID 250 bandwidth goes 3.44 → 5.29
octaves as Rw goes 0 → 33k. GAP #4 fitted Rw against the boost-to-cut SPAN, which is a HEIGHT metric
and nearly blind to width, so nothing in that fit pushed back. Range and width are coupled through
one element; you cannot have both.

**⚠ METHOD CORRECTION worth carrying forward: do not read a peak's frequency off the 1/3-octave
grid.** It locates a peak only to ±1/6 octave. On the raw grid three of the six positions looked
*exact*. Refined by a parabolic fit through the peak band and its two neighbours on the log-f axis
(`analysis/mid_shape_verify.py::peak`), **every one of the six was 9–20 % low** — including the two
GAP #4 believed it had landed. This is what turned "centres are fine, only width is wrong" into the
fit below, and it also retires GAP #4's argument that `midLoCap250 = 22n` was corroborated by being
the stock board's schematic-verified C33: that corroboration came from circuit.md's nodal sim run at
**Rw = 0**, and with the fitted wiper R in the model 22n centres at 306 Hz against the measured
349 Hz. A behavioural match does not survive a change to the rest of the network.

Peak frequency, real `OfflineRender` renders, sub-band interpolated:

| position | pedal | A2c-1 (GAP #4) | A2c-2 |
|---|---|---|---|
| LO-MID 250 | 349 Hz | 294 (−16 %) | **372 (+6 %)** |
| LO-MID 500 | 545 Hz | 436 (−20 %) | **548 (+0.5 %)** |
| LO-MID 1k | 1090 Hz | 929 (−15 %) | **1061 (−3 %)** |
| HI-MID 750 | 784 Hz | 665 (−15 %) | **825 (+5 %)** |
| HI-MID 1.5k | 1613 Hz | 1409 (−13 %) | **1586 (−2 %)** |
| HI-MID 3k | 3026 Hz | 2611 (−14 %) | **3178 (+5 %)** |

| metric (12 curves = 6 positions × both knob extremes) | A2c-1 | A2c-2 |
|---|---|---|
| peak-frequency error, mean / worst | 13.0 % / 20.1 % | **3.1 % / 8.7 %** |
| bandwidth ratio plugin/pedal, mean / worst | 1.54× / 1.88× | **1.31× / 1.56×** |
| stage-shape curve RMS, mean | 2.390 dB | **1.819 dB** |

Full matrix (63 captures, 240 rows): **CLEAN 1.152 → 1.023**, **ALL 3.558 → 3.494**, **OD 5.965
unchanged and bit-identical** (the mid stages sit post-BLEND and are flat in every OD capture — the
change is surgical by construction). **5 rows better by >0.5 dB, 0 worse.** Per capture, the correct
unit for the clean subset: **mean 1.168 → 1.045 dB, 21/29 → 22/29 ≤1.5 dB, worst 3.53 → 3.30.** Three
captures move the wrong way by +0.02…+0.12 dB — all inside the 0.144 dB take-to-take repeatability
floor, i.e. noise, not a trade.

**Non-degenerate.** All eight shipped values (6 caps + 2 Rw) sit at an **interior minimum** of the
shape objective with their E12 neighbours worse on both sides — e.g. LO-MID 250 `10n 1.24 / 12n 1.05 /
15n 0.97 / 18n 1.05 / 22n 1.24`, and Rw `0k 2.00 / 15k 1.07 / 22k 0.97 / 33k 1.09 / 68k 1.83`. That
is the check that failed for the GAP #3b C13 candidate and the session-5/6 clipper fits (monotone
"make it see less"), so it was run before anything was shipped. The three positions of each band stay
clearly differentiated (cap ratios 2.2×/3.8× and 3.7×/4.0×), so this is **not** the session-22 joint
fit that collapsed the "250" position onto the 500 Hz cap and was rejected.

**Structural hypotheses tested and rejected** (`analysis/mid_shape_hypotheses.py`): scaling R40/R41
instead of Rw (needs 19.7 kΩ against a schematic-verified 220 kΩ and 175 nF caps); switching C32 as a
scaled PAIR with C33 for constant Q (RMS 4.10 / 2.37 — worse than shipped, confirming session 21's
rejection now on shape as well as range); adding R40/R41 on top of Rw (runs away to Rw = 4.2 MΩ,
R40/R41 × 165 for a 0.002 dB gain — a textbook degeneracy).

**▶ A2c IS CAPPED HERE — the target is not reachable and further fitting is a dead end.**
Seven captures remain >1.5 dB (`himidfreq-750_himid-1700` 3.30, `himidfreq-750_himid-0700` 3.29,
`lomidfreq-250_lomid-1700` 2.91, `lomidfreq-250_lomid-0700` 2.31, `himid-1700` 2.09, `lomid-1700`
1.92, `himid-0700` 1.74); mean is **1.045 dB** (0.969 over the agreed 30 Hz–10 kHz band) against a
≤0.7 target. The binding constraint is the residual 1.31× bandwidth, and it is **structural under the
shared-parameter constraint**: a per-position UNCONSTRAINED fit reaches **0.17–0.44 dB**, so the
topology itself can reproduce the pedal's curve, but only by letting **C32 — the fixed, schematic-
verified across-lug cap — take a different value at every switch position** (26.8n/31.9n/7.2n on
LO-MID) with R40/R41 at 3.5–9.6× nominal. That is a per-position fudge with no physical counterpart,
which is exactly what GAP #4 rejected on principle. Two honest bounds on how much is even left to
chase: the pedal's own cut-vs-boost captures disagree on peak frequency by **6.1 % on average**
(16 % at HI-MID 3k), so the surviving 3.1 % mean error is at the measurement floor; and knob-position
pointer error alone is worth >1 dB on a ±28 dB mid range (§4 A2c item 4).
**Recommendation: accept the tiered target's ≤1.5 dB band as unmet for the six mid-extreme captures
and record the achievable floor as ~1.0 dB mean / ~3.3 dB worst**, rather than spending further
budget. Reopening this needs NEW evidence about the switch's real topology (e.g. whether the Ultra's
mid-frequency selector is 2-pole and switches the across-lug cap too), not another fit.

### ▶ Remaining candidates (not yet investigated)

- **GAP #3 (A3) is now decomposed above** — 3a (rail clamp) and 3b (static GRUNT-dependent tilt).
  Superseded here: the earlier one-line framing ("sub-bass excess, suspect the clean-bleed level")
  and the blanket "NOT C12/C13" (see the table above — they are a partial lever, just not a
  physical answer at the size required).
- **Per-band mid deviations > 1.5 dB** in the existing report (the low-end fix doesn't touch mids,
  so the current baseline's mid/high data is still valid to mine — no re-render needed).
- **BLEND-sweep balance** — the `kInputRef 0.87 → 3.377` move (session 17) shifted where the OD
  path sits vs the clean tap in the clipping regime; the harmonic-ratio fit objective could not see
  it. Check `blend-0700..1430` for a balance error that appears only at intermediate BLEND. (Not
  yet examined; the session-20 subset used max-OD captures only.)

## 5. Performance / HQ pass (not started)

`PerfBenchmark` / `FeatureProfile` / `OSFidelity` → the `hq` toggle decision (omega4 vs
AccurateOmega is usually the only real lever) + README perf table. Plus the deferred OS-fidelity
work: the session-17 4× narrow-band aliasing residual at the amp-0.5 extreme corner (8× is pristine;
recommend 8× for extreme high-drive) — see the OSValidationTest header.

## 6. Carry-forward from Phase 8

Re-verify the **VU idle-noise gate threshold against the new makeup** (0.9 → 3.684 shifted the idle
floor ~4×; calibration §7 / build-plan Phase-8 item 3). The meter may show idle noise as activity
until the threshold is re-checked.
