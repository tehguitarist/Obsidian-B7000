#!/usr/bin/env python3
"""Is ``analyze.thd()`` (the DISCRETE-TONE estimator) valid at HF?

``A.thd(x, f0)`` sums orders k=2..8 unconditionally.  For harmonics above
Nyquist, ``np.argmin`` clamps to the topmost FFT bin, so every out-of-band
order re-reads the same near-Nyquist bin and adds it to the RSS again:

    f0 = 8000 -> H3 sits exactly at Nyquist; H4..H8 are FIVE re-reads of the edge
    f0 = 4000 -> H7 (28k) and H8 (32k) re-read the edge

If the near-Nyquist bin holds anything at all, THD is inflated by up to sqrt(N)
of it. This script compares guarded (orders limited to Nyquist) vs. unguarded.

Run from repo root:
    python3 analysis/tone_thd_nyquist_check.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import analyze as A
import captures as C

FS = A.FS
NYQ = FS / 2.0
MARGIN = 0.95


def thd_guarded(x, f0, max_order=8):
    """A.thd() with out-of-band orders dropped instead of clamped to the top bin."""
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft(x * w))
    fr = np.fft.rfftfreq(len(x), 1 / FS)

    def amp(fc):
        i = int(np.argmin(np.abs(fr - fc)))
        return np.max(X[max(0, i - 3) : i + 4])

    fund = amp(f0)
    orders = [k for k in range(2, max_order + 1) if k * f0 <= NYQ * MARGIN]
    harm = np.sqrt(sum(amp(f0 * k) ** 2 for k in orders)) if orders else 0.0
    return 100 * harm / (fund + 1e-20), orders


orig = A.load(A.ORIG)
caps = [
    (p, q)
    for p, q in C.find_captures()
    if A.is_full_length(C.load_capture(p), orig)
]

print("Discrete-tone THD: UNGUARDED (shipped A.thd, orders 2..8 clamped) vs NYQUIST-GUARDED")
print(f"  FS={FS:.0f}  Nyquist={NYQ:.0f} Hz  guard: keep order N only while N*f0 <= {NYQ*MARGIN:.0f} Hz")
print()
print(f"  {'capture':<26} {'f0':>6} {'unguard':>8} {'guarded':>8} {'infl':>7}  orders kept")
print("  " + "-" * 78)

worst = []
for p, parsed in caps:
    cal, _ = A.align(C.load_capture(p), orig)
    lbl = f"{parsed.get('rev')} D{float(parsed.get('drive',0)):.2f} BL{float(parsed.get('blend',1)):.2f}"
    for f0 in (2000, 4000, 8000):
        seg = A.seg_of(cal, f"tone_{f0:g}")
        u = float(A.thd(seg, f0)[0])
        g, orders = thd_guarded(seg, f0)
        infl = u - g
        worst.append((abs(infl), lbl, f0, u, g))
        print(f"  {lbl:<26} {f0:>6} {u:>8.2f} {g:>8.2f} {infl:>+7.2f}  {orders}")
    print()

print("=== WORST INFLATIONS (percentage points fabricated by out-of-band orders) ===")
for d, lbl, f0, u, g in sorted(worst, reverse=True)[:8]:
    print(f"  {lbl:<26} {f0:>6} Hz: {u:6.2f} -> {g:6.2f}  ({d:+.2f} pp fabricated)")

print("\nAlso check the REFERENCE signal itself (pure synthesised tones -- should be ~0 either way):")
for f0 in (2000, 4000, 8000):
    seg = A.seg_of(orig, f"tone_{f0:g}")
    u = float(A.thd(seg, f0)[0])
    g, orders = thd_guarded(seg, f0)
    print(f"  reference tone_{f0:<5g}: unguarded {u:6.3f}  guarded {g:6.3f}")
