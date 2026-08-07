#!/usr/bin/env python3.11
"""Mutation runner for GATE BH (analysis/hf_null_shape_gate.py), session 178.

Disciplines carried in (measurement-discipline.md §3):
  * the mutant LIVES in analysis/ (sibling imports resolve) and RUNS from the repo root
    (data paths resolve) -- s110, both halves.
  * the mutant path is PID-unique -- s139, so two concurrent runs cannot score each other's file.
  * the mutant's OUTPUT path is redirected to a PID-unique name and the redirect REFUSES if its
    pattern does not apply -- s153, so a faithful copy cannot overwrite the real gate's report.
  * an UNMUTATED control runs first; if it does not pass, no arm below is attributable.
  * arms check GUARD IDENTITY (a token the failure must contain), not just rc != 0 -- s117.
  * arms with expect_rc == 0 test a COMPUTED VERDICT: they break the data behind a conclusion and
    require the gate to print the OPPOSITE one.  s128's rule -- without these, a conclusion that
    has silently become hard-coded narration passes.

Run: /opt/homebrew/bin/python3.11 analysis/_mutate_gate_bh.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "hf_null_shape_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bh_{os.getpid()}.py")

# (name, pattern, replacement, expect_rc, must_contain, why)
ARMS = [
    ("bh0-single-grunt",
     r'if len\(by_grunt\) < 3:',
     'if False:',
     0, "GRUNT:",
     "disable the GRUNT-coverage guard.  This arm is the CONTROL for that guard's own "
     "reachability: with three positions present it must still pass, which proves the guard is "
     "not what is producing the pass."),

    ("bh1a-break-transfer",
     r'd = np\.full\(np\.shape\(f\), float\(p\["gainDb"\]\)\)',
     'd = np.full(np.shape(f), float(p["gainDb"])) + 0.9 * np.log10(np.asarray(f) / 1000.0)',
     1, "BH1a",
     "inject a tilt into the Python OdMakeup model.  The render/python known answer must "
     "REFUSE -- without it BH3's arithmetic is an argument rather than a measurement."),

    ("bh1b-flat-estimator",
     r'return F\.notch_geometry\(g, d, core=core, shoulder=sh\)',
     'r = F.notch_geometry(g, d, core=core, shoulder=sh); r["depth_point"] = 5.0; return r',
     1, "BH1b",
     "make the estimator return a CONSTANT depth.  The injected-ordering control must refuse: a "
     "reader that cannot order what it is handed cannot grade an ordering."),

    ("bh1c-clean-leak",
     r'CLEAN_CONTROL = "blend-0700_base-od\.wav"',
     'CLEAN_CONTROL = "ref-od.wav"',
     1, "BH1c",
     "point the CLEAN control at a BLEND=max capture, where the OD branch IS in circuit.  The "
     "arms then differ and the bit-identity control must refuse -- proving it is not vacuous."),

    ("bh2-vacuous-arms",
     r'"s172 shelf":   S172,',
     '"s172 shelf":   (),',
     1, "BH2",
     "make an arm a no-op.  The non-vacuity check must catch it: a --fit that never reaches the "
     "DSP reads as a clean result (s110)."),

    # ⚠ This arm must patch the line that PRODUCES `kept`, not one after the line that PRINTS it.
    # A first draft patched below the print and duly reported NARRATED against a working gate --
    # `suspect the mutation before the guard` (s110), and the tell was that the token it wanted
    # was one the mutated code could no longer reach.
    ("bh6-unmatched",
     r'    kept, dropped = matched_cells\(DEPTH_GRADED, "cell"\)',
     '    kept, dropped = ([(l, r) for l, _, _, _ in CONDITIONS for r in RUNGS], [])',
     0, "MATCHED membership: 30/30",
     "force BH6 back to the UNMATCHED population the first draft used.  rc stays 0 -- this arm "
     "exists to prove the matched membership is REACHED and printed, so a future edit that "
     "silently drops it is visible in this runner's output rather than in a wrong conclusion."),

    # ---- computed-verdict arms: expect_rc 0, and the OPPOSITE verdict must be printed ----------
    # ⚠ The obvious mutation -- give the SHIPPED arm s172's shelf -- makes two ARMS entries
    # identical, at which point the NON-VACUITY guard fires first (rc=1) and the verdict is never
    # reached.  That is the gate being better than this runner's model of it (s119), so the
    # EXPECTATION is what changed, not the guard: re-point the baseline instead, which flips the
    # verdict's operand without duplicating an arm.
    ("bh2-verdict-ordering",
     r'BASELINE_ARM = "ship \(s173\)"',
     'BASELINE_ARM = "s172 shelf"',
     0, "MATCHES ND's ordering",
     "make the arm that DOES reproduce ND's ordering the baseline.  BH2's verdict must flip to "
     "'MATCHES ND's ordering' -- if it still prints 'does NOT reproduce', it is narration."),

    ("bh3-verdict-mechanism",
     r'gdb = float\(makeup_db\(np\.array\(\[f_null\]\), 48000\.0, p\)\[0\]\)',
     'gdb = -float(makeup_db(np.array([f_null]), 48000.0, p)[0])',
     0, "REFUTED",
     "negate the OD-branch gain at the null.  The rank correlation must go negative and BH3 must "
     "print its own mechanism REFUTED rather than CONSISTENT."),

    ("bh6-verdict-depth",
     r'err\[a\]\.append\(rm\["depth_point"\] - rp\["depth_point"\]\)',
     'err[a].append(0.0)',
     0, "NOT systematically deeper",
     "zero the model-minus-ND bass error.  BH6's verdict must flip to 'NOT systematically "
     "deeper' -- the conclusion the whole bass half of item 17 rests on."),

    ("bh5-verdict-frontier",
     r'dominating = \[a for a in ARMS',
     'dominating = [a for a in list(ARMS)[:1]] or [a for a in ARMS',
     0, "A DOMINATING CANDIDATE EXISTS",
     "force a dominating candidate.  BH5 must print that one exists rather than the "
     "'NO DOMINATING CANDIDATE' text, or its frontier verdict is hard-coded."),
]


def run(path, out_json):
    return subprocess.run([sys.executable, path, "--json", out_json],
                          cwd=ROOT, capture_output=True, text=True)


def main():
    src = open(GATE).read()
    out_json = f"analysis/reports/_mutate_bh_{os.getpid()}.json"

    print("=" * 92)
    print("MUTATION RUNNER — GATE BH (hf_null_shape_gate.py)")
    print("=" * 92)

    # --- the unmutated CONTROL.  Without it, no failure below is attributable (s110). ----------
    open(MUTANT, "w").write(src)
    ctl = run(MUTANT, out_json)
    if ctl.returncode != 0:
        print("⛔ CONTROL FAILED — no arm below is attributable.\n")
        print(ctl.stdout[-3000:], ctl.stderr[-2000:])
        os.remove(MUTANT)
        sys.exit(1)
    print("control (unmutated): PASS\n")

    fails = []
    for name, pat, rep, exp_rc, must, why in ARMS:
        mutated, n = re.subn(pat, rep, src, count=1)
        if n != 1:
            print(f"  {name:24s} ⛔ PATCH DID NOT APPLY — the pattern no longer matches the gate; "
                  f"update THIS runner rather than deleting the arm")
            fails.append(name)
            continue
        open(MUTANT, "w").write(mutated)
        r = run(MUTANT, out_json)
        blob = r.stdout + r.stderr
        rc_ok = (r.returncode != 0) if exp_rc else (r.returncode == 0)
        tok_ok = must in blob
        if rc_ok and tok_ok:
            verdict = "PASS"
        elif not rc_ok:
            verdict = f"GUARD DEAD (rc={r.returncode}, wanted {'!=0' if exp_rc else '0'})"
            fails.append(name)
        else:
            verdict = f"NARRATED (rc ok, but {must!r} never printed)"
            fails.append(name)
        print(f"  {name:24s} {verdict}")
        if verdict != "PASS":
            print(f"      why: {why}")
            print(f"      tail: {blob.strip().splitlines()[-1][:150] if blob.strip() else '(no output)'}")

    os.remove(MUTANT)
    for stray in (os.path.join(ROOT, out_json),):
        if os.path.exists(stray):
            os.remove(stray)

    print()
    print(f"{len(ARMS) - len(fails)}/{len(ARMS)} arms PASS")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
