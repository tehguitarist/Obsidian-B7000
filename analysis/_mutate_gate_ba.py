#!/usr/bin/env python3.11
"""Mutation test for GATE BA (analysis/task_e_placement_gate.py).

GATE BA's headline is a REFUTATION of the architecture task E was scoped to reuse, and it rests on
a cancellation that is exact algebra.  That makes two failure modes uniquely dangerous here and
they are what most of these arms exist for:

  * **VACUITY.**  BA2 adds a probe section to every rung and requires the drive-tilt not to move.
    An INERT probe passes that trivially, so the headline would read "EXACTLY ZERO" for a gate
    that measured nothing.  BA1b is the guard; `ba1b-inert` is the arm that proves BA1b works.
  * **NARRATION.**  "a post-clipper section contributes NOTHING" is precisely the kind of sentence
    that gets hard-coded (s161 AX3 did exactly this, inside a gate written to apply the rule), so
    `ba2-verdict` breaks the physics and requires the OPPOSITE verdict to appear.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **That AF6's requirement is right.**  BA imports it from GATE AF's stored report; nothing here
    tests the requirement itself, only what a candidate would have to do to meet it.
  * **The pre-clipper route is SIZED, not screened.**  BA4's bound is necessary, never sufficient,
    and no arm can turn a necessary condition into a screen.
  * **The rendered curves themselves.**  BA1d checks they are finite and that the rungs differ; it
    cannot check the plugin is correct.  That is ctest's job, not a mutation runner's.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * `--json` has NO default, so a mutant invoked without it writes nothing and cannot leave a
    deliberately falsified report on disk wearing the real gate's name (s153).  ASSERTED below.
  * the mutant's PRIVATE RENDER DIR is redirected to a PID-unique path, so a mutated arm cannot
    poison the real gate's render cache -- and the redirect REFUSES if its pattern stops applying
    (a silent no-op restores the bug it prevents).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

Run:  python3.11 analysis/_mutate_gate_ba.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "task_e_placement_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_ba_{os.getpid()}.py")

# (name, expect_rc, must_contain, find, replace, why)
ARMS = [
    # ---- refusals ---------------------------------------------------------------------------
    ("ba0-privdir", 1, "GATE BA BA0 FAIL",
     '    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):',
     '    if True:',
     "point the private render dir at GATE W's published cache.  One run of that would re-render "
     "the artefacts GATE W's numbers came from (s159 AW0), so it must be a refusal and not a "
     "warning"),

    ("ba0-bleedfree", 1, "GATE BA BA0 FAIL",
     '    ("flat", "noon"): "level-1700_base-od.wav",',
     '    ("flat", "noon"): "ref-od.wav",',
     "swap in a capture at LEVEL noon.  Every statement in this gate is about the BLEED-FREE OD "
     "path (GATE K2: bleed vanishes only at LEVEL and BLEND max), and s151 measured that a "
     "LEVEL-noon set is ~44 % clean -- the gate must refuse rather than dilute"),

    ("ba1a-estimator", 1, "GATE BA BA1a FAIL",
     "    s, _n = AG.tilt_at(np.asarray(d), np.log2(W.GRID / f0), half)\n    return s",
     "    s, _n = AG.tilt_at(np.asarray(d), np.log2(W.GRID / f0), half)\n    return s * 0.97",
     "scale the tilt estimator by 3 %.  It must stop recovering an injected tilt -- if it does "
     "not, BA1a is comparing nothing and every slope in the gate is unvalidated"),

    # ⚠⚠ THE MOST IMPORTANT ARM.  Without BA1b, BA2's headline passes for an inert probe.
    ("ba1b-inert", 1, "GATE BA BA1b FAIL",
     "    return (4.0 * np.log2(grid / 1000.0)",
     "    return 0.0 * (4.0 * np.log2(grid / 1000.0)",
     "make BA2's probe IDENTICALLY ZERO.  BA2 would then report 'EXACTLY ZERO' having measured "
     "nothing at all -- `empty-gate-must-fail` in the one place it is invisible.  BA1b must catch "
     "it BEFORE BA2 prints"),

    ("ba1c-drawn", 1, "GATE BA BA1c FAIL",
     '    n_moved, total, _vals = AJ.ladder_divergence("flat")',
     '    n_moved, total, _vals = 0, 12, {}',
     "hide the shipped-vs-drawn divergence.  GATE AJ/AK/AN screened the DRAWN ladder for ten "
     "sessions (s149 AO); a gate that reads the ladder must refuse rather than repeat it"),

    ("ba1d-vacuous", 1, "GATE BA BA1d FAIL",
     "    return {sw: W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)) for sw in RUNGS}",
     "    one = W.smooth(*A.transfer_h1(A.seg_of(al, RUNGS[0]), ref))\n"
     "    return {sw: one for sw in RUNGS}",
     "make all four rungs identical.  Every drive-tilt would then be a STRUCTURAL zero and BA2's "
     "cancellation would pass for the wrong reason entirely"),

    ("ba4a-levels", 1, "GATE BA BA4a FAIL",
     '    lvl = {"sweep_clean": float(G.CLEAN_FR_LEVELS_DB[0])}',
     '    lvl = {}',
     "remove the imported stimulus levels.  The admissible range [0, dL] is undefined without "
     "them, and this gate's own first draft got that frame wrong -- so a missing level must "
     "refuse, never fall back to a guess"),

    # ---- computed verdicts ------------------------------------------------------------------
    # ⚠⚠ THE HEADLINE ARM.  BA2's sentence is exactly the kind that gets hard-coded.
    # ⚠ `expect_rc = 1`, and the first version of this arm had it as 0 and duly scored a WORKING
    # gate as GUARD DEAD.  BA2 is BOTH a computed verdict and a validity gate: if the cancellation
    # fails then the decomposition does not describe this build, so BA4's bound is unfounded and
    # everything below is meaningless — which is exactly s108's test for when a gate may exit.
    # So the arm requires BOTH the refusal AND the opposite verdict in the text; a hard-coded
    # "EXACTLY ZERO" would still fail it, on the string.  `suspect the mutation before the guard`
    # (s110/s114).
    ("ba2-verdict", 1, "NOT zero",
     "            pert = drive_tilt({sw: per[sw] + wild for sw in RUNGS}, vertex)",
     "            pert = drive_tilt({sw: per[sw] + (wild if sw == RUNGS[-1] else 0.0 * wild)\n"
     "                               for sw in RUNGS}, vertex)",
     "add the probe to the HOTTEST RUNG ONLY, i.e. make it level-dependent.  It then no longer "
     "cancels, and BA2 MUST say so -- this is what separates a measured cancellation from a "
     "sentence about one"),

    ("ba4a-premise", 0, "NOT everywhere inside",
     "        good = (s_lo >= -STEP_TOL) and (s_hi <= dL + STEP_TOL)",
     "        good = (s_lo >= -STEP_TOL) and (s_hi <= 0.5 * dL)",
     "halve the admissible ceiling.  The gamma bound's premise must then report itself as NOT "
     "established -- it is the one thing BA4b rests on, so it cannot be a fixed string"),

    ("ba5-refusal", 0, "READABLE",
     "    n_pos = sum(1 for c in coefs if c > 0)",
     "    n_pos = 0",
     "force the ATTACK coefficients to agree in sign.  BA5 must then report the switch as a "
     "READABLE dose-response -- the refusal has to be able to come back as its opposite, or it "
     "is narration (s161 AX3, committed inside a gate written to apply that rule)"),

    ("ba6-verdict", 0, "THE POST-CLIPPER SLOT IS NOT REFUTED",
     "    cancels = ba2(curves, vertex, out)",
     "    cancels = False",
     "force the cancellation to read as failed.  BA6's closing paragraph must invert with it "
     "rather than always announcing the refutation"),
]


def run(path, extra=()):
    return subprocess.run([sys.executable, path, *extra],
                          cwd=ROOT, capture_output=True, text=True, timeout=3600)


def main():
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()

    # s153: a mutant must not be able to write the real gate's report.
    if re.search(r'add_argument\("--json"[^)]*default=(?!None)', src):
        sys.exit("MUTATION HARNESS FAIL: --json has a non-None default, so a mutant would write a "
                 "deliberately falsified report over the real one (s153)")

    # Redirect the mutant's render dir.  A silent no-op here restores the bug it prevents, so the
    # substitution is asserted to apply.
    priv_pat = 'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s164_task_e")'
    if src.count(priv_pat) != 1:
        sys.exit("MUTATION HARNESS FAIL: cannot redirect the mutant's private render dir -- the "
                 "PRIV_DIR line has moved, and without the redirect every arm would render into "
                 "the real gate's cache")
    src_m = src.replace(priv_pat,
                        f'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", '
                        f'"s164_task_e_mut_{os.getpid()}")')

    print("=== CONTROL (unmutated, but rendering into the mutant's private dir) ===")
    with open(MUT, "w", encoding="utf-8") as fh:
        fh.write(src_m)
    c = run(MUT)
    if c.returncode != 0:
        print(c.stdout[-3000:], c.stderr[-2000:])
        sys.exit("MUTATION HARNESS FAIL: the UNMUTATED gate does not pass, so no failure below is "
                 "attributable to a mutation (s107)")
    print(f"  control OK (rc=0), {len(c.stdout.splitlines())} lines\n")

    passed = 0
    try:
        for name, rc_want, want, find, repl, why in ARMS:
            if src_m.count(find) != 1:
                print(f"  {name:<16} PATCH DID NOT APPLY ({src_m.count(find)} matches) -- the arm "
                      f"targets a line that has moved")
                continue
            with open(MUT, "w", encoding="utf-8") as fh:
                fh.write(src_m.replace(find, repl))
            r = run(MUT)
            ok_rc = (r.returncode != 0) if rc_want else (r.returncode == 0)
            body = r.stdout + r.stderr
            ok_txt = want in body
            verdict = ("PASS" if (ok_rc and ok_txt)
                       else ("NARRATED" if (ok_rc and not ok_txt and rc_want == 0)
                             else ("WRONG GUARD" if ok_rc else "GUARD DEAD")))
            passed += verdict == "PASS"
            print(f"  {name:<16} {verdict:<12} rc={r.returncode} "
                  f"want={'!=0' if rc_want else '==0'} | {want!r} "
                  f"{'found' if ok_txt else 'MISSING'}")
            if verdict != "PASS":
                print(f"      why the arm exists: {why}")
                print("      last output:", (body.strip().splitlines() or ["<empty>"])[-1][:170])
    finally:
        if os.path.exists(MUT):
            os.remove(MUT)

    print(f"\n{passed}/{len(ARMS)} arms PASS")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
