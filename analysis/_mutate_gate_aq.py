#!/usr/bin/env python3.11
"""Mutation test for GATE AQ (analysis/notch_shape_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate makes three claims that a reader
    would quote — "the Q reader is quantised", "the pedal's Q is not one number", and "matching the
    shape does NOT collapse the metric gap" — and a verdict that cannot become its opposite is
    narration (s34/s61/s68).  Three arms drive each to the opposite branch and require the gate to
    print it.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * arms that corrupt `od_tone_restore_fit` (an IMPORTED module) inject a module-level
    monkey-patch into the mutant AFTER its imports (s139), so the override dies with the
    subprocess and leaves no shared state to restore.

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * AQ3's per-cell (gain, Q) values are printed, not gated — they are the gate's OUTPUT, and the
    thing that gates them is AQ1d's round trip, which has two arms.
  * AQ2's per-cell reach/no-reach is gated only in aggregate (via AQ4's exclusion and the verdict
    block).  An arm that flips a single cell's reachability without flipping anything else would
    have to fake the ladder for one cell only, which tests the fake rather than the gate.
  * `q_interp`'s absolute accuracy has no arm BY DESIGN: AQ1c gates monotonicity and AQ1d gates
    round-trip recovery, because the reader is measurably BIASED at low Q (shoulder truncation)
    and that bias cancels in every comparison this gate makes.  An accuracy arm would assert
    something the gate deliberately does not claim.

Run:  python3.11 analysis/_mutate_gate_aq.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "notch_shape_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_aq_{os.getpid()}.py")

# --- monkey-patches injected after the mutant's own imports -------------------------------------

# (a) bias this gate's inner solve so it no longer agrees with GATE AP's.  AQ1a is the ONLY thing
#     establishing that promoting Q from a shipped constant to an argument did not change the
#     quantity being solved for; without it the 2-D solve is an unvalidated re-implementation.
_MONKEY_INNER_BIAS = '''
_orig_inner = solve_gain_at_q
solve_gain_at_q = lambda *a, **k: (lambda v: None if v is None else v + 0.05)(_orig_inner(*a, **k))
'''

# (b) perturb the GRID reader's q off the cell lattice.  AQ1c's structural claim is that every `q`
#     is exactly 1/(2^(m/48) − 2^(−n/48)) for integer (m, n) — a closed form with no threshold — and
#     the quantisation account this whole session rests on is wrong if that does not hold.
_MONKEY_Q_OFF_LATTICE = '''
_orig_geo_lat = F.notch_geometry


def _off(g, d, core=None, shoulder=None, depth="point"):
    r = _orig_geo_lat(g, d, core=core, shoulder=shoulder, depth=depth)
    r["q"] = r["q"] * 1.003
    return r


F.notch_geometry = _off
'''

# (c) make the grid reader continuous (q := q_interp).  AQ1c must then refuse: this gate exists
#     because `q` COLLIDES, and if it does not, the defect it documents is not reproducing and the
#     s153 quantisation finding must not be quoted.
_MONKEY_NO_COLLISIONS = '''
_orig_geo_nc = F.notch_geometry


def _cont(g, d, core=None, shoulder=None, depth="point"):
    r = _orig_geo_nc(g, d, core=core, shoulder=shoulder, depth=depth)
    r["q"] = r["q_interp"]
    return r


F.notch_geometry = _cont
'''

# (d) make `q_interp` no better than `q` (snap it back to the lattice).  AQ1c must refuse on
#     MONOTONICITY: a step function cannot be an objective, and every solve below reads q_interp.
_MONKEY_INTERP_IS_GRID = '''
_orig_geo_ig = F.notch_geometry


def _snap(g, d, core=None, shoulder=None, depth="point"):
    r = _orig_geo_ig(g, d, core=core, shoulder=shoulder, depth=depth)
    r["q_interp"] = r["q"]
    return r


F.notch_geometry = _snap
'''

# (e) bias the 2-D solve's GAIN coordinate -- AQ1d's round trip.  A 2-D solve can slide along a
#     gain/Q valley in a way a 1-D one cannot, so both coordinates need their own arm.
_MONKEY_2D_GAIN_BIAS = '''
_orig_2d_g = solve_gain_q
solve_gain_q = lambda *a, **k: (lambda v: v if v is None else (v[0] + 0.2, v[1], v[2], v[3]))(
    _orig_2d_g(*a, **k))
'''

# (f) bias the 2-D solve's Q coordinate -- the other half of AQ1d.
_MONKEY_2D_Q_BIAS = '''
_orig_2d_q = solve_gain_q
solve_gain_q = lambda *a, **k: (lambda v: v if v is None else (v[0], v[1] * 1.03, v[2], v[3]))(
    _orig_2d_q(*a, **k))
'''

# (g) stop the reader refusing on a featureless curve -- AQ1d's flat-curve control.  `a silent
#     estimator and an absent feature are indistinguishable` (s126/s133).
# ⚠ SCOPED to a constant curve: unscoped it makes the real cells degenerate and crashes in an
# EARLIER sub-gate, i.e. it would be caught by a different guard than the one it names (s119).
_MONKEY_NEVER_REFUSE = '''
import numpy as _np
_orig_geo_nr = F.notch_geometry


def _never(g, d, core=None, shoulder=None, depth="point"):
    try:
        return _orig_geo_nr(g, d, core=core, shoulder=shoulder, depth=depth)
    except RuntimeError:
        if float(_np.ptp(d)) > 1e-9:
            raise
        return {"f0": 323.0, "depth": 0.0, "depth_point": 0.0, "depth_area": 0.0, "q": 5.0,
                "q_interp": 5.0, "lsh": 0.0, "rsh": 0.0, "bottom": 0.0, "lsh_f": 210.0,
                "rsh_f": 520.0}


F.notch_geometry = _never
'''

# (h) THE COMPUTED-VERDICT PATCH, shared by two arms.  Replace each pedal curve with EXACTLY what
#     the shipped stage already produces (stage-subtracted model + the shipped biquad).  The pedal
#     null then HAS the biquad's own shape, so AQ1d's round trip says both metrics must return the
#     shipped (gain, Q) and the metric gap must go to zero -- i.e. AQ4 must print COLLAPSED, and
#     every cell must be reachable because the target Q is one the section demonstrably produces.
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
    g, _ped, mod, mt = _orig_curves(fname, sweep, ren_dir=ren_dir, meta=True)
    drv, gp = _DRV[fname], F.grunt_pos_of(fname)
    off = mod - F.current_response(g, drv, _FS, _T, gp, F.clean_frac_of(fname))
    q = F.lerp5(_T["kNotchQ"][gp], drv, _T["kX"])
    ship = F.lerp5(_T["kNotchGainDb"][gp], drv, _T["kX"])
    ped = off + F.rbj_peak_db(g, _FS, _T["kNotchFreq"], q, -ship)
    return (g, ped, mod, mt) if meta else (g, ped, mod)


F.curves = _synth
'''

# (i) make the pedal's Q identical at every stimulus rung -- AQ2b's computed verdict.  The claim
#     "the pedal's Q is not one number" must be able to become "it is".
_MONKEY_Q_STIMULUS_FLAT = '''
_orig_aq2 = aq2


def _flat_q(*a, **k):
    reach, hit, tot = _orig_aq2(*a, **k)
    for v in reach.values():
        if v:
            ref = v[0]["ped_q"]
            for r in v:
                r["ped_q"] = ref
    return reach, hit, tot


aq2 = _flat_q
'''

ARMS = [
    # ---------------- REFUSAL ARMS ----------------------------------------
    ("AQ1a  the inner solve must still be GATE AP's",
     "add 0.05 dB to every gain this gate solves.  AQ1a is the ONLY check that promoting Q from a\n"
     "    shipped constant to an argument left the quantity unchanged — without it the 2-D solve\n"
     "    is an unvalidated re-implementation of a gate that already exists.",
     [(r'^def main\(\)', _MONKEY_INNER_BIAS + '\n\ndef main()')],
     1, "AQ1a", ),

    ("AQ1c  every grid `q` must sit exactly on the cell lattice",
     "scale the grid reader's q by 1.003, off the lattice.  ⭐ This is the arm that makes the\n"
     "    quantisation account DERIVED rather than observed: the whole s153 finding is that `q` can\n"
     "    only take the values 1/(2^(m/48) − 2^(−n/48)), and if that closed form does not hold the\n"
     "    explanation is wrong even though the collisions would still be visible in the table.",
     [(r'^REAL = ', _MONKEY_Q_OFF_LATTICE + 'REAL = ')],
     1, "AQ1c", ),

    ("AQ1c  the grid reader must actually COLLIDE",
     "make `q` continuous (q := q_interp).  If the shipped reader does not collide, the defect this\n"
     "    session documents is not reproducing and none of it may be quoted — the guard exists so a\n"
     "    future grid change silently repairing `q` cannot leave the narrative standing.",
     [(r'^REAL = ', _MONKEY_NO_COLLISIONS + 'REAL = ')],
     1, "AQ1c", ),

    ("AQ1c  `q_interp` must be strictly monotone",
     "snap q_interp back onto the grid lattice.  Every solve in this gate reads q_interp, and a\n"
     "    step function is not invertible — which is exactly why the first draft of AQ1d failed at\n"
     "    3 of 4 injected pairs against a solver that was fine.",
     [(r'^REAL = ', _MONKEY_INTERP_IS_GRID + 'REAL = ')],
     1, "AQ1c", ),

    ("AQ1d  the 2-D round trip must recover the injected GAIN",
     "add 0.2 dB to the solved gain.  A 2-D solve can slide along a gain/Q valley in a way a 1-D\n"
     "    one cannot, so recovering BOTH coordinates is what shows the two constraints pin a point.",
     [(r'^def main\(\)', _MONKEY_2D_GAIN_BIAS + '\n\ndef main()')],
     1, "AQ1d", ),

    ("AQ1d  the 2-D round trip must recover the injected Q",
     "scale the solved Q by 1.03 — the other coordinate, and the one every claim about SHAPE in\n"
     "    this gate depends on.",
     [(r'^def main\(\)', _MONKEY_2D_Q_BIAS + '\n\ndef main()')],
     1, "AQ1d", ),

    ("AQ1d  the reader must REFUSE on a featureless curve",
     "return a zero-depth reading instead of raising when the minimum rests on a CORE bound.\n"
     "    AQ2's membership counts and AQ3's `n` columns all depend on the refusal being real.",
     [(r'^REAL = ', _MONKEY_NEVER_REFUSE + 'REAL = ')],
     1, "AQ1d", ),

    ("AQ2  the reachability sweep must actually measure something",
     "empty the ladder inside aq2 only, so no cell is measured.  `empty-gate-must-fail` — a\n"
     "    reachability verdict computed over zero cells is the flattering answer, every time.\n"
     "    ⚠ Patched INSIDE aq2 rather than at QLADDER: emptying the ladder globally breaks AQ1d\n"
     "    first, which would score this arm against a guard it does not name (s119).",
     [(r'lad = q_reach\(g, mod_off, pg\["depth_point"\], drv, T, fs, "point"\)',
       'lad = []')],
     1, "AQ2", ),

    # ---------------- COMPUTED-VERDICT ARMS -------------------------------
    ("AQ4-verdict  'the gap SURVIVED' must be able to become 'COLLAPSED'",
     "replace each pedal curve with exactly what the shipped stage already produces, so the pedal\n"
     "    null carries the biquad's OWN shape.  AQ1d's round trip then says both metrics must\n"
     "    return the shipped (gain, Q) and the gap must go to zero.  This gate's headline is that\n"
     "    shape-matching does NOT close the metric gap; a headline that cannot inv"
     "ert is narration.",
     [(r'^REAL = ', _MONKEY_PEDAL_IS_SHIPPED + 'REAL = ')],
     0, "COLLAPSED", ),

    ("AQ2b-verdict  'the pedal's Q is not one number' must be able to become 'it is'",
     "force the pedal's Q equal at all three stimulus rungs.  AQ2b's conclusion — that a\n"
     "    DRIVE-keyed table cannot carry a stimulus-dependent Q — is the gate's most consequential\n"
     "    statement, so it needs a branch that states the opposite and an arm that reaches it.",
     [(r'^def main\(\)', _MONKEY_Q_STIMULUS_FLAT + '\n\ndef main()')],
     0, "Q IS STIMULUS-STABLE", ),
]


def run(path):
    p = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ⛔⛔ EVERY MUTANT MUST WRITE ITS REPORT SOMEWHERE ELSE.  A mutant runs `main()`, and `main()`
# writes the gate's report — so without this the LAST arm's output is left on disk under the real
# gate's filename, wearing its name.  It cost this session a false "the rebuild changed the
# numbers" alarm (the file compared against turned out to be the AQ2b-verdict arm's own forced-flat
# output), and it would have handed a later session a poisoned artefact silently.  The control run
# is redirected too: it must exercise the same code path as the arms.
def _redirect_report(text):
    out, n = re.subn(r'"s153_notch_shape\.json"', f'"_mut_s153_{os.getpid()}.json"', text)
    if n != 1:
        sys.exit("_mutate_gate_aq: could not redirect the mutant's report path — refusing to run "
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
        for l in [l for l in out.strip().splitlines() if l.strip()][-6:]:
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
                                       else "REFUSED as required") + f" (rc={rc}, saw '{must}')")
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
    stray = os.path.join(HERE, "reports", f"_mut_s153_{os.getpid()}.json")
    if os.path.exists(stray):
        os.remove(stray)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
