# Reference Validation & Capture — Hard-Won Lessons

How to measure how close the plugin is to the real pedal, and how to capture the pedal so the
measurement is actually trustworthy. Companion to `calibration-and-gain-staging.md` (that doc sets
levels; this one verifies them and the rest of the model against the real thing).

> **The single biggest lesson: the test signal is almost never the limitation — the capture
> SETTINGS MATRIX is.** A perfect signal captured at the wrong/confounded settings can't be fit.
> Spend your recapture budget on the matrix (§3), not on the signal.

The reusable harness lives in `analysis/`:
- `gen_test_signal.py` — the comprehensive A/B signal (full-range sweep + 3 driven sweeps for THD +
  level steps + discrete tones + IMD + decay notes). Single source of truth for segment timings.
- `analyze.py` — reusable primitives: load/align, `normalize_gain` (level-match before shape
  comparison), `transfer` + `band_response` (31-band FR), `thd` (discrete) + `harmonic_thd_curve`
  (continuous Farina swept THD) + `banded_thd` (100 Hz–12 kHz subset of the FR grid, per-harmonic),
  `frac_align`/`null_depth` (sub-sample null), `parse_filename` (clock + 0-10 notations),
  `is_full_length` (truncation guard).

---

## 0. Normalize level before comparing SHAPE — but don't let it hide a real calibration gap

Every FR/THD/harmonic-placement comparison below is about **shape**, not absolute level — so
level-normalize `test` onto `ref` first with `normalize_gain()` (least-squares scalar match) before
running `transfer()` or `banded_thd()`, or a pure level offset from the plugin/capture-gain mismatch
will read as a tonal or distortion-amount difference it isn't. `normalize_gain()` returns the applied
gain in dB alongside the scaled signal — **always look at that number, don't discard it**:

- A gain that varies capture-to-capture with no pattern is ordinary capture-level noise — fine to
  normalize away per-comparison.
- The **same** gain offset appearing consistently across many captures is a real input/output
  calibration gap (§4 below, and `calibration-and-gain-staging.md` §2) — normalizing it away
  capture-by-capture would hide the very thing §4's decomposition is for. Track it, don't silently
  absorb it.

## 1. The four analyses (what each answers)

1. **Frequency response** — the **standard 31-band 1/3-octave grid, 20 Hz–20 kHz**
   (`analyze.py`'s `THIRD_OCTAVE_31_CENTERS`) sampled from the **clean** sweep's continuous curve
   via `transfer()` + `band_response()`. Read EQ ONLY from the clean (low-level) sweep so clip
   harmonics don't pollute the tone fit. This is your taper/tone-stack accuracy check, and it's the
   full-range grid everything else below is defined relative to.
2. **THD by frequency band** — `harmonic_thd_curve()` deconvolves a **driven** sweep (Farina
   exponential-sweep harmonic separation) into a **continuous** THD(f) curve from a single capture —
   no need for hundreds of discrete tones. **VALIDATE the swept curve against the discrete-tone
   `thd()` at the same frequencies before trusting it** — if they disagree, the deconvolution/gating
   is wrong, fix it first. (On the reference build, tightening the harmonic gate to 35% of the
   inter-order gap took the swept curve from ~25% high to within ~1% of the discrete tones.)

   For the actual pass/fail check, don't stop at the continuous curve — bucket it with
   `banded_thd()`, which reuses **the same 31-band grid as the FR analysis above** but reports only
   the **100 Hz–12 kHz subset** of it (where most saturation character lives, and where the driven
   sweep has usable SNR) — it is not a separate band layout, so a THD band and an FR band at the
   same center line up exactly. Report, per band: aggregate THD% AND each harmonic order's
   amplitude relative to the fundamental (dB). Two circuits can land on the same aggregate THD%
   with completely different harmonic **placement** (which bands carry the distortion) and
   **balance** (which orders dominate in each band) — the per-band, per-order breakdown is what
   actually validates clip character, the single-number THD curve only validates clip *amount*.
   Cross-reference against the low-frequency discrete-tone harmonic check in
   `calibration-and-gain-staging.md` §6b, which validates even/odd balance at one frequency in
   detail; `banded_thd()` extends that check across the 100 Hz–12 kHz range.
3. **Null test** — `frac_align()` then `null_depth()`: sub-sample align, optimal-gain level-match,
   subtract, report residual dB. **It measures timbre/shape/phase, NOT absolute level** (the gain
   match removes level). Report the BEST null (cleanest linear setting — the README headline) and
   the WORST (honesty). Integer-only alignment is not enough: 1 sample at 20 kHz ≈ 150° phase error.
   - **Split linear vs nonlinear** with `linear_removed_null()` (coherence-based). The raw null
     removes only a broadband gain, so its residual is part-linear (EQ/phase) and part-nonlinear.
     The linear-removed figure is the floor if every linear difference were matched — what's left is
     the genuinely nonlinear residual (clipping-harmonic phase + the capture's own fidelity). If
     linear-removed is *much* deeper than raw, the residual is mostly LINEAR (a better taper /
     less discretization warp could close it); if they're close, you're at the nonlinear floor and
     tweaking the plugin won't help. (On the reference build: raw ~−11 dB, linear-removed ~−20 dB —
     so ~half the residual was the deliberate tone-taper trade + WDF phase, and the clipping model
     itself agreed to ~−20 dB. Report the nonlinear floor separately; it's the real model-accuracy
     figure.)
   - **Chasing the deepest null (diagnostic):** a coordinate-descent over the knob params (Bass /
     Treble / Drive — NOT Volume, which is pure level the gain-match already removes) tells you
     whether a residual is a small taper-MAPPING offset (deepens with a consistent small tweak
     across independent captures → worth fixing) or just hand-set knob tolerance / the nonlinear
     floor (scatters, or barely moves). On the reference build the tweaks were consistent in
     *direction* but only recovered ~2.5 dB and floored at the same ~−13 dB — confirming the model,
     not a bug. Note Bass+Drive are often COUPLED (shared feedback network), so their individual
     offsets trade off in the search and aren't uniquely attributable.
4. **Knob-tracking pass/fail** — at every captured setting, does the plugin match the real pedal?
   Separate three things with explicit thresholds, because they fail for different reasons:
   - **SHAPE** — EQ compared RELATIVE to 1 kHz (level offset removed) → tone-stack accuracy.
   - **LEVEL** — absolute output at 1 kHz → the gain-staging/makeup calibration.
   - **THD** — distortion amount → clipping character.

---

## 2. Wiring it to your pedal

The orchestrators (compare-vs-batch, null-vs-batch, knob-tracking) render the plugin via an
**`OfflineRender`** console exe that runs your REAL DSP chain plus the exact `processBlock` gain
staging (kInputRef in, kOutputMakeup·volume/kInputRef out), and takes knob positions + mode as
CLI args. Build it as a `juce_add_console_app` target (see `build.md`). Then each orchestrator:
parse filename → render plugin at those settings → `align` both to the reference → compare per §1.
Use OS 8x for the comparison to take aliasing off the table. `analyze.py` is pedal-agnostic; only
the OfflineRender arg layout is per-pedal.

**`OfflineRender` must write 32-bit float WAV, never 16/24-bit integer PCM.**
`calibration-and-gain-staging.md` §2 is explicit that output exceeding 0 dBFS at high drive+volume
is faithful, expected behaviour, not a bug to pad away — so a render batch WILL legitimately contain
samples >1.0 at those settings. Writing that through an integer format hard-clips (or wraps) it at
the format's ceiling, silently corrupting exactly the high-drive captures where THD/harmonic-balance
accuracy matters most, while looking like a normal WAV file (no error, no warning) right up until
the analysis numbers come out wrong. `analyze.py`'s `load()` warns if it's handed an integer-PCM
file for this reason — treat that warning as a real problem, not noise, for any render/capture pair
used in a level- or clipping-sensitive comparison (banded THD, null test). `scipy.io.wavfile.write`
with a `float32` buffer round-trips uncalibrated through this whole path with no extra flags needed.

---

## 3. Capture protocol (the part that actually matters)

1. **Fix the interface gain for the WHOLE session and never touch it.** Ambiguous return gain
   between sessions makes absolute level unverifiable — it cost real investigation on the reference
   build to decide a level deficit was genuine rather than a recording artifact.
2. **Capture a BYPASS pass first** (pedal in true bypass, same signal). This is the absolute-level /
   unity anchor — without it you cannot state absolute level with confidence.
3. **One knob at a time.** Hold the other controls fixed; step only the knob under test (~5–6
   positions). Confounded multi-knob captures can't be used to fit an individual taper.
4. **Sweep EVERY control — including Volume.** A control you never sweep has zero ground truth; on
   the reference build Volume was never captured and its taper stayed an unvalidated guess.
5. **Full length, no truncation.** A short file's missing segments read as zeros → garbage numbers.
   `is_full_length()` skips them, but you still lose the capture.
6. **Read EQ only from the clean sweep** — keep drive low on the FR captures.
7. **Consistent filename notation** the parser understands, e.g.
   `V1200 B0700 T0700 G1030 switch mid <signal>.wav` (clock HHMM: 0700=min, 1200=noon, 1700=max;
   `switch up/mid/down`). The 0-10 dial notation (`G3 V4 B6 T4 SYM`) is also auto-detected.
8. **Cross-check fits against ≥2 batches**, and note **primary vs secondary** references — knob
   direction and component values differ between an original and a licensed reissue.

A good default matrix: bypass ×1; Volume sweep (incl. the pedal's unity position) at min drive/no
cut; Drive sweep × each clip mode; Bass sweep; Treble sweep. ~30 captures, ~40 min.

---

## 4. Decomposing a level deficit (do this before changing any constant)

If the plugin is quieter/louder than the real pedal, find out WHY before touching `kOutputMakeup`:

- Measure plug−real at a **clean, low input level** (no clipping) across several input levels.
  - **Constant across input level** → a pure linear-gain error → makeup (or a globally-off volume
    taper). Anchor the fix on the **cleanest pure-linear, no-drive** capture.
  - **Grows with drive** → the clipped-output scaling (the clipping ceiling). **Do NOT mask this
    with makeup** — makeup is a flat scalar; using it to paper over a drive-dependent gap throws off
    every clean setting. (See the "go hotter" trap in `calibration-and-gain-staging.md`.)
  - **Differs by volume position** → the volume taper, not makeup.
- **Cross-check:** after fixing makeup, unity (output = input at min drive / no cut) should land at
  the volume position the REAL pedal does (often ~1 o'clock). If the makeup that level-matches your
  captures ALSO lands unity at the right spot, that's two independent facts agreeing — strong
  evidence it's right. (On the reference build this is exactly how the makeup value was confirmed.)

This decomposition is why `calibration-and-gain-staging.md` §2 says **calibrate makeup to the
captures** rather than pinning it to a "headroom-safe" number — see that section.

### When a measurement contradicts the physics, suspect the capture — not the model

Before reshaping a taper to chase a discrepancy, check it against what the circuit is *physically
forced* to do. If the captures imply behaviour the topology can't produce, it's almost certainly a
capture artifact (usually a per-session recording-gain offset — exactly what the bypass anchor and
fixed-gain rule above prevent). Reshaping the model to match would bake a recording error into the
plugin and wreck the control's feel.

Worked example (reference build): one volume position read ~3.5 dB quiet vs another, suggesting the
volume taper was wrong. But the volume divider (audio pot + a fixed resistor across the upper arm)
is *physically forced* to rise ~+3.3 dB between those two positions **regardless of the pot's taper
law** (the fixed resistor pins the upper arm ~constant in that range, so the divider just tracks the
wiper). The captures showing the two positions ~equal is impossible for that circuit — so it was a
capture-gain discrepancy between the two sessions, not a taper error, and the model was left alone.
The tell: the deficit ≈ exactly the one physically-correct step. (A separate gotcha from this:
controls in a feedback gain-set leg invert the pot's concavity vs a plain divider/attenuator, and
some tone pots are reverse-wired — so "what taper shape is correct" depends on where the pot sits in
the circuit, not just the pot's own marking. Verify the topology before fitting a taper.)
