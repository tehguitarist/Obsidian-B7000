#!/usr/bin/env python3.11
"""Mutation test for GATE BB (analysis/preclip_preemph_gate.py).

GATE BB refutes route (i) — a FIXED pre-clipper pre-emphasis — and it does so on a statistic the
gate was NOT built to test.  That history is why several of these arms exist in the shape they do:

  * The gate opened on a SIGN hypothesis (a fixed dP' delivers a correction whose sign tracks the
    clipper's dgamma, which reverses across the DRIVE knob).  **That hypothesis FAILED** — only 2
    of 6 probes flip.  The refutation came from BB4 instead, on SIZE CONSISTENCY.  So `bb3-sign`
    and `bb6-verdict` both matter: the sign branch must still be able to fire, and the verdict
    must be driven by the statistic that actually decided it.
  * The conclusion generalises from six ladder probes to "any section" ONLY because the transfer
    coefficient is a property of the chain.  `bb4-mix` guards the screen that makes that readable.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **Route (ii) is untouched.**  A LEVEL-DEPENDENT section has no fixed dP' and nothing here
    bounds it — that is the point of the verdict, not a gap in it.
  * **AF6's requirement** is imported from GATE AF's stored report; no arm tests it.
  * **The probes are not proposals.**  BB5's collateral prices what moving P' near the vertex
    costs at all; a shipped section would be shaped to minimise it, and no arm can model that.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path and its PRIVATE RENDER DIR are both PID-UNIQUE (s139/s153), and the render
    redirect REFUSES if its pattern stops applying.
  * `--json` has NO default, so a mutant cannot leave a falsified report wearing the real name.
  * an unmutated CONTROL runs first (s107); failures are scored on the guard's own tag (s117).

Run:  python3.11 analysis/_mutate_gate_bb.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "preclip_preemph_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_bb_{os.getpid()}.py")

ARMS = [
    # ---- refusals ---------------------------------------------------------------------------
    # ⚠⚠ THE MOST IMPORTANT REFUSAL.  This is the s149 defect class: a gate that writes one
    # constant while its closed form scales a different number runs fine and prints plausible,
    # monotone nonsense.  Every dP' in the gate — i.e. every denominator — depends on it.
    ("bb0-correspond", 1, "GATE BB BB0 FAIL",
     '    ("C5 x0.25", "trebleC5", "C5", 0.25),',
     '    ("C5 x0.25", "trebleC5", "C9", 0.25),',
     "point one probe's closed form at a DIFFERENT ladder element from the constant it writes.  "
     "The gate must refuse rather than compute a coefficient whose numerator and denominator "
     "describe different perturbations (s149 AO)"),

    ("bb0-bleedfree", 1, "GATE BB BB0 FAIL",
     '    ("DRIVE", "noon"): "level-1700_base-od.wav",',
     '    ("DRIVE", "noon"): "ref-od.wav",',
     "swap in a LEVEL-noon capture.  s151 measured that set ~44 % clean, and every statement here "
     "is about the bleed-free OD path (GATE K2) — the gate must refuse rather than dilute"),

    ("bb1b-baseline", 1, "GATE BB BB1b FAIL",
     "        got = drive_tilt(base[k], vertex)",
     "        got = drive_tilt(base[k], vertex) + 1e-6",
     "move the baseline by 1e-6 dB/oct against GATE BA's STORED value.  A baseline that has "
     "silently drifted makes every delivered/required comparison a fiction (s77's SHIP_RECORD)"),

    ("bb1c-floor", 1, "GATE BB BB1c FAIL",
     '    ("R12 x4.0", "trebleLadderR12", "R12", 4.0),',
     '    ("R12 x4.0", "trebleLadderR12", "R12", 1.02),',
     "shrink a probe until its |dP'| falls under the floor IMPORTED from BA5.  A coefficient "
     "computed on a denominator at its own floor is exactly what GATE BA5 refused, so this gate "
     "must refuse it too rather than quoting the ratio"),

    ("bb1d-inert", 1, "GATE BB BB1d FAIL",
     '_ek, inert_spec = INERT',
     '_ek, inert_spec = ("C5 sub", "trebleC5", "C5", ("abs", 4e-9))',
     "replace the INERT control with a probe that really does change the render.  `trebleC8` is "
     "out of circuit at ATTACK flat, so a non-zero change there would mean the probe mechanism "
     "reaches something it should not — the gate must refuse"),

    ("bb4-mix", 1, "GATE BB BB4 FAIL",
     "MIX_MULT = 10.0",
     "MIX_MULT = 0.2",
     "tighten the level-dominance screen until almost no probe survives.  With fewer than three "
     "slope probes the coefficient cannot be shown to be a property of the CHAIN, and the "
     "generalisation to un-rendered sections fails — so the gate must refuse, not narrow quietly"),

    # ---- computed verdicts --------------------------------------------------------------------
    # The gate's opening hypothesis FAILED on real data, so this arm proves the branch still works
    # — otherwise "sign does not refute it" would be indistinguishable from a dead branch.
    ("bb3-sign", 0, "REFUTED ON THIS AXIS",
     "            npos = sum(1 for v in vs if v > 0)",
     "            npos = 1 if len(vs) > 1 else 0",
     "force every probe to look like a sign-flipper.  BB3's REFUTED-on-sign branch must fire — "
     "the real data does NOT take it (2 of 6), so without this arm a dead branch and a true "
     "negative are the same output"),

    ("bb4-collapse", 0, "IS NOT REFUTED",
     "        needed[k] = req[k] / medc[k]",
     "        needed[k] = req[k] / medc[('DRIVE', 'min')]",
     "give every condition the SAME coefficient, so one fixed dP' would serve them all.  The "
     "size verdict must come back as NOT REFUTED — it is the statistic the whole conclusion "
     "rests on and cannot be a fixed string"),

    # ⚠ The first version of this arm was `lost = [] or <original>`, which is a NO-OP because an
    # empty list is falsy and `or` falls straight through — it scored a working gate as NARRATED.
    # `suspect the mutation before the guard` (s110/s114).  Mutating the COMPARISON instead makes
    # the condition unsatisfiable (a prominence is never below minus the shipped one).
    ("bb5-collateral", 0, "(none)",
     'if any(rows[l][i][1] < 0.5 * rows["SHIPPED"][i][1] for i in range(len(feats)))]',
     'if any(rows[l][i][1] < -1.0 * rows["SHIPPED"][i][1] for i in range(len(feats)))]',
     "make the collateral screen find nothing.  BB5 must say so rather than always reporting "
     "features lost — GATE Y's finding is being re-measured here, not restated"),
]


def run(path, extra=()):
    return subprocess.run([sys.executable, path, *extra],
                          cwd=ROOT, capture_output=True, text=True, timeout=5400)


def main():
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()

    if re.search(r'add_argument\("--json"[^)]*default=(?!None)', src):
        sys.exit("MUTATION HARNESS FAIL: --json has a non-None default, so a mutant would write a "
                 "deliberately falsified report over the real one (s153)")

    priv = 'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s165_preclip")'
    if src.count(priv) != 1:
        sys.exit("MUTATION HARNESS FAIL: cannot redirect the mutant's private render dir — the "
                 "PRIV_DIR line has moved, and without the redirect every arm would render into "
                 "the real gate's cache")
    src_m = src.replace(priv, f'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", '
                              f'"s165_preclip_mut_{os.getpid()}")')

    print("=== CONTROL (unmutated, rendering into the mutant's private dir) ===")
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
                print(f"  {name:<17} PATCH DID NOT APPLY ({src_m.count(find)} matches) -- the arm "
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
            print(f"  {name:<17} {verdict:<12} rc={r.returncode} "
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
