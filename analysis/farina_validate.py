#!/usr/bin/env python3
"""M-1: Validate the Farina continuous-THD curve against the discrete-tone THD.

analyze.harmonic_thd_curve's own docstring says "VALIDATE against discrete-tone
thd() before trusting it". This validation uses a bracket test immune to level
mismatch: the tones are at -14 dBFS, the sweeps at -18 and -12, so

    THD_farina(-18) <= THD_tone(-14) <= THD_farina(-12)

must hold (monotonic-in-level, obeyed by every clip mechanism here).

Run from repo root:
    python3 analysis/farina_validate.py [--rev V1] [--os 8] [--bin PATH]
"""
import os
import sys
import argparse
import tempfile
import subprocess

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
import gen_test_signal as G
import captures as C

DEFAULT_BIN = C.RENDER_BIN
TONE_FREQS = G.TONE_FREQS
BRACKET_LO, BRACKET_HI = "sweep_drv_-18", "sweep_drv_-12"
TONE_DB = -14.0


def render_plugin(binpath, args, out_path, os_factor):
    cmd = [binpath, A.ORIG, out_path, "--os", str(os_factor)] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(f"  ! render failed: {r.stderr.strip() or r.stdout.strip()}\n")
        return False
    return True


def farina_at(sig, ref, freqs, max_order=7):
    fr, thd, _ = A.harmonic_thd_curve(sig, ref, max_order=max_order)
    return [float(np.interp(f, fr, thd)) for f in freqs]


def tone_thd(al, f):
    try:
        val, _ = A.thd(A.seg_of(al, f"tone_{f:g}"), f)
        return float(val)
    except Exception as e:
        sys.stderr.write(f"  ! tone_{f:g} failed: {e}\n")
        return None


def verdict(lo, tone, hi):
    if tone is None:
        return "no-tone"
    a, b = min(lo, hi), max(lo, hi)
    slack = max(0.3, 0.15 * max(abs(a), abs(b)))
    if a - slack <= tone <= b + slack:
        return "OK"
    return "FAIL"


def analyse_capture(path, parsed, orig, binpath, os_factor):
    cap = C.load_capture(path)
    if not A.is_full_length(cap, orig):
        sys.stderr.write(f"  ! SKIP (truncated): {os.path.basename(path)}\n")
        return None
    cap_al, _ = A.align(cap, orig)

    args = C.render_args(parsed)
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "ren.wav")
        if not render_plugin(binpath, args, out, os_factor):
            return None
        ren, _ = A.align(A.load(out), orig)

    ref = A.seg_of(orig, "sweep_clean")
    rows = []
    for who, sig in (("pedal", cap_al), ("plugin", ren)):
        lo = farina_at(A.seg_of(sig, BRACKET_LO), ref, TONE_FREQS)
        hi = farina_at(A.seg_of(sig, BRACKET_HI), ref, TONE_FREQS)
        tones = [tone_thd(sig, f) for f in TONE_FREQS]
        rows.append((who, lo, tones, hi))
    return rows


def probe_orders(path, parsed, orig, binpath, os_factor, f_lo=2000.0, f_hi=4600.0):
    cap = C.load_capture(path)
    if not A.is_full_length(cap, orig):
        return
    args = C.render_args(parsed)
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "ren.wav")
        if not render_plugin(binpath, args, out, os_factor):
            return
        ren, _ = A.align(A.load(out), orig)

    ref = A.seg_of(orig, "sweep_clean")
    fr, thd, Hn = A.harmonic_thd_curve(A.seg_of(ren, BRACKET_LO), ref, max_order=7)
    H1 = Hn[1]
    cid = f"{parsed.get('rev')} D{parsed.get('drive',0):.2f} BL{parsed.get('blend',0):.2f}"
    print(f"--- ORDER PROBE (plugin, {cid}, {BRACKET_LO}) ---")
    print("per-order dB re fundamental; 'lim' marks the first order whose N*f exceeds each limit")
    print(f"{'freq':>7}{'THD%':>8}" + "".join(f"{'H'+str(o):>8}" for o in range(2, 8)) + "   N*f>20k  N*f>24k")
    freqs = [2000, 2200, 2400, 2560, 2700, 2800, 2857, 2874, 2900, 3000, 3200, 3429, 3600, 4000, 4400]
    for f in freqs:
        t = float(np.interp(f, fr, thd))
        row = f"{f:>7.0f}{t:>8.2f}"
        for o in range(2, 8):
            h = float(np.interp(f, fr, Hn[o]))
            h1 = float(np.interp(f, fr, H1))
            row += f"{20*np.log10(h/(h1+1e-20)+1e-20):>8.1f}"
        n20 = next((o for o in range(2, 8) if o * f > G.SWEEP_F1), None)
        n24 = next((o for o in range(2, 8) if o * f > A.FS / 2), None)
        row += f"{('H'+str(n20)) if n20 else '-':>10}{('H'+str(n24)) if n24 else '-':>9}"
        print(row)
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="dump per-order magnitudes across the ceiling region")
    ap.add_argument("--rev", default=None, help="only captures of this revision (regex matched against rev field)")
    ap.add_argument("--os", type=int, default=8)
    ap.add_argument("--bin", default=DEFAULT_BIN)
    ap.add_argument("--limit", type=int, default=3)
    a = ap.parse_args()

    if not os.path.exists(a.bin):
        sys.exit(f"OfflineRender not found at {a.bin} — check RENDER_BIN in captures.py or set --bin")

    orig = A.load(A.ORIG)
    caps = C.find_captures()
    if a.rev:
        caps = [(p, q) for p, q in caps if q.get("rev") and a.rev.lower() in q["rev"].lower()]
    caps = caps[: a.limit]
    if not caps:
        sys.exit("no captures matched")

    if a.probe:
        for path, parsed in caps:
            probe_orders(path, parsed, orig, a.bin, a.os)
        return

    print("M-1 FARINA VALIDATION — bracket test")
    print(f"  tone level {TONE_DB:+.0f} dBFS must sit between Farina@{BRACKET_LO[-3:]} and Farina@{BRACKET_HI[-3:]}")
    print(f"  OS={a.os}x   max_order=7")
    print(f"  order-7 aliases above {A.FS/(2*7):.0f} Hz — bands near/above that are the suspects\n")

    fails = []
    for path, parsed in caps:
        rows = analyse_capture(path, parsed, orig, a.bin, a.os)
        if rows is None:
            continue
        cid = f"{parsed.get('rev')} D{parsed.get('drive', 0):.2f} BL{parsed.get('blend', 0):.2f}"
        print(f"--- {cid} ---")
        print(f"{'freq':>7} {'who':>7} {'far@-18':>9} {'tone@-14':>9} {'far@-12':>9}  verdict")
        for who, lo, tones, hi in rows:
            for f, l, t, h in zip(TONE_FREQS, lo, tones, hi):
                v = verdict(l, t, h)
                ts = f"{t:9.2f}" if t is not None else f"{'-':>9}"
                mark = "" if v == "OK" else "  <<<"
                print(f"{f:7.0f} {who:>7} {l:9.2f} {ts} {h:9.2f}  {v}{mark}")
                if v == "FAIL":
                    fails.append((cid, who, f, l, t, h))
        print()

    print("=" * 72)
    if not fails:
        print("All tones fall inside their Farina bracket — the curve is trustworthy at the tone freqs.")
    else:
        print(f"{len(fails)} bracket FAILURES — Farina disagrees with the discrete tones here:")
        for cid, who, f, l, t, h in fails:
            print(f"  {cid:<22} {who:>6} @{f:6.0f} Hz: bracket [{min(l,h):.2f}, {max(l,h):.2f}] vs tone {t:.2f}")
        print("\nA failure at/above ~2 kHz convicts the 3000 Hz ceiling; the fix is to lower the")
        print("ceiling to the highest PASSING tone, and/or use order-limiting (M-2).")


if __name__ == "__main__":
    main()
