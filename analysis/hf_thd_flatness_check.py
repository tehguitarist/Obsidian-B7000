#!/usr/bin/env python3
"""Is the plugin's LEVEL- and DRIVE-INDEPENDENT HF THD real, or an estimator artefact?

Uses an INDEPENDENT estimator (discrete-tone THD via plain harmonic binning) to
cross-validate the Farina swept-THD method. The bracket test:

    THD_sweep(-18) <= THD_tone(-14) <= THD_sweep(-12)

Run from repo root:
    python3 analysis/hf_thd_flatness_check.py [--os 8]
"""
import os
import sys
import argparse
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import analyze as A
import captures as C

DEFAULT_BIN = C.RENDER_BIN
TONE_HZ = (2000.0, 4000.0)
SWEEPS = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")


def sweep_thd(al, ref, hz):
    fr, thd, _ = A.harmonic_thd_curve(al, ref, max_order=7)
    return float(thd[int(np.argmin(np.abs(fr - hz)))])


def tone_thd(sig, hz):
    return float(A.thd(sig, hz)[0])


def render(parsed, extra, orig, osf):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    args = C.render_args(parsed, extra_args=extra)
    r = subprocess.run(
        [DEFAULT_BIN, A.ORIG, tmp.name, "--os", str(osf)] + args,
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        os.unlink(tmp.name)
        return None
    try:
        al, _ = A.align(A.load(tmp.name), orig)
    finally:
        os.unlink(tmp.name)
    return al


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--os", type=int, default=8)
    a = ap.parse_args()

    if not os.path.exists(DEFAULT_BIN):
        sys.exit(f"OfflineRender not found at {DEFAULT_BIN} — check RENDER_BIN in captures.py")

    orig = A.load(A.ORIG)
    ref = A.seg_of(orig, "sweep_clean")

    caps = [
        (p, q)
        for p, q in C.find_captures()
        if A.is_full_length(C.load_capture(p), orig)
    ]
    caps.sort(key=lambda pq: (pq[1].get("rev"), -float(pq[1].get("drive", 0))))

    print(f"HF THD flatness -- Farina sweep vs INDEPENDENT tone estimator (OS={a.os}x)")
    print("bracket: sweep(-18) <= tone(-14) <= sweep(-12).  WIDTH = sweep(-12) - sweep(-18).")
    print("a narrow WIDTH means the bracket is trivially satisfiable => 'ok' proves little.\n")

    for hz in TONE_HZ:
        print(f"--- {hz:.0f} Hz " + "-" * 62)
        print(f"  {'capture':<22} {'who':<6} {'swp-18':>8} {'swp-12':>8} {'swp-6':>8} "
              f"{'tone-14':>8} {'width':>7}  verdict")
        for path, parsed in caps:
            cap = C.load_capture(path)
            cal, _ = A.align(cap, orig)
            al = render(parsed, [], orig, a.os)
            if al is None:
                continue
            label = (
                f"{parsed.get('rev')} D{float(parsed.get('drive',0)):.2f}"
                f" BL{float(parsed.get('blend',1)):.2f}"
            )
            for who, sig in (("pedal", cal), ("plug", al)):
                s = [sweep_thd(A.seg_of(sig, sg), ref, hz) for sg in SWEEPS]
                seg = A.seg_of(sig, f"tone_{hz:.0f}")
                t = tone_thd(seg, hz) if seg is not None and len(seg) else float("nan")
                width = s[1] - s[0]
                near = min(abs(t - s[0]), abs(t - s[1])) if np.isfinite(t) else float("nan")
                if not np.isfinite(t):
                    v = "no tone segment"
                else:
                    agree = near <= max(0.15, 0.10 * max(s[0], s[1]))
                    v = ("AGREE" if agree else "DISAGREE") + f" (|tone-sweep|={near:.2f}pp)"
                    if not (s[0] <= t <= s[1]):
                        v += "; non-monotonic in level" if agree else "; ordering also fails"
                print(f"  {label:<22} {who:<6} {s[0]:>8.2f} {s[1]:>8.2f} {s[2]:>8.2f} "
                      f"{t:>8.2f} {width:>7.2f}  {v}")
        print()

    print("READ: AGREE on the plugin rows => the flat HF THD is REAL, not an estimator artefact, and")
    print("may be used as evidence. DISAGREE => the Farina reading is suspect at that anchor.")
    print("'non-monotonic in level' is a statement about the CIRCUIT, not about the estimator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
