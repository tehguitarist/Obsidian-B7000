#!/usr/bin/env python3.11
"""Mutation test for GATE BC (analysis/od_drive_tilt_gate.py).

GATE BC is the ACCEPTANCE test for a SHIPPED stage, so its verdicts have already become constants
in `src/dsp/FitParams.h` and a comment block in `src/dsp/OdDriveTilt.h`.  That is the strongest
possible reason for every one of them to be computed rather than narrated, and it is why five arms
carry `expect_rc == 0`.

⚠ A note before the arm list, because this gate's own runner tripped on it once: BC's `note()`
correctly makes the WHOLE gate exit `rc=1` when the shipped stage fails ANY of item 6's own three
gates -- an ACCEPTANCE gate failing its acceptance criteria is a validity condition for the
gate's PURPOSE, the same carve-out GATE BA's `ba2-verdict` needed (s108).  So `bc1c-clean`,
`bc2-ceiling`, `bc3-gate1` and `bc4-overshoot` all expect `rc != 0` even though they are testing
computed OUTCOMES -- the text they must contain is what proves the outcome is computed rather than
narrated, and the exit code is what proves the acceptance gate actually gates.

⚠⚠ THE TWO ARMS THAT MATTER MOST, and why:
  * `bc1c-clean` — gate 3 (CLEAN bit-identical) is the ONE gate that is true *by construction*
    (the stage is only wired into the OD path), which makes it exactly the kind of check that can
    quietly become a tautology.  The arm makes the clean render differ and requires the gate to
    say so.
  * `bc1b-gate` — the whole gate rests on `--fit odTiltEnabled=0` really disabling the stage.  If
    it did not, OFF and ON would both carry the correction and every "delivered" number would be a
    difference of two identical things.  BC1b catches that by reproducing GATE BA's STORED
    baseline, and this arm proves BC1b fires.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **The matrix cost.**  BC deliberately does not price it; `comprehensive_report.py` does, and
    the trade is a user decision.  No arm here can substitute for that.
  * **AF6's requirement and GATE W6's pedal walk** are IMPORTED; nothing here tests them.
  * **Musical behaviour.**  The envelope's time constant is not graded by anything in this gate —
    a sweep has constant amplitude, so the gate is blind to attack/release entirely.

Mechanics (s110/s139/s153/s107/s117), same as the neighbouring runners: the mutant lives in
analysis/ and runs from the repo root, its path and its private render dir are PID-unique, the
render redirect REFUSES if its pattern stops applying, an unmutated control runs first, and
failures are scored on the guard's own tag.

Run:  python3.11 analysis/_mutate_gate_bc.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "od_drive_tilt_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_bc_{os.getpid()}.py")

ARMS = [
    # ---- refusals ---------------------------------------------------------------------------
    ("bc0-bleedfree", 1, "GATE BC BC0 FAIL",
     '    ("DRIVE", "noon"): "level-1700_base-od.wav",',
     '    ("DRIVE", "noon"): "ref-od.wav",',
     "swap in a LEVEL-noon capture.  Every number here is about the bleed-free OD path (GATE K2, "
     "and s151 measured a LEVEL-noon set ~44 % clean) — the gate must refuse, not dilute"),

    # ⚠⚠ the arm that protects the gate's own premise.
    ("bc1b-gate", 1, "GATE BC BC1b FAIL",
     '             + ["--fit", f"odTiltEnabled={1 if on else 0}"])',
     '             + ["--fit", "odTiltEnabled=1"])',
     "make the OFF arm render with the stage ON.  Every 'delivered' number would become a "
     "difference of two identical renders, i.e. zero, and the gate would report a stage that "
     "does nothing as one that does nothing wrong.  BC1b must catch it via GATE BA's baseline"),

    ("bc1a-estimator", 1, "GATE BC BC1a FAIL",
     "import task_e_placement_gate as BA       # noqa: E402  slope(), fingerprint(), the PRIV rules",
     "import task_e_placement_gate as BA       # noqa: E402\n"
     "_orig_slope = BA.slope\nBA.slope = lambda d, f0, half=BA.HALF: _orig_slope(d, f0, half) * 0.97",
     "scale the tilt estimator by 3 %.  It must stop recovering an injected tilt — otherwise "
     "BC1a is comparing nothing and every slope in the gate is unvalidated"),

    # ⚠ The first version of this arm lowered the threshold BELOW real d_od (~4.7 dB), which
    # is `suspect-the-mutation-before-the-guard` in its purest form: the mutated threshold and
    # the original ONE BOTH sit below the real value, so neither fires and the arm is vacuous
    # regardless of which line is live.  Raising it ABOVE the real value instead forces the
    # guard to fire, proving it CAN — the correct direction for a floor check.
    ("bc1d-vacuous", 1, "GATE BC BC1d FAIL",
     "    if d_od < 0.1:",
     "    if d_od < 100.0:",
     "raise the non-vacuity floor above what the stage actually delivers.  The refusal must "
     "fire — proving the floor is a live check, not a threshold nothing ever reaches"),

    ("bc1c-untested", 1, "GATE BC BC1c FAIL",
     'CLEAN_FILES = ["ref-clean.wav"]',
     'CLEAN_FILES = ["no-such-clean-capture.wav"]',
     "remove every CLEAN capture so gate 3 is never tested.  An UNTESTED gate 3 must be a "
     "refusal, not a silent pass — it is the gate that is true by construction and therefore the "
     "easiest to leave vacuous"),

    # ---- computed verdicts --------------------------------------------------------------------
    ("bc1c-clean", 1, "gate 3 FAILS",
     "        a, b = A.load(render(f, False)), A.load(render(f, True))",
     "        a, b = A.load(render(f, False)), A.load(render(f, True)) * 1.000001",
     "make the CLEAN render differ by 1e-6.  Gate 3 must report FAIL — it is true by "
     "construction today, which is exactly why it must still be able to come back false"),

    ("bc2-ceiling", 1, "OVER",
     "CEILING = 1.193",
     "CEILING = 0.5",
     "lower gate 2's ceiling below what the stage delivers.  The per-condition OVER flag must "
     "fire — the ceiling check cannot be a fixed string"),

    ("bc3-gate1", 1, "gate 1 FAILS",
     "    rms = float(np.sqrt(np.mean(np.square(errs))))",
     "    rms = float(np.sqrt(np.mean(np.square(errs)))) + 10.0",
     "make the shipped shape worse than a constant tilt.  Gate 1's verdict must invert — it is "
     "the claim that separates this stage from the class item 6 explicitly refuted"),

    ("bc4-overshoot", 1, "OVERSHOOT",
     "    ped = 100.0 * (AG.W6_PEDAL_PEAK_HZ[1] / AG.W6_PEDAL_PEAK_HZ[0] - 1.0)",
     "    ped = -1.0",
     "shrink the pedal's walk so the model's now overshoots it.  BC4 must say so — gate 2 is a "
     "CEILING, so overshoot is the failure mode it exists to catch"),

    ("bc5-collateral", 0, "1 of 4 non-target",
     "        if n == \"treble_peak\":\n            continue                       # the target — it is SUPPOSED to move",
     "        if n == \"never_a_feature\":\n            continue",
     "stop excluding the TARGET feature from the collateral count.  `treble_peak` moves by design, "
     "so the count must rise — which proves the exclusion is doing real work rather than the "
     "count being empty for an unrelated reason"),
]


def run(path, extra=()):
    return subprocess.run([sys.executable, path, *extra],
                          cwd=ROOT, capture_output=True, text=True, timeout=5400)


def main():
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()

    if re.search(r'add_argument\("--json"[^)]*default=(?!None)', src):
        sys.exit("MUTATION HARNESS FAIL: --json has a non-None default (s153)")

    priv = 'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s166_odtilt")'
    if src.count(priv) != 1:
        sys.exit("MUTATION HARNESS FAIL: cannot redirect the mutant's private render dir — the "
                 "PRIV_DIR line has moved, and without the redirect every arm would render into "
                 "the real gate's cache")
    src_m = src.replace(priv, f'PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", '
                              f'"s166_odtilt_mut_{os.getpid()}")')

    print("=== CONTROL (unmutated, rendering into the mutant's private dir) ===")
    with open(MUT, "w", encoding="utf-8") as fh:
        fh.write(src_m)
    c = run(MUT)
    if c.returncode != 0:
        print(c.stdout[-3000:], c.stderr[-2000:])
        sys.exit("MUTATION HARNESS FAIL: the UNMUTATED gate does not pass (s107)")
    print(f"  control OK (rc=0), {len(c.stdout.splitlines())} lines\n")

    passed = 0
    try:
        for name, rc_want, want, find, repl, why in ARMS:
            if src_m.count(find) != 1:
                print(f"  {name:<16} PATCH DID NOT APPLY ({src_m.count(find)} matches)")
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
