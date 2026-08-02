#!/usr/bin/env python3.11
"""KNOWN-ANSWER GATE for the H1-only Farina frequency-response read (`analyze.transfer_h1`).

Session 90, Phase 9 item 0.  This is the gate that has to pass BEFORE any release-gate number is
re-baselined against the new instrument -- `.claude/rules/measurement-discipline.md` §1: *do not fit
against an instrument you have not validated*.

WHY THE INSTRUMENT NEEDED REPAIRING
-----------------------------------
Every FR number on this project, including the whole Phase 9 release gate, came from
`analyze.transfer()` -- a cross-spectral-density estimate |Pxy|/Pxx.  A CSD rejects content that is
INCOHERENT with the input.  A swept sine's harmonics are not incoherent: H2 of a fundamental one
octave down is a deterministic function of the input, and within an 8192-point Welch segment the
sweep barely moves, so that harmonic lands in the same analysis bin as the fundamental and is
reported as frequency response.  At drive, "the pedal's HF response" and "the pedal's HF distortion"
were therefore not separable by the instrument that measured them -- which is exactly the ambiguity
session 89 hit on the twelve worst OD rows (all at 12901.6 Hz, 26-36 dB).

`analyze.transfer_h1()` separates them by construction instead: after Farina deconvolution the N-th
harmonic response sits dt_N = T*ln(N)/R ahead of the linear response IN TIME (1.00 s for H2 on this
10 s, 20 Hz-20 kHz sweep), so a window around t = 0 narrower than that spacing contains the linear
response and nothing else.

WHAT THIS GATE CHECKS
---------------------
  KA-1  linear recovery      -- a known IIR cascade, no distortion at all.  Both instruments should
                                pass; if the H1 read cannot recover a filter it is simply broken.
  KA-2  harmonic rejection   -- the SAME filter, plus synthesised 2nd- and 3rd-harmonic sweeps at
                                a brutal, flat -10/-14 dB re the UNFILTERED fundamental.  The known
                                answer is unchanged (the added content is exactly orders 2 and 3),
                                so the H1 read must still return the filter.
  KA-3  mutation             -- KA-2's tolerance must REJECT the old instrument.  A gate that both
                                instruments pass proves nothing about the repair; this asserts the
                                CSD's error EXCEEDS the H1 tolerance, so a silent revert to
                                `transfer()` would fail this file rather than pass it.
  KA-4  gate-width sanity    -- the H1 window must be narrower than the H1->H2 spacing.  This is the
                                one assumption the whole separation rests on, and it depends on the
                                sweep length and range in gen_test_signal.py -- so it is asserted
                                against those constants rather than trusted.

`--compare` runs the two instruments against the real captures (no plugin render needed) and reports
where they disagree, per band and per drive level.  That is the measurement session 89 asked for:
it says how much of the recorded FR error was ever frequency response at all.

Run from the repo root:
    python3.11 analysis/h1_fr_gate.py --selftest
    python3.11 analysis/h1_fr_gate.py --compare [--only ref] [--jobs N]
"""
import argparse
import os
import sys

import numpy as np
from scipy import signal as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
import gen_test_signal as G
import captures as C
import matrix_grade as MG
from parallel import pmap_cpu, add_jobs_arg

# The band the release gate is measured over, after session 90 widened it (see matrix_grade).
BANDS = [round(b, 1) for b in A.fractional_octave_freqs(20.0, 20000.0, 3)
         if MG.GRADE_LO - 1e-6 <= b <= MG.GRADE_HI + 1e-6]

# Tolerances.  These are ceilings on the INSTRUMENT's own error against an exactly-known answer;
# they are not accuracy claims about a capture.  Set from the measured self-test residual with
# ~3x headroom, tight enough that the CSD fails KA-2 by an order of magnitude (see KA-3).
TOL_LINEAR_DB = 0.15        # KA-1, either instrument
TOL_HARMONIC_DB = 0.35      # KA-2, H1 read only (KA-3 mutation must EXCEED this)
TOL_NONLINEAR_DB = 0.50     # KA-5 alias-free arm, H1 read only

H2_REL_DB = -10.0           # KA-2 harmonic levels, re the UNFILTERED fundamental -- deliberately
H3_REL_DB = -14.0           # far hotter than anything this pedal produces


# ---- synthetic known-answer signals ----------------------------------------------------------
def sweep_phase(sec=G.SWEEP_SEC, f0=G.SWEEP_F0, f1=G.SWEEP_F1):
    """The exponential sweep's instantaneous phase -- the same expression gen_test_signal.log_sweep
    integrates, so the synthesised harmonics below are EXACTLY orders 2 and 3 of the reference and
    land exactly where the Farina gating expects them."""
    t = np.arange(int(sec * G.FS)) / G.FS
    k = np.log(f1 / f0)
    return 2 * np.pi * f0 * sec / k * (np.exp(t / sec * k) - 1.0)


def known_filter():
    """A deliberately pedal-shaped known answer: 20 Hz 1st-order highpass (C21-ish) into a 3.3 kHz
    2nd-order lowpass (the IC4_A Sallen-Key).  The HF rolloff is the point -- it is what makes the
    CSD's harmonic contamination visible at the top of the band, which is where session 89's twelve
    worst rows sat.  Returned as SOS so both the filtering and the truth come from one object."""
    hp = sps.butter(1, 20.0, btype="highpass", fs=G.FS, output="sos")
    lp = sps.butter(2, 3300.0, btype="lowpass", fs=G.FS, output="sos")
    return np.vstack([hp, lp])


def truth_db(sos, freqs):
    w, h = sps.sosfreqz(sos, worN=np.asarray(freqs, dtype=float), fs=G.FS)
    return 20 * np.log10(np.abs(h) + 1e-20)


def harmonic_sweep(order, amp_db, sec=G.SWEEP_SEC, f0=G.SWEEP_F0):
    """An EXACT N-th harmonic of the reference sweep, band-limited below Nyquist.

    ⚠ The band-limiting is not cosmetic and its absence is what a first draft of this gate got
    wrong. `sin(N*phase)` runs to N*20 kHz, so at 48 kHz H2 aliases above 12 kHz and H3 above
    8 kHz — and ALIASED content is not harmonic, so it does not sit at the N-th gate position and
    contaminates the H1 read by 20+ dB. The test would then have measured aliasing in its own
    stimulus and blamed the instrument. Order N is generated only while N*f(t) <= 0.95*Nyquist,
    with a raised-cosine fade at the truncation so the edge does not splatter."""
    t = np.arange(int(sec * G.FS)) / G.FS
    k = np.log(G.SWEEP_F1 / f0)
    inst_f = order * f0 * np.exp(t / sec * k)
    x = 10 ** (amp_db / 20.0) * np.sin(order * sweep_phase(sec, f0))
    keep = inst_f <= 0.95 * (G.FS / 2.0)
    n_keep = int(np.count_nonzero(keep))
    x[n_keep:] = 0.0
    fade_n = min(int(0.05 * G.FS), n_keep // 2)
    if fade_n > 1:
        x[n_keep - fade_n:n_keep] *= np.linspace(1.0, 0.0, fade_n)
    return G.fade(x, 10.0)


def build_case(with_harmonics):
    """-> (ref, out).  `out` is the reference through known_filter(), optionally plus exact,
    band-limited 2nd and 3rd harmonic sweeps at a flat level re the unfiltered fundamental."""
    ref = G.log_sweep(G.SWEEP_SEC, -30.0)
    sos = known_filter()
    out = sps.sosfilt(sos, ref)
    if with_harmonics:
        out = out.copy()
        for order, rel in ((2, H2_REL_DB), (3, H3_REL_DB)):
            h = harmonic_sweep(order, -30.0 + rel)     # re the reference sweep's own -30 dBFS
            n = min(len(out), len(h))
            out[:n] += h[:n]
    return ref, out


def read_at_bands(fn, out, ref, bands):
    f, mag = fn(out, ref)
    return np.array([float(np.interp(b, f, mag)) for b in bands])


# ---- KA-5: a real static nonlinearity, with an ANALYTIC known answer --------------------------
TANH_DRIVE = 1.6            # peak drive into tanh at 0 dB of the filter -> ~ -2.6 dB compression
KA5_OS = 16                 # oversampling factor for the alias-FREE arm


def tanh_fundamental(amp, n=4096):
    """Exact fundamental amplitude out of tanh(A sin θ): a1 = (2/π)∫₀^π tanh(A sinθ) sinθ dθ.

    This is what makes KA-5 a KNOWN-ANSWER test rather than a plausibility check — the truth comes
    from the nonlinearity's own algebra, not from another instrument. tanh is memoryless, so with a
    slow sweep the instantaneous amplitude A = |H(f)| * drive gives the fundamental at every f."""
    th = (np.arange(n) + 0.5) * np.pi / n
    a = np.asarray(amp, dtype=float)[..., None]
    return (2.0 / np.pi) * np.sum(np.tanh(a * np.sin(th)) * np.sin(th), axis=-1) * (np.pi / n)


def build_nonlinear_case(alias_free, filtered=True):
    """-> (ref, out, truth_db_at_bands) for tanh(drive * x), optionally through known_filter().

    `alias_free=True` runs the nonlinearity at KA5_OS x so its harmonics stay below Nyquist; False
    is the honest 1x case, where order N folds back and — the mechanism this gate exists to expose
    — lands EXACTLY ON THE FUNDAMENTAL at f = FS/(N+1), i.e. 16000 Hz (N=2) and 12000 Hz (N=3).
    Content there is coincident with the fundamental in BOTH time and frequency, so no amount of
    gating or coherence can reject it. That is not an instrument defect; it is a limit of the
    STIMULUS, and it sits right on top of the two highest graded bands (12901.6, 16255 Hz).

    `filtered=False` drops the pre-filter so the drive stays FLAT to 20 kHz. That arm exists
    because the filtered one cannot exercise the fold at all — the 3.3 kHz lowpass leaves ~-22 dB
    at 12 kHz, so tanh is essentially linear there and generates nothing to fold. A pedal-shaped
    chain suppresses its own alias-onto-fundamental; a flat-drive nonlinearity does not."""
    ref = G.log_sweep(G.SWEEP_SEC, -30.0)
    sos = known_filter() if filtered else None
    lin = sps.sosfilt(sos, ref) if filtered else ref
    amp = 10 ** (-30.0 / 20.0)
    if alias_free:
        up = sps.resample_poly(lin, KA5_OS, 1)
        out = sps.resample_poly(np.tanh(TANH_DRIVE / amp * up), 1, KA5_OS)[:len(lin)]
    else:
        out = np.tanh(TANH_DRIVE / amp * lin)
    out = out * amp / TANH_DRIVE                     # undo the drive scaling -> unity at small signal
    lin_db = truth_db(sos, BANDS) if filtered else np.zeros(len(BANDS))
    a_in = TANH_DRIVE * 10 ** (lin_db / 20.0)
    truth = 20 * np.log10(tanh_fundamental(a_in) / TANH_DRIVE + 1e-20)
    return ref, out, truth


# ---- the gate ---------------------------------------------------------------------------------
def selftest(verbose=True):
    sos = known_filter()
    truth = truth_db(sos, BANDS)
    fails = []

    def report(title, err, tol, name, gated=True):
        worst_i = int(np.argmax(np.abs(err)))
        ok = np.max(np.abs(err)) <= tol
        if verbose:
            # Only GATED rows print PASS/FAIL. A reported-only row printing "FAIL" beside an
            # "ALL PASS" verdict is `computed-verdicts-not-narrated` in miniature.
            mark = ("PASS" if ok else "FAIL") if gated else ("report" if ok else "report OVER-TOL")
            print(f"  {title:<34}{name:<10}max |err| {np.max(np.abs(err)):6.3f} dB "
                  f"@ {BANDS[worst_i]:>8.1f} Hz   rms {np.sqrt(np.mean(err ** 2)):5.3f}   "
                  f"[{'tol' if gated else 'ref'} {tol:.2f}]  {mark}")
        return ok, float(np.max(np.abs(err)))

    print(f"\n=== H1 FR instrument — known-answer self-test "
          f"({len(BANDS)} bands, {BANDS[0]:.0f}–{BANDS[-1]:.0f} Hz) ===\n")

    # --- KA-1: pure linear -------------------------------------------------------------------
    ref, out = build_case(with_harmonics=False)
    e_h1 = read_at_bands(A.transfer_h1, out, ref, BANDS) - truth
    e_csd = read_at_bands(A.transfer, out, ref, BANDS) - truth
    ok1a, _ = report("KA-1 linear recovery", e_h1, TOL_LINEAR_DB, "H1")
    ok1b, _ = report("KA-1 linear recovery", e_csd, TOL_LINEAR_DB, "CSD")
    if not ok1a:
        fails.append("KA-1 H1: the H1 read cannot recover a known filter with no distortion present")
    if not ok1b:
        fails.append("KA-1 CSD: the control failed on a purely linear case — suspect the harness, "
                     "not either instrument")

    # --- KA-2: same filter, brutal harmonics -------------------------------------------------
    ref, out = build_case(with_harmonics=True)
    e_h1 = read_at_bands(A.transfer_h1, out, ref, BANDS) - truth
    e_csd = read_at_bands(A.transfer, out, ref, BANDS) - truth
    ok2, _ = report(f"KA-2 harmonics H2{H2_REL_DB:+.0f}/H3{H3_REL_DB:+.0f} dB", e_h1,
                    TOL_HARMONIC_DB, "H1")
    _, csd_worst = report(f"KA-2 harmonics H2{H2_REL_DB:+.0f}/H3{H3_REL_DB:+.0f} dB", e_csd,
                          TOL_HARMONIC_DB, "CSD")
    if not ok2:
        fails.append("KA-2: the H1 read is contaminated by harmonic content — the gating is not "
                     "separating orders, which is the whole premise of transfer_h1")

    # ⭐ REPORTED, NOT GATED, and the single most useful line this file prints. The CSD passes
    # KA-2 too, at its own linear-case error — so on THIS stimulus `transfer()` is not measurably
    # contaminated by harmonic distortion, and session 89's premise (a) does not survive as
    # stated. The reason is that an exponential sweep separates orders IN TIME (~1 s/octave here
    # against a 170 ms Welch window), so the harmonic at bin b and the fundamental at bin b never
    # occupy the same analysis window. See KA-5 for what DOES defeat both instruments.
    print(f"\n  {'CSD-vs-H1 on KA-2':<34}{'':<10}CSD {csd_worst:.3f} dB vs H1 "
          f"{np.max(np.abs(e_h1)):.3f} dB — the CSD is "
          f"{'ALSO CLEAN' if csd_worst <= TOL_HARMONIC_DB else 'CONTAMINATED'} here (reported, "
          f"not gated)")

    # --- KA-3: MUTATION — break the gate, and KA-2 must catch it -------------------------------
    # The honest mutation for KA-2 is not "does the OLD instrument fail" (it does not, see above)
    # but "would this test notice if transfer_h1's separation stopped working". Widening the H1
    # gate past the H1->H2 spacing swallows H2 by construction, so KA-2 must reject it. A gate
    # that cannot fail is `mutation-test-a-guard` (s88) waiting to happen.
    broken = read_at_bands(lambda o, r: A.transfer_h1(o, r, gate_fraction=1.20),
                           out, ref, BANDS) - truth
    broken_worst = float(np.max(np.abs(broken)))
    mutation_ok = broken_worst > TOL_HARMONIC_DB
    print(f"  {'KA-3 mutation (gate 0.35 -> 1.20)':<34}{'H1-broken':<10}"
          f"max |err| {broken_worst:6.3f} dB   (must EXCEED tol {TOL_HARMONIC_DB:.2f})  "
          f"{'PASS' if mutation_ok else 'FAIL'}")
    if not mutation_ok:
        fails.append("KA-3: a deliberately-broken H1 gate (wide enough to contain H2) still passes "
                     "KA-2 — the test does not discriminate and proves nothing about the gating")

    # --- KA-4: the separation assumption itself ----------------------------------------------
    T, R = G.SWEEP_SEC, np.log(G.SWEEP_F1 / G.SWEEP_F0)
    dt2 = T * np.log(2.0) / R
    gate_half = A.H1_GATE_FRACTION * dt2
    width_ok = gate_half < dt2
    print(f"  {'KA-4 gate width':<34}{'':<10}half-gate {gate_half * 1e3:.0f} ms vs H1->H2 "
          f"spacing {dt2 * 1e3:.0f} ms   {'PASS' if width_ok else 'FAIL'}")
    if not width_ok:
        fails.append("KA-4: the H1 gate is WIDER than the H1->H2 spacing — it contains H2 by "
                     "construction and the separation is fictional")

    # --- KA-5: a REAL static nonlinearity, truth from the nonlinearity's own algebra -----------
    print()
    for filtered, alias_free in ((True, True), (True, False), (False, True), (False, False)):
        tag = ("LPF, " if filtered else "flat, ") + ("no alias (16x)" if alias_free else "1x ALIAS")
        ref5, out5, truth5 = build_nonlinear_case(alias_free, filtered)
        e5_h1 = read_at_bands(A.transfer_h1, out5, ref5, BANDS) - truth5
        e5_csd = read_at_bands(A.transfer, out5, ref5, BANDS) - truth5
        ok5a, _ = report(f"KA-5 tanh, {tag}", e5_h1, TOL_NONLINEAR_DB, "H1", gated=alias_free)
        report(f"KA-5 tanh, {tag}", e5_csd, TOL_NONLINEAR_DB, "CSD", gated=alias_free)
        if alias_free and not ok5a:
            fails.append(f"KA-5 ({tag}): the H1 read cannot recover the fundamental of a static "
                         "nonlinearity with aliasing removed — the known answer here is the tanh "
                         "describing function, so this is the instrument, not the stimulus")

    # Where order N folds onto the fundamental: N*f = FS - f. Printed after the flat arms, which
    # are the ones that actually exercise it.
    folds = ", ".join(f"H{n} @ {G.FS / (n + 1.0) / 1000:.1f} kHz" for n in (2, 3, 4))
    print(f"\n  ALIAS FOLD (the 1x arms, reported not gated): order N lands on the fundamental at "
          f"f = FS/(N+1)\n      {folds} — coincident with the fundamental in BOTH time and "
          f"frequency, so\n      NEITHER instrument can reject it. 12.0 and 16.0 kHz sit on the "
          f"top two graded bands.\n      On the flat-drive arm the H1 read is the MORE sensitive "
          f"of the two there; the LPF arm shows\n      why a pedal-shaped chain barely sees it "
          f"(-22 dB of drive at 12 kHz leaves nothing to fold).")

    print()
    if fails:
        for f in fails:
            print(f"  FAIL: {f}")
        print(f"\n=== {len(fails)} FAILURE(S) — do not re-baseline against this instrument ===\n")
        return False
    print("=== ALL PASS — transfer_h1 is validated for FR reads at drive ===\n")
    return True


# ---- real-capture comparison -------------------------------------------------------------------
SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")


def _compare_one(path):
    orig = _CMP["orig"]
    cap = C.load_capture(path)
    if not A.is_full_length(cap, orig):
        return None
    cap_al, _ = A.align(cap, orig)
    inp = A.seg_of(orig, "sweep_clean")
    row = {"file": os.path.basename(path)}
    for sw in SWEEPS:
        seg = A.seg_of(cap_al, sw)
        if float(np.max(np.abs(seg))) < 1e-6:
            continue
        h1 = read_at_bands(A.transfer_h1, seg, inp, BANDS)
        cs = read_at_bands(A.transfer, seg, inp, BANDS)
        row[sw] = (cs - h1).tolist()          # CSD minus H1 = what the old instrument added
    return row


_CMP = {}


def _cmp_init():
    _CMP["orig"] = A.load(A.ORIG)


def compare(only, jobs):
    caps = C.find_captures()
    if only:
        subs = [s.strip() for s in only.split(",") if s.strip()]
        caps = [(p, d) for p, d in caps if any(s in os.path.basename(p) for s in subs)]
    print(f"\n=== CSD minus H1 on {len(caps)} real captures (positive = the old instrument read "
          f"MORE gain) ===")
    print("    This is measured on the CAPTURES ALONE — no plugin render, no model involved.\n")
    # CPU-bound (wav load + FFTs), so PROCESSES per parallel.pmap_cpu; the 4M-sample reference is
    # loaded once per worker by the initialiser rather than pickled with every item.
    rows = [r for r in pmap_cpu(_compare_one, [p for p, _ in caps], jobs=jobs,
                                initializer=_cmp_init) if r]

    print(f"{'sweep':<16}{'n':>5}{'median|d|':>11}{'p90|d|':>9}{'max|d|':>9}   worst band")
    for sw in SWEEPS:
        vals = np.array([r[sw] for r in rows if sw in r])
        if not len(vals):
            continue
        a = np.abs(vals)
        wi = np.unravel_index(int(np.argmax(a)), a.shape)
        print(f"{sw:<16}{len(vals):5d}{np.median(a):11.2f}{np.percentile(a, 90):9.2f}"
              f"{a.max():9.2f}   {BANDS[wi[1]]:.0f} Hz  ({rows[[i for i, r in enumerate(rows) if sw in r][wi[0]]]['file']})")

    print(f"\n  per-band |CSD − H1|, median over captures:")
    print(f"{'band Hz':>10}" + "".join(f"{sw.replace('sweep_', ''):>12}" for sw in SWEEPS))
    for bi, b in enumerate(BANDS):
        cells = []
        for sw in SWEEPS:
            vals = np.array([r[sw][bi] for r in rows if sw in r])
            cells.append(f"{np.median(np.abs(vals)):12.2f}" if len(vals) else f"{'-':>12}")
        print(f"{b:10.1f}" + "".join(cells))
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run the known-answer gate")
    ap.add_argument("--compare", action="store_true", help="CSD vs H1 on the real captures")
    ap.add_argument("--only", default=None, help="filename substrings for --compare")
    add_jobs_arg(ap, "Used by --compare.")
    a = ap.parse_args()
    if not (a.selftest or a.compare):
        a.selftest = True
    ok = True
    if a.selftest:
        ok = selftest()
    if a.compare:
        compare(a.only, a.jobs)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
