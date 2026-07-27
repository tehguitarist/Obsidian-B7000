#!/usr/bin/env python3.11
"""Phase-9 SESSION 53 — dedicated STIMULUS for an UNBIASED A3 complex-target measurement.

Standalone signal (does NOT touch the frozen main test signal or its captures — same posture as
`gen_jfet_ladder.py`). Play it through the REAL B7K Ultra across a BLEND sweep and record the
output; the reader `analysis/read_a3_tones.py` then feeds the same blend-axis algebra as
`a3_blend_axis.py` but with the FUNDAMENTAL extracted narrowband instead of a 1/3-oct band total.

WHY THIS EXISTS — it removes the one known bias in the session-52 impossibility proof.
`a3_blend_axis.py` solves `t(B)^2 = 1 + k1.B + k2.B^2` from band ENERGY. That is exact for the
mixing law (every OD harmonic carries the same B, so band energy keeps the quadratic form), but
the recovered magnitude is then

    r = sqrt(|g1|^2 + H)        H = the band's HARMONIC power

i.e. an UPPER BOUND on the fundamental, while `Q = Re g1` stays exact — so `cos theta = Q/r` is
biased TOWARDS 90 degrees (session 52 item 3b). Two consequences the whole project now rests on:

  1. The ~-38 deg "excess lead" that proves NO causal linear post-clipper element can supply A3's
     target is computed from that biased theta. Session 52 sized the bias (needs H/P of 0.6..265
     to reconcile; impossible at 8 of 15 bands) but could not MEASURE it away.
  2. C3's size at 20-32 Hz "is not measured to better than ~3 dB" for the same reason — and C3 is
     the DOMINANT A3 term (session 51 item 7).

With a single tone per band there is no harmonic power INSIDE the measurement: the fundamental is
extracted at exactly the drive frequency, so `r` becomes the fundamental magnitude and `theta`
becomes unbiased. If the excess lead SURVIVES on tones, the session-52 impossibility is airtight
and the search must move pre-clipper. If it COLLAPSES, sessions 47-52 were chasing an artefact and
the post-clipper region reopens. Either answer is worth the capture.

CONTENTS (48 kHz, 32-bit float, ~105 s):
  * sweep_clean  : 10 s log sweep @ -30 dBFS — alignment anchor. SAME NAME as the main signal's
                   anchor on purpose, so `analyze.align()` correlates on it unchanged.
  * tn_<f>_<dB>  : 2.0 s tones at the project's 1/3-oct band centres 20 Hz .. 1613 Hz, at TWO
                   levels: -18 dBFS (the A3 measurement condition — GRUNT cut / drive noon /
                   -18 dBFS, the operating point every A3 number is quoted at) and -30 dBFS (a
                   near-linear CONTROL: at -30 the OD path is ~linear, so the same solve must
                   return a level-INDEPENDENT transfer. If it does not, the tone read is itself
                   level-contaminated and must be reported as such, not averaged).

Band list = the 17 A3 bands plus the three 2/3-oct side monitors below 2 kHz (session 49 item 8).
Nothing above 1613 Hz: session 51 item 5 established the blend axis diverges above ~2 kHz, and the
fit band is 40 Hz - 1.7 kHz (session 52 item 1). 20/25/32 Hz ARE included precisely because that is
where the existing instrument is worst.

TONE_SEC = 2.0 gives 40 cycles at 20 Hz; the reader windows the MIDDLE 1.5 s so neither the 5 ms
fade nor any settling transient enters the estimate.

Run:  /opt/homebrew/bin/python3.11 analysis/gen_a3_tones.py   (writes analysis/a3_tones_48k.wav)
"""
import numpy as np
from scipy.io import wavfile
import gen_test_signal as G   # reuse fade()/log_sweep()/tone()/silence() so conventions never drift

FS = G.FS

# The project's 1/3-oct band centres over A3's span (matches a3_blend_axis / a3_shape_gate / the
# report's `meta.bands` values below 2 kHz). Do NOT round these — the reader extracts at exactly
# these frequencies and any mismatch shows up as a spurious magnitude/phase error.
TONE_FREQS = (20.0, 25.0, 32.0, 40.0, 50.0, 64.0, 80.0, 101.0, 127.0, 160.0,
              202.0, 254.0, 320.0, 403.0, 508.0, 640.0, 806.0, 1016.0, 1281.0, 1613.0)

TONE_DB = (-18, -30)      # A3's own condition, then a near-linear control (see docstring)
TONE_SEC = 2.0
GAP = 0.3
LEAD = 0.5
TAIL = 0.5


def build_segments():
    segs = [("sweep_clean", G.log_sweep(G.SWEEP_SEC, -30))]   # alignment anchor, same name as main
    for db in TONE_DB:
        for f in TONE_FREQS:
            segs.append((f"tn_{f:g}_{db}", G.tone(f, TONE_SEC, db)))
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
    out = "analysis/a3_tones_48k.wav"
    wavfile.write(out, FS, sig)
    peak = float(np.max(np.abs(sig)))
    print(f"wrote {out}  ({len(sig)/FS:.1f} s, {len(sig)} samples, {FS} Hz, 32-bit float)")
    print(f"peak = {peak:.4f}  ({20*np.log10(peak+1e-20):.1f} dBFS)")
    print(f"tones: {len(TONE_FREQS)} bands ({TONE_FREQS[0]:g}..{TONE_FREQS[-1]:g} Hz) "
          f"x {len(TONE_DB)} levels {TONE_DB} = {len(TONE_FREQS)*len(TONE_DB)} segments")
    print("\nsegment timing map (s):")
    for name, (t0, t1) in times.items():
        print(f"  {name:16} {t0:7.3f} .. {t1:7.3f}  ({t1-t0:.2f}s)")
