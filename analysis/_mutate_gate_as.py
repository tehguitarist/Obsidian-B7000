#!/usr/bin/env python3.11
"""Mutation test for GATE AS (analysis/ladder_zin_tilt_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's value is five statements a
    reader would quote forward — "the lever is real at a limit", "the class is not shape-refuted
    the way its predecessors were", "it is decided on the SIZE of the element change", "the
    added-element branch falls too" and "it passes the GRUNT gate and is still refuted" — and a
    verdict that cannot become its opposite is narration (`computed-verdicts-not-narrated`).

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * the mutant's REPORT path is redirected, and the redirect REFUSES if its pattern does not apply
    — a mutant runs `main()` (s153).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * **AS1d (probe independence) has no arm.**  Its blindness is structural and already stated in
    its own line: both probes share the ELEMENT SET as input, so it validates the extraction and
    can say nothing about the value set (s145 AM1a / s149 AO).  An arm that appeared to reach that
    would be worse than the honest gap — AS1c is the guard that covers the value set, and it IS
    armed.
  * **AS5's root-cause profile is printed, not gated.**  It explains AS3/AS4's result; it does not
    decide anything, so there is no verdict to invert.
  * **The pair-element SELECTION (AS2 -> AS3) has no arm.**  Reversing the lever ordering changes
    which six elements are searched and does not change any verdict — the class is refuted at the
    limits of every element — so an arm there would assert a difference that does not exist.

Run:  python3.11 analysis/_mutate_gate_as.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "ladder_zin_tilt_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_as_{os.getpid()}.py")

# --- monkey-patches injected after the mutant's own imports -------------------------------------

# (a) BREAK THE LICENCE — and break it NONLINEARLY.  AS1a asserts that the tilt operator is linear
#     on log-magnitude, which is the entire reason this gate may model the drain node alone and no
#     part of the chain downstream of it.  ⚠ s138's lesson: a DIFFERENT LINEAR functional does not
#     break additivity, so an arm that merely mixes in another coefficient reads GUARD DEAD against
#     a guard that is working.  A squared term is genuinely nonlinear and fires immediately.
_MONKEY_LICENCE = '''
_orig_tilt = AI.tilt_fine
AI.tilt_fine = lambda db, f0, half: (lambda v: v + 1e-3 * v * v)(_orig_tilt(db, f0, half))
'''

# (b) BIAS THE EXPONENT ESTIMATOR, BUT ONLY WHERE AS1e READS IT.  A flat bias would trip AS1f's
#     AL4-reproduction die first and be scored against a guard it does not name (s119).  The f^3
#     known answer is the only all-POSITIVE curve this gate ever hands the estimator — the pole
#     curve, the deficits and every mechanism reading are negative — so keying the bias on the
#     first sample's sign reaches AS1e alone.
_MONKEY_ESTIMATOR = '''
_orig_ee = endpoint_exponent


def _biased_ee(f, y):
    v = _orig_ee(f, y)
    return v + 0.5 if np.asarray(y, dtype=float)[0] > 0.0 else v


endpoint_exponent = _biased_ee
'''

# (c) MAKE THE TWO LADDER VALUE SETS IDENTICAL.  This is the defect GATE AO found sitting in three
#     gates for ten sessions; the guard against it is the one thing that says WHICH network is
#     being screened.
_MONKEY_DIVERGENCE = '''
AJ.ladder_divergence = lambda position="flat": (0, 12, {})
'''

# (d) TRUNCATE THE TILT WINDOWS.  AS1b's bit-identity is what licenses evaluating the ladder on
#     1308 of 6001 points instead of all of them — a 3.7x saving that the entire 7140-probe search
#     rests on.  Dropping five indices makes the subset and the full grid disagree.
_MONKEY_WINDOW = '''
_orig_wi = window_indices
window_indices = lambda centres, half: _orig_wi(centres, half)[:-5]
'''

# (e) MAKE EVERY PROBE FAIL THE VALIDITY COLUMNS.  AS3's frontier must not be readable from an
#     empty set (`empty-gate-must-fail`) — and its whole methodological point is that the
#     unvalidated top of the exponent table is an artefact, so a gate that would happily report a
#     frontier over nothing would be reporting the artefact.
_MONKEY_CLEAN_NONE = '''
clean_shape = lambda row: False
'''


ARMS = [
    # ---------------- REFUSAL ARMS ----------------------------------------
    ("AS1a  the tilt operator must be LINEAR on log-magnitude",
     "make `tilt_fine` quadratic.  This is the licence that lets the gate model the drain node\n"
     "    alone; without it every fixed block downstream would have to be modelled, and the\n"
     "    closed-form screen would not exist.",
     [(r'^def _die\(msg\):', _MONKEY_LICENCE + '\n\ndef _die(msg):')],
     2, "known answers failed", ),

    ("AS1b  the windowed-subset evaluation must be BIT-IDENTICAL",
     "drop five window indices.  The 7140-probe search only exists because the ladder need not be\n"
     "    evaluated where no tilt window reads it; the bar is bit-identity, not a tolerance,\n"
     "    because anything looser would hide a window that had drifted by one index.\n"
     "    ⚠ Anchored AFTER `window_indices` is defined, not at the first def in the file: a\n"
     "    monkey-patch injected above its own target is a NameError, which scores as WRONG EXIT\n"
     "    against a guard that was never reached (s110 — suspect the mutation before the guard).",
     [(r'^def drain_tilts\(', _MONKEY_WINDOW + '\n\ndef drain_tilts(')],
     2, "known answers failed: subset", ),

    ("AS1c  the shipped and drawn ladders must DIVERGE",
     "make the two element sets identical.  ⭐ This is the guard whose ABSENCE was GATE AO's\n"
     "    finding — AJ, AK and AN all screened the DRAWN network for ten sessions and nothing went\n"
     "    red, because nothing asserted the two sets differ.",
     [(r'^def _die\(msg\):', _MONKEY_DIVERGENCE + '\n\ndef _die(msg):')],
     2, "AS1c", ),

    ("AS1e  the exponent estimator must return an injected KNOWN exponent",
     "bias the estimator by +0.5 on all-positive curves, which is the f^3 known answer and\n"
     "    nothing else (so AS1f's earlier die cannot claim the arm — s119).  A reader that biased\n"
     "    upward would manufacture this gate's entire subject: every '>2' in AS3 would be the\n"
     "    instrument, and AL4 hit exactly this risk on the deficit side.",
     [(r'^def shape_columns\(d\):', _MONKEY_ESTIMATOR + '\n\ndef shape_columns(d):')],
     2, "known answers failed: estimator", ),

    ("AS1f  AL4's endpoint exponent must reproduce from AL4's own stored data",
     "raise the stored deficits to the power 1.2, which changes the exponent while leaving the\n"
     "    sign and the monotonicity intact.  ⚠ Scaling them would NOT work — an endpoint exponent\n"
     "    is a ratio and is scale-invariant, so a multiplicative arm here is vacuous by\n"
     "    construction (s110: suspect the mutation before the guard).",
     [(r'        _CTX\["deficits"\] = np\.array\(prim\["deficits"\], dtype=float\)',
       '        _CTX["deficits"] = -np.abs(np.array(prim["deficits"], dtype=float)) ** 1.2')],
     2, "AS1f", ),

    ("AS3  the frontier must not be readable from an empty validated set",
     "make every probe fail the validity columns.  The gate's methodological point is that the\n"
     "    unvalidated top of the exponent table is a zero-crossing artefact; a gate that reported\n"
     "    a frontier anyway would be reporting exactly that artefact.",
     [(r'^def gate_as1\(out\):', _MONKEY_CLEAN_NONE + '\n\ndef gate_as1(out):')],
     2, "AS3", ),

    ("AS4  the linearised basis must reproduce a finite-difference combined perturbation",
     "scale the Jacobian by 1.5.  AS4's span argument — that EVERY small perturbation of this\n"
     "    ladder makes one shape — is the only part of the gate that covers directions a finite\n"
     "    probe grid cannot enumerate, and it is worth nothing if the basis is not the derivative.",
     [(r'    B = np\.array\(cols\)\.T ',
       '    B = np.array(cols).T * 1.5 ')],
     2, "AS4", ),

    # ---------------- COMPUTED-VERDICT ARMS -------------------------------
    ("AS8-verdict  'decided on the SIZE of the element change' must be able to become "
     "'a physically-bounded joint point EXISTS'",
     "report every probe's fold change as 1.0, so the x1000 element moves that buy the steep\n"
     "    exponents count as drifts a mechanism could supply.  ⭐⭐ This is the arm that matters\n"
     "    most: the FIRST draft of this gate graded exponent against reach only, found a joint\n"
     "    point, and would have published 'this class is NOT refuted'.  The drift axis is what\n"
     "    decides it, so the branch that says so has to be able to say the opposite.",
     [(r'               drift=float\(max\(max\(fr, 1\.0 / fr\) for fr in fracs\)\),',
       '               drift=1.0,')],
     0, "A PHYSICALLY-BOUNDED JOINT POINT EXISTS", ),

    ("AS8-verdict  'the lever is real at a limit' must be able to become 'REFUTED ON SIZE'",
     "scale every probe's reach by 1e-4.  This gate's first finding is that the load side of the\n"
     "    divider genuinely reaches where AK/AJ/AN did not — a claim that separates it from three\n"
     "    prior refutations, and therefore one that must be computed rather than asserted.",
     [(r'               reach=float\(abs\(d\[iv\] / c\["budget"\]\)\) if c\["budget"\] else 0\.0,',
       '               reach=1e-4 * float(abs(d[iv] / c["budget"])) if c["budget"] else 0.0,')],
     0, "REFUTED ON SIZE", ),

    ("AS8-verdict  'not shape-refuted the way its predecessors were' must be able to become "
     "'REFUTED ON SHAPE'",
     "scale every MECHANISM exponent by 0.3, leaving the deficit's own (read in AS1 by a\n"
     "    different path) untouched.  The gate explicitly tells a reader NOT to quote gate 5's\n"
     "    single-pole bound against this class; that instruction is only worth having if the line\n"
     "    could have said the opposite.",
     [(r'    return \{"exponent": endpoint_exponent\(_ctx\(\)\["centres"\], d\),',
       '    return {"exponent": 0.3 * endpoint_exponent(_ctx()["centres"], d),')],
     0, "REFUTED ON SHAPE", ),

    ("AS6-verdict  'the added-element branch falls too' must be able to reach",
     "force the added-element sweep's validated set to a steep exponent.  A perturbation of a\n"
     "    network need not be a drift of one of its parts, and the added-element branch is the\n"
     "    half of the class that a component list would miss entirely — so its verdict must be\n"
     "    computed.  ⚠ This arm fabricates the reading rather than finding a steep capacitance,\n"
     "    which is stated rather than dressed up: it tests the BRANCH, not the physics.",
     [(r'    valid = \[r for r in rows if clean_shape\(r\) and r\["sign_ok"\]\]',
       '    valid = [dict(r, exponent=3.5) for r in rows]')],
     0, "THE ADDED-ELEMENT BRANCH REACHES ON SHAPE", ),

    ("AS7-verdict  'passes the GRUNT gate and is still refuted' must be able to become "
     "GRUNT-dependent",
     "give the candidate's own tilt change a 5 % GRUNT-dependent component.  ⭐ The methodological\n"
     "    result — sign-admissibility is NECESSARY, NOT SUFFICIENT — is the second-most quoted\n"
     "    thing GATE AK produced, and repeating it here is only meaningful if the gate could have\n"
     "    found the candidate GRUNT-dependent instead.",
     [(r'    dmech = tilts\(kwp, "flat"\) - base',
       '    dmech = (tilts(kwp, "flat") - base) * 1.05')],
     0, "THE CANDIDATE IS GRUNT-DEPENDENT", ),
]


def run(path):
    p = subprocess.run([sys.executable, path], cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ⛔⛔ EVERY MUTANT MUST WRITE ITS REPORT SOMEWHERE ELSE (s153).  A mutant runs `main()`, and
# `main()` writes the gate's report — so without this the LAST arm's forced-false output is left on
# disk under the real gate's filename.  The redirect REFUSES rather than silently no-opping,
# because a redirect that quietly fails restores the exact bug it was added to prevent.  The
# control run is redirected too: it must exercise the same code path as the arms.
def _redirect_report(text):
    out, n = re.subn(r'"analysis/reports/s155_ladder_zin_tilt\.json"',
                     f'"analysis/reports/_mut_s155_{os.getpid()}.json"', text)
    if n != 1:
        sys.exit("_mutate_gate_as: could not redirect the mutant's report path — refusing to run "
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
        for l in [l for l in out.strip().splitlines() if l.strip()][-8:]:
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
    stray = os.path.join(HERE, "reports", f"_mut_s155_{os.getpid()}.json")
    if os.path.exists(stray):
        os.remove(stray)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
