#!/usr/bin/env python3.11
"""GATE X — does 1st-order ADAA on the CD4049 VTC reduce the realtime alias floor?

Session 123. Phase 10 B's head item (`CLAUDE.md` open work item 1, re-scoped in session 121 to
the 2x/4x REALTIME floor rather than the 8x render floor, which `rtsafe` already took to -61 dB).

WHY THIS GATE EXISTS AT ALL — a premise had to fall first
---------------------------------------------------------
Three source files asserted, from session 6 to 122, that memoryless ADAA "does not apply" to this
stage because the VTC "lives inside an implicit RC-coupled shunt-feedback loop ... it is NOT a
memoryless function of one input" (`PedalChain.h`'s anti-aliasing block; `FitParams.h` clipK). That
conflates the STAGE with the NONLINEARITY. ADAA1 needs only a memoryless map whose ARGUMENT is
~linear between samples; `vtc` is a memoryless map from node W, and W is an ordinary signal inside
the discretisation. `Clipper::setADAA` carries the full argument and the self-consistency point
(node-W KCL makes W a LINEAR combination of x and y, so substituting the averaged value INSIDE the
solve antialiases W too, at no extra cost).

⚠⚠ THE ARM STRUCTURE IS THE WHOLE DESIGN, AND IT IS NOT OPTIONAL
----------------------------------------------------------------
`sigma_k`'s primitive is elementary only at k = 2 (it is an incomplete beta function otherwise), so
`Clipper::adaaExact()` gates ADAA on `clipK == 2.0` and the SHIPPED `clipK = 2.4653` gets NO ADAA.
⇒ every ADAA reading here is taken at k = 2, which is **a different model from the shipped one**.
So the gate reports THREE things separately and refuses to mix them:

  (A) `k2_off` vs `ship_off`  — what re-anchoring k to its ADAA anchor costs/buys ON ITS OWN.
  (B) `k2_res` / `k2_full` vs `k2_off` — what ADAA buys, quoted against its OWN baseline.
  (C) the shipped build, unchanged, as the epoch anchor.

Quoting (B) against `ship_off` would be `verify-the-BASELINE-not-its-LABEL`: it would credit ADAA
with the k-change too. The gate computes deltas only within a matched k and says so in the output.

SUB-GATES (all computed; the script exits non-zero only on an INSTRUMENT failure, never on how the
physics comes out — `hard-exit-on-the-gate's-own-validity`, s108 P5)
  X1  KNOWN ANSWER — this file's render wrapper with `extra_fit=[]` must reproduce
      `alias_gate.render_sine` BIT-IDENTICALLY. That is what licenses the copy; without it the
      whole gate is measuring an unvalidated renderer.
  X2  MUTATION / INERTNESS — at k = 2 the flag must CHANGE the render (a flag that never reaches
      the stage reads as "ADAA bought nothing"), and at the shipped k it must NOT (the documented
      `adaaExact()` gate, verified rather than assumed).
  X3  HEADLINE — alias floor vs OS factor x amplitude, all four arms.
  X4  COST — harmonic power and H2/H3 per arm, ABSOLUTE, printed beside every ratio
      (`print both operands beside every ratio`, s102 J10). `alias_db` is normalised on harmonic
      power, so a drop cannot come from the output merely getting quieter — but it CAN come from
      the wanted distortion changing, and that has to be visible rather than argued.
  X5  DIRECTION — the claim is that ADAA's payoff is largest where oversampling is weakest. That is
      a parameter-free ordering (benefit must fall as OS rises), so it is checked, not asserted.

Usage:
  python3.11 analysis/clip_adaa_gate.py --run [--json analysis/reports/s123_clip_adaa.json]
  python3.11 analysis/clip_adaa_gate.py --selftest      (X1 + X2 only, ~4 renders)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import alias_gate as AG  # noqa: E402  the validated instrument — do NOT re-derive the metric
from parallel import pmap, add_jobs_arg  # noqa: E402

SHIPPED_K = 2.4653   # FitParams::clipK (session-44 A5 re-fit)
ANCHOR_K = 2.0       # the ADAA anchor (Clipper::kHardness)

# amp 0.35 / 0.70 are session 121's own quoted realtime exposure points.
AMPS = [0.35, 0.70]
FACTORS = [1, 2, 4, 8]

# (label, clipK, clipAdaa) -- `ship_off` is the epoch anchor, the other three share k = 2.
ARMS = [
    ("ship_off", SHIPPED_K, 0),
    ("k2_off", ANCHOR_K, 0),
    ("k2_full", ANCHOR_K, 1),
    ("k2_res", ANCHOR_K, 2),
]


# ---------------------------------------------------------------------------
# Render — a copy of alias_gate.render_sine with an extra_fit passthrough.
#
# It is a COPY on purpose: alias_gate is a validated instrument that three sessions quote from, and
# widening its signature to thread a parameter it does not need would put those quotes at risk. X1
# is what makes the copy safe -- with extra_fit=[] it must be bit-identical to the original.
# ---------------------------------------------------------------------------
def render_sine_ex(amp, os_factor, extra_fit=(), satneg=AG.SHIPPED_SATNEG,
                   fs=AG.FS, k=AG.K_BIN, n=AG.M, settle_s=AG.SETTLE_S_NEW,
                   drive=0.85, tmpdir=None, keep=None):
    period = n / k
    settle = int(np.ceil(settle_s * fs / n)) * n
    total = settle + n + 4096
    t = np.arange(total)
    x = (amp * np.sin(2.0 * np.pi * t / period)).astype(np.float32)

    own_tmp = tmpdir is None
    tmpdir = tmpdir or tempfile.mkdtemp(prefix="clip_adaa_")
    tag = f"a{amp}_os{os_factor}_sn{satneg}_x{'_'.join(extra_fit).replace('=', '')}"
    inp = os.path.join(tmpdir, f"in_{tag}.wav")
    outp = keep or os.path.join(tmpdir, f"out_{tag}.wav")
    wavfile.write(inp, int(fs), x)

    cmd = [AG.RENDER_BIN, "--in", inp, "--out", outp,
           "--os", str(os_factor), "--input-ref", "1", "--output-makeup", "1",
           "--blend", "1", "--level", "1", "--drive", str(drive), "--master", "1",
           "--fit", f"jfetSatNeg={satneg}"]
    for e in extra_fit:
        cmd += ["--fit", e]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"OfflineRender failed: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    sr, y = wavfile.read(outp)
    assert sr == int(fs), (sr, fs)
    y = np.asarray(y, dtype=float)
    if y.ndim > 1:
        y = y[:, 0]
    if own_tmp and keep is None:
        for p in (inp, outp):
            try:
                os.remove(p)
            except OSError:
                pass
    return y[settle:settle + n]


def arm_fit(clip_k, adaa):
    """The --fit list for an arm. clipK is ALWAYS passed, even at the shipped value, so every arm
    goes down an identical code path and an arm difference can never be 'one arm took a default'."""
    return (f"clipK={clip_k}", f"clipAdaa={adaa}")


# ---------------------------------------------------------------------------
# X1 / X2 — the instrument gates
# ---------------------------------------------------------------------------
def gate_x1():
    """The copied renderer must reproduce the validated one exactly at extra_fit=[]."""
    print("\n  X1  KNOWN ANSWER — copied renderer vs alias_gate.render_sine")
    ok = True
    for amp, fac in ((0.35, 2), (0.70, 8)):
        a = AG.render_sine(amp, fac, AG.SHIPPED_SATNEG, settle_s=AG.SETTLE_S_NEW)
        b = render_sine_ex(amp, fac, extra_fit=())
        same = (len(a) == len(b)) and bool(np.array_equal(a, b))
        worst = 0.0 if same else float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
        print(f"      amp {amp}  os {fac}x : {'BIT-IDENTICAL' if same else f'DIFFER (worst {worst:.3e})'}")
        ok = ok and same
    if not ok:
        sys.exit("X1 FAILED: the render wrapper is not the validated one — nothing below is "
                 "attributable to the model. Fix the wrapper, do not reinterpret the numbers.")
    return {"bit_identical": True}


def gate_x2():
    """The flag must be live at k = 2 and inert at the shipped k. BOTH directions are required:
    the first rules out a dead flag, the second verifies adaaExact()'s documented gating."""
    print("\n  X2  MUTATION / INERTNESS — is the flag live where it should be, dead where it should be?")
    out = {}
    ok = True
    for label, clip_k, want_change in (("k2", ANCHOR_K, True), ("shippedK", SHIPPED_K, False)):
        off = render_sine_ex(0.70, 2, extra_fit=arm_fit(clip_k, 0))
        res = render_sine_ex(0.70, 2, extra_fit=arm_fit(clip_k, 2))
        changed = not bool(np.array_equal(off, res))
        worst = float(np.max(np.abs(off - res)))
        verdict = "OK" if changed == want_change else "*** GATE DEAD ***"
        print(f"      clipK={clip_k:<7} adaa 2 vs 0: "
              f"{'CHANGED' if changed else 'identical'}  worst {worst:.3e}   "
              f"(expected {'change' if want_change else 'no change'})  {verdict}")
        out[label] = {"changed": changed, "worst_abs": worst, "expected_change": want_change}
        ok = ok and (changed == want_change)
    if not ok:
        sys.exit("X2 FAILED: either the ADAA flag never reaches the stage (so an 'ADAA bought "
                 "nothing' reading would be vacuous), or adaaExact() is not gating on clipK as "
                 "documented (so the shipped build is not the build that was measured).")
    return out


# ---------------------------------------------------------------------------
# X3 / X4 — the measurement
# ---------------------------------------------------------------------------
def harmonic_terms(y, k=AG.K_BIN, n=AG.M):
    """Absolute harmonic powers, so the ratio in `alias_db` always has its operands beside it."""
    mag = np.abs(np.fft.rfft(np.asarray(y[:n], dtype=float)))
    e = mag ** 2
    nb = len(mag)
    orders = {}
    o = 1
    tot = 0.0
    while o * k < nb:
        orders[o] = float(e[o * k])
        tot += e[o * k]
        o += 1
    h1 = orders.get(1, 0.0) + 1e-300
    return {
        "h_pow_db": float(10.0 * np.log10(tot + 1e-300)),
        "h1_db": float(10.0 * np.log10(h1)),
        "h2_re_h1_db": float(10.0 * np.log10((orders.get(2, 0.0) + 1e-300) / h1)),
        "h3_re_h1_db": float(10.0 * np.log10((orders.get(3, 0.0) + 1e-300) / h1)),
    }


def _one(job):
    label, clip_k, adaa, amp, fac = job
    y = render_sine_ex(amp, fac, extra_fit=arm_fit(clip_k, adaa))
    r = AG.strip(AG.metric_new(y))
    r.update(harmonic_terms(y))
    r.update({"arm": label, "clipK": clip_k, "clipAdaa": adaa, "amp": amp, "os": fac})
    return r


def run(jobs=None):
    grid = [(lab, ck, ad, a, f)
            for (lab, ck, ad) in ARMS for a in AMPS for f in FACTORS]
    return pmap(_one, grid, jobs=jobs)


def report(rows):
    by = {(r["arm"], r["amp"], r["os"]): r for r in rows}
    labels = [a[0] for a in ARMS]

    print("\n  X3  HEADLINE — alias/signal floor (dB, lower is better; inharmonic re harmonic)")
    print("      ⚠ `k2_*` arms are a DIFFERENT MODEL from `ship_off` (clipK 2.4653 -> 2.0).")
    print("        ADAA is credited only against `k2_off`; the k-change is its own column.")
    for amp in AMPS:
        print(f"\n      amp {amp}")
        print("        os |  " + "  ".join(f"{l:>9}" for l in labels)
              + "  ||  dADAA_res  dADAA_full |   dK(k2_off-ship)")
        for fac in FACTORS:
            cells = [by[(l, amp, fac)]["alias_db"] for l in labels]
            d_res = by[("k2_res", amp, fac)]["alias_db"] - by[("k2_off", amp, fac)]["alias_db"]
            d_full = by[("k2_full", amp, fac)]["alias_db"] - by[("k2_off", amp, fac)]["alias_db"]
            d_k = by[("k2_off", amp, fac)]["alias_db"] - by[("ship_off", amp, fac)]["alias_db"]
            print(f"        {fac}x |  " + "  ".join(f"{c:>9.2f}" for c in cells)
                  + f"  ||  {d_res:>+9.2f}  {d_full:>+9.2f} |   {d_k:>+9.2f}")

    print("\n  X4  COST — the operands behind the ratio, and the wanted distortion")
    print("      (h_pow = total harmonic power, dB re unity; H2/H3 re H1)")
    for amp in AMPS:
        for fac in FACTORS:
            print(f"\n      amp {amp}  os {fac}x")
            print("        arm       |   h_pow |     H1  |  H2/H1  |  H3/H1  |  alias  |   lf")
            for l in labels:
                r = by[(l, amp, fac)]
                print(f"        {l:<9} | {r['h_pow_db']:>7.2f} | {r['h1_db']:>7.2f} | "
                      f"{r['h2_re_h1_db']:>7.2f} | {r['h3_re_h1_db']:>7.2f} | "
                      f"{r['alias_db']:>7.2f} | {r['lf_db']:>7.2f}")

    print("\n  X5  DIRECTION — is ADAA's benefit largest where oversampling is weakest?")
    print("      Parameter-free ordering: |benefit| should DECREASE as the OS factor rises.")
    verdicts = {}
    for amp in AMPS:
        ben = [by[("k2_res", amp, f)]["alias_db"] - by[("k2_off", amp, f)]["alias_db"]
               for f in FACTORS]
        mono = all(ben[i] <= ben[i + 1] + 1e-9 for i in range(len(ben) - 1))
        print(f"      amp {amp}: benefit by OS " + " ".join(f"{f}x {b:+.2f}" for f, b in zip(FACTORS, ben))
              + f"   -> {'monotone (as claimed)' if mono else 'NOT monotone — say so, do not round off'}")
        verdicts[amp] = {"benefit_by_os": ben, "monotone": bool(mono)}
    return verdicts


# ---------------------------------------------------------------------------
# X6 — the f0 sweep. THE HEADLINE CANNOT BE QUOTED WITHOUT THIS.
#
# X3 is n = 1 in frequency: one tone at f0 = 2499.02 Hz. The alias floor is strongly f0-dependent
# (OSValidationTest's own header: -85...-115 dB below 1.5 kHz, collapsing to -17...-26 dB above
# 2.3 kHz), and session 121 measured that the SIGN of a change is not uniform across tones even
# when its median is ("the median/worst over the full 21-tone sweep is the number to quote, not any
# single tone"). So the ADAA verdict is a median + worst + improved-fraction over AG.SWEEP_KS, and
# X3's single tone is demoted to an illustration.
#
# ⚠ AG.SWEEP_KS contains DEGENERATE tones by construction — a fundamental that exactly divides fs
# puts every harmonic AND every fold on a harmonic bin, so inharmonic content is impossible and the
# cell reads ~-200 dB (alias_gate's own note: "flag them, don't average them"). They are detected
# from the reading, not from a hardcoded list, and excluded from the statistics with the count
# printed.
DEGENERATE_DB = -150.0


def _one_sweep(job):
    label, clip_k, adaa, amp, fac, kbin = job
    y = render_sine_ex(amp, fac, extra_fit=arm_fit(clip_k, adaa), k=kbin)
    m = AG.metric_new(y, k=kbin)
    return {"arm": label, "clipK": clip_k, "clipAdaa": adaa, "amp": amp, "os": fac,
            "kbin": kbin, "f0": kbin * AG.FS / AG.M, "alias_db": m["alias_db"],
            "lf_db": m["lf_db"], **harmonic_terms(y, k=kbin)}


def f0sweep(jobs=None, amps=(0.35, 0.70), factors=(1, 2, 4, 8)):
    arms = [a for a in ARMS if a[0] in ("k2_off", "k2_full")]
    grid = [(lab, ck, ad, a, f, kb)
            for (lab, ck, ad) in arms for a in amps for f in factors for kb in AG.SWEEP_KS]
    return pmap(_one_sweep, grid, jobs=jobs)


def report_f0sweep(rows, amps=(0.35, 0.70), factors=(1, 2, 4, 8)):
    by = {(r["arm"], r["amp"], r["os"], r["kbin"]): r for r in rows}
    print(f"\n  X6  f0 SWEEP — ADAA (Full) vs its own k=2 baseline over {len(AG.SWEEP_KS)} bin-exact tones")
    print("      benefit < 0 = ADAA IMPROVES the alias floor. Median/worst/improved-fraction are")
    print("      the quotable statistics; a single tone is not (s121).")
    out = {}
    for amp in amps:
        print(f"\n      amp {amp}")
        print("        os |     n | degen |  median |    p90  |   best  |  worst  | improved")
        for fac in factors:
            ben, ndeg = [], 0
            for kb in AG.SWEEP_KS:
                off = by[("k2_off", amp, fac, kb)]["alias_db"]
                full = by[("k2_full", amp, fac, kb)]["alias_db"]
                if off < DEGENERATE_DB or full < DEGENERATE_DB:
                    ndeg += 1
                    continue
                ben.append(full - off)
            b = np.array(ben)
            frac = float((b < 0).mean())
            print(f"        {fac}x | {len(b):>5} | {ndeg:>5} | {np.median(b):>+7.2f} | "
                  f"{np.percentile(b, 90):>+7.2f} | {b.min():>+7.2f} | {b.max():>+7.2f} | "
                  f"{frac * 100:>5.1f}% ({int((b < 0).sum())}/{len(b)})")
            out[f"amp{amp}_os{fac}"] = {
                "n": int(len(b)), "degenerate": ndeg, "median": float(np.median(b)),
                "p90": float(np.percentile(b, 90)), "best": float(b.min()),
                "worst": float(b.max()), "improved_frac": frac}
    print("\n      ⚠ Read the `worst` column: a median that improves while `worst` is positive means")
    print("        ADAA costs at SOME fundamentals. That is a real, per-tone cost, not scatter.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="X1 + X2 + the full X3/X4/X5 measurement")
    ap.add_argument("--selftest", action="store_true", help="X1 + X2 only")
    ap.add_argument("--f0sweep", action="store_true",
                    help="X6: the 21-tone f0 sweep — REQUIRED before quoting any ADAA number")
    ap.add_argument("--json", default=None)
    add_jobs_arg(ap)
    a = ap.parse_args()
    if not (a.run or a.selftest or a.f0sweep):
        ap.error("pick --run / --selftest / --f0sweep")

    if not os.path.exists(AG.RENDER_BIN):
        sys.exit(f"OfflineRender not built: {AG.RENDER_BIN}")

    print(f"  geometry (inherited from alias_gate): fs = {AG.FS:.0f}  M = {AG.M}  "
          f"K = {AG.K_BIN}  f0 = {AG.F0:.4f} Hz")
    print(f"  arms: " + ", ".join(f"{l}(k={k}, adaa={d})" for l, k, d in ARMS))

    out = {"x1": gate_x1(), "x2": gate_x2()}
    if a.selftest and not (a.run or a.f0sweep):
        print("\n  X1 + X2 PASS — the instrument is valid; run --run for the measurement.")
    if a.run:
        rows = run(jobs=a.jobs)
        out["x5"] = report(rows)
        out["rows"] = rows
    if a.f0sweep:
        srows = f0sweep(jobs=a.jobs)
        out["x6"] = report_f0sweep(srows)
        out["sweep_rows"] = srows
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"\n  wrote {a.json}")


if __name__ == "__main__":
    main()
