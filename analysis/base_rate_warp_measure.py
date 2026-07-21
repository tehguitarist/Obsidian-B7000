#!/usr/bin/env python3
"""Measure the model's OWN base-rate bilinear top-octave warp.

The target for a Phase-8 calibration high-shelf (dsp.md "Top-octave accuracy"):
render the clean/linear path at base fs (48k) and at 2x base fs (96k, the
near-analog reference), and compare the clean-sweep FR. The droop
mag(48k) - mag(96k), normalised to 1 kHz, is exactly what the shelf should
invert. This is fit to the PLUGIN's own two-rate difference, NOT to captures —
it isolates the discretisation warp from every other calibration question.

Run from repo root (single-unit pedal — no "revisions"; the clean path is
selected with --dry-args, defaulting to DIST-off + full-wet BLEND):
    /opt/homebrew/bin/python3.11 analysis/base_rate_warp_measure.py
    /opt/homebrew/bin/python3.11 analysis/base_rate_warp_measure.py \\
        --dry-args "--dist-engage,0,--blend,1.0,--drive,0.0" --os 8
"""
import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A  # noqa: E402
import captures as C  # noqa: E402

ANCHORS = (6000, 8000, 10000, 12500, 14500, 16000)

# The clean/linear path: distortion disengaged (BLEND forced to 100% clean),
# blend full so nothing of the OD path leaks, drive at minimum. This is the row
# the shelf is fit against — a pure linear render whose only top-octave error is
# the base-rate cap warp we're trying to measure.
_DEFAULT_DRY_ARGS = ["--dist-engage", "0", "--blend", "1.0", "--drive", "0.0"]


def transfer_db(out, inp, fs, targets):
    """Welch/CSD transfer magnitude at ``targets``, over the clean-sweep window."""
    a, b = A.T["sweep_clean"]
    i0, i1 = int(a * fs), int(b * fs)
    o = out[i0:i1]
    x = inp[i0:i1]
    n = min(len(o), len(x))
    npseg = 8192 * (fs // 48000)
    import scipy.signal as sps
    f, Pxy = sps.csd(x[:n], o[:n], fs, nperseg=npseg)
    _, Pxx = sps.welch(x[:n], fs, nperseg=npseg)
    H = 20 * np.log10(np.abs(Pxy) / (Pxx + 1e-20) + 1e-12)
    return {t: float(np.interp(t, f, H)) for t in targets}


def _to_mono_f64(y):
    if y.dtype.kind in "iu":
        y = y.astype(np.float64) / np.iinfo(y.dtype).max
    else:
        y = y.astype(np.float64)
    return y[:, 0] if y.ndim > 1 else y


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", default=C.RENDER_BIN, help="path to OfflineRender binary")
    ap.add_argument("--dry-args", default="",
                    help="comma-separated CLI flags selecting the clean/linear render "
                         "(default: DIST off + full-wet BLEND + zero DRIVE)")
    ap.add_argument("--os", type=int, default=8)
    a = ap.parse_args()

    if not os.path.exists(a.bin):
        sys.exit(f"OfflineRender not found at {a.bin} — cmake --build build --target OfflineRender")

    dry_args = [t.strip() for t in a.dry_args.split(",") if t.strip()] or _DEFAULT_DRY_ARGS

    orig48 = A.load(A.ORIG)

    with tempfile.TemporaryDirectory() as tmp:
        import scipy.signal as sps
        in96 = sps.resample_poly(orig48, 2, 1)
        p48 = os.path.join(tmp, "in48.wav")
        p96 = os.path.join(tmp, "in96.wav")
        wavfile.write(p48, 48000, orig48.astype(np.float32))
        wavfile.write(p96, 96000, in96.astype(np.float32))

        print("=" * 78)
        print("Model's OWN base-rate top-octave warp")
        print("droop = mag(48k) - mag(96k); NEGATIVE = 48k model is DARKER = shelf target.")
        print("Normalised to 1 kHz. This is the shelf's target -- fit to plugin, NOT captures.")
        print(f"clean path: {' '.join(dry_args)}")
        print("=" * 78)
        print(f"{'':>4} | " + " ".join(f"{f / 1e3:>6.1f}k" for f in ANCHORS))

        o48 = os.path.join(tmp, "warp_48.wav")
        o96 = os.path.join(tmp, "warp_96.wav")
        cmd48 = [a.bin, p48, o48, "--os", str(a.os)] + dry_args
        cmd96 = [a.bin, p96, o96, "--os", str(a.os)] + dry_args
        for cmd, label in [(cmd48, "48k"), (cmd96, "96k")]:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                sys.exit(f"render failed @ {label}: {r.stderr or r.stdout}")

        _, y48 = wavfile.read(o48)
        _, y96 = wavfile.read(o96)
        y48 = _to_mono_f64(y48)
        y96 = _to_mono_f64(y96)

        H48 = transfer_db(y48, orig48, 48000, ANCHORS + (1000,))
        H96 = transfer_db(y96, in96, 96000, ANCHORS + (1000,))
        droop = {t: (H48[t] - H48[1000]) - (H96[t] - H96[1000]) for t in ANCHORS}
        print(f"{'dB':>4} | " + " ".join(f"{droop[t]:>7.2f}" for t in ANCHORS))

        print("=" * 78)
        print("Shelf should invert this row (a rising high-shelf).")
        print("Fit corner/gain/Q to it, then verify the 48k render tracks the")
        print("96k truth to within a small tolerance through ~14k.")


if __name__ == "__main__":
    main()
