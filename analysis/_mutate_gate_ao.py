#!/usr/bin/env python3.11
"""Mutation test for GATE AO (analysis/ladder_epoch_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS (GATE AO's `_die` exits 2, so rc = 1 is a crash).
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's deliverables are (i) "every
    verdict holds", (ii) "AJ's graded columns are bit-identical", and (iii) the KA-ONLY
    classification of `drain_db(zin)` — and a verdict that cannot become its opposite is
    narration, so arms below drive (i), (ii) and (iii) to their other outcomes.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * ⚠ arms that corrupt `ladder_zin`, `shipped_treble` or `jfet_source_z` are mutating an
    IMPORTED module, so they inject a module-level monkey-patch into the mutant AFTER its imports
    (s139) -- the override dies with the subprocess and leaves no shared state to restore.
  * ⚠⚠ THE AO2 AUDITOR IS ITSELF A PARSER, and s148's AN1b defect was a parser mis-reading scope.
    Two arms therefore attack the auditor directly (keyword handling, and the KA-ONLY
    classification), and both must be caught by AO2's OWN synthetic known answer -- which is the
    point of having one.
  * ⚠ AO3 launches six subprocesses of the three gates under audit.  None of them renders, so no
    arm here can touch the render cache, and no arm writes to src/.

Run:  python3.11 analysis/_mutate_gate_ao.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "ladder_epoch_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_ao_{os.getpid()}.py")
SCRATCH = tempfile.mkdtemp(prefix="ao_mut_")

# --- monkey-patches injected after the mutant's own imports ---------------------------------
# (a) make the SHIPPED set equal the DRAWN set -- i.e. the exact defect this gate exists to catch,
#     re-introduced.  AO1a must refuse: without that guard the whole gate silently compares a
#     network with itself and reports reassuring zeros.
_MONKEY_NO_DIVERGENCE = '''
import resonance_census as _AM
_AM.shipped_treble = lambda position: _AM.drawn_treble()
AJ.AM = _AM
'''

# (b) make ladder_zin depend on the probe it is measured with -- AO1b.
_MONKEY_PROBE_DEP = '''
_orig_zin = AJ.ladder_zin


def _mutated_zin(f, position="flat", zs_probe=1.0e3, which=None):
    return _orig_zin(f, position=position, zs_probe=zs_probe, which=which) * (
        1.0 + 0.3 * (zs_probe / 1.0e3))


AJ.ladder_zin = _mutated_zin
'''

# (c) break the current-source limit by clamping the scaling inside jfet_source_z -- AO1d.
_MONKEY_CLAMP_LIMIT = '''
_orig_zsrc = EQ.jfet_source_z


def _clamped(f, gm=None, ro=None, Rq2=None, R6=None, C3=None, **kw):
    ro = min(ro, 1.0e7)
    Rq2 = min(Rq2, 1.0e7)
    return _orig_zsrc(f, gm=gm, ro=ro, Rq2=Rq2, R6=R6, C3=C3, **kw)


EQ.jfet_source_z = _clamped
'''

# (d) make the B7K_LADDER_VALS switch INERT inside the subprocesses, so both runs of every gate
#     use the same ladder and nothing moves.  AO3's zero-diff refusal must fire: a comparison that
#     compares a thing with itself reads as reassurance (s110's vacuous-mutation lesson).
_MONKEY_INERT_SWITCH = '''
_orig_kwargs = AJ.ladder_kwargs
AJ.LADDER_VALS = "shipped"
AJ.ladder_kwargs = lambda position="flat", which=None: _orig_kwargs(position, "shipped")
os.environ["B7K_LADDER_VALS"] = "shipped"
_orig_run = subprocess.run


def _forced(cmd, **kw):
    env = dict(kw.pop("env", os.environ))
    env["B7K_LADDER_VALS"] = "shipped"
    return _orig_run(cmd, env=env, **kw)


subprocess.run = _forced
'''

# (e) force one of the three gates to report a DIFFERENT verdict between the two runs, so AO4's
#     "every verdict holds" must become "A VERDICT CHANGED".  Done by rewriting the verdict string
#     in the shipped-arm report only -- the cheapest way to drive AO4's clause to its other branch
#     without pretending a physics result changed.
_MONKEY_FLIP_VERDICT = '''
_orig_run2 = subprocess.run


def _tamper(cmd, **kw):
    r = _orig_run2(cmd, **kw)
    env = kw.get("env") or {}
    if env.get("B7K_LADDER_VALS") == "shipped":
        p = cmd[-1]
        if os.path.exists(p):
            import json as _j
            d = _j.load(open(p))
            for sec in list(d):
                if isinstance(d[sec], dict) and "verdict" in d[sec]:
                    d[sec]["verdict"] = "MUTATED — ADMISSIBLE ON EVERY CHEAP GATE"
            _j.dump(d, open(p, "w"))
    return r


subprocess.run = _tamper
'''

# (f) force AJ's graded reach to differ between the two runs, so AO4's "AJ's graded columns are
#     BIT-IDENTICAL" must stop being printed.  That clause is the gate's explanation of WHY the
#     defect survived unnoticed, and an explanation that cannot be falsified is narration.
_MONKEY_MOVE_GRADED = '''
_orig_run3 = subprocess.run


def _bump(cmd, **kw):
    r = _orig_run3(cmd, **kw)
    env = kw.get("env") or {}
    if env.get("B7K_LADDER_VALS") == "shipped" and "pre_clipper" in " ".join(cmd):
        p = cmd[-1]
        if os.path.exists(p):
            import json as _j
            d = _j.load(open(p))
            d["aj2"]["reach"] = d["aj2"]["reach"] * 1.5
            _j.dump(d, open(p, "w"))
    return r


subprocess.run = _bump
'''

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AO1a  the shipped-vs-drawn DIVERGENCE guard",
     "make `shipped_treble` return the DRAWN set -- the defect this gate exists to catch, put\n"
     "    back.  Without AO1a every comparison below compares one network with itself and prints\n"
     "    reassuring zeros; this is the guard whose ABSENCE in GATE AJ is the whole finding, so\n"
     "    the gate reporting it must itself be guarded.",
     [(r'^OUT_JSON = ', _MONKEY_NO_DIVERGENCE + 'OUT_JSON = ')],
     2, "AO1a", []),

    ("AO1b  `ladder_zin` must be probe-INDEPENDENT, at BOTH element sets",
     "make the extracted Zin depend on the probe impedance used to extract it.  AJ1d asserted\n"
     "    this at the DRAWN set only; the whole point of re-asserting it here is that the shipped\n"
     "    ladder is a different network and the divider extraction has to be valid there too.",
     [(r'^OUT_JSON = ', _MONKEY_PROBE_DEP + 'OUT_JSON = ')],
     2, "AO1b", []),

    ("AO1c  the divider identity S_zin + S_zout == 1",
     "return a wrong S_zout so the two sensitivities no longer partition.  AO4's entire\n"
     "    source-vs-load asymmetry reading -- the audit's standing output -- is this identity, so\n"
     "    if it does not hold exactly, 'the load side carries 5x the lever' means nothing.",
     [(r's_out = zin / \(zout \+ zin\)', 's_out = 1.3 * zin / (zout + zin)')],
     2, "AO1c", []),

    ("AO1d  the L -> inf limit must BE the bare ladder",
     "clamp ro/rq2 inside jfet_source_z so the current-source limit is never reached.  AN1e is\n"
     "    re-asserted here at the SHIPPED set because AO4 reads the asymmetry at that limit.",
     [(r'^OUT_JSON = ', _MONKEY_CLAMP_LIMIT + 'OUT_JSON = ')],
     2, "AO1d", []),

    ("AO2(parser)  the auditor must handle KEYWORD arguments",
     "drop keyword arguments from the call-site scan, so a parameter passed only by keyword reads\n"
     "    as NEVER PASSED.  Most call sites in these gates pass by keyword, so this mutation makes\n"
     "    the audit report almost everything unscreened -- a spectacular false positive.  It must\n"
     "    be caught by AO2's OWN synthetic known answer, which is the arm that proves the known\n"
     "    answer is load-bearing rather than decorative (s148's AN1b defect was exactly a parser).",
     [(r'pairs \+= \[\(kw\.arg, kw\.value\) for kw in node\.keywords if kw\.arg in seen\]',
       'pairs += []')],
     2, "AO2 known answer", []),

    ("AO2(KA-ONLY)  the known-answer-only classification must exist",
     "make the KA_FUNC pattern match nothing, so a parameter moved ONLY inside a known-answer\n"
     "    sub-gate is reported as genuinely SWEPT.  That is the distinction the gate's headline\n"
     "    turns on: `drain_db(zin)`'s only non-baseline expression is `inf` inside gate_ak1, so\n"
     "    without KA-ONLY the gate would report `zin` as screened and the standing output would\n"
     "    vanish.  Caught by the synthetic known answer's `e` case.",
     [(r'KA_FUNC = re\.compile\(r"\^gate_\[a-z\]\{2\}1\[a-z\]\?\$"\)',
       'KA_FUNC = re.compile(r"^zzz_no_such_function$")')],
     2, "AO2 known answer", []),

    ("AO2(table)  a mechanism function named in AUDIT must exist",
     "point one AUDIT row at a function that is not top-level.  Silently skipping an entry is how\n"
     "    an exhaustiveness claim goes unchecked in the first place -- which is the defect s148\n"
     "    found, so this gate must not be able to commit it.",
     [(r'\("j201_shaper_tilt_gate", "drain_db", \("f",\)',
       '("j201_shaper_tilt_gate", "no_such_mechanism_fn", ("f",)')],
     2, "AO2", []),

    ("AO3(vacuity)  a zero diff between the two element sets must REFUSE",
     "make the B7K_LADDER_VALS switch inert in the subprocesses, so both runs of every gate use\n"
     "    the shipped ladder and nothing moves.  11 of 12 values differ (AO1a), so a zero diff can\n"
     "    only mean the switch never reached the gate -- and a vacuous comparison reading as\n"
     "    reassurance is s110's documented failure mode.",
     [(r'^OUT_JSON = ', _MONKEY_INERT_SWITCH + 'OUT_JSON = ')],
     2, "AO3", []),

    ("AO3(membership)  a named graded key must be present in the report",
     "rename one graded key so it is absent.  The graded quantities are named explicitly precisely\n"
     "    so a rename cannot silently drop one from the survive/moved classification.",
     [(r'"aj2\.reach", "aj2\.exponent"', '"aj2.no_such_reach", "aj2.exponent"')],
     2, "AO3", []),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) ----------------------
    ("AO4(verdicts)  'every verdict holds' must be able to become its opposite",
     "tamper with the shipped-arm reports so one gate's verdict string differs between the two\n"
     "    runs.  'All three verdicts hold' is this session's load-bearing reassurance, and a\n"
     "    reassurance that cannot fail is narration (s34/s61/s68).",
     [(r'^OUT_JSON = ', _MONKEY_FLIP_VERDICT + 'OUT_JSON = ')],
     0, "A VERDICT CHANGED", []),

    ("AO4(graded)  'AJ's graded columns are BIT-IDENTICAL' must be falsifiable",
     "move AJ's graded reach in the shipped arm only.  That clause is the gate's EXPLANATION of\n"
     "    why a defect in three gates' shared input went unnoticed for ten sessions -- if it\n"
     "    cannot be falsified it is a story, not a measurement.  The arm passes when the gate\n"
     "    stops printing it AND reports aj_graded_identical=False.",
     [(r'^OUT_JSON = ', _MONKEY_MOVE_GRADED + 'OUT_JSON = ')],
     0, "aj_graded_identical=False", []),
]


def run(path, extra):
    p = subprocess.run([sys.executable, path, "--out", os.path.join(SCRATCH, "out.json")] + extra,
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()

    open(TMP, "w").write(src)
    rc, out = run(TMP, [])
    tail = [l for l in out.strip().splitlines() if l.strip()][-3:]
    print(f"CONTROL   rc={rc}, gate passes from {os.path.relpath(TMP, REPO)}  "
          f"{'✓' if rc == 0 else '✗ ' + str(tail)}")
    if rc != 0:
        print("\n⛔ the UNMUTATED control does not pass — no failure below is attributable to any "
              "mutation (s107).  Fix this first.")
        return 1

    bad = 0
    for name, why, patches, exp_rc, must, extra in ARMS:
        mutated = src
        ok_patch = True
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches) — the arm is testing "
                      f"nothing.  Pattern: {pat[:70]}")
                bad += 1
                ok_patch = False
                break
            mutated = new
        if not ok_patch:
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
    shutil.rmtree(SCRATCH, ignore_errors=True)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
