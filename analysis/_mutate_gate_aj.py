#!/usr/bin/env python3.11
"""Mutation test for GATE AJ (analysis/pre_clipper_tilt_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.  GATE AJ refuses with rc = 2 (its `_die`), so a
    mutant that exits 1 is a crash, not a fired guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  GATE AJ's deliverable is THREE
    refutations plus a joint conclusion, and a refutation that cannot become a non-refutation is
    narration -- so five of the twelve arms below drive AJ5 to its other outcomes, one per
    candidate plus the joint line plus the shape/size split inside candidate 1.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements, and satisfying one is the natural way to break the
    other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * ⚠ arms that need to move a STORED report's contents write a patched copy of the report to the
    scratch dir and point the gate at it with `--ai`, rather than editing the real one -- a
    mutation runner that mutates a shared artefact is a `rebaseline-all-derived-artefacts` bug
    waiting to happen.
  * ⚠ this gate reads only stored reports and closed-form arithmetic -- no render, no cache, so
    no arm here can trigger one.

Run:  python3.11 analysis/_mutate_gate_aj.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "pre_clipper_tilt_gate.py")
# ⚠ PID-unique.  The mutant must LIVE in analysis/ (sibling imports resolve) but a FIXED name
# means two concurrent runs of this file overwrite each other's mutant between the write and the
# subprocess launch — each arm then scores whatever the other run happened to write.  That is
# s133's "a concurrency-only bug inside a mutation test reads as a gate defect" in its
# cross-process form, and it bit this session: two runners were briefly alive at once.
TMP = os.path.join(HERE, f"_mutated_gate_aj_{os.getpid()}.py")
SCRATCH = tempfile.mkdtemp(prefix="aj_mut_")

AI_REPORT = os.path.join(REPO, "analysis", "reports", "s138_at_clipper_tilt.json")
AG_REPORT = os.path.join(REPO, "analysis", "reports", "s135_drive_tilt.json")


def _patched_report(path, mutate, tag):
    """Write a mutated COPY of a stored report to scratch and return its path."""
    d = json.load(open(path))
    mutate(d)
    out = os.path.join(SCRATCH, f"{tag}_{os.path.basename(path)}")
    json.dump(d, open(out, "w"))
    return out


def _drop_grunt(d):
    d["ai3"]["need"].pop("boost")


def _flip_defect(d):
    for k in d["ai3"]["need"]:
        d["ai3"]["need"][k] = -d["ai3"]["need"][k]


def _uncount_ag4(d):
    for r in d["ag4"]["rows"]:
        r[3] = 0.0


def _positive_deficit(d):
    for r in d["ag4"]["rows"]:
        if r[3]:
            r[2] = r[1] + 1.0        # PEDAL - MODEL becomes +1.0 dB/oct at a counted centre
            break


AI_DROP = _patched_report(AI_REPORT, _drop_grunt, "drop")
AI_FLIP = _patched_report(AI_REPORT, _flip_defect, "flip")
AG_UNCOUNT = _patched_report(AG_REPORT, _uncount_ag4, "uncount")
AG_POS = _patched_report(AG_REPORT, _positive_deficit, "pos")

# ⚠ The tilt ESTIMATOR lives in the imported `at_clipper_tilt_gate` (GATE AI), not in the gate
# under test, so the two arms that corrupt it must patch the DEPENDENCY rather than the file —
# s128's documented case.  Here the patch is injected at module level in the mutant itself
# (after the imports, before main), so there is no shared-state restore to get wrong: the
# override lives and dies with the subprocess.
_MONKEY = '''
def _mutated_tilt(db, f0, half):
    lg = np.log2(AI.FINE / f0)
    m = np.abs(lg) <= half
    x, y = lg[m], np.asarray(db)[m]
    A = np.vstack([x ** 2, x, np.ones(x.size)]).T
    c = np.linalg.lstsq(A, y, rcond=None)[0]
    return float({body})


AI.tilt_fine = _mutated_tilt
'''

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AJ1a  THE LICENCE — a candidate-independent block must cancel from the tilt CHANGE",
     "make the tilt estimator a NONLINEAR functional of the curve, by adding a term in the SQUARE "
     "of the fitted curvature.\n"
     "    ⚠ s138's AI1c arm was WRONG the first time and this one inherits the fix: a different "
     "LINEAR functional (say c1 + 0.05*c0) does NOT break additivity, so the fixed block still "
     "cancels and the guard is right to stay silent.  Only a genuinely nonlinear functional "
     "breaks `tilt(a+b) = tilt(a) + tilt(b)`.\n"
     "    Without AJ1a the gate's whole no-render simplification -- screening three candidates "
     "without ever rendering the treble ladder, IC2_A, the bridged-T or the Sallen-Keys -- would "
     "be an unexamined argument rather than a measured fact.",
     [(r'^AG_REPORT = ', _MONKEY.format(body="c[1] + 1.0e-3 * c[0] ** 2") + 'AG_REPORT = ')],
     2, "AJ1a", []),

    ("AJ1b  the tilt estimator must recover an injected tilt EXACTLY",
     "return 1.05x the linear coefficient -- still a LINEAR functional, so AJ1a stays silent and "
     "the two guards are shown to be independent rather than one guard checked twice.  Every "
     "number in AJ2-AJ4 is a tilt, so a mis-scaled estimator would print a plausible, monotone, "
     "entirely wrong set of reaches.",
     [(r'^AG_REPORT = ', _MONKEY.format(body="c[1] * 1.05") + 'AG_REPORT = ')],
     2, "AJ1b", []),

    ("AJ1c  the gate-node block must reduce to JfetStage.h's documented oracle at Cin -> 0",
     "scale R5 by 1.02 inside the gate block only.  This is the single check tying AJ2's Miller "
     "arithmetic to the SHIPPED J201 input network; without it AJ2 could screen a network the "
     "plugin does not have and report the difference as a device fact.",
     [(r'^    yg = 1\.0 / r5 \+ s \* cin$', '    yg = 1.0 / (r5 * 1.02) + s * cin')],
     2, "AJ1c", []),

    ("AJ1d  the ladder input impedance must be probe-independent",
     "make ladder_zin add a probe-proportional term.  Zin sets the Miller factor (1+|A|), and a "
     "probe-dependent Zin would mean the |A| < 1 finding -- the load-bearing structural half of "
     "AJ2 -- was an artefact of the extraction rather than a property of the ladder.",
     [(r'^    return zs_probe \* ratio / \(1\.0 - ratio\)$',
       '    return zs_probe * ratio / (1.0 - ratio) + 0.01 * zs_probe')],
     2, "AJ1d", []),

    ("AJ2c  membership — AG4 must still supply the 3 uncontaminated centres its finding rests on",
     "DATA-level: hand the gate an AG report with every AG4 centre un-counted.  The exponent "
     "screen is the half of AJ2 that generalises past this candidate, and it must refuse rather "
     "than quietly fall back on contaminated centres (whose windows reach ND's treble notch).",
     [], 2, "AJ2c", ["--ag", AG_UNCOUNT]),

    ("AJ2c  sign — a counted centre with a non-negative deficit must REFUSE, not take log of it",
     "DATA-level: set one counted centre's PEDAL-MODEL deficit to +1.0 dB/oct.  log|D| is only "
     "the right statistic while the deficit keeps one sign; a sign change there means the "
     "exponent is describing a crossing, not a steepening (s128's whole lesson on the THD "
     "surface), and the gate must say so instead of printing an exponent.",
     [], 2, "AJ2c", ["--ag", AG_POS]),

    ("main  membership — the stored defect must cover all three GRUNT positions",
     "DATA-level: drop `boost` from the AI report's defect.  The GRUNT-consistency screen is item "
     "6's fourth pre-registered gate and AJ4 rests on it entirely; with a position missing the "
     "screen is not evaluable and a partial answer would read as a full one (s129's three-outcome "
     "rule).",
     [], 2, "not all three GRUNT positions", ["--ai", AI_DROP]),

    ("AJ3  normalisation — a zero-peak shaped square must REFUSE, not divide by it",
     "zero the drive-stage transfer.  The slew rate is read off a waveform normalised to the "
     "rail, so a degenerate peak would silently emit a rate of 0 V/us and read as an infinite "
     "margin -- the flattering direction, and exactly `empty-gate-must-fail`.",
     [(r'^        coef = an \* h$', '        coef = an * h * 0.0')],
     2, "AJ3", []),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) -----------------------
    ("VERDICT  candidate 1 must be able to lose the SHAPE half independently of the SIZE half",
     "raise the single-pole exponent bound to 5.0, which makes the measured 2.84 admissible.  The "
     "verdict must then read REFUTED ON SIZE rather than ON SHAPE AND SIZE -- proving the shape "
     "clause is computed from the measured exponent and is not a sentence the gate always prints.",
     [(r'^SINGLE_POLE_EXPONENT_BOUND = 2\.0.*$', 'SINGLE_POLE_EXPONENT_BOUND = 5.0')],
     0, "REFUTED ON SIZE —", []),

    ("VERDICT  candidate 1 must be able to REACH",
     "raise the capacitance ceiling to 1 nF AND the exponent bound to 5.0, so both of AJ2's "
     "clauses are satisfied at once.  A candidate that cannot be made to reach is not being "
     "screened by this gate, only described by it.",
     [(r'^J201_CIN_CEILING_PF = 10\.0.*$', 'J201_CIN_CEILING_PF = 1000.0'),
      (r'^SINGLE_POLE_EXPONENT_BOUND = 2\.0.*$', 'SINGLE_POLE_EXPONENT_BOUND = 5.0')],
     0, "REACHES — the J201 gate capacitance", []),

    ("VERDICT  candidate 2's slew clause must be able to REACH",
     "drop the minimum-spec slew rate to 0.1 V/us, below the rate at the vertex.  This is the "
     "arm that proves the 12x margin is a comparison and not a constant: without it, 'slew does "
     "not engage' could be true of the sentence rather than of the part.",
     [(r'^import sk_mechanism_locus as AF .*$',
       'import sk_mechanism_locus as AF  # patched\nAF.TL07X_SR_MIN = 0.1')],
     0, "REACHES ON SLEW", []),

    ("VERDICT  candidate 3's SIGN refutation must invert when the DEFECT's sign inverts",
     "DATA-level: negate the stored defect at all three GRUNT positions.  AJ4's mechanism is "
     "POSITIVE everywhere, so against a positive defect the sign test must now PASS at all three "
     "-- which simultaneously tests AB5's rule that the target appears in the predicate as a "
     "VARIABLE, and tests the joint line, since one candidate ceasing to be refuted on sign must "
     "stop the run printing ALL THREE REFUTED.\n"
     "    ⚠ The size clause still binds, so the expected string is the mixed branch, not REACHES.",
     [], 0, "RIGHT SIGN EVERYWHERE, TOO SMALL", ["--ai", AI_FLIP]),
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
