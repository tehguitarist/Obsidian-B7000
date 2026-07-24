# Phase 9 — Reference validation (plugin vs real-pedal captures)

> **The GATE-9 report: numbers, not adjectives.** Records HOW the plugin is A/B'd against the
> captured Darkglass B7K Ultra, the gaps found (with dB), the fixes shipped, and what's left.
> Read this + `docs/validation-and-capture.md` (method) + `.claude/rules/dsp.md` (fix rules).
>
> **Status (2026-07-24, session 18):** Phase 7 calibration shipped (session 17); Phase 8 UI done.
> Phase 9 in progress — the dominant "doesn't sound like the pedal" gap (the low end) is FOUND,
> FIXED, and committed. Residual-gap hunt continues.

---

## 0. Backlog — prioritized TODO (START HERE on a fresh session)

Ordered by impact on "sounds like the real pedal" first, then release-readiness. Each links to the
detail section below. Check off + move to the Gap log (§4) as they land.

**A. Close the remaining voicing gaps (Phase 9 core — highest impact on the sound):**
- [x] **A0. Regenerate the full 63-cap baseline report at the shipped c21R=100k** (session 19). Confirmed GAP #1 holds (clean low end ~0 dB). Cache seeded.
- [x] **A1. Bridged-T ~717 Hz notch** — INVESTIGATED, **non-issue** (session 19). No unmatched notch: bands 508/640/806/1016 track flat (~−1.5 dB), no local dip. Do NOT reshape `bt*`. See §4 GAP #1b.
- [x] **A1b/c/d. TREBLE ~322 Hz notch too deep — the real root gap. FIXED + shipped** (session 19, GAP #2 below). Found while chasing A1: the OD low-mids (100–500 Hz) are scooped by the treble-ladder two-path cancellation notch (~28 dB model vs −3.4 dB capture). New `trebleLadderDampR=30k` shallows it. This is the root of the "backwards GRUNT" + the 254 Hz BLEND null.
- [ ] **A2. Mid-band deviations > 1.5 dB.** Mine the existing baseline (mids are unaffected by the low-end/notch fixes). Fix via the Baxandall/mid `FitParams` or taper as decomposition warrants.
- [ ] **A3. OD/clean BLEND balance — now the BIGGEST residual.** The `grunt-boost`/`grunt-flat` captures stay 12–26 dB off after the notch fix: a sub-bass excess (20–40 Hz) where the pedal has a low-mid bump. Session 19 proved the 254 Hz null is NOT a polarity bug (OD/clean in-phase at LF) and C12/C13 don't fix it (level, not corner). Root suspect = the clean-bleed level/shape + grunt coupling in the clipping regime (kInputRef 0.87→3.377 move). **Start here for the next voicing gain.** Probes: `blend_null_probe.cpp`, `od_taps_probe.cpp`.
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

## 3. Tooling caveats (must-know)

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

### ▶ Remaining candidates (not yet investigated)

- **OD/clean BLEND balance (A3) — the biggest residual.** `grunt-boost`/`grunt-flat` captures stay
  12–26 dB off: the plugin over-emphasises 20–40 Hz vs the pedal's low-mid bump. NOT a polarity bug,
  NOT C12/C13. Suspect the clean-bleed level/shape + grunt coupling in the clipping regime.
- **C12/C13 (GRUNT switched caps) — made fittable (session 19) but NOT a fix.** Shrinking them changes
  the boost LEVEL, not the OD bass-peak FREQUENCY (that was the treble notch, GAP #2). Left at
  schematic values (47n/220n). Do not fit them to compensate for the A3 sub-bass.

- **Bridged-T recovery notch** (risk register #1). All four values are `FitParams` fields but were
  never capture-reshaped; ideal −28 dB @ ~717 Hz is suspiciously deep. Check the ~700 Hz region in
  the OD-path captures (it's post-clipper, pre-BLEND → affects driven, not the clean tap).
- **Per-band mid deviations > 1.5 dB** in the existing report (the low-end fix doesn't touch mids,
  so the current baseline's mid/high data is still valid to mine — no re-render needed).
- **OD/clean BLEND balance** — the `kInputRef 0.87 → 3.377` move (session 17) shifted where the OD
  path sits vs the clean tap in the clipping regime; the harmonic-ratio fit objective could not see
  it. Check BLEND-sweep captures (blend-0700..1430) for a balance error that appears only at
  intermediate BLEND.

## 5. Performance / HQ pass (not started)

`PerfBenchmark` / `FeatureProfile` / `OSFidelity` → the `hq` toggle decision (omega4 vs
AccurateOmega is usually the only real lever) + README perf table. Plus the deferred OS-fidelity
work: the session-17 4× narrow-band aliasing residual at the amp-0.5 extreme corner (8× is pristine;
recommend 8× for extreme high-drive) — see the OSValidationTest header.

## 6. Carry-forward from Phase 8

Re-verify the **VU idle-noise gate threshold against the new makeup** (0.9 → 3.684 shifted the idle
floor ~4×; calibration §7 / build-plan Phase-8 item 3). The meter may show idle noise as activity
until the threshold is re-checked.
