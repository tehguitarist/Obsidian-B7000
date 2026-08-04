#!/usr/bin/env python3.11
"""Mutation test for GATE AN (analysis/jfet_rout_tilt_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS.  GATE AN refuses with rc = 2 (its `_die`), so a
    mutant that exits 1 is a crash, not a fired guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's deliverable is a refutation
    that interlocks three axes, plus the AN1b staticity reading and the AN4 sign gate — and a
    refutation that cannot become a non-refutation is narration, so four arms below drive
    AN1b/AN3/AN4/AN5 to their OTHER outcomes.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements, and satisfying one is the natural way to break the
    other (s110).
  * the mutant path is PID-UNIQUE (s139): a fixed name lets two concurrent runs overwrite each
    other's mutant between the write and the subprocess launch.
  * an unmutated CONTROL runs first; if it does not pass, no failure below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * arms that move a STORED report write a patched COPY to scratch and point the gate at it.
  * ⚠ arms that corrupt the tilt estimator or the ladder impedance are mutating an IMPORTED
    module (GATE AI's / GATE AJ's), so they inject a module-level monkey-patch into the mutant
    after its imports — s128's "mutate the dependency" case in the form that leaves no shared
    state to restore (the override dies with the subprocess).
  * ⚠ AN1b reads `src/dsp/JfetStage.h`.  Its arm does NOT edit that file — it re-points the
    gate's `JFET_SRC` at a patched COPY in scratch, so no arm here can touch `src/`.
  * ⚠ this gate reads only stored reports, one header, and closed-form arithmetic — no render,
    no cache, so no arm can trigger one.

Run:  python3.11 analysis/_mutate_gate_an.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "jfet_rout_tilt_gate.py")
TMP = os.path.join(HERE, f"_mutated_gate_an_{os.getpid()}.py")
SCRATCH = tempfile.mkdtemp(prefix="an_mut_")

AH_REPORT = os.path.join(REPO, "analysis", "reports", "s137_vertex_curvature.json")
AL_REPORT = os.path.join(REPO, "analysis", "reports", "s141_deficit_exponent.json")
JFET_SRC = os.path.join(REPO, "src", "dsp", "JfetStage.h")


def _patched_report(path, mutate, tag):
    d = json.load(open(path))
    mutate(d)
    out = os.path.join(SCRATCH, f"{tag}_{os.path.basename(path)}")
    json.dump(d, open(out, "w"))
    return out


def _unusable_limb(d):
    d["al4"]["primary"]["usable"] = False


def _two_centres(d):
    for k in ("centres", "deficits"):
        d["al4"]["primary"][k] = d["al4"]["primary"][k][:2]


def _break_stored_exponent(d):
    d["al4"]["primary"]["endpoint_exponent"] = 1.234


def _flip_deficit_sign(d):
    p = d["al4"]["primary"]
    p["deficits"] = [-x for x in p["deficits"]]


AL_UNUSABLE = _patched_report(AL_REPORT, _unusable_limb, "unusable")
AL_SHORT = _patched_report(AL_REPORT, _two_centres, "short")
AL_BADEXP = _patched_report(AL_REPORT, _break_stored_exponent, "badexp")
AL_FLIP = _patched_report(AL_REPORT, _flip_deficit_sign, "flip")

# A JfetStage.h copy with a per-sample mutation of `ro` planted inside process().
JFET_MUTATED = os.path.join(SCRATCH, "JfetStage_mutated.h")
_src = open(JFET_SRC).read()
_m = re.search(r"(inline double process\(double x\) noexcept\s*\{)", _src)
if _m is None:
    print("⛔ could not find process() in JfetStage.h to plant the AN1b mutation.")
    sys.exit(1)
open(JFET_MUTATED, "w").write(
    _src[:_m.end()] + "\n        ro = ro * 1.0001;  // planted by _mutate_gate_an\n"
    + _src[_m.end():])

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


def _mutated_zin(f, position="flat", zs_probe=1.0e3):
    return _orig_ladder_zin(f, position=position, zs_probe=zs_probe) * (1.0 + 0.3 * (zs_probe / 1.0e3))


AJ.ladder_zin = _mutated_zin
'''

# Make Zout NON-homogeneous in L, by scaling only ro and leaving rq2 alone.
_BREAK_HOMOG = [(r'return EQ\.jfet_source_z\(f, gm=gm, ro=L \* ro, Rq2=L \* rq2, R6=AJ\.J_R6, C3=AJ\.J_C3\)',
                 'return EQ.jfet_source_z(f, gm=gm, ro=L * ro, Rq2=rq2, R6=AJ.J_R6, C3=AJ.J_C3)')]

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, extra_argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AN1a  THE LICENCE — an L-independent block must cancel from the tilt CHANGE",
     "make the tilt estimator a NONLINEAR functional of the curve (a term in the SQUARE of the\n"
     "    fitted curvature).  ⚠ inherits s138/s139's fix: a different LINEAR functional does NOT\n"
     "    break additivity, so the fixed block would still cancel and the guard would be right to\n"
     "    stay silent.  Without AN1a, screening the J201 without ever rendering the ladder, IC2_A,\n"
     "    the clipper or the Sallen-Keys is an unexamined argument rather than a measured fact.",
     [(r'^AG_REPORT = ', _MONKEY_TILT.format(body="c[1] + 1.0e-3 * c[0] ** 2") + 'AG_REPORT = ')],
     2, "AN1a", []),

    ("AN1b(estimator)  the tilt estimator must recover an injected tilt EXACTLY",
     "return 1.05x the linear coefficient — still LINEAR, so AN1a stays silent and the two guards\n"
     "    are shown to be independent rather than one guard checked twice.  Every number in\n"
     "    AN2-AN4 is a tilt, so a mis-scaled estimator prints a plausible, entirely wrong set of\n"
     "    reaches.",
     [(r'^AG_REPORT = ', _MONKEY_TILT.format(body="c[1] * 1.05") + 'AG_REPORT = ')],
     2, "AN1b", []),

    ("AN1c  Zout must be HOMOGENEOUS degree 1 in L",
     "scale only `ro` and leave `rq2` fixed, so the two resistances no longer move together.\n"
     "    This is the load-bearing physical claim: Q2 is the active load carrying Q1's OWN drain\n"
     "    current, so one Id scales both.  If it fails, the mechanism is not a one-parameter\n"
     "    family and AN2's two limits BRACKET NOTHING — every reach below would be a reading at\n"
     "    an arbitrary point of a two-parameter space.",
     _BREAK_HOMOG, 2, "AN1c", []),

    ("AN1d  the ladder Zin must be probe-independent",
     "make `ladder_zin` depend on the probe impedance it is measured with.  Z_drain is built on\n"
     "    it, so a probe-dependent Zin makes every divider number an artefact of the probe.",
     [(r'^AG_REPORT = ', _MONKEY_ZIN + 'AG_REPORT = ')],
     2, "AN1d", []),

    ("AN1e  the L -> inf limit must BE the bare ladder",
     "break the limit by clamping L in `drain_db_L`, so L -> inf no longer reaches the\n"
     "    current-source limit.  AN2's ceiling and AN3's most-favourable probe are both taken\n"
     "    there, so if that limit is not what it claims to be, the ceiling bounds nothing.",
     [(r'return AK\.drain_db\(gm, L \* ro, L \* rq2, zin, f=f\)',
       'return AK.drain_db(gm, min(L, 3.0) * ro, min(L, 3.0) * rq2, zin, f=f)')],
     2, "AN1e", []),

    ("AN3(import)  recomputing AL4's endpoint exponent must reproduce its stored value",
     "corrupt the STORED endpoint exponent in a COPY of AL's report, leaving its centres and\n"
     "    deficits intact.  The gate recomputes the statistic from those centres and compares —\n"
     "    which is what makes the mechanism/deficit comparison like-for-like rather than two\n"
     "    different statistics being differenced (s145's 'import the source's FUNCTIONS, not its\n"
     "    summary').",
     [], 2, "AN3", ["--al", AL_BADEXP]),

    ("AN3(membership)  an unusable AL4 limb must REFUSE, not fall back",
     "mark AL4's primary limb `usable: false`.  The gate must refuse rather than silently pick a\n"
     "    different window — s122's 'a known answer must NAME its condition', and s133's rule\n"
     "    that a partial/absent membership gets its own branch.",
     [], 2, "AN3", ["--al", AL_UNUSABLE]),

    ("AN3(n)  a limb with fewer than 3 centres must REFUSE",
     "truncate AL4's limb to 2 centres.  An exponent over 2 points is a line through 2 points; the\n"
     "    gate must say so rather than print it (`check n before reading a trend`).",
     [], 2, "AN3", ["--al", AL_SHORT]),

    ("AN1b(scan)  the staticity scan must not find zero mutation sites",
     "narrow the assignment regex so it matches nothing.  A source scan that silently matches\n"
     "    nothing reports 'static' for any file whatsoever — `empty-gate-must-fail` in a costume,\n"
     "    and here it would manufacture this gate's own premise.",
     [(r'assign_re = re\.compile\(r"\(\?<!\[\\w\.>\]\)\(ro\|rq2\)\\s\*=\(\?!=\)"\)',
       'assign_re = re.compile(r"(?<![\\\\w.>])(zzz_no_such_member)\\\\s*=(?!=)")')],
     2, "AN1b", []),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) ----------------------
    ("AN1b(verdict)  a per-sample mutation of `ro` must FLIP the staticity verdict",
     "point the gate at a COPY of JfetStage.h with `ro = ro * 1.0001;` planted inside process().\n"
     "    AN1b's claim — that the mechanism is ABSENT from the model — is this gate's entire\n"
     "    premise, so it must be falsifiable by the model actually containing it.\n"
     "    ⚠ NOTE this arm caught a REAL defect in the gate's first draft: the original scan\n"
     "    attributed `ro = Ro` to `prepare` (setNonlinear's signature spans two lines, so a\n"
     "    one-line regex never matched it) and counted the member DECLARATION as a mutation,\n"
     "    reporting NOT-STATIC against a static model.  s110's 'suspect the check before the\n"
     "    code', fired on the check.",
     [(r'^JFET_SRC = .*$', f'JFET_SRC = {JFET_MUTATED!r}')],
     0, "NOT ESTABLISHED STATIC", []),

    ("AN3(verdict)  a RISING mechanism must stop being refuted on shape",
     "replace the mechanism's per-centre tilt change with an injected f^+3 profile, which RISES\n"
     "    faster than the deficit and beats the single-pole bound.  AN3's refutation is the\n"
     "    strongest of the three, so it must be able to become an ADMISSIBLE reading.",
     [(r'mech_by_probe\[label\] = m',
       'm = m[0] * (centres / centres[0]) ** 3.0\n        mech_by_probe[label] = m')],
     0, "ADMISSIBLE ON SHAPE", []),

    ("AN4(verdict)  a GRUNT-dependent mechanism must fail the sign gate",
     "make the drain block depend on the GRUNT cap, by folding the cap RATIO into the L scaling.\n"
     "    The J201 is UPSTREAM of the switch, so this must be impossible for a correct model — and\n"
     "    the gate must SAY so rather than print a 3/3 pass it cannot lose.\n"
     "    ⚠ FIRST DRAFT WAS VACUOUS (s110: suspect the mutation before the guard).  It used\n"
     "    `L_LIMIT_HI * (cg/cut)`, and 1e9 x 1 vs 1e9 x 60 are BOTH the L -> inf limit, so all\n"
     "    three positions landed on the identical value, the spread stayed at 1e-14 and the arm\n"
     "    read as the gate narrating.  A MODERATE L is required for the cap ratio to bind.",
     [(r'd = \(AI\.tilt_fine\(lim \+ g_db, f0, half\) - AI\.tilt_fine\(base \+ g_db, f0, half\)\)',
       'd = (AI.tilt_fine(drain_db_L(cg / 3.69e-9, gm, ro, rq2, zin) + g_db, f0, '
       'half) - AI.tilt_fine(base + g_db, f0, half))')],
     0, "GRUNT-DEPENDENT", []),

    ("AN5(verdict)  a sign-flipped deficit must move the interlock's sign column",
     "flip the sign of every deficit in a COPY of AL's report, so the mechanism's own (unchanged)\n"
     "    sign now AGREES with the deficit at every centre.  The interlock's middle clause counts\n"
     "    sign disagreements, and a count that cannot change is narration.",
     [], 0, "wrong sign at 0/10", ["--al", AL_FLIP]),
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
