#!/usr/bin/env python3.11
"""Mutation test for GATE AE (analysis/hf_null_presence_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS -- guards whose job is to stop the gate.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS. s108's rule means a well-built gate's
    headline findings deliberately never change the exit code, so a conclusion that has quietly
    become hard-coded narration would survive an exit-code-only runner. Those arms break the data
    behind a verdict and require the gate to print a DIFFERENT one.

⚠ THIS GATE'S HEADLINE IS A NEGATIVE RESULT ("the model has no interior extremum here"), which is
the single easiest kind of finding to produce by accident -- a broken estimator, an empty
membership, a window in the wrong place and a genuinely featureless curve all print the same thing.
So the two COMPUTED-VERDICT arms below are not decoration: AE9 injects a feature into the model and
requires the verdict to stop saying CONFIRMED, and AE10 removes the reference's feature and
requires it to say NEITHER SIDE. If either arm passes silently the gate is narrating.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (so sibling imports resolve) and RUNS from the repo root
    (so data paths resolve) -- two different requirements, and satisfying one is the natural way
    to break the other (s110).
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * three arms patch an IMPORTED module (`od_absolute_gate`, `feature_locus_gate`,
    `bass_peak_locus`) rather than the gate under test, because that is where the quantity lives.
    Said at each arm rather than pretended to be local.
  * failures are scored on the guard's own tag, not merely on rc != 0 (s117).
  * every arm writes to its OWN --out so a mutated run cannot overwrite the real report.

Run:  python3.11 analysis/_mutate_gate_ae.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "hf_null_presence_gate.py")
TMP = os.path.join(HERE, "_mutated_gate_ae.py")
REPORT = "analysis/reports/s124_ship.json"
SCRATCH = "build/s133_hf_null/_mutation_out.json"

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, must_ABSENT).
# `must_absent` exists because this gate's headline is a NEGATIVE result: proving a verdict is
# computed means proving the PRE-MUTATION claim disappears, not only that some new string appears.
ARMS = [
    ("AE0  endpoint membership",
     "move GATE Q's endpoint count out from under the gate. The bleed-free class IS the headline's "
     "population, so a membership that has silently changed must stop the run, not be absorbed. "
     "Patches the IMPORTED od_absolute_gate, which owns the selection.",
     [(r"^import od_absolute_gate as Q.*$",
       "import od_absolute_gate as Q  # noqa: E402\n"
       "_qe = Q.endpoints_od\nQ.endpoints_od = lambda caps: _qe(caps)[:-1]")],
     2, "AE0", None),

    ("AE0  AD5b group vacuity",
     "empty ONE of AD5b's GRUNT groups, so the cross-instrument known answer has a class with "
     "nothing in it. A gate that produces no data must refuse rather than fall through "
     "(`empty-gate-must-fail`). Patches the IMPORTED hw_trend_gate, which owns the predicate.",
     [(r"^import hw_trend_gate as AD.*$",
       "import hw_trend_gate as AD  # noqa: E402\n"
       "_bf = AD.bleed_free\nAD.bleed_free = lambda s: _bf(s) and s.get('gruntIdx') != 0")],
     2, "AE0", None),

    ("AE1b(i)  NOT-SILENT control",
     "point the control at `bt_notch` -- the feature the gate's own constant block records as NOT "
     "established present at these conditions (0.13 dB on the model). The guard must refuse, "
     "because a control that is itself faint cannot certify that a faint reading is the device.",
     [(r'^NOT_SILENT_CONTROL = "treble_peak"$',
       'NOT_SILENT_CONTROL = "bt_notch"')],
     2, "AE1b", None),

    ("AE1b(iii)  synthetic zero-rung control",
     "make the ZERO-depth rung carry a real notch. The arm's own built-in mutation control must "
     "then fire: if a 0 dB injection 'finds' something, the injection test proves nothing and the "
     "headline's zero counts are unvalidated.",
     [(r"^INJECT_DB = \(0\.0, 1\.0, 3\.0, 9\.0\)$",
       "INJECT_DB = (6.0, 1.0, 3.0, 9.0)")],
     2, "AE1b", None),

    ("AE1b(iii)  depth ordering",
     "inject the depths out of order. Recovered prominence must then stop being monotone in "
     "injected depth, and the gate must refuse to quote any depth below.",
     [(r"^INJECT_DB = \(0\.0, 1\.0, 3\.0, 9\.0\)$",
       "INJECT_DB = (0.0, 9.0, 3.0, 1.0)")],
     2, "AE1b", None),

    ("AE1b(iii)  slope/curvature law",
     "break the vertex fit so the recovered centre no longer converges on the injected one as the "
     "notch deepens. The centre error must then stop falling with depth -- the law that says the "
     "bias IS the background slope. Patches the IMPORTED bass_peak_locus, which owns the "
     "estimator.",
     [(r"^import bass_peak_locus as Y.*$",
       "import bass_peak_locus as Y  # noqa: E402\n"
       "_bi = Y._best_interior\n"
       "def _biased(d, win, kind, grid=None):\n"
       "    r = _bi(d, win, kind) if grid is None else _bi(d, win, kind, grid)\n"
       "    r = dict(r)\n"
       "    r['f0'] = r['f0'] * 1.03\n"
       "    return r\n"
       "Y._best_interior = _biased")],
     2, "AE1b", None),

    # ⚠ THE FIRST VERSION OF THIS ARM WAS VACUOUS AND IT EXPOSED A REAL DEFECT IN THE GATE.
    # It dropped `sweep_drv_-12` from the REPORT, which reaches AE1c and nothing else: AE3 reads
    # renders and captures, where the four sweeps are TIME WINDOWS of one file rather than
    # optional keys, so no rung can go missing and the rung-level branch could never fire.  A
    # guard that cannot fire is worse than no guard, so the gate now guards the partiality that IS
    # real here -- a missing GRUNT class -- and labels the rung branch as a structural invariant
    # rather than a tested guard.  This arm targets the guard that can actually fire (s110:
    # suspect the mutation before the guard; and then fix whichever turns out to be wrong -- here
    # it was both).
    ("AE3  a missing GRUNT class is a REFUSAL, not an exclusion",
     "collapse GRUNT boost into cut where AE3 bins its captures, so only 2 of 3 GRUNT positions "
     "survive. AD5b's headline is '3 of 3', so grading a partial set against it is a membership "
     "defect and s129's three-outcome rule makes it a refusal, not a quiet exclusion.",
     [(r'^        gi = caps\[f\]\["settings"\]\.get\("gruntIdx"\)$',
       '        gi = min(1, caps[f]["settings"].get("gruntIdx"))')],
     2, "AE3", None),

    ("AE4  the mute premise",
     "assert the model mutes at LEVEL min while making nothing silent. The exclusion rests on "
     "GATE L7, and an exclusion whose premise no longer holds must be re-derived rather than "
     "applied -- so the gate must refuse instead of quietly excluding a live row.",
     [(r"^import feature_locus_gate as W.*$",
       "import feature_locus_gate as W  # noqa: E402\nW.SILENT_DB = -1e9")],
     2, "AE4", None),

    ("AE9  COMPUTED VERDICT — the model's absence is measured, not narrated",
     "inject a real notch into the MODEL's bleed-free curves. Nothing about the reference changes, "
     "so the headline MUST stop saying the model has no extremum. If AE5 hard-codes the answer "
     "this session found, it will keep saying CONFIRMED. Patches the gate's own curve read, which "
     "is where both sides' data enters.",
     # ⚠⚠ THE FIRST VERSION OF THIS ARM CARRIED A CONCURRENCY-ONLY BUG, IN THE TEST.  It flagged
     # the injection through a module-level `_INJECT_MODEL = [False]` set around the model's read
     # and cleared before the pedal's -- correct in a serial run, and `parallel.pmap` uses a
     # **ThreadPoolExecutor**, so the flag is shared mutable state across workers.  The result was
     # the exact signature of a race: the injection reached SOME model reads and leaked into SOME
     # PEDAL reads (ND's prominence moved 2.12 -> 5.77 dB in a cell nothing was supposed to touch).
     # The arm still "worked" well enough to look plausible.  Fixed by passing the depth as an
     # ARGUMENT -- no shared state, so no ordering to get wrong.
     # ⭐ `a-concurrency-only-bug-passes-every-serial-verification-you-have` (s73), committed inside
     # a mutation test, where a wrong result reads as a gate defect rather than a test defect.
     [(r"^def read_side\(al, sw, ref\):$",
       "def read_side(al, sw, ref, inject=0.0):"),
      (r"^    out = \{\"peak_db\": float\(np\.max\(d\)\)\}$",
       "    out = {\"peak_db\": float(np.max(d))}\n"
       "    if inject:\n"
       "        d = d - inject * np.exp(\n"
       "            -((np.log(W.GRID / 7099.3) / (3.0 * W.GRID_STEP_FRAC)) ** 2))"),
      (r"^        rec\[\"model\"\]\[sw\] = read_side\(ren_al, sw, ref\)$",
       "        rec[\"model\"][sw] = read_side(ren_al, sw, ref, inject=8.0)")],
     0, "NO interior extremum at all: 0 of 9", "CONFIRMED bleed-free"),

    # ⚠ THE FIRST VERSION OF THIS ARM ZEROED THE REFERENCE OUTRIGHT AND WAS CAUGHT BY AN EARLIER
    # GUARD -- with both sides at exactly 0.00, every AE1c cell became a TIE, its known answer had
    # no ordering left to reproduce, and it refused before AE5 ran.  That is the gate being better
    # than the test's model of it (s119), so the fix is the EXPECTATION, not the guard: scale the
    # reference BELOW the presence bar instead of to zero.  AE1c still has an ordering to check,
    # and AE5 still sees a reference with nothing over the bar -- which is the branch under test.
    ("AE10 COMPUTED VERDICT — the reference's presence is measured, not narrated",
     "scale the REFERENCE's prominence below the presence bar, so neither side has a feature over "
     "it. The model is untouched, so the verdict must move from 'we lack a drive-generated "
     "feature' to 'NEITHER SIDE HAS ONE' -- the branch that would take this item OFF item 6's "
     "list. If AE5 hard-codes what this session found, it will keep naming the model's deficit.",
     [(r"^        rec\[\"pedal\"\]\[sw\] = read_side\(cap_al, sw, ref\)$",
       "        _p = read_side(cap_al, sw, ref)\n"
       "        for _k, _v in _p.items():\n"
       "            if isinstance(_v, dict):\n"
       "                _v['wide'] = dict(_v['wide'], prom=_v['wide']['prom'] * 0.02)\n"
       "        rec[\"pedal\"][sw] = _p")],
     0, "NEITHER SIDE HAS ONE", "lacks a DRIVE-GENERATED feature"),
]


def run(path, out_json):
    p = subprocess.run([sys.executable, path, REPORT, "--out", out_json],
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()
    open(TMP, "w").write(src)
    rc, out = run(TMP, SCRATCH)
    if rc != 0:
        print("CONTROL FAILED — the unmutated copy does not pass, so nothing below is "
              f"attributable to a mutation (rc={rc}).")
        print(out[-3000:])
        os.remove(TMP)
        return 1
    print("CONTROL  unmutated copy passes (rc=0) ... OK\n")

    npass = 0
    for name, why, patches, exp_rc, must, absent in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"[{name}] MUTATION DID NOT APPLY (pattern {pat!r}) — this is a defect in "
                      f"the TEST, not the gate (s110: suspect the mutation first).")
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue
        open(TMP, "w").write(mutated)
        rc, out = run(TMP, SCRATCH)
        hit = (must in out) and (absent is None or absent not in out)
        good = (rc == exp_rc) and hit
        npass += 1 if good else 0
        if good:
            verdict = "OK"
        elif rc != exp_rc and not hit:
            verdict = f"**GUARD DEAD** (rc={rc}, expected {exp_rc}; and no {must!r})"
        elif rc != exp_rc:
            verdict = f"**WRONG RC** (rc={rc}, expected {exp_rc})"
        else:
            verdict = (f"**NARRATED** (rc as expected but never printed {must!r})" if must not in out
                       else f"**NARRATED** (still printed the pre-mutation claim {absent!r})")
        print(f"[{name}]\n    {why}\n    -> {verdict}")
        if not good:
            print("    --- tail ---")
            print("    " + "\n    ".join(out.strip().splitlines()[-14:]))
        print()

    os.remove(TMP)
    if os.path.exists(SCRATCH):
        os.remove(SCRATCH)
    print(f"{npass}/{len(ARMS)} arms behaved as specified.")
    return 0 if npass == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
