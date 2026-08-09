#!/usr/bin/env python3.11
"""Mutation test for GATE BQ (analysis/level_sensitivity_gate.py).

GATE BQ re-measures the two numbers a LEVEL-taper candidate is graded against, so its output feeds
straight into a SHIP decision.  Every headline it prints is a COMPUTED verdict, and four arms below
carry `expect_rc == 0` to prove it: a gate whose conclusions are hard-coded strings passes all its
refusal arms perfectly and is still narration (s108/s128, `computed-verdicts-not-narrated`, seven
prior occurrences and one of them inside a gate written to apply the rule).

⚠⚠ THE THREE ARMS THAT MATTER MOST, and why:
  * `bq1-ka` — the ENTIRE attribution ("the move is model-side") rests on the pedal reproducing two
    primary artefacts.  That check is the gate's load-bearing claim and it must be able to fail.
  * `bq2-matching` — matched membership is the difference between `need = 1.02x` and a number
    computed against whatever each side happened to read.  Item 9's own published pair carries this
    exact scar (9.1 % vs 133.5 % raw), so the arm drops matching and requires the answer to move.
  * `bq3-denominator` — `need` divides by the model's span, and at `drv_-6` that span is 1.3 %.
    Without the floor the gate would publish a fold computed against the locator's own noise.

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **Whether the taper should ship.**  BQ4 prints a comparison and three standing objections; no
    arm here can test a decision nobody has taken.
  * **Whether a b/a fold actually MOVES a centre 1:1.**  That is AY5(b)'s necessary-not-sufficient
    caveat, printed every run by both gates, and no arm can test it — it needs a re-render under a
    candidate taper, which is the work this gate exists to decide whether to do.
  * **The pedal's own numbers.**  They reproduce two stored artefacts to 0.1 %; nothing here can
    validate the artefacts themselves.
  * **`RESOLUTION_FRAC`.**  It is W's own `GRID_STEP_FRAC / 3` convention, imported.  GATE W1
    MEASURES the locator's resolution, and W1 cannot run on this epoch (its `s110_null_locus.json`
    is absent), so the figure is inherited rather than re-measured — a real limitation, printed by
    BQ2 and not fixable here.

⛔⛔ NO ARM POINTS ANY RENDER AT `build/s122_feature_locus/`.  The two cache arms below both operate
on a PID-unique decoy directory, so a DEAD guard damages the decoy and never the real s122 epoch
that GATEs AV / AW / AF / AG / BC read.  A mutation runner that could destroy the artefact it is
testing the protection of is not a test (s153: the runner's own side effects are the hazard).

Mechanics (s110/s139/s153/s107/s117): the mutant lives in analysis/ and runs from the repo root,
its path, its render dir and its output JSON are all PID-unique, each redirect REFUSES if its
pattern stops applying, an unmutated control runs first, and failures are scored on the guard's own
tag rather than on a bare non-zero exit.

Run:  python3.11 analysis/_mutate_gate_bq.py
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "level_sensitivity_gate.py")
PID = os.getpid()
MUT = os.path.join(HERE, f"_mutated_gate_bq_{PID}.py")
REN = f"build/_mut_bq_{PID}"
OUTJ = f"analysis/reports/_mut_bq_{PID}.json"
DECOY = f"build/_mut_bq_decoy_{PID}"

ARMS = [
    # ---- refusals ------------------------------------------------------------------------------
    ("bq0-stale-bin", 1, "GATE BQ0",
     "    bmt = os.stat(binp).st_mtime",
     "    bmt = 0.0",
     "make every src file postdate the render binary.  BQ0 must refuse: a stale binary reports the "
     "PREVIOUS build's model numbers with no error anywhere (s152, and s185 hit it for real inside "
     "a same-second rebuild), and this gate's whole output is a model-side measurement"),

    ("bq0-cache-changed", 1, "CHANGED during this run",
     "    fp_after = dir_fingerprint(FORBIDDEN_DIR)",
     "    fp_after = 'deadbeefdeadbeef'",
     "make the read-only cache appear to have changed mid-run.  The integrity check must fire — it "
     "is the only thing standing between this gate and the s122 epoch, whose 25 stamps are ALREADY "
     "all stale, so a single stray render there is unrecoverable"),

    ("bq0-render-into-cache", 1, "refusing to render into the READ-ONLY cache",
     'REN_DIR = "build/s190_level_sensitivity"          # PRIVATE.  Never W.REN_DIR.',
     f'REN_DIR = "{DECOY}"',
     "point the render directory AT the forbidden directory (both re-pointed to a PID-unique DECOY, "
     "so a dead guard cannot touch the real cache).  `_render_into`'s assert must fire BEFORE any "
     "render runs"),

    ("bq1-transcription", 1, "does not reproduce GATE AY",
     '    "bass_notch":   {"pedal_pct": 30.0, "model_pct": 17.2, "src": "AY5(c), matched"},',
     '    "bass_notch":   {"pedal_pct": 30.0, "model_pct": 99.9, "src": "AY5(c), matched"},',
     "corrupt the per-side pair so its ratio no longer equals the target GATE AY actually grades "
     "against.  The check must refuse — otherwise this gate could silently re-measure a DIFFERENT "
     "target than the one its consumer uses, which is `verify-the-BASELINE-not-its-LABEL` across a "
     "gate boundary"),

    ("bq1-ay-missing", 1, "carries no ay5.headroom.targets",
     '    ay_targets = json.load(open(ay_path)).get("ay5", {}).get("headroom", {}).get("targets", {})',
     "    ay_targets = {}",
     "empty GATE AY's stored targets.  The gate must refuse rather than proceed with an unchecked "
     "transcription — a `hasattr`-style guard around a name that is never defined is a check that "
     "passes forever, and the FIRST DRAFT OF THIS GATE SHIPPED EXACTLY THAT before this arm existed"),

    # ---- computed verdicts (expect_rc == 0) -----------------------------------------------------
    ("bq1-ka", 0, "A PRIMARY SOURCE DID NOT REPRODUCE",
     '    "treble_notch": {"pedal_pct": 44.1, "pedal_n": 6, "model_pct": 3.7,',
     '    "treble_notch": {"pedal_pct": 66.0, "pedal_n": 6, "model_pct": 3.7,',
     "move the primary pedal figure 50 % away.  The known answer must FAIL and say so — the gate's "
     "entire attribution ('the move is model-side') rests on this reproducing, so a check that "
     "cannot go red makes the headline unfalsifiable"),

    ("bq1-ka-n", 0, "primary recorded n=",
     '"treble_notch": {"pedal_pct": 44.1, "pedal_n": 6, "model_pct": 3.7,',
     '"treble_notch": {"pedal_pct": 44.1, "pedal_n": 5, "model_pct": 3.7,',
     "keep the primary SPAN right and change its recorded DETENT COUNT.  The known answer must "
     "still fail: two spans agreeing over different memberships is the coincidence this whole gate "
     "exists to stop being quoted (s178's 13th occurrence), so matching the value is not enough"),

    ("bq2-matching", 0, "REFUSED: < 3 matched detents",
     "                if m is not None and p is not None:",
     "                if m is not None or p is not None:",
     "drop MATCHED membership for 'either side read it'.  The refused-cell count must change — "
     "this is item 9's own published scar (treble_notch reads 9.1 % vs 133.5 % raw against "
     "9.1 % vs 24.3 % matched), and an unmatched span rewards exactly the arm that reads less"),

    ("bq3-denominator", 0, "under the 1.45 % denominator floor",
     "RESOLVE_MULT = 3.0",
     "RESOLVE_MULT = 0.0",
     "remove the denominator floor.  The `drv_-6` treble cell must stop being refused and publish a "
     "fold computed against a 1.3 % model span, i.e. against the locator's own resolution "
     "(`ratio-statistics-need-a-denominator-guard`).  The arm requires the REFUSAL to be present in "
     "the control and gone here"),

    ("bq-verdict", 0, "EVERY RE-MEASURED TARGET IS SMALLER",
     "    if shrank == len(moved):",
     "    if False and shrank == len(moved):",
     "disable the SMALLER branch of the verdict.  The headline must vanish — if it survives, the "
     "conclusion is a printed string rather than a reading of the table above it"),
]


# Arms whose needle must be present in the CONTROL and ABSENT in the mutant (see main()).
DISAPPEARS = {"bq2-matching", "bq3-denominator", "bq-verdict"}

REN_LINE = 'REN_DIR = "build/s190_level_sensitivity"          # PRIVATE.  Never W.REN_DIR.'
OUT_LINE = 'OUT_JSON = "analysis/reports/s190_level_sensitivity.json"'


def build(find, repl):
    """Apply one arm, then redirect every side effect to a PID-unique path.

    ⚠ A redirect that silently no-ops restores the exact hazard it exists to prevent (s153), so
    each one REFUSES when its pattern stops applying.  The one legitimate exception is an arm
    whose own mutation already re-points that path to a PID-unique location -- `bq0-render-into-
    cache` rewrites the REN_DIR line itself -- and that is recognised by checking the RESULT
    (does the source now name a PID-unique dir?) rather than by naming the arm, so a future arm
    gets the same treatment automatically."""
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
    p = subprocess.run([sys.executable, MUT], cwd=ROOT, capture_output=True, text=True,
                       timeout=3600)
    return p.returncode, p.stdout + p.stderr


def main():
    print("=" * 92)
    print("MUTATION TEST -- GATE BQ")
    print("=" * 92)
    # CONTROL first: without it, every 'failure' below is unattributable (s107).
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
    print(f"  CONTROL ok (rc=0)\n")
    ctl_out = out

    npass = 0
    for name, exp_rc, needle, find, repl, why in ARMS:
        # The decoy arm needs its forbidden dir re-pointed too, on the mutant only.
        extra = None
        if name == "bq0-render-into-cache":
            extra = ("FORBIDDEN_DIR = W.REN_DIR                          # build/s122_feature_locus -- READ-ONLY",
                     f'FORBIDDEN_DIR = "{DECOY}"')
        src = build(find, repl)
        if src is None:
            print(f"  {name:<24s} PATCH DID NOT APPLY -- the arm targets code that has moved")
            continue
        if isinstance(src, str) and src.startswith("REDIRECT-FAILED"):
            print(f"  {name:<24s} {src}")
            continue
        if extra:
            assert extra[0] in src, "decoy redirect no longer applies"
            src = src.replace(extra[0], extra[1], 1)
        rc, out = run(src)
        ok_rc = (rc != 0) if exp_rc else (rc == 0)
        # Two kinds of computed-verdict arm, and they need OPPOSITE checks:
        #   * DISAPPEARS -- the arm's point is that a line the control prints must STOP being
        #     printed (a refusal that should no longer fire, a verdict branch that should no
        #     longer be taken).  Requiring `needle in out` there scores a working guard as broken,
        #     which is how `bq2-matching` first read WRONG GUARD against a correct gate.
        #   * APPEARS    -- the arm's point is that a NEW line must be printed.
        # Both are checked against the CONTROL, so an arm cannot pass by the line being absent for
        # some unrelated reason.
        if name in DISAPPEARS:
            hit = (needle in ctl_out) and (needle not in out)
        else:
            hit = needle in out
        if ok_rc and hit:
            print(f"  {name:<24s} PASS   (rc={rc})")
            npass += 1
        elif not ok_rc:
            tag = "GUARD DEAD" if exp_rc else "CRASHED (expected a computed verdict)"
            print(f"  {name:<24s} {tag}   (rc={rc}, wanted "
                  f"{'non-zero' if exp_rc else '0'})")
            print("      " + out.strip().splitlines()[-1][:150] if out.strip() else "")
        else:
            print(f"  {name:<24s} WRONG GUARD / NARRATED -- {needle!r} not as required")
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
