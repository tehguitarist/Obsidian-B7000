#!/usr/bin/env python3.11
"""Does the PLUGIN'S CLEAN path (DIST off / distEngage=False) carry harmonics the real pedal's
clean output doesn't?

User question (2026-07-27): "even the clean captures (distortion off) has some THD and harmonics
that the pedal doesn't." This script checks it directly rather than trusting the impression.

Method: for a representative set of real `*_base-clean*.wav` / `ref-clean*.wav` captures, render
the SAME conditions through OfflineRender (current shipped defaults, no --fit overrides), align
both to the reference test signal, and compare per-tone discrete-harmonic content at every
TONE_FREQS segment (82-8000 Hz, embedded in every capture) plus cal_1k. Reports:
  - guarded THD% (tone_thd_nyquist_check.py's Nyquist-safe estimator) for pedal vs plugin
  - per-harmonic dB re fundamental (H2..H5) for both, plus the DELTA (plugin - pedal)
A capture's own measurement noise floor is estimated from a silent stretch (segment "cal_1k"'s
pre-roll is not isolated silence in this signal, so we instead report the pedal's OWN H2..H5 in
the analogous FLAT/no-signal-adjacent cal_1k tone as a sanity low bound, and flag deltas that
clear that floor by a healthy margin).

Run: /opt/homebrew/bin/python3.11 analysis/clean_thd_check.py
"""
import sys, os, subprocess, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import captures as C

FS = A.FS
BIN = C.RENDER_BIN
CAP_DIR = "analysis/captures"

TONES = [82.41, 110, 220, 440, 1000, 2000, 4000, 8000]

# Representative clean-set captures: flat reference + a spread of EQ deviations, incl. the
# hottest boost positions (most likely to expose rail-clamp / headroom differences).
CANDIDATES = [
    "ref-clean.wav",
    "bass-1700_gain-n12_base-clean.wav",
    "treble-1700_gain-n12_base-clean.wav",
    "lomid-1700_gain-n12_base-clean.wav",
    "himid-1700_gain-n12_base-clean.wav",
    "master-1700_gain-n12_base-clean.wav",
    "bass-0930_base-clean.wav",
    "treble-0930_base-clean.wav",
]


def render_plugin(parsed, out_path):
    args = [BIN, "analysis/test_signal_48k.wav", out_path, "--os", "8"] + C.render_args(parsed)
    subprocess.run(args, check=True, capture_output=True)


NYQ = FS / 2.0
MARGIN = 0.95


def harmonics_db(x, f0, max_order=6):
    """Per-harmonic level re fundamental (dB), Nyquist-guarded, near-bin-peak amplitude."""
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft(x * w))
    fr = np.fft.rfftfreq(len(x), 1 / FS)

    def amp(fc):
        i = int(np.argmin(np.abs(fr - fc)))
        return np.max(X[max(0, i - 3): i + 4])

    fund = amp(f0)
    out = {}
    for k in range(2, max_order + 1):
        if f0 * k > NYQ * MARGIN:
            break
        out[k] = 20 * np.log10(amp(f0 * k) / (fund + 1e-20) + 1e-20)
    thd_pct = 100 * np.sqrt(sum((10 ** (v / 20)) ** 2 for v in out.values())) if out else 0.0
    return out, thd_pct


def main():
    orig = A.load(A.ORIG)
    tmp = tempfile.mkdtemp(prefix="clean_thd_")
    print(f"{'capture':<38}{'segment':>7}  {'ped THD%':>9} {'plg THD%':>9}  {'H2 ped/plg':>12}  "
          f"{'H3 ped/plg':>12}  {'delta(worst harm)':>18}")
    print("-" * 128)

    flags = []
    for cap_name in CANDIDATES:
        cap_path = os.path.join(CAP_DIR, cap_name)
        if not os.path.exists(cap_path):
            print(f"  (missing capture: {cap_name}, skipping)")
            continue
        parsed = C.parse_capture(cap_name)
        if not A.is_full_length(C.load_capture(cap_path), orig):
            print(f"  (short/truncated capture: {cap_name}, skipping)")
            continue
        ped, lag = A.align(C.load_capture(cap_path), orig)

        out_path = os.path.join(tmp, cap_name)
        render_plugin(parsed, out_path)
        plg_raw = A.load(out_path)
        plg, _ = A.align(plg_raw, orig)

        segs_to_check = [(f0, f"tone_{f0:g}") for f0 in TONES] + [(1000.0, "lvl_-3")]
        for f0, segname in segs_to_check:
            ped_seg = A.seg_of(ped, segname)
            plg_seg = A.seg_of(plg, segname)
            ped_h, ped_thd = harmonics_db(ped_seg, f0)
            plg_h, plg_thd = harmonics_db(plg_seg, f0)

            h2p = ped_h.get(2, float("nan"))
            h2q = plg_h.get(2, float("nan"))
            h3p = ped_h.get(3, float("nan"))
            h3q = plg_h.get(3, float("nan"))

            worst_delta = -999
            worst_k = None
            for k in ped_h:
                if k in plg_h:
                    d = plg_h[k] - ped_h[k]
                    if d > worst_delta:
                        worst_delta, worst_k = d, k

            print(f"{cap_name:<38}{segname:>7}  {ped_thd:>9.3f} {plg_thd:>9.3f}  "
                  f"{h2p:>5.1f}/{h2q:>5.1f}  {h3p:>5.1f}/{h3q:>5.1f}  "
                  f"H{worst_k}: {worst_delta:>+7.2f} dB")

            # Flag: plugin genuinely hotter (not just both near the -100dB noise floor) at some
            # harmonic order, by more than a healthy margin.
            if worst_k is not None and worst_delta > 6.0 and plg_h[worst_k] > -80.0:
                flags.append((cap_name, segname, worst_k, ped_h[worst_k], plg_h[worst_k], worst_delta))

    print("\n=== FLAGGED: plugin harmonic clearly hotter than the pedal's own (>6 dB, plugin above -80 dBc) ===")
    if not flags:
        print("  (none)")
    for cap_name, segname, k, pv, qv, d in sorted(flags, key=lambda r: -r[5]):
        print(f"  {cap_name:<38} seg={segname:<10}  H{k}: pedal {pv:+7.2f} dBc  plugin {qv:+7.2f} dBc  "
              f"(+{d:.2f} dB hotter)")


if __name__ == "__main__":
    main()
