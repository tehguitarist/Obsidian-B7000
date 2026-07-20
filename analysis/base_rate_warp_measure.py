#!/usr/bin/env python3
"""Measure the model's OWN base-rate bilinear top-octave warp.

The target for a calibration high-shelf: render the dry/linear path at base fs
(48k) and at 2x base fs (96k, near-analog reference), compare the clean-sweep
FR. The droop = mag(48k) - mag(96k) is what the shelf should invert.

Run from repo root:
    python3 analysis/base_rate_warp_measure.py \\
        --revs "V1,V2" --dry-args "--blend,0.0" --os 8
"""
import argparse
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "analysis"))
import analyze as A

ANCHORS = (6000, 8000, 10000, 12500, 14500, 16000)


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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bin", default="build/OfflineRender_artefacts/Release/OfflineRender",
                    help="path to OfflineRender binary")
    ap.add_argument("--revs", default="V1",
                    help="comma-separated list of revisions/variants to test")
    ap.add_argument("--dry-args", default="",
                    help="comma-separated extra CLI flags for dry/linear render "
                         "(e.g. '--blend,0.0' for a blend knob to 100% wet bypass)")
    ap.add_argument("--os", type=int, default=8)
    a = ap.parse_args()

    if not os.path.exists(a.bin):
        sys.exit(f"OfflineRender not found at {a.bin}")

    revs = [r.strip() for r in a.revs.split(",") if r.strip()]
    dry_args = a.dry_args.split(",") if a.dry_args else []

    orig48 = A.load(A.ORIG)

    with tempfile.TemporaryDirectory() as tmp:
        # 2x base rate reference input
        in96 = np.zeros(0)
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
        print("=" * 78)
        print(f"{'rev':>4} | " + " ".join(f"{a/1e3:>6.1f}k" for a in ANCHORS))

        droops = {}
        for rev in revs:
            o48 = os.path.join(tmp, f"{rev}_48.wav")
            o96 = os.path.join(tmp, f"{rev}_96.wav")

            cmd48 = [a.bin, p48, o48, "--os", str(a.os), "--rev", rev] + dry_args
            cmd96 = [a.bin, p96, o96, "--os", str(a.os), "--rev", rev] + dry_args

            for cmd, label in [(cmd48, "48k"), (cmd96, "96k")]:
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode != 0:
                    sys.exit(f"render failed ({rev} @ {label}): {r.stderr or r.stdout}")

            _, y48 = wavfile.read(o48)
            _, y96 = wavfile.read(o96)
            if y48.dtype.kind == "i":
                y48 = y48.astype(np.float64) / np.iinfo(y48.dtype).max
            else:
                y48 = y48.astype(np.float64)
            if y96.dtype.kind == "i":
                y96 = y96.astype(np.float64) / np.iinfo(y96.dtype).max
            else:
                y96 = y96.astype(np.float64)
            if y48.ndim > 1:
                y48 = y48[:, 0]
            if y96.ndim > 1:
                y96 = y96[:, 0]

            H48 = transfer_db(y48, orig48, 48000, ANCHORS + (1000,))
            H96 = transfer_db(y96, in96, 96000, ANCHORS + (1000,))
            d = {t: (H48[t] - H48[1000]) - (H96[t] - H96[1000]) for t in ANCHORS}
            droops[rev] = d
            print(f"{rev:>4} | " + " ".join(f"{d[a]:>7.2f}" for a in ANCHORS))

        if len(revs) > 1:
            print("-" * 78)
            med = {a: float(np.median([droops[r][a] for r in revs])) for a in ANCHORS}
            print(f"{'med':>4} | " + " ".join(f"{med[a]:>7.2f}" for a in ANCHORS))

        print("=" * 78)
        print("Shelf should invert ~ the MEDIAN row (a rising high-shelf).")
        print("Fit corner/gain/Q to it, then verify the 48k render tracks the")
        print("96k truth to within a small tolerance through ~14k.")


if __name__ == "__main__":
    main()
