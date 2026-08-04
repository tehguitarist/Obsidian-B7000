#!/usr/bin/env python3.11
"""Mutation test for GATE AL (analysis/deficit_exponent_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.  GATE AL refuses with rc = 2 (its `_die`), so a
    mutant that exits 1 is a crash, not a fired guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's whole point is that it could
    have OVERTURNED two standing refutations, so "AJ2c survives" has to be a thing the gate
    computes rather than a sentence it prints -- five arms below drive AL3/AL4/AL5 to their other
    outcomes, one per verdict the gate emits.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements, and satisfying one is the natural way to break the
    other (s110).
  * the mutant path is PID-unique: a fixed name lets two concurrent runs score each other's
    mutant (s139).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * ⚠ the ESTIMATOR lives in the imported `vertex_curvature_gate` (GATE AH), not in the gate under
    test, so arms that corrupt it inject a module-level monkey-patch into the MUTANT after its
    imports (s139's form) -- there is no shared state to restore, because the override lives and
    dies with the subprocess.
  * ⚠ arms that need to move a STORED report write a patched COPY to scratch and point the gate at
    it with `--ag` / `--aj`, never editing the real one.
  * ⚠ this gate reads GATE W's RENDER CACHE.  No arm changes a render argument, so none can
    trigger a re-render (and none rebuilds anything -- `never-rebuild-while-a-render-is-in-flight`
    is not reachable from here).

Run:  python3.11 analysis/_mutate_gate_al.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "deficit_exponent_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_al_{os.getpid()}.py")
SCRATCH = tempfile.mkdtemp(prefix="al_mut_")

AG_REPORT = os.path.join(REPO, "analysis", "reports", "s135_drive_tilt.json")
AJ_REPORT = os.path.join(REPO, "analysis", "reports", "s139_pre_clipper_tilt.json")


def _patched_report(path, mutate, tag):
    d = json.load(open(path))
    mutate(d)
    out = os.path.join(SCRATCH, f"{tag}_{os.path.basename(path)}")
    json.dump(d, open(out, "w"))
    return out


def _uncount_ag4(d):
    for r in d["ag4"]["rows"]:
        r[3] = 0.0


def _sign_flip_ag4(d):
    for r in d["ag4"]["rows"]:
        if r[3]:
            r[2] = r[1] + 1.0            # make one counted centre's PEDAL-MODEL positive
            break


def _drop_aj_exponent(d):
    d["aj2"].pop("exponent")


def _bound_way_up(d):
    d["aj2"]["exponent_bound"] = 5.0     # nothing measured can beat it


def _bound_way_down(d):
    d["aj2"]["exponent_bound"] = -10.0   # everything beats it, uniformly


AG_UNCOUNT = _patched_report(AG_REPORT, _uncount_ag4, "uncount")
AG_POS = _patched_report(AG_REPORT, _sign_flip_ag4, "pos")
AJ_NOEXP = _patched_report(AJ_REPORT, _drop_aj_exponent, "noexp")
AJ_HIGH = _patched_report(AJ_REPORT, _bound_way_up, "high")
AJ_LOW = _patched_report(AJ_REPORT, _bound_way_down, "low")

# Injected after the mutant's imports; `AH` is already bound there.
_MONKEY = '''
_AL_REAL_TILT = AH.tilt_at


def _mutated_tilt(grid, db, f0, half):
    v = _AL_REAL_TILT(grid, db, f0, half)
    return None if v is None else {body}


AH.tilt_at = _mutated_tilt
'''

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AL1a  the estimator must recover an injected TILT exactly",
     "scale the returned slope by 1.05 in the IMPORTED estimator.  Every number in AL3-AL5 is a "
     "tilt difference, so a mis-scaled estimator would print a plausible, monotone, entirely "
     "wrong deficit curve -- and, because the exponent is a RATIO of deficits, a pure scaling "
     "would leave the exponent itself untouched and the error invisible below AL1.",
     [(r'^REPORT = ', _MONKEY.format(body="v * 1.05") + 'REPORT = ')],
     2, "AL1a", []),

    ("AL1b  the estimator must DISCRIMINATE the class bound from the measurement",
     "compress the deficit's dynamic range with a square root, which HALVES every exponent "
     "(2.000 -> 1.00, 2.840 -> 1.42) while leaving AL1a's pure-tilt recovery exact, so the two "
     "arms are shown to be independent.\n"
     "    ⚠ This is the arm the gate's credibility rests on.  An estimator that cannot separate "
     "an injected 2.000 from an injected 2.840 could have MANUFACTURED AJ2c's refutation, and no "
     "amount of extra centres would reveal it.",
     [(r'^    return \{"model": float\(mt\.mean\(\)\), "pedal": float\(pt\.mean\(\)\),$',
       '    _d = float(pt.mean() - mt.mean())\n'
       '    _d = (1.0 if _d >= 0 else -1.0) * abs(_d) ** 0.5\n'
       '    return {"model": float(mt.mean()), "pedal": float(pt.mean()),'),
      (r'^            "deficit": float\(pt\.mean\(\) - mt\.mean\(\)\),$',
       '            "deficit": _d,')],
     2, "AL1b", []),

    ("AL1c  the refuted class's own bound must come back 2.000",
     "give the real pole a u^1.5 numerator, so its finite-difference exponent reads 3 instead of "
     "2.  AL1c is the ONLY thing tying this gate's target to AJ2c's analytic bound; without it "
     "the gate could screen against a bound of its own invention and report the difference as a "
     "physics result.",
     [(r'^    return -k \* u / \(1\.0 \+ u\) if kind == "appear" else 2\.0 \* k \* u / \(1\.0 \+ u\) \*\* 2$',
       '    return -k * u ** 1.5 / (1.0 + u) if kind == "appear" else '
       '2.0 * k * u ** 1.5 / (1.0 + u) ** 2')],
     2, "AL1c", []),

    ("AL2  independent centres must actually be INDEPENDENT",
     "space them by HALF a window instead of a whole one, so consecutive fits share half their "
     "points.  The entire value of this gate over AG4 is that it quotes an n; overlapping windows "
     "are one curve sampled finely, and quoting 12 of them as 12 measurements would be a worse "
     "error than the n = 3 the gate exists to fix.",
     [(r'^        if f >= out\[-1\] \* 2\.0 \*\* \(2\.0 \* half\) - 1e-9:$',
       '        if f >= out[-1] * 2.0 ** (1.0 * half) - 1e-9:')],
     2, "AL2", []),

    ("AL2  every fit window must stay inside the feature-free band",
     "drop the half-window margin when choosing admissible centres, so the lowest window reaches "
     "below 1000 Hz into the bridged-T.  A slope read across a MIGRATING feature is that feature "
     "sliding through the window, not a tilt -- AG1c's rule, and the reason AG4 had only three "
     "centres in the first place.",
     [(r'^    lo, hi = SMOOTH_LO \* 2\.0 \*\* half, SMOOTH_HI \* 2\.0 \*\* -half$',
       '    lo, hi = SMOOTH_LO, SMOOTH_HI')],
     2, "reaches outside the feature-free band", []),

    ("AL1a  an under-sampled estimator must REFUSE, not crash",
     "raise the imported minimum point count to 20, above the 9 the primary window holds, so the "
     "estimator returns None everywhere.\n"
     "    ⚠ THIS ARM WAS AIMED AT AL2's primary-usable branch and is caught by AL1a instead — "
     "s119's case, the gate being better than the test's model of it, so the EXPECTATION is fixed "
     "rather than the guard.  AL1a evaluates the estimator AT the primary half-width, so any grid "
     "coarse enough to under-sample the primary refuses there first and AL2's branch is "
     "structurally unreachable; it is labelled in the gate as an invariant kept against a future "
     "refactor and explicitly NOT claimed as tested (s133).\n"
     "    What the arm does test is real and was a genuine defect when written: the first version "
     "died with `TypeError: unsupported operand type(s) for -: NoneType and NoneType`, which "
     "hands the next session a symptom instead of a reason (s117).",
     [(r'^REPORT = ', 'AH.MIN_PTS = 20\nREPORT = ')],
     2, "AL1a — the estimator is under-sampled", []),

    ("main  AG4 must still supply the 3 centres this gate audits",
     "DATA-level: hand it an AG report with every AG4 centre un-counted.  The gate's job is to "
     "audit a specific stored reading; if that reading is not there, it must refuse rather than "
     "silently audit something else.",
     [], 2, "uncontaminated AG4 centres", ["--ag", AG_UNCOUNT]),

    ("main  AJ2c's stored exponent must be present, never transcribed",
     "DATA-level: remove aj2.exponent from the s139 report.  A gate that falls back on a "
     "hardcoded 2.84 would be checking a handover against itself.",
     [], 2, "will not transcribe", ["--aj", AJ_NOEXP]),

    ("AL1d  AG4's own stored deficits must be single-signed to be auditable",
     "DATA-level: make one counted AG4 centre's PEDAL-MODEL deficit positive.  log|D| is only the "
     "right statistic while the deficit keeps one sign, and the gate must say the source number "
     "is unreconstructable rather than take a log across a crossing.",
     [], 2, "AG4's own stored deficits change sign", ["--ag", AG_POS]),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) -----------------------
    ("VERDICT  AL4 must be able to say AJ2c DOES NOT SURVIVE",
     "DATA-level: raise the stored class bound to 5.0, which nothing measured can beat.  This is "
     "the arm that proves the headline is a comparison against an IMPORTED bound and not a "
     "sentence the gate always prints -- and it is the outcome this whole session was run to "
     "make possible, so if it cannot be reached the audit was decorative.",
     [], 0, "DOES NOT SURVIVE", ["--aj", AJ_HIGH]),

    ("VERDICT  AL4's UNIFORMITY clause must be able to come back clean",
     "DATA-level: drop the stored bound to -10, so every pair beats it.  AL4's second verdict is "
     "a correction to AJ2c's PHRASING rather than to its conclusion, and a correction that cannot "
     "become a non-correction is narration.",
     [], 0, "UNIFORMLY too", ["--aj", AJ_LOW]),

    # ⚠ BOTH AL3 ARMS ARE CONDITIONED ON `inject is None`.  `deficit_at` serves AL1b's synthetic
    # known answer as well as the real measurement, so an unconditional perturbation shifts the
    # INJECTED exponents too and AL1b refuses before AL3 is reached — s119 again, and the honest
    # fix is to make the mutation touch only the measurement it is aimed at rather than to weaken
    # AL1b.  Both arms failed exactly this way when first written.
    ("VERDICT  AL3's non-monotonicity must be MEASURED, not asserted",
     "scale each deficit by (f0/1000)^8, making |D| monotone increasing by construction "
     "(the measured fall is a factor 4.55 over a 1.26x frequency ratio, so an exponent below "
     "~6.6 does not overcome it — a weaker arm reads NARRATED and tests nothing).  AL3's "
     "finding -- that the deficit has an interior minimum AG4's three centres could never have "
     "seen -- is the session's second result, and it must be able to come back False.",
     [(r'^            "deficit": float\(pt\.mean\(\) - mt\.mean\(\)\),$',
       '            "deficit": float(pt.mean() - mt.mean())\n'
       '                       * ((f0 / 1000.0) ** 8 if inject is None else 1.0),')],
     0, "monotone increasing across ALL centres: True", []),

    ("VERDICT  AL3's SIGN scan must be able to fire",
     "flip the deficit's sign above 2 kHz.  A single-signed verdict that cannot become a "
     "sign-change verdict says nothing about the data, and the sign scan is what licenses every "
     "log below it.",
     [(r'^            "deficit": float\(pt\.mean\(\) - mt\.mean\(\)\),$',
       '            "deficit": float(pt.mean() - mt.mean())\n'
       '                       * (-1.0 if (f0 > 2000.0 and inject is None) else 1.0),')],
     0, "THE DEFICIT CHANGES SIGN", []),

    ("VERDICT  AL5 must be able to find a SHIPPED resonance that reaches",
     "retune the 3.3 kHz Sallen-Key's caps by a common factor 1.335, which moves f0 3337 -> 2500 "
     "Hz and leaves Q unchanged (scaling BOTH caps scales numerator and denominator of Q "
     "alike).  That puts the vertex at w = 1.17, inside the admissible band AL5 itself derives.\n"
     "    ⚠ Without this arm, 'no shipped resonance reaches it' could be a property of the "
     "sentence rather than of the shipped values -- and the admissible band printed beside it "
     "would be unfalsifiable decoration.",
     [(r'^    \("IC4_A  R26/R27/C19/C20", 22e3, 47e3, 2\.2e-9, 1\.0e-9\),$',
       '    ("IC4_A  R26/R27/C19/C20", 22e3, 47e3, 2.937e-9, 1.335e-9),')],
     0, "a SHIPPED Sallen-Key reaches", []),
]


def run(path, extra):
    p = subprocess.run([sys.executable, path, "--json", os.path.join(SCRATCH, "out.json")] + extra,
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()

    open(TMP, "w").write(src)
    rc, out = run(TMP, [])
    tail = [l for l in out.strip().splitlines() if l.strip()][-1:]
    print(f"CONTROL   rc={rc}, gate passes from {os.path.relpath(TMP, REPO)}  "
          f"{'✓' if rc == 0 else '✗ ' + str(tail)}")
    if rc != 0:
        print("\n⛔ the UNMUTATED control does not pass — no failure below is attributable to any "
              "mutation (s107).  Fix this first.")
        return 1

    bad = 0
    for name, why, patches, exp_rc, must, extra in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches) — the arm is testing "
                      f"nothing.  Pattern: {pat[:70]}")
                bad += 1
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue
        open(TMP, "w").write(mutated)
        rc, out = run(TMP, extra)
        hit = must in out
        ok = (rc == exp_rc) and hit
        if ok:
            if exp_rc == 0:
                print(f"✓ {name}\n    VERDICT CHANGED as required (rc=0, saw '{must}')")
            else:
                print(f"✓ {name}\n    REFUSED as required (rc={rc}, saw '{must}')")
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
            for l in [l for l in out.strip().splitlines() if l.strip()][-3:]:
                print(f"      | {l[:110]}")

    if os.path.exists(TMP):
        os.remove(TMP)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
