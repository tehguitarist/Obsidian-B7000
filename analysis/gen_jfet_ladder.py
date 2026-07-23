#!/usr/bin/env python3.11
"""Phase-7 SESSION 13 — dedicated STIMULUS for the drive-min static-vs-dynamic CONFIRM capture.

Standalone signal (does NOT touch the frozen main test signal or its captures). Play it through
the REAL B7K Ultra at DRIVE-MIN (see recording notes in the session handover) and record the
output; the reader `analysis/read_jfet_ladder.py` then extracts H2(f, level) and overlays the
below-/on-/above-corner slope curves against the model to CONFIRM the JFET is static.

WHY these contents (handover §3o(2), §3r): the existing data has a DENSE H2-vs-level ladder only
at 1 kHz; the below-corner (110 Hz) and on-corner (220 Hz) rest on 3 slope samples each, which is
the sole thinness in the session-13 STATIC lean. This signal gives 3 dense, clipper-free ladders
(110 below / 220 on / 440 above the 219 Hz C3 corner) extending well below the old -36 dBFS floor,
so the collapse test has real below-corner coverage.

CONTENTS (48 kHz, 32-bit float, ~85 s):
  * sweep_clean : 10 s log sweep @ -30 dBFS  — alignment anchor (analyze.align correlates on this
                  name) + a bonus continuous H2(f) at drive-min.
  * lad_<f>_<dB>: 1.0 s tones @ f in {110,220,440} Hz, levels -6 .. -60 dBFS in 3 dB steps.
                  Same 3 dB grid as the main 1 kHz ladder (overlaps -6..-36), extended to -60.
Top of the ladder (-6 dBFS) grazes the CD4049 onset on purpose (to locate where the clean-JFET
regime ends at each tone); the reader excludes clipper-contaminated points from the static verdict.

Run:  /opt/homebrew/bin/python3.11 analysis/gen_jfet_ladder.py    (writes analysis/jfet_ladder_48k.wav)
"""
import numpy as np
from scipy.io import wavfile
import gen_test_signal as G   # reuse fade()/log_sweep()/tone() so conventions never drift

FS = G.FS
LADDER_FREQS = (110.0, 220.0, 440.0)     # below / on / above the 219 Hz C3 degeneration corner
LADDER_DB = list(range(-6, -61, -3))     # -6, -9, ... , -60  (19 steps, same grid as the 1k ladder)
TONE_SEC = 1.0
GAP = 0.3
LEAD = 0.5
TAIL = 0.5


def build_segments():
    segs = [("sweep_clean", G.log_sweep(G.SWEEP_SEC, -30))]   # alignment anchor, same name as main
    for f in LADDER_FREQS:
        for db in LADDER_DB:
            segs.append((f"lad_{f:g}_{db}", G.tone(f, TONE_SEC, db)))
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
    out = "analysis/jfet_ladder_48k.wav"
    wavfile.write(out, FS, sig)
    peak = float(np.max(np.abs(sig)))
    print(f"wrote {out}  ({len(sig)/FS:.1f} s, {len(sig)} samples, {FS} Hz, 32-bit float)")
    print(f"peak = {peak:.4f}  ({20*np.log10(peak+1e-20):.1f} dBFS)  — no clipping headroom margin")
    print(f"tones: {LADDER_FREQS} Hz x {len(LADDER_DB)} levels ({LADDER_DB[0]}..{LADDER_DB[-1]} dBFS, 3 dB)")
    print("\nsegment timing map (s):")
    for name, (t0, t1) in times.items():
        print(f"  {name:14} {t0:7.3f} .. {t1:7.3f}  ({t1-t0:.2f}s)")
