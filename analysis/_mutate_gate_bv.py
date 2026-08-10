#!/usr/bin/env python3.11
"""Mutation test for GATE BV (analysis/comb_confirm_gate.py).

GATE BV is the FINAL CONFIRMATION SWEEP -- the check that decides whether the seven shipped fixes
in item 19's comb survive off the settings they were fitted at.  Its output is the last measurement
before the action list closes, so every verdict in it will be quoted, and four arms below carry
`expect_rc == 0` to prove those verdicts are COMPUTED: a gate whose conclusions are hard-coded
strings passes every refusal arm perfectly and is still narration (`computed-verdicts-not-narrated`,
eight prior occurrences, one of them committed inside a gate written to apply the rule).

⚠⚠ THE FOUR ARMS THAT MATTER MOST, and why each earns its runtime:
  * `bv2-ka` -- the ENTIRE attribution rests on the pedal side reproducing GATE BQ, which in turn
    reproduces s125's loci and GATE AE's docstring.  If that check cannot fail, then "the model
    moved" and "my locator moved" are indistinguishable and nothing in BV4/BV5 is attributable.
  * `bv4-matching` -- matched membership is the difference between a comparison and a pool of
    whatever each side happened to read, and an estimator that REFUSES is correlated with the thing
    being graded (s178's 13th occurrence, in its most self-serving form: a feature too shallow to
    locate is the outcome under test).  The arm drops matching and requires a REFUSED verdict to
    stop being printed.
  * `bv5-stability` -- s178 measured this comb's treble null reading "20 dB too deep" and "11 dB
    too shallow" on the SAME build two rungs apart.  BV pools four rungs, so without the stability
    flag it would publish medians over an axis that inverts.  67 % of graded cells are stable; the
    flag on the other 33 % is load-bearing.
  * `bv5-both-depths` -- s186 measured the point and area estimators disagreeing about the SIGN at
    4 of 6 bleed-free cells, i.e. recommending OPPOSITE corrections.  The arm makes the two
    estimators identical and requires the disagreement warning to vanish.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **Whether any of the seven features SHOULD be fixed.**  BV grades; it proposes nothing, and no
    arm can test a decision nobody has taken.
  * **The locator itself.**  Its windows, grid and validity rule are W's, imported.  GATE W1
    MEASURES the locator's resolution and cannot run on this epoch (`s110_null_locus.json` is
    absent), so `RESOLUTION_FRAC` is inherited rather than re-measured -- a real limitation, and
    the reason BV2's cross-epoch known answer is the gate's only instrument validation.
  * **The comb-contrast depth definition.**  It is a CHOICE (neighbour-referred, item 18/19's own
    `C1`), and its end features N1/N4 have ONE shoulder each, so their contrast carries their
    neighbour's centre error.  Named in BV5's header; no arm can test a definition.
  * **The pedal's own numbers.**  They reproduce two stored artefacts exactly; nothing here can
    validate the artefacts themselves.

⛔⛔ NO ARM POINTS ANY RENDER AT `build/s122_feature_locus/`.  The cache arm operates on a
PID-unique DECOY, so a DEAD guard damages the decoy and never the real s122 epoch that GATEs
AV / AW / AF / AG / BC read -- an epoch whose 25 stamps are ALREADY all stale, so a single stray
render into it is unrecoverable.  A mutation runner that could destroy the artefact whose
protection it is testing is not a test (s153: the runner's own side effects are the hazard).

Mechanics (s110/s139/s153/s107/s117): the mutant lives in analysis/ and runs from the repo root,
its path, its render dir and its output JSON are all PID-unique, each redirect REFUSES if its
pattern stops applying, an unmutated CONTROL runs first, and failures are scored on the guard's own
tag rather than on a bare non-zero exit.

Run:  python3.11 analysis/_mutate_gate_bv.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "comb_confirm_gate.py")
PID = os.getpid()
MUT = os.path.join(HERE, f"_mutated_gate_bv_{PID}.py")
REN = f"build/_mut_bv_{PID}"
OUTJ = f"analysis/reports/_mut_bv_{PID}.json"
DECOY = f"build/_mut_bv_decoy_{PID}"

REN_LINE = 'REN_DIR = "build/s201_comb_confirm"        # PRIVATE.  Never W.REN_DIR.'
OUT_LINE = 'OUT_JSON = "analysis/reports/s201_comb_confirm.json"'
FORBID_LINE = 'FORBIDDEN_DIR = W.REN_DIR                  # build/s122_feature_locus -- READ-ONLY, ENFORCED'

# Arms whose point is that a line the CONTROL prints must STOP being printed.  Requiring the needle
# to APPEAR there would score a working guard as broken -- the mistake `bq2-matching` made on its
# first run against a correct gate.
DISAPPEARS = {"bv4-matching", "bv4-thin", "bv5-stability", "bv5-both-depths"}

ARMS = [
    # ---- refusals ------------------------------------------------------------------------------
    ("bv0-stale-bin", 1, "GATE BV0",
     "    bmt = os.stat(binp).st_mtime",
     "    bmt = 0.0",
     "make every src file postdate the render binary.  BV0 must refuse: a stale binary reports the "
     "PREVIOUS build's model numbers with no error anywhere (s152; s185 hit it for real inside a "
     "same-second rebuild), and this gate exists to certify the SHIPPED build specifically"),

    ("bv0-cache-changed", 1, "CHANGED during this run",
     "    fp_after = dir_fingerprint(FORBIDDEN_DIR)",
     "    fp_after = 'deadbeefdeadbeef'",
     "make the read-only cache appear to have changed mid-run.  The integrity check must fire -- "
     "it is the only thing standing between this gate and an epoch five other gates read"),

    ("bv0-render-into-cache", 1, "refusing to render into the READ-ONLY cache",
     REN_LINE, f'REN_DIR = "{DECOY}"',
     "point the render directory AT the forbidden directory (both re-pointed to a PID-unique "
     "DECOY, so a dead guard cannot touch the real cache).  `_render_into`'s assert must fire "
     "BEFORE any render runs"),

    ("bv1-grunt-cut-only", 1, "GATE BV1 REFUSES",
     "    files = sorted(set(base) | set(extra) | set(ladder.values()))",
     "    files = sorted(f for f in (set(base) | set(extra) | set(ladder.values()))\n"
     "                   if 'grunt-' not in f)",
     "drop every GRUNT-tokened capture, which is exactly the membership this whole project defaults "
     "into (s151: an untokened capture is GRUNT = Cut, and s195's pool was 7 cut / 1 flat / 2 "
     "boost).  BV1 must REFUSE rather than silently grading a one-position sweep"),

    ("bv2-ka", 1, "GATE BV2 REFUSES",
     "            f0.append(by_file[fn]['pedal'][sw][feat]['f0'])".replace("'", '"'),
     "            f0.append(by_file[fn]['pedal'][sw][feat]['f0'] * (1.0 + 0.02 * len(f0)))".replace("'", '"'),
     "tilt the pedal-side ladder by 2 % per detent.  The cross-epoch known answer must fail: it is "
     "the ONLY thing that separates 'the model moved' from 'my locator moved', and without it every "
     "verdict in BV4/BV5 is unattributable"),

    # ---- computed verdicts (rc == 0; the LINE must change) -------------------------------------
    # ⚠⚠ THIS ARM'S FIRST VERSION WAS VACUOUS, AND DIAGNOSING IT PRODUCED A FINDING (s110: suspect
    # the mutation before the guard).  It targeted `mid_notch` at played GRUNT cut, on the
    # reasoning that 12 model-valid readings against 0 matched would flip REFUSED into a verdict.
    # Measured, the model reads that feature in **0 of 112** played GRUNT-cut cells -- so matching
    # is not the binding constraint there and dropping it cannot change the line.  The guard was
    # fine; the arm was pointed at a cell where the model has no feature at all.
    # ⇒ re-pointed at `bt_notch` corner/flat, VERIFIED to have model-valid 11 and matched 0, so
    # dropping the pedal-side requirement genuinely turns a refusal into a quoted number.
    ("bv4-matching", 0, "bt_notch      corner  grunt flat   REFUSED -- no matched cell",
     "            if valid(m) and valid(p):",
     "            if valid(m):",
     "drop matched membership and accept any cell the MODEL can read.  `bt_notch` at the corner at "
     "GRUNT flat has 11 model-valid readings and 0 matched -- the pedal has no bridged-T notch "
     "there at all -- so unmatched pooling would manufacture a model-vs-pedal comparison out of "
     "cells only one side can read (s178's 13th occurrence, in its most self-serving form)"),

    ("bv4-thin", 0, "THIN (n<3) -- printed, NOT a verdict",
     "MIN_N = 3", "MIN_N = 0",
     "remove the thin-cell guard.  The THIN marker must disappear -- and with it the protection "
     "that stopped this gate's own first run quoting +18.33 dB off a SINGLE matched cell beside "
     "figures backed by 50 (`check-n-before-reading-a-trend`, s82)"),

    ("bv5-stability", 0, "NOT STABLE ACROSS STIMULUS",
     "    return len(vs) <= 1", "    return True",
     "make every pooled verdict claim stimulus stability.  The flag must disappear -- it is what "
     "stops a median over four rungs being read as a property of the model when s178 measured this "
     "comb's verdicts inverting between ADJACENT rungs on one build"),

    ("bv5-both-depths", 0, "ESTIMATORS DISAGREE ON SIGN",
     '        rec["depth_area"] = sgn * (float(np.mean([out[n]["area_db"] for n in usable])) - rec["area_db"])',
     '        rec["depth_area"] = rec["depth_point"]',
     "collapse the AREA depth onto the POINT depth.  The sign-disagreement warning must disappear "
     "-- s152/s180/s186: the point depth is a LOWER BOUND wherever the null bottom sits at/below "
     "the residue, and at 4 of 6 bleed-free cells the two estimators recommend OPPOSITE corrections"),
]


def build(find, repl):
    """Patch one thing, then redirect the render dir and the output JSON to PID-unique paths.

    Each redirect REFUSES if its pattern no longer applies -- a redirect that silently no-ops puts
    the mutant's renders and its report on top of the real gate's (s153)."""
    src = open(SRC).read()
    if find not in src:
        return None
    out = src.replace(find, repl, 1)
    for a, b, already in ((REN_LINE, f'REN_DIR = "{REN}"', (REN, DECOY)),
                          (OUT_LINE, f'OUT_JSON = "{OUTJ}"', (OUTJ,))):
        if a in out:
            out = out.replace(a, b, 1)
        elif not any(tok in out for tok in already):
            return "REDIRECT-FAILED:" + a[:40]
    return out


def run(mut_src):
    open(MUT, "w").write(mut_src)
    p = subprocess.run([sys.executable, MUT, "--jobs", "8"], cwd=ROOT,
                       capture_output=True, text=True, timeout=7200)
    return p.returncode, p.stdout + p.stderr


def main():
    print("=" * 92)
    print("MUTATION TEST -- GATE BV")
    print("=" * 92)
    ctl_src = open(SRC).read()
    for a, b in ((REN_LINE, f'REN_DIR = "{REN}"'), (OUT_LINE, f'OUT_JSON = "{OUTJ}"')):
        assert a in ctl_src, f"control redirect no longer applies: {a[:50]}"
        ctl_src = ctl_src.replace(a, b, 1)
    rc, out = run(ctl_src)
    if rc != 0:
        print("CONTROL FAILED -- no arm below is attributable\n")
        print(out[-4000:])
        cleanup()
        sys.exit(1)
    print("  CONTROL ok (rc=0)\n")
    ctl_out = out

    npass = 0
    for name, exp_rc, needle, find, repl, why in ARMS:
        extra = None
        if name == "bv0-render-into-cache":
            extra = (FORBID_LINE, f'FORBIDDEN_DIR = "{DECOY}"')
        src = build(find, repl)
        if src is None:
            print(f"  {name:<24s} PATCH DID NOT APPLY -- the arm targets code that has moved")
            print(f"      why: {why}")
            continue
        if isinstance(src, str) and src.startswith("REDIRECT-FAILED"):
            print(f"  {name:<24s} {src}")
            print(f"      why: {why}")
            continue
        if extra:
            assert extra[0] in src, "decoy redirect no longer applies"
            src = src.replace(extra[0], extra[1], 1)
        rc, out = run(src)
        ok_rc = (rc != 0) if exp_rc else (rc == 0)
        if name in DISAPPEARS:
            # Checked against the CONTROL, so an arm cannot pass by the line being absent for some
            # unrelated reason -- and a control that stops printing it reports honestly.
            hit = (needle in ctl_out) and (needle not in out)
        else:
            hit = needle in out
        if ok_rc and hit:
            print(f"  {name:<24s} PASS   (rc={rc})")
            npass += 1
        elif not ok_rc:
            tag = "GUARD DEAD" if exp_rc else "CRASHED (expected a computed verdict)"
            print(f"  {name:<24s} {tag}   (rc={rc}, wanted {'non-zero' if exp_rc else '0'})")
            if out.strip():
                print("      " + out.strip().splitlines()[-1][:150])
        else:
            why_not = ("needle absent from CONTROL" if name in DISAPPEARS and needle not in ctl_out
                       else "needle did not change as required")
            print(f"  {name:<24s} WRONG GUARD / NARRATED -- {why_not}: {needle[:60]!r}")
        print(f"      why: {why}")
    print(f"\n  {npass} / {len(ARMS)} arms pass")
    cleanup()
    sys.exit(0 if npass == len(ARMS) else 1)


def cleanup():
    for p in (MUT, os.path.join(ROOT, OUTJ)):
        if os.path.exists(p):
            os.remove(p)
    for d in (os.path.join(ROOT, REN), os.path.join(ROOT, DECOY)):
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
