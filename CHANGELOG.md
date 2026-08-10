# Changelog

## 1.0.1 — 2026-08-10

Accuracy follow-up to 1.0.0. No control, parameter, or preset changes — a DAW project saved against
1.0.0 loads and sounds the same except where listed below.

### Fixed

- **A footswitch click.** Engaging or disengaging the Distortion footswitch could produce an
  audible click at some EQ settings — the internal mix-balance stages were reading the wrong signal
  during the footswitch's own transition. Worst case measured at 2.85× the signal's own largest
  sample-to-sample step; now measures at 0.59×, below the signal's own step.
- **The 3-position switches (Attack, Grunt, and both mid-frequency selectors) now crossfade
  cleanly** when changed during playback, closing the small click 1.0.0 listed as a known
  limitation.
- The overdrive tone-shaping stage's correction at the Grunt Boost and Flat positions was applied
  with the wrong sign (making the ~320 Hz midrange character less accurate, not more, at those
  switch positions); corrected. At Grunt Cut, a residual over-correction at moderate Drive settings
  is narrowed.
- The bass response's centre frequency at Grunt = Cut is corrected. A user-reported "less bass"
  perception traced to that null sitting at roughly 1.37× the intended frequency — a centring
  error, not a level one.
- A previously-unmodelled coupling capacitor in the LO-MID EQ band (present on the schematic) is
  now in the model, improving low-mid accuracy.

### Changed

- **6 of 14 gated accuracy rows are now over their agreed target** (down from 9 at 1.0.0).
- The overdrive-path headroom fix flagged in 1.0.0 as scheduled for this release ("clipper
  headroom") was investigated and found not to fit inside the pedal's own 9 V supply rail — it does
  not work, on the physics, not on effort. The underlying defect (the overdrive path reads quiet
  relative to the reference, worst at Grunt flat/boost) remains, and is now understood to be a
  structural limit rather than an open task.

### Verification

- **22/22** automated tests (was 21/21).
- Re-validated against the same 162-capture reference matrix.

## 1.0.0 — 2026-08-06

First release. Circuit-level emulation of the **Darkglass B7K Ultra** bass overdrive / DI preamp,
built as AU + VST3 on JUCE 8 and `chowdsp_wdf`.

### What it is

A wave-digital model of the pedal's actual signal path, not a filter-bank imitation: J201 JFET
front end, CD4049UBE CMOS-inverter clipper solved implicitly per sample, the treble/ATTACK ladder,
the GRUNT coupling bank, the recovery bridged-T and both Sallen-Key sections, the 4-band active
Baxandall EQ with switchable mid frequencies, and the LEVEL/BLEND crossfade — all with the
schematic's own component values except where a fit against the reference demanded otherwise (each
such departure is recorded at the constant).

**Controls.** MASTER, BLEND, LEVEL, DRIVE, 4-band EQ (LO / LO-MID / HI-MID / HI) with 3-position
LO-MID (250/500/1k Hz) and HI-MID (750/1.5k/3k Hz) selectors, 3-way ATTACK, 3-way GRUNT, plus
input/output trims with an optional link, selectable 1×/2×/4×/8× oversampling (separate realtime
and offline-render factors), and true bypass.

### Verification

- **21/21** automated tests, including a full control sweep (3123 configurations — every switch
  combination × DRIVE × BLEND × LEVEL, the four EQ knobs, all four oversampling factors, and
  continuous knob motion) with no NaN/Inf, no instability and no clicks from any continuous control.
- **AU validation passes** (`auval -v aufx Ob7k LPrc`).
- Validated against a 162-capture reference matrix on 1/3-octave frequency response, continuous
  swept THD, per-order harmonics and sub-sample null depth.

### Performance

At the shipped 2× default: **~2.5 % of one CPU core, 40× realtime, 49 samples latency.** 1× is
~1.2 %, 8× ~7.2 %. (Machine-specific; only the ratios are meaningful.)

### Known limitations — measured, not estimated

- **The overdrive path is quiet relative to the reference**, by roughly 1 dB at GRUNT cut and 6–8 dB
  across the midband at GRUNT flat/boost, bleed-free. This is the project's largest open defect;
  its physical-carrier search is exhaustively closed and the remaining candidate (clipper headroom)
  is scheduled for the next release.
- **9 of 14 gated accuracy rows are over their agreed target.** Six have been since the
  oversampling/ADAA re-anchor; three are the measured, deliberately-accepted price of engineered
  corrections aimed at defects the reference matrix cannot see.
- **The 3-position switches are not crossfaded**, so changing a mid-frequency selector during
  playback produces a small step (measured at ~2.5× the signal's own largest sample-to-sample
  change — audible as a soft click, not a bang). ATTACK and GRUNT are well below that.
- **The reference is an emulation, not a hardware unit.** Even-order harmonic structure is the one
  axis where hardware measurements govern instead, and the model is deliberately aimed at hardware
  for the low-frequency corners — so it diverges from the reference there on purpose.
- The XLR balanced DI output is not modelled (it is a buffer/inverter pair fed from the same
  MASTER-controlled node as the ¼" output).
