# Phase 9 — Reference validation (plugin vs real-pedal captures)

> **The GATE-9 report: numbers, not adjectives.** Records HOW the plugin is A/B'd against the
> captured Darkglass B7K Ultra, the gaps found (with dB), the fixes shipped, and what's left.
> Read this + `docs/validation-and-capture.md` (method) + `.claude/rules/dsp.md` (fix rules).
>
> **Status (2026-07-25, session 21):** Phase 7 calibration shipped (session 17); Phase 8 UI done.
> Phase 9 in progress. GAP #1 (low end), GAP #1b (bridged-T — investigated twice, closed both times,
> non-issue), GAP #2 (treble notch), and GAP #3a (rail clamp) are all FIXED and, except this
> session's rail-clamp change, committed. A harness defect (gain-n12 captures rendered 12 dB hot)
> that had been distorting the GAP #3a rail-clamp trial is also fixed. GAP #3b (static GRUNT-tilt)
> remains open — see §4.

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
- [~] **A3-next (iii). GRUNT caps — RE-RUN DONE (session 22), not shipped.** The rail clamp was NOT
  what ÷4 was compensating for: on the rails-on baseline ÷4 still gives OD band-RMS **6.014 → 5.355**
  (18 rows better >0.5 dB, 0 worse), so it is an independent lever. **⭐ New: `C13 = 22n` alone — the
  value the BACKUP schematic shows — recovers ~74 % of that (→ 5.527) while leaving C12 at its
  verified 47n.** circuit.md predicted this exact trigger ("re-zoom the primary GRUNT symbol if the
  modelled bass-into-clip corner looks wrong"). **▶ NEXT: a `schematic-checker` pass on C13
  (primary p.4 GRUNT cap symbol + the BOM line) BEFORE changing the constant** — unlike GAP #4's
  `[ENG]` caps, C13 is schematic-verified with a documented conflicting value, so there is a ground
  truth to settle; if the primary really is 220n this becomes a fit, if not it is a bug fix. §4 3b.
- [ ] **A4. Re-grade the full matrix after A2–A3; write final GATE-9 numbers into §4.**

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

| candidate | OD band-RMS (92 rows) | tilt | rows better >0.5 dB | worse | physical? |
|---|---|---|---|---|---|
| **baseline** (C12 47n / C13 220n) | 6.014 | 8.48 | — | — | primary schematic + BOM |
| C12/C13 ÷2 (23.5n / 110n) | 5.725 | 8.18 | 10 | 0 | no |
| **C13 = 22n only** | **5.527** | **7.79** | 12 | 1 | **YES — backup schematic rev** |
| C12/C13 ÷4 (11.75n / 55n) | **5.355** | **7.60** | 18 | 0 | no |

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
Note the fit's ideal C13 sits near 55n — between the two documented values — so neither is exact and
some residual will remain either way.

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

**⚠ RESIDUAL, still open:** Rw pulls each peak's CENTRE down, so LO-MID 500 (508 → 403 Hz) and HI-MID
750 (806 → 640 Hz) now sit a band low where they were previously right. Only LO-MID 250's centre was
recovered (via the cap). A joint fit that refits **all six** caps scores better on paper (span RMS
2.84) but **collapses LO-MID "250" onto ~10n — the 500 Hz position's own cap** — destroying the
switch's frequency differentiation, so it was **rejected**. Recovering the other centres needs its own
evidence, not a blind fit.

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
