#!/usr/bin/env python3.11
"""Mutation test for GATE AP (analysis/null_depth_censor_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.
  * `expect_rc == 0` arms test the COMPUTED VERDICT.  This gate's deliverable is
    "N of 9 shipped entries owe a change larger than the fit's own residual", and a verdict that
    cannot become its opposite is narration (s34/s61/s68) — so one arm drives it to "NO shipped
    entry owes a change" and requires the gate to say so.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * ⚠ most arms corrupt `od_tone_restore_fit`, an IMPORTED module, so they inject a module-level
    monkey-patch into the mutant AFTER its imports (s139) — the override dies with the subprocess
    and leaves no shared state to restore.

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * AP4's membership finding ("2 of 9 entries rest on <=1 sweep cell") has no arm.  Flipping it
    needs a reader that never refuses, and that same patch kills AP1c's flat-curve control — the
    gate is better than this test's model of it (s119), so the honest move is to record the gap
    rather than weaken a guard to cover it.
  * AP6's two correlations are printed, not gated, so there is nothing to mutate.

Run:  python3.11 analysis/_mutate_gate_ap.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "null_depth_censor_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_ap_{os.getpid()}.py")

# --- monkey-patches injected after the mutant's own imports -------------------------------------

# (a) average in dB instead of in POWER.  ⭐ The point of this arm: a dB average is IDENTICAL to a
#     power average on a flat curve, so AP1a's own synthetic control cannot see it — only the
#     cross-implementation comparison against GATE R's band_db can.  This is the arm that proves
#     that comparison is load-bearing rather than decorative.
_MONKEY_DB_AVERAGE = '''
import numpy as _np


def _db_avg(g, d, centre, frac=F.DEPTH_FRAC):
    lo, hi = centre * 2.0 ** (-0.5 / frac), centre * 2.0 ** (0.5 / frac)
    m = (g >= lo) & (g <= hi)
    if not m.any():
        return float(_np.interp(centre, g, d))
    return float(_np.mean(_np.asarray(d)[m]))


F.band_db_grid = _db_avg
'''

# (b) add a constant to every band average -- AP1a's flat-curve control.
_MONKEY_BAND_OFFSET = '''
_orig_band = F.band_db_grid
F.band_db_grid = lambda g, d, centre, frac=F.DEPTH_FRAC: _orig_band(g, d, centre, frac) + 0.7
'''

# (c) make the AREA depth just BE the point depth.  AP1b must refuse: the whole gate rests on the
#     area depth being more robust to censoring, and if it is the same statistic there is nothing
#     to be robust about.
_MONKEY_AREA_IS_POINT = '''
_orig_geo = F.notch_geometry


def _same(g, d, core=None, shoulder=None, depth="point"):
    r = _orig_geo(g, d, core=core, shoulder=shoulder, depth=depth)
    r["depth_area"] = r["depth_point"]
    if depth == "area":
        r["depth"] = r["depth_point"]
    return r


F.notch_geometry = _same
'''

# (d) shift the clipping harness so its zero rung is not zero -- AP1b's own inertness control.
# ⚠ A first draft monkey-patched `np.maximum` globally and crashed inside W.smooth(), which uses
# it on ARRAY INDICES.  A patch aimed at a harness must be applied at the harness, not at a
# primitive the whole pipeline shares — so this one is a source edit on the ladder itself.

# (e) bias the solved gain -- AP1c's round trip is the only thing establishing that the two AP3
#     columns are the same unit, so a solver that loses the injected gain must be caught.
_MONKEY_SOLVE_BIAS = '''
_orig_solve = solve_gain
solve_gain = lambda *a, **k: (lambda v: None if v is None else v * 1.1)(_orig_solve(*a, **k))
'''

# (f) stop the reader refusing on a CORE bound -- AP1c's flat-curve mutation control.  `a silent
#     estimator and an absent feature are indistinguishable` (s126/s133).
_MONKEY_NEVER_REFUSE = '''
import numpy as _np
_orig_geo2 = F.notch_geometry


def _never(g, d, core=None, shoulder=None, depth="point"):
    try:
        return _orig_geo2(g, d, core=core, shoulder=shoulder, depth=depth)
    except RuntimeError:
        # SCOPED TO A CONSTANT CURVE.  Unscoped, this makes AP1b's clipped ladders degenerate and
        # crashes np.polyfit's lstsq -- i.e. it is caught by an EARLIER guard, as a crash rather
        # than a refusal (s119).  Narrowed so the arm tests the control it names.
        if float(_np.ptp(d)) > 1e-9:
            raise
        return {"f0": 323.0, "depth": 0.0, "depth_point": 0.0, "depth_area": 0.0, "q": 5.0,
                "lsh": 0.0, "rsh": 0.0, "bottom": 0.0, "lsh_f": 210.0, "rsh_f": 520.0}


F.notch_geometry = _never
'''

# (g) make the AREA depth a concave function of itself, so it turns over inside the solve's own
#     gain ladder and the root stops being unique -- AP3's uniqueness guard.
_MONKEY_NONMONOTONE = '''
_orig_geo3 = F.notch_geometry


def _hump(g, d, core=None, shoulder=None, depth="point"):
    r = _orig_geo3(g, d, core=core, shoulder=shoulder, depth=depth)
    if abs(float(d[0])) < 1e-12:
        return r          # AP1c's synthetic sits on a flat background of exact zeros; leave it
    x = r["depth_area"]
    r["depth_area"] = x - 0.06 * x * x
    if depth == "area":
        r["depth"] = r["depth_area"]
    return r


F.notch_geometry = _hump
'''

# (h) corrupt the REFERENCE AP3a compares against -- and note WHY it must be the reference alone.
# ⭐⭐ A first draft added 5 dB to every shipped notch gain via `shipped_tables`, and AP3a passed
# unchanged: the same table is used BOTH to subtract the stage out of the rendered curve AND as
# the reference, so a uniform shift cancels exactly.  That is a real property of the known answer,
# not a bad mutation -- AP3a certifies THE SOLVE and is blind to the table's absolute value
# (s145's `a-known-answer-is-blind-to-what-both-sides-share-as-INPUT`).  It is now recorded in
# ap3a's own docstring, and the arm attacks the reference alone, which is what the check claims.

# (i) THE COMPUTED-VERDICT ARM.  Replace each pedal curve with EXACTLY what the shipped table
#     already produces (the stage-subtracted model plus the shipped biquad).  Both metrics must
#     then solve to the shipped gain -- AP1c's round trip says so, since the target now has the
#     biquad's own shape -- and the gate must report that NOTHING owes a change.
_MONKEY_PEDAL_IS_SHIPPED = '''
import feature_locus_gate as _W
_orig_curves = F.curves
_T = F.shipped_tables()
_FS = 48000.0 * _W.OS_FACTOR
_DRV = {}
for _s in F.SETS.values():
    for _fn, _dv in _s:
        _DRV[_fn] = _dv


def _synth(fname, sweep, ren_dir=F.REN_DIR, meta=False):
    r = _orig_curves(fname, sweep, ren_dir=ren_dir, meta=True)
    g, _ped, mod, mt = r
    drv, gp = _DRV[fname], F.grunt_pos_of(fname)
    off = mod - F.current_response(g, drv, _FS, _T, gp, F.clean_frac_of(fname))
    q = F.lerp5(_T["kNotchQ"][gp], drv, _T["kX"])
    ship = F.lerp5(_T["kNotchGainDb"][gp], drv, _T["kX"])
    ped = off + F.rbj_peak_db(g, _FS, _T["kNotchFreq"], q, -ship)
    return (g, ped, mod, mt) if meta else (g, ped, mod)


F.curves = _synth
'''

ARMS = [
    # ---------------- REFUSAL ARMS ----------------------------------------
    ("AP1a  band_db_grid must average in POWER, not in dB",
     "average the band in dB.  ⭐ On a FLAT curve a dB average and a power average are the same\n"
     "    number, so AP1a's own synthetic control is blind to this — only the comparison against\n"
     "    GATE R's band_db can see it.  This arm is what proves that comparison is load-bearing.",
     [(r'^REAL = ', _MONKEY_DB_AVERAGE + 'REAL = ')],
     1, "AP1a", ),

    ("AP1a  the flat-curve control must be exact",
     "add 0.7 dB to every band average.  The cross-implementation check above would catch a\n"
     "    SHAPE error; this one catches an offset, and the two arms together are why AP1a has two\n"
     "    tests rather than one.",
     [(r'^REAL = ', _MONKEY_BAND_OFFSET + 'REAL = ')],
     1, "AP1a", ),

    ("AP1b  the AREA depth must actually be more robust than the point depth",
     "make depth_area == depth_point.  This is the gate's CENTRAL PREMISE: if the two statistics\n"
     "    respond to censoring identically there is no censor-robust reading to be had, and every\n"
     "    number in AP3 is a restatement of the shipped table.",
     [(r'^REAL = ', _MONKEY_AREA_IS_POINT + 'REAL = ')],
     1, "AP1b", ),

    ("AP1b  the zero-clip rung must be inert",
     "shift every clip level by 0.1 dB so the ladder's own zero rung already bites.  A censoring\n"
     "    ladder that perturbs the unclipped reading measures its own harness.",
     [(r'cl = np\.maximum\(ped, bottom \+ c\)', 'cl = np.maximum(ped, bottom + c + 0.1)')],
     1, "AP1b", ),

    ("AP1c  the round trip must recover the injected gain",
     "bias every solved gain by 10 %.  AP1c is the ONLY thing establishing that AP3's point and\n"
     "    area columns are the same unit — without it, their difference is two units subtracted.",
     [(r'^def main\(\)', _MONKEY_SOLVE_BIAS + '\n\ndef main()')],
     1, "AP1c", ),

    ("AP1c  the reader must REFUSE on a featureless curve",
     "return a zero-depth reading instead of raising when the minimum rests on a CORE bound.\n"
     "    A silent estimator and an absent feature are indistinguishable (s126/s133), and this\n"
     "    gate's membership counts depend on the refusal being real.",
     [(r'^REAL = ', _MONKEY_NEVER_REFUSE + 'REAL = ')],
     1, "AP1c", ),

    ("AP3  the solved gain must be a UNIQUE root",
     "make the area depth concave in itself so it turns over inside the solver's own gain ladder.\n"
     "    brentq returns *a* root; with two, the 'solved gain' is a choice the gate never made.",
     [(r'^REAL = ', _MONKEY_NONMONOTONE + 'REAL = ')],
     1, "AP3", ),

    ("AP3a  the point solve must reproduce the SHIPPED table",
     "shift the REFERENCE the check compares against by 5 dB, leaving the physics alone.\n"
     "    ⭐ It must be the reference ALONE: shifting `shipped_tables` instead leaves AP3a passing\n"
     "    unchanged, because that table is used BOTH to subtract the stage out and as the\n"
     "    reference, so the shift cancels — a real blind spot of this known answer, now recorded\n"
     "    in ap3a's docstring.  This known answer is what licenses reading AP3's area column.",
     [(r'ship = F\.lerp5\(T\["kNotchGainDb"\]\[gpos\], drv, T\["kX"\]\)\n(\s+)gp, ga = \[\], \[\]',
       r'ship = F.lerp5(T["kNotchGainDb"][gpos], drv, T["kX"]) + 5.0\n\1gp, ga = [], []')],
     1, "AP3a", ),

    # ---------------- COMPUTED-VERDICT ARM --------------------------------
    ("AP-verdict  'N entries owe a change' must be able to become 'none do'",
     "replace each pedal curve with exactly what the shipped table already produces.  Both metrics\n"
     "    must then return the shipped gain (AP1c's round trip says so — the target now carries the\n"
     "    biquad's own shape), so the gate must report that the censoring moves nothing.  A\n"
     "    headline that cannot invert is narration.",
     [(r'^REAL = ', _MONKEY_PEDAL_IS_SHIPPED + 'REAL = ')],
     0, "Open item 0 CLOSES", ),
]


def run(path):
    p = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ⛔⛔ EVERY MUTANT MUST WRITE ITS REPORT SOMEWHERE ELSE (added s153, after the identical defect
# was found in GATE AQ's runner).  A mutant runs `main()`, and `main()` writes the gate's report —
# so without this the LAST arm's output is left on disk under the real gate's filename, wearing its
# name.  In GATE AQ that produced a false "the rebuild changed the numbers" alarm; here it would
# quietly replace the artefact `CLAUDE.md` cites.  The control run is redirected too, so it
# exercises the same path as the arms.
def _redirect_report(text):
    out, n = re.subn(r'"s152_null_depth_censor\.json"', f'"_mut_s152_{os.getpid()}.json"', text)
    if n != 1:
        sys.exit("_mutate_gate_ap: could not redirect the mutant's report path — refusing to run "
                 "rather than let a mutant overwrite the gate's own artefact")
    return out


def main():
    src = _redirect_report(open(SRC).read())

    open(TMP, "w").write(src)
    rc, out = run(TMP)
    print(f"CONTROL   rc={rc}, gate passes from {os.path.relpath(TMP, REPO)}  "
          f"{'✓' if rc == 0 else '✗'}")
    if rc != 0:
        print("\n⛔ the UNMUTATED control does not pass — no failure below is attributable to any "
              "mutation (s107).  Fix this first.")
        for l in [l for l in out.strip().splitlines() if l.strip()][-5:]:
            print(f"      | {l[:110]}")
        os.remove(TMP)
        return 1

    bad = 0
    for name, why, patches, exp_rc, must in ARMS:
        mutated = src
        ok_patch = True
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches) — the arm is testing "
                      f"nothing.  Pattern: {pat[:70]}")
                bad += 1
                ok_patch = False
                break
            mutated = new
        if not ok_patch:
            continue
        open(TMP, "w").write(mutated)
        rc, out = run(TMP)
        hit = must in out
        ok = (rc == exp_rc) and hit
        if ok:
            print(f"✓ {name}\n    " + ("VERDICT CHANGED as required" if exp_rc == 0
                                       else f"REFUSED as required") + f" (rc={rc}, saw '{must}')")
        else:
            bad += 1
            if exp_rc != 0 and rc == 0:
                kind = "GUARD DEAD — the mutant ran clean"
            elif exp_rc == 0 and rc != 0:
                kind = f"CRASHED (rc={rc}) — the arm was meant to change a verdict, not refuse"
            elif exp_rc == 0 and not hit:
                kind = "NARRATED — the gate passed but never printed the opposite verdict"
            elif rc != exp_rc:
                kind = f"WRONG EXIT (rc={rc}, wanted {exp_rc})"
            else:
                kind = f"WRONG GUARD — refused without '{must}'"
            print(f"✗ {name}\n    {kind}")
            for l in [l for l in out.strip().splitlines() if l.strip()][-4:]:
                print(f"      | {l[:110]}")

    if os.path.exists(TMP):
        os.remove(TMP)
    stray = os.path.join(HERE, "reports", f"_mut_s152_{os.getpid()}.json")
    if os.path.exists(stray):
        os.remove(stray)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
