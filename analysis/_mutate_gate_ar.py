#!/usr/bin/env python3.11
"""Mutation test for GATE AR (analysis/notch_residual_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's whole value is four statements a
    reader would quote forward — "the paired gap SHRANK where AQ4's pooled one SURVIVED", "the
    BOTTOM term carries it", "the residual changes sign across stimulus", and "the more asymmetric
    side is the COMPOSITE" — and a verdict that cannot become its opposite is narration
    (`computed-verdicts-not-narrated`, s34/s61/s68).  Four arms drive each to the other branch and
    require the gate to print it.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * the mutant's REPORT path is redirected, and the redirect REFUSES if its pattern does not
    apply — a mutant runs `main()`, so without this the last arm's forced-false output is left on
    disk wearing the real gate's filename (s153, which cost that session a false alarm).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * **AR5b has no arm on its p-value branch**, deliberately.  The measured p is 0.0523 — ON the
    0.05 convention — so an arm that flipped the branch would be testing a coin, not a guard.  What
    IS armed is the thing the gate actually rests on: the printed r², via the verdict block.  This
    is the same reasoning as GATE AQ's refusal to arm `q_interp`'s absolute accuracy.
  * AR5a's per-cell f0 offsets are printed, not gated; the aggregate is armed instead.
  * AR1b's blindness is structural and already stated in its own docstring (both sides share the
    element set as input, s145/s149) — a mutation cannot reach what a check cannot see, and adding
    an arm that appeared to would be worse than the honest gap.

Run:  python3.11 analysis/_mutate_gate_ar.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "notch_residual_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_ar_{os.getpid()}.py")

# --- monkey-patches injected after the mutant's own imports -------------------------------------

# (a) break the S − B identity.  AR1a is what makes AR4 a DECOMPOSITION rather than two numbers
#     that happen to be printed together; adding a constant to S alone breaks the algebra while
#     leaving every curve reading untouched, so nothing else has an excuse to notice.
_MONKEY_IDENTITY = '''
_orig_terms = terms


def _bent(g, d, geo=None):
    r, S, B, resid = _orig_terms(g, d, geo=geo)
    return r, S + 0.05, B, abs((r["depth_point"] - r["depth_area"]) - ((S + 0.05) - B))


terms = _bent
'''

# (b) bias the 1-D solve, so this gate's records no longer re-aggregate to GATE AP's stored
#     per-cell numbers.  AR1b is the ONLY thing establishing that AR2/AR3's re-pairing is a
#     RE-AGGREGATION of AQ4's own numbers rather than a second, independent measurement — without
#     it, "the paired form disagrees" is equally consistent with my solves simply being different.
_MONKEY_1D_BIAS = '''
_orig_ap_solve = AP.solve_gain
AP.solve_gain = lambda *a, **k: (lambda v: None if v is None else v + 0.05)(_orig_ap_solve(*a, **k))
'''

# (c) the same for the 2-D solve — the other half of AR1b, and the one AR3's headline reads.
_MONKEY_2D_BIAS = '''
_orig_aq_solve = AQ.solve_gain_q
AQ.solve_gain_q = lambda *a, **k: (lambda v: v if v is None else (v[0] + 0.05, v[1], v[2], v[3]))(
    _orig_aq_solve(*a, **k))
'''

# (d) make `skew` unreadable everywhere.  AR5(c)'s membership guard must refuse rather than screen
#     an asymmetry candidate on an empty set (`empty-gate-must-fail`) — and this gate's asymmetry
#     reading is the one genuinely NEW measurement it takes, so an unguarded empty is exactly how
#     a structural claim would get made about nothing.
_MONKEY_SKEW_NAN = '''
skew = lambda r: float("nan")
'''

# (d2) bias the 1-D solve used ONLY by AR1c's synthetic control.  `AQ.solve_gain_at_q` is called
#      nowhere else in this gate (build() uses AP.solve_gain and AQ.solve_gain_q), so this arm
#      reaches AR1c without tripping AR1b on the way — the s119 requirement that an arm be scored
#      against the guard it names.
_MONKEY_AR1C_SOLVE_BIAS = '''
_orig_at_q = AQ.solve_gain_at_q
AQ.solve_gain_at_q = lambda *a, **k: (lambda v: None if v is None else v + 0.5)(
    _orig_at_q(*a, **k))
'''

# (e) — the AR4 verdict arm is a DATA-LEVEL LABEL SWAP applied inside ar4 (see ARMS below), not a
#     monkey-patch.  The first draft zeroed the bottom term on both curves, which makes dB a
#     constant-zero array: `np.corrcoef` then returns nan, every comparison against nan is False,
#     and the gate falls through to its SPLIT branch — i.e. the arm would have reported NARRATED
#     against a verdict block that was working.  `a-nan-does-not-trip-a-threshold` (s106), inside a
#     mutation arm.  Swapping the two terms' labels keeps both arrays non-degenerate and asks the
#     only question that matters: is the verdict computed from the data, or attached to a name?

# (f) THE AR3 VERDICT PATCH.  Shrink the 2-D design's per-sweep gaps to ~0 so shape-matching
#     appears to close the disagreement entirely.  ⚠ Patched at `_paired` rather than at the solver
#     so AR1b (which reads the records directly) still passes — an arm that trips an EARLIER guard
#     is scored against a guard it does not name (s119).
_MONKEY_2D_GAP_TINY = '''
_orig_paired = _paired


def _shrunk(recs, which):
    out = _orig_paired(recs, which)
    return [(r, d * 0.001) for r, d in out] if which == "t2" else out


_paired = _shrunk
'''

ARMS = [
    # ---------------- REFUSAL ARMS ----------------------------------------
    ("AR1a  the metric difference must BE S − B",
     "add 0.05 dB to the shoulder term only.  ⭐ This is the arm that makes AR4 a decomposition:\n"
     "    without the identity holding at machine precision, 'the bottom term carries 0.84' is a\n"
     "    statement about two numbers that were printed near each other.",
     [(r'^def build\(\)', _MONKEY_IDENTITY + '\n\ndef build()')],
     1, "\u274c AR1a", ),

    ("AR1b  the records must re-aggregate to GATE AP's stored 1-D numbers",
     "add 0.05 dB to every 1-D solve.  AR1b is the ONLY thing making AR3's re-pairing a\n"
     "    RE-AGGREGATION of AQ4's own numbers — without it, 'the paired form disagrees with AQ4'\n"
     "    is equally consistent with my solver simply being a different solver.",
     [(r'^def build\(\)', _MONKEY_1D_BIAS + '\n\ndef build()')],
     1, "\u274c AR1b", ),

    ("AR1b  …and to GATE AQ's stored 2-D numbers",
     "the other half: bias the 2-D solve, which is the column AR3's headline is read from.",
     [(r'^def build\(\)', _MONKEY_2D_BIAS + '\n\ndef build()')],
     1, "\u274c AR1b", ),

    ("AR1c  the synthetic control must recover the injected gain",
     "bias the 1-D solve AR1c uses (`AQ.solve_gain_at_q`, which this gate calls NOWHERE else, so\n"
     "    the arm cannot be caught by AR1b first — s119).  The composite is then built at the wrong\n"
     "    gain and every residual AR1c reports must leave zero.\n"
     "    ⚠⚠ THE FIRST DRAFT OF THIS ARM WAS VACUOUS AND THE VACUITY IS A MEASUREMENT WORTH\n"
     "    KEEPING (s110: suspect the mutation before the guard; s122: keep the vacuous one if it\n"
     "    proved an invariance).  It gave AR1c's synthetic model a SLOPING background instead of a\n"
     "    flat one, and the gate ran clean — correctly, because the pedal and the composite are\n"
     "    built on the SAME background and the point solve recovers the injected gain exactly, so\n"
     "    every residual is zero for ANY background whatsoever.  ⇒ AR1c's `flat` is a SIMPLIFICATION\n"
     "    and not a condition of the control, which is worth knowing before anyone 'improves' it by\n"
     "    making the background realistic and believes that strengthened it.",
     [(r'^def build\(\)', _MONKEY_AR1C_SOLVE_BIAS + '\n\ndef build()')],
     1, "\u274c AR1c", ),

    ("AR3  the paired comparison must actually have cells",
     "empty the paired intersection.  A gap verdict computed over zero cells is the flattering\n"
     "    answer every time (`empty-gate-must-fail`), and this gate's headline IS that verdict.",
     [(r'    keys = sorted\(set\(p1\) & set\(p2\)\)', '    keys = []')],
     1, "\u274c AR3", ),

    ("AR5  the asymmetry screen must refuse rather than screen nothing",
     "make every skew unreadable.  The asymmetry reading is the one NEW measurement this gate\n"
     "    takes, and it carries a STRUCTURAL claim (a symmetric section cannot span an asymmetric\n"
     "    null) — precisely the kind that must not be made over an empty set.",
     [(r'^def build\(\)', _MONKEY_SKEW_NAN + '\n\ndef build()')],
     1, "\u274c AR5", ),

    ("AR6  the stimulus axis must have readable cells",
     "empty AR6's membership.  Its conclusion is the most consequential thing here — that what\n"
     "    survives shape-matching is s151 §6's architectural limit rather than a shape defect — so\n"
     "    it must not be reachable from no data.",
     [(r'    ok = \[r for r in recs if r\["comp"\] is not None and np\.isfinite\(r\["D"\]\)\]\n'
       r'    if not ok:', '    ok = []\n    if not ok:')],
     1, "\u274c AR6", ),

    # ---------------- COMPUTED-VERDICT ARMS -------------------------------
    ("AR3-verdict  'SHRANK' must be able to become 'COLLAPSED'",
     "shrink the 2-D design's per-sweep gaps to ~0, so shape-matching appears to close the\n"
     "    disagreement inside the fit's own residual.  This gate's headline is that the PAIRED gap\n"
     "    behaves differently from AQ4's pooled one; a headline that cannot invert is narration.",
     [(r'^def ar2\(recs\)', _MONKEY_2D_GAP_TINY + '\n\ndef ar2(recs)')],
     0, "COLLAPSED", ),

    ("AR4-verdict  'the BOTTOM term carries it' must be able to become the shoulders",
     "swap the two terms' labels where ar4 builds them.  AR4 is what would point a successor at\n"
     "    sharpness-inside-the-half-depth-width rather than at the skirts — the opposite\n"
     "    instruction — so the branch that says so needs an arm that reaches it.  ⚠ A first draft\n"
     "    zeroed the bottom term instead and made its correlation `nan`, which silently routed the\n"
     "    gate to its SPLIT branch: the arm would have failed a verdict block that was correct.",
     [(r'    dS = np\.array\(\[r\["S_p"\] - r\["S_c"\] for r in ok\]\)\n'
       r'    dB = np\.array\(\[r\["B_p"\] - r\["B_c"\] for r in ok\]\)',
       '    dS = np.array([r["B_p"] - r["B_c"] for r in ok])\n'
       '    dB = np.array([r["S_p"] - r["S_c"] for r in ok])')],
     0, "THE SHOULDER TERM CARRIES IT", ),

    ("AR6-verdict  'the residual changes sign' must be able to become one-signed",
     "take |D| inside AR6 only, so the residual is one-signed across the ladder.  ⚠ Patched at the\n"
     "    DATA feeding the verdict rather than at the sign test itself — mutating the test would\n"
     "    prove only that an `if` works (s114).",
     [(r'        D = np\.array\(\[r\["D"\] for r in v\]\)',
       '        D = np.abs(np.array([r["D"] for r in v]))')],
     0, "one-signed across the stimulus ladder", ),

    ("AR5c-verdict  'the more asymmetric side is the COMPOSITE' must be able to name the pedal",
     "swap the two skew columns.  ⭐⭐ This is the arm that matters most in this gate: s153 named\n"
     "    the candidate as 'the PEDAL's null is asymmetric', the measurement says the opposite side\n"
     "    is the skewed one, and that inversion is the finding.  A direction printed by a line that\n"
     "    cannot print the other direction would be worth nothing.",
     [(r'    ok = \[r for r in recs if r\["comp"\] is not None\]\n    res = \{\}',
       '    ok = [r for r in recs if r["comp"] is not None]\n'
       '    for _r in ok:\n'
       '        _r["skew_p"], _r["skew_c"] = _r["skew_c"], _r["skew_p"]\n'
       '    res = {}')],
     0, "the more asymmetric side is the PEDAL", ),
]


def run(path):
    p = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ⛔⛔ EVERY MUTANT MUST WRITE ITS REPORT SOMEWHERE ELSE (s153).  A mutant runs `main()`, and
# `main()` writes the gate's report — so without this the LAST arm's output is left on disk under
# the real gate's filename, wearing its name.  The redirect REFUSES rather than silently no-opping,
# because a redirect that quietly fails restores the exact bug it was added to prevent.  The
# control run is redirected too: it must exercise the same code path as the arms.
def _redirect_report(text):
    out, n = re.subn(r'"s154_notch_residual\.json"', f'"_mut_s154_{os.getpid()}.json"', text)
    if n != 1:
        sys.exit("_mutate_gate_ar: could not redirect the mutant's report path — refusing to run "
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
    stray = os.path.join(HERE, "reports", f"_mut_s154_{os.getpid()}.json")
    if os.path.exists(stray):
        os.remove(stray)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
