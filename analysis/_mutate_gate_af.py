#!/usr/bin/env python3.11
"""Mutation test for GATE AF (analysis/sk_mechanism_locus.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS -- guards whose job is to stop the gate.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS. s108's rule means a well-built gate's
    headline findings deliberately never change the exit code, so a conclusion that has quietly
    become hard-coded narration would survive an exit-code-only runner. Those arms break the data
    behind a verdict and require the gate to print the OPPOSITE verdict.

GATE AF is almost entirely computed verdicts -- its whole output is five REFUTED classifications
and one sizing -- so five of the ten arms below are `expect_rc == 0`. That ratio is the point: an
exit-code-only runner would have tested one sixth of this gate.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (so sibling imports resolve) and RUNS from the repo root
    (so data paths resolve) -- two different requirements, and satisfying one is the natural way
    to break the other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * three arms patch the IMPORTED `bt_pair_shape_gate`, which owns the pedal target and the
    cascade's known answer, rather than the gate under test. Said at each arm rather than
    pretended to be local (s128).
  * failures are scored on the guard's own tag, not merely on rc != 0 (s117).
  * the verdict arms assert on the `AF7-MEMBERSHIP` line, never on a COUNT -- five candidates all
    classify the same way today, so any count-based assertion would pass vacuously the moment a
    swap left the totals alone (s130's `_mutate_gate_ab.py` arm 6).

Run:  python3.11 analysis/_mutate_gate_af.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "sk_mechanism_locus.py")
TMP = os.path.join(HERE, "_mutated_gate_af.py")

IMPORT_AB = r"^import bt_pair_shape_gate as AB.*$"

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain).
ARMS = [
    # ---------------- REFUSAL ARMS ----------------------------------------
    ("AF1a  finite-GBW reduces to the shipped ideal form",
     "break the op-amp's closed-loop response so it no longer tends to unity as ft -> inf. "
     "Every number in AF2 is then a property of a transcription error rather than of an "
     "op-amp, and the gate must refuse before the sweep is read.",
     [(r"    K = 1\.0 / \(1\.0 \+ s / \(2\.0 \* np\.pi \* ft\)\)",
       "    K = 0.90 / (1.0 + s / (2.0 * np.pi * ft))")],
     2, "AF1a"),

    ("AF1b  cascade reproduces s125 / GATE AB1",
     "move the closed-form answer the cascade must reproduce. AF1b must refuse rather than "
     "screen candidates against a cascade that no longer agrees with the derivation it "
     "inherits. Patches the IMPORTED bt_pair_shape_gate, which owns that constant.",
     [(IMPORT_AB, "import bt_pair_shape_gate as AB  # noqa: E402\nAB.S125_PEAK_HZ = 1500.0")],
     2, "AF1b"),

    ("AF4  railEnabled must be true for W6's reading to be about the shipped build",
     "flip the shipped rail-clamp flag. AF4's whole argument is that the EMPIRICAL answer is "
     "already on disk -- but W6 measured a build with the clamps ON, so if they ship off the "
     "reading is about a different plugin and must not be quoted.",
     [(r'^RAIL_ENABLED = .*$', "RAIL_ENABLED = False")],
     2, "AF4"),

    ("AF4  the stored GATE W report must exist",
     "point the report path at a file that is not there. The gate must refuse rather than fall "
     "back to transcribing W6's number from a handover -- `rebuild-targets-dont-transcribe`.",
     [(r'^W_REPORT = .*$', 'W_REPORT = os.path.join(REPO, "analysis", "reports", "_absent.json")')],
     2, "AF4"),

    ("VACUITY  desynchronised FitParams.h",
     "rename the constant the gate reads out of the shipped source. A gate whose constants have "
     "silently stopped matching the plugin must refuse, not print fiction "
     "(`verify-the-CONSTANT-not-the-prose`).",
     [(r'RAIL_NEG = abs\(float\(_read_fitparam\("railNeg"\)\)\)',
       'RAIL_NEG = abs(float(_read_fitparam("railNegXXX")))')],
     2, "desynchronised"),

    ("AF6  the vertex law is a KNOWN ANSWER, not decoration",
     "detune the closed-form prediction by 3x. The measured tilt is unchanged, so the two must "
     "disagree and the guard must fail -- otherwise AF6's 'this certifies the reframe' line is "
     "narration and the agreement percentage is never actually checked.",
     [(r"    T_pred = -curv \* need_oct", "    T_pred = -curv * need_oct * 3.0")],
     1, "AF1c/AF6"),

    # ---------------- COMPUTED-VERDICT ARMS -------------------------------
    ("AF2  COMPUTED VERDICT — GBW is classified by comparison, not by assertion",
     "give the op-amp a 10 kHz gain-bandwidth, below the 16.09 kHz the target needs. The "
     "candidate's REFUTED verdict must invert; if AF2/AF7 hard-code 'refuted' the arm passes "
     "with the wrong answer.",
     [(r"^TL07X_GBW_TYP = .*$", "TL07X_GBW_TYP = 1.0e4"),
      (r"^TL07X_GBW_MIN = .*$", "TL07X_GBW_MIN = 1.0e4")],
     0, "reaches=['falling op-amp GBW']"),

    ("AF3  COMPUTED VERDICT — slew is classified by comparison",
     "give the op-amp a 0.01 V/us slew rate, far below the 0.160 V/us the chain presents. Slew "
     "limiting must then be classified as REACHING.",
     [(r"^TL07X_SR_TYP = .*$", "TL07X_SR_TYP = 0.01"),
      (r"^TL07X_SR_MIN = .*$", "TL07X_SR_MIN = 0.01")],
     0, "reaches=['slew-rate limiting']"),

    ("AF4  COMPUTED VERDICT — the rail-clamp verdict reads the stored span",
     "replace W6's measured 0.21 % span with 50 %. Rail clamping must then be classified as "
     "REACHING -- proving AF4's refutation is computed from the stored report rather than "
     "restating what this session already believed.",
     [(r'    span = w6\.get\("span_frac"\)', "    span = 0.50")],
     0, "reaches=['output rail clamping']"),

    ("AF6  COMPUTED VERDICT — the required tilt is a comparison against the target",
     "flip the SIGN of the pedal's peak target. The cascade is untouched, so the required tilt "
     "MUST invert; a hard-coded direction (AB5's own s130 defect) would keep printing a "
     "negative slope. Patches bt_pair_shape_gate, which owns the target.",
     [(IMPORT_AB,
       "import bt_pair_shape_gate as AB  # noqa: E402\n"
       "AB.PEDAL_DPEAK = -AB.PEDAL_DPEAK")],
     0, "MEASURED tilt  : +"),
]


def run(path, argv=()):
    p = subprocess.run([sys.executable, path, *argv], cwd=REPO,
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()

    # ---- CONTROL: the unmutated copy, in the mutant's own location --------
    open(TMP, "w").write(src)
    rc, out = run(TMP)
    if rc != 0:
        os.remove(TMP)
        print("CONTROL FAILED — the unmutated copy does not pass where the mutants run.")
        print(f"  rc={rc}\n{out[-2500:]}")
        sys.exit(1)
    print(f"CONTROL   rc=0, gate passes from {os.path.relpath(TMP, REPO)}  ✓\n")

    passed = 0
    for name, why, patches, want_rc, want_str in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches for {pat!r}) — the arm is "
                      f"vacuous, which is a defect in the TEST (s110).")
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue

        open(TMP, "w").write(mutated)
        rc, out = run(TMP)
        ok_rc = rc == want_rc
        ok_str = want_str in out
        if ok_rc and ok_str:
            passed += 1
            kind = "REFUSED" if want_rc else "VERDICT INVERTED"
            print(f"✓ {name}\n    {kind} as required (rc={rc}, saw {want_str!r})")
        else:
            print(f"✗ {name}\n    {why}")
            if not ok_rc:
                print(f"    WRONG EXIT: got rc={rc}, wanted {want_rc}"
                      + ("  — GUARD DEAD" if want_rc and rc == 0 else ""))
            if not ok_str:
                tag = "NARRATED" if want_rc == 0 else "WRONG GUARD"
                print(f"    {tag}: output never contained {want_str!r}")
            print("    " + "\n    ".join(out.strip().splitlines()[-6:]))

    os.remove(TMP)
    print(f"\n{passed}/{len(ARMS)} arms behaved as required.")
    sys.exit(0 if passed == len(ARMS) else 1)


if __name__ == "__main__":
    main()
