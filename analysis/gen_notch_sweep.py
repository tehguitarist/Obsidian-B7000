#!/usr/bin/env python3.11
"""Phase-9 SESSION 68 — dedicated STIMULUS for measuring the ATTACK cancellation notch WITHOUT the
bin-smearing and shoulder-contamination biases that every depth/width number since session 61 has
had to carry.

Standalone signal (does NOT touch the frozen main test signal or its captures), same pattern as
`gen_jfet_ladder.py`. See `docs/final-capture-window.md` §3 for the recording matrix.

WHY THIS EXISTS
---------------
The open ATTACK item is now the null's WIDTH, and width is exactly the quantity a 5.86 Hz-bin CSD
estimate corrupts worst. `attack_notch_probe.py`'s own self-test measured TWO distinct biases, and
both UNDERSTATE:
  * BIN SMEARING          a 5.86 Hz-bin estimate cannot reach a sharp deep floor -- a true 33 dB
                          notch reads 28.71 dB.
  * SHOULDER CONTAMINATION a broad notch's own skirt reaches into the 200-270 Hz reference window,
                          so `shoulder - min` understates the depth DEFINITIONALLY (-4.39 dB at
                          Qp 0.7).
And the pedal's boost null is only ~4 bins wide, so its half-depth BIN-SPAN width is quantised at
roughly +-25% -- which is why session 63 had to add an interpolated width column, and why session
66's width result (0.87/1.29/1.03x the pedal's) still carries a caveat it cannot shed.

A STEPPED SINE removes all of it. Each tone is measured narrowband at its OWN frequency, so there is
no band averaging, no window leakage across the notch, and the resolution is the STEP SIZE (2 Hz),
not a transform's bin width. f0 and width become directly measured rather than
estimated-with-a-bias-note.

⚠ CORRECTION (session 70): "and depth stops being a lower bound" -- as this header originally read
-- WAS AN OVER-CLAIM, and it contradicted this file's own scope note further down ("read a broad
depth as a bound"). A stepped sine fixes BIN SMEARING, which is a resolution artefact, but NOT
SHOULDER CONTAMINATION, which is definitional: a broad null's skirt reaches into the 200-270 Hz
reference window however finely the axis is sampled. Measured on the reader's self-test, the
shoulder method still understates a Qp 0.7 null by -4.23 dB.
⭐ Depth IS now a value rather than a bound, but that came from a different fix, in the reader
rather than the stimulus: `read_notch_sweep.fitted_depth` fits the two-pole notch's own analytic
magnitude plus a linear background to the whole curve, so depth is a FITTED parameter instead of a
difference of two contaminated points. That recovers all six synthetic cases to <=0.03 dB,
including the broad ones. It costs an assumption (that the null is two-pole), which is why the
definitional `depth` is still reported beside it.

⭐ SESSION 68 ALSO RAISED THE PRIORITY OF THIS MEASUREMENT. At drive noon the null was measured to
lose ALL ATTACK dependence (f0 328.1/328.1/328.1 Hz, spread 0.0 Hz, depths within 0.91x) where at
drive min it moves 17.6 Hz with boost 2.04x deeper. Both reads are stable to the bin across their
quiet levels, so they genuinely disagree, and the disagreement is UNEXPLAINED. A measurement free of
the smearing/contamination biases is the natural arbiter, which is why both drive settings are in the
matrix below rather than just the near-linear one.

CONTENTS (48 kHz, 32-bit float, ~176 s)
---------------------------------------
  * sweep_clean   10 s log sweep @ -30 dBFS. ⭐ REQUIRED, and it must keep this NAME: `analyze.align`
                  correlates on it, so it is the alignment anchor. Also gives a free continuous
                  reference read of the same notch on the old instrument, in the same file -- so the
                  stepped and swept measurements can be compared WITHIN one capture, with no
                  take-to-take term between them.
  * cal_1k        1 s tone @ 1 kHz, -14 dBFS. Kept as a level/rate reference for a human reading
                  the file, and cheap to leave in.
                  ⛔⛔ CORRECTION (session 70): THIS DOES **NOT** MAKE `captures.load_capture()`
                  WORK, AND THE ORIGINAL CLAIM HERE WAS WRONG. That guard inspects a FIXED window at
                  t = 0.5-1.45 s, not the segment map -- and in this stimulus the 10 s `sweep_clean`
                  anchor occupies that window (it has to come first, or the aligner would be
                  correlating behind 100 tones), so the cal tone lands at ~10.6 s where the guard
                  never looks. Measured consequence: the guard reads the sweep's ~30 Hz content,
                  infers a huge speed error, and RESAMPLES a 176.100 s capture down to 89.9 s --
                  after which every segment offset is wrong and the -18 dBFS half of the file falls
                  off the end and reads -600 dB. Session 13's note on the jfet ladder ("use the raw
                  loader, NOT captures.load_capture()") applies here for the SAME reason, and this
                  header claimed to have solved it without testing that it had.
                  ⇒ **Readers of this stimulus must load raw** -- see `read_notch_sweep.load_raw`.
  * nt_<f>_<dB>   0.5 s tones on the variable grid below, at each of LEVELS_DB. 126 steps x 2 levels.

WHY THESE PARAMETERS
--------------------
  SPAN 150-550 Hz   ⭐ chosen by the SHOULDER, not by the notch -- see the comment on SKIRT_HZ. It must
                    contain the 200-270 Hz window every depth is referred to AND the 421.9 Hz upper
                    shoulder, with clearance either side for a BROAD null's skirts. A 250-450 span
                    (my first draft) is wide enough for the null and still gets the depth wrong.
  CORE 280-380 Hz   at 2 Hz: ~3x finer than the 5.86 Hz bin grid, so a 4-bin-wide null is resolved by
                    ~12 points instead of 4. Every null this project has measured lands in here
                    (316.4 / 328.1 / 334.0 at drive min, 328.1 at drive noon, and session 46's
                    334 -> 299 Hz migration).
  SKIRTS at 4 Hz    the skirts only have to establish a LEVEL -- nothing sharp lives out there -- so
                    halving their resolution halves the file length at no cost to any measurement.
  0.5 s tones       150 cycles at 300 Hz -- ample for a narrowband estimate, and 0.5 s of steady
                    state is >> any settling time in the pedal's audio-band networks.
  LEVELS -30/-18    -30 matches `sweep_clean` (the quiet, near-linear read every notch number is
                    quoted at) and -18 is the level CONTROL: session 46 measured this notch MIGRATING
                    with level, so a single level cannot tell a network property from an operating
                    point. Two levels keep the file short enough to record comfortably; the existing
                    swept captures already cover -36/-12/-6.

VALIDATED AGAINST SYNTHETIC NOTCHES OF KNOWN f0 / DEPTH / WIDTH (session 68)
---------------------------------------------------------------------------
Five two-pole notches (depth exact in closed form via Qz = Qp*10^(depth/20), w0 prewarped so the
bilinear maps the null to exactly f0) pushed through THIS stimulus and read narrowband, against the
same notches read by `analyze.transfer` on the embedded 10 s sweep:

  truth  328/33/Qp4.0   STEPPED f0 328.0 depth 32.74 width  12.1  |  SWEPT 328.1  28.69  15.6
         316/15/Qp0.9           316.0       11.32       108.7     |        316.4  11.45 103.9
         334/16/Qp1.0           334.0       13.29       107.1     |        334.0  13.65 101.0
         328/30/Qp2.0           328.0       29.05        27.5     |        328.1  27.41  31.2
         300/20/Qp1.5           300.0       17.79        54.1     |        298.8  18.41  50.9

  ⭐ On the SHARP null -- which is what the boost throw is (32.7 dB, ~4 bins wide, and the throw whose
    WIDTH is the open item) -- the depth error is 0.26 dB against the swept instrument's 4.31, and the
    width reads 12.1 Hz against 15.6. A ~30% systematic over-read on a ~12 Hz feature is the SAME SIZE
    as the 0.87-1.29x width discrepancy sessions 63-66 have been arguing about.
  ⭐ f0 is recovered EXACTLY on the stepped grid in all five cases.
  ⚠ The residual error on the BROAD notches (true 15 -> read 11.3) is NOT a resolution problem and this
    stimulus does not fix it: `shoulder - min` understates a broad null DEFINITIONALLY. Both instruments
    now show it equally (11.32 vs 11.45), which is how you can tell it is definitional rather than
    instrumental. Read a broad depth as a bound; the sharp ones are values.

⚠ SCOPE / WHAT THIS STILL DOES NOT DO
  * MAGNITUDE ONLY. A notch's depth is set by how exactly two paths cancel, i.e. by phase. A stepped
    sine CAN carry phase if the capture's latency is known -- which is what `docs/final-capture-window.md`
    protocol item 1 (a bracketing `bypass` take) exists to make possible -- but nothing here assumes it.
  * The pedal is still measured through its own nonlinearity at any level; the -18 dBFS row is a
    control for that, not an escape from it. Read the quiet row (session 61 item 3).

Run:  /opt/homebrew/bin/python3.11 analysis/gen_notch_sweep.py   (writes analysis/notch_sweep_48k.wav)
"""
import numpy as np
from scipy.io import wavfile
import gen_test_signal as G   # reuse fade()/log_sweep()/tone()/silence() so conventions never drift

FS = G.FS
# ⚠⚠ THE SPAN MUST REACH THE SHOULDER, AND MY FIRST VERSION DID NOT. It ran 250-450 Hz, which looks
# generous around a null at 316-334 Hz -- but every DEPTH in this project is referred to the
# **200-270 Hz shoulder**, and a BROAD null's skirt reaches into that window (that is
# `attack_notch_probe`'s shoulder-contamination bias). With no data below 250 Hz the stepped read has
# to take its shoulder from 250-270 Hz, i.e. from deep inside the skirt. Validated against synthetic
# notches: on a Qp 0.9 / 15 dB null the 250 Hz version read the depth as **7.56 dB, WORSE than the
# 5.86 Hz-bin swept instrument it was built to beat (8.88)**, while nailing the sharp Qp 4 case.
# ⇒ a finer grid does not help if the grid does not span the REFERENCE the quantity is defined against.
# Fixed by reaching 150 Hz (well clear of the 200-270 shoulder) and 550 Hz (clear of the 421.9 Hz
# upper shoulder), with the step VARIED so the file stays a sane length: nothing in the skirts is
# sharp, so they only need enough resolution to establish a level.
CORE_HZ = (280.0, 380.0)                 # the notch itself -- every null measured lands in here
CORE_STEP = 2.0                          # ~3x finer than the 5.86 Hz bin grid
SKIRT_HZ = (150.0, 550.0)                # must span the 200-270 shoulder AND the 421.9 upper peak
SKIRT_STEP = 4.0                         # levels only; no sharp feature lives out here
LEVELS_DB = (-30, -18)                   # -30 = the quiet near-linear read; -18 = level CONTROL
TONE_SEC = 0.5                           # 150 cycles at 300 Hz
CAL_DB = -14                             # matches the main signal's discrete-tone level
GAP = 0.15
LEAD = 0.5
TAIL = 0.5


def _freqs():
    lo = np.arange(SKIRT_HZ[0], CORE_HZ[0], SKIRT_STEP)
    core = np.arange(CORE_HZ[0], CORE_HZ[1] + 0.5 * CORE_STEP, CORE_STEP)
    hi = np.arange(CORE_HZ[1] + SKIRT_STEP, SKIRT_HZ[1] + 0.5 * SKIRT_STEP, SKIRT_STEP)
    return np.concatenate([lo, core, hi])


FREQS = _freqs()


def build_segments():
    # sweep FIRST -- analyze.align correlates on it, so it must not sit behind 100 tones.
    segs = [("sweep_clean", G.log_sweep(G.SWEEP_SEC, -30)),
            ("cal_1k", G.tone(1000.0, 1.0, CAL_DB))]
    for db in LEVELS_DB:
        for f in FREQS:
            segs.append((f"nt_{f:g}_{db}", G.tone(float(f), TONE_SEC, db)))
    return segs


def assemble():
    parts = [G.silence(LEAD)]
    pos = LEAD
    times = {}
    for name, audio in build_segments():
        t0 = pos
        parts.append(audio)
        pos += len(audio) / FS
        times[name] = (t0, pos)
        parts.append(G.silence(GAP))
        pos += GAP
    parts.append(G.silence(TAIL))
    return np.concatenate(parts).astype(np.float32), times


def segment_times():
    return assemble()[1]


if __name__ == "__main__":
    sig, times = assemble()
    out = "analysis/notch_sweep_48k.wav"
    wavfile.write(out, FS, sig)
    peak = float(np.max(np.abs(sig)))
    print(f"wrote {out}  ({len(sig)/FS:.1f} s, {len(sig)} samples, {FS} Hz, 32-bit float)")
    print(f"peak = {peak:.4f}  ({20*np.log10(peak+1e-20):.1f} dBFS)")
    print(f"tones: {len(FREQS)} steps x {len(LEVELS_DB)} levels = {len(FREQS)*len(LEVELS_DB)}")
    print(f"span {SKIRT_HZ[0]:g}-{SKIRT_HZ[1]:g} Hz: core {CORE_HZ[0]:g}-{CORE_HZ[1]:g} at {CORE_STEP:g} Hz, skirts at {SKIRT_STEP:g} Hz "
          f"(vs the {FS/8192.0:.2f} Hz bin grid it replaces)")
    print(f"levels: {', '.join('%g dBFS' % d for d in LEVELS_DB)}")
    print("\nanchors present:  sweep_clean (analyze.align)   cal_1k (level reference only -- see the")
    print("                  header: it does NOT satisfy captures.load_capture; load raw)")
    print("first/last few segments (s):")
    keys = list(times)
    for name in keys[:4] + ["..."] + keys[-2:]:
        if name == "...":
            print("   ...")
            continue
        t0, t1 = times[name]
        print(f"  {name:16} {t0:7.3f} .. {t1:7.3f}  ({t1-t0:.2f}s)")
