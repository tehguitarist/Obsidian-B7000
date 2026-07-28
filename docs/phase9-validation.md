# Phase 9 — Reference validation (plugin vs real-pedal captures)

> **The GATE-9 report: numbers, not adjectives.** Records HOW the plugin is A/B'd against the
> captured Darkglass B7K Ultra, the gaps found (with dB), the fixes shipped, and what's left.
> Read this + `docs/validation-and-capture.md` (method) + `.claude/rules/dsp.md` (fix rules).
>
> **Status (2026-07-25, session 25):** Phase 7 calibration shipped (session 17); Phase 8 UI done.
> Phase 9 in progress. FIXED + committed: GAP #1 (low end), GAP #1b (bridged-T — investigated twice,
> closed both times, non-issue), GAP #3a (rail clamp), GAP #4 (mid-band range),
> **A2c-1 (TREBLE range, session 25)**, plus the gain-n12 harness defect. GAP #3b is CLOSED as
> mis-attributed (session 23): it is not a GRUNT-cap gap, and neither the ÷4 nor the `C13 = 22n`
> candidate was shipped — see §4 "3b CLOSED".
> **User-initiated detour (session 24-25): before resuming A3, nail the base-clean path** (no
> nonlinearity, so a clean-path error is a confound sitting under every OD comparison) — see §4
> "A2c". Session 24 fixed two bad captures + a grading bug and agreed the target; session 25 shipped
> the first fit (`trebleWiperR`, R36 3.3k → 4.7k). **Two voicing items remain open: A2c (clean
> tightening — target ≤0.7 dB mean NOT yet met at 1.168, and the entire remaining residual is the
> mid-band group) and A3 (the OD/clean BLEND balance below ~200 Hz, quantified — §4 "A3 handover").**
>
> ⛔ **UPDATE (session 46, 2026-07-27): GAP #2 is REOPENED and is an A3 symptom.** The pedal's
> ~320 Hz cancellation notch (7–24 dB at full resolution) is entirely absent from the model, and the
> reason is A3: the model's OD path sits 11–14 dB under the clean bleed through 250–640 Hz, burying a
> notch it genuinely has. **A3's scope is therefore wider than "below ~200 Hz"** — the same OD/bleed
> imbalance is measurable up to at least 640 Hz. New A3 sub-gate + numbers in §4 "GAP #2 REOPENED".
>
> ⭐⭐ **UPDATE (session 47, 2026-07-27): A3 IS NOT AN LF GAP AT ALL.** Measured whole-band for the
> first time (`analysis/a3_shape_gate.py`), the model's OD path is too weak relative to the clean
> bleed at **every** band — a bathtub from **+10.4 dB at 20 Hz** through a minimum of **+2.6 dB at
> 50 Hz** to **+9.0 dB at 508 Hz**, score 5.808 dB. It is at least three components (a broadband
> floor, a mid/HF rise, and a steep sub-40 Hz rise) and no single first-order corner produces it.
> The mid/HF half is entirely accounted for by the IC2_B bridged-T shunt cap, but the fix is blocked
> from shipping by the 16 `gain-n12` rows. §4 "A3 step 4".
> Current grade (240 rows, re-baselined session 25): **OD 5.965 / CLEAN 1.152 / ALL 3.558 dB**
> band-RMS.
>
> **UPDATE (session 34, 2026-07-26; corrected + shipped session 35): A3's blocker — the DRIVE
> AXIS — is LARGELY fixed.** `trebleC7` (C7 100n → 680 pF) restores IC2_A's LF headroom, so the
> model's |OD| finally grows monotonically with DRIVE at 40–101 Hz instead of turning over at 2:30.
> Grade now **OD 3.931 / CLEAN 0.465 (bit-identical) / ALL 2.198 dB**, and the OD bass-tilt that has
> been A3's signature since session 20 goes **9.10 → 1.20 dB**.
>
> ⚠ **TWO CORRECTIONS TO SESSION 34's OWN ENTRY, both found session 35.**
> **(a) The value was never actually in the source.** `FitParams::trebleC7` still read `100.0e-9`,
> with a comment saying "NOT YET MOVED OFF NOMINAL", while this file and `circuit.md` both stated
> 680 pF shipped. Only the *plumbing* landed. **Shipped for real in session 35**; the default
> `build/a3_dec_drv*.csv` baseline had also been generated at 100 n, so every phase tool reading it
> was rebuilding the OLD, untrustworthy target.
> **(b) "The drive axis is FIXED" overstates the gate.** 680 pF clears G1 (monotone |OD|, FAIL at
> 5/5 bands → PASS) but does **not** clear G2 containment — it flips the 2:30→max step from 7.89 dB
> SHORT to 1.75 dB OVER at 50 Hz (6.82 short → 0.98 over at 64 Hz). Large and in the right
> direction; not "fixed". The value was selected on the step-profile RMS (4.72 → 0.647 dB), which is
> a different metric.
>
> **A3 is NOT closed**, but session 35 designed and gated the residual element — see §4 "A3 step 3b".

---

## 0. Backlog — prioritized TODO (START HERE on a fresh session)

Ordered by impact on "sounds like the real pedal" first, then release-readiness. Each links to the
detail section below. Check off + move to the Gap log (§4) as they land.

**A. Close the remaining voicing gaps (Phase 9 core — highest impact on the sound):**
- [x] **A0. Regenerate the full 63-cap baseline report at the shipped c21R=100k** (session 19). Confirmed GAP #1 holds (clean low end ~0 dB). Cache seeded.
- [~] **A1. Bridged-T ~717 Hz notch** — was CLOSED as a non-issue (session 19, re-opened and
  re-closed session 20/21) on OUTPUT dips over 116 OD rows (median −2.45 vs the pedal's −3.02 dB),
  topology pixel-zoom-verified identical on both schematics.
  ⛔⛔ **REOPENED (session 64) — and the reason is that the closing measurement could not see the
  thing it closed.** It compared **output** dips in a region where the clean bleed sits **11–31 dB
  ABOVE** the OD path, so it was insensitive to the OD path's own shape *by construction* — session
  51 item 8 already flagged that closure as "weaker than recorded". Measured **directly on the OD
  path, bleed-free by topology** (LEVEL max / BLEND max, drive min), each curve referred to its own
  200 Hz value, the drop over **200 → 480 Hz** is **pedal −4.88 dB vs the model −11.05** — a
  **6.2 dB shape error**, present in **all three ATTACK throws** (so it is shared, not ATTACK's) and
  **level-independent to 0.02–0.15 dB** across −36/−30 dBFS (so not an operating point).
  ⭐⭐ **And the element is named arithmetically:** over the same span the **IC2_B bridged-T alone
  drops −10.79 dB** and the two Sallen-Keys **−0.03 dB**, so the bridged-T accounts for the model's
  −11.05 **to 0.26 dB** and nothing else in the chain has authority there. The pedal's scoop is
  **~2.3× shallower** — circuit.md **risk #1** verbatim. ⚠ Note what is and is not claimed: the
  bridged-T is the only element in the *model* with authority here; whether the *pedal's* scoop is
  itself shallower or something else compensates is not settled by this. ▶ This is now the
  best-localised open OD-path shape error. `analysis/attack_shape_screen.py --tilt` is the
  instrument. See §4 "A3 step 21" item 6, and §4 GAP #1b for the superseded closure.
- [~] **A1b/c/d. TREBLE ~322 Hz notch. Shipped session 19 as `trebleLadderDampR=30k` — ⛔ REOPENED
  session 46 (user-reported): the fix moved AWAY from the feature it is named after, and the feature
  is an A3 symptom.** Session 19's premise was the ISOLATED stage transfer (~37 dB deep vs "−3.4 dB
  capture") — but the *assembled* notch was already ≤2.6 dB (session 14) and ~1.6 dB at the OUTPUT,
  so damping took it to ~0.4 dB against a pedal that has **7–24 dB at full resolution** (the −3.4 dB
  figure is a 1/3-oct read of a notch centred 316–334 Hz, understating it by up to 20 dB). The
  320 Hz band is now **the largest single-band mid error in the matrix (+4.09 dB at `ref-od`
  drv_-12)**. ⭐ Root cause is NOT notch depth: at the schematic Rd=0 the model's OD path *does*
  carry a 31 dB notch, but the clean bleed sits 11–31 dB above the OD path through 250–640 Hz and
  buries it. **⛔ DO NOT move `trebleLadderDampR`** — the full matrix refutes Rd=0 (OD 3.186 → 3.412,
  24 rows worse / 1 better); it is one knob trading the notch against the broad low-mid level, i.e. a
  compensating error for A3. **Fix A3 first, then re-fit it.** New A3 sub-gate + full numbers in §4
  "GAP #2 REOPENED".
  ⭐ **UPDATE (session 62): GAP #2 and ATTACK are answered by the SAME proposal** — see §4 "A3 step
  19". `trebleLadderDampR` stops being one constant and becomes the ATTACK switch's notch-leg pole:
  **6.14 kΩ (flat) / 478 Ω (boost) / 6.04 kΩ (cut)**, which reproduces the pedal's notch to 0.1 Hz
  and 0.18 dB at all three throws. So "fix A3 first, then re-fit it" is now "build the two-pole
  ATTACK topology, which re-fits it". Still **not shipped** — the 63-capture matrix is the arbiter.
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
  >0.5 dB / 0 worse, OD bit-identical. All 8 values at interior minima. **A2c's ≤0.7 / ≤1.5 target was
  NOT reachable under a shared-parameter fit** — the remaining width error needs C32 (schematic-
  verified, fixed) to vary per switch position. Floor recorded as ~1.0 dB mean / ~3.3 dB worst.
  **User authorized (2026-07-26) per-knob/per-switch-position fitting to push further** — done in
  A2c-3 below, and the floor above is superseded. §4 A2c-2.
- [x] **A2c-3. The mid selector is a 2-POLE switched cap PAIR — SHIPPED; A2c CLOSED and its TARGET MET
  (session 27).** The authorised per-position fit was run and its answer needed no per-position
  freedom: the free per-position C32 optimum is a **near-constant C32/C33 ratio** in both bands, i.e.
  one selector switching a scaled PAIR. Shipped `midCapRatioLo/Hi = 10.0` (new, + `MidBand::
  setAcrossCap`), caps re-fitted to LO-MID **6n8/3n9/2n2** + HI-MID **2n7/1n5/680p** (across-lug
  68n/39n/22n and 27n/15n/6n8), `midWiperR` 22k/18k → **6k8 both**. **Per clean capture over the
  agreed 30 Hz–10 kHz band: mean 0.955 → 0.485 dB (target ≤0.7 ✓), 23/30 → 30/30 ≤1.5 dB (✓), worst
  3.54 → 1.01.** All seven mid-extreme captures now < 1.0 dB. CLEAN 1.023 → 0.544, ALL 3.494 → 3.254,
  **OD unchanged to 4.5e-11 dB**; 32 rows better >0.5, 0 worse. Bandwidth ratio **1.30× → 0.99×** —
  the width error A2c-2 called structural is gone. Ratio, Rw and every cap at interior minima; a
  fixed ratio makes the stage exactly scale-invariant, hence constant-Q/constant-range at every
  position, matching the pedal. ⭐ Each band's top position lands on its documented pair (LO-MID
  2n2/22n, HI-MID 680p/6n8). ⚠ Also fixed a real defect in `mid_shape_verify.py` (fixed 5.12 kHz
  anchor sat inside the HI-MID skirts and flattered A2c-2's numbers). ctest 17/17. §4 A2c-3.
- [~] **A3. OD/clean BLEND balance — now the BIGGEST residual.** The `grunt-boost`/`grunt-flat` captures stay 12–26 dB off after the notch fix: a sub-bass excess (20–40 Hz) where the pedal has a low-mid bump. Session 19 proved the 254 Hz null is NOT a polarity bug (OD/clean in-phase at LF) and C12/C13 don't fix it (level, not corner). ⚠ **This entry's "root suspect = the clean-bleed LEVEL/shape" is SUPERSEDED — session 29 measured the bleed level as only ~1 dB off and found the real cause is OD-vs-bleed PHASE (an LF cancellation null the model cannot produce).** Do not start from this framing; see the live A3 entry below and §4 "A3 ROOT CAUSE". Probes: `a3_blend_decompose.cpp`, `od_taps_probe.cpp`.
- [ ] **A3-adjacent (NEW, session 30, 2026-07-26). A genuine, level-dependent HF collapse in
  `ref-od_gain-n12` that `ref-od` does NOT have — not yet localised.** Found by direct chart review:
  after correcting for the broadband-gain-match artifact above, a real ~2–4 dB dip persists through
  400–1000 Hz plus a much bigger **~10–12 dB narrowband collapse at 5.1–6.4 kHz**, tapering into a
  −5…−6 dB shelf through 8–16 kHz. Confirmed NOT primarily a measurement/SNR artifact: coherence dips
  to 0.59–0.78 in-band (vs 0.90+ at neighbouring bands) but the plugin's actual band-limited RMS is
  genuinely ~12 dB lower than the pedal's (−50.5 vs −38.4 dBFS, 4.8–7 kHz) — real missing energy, not
  just decorrelation. Only shows up at the reduced (`gainSessionDb=-12`) stimulus level; `ref-od` at
  full level doesn't have it, which rules out a static filter/EQ explanation (those aren't
  level-dependent) and points at gain-staging or a nonlinear-stage operating-point difference instead.
  ~~**Investigate AFTER A3 ships**~~ ~~⛔ **PRIORITY RAISED (session 47): ON A3's CRITICAL PATH.**~~
  ⛔⛔ **PRIORITY LOWERED AGAIN (session 49) — this group is NOT blocking A3, and session 47's reason
  for raising it did not survive measurement.** Session 47's claim was that `btC17` improves every
  other row group monotonically (non-`gain-n12` OD 3.372 → 3.206) while these 16 rows alone turn the
  aggregate around. Re-measured on `matrix_grade`'s own group split (session 47's figures came from an
  ad-hoc split and are not comparable), **non-`gain-n12` OD does NOT improve: 2.909 → 2.932 at the
  f0-pair and 3.190 at 10n alone**, and underneath that flat number is a 76-vs-16-row GRUNT trade, not
  a uniform gain. `btC17` is now **refuted on reachability** — at fixed notch f0 the bridged-T cannot
  lift 250–640 Hz by ≥4 dB for less than 3.66 dB at 1–13 kHz (1469-setting Pareto scan) — so no A3
  decision waits on these rows. Session 48 already localised them as a **capture defect** (their THD
  turnover, which no gain can move, differs from their twins' by up to 15.6 dB), so the fix is a
  re-capture of 4 files, not analysis. §4 "A3 step 5" items (1)/(2)/(5); original evidence in §4 "A3
  chart-review corroboration".
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
  **⭐ RE-OPENED AND DISSOLVED (session 38) — the "shelf vs bump" premise was STALE and the conclusion
  is now stronger, not weaker.** The premise died on its own: at the shipped state the model's OUTPUT
  span **is** a bump (peak +10.3 dB at 90–101 Hz, negative below 50), because `trebleC7` + `clipC15`
  changed the OD/bleed ratio. The **OD path's own span is still a monotone shelf and is essentially
  unchanged** (19.12→5.27 dB pre, 19.17→5.50 post, by exact decomposition) — nothing touched the GRUNT
  network; **the BLEND sum does the shelf→bump conversion for free** once |OD| drops below the bleed at
  LF. So session 23 compared an OD-path shape against an OUTPUT shape — the GAP #1b category error
  (session 21) one gap over. **The cap scan was re-run at the shipped state anyway** (it could not be
  carried forward) and is still monotone with no interior minimum; sharper, the (peak-frequency,
  peak-height) locus C12 traces — 47n 90 Hz/+10.3 → 12n 126/+4.3 → 1n5 147/+0.7 — moves right and
  **DOWN**, while the pedal's point (178 Hz/+6.3) is right and **UP**: **off the curve in both
  coordinates at once, so no cap value can reach it.** ⇒ **3b needs no GRUNT-side fix; session 23's own
  "fold it into A3" verdict stands.** What is new is that the span is a *magnifier* of A3's crossover
  and yields a sub-gate no other A3 gate provides — see §4 "GAP #3b DISSOLVED".
- [x] **A2d. The sub-60 Hz clean deficit — FIXED + shipped (session 28), user-reported.** `c21R`
  100k → **220k** (corner 15.9 → 7.2 Hz). `bypass.wav` round-trips at −0.03 dB across 20–63.5 Hz, so
  the deficit was the plugin, not the rig; it was identical in all 30 clean captures (shared
  post-BLEND path) and C21 is the only audible-band HP there. **Per clean capture, 20 Hz–10 kHz:
  mean 0.589 → 0.415, worst 1.101 → 0.985; 30 Hz–10 kHz 0.465 → 0.416; CLEAN row-counted
  0.544 → 0.465.** Interior minimum verified both sides. **⚠ OD 5.965 → 6.221 / ALL 3.254 → 3.343 —
  EXPECTED and not a new error** (C21 is shared, A3 is an OD LF *excess*; below 50 Hz this unmasks
  A3, above 63 Hz it is a constant −0.33 dB gain-match reframe). Do NOT tune `c21R` on the OD/ALL
  aggregate. §4 A2d.
- [ ] **A2e. >10 kHz divergence — QUANTIFIED, not fixed (session 28).** Bilinear warp RULED OUT by
  measurement (48k-vs-96k droop ±0.13 dB, no trend — closes the Phase-6 carry-forward for the clean
  path at flat EQ). Two parts: flat EQ is −0.29 dB at 10 kHz (near the 0.144 dB floor); mid
  boost/cut extremes reach **−6.03 dB span error at 16 kHz** (HI-MID 3k) because the plugin's mid
  skirts fall faster than the pedal's. Wiper-leg R ruled out against the oracle; **element NOT
  identified**. Recommend it stays behind A3. §4 A2e.
- [ ] **A2f. The ±0.2 dB residual shape — characterised, PARKED (session 28).** One gentle tilt
  (+0.20 dB at 80–500 Hz, −0.25 dB at 2.5–10 kHz), not a peak+dip; ~3× the take-to-take floor. §4 A2f.
- [ ] **▶ RE-AGREE THE GRADING BAND before A4/GATE-9.** A2d's entire deficit lived at 20–31.7 Hz,
  below the agreed 30 Hz edge — which is why A2c could be declared closed on target with it still
  present. For a bass DI (5-string low B = 30.9 Hz) the low edge should arguably be 20 Hz. §4 A2d.
- [~] **A3. OD/clean BLEND balance — THE remaining voicing gap. ROOT CAUSE FOUND (session 29),
  not yet fixed.** It is **not a level error**: below ~80 Hz the pedal's OD path is **anti-phase with
  the clean bleed**, and the model has them in phase everywhere. Proven by sweeping DRIVE (not just
  drive noon): the pedal's 40 Hz output *falls* with drive into a **−31.8 dB null at 2:30**
  (−18.0 → −18.4 → −20.5 → **−31.8** → −14.7 across min→max) and the null then **migrates to ~22 Hz**
  at max drive — a magnitude-matched cancellation. The plugin rises monotonically and nulls nowhere.
  Crossover ~80 Hz; above it both add, so it is a rotation, **not** a sign flip (session 19 stands).
  Model needs ≈**90–120° more LF lead** in the OD path (~140–180° @40 Hz decaying to ~0 by 200 Hz).
  **⛔ Every OD-attenuation candidate is now DEAD, not just insufficient** — attenuation cannot make a
  null. **⚠ Two handover corrections: the bleed LEVEL is ~1 dB off, not 3.6** (that gate read a phase
  effect as a level error, measuring against the already-cancelled drive-noon total; at drive-min the
  pedal is flat at −17.4…−18.3 vs the model's −16.93, the resistive-bleed signature), **and A3's
  target is unchanged by A2d's `c21R` move** (shared post-BLEND, cancels in the difference —
  reproduced to 0.2–0.3 dB).
  **⭐ STEP 1 DONE (session 31) — the phase is LOCALISED, and the answer is that NO EXISTING STAGE
  CAN SUPPLY IT.** Per-stage budget at 40 Hz: jfet **+76.9** / treble **−76.4** / drive −0.2 /
  clipper **+87.4** / recovery **−28.7** / SKs −1.5 = **+57.6** (the probe reproduces
  `a3_blend_decompose`'s row exactly). Both leads are first-order highpasses already within 3–13° of
  their 90° ceiling. The requirement is now a **bound, not an estimate**: the null DEPTH alone forces
  **θ(40 Hz) ≥ 168°** at every plausible bleed level (deficit ≥111°), and θ ≥ 97–130° at 80–127 Hz
  (deficit ≥76–112°).
  **⛔ With every lag lever at a physically absurd extreme at once** (`jfetRo` 20k, `jfetRq2` 100k,
  C5 ladder deleted) the model reaches only **94° at 40 Hz** — still ≥74° short — and the bridged-T's
  −28.7° is not available anyway (GAP #1b closed it on 116 rows). ⇒ **look for LF structure the OD
  path does not have, not for a mis-parameterised stage.** Also settled this session: the OD phase is
  **drive-independent (<0.1°)**, so this is a LINEAR problem that can be gated at drive-min;
  "decaying to ~0 by 200 Hz" is **wrong** (≈85–88° at 202–254 Hz); the model's OD-vs-drive magnitude
  is **non-monotone** where the pedal's cannot be (needs its own gate); and the bleed level is
  **unresolved at ±2 dB**, with its sign now disputed rather than settled.
  **▶ NEXT = step 2: gate candidates on the NULL** (near 40 Hz at drive 2:30, migrating to ~22–25 Hz
  by max) **and on NOT over-rotating past 90° at 202–254 Hz**, never on band-RMS.
  New tools: `a3_blend_decompose.cpp`, `a3_solve.py`, `od_phase_probe.cpp`, `a3_phase_solve.py`.
  §4 "A3 ROOT CAUSE" + §4 "A3 step 1".
- [~] **A3 step 2 — first candidate KIND question asked and it came back NEGATIVE (session 32).**
  "Is the missing transfer non-minimum-phase (a two-path / RHP-zero mechanism) rather than an
  ordinary passive network?" **Tested and NOT established — do not act on it.** A Bode gain-phase
  ceiling over the measured `s(f)` appears to prove it (36–84° short at 20–80 Hz, surviving a repair
  of the weak points), but the ceiling at 40 Hz is set mostly by the **sub-20 Hz magnitude slope that
  no capture measures**, and the flat extrapolation used costs **36–91° at 20–40 Hz** on closed-form
  test networks — the whole shortfall. Declare a 12 dB/oct tail and 40 Hz goes **−37° → +1°**;
  independently, explicit coincident-HP candidates at fc 70–85 Hz **clear** the same bound (+8.5 /
  +17.6°), which a real ceiling forbids. ⇒ minimum-phase stays live; the binding constraint remains
  **SHAPE** (the requirement is a hump; one corner cannot place it), so step 1's pole+zero
  recommendation is unchanged. New tool `a3_extra_tf_probe.py` (self-test + explicit tail sweep).
  §4 "A3 step 2". ⚠ **The "hump" half of this is RETIRED by session 33 — see next entry.**
- [~] **A3 step 2 (session 33) — the TARGET had a sign error, and the real blocker is the DRIVE
  AXIS. No candidate proposed, deliberately.** (a) ⭐ Sessions 31/32 read the requirement off
  `abs(theta_mdl)`, but the model's OD-vs-bleed phase is **signed and crosses zero near 90 Hz**, so
  the extra phase an added element must supply was understated by **2|θ_mdl|** — 15° at 101 Hz to
  **76° at 202–254**. Corrected, the requirement is a broad **plateau** (+44° at 20 Hz, +107 at 32,
  +115…+137 from 64 to 254), not a hump falling to ~50° — which **retires the pole+zero/lead-network
  recommendation** (a lead network's phase returns to zero). Both sessions' negative results stand.
  (b) Band set extended to **806 Hz**, so the tail that decides realisability is now measured, not
  extrapolated (session 32's lesson applied at the other end). (c) ⚠ The target is a **function of
  the bleed level β** — 82° of swing at 254 Hz across the ±2 dB β is unresolved by — so "gate the
  phase, fit the bleed after" (standing since session 29) **has no fixed point**. (d) Causality
  (minimum-phase couples magnitude to phase) is the missing equation and is tail-free, but it wants
  β ≤ −18.5 while the drive-sweep least-squares wants −15.5; neither is decisive, and the bleed
  **stays open** with its sign leaning back to session 29's. (e) ⛔ **No candidate is proposed
  because the target is unreliable exactly where A3 lives**: the drive-sweep residual is **2–5 dB at
  40–101 Hz at every β**, and the best min-phase element still misses bands by 30–50°.
  (f) ⭐ **So session 31 item 6 is the blocker, not a side issue, and it is now localised: IC2_A's
  RAIL CLAMP.** With rails off the DriveStage increment over drive 2:30→max is a frequency-uniform
  **+7.78 dB**; as shipped it is **+0.40 dB at 40 Hz** vs +6.99 at 320 Hz, and the clipper then goes
  backwards on top. The pedal needs **+6.2 dB** on that step at 40 Hz where the model gives **−2.5**.
  Do NOT lower the rail voltages (derived, not fitted, session 21) — the signal reaching them is
  likely too bass-heavy. ⭐ **Which unifies A3**: an LF excess *upstream of IC2_A* would cause the
  rail saturation AND be the missing lead, so a 2nd-order highpass at ~100–160 Hz placed **before
  the DRIVE stage** is the first candidate with a mechanism behind it.
  **▶ NEXT = A3 step 3, re-ordered: fix the drive axis first, re-solve, then design.**
  New tool `a3_lead_design.py`. §4 "A3 step 2 — the TARGET WAS WRONG".
- [~] **A3 step 3c (session 37) — the LEVEL AXIS is gated for the first time. The queued −12/−6
  "clipper-side over-compression" item is MEASURED and it is SMALL; the big level-axis error is
  `clipC15`, shipped last session at a value three A3 gates reject.** New tool
  `analysis/a3_level_axis.py` (+ `a3_level_axis_scan.sh`): the level step of the pedal's total relative
  to its own full-clean capture is **β-free by construction** (β is a resistive, level-independent
  divider ratio that cancels in the step), so it needs no bleed estimate. Guard verified: the reference
  capture is linear across levels (+6.000 dB step, 0.013–0.028 dB shape spread). Self-test PASS after it
  caught two errors in my own solve (an averaged θ worth 9.4 dB near a null; `np.sign(0) == 0` defeating
  the root bracket).
  **(a) The defect is NOT frequency-flat.** dT residual: CONTROL (drive min+9:30, ≤254 Hz) **0.13 /
  0.51 dB** — the instrument is clean; noon **0.53 / 0.58**; hot drives 101–254 Hz **0.29 / 1.07**; hot
  drives **≤80 Hz 2.75 / 8.27**. So the genuine clipper-side item is **0.5–1.1 dB and mid-band**, which
  **confirms session 35's oracle floor** (0.42 → 0.91 → 1.14) from an independent direction, while
  session 34's "roughly frequency-flat 1–2 dB" description does not survive.
  **(b) The clipper VTC is a real lever on this axis** (a first — G1/G2 was structurally blind to
  everything post-nonlinearity), wanting ceilings at **0.7–0.9×** with genuine interior minima in
  several subsets — **but two subsets are monotone in opposite directions**, so it trades regions rather
  than fixing one defect. ⛔ Not shipped; it needs a joint re-fit with `kInputRef` (its approximate
  session-16/17 degenerate partner), not a one-parameter scan.
  **(c) ⭐⭐ `a3_lead_fit.py`'s "none (H = 1)" row was never H = 1** — it fitted a free broadband gain
  (**k = 1.898, +5.6 dB** at the shipped state), so four sessions' "no element baseline" was the model
  plus a level correction, and the mislabel hid the finding. Fixed (`fix_k`), with a separate free-gain
  row. Corrected true no-element rms vs the raw drive captures: **5.2 nF → 0.904 dB with k = 0.995**
  (wants no level correction, β −17.38) versus **1.5 nF → 3.339 dB wanting +5.6 dB**, i.e. **the shipped
  value is worse than deleting the element**. Null band over 3 levels × 5 drives: **5.2 nF 12/15,
  3.0 nF 12/15, 1.5 nF 0/15, off 0/15.**
  **(d) ⚠⚠ Session 36 selected 1.5 nF on a contaminated metric, twice over.** The HF band's apparent
  preference (2.794 → 3.823 dB) is **entirely the per-row gain-match reframe** — re-anchored to those
  bands it is **flat at 2.579–2.597** — and HF is 15 of the 26 graded bands. What is left is **entirely
  the GRUNT flat/boost rows**: at GRUNT **cut** (68 rows) LF band-RMS bottoms at **4–5.2 nF** and
  **1.5 nF is the worst value tested**; only GRUNT flat/boost prefer it, and that is **GAP #3b**
  (session 23: the pedal's GRUNT span is a *bump*, the model's a *shelf*, and "a first-order coupling
  cap can never turn a shelf into a bump"). ⇒ 1.5 nF is a **compensating error** for an unfixed defect,
  chosen by letting the defective row group vote — the same exclusion session 36 correctly applied to
  the 16 `gain-n12` rows and did not apply to these 28.
  **(e) ✅ SHIPPED (user decision 2026-07-27): `clipC15` 1.5 nF → 5.2 nF.** Interior minimum verified
  both sides on the raw-capture fit (4.0 nF 1.115 / 4.7 nF 0.979 / **5.2 nF 0.904** / 6.0 nF 1.022 dB,
  `k = 0.995` at the minimum). ctest 17/17. Full matrix: **GRUNT cut 2.478 → 2.284, cut `gain-n12`
  6.837 → 5.843, flat 2.191 → 4.055, boost 2.850 → 5.449, ALL OD 3.080 → 3.357, CLEAN bit-identical,
  OD tilt −0.72 → −0.11**; level-axis null **0/15 → 12/15** and dT residual **1.20/3.51 → 1.00/2.14**.
  **The +0.28 dB ALL-OD regression is the 28 GRUNT flat/boost rows and is EXPECTED — do not fix it
  with C15.** Baselines (`comprehensive_data.json`, `build/a3_dec_drv*.csv`, `build/a3_lvl*.csv`)
  regenerated at the shipped state.
  **▶ NEXT: ~~(i) GAP #3b properly — the GRUNT bump-vs-shelf~~ — RESOLVED session 38, and it needs NO
  GRUNT-side fix; see the A3-next (iii) entry above and §4 "GAP #3b DISSOLVED". (i) is now the joint
  `clipSat`/`kInputRef` re-fit** (never a one-parameter scan), carrying the new GRUNT-derived crossover
  sub-gate. §4 "A3 step 3c".
- [~] **A3 crossover sub-gate — RE-MEASURED at the session-44 baseline and the GRUNT side is now
  EXHAUSTED (session 45, 2026-07-27).** Analysis only; **no shipped constant moved.** The gate
  survives the new `kInputRef`: **flat −0.78 oct / +4.33 dB, boost −0.97 / +4.61** (was −0.89/+4.00
  and −1.05/+5.16), i.e. session 44 bought ~0.1 oct and evened the heights, and the pedal row still
  reproduces `GATE_TARGETS` exactly so the locator needs no repair. Flat and boost still agree to
  0.19 oct ⇒ ONE coherent error.
  **(a) The mechanism is now explicit:** in GRUNT **cut** the OD never reaches the bleed (≤ −11.2 dB),
  so the span's denominator IS the bleed and **the gate's peak tracks where |OD|/|bleed| is MAXIMAL**.
  Requirement: move that maximum **+0.79 oct / −4.36 dB (flat), +1.00 oct / −4.72 dB (boost)** =
  a trade rate near **−5 dB/oct**.
  **(b) ⛔ All four GRUNT-side elements refuted, with a mechanism.** `clipC12`/`clipC13` move the right
  way but trade **1.8–3.9× too steeply** and run out of travel (C12's asymptote is 160.3 Hz at +0.33 dB
  — even deleting the cap never reaches 178 Hz). `clipC11`/`clipR16` have the **wrong sign** (+4…+5
  dB/oct). ⚠ R16 refuted an analytic prediction of +0.62 oct: **68× buys 0.10 oct**, because lowering
  it raises the closed-loop gain `−R18/R16` and lifts `OD(cut)` into the denominator.
  **(c) Reachability probe only:** `clipC15` trades at −3.2…−6.5 dB/oct (straddling the requirement)
  and at 0.6 nF the flat row would PASS — **but it is a SHARED element, the boost row does not follow
  (2.04 dB short), and the null gate disagrees.** Not a proposal. New tool
  `analysis/crossover_locus.py` (~20 s/point vs ~6 min, self-check validated to 0.01 oct); `clipR16`
  plumbed as a diagnostic FitParam, default = schematic 6k8, bit-identical.
  §4 "A3 crossover sub-gate RE-MEASURED".
- [ ] **⚠ A3-stale-1. `build/a3_dec_drv*.csv` were rendered at the OLD `kInputRef`** (header
  `amp=0.425139` = 3.377) and every A3 tool reads them silently. **Regenerated at the shipped state
  (session 45)** — but the general defect stands: session 44 re-baselined the matrix and not its
  siblings. **Before trusting any A3 number, check the CSV header's `amp` against the shipped
  `kInputRef`.** §4 item (7a).
- [ ] **⚠ A3-open-1. The null gate still wants +3.84 dB of broadband OD gain** (`k = 1.555`), worth
  2.377 → 0.958 dB. It has shrunk from the pre-session-44 family's k = 1.804 but not gone, and it
  **does not reconcile with session 37's recorded k = 0.995** at the same C15 — open discrepancy,
  check before quoting either. §4 item (6).
- [ ] **⛔ B2b (NEW, blocking a green suite). `OSValidationTest` FAILS on `df14ff3` — ctest is 16/17,
  not 17/17.** Verified by stashing session 45's changes: identical failure at the committed tree, so
  it is session-44 fallout. At the fixed probe amp 0.35 the alias floors are **2× −25.6 / 4× −32.1 /
  8× −23.6 dB**. Session 17's trap in reverse — it moved that amp 0.2 → 0.35 *because* `kInputRef`
  3.377 raised clipper onset, and session 44's 2.7× K drop moved the operating point back into the
  anomaly zone. **⛔ Do not just re-tune the amp to green**: establish first whether 8× genuinely is
  worse than 2× there (a real high-drive quality finding, backlog B2) — a gate with a hardcoded
  operating point is not level-invariant. §4 item (7b).
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
- [ ] **A5. The CLEAN (DIST-off) path distorts hard at moderate-to-hot input levels the pedal
  doesn't — CONFIRMED (session 39, 2026-07-27), user-reported, not yet fixed.** The −14 dBFS
  discrete tones (82 Hz–8 kHz) show nothing (both pedal and plugin at their measurement floor), but
  the 1 kHz `lvl_` level ladder embedded in every capture shows the pedal pinned to its floor
  −36…−3 dBFS while the **plugin breaks between −12 and −9 dBFS and reaches 11–23% THD by −3 dBFS**
  — confirmed on `ref-clean.wav` (flat EQ) and five more representative captures incl. the hottest
  EQ-boost extremes. **Root cause localised and A/B-confirmed: the session-21 RailClamp** —
  `--fit railEnabled=0` returns every case to the pedal's own floor. Likely first offender:
  `EqPreGain`'s always-on fixed −2.2× gain, given `kInputRef` (3.377 V/FS, session 17) alone puts
  the −3 dBFS peak within range of the rail window after that multiply. **Verified NOT an
  OS/aliasing artefact** — bit-identical at OS 1×/2×/4×/8×, per §5. Positioned **before B
  (perf/HQ)** per user request. New tool `analysis/clean_thd_check.py`. §4 "A5".
  **⭐⭐ LOCALISED (session 41): it is IC5_B, the fixed −2.2 EqPreGain stage — the highest node in
  the whole clean chain (+6.85 dB vs +6.66 for every other op-amp output) and UPSTREAM of every EQ
  band, so no EQ or MASTER setting changes it.** Onset −8.79 dBFS at the hard limit, ≈ −10.0 dBFS
  at the RailClamp knee, identical in all six EQ cases tested. **And it is not a rail-voltage
  question: `kInputRef = 3.377 V/FS` needs 5.260 V at IC5_B where the pedal's 9 V supply allows
  ±4.325 V — impossible by 1.70 dB, whatever op-amp is fitted.** Ceilings: ≤ 2.777 (supply),
  ≤ 1.734 (TL07x), ≤ 1.509 (TL07x knee — what the pedal's 0.0000 % at −3 dBFS actually requires).
  ⚠ **This breaks the (kInputRef, clipSat) degeneracy from outside and the two answers DISAGREE** —
  scaling kInputRef to ≤1.5 drags the clipper ceiling back into the regime session 17 rejected. ⛔
  Do NOT lower `kInputRef` alone; it needs a joint re-fit with the clipper family, with the clean
  path's supply bound as a hard constraint. New tools `analysis/clean_rail_probe.cpp`,
  `clean_headroom_probe.py`, `clean_headroom_bound.py`. §4 "A5 step 1".
  **⭐⭐ ANSWERED (sessions 42–43) — AND THE PREMISE OF THE DISAGREEMENT WAS FALSE. The two
  constraints do NOT conflict: fencing `kInputRef` to the clean-path bound makes the OD harmonic
  fit BETTER, not worse.** Cost on one scale: shipped **649.6** → unfenced control **97.0** →
  **fenced 45.8** (ψ3 error 29.4° → **0.8°**). The reason is that **the unfenced objective does
  not identify K at all** — the control run parks `kInputRef` on its bound (5.972 of 6.0) *and*
  `clipSatHi` on its bound, giving a `clipSat` sum of **7.32 V = 130 % of the derived 5.636 V
  CD4049 rail, i.e. physically impossible**. So session 17's 3.377 was a property of its box, not
  a measurement, and the clean path is simply the constraint that pins a genuinely unpinned
  parameter. ✅ The 5.636 V rail is **triple-checked** — the backup schematic's U3B–U3F spare
  sections are input-grounded exactly as the primary's.
  **✅✅ CONCLUDED + SHIPPED (session 44).** Both session-43 blockers were artefacts of the search,
  not the physics: with `clipA0`'s floor moved 20 → 8 it settles INTERIOR at 21.2–21.4 (and the
  prior is now *derived* — the same DAFx device model gives **A0 = 22.0**; note the TI datasheet has
  no gain spec at all, so "20–30" was always a community measurement), and the square-law identity
  costs **nothing** (43.6 constrained vs 39.8 free) and is genuinely **corroborated** — freed again
  from the constrained basin it returns **1.009**, with perturbed seeds scoring far worse. SHIPPED
  `kInputRef` **3.377 → 1.2596** plus the whole clipper/JFET family: cost **649.6 → 34.1**, every
  step-4 check green, **nothing resting on a bound**. ⭐ **A5's defining symptom is GONE** — the
  clean-path ladder now reads 0.000 % at `lvl_-12/-9/-6/-3` on every capture (was 0.57/10.5/20.3 %),
  14 flagged harmonics → 0. ctest 17/17, 63-capture matrix re-baselined. ⚠ One residual: `clipSat`
  sum at 18 % of the rail (SOFT — the rail bounds from above only; forcing it back is jointly
  infeasible at 5.9× cost). §4 "A5 step 2 CONCLUDED".
- [x] **A5b. ⭐⭐ THE OUTPUT LEVEL CALIBRATION HAD GONE STALE — the plugin was 3 dB TOO LOUD.
  FIXED + shipped (session 41).** `kOutputMakeup` **3.684 → 2.599** (−3.03 dB) and
  `masterTaperExp` **2.25 → 1.998**. Invisible to every Phase-9 number by construction (§1: every
  grade is gain-matched, so the matrix measures SHAPE only). Four causes, all staleness: a 12 dB
  double-count `master_taper_makeup.py` inherited from session 21's `--input-trim` harness fix
  (re-run as-was it returns makeup 10.43); the reference capture `master-1700_gain-n12_base-clean`
  being a session-24 re-record (−16.62 → −18.20 dBFS, worth 1.58 dB); four clean-path fixes shipped
  since (s25–s28, worth 1.44 dB); and `ref-clean.wav` — which IS the master = 0.50 member of the
  same series — never being in the taper fit's capture list. Absolute level model − pedal is now
  **−0.85 / +2.00 / −0.67 / −0.01 dB** at master 0.25/0.50/0.75/1.00 (was ≈ +2.4/+3.5/+3.0/+3.0).
  ctest 17/17. ⚠ **Backlog C1 (VU idle gate) must be re-checked against 2.599.** §4 "A5 step 1" (5)–(7).

- [x] **A3 step 3d. The −12/−6 dBFS "mid-band clipper item" is CLOSED as NOT MEASURABLE
  (session 40, 2026-07-27).** The joint `clipSat`/`kInputRef` re-fit was run (5×5 grid, 25
  candidates). **82 % of `mf_hot`'s mean-square was the single 254 Hz band, which is not
  clipper-reachable** — its residual is full size at the CONTROL drives (+1.60 dB at drive min;
  own control 1.51 vs hot 1.90) and matching it needs >24 dB of OD cut. Not a cliff (S = 0.27, the
  lowest of the band set) and not a capture artefact (`bypass.wav` and `ref-clean.wav` step +6.00 dB
  at 254 Hz with 0.00 deviation). With it excluded the item is **0.44 dB against a band-matched
  control of 0.29 dB = 0.15 dB, at the 0.144 dB take-to-take floor**, and the grid's best candidate
  sits at a CORNER with its control falling in lockstep. **Nothing shipped; do not re-open on
  `mf_hot`.** New/updated tools: `analysis/a3_clipper_joint_scan.py`, and `grunt_span_probe.py`'s
  `crossover_gate()` (session 38's sub-gate, now runnable and reproducing its record exactly).
  §4 "A3 step 3d".

- [~] **▶ A3 step 14 (session 58) — the CLIPPER IS DE-CONVOLVED from the ATTACK measurement, so the
  network's LINEAR transfer is pinned over 80–254 Hz for the first time; the required SHAPE is
  specified; and 403–640 Hz is shown to be UNDECIDABLE on this axis.** Session 57's next-step (a),
  answered in the two parts that must precede proposing a topology. Tooling + analysis only; nothing
  in `src/` or `tests/` changed, ctest run and unchanged at 16/17 (`OSValidationTest`, identical
  numbers). New `analysis/attack_tf_spec.py`, `analysis/attack_linear_extract.py`.
  **(1) THE SPECIFICATION.** Minimum-phase families of rising order against the −30 dBFS ratio
  (floor √2 × 0.144 = **0.204 dB**): ⭐ **CUT is a frequency-FLAT −3.2 dB across 80–1613 Hz** (order 0,
  rms 0.566 — **no corners at all**); ⛔ **BOOST saturates at 0.31–0.35 dB**, orders 2 and 3 buying
  0.30 and 0.01 dB respectively and only by parking corners **off-band** (21 Hz, 0.5 Hz) or landing a
  zero **on a pole** (228/200 Hz). ⚠ A self-test gate had to be fixed first: at order 3 DE converged
  to **0.360 dB on a target the family generated itself**, deterministically — 60 multi-start
  `least_squares` restarts take every family to 0.00000 dB. Same lesson as step 13's discarded
  random search.
  **(2) ⭐⭐ THE DE-CONVOLUTION, WITH NO NEW CAPTURES.** Under a swept sine the clipper sees one tone
  at a time, so `r_boost(f,L) = h · r_ref(f, L+h)` ⇒ `ratio_dB = h_dB + S_f(L+h) − S_f(L)`, with
  `S_f` the pedal's OWN measured ref transfer vs level. `h` solved per band by bisection; the clipper's
  shape, rails and drive dependence all cancel. ⭐ **And session 52 §3b's `r = √(|g1|²+H)` upper-bound
  bias cancels EXACTLY** — boost@L and ref@(L+h) present the clipper with the identical waveform, so
  this is the first ATTACK instrument not exposed to it. Gates: recovery of a known `h(f)` through a
  known compressor to **1.8e-15 dB**, liveness to the same, and **no extrapolation** (cells needing
  level data we do not have print `--`).
  **(3) THE RESULT.** `h` boost **+7.03@80 / +7.83@101 / +8.24@127 / +8.38@160 / +8.44@202** (resid
  0.29–1.33) and `h` cut **−3.15 / −2.92 / −2.91 / −3.00 / −3.09** (resid **0.111–0.426, within 2× the
  floor**). ⭐ A genuine de-convolution at the mid bands: at 254 Hz the raw drive-noon ratio reads
  **+3.65 dB** where `h` is **+7.77** — the clipper had eaten 4 dB. ⚠ The fixed level subset is chosen
  by feasibility and is **identical at every band**; the first draft let each band pick its own and the
  summary then claimed "3 levels each" over a table showing 2 and 3 — the session-49 item-7 trap in my
  own gate.
  **(4) ⛔ A FIT-FREE BOUND, AND ITS LIMIT.** `h` drops out of a level difference, so
  `|ratio(L1)−ratio(L2)| ≤ 2·TV(S)`: BOOST exceeds it at **403 / 508 / 640 Hz by +3.03 / +4.03 /
  +4.35 dB**. ⚠⚠ **Do NOT read that as a refutation** — those are exactly the three bands where the
  OD fundamental is weakest (the bridged-T scoop, −17…−18.6 dB) while its octave-down neighbours are
  4–6 dB hotter, i.e. where harmonic leakage into the band is worst and §2's cancellation argument
  (which needs `h` flat) fails hardest. ⭐ Conditioning was checked as an alternative and does **not**
  explain it: `min|t|` is flat at 0.152–0.251 and anti-correlates with the residual.
  **(5) ▶ the same 6 drive-min captures, now sharper** — at drive min the compression budget goes to
  ~0 at every band, so the ratio *is* `h(f)` directly and 403–640 becomes decidable.
  `docs/session58-capture-request.md`; all six re-verified to parse AND to emit `--attack 1/2`
  (checked, because a switch that parses but is not passed to the renderer is the session-20
  `--input-trim` defect). §4 "A3 step 14".

- [~] **▶ A3 step 15 (session 59) — the 15 new captures are IN and verified. Session 58's drive-min
  premise EXPIRES on the INSTRUMENT, not the physics; the bonus drive-max ladders settle `h`'s
  placement OUT-OF-SAMPLE; and the instrument that WILL decide 403–640 Hz is validated on a file
  already on disk.** New `analysis/attack_drive_axis.py`; new report
  `analysis/reports/s59_matrix100.json`, a proven **strict superset** of `s54_matrix85.json`
  (20 400 values bit-identical) so no prior number moves.
  **(1)** ⭐ the **B=0 ATTACK control PASSES** (boost worst −0.062 dB, cut +0.051, floor 0.144) —
  the shared normaliser behind every ATTACK ladder since session 55 is now verified, not assumed.
  **(2)** ⛔⛔ the **drive-min ladders cannot be read on the blend axis.** Drive min idles the clipper
  but also drops the OD path to ~−15 dB under the clean bleed, so `t(B)=|β+B·G|` degenerates to
  `β+B·Re(G)` and the taper absorbs the effect (session 47 item 11's small-µ degeneracy). **Proven
  with a known feature**: the post-clipper bridged-T scoop, which cannot depend on the DRIVE knob, is
  **absent (0.6/0.7 dB) vs 5.2/5.3 at noon and 10.9 at max**. ⇒ **403–640 Hz still undecided.**
  ⚠ the drive-min budget is **not ~0 but 1.70–2.75 dB** — the **J201 sits upstream of DRIVE** and
  never idles. ⭐ **The DRIVE axis trades compression against sensitivity in BOTH directions; drive
  noon is the sweet spot.**
  **(3)** ⭐⭐ **drive max settles the placement out-of-sample**: predicting its ratio from session
  58's published `h` and drive max's own level transfer gives **pre-clipper rms 0.08 dB vs
  post-clipper 7.50 dB** (~90×) on data never in that fit. ⚠ but it **corroborates rather than
  re-measures** the VALUE (4 of 5 h-intervals contain s58's number; **202 Hz does not**).
  **(4) ▶ 2 FILES — `docs/session59-capture-request.md`.** At **LEVEL max** the bleed is **exactly
  zero** and LEVEL sits **after every nonlinearity**, so at BLEND max the output IS the OD path and
  `h(f)` is a plain subtraction. Pre-flight on the existing `drive-0700_level-1700_base-od.wav`:
  **bridged-T scoop back at 6.0–6.1 dB**, |G| up ~8 dB, −30/−18 dBFS agreeing to ~0.1 dB.
  §4 "A3 step 15".

- [~] **▶ A3 step 18 (session 61) — the drawn ATTACK topology is REFUTED on the SIGN of the notch
  shift (0 of 782 random draws, not an optimiser result), and the specification splits into TWO jobs
  that need TWO switch poles.** Session 60's next-step (a), first move — the cheap reachability screen
  before any proposal. New `analysis/attack_notch_screen.py`. Nothing in `src/`/`tests/` changed.
  **(1) ⭐ The scored statistic is a SIGN, not a distance:** relative to flat the pedal moves the null
  **DOWN in BOTH throws** (−17.6 / −5.9 Hz) and makes **boost 2.04× deeper**. No component scaling
  changes a sign.
  **(2) ⛔⛔** At the schematic `RdampC5 = 0` the model's notch sits at **320.3 Hz in all three
  positions (spread 0.0 Hz)**, and C8 swept over **four decades** never fixes the sign — cut always
  moves **UP**, boost **DOWN**, because boost puts C8 in a **bridging** path and cut in a **shunt to
  ground**.
  **(3) ⭐⭐ A SIGN CENSUS removes the optimiser from the argument and localises the failure to ONE
  requirement:** 6000 random draws over ±2 decades in all 12 elements, 782 of which move the null
  measurably ⇒ **0 match the pedal.** Per sign: *boost down* 52.3 %, *boost deeper* 48.7 %, **"cut
  moves DOWN" 0.0 %** — structural, not a co-occurrence problem.
  **(4)** The free 12-element DE search agrees and **saturates** (cost 6.85/6.78/6.78 at ±1/±2/±3
  decades — 0.08 across 2 orders of magnitude) and **switches the throws off** (both shifts → 0.00)
  rather than trading. Gates first: liveness **0.000e+00**, search gate **0.002/0.065** = ~100×
  separation. ⚠ That gate needed tightening — its first version accepted **railed** targets sitting on
  the search-window edge and recovered them trivially.
  **(5) ⭐ Clean decomposition:** the search reproduces the **flat** position essentially exactly
  (333.9 vs 333.98 Hz, 16.04 vs 16.01 dB) ⇒ **the notch-forming network is fine; the switch's coupling
  into it is what is wrong.**
  **(6) ⭐⭐ What CAN make it:** `RdampC5` alone **nails the DEPTH triple to ±0.1 dB** (so a 2× depth
  change is just a damping change) but puts every f0 at 319–320 Hz; `RdampC5`+`C5` switched together
  hits all three (f0, depth) pairs with structured values (Rd 6117/437/6117 Ω, C5 22.6/20.4/19.3 nF)
  — ⚠ 2 dof vs 2 targets, so that fit is not evidence. **The deciding test is the broadband gain of
  the same setting: −0.14 dB where +8.64 is required.** ⛔ The notch leg supplies ~0 dB broadband.
  **(7) ⇒ STOP LOOKING FOR ONE ELEMENT.** The notch triple is reachable *inside* the notch leg; the
  broadband ±gain is not reachable there at all ⇒ the measurement points at a **3-way switch with more
  than one POLE**. ⭐ Direct precedent: **A2c-3 resolved the mid-frequency selector exactly this way**
  (2-pole, switching the across-lug cap with the series cap) after single-element fits could match
  range *or* centre but never both. §4 "A3 step 18".

- [~] **A3 step 17 (session 61) — session 60's item (8b) is now REPRODUCIBLE, and it reproduces
  EXACTLY. The ATTACK notch spec is a committed measurement, plus three refinements item 8b did not
  make.** Session 60's next-step (a0). New `analysis/attack_notch_probe.py` (gated, `--selftest`),
  new `analysis/reports/s61_attack_notch.json`. Tooling + analysis only — **nothing in `src/`/`tests/`
  changed**, ctest **RUN** at the pre-existing session-44 **16/17** (`OSValidationTest`, identical
  `amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`).
  **(1) ⭐ THE AD-HOC NUMBERS SURVIVE, to the bin and to 0.03 dB:** cut **316.4 Hz / 14.93 dB**,
  boost **328.1 / 32.70**, flat **334.0 / 16.01** (s60 recorded 316.4/14.9, 328.1/32.7, 334.0/16.0).
  So verdict (2) stands: a **17.6 Hz spread — 3.0× the 5.86 Hz bin — and boost at 2.04× flat's
  depth**, which no pure broadband gain can produce. **ATTACK and GAP #2 remain ONE problem.**
  **(2) ⚠ MY FIRST GATE WAS WRONG AND FAILED FOR THE RIGHT REASON.** It assumed a bin grid is
  accurate on a BROAD notch and biased on a sharp one, and gated the broad case at ±1.5 dB. The broad
  case is the **worst (−4.3 dB)**, because there are **two** bias mechanisms and only one is about
  resolution: **(i) shoulder contamination** — a broad notch's own skirt reaches into the 200–270 Hz
  reference window, so `shoulder − min` understates the depth *definitionally*; **(ii) bin smearing**
  — a 5.9 Hz-bin CSD estimate cannot reach a sharp deep floor (a true 33 dB notch reads ~29). Both
  **understate**, so the gate was rebuilt on what the verdict actually uses: depth **never
  over-states** (worst +0.05 dB) and depth **RANKING** survives a doubling (true 16/33 → read
  14.9/29.8). ⇒ **every depth here is a LOWER bound**, which cannot manufacture the boost/flat gap.
  **(3) ⭐ REFINEMENT — item 8b's "identical to the bin at −36/−30/−18" is true of FREQUENCY ONLY.**
  Boost's **depth moves 5.11 dB** across those same three levels (33.0 → 32.7 → 27.9) while its
  frequency does not move at all; cut moves 0.07, flat 0.82. Mechanism is already known: boost pushes
  ~8 dB more into the J201, which sits upstream of DRIVE and never idles (s59 item 3), so compression
  reaches boost first. ⇒ **quote the quietest row; treat depth as a bound, frequency as a value.**
  **(4) ⭐ REFINEMENT — the nominal 287–351 Hz exclusion window UNDER-COVERS.** Located by
  measurement (contiguous region where `|h − median|` exceeds the 0.204 dB floor, then re-derived
  against a median the window no longer pollutes), it is **269.5–369.1 Hz on boost** and
  **269.5–521.5 Hz on cut**. The medians barely move (0.02 dB), so this is a refinement not a
  reversal — but the read now excludes the measured window by name.
  **(5) ⚠ REFINEMENT — "h is broadband flat" is much STRONGER for boost than for cut, and item 8b did
  not say so.** Over 80 Hz–1.6 kHz ex-window: boost **+8.64 dB, spread 1.90 (22 % of its own size)**;
  cut **−2.39 dB, spread 2.05 (86 %)**, needing a **252 Hz** exclusion window against boost's 100 Hz.
  Same finding as the 421.9 Hz cancellation check: the shared peak **cancels on boost** (range
  0.47 dB over 360–500 Hz) but **not on cut** (1.16 dB, 5.7× the floor) ⇒ **cut carries real
  structure over ~350–520 Hz.** Note this is the same region and direction as step 16 item 11's
  unexplained cut-shape disagreement with session 58 — the two may be one item.
  **(6)** Confirmed in passing: `flat |H|` varies **4.44 dB across the 1/3-oct band at 403 Hz** (0.80
  at 508, 1.11 at 640), so 8b(i)'s "403/508/640 are not sitting on sharp features" is too strong for
  403. What defends the 1/3-oct read is not the absence of a feature but that the feature is
  **shared and cancels** — which (5) shows holds on boost and only partly on cut. §4 "A3 step 17".

- [~] **A3 step 16 (session 60) — `h(f)` is MEASURED whole-band by plain subtraction, 403–640 Hz
  is DECIDED, and the throw is BROADBAND — so sessions 57/58's "+8 dB peaked at ~200 Hz" is a bleed
  artefact and the topology requirement is far simpler than recorded.** The 2 requested captures
  landed plus 2 bonus GRUNT files. Tooling + analysis only; nothing in `src/`/`tests/` changed, ctest
  RUN at the pre-existing 16/17. New `analysis/attack_level_extract.py`, `analysis/extract_m36.py`;
  new `analysis/reports/s60_matrix104.json`, proven a **strict superset** of s59 (24 000 values
  bit-identical).
  **(1)** The zero-bleed premise is **bounded by measurement, not trusted**: deepest |G| is −34.0 dB
  ⇒ worst-case dilution ≤0.87 dB, and bleed can only shrink `h` ⇒ every value is a **lower bound**.
  **(2) ⚠** The plain subtraction is **not** `h` — boost pushes ~8 dB more into the J201 (which never
  idles), so its raw ratio moves **2.41 dB at 640 Hz** across level where cut moves 0.27. Session
  59's pre-flight checked the **flat reference**, which could not have seen this.
  **(3) ⭐⭐** The fix was a level the matrix has **never read**: `sweep_clean_-36` is in every
  capture but `comprehensive_report.py` stops at −30. Extracted pedal-side into a **side file**
  (not a change to the shared oracle). With it, boost's two quietest levels agree to **0.065 dB**
  and `raw − solved` is **0.027 dB** ⇒ **converged; the de-convolution is confirmatory, not
  load-bearing.**
  **(4) ⭐⭐ RESULT — boost is a BROADBAND ~+8.6 dB, flat 80 Hz–1.6 kHz (±1 dB); cut ~−2…−3 dB, also
  broadly flat.** Not a low-mid peak. The old LEVEL-**noon** pair (independent, different day)
  reproduces session 57's +4.50 dB peak at 202 Hz, and predicting it from the bleed-free `h` plus the
  known LEVEL/BLEND coefficients puts the peak at **202 Hz — the same band as the |OD| maximum**
  ⇒ the "resonance" was the bleed diluting a flat gain where |OD| is weakest.
  **(5) ⚠⚠** 320 Hz is **not a transfer value** (1/3-oct sample on the 316–334 Hz notch that
  migrates with level); 254 and 403 bracket it. **(6) ⚠** The MODEL control genuinely **failed**
  (solved `h` spread 5.3/12.7 dB) — recorded, not explained away: GRUNT's `h` is ~+20 dB so the only
  computable bands are the scoop floor where harmonic leakage is worst. The headline does not rest on
  it. **(7) ⚠** Disagrees with session 58 on **cut's shape** (a slope, not flat) and by +1.6 dB at
  80 Hz on boost, common-mode at LF — unexplained. §4 "A3 step 16".

- [~] **A3 step 13 (session 57) — the pedal's ATTACK shape is MEASURED bleed-free, the [ENG] ladder
  topology is REFUTED on a second independent instrument, and step 11 §5's ambiguity is RESOLVED IN
  DIRECTION toward reading (i).** Session 56's next-step (a), answered with captures already on disk.
  Tooling + analysis only; nothing in `src/` or `tests/` changed, ctest run and unchanged at 16/17
  (`OSValidationTest`). New `analysis/attack_topology_probe.py`.
  ⚠ **Two corrections to step 12's handover:** there are **6** `attack-*_blend-*` captures, not 8,
  and they are **not unused** (`a3_condition_axis.py:105-111` since session 54); and the ATTACK peak
  is at **~101–127 Hz**, not ~202 — that came from the bleed-diluted OUTPUT span, and the dilution
  moved it an octave. **(1)** The switch only reroutes C8's plate ⇒ `H(boost)/H(flat)` is a **purely
  linear** ladder property, so the comparison needs no clipper, bleed or dilution model. Pedal
  **+6.82@80 / +7.19@101 / +4.62@202 / −1.26@640** vs ladder **−0.02 / −0.02 / −0.02 / +0.43** — a
  **falling low-mid peak against a rising HF shelf**, rms 4.31 (boost) / 3.14 (cut) dB.
  **(2) ⭐⭐ THE LEVEL AXIS RESOLVES (i) vs (ii), AGAINST (ii):** a clipper mechanism must FADE toward
  the linear regime; the effect **grows** monotonically as level drops (254 Hz: −0.36 → +0.06 →
  +3.65 → **+8.71** from −6 to −30 dBFS), reaching **~9 dB over 80–640 Hz** where the ladder has
  0.03. ⭐ **CUT is level-INVARIANT** (−3.0 dB at 80–202 across 18 dB) — boost-dependent/cut-invariant
  is exactly a LINEAR level change ahead of a compressor, and explains step 12's unexplained
  boost/cut asymmetry. The known upper-bound bias is worse at high level so it biases *against* the
  trend; conditioning *improves* as level falls (0.043 vs 0.165 dB). ⚠ Direction only — the linear
  limit's magnitude is not pinned. **(3)** Reachability, all 11 elements freed, both throws on one
  parameter set: joint shape rms **3.028 dB at ±3, ±6 AND ±9 decades** (identical to 3 d.p. —
  saturated, 21× floor), with the fit setting boost **identically to 0.00 dB** rather than trading.
  ⚠ A random-search first attempt **failed its own gate** (0.727 dB on a reachable target) and was
  discarded; DE passes at 0.0027 dB. ⚠ A **pathology guard** was required — the unguarded ±9-decade
  run reported `D = +88 dB` by driving the FLAT denominator to −320 dB at a 44 dB shape error.
  **(4) ▶ the one capture gap is exactly 6 files**: `drive-0700_attack-{boost,cut}_blend-{0930,1200,
  1430}_base-od` — at drive min the OD path is near-linear, so the ATTACK ratio there must equal the
  ladder's linear ratio exactly, with no describing-function caveat. §4 "A3 step 13".

- [~] **A3 step 12 (session 56) — step 11's ATTACK finding SURVIVES an independent instrument, and
  the modelled ATTACK network is REFUTED as its carrier.** Session 55's next-steps (b) then (a).
  Tooling + analysis only; nothing in `src/` or `tests/` changed, ctest run and unchanged at 16/17
  (`OSValidationTest`). New `analysis/attack_span_probe.py` (matched-pair output span from the
  frozen matrix — no solve, no bleed estimate, no `b0`) and `analysis/attack_c8_screen.py`.
  **(b) THE GATE PASSES.** Model ATTACK span over 80–640 Hz is **≤0.08 dB at every one of 4 drives ×
  4 levels**, below the 0.204 dB span floor, vs the pedal's up to 5.61 dB. ⭐ The **GRUNT control**
  is what makes it airtight: a schematic-verified linear cap bank on the same instrument gives
  **11.63 dB (138× ATTACK)** and tracks the pedal at **71–157 %** where ATTACK tracks at **1–13 %**
  ⇒ the model's null is inertness, not the output-span dilution caveat. ⚠ One refinement: the model
  is **magnitude**-inert (d|OD| ≤ 0.132 dB ≤1700 Hz), NOT phasor-inert — d(arg) runs +1.5° → +21.2°,
  and that part *is* diluted away (the decompose's own `full` column predicts the report's model
  rows, an independent two-renderer cross-check). **(3) ⭐⭐ A DISCRIMINATION step 11 could not make:**
  at the matrix's most linear corner the pedal's span **converges** to ~2.7 dB (2.92/2.68/2.16/1.14
  at −30/−18/−12/−6 dBFS, 8 % between the two lowest) instead of vanishing, and the GRUNT control
  has the identical shape ⇒ **a LINEAR pre-clipper low-mid difference exists** (step 11 §5 reading
  (i)); the high-level collapse is a generic clipper+bleed property the model already reproduces.
  **(a) THE LADDER IS REFUTED, WITHOUT A `src/` CHANGE** — the oracle already parameterises it, so
  reachability was screened before writing the plumbing. **C8 alone SATURATES at 1.20 dB rms = 45 %
  of the target** with a FLAT joint error across 22n–100n (the tool refuses to call that an interior
  minimum). With R7/R8/RdampC5 free the *size* is reachable and 80–254 Hz tracks to 0.4–0.7 dB, but
  best joint err is **0.76 dB = 3.7× the floor**, R7 rests on its bound, and it costs ×0.10/×3.16 on
  two **schematic-verified** resistors. ⭐ And the residual is a **shape**: every setting plateaus
  above 254 Hz while the pedal **peaks at +4.23 @202 and falls to +0.21 @320 / +1.35 @640**; adding
  damping drives RdampC5 to the far edge, so it is NOT GAP #2's notch reappearing. ⇒ the live A3
  question is the ATTACK **topology** ([ENG], not on our schematic), and it needs a measurement of
  the pedal's ATTACK shape — the 8 unused `attack-*_blend-*` captures — not another fit. §4 "A3 step 12".

- [~] **A3 step 11 (session 55) — ATTACK is reachable in the model at last, and the model's ATTACK
  response is measurably NULL where the pedal's is ±3–7 dB across 80–640 Hz.** Session 54's
  next-step (b). Tooling + analysis only; nothing in `src/` or `tests/` changed, ctest confirmed
  unchanged at 16/17 (`OSValidationTest`). `a3_blend_decompose.cpp` gained `attackIdx=` (it
  hardcoded `p.attackIdx = 0`, so the two ATTACK conditions had no model side at all), the CSV
  header now states its own `attack=`, and the four missing condition CSVs were rendered — **all
  seven conditions of `a3_condition_axis.py` now have a model side.** Verified BOTH directions plus
  the two standing traps: default bit-identical to explicit `attackIdx=0`, `=1`/`=2` provably
  differ, default bit-identical to the pre-existing `a3_dec_drv0.5.csv`, and `drv0.0`/`drv1.0`
  re-rendered bit-identical (session 45 item 7a). Steps 2 and 3 reproduce session 54's figures
  exactly. **New step 4 runs step 2's localiser pedal-vs-MODEL**, on ONE common band set (the
  fourth occurrence of the differing-members trap) and **decomposed** into pedal / model / residual
  so "the perturbation is small" and "the model gets it wrong" are separated on the page: **grunt
  flat 6.06/7.98/2.00 dB and 16.2/57.5/42.7° | grunt boost 7.49/8.00/2.00 and 41.7/68.6/42.1 |
  attack boost 4.99/0.05/5.01 and 11.3/8.4/15.7 | attack cut 3.24/0.07/3.18 and 10.7/7.1/6.6.**
  `H_req` is **SWITCH-DEPENDENT** (worst 7.22 dB / 60.5°), the same closure step 3 gets on DRIVE now
  on a second axis. ⭐ **The finding: the model's `d|G|` across ATTACK is ≤0.13 dB at EVERY band
  20 Hz–1.6 kHz** (a 220 pF C8 can only act above ~2 kHz, and it does: −7.8/+10.4 dB at 2.5/4 kHz)
  **while the pedal's is a smooth monotone +6.8→−1.3 dB (boost) / −3.3→−5.1 dB (cut) over
  80–640 Hz** — exactly where C2 lives. ⭐ **That INVERTS session 54 item 4**: normalised for what
  the model already reproduces, ATTACK has the LARGEST magnitude residual and GRUNT the largest
  phase residual, where the un-normalised pedal-side read had ATTACK smallest. Session 53 item 2
  refuted the ladder as a source of *flat phase lead* — untouched; the ladder as a **magnitude**
  carrier has never been tested, and it is still `static constexpr`/unreachable (session 50's own
  next-step (a)). ⚠ **States exactly one thing:** it falsifies "pedal_OD = model_OD × ONE
  switch-independent linear H", and does NOT separate "the model's switch response is wrong" from
  "there is a pre-clipper element" — both readings are pre-/in-clipper, which is where sessions
  53/54 had already narrowed to, and ATTACK is **[ENG]** so there is no verified topology to defer
  to. §4 "A3 step 11".

- [~] **A3 step 9 (session 53) — ⭐⭐ TWO LOAD-BEARING PREMISES EXPIRED. READ THIS BEFORE step 8 or
  step 6, both of which it qualifies.** (a) **Session 50's post-clipper restriction is INVERTED**: its
  0.094 dB residual is **not reproducible** (recomputed 0.471 dB RMS = 5× larger, 3.3× the capture
  floor), the axis was **power-tested** and provably CAN detect drive-dependence (thresholds 0.67–2.6 dB
  at 15/16 bands vs the 4–19 dB pre-clipper elements deliver), and at the real residual the same
  argument implies a **median 3.5 dB of unmodelled drive-dependence** with 6/16 bands inside the
  pre-clipper range ⇒ **pre-clipper is back in play; it is the only region not ruled out.** (b)
  **Session 31's "the OD phase is drive-independent (<0.1°), so A3's phase gap is a LINEAR problem" is
  FALSE at the current state** — spread up to **53.4°** at 640 Hz, ≥17° above 127 Hz, caused by
  `trebleC7` (s34) and `kInputRef` (s44) moving the clipper's operating point ⇒ the OD path is **not an
  LTI transfer** at A3's condition, so `H_req` is a ratio of **describing functions** and carries no
  Bode obligation. **Quote session 52 as "no LINEAR fix exists", never as "no fix exists".** Also: the
  "model carries all-pass lag" escape is **refuted structurally** (all-pass phase is monotone; the
  requirement is flat), though `trebleLadderDampR` is now known to control whether the OD path is
  minimum-phase at all; and `clipA0` has **~1/45th** of the needed phase authority. ⭐ **Every mechanism
  tested produces a phase change that GROWS with frequency while the requirement is FLAT** ⇒ the flat
  −38° may be an instrument artefact, and **Set A of the session-53 captures is the critical path**
  (`docs/session53-capture-request.md`). **✅ CAPTURES ARE NOW COMPLETE (31 files, verified clean, no
  clipping, no truncation — see §4 item 6's completion check) but DELIBERATELY NOT YET ANALYSED**
  (user request, 2026-07-28: document and stop, analysis is next session). **Next session starts
  with: (1) check the Set B control (`drive-1700_blend-0700_base-od`) against `blend-0700_base-od`
  BEFORE reading anything else out of Sets B/C/D; (2) write `read_a3_tones.py` for Set A — the real
  priority.** §4 "A3 step 9".

- [~] **A3 step 8 (session 52) — ⛔⛔ THE POST-CLIPPER LINEAR CORRECTION NETWORK IS REFUTED, from the
  MEASURED phase, for the whole CLASS rather than for particular elements; and the blend axis is
  UNRELIABLE below 40 Hz, which is where C3's size was quoted.** Analysis + tooling only; nothing in
  `src/` or `tests/` changed. Baseline verified first (`a3_shape_gate --selfcheck` PASS 5.808, worst
  dev 0.027 dB). New tool `analysis/a3_correction_fit.py` (self-test recovers a known network through
  the real observation structure to 0.00000 dB / 0.0000°). **(a) ⚠⚠ THE INSTRUMENT'S OWN VALIDATION,
  READ PER BAND:** `a3_blend_axis --validate` is ≤0.32 dB / ≤2.7° from 40 Hz to 1.6 kHz but **+2.77 dB
  and 20.0° wrong at 20 Hz, and θ RAILED at 180° at 32 Hz** — and its published "mean 0.075 dB over
  40–1700 Hz" summary *starts at 40 Hz*, so it excluded its own three worst bands, which are exactly
  the ones carrying session 51's "C3 is the dominant A3 term" claim. **(b) ⭐⭐ THE RESULT:** over the
  validated band the required correction's magnitude fits to **0.103 dB** (min-phase, 13 params) but
  magnitude and phase together do NOT — the Pareto frontier runs **0.23 dB @ 40.3° … 5.66 dB @ 2.6°**,
  with no point at both, against a 0.144 dB capture floor and 2.7° validated phase accuracy. The
  measurement wants **more LEAD than the min-phase realisation of its own magnitude** (~−38° flat over
  five octaves), and min-phase is the maximum-lead realisation ⇒ **no causal linear element of any
  order can supply this target.** Computed on families that include unbounded rising tails, so it is
  not session 32's truncated-tail artefact. **(c) THREE ESCAPES CLOSED:** a delay-compensation
  mismatch (a delay's error grows with f; the shortfall is FLAT — 32.3° rms vs 12.9° for a flat
  offset); a newly-derived **harmonic-power bias** in the axis (`r = sqrt(|g1|²+H)` is an upper bound
  and `cos θ = Q/r` is biased toward 90°, which pushes the *right way*) — but reconciling it needs
  H/P of 0.6–265 and at **8 of 15 bands no inflation of any size works**; and a wrong bleed level `b0`
  (the leading hypothesis, since `b0` shifts `Q` identically at every band exactly as the flat
  shortfall suggests) — **refuted by its own scan**, which saturates with no interior optimum and
  still never reaches realisability, while session 34 item 2 independently excludes β ≤ −18.5 dB.
  **(d) ▶ Where it points:** the falsified premise is that the pedal's OD path is the model's times a
  linear transfer function; since only the phase is unrealisable, the difference is upstream of or
  inside the nonlinearity — which sits against session 50's "post-clipper only", whose evidence was
  the drive-independence of `s` on a solve now known to rail at 5 bands. **Re-examine that argument
  before acting on either.** §4 "A3 step 8".

- [~] **A3 step 7 (session 51) — A3 measured on a SECOND, INDEPENDENT axis (BLEND). The curve is
  MUTUALLY VALIDATED over 101 Hz–1 kHz (two instruments sharing no information agree to ≤1.6 dB and
  ≤5°), but the drive-axis target every candidate has been ranked on since session 47 is ON ITS
  SEARCH BOUNDARY (θ = 0°/180°) at 202, 254, 320, 1613 and 4064 Hz — and 202/254 are inside C2's own
  span, so part of the curve the C2 search aimed at is set by a railed solve.** Analysis + tooling
  only; nothing in `src/` or `tests/` changed. New tool `analysis/a3_blend_axis.py`, whose mixing law
  is linear and parameter-free (a quadratic in B with unit intercept), self-tests to 0.000000 dB and
  reproduces `a3_blend_decompose`'s exact taps to 0.075 dB mean over 40–1700 Hz. **Results:**
  ✅ `LevelBlend`'s mixing law is CORRECT (pedal worst 0.083 dB vs the 0.144 dB floor) so the
  BLEND/LEVEL network is not A3's cause; ⭐ the pedal's BLEND taper is non-linear (effective B =
  0.212/0.482/0.739); ⚠ the axis is algebraically BLIND to β and cannot be used to challenge it;
  ⭐ **C3 is far bigger than the shape gate says** — the pedal's OD path is nearly FLAT 20→101 Hz
  (≈2.4 dB/oct) where the model rolls off ~9.5 dB/oct, level- and β-robustness both checked, so it is
  a real transfer and not a floor; ⭐ the pedal's mid scoop is ~5 dB SHALLOWER and centred LOWER than
  the model's, with GAP #2's 320 Hz notch visible in the OD path for the first time. ▶ Re-target the
  gate at the measured curve and re-derive C1/C2/C3 BEFORE more carrier hunting; then fit a
  post-clipper correction network to the measured complex target (user has authorised breaking the
  schematic). §4 "A3 step 7".

- [~] **A3 step 6 (session 50) — the C2 carrier SEARCH SPACE is closed, and it is EMPTY; plus the
  component budget A3 should have had since session 34.** Analysis + tooling only; nothing in `src/`
  changed. New tools `analysis/a3_carrier_scan.py` (reachability over the whole OD path) and
  `analysis/a3_component_budget.py` (the beta budget). **(a) The budget:** at the identified
  beta = −16.75 dB (interval [−17.25, −16.50] at the 0.144 dB capture floor; model ships −16.93,
  inside it) A3 splits into **C1 a flat +2.68 dB floor, C2 a +3.20 dB low-mid rise over 101–508, and
  C3 a +7.86 dB LF rise at 20 Hz (9.18 dB/oct)**. **beta explains at most 0.26 dB of C1**, so C1 is a
  real broadband OD deficit — corroborated independently by `a3_lead_fit`'s free-gain row wanting
  **+4.03 dB**. Fixing any ONE component perfectly leaves 3.5–4.8 dB of the 5.82 score, so **A3 will
  not close on one element.** **(b) ⭐⭐ Only a POST-clipper linear element can supply `s(f)`**: `s` is
  one scale per band that must fit all five drives, and the delivered lift is drive-INDEPENDENT
  (`drvspr` = 0.00) for every post-clipper element and **4–19 dB** for every pre-clipper one.
  Confirmed quantitatively — the cheap screen predicts the real shape-gate score to 3 d.p. for
  post-clipper candidates (4.68→4.676; `btC17=10n` 3.49→3.490) and is wrong by 2.7 dB for pre-clipper
  ones (`clipC11=10n` screen 3.26, real **5.922 = WORSE**; `jfetGm=0.4e-3` 2.88, real 5.661). **(c) ⛔
  Nothing reachable supplies C2** (+5.91 dB over 101–508 for ≤1 dB above 1 kHz): the post-clipper
  region holds only `OdCoupling` (LF-only, ±3.45 dB), the bridged-T (refuted, session 49, reproduced
  here) and two HF Sallen-Keys — ⇒ **C2's carrier is a MISSING element**, as `OdCoupling` itself was
  until session 36. **(d) ⭐⭐ The shape gate is NOT valid for C3.** Reverting `clipC15` to the
  schematic 2u2 improves the score 5.808 → 4.676 at **+0.00 dB** side effect and collapses the
  free-k demand to +0.39 dB — but the null gate goes **4/5 → 1/5**, and `a3_lead_fit` then
  re-discovers a 1st-order ~30 Hz highpass (**4/5, PASS**), i.e. it puts C15 straight back.
  **`clipC15` stays at 5.2 nF; gate C3 on the NULL, never the shape curve.** **(e) Scope:** the scan
  is GRUNT cut / −18 dBFS, so level-dependent levers read zero — `railPos/Neg` are exactly 0.00 there
  and were liveness-checked live (8.95 dB at −6 dBFS/drive max). §4 "A3 step 6".

**B. Performance / quality pass (Phase 9 part 2):**
- [ ] **B1. PerfBenchmark / FeatureProfile / OSFidelity probes** → the `hq` toggle decision (omega4 vs AccurateOmega is usually the only real lever) + README perf table. See §5.
- [ ] **B1b. NEW (2026-07-27, user request): explicit no-OS (1×) and low-OS (2×) sweeps with a
  written compensation decision** — not just the 4× vs 8× fidelity comparison. Measure the plain
  linear-stage top-octave droop (`dsp.md` "Top-octave accuracy") at 1×/2× in addition to
  aliasing/harmonics, and decide + implement or explicitly reject the "low-OS top-octave restore"
  shelf `dsp.md` already specs — low-CPU/low-latency users will run at 1×/2× routinely, not just
  transiently. See §5.
- [ ] **B2. Deferred OS-fidelity residual** — the 4× narrow-band aliasing at the amp-0.5 extreme corner (8× pristine; recommend 8× for extreme high-drive). See §5 + the OSValidationTest header.

**C. Carry-forwards:**
- [ ] **C1. VU idle-gate threshold vs the makeup** — ⚠ **the target moved again in session 41: the makeup is now 2.599, not 3.684** (§4 "A5 step 1"), so the idle floor is 0.9 → 2.599 ≈ 2.9× the Phase-8 value, not ~4×. Re-check the gate against **2.599**. Phase-8 carry-forward, §6.
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

### ⛔ GAP #2 — Treble ~322 Hz notch. Shipped session 19; **REOPENED session 46** — see "GAP #2 REOPENED" at the end of §4 before acting on anything below.

> ⚠ **The record below is kept for its reasoning, not as a current verdict.** Its "~37 dB deep in the
> assembled model" is an ISOLATED-stage number (the assembled notch was ≤2.6 dB — session 14), and its
> "−3.4 dB in the capture" is a 1/3-oct read of a notch that is 7–24 dB deep at full resolution. The
> shipped `trebleLadderDampR = 30k` therefore damped a quantity that was already ~4× too shallow at the
> output. **Do not move the constant on this basis either** — the full matrix refutes Rd=0; it is a
> compensating error for A3's OD-vs-bleed balance and must be re-fitted only after A3.

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

#### ⭐ A3 ROOT CAUSE (session 29, 2026-07-26) — the pedal has an LF CANCELLATION NULL that the model cannot produce. Analysis only; nothing in `src/` changed.

**The one-line result.** Below ~80 Hz the real pedal's OD path is **anti-phase with the clean BLEND
bleed**; the model has them in phase at every frequency and every drive. So the gap was never a level
error, and no amount of OD-path attenuation can close it — attenuation cannot produce a null.

**The decisive evidence — sweep the DRIVE axis, not just drive noon.** Each drive setting minus the
`blend-0700` full-clean capture, per band, per-capture gain **un-applied** (session 23's rule).
`sweep_drv_-18`; the trend is identical at `-12` and `-6`.

| 40 Hz | drive min | 9:30 | noon | 2:30 | max |
|---|---|---|---|---|---|
| **pedal** | −18.0 | −18.4 | −20.5 | **−31.8** | −14.7 |
| **plugin** | −13.1 | −11.3 | −7.7 | −4.1 | −6.0 |

The pedal's 40 Hz output **falls** as drive rises, collapses into a **−31.8 dB null at 2:30**, then
recovers at max. That is only possible if the OD contribution is subtracting: as drive grows, |OD|
rises through |bleed|, cancels it, and overshoots. Corroboration that it is a genuine magnitude-matched
cancellation and not a one-band artefact: **the null MIGRATES DOWN in frequency as drive rises past
it** — at max drive 40 Hz has recovered to −14.7 while 20/25 Hz have collapsed to −21.7/−22.5, i.e.
the null has moved to ~22 Hz, exactly where |OD| now equals |bleed|.

The plugin rises monotonically at every band and every drive setting and has no null anywhere.

**The crossover is ~80 Hz, and it is a rotation, not a sign flip.** Below it the pedal subtracts;
above it it adds (127 Hz: −15.3 → −14.1 → −10.8 as drive rises). A global inversion would subtract at
*all* frequencies, so **session 19's "not a polarity bug" verdict stands unchanged** — this is
frequency-dependent phase, the different claim that handover section explicitly reserved.

**Measured phase, model side** (`a3_blend_decompose`, GRUNT cut / drive noon / BLEND max, OD-vs-bleed):
+104° @20, +58° @40, +24° @64, +8° @80, −7° @101, −31° @160, −37° @202. The model already crosses zero
near 90 Hz — the shape is roughly right, but it never approaches anti-phase, so it can only ever add.
To reproduce the null the OD path needs ≈**90–120° more LF lead**, i.e. ~140–180° at 40 Hz decaying to
~0 by 200 Hz. A second-order-ish highpass character cornering near 80–100 Hz has that shape; a single
first-order corner cannot (it saturates at 90° and is nearly flat in phase across 20–250 Hz, which is
why the ~896 Hz GRUNT-cut corner alone was never going to explain a crossover at 80 Hz).

**⚠ TWO CORRECTIONS TO THE HANDOVER ABOVE — both change what to work on.**

1. **The bleed's LEVEL is very nearly right; hypothesis (a) is largely dead.** At drive-min the
   pedal's curve is **flat at −17.4…−18.3 dB across 20–64 Hz** — the exact signature of a resistive,
   frequency-flat bleed — against the model's measured bleed of **−16.93 dB**. That is ~1 dB, not the
   3.6 dB the gate implied. **The gate number was measured against the pedal's *drive-noon* total,
   which is itself depressed by the cancellation**, so it overstated the bleed error by reading a
   phase effect as a level effect. What is "necessarily part of A3" is the PHASE.
2. **A3's target is UNCHANGED by session 28's `c21R` move.** `c21R` is shared post-BLEND, so it
   cancels exactly in the `ref-od` − `blend-0700` difference. Re-measured on the current build the
   handover table reproduces to **0.2–0.3 dB on both rows**, so every number in it still stands as
   written. (It was computed at `sweep_drv_-18` — recorded here because it was not stated.)

**⚠ A method error made and corrected in this session, worth not repeating.** The first version of
`a3_solve.py` concluded that because the model's bleed exceeds the pedal's total at 20–64 Hz, *no* OD
phasor could reach the target — "impossible". That is wrong: with **both** the OD magnitude and phase
free, |1 + m·e^{iθ}| sweeps [|1−m|, 1+m], and over all m that covers [0, ∞), so every target is
reachable. What the geometry actually forces is the **sign** of the interaction:

> T < 1 ⟹ m² + 2m·cosθ < 0 ⟹ cosθ < −m/2 < 0 ⟹ **θ > 90°**

i.e. wherever the pedal's total sits below the model's own bleed, the OD contribution *must* be
partially cancelling. That is the stronger and correct claim, and it is what the script now reports.
Lesson: when solving a two-phasor sum, free **both** magnitude and angle before declaring a target
unreachable — pinning one of them turns "not at this level" into a false impossibility.

**⛔ What this rules out.** Every OD-path *attenuation* candidate is now dead, not merely
insufficient: `clipC11`/`clipC12`/`clipC13` scaling, a broadband OD trim, and any "make the clipper
see less" lever. They cannot create a null at any value. This retires the whole family the handover
called "necessary-not-sufficient" — it is not necessary either.

**▶ NEXT, in order.**
1. **Localise the missing phase per OD stage** with `analysis/od_taps_probe.cpp` (it already taps
   jfet/treble/drive/clipper/recovery/skB/skA). Measure each boundary's phase vs the clean tap across
   20–250 Hz and find which stage owes the ~90–120°. Do this BEFORE proposing an element — sessions
   19/20 both mis-attributed a gap by reasoning from a stage transfer instead of measuring.
2. **Gate any candidate on the NULL, not on band-RMS.** Null frequency vs drive setting pins the OD
   path's LF phase *and* magnitude simultaneously and is far tighter than an aggregate: the fix must
   reproduce a null near 40 Hz at drive 2:30 that migrates to ~22 Hz by max. A candidate that
   improves band-RMS without producing a moving null has not fixed this.
3. Only then consider the residual ~1 dB bleed level, which is small enough to be inside other
   errors — do not fit it before the phase is right, or it will absorb the phase error.

**Tools added this session:** `analysis/a3_blend_decompose.cpp` — exact BLEND-node decomposition
(`full = od + bleed`, superposition self-checked to <−280 dB) at arbitrary grunt/drive/level, with a
BLEND=0 full-clean reference pass so its dB are directly comparable to the A3 table; raw phasors on
stdout. `analysis/a3_solve.py` — the geometry solve above. ⚠ Both fix a settings bug inherited from
`blend_null_probe.cpp`, which sets `attackIdx = 1` and calls it "Boost centre (ref-od baseline)" —
`_REF_OD` is ATTACK **Flat** (idx 0). At LF C8's 220 pF makes this near-inert, but at drive noon it
moves the clipper's operating point; do not copy that line into a new probe.

#### A3 chart-review corroboration + a NEW open item (session 30, 2026-07-26). Analysis only; nothing in `src/` changed.

The user read the `ref-od`/`ref-od_gain-n12` FR charts directly (not via a decomposition probe) and
flagged three things independently of session 29's phasor analysis. Checked all three against
`analysis/reports/comprehensive_data.json` + a fresh render on the current `main`:

1. **LF peak-location mismatch — independent corroboration of the session-29 root cause.** At
   `sweep_drv_-6` the pedal dips to its quietest at 40–50 Hz (+3.5 dB) then rises to a broad peak at
   160–200 Hz (+13.2 dB); the plugin instead rises monotonically from 20 Hz and peaks at 63–80 Hz
   (+11.3 dB) with no dip. Exactly the shape the missing cancellation null predicts: without it, the
   model's peak sits wherever its uncancelled LF corner naturally lands instead of migrating past the
   null into the pedal's real >100 Hz bump. Nothing new here beyond session 29 — a second, independent
   read of the same still-unfixed gap.
2. **The "increasing level shortfall with frequency" the user read off the chart is mostly a
   measurement artifact of (1), not a separate bug — see §3's new caveat.** Re-anchoring the
   gain-match to bands ≥200 Hz (excluding the broken LF region) collapses the apparent −3…−6 dB
   mid/high "rolloff" down to ≤~1–2 dB, while the true LF error is revealed as the plugin running
   **+8…+10 dB too hot** at 40–63 Hz (consistent with (1), not with it). **Any prior/future chart read
   using the report's stock broadband gain-match should be treated with this in mind until A3 ships.**
3. **The 320→400→~800 Hz dip/peak/dip structure is a mix of two already-known, already-partially-
   addressed items** (re-confirmed at higher precision, not new): the 320/403 Hz wiggle is GAP #2's
   TrebleAttack ladder notch (session 19's fix was explicitly "modest" — the pedal's real ~1.6 dB
   dip-to-peak swing there is still only ~0.3–0.4 dB in the model); the ~800 Hz softness is in GAP
   #1b's bridged-T territory (closed on an aggregate 116-row median, not checked at this single-capture
   resolution before). Worth a fresh look after A3, since A3's fix changes the BLEND-node level feeding
   this same region.

**⭐ NEW — checked whether the same artifact explains `ref-od_gain-n12`'s midrange deficit. Partially.**
`null_depth` is comparably bad for both captures (`ref-od` −4.93 dB, `ref-od_gain-n12` −3.93 dB), so
gain-n12 isn't uniquely broken in overall correlation, and re-anchoring its gain-match the same way
(to its 1.6–3.2 kHz best-agreement plateau) surfaces the *same* +3…+5.7 dB LF excess as `ref-od` — so
the sub-1 kHz portion of its "deficit" is largely (2) again. **But a real, distinct residual survives
the re-anchor that `ref-od` does not have at all:** a genuine ~2–4 dB dip through 400–1000 Hz, and a
much larger **~10–12 dB narrowband collapse at 5.1–6.4 kHz**, tapering into a −5…−6 dB shelf through
8–16 kHz. Checked this isn't just low-SNR noise: coherence(cap, ren) at 5.1 kHz is 0.59 (vs 0.90+ at
neighbouring bands, so genuinely reduced correlation) but the plugin's absolute band-limited RMS
(4.8–7 kHz, Butterworth-filtered) is also really lower — **−50.5 dBFS vs the pedal's −38.4 dBFS**, a
~12 dB real energy gap, not merely a decorrelation artifact. It is present ONLY at the reduced
(`gainSessionDb=-12`) stimulus level, which a static filter/EQ error cannot explain (those aren't
level-dependent) — points at gain-staging or a nonlinear-stage operating-point difference instead.
**Not localised. Not yet in any prior session's findings. Parked for after A3** (§0 backlog
"A3-adjacent") since A3's fix changes the gain-staging feeding this same BLEND region.

#### ⭐ A3 step 1 — PHASE LOCALISED (session 31, 2026-07-26): no existing stage can supply it. Analysis only; nothing in `src/` changed.

Session 29's step 1 was "localise the missing 90–120° per OD stage with `od_taps_probe.cpp`, BEFORE
proposing an element". Done, and the answer is a **negative result that redirects step 2**: the
missing lead is not mis-attributed to a stage, it is a mechanism the model **does not have at all**.

**(1) ⭐ THE OD PHASE IS DRIVE-INDEPENDENT — so A3's phase gap is a LINEAR problem.** Swept the DRIVE
knob 0 → 1 through `od_phase_probe`: every per-stage phase moves **< 0.1°** at every band. Only the
magnitude moves. This matters twice over: the fix can be developed and gated at drive-min where the
whole chain is linear (no describing function needed), and any candidate that produces its phase
shift *through* a nonlinearity is the wrong shape of fix. It also confirms session 29's reading of
the null migration — the null moves with drive because |OD| grows past |bleed| at ever-lower
frequencies, not because anything rotates.

**(2) THE PER-STAGE PHASE BUDGET, measured** (`analysis/od_phase_probe.cpp`, GRUNT cut / BLEND max /
ATTACK flat, per-stage increment vs the clean tap, inversions removed):

| deg @ | jfet | treble | drive | clipper | recov | skB | skA | **total** |
|---|---|---|---|---|---|---|---|---|
| 40 Hz | **+76.9** | **−76.4** | −0.2 | **+87.4** | **−28.7** | −0.5 | −1.0 | **+57.6** |
| 80 Hz | +65.5 | −92.0 | −0.4 | +84.8 | −46.7 | −0.9 | −2.0 | +8.2 |
| 127 Hz | +54.8 | −93.8 | −0.7 | +81.8 | −57.8 | −1.5 | −3.2 | −20.3 |

The probe is **validated against `a3_blend_decompose`**: because `LevelBlend` is purely resistive and
everything after it is shared, the skA column *is* the OD-vs-bleed phase at the BLEND node, and it
reproduces session 29's row (+104/+58/+24/+8/−7/−31/−37) exactly. Two leads, two lags, and **both
leads are first-order highpasses already sitting within 3–13° of their 90° asymptote**: the JFET
input HP (C2 1n into R4+R5 = 1.1M, 144.7 Hz → atan(144.7/40) = 74.6°) and the clipper's GRUNT-cut
coupling (~896 Hz → atan(896/40) = 87.4°, exact). Note the "treble" increment also carries the JFET's
own output impedance, which `TrebleAttack` stamps.

**(3) THE REQUIREMENT IS NOW BOUNDED, NOT ESTIMATED** (`analysis/a3_phase_solve.py`). As the OD
magnitude *m* sweeps the positive reals, `|1 + m·e^{iθ}|` traces a ray from 1 whose closest approach
to the origin is `|sin θ|`. So the DEEPEST total measured at any drive gives
**θ ≥ 180° − asin(min_d t_d / β)** — one capture per band, and **no model of how the OD grows with
drive**. 1/3-octave banding can only *fill* a null, never deepen it, so it is conservative:

| Hz | 20 | 25 | 32 | **40** | 50 | 64 | 80 | 101 | 127 |
|---|---|---|---|---|---|---|---|---|---|
| θ ≥ (β = −18.0) | 139.0 | 143.6 | 154.8 | **168.2** | 136.0 | 119.3 | — | — | — |
| θ ≥ (β = −15.2) | 151.6 | 154.6 | 162.0 | **171.5** | 149.8 | 140.8 | 130.0 | 119.6 | 96.8 |
| model | 104.2 | 90.0 | 73.3 | **57.6** | 41.5 | 23.7 | 8.0 | 7.3 | 20.7 |
| **deficit ≥** | 35 | 54 | 81 | **111** | 95 | 96 | 103 | 112 | 76 |

**θ(40 Hz) ≥ 168° for every bleed level in the plausible range**, so session 29's "~140–180°" is
sharpened to the very top of its own range. An independent 5-point least-squares over the whole drive
sweep (part 3 of the tool) agrees on the shape and adds the bands the bound cannot reach: ~148/152/
180/180/131/139/134/127/117/104/88/86° at 20→254 Hz. ⚠ **One handover phrase does NOT survive:
"decaying to ~0 by 200 Hz" is wrong** — the least-squares puts θ at ~85–88° still at 202–254 Hz, and
the pedal's totals there rise monotonically with drive, which needs θ < 90° but not θ ≈ 0.

**(4) ⛔ AND NO EXISTING STAGE CAN SUPPLY IT — this is the load-bearing result.** Scanned every lever
that has authority over the two lags. The treble lag **saturates**: `jfetRo` 200k → 20k (10× below
nominal) buys +28°, deleting the C5 ladder outright (`trebleLadderDampR` → 3 MΩ) buys +26°, `jfetRq2`
1M → 100k buys +18°. With **all three at physically absurd extremes simultaneously** the OD-vs-bleed
phase reaches only **94.0° at 40 Hz**, against a requirement of ≥168°. Still ≥74° short.

The arithmetic ceiling says the same thing: the two HP leads sum to +164° at 40 Hz, and that is only
reachable if *all* lag is zero — including the recovery bridged-T's −28.7°, which is **schematic-
verified on both schematics and capture-confirmed** (GAP #1b, closed on 116 OD rows) and therefore is
not on the table. So the realistic headroom above the shipped +57.6° is ~+65°, and about +110° is
needed. ⇒ **The OD path needs an additional phase-lead mechanism that does not exist in the model.**

**(5) SHAPE CONSTRAINT ON WHATEVER THAT MECHANISM IS — it is not "more highpass".** The deficit is a
HUMP, falling at both ends: ~35–54° at 20–25 Hz, ≥111° at 40, ≥103–112° at 80–101, ~76° at 127,
~50° at 202–254. Two cascaded first-order HPs steep enough to reach 171° at 40 Hz need fc ≈ 545 Hz
each, which then leaves 139° at 202 Hz — where the pedal still ADDS and needs θ < 90°. So a pure
highpass character over-rotates the upper end. A pole+zero (lead-network / bandpass) character has
the right shape. The candidate must also not over-rotate past 180° at 20–40 Hz, where the model
already carries +104°/+58°.

**(6) SEPARATE NEW FINDING — the model's OD magnitude vs DRIVE is NON-MONOTONE, and the pedal's is
not.** Model μ_d = |od|/|bleed| at 40 Hz across drive min→max: **0.79 / 1.22 / 2.30 / 3.84 / 2.87** —
it peaks at 2:30 and FALLS by max. The pedal's must keep growing straight through the null and out
the far side (−31.8 dB at 2:30 → −14.7 at max requires m to pass 1 and continue). This is a
drive-axis error independent of the phase gap — it is why the least-squares residual is ~4 dB at
40–101 Hz and nowhere else — and it is presumably the clipper compressing too early at max drive
(GAP #3a territory). **Do not fold it into the phase fix; it needs its own gate.**

**(7) ⚠ THE BLEED LEVEL IS NOT SETTLED, AND SESSION 29'S OWN LESSON RECURSES.** The least-squares
fits β = **−15.2 dB** against the model's −16.93, i.e. the model's bleed is ~1.7 dB **LOW** — the
opposite sign to session 29, which read the pedal's drive-min total (−17.4…−18.3) as the bleed and
concluded the model was ~1 dB HIGH. Both readings are defensible and they disagree because the
drive-min total is *itself* already pulled down by the same cancellation: with θ ≈ 180° at LF even a
small OD subtracts. That is exactly the trap session 29 identified at drive-noon, one notch weaker
and not noticed. **Treat the bleed as within ~±2 dB and unresolved**, which does not change the plan
— item 3 already said not to fit it until the phase is right.

**Tools.** `analysis/od_phase_probe.cpp` — per-stage cumulative + incremental phase and magnitude vs
the clean tap, with trailing `key=value` FitParams overrides so a lever's phase authority can be
scanned without a rebuild. `analysis/a3_phase_solve.py` — the bound above, plus the 5-point
drive-sweep least-squares, with a `--selftest` that re-solves data synthesised from the model itself.
⚠ **The self-test earned its keep**: the first version used a golden section over the OD magnitude
and came back 7° wrong at 20 Hz on data where the residual must be zero — at fixed θ with cos θ < 0
the predicted level dips *through* the cancellation and rises again, so the cost is **bimodal in m**
and a unimodal search silently picks the wrong branch. Grid both axes. Any future two-phasor solve in
this project has the same hazard.

**▶ NEXT (A3 step 2), revised by (4) and (5).** Stop looking for a stage that is mis-parameterised;
look for LF structure the OD path does not have. Gate every candidate on the **NULL** — it must
produce a null near 40 Hz at drive 2:30 migrating to ~22–25 Hz by max — and additionally check it
does **not** push θ past 90° at 202–254 Hz, where the pedal still adds. `od_phase_probe` at drive-min
is the cheap inner loop (the gap is linear, per (1)); `a3_phase_solve` re-run against a candidate
render is the acceptance check.

#### ⛔ A3 step 2 — "the missing element is NON-minimum-phase" was tested and **DOES NOT HOLD** (session 32, 2026-07-26). Analysis only; nothing in `src/` changed.

The obvious next question after step 1 is what KIND of element to look for, and the sharpest version
of it is: **is the missing transfer minimum-phase?** If it were not, the search would have to move to
right-half-plane zeros — a genuine two-path cancellation inside the OD chain — rather than any
ordinary passive network. New tool `analysis/a3_extra_tf_probe.py` asked it two ways. **The answer is
that the question stays open, and the argument that appeared to close it was wrong.**

**(1) The family fits do not settle it.** Fitting candidate transfers (1st/2nd-order HP, shelf,
resonant HP, HP+all-pass) to the required complex response `G(f) = s(f)·e^{i(θ_ped − θ_mdl)}` fails
the way step 1 predicted: magnitude-optimal fits land 20–70° short in phase, phase-optimal fits blow
the magnitude by 20+ dB. That is a statement about **those families**, not about minimum-phase.

**(2) ⚠⚠ THE BODE-CEILING ARGUMENT IS AN ARTEFACT OF ITS OWN EXTRAPOLATION — this is the finding.**
The tempting escalation is Bode's gain-phase relation: for a fixed magnitude the minimum-phase
realisation delivers the **maximum** lead of any causal LTI network, so reconstructing φ from the
measured `s(f)` gives a topology-free ceiling. Run naively it appears decisive — the ceiling falls
36–84° short of the depth bound at every band 20–80 Hz, and the shortfall **survives** a monotone
repair of the two least trustworthy points (40 Hz: −84 → −37°). It is still wrong. **The phase at
40 Hz is bought mostly by the magnitude slope BELOW 20 Hz, which no capture in the matrix measures**,
and the probe extrapolated those tails FLAT. A self-test on networks whose phase is known in closed
form measures that bias directly:

| test network | integral itself | 12-band grid | FLAT tail, err at 20 / 40 Hz |
|---|---|---|---|
| 1st-order HP, fc 150 Hz | 0.03° | 4.85° | **−45.4 / −19.3°** |
| 2nd-order HP, fc 52 Hz | 0.05° | 3.66° | **−86.0 / −36.0°** |
| 2nd-order HP, fc 150 Hz | 0.05° | 9.69° | **−90.7 / −38.6°** |

The integral is exact; the flat tail costs **36–91° at exactly the bands A3 is about** — the entire
size of the "surviving" shortfall. Declare a 12 dB/oct sub-20 Hz tail on the repaired curve and the
40 Hz shortfall goes **−37° → +1°**. ⚠ The rationale originally written into the probe — that flat
tails are "the assumption most generous to the candidate at 40 Hz" — is **backwards** for a curve
that falls toward LF: a highpass keeps falling below 20 Hz, and that continued slope is precisely
what buys lead at 40 Hz, so truncating it flat destroys most of the lead rather than conceding it.

**(3) Corroboration from the other side, which is what makes this conclusive rather than merely
doubtful.** The probe's own explicit candidates contradict its ceiling: coincident 2nd-order
highpasses at **fc = 70–85 Hz CLEAR the 40 Hz depth bound (+8.5 / +17.6°)**. A real ceiling can never
be beaten by a construction that satisfies it. Two independent routes therefore agree the ceiling was
the broken part, not the physics. ⇒ **Do not record "no passive network can do this", and do not
pivot the search to two-path/RHP-zero candidates on this basis.**

**(4) What actually survives is session 31 item (5), restated with numbers: the binding constraint is
SHAPE, not attainable lead.** The coincident HP that clears 40 Hz is 20–45° short at 64–80 Hz while
running 8–16 dB hot at 20–25 Hz. The requirement is a **hump**, and one corner frequency cannot place
it — consistent with step 1's pole+zero (lead-network) recommendation, which is unchanged.

**⚠ METHOD TRAP, GENERAL.** A Hilbert/Bode phase reconstruction over a **band-limited** magnitude is
not assumption-free, however model-free it looks: the unmeasured tails dominate the answer at the
band edges, which is exactly where a bass problem lives. Never quote such a ceiling without (a) a
self-test against closed-form networks and (b) an explicit tail sweep. `min_phase()` now takes the
tail slopes as required arguments rather than defaulting to flat, `selftest()` runs on every
invocation, and the tool prints its own VERDICT.

#### ⛔ A3 step 2 — the TARGET WAS WRONG, and the blocker is the DRIVE AXIS (session 33, 2026-07-26). Analysis only; nothing in `src/` changed.

The plan was "propose a pole+zero candidate, gate it on the null". No candidate is proposed, because
checking the target first found a sign error in it and then a reason it cannot be designed against
yet. New tool `analysis/a3_lead_design.py` (log `analysis/fit_logs/s33_a3_lead_design.log`).

**(1) ⭐⭐ THE REQUIRED EXTRA PHASE WAS UNDERSTATED BY UP TO 76° — sessions 31 and 32 both read it off
an `abs()`.** `a3_phase_solve.py` part 3 solves for `|theta_ped|` (the sign is unobservable from
magnitudes), and it printed the MODEL's phase as `abs(theta_mdl)` so the two columns would look
comparable. But the model's OD-vs-bleed phase is **signed and crosses zero near 90 Hz**:

| f | 20 | 25 | 32 | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| θ_mdl printed | 104.2 | 90.0 | 73.3 | 57.6 | 41.5 | 23.7 | 8.0 | 7.3 | 20.7 | 31.5 | 37.9 | 37.6 |
| θ_mdl **actual** | +104.2 | +90.0 | +73.3 | +57.6 | +41.5 | +23.7 | +8.0 | **−7.3** | **−20.7** | **−31.5** | **−37.9** | **−37.6** |

so the `deficit` column — and `a3_extra_tf_probe.py`'s `DPHI`, which transcribes it — understates the
phase an added element must supply by **2|θ_mdl|**: 15° at 101 Hz, 41° at 127, 63° at 160, **76° at
202–254**. Verified directly against `build/a3_dec_drv0.5.csv`. Both files now print the signed value
and label the column `extra`.

**⚠ What this retires: "the deficit is a HUMP falling to ~50° at 202–254, so a pole+zero / lead
network has the right shape" (session 31 item 5, reaffirmed by session 32 item 4).** Corrected, the
requirement is a broad **PLATEAU** — ~+44° at 20 Hz, +107 at 32, and +115…+137 continuously from
64 Hz to 254 Hz. A lead network's phase returns to zero, so that recommendation does not follow from
the data any more. **Both sessions' NEGATIVE results stand unharmed** (no existing stage can supply
the lead; the Bode ceiling was decided by its unmeasured tails) — only the shape of the fix changes.

**(2) THE BAND SET NOW REACHES 806 Hz, measured rather than extrapolated.** `a3_blend_decompose.cpp`
and `PROBE_BANDS` extended to 320/403/508/640/806. This is the direct application of session 32's
lesson: whether a +120° plateau at 254 Hz is realisable is decided by what |G| does *above* the band,
so that tail is now measured. (320 Hz is then excluded from every fit — it is the TrebleAttack notch
band, a known separate gap, and shows up as a lone outlier: s = 0.57 against 1.10 and 1.54 either
side.)

**(3) ⚠⚠ THE TARGET IS NOT IDENTIFIABLE WITHOUT THE BLEED LEVEL, SO THE STANDING ORDER OF WORK HAS NO
FIXED POINT.** Session 29 item 3 said "only then revisit the residual bleed level — fitting it first
would absorb the phase error", and 31 repeated it. But the phase target is a function of β:

| β dB | extra @40 | @101 | @160 | @202 | @254 |
|---|---|---|---|---|---|
| −15.4 (s31 least-squares) | 122 | 133 | 134 | 123 | 120 |
| −16.9 (model's own) | 122 | 125 | 122 | 102 | 89 |
| −18.0 | 122 | 119 | 111 | 80 | 38 |

**82° of swing at 254 Hz across the ±2 dB the bleed is unresolved by.** So the phase cannot be gated
first and the level fitted afterwards; they are one problem.

**(4) CAUSALITY IS THE MISSING EQUATION, AND IT DISAGREES WITH THE LEAST-SQUARES.** Magnitude and
phase are not independent for a causal element, which the levels alone cannot express. Fitting a
**minimum-phase** rational to |G| alone (its phase is then not ours to choose) and asking how far
short it lands is a constructive ceiling — and unlike a Bode integral it needs **no tail assumption**,
which is what makes it usable after session 32. Non-minimum-phase content can only *subtract* phase,
so a shortfall here cannot be recovered by any causal element at any order.

| β dB | driveRMS | edge | magRMS | shortRMS | mean | worst |
|---|---|---|---|---|---|---|
| −20.0 | 2.37 | 7 | 1.20 | 38 | +7 | −30 |
| −18.5 | 2.10 | 6 | 1.01 | 47 | −12 | −51 |
| −17.0 | 1.90 | 5 | 0.85 | 52 | −40 | −68 |
| −15.5 | 1.84 | 2 | 0.60 | 61 | −58 | −83 |
| −14.0 | 1.94 | 1 | 0.40 | 83 | −82 | −106 |

The drive-sweep least-squares is minimised near **−15.5** and causality wants **≤ −18.5**: they pull
opposite ways. Neither is decisive — `driveRMS` moves only 1.84 → 2.10 dB across the whole range (on
a ~2 dB floor set by item 5), so session 31's β = −15.2 was never strong evidence; and the low-β end
leans on bands whose θ has **pinned at 180°** (`edge` = 6–7 of 12). ⇒ **the bleed level is still
open, its sign now leans back toward session 29's** (model ~1.5 dB HIGH, not LOW), and it must be
resolved *jointly* with the element, not before or after it.

**(5) ⛔⛔ WHY NO CANDIDATE IS PROPOSED — the bands that carry the null are the bands that do not fit,
at EVERY β.** Per-band drive-sweep residual (dB):

| β | 20 | 25 | 32 | **40** | **50** | **64** | **80** | **101** | 127 | 160 | 202 | 254 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| −18.5 | 1.4 | 1.5 | 1.8 | **4.9** | **4.1** | **3.9** | **3.2** | **2.3** | 1.4 | 0.6 | 0.1 | 0.2 |
| −15.5 | 0.8 | 0.9 | 0.8 | **4.1** | **4.3** | **3.8** | **3.1** | **2.2** | 1.3 | 0.5 | 0.1 | 0.3 |

40–101 Hz sits at **2–5 dB regardless of β**. The `(s, θ)` solve there is fitting against the model's
`μ_d`, which session 31 item 6 already showed is wrong on the drive axis — so the phase target
inherits that error *exactly where A3 lives*. Consistent with this, the best min-phase element at the
best β still misses individual bands by 30–50° (`shortRMS` never falls below ~28° at any β). **A
candidate fitted to this target would be fitted to a known defect.**

**(6) ⭐ SO THE DRIVE-AXIS DEFECT IS NOT A SIDE ISSUE — IT IS THE BLOCKER, AND IT IS NOW LOCALISED TO
IC2_A's RAIL CLAMP.** Session 31 item 6 recorded the symptom (model μ_d peaks at drive 2:30 and falls
by max; the pedal's must grow through the null and out) and guessed "presumably the clipper". Measured
per stage with `od_phase_probe` (drive 2:30 → max, dB):

| | 40 Hz | 64 Hz | 101 Hz | 202 Hz | 320 Hz |
|---|---|---|---|---|---|
| DriveStage, rails as shipped | **+0.40** | +0.51 | +0.89 | +4.67 | +6.99 |
| DriveStage, rails effectively off | **+7.77** | +7.78 | +7.78 | +7.77 | +7.78 |
| clipper increment, rails on | −2.17 | −1.88 | −1.47 | +0.30 | +0.28 |
| clipper increment, rails off | +2.63 | +0.81 | +0.25 | +0.32 | +0.23 |

With the rails off the DriveStage increment is a **frequency-uniform +7.78 dB**, exactly as a linear
gain stage must be, and the clipper no longer goes backwards anywhere. **The primary agent is IC2_A's
RailClamp, not the clipper** — its input is bass-heavy, so it saturates at LF first and eats the whole
knob movement at 40 Hz while passing +7 dB at 320 Hz. It is a level effect: the model's 40 Hz OD grows
monotonically to +25 dB at −36/−30 dBFS but peaks at drive 2:30 and falls at −18 and −12 dBFS.

Size of the error at 40 Hz: the pedal goes −31.8 dB (2:30) → −14.7 (max), which with θ ≈ 180° needs
|OD|/|bleed| to grow **+6.2 dB** on that one step; the model delivers **−2.5 dB**. An **8.7 dB**
discrepancy on a single drive step, in the band that defines the null.

⚠ Do NOT read this as "lower the rail voltages". `railNeg = 2.9 / railPos = 2.7` were **derived**
physically in session 21 precisely because the capture objective on them is monotone with no interior
minimum — the classic "make the clipper see less" degeneracy. The rails are probably right and the
signal reaching them is probably too bass-heavy.

**⭐ WHICH UNIFIES THE TWO PROBLEMS.** An LF excess *upstream of IC2_A* would (i) make the drive stage
rail at LF preferentially, producing exactly the non-monotone μ_d above, and (ii) be the missing
highpass/lead itself. The corrected requirement's magnitude — |G| ≈ −14…−19 dB at 32–50 Hz rising to
0 dB by 160 Hz — is the shape of a 2nd-order highpass in the 100–160 Hz region, and placing it
**before the DRIVE stage** would do both jobs at once. That is a hypothesis with a mechanism, not a
curve fit, and it is the first A3 candidate that predicts something the objective did not ask for.

**▶ NEXT (A3 step 3), re-ordered.** (a) Fix the drive-axis magnitude defect first — the model's |OD|
must grow monotonically with drive at 40–101 Hz, gated on reproducing the pedal's +6.2 dB over the
2:30→max step, NOT on band-RMS. (b) Re-run `a3_phase_solve` + `a3_lead_design`; the 40–101 Hz
drive-fit residual should collapse from 2–5 dB, and only then is the phase target worth designing
against. (c) Test the unified hypothesis directly by placing a 2nd-order highpass ahead of IC2_A and
checking whether it fixes the drive axis *and* the phase together. (d) Gate on the NULL as before
(near 40 Hz at drive 2:30, migrating to ~22–25 Hz by max) and re-fit β **jointly**, never after.

**⚠ METHOD TRAPS FROM THIS SESSION.**
- **A transcribed constant is where the error was.** `a3_extra_tf_probe.py` hard-codes the target as
  literal arrays copied out of another tool's printout; the sign was lost in the copy and two sessions
  built on it. `a3_lead_design.py` imports `a3_phase_solve` and rebuilds the target live instead.
- **`abs()` on a quantity whose sign is unobservable is fine; differencing it against one whose sign
  IS observable is not.** The two columns looked comparable and were not.
- **A self-selecting score.** The β scan first ranked each β on "bands whose drive fit is trustworthy",
  which drops bands as β falls — β = −21 scored best on 4 bands while fitting worse at all 12. Fixed
  band set, and report how many bands are degenerate.
- **A mean can hide the finding.** Scoring the phase shortfall by its mean gave "≈0" at β = −18.5
  while individual bands were +80/−50; the RMS never goes below 28°.

#### ✅✅ A3 step 3a — the DRIVE AXIS IS FIXED, and the unified hypothesis is CONFIRMED (session 34, 2026-07-26). `trebleC7` SHIPPED.

Session 33's plan was (a) fix the drive-axis magnitude defect, (b) re-run the phase solve and check the
40–101 Hz residual collapses, (c) test whether one element upstream of IC2_A does both. All three ran,
and **(c) is confirmed by a single first-order highpass**: `FitParams::trebleC7` = C7 **100 n → 680 pF**
(`TrebleAttack::setC7`, applied in `PedalChain::applyParams`). ctest **17/17**; `trebleC7 = kC7`
reproduces the shipped stage bit-for-bit (verified: all five decompose CSVs byte-identical to session
33's before any value moved).

**(1) THE GATE, BUILT FIRST AND DERIVED LIVE — `analysis/a3_drive_axis.py` (+ `a3_drive_axis_scan.sh`).**
No transcribed constants (session 33's own trap): it reads the captures, inverts the totals, and
enumerates the ambiguity instead of choosing. Because the bleed is drive-independent — **verified, not
assumed** (the decompose probe's clean column is identical to 0.00e0 dB across all five drives) — every
*step* in |OD| is β-free, which is what makes the gate usable while β is still open. Three sub-gates:
G1 |OD| monotone in drive at 40–101 Hz; G2 the 2:30→max step; G3 the mid steps must not regress.

⚠ **The self-test immediately falsified my first version.** I asserted that monotone-|OD| pruning picks
the branch uniquely; it does not. At the drive sitting *in* the null, m = 1 ± r with r small, so **both**
roots stay monotone-compatible with their neighbours. So the totals **bound** the 2:30→max step, they do
not determine it — session 33's single "+6.2 dB at 40 Hz" is one of two branches. Corrected, the tool
reports a range and G2 gates on containment. **At 50 and 64 Hz the two branches collapse onto one value,
so the target there is a number, not a range — read G2 at 50/64, not at 40.**

**(2) ⭐ NEW AND DECISIVE: β ≤ −18.5 dB IS REFUTED, from the magnitudes alone.** At 40, 50 **and** 64 Hz,
and at θ = 170/175/180°, **no monotone ladder exists at all** at β = −18.5. The mechanism is clean: at LF
the OD subtracts, so the total must sit *below* the bleed while the OD is small — a β below the pedal's
own drive-min total (−18.03 dB at 40 Hz) forces m(min) > 2, an OD already 6 dB *above* the bleed at the
bottom of the knob, which then has to fall to reach the null. **This breaks session 33 item 4's tie**
(drive-sweep least-squares wanted −15.5, the causality/min-phase fit wanted ≤ −18.5) in favour of the
higher β, on a third and independent axis. Corroborated after the fix: see (4).

**(3) THE MECHANISM, MEASURED.** The OD path's response *into* IC2_A peaks at 32–40 Hz (−8.5 dB re the
clean tap) and falls to −20.5 dB by 320 Hz — 12 dB bass-heavy, because C7 at 100 n corners at ~1.2 Hz
into R13 and is inert everywhere in band. At −18 dBFS/max drive the unclamped IC2_A output at 40 Hz is
**≈8 V** against a ±2.7/2.9 V rail, so it hard-clips at LF and the whole top half of the DRIVE knob does
nothing there. ⭐ **The size needed is independently the same number:** ~9.4 dB of LF cut just reaches the
rail, and session 33's |G| requirement was −14…−19 dB at 32–50 Hz. Two derivations that never saw each
other. (And the clipper "going backwards" at 40 Hz is downstream of this: a squarer IC2_A output puts far
more harmonic energy through the ~896 Hz GRUNT-cut coupling, which saturates the CD4049 and suppresses
the already-weak 40 Hz fundamental.)

**(4) RESULTS AT THE A3 OPERATING POINT (`sweep_drv_-18`, where the null and the whole A3 target were
measured).** Step-profile RMS over 50–254 Hz vs the pedal: **4.72 → 0.647 dB**. G1 **FAIL at 5/5 bands →
PASS**. Session 33's pre-registered prediction for (b) is met and then some — the 40–101 Hz drive-fit
residual in `a3_phase_solve` part 3:

| | 40 | 50 | 64 | 80 | 101 |
|---|---|---|---|---|---|
| shipped | 4.40 | 4.19 | 3.83 | 3.13 | 2.24 |
| C7 = 680 p | **0.16** | **0.19** | **0.28** | **0.46** | **0.46** |

and the solve's magnitude scale `s` — how far the model's OD is from the pedal's in absolute terms —
goes from **0.15–0.18 at 20–50 Hz (a factor of ~6 too hot)** to **0.74–1.11 across 20–254 Hz**. Nothing
in the objective asked for that; it was fitted on the drive *shape* alone.

**⭐ AND β IS NOW IDENTIFIED.** `a3_lead_design`'s per-band residual-vs-β scan was 2–5 dB at 40–101 Hz at
*every* β (that was session 33 item 5, the reason no candidate could be proposed). It now has a sharp
optimum: **0.1–0.5 dB at every band at β ≈ −16.5…−17.0**, i.e. essentially the model's own −16.93 dB.
Session 33 said the level and the element "are one problem and must be solved jointly" — that was right,
and fixing the magnitude is what made the joint problem well-conditioned.

**(5) WHAT IS LEFT OF THE PHASE, AND ITS SHAPE CHANGES BACK.** C7 supplies +75° at 40 Hz, +69 at 64, +61
at 101, +36 at 254 — exactly a first-order HP's own phase at fc ≈ 183 Hz, as it must. The residual
requirement is now **+30…+36° from 40 to 127 Hz, ~0 by 160–254, and NEGATIVE (−39/−21°) at 20–25** —
a bump that returns to zero at both ends. **That is a lead-network (pole+zero) shape again**, i.e.
session 31 item 5's original recommendation, which session 33's sign correction had retired in favour of
a +115…+137° plateau. The plateau was an artefact of the broken drive axis, not of the sign fix — the
sign fix itself still stands. Best causal fit found: zeros 59.9 Hz Q 1.17 / 479 Hz, poles 69.6 Hz Q 1.06
/ 1626 Hz, worst per-band shortfall **42°** (was ~28° RMS against a far larger target). **Not built** —
it is the next step's job, and it must be gated on the null and fitted jointly with β.

**(6) FULL MATRIX — the biggest single move in Phase 9, and surgical.**

| | OD | CLEAN | ALL | OD tilt |
|---|---|---|---|---|
| shipped | 6.221 | 0.465 | 3.343 | 9.10 |
| trebleC7 = 680 p | **3.931** | **0.465** | **2.198** | **1.20** |

**93 rows better by >0.5 dB, 16 worse, 124 bit-identical.** The CLEAN half is untouched to the bit (C7 is
in the OD path; the clean tap splits at IC1_A) — surgical by construction, like `midCapRatio` and
`trebleWiperR` before it. ⭐ **The `od_tilt_metric` bass-tilt number that has been the A3 signature since
session 20 goes 9.10 → 1.20 dB.** Biggest improvements are exactly the captures that defined the gap:
`drive-0700_grunt-boost` **20.91 → 7.61**, `drive-0930_grunt-boost` 19.27 → 8.85, `grunt-flat` 15.80 →
6.20, `drive-0930_grunt-flat` 15.67 → 5.27. Worst regressions are +2.5 dB and concentrated in
`level-*_gain-n12` / high-drive rows (`level-1430_gain-n12` 2.54 → 5.06, `drive-1700_grunt-boost` 5.83 →
7.44) — see (7).

**(7) ⚠ THE HONEST LIMITS. Read these before treating A3 as closed.**
- **It fixes the drive axis at −18 dBFS, NOT at −12 or −6.** Per-level step-residual RMS: −18 **4.72 →
  0.65**, −12 5.36 → 4.58, −6 3.65 → **4.26 (worse)**. But the residual at those levels is a roughly
  frequency-FLAT ~1–2 dB over-compression against pedal targets that are themselves near zero (+0.06 to
  +0.36 dB) — a *different*, smaller defect, not the frequency-shaped drive-axis error C7 addresses.
  ⚠ **A naive joint-level RMS hides this and slides the optimum to ever-smaller C7** — the "a mean can
  hide the finding" trap again, one session later. Read the per-band table, not the joint scalar.
- **680 pF against a schematic-and-BOM-verified 100 n is a factor of 147.** That is a far weaker physical
  story than `trebleWiperR` (3k3→4k7) or `c21R` (10×). Same third branch as always — our schematic is a
  clone of the *original* B7K, the captured unit is an Ultra — but **do not describe this as having found
  the real circuit.** What is established is that a **first-order highpass at ~183 Hz somewhere in the OD
  path ahead of IC2_A** is required; that C7 is the element carrying it is the *cheapest* placement, not a
  proven one. ▶ A `schematic-checker` pass on C7 / R11 / R13 and the node-P network is owed.
- **The value was selected on the drive-axis gate, not on band-RMS** (dsp.md/§0's standing rule). The
  matrix is corroboration and a regression check. Interior minimum verified on the gate in both
  directions (objective 4.72 at 100 n → **0.647 at 680 p** → 4.62 at 220 p) — **not** the "delete the
  element" degeneracy that killed the session-5/6 clipper fits and the GAP #3b `clipC13` scan.

**⚠ METHOD NOTES.**
- **A verdict narrated in a string outlives the condition it described.** `a3_lead_design` hard-coded
  "40–101 Hz sits at 2–5 dB regardless of β" and "⛔ DO NOT BUILD THIS"; after the fix those sentences
  printed directly above a table of 0.2 dB. Both are now **computed from the scan** and flip to a PASS
  verdict on their own. Same class as the transcribed target that file exists to correct.
- **The self-test is what caught the branch-uniqueness error**, before it reached a number anyone quoted.
- `a3_phase_solve.py` and `a3_lead_design.py` both gained `--csv-prefix` so a candidate render can be
  graded without clobbering the shipped baseline CSVs.

**▶ NEXT (A3 step 3b).** (a) Design the residual lead network against the now-trustworthy target
(+30…+36° at 40–127 Hz, →0 by 160, negative at 20–25), fitting **β jointly** — the scan now identifies it
sharply at ≈ −16.5…−17.0, so re-check that as part of the fit rather than before or after. (b) Gate on
the NULL (near 40 Hz at drive 2:30, migrating to ~22–25 Hz by max), never band-RMS. (c) Then take the
level-dependent flat over-compression at −12/−6 dBFS in (7) as its own item — it is now the second-
largest OD residual and is clipper-side, not upstream. Then A4 re-grade + GATE-9, the queued `gain-n12`
HF collapse (which these rows moved), B (perf/HQ), C (carry-forwards), D (release).

#### ▶ A3 step 3b — the residual element is DESIGNED and GATED, not yet built (session 35, 2026-07-26).

**(0) FIRST: `trebleC7` was shipped for real.** See the two corrections at the head of this file — the
680 pF value existed only in prose, and the default decompose baseline was still at 100 n. Everything
below is on a regenerated baseline at the genuinely shipped default. ctest **17/17** after a full rebuild.

**(1) ⚠ A SOLVER GATE HAD SILENTLY FAILED — `a3_phase_solve --selftest` was FAILING.** Worst |Δθ| 6.02°
against a 0.5° threshold, at 20 Hz alone. **The solver was right and the test's reference was wrong.**
`model[d][b][1]` is a *difference* of two `cmath.phase` values, so it lives in (−360°, 360°] and is not a
principal value — at 20 Hz it now reads +183.02°. Magnitudes identify θ only up to sign and modulo 360,
which is exactly why `fit_band` searches [0°, 180°]; the reference had to be folded the same way.
183.02° ≡ −176.98°, and the solver returned 176.98°. Fixed via `identifiable_theta()`; self-test back to
**PASS at 0.062°** (grid resolution). ⚠ It had been latent for four sessions and only fired because
`trebleC7` rotated the model's LF phase *past anti-phase* — i.e. the fix to one thing is what exposed it.

**(2) NEW TOOL, and it removes an inference layer: `analysis/a3_lead_fit.py`.** `a3_lead_design` fits a
network to a *derived* target — it first solves (s, θ) per band, then fits a network to that point
estimate as though it were a measurement. But those solves carry wide intervals (at 127 Hz θ is
[29°, 99°]), so a candidate inside the interval but off the point estimate scores as a failure, and one
hitting the point estimate where the interval is 70° wide scores as a success. `a3_lead_fit` scores a
candidate **directly against the five raw drive captures**:

    pred_dB(b,d) = β + 20log10 | 1 + |H(b)| · μ_d(b) · e^(i(θ_mdl(b,d) + arg H(b))) |

No target, no transcription, no point estimate — and **β is just another free parameter**, which is what
"fit β jointly, never before or after" actually requires. Self-test recovers a known network and a known
β to **0.000 dB / 0.00° / 0.000 dB**.

**(3) THE RESULT (sweep_drv_−18, the level where A3 was measured).** RMS over 16 bands × 5 drives:

| candidate | rms dB | β | network | null gate |
|---|---|---|---|---|
| none (H = 1) | 2.488 | −16.90 | — | **1/5, 10.2 dB — FAIL** |
| **1 zero / 1 pole (lead)** | **0.850** | **−17.48** | **zero 6.5 Hz, pole 41.6 Hz** | **4/5, 1.1 dB — PASS** |
| 2 real zeros / 2 real poles | 0.698 | −17.47 | z 0.1/80.6, p 19.6/136.4 | 4/5, 1.0 dB — PASS |
| 3 zeros / 3 poles | 0.547 | −17.12 | Q=20 near-cancelling pair | 5/5, 1.2 dB — PASS (overfit) |
| ORACLE (per-band s, φ free) | 0.301 | | no causality constraint | — |

**⭐ THE NULL GATE PASSES — the first A3 candidate ever to do so.** Deepest band per drive
(min→max), pedal **50/50/50/40/25 Hz** at **−18/−19/−21/−32/−23 dB**; with the lead network
**50/50/50/40/32 Hz** at **−19/−20/−22/−32/−23**. The −32 dB null at drive 2:30 that has been A3's
signature since session 29 is reproduced **to the dB**. With no element the model gets the null band
wrong at 4 of 5 drives and is **10 dB too shallow** at 2:30 — so the gate genuinely discriminates; it is
not passing everything.

⚠ **The gate is run on the same data the element was fitted to**, so it is a check that the fit did not
reach low RMS by the wrong *mechanism* (which the no-element row proves it can detect), **not**
independent validation. Independent validation is the full-matrix render, which needs the element built.

**(4) ⭐⭐ AND THIS QUANTIFIES THE −12/−6 dBFS DEFECT AS A HARD FLOOR.** The ORACLE row — per-band
magnitude *and* phase free, no causality linking them — is the residual **no multiplicative linear
element on the OD path can remove, at any order**. Evaluated per level, with the −18-fitted element also
held FIXED and only β re-optimised:

| sweep | no element | −18-fitted element, FIXED | element refitted | **ORACLE floor** |
|---|---|---|---|---|
| −18 dBFS | 2.488 | 0.850 | 0.850 | **0.423** |
| −12 dBFS | 2.332 | 1.492 | 1.267 | **0.909** |
| −6 dBFS | 2.705 | 1.729 | 1.619 | **1.136** |

Two things fall out. **(a) The element is level-robust** — held fixed at its −18 values it lands within
0.11–0.23 dB of a full refit at both other levels, which is what a genuinely *linear* element must do and
is decent evidence it is real rather than absorbing a nonlinearity. **(b) The oracle floor RISES
0.42 → 0.91 → 1.14 dB.** So roughly **1 dB of the −12/−6 residual is structurally unreachable from the
OD path** — session 34 item (7) inferred that the level-dependent over-compression was clipper-side; this
puts a **number** on it and proves it, because no linear element of any order can touch it.
⇒ **Do NOT fit the element jointly across levels.** That would drag it toward absorbing a defect it
cannot fix — the same "a joint-level RMS slides the optimum" trap session 34 recorded for C7 itself.
**Fit at −18 (oracle 0.42), then CHECK at −12/−6.**

**(5) β IS NOW IDENTIFIED, AND THE SESSION-33 STANDOFF HAS CLOSED.** Joint fit gives **β = −17.1…−17.5 dB**,
consistent across every family and all three levels (−17.25/−17.49/−17.96). Independently,
`a3_lead_design`'s scan now minimises driveRMS at **β = −17.0** and puts the causality criterion at
**−17.5** — a 0.5 dB disagreement, against the **3 dB** standoff session 33 recorded (least-squares −15.5
vs causality ≤ −18.5). The model ships −16.93 dB, so the model's bleed is **~0.3–0.6 dB high** — the sign
session 29 measured directly, and small enough that it is not the story.

**(6) ⚠ THREE MORE NARRATED VERDICTS HAD GONE STALE** in `a3_lead_design.py` — the file whose own
docstring warns about exactly this, now the third occurrence. It hard-coded "driveRMS is minimised near
β = −15.5 and causality wants β ≤ −18.5; they pull opposite ways" and "shortRMS never falls below ~28°
ANYWHERE". Live: −17.0 vs −17.5 (they now *agree*), and shortRMS bottoms at **20°**. All three now
computed from the scan and flip verdict on their own.

**(7) ⭐⭐ IT IS NOT A LEAD NETWORK — IT IS ONE MORE COUPLING CAP.** The free-zero fits put the zero at
0.3/2.3/6.5 Hz depending on stimulus level, i.e. **below the 20 Hz measurement floor and not identified**,
which is the signature of a zero that is really at the ORIGIN. Asked directly — pin the zero at s and fit
only the pole — a **plain first-order high-pass** lands at:

| family | rms dB | β | fitted | null gate |
|---|---|---|---|---|
| **1st-order HIGH-PASS (one coupling cap)** | **0.912** | **−17.36** | **fc = 30.3 Hz, k = 0.996** | **4/5, 0.9 dB — PASS** |
| 2nd-order high-pass | 0.914 | −17.36 | fc 30.1 Hz + a **second pole at 0.1 Hz = inert** | 4/5, 0.9 dB |
| 1 zero / 1 pole (lead/shelf) | 0.850 | −17.48 | zero 6.5, pole 41.6 Hz | 4/5, 1.1 dB |

The high-pass is **0.06 dB** behind the free lead — comfortably inside the **0.144 dB** take-to-take
capture floor (§3) — and has the **best null-depth error of any family (0.9 dB)**. The 2nd-order variant
**degenerates to 1st order on its own** (second pole driven to the 0.1 Hz clamp), so the data wants
**exactly one** more corner, not two. And `k = 0.996`: no level change, purely a corner.

⭐ **The corner is identified far more tightly than the lead's zero ever was.** Refitted independently at
each stimulus level: **30.3 / 31.4 / 28.4 Hz — a ±5 % spread**, against the lead zero's 0.3/2.3/6.5 Hz
(20×). Held fixed at 30.3 Hz it lands within 0.11–0.13 dB of a full refit at −12 and −6. That is what a
genuinely **linear** element must do, and it is the strongest evidence yet that this is a real part.

⇒ **The residual A3 element is a first-order high-pass at ~30 Hz in the OD path — i.e. one more coupling
capacitor.** Not a shelf, not a lead network, no gain change.

**(8) `schematic-checker` ON C7 — the "smaller effective R" escape is ARITHMETICALLY CLOSED.** C7 sits
between node P (shunted by R11 470k, fed through R8 470k) and IC2_A(+) (shunted by R13 1M), and for a
series cap the corner is set by the **sum** of the shunt resistances either side — so it is ≈ **1.0–1.3 MΩ
regardless of which side R11 is on**. Consequences: **C7 = 680 pF into 1.28 MΩ = 182.8 Hz**, reproducing
the model's ~183 Hz exactly; and to reach 183 Hz with an ordinary 100 n you would need **8.70 kΩ**, which
R13 alone (1 MΩ) floors out of reach, and which would additionally be a **broadband −31 dB divider** into
IC2_A that the gain-staging calibration could not have missed. **So the 147× cannot be dissolved by
re-reading the resistors** — it is a real capacitor disagreement or a wrong placement.
- ⚠ **No dedicated pixel-zoom read of the C7 glyph is on record** (unlike C13/C33/C4/C36/R19/GRUNT) — it
  was only ever checked as a *table entry*, and per session 23 the symbol and the BOM are **one CAD
  source, not two independent voices**. The image pass is still owed: the C7 glyph (`100n` vs a
  picofarad string, and mis-attribution from C8 220 pF / C2 1n nearby), the R13 glyph (the `m`-notation
  gotcha — `1m` vs a `k` value), and junction dots on node P (the one failure mode a BOM census cannot
  catch). Crop `0.27,0.28–0.46,0.47`.
- ⚠ **circuit.md contradicts itself on R11** — the component table says "470k to GND at IC2_A input side"
  while the node graph puts R11 at node **P**. The shipped `TrebleAttack.h` follows the node graph. Does
  not change the corner (see above), but it is exactly the wording class that hid the ATTACK pole error.
- ⚠ **An arithmetic slip was propagated into five files**: "C7 at 100 n corners at ~0.1 Hz into R13".
  The correct figure is **~1.2 Hz** (1.24 Hz at 1.28 MΩ; 1.59 Hz into R13 alone) — off by ~12×. The
  conclusion is unaffected (inert in band either way) but the number was wrong in `FitParams.h`,
  `TrebleAttack.h`, `circuit.md`, this file and `CLAUDE.md`. **Corrected in all five.**

**(9) ⭐⭐ THE PIXEL-ZOOM PASS IS IN, AND IT VINDICATES C7 ON A STRUCTURAL ARGUMENT RATHER THAN A
READING.** Primary p.4 rasterised at **900 DPI** (vector source, `schematics/crop.py`, crop
`0.27,0.28–0.46,0.47`):
- **C7 = `100n`, unambiguous.** Crisp vector glyph, designator directly above and value directly below
  its own symbol — not `100p`, not mis-attributed from C8 (`220pf`) or C2 (`1n`). **R13 = `1m`**
  confirmed (the m-notation, = 1 MΩ). R11 = `470k`, C8 = `220pf`, R8 = `470k`, R7 = `200k`.
- **Topology confirmed exactly as circuit.md's node graph**, and the component table's looser wording is
  the wrong one: **R11 shunts node P (the SOURCE side of C7)**, C7 is in series, **R13 goes from
  IC2_A(+) to VD**. The C7→IC2_A(+) run carries **no intervening element and no extra junction dots** —
  it goes straight to pin 3. The ATTACK switch is also re-confirmed: **pin 2 = pole = C8's bottom
  plate**, throws to node M and GND.
⇒ **The 147× is REAL** — a genuine document-vs-captured-unit disagreement, not a misread, and with the
"smaller effective R" escape already closed arithmetically (§8) there is no reading of the schematic that
rescues 100 n.

**⭐ BUT HERE IS THE ARGUMENT THAT ACTUALLY JUSTIFIES C7, and it is not a curve-fitting one.** Re-run the
whole family fit against a model with **C7 back at the schematic 100 n**:

| | ORACLE floor | best causal element | null gate, best family |
|---|---|---|---|
| C7 = 680 pF | **0.301 dB** | 0.547 dB | **4/5 bands, 0.9 dB — PASS** |
| C7 = 100 n (schematic) | **2.212 dB** | 2.429 dB | **0/5–2/5 bands, 6.8–8.1 dB — ALL FAIL** |

The oracle floor is what **no linear element of any order** can beat. At 100 n it is **2.21 dB**, so *no
amount of added EQ anywhere in the OD path can rescue the schematic value* — and **every family fails the
null gate**, most of them putting the null at 20 Hz at every drive setting. **This is the difference
between a fudge and a fix.** C7 is upstream of IC2_A's rail clip, so its job is to restore *headroom
ahead of a nonlinearity*; a downstream linear multiplier cannot replicate that, and the oracle floor
proves it rather than asserting it. An arbitrary EQ boost would have been substitutable by definition.

**(10) THE R20/R21 ROUTE FOR THE ~30 Hz CORNER IS ARITHMETICALLY DEAD.** IC2_B's input coupling read at
900 DPI: **C15 = `2u2` (polarised electrolytic, + on the clipper side) → R20 `10k` → node X → IC2_B(+)**,
with **R21 `1m` from node X to VD**. C15 therefore works into R20 + R21 = 1.01 MΩ → **0.072 Hz**, exactly
as documented. Shrinking R21 cannot reach 30 Hz: **even R21 → 0 leaves R20's 10 kΩ, giving 7.2 Hz** — and
R21 → 0 ties the node to VD and kills the signal anyway. Reaching 30.3 Hz needs **C15 ≈ 5.2 nF against a
2.2 µF electrolytic — a 420× departure**, worse than C7's and, unlike C7, with **no structural
justification**: C15 sits *after* the clipper, so a change there is a pure linear multiplier, i.e.
precisely the substitutable "arbitrary EQ" that the oracle argument above distinguishes C7 from.
⇒ **The ~30 Hz element is characterised but has no credible physical carrier. Do NOT ship it as a C15
value.** It is worth 2.488 → 0.912 dB on the drive-axis metric, so it is real signal, not noise — but it
should be parked as a measured residual until its carrier is identified.

#### ▶ A3 step 3b, continued — C15 IMPLEMENTED AND SHIPPED (session 36, 2026-07-26). User-authorised.

> ⚠⚠ **THE VALUE IN THIS SECTION (1.5 nF) WAS REVERTED TO 5.2 nF IN SESSION 37 — see "A3 step 3c"
> below before acting on anything here.** The *stage* (`PedalChain::OdCoupling`) and everything in
> items (11)–(14) stand. What does not stand is item (15)'s value selection: the 96-row band-RMS scan
> it rests on was contaminated by the per-row gain-match reframe at HF, and its remainder came entirely
> from the GRUNT flat/boost rows, which carry the separate unfixed GAP #3b. On the gates that target
> A3 — the migrating null and the raw-capture fit — 1.5 nF is **worse than deleting the element**.

**(11) THE BLEED-SIDE HYPOTHESIS WAS TESTED, NOT JUST REASONED ABOUT, AND IT IS RULED OUT.** Before
building anything, the proposed diagnostic from session 35's handover — "does the pedal's clean tap have
its own LF rolloff, making the OD path only *appear* to need a highpass?" — was run computationally
(`a3_lead_fit.py::clean_side_test`, a per-band constant dB offset, maximally generous to the hypothesis).
It is answered by the topology itself, and the computation confirms it: the clean bleed provably does
**not** depend on DRIVE (DRIVE only touches the OD gain stage, downstream of where the clean tap splits
at IC1_A — verified directly on the model, session 34: clean column identical to 0.00e0 dB across all
five drives). A frequency-dependent correction on the BLEED side is therefore mathematically a per-band,
**drive-INDEPENDENT** dB offset — it cannot reproduce a defect that varies by drive at fixed frequency.
And the defect does vary by drive: at 40 Hz the "no element" residual is **5.64 dB**, while the best
possible bleed-side correction only reaches **5.43 dB** — essentially unchanged, because a flat-per-band
correction has no lever on the shape. At 20/50/64 Hz the story is the same (0.78→3.42 WORSE, 2.82→2.58
barely moved) while the OD-side element reaches 0.71/0.41/0.43. **Ruled out properly, not by assertion.**

**(12) THE ELEMENT WAS BUILT — `PedalChain::OdCoupling`, a new stage.** Not a value change: C15/R20/R21
were **entirely absent from the model** before this session (`clipper.process(s)` fed straight into
`recovery.process(s)`, confirmed by grep — no coupling stage of any kind, not even an inert placeholder).
Added as a single-node trapezoidal-companion first-order highpass, same convention as `C21Highpass`:
`r = R20+R21 = 1.01 MΩ` fixed (schematic-verified, and the pixel-zoom pass above closed off any
resistance-side explanation), `c` fittable via `FitParams::clipC15`. Runs at OS rate (it sits inside the
oversampled region, between `Clipper` and `RecoveryBridgedT`), unlike the base-rate `C21Highpass`. Wired
into `runOdSample()` and `runOdSampleTapped()` (extended `OdTaps` with a new `odCoupling` field — checked
both callers use named field access, so this is safe to insert mid-struct). `--fit clipC15=` added to
both `offline_render.cpp` and `a3_blend_decompose.cpp`'s key tables.

**(13) ⭐⭐ A GENUINE METHODOLOGICAL FINDING: THE DRIVE-AXIS GATE (G1/G2) IS MATHEMATICALLY BLIND TO
THIS ELEMENT, BY CONSTRUCTION — NOT A BUG.** Sweeping `clipC15` from 3.3 nF to 8.2 nF through
`a3_drive_axis_scan.sh` produced **bit-identical G1/G2 output at every value**, which first looked like a
wiring failure (it was checked: the raw OD phasors in the decompose CSVs DO differ per value — confirmed
by direct diff). The reason is structural: G1/G2 measure the **OD phasor's own step** between two drive
settings at a fixed band (`model[40]["od_db"][4] - model[40]["od_db"][3]`), and `OdCoupling` applies the
**same** complex `H(f)` at every drive (it is a plain LTI filter with no drive dependence at all) — so
`H(f)` cancels exactly out of any step/ratio between two drives at the same band. **A drive-independent
filter cannot move G1/G2, whatever its value, and this is true of any purely linear element placed
anywhere in the OD path.** This is *why* C7 could fix the drive axis and C15 structurally cannot: C7 sits
**ahead of IC2_A's own rail-clip nonlinearity**, so it changes *whether and how much* that nonlinearity
engages at each drive setting (a real drive-dependent effect on the OD magnitude), whereas C15 sits after
every nonlinearity in the chain, so nothing downstream of it can be drive-dependent by the time it acts.
**Do not read G1/G2 as a general A3 gate** — it tests one specific, structurally narrow property (OD-path
drive-axis magnitude behaviour) that only a pre-nonlinearity element can move. The null gate in
`a3_lead_fit.py` tests a different, complementary property (the TOTAL post-BLEND signal against the
pedal's own captures, which C15 *can* affect because it changes the OD magnitude relative to the
drive-varying bleed ratio inside a nonlinear `|1+...|` sum) — that is the right gate for this class of
element, and it is what C15 was actually designed and judged against.

**(14) ⚠ A METHODOLOGY BUG IN MY OWN A/B TESTING, CAUGHT BEFORE IT PROPAGATED.** The first matrix scan
compared several `clipC15` values against a report generated with **no `--fit` override at all** — but
since `FitParams::clipC15`'s *default* had already been provisionally set to 5.20e-9 (the abstract fit's
value) before this scan ran, "no override" was NOT "C15 off", it was "C15 at 5.2 nF". So a run explicitly
at `clipC15=5.2e-9` came back **bit-identical** to the "baseline" — correct, but initially alarming,
because the baseline secretly wasn't a baseline. Re-run with a genuine off condition
(`--fit clipC15=2.2e-6`, the schematic value, audibly inert at 0.072 Hz) to get a real comparison.
**Lesson: when a FitParams default has already been provisionally moved mid-session, "omit the flag" and
"disable the feature" are no longer the same thing — always pass the explicit off-value, never rely on
omission, once a default has changed.**

**(15) ⭐ THE REAL MATRIX DISAGREES WITH THE ABSTRACT FIT, AND THE REAL MATRIX WINS.** `a3_lead_fit.py`
fits ONE fixed operating point (GRUNT=Cut, BLEND=max, ATTACK=Flat, EQ flat) against 5 single-tone drive
captures and landed on fc ≈ 28–31 Hz. But scanning the ACTUAL shipped stage against the real matrix
subset (`--only drive,grunt,ref-od,level`, 96 rows spanning all three GRUNT positions and three stimulus
levels) shows a clear, bidirectionally-verified **interior minimum at a much lower capacitance**:

| C15 (nF) | off (2u2) | 0.3 | 0.7 | 1.0 | **1.5** | 2.0 | 3.0 | 4.0 | 5.2 | 6.5 | 8.0 | 10.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| band-RMS dB | 4.508 | 4.734 | 4.048 | 3.698 | **3.475** | 3.490 | 3.568 | 3.698 | 3.839 | 3.986 | 4.106 | 4.187 |

Minimum at **1.5 nF (fc ≈ 105 Hz)**, not ~30 Hz — the single-condition abstract fit does not generalise
across GRUNT positions. **Genuine interior minimum**: worse in BOTH directions (0.3 nF is worse than off
entirely — a too-high corner actively harms), not the monotone "smaller is always better" degeneracy that
would be a red flag. **Shipped at 1.5 nF, the matrix optimum, not the abstract fit's value.**

**(16) FULL 63-CAPTURE MATRIX — CONFIRMED, and the win is large.** Two full renders, `clipC15 = 1.5 nF`
(shipped) vs `clipC15 = 2.2 µF` (schematic, audibly inert), so the diff isolates C15 alone on top of the
already-shipped `trebleC7`:

| | OD | CLEAN | ALL | OD tilt |
|---|---|---|---|---|
| C15 off (schematic 2u2) | 3.926 | 0.465 | 2.195 | +1.18 |
| **C15 = 1.5 nF (shipped)** | **3.080** | **0.465** | **1.773** | **−0.72** |

**41 rows better by >0.5 dB, 18 worse, 124 bit-identical.** CLEAN is **bit-identical** (0.465 both sides)
— surgical by construction, as it must be: C15 is in the OD path and the clean tap splits at IC1_A.
Biggest improvements are exactly the captures that defined the gap: `grunt-boost` **9.09 → 1.80** at
−12 dBFS, **9.21 → 2.60** at −18, `drive-0930_grunt-boost` **8.08 → 2.07**, `drive-1700_grunt-boost`
8.41 → 3.35.

**⚠ AND THE REGRESSIONS ARE A COHERENT, ALREADY-KNOWN GROUP — read this before "fixing" them.** Splitting
the 120 OD rows (using `matrix_grade.rows_of`, which excludes the silent zero-knob captures — a naive
aggregate over raw rows hits the session-18 −640 dB trap and returns nonsense):

| OD subset | n | off | on | change |
|---|---|---|---|---|
| ALL OD rows | 120 | 4.590 | **3.763** | **−0.827** |
| **NON-`gain-n12` (the clean read)** | 104 | 4.472 | **2.925** | **−1.547** |
| `gain-n12` (known-bad group) | 16 | 5.294 | **7.114** | **+1.820** |

So C15 is a **large win (−1.55 dB) everywhere the model is otherwise sound**, and a real regression
(+1.82 dB) confined to the 16 `gain-n12` rows — **which is precisely the group with a known, separate,
unfixed defect**: session 30's "genuine level-dependent HF collapse in `ref-od_gain-n12`" and session 34's
oracle-floor result that the −12/−6 dBFS residual is **clipper-side and unreachable from the OD path at
any order**. Band-by-band on the worst row (`level-1700_gain-n12`, −6 dBFS): the change is a *constant*
−1.36 dB above ~1 kHz — exactly the per-row gain-match re-solving (the session-28 measurement-frame trap,
and `gain_db_applied` moved −1.365 dB, confirming it) — but a genuine **−14.6 dB at 20 Hz**, because the
pedal has strong LF on that capture where the plugin was *already* 12 dB deficient, and C15 cuts more.
⇒ **Adding LF cut to the OD path must make an already-LF-deficient capture worse. Do NOT chase these 16
rows with C15, and do not re-fit C15 to reduce them** — same posture as session 28's `c21R` note ("OD got
worse and that is EXPECTED — do not fix it"). They should move on their own once the clipper-side item
is addressed.

**⚠ HONEST LIMITS, unchanged from session 35's framing.** C15 at 1.5 nF against a schematic 2u2 is a
**~1470× departure** — larger than C7's 147×, and without C7's structural argument (C15 is *after* the
CD4049 clipper, so a change here is a plain linear multiplier; several other post-clipper positions could
carry an identical transfer function — this placement is a convenient carrier, not a load-bearing physical
claim). **Shipped anyway on explicit user authorisation (2026-07-26):** "if changing the C15 change will
make the plugin more accurate, lets do it, I don't care how off it is" — same posture as `clipK`/`clipC11`
(session 17). Accuracy against the captures is the standing priority for this class of element; physical
plausibility is not required once schematic-checker has closed off a documentation error (session 35) and
a genuine interior minimum rules out curve-fitting noise.

**▶ NEXT.** (a) ~~Confirm the full-matrix numbers~~ — **DONE, see (16): OD 3.926 → 3.080, ALL 2.195 →
1.773, CLEAN bit-identical.** (b) Then the −12/−6 dBFS clipper-side
over-compression item (session 34 item 7 / step-3b item 4), now bounded at roughly 1 dB of oracle-floor
residual that no linear OD-path element can touch. (c) Then A4 re-grade + GATE-9, the queued `gain-n12`
HF collapse, B (perf/HQ), C (carry-forwards), D (release).

#### ▶ A3 step 3c — the LEVEL AXIS is gated for the first time, and it says the −12/−6 item is small while `clipC15` is on the wrong value (session 37, 2026-07-26). Analysis only; nothing in `src/` changed, ctest 17/17.

The queued task was "the −12/−6 dBFS clipper-side over-compression item". It is now **measured** rather
than inferred, and the measurement re-orders the work: the genuine clipper-side part is **~0.5–1.1 dB**
(exactly session 35's oracle floor, so that bound was right), but it is **not** the "roughly
frequency-flat 1–2 dB" of session 34's description, and a **much larger** level-axis error sits at
≤80 Hz / high drive which is **not** clipper-side — it is `clipC15`, shipped last session at a value
that three independent A3 gates reject.

**(1) NEW TOOL — `analysis/a3_level_axis.py` (+ `a3_level_axis_scan.sh`). The LEVEL axis had never been
gated.** Every A3 gate so far has been a DRIVE-axis or single-level test: G1/G2 (session 34), the
migrating null (sessions 29/35), the per-level a3_lead_fit RMS (session 35). None of them asks how the
OD/bleed ratio moves with *stimulus level*, which is the axis the −12/−6 defect lives on by definition.

The derivation is β-free, which is what makes it usable while the bleed level is still disputed. Per
band the pedal's total at BLEND=max relative to its OWN full-clean capture is
`T(b,d,L) = β + 20log10|1 + m(b,d,L)·e^(iθ(b))|`, and β is a resistive divider ratio (`LevelBlend` has
no caps) with the whole post-BLEND chain shared with the reference — so β is level-independent and
**cancels exactly** in the level step `dT(b,d) = T(hot) − T(cold)`. So does the stimulus segment's own
nominal offset, because the reference is measured at the same level. No β fit, no derived target.

⚠ **GUARD, computed not assumed:** the reference capture must itself be linear across levels or its
nonlinearity leaks into every `dT`. Measured: the nominal +6 dB step is recovered at **+6.000 / +5.998 dB**
with **0.013 / 0.028 dB** of shape spread. The clean path is linear and β really is level-independent.

**(2) THE SELF-TEST EARNED ITS KEEP TWICE, on my own code.** Synthesising the pedal from the model must
return `need = 0`. It first returned **9.37 dB**: `solve_need` averaged the two levels' θ while `dT_mdl`
used each level's own θ, and near a null a fraction of a degree of phase is worth several dB. Fixed, it
then returned exactly **24.00 dB** — the "unreachable" sentinel — because `f(0)` is *exactly* zero in the
self-test and `np.sign(0) == 0` defeats a `sign[:-1]*sign[1:] < 0` crossing test. Both fixed; self-test
**PASS at 0.0000 dB**. Neither would have been visible in the real numbers.

**(3) ⭐ THE DEFECT IS NOT FREQUENCY-FLAT — it is LF and high-drive.** `dT` residual (model − pedal) rms
at the shipped state, 320 Hz excluded throughout:

| subset | −18→−12 | −12→−6 |
|---|---|---|
| drive min+9:30, ≤254 Hz (**CONTROL**) | **0.13** | **0.51** |
| drive noon, ≤254 Hz | 0.53 | 0.58 |
| drive 2:30+max, **101–254 Hz** | 0.29 | 1.07 |
| drive 2:30+max, **≤80 Hz** | **2.75** | **8.27** |
| all bands, all drives | 1.20 | 3.51 |

The CONTROL is the load-bearing row: at drive min/9:30 both devices are near-linear, so 0.13/0.51 dB is
the method's own noise floor — the instrument is clean. Against that floor, the mid-band level
dependence (noon 0.53/0.58; hot drives 101–254 Hz 0.29/1.07) is **0.5–1.1 dB and that is the genuine
clipper-side item** — it lands on session 35's oracle floor (0.42 → 0.91 → 1.14 dB per level) almost
exactly, from a completely different direction. ⇒ **Session 35's ~1 dB bound is CONFIRMED. Session 34's
description of it as "roughly frequency-flat" is not** — 87 % of the level-axis residual is below 80 Hz
at drive 2:30/max, where it is 3–8 dB.

**(4) THE CLIPPER VTC IS A REAL LEVER ON THIS AXIS (a first) BUT IT IS NOT SHIPPABLE.** Every clipper
parameter was liveness-checked first (session-16 lesson L-009) — at drive 2:30 / −6 dBFS, `clipSatLo`
2.113 dB, `clipSatHi` 1.827, `clipK` 0.717, `jfetCeilNeg` 0.507, `jfetExpandBeta` 0.639, `clipA0` 0.683
of max |Δ(OD)|. Scaling the fitted ceiling pair (`clipSatLo` 2.0067 / `clipSatHi` 2.9321) together:

| scale | CONTROL | noon ≤254 | hot ≤80 | hot 101–254 | ALL |
|---|---|---|---|---|---|
| 0.55 | 0.10 / 0.32 | 0.15 / 0.68 | 2.11 / 7.38 | 0.79 / 1.84 | 0.95 / 3.18 |
| 0.70 | 0.12 / 0.37 | 0.26 / 0.55 | **1.64** / 7.72 | 0.44 / 1.56 | **0.73** / 3.30 |
| 0.80 | 0.12 / 0.42 | 0.40 / **0.52** | 1.90 / 7.89 | 0.28 / 1.46 | 0.83 / 3.36 |
| 0.90 | 0.13 / 0.47 | 0.49 / 0.53 | 2.31 / 8.06 | **0.28** / 1.18 | 1.00 / 3.42 |
| **1.00 (shipped)** | 0.13 / 0.51 | 0.53 / 0.58 | 2.75 / 8.27 | 0.29 / 1.07 | 1.20 / 3.51 |
| 1.15 | 0.13 / 0.54 | 0.55 / 0.67 | 3.47 / 8.66 | 0.41 / 0.98 | 1.49 / 3.67 |
| 1.35 | 0.13 / 0.53 | 0.54 / 0.78 | 4.42 / 9.22 | 0.60 / 0.94 | 1.89 / 3.90 |

Direction: **lower ceilings** (≈0.7–0.9×), i.e. the clipper is not driven hard enough relative to where
it clips. Several subsets show genuine **interior minima** there (noon at −12→−6 bottoms at 0.80;
hot ≤80 and ALL at −18→−12 bottom at 0.70; hot 101–254 at −18→−12 at 0.80–0.90) — so this is not purely
the "make the clipper see less" degeneracy that killed the session-5/6 fits. **But two rows are
monotone and they disagree with each other**: the CONTROL improves all the way down to 0.55 (the
degeneracy signature), and `hot 101–254` at −12→−6 improves monotonically in the *opposite* direction
(1.84 at 0.55 → 0.94 at 1.35). A parameter that trades one region against another is not a fix for a
single defect. ⛔ **Not shipped, and do not ship it on a scalar.** Note also that with `kInputRef` fixed,
scaling the ceilings down is *approximately* the session-16/17 degenerate partner of driving the input
hotter (not exactly — the JFET is upstream and also nonlinear), so the honest next step is a **joint
re-fit of that family**, not a one-parameter scan.

**(5) ⚠⚠ A DEFECT IN THE ACCEPTANCE TOOL: `a3_lead_fit.py`'s row labelled `none (H = 1)` WAS NOT H = 1.**
For the empty family `unpack` still returned a free log-gain, so the "no element baseline" every
session has quoted was really **the model plus a fitted broadband OD gain** — at the shipped state it
comes back **k = 1.898 (+5.6 dB)**. Consequences: (a) the elements' improvements were *understated*, not
overstated, because the baseline was stronger than advertised; (b) the null-gate row under that label was
never the shipped model's null; (c) it **hid a finding**. Fixed with a `fix_k` flag, and a separate
"broadband OD gain only (H = k)" row added so the two questions stay apart. Self-test still PASS.

**(6) ⭐⭐ AND THE HIDDEN FINDING IS THE HEADLINE: ON ITS OWN TOOL, THE SHIPPED `clipC15 = 1.5 nF` IS
WORSE THAN HAVING NO ELEMENT AT ALL.** True no-element rms against the five raw drive captures
(sweep_drv_−18), now that k really is 1:

| `clipC15` | **true no-element rms (H = 1)** | β | k the free-gain row wants |
|---|---|---|---|
| off — schematic 2u2 | 2.846 | −18.03 | 0.651 |
| **5.2 nF (session 35's fitted value)** | **0.904** | **−17.38** | **0.995** |
| 1.5 nF (**SHIPPED**) | **3.339** | −16.20 | **1.898** |

At 5.2 nF the model explains the raw captures to **0.904 dB with nothing added and k = 0.995** — it wants
no level correction at all — and β lands at −17.38, 0.45 dB from the model's own −16.93, which is the
figure session 35 reported. At 1.5 nF the same metric reads **3.339 dB**, *worse than deleting the
element*, and the fit asks for **+5.6 dB** of broadband OD gain to patch it. (5.2 nF into the
schematic-verified R20+R21 = 1.01 MΩ is fc = 30.3 Hz — i.e. 5.2 nF **is** session 35's fitted element,
which scored 0.912 dB. The two tools agree to 0.008 dB.)
⚠ **This also qualifies session 35's item (5).** "β = −17.1…−17.5, consistent across every family" was
consistent among *free-k* fits, which all share the same k↔β trade; with k pinned, β moves to −16.20 at
1.5 nF. β is only well-identified at ≈5.2 nF.

**(7) THE NULL GATE, EXTENDED TO ALL THREE STIMULUS LEVELS, AGREES — and it has a genuine interior
optimum.** Deepest band ≤254 Hz, model vs pedal, over 3 levels × 5 drives (15 cells):

| `clipC15` | off | 1.5 nF (shipped) | 3.0 nF | 5.2 nF | 8.0 nF |
|---|---|---|---|---|---|
| null band matches | **0/15** | **0/15** | **12/15** | **12/15** | 5/15 |

At 1.5 nF the model's null sits a full band HIGH at every drive and level (64 Hz where the pedal has 50;
50 Hz where the pedal has 25–32 at max drive). Worse in **both** directions from ~3–5 nF, so this is a
real optimum, not a monotone slide. ⚠ **Read with the caveat that null placement also moves with OD
LEVEL** — with a free k, 1.5 nF's null improves to 2/5 at −18 — so the null criterion alone can be
gamed by a level error; that is exactly why it is quoted here alongside (6), which fixes k.

**(8) ⚠⚠ SO WHY DID SESSION 36's SCAN PICK 1.5 nF? TWO REASONS, BOTH ALREADY DOCUMENTED TRAPS.**

**(a) The per-row gain-match reframe (session 28's trap, session 30 §3's caveat).** In the raw report the
HF band (320 Hz–12.9 kHz, **15 of the 26 graded bands**) appears to *strongly* prefer 1.5 nF —
2.794 → 3.823 dB across 1.5 → 10 nF. But a first-order corner at 105 Hz vs 30 Hz is indistinguishable
above 320 Hz. Re-anchoring the gain match to those bands only (session 30 item 2's method) collapses the
whole effect: **HF band-RMS is FLAT at 2.579 → 2.597 dB across every C15 value tested.** It was the
broadband scalar re-solving, and because HF carries most of the graded bands it dominated the aggregate
that selected the value. Re-anchored, the GRADE optimum is not a sharp 1.5 nF minimum but a flat plateau
(2.0 nF 3.349, 1.5 nF 3.367, 3.0 nF 3.377).

**(b) ⭐ The residual preference is entirely the GRUNT flat/boost rows — a known, separate, unfixed
defect.** LF 25–80 Hz band-RMS on OD rows, gain match re-anchored to HF, split by GRUNT position:

| `clipC15` | GRUNT **cut** (68 rows) | GRUNT flat (12) | GRUNT boost (16) |
|---|---|---|---|
| off (2u2) | 4.378 | 9.759 | 12.670 |
| **1.5 nF (shipped)** | **5.083 ← worst tested** | **2.911** | **4.380** |
| 2.0 nF | 4.634 | 4.260 | 5.263 |
| 3.0 nF | 4.060 | 5.437 | 6.851 |
| 4.0 nF | **3.835** | 6.416 | 8.340 |
| 5.2 nF | **3.839** | 7.335 | 9.427 |
| 8.0 nF | 4.041 | 8.924 | 10.760 |
| 10.0 nF | 4.137 | 8.923 | 11.284 |

The two groups want **opposite** values. At GRUNT **cut** — the condition A3 is defined at, and the
condition whose GRUNT topology the model gets right — LF band-RMS has an interior minimum at **4–5.2 nF**
and **1.5 nF is the worst value tested, worse even than deleting the element.** The monotone preference
for 1.5 nF comes only from GRUNT flat/boost, and **that is precisely GAP #3b**: session 23 measured the
pedal's GRUNT span as a **bump centred 127–202 Hz** against the model's **monotone high-pass shelf
maximal at DC**, and recorded that *"a first-order coupling cap can only move a shelf's corner — it can
never turn a shelf into a bump"*. `clipC15 = 1.5 nF` is a first-order coupling cap being used to
attenuate that shelf. ⇒ **it is a compensating error for an unfixed defect, selected by letting the
defective row group vote.** Session 36 applied exactly this reasoning to exclude the 16 `gain-n12` rows
and did not apply it to the 28 GRUNT flat/boost rows.

**(9) ✅ SHIPPED (user decision 2026-07-27): `clipC15` 1.5 nF → 5.2 nF (fc ≈ 30.3 Hz), on the standing
rule that the NULL and the raw-capture fit are the gate and matrix band-RMS is corroboration.** Evidence for, all
independent: raw-capture fit **0.904 dB with k = 0.995** vs 3.339 dB / +5.6 dB at 1.5 nF (6); null band
**12/15 vs 0/15** (7); β identified at −17.38, matching the model's own bleed to 0.45 dB (6); GRUNT-cut
LF band-RMS at its interior minimum (8b). **Expect the GRUNT flat/boost rows and the matrix aggregate to
get WORSE, and do not fix that with C15** — same posture as session 28's `c21R` ("OD got worse and that
is EXPECTED") and session 36's own `gain-n12` note.
⚠ Both values are wild departures from the schematic 2u2 (**423×** at 5.2 nF, 1470× at 1.5 nF), so this
does not change the provenance story or the user authorisation of 2026-07-26 at all — it is purely a
question of which value is more accurate.

**(10) ⭐ THE FULL 63-CAPTURE MATRIX MEASURES THE TRADE EXACTLY, AND IT SPLITS ON GRUNT AS PREDICTED.**
Full render at `clipC15 = 5.2e-9` vs the shipped 1.5 nF (`s37_full_c15_5p2n.json` vs `s36_full_c15on.json`):

| OD group | rows | 1.5 nF (shipped) | 5.2 nF | change |
|---|---|---|---|---|
| **GRUNT cut** | 76 | 2.478 | **2.284** | **−0.194** |
| **GRUNT cut, `gain-n12`** | 16 | 6.837 | **5.843** | **−0.994** |
| GRUNT flat | 12 | 2.191 | 4.055 | +1.864 |
| GRUNT boost | 16 | 2.850 | 5.449 | +2.599 |
| **ALL OD** | 120 | **3.080** | 3.357 | +0.277 |
| CLEAN | 120 | 0.465 | 0.465 | bit-identical |
| **OD tilt** | | **−0.72** | **−0.11** | closer to 0 |

24 rows better by >0.5 dB, 30 worse, 124 bit-identical. So **92 of the 120 OD rows improve and only the
28 GRUNT flat/boost rows regress** — precisely the split (8b) predicts. The aggregate moves the other way
(+0.277) *because* those 28 rows regress hard, which is the arithmetic of letting them vote.
⭐⭐ **And note what happens to the 16 `gain-n12` rows: 6.837 → 5.843 (−0.994).** Session 36 recorded
their +1.82 dB regression as "confined to the known-bad group... they should move on their own once the
clipper-side item is addressed". They move on their own once **`clipC15`** is corrected — no clipper
change involved. That is direct evidence the `gain-n12` regression session 36 attributed to the pending
clipper item was substantially caused by `clipC15 = 1.5 nF` itself.
⭐ The `od_tilt_metric` — A3's signature since session 20, target 0 — goes **−0.72 → −0.11**.

**(11) ✅ SHIPPED AND VERIFIED AT THE SHIPPED STATE.** `FitParams::clipC15 = 5.2e-9`. Value picked on
the raw-capture fit's own **interior minimum, verified both sides**: 4.0 nF 1.115 / 4.7 nF 0.979 /
**5.2 nF 0.904** / 6.0 nF 1.022 dB, with the free-gain row wanting `k = 0.995` at the minimum. ctest
**17/17**. Level-axis gate re-run against the shipped default:

| | before (1.5 nF) | **after (5.2 nF)** |
|---|---|---|
| null band matches (3 levels × 5 drives) | 0/15 | **12/15** |
| dT residual, all bands (−18→−12 / −12→−6) | 1.20 / 3.51 | **1.00 / 2.14** |
| dT residual, hot drives ≤80 Hz | 2.75 / 8.27 | **2.23 / 4.97** |
| dT residual, noon ≤254 Hz | 0.53 / 0.58 | **0.49 / 0.36** |
| dT residual, CONTROL (min+9:30) | 0.13 / 0.51 | 0.13 / 0.47 |

⚠ **AND THE VERIFICATION CAUGHT A STALE BINARY — the session-35 trap in a new guise.** After the edit,
`OfflineRender --print-fit` correctly reported `fit.clipC15=5.2e-09`, but `a3_blend_decompose` still
rendered 1.5 nF: it is built by a hand-written `c++` command, **not by CMake**, so `cmake --build` does
not rebuild it when `FitParams.h` changes. Every phase tool reads its CSVs. **Check: a render at the
default must be bit-identical to one at the explicit new value AND differ from the old one** — both
directions, because "identical to the new value" alone also passes if nothing was rebuilt and the two
values happen to be compared against each other. Rebuilt, re-verified both ways, and
`build/a3_dec_drv*.csv` + `build/a3_lvl*.csv` + `analysis/reports/comprehensive_data.json` were all
regenerated at the shipped state (session 35's stale-baseline trap).

**⚠ METHOD NOTES.**
- **My own scan lost a run to a quoting bug, and the session-36 lesson caught it.** Eight clipper
  candidates came back **bit-identical**, having just been liveness-checked as live. Cause: `set -- $spec`
  in a zsh loop — **zsh does not word-split unquoted parameter expansions**, so the whole string became
  the tag and *no* `key=value` reached the tool, silently re-rendering the shipped defaults under each
  candidate's name. `a3_level_axis_scan.sh` now **refuses to run with zero overrides** and rejects any
  argument that is not `key=value`. A bit-identical A/B must be a measurement, never an accident.
- **"Verify the constant, not the prose" now has a sibling: verify the BASELINE, not its label.** (5) is
  the same class as session 35's `trebleC7` catch — a row everyone reads as the baseline was not the
  baseline, for four sessions, and the mislabel concealed a 5.6 dB level finding.
- **Below 80 Hz at high drive, neither `dT` nor the null argmin is a reliable ranker on its own.** Both
  are cliff-dominated there: `dT` moves non-monotonically across C15 (off 3.73 → 8.0 nF 3.84 → 5.2 nF
  4.97 → 3.0 nF 7.75 → 1.5 nF 8.27 at −12→−6) in an order that does not track the null match, and the
  argmin is a coarse 1/3-octave statistic. Rank on (6), cross-check with (7) and (8b).

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

**▶▶ USER AUTHORIZATION (2026-07-26, superseding the "do not fit it away" line above): the user has
explicitly authorized per-knob/per-switch-position fitting to close the remaining gap further** — the
same posture already used for `clipK`/`clipC11` (dsp.md "fit the corner"; user-authorised departures
from a schematic-plausible shared element when the capture disagrees). This unlocks exactly the
per-position free-fit family that was rejected above on principle (C32/C34 and/or R40/R41 varying
*per switch position*, not shared across a band) — it reaches 0.17–0.44 dB per position, so it is a
live candidate now, not a dead end. **Not yet implemented.** See the session-27 handover for the
concrete next step. A2c-2's peak-frequency numbers (3.1 % mean / 8.7 % worst) should tighten further
as a side effect of the same per-position fit, bounded by the ~6.1 % measurement floor established
above (do not chase past it).

#### ✅✅ A2c-3 — the mid selector is a 2-POLE SWITCHED CAP PAIR. A2c CLOSED; the target is MET (session 27, 2026-07-26).

**Shipped:** the across-lug cap is switched together with the series cap, at a fixed ratio
`C32 = 10 × C33` — new `FitParams::midCapRatioLo/Hi` (both **10.0**) and `MidBand::setAcrossCap()`,
applied in `PedalChain::applyParams()` alongside the existing `setSeriesCap()`. With that in place
the switched-cap table and the wiper R were re-fitted:

| | 250 / 750 Hz | 500 / 1.5k | 1k / 3k |
|---|---|---|---|
| LO-MID series C33 | 15n → **6n8** | 6n8 → **3n9** | 1n8 → **2n2** |
| LO-MID across C32 | 22n → **68n** | 22n → **39n** | 22n → **22n** |
| HI-MID series C35 | 10n → **2n7** | 2n7 → **1n5** | 680p → **680p** |
| HI-MID across C34 | 6n8 → **27n** | 6n8 → **15n** | 6n8 → **6n8** |

and `midWiperRLo` 22k → **6k8**, `midWiperRHi` 18k → **6k8** (now the same value in both bands).
ctest **17/17** (new `MidBandTest` Test 6), AU + VST3 clean.

**⭐ THE HEADLINE: A2c's agreed target is met, and the seven failing captures are gone.** Per clean
capture over the agreed 30 Hz–10 kHz band: **mean 0.955 → 0.485 dB** (target ≤ 0.7) and **23/30 →
30/30 captures ≤ 1.5 dB** (target: none over 1.5), **worst 3.54 → 1.01 dB**. Over the full graded
band the same numbers are 1.023 → 0.544, 23/30 → 30/30, worst 3.365 → 1.069. Every one of the seven
mid-extreme captures A2c-2 recorded as unreachable now sits **below 1.0 dB**; the worst clean capture
in the set is no longer a mid capture at all (`treble-1700`, 1.01 dB).

Full matrix, 63 captures / 240 rows: **CLEAN 1.023 → 0.544**, **ALL 3.494 → 3.254**, **OD 5.965
unchanged**. **32 rows better by > 0.5 dB, 0 worse**; 102 rows bit-identical. The OD half was checked
strictly rather than assumed: over all 128 OD rows the largest change in plugin dB at any band is
**4.5e-11 dB** (float noise) — surgical by construction, the mids sit post-BLEND and are flat in
every OD capture.

**⚠ A2c-2's headline numbers were flattered by a broken anchor, and this is the honest baseline.**
`mid_shape_verify.py` subtracted each curve's value at a fixed 5.12 kHz band. That band sits inside
the HI-MID positions' own skirts, so those rows were displaced wholesale — HI-MID 3k reported a
"peak" at 101 Hz for pedal and plugin alike (hence a flattering 0.0 % error that diluted the mean),
and HI-MID 750's curve RMS read 1.77/2.16 dB when it was really 4.08/4.61. Fixed to a peak-relative
baseline (median of the bands ≥ 2 octaves from the peak). Re-measured, the **session-26 build** reads
**2.357 dB mean curve RMS / 4.4 % peak error**, not the 1.819 / 3.1 % recorded. All A2c-3 numbers
below are under the corrected metric, on both sides.

| metric (12 curves = 6 positions × both knob extremes) | A2c-2 | A2c-3 |
|---|---|---|
| stage-curve RMS, mean / worst | 2.357 / 4.614 dB | **0.587 / 0.869 dB** |
| bandwidth ratio plugin/pedal, mean / worst | 1.30× / 1.74× | **0.99× / 1.05×** |
| peak GAIN error, worst | +3.4 / −2.4 dB | **+1.6 / −0.1 dB** |
| peak FREQUENCY error vs the pedal's own centre, mean | 3.4 % | 6.4 % *(see below)* |

**The width error is gone — 1.30× → 0.99×** — and with it the range error (peak gain now within
+1.6/−0.1 dB at every position, against ±2.4–3.4 dB before). That is the whole of what A2c-2 declared
structurally unreachable.

**HOW: not a per-position fudge in the end.** The user's authorisation unlocked a per-position free
fit, and running it is what produced the answer — but the answer turned out not to need per-position
freedom. Fitting C32 freely at each of the six positions lands at a **near-constant C32/C33 ratio in
both bands** (per-band joint refit: 10.4 and 9.4), i.e. one 2-pole selector swapping a scaled PAIR.
Constraining it that way costs essentially nothing against the unconstrained ceiling:

| family (oracle RMS, per band) | LO-MID | HI-MID |
|---|---|---|
| F0 A2c-2 shipped (per-position C33, one Rw) | 0.890 | 0.893 |
| F1 + per-position Rw | 0.694 | 0.707 |
| F2 + per-position C32 | 0.397 | 0.301 |
| F3 per-position C33 + C32 + Rw (the ceiling) | 0.302 | 0.244 |
| F4 F3 + per-position R40/R41 | 0.301 | 0.236 |
| **F5 cap PAIR: free ratio, one Rw per band** | **0.309** | **0.250** |
| F5 with ratio pinned 10.0 **and Rw pinned 6k8 in both bands** | 0.311 | 0.260 |

So the shipped model has **one more free parameter per band** than A2c-2 did, not six, and it reaches
the fully-unconstrained per-position ceiling to within 0.01 dB. Note F1: per-position Rw *alone* only
gets to 0.69/0.71 — the across-lug cap is the element that matters, and A2c-2 was right that Rw
cannot do this job.

**⭐ WHY A FIXED RATIO IS THE RIGHT CONSTRAINT, structurally.** The leg admittances depend only on the
products `s·C`, so scaling every cap by k with the resistors fixed gives **exactly the same curve
translated in frequency by 1/k**. A fixed ratio therefore makes Q — and hence boost/cut range —
identical at every switch position, with the switch moving only the centre. That is precisely what
the captures say the pedal does (~±12 dB at every position, the observation GAP #4 introduced a
damping R to force by other means), and it is circuit.md's own parked constant-Q alternative for this
stage. `MidBandTest` Test 6 asserts the identity directly (LO-MID 250 at f = HI-MID 3k at 10f, to
0.024 dB at 384 kHz — residual is bilinear warp, 1e-5 dB at 20 Hz rising monotonically with the
shifted frequency).

**⭐ CORROBORATION THE OBJECTIVE COULD NOT SEE.** At ratio 10 the highest-frequency position of each
band lands on that band's **documented pair**: LO-MID 1 kHz = C33 **2n2** / C32 **22n** (22n is
schematic-verified; 2n2 is the [ENG] table's own value) and HI-MID 3 kHz = C35 **680p** / C34 **6n8**
(both schematic-verified — the stock board's fixed HI-MID pair, itself a ratio of exactly 10). The
fitted model reads as *"the stock network IS one switch position, and the other two scale that same
pair up."* Nothing in the objective knew those values. **Calibrate it honestly, twice over:** the raw
optimum sits ~7 % from each documented value and it is E12 rounding that lands it exactly, and E12
quantisation gives any single hit a prior of roughly a fifth to a third. Two hits out of two possible,
at the position you would design around, is suggestive — not proof. It is nonetheless the only
independent evidence this gap has ever produced, and it is what distinguishes A2c-3 from the
per-position fudge A2c-2 rejected (C32 at 26.8n/31.9n/7.2n with R40/R41 at 3.5–9.6×, corresponding to
nothing).

**Acceptance checks, all run before shipping.**
* **Ratio — sharp interior minimum.** At the shipped cap set with Rw held: `1: 6.07 | 2: 4.85 |
  4: 2.98 | 6: 1.69 | 8: 0.79 | 10: 0.51 | 12: 0.89 | 15: 1.50 | 20: 2.25 | 30: 3.10` dB. Refitting
  Rw at each ratio gives the same answer (`8: 0.316 | 9: 0.301 | 10: 0.298 | 11: 0.304 | 12: 0.317`),
  so it is not an artefact of holding Rw fixed.
* **Rw — interior minimum, and much smaller than before.** At the shipped caps: `0k: 0.584 |
  2.2k: 0.539 | 4.7k: 0.509 | 6.8k: 0.500 | 10k: 0.515 | 15k: 0.587 | 22k: 0.737 | 33k: 0.997` dB
  (63 Hz–8 kHz; on 100 Hz–4.1 kHz 4.7k and 6.8k tie at 0.500/0.509). Once the pair carries the range,
  Rw drops 22k/18k → 6k8 and stops being the band's Q control.
* **Every cap — interior minimum on the E12 grid**, neighbours worse on both sides (e.g. LO-MID 250
  `4.7n 2.17 | 5.6n 1.05 | 6.8n 0.59 | 8.2n 1.67 | 10n 2.85`). Full table in `FitParams.h`.
  None of these is the monotone "make it see less" degeneracy that killed the session-5/6 clipper
  fits and the GAP #3b C13 candidate.
* **Not bought at mid-travel.** Unlike A2c-2, the objective uses every captured knob point, so the
  two default positions (which have 0930/1430 captures as well as the extremes) are fitted on four
  curves, not two — the GAP #4 pot-law lesson applied per position.
* **Positions stay differentiated** (cap ratios 1.74×/1.77× and 1.80×/2.21×), so this is not the
  session-22 collapse.

**⚠ ONE METRIC MOVED THE WRONG WAY, and it is E12 quantisation.** Peak-frequency error against the
pedal's own centre (the geometric mean of its cut and boost readings) went **3.4 % → 6.4 %**, against
a pedal-repeatability floor of **3.0 %**. This is not measurement noise and should not be waved away:
under this model `f ∝ 1/C` exactly, so an E12 step (~20 %) maps straight onto ~10 % of centre
frequency, and every one of the six errors matches its own cap's E12 rounding to within 1 % (raw
optimum → shipped: 6.45n→6n8 = −5.2 % predicted vs −5.1 % measured; 4.12n→3n9 = +5.8 % vs +6.6 %;
2.05n→2n2 = −6.7 % vs −6.2 %; 2.87n→2n7 = +6.2 % vs +6.0 %; 1.39n→1n5 = −7.7 % vs −6.6 %;
0.736n→680p = +8.2 % vs +7.7 %). Shipping the raw fitted values removes it.

**The raw alternative was rendered and measured, not estimated** (`--fit` overrides over the 16 mid
captures, no rebuild): raw caps give **mid-capture mean 0.557 → 0.458 dB, worst 0.957 → 0.819**, i.e.
about **0.05 dB** on the whole clean-set mean (0.485 → ~0.43). Twelve of the sixteen improve, four
regress slightly (worst `himidfreq-3k_himid-0700` +0.22). **E12 was shipped anyway, deliberately**:
the E12 set already meets the agreed target with margin, E12 is what makes this a buildable switch
rather than four significant figures of curve-fitting, and the documented-pair corroboration — the
only independent evidence this gap has ever produced — exists only in the rounded set. Trading that
for 0.05 dB would be a bad deal. **If a future session wants the last of it the lever is exact and
its cost is measured: `--fit midLoCap250=6.446e-9 midLoCap500=4.120e-9 midLoCap1k=2.046e-9
midHiCap750=2.868e-9 midHiCap1500=1.385e-9 midHiCap3k=0.736e-9 midWiperRLo=6590 midWiperRHi=6590`.**

**A2c IS CLOSED.** The floor A2c-2 recorded (~1.0 dB mean / ~3.3 dB worst, "reopening needs new
evidence about the switch's real topology, not another fit") was correct in its diagnosis and is now
superseded by exactly that evidence. Remaining known limits, unchanged: the pedal's own cut-vs-boost
peak-frequency spread (3.0 % mean against the geometric-mean centre, 7.7 % at HI-MID 3k) and knob
pointer error worth > 1 dB on a ±28 dB range.

**Tools:** `analysis/mid_perpos_fit.py` (the per-position / cap-pair family comparison, with
interior-minimum scans); `analysis/mid_shape_verify.py` (acceptance — now with the corrected
peak-relative baseline; **use this, not a band-grid argmax, for any peaking-stage claim**).

### ✅ A2d — the sub-60 Hz clean deficit. FIXED + shipped (session 28, 2026-07-26). User-reported.

**The report.** User A/B'd the clean captures and flagged three things: (1) below ~40–60 Hz the
plugin is uniformly quieter than the pedal, "critical for a bass plugin"; (2) divergence above
10 kHz; (3) a small ±0.2 dB shape. All three are real. (1) is fixed here; (2) and (3) are
quantified below and left open.

**⭐ THE CONTROL THAT SETTLES IT IS `bypass.wav`.** It round-trips at **−0.03 dB at every band
20–63.5 Hz**, so the LF deficit is NOT the capture chain — it is the plugin. (A capture-chain
rolloff would also push the error the *other* way: it lands in `pedal_db`, making
plugin−pedal more POSITIVE. We measure negative.) Use this anchor before attributing any band-edge
error to the rig.

Flat-EQ clean residual, bypass-corrected (plugin − pedal, minus the bypass chain):

| Hz | 20 | 25 | 31.7 | 40 | 50 | 63.5 | 80 |
|---|---|---|---|---|---|---|---|
| dB | **−1.31** | −1.13 | −0.75 | −0.38 | −0.15 | 0.00 | +0.09 |

Identical across all 30 clean captures (tight min/max spread), which places it in the SHARED
post-BLEND path — and **C21 is the only audible-band highpass there** (100n against `c21R`,
15.9 Hz). Everything else in the clean path corners at ≤1.6 Hz (InputBuffer 1.59, MasterOut
0.72 ×2). This is the same element session 18 moved 10k → 100k; that fix was real but incomplete.

**SHIPPED: `c21R` 100k → 220k** (corner 15.9 → 7.2 Hz). **Interior minimum, verified on both
sides** — not the monotone "delete the element" degeneracy that killed the session-5/6 clipper fits
and the GAP #3b `clipC13` candidate:

| c21R | 100k | 150k | 180k | **220k** | 270k | 330k | 470k |
|---|---|---|---|---|---|---|---|
| corner Hz | 15.9 | 10.6 | 8.8 | **7.2** | 5.9 | 4.8 | 3.4 |
| ≤63 Hz RMS | 0.849 | 0.421 | 0.319 | **0.261** | 0.248 | 0.260 | 0.287 |
| 20 Hz–10 kHz | 0.471 | 0.316 | 0.292 | **0.283** | 0.284 | 0.288 | 0.295 |
| Δ @ 20 Hz | −1.28 | −0.43 | −0.20 | **−0.02** | +0.11 | +0.19 | +0.27 |

220k minimises 20 Hz–10 kHz, lands the 20 Hz band dead on (−1.28 → −0.02 dB), and is within
0.001 dB of optimum on the agreed 30 Hz–10 kHz band (where the curve is nearly flat 150k–270k, so
that band could not have chosen this value — see the band note below).

**Result, per clean capture (30 captures, the session-24 unit):**

| band | mean | worst |
|---|---|---|
| 30 Hz–10 kHz (agreed) | 0.465 → **0.416** | 1.043 → 1.015 |
| 20 Hz–10 kHz | 0.589 → **0.415** | 1.101 → 0.985 |

Row-counted: **CLEAN 0.544 → 0.465**. 22 of 30 captures improve, 7 move by <0.06 dB.

**⚠ THE OD HALF GETS WORSE, AND THAT IS EXPECTED — READ THIS BEFORE "FIXING" IT.**
**OD 5.965 → 6.221, ALL 3.254 → 3.343; 28 rows worse by >0.5 dB, 0 better** (worst
`drive-0700_grunt-boost` drv−12 +1.21). C21 is in the SHARED post-BLEND path, and A3 is an OD LF
**excess** (+12.8 dB at 40 Hz), so adding low end necessarily worsens it. Decomposed per band, the
OD move is two things and **neither is a new error**:
* **Below 50 Hz — genuine unmasking.** +0.93 dB at 20 Hz, +0.47 at 31.7, +0.19 at 40. At 100k the
  shared clean-path deficit was partially CANCELLING A3's OD excess. That compensating-error pair
  is exactly what session 24's "nail base-clean first, a clean-path error is a confound sitting
  under every OD comparison" was meant to expose. A3's true size is now visible, not larger.
* **Above 63 Hz — a constant −0.33 dB at EVERY band, right out to 16 kHz.** That is the report's
  per-row **gain-match** re-solving: adding LF energy shifts the broadband null, pushing every other
  band down together. It is a measurement-frame shift, not a voicing change (same warning as
  session 23's `grunt_span_probe` note — the per-capture `gain_db_applied` leaks into any naive
  cross-report band diff).
⇒ **Do not tune `c21R` against the OD or ALL aggregate.** Those numbers are dominated by A3, and
A3's fix must REMOVE 13–15 dB of LF from the OD path, at which point this +0.26 dB reverses.
Judge `c21R` on the CLEAN set against the `bypass.wav` anchor, as above.

**⚠ TWO CAVEATS — do not read this as "found the real circuit".**
* The implied corner is **not constant** across the LF bands (9.1 / 7.1 / 7.3 / 9.8 Hz at
  20 / 25 / 31.7 / 40 Hz), so this is a corner APPROXIMATION; a purely first-order mismatch would
  give one number. The +0.20 dB low-mid tilt below contaminates the solve above ~50 Hz.
* 220k is **22× the nominal ~10k stack input Z**. The physical story for C21 is thin — same posture
  as 10k → 100k, and the same third branch as R36 / C13 / the `[ENG]` mid caps: our schematic is a
  clone of the ORIGINAL B7K, the captured unit is an Ultra. Behavioural match to the unit we
  recorded. C21's schematic value/placement is **still** worth a `schematic-checker` pass.

**⚠ ONE CAPTURE REGRESSES MONOTONICALLY with c21R: `bass-0930` (BASS cut) 0.424 → 0.554 dB.** It is
already +1.0 dB *relative* at 40 Hz before this change — the Baxandall BASS **cut** is ~1 dB too
shallow there. Separate, smaller gap. **Do not fix it with `c21R`.**

**▶ THE GRADING BAND SHOULD BE RE-AGREED.** The entire deficit lives at 20–31.7 Hz, and the agreed
band starts at 30 Hz — which is precisely why this survived A2c being declared closed on target. On
the 30 Hz–10 kHz band the scan is nearly flat from 150k–270k; only the 20 Hz–10 kHz band resolves
the optimum. For a bass DI (5-string low B = 30.9 Hz) the low edge should arguably be 20 Hz. Settle
this before A4 writes the GATE-9 numbers.

### ▶ A2e — >10 kHz divergence. QUANTIFIED, NOT FIXED (session 28). Two separate things.

**Bilinear warp is RULED OUT — measured, not assumed.** `analysis/base_rate_warp_measure.py` renders
the clean path at 48k and at 96k: droop is **+0.13 / +0.13 / +0.02 / −0.01 / +0.11 / −0.05 dB** at
6/8/10/12.5/14.5/16 kHz — no systematic trend. **This closes the standing Phase-6 carry-forward**
("the EQ's audible-band HF caps warp at base rate, ~0.3 dB @10 kHz") *for the clean path at flat
EQ*: at flat EQ the Baxandall is a ratio and the warp cancels, the mids at noon are exactly flat,
and MasterOut has no audible-band caps.

**(a) Flat EQ — small, near the floor.** Bypass-corrected: **−0.29 dB at 10 kHz, −0.31 at 12.9 k,
−0.38 at 16 k**. Against a 0.144 dB take-to-take floor this is systematic but minor.

**(b) Mid boost/cut extremes — this is the real story, and it is the MID SKIRT.** Using the
matched-pair boost-minus-cut SPAN (the whole rest of the chain cancels), the error is ~0 at LF where
it must be, and grows monotonically above each position's centre:

| position | span error @16 kHz | LF plateau |
|---|---|---|
| LO-MID 250 | −0.66 dB | +0.01 |
| LO-MID 500 | −1.05 | ~0 |
| HI-MID 750 | −1.37 | −0.08 |
| HI-MID 1.5k | −3.17 | ~0 |
| HI-MID 3k | **−6.03** | −0.07 |

i.e. **the plugin's mid peaks have steeper HF skirts than the pedal's** — the pedal's mid controls
retain measurably more authority above 10 kHz. Worst single capture:
`himidfreq-3k_himid-1700` −3.14 dB at 16 kHz.

**⛔ RULED OUT: the wiper-leg R is NOT the lever.** Checked against the oracle
(`eq_reference.mid_stage_tf`) across Rw = 0…33k: the model's span correctly asymptotes to ~0 at both
extremes (HI-MID 750: −0.32 dB at 16 kHz, −0.03 at 50 kHz), so this is not HF leakage through the
wiper leg. **The element is NOT identified.** Reopening A2c for this means touching a gap that just
closed on target, over a band above where bass content lives — recommend it stays behind A3.

### ▶ A2f — the ±0.2 dB residual shape. CHARACTERISED, PARKED (session 28). User-reported.

Bypass-corrected at flat EQ it is **one gentle tilt, not a peak plus a dip**: **+0.20 dB across
80–500 Hz, crossing zero near 900 Hz, −0.20 to −0.29 dB from 2.5–10 kHz.** Peak-to-peak ~0.5 dB,
about 3× the 0.144 dB take-to-take floor — real, but the smallest item open.

⚠ **Part of the apparent "dip at 8 kHz" in raw charts is the measurement chain**: `bypass.wav`
itself reads **+0.19 dB at 8.1 kHz** and −0.20 at 16 kHz. Always bypass-correct before reading shape
off a clean chart.

⚠ **Replicate count is lower than it looks.** `master-0930`, `master-1430_gain-n12`,
`master-1700_gain-n12` and `ref-clean_gain-n12` have deltas identical to <0.001 dB — MASTER is a
flat divider so all four are ONE shape. Flat-EQ evidence is effectively **2 independent shapes**
(that group + `ref-clean.wav`, which differs by ~0.18 dB = the take-to-take floor), not 5.

### ⭐ GAP #3b DISSOLVED (session 38, 2026-07-27) — the premise was stale, and the GRUNT span turns out to be an A3 *instrument*, not a gap

Analysis only. **NOTHING in `src/` changed**, so ctest is untouched at 17/17. The only code change is two
extra `--fit` keys (`clipC12`/`clipC13`) on `a3_blend_decompose`, plus a docstring correction on
`grunt_span_probe.py` (a real defect — see item 5).

**(1) THE HANDOVER'S "BIGGEST REMAINING OD GAP" RESTED ON A 14-SESSION-OLD MEASUREMENT, AND IT HAD
EXPIRED.** Session 23 recorded: pedal GRUNT span (flat−cut, drive-min) is a **bump** centred 127–202 Hz;
plugin is a **monotone high-pass shelf maximal at DC** (+13.8 dB at 40 Hz); *"a first-order coupling cap
can only move a shelf's corner — it can never turn a shelf into a bump."* Re-measured at the shipped
state, the pedal row reproduces **exactly** (it is a capture) and the plugin row has completely changed:

| band Hz | 25 | 32 | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pedal | −1.1 | −2.0 | −3.1 | −2.7 | +0.5 | +3.5 | +5.2 | **+6.0** | **+6.2** | **+6.2** | +5.6 |
| plugin (s23) | +12.8 | +13.4 | **+13.8** | +13.8 | +13.5 | +13.0 | +12.2 | +11.0 | +9.3 | +7.0 | +4.6 |
| plugin (NOW) | −3.8 | −9.2 | −5.9 | +3.6 | +8.3 | +10.0 | **+10.3** | +9.6 | +8.5 | +6.9 | +5.1 |

**The model now makes a bump.** Nobody worked on GRUNT — `trebleC7` (s34/35) and `clipC15` (s36/37) did
it as a side effect. Same lesson class as *"verify the CONSTANT, not the prose"* (s35) and *"verify the
BASELINE, not its LABEL"* (s37), one level up: **verify the PREMISE, not the prior session's framing of
it.** A stale premise is the most expensive kind, because it selects the next session's whole workplan.

**(2) ⭐⭐ AND THE MECHANISM SHOWS SESSION 23's INFERENCE WAS A CATEGORY ERROR — THE GAP #1b TRAP, ONE GAP
OVER.** The exact BLEND-node decomposition (`a3_blend_decompose`, `full = od + bleed` self-checked to
<−280 dB) separates the two. The **OD path's own GRUNT span is a monotone shelf in BOTH builds and is
essentially unchanged**:

| flat−cut span, drive-min | 25 | 32 | 40 | 101 | 202 | 403 | 640 |
|---|---|---|---|---|---|---|---|
| **OD path**, PRE (C7 100n, C15 inert) | 19.12 | 18.88 | 18.26 | 14.06 | 12.64 | 9.39 | 5.27 |
| **OD path**, POST (shipped) | 19.17 | 19.11 | 19.00 | 17.38 | 14.08 | 9.78 | 5.50 |
| **OUTPUT**, PRE | 12.81 | 13.48 | 13.31 | 8.87 | 4.79 | 1.44 | 0.61 |
| **OUTPUT**, POST | −2.97 | −10.65 | −5.52 | 10.18 | 6.24 | 2.49 | 1.03 |

⇒ *"a coupling cap can never turn a shelf into a bump"* is **true, and irrelevant**: the cap never had
to. **The BLEND sum does the conversion for free** — the total is `OD + bleed`, so once |OD| falls below
the flat bleed at LF the span is squeezed toward 0 there and a monotone OD shelf presents as an output
bump. Session 23 compared the model's **OD-path** shape against the pedal's **OUTPUT** shape. That is
precisely GAP #1b's error (session 21: *"session 20 compared the model's isolated stage transfer against
the pedal's OUTPUT shape"*), recurring one gap later. **Whenever the observable is post-BLEND, the bleed
is part of the transfer.**

**(3) WHAT ACTUALLY REMAINS, MEASURED PROPERLY.** Peak located by parabolic interpolation on the log-f
axis, never off the 1/3-octave grid (the standing rule):

| position | pedal peak | model peak | error |
|---|---|---|---|
| flat | **178 Hz @ +6.27 dB** | 96 Hz @ +10.27 dB | **0.89 oct LOW, 4.00 dB TALL** |
| boost | **144 Hz @ +11.23 dB** | 70 Hz @ +16.39 dB | **1.04 oct LOW, 5.16 dB TALL** |

Flat and boost agree to 0.15 oct and 1.2 dB ⇒ **ONE coherent error, not two**, and both quantities are
properties of the **OD/bleed crossover** — i.e. A3 — not of the GRUNT network.

**(4) ⛔ AND THE CAPS PROVABLY CANNOT REACH IT — a sharper result than session 23's "no interior
minimum".** The s23 scan predated C7/C15 so it could not be carried forward; re-run at the shipped state
it is still monotone (mean span-err 6.55 shipped → 5.08 at C12 ×0.5 → 4.77 at ×0.25, and 7.72/8.61 going
the other way; C13 likewise 8.07 → 5.94 → 4.23). But the decisive statement is the **locus**, because one
cap moves peak height and peak frequency *together*:

| C12 | 47n (ship) | 24n | 12n | 6n | 3n | 1n5 |
|---|---|---|---|---|---|---|
| flat-span peak | 90 Hz / **+10.28** | 110 / +7.11 | 126 / +4.30 | 137 / +2.40 | 142 / +1.28 | 147 / **+0.65** |

The locus runs **right and DOWN**, asymptoting near ~150 Hz with the height collapsing through zero. The
pedal's point is **178 Hz at +6.27 dB — right and UP.** It is off the curve **in both coordinates at
once**, so *no* value of C12 reaches it; the monotone "smaller is better" score is the familiar
degeneracy (shrink the element until it stops contributing), buying frequency by throwing away height.
Same for C13 on the boost row. ⇒ **GAP #3b needs no GRUNT-side fix. Session 23's own verdict — "3b is
GAP #3/A3 seen through the GRUNT switch, not a gap of its own; fold it into A3" — stands.** The session-37
handover's re-elevation of it to *"the biggest remaining OD gap, needs its own structural fix"* does not.

**(5) ⚠⚠ A DEFECT IN `grunt_span_probe.py`'s OWN PREMISE, AND IT HAD ALREADY MISLED A DECISION.** Its
docstring claimed the position-to-position difference *"cancels the entire rest of the chain EXACTLY —
the clean/OD blend balance, every EQ band, the gain-match, the output makeup."* The EQ bands, gain-match
and makeup do cancel (post-BLEND **multipliers**). **The blend balance does not** — the bleed is
**additive**, inside the log, so it survives any ratio. Consequence, measured: on this metric
`clipC15 = 1.5 nF` scores **3.654 / 1.755** against the shipped 5.2 nF's **6.862 / 4.507** — the metric
*prefers the value session 37 rejected on β-free evidence*, for exactly the reason session 37 identified
(it rewards anything that attenuates the OD path). ⇒ **the GRUNT span must never be used to select a
SHARED OD-path element** — only GRUNT-side ones (C11/C12/C13, R16), where the difference genuinely is the
differential. Docstring corrected.

**(6) ⭐ THE PAYOFF: THE SPAN IS A MAGNIFIER OF A3's CROSSOVER, AND IT MEASURES SOMETHING NO OTHER A3
GATE DOES.** A3's existing gates read null *depth* (`a3_lead_fit`), the *drive* axis (G1/G2) and the
*level* axis (`a3_level_axis`). None reads the **crossover frequency** — where |OD| overtakes the bleed —
and that is exactly what the span's bump peak locates, amplified by sitting on the cancellation. **New A3
sub-gate: the model's GRUNT-span bump must peak within ~1/6 octave of 178 Hz (flat) / 144 Hz (boost) at
drive-min. It is currently ~1 octave low, and it is ~4–5 dB too tall.** Carry this into the joint
`clipSat`/`kInputRef` re-fit as an acceptance check — a candidate that improves the null depth while
leaving the crossover an octave low has not fixed A3.

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

### ⭐⭐ A5 — the CLEAN (DIST-off) path distorts hard at moderate-to-hot levels the pedal doesn't. CONFIRMED (session 39, 2026-07-27), user-reported, not yet fixed

User's impression: "even the clean captures (distortion off) has some THD and harmonics that the
pedal doesn't." **VERIFIED by direct measurement — analysis only, NOTHING in `src/` changed, ctest
untouched.** New tool `analysis/clean_thd_check.py`.

**(1) THE TEST.** Every capture (clean or driven) embeds two harmonic-analysable signal families:
discrete tones at −14 dBFS spanning 82–8000 Hz (`gen_test_signal.py::TONE_FREQS`), and a 1 kHz
"compression knee" level ladder from −36 to −3 dBFS in 3 dB steps (`LEVEL_STEPS_DB`, segments
`lvl_-36`…`lvl_-3`) — built for characterising the OD path, but present unconditionally in every
clean capture too. Rendered `ref-clean.wav`'s exact settings (flat EQ, DIST off) through
`OfflineRender` at the shipped defaults and compared per-harmonic level (H2..H6, Nyquist-guarded,
same estimator as `tone_thd_nyquist_check.py`) against the real pedal's own `ref-clean.wav` capture,
tone by tone and level by level.

**(2) RESULT IS SPLIT — the −14 dBFS discrete tones do NOT show the defect; the level ladder does,
sharply.** At every one of the eight −14 dBFS tones (82 Hz–8 kHz), both pedal and plugin sit at
their respective measurement/numerical floors (THD ≤0.001%, every harmonic below −100 dBc) — this
part of the user's impression does not hold at that level. But on the `lvl_` 1 kHz ladder the pedal
stays pinned to its floor (THD 0.0000%, H2/H3 below −130 dBc) at **every** step −36…−3 dBFS, while
**the plugin is bit-clean only through −12 dBFS and then breaks hard: `lvl_-9` THD 0.97%, `lvl_-6`
12.9%, `lvl_-3` 22.9%** — measured on `ref-clean.wav`, i.e. with flat EQ and no boost active at all.
Confirmed on five more representative captures (`bass/treble/lomid/himid/master-1700_gain-n12` —
the hottest EQ-boost extremes — plus `bass-0930`/`treble-0930`): every one shows the identical
onset between −12 and −9 dBFS, reaching **11–23% THD by −3 dBFS**. −3 dBFS is an ordinary hot
playing peak, not an edge case — this is audible, not a measurement nit.

**(3) ROOT CAUSE LOCALISED AND CONFIRMED BY DIRECT A/B: the session-21 RailClamp.**
`--fit railEnabled=0` on the identical render drops every one of the above straight back to the
pedal's own numerical floor (0.0000% at every level, every capture tested) — not a rounding
artefact, exactly the op-amp rail saturation engaging. With DIST off the audible chain is
`IC1_A buffer (unity) → LevelBlend (distEngage=false returns cleanIn LITERALLY unmodified, verified
directly in LevelBlend.h::process) → C21 HP → EqPreGain (buffer + FIXED −2.2×, always active
regardless of EQ knob position — confirmed by `ref-clean.wav`'s FLAT-EQ render already showing the
defect) → Baxandall → LO-MID → HI-MID → MasterOut`, i.e. the ONLY nonlinearity anywhere on this
path is RailClamp on each op-amp output. Rough arithmetic is consistent with EqPreGain being the
first stage to rail: at −3 dBFS, `kInputRef` (3.377 V/FS, session 17) puts ≈2.39 V peak at IC1_A's
output; ×2.2 ≈ 5.3 V peak swinging around VD = 4.5 V — spanning roughly [−0.8, +9.8] V against the
shipped `railNeg/railPos` window of ≈[1.6, 7.2] V — hard clipping both peaks well before Baxandall
or MasterOut ever see the signal. Consistent with `master-1700` (MAXIMUM master, i.e. LEAST
available downstream attenuation) showing the *same* onset as every other capture, not a worse
one — the damage is done upstream of Master's knob. **Not yet pinned to the single worst-offending
stage** (Baxandall/mids/MasterOut could compound); that localisation is the natural next step and
was not attempted this session.

**(4) WHY NO EXISTING GATE CAUGHT THIS.** Every A2/A2c/A2d clean-set grade to date reads the
`sweep_clean` segment family, which tops out at **−30 dBFS** (`CLEAN_FR_LEVELS_DB = (−30, −36)`) —
well under the −12 dBFS onset. The `lvl_` ladder is rendered by the full-matrix harness but nothing
has read its harmonic content specifically; the existing band-RMS/FR grading is insensitive to a
narrow, level-triggered nonlinearity like this one. Same blind-spot class as A3-adjacent
(session 30) — a level-dependent defect invisible to fixed-level grading.

**(5) SCOPE — NOT an oversampling/aliasing issue, so it is orthogonal to the OS-sweep work in §5.**
EqPreGain/Baxandall/mids/MasterOut all sit in the shared post-BLEND EQ block, which runs at BASE
rate unconditionally (only the OD region — JFET→clipper→SK — sits inside the oversampled span, per
`dsp.md`/`PedalChain.h`'s stage list). **Verified, not just inferred from topology:** the identical
`ref-clean.wav` `lvl_-3` render is bit-identical (THD = 22.8546%, H2/H3 to 4 decimal places) at
OS 1×/2×/4×/8× — a headroom/gain-staging bug, not an aliasing one. Flagged for the SAME phase as
the performance/OS pass anyway (both are "make the low-drama signal paths faithful" work), and
because §5's OSFidelity sweep is a natural place to also confirm this defect — and its eventual
fix — hold across every OS
factor, not because the two are mechanistically related.

**▶ NEXT (before B/perf, per user request — backlog A5): localise which stage(s) actually rail**
(EqPreGain first suspect, per the arithmetic in (3)) and either (a) re-derive rail headroom for
that stage specifically instead of the single global `railNeg/railPos` pair, or (b) revisit whether
`kInputRef`/`EqPreGain`'s fixed −2.2× gain still make sense together post-session-17 (the same
"degenerate pair" caution already logged for `kInputRef`/clip-ceiling there) — do **NOT** raise the
rail voltages blind, they are physically derived from the +9V/D3/VD chain, not fitted (session 21).
Tool: `analysis/clean_thd_check.py` (per-capture, per-tone/level harmonic delta, `--fit`-aware).

### ⭐⭐ A3 step 3d — the "−12/−6 dBFS mid-band clipper item" DOES NOT SURVIVE ITS OWN AUDIT (session 40, 2026-07-27). Analysis + tooling only; NOTHING in `src/` changed

The queued next step was a JOINT `clipSat{Lo,Hi}` / `kInputRef` re-fit against the level axis
(session 37 item 4, re-affirmed by session 38). It was run. **The conclusion is that there is no
measurable clipper-side mid-band defect to fit, and the number the item was sized from was
82 % one band the clipper provably cannot reach.** No candidate is proposed and nothing is shipped.

**(1) ⭐⭐ AUDIT THE METRIC BEFORE FITTING TO IT — 82 % OF `mf_hot` IS THE SINGLE 254 Hz BAND.**
`mf_hot` (drives 2:30+max, 101–254 Hz, level step −12→−6) reads 0.94 dB at the shipped state. Split
by band: **101 Hz 0.45 / 127 Hz 0.40 / 160 Hz 0.54 / 202 Hz 0.35 / 254 Hz 1.90**, i.e. **254 Hz alone
is 82.4 % of the mean-square** and the other four together are 0.44 dB. Every "0.5–1.1 dB mid-band
clipper item" figure recorded in sessions 34/37 is this contaminated aggregate.

**(2) THE OBVIOUS EXPLANATION WAS TESTED AND REFUTED — 254 Hz IS NOT A CLIFF.** Session 37 item (9)
demoted `lf_hot` because below 80 Hz at high drive the total sits on the cancellation and amplifies
any error. That reasoning does **not** transfer: at 254 Hz the amplification
`S = d(total)/d(OD gain)` is **0.27, the LOWEST of the whole band set** (101 Hz is 0.47), with
m ≈ 0.43 and θ ≈ 45–53° — nowhere near anti-phase. The band is *de-amplified*, so its residual is
real signal, not magnified noise.

**(3) NOR IS IT A CAPTURE ARTEFACT — and the control that settles it is `bypass.wav`.** Both
`bypass.wav` (the pedal in true bypass, i.e. a wire) and `ref-clean.wav` (DIST off, measured at
0.0000 % pedal THD by A5) step by **exactly +6.00 dB at 254 Hz, deviation 0.00 to two decimals**,
at both level steps and at every other band. The `blend-0700` reference is −0.02. So the capture
chain and the 1/3-octave analysis are clean there, and the earlier suspicion that 254 Hz might be
an edge-of-band artefact like the excluded 320 Hz band is **wrong on that specific ground**.
(Standing lesson re-applied: `bypass-capture-is-the-control`.)

**(4) ⭐⭐ WHAT IT ACTUALLY IS: NOT CLIPPER-REACHABLE. THE DECISIVE TEST IS THE CONTROL DRIVES.**
A clipper-side compression error must vanish at drive min/9:30, where the clipper barely engages —
that is the entire basis for using `ctrl` as the control. Per-drive dT residual at 254 Hz, −12→−6:
**min +1.60 / 9:30 +1.41 / noon +0.98 / 2:30 +1.21 / max +2.40 dB.** It is **full size at the
control drives**; its own control rms is **1.51 dB against the hot 1.90**. Corroboration from the
other direction: matching the pedal's dT at 254 Hz/max needs **more than 24 dB of OD cut** (it hits
`solve_need`'s ±24 sentinel), with only **0.09 dB of headroom** against muting the model's OD path
at that band entirely. ⇒ **no clipper VTC parameter, at any value, is responsible for it.**
⚠ Note this corrects a natural first reading: `need = +24.00` is the UNREACHABLE SENTINEL, not a
value. Check `solve_need`'s span before quoting it.

**(5) IN THE PEDAL'S OWN RAW DATA IT IS A LONE SPIKE FLANKED BY CLEAN NEIGHBOURS.** Pedal
level-step deviation from +6.00 dB at drive **min**, −12→−6, by band: 80 **+0.00** / 101 +0.09 /
127 +0.23 / 160 +0.15 / 202 **+0.30** / 254 **−1.34** / 320 **+0.06** / 403 −0.26. Curvature at
254 Hz is 2.68 (min) / 3.01 (9:30) against the model's 0.44–0.48 and against ~0.2 at its own
neighbours. Meanwhile **320 Hz — the already-EXCLUDEd TrebleAttack-notch band — is the only band
POSITIVE in every OD capture** (+0.06…+0.69). **Hypothesis, consistent with the evidence but NOT
proven: 254 Hz sits on the skirt of the pedal's ~300 Hz TrebleAttack two-path cancellation notch
(GAP #2; session 19 measured it at ~322 Hz, −3.4 dB in the capture), whose balance shifts with
level because one of its two paths is the nonlinear one.** A notch-skirt band is steep, so a small
level-dependent shift in the notch produces a large level-step deviation confined to it.
⇒ **254 Hz should be excluded from level-axis aggregates for the same reason 320 Hz already is** —
explicitly and with this evidence recorded, never silently.

**(6) ⭐ WITH 254 Hz REMOVED THE ITEM IS AT THE NOISE FLOOR.** Like-for-like, on the SAME bands:

| subset (level step −12 → −6) | rms dB | n |
|---|---|---|
| CONTROL min+9:30, 101–202 Hz | **0.29** | 8 |
| CONTROL noon, 101–202 Hz | 0.25 | 4 |
| **TARGET 2:30+max, 101–202 Hz (`mf_ex254`)** | **0.44** | 8 |
| TARGET 2:30+max, 101–254 Hz (`mf_hot`, as previously ranked) | 0.94 | 10 |
| 254 Hz alone, 2:30+max | 1.90 | 2 |

The genuine mid-band item is **0.44 dB against a band-matched control of 0.29 dB — a margin of
0.15 dB, i.e. AT this project's 0.144 dB take-to-take capture repeatability floor.** ⚠ The
whole-band `ctrl` (0.47) was never the right comparator for a 101–254 Hz target; restricted to
101–254 the control is **0.72**, *larger* than the ex-254 target it was supposed to bound.

**(7) THE JOINT 5×5 SCAN WAS RUN ANYWAY, AND CONFIRMS IT EMPIRICALLY.**
`analysis/a3_clipper_joint_scan.py`, satScale × kInputRefScale ∈ {0.70, 0.85, 1.00, 1.15, 1.30}²,
25 candidates × 15 renders, liveness-guarded. Ranked on `mf_ex254` with the band-matched control
printed beside it:

* **The best `mf_ex254` (0.27 at satSc 0.70 / krSc 0.70) sits at a GRID CORNER, not an interior
  minimum** — the degeneracy signature the scan was built to detect.
* **Its matched control falls in lockstep** (0.29 → 0.14), so the ratio target/control gets
  *worse* (1.52 → 1.93). Nothing is being separated from the noise floor; everything is shrinking.
* **Margin (`mf_ex254 − ctrl_ex`) over the whole grid: 0.08 – 0.56 dB, shipped 0.15.** Every
  candidate at or below shipped is inside the 0.144 dB floor, and the candidates with the *smallest*
  margin (0.08) get there by raising the control to meet the target, not by fixing anything.

⇒ **No 2-D interior optimum exists on the corrected target. Do not ship a `clipSat`/`kInputRef`
change for this item.** The metric is demonstrably sensitive to these parameters (`mf_ex254` spans
0.27–0.95 across the grid); it simply has no optimum, because there is no defect there to find.

**(8) TWO SIDE FINDINGS FROM THE SAME RENDERS, BOTH BELONGING TO A5 RATHER THAN HERE.**
*(a)* **Rails OFF** (`railNeg/railPos = 1000`, equivalent to disabling the clamp since RailClamp is
dead-linear to the knee — no rebuild needed) improves **`all` 1.00/2.14 → 0.61/1.16 and the null
band 12/15 → 13/15**, while barely moving `mf_ex254` (0.44 → 0.42). So the model is railing
somewhere that costs it on the level axis — **the same class of defect as A5, in the OD path rather
than in the post-BLEND EQ block A5 measured.** Fold it into A5's rail-headroom item.
*(b)* ⚠ **My own rail hypothesis for the CONTROL was refuted by that A/B**: rails-off makes
`ctrl_ex` **worse** (0.29 → 0.33), so the control's sensitivity to `kInputRef` is *not* railing.
What improves the control is the anti-diagonal (satSc = krSc), which by construction holds the
clipper's operating point fixed while reducing how hard the **JFET** is driven — consistent with
the structural fact that DRIVE sits *downstream* of the J201, so the control drives' residual
nonlinearity is JFET-side. `kInputRef ×0.70 alone` improves the control (0.29 → 0.22) but wrecks
the target (0.44 → 0.73), so it is not a free win either.

**(9) ✅ THE CROSSOVER SUB-GATE IS NOW A COMMITTED, RUNNABLE TOOL — and it reproduces session 38
exactly.** Session 38 defined the gate but measured it ad hoc. `grunt_span_probe.py` gained
`peak()` (parabolic vertex in log2 f, the `mid_shape_verify.py` pattern) and `crossover_gate()`,
scoped to the drive-min triple on `sweep_clean`. At the shipped state it returns **pedal flat
177.8 Hz / +6.27 dB, boost 144.0 Hz / +11.23 dB; model 95.7 Hz / +10.27 dB, 69.4 Hz / +16.39 dB;
deltas −0.89 oct / +4.00 dB and −1.05 oct / +5.16 dB** — every figure matching session 38's record
to the last decimal, so the locator is validated rather than merely plausible. It carries a
self-check that flags any drift of the *pedal* row from `GATE_TARGETS`, and it refuses to run on
`sweep_drv_-6` (where the pedal's own span peak moves to ~106/89 Hz — a different question).
⛔ The standing prohibition is restated in-tool: judge on PEAK LOCATION only, never this probe's
aggregate span-err RMS, which prefers the already-rejected `clipC15 = 1.5 nF`.

**⭐ THE METHOD LESSON, which is the transferable part.** Sessions 34 and 37 both sized this item
from `mf_hot` without splitting it by band. The number was real, the aggregate was real, and the
attribution was wrong — one band supplying 82 % of a metric, and that band not reachable by the
parameter family being fitted. **A `defective-rows-must-not-vote` failure in a new place: not rows
of a capture matrix this time, but BANDS inside a single aggregate.** The check that caught it costs
one decomposition and should precede any fit: *split the objective by its members, and confirm each
member is reachable by the knob you intend to turn.* The corollary that made it decisive: **compare
a target against a BAND-MATCHED control, not a whole-band one** — the whole-band `ctrl` (0.47)
flattered a 101–254 Hz target whose own matched control was 0.72.

**▶ NEXT.** (a) The A3 mid-band clipper item is **CLOSED as not-measurable**; do not re-open it
without new evidence that is not `mf_hot`. (b) The 254 Hz notch-skirt hypothesis (5) is worth one
confirmation pass against GAP #2's TrebleAttack notch, since if correct it also predicts the
320 Hz sign anomaly — cheap, and it would let 254 Hz be excluded on a mechanism rather than on a
symptom. (c) A5's rail-headroom item now has a second, independent motivation from (8a). (d) The
crossover sub-gate (9) remains A3's largest measured, unexplained error (~1 octave, ~4–5 dB) and is
the natural next A3 target.

### ⭐⭐ A5 step 1 (session 41, 2026-07-27) — the clean-path rail is LOCALISED to IC5_B, and the level it rails at is ARITHMETICALLY IMPOSSIBLE for this pedal's supply. Plus: the output level calibration had gone stale and the plugin was 3 dB too loud — SHIPPED

Session 39 confirmed the defect and A/B'd its cause to the RailClamp, but "EqPreGain first suspect"
was an arithmetic guess. This session measured it, and the measurement led somewhere bigger than
the stage.

**New tools.** `analysis/clean_rail_probe.cpp` (per-op-amp-node unclamped swing, via a new
`PedalChain::processPostBlendTapped` — the exact sibling of the session-19 `runOdSampleTapped`);
`analysis/clean_headroom_probe.py` (measures the onset by bisection on `--input-trim`, plus a
`--input-ref` control); `analysis/clean_headroom_bound.py` (the supply arithmetic + the pedal's own
ladder linearity).

**(1) THE OFFENDER IS IC5_B, AND NO EQ SETTING CAN CHANGE THAT.** With the clamps disabled the
DIST-off path is exactly linear (self-test: node gains identical to **0.000000 dB** at two probe
levels 12 dB apart), so one render at one level gives every node's rail onset at once. At 1 kHz,
flat EQ: BLEND wiper and C21 are passive at 0.00 dB; **IC5_B +6.85 dB (×2.2)**; IC5_C / IC5_D /
IC6_A all +6.66 dB; IC6_B can only be smaller (the MASTER divider ≤ 1). So **IC5_B is the highest
node in the whole clean chain and it is UPSTREAM of every EQ band** — the onset is
**−8.79 dBFS (hard limit) / ≈ −10.0 dBFS (RailClamp's 0.35 V knee, where distortion actually
starts)** in all six EQ cases tested, including every single-band boost extreme and MASTER max.
That reproduces session 39's independent "bit-clean through −12, 0.97 % at −9" from the other side.

**(2) ⭐⭐ AND IT IS NOT A RAIL-VOLTAGE QUESTION — `kInputRef = 3.377 V/FS` IS IMPOSSIBLE ON A 9 V
PEDAL.** Two schematic-verified facts do the work: IC5_B's gain is `−R29/R28 = −2.2`, fixed and
always in circuit, and the supply is 9 V → D3 (~0.35 V) → 8.65 V with VD = 4.325 V, so **no node in
this pedal can swing more than ±4.325 V**, whatever op-amp is fitted. At the ladder's hottest rung
(−3 dBFS, where the pedal reads **0.0000 %** THD) `kInputRef = 3.377` puts **2.391 V pk at the jack
and 5.260 V at IC5_B — 1.70 dB ABOVE the supply ceiling.** Implied ceilings on `kInputRef`:
**≤ 2.777 V/FS** (supply — unbeatable), **≤ 1.734** (session-21 TL07x hard limit), **≤ 1.509**
(TL07x knee, i.e. what "no measurable THD at −3 dBFS" actually requires). Shipped: **3.377**.

**(3) THE LADDER AGREES, AND SO DOES THE CONTROL.** Model THD% at −9/−6/−3 dBFS on `ref-clean`:
`kInputRef` **3.377 → 1.05 / 13.03 / 22.91**; 2.400 → 0 / 1.13 / 13.16; 1.700 → 0 / 0 / 1.14;
**1.200 and 0.870 → 0.0000 at every rung, exactly like the pedal.** Control: the onset moves
**dB-for-dB** with `kInputRef` (worst error **0.00 dB** over a 9 dB sweep) ⇒ the only nonlinearity
on this path really is a fixed-voltage clamp, which is what makes the whole bound argument valid.
And the pedal's own ladder steps **3.000 dB** twelve times with a worst deviation of **0.0005 dB**
over 33 dB — it genuinely does not compress, so this is not a capture artefact.

**(4) ⚠ SO THE (kInputRef, clipSat) DEGENERACY IS BROKEN FROM OUTSIDE — AND THE TWO ANSWERS
DISAGREE.** `GainStaging.h` records that under audio-only captures `kInputRef` is degenerate with
the clip ceiling and cannot be measured, which is why session 17 fitted the pair jointly and chose
3.377 on FAMILY physicality (at 0.87 the clipper ceiling had to fall to ~1.3 V/side against a ~7 V
R19-dropped rail). **The clean path contains no clipper, so it supplies a third constraint the
joint fit never saw — and it says ≤ 1.5.** Scaling `kInputRef` down by that factor scales the
fitted clipper ceilings with it (`clipSat` sum 4.94 V → ~2.2 V), i.e. straight back into the
regime session 17 rejected. **This is a genuine contradiction between two physical arguments, not
a value to nudge**, and it is the reason nothing was shipped for it here. ⛔ **Do NOT lower
`kInputRef` alone** — it is the anchor every nonlinear fit since session 17 was made against.
Corroborating hint from a different direction: session 40 (8a) found rails-OFF *improves* the OD
level axis (`all` 1.00/2.14 → 0.61/1.16, null band 12/15 → 13/15), i.e. the model rails somewhere
it should not in the OD path too — the same class of error, one path over.

**(5) ⭐⭐ THE OTHER FINDING: THE OUTPUT LEVEL CALIBRATION HAD GONE STALE AND THE PLUGIN WAS 3 dB
TOO LOUD. SHIPPED: `kOutputMakeup` 3.684 → 2.599, `masterTaperExp` 2.25 → 1.998.** Found while
converting dBFS to volts for (2). **Invisible to every Phase-9 number by construction** — §1: each
capture is gain-matched before differencing, so the entire 63-capture matrix measures SHAPE and
absolute level is a separate axis. Four things had to be untangled:
- **A 12 dB double-count in the tool itself.** Session 21 correctly taught `render_args()` to emit
  `--input-trim` for a capture's gain session; `master_taper_makeup.py` predates that and already
  corrects the *capture* UP by +12.071 dB, so the render was being trimmed DOWN by the same amount
  and the whole 12 dB landed in `kOutputMakeup`. Re-run as-was it returns **10.43**. Fixed by
  clearing the tag on the render template. ⭐ **A harness fix can break a tool that is not part of
  the harness** — nothing re-ran this script between session 17 and now.
- **A stale reference capture.** `master-1700_gain-n12_base-clean.wav` is the single capture this
  constant is level-matched against, and session 24 found it to be a **bad take and re-recorded
  it** (sweep_clean RMS **−16.62 → −18.20 dBFS**). Worth **1.58 dB**.
- **A moved model.** `trebleWiperR` (s25), the mid cap table + `midWiperR` + `midCapRatio`
  (s26/27) and `c21R` (s28) each change the clean chain's broadband gain. Worth **1.44 dB**.
  1.58 + 1.44 = **3.02 dB**, and the direct model-vs-pedal ladder comparison reads **+3.016 dB** —
  the decomposition closes to 0.01 dB.
- **A missing knob point.** `ref-clean.wav` **IS** the master = 0.50 member of the same series
  (`_REF_OD` with `base=clean` is every pot at noon) — it simply carries no `master-` filename
  token, so the taper fit never saw the MIDDLE of the knob's travel, which is exactly where the
  shipped value was worst. Added.

**(6) THE TAPER IS NOT A POWER LAW, AND SAYING SO IS THE HONEST RESULT.** Per-point exponents are
**1.929 / 2.322 / 1.734 at m = 0.25 / 0.50 / 0.75** — non-monotone, so no exponent fits all three
(same finding as the DRIVE C-taper, session 16). Worst whole-travel error: **2.25 (shipped) 3.87 dB
| 2.322 4.73 | 1.734 3.54 | 1.929 2.37 | 1.998 (least squares) 1.95**. Shipped the least-squares
value. ⭐ **`master_taper_makeup.py`'s own untargeted consistency check — which session 17 printed
as `worst |err| = 3.71 dB (CHECK — taper/makeup mismatch)` and shipped anyway — is the thing that
would have caught all of this in 2026-07-24.** A failing acceptance check is not a footnote.

**(7) VERIFIED AFTER SHIPPING.** ctest **17/17**. Absolute level, model − pedal, on the linear part
of the ladder (identical at every rung, as a scalar must be): master **0.25 −0.85 / 0.50 +2.00 /
0.75 −0.67 / 1.00 −0.01 dB** (master 0.00 is the divider null — both silent; do not aggregate it,
session-18 trap). Before: roughly +2.4 / +3.5 / +3.0 / +3.0. The residual +2.00 dB at m = 0.50 is
the power law's own limit per (6), not a fit error. **Both constants are post-EQ scalars**
(`outputGain = makeup / kInputRef`; MASTER is a divider), so they move **no** nonlinear operating
point and invalidate **no** OD fit — but they DO shift the idle floor, so backlog **C1 (VU
idle-gate threshold) must now be re-checked against 2.599, not 3.684**.

**▶ NEXT.** (a) A5's remaining question is **not** "which stage" — that is answered — but the
`kInputRef` contradiction in (4). It needs a joint re-fit of `kInputRef` **with** the clipper
family, judged on the CLEAN path's supply bound as a hard constraint alongside the OD harmonic
targets; the alternative is that something in the OD chain's gain distribution is wrong in a way
that lets the clipper live at a lower absolute drive. **Do not fit either half alone.** (b) The
A3 crossover sub-gate (§4 "GAP #3b DISSOLVED" item 9) is still A3's largest measured unexplained
error. (c) The 254 Hz notch-skirt confirmation. Then A4 re-grade + GATE-9, `gain-n12` HF collapse,
B (perf/HQ), C (carry-forwards), D (release).

### ⭐⭐ A5 step 2 (sessions 42–43, 2026-07-27) — THE CONTRADICTION IS DISSOLVED, AND IN THE OPPOSITE DIRECTION TO THE ONE PREDICTED. The clean path's supply bound does not fight the OD harmonic targets; imposing it makes the fit **better** and **physical**. NOTHING in `src/` changed — no candidate shipped

Session 41 left A5 with what looked like a genuine collision between two physical arguments: the
clean path says `kInputRef ≤ 1.509 V/FS` (IC5_B's fixed −2.2× against an 8.65 V supply), the shipped
value is 3.377, and session 17 had chosen 3.377 on the grounds that anything lower drove the clipper
ceiling to a level it judged unphysical. The resume plan written for this step assumed the likely
answer was "the constrained family is a genuinely worse fit, and now you must choose which
constraint to relax". **That assumption was wrong, and the way it was wrong is the finding.**

**(1) ⭐⭐ THE UNFENCED HARMONIC OBJECTIVE DOES NOT IDENTIFY `kInputRef` AT ALL — IT RUNS TO
WHATEVER CEILING THE BOX PROVIDES.** The CONTROL run (`--fence-a0=20,30` only, i.e. session 17's
protocol unchanged, on today's model) returns **`kInputRef` = 5.972 against a bound of 6.0** and
**`clipSatHi` = 3.9999 against a bound of 4.0** — *both resting on their bounds*, which
`fit_nonlinear.py` itself labels "a property of the box, not the pedal". So session 17's 3.377 was
never a measurement either; it was where *its* box and starts happened to stop. ⇒ **the "degenerate
pair" warning in `GainStaging.h` is stronger than recorded: K is not weakly identified by the OD
harmonics, it is not identified at all.** An external constraint is not an inconvenience here, it
is the only thing that can pin K.

**(2) ⭐⭐ AND THE CONTROL'S ANSWER IS PHYSICALLY IMPOSSIBLE.** Its `clipSatLo+Hi` = **7.323 V =
130 % of the derived 5.636 V CD4049 rail** (§ `circuit.md` R19 note; `clipper_rail_selfconsistent.py`).
Not "near the rail", not "implausible" — a CMOS inverter cannot swing 130 % of its own supply. The
only reason session 17's equivalent number (4.94 V) passed was that it was checked against a round
"~7 V rail" **that no calculation ever produced**. With the real ceiling in the tool, the
unconstrained protocol fails its own acceptance check.

**(3) ✅ THE CONSTRAINED FIT IS BETTER ON EVERY AXIS THAT MATTERS.** KFENCED =
`--fence-a0=20,30 --fence=kInputRef=0.40,1.509 --fence=clipSatLo=0.30,4.0 --fence=clipSatHi=0.30,4.0`
(K fenced to the clean-path bound AND the clipper ceilings freed off session 15's [1.5, 4.0] box —
both at once, or the two constraints are jointly infeasible and the result is uninterpretable):

| | SHIPPED (s17) | CONTROL (unfenced) | **KFENCED** |
|---|---|---|---|
| cost (same objective, today's model) | 649.59 | 97.0 | **45.8** |
| ψ3 @ 1 kHz error | — | 29.4° | **0.8°** |
| `kInputRef` | 3.377 | **5.972 (ON BOUND)** | 1.435 |
| → V peak at the −6 dBFS "hot bass" rung | 1.69 | **2.99 (implausible)** | **0.72 (plausible)** |
| `clipSatLo+Hi` | 4.939 V (88 % of rail) | **7.323 V (130 % — IMPOSSIBLE)** | 1.423 V (25 %, soft flag) |
| FAMILY verdict | — | **NOT PHYSICAL** | **PHYSICAL** (soft flag) |

**14× better than the shipped point and 2.1× better than the unfenced control**, with a phase
residual of 0.8° against the control's 29.4°. Cross-checked: `a5_fit_eval.py` scores the two fitted
vectors at **45.76 / 96.99**, reproducing the fits' own 45.8 / 97.0 — the two tools agree, so the
comparison is on one scale.
⚠ **And it is NOT a seeding artefact.** Two of KFENCED's three starts had `kInputRef` clipped into
the fence (2.4 and 3.4 → 1.509), which would be a fair objection — but **the winning start was
start 3 (K = 0.87, already inside the fence), at 45.8**, with the clipped start 2 second at 56.5.
The best point was not reached from a clipped seed.

**(4) ⛔ BUT DO NOT SHIP IT — IT FAILS THE ONE CHECK THE OBJECTIVE CANNOT SEE.**
`2·a·jfetCeilNeg` = **4.095** against the square-law identity of ~1.0. This quantity is
*deliberately left unconstrained* in the fit precisely so it can act as independent corroboration
(step-4 acceptance), and the constrained point misses it by 4× — while the CONTROL, for all its
unphysicality elsewhere, lands at **1.161**. Two further flags: **`clipA0` rests on its bound**
(20.03 in [20, 30] — the optimum wants A0 *below* circuit.md's datasheet prior), and the `clipSat`
sum at **25 % of the rail** carries the soft flag (the fitted VTC saturates well before the device's
output stage would — that needs a mechanism; it is not a supply violation, but it is not nothing).
**Neither fit is shippable. The constrained one is the right *direction*, not the right *point*.**
⚠ `gm`-sensitivity is flat for neither (KFENCED 45.8 → 66.8 / 109.2 / 326.6 across 0.09/0.12/0.15 mS;
CONTROL 97 → 156 / 190 / 489), so the session-4 `jfetGm` anchor is doing real work in both.

**(5) ✅ THE 5.64 V RAIL IS NOW TRIPLE-CHECKED (session 43).** Session 42 derived it from the
fixed point `VDD = 8.65 − I_DD(VDD)·R19` on the DAFx-2020 CD4049 model, but verified the
load-bearing precondition — that IC3's five spare sections are input-grounded, not floating — on
the PRIMARY schematic only, and honestly flagged the backup as unchecked. That flag mattered: if
those inputs floated, all six sections draw crowbar current, the rail collapses **5.64 → 2.70 V**,
and the shipped `clipSat` sum becomes **impossible at 183 %** rather than merely tight. Checked at
600 DPI: the backup draws the spares as an explicit row across its top-left (region A, cols 3–6) as
**U3B–U3F**, with **inputs pin 5/7/9/11/14 all on ONE junction-dotted net terminating at a GND
symbol**, and every spare output (4/6/10/12/15) left dangling — node-for-node identical to primary
p.4. ⇒ **n = 1 confirmed on both sources.**

**(6) ⚙ TOOLING.** `fit_nonlinear.py`: generic repeatable `--fence KEY=lo,hi` (the existing
`--fence-a0=` still works); PID-qualified temp render filenames so two fits can run concurrently;
and the family check now judges `clipSat` against the **derived 5.636 V** ceiling as a HARD fail
(printing % of rail), with the old 3.0 V floor **demoted to an explicitly-labelled SOFT flag** —
the rail argument bounds `satsum` from ABOVE only, and rejecting a candidate on an unexplained
floor is exactly the half-of-a-degenerate-pair error session 16 caught. New
`analysis/a5_fit_eval.py` (score any point on the fit's objective without re-fitting) and
`analysis/clipper_rail_selfconsistent.py` (the rail solve).

**⚠ METHOD LESSON — A BACKGROUND JOB THAT "PRINTS NOTHING" MAY JUST BE BLOCK-BUFFERED.** Session 42
launched these two fits, saw only 2–4 header lines after ~10 minutes, and recorded them as "still
running, no output yet". In fact **Python block-buffers stdout when redirected to a file**: the
entire header was sitting in a buffer and only the unbuffered `stderr` warnings had appeared. The
processes then died with the session and had to be relaunched from scratch. **Launch analysis runs
with `python3.11 -u`** — otherwise you cannot distinguish progress from a hang, and "no output" is
not evidence of either.

**▶ NEXT.** Superseded by session 44 below — the point was found and SHIPPED.

### ✅✅ A5 step 2 CONCLUDED (session 44, 2026-07-27) — the family is re-fitted under the clean-path bound and **SHIPPED**. `kInputRef` 3.377 → **1.2596**, the whole clipper/JFET family with it. A5's defining symptom is GONE

Session 43 left two named blockers on the constrained point: it failed the square-law corroboration
(`2·a·ceilNeg` = 4.095 against ~1.0) and parked `clipA0` on its 20.0 floor. **Both were artefacts of
the search, not of the physics.** Six fits (all `python3.11 -u`, all seeds placed INSIDE their
fences — see the tooling note) resolved them and produced a point that clears every step-4 check
with nothing resting on a bound.

**(1) ⭐ THE `clipA0` FLOOR-REST WAS THE FENCE SITTING ON THE OPTIMUM, AND THE PRIOR IS NOW DERIVED
RATHER THAN ASSUMED.** With the floor moved 20 → 8, A0 does **not** run down: it settles at
**21.44** (A0FREE) and **21.19** (SQLAW), both interior. And the prior itself is no longer an
assumption. ⚠ **First correction: circuit.md's "A0 = 20–30" is NOT a datasheet number** — the TI
CD4049UB datasheet gives a VTC only at VCC = 5 V, as a min/max tolerance envelope, and carries **no
small-signal gain spec at all** (`nonlinear-component-modeling.md` §1 says so explicitly: "get those
from DAFx / capture"). 20–30 is a community measurement on real B3K/B7K units. It CAN, however, be
derived from the same DAFx-2020 device model that gave the 5.636 V rail: at the shunt-feedback
self-bias point both devices saturate at the same current, so
`A0 = (gm_n + gm_p)/(gds_n + gds_p) = (1/vov_n + 1/vov_p)/λ` — **the current cancels exactly**, so
this inherits none of the crowbar-current uncertainty. At the DAFx λ = 0.06 it gives **A0 = 22.0**,
inside the community band from a completely independent direction. New section (4) of
`clipper_rail_selfconsistent.py`. ⚠ Its one honest gap: the DAFx fit publishes λ for the p-channel
only, so λ is swept rather than assumed and A0 is a range — do not quote a number without its λ.
Reaching A0 < 15 needs λ > 0.09 on both devices, A0 < 10 needs λ > 0.13.

**(2) ⭐⭐ THE SQUARE-LAW CORROBORATION IS FREE, AND IT IS GENUINELY CORROBORATED — NOT IMPOSED.**
`a` (jfetSatNeg) = 1/Vov and `cn` (jfetCeilNeg) = Vov/2, so a square-law device satisfies
`2·a·cn = 1` exactly. New `fit_nonlinear.py --square-law` imposes it as a SUBSTITUTION
(`cn := 1/(2a)`, not a penalty) so the constrained point is scored on the identical objective and
the costs compare on one scale. Imposing it costs **nothing**: 43.6 constrained vs 39.8
unconstrained-at-fenced-K, and it **beat session 43's unconstrained 45.8**. ⚠ But an imposed check
cannot corroborate — that is the whole point of leaving it free — so a separate run (`FREECHK`)
**freed the identity again and started from the constrained basin**: it came back at
**`2·a·ceilNeg` = 1.009**, and both perturbed seeds (cn 1.10 → cost 57.8, cn 0.40 → 73.4) scored far
worse. **The data prefers the identity; session 43's 4.095 was an unvisited region, not an
unreachable one.**
⭐ Sharper than "it missed the identity": session 43's point is **outside the identity's feasible
region entirely**. Projecting it onto the manifold makes the waveshaper **fold back** (min slope
−9.4e−02), because the square law caps `|a|·s` at ~0.80–0.95 (β-dependent) while that point sits at
0.970. It would need β ≈ 4 — its upper bound — to be feasible at all.

**(3) ⛔ AND THE REMAINING TENSION IS LOCATED EXACTLY: it is the `clipSat` SOFT FLOOR, nothing else.**
`SQ_PHYS` added session-15's physical `clipSat` fence ([1.5, 4]/side) on top of the square law, the
K bound and the A0 prior — i.e. every constraint at once. Cost **34.1 → 201.8 (5.9×)**, ψ3 error
7.7° → 27.4°, and **three parameters pinned simultaneously** (`clipA0` on 20, `clipSatLo` on 1.5,
`kInputRef` on 1.509). Every constraint binding at once is the signature of a jointly infeasible
region. So the shipped point's `clipSat` sum of 1.036 V (**18 % of the 5.636 V rail**) is a real,
quantified residual — but it is a **SOFT** flag by construction: the rail bounds `satsum` from
ABOVE only, and rejecting on the floor alone is the half-of-a-degenerate-pair error session 16
caught. It is also **structural to the fenced K**: the clipper's drive scales with K, so a 2.7×
lower K pulls the fitted ceiling down with it.

**(4) ⚠⚠ THE OPTIMISER IS FINDING LOCAL MINIMA — DO NOT READ SUB-2× COST DIFFERENCES AS RANKINGS.**
Proof from this session's own runs: `BOTH`'s box **strictly contains** `SQLAW`'s (`clipA0` ∈ [8,30]
⊃ [20,30], same everything else) and yet it scored **79.9 against 43.6**. Every cost below is a
local optimum. This is why the ship decision was NOT made on cost.

**(5) ⛔ AND WHY THE SHIP STOPPED WHERE IT DID: each widened box buys ~10 % of cost by parking a
DIFFERENT parameter on a bound.** `SQ2` 34.1 (nothing on a bound) → `FREECHK` 30.8 (`clipA0` on its
30 ceiling) → `FREECHK2` 27.5 (`clipA0` 34.8, outside both the community prior and the derived 22;
`kInputRef` **on** its 1.509 fence; the identity drifted to 0.813). That is the degeneracy sliding,
not the fit improving — the same "the objective does not identify this direction" signature session
43 found for K itself. **Stop at the point where nothing rests on a bound.**

**THE RUNS, all on one objective and one model** (`analysis/fit_logs/step7_a5_*.log`):

| run | cost | 2·a·ceilNeg | clipA0 | kInputRef | clipSat sum | ψ3 err | on a bound? |
|---|---|---|---|---|---|---|---|
| SHIPPED s17 | 649.6 | 1.741 | 26.1 | 3.377 | 4.94 V (88 %) | — | K physically impossible |
| CONTROL s43 | 97.0 | 1.161 | 22.6 | **5.97** | **7.32 V (130 %)** | 29.4° | K + clipSatHi — NOT PHYSICAL |
| KFENCED s43 | 45.8 | **4.095** | **20.0** | 1.435 | 1.42 V (25 %) | 0.8° | clipA0 floor |
| A0FREE | 39.8 | **3.631** | 21.44 | 1.368 | 1.47 V (26 %) | 1.3° | none |
| SQLAW | 43.6 | 1.000 (imposed) | 21.19 | 1.005 | 0.73 V (13 %) | 1.8° | clipSatLo floor |
| BOTH | 79.9 | 1.000 (imposed) | **10.6** | 0.972 | 0.72 V | 9.7° | beta floor |
| SQ_PHYS | **201.8** | 1.000 (imposed) | **20.0** | **1.509** | 3.24 V (57 %) | 27.4° | **three at once** |
| **✅ SQ2 (SHIPPED)** | **34.1** | **1.000** | **24.87** | **1.2596** | 1.04 V (18 %, soft) | 7.7° | **NONE** |
| FREECHK | 30.8 | **1.009 (FREE)** | **30.0** | 1.242 | 1.18 V (21 %) | 1.8° | clipA0 ceiling |
| FREECHK2 | 27.5 | 0.813 | **34.8** | **1.509** | 1.61 V (29 %) | 2.7° | K ceiling |

**(6) ✅✅ SHIPPED = SQ2** (`FitParams.h` + `GainStaging.h::kInputRefNominal`): `kInputRef`
**3.377 → 1.2596**, `clipA0` 26.142 → **24.871**, `clipSatLo` 2.0067 → **0.4377**, `clipSatHi`
2.9321 → **0.59791**, `clipK` 2.8462 → **2.4653**, `clipC11` 5.7207 → **3.69 nF**, `jfetSatPos`
0.20072 → **0.4559**, `jfetSatNeg` 3.1769 → **0.76054**, `jfetCeilPos` 2.3428 → **2.0111**,
`jfetCeilNeg` 0.27408 → **0.65743**, `jfetExpandBeta` 2.1354 → **0.46279**. `kOutputMakeup` is
UNCHANGED at 2.599 — K cancels through the linear path, so the clean LEVEL does not move.
Chosen over the two lower-cost points because it is the only one with **zero bound-rests**, its
`clipA0` sits inside both the community prior and near the derived 22.0, and its identity value is
independently corroborated by FREECHK (1.009, freed, from this same basin). **ctest 17/17.**

**(7) ✅✅ AND A5's DEFINING SYMPTOM IS GONE — the acceptance test, not an inference.**
`clean_thd_check.py` extended to carry the WHOLE onset region (`lvl_-12/-9/-6/-3`), not just the top
rung — checking only `lvl_-3` reports that the defect exists but cannot show that it has actually
gone rather than moved up one rung, and `-12` gives a known-clean control rung inside the same
capture. 1 kHz THD %, pedal / plugin, on `ref-clean`:

| rung | BEFORE (K = 3.377) | AFTER (K = 1.2596) |
|---|---|---|
| `lvl_-12` | 0.000 / 0.000 (control) | 0.000 / **0.000** |
| `lvl_-9` | 0.000 / 0.572 | 0.000 / **0.000** |
| `lvl_-6` | 0.000 / 10.49 | 0.000 / **0.000** |
| `lvl_-3` | 0.000 / 20.30 | 0.000 / **0.000** |

Across all 9 clean captures × 4 rungs the FLAGGED list goes from **14 entries (up to +137 dB hotter
than the pedal)** to **none** — every plugin harmonic now sits BELOW the pedal's own noise floor.
**A5 is closed.**

**(8) ✅ THE 63-CAPTURE MATRIX, RE-BASELINED (mandatory — K is upstream of every nonlinearity).**
**OD 3.357 → 3.186 (−0.17) | CLEAN 0.465 → 0.427 (−0.04) | ALL 1.911 → 1.807 (−0.10)**;
**40 rows better by >0.5 dB vs 22 worse.** ⭐ **And the split is coherent, not a wash: every
improvement is a HOT row and every regression is a QUIET one.** Top gains are
`treble-1700_gain-n12` `sweep_drv_-6` **2.54 → 0.39**, `ref-od_gain-n12` `sweep_drv_-18`
**6.90 → 4.92** and `-12` **5.81 → 3.84**, `drive-1700_grunt-boost` `-12` **5.34 → 3.39** — i.e.
precisely the level-dependent rows where the model was railing and the `gain-n12` group session 30
flagged. The regressions are all `sweep_clean` / `sweep_drv_-18` (worst `drive-1430_base-od`
`sweep_clean` **2.94 → 4.34**): a 2.7× lower K moves the whole nonlinear operating point down, so
the quiet end now sits further below clipper onset. ⚠ **OD tilt moved −0.11 → +0.77**, i.e. slightly
bass-heavy again — small, but it is the A3 metric, so re-read it when A3's crossover sub-gate is
next touched rather than treating −0.11 as still current.

**⚙ TOOLING.** `fit_nonlinear.py`: `--start=` is now **repeatable** (session 43's KFENCED had two of
its three seeds silently clipped onto the K fence edge, so its real start diversity was 2 — the
winner happened to be the un-clipped one, which is what kept that result standing); `--square-law`
as described in (2), applied inside `cost()` so every downstream consumer sees the evaluated vector,
and written back into `best.x` before reporting so the printed point can be pasted straight into
`a5_fit_eval.py`. `clipper_rail_selfconsistent.py` gained the A0 derivation (1).
`clean_thd_check.py` gained the full ladder (7). `a5_fit_eval.py`'s `SHIPPED` dict updated to the
new family, with the session-17 one kept as `SHIPPED_S17` so the staleness comparison stays
reproducible.

**⚠ STILL OPEN, carried forward honestly.** (a) The `clipSat` sum at 18 % of the rail wants a
mechanism — it is not a supply violation and (3) shows forcing it back is infeasible, but it is the
one physical prior this family does not satisfy. (b) **gm-sensitivity is still not flat**
(34.1 → 68.1 / 86.6 / 237.9 at gm 0.09/0.12/0.15 mS), so the session-4 `jfetGm` anchor remains
load-bearing — no worse than every prior fit, but unresolved. (c) `clipC11` = 3.69 nF is now BELOW
the schematic 4.7 nF, having been above it (5.72) since session 17.

### ⭐ A3 crossover sub-gate RE-MEASURED at the session-44 baseline (session 45, 2026-07-27) — it survives the new `kInputRef`, every GRUNT-side element is now refuted with a MECHANISM, and two stale-baseline defects surfaced

Analysis + one diagnostic plumbing change. **No shipped constant moved** (`clipR16`'s default IS the
schematic 6k8, verified bit-identical). New tool `analysis/crossover_locus.py`.

**(1) THE GATE WAS RE-MEASURED BEFORE ANYTHING WAS DESIGNED, and the pedal row proves the locator is
sound.** The baseline was checked first (`matrix_grade` reproduces session 44's OD 3.186 / CLEAN
0.427 / ALL 1.807 exactly), then `grunt_span_probe.py::crossover_gate()` re-run on it:

| position | pedal (capture) | model, s38/s40 | model, NOW | error then | error NOW |
|---|---|---|---|---|---|
| flat  | **177.8 Hz / +6.27 dB** | 95.7 / +10.27 | **103.5 / +10.60** | −0.89 oct, +4.00 dB | **−0.78 oct, +4.33 dB** |
| boost | **144.0 Hz / +11.23 dB** | 69.4 / +16.39 | **73.4 / +15.85** | −1.05 oct, +5.16 dB | **−0.97 oct, +4.61 dB** |

The pedal row reproduces `GATE_TARGETS` with no drift note, so **only the model row moved** — the
tool needs no repair. Session 44's `kInputRef` 3.377 → 1.2596 bought **≈0.1 octave** on both rows and
evened the two height errors (5.16/4.00 → 4.61/4.33). Flat and boost still agree to 0.19 oct /
0.28 dB, so session 38's "ONE coherent error, not two" holds at the new baseline. **Still FAIL, and
still the largest measured unexplained OD error.**

**(2) NEW TOOL — `analysis/crossover_locus.py`, the gate's fast inner loop, VALIDATED before use.**
`crossover_gate()` reads a 63-capture report (~6 min/point), which cannot trace a locus. But the
sub-gate is DEFINED at drive-min on `sweep_clean` (−30 dBFS) where the OD path is essentially linear,
so the exact BLEND decomposition (`a3_blend_decompose`) yields the same three transfers in ~20 s per
position. `--selfcheck` is mandatory and is the whole point: probe vs report is **−0.01 oct / +0.03 dB
(flat), −0.03 / +0.10 (boost)** ⇒ the locus is readable. It carries session 38's scope rule in its
docstring (GRUNT-side elements only).

**(3) ⭐ THE MECHANISM IS SIMPLER THAN "CROSSOVER", AND THAT MAKES THE REQUIREMENT A SINGLE NUMBER
PAIR.** `|OD| − |bleed|` per band at drive-min:

| pos | 40 | 80 | 101 | 127 | 160 | 254 | 403 | crossing |
|---|---|---|---|---|---|---|---|---|
| cut   | −21.5 | −13.0 | −11.7 | **−11.2** | −11.5 | −14.1 | −15.9 | **never** |
| flat  | +1.0 | +8.7 | **+9.5** | +9.2 | +8.0 | +2.9 | −1.9 | 37.9 Hz |
| boost | +10.6 | **+14.5** | +14.0 | +12.7 | +10.6 | +4.4 | −1.1 | 21.9 Hz |

In CUT the OD **never reaches the bleed** (≤ −11.2 dB at its own best band), so the span's denominator
is the bleed at every band and `span(pos) ≈ 20log10|1 + OD(pos)/bleed|`. ⇒ **the gate's peak tracks
where |OD(pos)|/|bleed| is MAXIMAL, not where it crosses unity.** So the requirement reads directly:
move that maximum **+0.79 oct and −4.36 dB (flat) / +1.00 oct and −4.72 dB (boost)**.

**(4) ⛔⛔ ALL FOUR GRUNT-SIDE ELEMENTS SCANNED AT THE NEW STATE AND ALL FOUR REFUTED — and the reason
is a SLOPE, which is sharper and more portable than session 38's "off in both coordinates".** Express
the requirement as a trade rate in (peak frequency, peak height): the pedal's point lies at
**−5.5 dB/oct (flat) / −4.7 dB/oct (boost)** from the model's. Each element's locus has its own rate:

| element | trade rate | vs required | verdict |
|---|---|---|---|
| `clipC12` (flat)  | −14.8 → −18.1 dB/oct | **2.7–3.4× too steep**, steepening | asymptote **160.3 Hz at +0.33 dB** — even C12 → 0 never reaches 178 Hz |
| `clipC13` (boost) | −8.4 → −18.5 dB/oct | **1.8–3.9× too steep**, steepening | reaches 146.6 Hz but only at +2.52 dB, **8.7 dB short** |
| `clipC11`         | **+3.9 dB/oct** | **WRONG SIGN** | +0.13 oct over a 2.5× change |
| `clipR16` (new)   | **+4.3 … +5.3 dB/oct** | **WRONG SIGN** | **68× (6800 → 100 Ω) buys 0.10 octave** |

So the family splits: C12/C13 move the right way on both coordinates but pay ~3× too much height per
octave and run out of travel; C11/R16 move height and frequency **together**, so no setting of either
approaches the target. ⚠ **R16's result refuted my own analytic prediction and that is why it was
measured.** Corners scale as `1/(R16 + R18/(1+A0))`, so R16 → 0 should buy 0.62 oct at constant shelf
height (the cap RATIOS are untouched). It buys 0.10, because lowering R16 also raises the closed-loop
gain `−R18/R16`, which lifts `OD(cut)` off the floor and into the denominator, cancelling most of the
move. **R16 is not a frequency knob with a gain side-effect; the two effects are the same size.**
⇒ **the sub-gate cannot be closed from the GRUNT side.** Session 38's verdict stands at the new
baseline, now with a mechanism rather than an observation.

**(5) REACHABILITY ONLY, NOT A SELECTION — the required rate is BRACKETED by two shared OD-path
corners, and neither is the answer.** Both scanned purely to ask "does any first-order LF corner in
the OD path trade at ≈−5 dB/oct":

| | 5.2n / 680p | 3.0n / 400p | 1.8n / 240p | 1.0n / 140p | 0.6n / 80p |
|---|---|---|---|---|---|
| `clipC15` flat | 103.0 / +10.63 | 109.8 / +10.34 | 122.0 / +9.61 | 141.1 / +8.25 | **164.1 / +6.55** |
| `clipC15` boost | 71.8 / +15.95 | 80.4 / +15.23 | 91.5 / +13.86 | 108.9 / +11.63 | 126.3 / +9.19 |
| `trebleC7` flat | 103.0 / +10.63 | 119.7 / +8.32 | 134.5 / +6.12 | 146.1 / +4.08 | 156.1 / +2.54 |

`clipC15` trades at **−3.2 … −6.5 dB/oct** (straddling the required −5.5) and `trebleC7` at
**−10.5 … −13.1** (too steep). At 0.6 nF, C15 puts the flat row **0.12 oct / 0.28 dB from the pedal —
it would PASS the flat gate.**
⛔ **This is NOT a proposal to move `clipC15`, for three independent reasons.** (a) It is a SHARED
OD-path element, so this metric is disqualified from selecting it — and 0.6 nF is a more extreme
version of the 1.5 nF that this same metric already preferred over the β-free 5.2 nF (session 38 item
5, session 37 item (c)). (b) **The boost row does not follow**: at 0.6 nF boost is 126.3 / +9.19, still
0.19 oct low and **2.04 dB short**, while flat is at 0.12 / 0.28. One C15 value cannot close both —
and flat-and-boost agreeing is exactly what makes this one error rather than two. (c) The null gate
disagrees (item 6). **What the pair of loci DOES establish is a shape requirement: the fix needs a
trade rate near −5 dB/oct on BOTH rows simultaneously, and no single first-order LF corner in the OD
path delivers that.**

**(6) ⭐ SAME-SESSION A/B: SESSION 44 IMPROVED THE A3 NULL GATE ON EVERY ROW — including the ORACLE
floor, which is the bound the DATA sets.** `a3_lead_fit.py` re-run against the pre-session-44
parameter family (old `kInputRef` 3.377 + the whole session-17 clipper/JFET set, passed as `--fit`
overrides so the binary, captures and tool are identical on both sides):

| a3_lead_fit row | pre-session-44 family | **shipped (session 44)** |
|---|---|---|
| none (H = 1, k pinned) | 3.854 dB, β −15.07 | **2.377 dB**, β −16.20 |
| broadband OD gain only | 2.354, k = 1.804 | **0.958**, k = 1.555 |
| best causal element | 1.673 (3z/3p) | **0.468** (3z/3p) |
| **ORACLE (floor set by the data)** | **1.280** | **0.220** |

The oracle dropping **5.8×** is the load-bearing number: session 44 did not merely reshape the A3
residual, it made the problem genuinely smaller. ⚠ **The one row that is still asking for something
is the level**: the fit wants **k = 1.555 (+3.84 dB) of broadband OD gain**, and freeing it is worth
2.377 → 0.958 dB. It has shrunk (the old family wanted k = 1.804, +5.13 dB) but has not gone away.
⚠⚠ **And this does NOT reconcile with session 37's recorded figure** for the same tool at 5.2 nF —
"0.904 dB with **k = 0.995** (wants NO level correction), β −17.38". The rms and β match today's
free-k row well (0.958, β −17.29); **`k` does not** (0.995 vs 1.555). Recorded as an open
discrepancy, not explained away — check whether s37's row was a different family or whether the tool
has changed under it before quoting either number.

**(7) ⚠⚠ TWO STALE-BASELINE DEFECTS, BOTH PRE-EXISTING, BOTH CARRIED FORWARD AS GREEN.**
**(a) `build/a3_dec_drv*.csv` were rendered at the OLD `kInputRef`.** Dated 06:18 against the
session-44 commit's 12:56, and their header `amp=0.425139` is exactly `10^(−18/20) × 3.377` — the old
K, confirmed by re-rendering the old family and getting the identical amp (the shipped state gives
0.158574). Session 44 re-baselined `comprehensive_data.json` and the 63-capture matrix but not these,
and **every A3 tool reads them** (`a3_lead_fit`, `a3_phase_solve`, `a3_lead_design`), silently. Item
(6) would have been measured against pre-session-44 data. Regenerated at the shipped state.
⭐ **The lesson: a re-baseline that names one artefact leaves its siblings stale.** Sibling to session
35's "`build/a3_dec_drv*.csv` — the default baseline every phase tool reads — was bit-identical to a
fresh NOMINAL render", which is the same file, the same trap, ten sessions apart.
**(b) ctest is 16/17, NOT 17/17 — `OSValidationTest` fails on the committed tree.** Verified by
stashing this session's changes and re-running at `df14ff3`: **identical numbers**, so it is session-44
fallout, not this session's. At the gate's fixed probe amp 0.35 the alias floors are
**2× −25.6 / 4× −32.1 / 8× −23.6 dB**, so 8× is worse than 2× and the "oversampling works" assertion
fires. Mechanism = **session 17's trap running in reverse**: that session moved the probe amp 0.2 →
0.35 *because* `kInputRef` 3.377 had raised clipper onset; session 44's 2.7× K drop moved the
operating point back down into the documented anomaly zone. ⭐ **A gate with a hardcoded operating
point is not level-invariant — any gain-staging change re-scopes it.** ⛔ **Do not just re-tune the
probe amp to green.** Decide first whether 8× really is worse than 2× at this operating point, which
would be a genuine quality finding for high-drive users and belongs to backlog B2, not to a threshold
edit.

**▶ WHAT THIS HANDS TO A3.** The crossover sub-gate is confirmed live, coherent across flat and boost,
and **unreachable from the GRUNT side** — it is an A3 instrument exactly as session 38 concluded. The
requirement is now stated in a form a candidate can be tested against directly: **move the maximum of
|OD|/|bleed| up 0.79 oct (flat) / 1.00 oct (boost) while dropping it 4.4 / 4.7 dB, i.e. a trade rate
near −5 dB/oct on BOTH rows at once.** `crossover_locus.py --selfcheck --scan KEY=...` is the ~20 s
inner loop for testing that; the acceptance check remains `crossover_gate()` on a full report, and any
value must additionally clear `a3_lead_fit`'s null gate (item 6) before shipping.

### ⛔ GAP #2 REOPENED (session 46, 2026-07-27) — the ~320 Hz notch is the largest single-band mid error, session 19's fix moved AWAY from it, and it is an A3 symptom, not a treble-network one

**User-reported from an FR chart** (`ref-od`, `sweep_drv_-12`): the pedal has a large dip just above
300 Hz before rising to a peak past 400 Hz, and *"our plugin doesn't show this against any capture at
all."* Correct on both counts. Analysis only — **NOTHING in `src/` changed, no constant moved.**

**(1) IT IS THE 320 Hz BAND, AND IT IS THE BIGGEST MID ERROR IN THE MATRIX.** `ref-od`, plugin −
pedal, 1/3-oct: at `sweep_drv_-12` the 320 Hz band is **+4.09 dB** against ≤1.7 dB at every other band
from 100 Hz to 1.3 kHz. It is present at every stimulus level and grows as level falls:
**clean +7.06 / drv_-18 +5.64 / drv_-12 +4.09 / drv_-6 +2.03 dB.**

**(2) ⭐ MEASURED AT FULL RESOLUTION IT IS FAR BIGGER THAN THE BAND GRID SHOWS — up to −24 dB.**
`A.transfer` (nperseg 8192 → 5.9 Hz bins) over 200–520 Hz, notch centre and depth vs its left/right
shoulders. **⚠ Session 19's "−3.4 dB in the capture" is a 1/3-oct read and understates it by up to
20 dB** — 320.0 Hz is not the notch centre, so the band-grid point sample lands on the skirt. Same
class as the A2c-2 lesson (never read a peak's frequency, or a notch's depth, off the 1/3-oct grid).

| capture | sweep_clean | drv_-18 | drv_-12 | drv_-6 |
|---|---|---|---|---|
| `ref-od` | 334 Hz, **−8.96** | 316, −8.42 | 316, **−7.19** | 316, −4.30 |
| `attack-boost` | 334, **−17.41** | 334, −12.96 | 334, −7.95 | 316, −4.68 |
| `attack-cut` | 316, −7.24 | 316, −7.20 | 316, −6.56 | 299, −3.78 |
| `grunt-boost` | 322, **−24.24** | 322, −13.80 | 316, −8.24 | 299, −4.33 |
| `blend-1430` | 334, −3.63 | 316, −3.44 | 316, −2.85 | 299, −1.58 |
| `ref-clean` | **none** | none | none | none |

Four properties, all consistent with a genuine two-path cancellation in the OD path: **absent from the
clean (DIST-off) path entirely**; **monotone in BLEND** (pedal depth vs local neighbours across the
blend sweep at drv_-18: `blend-0700` −0.02 → `0930` −0.26 → `1200` −0.86 → `1430` −2.02 → BLEND max
**−5.58 dB**); **ATTACK sets its depth** (boost −17.4 / flat −9.0 / cut −7.2 at sweep_clean — ~10 dB of
authority); and it **migrates 334 → 299 Hz as level rises**, which no purely linear network can do.

**(3) ⭐⭐ THE MODEL DOES HAVE THE NOTCH — IT IS BURIED UNDER THE CLEAN BLEED. THIS IS NOT A
NOTCH-DEPTH PROBLEM.** `a3_blend_decompose` at the chart's exact operating point (GRUNT cut, drive
noon, −12 dBFS), OD path vs bleed at the BLEND node, dB:

| | 254 Hz | 320 Hz | 403 Hz | 508 | 640 |
|---|---|---|---|---|---|
| **Rd = 0** (schematic) OD | −43.2 | **−63.6** | −45.6 | −46.4 | −51.0 |
| bleed | −32.3 | −32.3 | −32.3 | −32.3 | −32.3 |
| **OD − bleed** | −10.9 | **−31.3** | −13.3 | −14.1 | −18.7 |
| total | −30.98 | −32.56 | −31.80 | −31.04 | −31.48 |
| **Rd = 30k** (shipped) OD | −38.0 | **−39.9** | −42.5 | −46.3 | −51.0 |
| total | −28.69 | −29.30 | −29.98 | −30.75 | −31.35 |

At the schematic value the model's OD path carries a **31 dB** notch at 320 Hz — but the bleed sits
**31 dB above it**, so the total dips only 1.2 dB. ⇒ **the model's OD path is 11–14 dB too weak
relative to the clean bleed through 250–640 Hz, and that is what hides the notch. This is A3, in the
low-mids instead of at LF.** Session 20 inferred exactly this from the band data (*"a bleed-sensitive
sign that the plugin's OD is too weak vs the clean bleed in the mids"*); the decomposition now
measures it directly, at this band, for the first time.

**(4) ⚠⚠ AND SESSION 19'S FIX MOVES AWAY FROM IT. `trebleLadderDampR = 30k` DESTROYS THE NOTCH IN THE
OD PATH** — at 30k the OD path is monotone through 254→640 Hz (−38.0/−39.9/−42.5/−46.3), so the
feature is **unreachable at any bleed level**, even after A3 lands. The premise was a measurement of
the **isolated stage** (37 dB deep) — but session 14's `notch_scope.py` had already found the
*assembled* notch to be ≤2.6 dB, and at the OUTPUT it was never more than ~1.6 dB, i.e. **already ~4×
too shallow before the fix, which then took it to ~0.4 dB.** Sibling of GAP #1b: a stage-transfer
number judged against an output-shaped requirement.

**(5) ⛔ BUT DO NOT MOVE THE CONSTANT — THE FULL MATRIX REFUTES IT, AND MY OWN SINGLE-CAPTURE READ WAS
WRONG.** On `ref-od` alone, Rd = 0 looked like a clean win (127–640 RMS 2.063 → 1.477, full-band
2.569 → 2.461, 320 Hz error 4.71 → 1.67 dB, monotone toward 0). **It does not generalise.** Full
63-capture matrix at `--fit trebleLadderDampR=0` vs the shipped baseline:

| | shipped Rd=30k | Rd=0 |
|---|---|---|
| OD band-RMS | **3.186** | 3.412 |
| CLEAN | 0.427 | 0.427 (bit-identical) |
| ALL | **1.807** | 1.919 |
| OD tilt | **0.77** | 2.04 |
| rows better >0.5 dB / worse | — | **1 / 24** |

⭐ **Split it and the trade is explicit** (104 non-`gain-n12` OD rows): mean |err| at 320 Hz
**3.64 → 1.84 dB** (2× better) while the surrounding **200–520 Hz band-RMS 2.61 → 3.08** (worse).
⇒ **`trebleLadderDampR` is ONE knob doing TWO jobs** — it trades the notch against the broad low-mid
level, and neither end is right. That two-jobs-one-knob signature is the tell that **30k is a
compensating error propping up the OD low-mids broadband**, exactly the defect (3) measures. Same
pattern as `clipC15` at 1.5 nF (session 37): a constant fitted over rows carrying an unfixed defect
lands on the value that compensates for it. ⚠ Note Rd = 0 is **not** the usual "delete the element"
degeneracy — 0 IS the schematic ideal (no unmodelled damping), the physically privileged endpoint —
which is precisely why the single-capture scan looked so convincing. **The matrix is the arbiter.**

**(6) EVEN AT Rd = 0 THE MODEL DOES NOT REPRODUCE IT.** Band-metric depth (320 vs the mean of its
254/403 neighbours) at `ref-od` drv_-12: **pedal −4.17 dB | Rd = 0 −1.15 | Rd = 30k +0.03.** So Rd = 0
only stops making it worse; it is still 3.6× too shallow. **The fix is A3, not this constant.**

**▶ WHAT THIS HANDS TO A3 — A NEW ACCEPTANCE CHECK, AND IT MEASURES SOMETHING NO EXISTING A3 GATE
DOES.** `a3_lead_fit` reads null DEPTH at LF, G1/G2 read the DRIVE axis, `a3_level_axis` reads the
LEVEL axis, and `crossover_gate` reads the LF crossover FREQUENCY. **None reads the OD/bleed ratio in
the LOW-MIDS**, and (3) shows it is 11–14 dB off there. **NEW A3 SUB-GATE: at GRUNT cut / drive noon /
−12 dBFS the model's OD path must come within a few dB of the bleed over 250–640 Hz, such that its
~320 Hz notch survives to the output at ≥4 dB (band metric) / ≥7 dB (full resolution).** The table in
(2) is the target set — it is cheap, it is a *feature* rather than an aggregate, and its ATTACK and
BLEND monotonicity give three independent rows to check a candidate against.
**▶ ORDER OF WORK: (a)** leave `trebleLadderDampR` at 30k; **(b)** fix A3's OD/bleed balance;
**(c)** THEN re-fit `trebleLadderDampR` — the trade in (5) should dissolve and it should be free to
return toward the schematic 0, at which point the notch appears. **Re-fitting it before A3 will just
re-find a compensating value.**

### A3 step 4 (session 47, 2026-07-27) — A3's shape, measured WHOLE-BAND for the first time; the carrier is located and the notch mechanism is confirmed; NOTHING SHIPPED

Executing step (b) above. **Analysis + tooling only — no `src/` file changed, no constant moved,
ctest unchanged at 16/17** (the pre-existing session-44 `OSValidationTest` failure; verified
identical). Baseline verified first: `a3_blend_decompose` rebuilt and all five
`build/a3_dec_drv*.csv` reproduce bit-identically at the shipped defaults.

**(1) ⭐⭐ THE INSTRUMENT THAT WAS MISSING: A3 AS A CURVE, NOT A FEATURE.** Every A3 gate reads ONE
feature — `a3_lead_fit` the null DEPTH, G1/G2 the DRIVE axis, `a3_level_axis` the LEVEL axis,
`crossover_gate` the LF crossover FREQUENCY, GAP #2's sub-gate the 250–640 Hz ratio. None states the
OD/bleed ratio as a curve over the whole measured band, which is how *"A3 is below ~200 Hz"* survived
to session 46 and how the 250–640 Hz half of it was found by a user reading an FR chart rather than
by a gate. New tool **`analysis/a3_shape_gate.py`**: `a3_phase_solve` already solves, per band, the
scale `s` the model's OD magnitude needs for the pedal's five measured drive totals to be reproduced,
so **`s(f)` IS the A3 defect in dB** and the gate is `20log10 s(f) = 0` at every band. `--selfcheck`
reproduces the shipped baseline to 0.027 dB and is mandatory before any locus is read.

**(2) ⭐⭐ A3 IS NOT AN LF GAP. THE MODEL'S OD PATH IS TOO WEAK RELATIVE TO THE BLEED AT EVERY SINGLE
BAND, AND THE SHAPE IS A BATHTUB.** `20log10 s`, GRUNT cut / BLEND max / −18 dBFS, over the five
drive captures:

| f Hz | 20 | 25 | 32 | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **20log10 s** | +10.40 | +6.81 | +4.31 | +3.15 | +2.64 | +2.72 | +3.57 | +4.43 | +5.05 | +5.34 | +5.20 | +4.68 | +7.60 | +9.04 |

**SCORE (RMS over the 14 CORE bands) = 5.808 dB.** Minimum +2.64 dB at 50 Hz; it rises to +5.2 dB
through 127–254 and +7.6/+9.0 at 403/508, and to +10.4 dB at 20 Hz. It decomposes into at least
three components, and **no single first-order corner produces this**: a broadband ~+2.7 dB floor, a
mid/HF rise of ~+6 dB from 64 → 508 Hz, and a steep LF rise below ~40 Hz (≈9.5 dB/oct from 32 to
20 Hz, far steeper than any first-order high-pass).

⚠ **READ THE INTERVAL, NOT THE POINT.** `s` is only as identified as the cancellation is deep. The
joint (s, θ) region within +0.25 dB of the optimum **spans 1.0 at 640 and 806 Hz**, so those bands do
not constrain `s` at all and are printed as INFO; 320 Hz is the TrebleAttack-notch band and is
excluded as everywhere else in A3. **The CORE set is fixed ONCE from the shipped baseline and is
never re-derived per candidate** — a score whose own band set moves with the candidate lets the worst
candidate win by shrinking its scoring set (the session-33 self-selecting-score trap). At 403 and 508
the intervals are [1.82, 2.86] and [1.81, 3.53], i.e. **s ≥ 1.8 robustly** — those bands are real
evidence, not tail noise.

**(3) ⚠⚠ AND THE TOOL THAT FITS THE A3 ELEMENT DE-WEIGHTS EXACTLY WHERE THE DEFECT IS LARGEST.**
`a3_lead_fit.py` sets `CORE_HI = 254` and `WEAK_W = 0.15`, so every band above 254 Hz enters its
objective at 15 % weight. Its stated reason — *"above 254 Hz mu < 1 so the total is bleed-dominated
and the band constrains the tail, not the fit"* — **is the GAP #2 category error**: the total being
bleed-dominated *is the defect*, not a reason to ignore the band. It is not wholly wrong (640/806
genuinely carry no information, per (2)), but 403 and 508 do, and they are the two largest errors in
the whole curve. **Weight a band by its measured identifiability, not by a fixed frequency cutoff.**

**(4) LOCALISED PER STAGE — the bridged-T is the single largest roller-off across exactly the span
where the deficit lives.** `od_phase_probe` table C (cumulative |tap/clean|, drive-min, GRUNT cut),
per-stage increment from 127 Hz → 400 Hz: **jfet +4.37 | treble −7.33 | drive 0.00 | clipper +9.55 |
recovery (bridged-T) −11.28 | SK ×2 0.00**, netting −4.71 dB where the pedal's own ratio is flat. The
IC2_B bridged-T reaches **−18.2 dB by 403 Hz** on its way to its −28 dB / 717 Hz notch.

**(5) ⭐ `btC17` IS THE CARRIER, AT A VERIFIED INTERIOR MINIMUM.** `FitParams` already declares all
four bridged-T values as FIT parameters (*"risk register #1 … the depth is highly tolerance-sensitive
… to be reshaped to whatever the capture actually shows, including much shallower than ideal"*); they
were simply never reachable from `a3_blend_decompose`, which now has them (plumbing verified BOTH
ways — default bit-identical to the prior baseline AND to an explicit-nominal render, and an override
provably differs). Shape score vs `btC17`:

| btC17 | 22n (schematic) | 15n | 12n | 11n | **10n** | 9n | 8n | 4n7 |
|---|---|---|---|---|---|---|---|---|
| score dB | 5.808 | 4.092 | 3.605 | 3.520 | **3.490** | 3.521 | 3.621 | 4.438 |

Worse on **both** sides — not the "delete the element" degeneracy. At 10 nF the whole 64–508 Hz span
collapses from +2.72…+9.04 dB to **+0.79 / +1.00 / +1.11 / +0.96 / +0.52 / −0.34 / −1.53 / −0.30 /
−0.34 dB**, i.e. the mid/HF component of (2) is *entirely* accounted for. The LF component is
untouched (20 Hz +10.40 → +10.13), exactly as it must be — the bridged-T is flat below its 72 Hz
corner. **The other three bt values are refuted:** `btC16` is worse at 1.5n (6.241) and reshapes
badly at 3.3n; `btR23` improves only monotonically toward 10k (5.808 → 5.152) without moving 64–254 at
all, which is the degeneracy signature; `btR22` deepens the scoop.

**(6) ⭐⭐ GAP #2's SUB-GATE IS MET, AND SESSION 46's PREDICTION IS CONFIRMED.** At the sub-gate's own
operating point (GRUNT cut / drive noon / −12 dBFS), OD − bleed in dB:

| | 254 | 320 | 403 | 508 | 640 | band-metric notch depth |
|---|---|---|---|---|---|---|
| shipped | −5.62 | −7.62 | −10.19 | −13.96 | −18.72 | **+0.03** |
| `btC17=10n` | **+0.59** | −0.67 | −2.29 | −4.57 | −7.43 | +0.07 |
| `btC17=10n` + `Rd=0` | −4.64 | **−24.35** | −5.41 | −4.68 | −7.41 | **−2.82** |
| *pedal* | — | — | — | — | — | *−4.17* |

The requirement *"the OD path must come within a few dB of the bleed over 250–640 Hz"* is **met**. And
with `trebleLadderDampR` back at the schematic 0 the ~320 Hz notch finally survives to the output:
band-metric depth **+0.03 (shipped) → −1.15 (Rd = 0 alone, session 46) → −2.82 (both)** against the
pedal's −4.17 — from 0.7 % to 68 % of the pedal's depth. **Session 46 item (5)'s prediction that the
`trebleLadderDampR` trade would dissolve once A3's low-mids were supplied properly is confirmed.**

**(7) ✅ INDEPENDENT CORROBORATION FROM THE NULL GATE — the unexplained broadband-gain demand halves.**
`a3_lead_fit` at `btC17=10n` vs shipped: the **no-element baseline rms 2.377 → 1.741 dB** (the model
explains the raw captures better with nothing added), and **the broadband OD gain the fit asks for
collapses from k = 1.555 (+3.84 dB) to k = 1.203 (+1.61 dB)**. That k was recorded in session 45 as an
open discrepancy against session 37's k = 0.995; over half of it turns out to be *not* a level error
at all but the mid/HF scoop. ⚠ Against that: the null-FREQUENCY match of the no-element row degrades
4/5 → 2/5 (the deepest band moves to 64 Hz at the two lowest drives), and best-causal / oracle are
unchanged (0.468 → 0.500 / 0.220 → 0.262). btC17 does not touch A3's LF half, and slightly moves
where the LF null lands.

**(8) ⛔⛔ AND THE FULL 63-CAPTURE MATRIX DOES NOT SUPPORT SHIPPING IT. NOTHING WAS SHIPPED.**
Four full runs. Headline (matrix_grade): shipped **OD 3.186 / CLEAN 0.427 / ALL 1.807, tilt 0.77** →
`18n` **3.187 / 0.427 / 1.807, tilt 0.42** (1 row better, 0 worse) → `15n` **3.241 / 1.834, tilt 0.07**
(3 better, 8 worse) → `10n` **3.534 / 1.980** (6 better, **35 worse**) → `10n + Rd=0` **3.365 / 1.896**
(5 better, 26 worse). CLEAN is bit-identical throughout — the bridged-T is OD-path, so the change is
surgical by construction.

**⭐ BUT SPLIT BY ROW GROUP AND THE AGGREGATE IS CONTROLLED BY ONE DEFECTIVE GROUP** (band-RMS over
`matrix_grade.rows_of`):

| group | 22n (ship) | 18n | 15n | 10n | 10n+Rd0 |
|---|---|---|---|---|---|
| ALL OD (120) | 3.567 | **3.551** | 3.584 | 3.779 | 3.674 |
| non-`gain-n12` (104) | 3.372 | 3.288 | 3.245 | **3.206** | 3.422 |
| ..GRUNT cut (80) | 2.526 | 2.421 | **2.372** | 2.455 | 2.299 |
| ..GRUNT flat/boost (24) | 4.990 | 4.925 | 4.881 | **4.671** | 5.398 |
| `gain-n12` (16) | **4.641** | 4.925 | 5.280 | 6.347 | 5.012 |

**Every group except `gain-n12` improves as C17 falls; `gain-n12` degrades monotonically and by more
than everything else gains, and it alone turns the ALL-OD aggregate around.** Those 16 rows carry a
separately-documented, still-unlocalised, level-dependent defect (session 30's HF collapse in
`ref-od_gain-n12`, parked in §0 as "A3-adjacent"). This is the same signature session 36 recorded for
`clipC15` — *"a large win everywhere the model is otherwise sound, the regression confined to the 16
`gain-n12` rows"* — which session 37 then vindicated when those rows improved by 0.99 dB once C15 was
corrected. **It is still not sufficient grounds to ship**: the aggregate is the arbiter (session 46
item 5), a subset argument is exactly what this project has been burned by, and the shape gate's own
optimum (10n) is where the matrix is clearly worst. Recorded as a located, unshipped candidate.

**(9) THE NOTCH-FREQUENCY COST IS AVOIDABLE.** `btC17` alone moves the notch 717 → 1063 Hz
(f0 ∝ 1/√(C16·C17)), and `FitParams` warns that the notch FREQUENCY is far more trustworthy than its
depth. Scaling the pair the other way holds f0 fixed while lowering the zero's Q
(Qz = √(C17·R22·R23/C16)/(R22+R23)): **`btC17=10n` + `btC16=1.496n` scores 3.520 against 3.490, i.e.
the same, with the notch left at 717 Hz.** Prefer this form for any future candidate. ⭐ Note that at
that point `s` at 508 and 806 Hz reads 1.063 and 1.019 with intervals that now *include* 1.0 — once
the shape is corrected those bands stop identifying a defect at all.

**(10) ⚠ SCOPE NOTE — the crossover sub-gate is NOT an argument here, in either direction.**
`crossover_locus.py` (self-check PASS: −0.01 oct/+0.03 dB flat, −0.03/+0.10 boost) puts the drive-min
GRUNT-span peak at **103.0 Hz/+10.63 (flat)** and **71.8/+15.95 (boost)** at 22n, moving to
**107.7/+13.38** and **79.9/+18.69** at 10n — the right way in frequency (+0.06/+0.15 oct) and the
wrong way in height (+2.75/+2.74 dB against a −4.36/−4.72 requirement). **But that metric rewards any
element that ATTENUATES the OD path and is explicitly disqualified from selecting a SHARED element**
(session 38 item 5, its own docstring), and `btC17` is shared. Reported as information only.

**▶ NEXT, IN ORDER.**
**(a) The 16 `gain-n12` rows are now ON A3's CRITICAL PATH and should be the next item**, ahead of
further A3 element work. They are the only group voting against a change that improves every other
group monotonically, and their defect (session 30, level-dependent HF collapse) has been parked since
it was found. Localise it; then re-run this locus.
**(b)** ~~Keep `btC17 ≈ 10 nF` (in the f0-preserving form of (9)) as the located A3 low-mid
candidate~~ ⛔ **SUPERSEDED — `btC17` is REFUTED, see "A3 step 5" (session 49).** The f0-preserving
form was graded on the full matrix and does NOT improve the non-`gain-n12` OD rows (2.909 → 2.932),
and a Pareto scan over all four bt elements shows the required low-mid lift is unreachable at fixed f0
without ≥3.66 dB of side effect at 1–13 kHz. ⚠ Item (9)'s "prefer this form" recommendation is
**VOID**: it was scored over bands ≤806 Hz and could not see that the form adds +3.7 dB at 3–5 kHz.
**(c)** A3's LF half — the +10.4 dB at 20 Hz / +6.8 at 25 / +4.3 at 32, ≈9.5 dB/oct and steeper than
any first-order high-pass — is untouched by all of the above and is what remains of the classic
sessions-29-38 A3. The shape gate now measures it on the same axis as everything else.
**(d)** `trebleLadderDampR` stays at 30k until (a)/(b) land, then re-fit it — (6) shows the trade does
dissolve, so this ordering is confirmed, not just assumed.
**(e)** Then A4 re-grade + GATE-9, the `OSValidationTest` decision (session 45 item 7b), then B / C / D.

### A3 step 5 — `btC17` REFUTED ON REACHABILITY (session 49)

⛔⛔ **The session-47 candidate is CLOSED, and not on the subset argument it was parked under.** The
bridged-T cannot supply A3's low-mid lift without a broadband HF side effect the matrix refuses, and
that is a property of the NETWORK, not of one value. Analysis + tooling only; **nothing in `src/`
changed**, ctest unchanged at 16/17 (the pre-existing session-44 `OSValidationTest` failure).

**(1) THE VERIFICATION RENDER COMPLETED AND THE SPLIT DOES NOT SHOW THE PREDICTED SIGNATURE.** Session
48's background render (`analysis/reports/s48_btC17_10n_f0.json`, `btC17=10.0e-9` + `btC16=1.496e-9`,
63/63 captures) graded against the shipped baseline on `matrix_grade`'s group split:

| subset | rows | shipped | btC17 f0-pair | 10n alone |
|---|---|---|---|---|
| OD | 120 | 3.186 | 3.495 | 3.534 |
| CLEAN | 120 | 0.427 | 0.427 (bit-identical) | 0.427 |
| **OD ex `gain-n12`** | 104 | **2.909** | **2.932** | **3.190** |
| OD `gain-n12` [bad] | 16 | 4.991 | 7.154 | 5.765 |

The resume gate was *"if `OD ex gain-n12` improves monotonically while only the known-bad group
regresses, btC17 has a real case"*. **It does not improve** — it is flat (+0.023 dB, inside the
0.144 dB take-to-take floor) — so the decision never depended on the `gain-n12` exclusion at all.

⚠ **DO NOT compare these to session 47's `3.372 → 3.206`.** Those came from an ad-hoc split predating
`matrix_grade`'s group feature (session 47 also quotes "ALL OD 3.567" beside "OD 3.186" — two
different metrics in one entry). Measured on ONE tool, neither form improves the good rows.

**(2) ⭐ UNDERNEATH THE FLAT AGGREGATE IS A 76-vs-16 ROW TRADE.** Non-`gain-n12` OD, by GRUNT:

| GRUNT | rows | shipped | f0-pair | Δ | tilt shipped → f0-pair |
|---|---|---|---|---|---|
| cut | 76 | 2.373 | 2.639 | **+0.266** | +0.73 → −1.49 |
| flat | 12 | 3.724 | 3.551 | −0.173 | +1.24 → −1.62 |
| boost | 16 | 4.840 | 3.856 | **−0.985** | +7.02 → +3.71 |

So it is the **mirror image of `clipC15` in session 37**: there, the candidate helped GRUNT cut and
regressed the 28 flat/boost rows carrying GAP #3b; here it helps flat/boost and regresses the 76-row
cut baseline. The aggregate is flat only because cut outnumbers boost 76:16. Every group's tilt drops
~2.2 dB — on boost (+7.02 too bass-heavy) that is a large win; on cut (+0.73, already near zero) it
**overshoots to −1.49 bass-light**. That is the mechanism of the trade.

**(3) THE CUT REGRESSION IS LOCALISED, NOT BROADBAND** (76 GRUNT-cut rows, band-restricted band-RMS):

| | shipped | f0-pair | Δ |
|---|---|---|---|
| full graded band | 2.373 | 2.639 | +0.266 |
| **excluding 3225/4064/5120 Hz** | 2.278 | **2.164** | **−0.114** |
| those 3 bands only | 2.204 | 4.040 | **+1.836** |

Over all 104 good rows: full 2.909 → 2.932, **ex 3–5.5 kHz 2.859 → 2.564 (−0.295)**. ⇒ **the low/mid
half of the change is real and good**; a localised +1.5 dB HF regression cancels it in the aggregate.

**(4) ⚠⚠ AND MY FIRST EXPLANATION OF THAT WAS WRONG — corner arithmetic said "the upper shoulder moved
into the band" (R23·C16 7.09 → 3.22 kHz). The ORACLE says otherwise.** `bridged_t_tf` on the report's
own 1/3-oct grid, change vs shipped (positive = less attenuation = OD lift), mean over each region:

| form | 250–640 Hz | 403–2032 | 3.2–5.2 kHz | 6.5–12.9 kHz | notch f0 |
|---|---|---|---|---|---|
| `btC17` 10n alone | **+8.35** | +3.95 | −0.51 | −0.18 | 717 → **1063 Hz** |
| + `btC16` 1.496n (f0 held) | +7.70 | **+8.16** | **+3.69** | **+1.57** | 717 Hz |
| + `btR22` 220k (f0 held) | **+1.46** | +1.78 | −0.17 | −0.11 | 717 Hz |
| + `btR23` 72.6k (f0 held) | +6.57 | +6.75 | +3.91 | +1.65 | 717 Hz |

It is not a shoulder shift: scaling `btC16` makes the scoop **shallower everywhere above the notch**,
i.e. it converts a targeted low-mid lift into a broadband upper-band lift. And `btR22` — which holds
f0 *and* both shoulders exactly — buys only +1.46 dB, i.e. it holds f0 by nearly cancelling the whole
change. **10n alone is the only targeted form, and it pays f0: 320 Hz–2.5 kHz worsens by +0.4…+1.6 dB**
(per-band, 104 rows), which is why it grades worst of the three. **Holding f0 is REQUIRED, not
optional** — worth −0.03…−0.81 dB over 403 Hz–2 kHz.

**(5) ⭐⭐ THE REFUTATION, MADE GENERAL — a Pareto scan, not four hand-picked forms.** All four bt
elements over ±1 decade (13-point log grid, 20 736 combinations), keeping the 1469 that hold the
schematic notch f0 = 716.3 Hz within 5 %; score = mean lift over 250–640 Hz vs max |change| over
1016–12902 Hz:

| 1–13 kHz budget | max achievable 250–640 Hz lift |
|---|---|
| ≤0.5 dB | +0.60 |
| ≤1.0 dB | +1.41 |
| ≤2.0 dB | +2.50 |
| ≤3.0 dB | +3.88 |
| unbounded | +18.89 |

**Of the 631 settings reaching >+4 dB of lift, the MINIMUM HF change is 3.66 dB.** The shape gate puts
the need at 250–640 Hz at **+4.68…+9.04 dB** (`s` at 254/403/508), and the matrix already refuses the
pair's +3.69 dB of HF lift. ⇒ **at fixed f0 the bridged-T cannot deliver the required low-mid lift for
less than ~3.7 dB at 1–13 kHz. The two are structurally coupled; no value of any bt element separates
them.** Same form of result as session 38 item 4 (the GRUNT-cap locus off the curve in both
coordinates) and session 45 item 4 (the required slope). **A3's low-mid carrier must be an element
whose effect is confined to ≲1 kHz — the bridged-T is not it.**

**(6) ⭐⭐ ROOT CAUSE OF THE WRONG PREFERENCE: EVERY A3 INSTRUMENT STOPPED AT 806 Hz.** The band list in
`a3_blend_decompose.cpp`, `a3_phase_solve.PROBE_BANDS`, and `a3_shape_gate.CORE` all ended at 806 Hz,
so a candidate's side effects above 1 kHz were **unmeasurable by construction**. Session 47 chose the
f0-pair on a CORE score of 3.520 vs the shipped 5.808 while it was adding +3.7/+1.6 dB at 3–13 kHz,
every one of those bands outside the tool's domain. ⭐ **THE LESSON, one range up from session 33's own
extension to 806 Hz and session 32's tail finding: a gate whose DOMAIN is narrower than its
candidate's REACH cannot discriminate — widen the domain, don't trust the score.** This is "measure
the curve, not the feature" applied to the curve's *extent* rather than its shape.

**(7) ✅ THE BLIND SPOT IS FIXED, AND THE FIX IS VERIFIED BOTH WAYS.** Band lists extended to
**1016 / 1613 / 2560 / 4064 / 6451 / 10240 Hz** (2/3-oct spaced — these catch a broadband multi-dB
side effect, which is what this family produces; ⚠ do NOT read a narrow feature off that grid, the
session-46 error). `a3_shape_gate` gained a `SIDE` group, printed beside the score and **never
scored**. Three deliberate design decisions:
  - **β is now pinned to `BETA_BANDS` (= the original 17).** `fit_beta` sums each band's residual over
    the band list, so letting the monitors in would move β — and β moves every band's `s`, so adding
    an OBSERVER would have silently redefined the SCORE and broken comparability with every recorded
    number. **An observer must not participate.**
  - **The flag is on the CHANGE from shipped, not on |20log10 s|.** The shipped model already reads
    +11.31/+10.60/+11.11 dB at 1016/2560/10240, so an absolute threshold fires on the baseline and
    discriminates nothing (first draft did exactly that). `SIDE_BASELINE_DB` records the shipped row.
  - **NOT folded into CORE with a low weight** — that is session 47 item 3's error (`CORE_HI`/`WEAK_W`
    de-weighted by a frequency cutoff precisely where the defect was largest). Weight by measured
    identifiability or not at all. These bands are poorly conditioned (fit rms reaches 5.5 dB at
    6451; 4064 and 10240 are not identified), so a SIDE delta is an **indicator that a candidate
    reaches above 1 kHz, never a measurement of how much**. The matrix stays the arbiter.

  **Verification:** the 17 pre-existing bands are **bit-identical** across all five drive CSVs after
  the extension; `--selfcheck` still reproduces the baseline (worst deviation **0.027 dB**, score
  5.808 vs 5.800, **PASS**) with all SIDE deltas at +0.00; and on the rejected candidate the CORE
  score reproduces session 47's **3.520 exactly** while the flag now fires at **−8.44 dB at 1016 Hz**.
  ⭐ **Independent corroboration:** that −8.44 dB (the model needing *less* OD boost, i.e. the
  candidate *added* OD level) matches the bridged-T oracle's predicted **+8.45 dB** at the same band
  to 0.01 dB — two unrelated derivations of the same mechanism.

**(8) WHAT THIS DOES AND DOES NOT SETTLE.** Settled: `btC17`/the bridged-T is not A3's low-mid carrier
(5); the f0-pair does not ship; the shape gate's domain (6)/(7). **NOT settled:** the low-mid defect
itself is still real and still unlocalised — GAP #2's sub-gate (OD within a few dB of the bleed over
250–640 Hz) is unmet, and (3) shows a genuine −0.295 dB is available there to whatever element can
supply it *without* reaching above 1 kHz. The 4 `gain-n12` re-captures are still owed but are **no
longer blocking any A3 decision**.

**▶ NEXT, IN ORDER.**
**(a)** Find the A3 low-mid carrier under the (5) constraint: **it must lift 250–640 Hz by ~+5 dB with
≤~1 dB change above 1 kHz.** Run every candidate through `a3_shape_gate` and read the **SIDE row as
well as the score** — a candidate that flags is a matrix question before it is an improvement.
**(b)** A3's LF half (+10.40 dB at 20 Hz, ≈9.5 dB/oct) is untouched by all of this and remains the
classic sessions-29–38 A3.
**(c)** `trebleLadderDampR` stays at 30k — session 47 item 6 still says the trade dissolves once A3's
low-mids are supplied, and (5) means that supply is not coming from the bridged-T. Measure, don't assume.
**(d)** Re-capture `ref-od_gain-n12.wav` + `level-0930/1430/1700_gain-n12_base-od.wav` (4 files;
`level-0700_gain-n12` is the LEVEL=0 null) when convenient — no longer on the critical path.
**(e)** Then A4 re-grade + GATE-9, the `OSValidationTest` decision (session 45 item 7b), then B / C / D.

### A3 step 6 — the carrier search space is CLOSED to the post-clipper region, and it is EMPTY (session 50)

Executing the session-49 "▶ NEXT (a)" as a **reachability question asked of the whole OD path**, not a
value hunt, plus the component budget that should have preceded every candidate since session 34.
**Analysis + tooling only — nothing in `src/` changed**, ctest unchanged at 16/17 (the pre-existing
session-44 `OSValidationTest` failure). New tools `analysis/a3_carrier_scan.py` and
`analysis/a3_component_budget.py`. Baseline verified first: `a3_shape_gate --selfcheck` PASS at 5.808
(worst deviation 0.027 dB) before any locus was read.

**(1) THE COMPONENT BUDGET, AND beta's ROLE IN IT — SETTLED.** `a3_component_budget.py` sweeps the
pedal's bleed level and reports both the resulting `s(f)` curve and the joint fit residual, so beta's
identifiability is measured rather than assumed. Optimum **beta = −16.75 dB** (interior — the tool
refuses to report an interval when the optimum lands on the sweep edge, which the first draft did);
identified interval **[−17.25, −16.50]** at the pedal's own **0.144 dB take-to-take capture floor**.
The model ships −16.93, *inside* it.

| component | definition | value | span across beta's identified interval |
|---|---|---|---|
| **C1** broadband floor | mean of 50/64 Hz | **+2.68 dB** | 0.07 dB — rock solid |
| **C2** low-mid rise | mean 101–508 Hz, over C1 | **+3.20 dB** | 0.68–1.10 dB — solid |
| **C3** LF rise | 20 Hz, over C1 | **+7.86 dB** (9.18 dB/oct, 32→20) | 2.51 dB — the softest |

⭐ **beta accounts for at most 0.26 dB of the floor**, so **C1 is a real broadband OD-level deficit
that no bleed level explains.** Independently corroborated from the other direction: `a3_lead_fit`'s
free-gain row wants **k = 1.591 (+4.03 dB)** of broadband OD gain at the shipped state.

⚠ **And no single component is more than ~40 % of the score, so A3 will not close on one element.**
Score if each were fixed perfectly: **C1 alone 3.52 | C2 alone 4.34 | C3 alone 4.77 | all three 0.26**
(against 5.82 as it stands).

**(2) ⭐⭐ THE STRUCTURAL RESULT: ONLY A POST-CLIPPER LINEAR ELEMENT CAN SUPPLY `s(f)` AT ALL.** `s` is
ONE scale per band that must reproduce all five drive totals, and the shipped model already does that
to 0.094 dB rms — so whatever is missing is, as measured, drive-INDEPENDENT. The scan reports
`drvspr` (max-minus-min of the delivered lift across drive 0.0/0.5/1.0) and the split is total:

| region | elements | drvspr |
|---|---|---|
| **post**-clipper | `clipC15`, `btR22`, `btR23`, `btC16`, `btC17` | **0.00 at every value** |
| **pre**-clipper | `trebleC7`, `trebleLadderDampR`, `clipC11`, `jfetGm`, `clipSat*` | **4–19 dB** |

A post-clipper linear element multiplies |OD| by the same factor at every drive; a pre-clipper one
moves the clipper's operating point, so its delivered lift is a different number at every drive and
cannot be represented as a single `s` no matter what its average is.

**(3) ✅ AND THAT PREDICTION IS CONFIRMED QUANTITATIVELY — the cheap screen is EXACT for post-clipper
candidates and useless for pre-clipper ones.** Screen (`resid`, no beta/theta re-fit) vs the real
`a3_shape_gate` score:

| candidate | loc | drvspr | screen | real SCORE | error |
|---|---|---|---|---|---|
| shipped | — | 0.00 | 5.81 | 5.808 | 0.00 |
| `clipC15` inert | post | 0.00 | 4.68 | 4.676 | 0.00 |
| `btC17=10n` | post | 0.00 | 3.49 | **3.490** (session 47's own figure) | 0.00 |
| `clipC11=10n` | pre | 8.50 | 3.26 | **5.922 (WORSE)** | 2.66 |
| `jfetGm=0.4e-3` | pre | 9.71 | 2.88 | **5.661 (nil)** | 2.78 |

⚠ **Both pre-clipper candidates moved the fitted beta by 0.7 dB (−16.80 → −16.10) and TILTED the
curve** rather than lifting it — `clipC11=10n` overshoots 50 Hz to **−3.94 dB** while making 508 Hz
**worse** (+9.09 → +13.82). A screen that averages over the target span cannot see that. The metric
was changed to a mean-removed one (beta absorbs any flat part, so only SHAPE can count) and it still
does not rank pre-clipper candidates correctly — **the honest statement is that `LIFT`/`SIDE`/`drvspr`
are the trustworthy columns and any pre-clipper row needs Tier 2 regardless.**

**(4) ⛔ NO REACHABLE ELEMENT SUPPLIES C2.** The requirement is **+5.91 dB over 101–508 Hz for ≤1 dB
above 1 kHz**. Nothing in the table meets it. The best rows, all failing on one axis or the other:

| element | lift | side | verdict |
|---|---|---|---|
| `btC17=10n` | +5.90 | 1.83 | already refuted on the matrix (session 49); reproduced here |
| `btR22=47k` | +5.79 | 3.96 | side |
| `jfetGm=0.4e-3` | +4.68 | 2.26 | side, drvspr 9.71, and the gm anchor is load-bearing (session 44) |
| `clipC11=10n` | +4.50 | 1.34 | drvspr 8.50; real score is WORSE |
| `trebleC7=10n` | +2.00 | **0.06** | the only genuinely side-effect-free lever, and it delivers 34 % of the need — by adding **+13.84 dB at LF**, a 2.2× overshoot of C3 |
| `clipC15=100n` | +0.14 | 0.00 | LF-only, ±3.45 dB of authority — a C3 lever, not a C2 one |

⇒ **The post-clipper region is the only one that can supply C2, and it contains exactly three things:
`OdCoupling` (LF-only), the bridged-T (refuted on reachability), and two Sallen-Key LPFs (HF-only, and
not exposed as fit parameters at all). A3's C2 carrier is therefore a MISSING element** — the same
finding as `PedalChain::OdCoupling` itself, which was absent from the model entirely until session 36.
This is session 49's argument one level up: not "this element cannot", but "no element in the only
region that could, can".

**(5) ⭐⭐ THE SHAPE GATE IS NOT A VALID INSTRUMENT FOR C3 — and this nearly shipped a false positive
in one session rather than three.** Reverting `clipC15` to its **schematic 2u2** looks like the best
result of the session: shape score **5.808 → 4.676**, SIDE **+0.00 dB** (bit-clean above 1 kHz), C1
floor **+2.65 → +1.29**, C3 **+10.40 → +5.22**, C2 untouched (254/508 move 0.06/0.01 dB), the fitted
beta unmoved, and the free-k demand collapsing **1.591 (+4.03 dB) → 1.046 (+0.39 dB)** — i.e. it
appears to dissolve C1 and half of C3 at once, at a **schematic** value, retiring session 36's 423×
departure. **It does not survive the null gate:**

| state | shape score | null bands | free-k |
|---|---|---|---|
| `clipC15 = 5.2 nF` (shipped) | 5.808 | **4/5** (7.3 dB depth err) | +4.03 dB |
| `clipC15 = 2u2` (schematic) | **4.676** | **1/5** (10.4 dB) | +0.39 dB |
| `clipC15 = 2u2` + a fitted 1st-order HP | — | **4/5, 1.1 dB, PASS** | — |

⭐ **The third row is the resolution: with C15 inert, `a3_lead_fit` re-discovers a first-order ~30 Hz
highpass and the null comes straight back.** The two states are the same model; the shape gate simply
rewards the extra LF |OD| that deleting the highpass provides, while being **blind to the phase that
places the null** (its own docstring says so: *"a level/shape gate, not a phase gate"*). ⇒ **`clipC15`
stays at 5.2 nF**, and — the durable lesson — **C3 must be gated on the NULL (`a3_lead_fit`), never on
the shape curve.** At LF the OD and bleed are near anti-phase, so the total is dominated by
cancellation geometry, which is a phase property the shape gate does not score. The shape gate is the
right instrument for **C1 and C2 only**.

**(6) SCOPE LIMITS OF THE SCAN, RECORDED HONESTLY.** It runs at **GRUNT cut / −18 dBFS** (A3's own
measurement condition), so any level-dependent lever reads zero: `railPos`/`railNeg` move **exactly
0.00 dB** at every value including 1000 (rails off). ⚠ That is the operating point, **not** a dead
flag — liveness-checked per L-009 at −6 dBFS / drive max, where `railPos` 2.7 → 1.0 moves the OD path
**8.95 dB**. So the scan is a valid statement about A3 as measured, and NOT a general statement about
the OD path. Similarly it says nothing about GRUNT flat/boost.

**(7) A NOTE ON COMPARABILITY.** `a3_lead_fit`'s no-element rms reads **2.591 dB** here against session
47's 2.377 at the same shipped state. Not a regression — session 49 extended the probe band list from
17 to 23 bands, and this metric is an RMS over them ("22 bands × 5 drives"). Do not carry session 47's
figure forward across that change.

**▶ NEXT, IN ORDER.**
**(a)** C2's carrier is a **missing post-clipper element**. Before hypothesising one, close the loop on
the topology: the SK filters' values and the treble ladder (C5/C9/C6, R7/R8, R12/R14) are
`static constexpr` and reachable from no A3 tool — the ladder is the largest *pre*-clipper roll-off
across the target span (−7.33 dB, 127→400 Hz) and has never been swept. Expose them, re-run the scan,
and only then argue for a new element. ⚠ Plumbing must be verified BOTH ways (default bit-identical,
override provably differs) — `a3_carrier_scan --selfcheck` does exactly this.
**(b)** C1 (+2.68 dB flat, corroborated at +4.03 dB by the free-k row) is a **broadband OD-level**
question, not an EQ one; its levers are the clipper's closed-loop gain and the LevelBlend divider, and
it should be settled before any frequency-shaping element is fitted, or that element will absorb it.
**(c)** C3 stays on the null gate. Do not work it from the shape curve — see (5).
**(d)** `trebleLadderDampR` stays at 30k. **(e)** The 4 `gain-n12` re-captures, then A4 re-grade +
GATE-9, the `OSValidationTest` decision, then B / C / D.

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

### A3 step 7 — A3 measured on the BLEND axis; the curve is MUTUALLY VALIDATED over 101 Hz–1 kHz, and the drive-axis target is RAILING elsewhere (session 51)

**Analysis + tooling only. NOTHING in `src/` or `tests/` changed** (`git status` clean apart from the
new script), so ctest is unchanged at the pre-existing session-44 16/17 (`OSValidationTest`).
Baseline verified FIRST: `a3_shape_gate --selfcheck` PASS, score 5.808, worst deviation from the
recorded baseline 0.027 dB. New tool `analysis/a3_blend_axis.py`.

#### 1. Why a new axis at all

Session 50 closed the C2 carrier search space and found it empty, which leaves two possibilities:
the carrier is a missing element, or **the target curve is wrong**. Every A3 number since session 47
comes from one instrument — `a3_phase_solve`'s inversion along the DRIVE ladder —

    t_d = beta * |1 + s . mu_d . e^(i.theta)|        d = 1..5

which is bimodal in `s`, needs a grid on both axes, is only as identified as the cancellation is
deep, and **consumes the MODEL's own `mu_d` shape**. Sessions 33 and 47 both had to correct
published conclusions for exactly that reason. So the target deserved an independent check before
any more search.

**The BLEND axis is that check, and it had never been solved on.** BLEND sits after everything, so
sweeping it changes neither the OD phasor nor the clean phasor — both are literally constant across
the five captures — and the mixing is linear in the knob. Normalising by the B = 0 capture
(`blend-0700` **is** the clean tap, so it is the reference, not an unknown):

    t(B) = | beta(B) + B . G | ,   beta(B) = 1 - B.(1 - b0) ,   G = a0.Vo/Vc

and squaring, with `c = 1 - b0`:

    t(B)^2 = 1 + B . 2(Q - c) + B^2 . (P - 2Qc + c^2) ,   P = |G|^2 , Q = |G|cos(theta)

**a quadratic in B with unit intercept.** Four non-zero BLEND points determine its two coefficients
by ordinary least squares — closed form, no grid, no branch to jump — leaving **two spare equations
per band that test the mixing law instead of assuming it**. `a0`, `L` and the LEVEL taper never
appear: `a0` folds into `G` and cancels when pedal is divided by model.

⭐ **Harmonics do not break the law**, which is what makes it applicable to a distorting path at
all: every OD harmonic is multiplied by the same `B` and the clean tap contributes none, so band
ENERGY keeps the same form with `P` absorbing the harmonic power. Confirmed empirically, not
argued — the model control fits to **0.0000 dB** on a render whose OD path is clipping hard.

#### 2. ⚠⚠ WHAT THIS AXIS CANNOT DO — it is BLIND to the bleed level, and that was verified

Three unknowns `(c, P, Q)` map onto only TWO quadratic coefficients, so the triple is
**one-dimensionally degenerate and every `c` fits equally well.** Proven algebraically (the
expansion above) and demonstrated: freeing `c` on the MODEL's own render, where the true value is
`b0 = 0.14239`, returns **`b0 = 0.886` at a residual of 0.0002 dB.** ⇒ this tool takes `b0` from the
model and **cannot be used to challenge β**; β remains the drive axis's business (session 34 item 2
bounds it from monotonicity, session 50 puts it at −16.75 dB in [−17.25, −16.50]).
⚠ The first draft of the tool fitted a free level offset on `ref-od` instead and got a
level-independent **−1.87 dB** across three sweep levels spanning 24 dB, which read convincingly as
a capture-level error. It was this degeneracy.

#### 3. ✅ `LevelBlend`'s MIXING LAW IS CORRECT — a live hypothesis, closed

Parameter-free in `b0` (only the two quadratic coefficients are fitted), pedal-side worst per-band
|Δt| over the 20 bands ≤ 1.7 kHz:

| | interior B fitted | worst |Δt| |
|---|---|---|
| MODEL (control — the law is exact on it) | 0.2500 / 0.5000 / 0.7500 | **0.001 dB** |
| PEDAL | 0.2117 / 0.4816 / 0.7385 | **0.083 dB** |

**0.083 dB is BELOW the 0.144 dB take-to-take floor at every band** ⇒ the pedal obeys the law
`Vout(B) = beta(B).Vc + B.G` that `LevelBlend.h` implements. **The BLEND/LEVEL network is not A3's
cause.** That mattered: it was the one place a small topology error would have produced exactly
A3's signature (a broadband, drive-independent, frequency-flat OD-vs-bleed level error = C1), and
the captured unit is an Ultra with a DIST footswitch that must interrupt this very node.

⭐ **NEW MEASURED FACT: the pedal's BLEND taper is not linear.** Effective B = **0.212 / 0.482 /
0.739** at knob 0.25 / 0.50 / 0.75 — ordinary conformity error (~4 % of rotation, 15 % relative at
the quarter point), but it means the INTERIOR blend captures must not be used with nominal B.
⚠ Run with the nominal taper the pedal's law residual is **0.039 rms and infeasible (`r^2 < 0`) at
40/50 Hz**, which looks exactly like a structural finding. It is a pot. **Nothing prior is
invalidated:** sessions 8 and 29 used only the ENDPOINTS, and both endpoints are taper-immune — at
B = 1 the wiper IS pin3 so `beta(1) = b0` whatever the taper does, and B = 0 is the normaliser. The
fit is bounded in what it can absorb for the same reason, and cannot touch a frequency-dependent
defect, which is what A3 is.

#### 4. VALIDATION of the solver (mandatory, both directions)

* `--selftest` — synthesise `t(B)` through the law from the decompose phasors and re-solve: worst
  |Δr| **0.000000 dB**, worst |Δθ| **0.00000°**.
* `--validate` — solve the MODEL's own rendered totals and compare against `a3_blend_decompose`'s
  exact superposition taps: |Δr| over 40–1700 Hz **mean 0.075 dB, worst 0.324 dB**. Above ~2.5 kHz
  it diverges (+11.8 dB at 4064) because the swept-sine band average carries harmonic/aliasing power
  the single-tone tap does not — so **the shared taper fit is restricted to bands ≤ 1.7 kHz** and
  nothing above ~2 kHz should be read off this tool.
* Every run prints the MODEL as a CONTROL. The taper fit returning **exactly** nominal on the model
  is what licenses reading it on the pedal.

#### 5. ⭐⭐ THE RESULT — the A3 curve is MUTUALLY VALIDATED over 101 Hz – 1 kHz

`s_drive` from `a3_shape_gate`/`a3_phase_solve`, `s_blend` from this tool. Disjoint information: the
drive axis breaks the `(r, θ)` trade with `mu_d`'s shape across five DRIVE captures, this axis with
the B-dependence of one. Different captures, different maths (nonlinear 2-D grid vs closed-form
linear LS).

| f | s_drive | s_blend | diff | θ_drive | θ_blend |
|---|---|---|---|---|---|
| 101 | +4.50 | +5.11 | −0.61 | 93.5 | **95.3** |
| 127 | +5.12 | +5.66 | −0.54 | 75.2 | **75.0** |
| 160 | +5.41 | +6.52 | −1.11 | 51.0 | 56.5 |
| 403 | +7.55 | +6.78 | +0.77 | 84.9 | 81.4 |
| 508 | +8.93 | +8.28 | +0.65 | 78.8 | 74.2 |
| 640 | +9.64 | +11.20 | −1.56 | 76.9 | 87.3 |
| 806 | +11.52 | +11.53 | **−0.01** | 101.8 | **100.8** |

**Magnitudes to ≤1.6 dB and PHASES to ≤5° across 101 Hz – 1 kHz, from two instruments that share no
information.** A3's curve over that range is real and can be fitted against with confidence. This is
the first independent corroboration A3 has ever had.

#### 6. ⚠⚠ AND WHERE THEY DISAGREE, THE DRIVE AXIS IS ON ITS SEARCH BOUNDARY

| f | s_drive | s_blend | diff | θ_drive | θ_blend |
|---|---|---|---|---|---|
| 20 | +9.99 | +21.37 | **−11.38** | 144.9 | 118.3 |
| 25 | +6.63 | +18.88 | **−12.25** | 152.4 | 121.6 |
| 32 | +4.31 | +14.48 | −10.17 | 169.2 | 128.6 |
| 40 | +3.18 | +10.07 | −6.89 | 170.2 | 138.2 |
| 202 | +5.42 | +7.62 | −2.21 | **0.0 (boundary)** | 43.3 |
| 254 | +4.92 | +8.13 | −3.21 | **0.0 (boundary)** | 56.6 |
| 320 | −18.06 | +3.48 | −21.54 | **180.0 (boundary)** | 115.2 |
| 1613 | +5.12 | +6.90 | −1.78 | **0.0 (boundary)** | 59.2 |
| 2560 | +10.74 | +5.84 | +4.90 | **175.8** | 43.7 |
| 4064 | −1.63 | +4.78 | −6.41 | **0.0 (boundary)** | 106.1 |

⭐ **The drive solve searches θ ∈ [0°, 180°] and is sitting ON that boundary at 202, 254, 320, 1613
and 4064 Hz** (and within 4° of it at 2560). Where it is interior the two axes agree to ≤1.6 dB;
where it rails they differ by 2–21 dB. **`a3_shape_gate`'s SCORE — the number every A3 candidate has
been ranked on since session 47 — includes 202 and 254 Hz, both railed.** Those two bands are inside
C2's own span (101–508 Hz), so **part of the curve the C2 search has been aimed at is set by a solve
at its parameter boundary.** That is a concrete, sufficient reason the search has not converged, and
it is the same class as session 33's "6–7 of 12 bands have θ pinned at 180°" note — which was
recorded and then not carried into how the score is read.

⚠ Be fair about what railing means: θ = 0 is representable and physically plausible (the model's own
θ at 202 Hz is 16°); the unconstrained optimum is simply negative, and the sign is unobservable from
magnitudes. So this is not proof the drive axis is wrong there — it is proof it is **uninformative**
there, while the blend axis returns an interior 43°/57° at a law residual of 0.020 dB.

#### 7. ⭐ THE LF HALF (C3) IS MUCH BIGGER THAN THE SHAPE GATE SAYS, and it is not a floor

The pedal's own OD-path transfer, `r = |G|` in dB (this is a direct measurement, no model inversion):

| f | 20 | 25 | 32 | 40 | 50 | 64 | 80 | 101 |
|---|---|---|---|---|---|---|---|---|
| **pedal** | −19.94 | −19.91 | −19.78 | −19.41 | −18.61 | −17.35 | −15.79 | −14.31 |
| **model** | −41.31 | −38.79 | −34.26 | −29.47 | −25.73 | −22.88 | −20.78 | −19.42 |

**The pedal's OD path is nearly FLAT from 20 to 101 Hz (5.6 dB over 2.3 octaves ≈ 2.4 dB/oct) where
the model's rolls off at ~9.5 dB/oct.** ⚠ `r_ped` being flat at ≈ −20 dB across 20–40 Hz is exactly
what a measurement FLOOR looks like, so it was tested rather than assumed: across four stimulus
levels (−30/−18/−12/−6 dBFS) it reads **−20.53 / −19.94 / −19.31 / −18.65 dB with θ stable at
117–120°** and the law residual ≤0.05 dB. A fixed noise floor would fall ~24 dB as a ratio over that
range; +1.9 dB of mild level dependence is a real, slightly compressive transfer. It is also robust
to the fixed `b0`: ±1.5 dB on `b0` moves `r_ped` by <1 dB at 20 Hz and <0.25 dB at 101 Hz.
⇒ **C3 is the dominant A3 term, not a ~+8 dB tail.** (`s_blend` itself is much less robust than
`r_ped` at LF, because there it is dividing by a model `r` of −41 dB; quote `r_ped` as the
measurement and `s_blend` at LF as indicative only.)

#### 8. ⭐ THE MID SCOOP: the pedal's is ~5 dB SHALLOWER and centred LOWER than the model's

Same measurement, through the bridged-T region, referenced to each side's own 2560 Hz value:

| f | 254 | 320 | 403 | 508 | 640 | 806 | 1016 | 2560 |
|---|---|---|---|---|---|---|---|---|
| **pedal** | −13.68 | **−19.64** | −17.12 | −17.66 | −18.96 | −18.37 | −16.05 | −9.33 |
| **model** | −21.81 | −23.12 | −23.89 | −25.94 | **−30.16** | −29.90 | −25.01 | −15.17 |

* **Model:** one scoop, minimum at 640–806 Hz, **15.0 dB** deep re 2560 — that is the bridged-T's
  716 Hz notch, exactly where the schematic puts it.
* **Pedal:** **9.6 dB** deep at 640 (5.4 dB shallower), *plus* a distinct local minimum at **320 Hz**
  4–6 dB below its 254/403 neighbours.

⭐ Two consequences. **(a)** The 320 Hz feature is **GAP #2's TrebleAttack notch, measured in the OD
path itself for the first time** — session 46 predicted it was there and buried by the bleed; here it
is, in the pedal's own OD transfer, and the drive axis cannot see it because that band is where its
θ rails at 180°. **(b)** The bridged-T is implicated after all, as **too deep and centred too high** —
which is `circuit.md`'s parked risk #1 ("real notch DEPTH is loaded + tolerance-sensitive → capture-
validate"), now capture-validated for the first time. ⚠ This does **not** revive session 47's `btC17`
candidate, and it does not contradict session 49: that Pareto scan proved the bridged-T cannot lift
250–640 Hz at **fixed f0 = 716.3 Hz** — but f0 was held because the model's own schematic values put
it there, never because anything measured it. GAP #1b's closure is also weaker than recorded: it
compared OUTPUT dips (plugin −2.45 vs pedal −3.02 dB median over 116 OD rows) in a region where the
bleed sits 11–31 dB above the OD path, so that comparison was insensitive to the OD path's shape by
construction — the same "a gate that cannot see the quantity" class as session 49 item 7.

#### 9. Artefact

`build/a3_blend_axis_<sweep>.csv` — the pedal's measured OD-path transfer (r and θ per band, 20 Hz –
16 kHz, with an `identified` flag), i.e. **a measured complex target for the OD path** rather than an
inverted one. Regenerate with `python3.11 analysis/a3_blend_axis.py`.

#### 10. ▶ WHAT THIS CHANGES FOR THE PLAN

1. **Stop ranking A3 candidates on a score containing railed bands.** Either restrict
   `a3_shape_gate`'s CORE to bands where the drive solve is interior, or — better — re-target it at
   the blend axis's measured `r_ped(f)`, which is interior everywhere below 1.7 kHz and agrees with
   the drive axis wherever the drive axis is informative.
2. **C1/C2/C3 should be re-derived against the corrected curve before any more carrier hunting.**
   Session 50's budget (C1 +2.68 flat / C2 +3.20 over 101–508 / C3 +7.86 at 20 Hz) was fitted to the
   drive-axis curve; §7 says C3 is far larger and §6 says two of C2's five bands were railed.
3. **The user has authorised breaking the schematic.** With a measured complex OD-path target the
   right move is no longer to hunt for one component: fit a post-clipper linear correction network of
   whatever order the data demands, as `OdCoupling` was added in session 36, then gate it on the null
   (`a3_lead_fit`), the SIDE monitors, and the 63-capture matrix. Session 50 already proved no single
   element can close A3 (fixing any one leaves 3.5–4.8 dB of 5.82).
4. Unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures, A4 re-grade
   + GATE-9, the `OSValidationTest` decision, then B / C / D.

### A3 step 8 — ⛔⛔ NO POST-CLIPPER LINEAR ELEMENT OF ANY ORDER CAN CLOSE A3, from the measured phase; and the blend axis is UNRELIABLE at 20/25/32 Hz, where C3's size was quoted (session 52)

**Analysis + tooling only. NOTHING in `src/` or `tests/` changed**, so ctest is unchanged at the
pre-existing session-44 16/17 (`OSValidationTest`). Baseline verified FIRST: `a3_shape_gate
--selfcheck` PASS, score **5.808**, worst deviation from the recorded baseline **0.027 dB**. New tool
`analysis/a3_correction_fit.py`.

Session 51's plan item 3 was: with a measured complex target, stop hunting one component and **fit a
post-clipper linear correction network of whatever order the data demands**. That was done. It does
not work, and the reason is the phase.

#### 1. The target, and the two things that had never been checked about it

`H_req(f) = G_ped(f) / G_mdl(f)`, pedal side from `a3_blend_axis`'s measured `(r, |theta|)`, model
side from `a3_blend_decompose`'s **exact** superposition taps (signed phase, no solve). Two
preliminaries the previous sessions did not establish:

* ⭐ **The phase sign ambiguity is PER BAND, not global.** `unpack` folds each band independently
  through `acos`, so strictly there are 2^15 sign patterns, not 2. Treating it as one global sign is
  legitimate only while `theta_ped` stays clear of 0 and 180 deg — a continuous phase can only change
  sign through one of those. **Checked, not assumed: closest approach is 37.5 deg (at 50 Hz)**, so
  the two-branch treatment holds over this band set. The tool prints the check and refuses to call
  the branch test decisive if it ever fails.
* ⚠⚠ **The instrument is NOT uniformly trustworthy, and its own published summary hid where.**
  `a3_blend_axis --validate` solves the MODEL's rendered totals against its exact taps, i.e. it
  measures the solve's error where the answer is known. Read **per band** instead of as the recorded
  "mean 0.075 dB, worst 0.324 dB over 40–1700 Hz":

  | f | 20 | 25 | 32 | 40 … 1613 |
  |---|---|---|---|---|
  | **dr dB** | **+2.774** | −0.157 | **−0.963** | ≤0.324 |
  | **dtheta** | **20.0°** | **16.5°** | **13.9° + RAILED at 180.0** | **≤2.7°** |

  ⭐ **The published summary starts at 40 Hz, so it excludes the tool's own three worst bands — and
  those three are exactly the bands carrying session 51 item 7's "C3 is the dominant A3 term"
  claim.** Same class as session 49 item 7 (a domain narrower than the claim) and session 40's
  "split the aggregate", one level down: here the aggregate's *range* was the problem, not its
  membership. **The fit band is therefore 40 Hz–1.7 kHz** (`--lo-hz`, default 40, documented in the
  flag's own help so the exclusion cannot be mistaken for convenience).

#### 2. ⭐⭐ THE RESULT: the measured MAGNITUDE and the measured PHASE are mutually inconsistent with causality

Over the validated band the magnitude alone is easy — a min-phase cascade fits it to **0.103 dB**
(13 params) or **0.232 dB** including unbounded rising tails, i.e. below the 0.144 dB capture floor.
Jointly with the phase, nothing fits. The honest form is the **Pareto frontier**, not one weighted
number (same move as session 49's bridged-T scan):

| phase weight | 0.00 | 0.02 | 0.05 | 0.10 | 0.30 | 1.00 | 3.00 |
|---|---|---|---|---|---|---|---|
| **mag rms dB** | **0.232** | 0.351 | 0.882 | 1.126 | 2.202 | 4.799 | **5.657** |
| **phase rms deg** | **40.3** | 30.6 | 15.9 | 12.9 | 7.0 | 3.3 | **2.6** |

Matching the magnitude to 0.23 dB costs **40 deg** of phase; matching the phase to 2.6 deg costs
**5.7 dB** of magnitude. There is no point with both small, against a 0.144 dB capture floor and a
**2.7 deg** validated phase accuracy. The frontier is computed on the family that INCLUDES unbounded
pure-zero tails, so the shortfall cannot be blamed on a truncated tail — session 32's error, which
is why the tails are in the parameterisation at all.

⭐ **Why this is an impossibility and not a fit failure.** Minimum phase is the MAXIMUM-LEAD
realisation of a given magnitude: any other causal realisation is min-phase x an all-pass, and an
all-pass only ADDS lag. The measurement wants **more lead than the min-phase realisation of its own
magnitude** (a near-constant ~−38 deg of excess, 40 Hz to 1.6 kHz). So **no causal linear element of
any order, anywhere post-clipper, can supply A3's measured target.** That is one level stronger than
session 50, which ruled out the elements the model contains; this rules out the whole CLASS.
The `+` branch is selected over `−` by 2.6–4x in joint cost at every order, so the sign ambiguity is
not what is doing this.

#### 3. Three escapes, all tested and all closed

* **A delay-compensation mismatch on the OD path** (dsp.md's own standing warning about the BLEND
  node — the most mundane explanation). ⛔ EXCLUDED: a delay's phase error grows linearly with
  frequency, and over a 40x span the shortfall is FLAT. Best-fit pure delay −0.113 ms leaves
  **32.3 deg** rms; a flat −38.1 deg offset leaves **12.9 deg**.
* ⭐ **A previously-unquoted BIAS in the instrument.** From the law's own algebra
  `k1 = 2(Re(g1) − c)` and `k2 = |g1|^2 + H − 2c.Re(g1) + c^2` with `H` the band's HARMONIC power, so
  `unpack` returns `r = sqrt(|g1|^2 + H)` — an UPPER BOUND on the fundamental — while `Q = Re(g1)` is
  exact. Hence `cos(theta) = Q/r` is **biased TOWARDS 90 deg**, and correcting it moves theta away
  from 90 deg, which REDUCES the required lead over 127–640 Hz — exactly where the shortfall is
  worst. So it is a live explanation and was sized rather than waved off, as the implied
  harmonic-to-fundamental POWER ratio: **at 8 of the 15 bands no inflation of any size suffices**
  (the bias would have to act in the wrong direction, or the cosine would have to change sign), and
  where it is finite it needs H/P of **0.6, 1.0, 1.1, 2.1, 5.0, 8.3, 36.1, 265.1**. ⛔ CANNOT explain
  it. ⚠ Be fair: at 160/202/1613 Hz the required H/P (0.6–1.1) is large but not absurd for a
  hard-clipped path — the refutation rests on the 8 impossible bands, not on those three.
  ⚠ **This bias still qualifies session 51's own numbers**: `r_ped` is an upper bound on the pedal's
  OD fundamental and `theta_ped` is biased toward 90 deg. `s_blend` (solved/solved) partly cancels
  it; a solved-vs-exact ratio does not.
* **A wrong bleed level `b0`.** The blend axis declares itself blind to `b0` (3 unknowns onto 2
  coefficients, band by band) — but `b0` enters `Q = k1/2 + (1−b0)` identically at EVERY band while a
  min-phase network's phase is tied to its own magnitude, so requiring causality ACROSS bands should
  break the degeneracy. And the shortfall's near-constant ~−38 deg shape is exactly what one wrong
  scalar in `Q` looks like, so this was the leading hypothesis. ⛔ **REFUTED BY ITS OWN SCAN.** The
  cost falls monotonically toward low beta and **SATURATES** (spread 0.0047 over the three lowest
  points; as `b0 → 0`, `c → 1` and the target converges, so this direction is a degeneracy with no
  interior optimum — the "make it see less" signature) and **still never reaches realisability**
  (1.46 dB / 11.7 deg at beta = −45 dB). Independently, the helping direction is excluded from
  outside: **session 34 item 2 refutes beta ≤ −18.5 dB from magnitudes alone**. Within the admissible
  window [−18.5, −16.5] the best is **1.418 dB / 17.4 deg** — still 6x the validated phase accuracy.

#### 4. What this changes, and what it does NOT

**Closed:** session 51's plan item 3. Do not fit a post-clipper linear correction network; do not
re-derive one. The tool's section 3 still prints a lowest-joint-cost row for diagnosis and now says
so explicitly — its first draft printed "CHOSEN" for a network 19.6 dB off at 1613 Hz with `k` and
three Qs resting on their bounds, which is exactly what a fallthrough must never look like.

**Corrected:** session 51 item 7's LF numbers. The 20/25/32 Hz solve carries ~3 dB and 14–20 deg of
error with one railed theta, so **C3's SIZE at 20–32 Hz is not measured to better than ~3 dB**. The
qualitative claim (the pedal's OD path rolls off far less at LF than the model's) rests on `r_ped`
across 20–101 Hz plus the four-level robustness check and survives; the specific "+7.86 dB at 20 Hz,
9.18 dB/oct" budget figure does not, and neither does quoting `r_mdl` at 20 Hz from the solve
(−41.31 dB) when the exact tap says −44.09 dB.

**Where this points.** The falsified premise is "the pedal's OD path = the model's OD path x a linear
transfer function". Since the magnitude is comfortably realisable and only the phase is not, the
difference is not a missing linear element — it is upstream of, or inside, the nonlinearity, where no
Bode relation applies. ⚠ That sits against session 50's "only a POST-clipper element can supply
`s(f)`", whose evidence was the drive-INDEPENDENCE of `s` measured on the drive-axis solve —
and session 51 item 6 found that solve RAILED at 202/254/320/1613/4064 Hz. **Re-examine that
argument before acting on either.** A concrete hypothesis worth gating (NOT a finding): a memoryless
clipper inside an RC-coupled feedback loop has a drive-dependent effective fundamental phase, so a
clipper operating-point difference can produce exactly this — a phase discrepancy with no linear
realisation. That is GAP #3a territory, pre-clipper, not post.

▶ **NEXT, IN ORDER: (a)** settle the post-vs-pre question properly — re-run session 50's
drive-independence argument with the railed bands removed, since the whole "post-clipper only"
conclusion rests on it and one of its inputs is now known to be uninformative. **(b)** do NOT
re-target `a3_shape_gate` at `r_ped(f)` as session 51 item 10.1 proposed *without* first carrying
this section's caveats: `r_ped` is an upper bound (harmonic bias) and is unreliable below 40 Hz.
Restricting CORE to the bands where the drive solve is interior is still worth doing and is
unaffected. **(c)** C1 is still a broadband OD-LEVEL question and is still the right thing to settle
before any frequency-shaping element. **(d)** unchanged behind that: `trebleLadderDampR` stays at
30k, the 4 `gain-n12` re-captures, A4 re-grade + GATE-9, the `OSValidationTest` decision, then
B / C / D.

#### 5. Tooling notes

`analysis/a3_correction_fit.py`. `--selftest` synthesises the ACTUAL observation structure (a known
network on top of a known model phasor, pedal phase then folded as `acos` folds it) and recovers it
to **0.00000 dB / 0.0000 deg**, with the wrong branch rejected by ~7e9x in joint cost. ⚠ Its first
draft folded the network's own phase instead of a pedal phase, which made the target
non-representable and produced a 12.7 deg "phase degeneracy" that was then narrated into the
docstring as a property of magnitude-only fitting — computed properly it is 0.00 deg on
representable data. **A self-test that synthesises the wrong observation structure measures its own
mistake.** Artefact: `build/a3_correction_target_<sweep>.csv`.

### A3 step 9 — ⭐⭐ TWO LOAD-BEARING PREMISES EXPIRE: session 50's post-clipper restriction is INVERTED, and session 31's "the phase gap is LINEAR" is false at the current state (session 53)

Analysis + tooling only. **NOTHING in `src/` or `tests/` changed**, so ctest is unchanged at the
pre-existing session-44 16/17 (`OSValidationTest`). New tools `analysis/a3_drive_indep_audit.py`,
`analysis/a3_treble_lag_probe.py`, `analysis/gen_a3_tones.py`. Logs `analysis/fit_logs/s53_*.log`.

#### 1. Session 50 item 2 is INVERTED — but the instrument had to be POWER-TESTED first

Session 50 narrowed the whole A3 search to the post-clipper region on this argument: *`s` is ONE
scale per band that must reproduce all five drive totals, and the shipped model already does, to
**0.094 dB rms** — so whatever is missing is drive-INDEPENDENT; a post-clipper linear element
multiplies |OD| identically at every drive, a pre-clipper one moves the clipper's operating point
and delivers `drvspr` of 4–19 dB.*

That is an **affirmation of the consequent**. "A drive-independent model fits, therefore the truth
is drive-independent" holds only if a drive-DEPENDENT alternative would fit detectably worse.

⚠ **The going-in hypothesis was that the axis had no power, and it was WRONG.** The +0.5 dB θ
interval is 66–180° wide at every band from 127 Hz up (180° — the entire search range — at 320 Hz),
which looks like an instrument that cannot discriminate. Measured rather than assumed:
`a3_drive_indep_audit.py` injects a **mean-zero** multiplicative ramp of known peak-to-peak span
into synthetic totals built from the model, refits a drive-INDEPENDENT (s, θ), and records the
residual. Mean-zero is load-bearing — a constant offset is absorbed by `s` exactly, so only the
variation across drives is the signal under test.

**Detection thresholds (smallest span clearing the 0.144 dB capture floor): 0.67–2.6 dB at 15 of 16
bands in the 40–1700 Hz fit band.** Only 320 Hz is blind, and there `s = 0.01` (the OD path is
effectively muted). ⇒ the axis **does** have power, comfortably below the 4–19 dB pre-clipper
elements deliver. The reason wide θ intervals do not imply no power: the residual constrains the
**magnitude** ladder's shape, and `mu_spr` (max−min of the model's `mu_d` across the five drives)
spans **4–25 dB**, so a drive-dependent ramp cannot be absorbed even where θ is free.

⭐ **With power established, the verdict runs the other way.** The 0.094 dB figure **cannot be
reproduced from any code in the tree**. Recomputed at the shipped state the per-band residuals are

| f (Hz) | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 | 320 | 403 | 508 | 640 | 806 | 1016 | 1613 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rms (dB) | 0.78 | 0.56 | 0.34 | 0.21 | 0.24 | 0.20 | 0.22 | 0.44 | 0.43 | 0.39 | 0.17 | 0.07 | 0.40 | 0.07 | 0.15 | 1.25 |
| equiv. span (dB) | 4.6 | 4.1 | 3.5 | 2.7 | 3.3 | 3.0 | 3.6 | 6.6 | 6.9 | >20 | 2.5 | 1.1 | 5.3 | 1.1 | 0.9 | 5.8 |

giving **0.471 dB RMS** over the fit band — **5× the quoted figure and 3.3× the capture floor**.
0.094 is not the RMS (0.471), mean (0.370), median (0.290) or minimum (0.070, at 508/806 Hz) of
that quantity under any aggregation, so it is recorded as **not reproducible**, not as "wrong".

Inverting each band's own power curve, that residual is equivalent to a **median 3.5 dB of
unmodelled drive-dependence**, with **6 of 16 bands (40, 50, 202, 254, 640, 1613 Hz) already inside
the 4–19 dB pre-clipper range**.

⚠ **Honest scope.** The equivalent-span figure attributes the **whole** residual to
drive-dependence — capture noise, band leakage and errors in `mu_d`'s own shape all land there — so
it is an **UPPER BOUND** and does **not** prove the carrier is pre-clipper. What it does is remove
the reason for excluding it. Combined with session 52's proof about *added* post-clipper elements,
**pre-clipper is now the only region not ruled out.**

#### 2. ⛔ The "the model is carrying all-pass LAG" escape — a real gap in session 52, refuted structurally

Session 52 proved the target needs ~38° more lead than the min-phase realisation of its own
magnitude, and tested exactly one direction: what can be **ADDED**. Min phase is the maximum-lead
realisation, any other causal realisation is min-phase × all-pass, and an all-pass only adds LAG.

It never asked the mirror question: **is the model's own OD path already contributing all-pass lag
the pedal does not have?** Removing existing lag is indistinguishable from adding lead and is not
Bode-bound, because it corrects an element rather than adding one. Only a genuine TWO-PATH network
can do it (a cascade of min-phase stages is min-phase), and the OD path has exactly one
pre-clipper: the treble ladder (C5/C9/C6 with shunts R12/R14, summing against R7→R8 at node M).

`a3_treble_lag_probe.py` solves that network **symbolically** (sympy, 5-node KCL per circuit.md's
verified node graph), so there is an exact rational `H(s)`, exact zeros, and an exact
min-phase/all-pass factorisation `H = H_mp · A`, `A = Π (s−z)/(s+z̄)` over RHP zeros. **No Hilbert
reconstruction and no tail assumption, so session 32's trap cannot recur.** Self-check reproduces
`eq_reference.treble_attack_tf` to **0.000000 dB / 0.000000°**; |A(jω)|−1 = 0.00e0.

**Shipped network: 0 RHP zeros** — zeros at 0 (the C7 highpass), 110.45 Hz, and a damped complex
pair at 315.64 Hz with ζ = 0.48 (GAP #2's notch). Poles 37.82 / 179.13 / 190.95 / 322.86 Hz.

⭐ **New measured fact worth keeping: `trebleLadderDampR` controls whether the OD path is
minimum-phase at all.** Sweeping 1215 plausible ladder settings, **92 have RHP zeros — and every
one requires `RdampC5 ≤ 1k`**, i.e. near the schematic **0** that session 19 moved away from at 30k.

⛔ **But it cannot supply A3's shortfall.** Best available lead over 40–1613 Hz is **18.9° MEAN with
a 255° SPREAD** — 1.4° at 40 Hz, 4.4 at 127, 15.2 at 403, 42.9 at 806, 172.4 at 1281, wrapping to
−83.1 at 1613. **An all-pass factor's phase is monotone in frequency by construction, so it cannot
produce a FLAT offset across a 40× span** — the identical structural reason session 52 excluded a
delay mismatch. ⇒ **do NOT plumb the ladder on phase grounds.** ⚠ The ladder may still matter for
A3's **MAGNITUDE** (C1/C2); that is untested and live, and it remains `static constexpr` and
unreachable from every A3 tool, so session 50's next-step (a) still stands.

#### 3. ⭐⭐ Session 31 item 1 has EXPIRED — and this cracks the framework session 52's proof was built in

Session 31 recorded *"the OD phase is DRIVE-INDEPENDENT (<0.1° across the whole DRIVE knob, every
band) — so A3's phase gap is a **LINEAR** problem."* That premise has scoped every phase argument
since, including session 52's use of causal-linear filter theory. Re-measured from the five shipped
decompose CSVs at A3's own condition (GRUNT cut, −18 dBFS), the OD-vs-clean phase across the DRIVE
knob (drive 0.0 → 1.0):

| f (Hz) | 40 | 64 | 101 | 127 | 160 | 202 | 254 | 320 | 403 | 508 | 640 | 806 | 1016 | 1613 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spread (°) | 0.11 | 1.83 | 10.28 | 17.43 | 24.34 | 29.74 | 33.78 | 38.06 | 42.60 | 45.04 | **53.43** | 45.55 | 37.20 | 35.04 |

**≥17° at every band from 127 Hz up**, worst 53.4° at 640 Hz. Liveness-checked per L-009: |OD| at
101 Hz moves −11.7 → +8.9 dB across the knob, so this is not an inert probe. Cause: `trebleC7`
(session 34) and `kInputRef` 3.377 → 1.2596 (session 44) both moved the clipper's operating point
*after* session 31 measured it.

⭐⭐ **Consequence for session 52.** At A3's operating point the OD path is **not an LTI transfer**,
so `H_req = G_ped/G_mdl` is a ratio of **describing functions** (fundamental-to-fundamental gain at
a given amplitude), not of transfer functions — and a describing function carries no obligation to
satisfy Bode's magnitude–phase relation. The impossibility result is therefore **not a paradox**: it
is the expected signature of a **nonlinearity** difference, which is session 52 item 4's own
hypothesis, now with direct evidence instead of speculation. ⇒ **do not quote session 52 as "no fix
exists"; quote it as "no LINEAR fix exists", which is what it shows.**

#### 4. ⛔ `clipA0` is not the lever, so Option 1(c) does not proceed as framed

`clipA0` is the DC value of the same open-loop gain a pole would roll off — the closest available
proxy — swept at FIXED drive noon via `a3_blend_decompose clipA0=`. OD phase change vs the shipped
24.871: **A0 = 50.0 → +0.84° mean** (min −6.24, max +3.51); **A0 = 12.0 → −2.32° mean** (min −5.93,
max +0.81). Against a ~38° requirement that is roughly **1/45th** of the needed authority, and the
shape is a **bump peaking at 403 Hz**, not flat. An open-loop **pole** acts only above its corner,
so it would be HF-weighted — a ramp — which is the same shape failure. ⇒ the phase authority inside
the clipper loop is the **operating point** (53°, per §3), not `A0`.

#### 5. ⭐ The pattern across the entire search — read this before proposing anything

**Every mechanism tested produces a phase change that GROWS WITH FREQUENCY, and the measured
requirement is FLAT across 40×:** delay (session 52a, linear in f), the ladder's all-pass (§2,
monotone by construction), in-loop `A0` (§4, a 403 Hz bump), and the drive axis itself (§3, 0.11° →
53°). Nothing physical tested so far has a flat-in-frequency phase signature.

⚠ **That sharply raises the prior that the flat −38° is an ARTEFACT of the instrument.** Session 52
escape (b) only **sized** the harmonic-power bias indirectly (reconciling needs H/P of 0.6–265, and
8 of 15 bands are impossible at any inflation) — computed on the biased instrument itself. The
unbiased measurement is now a **capture request, not an analysis**: see `docs/session53-capture-request.md`
and §6 below.

#### 6. Captures requested and now COMPLETE (requested + captured 2026-07-28) — 27 files, two stimuli

New standalone stimulus `analysis/a3_tones_48k.wav` (`gen_a3_tones.py`): 10 s `sweep_clean`
alignment anchor + 20 bands 20 Hz–1613 Hz × {−18, −30} dBFS as 2.0 s tones, 103.3 s total. Same
posture as `gen_jfet_ladder.py` — it does **not** touch the frozen main test signal, and its
captures are skipped by `find_captures` exactly as `jfet_ladder_*` are.

- **Set A (5 files)** — tones across a BLEND sweep at the reference condition. The unbiased
  re-measurement of session 52's target: one tone per band means no harmonic power inside the
  measurement, so `r` stops being an upper bound and `θ` stops being biased toward 90°. Also gives
  C3's size at 20–32 Hz properly for the first time (currently unmeasured to better than ~3 dB,
  and C3 is A3's dominant term).
- **Set B (7)** — BLEND sweep at DRIVE min and max: drive-dependence on the good axis.
- **Set C (12)** — BLEND sweep × GRUNT (flat/boost) and ATTACK (boost/cut): the pedal's own
  switches as a pre-vs-post-clipper localiser.
- **Set D (3)** — LEVEL sweep at drive-min: pins `b0` from the pot law (β/α = 1−L exactly) instead
  of inheriting it from the model, closing session 52's escape (c) with a measurement.

✅ **Filenames pre-verified before recording**: all 22 matrix names parse to the correct knob values
and switch indices via `captures.py::parse_capture`/`render_args`; the 5 `a3tones_*` names are
correctly **rejected** so they skip rather than entering the matrix; the matrix still resolves to
exactly 63.

⚠ **Set B carries a CONTROL, `drive-1700_blend-0700_base-od`.** At BLEND 0 the wiper sits on the
clean pin, so the OD path contributes nothing and the capture must be identical to the existing
`blend-0700_base-od` whatever DRIVE does. Every sweep reuses that one file as its B=0 normaliser, so
if the control disagrees the shared normalisation is invalid and nothing downstream can be trusted.

⚠ **A retracted protocol request, recorded so it is not re-derived**: continuous single-take sweeps
were asked for to avoid per-take timing drift, then withdrawn — the blend axis recovers θ
algebraically from magnitudes (`a3_blend_axis.unpack`) and never reads waveform phase, so it is
**alignment-immune** and ordinary one-file-per-setting takes are correct.

**✅ CAPTURE COMPLETION CHECK (2026-07-28, same session).** 31 files landed in `analysis/captures/`
(gitignored — back them up) before this session closed. Verified, not merely counted:

- **22/22 Set B+C+D matrix files present**, re-checked against `captures.py::parse_capture`/
  `render_args` a second time now that they exist on disk (same result as the pre-recording check:
  correct knob values and switch indices; matrix still resolves to exactly 63 with these excluded).
- **9 `a3tones_*.wav` files present** — Set A's required 5, plus the optional Set E's 4
  (`a3tones_drive-1700_blend-*`) that the request flagged as "nice to have, only if still set up."
- **No clipping.** Screened every new file for CONSECUTIVE flat-topping (the real clipping
  signature — a squared-off waveform — not merely a hot peak, which a periodic tone produces
  naturally near its own crest). `attack-cut_blend-1430_base-od.wav` peaks at **0.9885**, matching
  the session-24 bad-take pinned-peak VALUE exactly, but on a **single sample** (max consecutive run
  = 1), not the many-sample flat top that signature actually requires — a genuine hot transient, not
  a re-run of that defect. Every other new file's peak is well clear of clipping. Zero files need
  re-capturing.
- **No truncation.** Every matrix file is 83.70 s, every `a3tones_*` file is 103.30 s — uniform
  across all 31, consistent with `gen_a3_tones.segment_times()`'s expected total and with the
  existing matrix's own segment layout. A short file's missing segments would read as zeros and
  produce confident nonsense (the standing capture-protocol warning); this rules that out.

⚠ **One item from this list is deliberately NOT done: the Set B control has NOT been checked against
`blend-0700_base-od.wav`.** Its file is present and clean, but the actual comparison — the thing
that validates every Set B/C number downstream — is analysis, not a capture-quality check, and per
the user's request this session stopped at "captures are ready" rather than starting the next
session's work. **This is the first thing the next session must do, before reading anything else out
of Sets B/C/D** (§4 item 6's own warning: if the control disagrees, the shared B=0 normalisation is
invalid).

---

### A3 step 10 — the 31 session-53 captures ANALYSED: the harmonic bias is MEASURED (~2°, not 38°), and H_req is measurably DRIVE-DEPENDENT, which closes the post-clipper linear class (session 54)

Analysis + tooling only. **NOTHING in `src/` or `tests/` changed**, so ctest is unchanged at the
pre-existing session-44 16/17 (`OSValidationTest`). New tools `analysis/read_a3_tones.py`,
`analysis/a3_condition_axis.py`, `analysis/a3_level_b0.py`. The frozen 63-capture baseline
(`analysis/reports/comprehensive_data.json`) was **NOT** overwritten — the 22 new matrix captures
went to a separate `analysis/reports/s54_matrix85.json`, because adding them to the aggregate would
silently redefine every "OD 3.186 / CLEAN 0.427 / ALL 1.807" figure in this document.

#### 1. ⭐⭐ SET A — THE HARMONIC-POWER BIAS IS NOW MEASURED, AND IT IS ~2°, NOT ~38°

`a3_blend_axis` reads 1/3-oct band ENERGY, so its magnitude is `r = sqrt(|g1|^2 + H)` (an UPPER
bound on the fundamental) while `Q = Re g1` is exact ⇒ `cos theta = Q/r` is biased TOWARDS 90°.
Session 52's impossibility proof is computed from that biased theta; session 52 could only SIZE the
bias indirectly (needs H/P of 0.6–265, impossible at 8 of 15 bands), and session 53 item 5 raised
the prior that the flat −38° is an artefact. Tones remove the bias by construction.

`read_a3_tones.py`, tones vs the swept instrument at the SAME operating point, 40–1700 Hz, 17 bands
both identified: **dtheta mean −2.1°, rms 2.5°, worst −4.1°; dr mean −0.39 dB, rms 0.46.**
The bias is REAL and in the PREDICTED DIRECTION (swept theta pulled toward 90°), but it is ~2°.
⇒ **session 52 escape (b) is REFUTED BY MEASUREMENT rather than sized: harmonic power cannot
account for a ~38° excess lead.**

Guards, because the whole point is that this number is trustworthy:
  * `--selftest` leg 2a **HARMONIC REJECTION 0.0006 dB** on a synthetic capture whose tones carry
    −10 dB H2 and −14 dB H3 — far dirtier than the real path. This IS the tool's central claim.
  * ⚠ leg 2b **HUM SENSITIVITY is reported, NOT gated.** The first draft asserted a tight bound on a
    run containing 50 Hz mains and FAILED — correctly, but for the wrong reason: a same-frequency
    contaminant is physically inseparable from signal and no window removes it. Gating on it would
    have tested the hum level, not the tool. It is now split out, and the gap-based SNR estimator is
    validated against it (reads 30.8 dB where hum costs 0.23 dB). Real captures: SNR ≥ 72 dB.
  * the law holds on the real tone captures at **0.090 dB** worst (floor 0.144).

#### 2. ⚠⚠ AND SET A FOUND SOMETHING NOT ASKED FOR: THE OD PATH IS COMPRESSING ABOVE ~800 Hz AT A3's OWN OPERATING POINT

The stimulus carries every band at −18 dBFS (A3's condition) AND −30 dBFS (near-linear control),
solved SEPARATELY and never averaged. `r(-18)` vs `r(-30)` agrees to ≤0.30 dB below 500 Hz but then
diverges: **806 Hz −1.68 | 1016 −4.07 | 1281 −5.74 | 1613 −6.83 dB**, with theta moving +7 to +10°.
A transfer must be level-independent; this is not one. ⇒ **above ~800 Hz `H_req` is not a transfer
function at all**, so neither Bode nor the min-phase argument binds there. This is session 53 item
3's conclusion (the OD path is not LTI at this operating point) reproduced on the LEVEL axis, from
an instrument that shares no information with the drive-axis one that produced it.

#### 3. ⭐⭐ SETS B/C — H_req IS DRIVE-DEPENDENT, WHICH CLOSES THE POST-CLIPPER LINEAR CLASS

`a3_condition_axis.py` runs the blend axis at SEVEN operating points. Each condition gets a full
5-point ladder: B=0 is the shared `blend-0700` normaliser, the three interior points are session
53's captures, and **B=1.00 already exists in the frozen matrix** (`<condition>_base-od.wav`), so no
condition is fitted short and the 63-matrix is untouched.

**Step 0 — the shared normaliser is VALID, and it was tested first.** At B=0 the OD path contributes
nothing, so the capture must be drive-independent. `drive-1700_blend-0700` minus `blend-0700` over
20 bands: **mean −0.011 dB, worst −0.054 dB** (floor 0.144). Every ladder divides by that file, so
this gates everything else.

**The result.** A post-clipper LINEAR element multiplies the OD path by the same `H(f)` at every
drive, so `H_req = G_ped/G_mdl` must be drive-independent. Measured at drive min / noon / max:

| f Hz | \|H\| min | noon | max | spread | argH min | noon | max | spread |
|---|---|---|---|---|---|---|---|---|
| 101 | +12.92 | +5.04 | +4.51 | 8.42 | +49.7 | +23.9 | +25.3 | 25.9 |
| 202 | +14.36 | +7.62 | +4.99 | 9.36 | +85.6 | +27.5 | +29.2 | 58.1 |
| 508 | +17.89 | +8.26 | +4.75 | 13.14 | +99.8 | +68.5 | +58.9 | 40.9 |
| 1613 | +6.85 | +6.85 | +6.22 | 0.63 | +53.3 | +44.3 | +36.8 | 16.5 |

**|H| spread mean 8.49 dB, worst 13.14 dB — 59× the 0.144 dB floor. argH spread mean 34.8°, worst
58.1°.** ⇒ **the pedal's OD path is NOT the model's OD path times ANY drive-independent linear
filter**, so no post-clipper linear correction of any order can close A3 across the DRIVE knob.
This MEASURES on the well-conditioned axis what session 53 item 1 argued from the inverted
drive-independence premise, without the railed drive solve.

⚠ **State it exactly that way and no stronger.** `H_req = G_ped/G_mdl` also moves if the MODEL's own
drive response is wrong — which it is, that being A3. So the falsified statement is
*"pedal_OD = model_OD × H, one drive-independent linear H"*. It does NOT separate "the model's drive
response is wrong" from "there is a pre-clipper element"; those are close to the same claim.

⭐ **The taper choice is deliberately CONSERVATIVE for this conclusion.** Per-condition tapers are the
primary read because they give the data the maximum freedom to make `H_req` look drive-INDEPENDENT.
The shared-taper sensitivity check agrees (|H| spread 5.03 dB mean / 7.34 worst), so the verdict does
not rest on the nuisance parameter.

**Step 2, the MODEL-FREE localiser** (pedal vs pedal across switch positions — it cannot inherit a
model error). dtheta vs the reference condition over 40–1700 Hz (re-run after §4 item 4's re-capture,
now 6 of 6 conditions passing):
**drive min +36.2° | drive max −20.0° | grunt boost −40.4° | grunt flat −15.5° | attack cut −12.5°
(rms 13.4) | attack boost −2.9° (rms 10.4, the smallest).** The pedal's own OD transfer moves far
more with DRIVE and GRUNT (the clipper's input coupling) than with ATTACK (the treble ladder's C8),
consistent with session 53 item 2's structural refutation of the treble ladder on phase grounds; both
ATTACK positions now land as real, non-degenerate, small-to-moderate signals, not one measured value
and one placeholder.
⚠ **Not a clean discriminator, and do not quote it as one:** ATTACK is a physically SMALLER
perturbation (C8 is 220 pF, mostly HF) than GRUNT's 47n/220n coupling swap, and this comparison does
not normalise for perturbation size. It says where the phase authority IS in the real pedal, not
that the treble ladder is exonerated.

#### 4. ⛔→✅ ONE CAPTURE WAS DEFECTIVE — `attack-cut_blend-1430_base-od.wav` — caught by a THRESHOLD-FREE test, RE-CAPTURED, RE-VERIFIED

For a fixed complex G, `t(B) = |beta(B) + B.G|` traces a STRAIGHT LINE in the complex plane, so its
modulus has **at most ONE interior minimum and no interior maximum**. The original attack-cut ladder
read **1.000 → 0.836 → 0.574 → 1.176 → 0.134**: two turning points, and t(0.75) > 1 (louder than the
full-clean reference). That is unreachable by ANY G, at ANY bleed level, under ANY taper — so it was
a defective capture, not a circuit difference, and no fitting could rescue it. Fired at **20 of 20
bands**, and dropping that one file made every band structurally possible again, which localised it
to a single file. It was the same file session 53's own screen flagged as peaking at 0.9885 — a
broadband gain knob (MASTER, confirmed by the user) left at 1430 instead of BLEND on that one take.

✅ **RE-CAPTURED and RE-VERIFIED same session.** RMS across the ladder now falls monotonically
(blend-0700 −14.41 → attack-cut_blend-0930 −15.94 → _1200 −19.04 → **_1430 −23.65** →
attack-cut_base-od −29.51 dB), peak dropped 0.9885 → 0.2828, and the re-solved taper (0.190/0.488/
0.780) sits squarely inside the other five conditions' spread instead of the degenerate 0.957/0.980/
0.905 the bad take produced. Law residual **0.063 dB** (was 6.731), well under the 0.144 dB floor.
**All 6 of 6 conditions now pass** — §4 item 3's table and step 2's localiser above are unaffected
(neither used attack-cut), but the localiser table now carries a real attack-cut row instead of NaN.
⚠ **The first re-capture attempt (same session) was ALSO checked and found still broken** (RMS
−12.78 dB, same 0.9885 peak) before this second one was accepted — never trust a "fixed" claim
without re-running the turning-point test, which is exactly why it has no threshold to argue with.

⚠ **This replaced a heuristic that MISSED the very file it was written for.** The first detector
looked for a large, frequency-FLAT residual (the signature of a level/knob error) — but the fitted
taper absorbed the offset (driving attack-cut's taper to a degenerate 0.957/0.980/0.905) and the
residual then no longer looked flat. A test derived from the law's own geometry has no threshold to
tune and cannot be absorbed by a nuisance parameter.

⚠ **AND A DEFECT IN MY OWN FIRST READING, worth keeping.** Session 54's first pass reported the
mixing law as FAILING for GRUNT flat (3.725 dB) and GRUNT boost (0.789 dB). It does not. Those worst
values sit at 32 Hz (min|t| = 0.028) and 25 Hz (0.050) — bands in a deep cancellation null, where a
fixed absolute error becomes a huge dB error. Every band above 50 Hz is ≤0.10 dB. `fit_taper`'s COST
already guards against this (it divides by t) but the `worst |dt|` it PRINTS is raw dB and does not.
GRUNT boost/flat push far more bass into the clipper, so |OD| approaches the bleed at LF and the
cancellation deepens — physically expected. `NULL_GUARD` now excludes null-dominated bands from the
verdict and reports them separately. Same class as session 49 item 7 and session 52 item 1: the
aggregate's RANGE was the problem, not its membership.

#### 5. SET D — b0 MEASURED ON THE LEVEL AXIS: ~1.2 dB ABOVE THE MODEL, AND IT DISAGREES WITH THE DRIVE AXIS

The blend axis is provably degenerate in the bleed level and takes `b0` from the model, so every
number it has produced inherits it. At BLEND max the LEVEL wiper is a three-way Thevenin node:

    V(L) = (g + (1-L)) / (1 + (1-L)/L + (1-L)),      g = Vod/Vclean

so the OD leg scales as 1/(1-L) while the bleed does not, and `b0(L)` follows with the taper
exponent `p` as the ONLY free parameter — shared across every band, hence over-determined.

**Result: p = 1.90 in [1.75, 2.05] ⇒ b0 = −15.70 dB in [−16.20, −15.25]**, against the model's
−16.93 dB. The fixed-p scan has a genuine INTERIOR optimum (rms 0.146 / **0.037** / 0.221 at
p = 1.5 / 1.9 / 2.5), so this is a measurement and not the flat-objective degeneracy that defeated
session 52's own b0 scan.

⚠ **It does NOT overlap session 50's drive-axis beta** (−16.75 dB in [−17.25, −16.50]) — but it DOES
agree with session 31's drive-axis least-squares (−15.2 dB), which found the model's bleed ~1.7 dB
low. So two independent axes now put the bleed ABOVE the model and one puts it below.
⚠ **Do not redefine b0 on this yet:** the law residual is 0.33 dB, above the 0.144 dB floor, so the
formal interval is optimistic; and session 8's bleed-free LEVEL-taper estimate (p = 2.22 ± 0.36,
from 36 harmonic estimates) overlaps p = 1.90 at ~1 sd, so the taper disagreement is not sharp.

⚠ **A REAL BUG IN THE FIRST DRAFT, caught by the data.** At LEVEL max the wiper is shorted to the OD
source, so the output IS Vod and the bleed is ZERO — but the draft special-cased `bleed(1) = 0.5`
and the limit as `|0.5g + 0.5|`, i.e. it put the bleed at its MAXIMUM exactly where it vanishes.
Since knob 1.0 gives L = 1 for every p, that wrong point was in every candidate fit: it dragged p
to 1.33 and inflated the residual to ~2.3 dB. The corrected `bleed()` now reproduces
`a3_blend_axis.model_b0()` to 1e-12 — an independent cross-check that the two derivations agree.

#### 6. ⭐ SENSITIVITY: SESSION 52's CONCLUSION SURVIVES BOTH KNOWN BIASES, AND THEY PARTLY OFFSET

Re-solving Set A's tone target across the bleed range moves the mean required `argH` over 40–1700 Hz:
**b0 = −16.93 → +36.3° | −16.20 → +40.6 | −15.70 → +43.6 | −15.25 → +46.4.** So the bleed
uncertainty is worth **+7.3°** at Set D's own value (+10.1° over the full range) — not negligible
against 38°, but it moves toward MORE required lead, i.e. HARDER to realise. Combined with the tone
bias (−2.1°) the net is about **+5°**. ⇒ **neither known bias dissolves session 52's excess lead;
together they slightly enlarge it.**

#### 6b. ⭐⭐ THE ARBITER — SESSION 52's IMPOSSIBILITY RE-RUN ON THE UNBIASED TONE TARGET, AND IT SURVIVES

`read_a3_tones.py` also emits the -18 dBFS target in `a3_blend_axis`'s EXACT CSV schema
(`build/a3_blend_axis_tones-setA.csv`), so `a3_correction_fit.py --sweep tones-setA` runs session
52's impossibility test with **ZERO changes to that tool** — deliberate, so that a change in the
RESULT cannot be confounded with a change in the instrument.

⭐ **The run validates itself.** A matched `--ntry 8` run on the SWEPT target reproduces session 52's
recorded frontier to 3 decimals (0.232/40.3, 0.882/15.9, 1.126/12.9, 2.202/7.0, 4.799/3.3), so the
cheap setting is equivalent here and the tones-vs-swept comparison is like-for-like.

| phase wt | TONES mag rms / ph rms | SWEPT mag rms / ph rms |
|---|---|---|
| 0.00 | 0.236 dB / **36.7°** | 0.232 dB / **40.3°** |
| 0.02 | 0.387 / 25.6 | 0.351 / 30.6 |
| 0.05 | 0.853 / 14.9 | 0.882 / 15.9 |
| 0.10 | 1.078 / 12.0 | 1.126 / 12.9 |
| 0.30 | 2.236 / 6.7 | 2.202 / 7.0 |
| 1.00 | 4.415 / 3.4 | 4.799 / 3.3 |

Magnitude alone is realisable (0.236 dB, under the 0.144–0.30 dB floor region); jointly with phase
nothing is. The min-phase excess falls **40.3° → 36.7°**, i.e. by 3.6° — matching the ~2.1° theta
bias measured directly in §4 item 1, and leaving the result intact. Computed on the family that
INCLUDES unbounded rising tails, so this is not session 32's truncated-tail artefact.

⇒ **SESSION 52's IMPOSSIBILITY IS CONFIRMED ON UNBIASED DATA. No causal linear element of any
order, anywhere post-clipper, can supply A3's measured target** — and the harmonic-power caveat that
qualified it since session 52 is now discharged by measurement rather than by argument.

#### 7. ▶ NEXT

  * **(a)** ✅ DONE — `attack-cut_blend-1430_base-od.wav` re-captured and re-verified same session
    (§4 item 4). All 6 of 6 Set B/C conditions now pass.
  * **(b)** make `attackIdx` reachable in `analysis/a3_blend_decompose.cpp` (line 150 hardcodes
    `p.attackIdx = 0`), so the ATTACK conditions get a model side and step 2's localiser can be run
    pedal-vs-model instead of pedal-vs-pedal. ⚠ that binary is built by a hand-written `c++`
    command, NOT by CMake — session 37 item 12's stale-binary trap applies.
  * **(c)** the post-clipper LINEAR class is now closed on measurement (§4 item 3) as well as on
    session 52's Bode argument. The remaining region is inside/before the clipper, where neither
    argument binds — `Clipper.h:309` gives `a0` no frequency dependence and the inverter no output
    impedance, both derivable from the DAFx-2020 two-MOSFET model that produced the 5.636 V rail.
  * **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude;
    §4 item 6 bounds what it is worth (~7° of argH, ~0.2 dB of |H|).
  * **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
    A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.

---

### A3 step 11 — ATTACK is reachable in the model at last, and the model's ATTACK response is measurably NULL where the pedal's is ±3–7 dB (session 55)

Session 54's next-step (b). Tooling + analysis only — **nothing in `src/` or `tests/` changed**, so
ctest is unchanged at the pre-existing session-44 **16/17** (`OSValidationTest`); confirmed by
running it, not assumed.

#### 1. THE CHANGE

`analysis/a3_blend_decompose.cpp` hardcoded `p.attackIdx = 0` (line 150), so the two ATTACK
conditions of session 54's condition axis had **no model side at all** and its localiser could only
ever run pedal-vs-pedal. Added `attackIdx=0|1|2` as a trailing `key=value` override — special-cased
next to `kInputRef` rather than added to `kFitKeys`, because it is a `PedalChain::Params` switch
index, not a `double FitParams::*`. Out-of-range values are rejected with a message rather than
silently clamped. The CSV **header line now states `attack=`** beside `grunt=`/`drive=`, so a file
that is read by name from a dozen tools declares its own operating point (sessions 45/37).

GRUNT was already reachable via `argv[1]`; those CSVs had simply never been rendered. So all four
missing condition CSVs were generated and wired into `a3_condition_axis.py::CONDITIONS`
(`build/a3_dec_{grunt-flat,grunt-boost,attack-boost,attack-cut}.csv`, superposition self-check
≤ −273 dB on all four). **Every one of the seven conditions now has a model side.**

#### 2. VERIFICATION — BOTH DIRECTIONS, plus the two traps this file keeps re-learning

The binary is built by a hand-written `c++` command, not by CMake, so `cmake --build` would not
rebuild it (session 37 item 12). Five checks, all run:

  * default render **bit-identical** to an explicit `attackIdx=0` render ✅
  * `attackIdx=1` and `=2` each **provably differ** from default, and from each other ✅
    (the first test alone also passes when nothing was rebuilt — that is the trap)
  * default render **bit-identical to the pre-existing `build/a3_dec_drv0.5.csv`** ✅ — the edit is
    surgical, and this simultaneously proves that baseline was not stale
  * `build/a3_dec_drv0.0.csv` and `drv1.0.csv` re-rendered and **bit-identical** ✅ (session 45 item
    7a: a re-baseline that names one artefact leaves its siblings stale, and step 3's whole verdict
    rests on these two)
  * `attackIdx=3` **rejected**, exit 1 ✅

Regression on the analysis side: `a3_condition_axis.py --selftest` PASS (1.8e-13 deg), and steps 2
and 3 reproduce session 54's recorded figures **exactly** (drive min +36.2° / drive max −20.0° /
grunt boost −40.4° / attack cut −12.5° / attack boost −2.9°; |H| spread mean 8.49 dB worst 13.14,
argH mean 34.8° worst 58.1°). The `H_req` computation was factored into one `hreq_of()` used by all
four call sites — it is now computed two taper variants × two axes, and four copies of a phase fold
is how a sign convention drifts between two halves of one verdict.

#### 3. NEW STEP 4 — THE LOCALISER RUN PEDAL-vs-MODEL

Step 2 asks whether the PEDAL's OD transfer moves with a switch. Its own recorded caveat is that it
does **not normalise for how big each perturbation is** (ATTACK moves 220 pF; GRUNT moves
47n/220n), so a small ATTACK row is ambiguous between "the ladder is not the carrier" and "the
ladder barely moved". Differencing `H_req` instead subtracts whatever the model **already
reproduces**, leaving only the part of each switch's effect the model gets **wrong** — which is what
a carrier hypothesis is actually about.

⚠ **ONE COMMON BAND SET, or the rows are not a ranking.** Per-condition identifiability differs
(grunt boost identifies 10 bands where the others identify 12–13), and an rms over different members
is the session-49-item-7 / session-52-item-1 / session-54-item-6 trap for the fourth time. The table
is restricted to the 8 bands identified in every condition (80–1016 Hz); each row still prints its
own total count so the restriction cannot hide a mostly-unidentified condition.

| condition | d\|G\| dB ped / mdl / **RESID** | dtheta deg ped / mdl / **RESID** | bands |
|---|---|---|---|
| grunt flat   | 6.06 / 7.98 / **2.00** | 16.2 / 57.5 / **42.7** | 13 |
| grunt boost  | 7.49 / 8.00 / **2.00** | 41.7 / 68.6 / **42.1** | 10 |
| attack boost | 4.99 / **0.05** / **5.01** | 11.3 / 8.4 / **15.7** | 12 |
| attack cut   | 3.24 / **0.07** / **3.18** | 10.7 / 7.1 / **6.6** | 12 |

(rms over the common bands; RESID = ped − mdl = the `d(H_req)` a correction would have to absorb.)

Worst across the four: **|H_req| 7.22 dB** against the 0.144 dB floor, **argH 60.5°**.
⇒ **`H_req` is SWITCH-DEPENDENT.** A post-clipper linear element sits downstream of both the treble
ladder and the clipper input, so it multiplies the OD path identically in every switch position —
the same argument step 3 runs on DRIVE, now on a second, independent axis.

#### 4. ⭐⭐ THE FINDING: THE MODEL'S ATTACK IS INERT BELOW 1.6 kHz; THE PEDAL'S IS NOT

The decomposition is what makes this visible, and it is not a marginal number. The **model's** own
`d|G|` across ATTACK, per band, is **≤0.13 dB at every band from 20 Hz to 1613 Hz** (−0.01 at 20 Hz,
+0.10/−0.13 at 403) and only becomes large at 2.5 kHz and above (−7.8 / +10.4 / +11.2 dB at
2560/4064/6451) — exactly what a 220 pF C8 must do. The **pedal's** is a broad, smooth, monotone
low-mid shape, not one band:

| f (Hz) | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 |
|---|---|---|---|---|---|---|---|---|---|
| attack **boost** | +6.82 | +7.19 | +6.87 | +5.95 | +4.62 | +3.65 | +2.01 | −0.39 | −1.26 |
| attack **cut**   | −3.28 | −3.04 | −3.01 | −3.00 | −2.94 | −3.11 | −4.24 | −4.55 | −5.06 |

So the pedal's ATTACK switch has **±3–7 dB of authority across 80–640 Hz that the model reproduces
essentially not at all** — the residual is ~100 % of the move because the model's contribution is
zero. That span is exactly where A3's C2 component lives (+3.20 dB over 101–508 Hz on the session-50
budget; +4.4…+9.0 dB on session 47's bathtub).

⭐ **This INVERTS session 54 item 4's tentative reading.** That item recorded ATTACK as producing the
*smallest* pedal-side move (rms 10.4°/13.4° vs GRUNT's 15.9°/43.1°) and read it as "consistent with
session 53 item 2 refuting the ladder", while flagging that it did not normalise for perturbation
size. Normalised, the ordering flips in MAGNITUDE: **ATTACK has the LARGEST magnitude residual of
the four (5.01 / 3.18 dB rms) and GRUNT the largest PHASE residual (42.7 / 42.1°).** Session 53 item
2 refuted the treble ladder as a source of *flat phase lead*, which is untouched; nothing had ever
tested the ladder as a **magnitude** carrier, and session 50's own next-step (a) already noted the
ladder is `static constexpr` and unreachable from every A3 tool.

#### 5. ⚠ WHAT THIS DOES AND DOES NOT ESTABLISH

  * It falsifies **"pedal_OD = model_OD × ONE switch-independent linear H"** and no more. `H_req`
    moves if the pedal has an element the model lacks **OR** if the model's own response to that
    switch is wrong — and the model's ATTACK/GRUNT response has never been gated on its own. It does
    **not** separate those, exactly as step 3's drive-axis version does not.
  * The two candidate readings of §4 are both pre-clipper or in-clipper, which is the region
    sessions 53/54 had already narrowed to: **(i)** the pedal's ATTACK network has far more
    low-mid authority than a 220 pF C8 — note ATTACK is **[ENG]**, the 3-way switch does not exist
    on our schematic at all, so there is no verified topology here to defer to; or **(ii)** the
    pedal's clipper operating point is far more sensitive to the HF content ATTACK moves than the
    model's is. Both are testable; neither is tested here.
  * The pedal-side numbers are **describing-function** differences, not transfer functions (the
    standing caveat on this whole axis) — a broadband move through a nonlinearity is expected even
    from an HF-only network. That cuts both ways: it is also why the model showing ~0.00 dB is the
    informative half.
  * ⚠ **Do not read the 2.5–10 kHz model rows.** They are above `FIT_HI_HZ` = 1700 Hz, where the
    blend axis is explicitly untrustworthy (session 51 item 5).
  * Step 2 (pedal-vs-pedal) **remains the model-free fallback**; where the two disagree, step 2 is
    the one that cannot inherit a model error. Both are printed, and neither replaces the other.

#### 6. ▶ NEXT

  * **(a)** ⭐ make the treble ladder reachable (`C5/C9/C6`, `R7/R8`, `R12/R14`, and `C8` itself are
    `static constexpr` — session 50's next-step (a), still open) and re-run step 4: if a ladder
    change closes the ATTACK magnitude residual it is a C1/C2 candidate on a second axis, and if it
    cannot, that is a reachability refutation of the same shape as session 49's bridged-T Pareto.
    ⚠ verify plumbing BOTH ways, as above.
  * **(b)** gate the model's ATTACK response on its own before reading any more into `H_req` — that
    is the ambiguity in §5's first bullet, and it is a cheap matched-pair measurement
    (`attack-boost_base-od` vs `ref-od` vs `attack-cut_base-od` already exist in the frozen matrix).
  * **(c)** unchanged from step 10: the post-clipper linear class is closed on measurement and on
    Bode; the remaining region is inside/before the clipper (`Clipper.h:309` gives `a0` no frequency
    dependence and the inverter no output impedance).
  * **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude.
  * **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
    A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.

---

### A3 step 12 — the ATTACK finding survives an independent instrument, and the modelled ATTACK network is refuted as its carrier (session 56)

Session 55's next-steps **(b)** then **(a)**, in that order. Tooling + analysis only — **nothing in
`src/` or `tests/` changed**, so ctest is unchanged at the pre-existing session-44 **16/17**
(`OSValidationTest`, same `amp 0.35 : 2x -25.6 / 4x -32.1 / 8x -23.6` failure); run, not assumed.
New tools `analysis/attack_span_probe.py` and `analysis/attack_c8_screen.py`.

#### 1. WHY (b) FIRST, AND WHY IT MATTERED

Step 11's finding — the model's ATTACK is inert below 1.6 kHz where the pedal's has ±3–7 dB of
authority — now carries the A3 search, and it was measured entirely through ONE instrument: the
blend-axis solve, whose pedal side is a *solved* quantity with a documented upper-bound bias
(session 52 item 3b). Step 11's own next-step (b) said to gate it independently before reading more
into `H_req`. Doing (a) first would have meant plumbing eight `static constexpr` values through
`FitParams`/`TrebleAttack`/`PedalChain`/two CLI maps against a premise that had never been
cross-checked.

`attack_span_probe.py` is that gate, on a completely different instrument: the frozen 63-capture
matrix, differenced as a **matched pair** (the GAP #4 / `grunt_span_probe` method). No solve, no
taper fit, no bleed estimate, no `b0`. Three ATTACK captures exist at each of four drive settings ×
four stimulus levels, so this is far more than the "cheap matched pair" the next-step budgeted for.

Self-test, all three run before any number is read: **(1)** a capture differenced against itself is
identically zero (0.000e+00 dB); **(2)** the report's per-row gain match really is being removed —
worst shift 1.222 dB, so the correction is load-bearing rather than a no-op it never exercises;
**(3) LIVENESS (L-009)** — the model's ATTACK span above 2 kHz is 12.62 dB, because a 220 pF C8
*must* act somewhere. Without (3) the LF null would be indistinguishable from a mis-wired probe.

#### 2. ⭐ THE GATE PASSES, AND THE GRUNT CONTROL IS WHAT MAKES IT AIRTIGHT

Span rms over 80–640 Hz, model vs pedal, across all drives and levels:

| | model | pedal | model/pedal |
|---|---|---|---|
| **ATTACK** (worst over 4 drives × 4 levels) | **0.08 dB** | 5.61 dB | **1 %–13 %** |
| **GRUNT** control, same instrument | **11.63 dB** | 11.94 dB | **71 %–157 %** |

The model's ATTACK span is *below the 0.204 dB span floor* (√2 × the 0.144 dB take-to-take shape
floor) at **every** drive and level. ⭐ **The control is the load-bearing half.** An output span does
not cancel the OD/bleed balance (`grunt_span_probe`'s standing caveat), so "the model's span is ~0"
invites the objection "a switch change just gets diluted at the output". GRUNT — a schematic- and
BOM-verified **linear cap bank on the clipper's input**, i.e. exactly the class of element proposed
for ATTACK — is 138× larger on the identical instrument, same captures, same bands. **So the model's
ATTACK null is inertness, not burial**, and step 11's blend-axis reading is confirmed by an
instrument that shares none of its machinery.

⚠ **One refinement to step 11's framing.** The model's ATTACK is **magnitude**-inert, not
phasor-inert. The exact superposition taps give `d|OD| ≤ 0.132 dB` at every band ≤1700 Hz, but
`d(arg OD)` runs **+1.5° at 80 Hz monotonically to +21.2° at 1613 Hz** (mirrored negative for cut).
That rotation *is* diluted away by the bleed — the decompose's own `full` (= od + bleed) column
predicts a ≤0.12 dB output span over 80–640 Hz and reproduces the report's model rows, which is an
independent cross-check between two renderers with no capture involved. Step 11's §4 quoted d|G|
only; its dtheta column (8.4° / 7.1°) already carried this, but "the model's ATTACK is inert" should
be stated as **magnitude**-inert or it is wrong.

#### 3. ⭐⭐ AND A DISCRIMINATION STEP 11 EXPLICITLY COULD NOT MAKE

Step 11 §5 left two readings open: **(i)** the pedal's ATTACK network has low-mid authority a 220 pF
C8 lacks — a *linear* pre-clipper difference; **(ii)** the pedal's clipper operating point is far
more sensitive to the HF that ATTACK moves — a *nonlinear* difference. The drive × level grid
separates them, because a clipper-operating-point mechanism must **vanish** where the clipper is
idle and a linear pre-clipper element must **not**.

At DRIVE min — the most linear corner in the matrix — the pedal's ATTACK boost span vs stimulus
level (−30 / −18 / −12 / −6 dBFS) is **2.92 / 2.68 / 2.16 / 1.14 dB rms**: it *converges* to ~2.7 dB
as level falls (8 % between the two lowest levels), it does not vanish. The GRUNT control, a known
linear element, has the identical shape (**8.88 / 7.28 / 5.26 / 2.92**) — so the collapse at high
level is a generic clipper+bleed property the model already reproduces, not something peculiar to
ATTACK, and it is not evidence either way. ⇒ **reading (i): a LINEAR, pre-clipper low-mid difference
of ~2.7 dB rms exists in the ATTACK network.**

⚠ Scoped exactly: this establishes a linear component exists. It does **not** show the whole ATTACK
residual at drive-noon/−6 dBFS is linear; reading (ii) may still contribute there.

⚠ **An unresolved discrepancy between the two instruments, recorded rather than explained.** The
blend axis puts boost/cut at 5.01 / 3.18 dB (1.6× asymmetric); the output puts them at 3.51 / 1.03
(3.4×). Dilution is common to both positions, so it does not obviously account for the difference.

#### 4. THEN (a) — AND THE SCREEN RAN BEFORE THE PLUMBING, WHICH IS WHY NO `src/` CHANGE WAS WRITTEN

Session 50's next-step (a) — make the treble ladder reachable — is a `src/` change with the standing
stale-binary trap attached (session 37 item 12). But `eq_reference.treble_attack_tf` **already**
parameterises every ladder element including C8, so reachability can be answered for free first.

`attack_c8_screen.py` predicts the OUTPUT span for a candidate ladder without rendering anything. At
the linear corner the OD path is a product, so a treble-network change enters the BLEND node as one
factor `r(f) = H(boost)/H(flat)`, and `a3_blend_decompose`'s drive-min CSV supplies the model's own
`od` and `cl` phasors by exact superposition — so `span = 20log10|od·r + cl| − 20log10|od + cl|`
needs no bleed estimate and no solve. **The dilution that makes an output span unreadable as a stage
transfer is here computed rather than worried about.**

**Self-test with a known answer:** at the shipped C8 = 220 pF the prediction must reproduce the
model's own *measured* span from the report. It does — boost 0.046 predicted vs 0.047 measured, cut
0.028 vs 0.029, worst per-band difference **0.003 dB**. A wrong `Zs` boundary, position map or
phasor convention fails here.

#### 5. ⛔ C8 ALONE IS REFUTED ON REACHABILITY, NOT ON VALUE

Target (pedal, drive-min, −18 dBFS, 80–640 Hz): **boost 2.68 / cut 0.40 dB rms**, strongly
asymmetric. C8 swept 220 pF → 100 nF, **both positions scored on ONE value** (C8 is a single part
and the switch only reroutes its bottom plate — a C8 that fixes boost while wrecking cut is not a
candidate; the GAP #4 joint-mid-cap failure mode):

| C8 | 220p | 2.2n | 6.8n | 22n | 47n | 100n |
|---|---|---|---|---|---|---|
| boost span rms | 0.05 | 0.44 | 0.89 | 1.11 | 1.17 | 1.20 |
| joint err | 1.94 | 1.81 | 1.54 | 1.40 | **1.40** | 1.41 |

**The boost span saturates at 1.20 dB rms = 45 % of the pedal's 2.68**, and the joint error is FLAT
across 22n–100n (rises +0.00 / +0.01 dB either side of its numerical minimum). ⭐ The tool refuses to
call that an optimum: an "interior minimum" test is not enough, because a saturating curve puts its
argmin in the grid's interior while being flat there — the "objective does not identify this
direction" signature (session 44 item 5), and calling it a minimum is how a degeneracy ships as a
fit. It requires the curve to rise on both sides by more than the capture floor, and it does not.
The mechanism is structural: in boost, C8 bridges R8, and as C8 → ∞ it fully shorts R8, so the lift
is bounded by the R7/R8 divider whatever the value.

#### 6. THE FRONTIER — THE NETWORK REACHES THE SIZE, AT A LARGE SCHEMATIC COST, AND NOT THE SHAPE

Session 49's bridged-T Pareto argument, one stage over: not "this value cannot" but "nothing in the
reachable space can". C8 × R7 × R8 (±1 decade on the resistors, 972 settings) — freeing R7/R8 makes
the bound **stronger**, since they are schematic-verified:

  * max BOOST span reachable **8.93 dB** (cut 1.30) — ⚠ on both resistor grid edges, so it bounds
    what is reachable and identifies nothing;
  * max BOOST with cut ≤ the pedal's **5.96 dB** (cut 0.61) ⇒ **the asymmetry is reachable too**,
    and its mechanism is visible: boost bridges R8 while cut shunts node P against R11, so with
    R8 ≫ R11 the same C8 acts an octave apart in the two throws.

Then the joint fit over C8 × R7 × R8 × RdampC5 (6 damping values added because the pedal's boost
span *collapses* at 320 Hz, GAP #2's notch band, which `trebleLadderDampR = 30k` is known to destroy
— session 46). Scored **twice**, both printed: 320 Hz is a band `a3_shape_gate`'s CORE,
`a3_phase_solve` and the level-axis aggregates all already exclude *by name*, so applying that
exclusion is consistency — but never silently (the session-40 rule).

| | best joint err | at | edges |
|---|---|---|---|
| all 10 bands | 1.06 dB | C8 6.8n / R7 20k / R8 1486k / Rd 100k | R7, RdampC5 |
| **ex 320 Hz** | **0.76 dB** | C8 6.8n / R7 20k / R8 1486k / Rd 30k | R7 |
| shipped | 1.94 dB | 220p / 200k / 470k / 30k | — |

⛔ **Not a candidate, on three counts.** (a) 0.76 dB is **3.7× the 0.204 dB span floor**. (b) R7
rests on its bound in both fits — not identified, the objective wants to keep going. (c) It costs
**×0.10 on R7 and ×3.16 on R8, both schematic-verified** (pixel-zoom + the R1–R54 BOM census) — a far
bigger claim than re-valuing the [ENG] C8.

⭐ **And the residual is a SHAPE the network cannot make.** Per band (boost, drive-min, −18):

| f (Hz) | 80 | 101 | 127 | 160 | 202 | 254 | 320 | 403 | 508 | 640 |
|---|---|---|---|---|---|---|---|---|---|---|
| pedal | −1.74 | +1.10 | +2.85 | +3.79 | **+4.23** | +4.04 | **+0.21** | +2.10 | +2.20 | +1.35 |
| best fit | −2.18 | +0.44 | +2.17 | +3.16 | +3.56 | +3.55 | +3.43 | +3.45 | +3.34 | +2.66 |

The fit tracks 80–254 Hz to ~0.4–0.7 dB and then **plateaus** while the pedal **peaks at 202 Hz and
falls away**. Adding RdampC5 does not recover it — the fit drives damping to the far edge (*more*
damping, further from the schematic 0), so the 320 Hz collapse is **not** GAP #2's notch reappearing.

#### 7. ⇒ NO `src/` CHANGE WAS WRITTEN, AND THAT IS THE RESULT

Next-step (a) asked for the ladder to be plumbed and step 4 re-run, and said that if it cannot close
the residual "that is a reachability refutation of the same shape as session 49's bridged-T Pareto".
It cannot, and the screen delivered that refutation without touching `src/` — which is the whole
reason it was run first. The modelled ATTACK network is a **partial** carrier: the low-mid *size* is
reachable but only by moving two verified resistors by 10× and 3×, the fit is unidentified, and the
shape above 254 Hz is wrong at every setting.

⚠ **Scope, twice.** The screen is the LINEAR corner only; at higher drive the ladder feeds a working
clipper and could do more, and only a real render tests that. And **ATTACK is [ENG]** — the 3-way
switch is not on our schematic at all — so the failure may be the assumed *topology* rather than any
value in it, which is the one hypothesis this screen cannot test.

#### 8. SIDE OBSERVATION, NOT CHASED

The GRUNT control shows the model **over**-delivering at `sweep_clean`: GRUNT flat tracks the pedal
at **137–157 %** at −30 dBFS while sitting at 96–124 % on the driven sweeps. That is the 28 GRUNT
flat/boost rows (GAP #3b) seen on a new axis. Recorded; not this session's item.

#### 9. ▶ NEXT

  * **(a)** The live A3 question is now the ATTACK **topology**, not its values: the modelled
    network can make a shelf, and the pedal makes a **peak at ~202 Hz that falls away above it**. A
    peaking shape needs a resonant/two-path element the [ENG] 3-way switch as drawn does not have.
    Since ATTACK is [ENG] there is no schematic to defer to — but equally, nothing corroborates a
    new topology, so this needs a *measurement* of the pedal's ATTACK transfer shape, not another
    fit. The 8 unused `attack-*_blend-*` captures are the obvious source.
  * **(b)** Carry the §3 result into `H_req`: a linear pre-clipper component of the ATTACK residual
    is now established, so step 11 §5's ambiguity is narrowed (not closed) toward reading (i).
  * **(c)** unchanged: the post-clipper linear class is closed on measurement and on Bode; the
    remaining region is inside/before the clipper (`Clipper.h:309`).
  * **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude.
  * **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
    A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.

### A3 step 13 — the pedal's ATTACK shape is MEASURED bleed-free, the [ENG] ladder topology is refuted on a second independent instrument, and step 11 §5's ambiguity is resolved toward reading (i) (session 57)

Session 56's next-step (a) called for a **measurement** of the pedal's ATTACK transfer shape rather
than another fit, and named the `attack-*_blend-*` captures as the source. That measurement is now
done, on captures that were already on disk. Analysis + tooling only — **nothing in `src/` or
`tests/` changed**, and ctest was RUN (not assumed) at the pre-existing session-44 **16/17**
(`OSValidationTest`, identical `amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`). New tool
`analysis/attack_topology_probe.py`.

#### 0. TWO CORRECTIONS TO THE SESSION-56 HANDOVER, BOTH OF WHICH CHANGE WHAT TO DO

Step 12 §9(a) described "the **8 unused** `attack-*_blend-*` captures". There are **6**
(`attack-{boost,cut}_blend-{0930,1200,1430}_base-od`), and they are **not unused** —
`a3_condition_axis.py:105-111` has read all six since session 54. So (a) was never a fresh data
source waiting to be opened; it is a re-read of data already in the pipeline, which is why it could
be answered the same session it was raised.

Step 12 also placed the pedal's ATTACK peak at **~202 Hz**. That came from the OUTPUT span, which
is diluted by the flat clean bleed by a frequency-dependent amount. Measured bleed-free the peak is
at **~101–127 Hz** (§1). The dilution moved the apparent peak by about an octave. Quote the
bleed-free number.

#### 1. ⭐⭐ THE COMPARISON IS NOW CLIPPER-FREE AND BLEED-FREE ON BOTH SIDES

The ATTACK switch only reroutes C8's bottom plate, so `H(boost)/H(flat)` is a **purely linear
property of the ladder** — no drive, no clipper, no bleed, no dilution model. Session 56's screen
had to *predict* an output span through a dilution calculation; this compares like with like.

LIVENESS (L-009), run first: C8 = 0 makes both throws identical to flat at **0.000e+00 dB** (the
switch really does only move that one plate), and the shipped 220 pF moves **2.36 dB** over the fit
band, so the probe is not inert.

| f Hz | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 | 1613 |
|---|---|---|---|---|---|---|---|---|---|---|
| pedal boost | +6.82 | **+7.19** | +6.87 | +5.95 | +4.62 | +3.65 | +2.01 | −0.39 | −1.26 | −0.41 |
| ladder boost | −0.02 | −0.02 | −0.03 | −0.03 | −0.02 | +0.00 | +0.12 | +0.24 | +0.43 | +2.36 |
| pedal cut | −3.28 | −3.04 | −3.01 | −3.00 | −2.94 | −3.11 | −4.24 | −4.55 | −5.06 | −1.16 |
| ladder cut | −0.03 | −0.04 | −0.06 | −0.07 | −0.09 | −0.11 | −0.16 | −0.19 | −0.24 | −0.83 |

**The modelled ladder is a rising HF shelf; the pedal is a falling low-mid peak.** They have
opposite slopes across the whole identified band — rms error **4.31 dB (boost) / 3.14 dB (cut)**
against the 0.144 dB floor. This is not a value error, and 320 Hz is blind on this axis in every
condition (null-dominated), so the 254/403 pair brackets it rather than measuring it.

#### 2. ⭐⭐ THE LEVEL AXIS RESOLVES STEP 11 §5 — AND IT RESOLVES **AGAINST** READING (ii)

Reading (ii) — the pedal's clipper converting an HF-only network into a broadband low-mid move —
requires the effect to **fade** toward the linear regime. Measured bleed-free at drive noon, the
ATTACK **boost** ratio does the opposite, monotonically, at every band:

| level | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 |
|---|---|---|---|---|---|---|---|---|---|
| −30 dBFS | +7.42 | +8.20 | +8.67 | **+8.98** | **+9.12** | +8.71 | +6.90 | +6.48 | +4.58 |
| −18 | +6.82 | +7.19 | +6.87 | +5.95 | +4.62 | +3.65 | +2.01 | −0.39 | −1.26 |
| −12 | +5.33 | +4.66 | +3.23 | +1.80 | +0.59 | +0.06 | −0.91 | −1.35 | −1.18 |
| −6 | +2.48 | +1.33 | +0.37 | −0.16 | +0.13 | −0.36 | −0.72 | −0.35 | −0.04 |
| linear ladder | −0.02 | −0.02 | −0.03 | −0.03 | −0.02 | +0.00 | +0.12 | +0.24 | +0.43 |

At 254 Hz it runs −0.36 → +0.06 → +3.65 → **+8.71** as level drops 24 dB. In the most linear
condition in the matrix the pedal's ATTACK network has **~9 dB of low-mid authority spanning
80–640 Hz** where the modelled ladder has **0.03 dB**.

⭐ **And the CUT throw is the clincher, because it is level-INVARIANT:**

| level | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 |
|---|---|---|---|---|---|---|---|---|---|
| −30 dBFS | −3.03 | −2.91 | −2.95 | −3.01 | −3.00 | −3.00 | −3.97 | −4.23 | −4.39 |
| −18 | −3.28 | −3.04 | −3.01 | −3.00 | −2.94 | −3.11 | −4.24 | −4.55 | −5.06 |
| −12 | −3.67 | −3.21 | −3.00 | −2.83 | −2.75 | −3.63 | −4.80 | −5.58 | −6.40 |
| −6 | −2.46 | −2.08 | −1.83 | −1.79 | −1.48 | −2.96 | −2.88 | −2.93 | −3.06 |

−3.0 dB at 80–202 Hz across an 18 dB level range. **Boost is strongly level-dependent, cut is not**
— which is exactly what a LINEAR level change ahead of a compressor does: a boost gets progressively
compressed away as level rises, a cut does not. That is a mechanism for the boost/cut asymmetry
session 56 §3 recorded as unexplained (blend axis 1.6× vs output 3.4×), and both halves point the
same way.

⭐ **Two things make this readable rather than suggestive.** (a) The known instrument bias cuts the
right way: `r = √(|g1|²+H)` is an UPPER bound inflated by harmonic power (session 52 §3b), which is
*worse* at high level — so it biases the ratio UP exactly where the effect measures smallest, and
the true trend is steeper than the table. (b) Conditioning **improves** as level falls (law residual
0.043 dB at −30 dBFS vs 0.165 at −6 dBFS, floor 0.144, 13 bands identified throughout), so the
trend is not the low-level end going soft — the noisiest row is the −6 dBFS one where the effect
reads ≈0.

⇒ **Reading (i) — a LINEAR pre-clipper low-mid element the model lacks — is established in
DIRECTION.** ⚠ State it exactly: the magnitude of the linear limit is **not** pinned, because the
level trend has not plateaued at drive noon, and a residual clipper contribution at higher levels is
not excluded. What is excluded is (ii) as the *primary* carrier.

#### 3. ⭐ REACHABILITY — THE TOPOLOGY CANNOT MAKE THE SHAPE, AND THE SEARCH IS GATED

Session 56 scored one value at a time against a predicted span. Here all **11** ladder elements are
freed at once (freeing schematic-verified parts only makes a negative result stronger) and **both
throws are scored with ONE parameter set** — they are the same network.

⚠ **My first attempt FAILED its own gate and was discarded.** Random search returned "best joint
3.04 dB, best D +0.77 dB", but recovered a *definitionally reachable* target to only **0.727 dB**,
with the max-D point resting on **6 of 11 bounds**. A 4× separation between reachable and measured
is not a refutation, it is a weak optimiser. Re-run with differential evolution the gate passes at
**0.0027 dB** on structured targets (including 26 and 30 dB ones), so a failure is now readable.

| box (decades) | best joint shape rms |
|---|---|
| ±1.5 | **3.029 dB** |
| ±3.0 | **3.028 dB** |
| ±6.0 | **3.028 dB** |
| ±9.0 | **3.028 dB** |

**It moves by 0.001 dB across 7.5 orders of magnitude of box widening in every element** —
saturated, not fenced, at **21× the capture floor**. And the fit's boost row is **identically 0.00 dB at every
band**, with cut a frequency-flat −3.12: the optimiser's best move is to switch the boost throw off
entirely rather than trade. That is the "objective cannot reach this direction" signature.

The shape statistic `D = ratio(101 Hz) − ratio(640 Hz)` (how far the effect FALLS across the
low-mids; a capacitive bridge is a high-pass action, so it should be ≤ 0) saturates at **+1.15 dB**
(0.984 / 1.145 / 1.150 / 1.151 at ±1.5 / ±3 / ±4.5 / ±6 decades) against the pedal's **+8.46**.

⚠ **A PATHOLOGY GUARD had to be added, and it is now in the tool.** The unguarded ±9-decade run
reported `D = +88 dB` — apparently reachable. It is not: `D` has the FLAT response in its
denominator, and that point drives flat to **−320 dB** with 72 dB of ripple (C5 = 0.63 F, C9 = 18 F,
R11 = 3.3e14 Ω, R7 = 2.5 mΩ), at a **shape rms of 44.4 dB**. A dead denominator inflates every ratio
without the curve resembling anything. Points whose flat response is implausibly small or ripply are
now rejected.

#### 4. WHAT IS AND IS NOT SETTLED

**Settled:** the pedal's ATTACK effect on the OD path is a low-mid peak centred ~101–127 Hz with
~+9 dB (boost) / ~−3 dB (cut) of authority at the linear end; the drawn [ENG] ladder cannot produce
that shape at any setting of any of its 11 elements; and the carrier is predominantly a **linear
pre-clipper** element, not a clipper-operating-point difference.

**Not settled:** ⚠ the pedal side is a **describing-function** ratio at drive noon — the LEVEL AXIS
is what makes it readable, and no single condition separates (i) from (ii). ⚠ **ATTACK is [ENG]** —
the 3-way switch is not on our schematic at all — so what is refuted is the *assumed* topology,
which nothing corroborated in the first place; this is not a schematic disagreement. ⚠ The linear
limit's magnitude is not pinned (§2).

#### 5. ⭐ THE ONE CAPTURE GAP, NOW PRECISELY SCOPED

Every ATTACK blend ladder is at **drive noon**. At **drive min** the OD path is near-linear, so the
pedal's bleed-free ATTACK ratio there *must equal the ladder's linear ratio exactly* if the topology
is right — an assumption-free test that needs no describing-function caveat at all. The drive-min
flat ladder already exists (`drive-0700_blend-{0930,1200,1430}` + `drive-0700_base-od`), and both
B=1 ATTACK anchors exist (`drive-0700_attack-{boost,cut}_base-od`). Missing is exactly **6 files**:

    drive-0700_attack-{boost,cut}_blend-{0930,1200,1430}_base-od.wav

All six verified to parse through `captures.parse_capture` (drive 0.0, blend 0.25/0.50/0.75) and
confirmed new to the 51-entry matrix. Drive-min identifiability covers 101–1613 Hz (it loses 80 and
806 relative to noon), so the peak region survives.

Two lesser gaps, recorded not requested: **320 Hz is blind on this axis in every condition** (deep
cancellation — an instrument property, no capture fixes it), and `drive-1700_attack-cut_base-od` is
absent while `drive-1700_attack-boost_base-od` exists. There is also no ATTACK-position B=0 control;
ATTACK should be exactly inert at B=0 on physical grounds, but that is the same assumption session
53 spent a capture verifying for DRIVE.

#### 6. ▶ NEXT

  * **(a)** The ATTACK carrier is a linear pre-clipper low-mid network of ~+9/−3 dB authority that
    the drawn ladder cannot be. Since ATTACK is [ENG], the question is what topology to *propose* —
    and the 6 drive-min captures in §5 are what would test a proposal without the
    describing-function caveat. Do not fit a new topology against the drive-noon target alone.
  * **(b)** ✅ DONE — step 11 §5's ambiguity is resolved in direction toward reading (i) (§2).
  * **(c)** unchanged: the post-clipper linear class is closed on measurement and on Bode; the
    remaining region is inside/before the clipper (`Clipper.h:309`).
  * **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude.
  * **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
    A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.

---

### A3 step 14 — the clipper is de-convolved and the ATTACK network's LINEAR transfer is pinned over 80–254 Hz; the required SHAPE is specified; and 403–640 Hz is shown to be undecidable on this axis (session 58)

Session 57's next-step (a) was: the ATTACK carrier is a linear pre-clipper low-mid network the drawn
ladder cannot be, ATTACK is `[ENG]` so the question is what topology to **propose** — and "do not fit
a new topology against the drive-noon target alone". This session did not fit a topology. It did the
two things that have to come first: turned the measurement into a **specification** (what order and
what corner frequencies must a proposal realise?) and then **removed the describing-function caveat
arithmetically**, which turned out to be possible from captures already on disk.

Analysis + tooling only — **nothing in `src/` or `tests/` changed**, and ctest was RUN (not assumed)
at the pre-existing session-44 **16/17** (`OSValidationTest`, identical `amp 0.35: 2x −25.6 /
4x −32.1 / 8x −23.6`). New tools `analysis/attack_tf_spec.py`, `analysis/attack_linear_extract.py`.
Baseline verified first: `attack_topology_probe.py --selftest` reproduces session 57's liveness
(C8 = 0 → 0.000e+00 dB, shipped 220 pF → 2.36 dB) and its search gate (worst recovery 0.0024 dB).

#### 1. THE SPECIFICATION — what order does the ATTACK ratio actually demand?

`attack_tf_spec.py` fits minimum-phase rational families of rising order to the bleed-free ratio at
the most linear condition in the matrix (`sweep_clean`, −30 dBFS), and reports where the residual
reaches the floor. The floor for a ratio of two solved quantities from the same instrument is
**√2 × 0.144 = 0.204 dB**, not 0.144 (the session-56 §2 convention).

⚠ **A self-test gate had to be fixed before any of this could be read.** At order 3 differential
evolution converged to a **0.360 dB local minimum on a target the family had generated itself**,
deterministically, at both budgets — a family that cannot recover its own parameters makes a large
residual on real data unreadable. Adding multi-start local refinement (60 random `least_squares`
starts on top of DE) takes every family to **0.00000 dB** recovery. This is a correctness
requirement, not a speed tweak, and it is the same lesson as session 57's discarded random search.

| family | BOOST rms | CUT rms |
|---|---|---|
| order 0 — flat gain | 1.859 | **0.566** |
| order 1 — shelf | 0.656 | 0.533 |
| order 2 — two real shelves | 0.350 | 0.315 |
| order 2 — resonant (biquad) | 0.322 | 0.114 |
| order 3 | 0.313 | 0.090 |

⭐ **CUT is, to 0.57 dB, a frequency-flat gain of −3.2 dB across the whole 80–1613 Hz band.** Order 0
— no corners at all. Everything below that is a single feature near 600 Hz (see §4).

⛔ **BOOST saturates at ~0.31–0.35 dB, 1.5–1.7× the floor, and never reaches it.** Order 2 buys
0.30 dB over order 1 and order 3 buys a further 0.01 dB — and both higher orders get there only by
parking a corner **off-band** (21 Hz, 0.5 Hz) or by landing a zero **on top of a pole** (228/200 Hz;
597/612 Hz for cut). Those are the "this order adds nothing" signatures, reported explicitly by the
tool rather than quoted as fitted values. **So the boost shape is not a low-order minimum-phase
rational**, and the honest read of that is not "the pedal contains something exotic" — it is that
~0.3 dB of the target is structure the fit cannot represent, which §3 then explains.

#### 2. ⭐⭐ THE CLIPPER IS DE-CONVOLVED — AND IT NEEDS NO NEW CAPTURES

Every ATTACK number since session 55 is a describing-function ratio, and session 57 had to state
that "the linear limit's magnitude is NOT pinned". It can be pinned, from the existing captures,
with one identity.

Write the OD path as `linear A(f) → clipper → linear B(f)` and let ATTACK insert a linear factor
`h(f)` ahead of the clipper. Under a **swept sine the clipper sees one tone at a time**, of
amplitude `|A(f)|·L`, so its describing-function gain is a function of that single scalar:

```
    r_ref  (f, L) = |B·A| · n(|A|·L)
    r_boost(f, L) = |B·A| · h · n(h·|A|·L) = h · r_ref(f, L + h)

⇒   ratio_dB(f, L) = h_dB(f) + S_f(L + h_dB) − S_f(L)
```

where `S_f` is **the pedal's own ref transfer as a function of stimulus level** — measured, not
modelled. The right-hand side is monotone in `h`, so `h` is solved per band per level by bisection.
Nothing about the clipper is assumed but memorylessness: its shape, rails and drive dependence all
cancel.

⭐ **And session 52 §3b's upper-bound bias cancels exactly here.** `r = √(|g1|²+H)` is inflated by
harmonic power, worse at high level — the standing caveat on every blend-axis number. In this
identity, boost at level `L` and ref at level `L+h` present the clipper with the **identical input
waveform**, so they carry identical harmonic power, and the identity equates two measurements rather
than a measurement to a model. This is the first ATTACK instrument not exposed to that bias.

Gates, all run first: self-test recovers a known `h(f)` through a known compressor to **1.8e-15 dB**
over 28 cells; liveness (`h = 0` → `0`) to the same; and **no extrapolation** — `L + h` must land
inside the captured level range or the cell prints `--`.

**The enabling measurement, and it is new: the pedal's own OD transfer vs level, per band.** Its
total variation is the **compression budget** — the most level dependence any pre-clipper linear
element can borrow from the clipper at that band.

| f Hz | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 | 1016 | 1280 | 1613 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| budget dB | 0.31 | 0.77 | 1.68 | 2.71 | 4.18 | 4.34 | **0.93** | **1.42** | **0.75** | 5.58 | 9.40 | 12.23 |
| min\|t\| | 0.152 | 0.196 | 0.234 | 0.251 | 0.241 | 0.169 | 0.159 | 0.163 | 0.154 | 0.152 | 0.166 | 0.187 |

#### 3. THE RESULT — h(f) pinned over 80–254 Hz, and 403–640 Hz shown to be undecidable

One `h` per band, fitted across a **fixed level subset chosen by feasibility and identical at every
band** (a positive `h` pushes `L+h` past the hottest captured row, so BOOST can only use the two
quiet rows; CUT drops −30 and keeps three). ⚠ The first draft let each band pick its own subset and
the summary line then claimed a uniform "3 levels each" while the table showed 2 and 3 — the
session-49 item-7 aggregate-over-different-members trap, in my own gate, caught and fixed.

| f Hz | h BOOST dB | resid | h CUT dB | resid |
|---|---|---|---|---|
| 80 | **+7.03** | 0.289 | **−3.15** | 0.426 |
| 101 | **+7.83** | 0.343 | **−2.92** | 0.340 |
| 127 | **+8.24** | 0.511 | **−2.91** | 0.281 |
| 160 | **+8.38** | 0.876 | **−3.00** | 0.177 |
| 202 | **+8.44** | 1.325 | **−3.09** | 0.111 |
| 254 | +7.77 | 1.631 | −4.01 | 0.754 |
| 403 | +4.78 | 2.255 | −4.17 | 0.843 |
| 508 | +3.55 | 3.278 | −4.45 | 1.432 |
| 640 | +1.66 | 2.940 | −4.61 | 1.661 |

**CUT: mean residual 0.267 dB / worst 0.426 over 80–202 Hz — within 2× the floor, and 0.111 at
202 Hz is BELOW it.** So the cut throw is a **frequency-flat −3.0 dB linear attenuation ahead of the
clipper**, and that is now a measured quantity rather than a description of a trend.

**BOOST: +7.0 → +8.4 dB rising from 80 to 202 Hz**, residual 0.29–1.33 (1.4–6.5× floor). ⭐ Note
this is a genuine de-convolution at the mid bands: at 254 Hz the raw drive-noon ratio reads **+3.65
dB** and `h` is **+7.77** — the clipper had eaten 4 dB.

#### 4. ⛔ AND A FIT-FREE BOUND SAYS 403–640 Hz CANNOT BE DECIDED ON THIS AXIS

Because `ratio(L) = h + S(L+h) − S(L)`, subtracting two levels makes **`h` drop out entirely**:

```
    |ratio(L1) − ratio(L2)|  ≤  2 · TV(S)
```

so if the measured ratio swings by more than twice the band's compression budget, **no linear
pre-clipper factor of any value can produce it**. Nothing is optimised, so this is the strongest
form of the result. Using the budget over the full captured range makes it generous.

| f Hz | 403 | 508 | 640 | (all others) |
|---|---|---|---|---|
| BOOST swing dB | 4.90 | 6.88 | 5.84 | within budget |
| 2 × budget | 1.86 | 2.84 | 1.49 | — |
| **excess** | **+3.03** | **+4.03** | **+4.35** | — |

CUT exceeds only marginally and only at 80 Hz (+0.60), 403 Hz (+0.06) and 640 Hz (+1.85).

⚠⚠ **DO NOT read this as "the boost throw is not a linear pre-clipper element."** The three
offending bands are exactly the three where the pedal's OD **fundamental is weakest** (−17.0 / −17.1
/ −18.6 dB — the bridged-T scoop) while its neighbours an octave down sit **4–6 dB hotter**. That is
precisely where harmonics generated at `f/2`, `f/3` … leak most into the band, i.e. where the
instrument's own `r = √(|g1|²+H)` upper bound is loosest. And the exact-cancellation argument in §2
requires `h` to be flat with frequency to hold for the leaked harmonics too — over 403–640 Hz the
fitted `h` falls 3 dB, so it is not. **The excess is real as measured; this axis cannot separate "the
boost throw does something a pre-clipper linear factor cannot" from "harmonic leakage inflates the
swing at the three scoop bands".** That is also the most likely source of §1's irreducible ~0.31 dB.

⭐ **Conditioning was checked as an alternative and does NOT explain the pattern.** `min|t|` (the
blend ladder's closest approach to a cancellation null) is flat across the band at 0.152–0.251 and
does not track the residual at all — 80 Hz is among the worst-conditioned (0.152) and has the
*smallest* boost residual, while 202 Hz is the best-conditioned (0.241) and has a residual 4.6× larger.
So the degradation is a property of frequency, not of null-dominance.

#### 5. WHAT IS AND IS NOT SETTLED

**Settled.** The ATTACK network's linear transfer, clipper-de-convolved, over 80–254 Hz:
**boost +7.0 → +8.4 dB rising to a maximum near 202 Hz; cut −3.0 dB, frequency-flat.** The cut throw
is a plain flat attenuation to within 2× the capture floor over 80–202 Hz and needs **no corners at
all** across the whole measured band. The two throws are therefore **strongly asymmetric in the
linear domain** (+8 vs −3, peaked vs flat) — which matters for a topology proposal, because a single
element rerouted between two positions would not naturally give one peaked throw and one flat one.

**Not settled.** ⚠ 403–1613 Hz on the boost throw — §4. ⚠ The `[ENG]` status is unchanged: nothing
corroborates any ATTACK topology, so `h(f)` above is a **specification a proposal must meet**, not a
disagreement with a drawn circuit. ⚠ Magnitude only; this axis has no phase, so these are
minimum-phase statements and a non-minimum-phase realisation is not excluded. ⚠ `h` is placed ahead
of the clipper because sessions 55–57 established the carrier is pre-clipper; an element **inside**
the clipper's feedback loop would not satisfy the §2 identity at all, and remains the natural reading
of §4's excess if it survives the drive-min captures.

#### 6. ▶ THE CAPTURE REQUEST IS NOW SHARPER, AND IT IS THE SAME SIX FILES

Session 57 scoped six drive-min ATTACK blend files. §4 raises their value: **at drive min the
compression budget goes to ~0 at every band**, so the measured ratio *is* `h(f)` directly — no
de-convolution, no leak-vs-physics ambiguity, and 403–640 Hz becomes decidable. Written up as
`docs/session58-capture-request.md`, with the settings, the two standing traps and the known gaps.
All six re-verified this session: they parse through `captures.parse_capture`, they are absent from
the matrix, and `render_args` genuinely emits `--attack 1` / `--attack 2` for them (checked, because
a switch position that parses but is not passed to the renderer is exactly the session-20
`--input-trim` defect — my first check of this was a flawed flat-membership diff that reported no
difference; the real diff is clean).

#### ▶ NEXT

* **(a)** The 6 drive-min captures (`docs/session58-capture-request.md`) — they convert §3's
  80–254 Hz result into a whole-band linear transfer and settle §4. Until then **do not propose a
  topology against 403–640 Hz**, which is the region a proposal would most want to fit.
* **(b)** With `h(f)` in hand, a proposal must produce **+8 dB peaked at ~200 Hz on one throw and a
  flat −3 dB on the other, from one 3-position switch**. §1 says cut needs **no corners**, so the
  cheapest structure consistent with both is a switch whose cut position is a plain attenuation and
  whose boost position is not the same element rerouted.
* **(c)** unchanged: the post-clipper linear class is closed on measurement and on Bode; the
  remaining region is inside/before the clipper (`Clipper.h:309`).
* **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude.
* **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
  A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.

### A3 step 15 — the 15 new captures: the drive-min premise EXPIRES on the instrument rather than the physics, and the drive-max ladders settle the PRE-clipper placement out-of-sample (session 59)

Tooling + analysis only — **nothing in `src/` or `tests/` changed**, and ctest was RUN (not assumed)
at the pre-existing session-44 **16/17** (`OSValidationTest`, identical `amp 0.35: 2x −25.6 /
4x −32.1 / 8x −23.6`). New `analysis/attack_drive_axis.py`. New report
`analysis/reports/s59_matrix100.json` — a **strict superset** of `s54_matrix85.json`, proven, not
assumed: all 85 prior captures present and **20 400 values bit-identical (worst |Δ| = 0.000e+00)**,
so every session-54–58 number is unmoved.

#### 0. The captures, verified first

The user delivered **15 files**, not the 6 requested: the six drive-min ATTACK ladders, **both B=0
controls** (§6's "worth one extra file", taken for both throws), the **entire drive-max ATTACK
ladder** (6 files), and `drive-1700_attack-cut_base-od.wav` (the matrix asymmetry session 57 §6
recorded). All 15 verified before any analysis: filenames parse through `captures.parse_capture`;
`render_args` genuinely emits `--attack 1` / `--attack 2` while a non-ATTACK control emits
`--attack 0`; 48 kHz, 83.700 s, no truncation; **no clipping** on the real signature (longest run of
consecutive near-peak samples ≤ 8, and the one file with a run of 8 peaks at 0.159); and every BLEND
ladder's RMS falls **monotonically** (the cheap form of session 54's geometric test that caught
MASTER left at 1430).

#### 1. ⭐ The B=0 ATTACK control PASSES — a standing assumption is now verified

Every ATTACK ladder since session 55 divides by `blend-0700_base-od.wav`, on the argument that at
BLEND = 0 the OD path is out of circuit so ATTACK cannot matter. Session 53 spent a capture verifying
the equivalent for DRIVE; for ATTACK it had never been tested. Over 20 bands 20–1700 Hz: **boost mean
−0.009 dB / worst −0.062; cut mean +0.036 / worst +0.051**, against the 0.144 dB floor. Valid.

#### 2. ⛔⛔ THE DRIVE-MIN PREMISE IS HALF RIGHT, AND THE HALF THAT FAILS IS THE INSTRUMENT

`docs/session58-capture-request.md` argued that at drive min the compression budget → 0, so the
measured ratio simply **is** `h(f)`, with no de-convolution and 403–640 Hz decidable. **Drive min does
idle the clipper. It also drops the pedal's OD path to ~−15 dB relative to the clean bleed** (vs
−13 at noon, −4 at max), and the blend axis measures exactly that ratio. The ladder
`t(B) = |β(B) + B·G|` then degenerates to `β(B) + B·Re(G)`: only the **projection** survives, `(r, θ)`
collapse to a ridge, and the fitted BLEND taper absorbs the difference. That is **session 47 item 11's
small-µ degeneracy at a new operating point**.

⭐ **This is PROVEN with a known feature, not argued from conditioning.** The IC2_B bridged-T sits
AFTER the clipper, is schematic-verified on both schematics and capture-confirmed (GAP #1b, 116 OD
rows), and its broad 400–700 Hz scoop **cannot depend on the DRIVE knob**. Measured as |G| at 202 Hz
minus the mean of 403/508/640 Hz:

| condition | sweep_clean | sweep_drv_−18 |
|---|---|---|
| drive min | **0.6 dB** | **0.7 dB** ⛔ absent |
| drive noon | 5.2 | 5.3 |
| drive max | 10.9 | (640 Hz unidentified) |

A solve that has lost a network physically obliged to be there is not measuring the OD path, whatever
its law residual says. Corroborating statistics, both computed: the boost/flat ratio **moves 0.94–2.69 dB**
under an equally defensible taper choice at drive min, versus **0.10–0.24 dB** at noon and **0.00–0.17 dB**
at max; and noise propagation (`--selftest` gate 3, 200 trials at the pedal's own 0.144 dB
take-to-take) gives at |G| = −15 dB only **84/200 solves, bias −1.53 dB, ratio error ±1.12 dB**,
against −3 dB's **200/200, bias +0.03, ±0.38**.

⇒ **The six drive-min captures are sound; the blend axis cannot read them. 403–640 Hz is STILL
undecided.** ⭐ The general lesson, and it is the useful one: **the DRIVE axis trades compression
against sensitivity in BOTH directions** — drive min removes the clipper but buries the signal, drive
max exposes the signal but compresses the effect away. Drive noon is the sweet spot, not an
unfortunate compromise.

⚠ **And the budget at drive min is not ~0 either — it is 1.70–2.75 dB**, because the **J201 sits
UPSTREAM of the DRIVE pot** (circuit.md), so it sees the same level at every drive setting and its own
compression never goes away. Drive min idles the **clipper**, not the OD path. (Drive noon 0.31–4.34;
drive max 14.03–22.68.)

#### 3. ⭐⭐ THE DRIVE-MAX LADDERS SETTLE THE PLACEMENT — OUT-OF-SAMPLE

The bonus drive-max ladders were **never part of session 58's fit**, so they are a test set rather
than more fitting data. Session 58 published `h(f)` from drive-noon captures alone; predict the
drive-max ratio from it and from drive max's **own** measured level transfer,
`ratio = h + S_max(L+h) − S_max(L)`, with nothing fitted. Drive max compresses so hard (budget
14–22 dB) that a **pre**-clipper `h` of +8 dB must be squashed to ~0, while a **post**-clipper element
of the same size arrives undiminished. The two hypotheses predict ~+0.3 dB and ~+8 dB.

| BOOST | 80 | 101 | 127 | 160 | 202 |
|---|---|---|---|---|---|
| s58 `h` (drive noon, published) | +7.03 | +7.83 | +8.24 | +8.38 | +8.44 |
| PREDICTED, `h` pre-clipper | +1.09 | +0.48 | +0.28 | +0.28 | — |
| PREDICTED, `h` post-clipper | +7.03 | +7.83 | +8.24 | +8.38 | +8.44 |
| **MEASURED at drive max** | **+1.24** | **+0.45** | **+0.24** | **+0.28** | **+0.44** |

**Pre-clipper rms residual 0.08 dB — below the 0.144 dB take-to-take floor — against 7.50 dB for
post-clipper.** A ~90× separation, on data the fit never saw. CUT is the same direction but weaker:
**0.84 dB vs 2.50 dB**, with a systematic residual (+1.14 → +0.45, monotone), which is about the size
of the drive-max cut throw's own taper sensitivity — consistent within the instrument's demonstrated
stability, not sharp.

⇒ **Sessions 55–58 placed `h` ahead of the clipper because the earlier sessions had put the carrier
there. It is now MEASURED, out-of-sample.**

#### 4. ⚠ HOW STRONG THAT TEST IS ABOUT `h`'s VALUE — stated, not glossed

Heavy compression is what makes §3 decisive about the **mechanism** and is the same thing that makes
it weak about the **value**: once the clipper is squashing, a wide range of `h` predicts nearly the
same output. Scanning `h` and keeping everything that predicts the measured ratio within the 0.204 dB
ratio floor: **80 Hz [5.6, 8.8] | 101 [3.0, 12.0] | 127 [0.7, 12.0] | 160 [1.7, 12.0] | 202 [5.2, 6.0]**.

**4 of 5 intervals contain session 58's published value; 202 Hz does NOT** ([5.2, 6.0] vs +8.44). That
is a genuine disagreement between the two drives at that one band, recorded rather than rounded up —
the tool computes the count and prints the warning itself rather than narrating a conclusion above a
table that contradicts it. Either way the widths mean **drive max CORROBORATES `h`; it does not
re-measure it. Session 58's drive-noon `h(f)` remains the estimate of the value.**

#### 5. What is settled, and what is not

* ✅ The shared B=0 normaliser is **verified** for the ATTACK conditions (§1).
* ✅ `h` is **PRE-clipper**, measured out-of-sample at ~90× in rms residual (§3).
* ✅ Session 58's de-convolution identity survives an independent condition it was not fitted on.
* ⛔ **403–640 Hz is still undecided.** The drive-min route fails on the instrument (§2), not on the
  captures.
* ⚠ 202 Hz shows a real drive-max/drive-noon disagreement on `h`'s value (§4).
* ⚠ Everything remains `[ENG]` and magnitude-only: `h(f)` is a **specification a topology proposal
  must MEET**, not a disagreement with a drawn circuit, and minimum-phase statements only.

#### ▶ NEXT

* **(a)** ⭐⭐ **TWO FILES — `docs/session59-capture-request.md`.** The capture that decides
  403–640 Hz is drive min at **LEVEL MAX**, and the method is **validated on a file already on disk,
  not proposed** (§6 of `attack_drive_axis.py`). At LEVEL max the wiper shorts to the OD source so the
  clean bleed is **exactly zero** (`level_blend_tf`), and LEVEL sits **after every nonlinearity**
  (circuit.md), so it cannot move the clipper's operating point. At BLEND max the output then simply
  **is** the OD path, and `h(f)` is a plain subtraction — no ladder, no taper, no `b0`, no solve, no
  de-convolution. Pre-flight on the existing `drive-0700_level-1700_base-od.wav`: the **bridged-T
  scoop is back at 6.0–6.1 dB** (vs 0.7 dB for the failed route), |G| is up ~8 dB into the
  well-conditioned range, and the −30/−18 dBFS curves agree to ~0.1 dB. Only
  `drive-0700_level-1700_attack-{boost,cut}_base-od.wav` are missing.
  **Gate any capture set on the bridged-T scoop before reading a ratio off it.**
* **(b)** unchanged: with `h(f)` in hand a proposal must make **+8 dB peaked at ~200 Hz on one throw
  and a flat −3 dB on the other, from one 3-position switch**; session 58 §1 says cut needs **no
  corners**. Do not fit a topology against 403–640 Hz until (a) lands.
* **(c)** unchanged: the post-clipper linear class is closed on measurement and on Bode; the
  remaining region is inside/before the clipper (`Clipper.h:309`).
* **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude.
* **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
  A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.

### A3 step 16 — h(f) is MEASURED whole-band by plain subtraction; 403–640 Hz is DECIDED; the throw is BROADBAND, and sessions 57/58's "202 Hz peak" is a bleed artefact (session 60)

**The two requested captures landed** (`drive-0700_level-1700_attack-{boost,cut}_base-od.wav`), plus
**two unrequested bonus files** at the same operating point,
`drive-0700_level-1700_grunt-{flat,boost}_base-od.wav`, which turned out to matter (see §4 below).
Tooling + analysis only — **nothing in `src/` or `tests/` changed**, and ctest was **RUN** (not
assumed) at the pre-existing session-44 **16/17** (`OSValidationTest`, identical `amp 0.35: 2x −25.6
/ 4x −32.1 / 8x −23.6`). New `analysis/attack_level_extract.py`, `analysis/extract_m36.py`. New
report `analysis/reports/s60_matrix104.json`, proven a **STRICT SUPERSET** of `s59_matrix100.json`
(all 100 present, **24 000 values bit-identical, worst |Δ| 0.000e+00**), so no session-54–59 number
moves.

**(1) The captures verified first.** All four parse through `captures.parse_capture`; `render_args`
emits `--drive 0.000000 --level 1.000000 --blend 1.000000` for every one and differs from the flat
reference in **exactly one flag** (`--attack 1`/`2`, or `--grunt 2`/`0`); 48 kHz / 83.700 s /
float32; peaks 0.28–0.53 with no flat-topping.

**(2) ⭐ THE ZERO-BLEED PREMISE IS BOUNDED BY MEASUREMENT, not trusted from the model.** The route
rests on `level_blend_tf` giving exactly zero bleed at LEVEL max — a claim about an *ideal* pot. A
real bleed cannot exceed the deepest |G| anywhere in the set, which is **−34.0 dB** (attack cut @
40 Hz). That bounds the worst-case (fully coherent) dilution of `h` at **≤0.87 dB** across 80–640 Hz.
⭐ **And a bleed common to all three files dilutes `h` TOWARD ZERO**, so every number below is a
**LOWER bound on |h|** — residual bleed cannot manufacture the +8.6 dB, only shrink it.

**(3) ⚠ THE PLAIN SUBTRACTION IS *NOT* h, AND THE PRE-FLIGHT THAT JUSTIFIED THIS REQUEST COULD NOT
HAVE SEEN IT.** Session 59 step 6 validated the route by showing the **flat reference** agrees
between −30 and −18 dBFS to ~0.1 dB. That does not transfer to the throws: **boost pushes ~8 dB more
signal into the J201, which sits upstream of DRIVE and never idles.** Measured, boost's raw ratio
moves **2.41 dB at 640 Hz** between those two levels while cut moves 0.27. Session 58's
de-convolution identity `ratio = h + S_f(L+h) − S_f(L)` was therefore applied here too — where it is
far better conditioned, because `S_f` is now a plain difference of two raw measurements rather than a
solved quantity. Gates: recovery of a known `h` through a known compressor to **2.4e-11 dB**,
liveness `h=0 → 0`, and **NO EXTRAPOLATION** (`L+h` must land inside the captured range or the cell
prints `--`).

**(4) ⭐⭐ AND THE FIX WAS A LEVEL THE MATRIX HAS NEVER READ.** `gen_test_signal.py` writes **two**
clean-end sweeps — `sweep_clean` at −30 dBFS and **`sweep_clean_-36` at −36** — but
`comprehensive_report.py`'s `ALL_SWEEP_LEVELS` stops at −30, so the −36 point has sat unread in
**every capture in the matrix since the first capture session**. `analysis/extract_m36.py` pulls it
out **pedal-side only** (no render, so no staleness risk) into a separate side file — deliberately
**not** a change to `comprehensive_report.py`, which is a shared oracle with 7+ importers whose
record shape and result-cache key would both have moved. Its self-test asserts the reference-segment
convention rather than arguing it: the two conventions differ by **exactly +6.000 dB with 6.8e-08
spread**, i.e. a constant, which cancels in every difference taken here.

**(5) ⭐⭐ WITH −36 dBFS THE MEASUREMENT IS DEMONSTRABLY CONVERGED, so h is READ, not inferred.**
Boost's two quietest levels (−36, −30) agree to **worst 0.065 dB** at every band — under the
√2 × 0.144 = **0.204 dB** floor — including 508 (0.018) and 640 (0.065), the two bands that were
still moving 1.5–2.4 dB between −30 and −18. At that level **`raw minus solved` is worst 0.027 dB**:
there is nothing left to de-convolve, so the de-convolution is *confirmatory, not load-bearing*.
⚠ **The read is from the converged levels only, NOT a mean over all of them** — averaging in the
compressing rows would drag 640 Hz from its converged +7.25 to +5.48 purely by mixing members, the
session-49-item-7 / session-58-item-3 trap.

**(6) ⭐⭐ THE RESULT — 403–640 Hz IS DECIDED, AND THE THROW IS BROADBAND.**

| h, dB | 40 | 50 | 64 | 80 | 101 | 127 | 160 | 202 | 254 | *320* | 403 | 508 | 640 | 806 | 1016 | 1280 | 1613 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **boost** | +7.95 | +10.14 | +9.08 | **+8.64** | +8.52 | +8.53 | +8.61 | +8.68 | +8.52 | *+0.53* | **+8.54** | **+8.13** | **+7.25** | +8.42 | +9.22 | +9.14 | +9.06 |
| **cut** | −5.85 | +1.05 | +0.20 | **−0.79** | −1.38 | −1.70 | −1.87 | −2.00 | −2.40 | *−3.40* | **−1.66** | **−2.14** | **−2.40** | −2.29 | −2.43 | −2.72 | −2.93 |

⭐ **Boost is a BROADBAND ~+8.6 dB, essentially flat from 80 Hz to 1.6 kHz (±1 dB), not a low-mid
peak.** Cut is ~**−2 to −3 dB**, also broadly flat above ~100 Hz, tending to 0 at the LF end.

**(7) ⭐⭐ WHICH MEANS SESSIONS 57/58's "PEAK AT ~202 Hz" IS A DILUTION ARTEFACT — computed, not
argued.** An **independent** drive-min ATTACK pair already existed, captured on a different day at
**LEVEL noon** where the bleed is *not* zero; referenced the same way it gives session 57's shape
exactly — a pronounced **+4.50 dB peak at 202 Hz**. Predicting that curve from the bleed-free `h`
plus the known LEVEL/BLEND coefficients (`a=0.180`, `b=0.142` at LEVEL noon vs `a=1`, `b=0` at max),
phase-bracketed because the od-vs-clean phase is unmeasured, puts the **peak at 202 Hz — the same
band as the measurement, and the same band as the |OD| maximum**. Dilution is weakest where |OD| is
strongest, and |OD| peaks at the bridged-T's 202 Hz shoulder. ⇒ **the "resonance" was the bleed
sculpting a flat gain.** ⚠ The envelope uses a nominal LEVEL taper and 4 of 9 bands sit 0.2–0.6 dB
outside it, so the **peak LOCATION is the claim; the fit is not exact.**

**(8b) ⚠⚠ CORRECTION — RAISED BY THE USER FROM AN FR CHART, CONFIRMED AT FULL RESOLUTION.** The
user asked whether this effort was missing the pedal's small peak between the two large mid peaks.
At 5.9 Hz bins on `ref-od`/drv_−12 those features are a sharp **MIN at 316.4 Hz** and a **MAX at
421.9 Hz**. Two results, and the second corrects (8).
⭐ **(i) THE BROADBAND RESULT SURVIVES.** At full resolution on the LEVEL-max set, `h` is smooth and
flat ~+8.5 dB **everywhere outside a narrow 287–351 Hz window** — +8.50@381, +8.49@404,
**+8.46@422**, +8.34@451, +8.03@510, +7.14@639, +8.27@809, +8.97@1002. **The 421.9 Hz peak cancels
EXACTLY in the ratio**: it belongs to the shared path and is present identically in every ATTACK
position, so it does not corrupt `h`, and 403/508/640 are not sitting on sharp features. The
1/3-oct grid is adequate for `h` **except** across the notch.
⛔ **(ii) BUT ATTACK MOVES THE CANCELLATION NOTCH — a pure broadband gain cannot.** Bleed-free,
drive min: **cut 316.4 Hz (depth 14.9 dB) | boost 328.1 Hz (32.7) | flat 334.0 Hz (16.0)**, i.e. the
null shifts ~18 Hz and **more than doubles in depth** on boost. Robust: identical **to the bin** at
−36/−30/−18 dBFS, migrating only at −12 where compression starts (session 46's 334 → 299 Hz).
⇒ **the ATTACK network IS two-path / interacts with the notch-forming network**, consistent with
circuit.md's ATTACK rerouting C8 *inside* the treble network. **Full spec: a broadband ±gain AND a
null moving 316.4/328.1/334.0 Hz at depth 14.9/32.7/16.0 dB.** ⭐ **This couples ATTACK to GAP #2** —
the model's notch is destroyed by `trebleLadderDampR = 30k` (session 46), so ATTACK and GAP #2 are
the SAME network and must be solved together. ⚠ These numbers came from an **ad-hoc probe**, not a
gated tool.
✅ **SUPERSEDED BY §4 "A3 step 17" (session 61), which reproduces every figure here to the bin and to
0.03 dB under gates — and refines three things this paragraph got loose:** "identical to the bin at
−36/−30/−18" is true of **frequency only** (boost's depth spreads 5.11 dB across those rows); the
287–351 Hz exclusion window **under-covers** (measured: 269.5–369.1 boost, 269.5–521.5 cut); and
"flat" is a strong description of **boost** (spread 22 % of its own size) but a weak one of **cut**
(86 %, and the shared 421.9 Hz peak does **not** cancel there). Quote step 17's numbers.

**(8) ⇒ THE BROADBAND SHAPE REQUIREMENT IS SIMPLER THAN RECORDED (but read (8b) first).** Session 57 concluded the network
needs "a resonant/two-path element" and session 58 specified "+8 dB **peaked at ~200 Hz** on one
throw and a flat −3 dB on the other". **Both of those shape claims are now superseded.** The
measured requirement is: **one 3-position switch giving a broadband ~+8.6 dB on one throw, ~−2.4 dB
on the other, and 0 in the middle, essentially flat across 40 Hz–1.6 kHz.** ⚠ "No resonator is
required" was an OVER-CLAIM — see (8b)(ii). ⚠ It is a **pre-clipper** gain (session 59 item 4 measured that placement out-of-sample,
~90× in rms residual), and 220 pF of C8 cannot produce it at 40 Hz — so this remains a refutation of
the *assumed* `[ENG]` ladder, not of any drawn circuit.

**(9) ⚠⚠ 320 Hz IS NOT A TRANSFER VALUE — do not fit to it.** It reads +0.53 (boost) / −3.40 (cut)
and is level-stable at the quiet end, but it is a **1/3-octave sample sitting ON the TrebleAttack
two-path cancellation notch**, which session 46 measured at full resolution as **316–334 Hz and
MIGRATING with level** (334 → 299 Hz). A band average across a sharp, moving notch depends on where
the notch sits inside the band, not on the network's gain there — session 46's own lesson ("never
read a notch's depth off the 1/3-oct grid", which understated it by up to 20 dB). That ATTACK moves
this band hard is real and expected (it reroutes C8 *inside* the network that forms the notch); the
**number** is not a gain. 254 and 403 bracket it.

**(10) ⚠ AND ONE GATE GENUINELY FAILED — recorded, not explained away.** The MODEL control
de-convolves GRUNT (a schematic+BOM-verified **linear** cap bank at the clipper input, so a
pre-clipper linear element is the model's ground truth *by construction*) and its solved `h` is
**NOT** level-independent: spread **5.27 dB** (grunt flat) and **12.75 dB** (grunt boost). Two
things make that readable rather than fatal. (a) GRUNT's `h` is ~**+20 dB**, so `L+h` leaves the
captured range at every level except −30, and the only bands where a spread is computable at all are
**403/508/640 — the bridged-T scoop floor**, where the OD fundamental is weakest and harmonic
leakage from `f/2`, `f/3` is worst (session 58 item 4's mechanism, reproduced here independently on
the model). (b) **The headline does not depend on the de-convolution at all** — at −36 dBFS raw and
solved agree to 0.027 dB. ⇒ **the de-convolution degrades when `h` is large relative to the sampling
of `S`, and at the scoop bands. Do not carry it to a large-`h` element without re-gating.**

**(11) OUT-OF-SAMPLE vs SESSION 58, stated as a disagreement rather than resolved by fiat.** Boost
agrees to **0.23–0.29 dB at 127–202 Hz** but differs by **+1.61 dB at 80 Hz** (rms 0.81); cut
differs by **+1.09…+2.36 dB** at every band (rms 1.54) and, more importantly, in **shape** — session
58 called cut "frequency-FLAT −3.2 dB, order 0, no corners", where this measures a gentle slope from
−0.79 @80 to −2.40 @254. Both differences are **positive at every band and largest at LF**, i.e.
common-mode, which is the signature of an error in the shared `flat` reference or in session 58's
`b0`/taper machinery rather than in the throws. This route is the more direct one (plain subtraction,
bleed bounded by measurement, convergence demonstrated on two quiet levels) and should be preferred,
but the disagreement is **not yet explained**.

**▶ NEXT, IN ORDER.**
* **(a0)** ⭐⭐ **FIRST — make (8b) reproducible; it was measured in an ad-hoc probe and is in NO
  committed tool, so it will otherwise be lost.** Write `analysis/attack_notch_probe.py`: full-
  resolution `A.transfer` on the three LEVEL-max drive-min captures, locate the 250–400 Hz minimum
  and its depth below the 200–270 Hz shoulder per ATTACK position, and report `h(f)` at full
  resolution so the smooth region and the notch window are separated **by measurement, not by the
  1/3-oct grid**. Needs a `--selftest` recovering a synthesised notch of known frequency/depth; the
  −36/−30/−18/−12 level sweep printed (−12 is where it migrates, which is the tell that the quiet
  rows are the trustworthy ones); and an explicit **NOTCH WINDOW** (~287–351 Hz) excluded BY NAME
  from the broadband read. **Re-derive (8b)'s numbers from the tool and correct them if they move.**
* **(a)** ⭐ then **propose the ATTACK topology against (6) AND (8b) together** — a broadband ±gain
  **plus** a null moving 316.4/328.1/334.0 Hz. Gate on the whole-band table in (6), excluding 320 Hz
  per (9), and on the matrix. **Do not propose a pure gain switch — (8b)(ii) rules it out.** Treat
  this as the same problem as **GAP #2** (`trebleLadderDampR`), not a separate one.
* **(b)** settle (11): the cut-shape disagreement with session 58, and the common-mode LF offset.
  A cheap test is the optional pair `level-1700_attack-{boost,cut}_base-od.wav` (drive **noon**,
  LEVEL max), which would re-measure session 58's own condition bleed-free.
* **(c)** unchanged: the post-clipper linear class is closed on measurement and on Bode; the
  remaining region is inside/before the clipper (`Clipper.h:309`).
* **(d)** settle `b0` between the LEVEL and DRIVE axes before quoting any absolute A3 magnitude.
* **(e)** unchanged behind that: `trebleLadderDampR` stays at 30k, the 4 `gain-n12` re-captures,
  A4 re-grade + GATE-9, the `OSValidationTest` decision, then B / C / D.
* **(f)** ⭐ **worth doing once, cheaply: fold `sweep_clean_-36` into the matrix properly.** (4)/(5)
  show a level the report has never read was the difference between "undecided" and "converged" at
  508/640 Hz. Adding it to `ALL_SWEEP_LEVELS` re-keys the result cache and changes every record's
  shape, so it is a deliberate re-baseline, not a drive-by edit.

---

### A3 step 17 — item 8b is now a committed, gated measurement and it reproduces exactly; three refinements it did not make (session 61)

Session 60's next-step **(a0)**. New `analysis/attack_notch_probe.py` + `analysis/reports/s61_attack_notch.json`.
**Nothing in `src/` or `tests/` changed**, and ctest was **RUN** at the pre-existing session-44
**16/17** (`OSValidationTest`, identical `amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`).

**WHY THIS RAN FIRST.** Step 16 item 8b is the finding that rules out proposing a plain gain switch
for ATTACK, and it couples ATTACK to GAP #2 — and it was measured in a throwaway script at the end of
a session, in no committed tool. Nothing else in the queue is worth doing while the constraint that
shapes it can evaporate.

**THE TOOL.** Full-resolution `A.transfer` (nperseg 8192 ⇒ **5.86 Hz bins**) on the three LEVEL-max /
drive-min captures, where the clean bleed is exactly zero by topology and the clipper is idle, so `h`
is a plain per-bin subtraction. Definitions are stated once and not re-derived downstream: `f0` is the
minimum of |H| in **250–400 Hz** (reported as the raw bin *and* a log-f parabolic refinement); `depth`
is (max |H| over **200–270 Hz**) minus that minimum, with the upper shoulder printed beside it because
the null sits between two peaks and one shoulder alone hides which side moved.

**(1) ⭐ THE AD-HOC NUMBERS SURVIVE — to the bin and to 0.03 dB.**

| at −30 dBFS | f0 bin | f0 refined | min dB | lo shoulder | up shoulder | **depth** | s60 item 8b |
|---|---|---|---|---|---|---|---|
| **cut** | 316.4 | 318.4 | −23.30 | −8.37 | −13.23 | **14.93** | 316.4 / 14.9 |
| **boost** | 328.1 | 327.7 | −30.34 | +2.36 | −2.95 | **32.70** | 328.1 / 32.7 |
| **flat** | 334.0 | 332.7 | −22.34 | −6.33 | −11.21 | **16.01** | 334.0 / 16.0 |

⇒ **ATTACK moves the null 17.6 Hz — 3.0× the bin — and boost's depth is 2.04× flat's.** A pure
broadband gain can do neither, so **the ATTACK network is two-path and interacts with the
notch-forming network; ATTACK and GAP #2 are ONE problem.** Item 8b(ii) stands as written.

**(2) ⚠ THE SELF-TEST FALSIFIED MY OWN GATE, WHICH IS WHY IT EXISTS.** Six synthesised notches of
known frequency and depth (two-pole notch, `Qz = Qp·10^(depth/20)` so the depth is exact in closed
form, `w0` prewarped so the bilinear maps the null to *exactly* f0 rather than near it) pushed through
the identical stimulus, transfer estimate and locator. Frequency recovers to **worst 4.22 Hz** (gate:
2 bins = 11.72 Hz). Depth does **not** behave as I assumed. My first gate declared a bin grid accurate
on a BROAD notch and biased on a sharp one, and gated the broad case at ±1.5 dB — it **FAILED at
−4.28 dB**, and the failure was correct:

* **(i) shoulder contamination** — a broad notch's own skirt reaches into the 200–270 Hz reference
  window, so the reference level is already attenuated and `shoulder − min` understates the depth.
  This is **definitional, not estimator error**, and the self-test's `shoulder` column shows it
  directly (~0 dB for the sharp cases, **−4.39 dB** at Qp 0.7).
* **(ii) bin smearing** — a 5.86 Hz-bin CSD estimate cannot reach the floor of a sharp deep notch: a
  true 33 dB notch at Qp 4 reads **28.71**.

Both mechanisms **understate**. So the gate was rebuilt on the properties the verdict actually uses:
depth **never over-states** (worst over-statement **+0.05 dB**, gate +0.20) and depth **RANKING**
survives a doubling (true 16.0/33.0, gap 17.0 → read 14.9/29.8, gap 14.9). Plus liveness (unfiltered
⇒ apparent depth 0.000 dB) and — the load-bearing one — **SEPARATION**: two notches synthesised
17.6 Hz apart read as **18.2 Hz apart**, which is exactly the size of the shift item 8b claims.
⭐ **General form of the lesson, and it is one this project keeps re-learning: gate the property the
conclusion rests on, not an absolute accuracy the statistic does not have.** "Boost roughly doubles
the depth" needs monotonicity and scale, not calibrated dB — and asserting the latter would have
buried a real definitional bias under a passing test.

**(3) ⭐ REFINEMENT — "identical to the bin at −36/−30/−18 dBFS" is true of FREQUENCY ONLY.**

| f0 Hz / depth dB | −36 | −30 | −18 | −12 | −6 |
|---|---|---|---|---|---|
| **cut** | 316.4 / 14.9 | 316.4 / 14.9 | 316.4 / 15.0 | 316.4 / 14.5 | 316.4 / 10.3 |
| **boost** | 328.1 / 33.0 | 328.1 / 32.7 | 328.1 / 27.9 | 328.1 / 20.7 | *316.4* / 17.6 |
| **flat** | 334.0 / 16.1 | 334.0 / 16.0 | 334.0 / 15.2 | *316.4* / 14.0 | *316.4* / 14.4 |

Frequency is identical to the bin across all three quiet rows at every position — item 8b's claim,
confirmed. **Depth is not: boost spreads 5.11 dB over those same rows** (cut 0.07, flat 0.82). The
mechanism is already on record — boost pushes ~8 dB more signal into the J201, which sits upstream of
DRIVE and never idles (step 15 item 3) — so compression reaches boost first. ⇒ **quote the quietest
row; treat depth as a bound and frequency as a value.** ⭐ And flat's null migrates **334 → 316.4 Hz**
at −12 dBFS, reproducing session 46's 334 → 299 Hz direction on an independent capture set — which is
the tell that the read has to come from the quiet end, not an average over levels.

**(4) ⭐ REFINEMENT — the nominal 287–351 Hz exclusion window UNDER-COVERS.** Located by measurement
(the contiguous region around the null where `|h − median|` exceeds the 0.204 dB floor, then
re-derived against a median that window no longer pollutes) it is **269.5–369.1 Hz on boost** and
**269.5–521.5 Hz on cut**. The medians move by 0.02 dB either way, so this is a refinement rather than
a reversal — but the broadband read now excludes the **measured** window, by name.

**(5) ⚠ REFINEMENT — "broadband flat" is a much stronger description of boost than of cut, and item 8b
did not distinguish them.** Over 80 Hz–1.6 kHz excluding the measured window: **boost +8.64 dB, spread
1.90 dB = 22 % of its own size**; **cut −2.39 dB, spread 2.05 dB = 86 %**, and cut needs a **252 Hz**
exclusion window against boost's 100 Hz. The 421.9 Hz check says the same thing from another
direction: that peak belongs to the shared path, so it must cancel in `h` — and it does on boost
(range **0.47 dB** over 360–500 Hz) but **not on cut** (**1.16 dB**, 5.7× the floor). ⇒ **cut carries
real structure over ~350–520 Hz.** ⭐ Worth connecting rather than filing separately: that is the same
region and the same direction as step 16 item 11's unexplained cut-shape disagreement with session 58
(which called cut frequency-flat with no corners, where step 16 measured a slope). **The two may be
one item**, and next-step (b) is the test for it.

**(6) A SMALL CORRECTION TO 8b(i) IN PASSING.** `flat |H|` varies **4.44 dB across the 1/3-octave band
at 403 Hz** (0.80 at 508, 1.11 at 640), so "403/508/640 are not sitting on sharp features" is too
strong for 403. What actually defends the 1/3-oct read is not the absence of a feature but that the
feature is **shared and therefore cancels** — which (5) shows holds on boost and only partly on cut.
Same distinction, better stated.

**WHAT IS NOW THE RECORD.** The ATTACK specification a topology proposal must meet:

* a **broadband gain** of **+8.64 dB (boost) / −2.39 dB (cut)**, flat to ±1 dB on boost across
  80 Hz–1.6 kHz, less flat on cut per (5);
* **AND a cancellation null at 316.4 / 328.1 / 334.0 Hz (cut / boost / flat)** with depth
  **≥ 14.9 / 32.7 / 16.0 dB** — lower bounds, two mechanisms, both understating.

⚠ Scope unchanged: ATTACK is `[ENG]`, so this is a specification, not a disagreement with a drawn
circuit; magnitude only, so a notch depth constrains how exactly two paths cancel but measures no
phase; and 320 Hz remains not a transfer value (step 16 item 9).

---

### A3 step 18 — the drawn ATTACK topology is REFUTED on the SIGN of the notch shift, and the specification splits into two jobs needing two switch poles (session 61)

Session 60's next-step **(a)**, first move: the cheap reachability screen before any proposal, in the
manner of sessions 49/56/57 — a refutation is worth more than a fit. New
`analysis/attack_notch_screen.py`. **Nothing in `src/` or `tests/` changed.**

**THE QUESTION.** Step 17 fixed the ATTACK specification as **two** requirements: a broadband
±gain (**+8.64 / −2.39 dB**) — already refuted as reachable by the drawn ladder in session 57, where
the shape statistic saturates at **+1.15 dB** against a required **+8.46** — and a **null that moves**
(cut 316.4 / boost 328.1 / flat 334.0 Hz, depth ≥ 14.9 / 32.7 / 16.0 dB). The second had never been
screened, and it is the half that rules out proposing a plain gain switch.

**(1) ⭐ THE HEADLINE STATISTIC IS A SIGN, NOT A DISTANCE.** Relative to flat, the pedal moves the
null **DOWN in BOTH throws** (cut −17.6 Hz, boost −5.9 Hz) and makes **boost 2.04× DEEPER**. A wrong
magnitude can be a wrong value; **a wrong sign cannot** — no scaling of any component changes it. So
the screen scores `f0_flat`, `depth_flat` and the four *differences*, with one parameter set covering
all three positions (it is one network with a switch in it — the constraint that killed session 56's
C8-alone screen and session 49's bridged-T Pareto).

**(2) ⛔⛔ AND THE DRAWN NETWORK MOVES THE TWO THROWS IN OPPOSITE DIRECTIONS.** At the schematic
`RdampC5 = 0` the notch sits at **320.3 Hz in ALL THREE positions** — spread **0.0 Hz** where the
pedal's is 17.6 — and C8 swept over **four decades** (22 pF → 2.2 µF) never fixes the sign: cut always
moves **UP** (to the 400 Hz window edge), boost **DOWN**. The mechanism is structural: boost puts C8
in a **bridging** path (M↔P) and cut puts it in a **shunt to ground** at P, so the two throws add
capacitance in different places and generically move a null opposite ways.

**(3) ⭐⭐ A SIGN CENSUS MAKES THAT INDEPENDENT OF THE OPTIMISER — and localises it to ONE
requirement.** 6000 random parameter sets over ±2 decades in all **12** ladder elements, classified by
the three signs, counting only draws where the switch moves the null by more than one bin (782 of
them):

| (cut DOWN, boost DOWN, boost DEEPER) | count | share |
|---|---|---|
| (0, 1, 0) | 367 | 46.9 % |
| (0, 0, 1) | 339 | 43.4 % |
| (0, 1, 1) | 42 | 5.4 % |
| (0, 0, 0) | 34 | 4.3 % |

**0 of 782 match the pedal.** Per sign: *boost moves down* occurs in 52.3 % of draws, *boost is
deeper* in 48.7 % — but **"cut moves DOWN" occurs in 0.0 %.** ⭐ A joint count of zero could be three
possible signs that never co-occur; a **per-sign** count of zero is structural. **In this topology the
cut throw can only move the null upward.** No optimiser is involved in that statement.

**(4) THE FREE SEARCH AGREES AND SATURATES.** All 12 elements freed, DE with a pathology guard: cost
**6.85 / 6.78 / 6.78** at ±1 / ±2 / ±3 decades — it moves **0.08 across two orders of magnitude of box
widening**, at ~7× the point where every residual sits at its own resolution. ⭐ And it **switches the
throws off** rather than trading, driving both shifts to **0.00 Hz** and both depth deltas to
**0.00 dB** — session 57's "the objective cannot reach this direction" signature exactly. Gates ran
first: liveness (C8 = 0 ⇒ spread **0.000e+00** in both f0 and depth) and a search gate recovering
targets the family generated itself to cost **0.002 / 0.065**, i.e. a **~100× separation** from the
6.78 residual. ⚠ The gate had to be tightened mid-session: its first version accepted targets whose
null sat **on the 250–400 Hz search edge** (both shifts came out at exactly −150 Hz = the window
width) and recovered them to 0.00000 — a railed target is recovered easily for the wrong reason, the
same "an optimum on its own boundary is uninformative" rule as sessions 47/51.

**(5) ⭐ THE DECOMPOSITION IS CLEAN, AND IT IS THE USEFUL PART.** The free search reproduces the
**flat** position essentially exactly (f0 **333.9 vs 333.98 Hz**, depth **16.04 vs 16.01 dB**) — so the
whole residual is the two throws' differentials. **The notch-forming network is fine; the switch's
coupling into it is what is wrong.**

**(6) ⭐⭐ SO WHAT *CAN* MAKE IT — and the answer says the switch needs more than one pole.**
`RdampC5` (GAP #2's own constant, the damping in the C5 ladder leg) moves f0 **down** and **deepens**
the null together, which is the pedal's boost direction. Tested:

* **(a) `RdampC5` alone — 1 dof against 2 targets.** It nails **DEPTH at all three positions to
  +0.1 / −0.1 / +0.0 dB** (Rd ≈ 6.06k / 624 Ω / 5.47k) ⭐ i.e. **the half of the spec that looked
  exotic — a 2× depth change — is just a damping change.** ⛔ But every position's f0 lands at
  **319–320 Hz** where the pedal spans 316.4–334.0, so one element cannot do both jobs.
* **(b) `RdampC5` + `C5` switched together — 2 dof, 2 targets.** Hits all three (f0, depth) pairs to
  cost 0.34 / 0.47 / 0.41 with sane, structured values: **Rd 6117 / 437 / 6117 Ω, C5 22.6 / 20.4 /
  19.3 nF** (cut/boost/flat — note cut and flat share one Rd). ⚠ **This fit is not evidence:** 2 dof
  against 2 targets hits them by construction.
* **(c) ⭐ THE DECIDING TEST — the same setting's broadband gain.** `h boost` = **−0.14 / −0.34 /
  −0.03 / +0.98 / +2.60 dB** at 100/200/400/800/1600 Hz against a required **+8.64**; `h cut` =
  −1.00 / −1.72 / +1.69 / −0.07 / −0.77 against **−2.39**. ⛔ **Not close, and in the wrong place** —
  the notch leg supplies ~0 dB of broadband gain. That is session 57's refutation arriving from the
  other direction.

**(7) ⇒ THE CONCLUSION, AND IT IS A DIRECTION FOR (a)'s PROPOSAL RATHER THAN A DEAD END.** The
specification splits into **two jobs that no single element does**: the **notch triple is reachable**,
but only by switching an element **inside the notch-forming ladder leg**; the **broadband ±gain is not
reachable there at all**. ⇒ **stop looking for one element.** A 3-position switch with **more than one
pole** — one section in the notch leg, one supplying broadband gain — is the shape of answer the
measurement points at. ⭐ **There is a direct precedent in this project:** A2c-3 resolved the
mid-frequency selector exactly this way, by recognising it as **2-POLE** (switching the across-lug cap
together with the series cap) after single-element fits could match range *or* centre but never both,
for the same structural reason (one element could not set two independent properties).

⚠ Scope unchanged: **ATTACK is `[ENG]`** — the 3-way switch is not on our schematic at all, so what is
refuted is the **assumed** topology, which nothing corroborated. Magnitude only. And `RdampC5` is
shared with **GAP #2**, so whatever replaces this network must produce the notch *and* move it — one
problem, not two.

---

### A3 step 19 — the multi-pole ATTACK topology is PROPOSED, and it MEETS the whole record: gain, depth and frequency come from three provably non-interacting groups (session 62)

**Analysis + tooling only. NOTHING in `src/` or `tests/` changed**, and ctest was **RUN** (not
assumed) at the pre-existing session-44 **16/17** — `OSValidationTest`, identical
`amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`. New `analysis/attack_multipole_screen.py`, new
`analysis/attack_tap_screen.py`, one additive change to `analysis/attack_notch_probe.py`. New
reports `analysis/reports/s62_multipole.json`, `analysis/reports/s62_tap.json`. This is session 61's
next-step (a).

#### 0. The measurement is now machine-readable, and it is a strict superset

`attack_notch_probe.py` wrote only a *summary* of `h` (median, spread, window). A topology proposal
has to be scored on the **shape** of `h` across the band, which cannot be rebuilt from a median —
and copying session 60's 1/3-oct table into the next tool by hand is the session-33 lost-sign trap.
The probe now also writes the **full-resolution `h(f)` curve**, 40–2000 Hz at its own 5.86 Hz bins.

⭐ Regenerated and proven a **strict superset** of the session-61 file: **all 184 shared values
bit-identical, worst |Δ| 0.000e+00**, four new keys, none lost. So no session-61 number moves.

#### 1. ⭐⭐ THE PROPOSAL, AND IT MEETS THE RECORD

**ATTACK = a 3-throw switch with TWO POLES**, one per half of the specification:

* **Pole A — a MOVING TAP on the R7/R8 divider (the broadband ±gain).** The drawn R8 is split and
  the switch selects which node the coupling cap C7 hangs off:
  `G –R7– M –Ra– T1 –Rb– T2 –Rc– T3 –R11– GND`, with **boost → T1, flat → T2, cut → T3**.
* **Pole B — the C5 ladder leg (the notch).** The leg's damping `Rd` **and** `C5` switch per throw.

Scored against the whole record, with each half tested on targets the other never saw:

| | model | pedal | err |
|---|---|---|---|
| **h median boost** | **+8.53 dB** | +8.65 | 0.12 |
| **h median cut** | **−2.31 dB** | −2.39 | 0.08 |
| **f0 cut / boost / flat** | **316.3 / 328.1 / 333.9 Hz** | 316.4 / 328.1 / 334.0 | ≤ **0.1 Hz** |
| **depth cut / boost / flat** | **14.75 / 32.69 / 15.87 dB** | 14.93 / 32.70 / 16.01 | ≤ **0.18 dB** |

Values: **Rd = 6.04k / 478 Ω / 6.14k** and **C5 = 22.4 / 20.8 / 19.7 nF** (cut/boost/flat), on a tap
divider **Ra 470k (pinned to the drawn R8) / Rb 506k / Rc 78.5k / R11 212k**.

⭐ **The throw ORDER is not fitted.** `g(boost) > 0 > g(cut)` is measured and a resistive tap can
only attenuate, so boost must be the highest tap. That is the one structural commitment, and it is
forced by the data rather than chosen.

⭐ **Cut and flat share their damping to within 2 % (6.04k vs 6.14k)** — session 61 item (10b) noticed
that hint and it survives a completely different fit. Read physically: the switch **shorts the
damping resistor in BOOST only**.

#### 2. ⭐⭐ WHY THIS IS A PROPOSAL AND NOT A FIT — the three requirements are carried by three
#### provably non-interacting groups

Perturbing every element ±20 % about the fitted point separates all twelve cleanly, with no overlap:

| group | d f0 | d depth | d h median | owns |
|---|---|---|---|---|
| tap divider `Ra Rb Rc R11` | **0.01–0.02 Hz** | 0.01–0.05 dB | 0.23–1.22 dB | the broadband gain |
| damping `Rd` | **0.17 Hz** | **2.53 dB** | **0.00 dB** | the depth |
| ladder RC `R7 R12 R14 C5 C6 C9` | **14–33 Hz** | 1.4–5.0 dB | **0.00 dB** | the frequency |

⇒ the notch leg is **exactly broadband-neutral (0.00 dB)** and the tap is **exactly notch-neutral
(0.01 Hz)**. The two-pole decomposition is therefore not an extra degree of freedom bolted on to
make a fit work — it is **forced**, because no element in this network moves both.

Mechanism, and it is simple: the tap's load is `C7 + R13 ≈ 1 MΩ` against a few hundred kΩ of rail,
far too light to disturb the R7-vs-ladder cancellation up at node M.

#### 3. ⚠ THE TOOL'S OWN HYPOTHESIS WAS REFUTED BY ITS OWN GATE, AND THE HEADER WAS CORRECTED

`attack_tap_screen.py` was written to ask whether **ONE** pole could do both jobs — a moving tap
changes gain *and* re-loads the rail, so it might move the null too. It does not: the tap moves `h`
by 3.80 dB and f0 by **0.00 Hz**, and a fitted 1-pole tap leaves the null at 318.8 Hz in all three
throws (**spread 0.04 Hz** against the pedal's 17.58). So **session 61's "more than one pole" is
CONFIRMED, not superseded.** The docstring's original paragraph asserting the opposite was rewritten
rather than left to print above a table contradicting it (the session-34 narrated-verdict trap).

#### 4. ⭐ AND THE f0 SHORTFALL WAS ARBITRATION, NOT STRUCTURE — settled by separating the fits

The *joint* fit (notch + 216 `h` bins in one objective) reached only **1.38 Hz** of f0 spread with
`Rd` switched and **8.52 Hz** with `Rd`+`C5`, against the required 17.58 — which reads like a
structural limit. It is not. Holding the tap divider (it is broadband-only, so it cannot help here)
and aiming the notch section at the **six notch numbers alone** reaches **notch cost 0.000** and
17.6 Hz of spread, and the broadband then **re-reads as a CHECK at 0.73 dB rms** with the medians in
§1. The joint objective was simply trading 6 notch residuals against 216 broadband ones.

⭐ **The general point: when a joint objective under-delivers on one requirement, separate the fits
before calling it unreachable — if the halves are carried by non-interacting groups (§2), scoring
them jointly buys nothing and costs arbitration.**

⛔ **AND THE THIRD ROW IS THE CONTROL THAT MAKES THE OTHERS READABLE.** Adding `R12` to the switched
set also reaches notch cost **0.000** — and its broadband check **explodes to 14.52 dB rms with
h boost +28.84 dB**. Nine free values hit six notch numbers trivially, by a network that is
broadband nonsense. The broadband re-read is doing real work; the notch cost alone is not evidence.

#### 5. THE ELEMENT CENSUS THAT PRECEDED IT (`attack_multipole_screen.py`)

Session 61 tried exactly one notch-leg candidate and flagged that 2 values against 2 targets per
position hit them by construction. This screens **156 families** — every 1- and 2-element subset of
the 12 ladder elements, × {C8 rerouting kept, removed} — fitting per-position values plus a shared
free `RdampC5`, and scoring the thing the construction cannot buy: with pole 2 a flat scalar, the
part of `h` that pole 1 leaves must already be FLAT, so only the **shape** is scored and the implied
pole-2 gain `g` is read out as a prediction.

⚠ **The NULL CONTROL is what makes the numbers readable, and it was computed, not assumed:** a pole 1
that does nothing broadband scores **bb 2.34**. The best family reaches **1.49** and the best joint
**1.34** — a real improvement, but nothing approaches the 1.0 floor, and the top 18 families span
only 1.49–1.72. ⇒ **no element-value family is distinctly better than any other**, which is what
sent the search to a topology (a changed CONNECTION) rather than another value.

#### 6. GATES — all run first, and two of them fired

* **SOLVER (new).** Both screens use a private vectorised 6-/8-node solver so DE is affordable. A
  fast copy of a shared oracle is a silent-divergence trap, so it is *proved* equal, not assumed:
  the multipole solver matches `eq_reference.treble_attack_tf` at **0.000e+00 dB/deg** over random
  parameter sets; the tap network's exact degenerate case (Ra = R8, Rb+Rc+R11 = R11, tap = T1)
  matches at **1.4e-14 dB**, and the short-based collapse is shown to BE a short by scaling it
  (1 mΩ → 4.9e-7 dB, 1 Ω → 3.4e-6, 1 kΩ → 3.4e-3).
* ⚠ **That solver gate FAILED TWICE FIRST, and both failures were the gate, not the code.** (a)
  Collapsing `Ra` and `Rb` leaves T1 = T2 = **M** and only T3 on P — two taps on the wrong node,
  reported as a 6 dB "failure" of a correct solver. (b) Using 1e-12 Ω as the short makes the
  conductance 1e12 against a 2e-6 rail and the 8×8 solve loses every digit; **shrinking** the short
  made the error *worse* (4.9e-7 → 7.0e-5 dB), which is the tell. **A degenerate case has to be
  stated exactly, and a numerical short is only as good as its conditioning.**
* **LIVENESS.** A switch moving nothing gives f0/depth/|h| spread **9.7e-08**; the drawn C8 moves f0
  by 3.10 Hz so the probe demonstrably sees a switch.
  ⚠ The first draft **gated** on the tap moving f0 — which would have converted §3's finding into a
  tool failure. It now reports that number and gates only on the probe seeing the switch at all.
* **SEARCH.** Targets the family definitionally can make, structured but not railed (a null on the
  250–400 Hz search edge is recovered for the wrong reason): recovered to **0.00002–0.00135**.
* **PATHOLOGY.** Dead/rippling responses rejected (session 57's +88 dB reachability artefact).

#### 7. ⚠ WHAT IS AND IS NOT CLAIMED

* **ATTACK is `[ENG]`** — the 3-way switch is not on our schematic at all. This proposes a topology;
  it does not disagree with a drawn one, and nothing corroborates it independently.
* **Only RATIOS are identified.** `h` is a ratio between switch positions, so any element common to
  all three throws cancels out of it **by construction**. `Ra` sits above all three taps and duly
  parked on whichever bound it started nearest (100 Ω and 10 MΩ scored the same) until it was pinned
  to the drawn R8. The same applies to every shared element: a 12-value "wide" fit moved the joint
  cost 4.45 → 4.40 while driving C9 to 288 nF — the classic unidentified-direction signature.
* **The proposal moves a schematic-verified value.** It wants the P-to-ground resistance to be
  ~797 kΩ split into three, against the drawn R11 = 470 kΩ. Since the switch itself is `[ENG]` the
  surrounding rail is a proposal too, but this should be stated, not buried.
* **Magnitude only**, and notch depths are **lower bounds** (probe gate 1(b), two understating
  mechanisms), so the depth *ranking* carries the claim, not the calibrated dB.
* **`C5` switching 19.7 → 22.4 nF is a ±7 % move**, i.e. inside cap tolerance as a *value*, but it is
  a real requirement — it is what supplies the 17.6 Hz. Realise it as a small **parallel trim cap**
  selected by the same pole (flat 19.7n base, +1.1n boost, +2.7n cut), not as three graded caps.
* **This is a LINEAR, PRE-clipper screen** at the drive-min/LEVEL-max operating point where the
  measurement was taken. It says nothing about behaviour at drive noon/max, which only a real render
  through the full chain tests.

#### 8. ⭐ GAP #2 FALLS OUT OF THE SAME ANSWER

`trebleLadderDampR` = 30k destroys the notch (session 46). The proposal puts the flat position's
damping at **6.14 kΩ** and boost's at **478 Ω** — i.e. **`trebleLadderDampR` stops being a single
constant and becomes the switched pole B**. ATTACK and GAP #2 are one network and this answers both.

#### 9. ▶ WHAT THIS SETS UP

The proposal is now specific enough to build, and what it needs is a **topology** change to
`TrebleAttack`, not the generic value-plumbing that session 50's open item described: a split rail
with a switched output tap, plus per-position `Rd` and `C5`. `Rd=0`/collapsed taps must remain
bit-identical to the shipped stage, and the plumbing must be verified BOTH ways (session 37 item 12).

---

### A3 step 20 — the two-pole ATTACK topology is BUILT, and it meets the NOTCH requirement exactly through the real chain; the broadband half is close but its SHAPE is not (session 63)

**This is the first session since 44 to change `src/`.** Session 62's next-step (a). New
`analysis/attack_topology_goldens.py`, `analysis/attack_render_gate.py`, `analysis/shape_gate.py`;
`src/dsp/TrebleAttack.h` gains the topology, `FitParams.h`/`PedalChain.h` the plumbing,
`tests/TrebleAttackTest.cpp` two new tests. **ctest 16/17** — the one failure is the pre-existing
session-44 `OSValidationTest` at *identical* numbers (`amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`),
unaffected by this work. ⚠ **Nothing is SHIPPED as a default**: every new value defaults to the
drawn network, and the 63-capture matrix is the arbiter (as it was for `btC17` and `clipC15`).

#### 1. ⭐⭐ THE BUILD NEEDS NO NEW NODES — the series collapse, and it is exact

`attack_tap_screen.py` solves the split rail as an 8-node network. The C++ stage does not have to:
**only the SELECTED tap carries a load** (C7, plus C8 when in circuit), so T1/T2/T3 are otherwise
bare interior points of one series chain, and series resistors with no loaded intermediate node
combine EXACTLY. Per throw the four-resistor rail collapses to the drawn two-resistor rail:

| throw | tap | Rtop (M→P) | Rbot (P→GND) |
|---|---|---|---|
| boost | T1 | `Ra` | `Rb + Rc + R11` |
| flat | T2 | `Ra + Rb` | `Rc + R11` |
| cut | T3 | `Ra + Rb + Rc` | `R11` |

So `N` stays at **7**, there are still three matrix inversions, and — the point — the default
(`Ra = R8`, `Rb = Rc = 0`, `R11 = R11`) stamps **bit-identical values into the same 7×7** as the
shipped stage. ⭐ **And `Rb`/`Rc` are only ever SUMMED, never inverted, so zero is exact.** That is
the thing the screen tool could not do: its 8-node solve needed a numerical short, and session 62
found that *shrinking* the short made the error WORSE (1e-12 Ω puts a 1e12 conductance against a
2e-6 rail). The C++ path has no such term at all.

⭐ **The collapse is GATED against an independent implementation, not against its own derivation.**
`attack_topology_goldens.py` scores it vs `attack_tap_screen.tf_tap`'s uncollapsed 8-node solve **at
the SPLIT point** (`Rb` = 506k, `Rc` = 78.5k, both large): worst **2.1e-14 dB** across all three
throws. ⚠ The tool also prints the same check at the DEFAULT point (**3.6e-07 dB**, short-limited)
and labels it a CONTROL — *that* case passes even for a wrong collapse, since every throw is then
the drawn network, so it is not the gate.

#### 2. ✅ PLUMBING VERIFIED BOTH WAYS, INCLUDING AGAINST THE PRE-CHANGE BINARY

Session 37 item 12's trap (that binary is built by a hand-written `c++` command, not CMake) plus
session 45 item 7a's. All checks on real renders of `attack-boost_base-od.wav`:

* default vs **explicit-nominal** `--fit` of all 9 new keys → **bit-identical**;
* default vs the proposal, vs **pole A alone**, vs **pole B alone**, vs `trebleC8=0` → all **differ**
  (so each pole is independently live, not just the pair);
* ⭐ **default vs a binary built from `git show HEAD:` of all four changed files → BIT-IDENTICAL** in
  all three ATTACK throws AND at drive noon / LEVEL noon where the clipper is working. The topology
  change is a true no-op at its defaults, not a numerically-close one.

⚠ **`kC8` had to become fittable** (`trebleC8`, default 220 pF) because session 62 screened the
proposal with **C8 REMOVED**; rendering it with 220 pF still in is not the thing that was screened.
Note where C8 attaches when the tap moves: at the **selected tap**, because in the drawn circuit
C8's top plate and C7 share node P. (`attack_tap_screen`'s optional `--c8` mode instead spans
M↔T3, the whole rail — a different and less faithful choice. The proposal ran at C8 = 0, so the two
never had to be reconciled; do not "fix" one to match the other without deciding which is the claim.)

#### 3. ⭐⭐ THE NOTCH REQUIREMENT IS MET **TO THE BIN**, THROUGH THE FULL CHAIN

`attack_render_gate.py` renders the real `PedalChain` at the measurement's own operating point
(drive MIN / LEVEL MAX / BLEND MAX) and scores it exactly as `attack_notch_probe.py` scores the
captures — plain subtraction of full-resolution transfers, no solve, no taper, no bleed model.

| variant | f0 cut / boost / flat (Hz) | depth (dB) | f0 spread |
|---|---|---|---|
| **PEDAL** | **316.4 / 328.1 / 334.0** | 14.93 / 32.70 / 16.01 | **17.58 Hz** |
| DRAWN (shipped defaults) | 398.4 / 398.4 / 398.4 | 9.02 / 8.38 / 8.95 | **0.00 Hz** |
| **TWO-POLE PROPOSAL** | **316.4 / 328.1 / 334.0** | 18.51 / 36.62 / 20.31 | **17.58 Hz** |

⭐ **Identical to the pedal at every throw, on the measurement's own 5.86 Hz bin grid**, and the
DRAWN default is *dead* — one frequency in all three throws, spread 0.00 Hz, which is the pattern
session 61 refuted on a sign (0 of 782 random draws). Depths run **3.6–4.3 dB DEEPER** than the
pedal, which is allowed rather than an error: probe gate 1(b) established that both bias mechanisms
(shoulder contamination, bin smearing) **understate**, so depth is a LOWER BOUND and the RANKING
carries the claim — model boost/others = **1.9×**, pedal **2.1×**.

⚠ **`f_bin`, NOT the parabola-refined `f_ref`.** The record (sessions 60–62) is quoted on the bin
grid and those three values are exactly bins 54/56/57. A first draft of the gate used `f_ref` and
reported the pedal as 318.4/327.7/332.7 — shifting every comparison by 1–2 Hz against a record
measured the other way, i.e. the session-33 transcription trap in a new guise.

#### 4. ⭐ THE BROADBAND HALF IS CLOSE, AND ITS SHORTFALL IS COMPRESSION — read from the quiet end

At −30 dBFS the proposal's boost median is +7.43 dB against the pedal's +8.63, which reads like a
1.2 dB network shortfall. It is not. Session 61 item 3's lesson (quote the QUIETEST row) settles it:

| variant | throw | −36 dBFS | −30 dBFS | −18 dBFS | trend |
|---|---|---|---|---|---|
| PEDAL | boost | **+8.91** | +8.63 | +4.49 | +4.43 dB |
| PEDAL | cut | −2.38 | −2.38 | −2.02 | −0.36 |
| DRAWN | boost | +0.87 | +0.70 | +0.09 | +0.78 |
| **PROPOSAL** | boost | **+8.28** | +7.43 | +1.97 | **+6.31** |
| **PROPOSAL** | cut | **−2.29** | −2.24 | −1.16 | −1.13 |

⇒ at the quiet end the requirement is **essentially met: +8.28 vs +8.91 (0.63 dB) and −2.29 vs
−2.38 (0.09 dB)**. ⚠ **But the model compresses HARDER than the pedal** (+6.31 dB of level trend vs
+4.43), and the DRAWN default shows almost none (+0.78) *because it has no boost to compress* —
which corroborates the mechanism. The tap raises what IC2_A sees, and `RailClamp` has been enabled
since session 21. **Recorded, not resolved:** the pedal's boost compresses too, so this is a ~1.9 dB
excess, not a new phenomenon — and it is A3/A5 headroom territory, not ATTACK's.

#### 5. ⛔ WHAT IS **NOT** MET: THE SHAPE. Two residuals the (f0, depth) table cannot express

⭐ **This is the session's methodological point, and it came from the USER: score the CURVE, not
elements in isolation.** Both findings below are invisible in a median-and-depth read.

**(a) The broadband SLOPE has the wrong sign, on both throws.** Over 80 Hz–1.6 kHz ex-window:

| throw | model median | pedal | model slope | pedal slope | model spread | pedal |
|---|---|---|---|---|---|---|
| boost | +7.43 | +8.63 | **−1.39 dB/dec** | **+1.23** | 2.78 | 1.90 |
| cut | −2.24 | −2.38 | **+0.10** | **−1.38** | **5.17** | 2.62 |

Residual rms **1.27 dB (boost) / 0.83 (cut)** against the 0.204 dB floor — a **6× improvement** on
the drawn network's 7.74 / 2.08, but not a match. Cut's spread is **2× the pedal's**, i.e. cut
carries structure the tap does not make (the same region session 60 item 11 and session 61 item 5
both flagged as an unexplained cut-shape disagreement — plausibly one item, still open).

**(b) ⭐ THE NULLS ARE ~2× TOO BROAD — and the Q *ordering* is right.** Half-depth bandwidth:

| variant | cut | boost | flat |
|---|---|---|---|
| PEDAL | 70.3 | **23.4** | 64.5 |
| DRAWN | 134.8 | 134.8 | 134.8 |
| **PROPOSAL** | 146.5 | **52.7** | 134.8 |

⇒ **pole B does its job structurally** — boost's null is the sharp one, ratio **2.6×** against the
pedal's **2.8×**, where the drawn network has no throw dependence at all — but **every** width is
~2.1× too broad. A *uniform* factor across all three throws points at a SHARED element (the ladder
RC / the shunts R12/R14), not at the switch. This is the same "centre right, range right, WIDTH
wrong" residual A2c-2 found in the mid stage.

⚠ **AND THE WIDTH STATISTIC HAD TO BE FIXED MID-SESSION.** The first version measured width at a
fixed −6 dB below the shoulder, which is **confounded with depth** — a deeper null crosses any fixed
contour further out, and this model IS deeper, so it reported ~1.6× "too wide" partly on its own
extra depth. Referring the contour to each null's OWN half-depth removes it. Same rule as (c) below
and as session 62's ratio-denominator guard: **normalise to something the feature under test does
not itself move.**

**(c) ⚠ AND THE PLOT'S FIRST NORMALISATION MANUFACTURED A THIRD "FINDING" THAT WAS NOT THERE.** The
null overlay was normalised to the *median over 200–500 Hz*, a window that INCLUDES the null — so a
model with a deeper null pulls that median down and paints its shoulders several dB high. That read
as a real "wrong shoulder slope" until it was checked. Re-normalised to the lower shoulder (the
200–270 Hz max, `locate_notch`'s own depth reference) both sets start at 0 as they must, and the
genuine difference is visible instead: the model's approach to the null has a much broader low-side
skirt, which is (b).

#### 6. GATES — and TWO OF MINE WERE WRONG, both in ways worth keeping

* **LIVENESS** drawn vs proposal, worst |Δh| = **10.14 dB**. OK.
* **BLEED** ⚠ **the first version tested nothing.** It rendered BLEND = 0 and asserted the result was
  far below BLEND = max, "proving the OD path is what is measured". But **BLEND = 0 is not silence —
  it is 100 % CLEAN**, so at drive MIN (where the OD path is quiet) the two sit within a few dB and
  it reported −5.7 dB / CHECK for a perfectly fine model. It measured the DRIVE knob. Replaced with
  the claim that actually matters, checked against `LevelBlendTest`'s own oracle: at LEVEL = 1 /
  BLEND = 1 the clean coefficient is **0.000e+00** and the OD coefficient **1.000000**, so `h` IS
  the ATTACK ratio. (And a common bleed could only *shrink* |h|, so every `h` is also a lower bound.)
* **CONVERGED** ⚠ **and its threshold was wrong too.** It gated |h(−36) − h(−30)| against the
  0.204 dB difference floor and reported CHECK — **but the PEDAL fails that same threshold** (0.469 dB
  at boost). Two reasons: boost genuinely spreads across level (item 4), and a WORST-over-249-bins
  statistic is noise-dominated, which is why session 60's 1/3-oct read of the same thing was 0.065 dB.
  Re-gated on the **rms**, against the **pedal's own value** as the yardstick: pedal boost 0.254 /
  cut 0.028; model boost **0.832 (CHECK)** / cut 0.044. Boost's excess is item 4's compression.
* ⭐ **GENERAL: gate against what the DEVICE does, not against an absolute floor the device itself
  cannot meet.** Session 61 learned this for depth; both failures above are the same lesson on a new
  quantity, found only because the pedal row was printed beside the model row.

#### 7. ⭐⭐ NEW GENERAL INSTRUMENT: `analysis/shape_gate.py` — FR and THD decomposed as CURVES

The user's session-63 point, generalised past ATTACK: **a single scalar cannot distinguish "the whole
curve is 1 dB high" from "it tilts 2 dB" from "there is a 20 dB notch at 320 Hz", and those three
have different causes and different fixes.** For each row the residual is projected onto an
ORTHONORMAL basis in log f, so the four terms partition the mean square **exactly**:

    rms² = LEVEL² + TILT² + CURVATURE² + LOCAL²

`LOCAL` — what is left after the smooth shape is removed — is the term no previous gate had, and it
is where a notch lives. On the frozen 63-capture baseline:

| group | rows | rms(q) | level | tilt | curv | **LOCAL** | interior | rms(a) | worst LOCAL |
|---|---|---|---|---|---|---|---|---|---|
| OD ex `gain-n12` | 252 | 2.611 | 0.846 | 0.897 | 0.995 | **2.075** | 2.023 | 1.903 | −20.8 dB @ 12.9 k |
| OD `gain-n12` [bad] | 16 | 5.218 | 2.670 | 2.865 | 1.083 | 3.274 | 3.100 | 4.991 | +21.4 @ 6451 |
| CLEAN | 120 | 0.487 | 0.199 | 0.312 | 0.155 | 0.276 | 0.281 | 0.427 | +1.9 @ 4064 |

⭐⭐ **THE HEADLINE: `LOCAL` IS THE DOMINANT PART OF THE OD RESIDUAL — 2.075 of 2.611, i.e. ~63 % of
the mean square is NARROW STRUCTURE, not level, tilt or curvature.** Every A3 instrument to date has
fitted smooth broadband shapes (bathtubs, corners, tapers, a min-phase correction network) against a
residual whose largest single component is narrow features. **And the CLEAN path is the opposite** —
`LOCAL` 0.276 against a 0.487 total, i.e. smooth-error-dominated, exactly as a well-fitted linear
path should be. The contrast is what makes the OD number readable.

⚠ **AND THE EDGE CONTROL IS WHAT MAKES IT A FINDING.** A least-squares polynomial has its worst
leverage at the ENDS of the fit range, and the first run put every worst-LOCAL band at 25–32 Hz or
4–13 kHz — exactly what that artefact looks like. Dropping the two outermost bands each side moves
`LOCAL` only **2.075 → 2.023**, so it survives. Without that control the headline would have been
polynomial edge behaviour.

⚠ **`rms(q)` IS NOT `matrix_grade`'s NUMBER, and a first draft of the docstring claimed it was.**
`matrix_grade` aggregates by ARITHMETIC mean of per-row band-RMS; the decomposition needs the
QUADRATIC mean for the terms to partition the group total too. They differ systematically
(2.611 vs 1.903 for OD ex `gain-n12`), so reading one as a regression against the other is pure
arithmetic. Both are now printed — `rms(a)` reproduces `matrix_grade` exactly (1.903 / 4.991 / 0.427
/ 1.573) — and `matrix_grade` remains the headline grade.

**THD is decomposed the same way but in dB**, because it is a RATIO: in percent a multiplicative
error at high THD swamps the same error at low THD and the "shape" is just wherever the pedal happens
to distort most. OD ex `gain-n12`: **rms(q) 9.986 = level 6.736 / tilt 4.286 / curv 3.372 / LOCAL
4.961**, i.e. THD error is **level-dominated** — the model's distortion AMOUNT is the biggest term —
and its **worst LOCAL band is 320 Hz at −28.24 dB**, the notch band, showing up independently in THD
as well as in FR.

#### 8. ⭐⭐ AND THD CORROBORATES THE WHOLE ATTACK FINDING FROM A COMPLETELY DIFFERENT DIRECTION

`shape_gate`'s THD-vs-level table ranks rows by their compression curve, and **every one of the worst
rows is an `attack-boost` row, with the model's THD 9–14 dB LOW**:

    drive-0700_attack-boost_blend-1430   -14.05 / -13.38 / -13.99 dB  (at -18 / -12 / -6 dBFS)
    attack-boost_blend-1430              -13.01 / -11.34 /  -9.46
    drive-0700_attack-boost              -12.07 / -11.98 / -12.50
    attack-boost                         -11.59 / -10.44 /  -9.20

That is **exactly what the DRAWN topology predicts**: in the shipped model ATTACK boost delivers
~0 dB instead of +8.6 dB, so the clipper never sees the extra drive and cannot make the pedal's
harmonics. ⭐ **So the ATTACK gap was measurable in THD all along, on rows that have been in the
matrix since the first capture session — nothing new had to be captured, only a curve had to be
looked at.** It also yields a falsifiable prediction for the topology: those rows must improve.


#### 9. ⛔⛔ AND THE MATRIX — THE ARBITER — DOES **NOT** SUPPORT SHIPPING IT. NOTHING SHIPPED.

The full 63-capture render landed at session end (`analysis/reports/s63_twopole.json`).

    subset            shipped        twopole
    OD ex gain-n12    1.903  (252)   2.218  (268)     tilt 0.95 -> 2.19
    CLEAN             0.427  (120)   0.427  (120)     bit-identical (OD-path change)
    ALL               1.573  (388)   1.791  (404)
    row movement over the 388 SHARED rows: 33 better >0.5 dB, 32 worse, 136 bit-identical
    biggest improvement -3.35 dB (level-1700_base-od, drv_-6)
    worst regression    +3.92 dB (level-1700_gain-n12_base-od, drv_-6)

⚠⚠ **DO NOT READ THOSE AGGREGATE ROWS AS A COMPARISON — THE MEMBERSHIP MOVED.** twopole has **284 OD
rows against shipped's 268**, because the tap raises levels enough that 16 previously-SILENT rows
(`max < -60 dB`, `matrix_grade`'s own exclusion) come into range. An rms over differently-populated
row sets is not a ranking — the session-49 item-7 trap, and this is its fifth appearance in this
project. **The valid comparison is the 388 shared rows**, and on those the verdict is a genuine wash
on counts (33 vs 32) with the aggregate moving the wrong way.

⭐ **AND THE DECOMPOSITION SAYS *WHY*, WHICH THE TOTAL CANNOT** (`shape_gate --vs`, 388 shared rows;
note the tool's A column is the positional report and B is `--vs`, so read the signs carefully):

| term | twopole | shipped | twopole − shipped |
|---|---|---|---|
| level | 1.031 | 0.878 | **+0.153 WORSE** |
| tilt | 0.885 | 0.944 | −0.059 better |
| curv | 1.008 | 0.836 | **+0.172 WORSE** |
| **local** | **1.778** | **1.806** | **−0.028 better** |
| rms | 2.454 | 2.371 | +0.083 worse |

⇒ **the topology moves the two terms it was designed to move (LOCAL and TILT) in the RIGHT direction,
and pays for it in LEVEL and CURVATURE.** That is exactly item 4's over-compression and item 5a's
wrong slope sign, now measured across the whole matrix instead of at one operating point. It is a
coherent, localised cost — not a diffuse failure — and it says the next move is the shape/headroom
residual, not a retreat from the topology. **But the aggregate is the arbiter and it says no: NOTHING
IS SHIPPED.** Same posture as `btC17` (session 49) and, for one session, `clipC15` (36 → 37).

⚠ The LOCAL improvement is only **0.028 dB** — the notch fix is real (item 3 matches to the bin) but
it is a tiny fraction of the matrix's LOCAL term. Read with item 7: LOCAL is 63 % of the OD residual
and this fixes a small part of it, so **most of that narrow structure is something else** and is the
single largest unexplored lead in A3.

### A3 step 21 — the width requirement, the instrument that could not have measured it, and a bigger finding that is not ATTACK's (session 64)

Session 63's next-step (a): the SHAPE/HEADROOM residual, named there as a **shared-element** fit
(all three null widths ~2.1× too broad by the same factor ⇒ the ladder RC / R12 / R14, not the
switch). Tooling + `src/` plumbing; **nothing shipped as a default** and every new value defaults to
the drawn network. **ctest 16/17** — the one failure is the pre-existing session-44 `OSValidationTest`
at *identical* numbers (`amp 0.35: 2x −25.6 / 4x −32.1 / 8x −23.6`). Baseline verified FIRST:
`attack_render_gate.py --both` reproduces session 63's every figure exactly (notch 316.4/328.1/334.0,
widths 146.5/52.7/134.8, slopes −1.39/+0.10, resid rms 1.27/0.83). New
`analysis/attack_shape_screen.py`; `analysis/attack_notch_probe.py` and
`analysis/attack_render_gate.py` gain the width statistic; **`src/dsp/TrebleAttack.h` gains
`setLadder()`** (session 50's next-step (a), open from session 50 to 63).

#### 1. WIDTH is now part of the shared notch oracle, and the record does not move

`locate_notch()` gained `width` (half-depth **bin span** — the definition sessions 60–63 quote) and
`width_i` (the same contour found by **linear interpolation** of its two crossings). Both are needed:
the pedal's boost null is **4 bins wide**, so a raw bin span is quantised at ~±25 % — far too coarse
to fit against, and it makes an optimiser chase a staircase. The record is quoted on the bin span so
that a recorded number is never silently redefined (the `f_bin`-vs-`f_ref` rule).

`attack_render_gate.py`'s **private copy** of the width function was deleted and it now calls the
oracle — two implementations of one definition is the silent-divergence trap session 62 called out
for the network solver. The probe's JSON also gained `mag_curve` (the raw per-throw magnitude over
180–500 Hz): width is referred to a throw's **own** shoulder, so unlike `h` it cannot be rebuilt
from the stored ratio.

**Regenerated and proven a STRICT SUPERSET twice** (once for the width fields, once after the
`refine_min` guard below): **1196 then 1454 shared leaves bit-identical, worst |Δ| 0.000e+00, 0
lost.** So no session-60–63 number moves. Pedal widths, bin / interpolated:
**70.3 / 23.4 / 64.5** and **77.9 / 27.1 / 71.9 Hz** (cut/boost/flat) — the bin column reproduces
the record exactly.

⭐ And the interpolated column immediately earned its keep: the DRAWN network's three widths are
*identical* on the bin grid (134.8 Hz each) and **138.6 / 137.8 / 138.7** interpolated — they were
never equal, only quantised to the same span.

Two real defects fixed in passing, both on paths nobody had run:
- `attack_render_gate.py --json` was a **`NameError`** (`bleed_sep_db=sep`; `sep` was deleted when
  that gate was rewritten in session 63).
- `refine_min()` **overflowed** (`2.0 ** vx` → `inf`) whenever a near-cancelling parabola threw the
  vertex far outside its bracketing bins — harmless for `f_bin` (an argmin) but it returned `inf`
  for `f_ref`. Now rejects an out-of-bracket vertex. Verified to move nothing recorded.

#### 2. ⚠⚠ THE LOAD-BEARING METHOD FINDING: the fast network screen is NOT calibrated to the shipped chain, and every ATTACK screen since session 61 assumed it is

At session 62's own proposal point, the treble-ladder-only Python solve against the **real render**:

| | f0 (cut/boost/flat) | depth | half-depth width |
|---|---|---|---|
| ladder solve | 316.25 / 327.75 / 333.75 | 14.74 / 32.63 / 15.85 | 121.3 / 52.3 / 139.6 |
| REAL RENDER | 316.4 / 328.1 / 334.0 | **18.51 / 36.62 / 20.31** | **150.6 / 59.6 / 138.6** |
| agreement | **0.35 Hz** | **~4 dB out** | **up to 24 % out** |

**Cause, measured not guessed.** `D(f) = render_dB − ladder_dB` is ONE shared downstream transfer to
within ~0.6 dB (six curves = two very different ladder settings × three throws) and it **FALLS
17.1 dB across 150–700 Hz** — the IC2_B bridged-T scoop heading for its 717 Hz minimum. Depth and
width are both measured against a shoulder at 200–270 Hz, so that tilt sits *inside* them.

⇒ **Session 62 fitted depth on an instrument ~4 dB offset from what ships.** Its reported 0.18 dB
worst depth error was real *in the ladder solve* and became 3.6–4.3 dB through the chain — which
session 63 observed and (correctly, depth being a lower bound) allowed, **without noting that the two
instruments disagree**. They do, and a width fit cannot survive a 24 % scale error.

**GATE C** transfers the requirement into the screen's own units and tests that transfer
out-of-sample, in **both** directions between two different ladders. It **CHECKS**: ±5 Hz f0,
±3.3 dB depth, **±10–27 % width**. So the tool declares itself a **LEVER FINDER** and names
`attack_render_gate.py` as the arbiter — a render is 17.6 s and an optimiser needs thousands of
evaluations, so the screen finds the lever and the render lands the value.

⚠ **And GATE C's first anchor was wrong, in a way worth recording.** Calibrating on the **DRAWN
default** failed by **62 Hz of f0 at every throw, identically** — and that identical-across-throws
error is the tell: `tf_tap` takes ONE optional `c8` spanning M↔T3, so it can express the drawn
**boost** throw (C8 bridges R8) and **cannot express cut or flat at all**. Passing `c8 = 0` models a
drawn network with C8 *removed* — a different circuit from the one that renders, so the
"calibration" was measuring a structural mismatch. **The drawn default is not a valid anchor for
this solver.** The anchor is now a genuinely different ladder at C8 = 0, rendered by the tool itself
(`--render-cal`).

#### 3. ⭐ THE SHARED LADDER IS PLUMBED — session 50's next-step (a), open for 14 sessions

`kR7 / kR12 / kR14 / kC9 / kC6` were `static constexpr` and reachable from **no** tool, which is why
every A3 screen that wanted them had to work in Python instead of the shipped stage. Now
`TrebleAttack::setLadder()` + `FitParams::{trebleR7, trebleLadderR12, trebleLadderR14, trebleC9,
trebleC6}` + `PedalChain::applyParams` + both CLI `--fit` maps. `kG7/kG12/kG14` became runtime
divisions of the same operands.

**Verified in THREE directions** (session 37 item 12 / session 45 item 7a — "default == explicit
nominal" passes on its own even when nothing was rebuilt, which is the trap, not the test):

| check | result |
|---|---|
| `TrebleAttackTest` Test 10: default vs explicit-nominal `setLadder` | **BIT-IDENTICAL** |
| Test 10: each of the five individually | **LIVE** (worst 4.9–13.3 dB) |
| render: default vs explicit-nominal | **BIT-IDENTICAL** |
| render: default vs a `--fit` on R12 / C9 | **DIFFER** |
| render: default vs the **pre-`src`-change binary**, all three throws | **BIT-IDENTICAL** |

Tests 8 and 9 still reproduce session 63 exactly (pole A alone +8.26 dB, pole B alone +0.21 dB,
boost null 9.23 → 20.17 dB).

⚠ All five are **schematic-verified** (circuit.md; covered by the R1–R54 / C1–C39 reconciliation), so
moving one is a capture-vs-document disagreement of the `trebleC7` (147×) / `c21R` (10×) /
`trebleWiperR` (1.4×) class — not a bug fix.

#### 4. ⛔ THE CENSUS — no shared element is a width lever, and the tap is width-neutral

±20 % on every shared value, at the proposal point:

| lever | mean \|Δwidth\| (Hz) | \|Δf0\| (Hz) | **Δwidth per Hz of f0** |
|---|---|---|---|
| R7 | 38.90 | 25.25 | 1.5 |
| R12 | 22.23 | 23.00 | 1.0 |
| C6 | 16.79 | 18.25 | 0.9 |
| C9 | 13.60 | 15.25 | 0.9 |
| C5 | 13.81 | 24.25 | 0.6 |
| R14 | 5.00 | 9.25 | 0.5 |
| **C7** | 2.84 | **0.25** | **11.4** |
| Ra / Rb / Rc / R11 | **0.07–0.32** | **0.00** | — (f0-neutral) |

Every notch-forming element moves width and f0 **together at ~0.5–1.5 Hz per Hz**, and f0 already
matches **to the bin**. Only C7 is width-selective, and its authority is small. ⭐ The **tap divider
is width-NEUTRAL to ≤0.5 Hz and f0-neutral to 0.00 Hz**, which extends session 62's pole-independence
result to the width statistic — so the notch fit PINS the tap and the broadband is fitted separately
(session 62 item 4's rule: separate non-interacting groups rather than let one objective arbitrate).

#### 5. ⚠ THE WIDTH IS REACHABLE — AND THE POINT THAT REACHES IT IS NOT A CANDIDATE

At ±1 decade this looks like a hard conflict: the frontier trades f0 against width and every fit
either holds f0 and stays ~1.3–1.6× too broad, or reaches the width with the f0 **spread collapsed**
to 1.5–5 Hz against the required 17.5 (session 61's "switch the throws off rather than trade"
signature). Seven single- and multi-element families all saturate at **cost 3.22–3.65**, and the
17-dof family beats the 12-dof one by **0.4 %**.

⛔ **But the BOX SWEEP forbids reading that as unreachability**, and that is the gate that mattered:
cost moves **0.71 across 6× of box widening** (3.11 at ±1 decade → 2.40 at ±3), i.e. **not
saturated**. Widening to ±3 decades then finds a point that meets **all nine numbers** — f0 to
0.25–1.0 Hz with spread 18.2 Hz, width to −0.8 / +8.5 / +11.9 %.

⇒ **and it is disqualified on its values, not on its cost:** **R7 × 572** (200 kΩ → **114 MΩ**),
C6 × 62, C5 × 0.025, C9 × 0.032, C7 × 0.024, R14 × 20.4, the tap **on its bound**, and the broadband
at **3.5× floor** with the boost slope overshooting to +2.58 dB/dec. That is session 62 item 4's
"reachable via broadband nonsense" control, arriving on its own. **114 MΩ is 100× the largest
resistor on the board.**

⇒ **The width residual is NOT a value error in the shared ladder.** It is not refuted as
unreachable, and it is not fittable at any plausible value — which is a different and more useful
statement than either.

#### 6. ⭐⭐ AND THE BIGGER FINDING IS NOT ATTACK'S AT ALL — `--tilt`

`h` is a **ratio between throws**, so everything shared by all three cancels out of it *by
construction* — which is precisely why every ATTACK instrument since session 57 has been blind to a
shared error. **Width is not a ratio**: it is measured on one throw's own magnitude against that
throw's own shoulder, so the **absolute** shape through the notch window is inside it. Measured
directly (bleed-free by topology at LEVEL max / BLEND max, drive min), each curve referred to its own
200 Hz value — drop over **200 → 480 Hz**:

| | cut | boost | flat | slope, flat |
|---|---|---|---|---|
| **PEDAL** | −4.93 | −5.36 | **−4.88** | −16.6 dB/dec |
| DRAWN model | −11.14 | −10.74 | **−11.05** | −28.4 dB/dec |
| proposal | −11.27 | −12.84 | −13.47 | −38.1 dB/dec |

**The model's OD path is 6.2 dB too dark across the notch window, in ALL THREE throws** (so it is
shared, not an ATTACK property) and **level-independent to 0.02–0.15 dB** between −36 and −30 dBFS
(so it is not an operating point — session 61 item 3's gate).

⭐⭐ **AND THE ELEMENT IS NAMED, ARITHMETICALLY.** Over the same 200 → 480 Hz the **IC2_B bridged-T
alone drops −10.79 dB** and the two Sallen-Keys together **−0.03 dB**. The drawn model measures
**−11.05 dB** ⇒ the bridged-T accounts for it **to 0.26 dB** and nothing else in the chain has
authority here. **The pedal's scoop is ~2.3× shallower through this window** — which is circuit.md
**risk #1** verbatim ("depth is highly tolerance-sensitive … reshape to whatever the capture shows,
including much shallower than ideal").

⇒ **GAP #1b is REOPENED, on an axis that can see it.** Session 21 closed it on **output** dips over
116 OD rows — in a region where the clean bleed sat **11–31 dB above** the OD path, so it was
insensitive to the OD path's shape *by construction*. Session 51 item 8 already flagged that closure
as "weaker than recorded". This measures the OD path's shape **directly and bleed-free**, and the
model is 6.2 dB too dark by 480 Hz.

#### 7. ⚠ AND THE OBVIOUS MECHANISM WAS TESTED AND REFUTED — the ~2.1× coincidence is a coincidence

It is very tempting to join items 5 and 6: the tilt excess is ~2.1× *and* the width excess is ~2.1×,
so the steeper background must be inflating the half-depth width. **Tested by removing only the tilt
difference** (a first-order rotation about 200 Hz, which cannot create or destroy a null) and
re-measuring the width with the same locator:

| | width now | de-tilted | pedal | ratio after (before) |
|---|---|---|---|---|
| prop cut | 150.6 | 131.9 | 77.9 | **1.69×** (1.93×) |
| prop boost | 59.6 | 47.2 | 27.1 | **1.74×** (2.20×) |
| prop flat | 138.6 | 126.9 | 71.9 | **1.76×** (1.93×) |

⇒ the excess tilt is worth about a **quarter** of the width excess; the rest is a genuine null-Q
difference. And on the DRAWN network de-tilting makes the ratio **worse** (1.93 → 1.96, 2.12). **The
two ~2.1× figures are unrelated.** Recorded because the joined reading is the natural one and it is
wrong.

#### 8. ⚠ THREE OF MY OWN GATES WERE WRONG FIRST — all three the same lesson

- **GATE C's anchor** was the drawn default, which this solver cannot represent (item 2).
- **GATE D** scored an **unmatchable broadband term** with the tap pinned, so it traded notch
  accuracy against it and reported 0.857 — read as "weak optimiser" when it was the gate's own
  construction. Notch-only, it recovers to 0.109. **A search gate must ask exactly the question whose
  failure it is meant to make readable.**
- **The bound check** covered only the shared values, and the **tap was quietly running to ×1/10** of
  a 1-decade box. Now every free value is checked.
- Plus the C5-trim parameterisation mapped the whole negative half of the box to exactly 0 — a
  self-inflicted degeneracy; now linear on [0, 0.3·C5].

⭐ **GENERAL: a gate built to make a failure readable has to be scored on the failing quantity
alone.** Every one of these was caught only because the gate printed the number beside its verdict.

#### 9. WHAT IS AND IS NOT SETTLED

**Settled.** The width statistic and its oracle; the ladder's reachability from every tool; that no
shared ladder element is a width lever at plausible values; that the tap is notch- and width-neutral;
that the fast screen is a lever finder and not a depth/width instrument; and that the OD path carries
a **6.2 dB, ATTACK-independent, level-independent shape error over 200–480 Hz that is the IC2_B
bridged-T**.

**NOT settled.** Why the nulls are ~1.7× too broad once the tilt is removed — that is a real null-Q
difference with no identified carrier. Whether the pedal's shallower scoop is its bridged-T being
shallower or something else compensating (the bridged-T is the only element in the *model* with
authority here; that is not the same claim). And session 63 item 5(a)'s cut-shape disagreement, which
is in the same region and may be one item with this.
