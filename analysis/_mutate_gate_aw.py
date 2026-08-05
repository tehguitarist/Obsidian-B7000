#!/usr/bin/env python3.11
"""Mutation test for GATE AW (analysis/model_prominence_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS — the private-directory guard, the membership check,
    the transcription known answer, the CROSS-GATE known answer that licenses the whole estimator
    arm, the widening theorem, the read-only fingerprint, the epoch arm's non-vacuity check, and
    AW6's window-containment theorem.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's value is four statements a
    later session would quote — "the model's FIXED verdicts are not a window artefact", "the
    membership is/is not window-stable", "N of 4 rows are unmoved since s122", and "the model's
    null is broader at 3 of 3 rungs" — and a verdict that cannot come back as its opposite is
    narration (`computed-verdicts-not-narrated`).

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path and its REPORT path are PID-UNIQUE, and the report redirect REFUSES if its
    pattern does not apply, because a mutant runs `main()` and would otherwise leave a
    deliberately-falsified report on disk wearing the real gate's filename (s153, s139).
  * ⭐ the mutant's PRIVATE RENDER DIRECTORY is also redirected, and that redirect refuses too.
    A mutant that renders is otherwise free to write into whatever directory its mutation points
    it at, and this gate's entire premise is that GATE W's cache is never written.
  * mutations that reach an IMPORTED module are injected as a module-level monkey-patch into the
    mutant itself rather than patching the dependency on disk (s139) — `AV.WIDEN` and
    `AV.cell_index` both live in `prominence_audit_gate`.
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * arms run with `--jobs 4`; the epoch arm's renders are cached after the control, so only the
    control pays for them.

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * **The end-of-run read-only fingerprint is armed only INDIRECTLY.**  Every mutation that would
    fire it for the real reason — actually rendering into GATE W's cache — would destroy the
    artefacts the whole gate exists to audit, and AW1b could then never detect the damage again.
    So the arm below makes the FINGERPRINT unstable instead, which proves the comparison is made
    and exits; the *path* half of the same protection is armed properly by `aw0-private-dir`.
  * **AW5's attribution is not armed.**  That every moved row lies in `OdToneRestore`'s band is an
    argument from where the stage sits (323 Hz, inside `mid_notch`'s window), not a measurement,
    and the gate says so at the verdict.  A mutation can prove the MOVE is computed; nothing
    mechanical can check the attribution.
  * **AW6's n = 3.**  The bleed-free set has three rungs, so no arm here can turn its deficit
    ordering into a statistical claim, and the gate deliberately makes none — the containment
    theorem is what carries it.

Run:  python3.11 analysis/_mutate_gate_aw.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "model_prominence_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_aw_{os.getpid()}.py")
MUT_REPORT = os.path.join(HERE, "reports", f"_mutant_aw_{os.getpid()}.json")
MUT_PRIV = os.path.join(ROOT, "build", f"_mutant_aw_prom_{os.getpid()}")

# An injection point immediately after the mutant's imports, for mutations that must reach a
# module the gate IMPORTS rather than the gate itself (s139: keep it inside the subprocess, so
# there is no dependency to restore and nothing leaks into another run).
INJECT_AT = "FAILED = []"

# (name, why, [(pattern, replacement), ...], expect_rc, must_contain)
ARMS = [
    ("control", "unmutated — if this does not pass, nothing below is attributable",
     [], 0, "GATE AW: model-side audit complete"),

    # ---- AW0: the two guards that keep GATE W's published artefacts safe ------------------------
    ("aw0-private-dir",
     "the epoch arm is pointed at GATE W's own cache — one run would overwrite the artefacts the "
     "estimator arm audits, and AW1b could never detect it again",
     [(r'^PRIV_DIR = .*$', 'PRIV_DIR = W.REN_DIR')], 1, "AW0"),

    ("aw0-missing-render",
     "a membership capture has no published render, so the estimator arm cannot be asked on the "
     "artefacts GATE W actually published from",
     [(r'    files, lad, eps = AV\.membership\(W\.REPORT\)',
       '    files, lad, eps = AV.membership(W.REPORT)\n'
       '    files = list(files) + ["not_a_real_capture.wav"]')], 1, "AW0"),

    ("aw0-readonly",
     "the cache fingerprint is made unstable — the before/after comparison must be MADE and must "
     "exit, which is the half of the read-only protection that can be armed without damaging the "
     "very artefacts this gate exists to protect (see the header)",
     [(r'^def fingerprint\(d\):$', 'def fingerprint(d, _n=[0]):'),
      (r'^    return out$', '    _n[0] += 1\n    out["__probe__"] = [_n[0]]\n    return out')],
     1, "AW0-readonly"),

    # ---- AW1: the three known answers ----------------------------------------------------------
    ("aw1a-transcription",
     "the pinned index is no longer `locate`'s own extremum, so the widen = 1.0 read stops BEING "
     "the shipped statistic and every model number below would describe a different estimator",
     [(re.escape(INJECT_AT),
       "_ci = AV.cell_index\nAV.cell_index = lambda d, win, kind, grid=W.GRID: _ci(d, win, kind, grid) + 1\n"
       + INJECT_AT)], 1, "AW1a"),

    ("aw1b-known-answer",
     "the admission bar drifts, so the cache no longer reproduces GATE W's STORED w6 MODEL rows — "
     "these curves would then not be the published artefacts and the whole estimator arm would be "
     "auditing a different chain wearing the right filenames",
     [(r'    return bool\(v\["w3_valid"\] and p >= W\.MIN_PROM_DB\)',
       '    return bool(v["w3_valid"] and p >= W.MIN_PROM_DB * 1.5)')], 1, "AW1b"),

    ("aw1c-unpinned",
     "the widened read re-locates its own extremum instead of holding the shipped one — s151's "
     "feature-jump, which breaks the theorem on INTERIOR readings and must be refused",
     [(r'                s = AV\.sides_at\(d, i, AV\.widen_win\(win, w\), kind\)',
       '                _w = AV.widen_win(win, w)\n'
       '                s = AV.sides_at(d, AV.cell_index(d, _w, kind), _w, kind)')],
     1, "AW1c"),

    # ---- AW5: the epoch arm must not be vacuous ------------------------------------------------
    ("aw5-vacuous",
     "the current binary is among the cache's own stamps — there is no epoch to measure and every "
     "Δ in AW5 would be 0 for a reason that has nothing to do with the model",
     [(r'        old_stamps\.add\(tuple\(json\.load\(open\(sp\)\)\.get\("bin"\) or \[\]\)\)',
       '        old_stamps.add(tuple(cur))')], 1, "AW5"),

    # ---- AW6: the containment theorem ----------------------------------------------------------
    ("aw6-containment",
     "E1 and E6 are read on different depth conventions, so the window containment that makes "
     "`E1 <= E6` a theorem no longer holds and the deficit stops being a width statistic",
     [(r'gm = OT\.notch_geometry\(g, mod_d, depth="point"\)',
       'gm = OT.notch_geometry(g, mod_d, depth="area")'),
      (r'gp = OT\.notch_geometry\(g, ped_d, depth="point"\)',
       'gp = OT.notch_geometry(g, ped_d, depth="area")')], 1, "AW6"),

    # ---- computed verdicts: each must be able to come back as its opposite ----------------------
    ("aw2-verdict",
     "COMPUTED VERDICT: with the widening made a no-op every model reading is window-free, and "
     "AW2 must say DEPTH rather than keep printing LOWER BOUND / WINDOW-DOMINATED",
     [(re.escape(INJECT_AT), "AV.WIDEN = (1.0, 1.0, 1.0, 1.0)\n" + INJECT_AT)],
     0, "DEPTH — window-free"),

    ("aw3-verdict",
     "COMPUTED VERDICT: the same no-op widening must flip AW3 to WINDOW-STABLE",
     [(re.escape(INJECT_AT), "AV.WIDEN = (1.0, 1.0, 1.0, 1.0)\n" + INJECT_AT)],
     0, "WINDOW-STABLE"),

    ("aw4-verdict",
     "COMPUTED VERDICT: with W6's classification bar moved between the shipped and widened model "
     "spans, a RESOLVED verdict flips — AW4 must say so instead of continuing to report that the "
     "model's FIXED rows are not a window artefact",
     [(r'else "DRIVE-DEP" if x > W\.STIM_MOVE_FRAC else "FIXED"\)',
       'else "DRIVE-DEP" if x > 0.003 else "FIXED")')],
     0, "A RESOLVED MODEL CLASSIFICATION FLIPS"),

    ("aw5-verdict",
     "COMPUTED VERDICT: the same bar move makes a MODEL classification differ between the two "
     "EPOCHS, and AW5 must report that a GATE W re-baseline is owed rather than that no verdict "
     "is stale",
     [(r'else "DRIVE-DEP" if x > W\.STIM_MOVE_FRAC else "FIXED"\)',
       'else "DRIVE-DEP" if x > 0.003 else "FIXED")')],
     0, "CLASSIFICATION MOVED"),

    ("aw6-verdict",
     "COMPUTED VERDICT: the two sides' deficits are swapped, so the model is no longer the "
     "broader null and AW6 must report 0 of 3 rather than keep asserting the Q attribution",
     [(r'        dm = r\["e6_model"\] - r\["e1_model_s156"\]\n'
       r'        dp = r\["e6_pedal"\] - r\["e1_pedal"\]',
       '        dp = r["e6_model"] - r["e1_model_s156"]\n'
       '        dm = r["e6_pedal"] - r["e1_pedal"]')],
     0, "at 0 of 3 rungs"),
]


def build(muts):
    src = open(SRC).read()
    # Neither redirect is optional and neither may silently no-op (s153).
    for pat, rep, what in (
            (r'OUT_JSON = os\.path\.join\(HERE, "reports", "s159_model_prominence\.json"\)',
             f'OUT_JSON = {MUT_REPORT!r}', "report"),
            (r'^PRIV_DIR = os\.path\.join\(os\.path\.dirname\(HERE\), "build", "s159_model_prom"\)$',
             f'PRIV_DIR = {MUT_PRIV!r}', "private render dir")):
        src, n = re.subn(pat, rep, src, flags=re.M)
        if n != 1:
            sys.exit(f"_mutate_gate_aw: the {what} redirect did not apply — refusing to run, "
                     f"because a mutant would then write outside its own sandbox")
    for pat, rep in muts:
        src, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None, f"PATCH DID NOT APPLY: {pat[:70]}"
    open(MUT, "w").write(src)
    return MUT, None


def run():
    ok = True
    print("=" * 96)
    print("MUTATION TEST — GATE AW (analysis/model_prominence_gate.py)")
    print("=" * 96)
    for name, why, muts, exp_rc, need in ARMS:
        path, err = build(muts)
        if err:
            print(f"\n  ⛔ {name:22} {err}")
            ok = False
            continue
        p = subprocess.run([sys.executable, "-u", path, "--jobs", "4"], cwd=ROOT,
                           capture_output=True, text=True, timeout=5400)
        out = p.stdout + p.stderr
        rc_ok = (p.returncode != 0) == (exp_rc != 0)
        str_ok = need in out
        tag = "PASS" if (rc_ok and str_ok) else ("NARRATED" if rc_ok else "GUARD DEAD")
        if not (rc_ok and str_ok):
            ok = False
        print(f"\n  {'✅' if rc_ok and str_ok else '⛔'} {name:22} rc={p.returncode} "
              f"(want {'!=0' if exp_rc else '0'})  [{tag}]")
        print(f"     {why}")
        if not str_ok:
            print(f"     ⛔ output never contained {need!r} — the verdict is NARRATED, not computed")
            print("     last lines:")
            for ln in out.strip().splitlines()[-8:]:
                print(f"       | {ln}")
    for f in (MUT, MUT_REPORT):
        if os.path.exists(f):
            os.remove(f)
    if os.path.isdir(MUT_PRIV):
        for n in os.listdir(MUT_PRIV):
            os.remove(os.path.join(MUT_PRIV, n))
        os.rmdir(MUT_PRIV)
    print("\n" + "=" * 96)
    print(f"MUTATION TEST: {'ALL ARMS PASS' if ok else 'FAILURES ABOVE'}  ({len(ARMS)} arms)")
    print("=" * 96)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
