#!/usr/bin/env python3.11
"""Mutation test for GATE AK (analysis/j201_shaper_tilt_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.  GATE AK refuses with rc = 2 (its `_die`), so a
    mutant that exits 1 is a crash, not a fired guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  GATE AK's deliverable is THREE
    refutations, a joint conclusion and a sign-gate reading, and a refutation that cannot become
    a non-refutation is narration -- so four of the twelve arms below drive AK2/AK3/AK4/AK5 to
    their other outcomes.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements, and satisfying one is the natural way to break the
    other (s110).
  * the mutant path is PID-UNIQUE (s139): a fixed name lets two concurrent runs overwrite each
    other's mutant between the write and the subprocess launch, and each arm then scores
    whatever the other run wrote.
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * arms that move a STORED report write a patched COPY to scratch and point the gate at it,
    rather than editing the real one.
  * ⚠ two arms corrupt machinery that lives in an IMPORTED module (the tilt estimator is GATE
    AI's, the ladder impedance is GATE AJ's), so they inject a module-level monkey-patch into
    the mutant itself, after its imports -- s128's "mutate the dependency" case, in the form
    that leaves no shared state to restore (the override dies with the subprocess).
  * ⚠ this gate reads only stored reports and closed-form arithmetic -- no render, no cache, so
    no arm here can trigger one.

Run:  python3.11 analysis/_mutate_gate_ak.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "j201_shaper_tilt_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_ak_{os.getpid()}.py")
SCRATCH = tempfile.mkdtemp(prefix="ak_mut_")

AG_REPORT = os.path.join(REPO, "analysis", "reports", "s135_drive_tilt.json")
AH_REPORT = os.path.join(REPO, "analysis", "reports", "s137_vertex_curvature.json")
AI_REPORT = os.path.join(REPO, "analysis", "reports", "s138_at_clipper_tilt.json")


def _patched_report(path, mutate, tag):
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


def _tiny_budget(d):
    d["ah7"]["tilt_max_db_oct"] = -0.001


AI_DROP = _patched_report(AI_REPORT, _drop_grunt, "drop")
AI_FLIP = _patched_report(AI_REPORT, _flip_defect, "flip")
AG_UNCOUNT = _patched_report(AG_REPORT, _uncount_ag4, "uncount")
AG_POS = _patched_report(AG_REPORT, _positive_deficit, "pos")
AH_TINY = _patched_report(AH_REPORT, _tiny_budget, "tiny")

_MONKEY_TILT = '''
def _mutated_tilt(db, f0, half):
    lg = np.log2(AI.FINE / f0)
    m = np.abs(lg) <= half
    x, y = lg[m], np.asarray(db)[m]
    A = np.vstack([x ** 2, x, np.ones(x.size)]).T
    c = np.linalg.lstsq(A, y, rcond=None)[0]
    return float({body})


AI.tilt_fine = _mutated_tilt
'''

_MONKEY_ZIN = '''
_orig_ladder_zin = AJ.ladder_zin


def _mutated_ladder_zin(f, position="flat", zs_probe=1.0e3):
    return _orig_ladder_zin(f, position, zs_probe) + 0.01 * zs_probe


AJ.ladder_zin = _mutated_ladder_zin
'''

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AK1a  THE LICENCE — a gm-independent block must cancel from the tilt CHANGE",
     "make the tilt estimator a NONLINEAR functional of the curve, by adding a term in the SQUARE "
     "of the fitted curvature.\n"
     "    ⚠ inherits s138/s139's fix: a different LINEAR functional does NOT break additivity, so "
     "the fixed block still cancels and the guard is right to stay silent.  Only a genuinely "
     "nonlinear functional breaks `tilt(a+b) = tilt(a) + tilt(b)`.\n"
     "    Without AK1a this gate's whole no-render simplification -- screening the J201 without "
     "ever rendering the treble ladder, IC2_A, the clipper or the Sallen-Keys -- would be an "
     "unexamined argument rather than a measured fact.",
     [(r'^AG_REPORT = ', _MONKEY_TILT.format(body="c[1] + 1.0e-3 * c[0] ** 2") + 'AG_REPORT = ')],
     2, "AK1a", []),

    ("AK1b  the tilt estimator must recover an injected tilt EXACTLY",
     "return 1.05x the linear coefficient -- still LINEAR, so AK1a stays silent and the two "
     "guards are shown to be independent rather than one guard checked twice.  Every number in "
     "AK2-AK5 is a tilt, so a mis-scaled estimator would print a plausible, monotone, entirely "
     "wrong set of reaches.",
     [(r'^AG_REPORT = ', _MONKEY_TILT.format(body="c[1] * 1.05") + 'AG_REPORT = ')],
     2, "AK1b", []),

    ("AK1c  jfet_source_z must BE the drain network this gate assumes",
     "drop the rq2 shunt from the predicted expression, so the gate's assumed network and the "
     "shipped one disagree.  Every reach in AK3 is computed from Z_drain; if the assumed network "
     "were wrong the gate would screen a stage the plugin does not have and report the difference "
     "as a device fact.",
     [(r'^    pred = 1\.0 / \(1\.0 / \(ro \+ rp / \(1\.0 \+ s_f \* J_R6 \* J_C3\)\) \+ 1\.0 / rq2\)$',
       '    pred = ro + rp / (1.0 + s_f * J_R6 * J_C3)')],
     2, "AK1c", []),

    ("AK1d  the BARE-device identity Gm*Rout = gm*ro must be flat at every gm",
     "raise k to the 1.1 power in Rout only, so Gm*Rout = gm*ro*k^0.1 and the identity fails.  "
     "This is the single check tying the gate's model of the stage to JfetStage.h's own class "
     "note; without it AK3 could be sizing a degeneration network the shipped stage does not "
     "implement.",
     [(r'^    return 20\.0 \* np\.log10\(np\.abs\(\(gm / k_of_s\(f, gm\)\) \* \(ro \* k_of_s\(f, gm\)\)\)\)$',
       '    return 20.0 * np.log10(np.abs((gm / k_of_s(f, gm)) * (ro * k_of_s(f, gm) ** 1.1)))')],
     2, "AK1d", []),

    ("AK1e  the ladder input impedance must be probe-independent",
     "make ladder_zin add a probe-proportional term (patched in the IMPORTED GATE AJ module).  "
     "Zin sets Z_drain, so a probe-dependent Zin would mean AK3's whole size column was an "
     "artefact of the extraction rather than a property of the ladder.",
     [(r'^AG_REPORT = ', _MONKEY_ZIN + 'AG_REPORT = ')],
     2, "AK1e", []),

    ("AK3b  membership — AG4 must still supply the 3 uncontaminated centres its finding rests on",
     "DATA-level: hand the gate an AG report with every AG4 centre un-counted.  The shape screen "
     "is the load-bearing half of AK3, and it must refuse rather than quietly fall back on "
     "contaminated centres (whose windows reach ND's treble notch).",
     [], 2, "AK3b", ["--ag", AG_UNCOUNT]),

    ("AK3b  sign — a counted centre with a non-negative deficit must REFUSE, not take log of it",
     "DATA-level: set one counted centre's PEDAL-MODEL deficit to +1.0 dB/oct.  log|D| is only "
     "the right statistic while the deficit keeps one sign; a sign change means the exponent is "
     "describing a crossing, not a steepening (s128's lesson on the THD surface), and the gate "
     "must say so instead of printing an exponent.",
     [], 2, "AK3b", ["--ag", AG_POS]),

    ("main  membership — the stored defect must cover all three GRUNT positions",
     "DATA-level: drop `boost` from the AI report's defect.  AK5 reports item 6's fourth "
     "pre-registered gate; with a position missing the screen is not evaluable and a partial "
     "answer would read as a full one (s129's three-outcome rule).",
     [], 2, "not all three GRUNT positions", ["--ai", AI_DROP]),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) -----------------------
    ("VERDICT  route 1's inertness must be a property of a CONSTANT gain, not a sentence",
     "apply the shaper's gain as a frequency-dependent TILT instead of a constant offset.  Route "
     "1's whole claim is that a memoryless shaper is a uniform gain change and therefore cannot "
     "move a vertex; if the gate printed that however the gain were applied, it would be "
     "narrating AB2 rather than measuring it.",
     [(r'^        d = abs\(AI\.tilt_fine\(base \+ g_db, f0, half\) - t0\)$',
       '        d = abs(AI.tilt_fine(base + g_db * np.log2(AI.FINE / f0), f0, half) - t0)')],
     0, "ROUTE 1 IS NOT INERT", []),

    ("VERDICT  route 2 must be able to lose the SHAPE clause independently of the SIZE clause",
     "force shape_refuted False.  The verdict must then fall back to REFUTED ON SIZE rather than "
     "ON SHAPE AND SIZE -- proving the shape clause is computed from the measured exponents and "
     "is not a sentence the gate always prints.",
     [(r'^    shape_refuted = max\(mech_pair\) < 0\.0 < min\(def_pair\)$',
       '    shape_refuted = False')],
     0, "REFUTED ON SIZE —", []),

    ("VERDICT  route 3 must be able to REACH, and the JOINT line must follow it",
     "DATA-level: hand the gate an AH report whose budget is -0.001 dB/oct, so the shelf's own "
     "0.027 dB variation clears it.  This tests two things at once: that AK4's class bound is a "
     "COMPARISON against the budget rather than a constant, and that AK6 stops printing ALL "
     "THREE REFUTED the moment one route survives.",
     [], 0, "REACHES — the shelf varies enough", ["--ah", AH_TINY]),

    ("VERDICT  AK5's sign reading must invert when the DEFECT's sign inverts",
     "DATA-level: negate the stored defect at all three GRUNT positions.  AK5's mechanism is "
     "NEGATIVE everywhere, so against a positive defect the sign agreement must drop to 0 of 3 "
     "-- which tests AB5's rule that the target appears in the predicate as a VARIABLE.  Without "
     "it, 'passes the sign gate 3/3' could be a property of the sentence rather than of the "
     "comparison, and that reading is the whole methodological point of AK5.",
     [], 0, "sign agreement : 0 of 3", ["--ai", AI_FLIP]),
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
