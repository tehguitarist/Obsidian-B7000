#!/usr/bin/env python3.11
"""Mutation test for GATE AV (analysis/prominence_audit_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS — the census's two staleness guards, AV1's
    transcription known answer, AV2's two structural claims, AV2c's estimator contrast, and AV4's
    non-decreasing-in-window-width theorem.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's value is three statements a
    later session would quote — "the readings are window-dominated", "the membership is not
    window-stable", and "the detector's failure is CONTEXTUAL" — and a verdict that cannot come
    back as its opposite is narration (`computed-verdicts-not-narrated`, which GATE AU's own first
    draft failed one session ago).

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * the mutant's REPORT path is redirected and the redirect REFUSES if its pattern does not apply,
    because a mutant runs `main()` and would otherwise leave a deliberately-falsified report on
    disk wearing the real gate's filename (s153).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * mutations are DATA-level or STRUCTURAL where possible: `if False:` disables a guard rather
    than firing it (s114), and a threshold nowhere near the data does nothing (s110).

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * **The census's CLASSIFICATION is not armed.**  A mutation can prove the table REFUSES an
    undeclared or vanished module; nothing mechanical can check that `hw_trend_gate.py` really is
    E4 rather than E1 — that came from reading the source, and AV0 says so in its own table.  The
    guard protects the table's COVERAGE, not its correctness.
  * **AV3's verdict thresholds are labels, not bars.**  `MOVE_TOL_DB` only separates "did not
    move" from "moved"; every quantitative statement in AV3 is the measured Δ itself, and the
    WINDOW-DOMINATED label is a comparison of two measured columns (Δ vs the reading's own median),
    so there is no threshold to mutate meaningfully.
  * **The pedal-side scope is not a mutation target.**  Whether the model side agrees is an open
    question the gate states in its docstring; no arm can settle it.

Run:  python3.11 analysis/_mutate_gate_av.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "prominence_audit_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_av_{os.getpid()}.py")
MUT_REPORT = os.path.join(HERE, "reports", f"_mutant_av_{os.getpid()}.json")

# (name, why, [(pattern, replacement), ...], expect_rc, must_contain)
ARMS = [
    ("control", "unmutated — if this does not pass, nothing below is attributable",
     [], 0, "GATE AV: census complete"),

    # ---- AV0: the census's two staleness guards ------------------------------------------------
    ("av0-undeclared",
     "a module touches a prominence and nobody classified it — the exact way E1's defect survived",
     [(r'    "read_notch_sweep\.py": \("--", "NONE",[^\n]*\n', "")], 1, "AV0"),

    ("av0-vanished",
     "a declared site no longer touches a prominence — the table has rotted",
     [(r'(SITES = \{\n)', '\\1    "does_not_exist_gate.py": ("E1", "DETECTOR", "phantom"),\n')],
     1, "AV0"),

    # ---- AV1: the transcription is asserted, never trusted --------------------------------------
    ("av1-transcription",
     "`sides_at` stops reproducing `W.locate` — every number below would be a different estimator",
     [(r'        k = int\(np\.argmax\(v\)\)', '        k = int(np.argmin(v))')],
     1, "AV1"),

    # ---- AV2: the two structural claims, one in each direction ----------------------------------
    ("av2a-e1-break",
     "E1's walk started somewhere other than the argmin — the break becomes reachable and AU1's "
     "structural claim, which this whole gate rests on, would be false",
     [(r'(        dd = rng\.normal\(size=n_cells\) \* rng\.uniform\(0\.1, 20\.0\)\n)'
       r'        j = int\(np\.argmin\(dd\)\)', '\\1        j = 1')], 1, "AV2a"),

    ("av2b-e2-vacuous",
     "E2 walks from the argmin too — then `_best_interior` is E1 under another name and s126's "
     "repair bought nothing; the gate must refuse rather than report a distinction it did not find",
     [(r'            if not \(dd\[j\] <= dd\[j - 1\] and dd\[j\] <= dd\[j \+ 1\]\):\n'
       r'                continue',
       '            if j != int(np.argmin(dd)):\n                continue')], 1, "AV2b"),

    ("av2c-contrast",
     "the perturbation is moved onto E3's NAMED shoulders instead of the window edges, so E3 does "
     "move — the contrast that separates a curve-referred estimator from a window-referred one",
     [(r'    for e in R\.NOTCH_WIN:', '    for e in R.SHOULDER_HZ:')], 1, "AV2c"),

    # ---- AV4: the theorem that certifies the widening is pinned ---------------------------------
    ("av4-unpinned",
     "the widened read re-locates its own extremum instead of holding the shipped one — s151's "
     "feature-jump, which must show up as a flip OUT and be refused",
     [(r'                s = sides_at\(d, i, widen_win\(win, w\), kind\)',
       '                _w = widen_win(win, w)\n'
       '                s = sides_at(d, cell_index(d, _w, kind), _w, kind)')], 1, "AV4"),

    # ---- computed verdicts: each must be able to come back as its opposite ----------------------
    ("av3-verdict",
     "COMPUTED VERDICT: with the widening made a no-op every reading is window-free, and AV3 must "
     "say DEPTH rather than keep printing WINDOW-DOMINATED",
     [(r'^WIDEN = \(1\.0, 1\.25, 1\.6, 2\.0\)', 'WIDEN = (1.0, 1.0, 1.0, 1.0)')],
     0, "DEPTH (window-free)"),

    ("av4-verdict",
     "COMPUTED VERDICT: the same no-op widening must flip AV4 to WINDOW-STABLE",
     [(r'^WIDEN = \(1\.0, 1\.25, 1\.6, 2\.0\)', 'WIDEN = (1.0, 1.0, 1.0, 1.0)')],
     0, "WINDOW-STABLE"),

    # ⚠ BOTH of these arms were WRONG in their first draft, and both failed against a gate that
    # was working — `suspect the mutation before the guard` (s110), twice in one runner:
    #   * zeroing `neigh` by patching its first term left the SECOND exponential intact, so the
    #     window still had one flank (a vacuous mutation, s110's own case);
    #   * making the background a steep TILT does not make E1 fire — a monotone window puts the
    #     extremum ON a bound, one walk side is empty, and `prom` is 0.0 by construction (s126).
    #     Forcing the INTRINSIC branch needs CURVATURE: an interior maximum with real descents on
    #     both sides and no injected feature.
    ("av5-verdict-none",
     "COMPUTED VERDICT: remove BOTH neighbouring features and neither arm shows a failure — AV5 "
     "must reach its THIRD outcome, not keep asserting a contextual one",
     [(r'            n_alone \+= W\.locate',
       '            neigh = neigh * 0.0\n            n_alone += W.locate')],
     0, "NO FAILURE DEMONSTRATED"),

    # ---- AV6b: the cross-gate known answer, and the verdict that rests on it --------------------
    ("av6b-known-answer",
     "the shipped arm's bar drifts, so the block no longer reproduces GATE W's STORED w6 pedal "
     "spans — it would then be re-grading a statistic W6 does not publish, and its consequence "
     "figures would say nothing about W6's numbers",
     [(r'if not c\["w3_valid"\] or p < W\.MIN_PROM_DB:',
       'if not c["w3_valid"] or p < W.MIN_PROM_DB * 1.5:')], 1, "AV6b"),

    ("av6-verdict",
     "COMPUTED VERDICT: with W6's classification bar moved between the shipped and widened spans, "
     "a published FIXED/DRIVE-DEPENDENT verdict flips and AV6 must say so instead of continuing to "
     "report that the classifications survive",
     [(r'else "DRIVE-DEP" if x > W\.STIM_MOVE_FRAC else "FIXED"\)',
       'else "DRIVE-DEP" if x > 0.08 else "FIXED")')], 0, "A PUBLISHED CLASSIFICATION FLIPS"),

    ("av5-verdict-intrinsic",
     "COMPUTED VERDICT: a feature-free background with real CURVATURE clears the bar on its own, "
     "which must flip AV5 to INTRINSIC — the branch that would condemn the detector role everywhere",
     [(r'            noise = rng\.normal\(size=len\(grid\)\) \* 0\.01',
       '            noise = (rng.normal(size=len(grid)) * 0.01 - 20.0\n'
       '                     * ((lg - np.log(c)) / np.log(win[1] / win[0])) ** 2)')],
     0, "INVENTS FEATURES"),
]


def build(muts):
    src = open(SRC).read()
    # The report redirect is not optional and must not silently no-op (s153).
    pat = r'OUT_JSON = os\.path\.join\(HERE, "reports", "s158_prominence_audit\.json"\)'
    src, n = re.subn(pat, f'OUT_JSON = {MUT_REPORT!r}', src)
    if n != 1:
        sys.exit("_mutate_gate_av: the report redirect did not apply — refusing to run, because a "
                 "mutant would then overwrite the real gate's report with a falsified one")
    for pat, rep in muts:
        src, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None, f"PATCH DID NOT APPLY: {pat[:70]}"
    open(MUT, "w").write(src)
    return MUT, None


def run():
    ok = True
    print("=" * 96)
    print("MUTATION TEST — GATE AV (analysis/prominence_audit_gate.py)")
    print("=" * 96)
    for name, why, muts, exp_rc, need in ARMS:
        path, err = build(muts)
        if err:
            print(f"\n  ⛔ {name:24} {err}")
            ok = False
            continue
        p = subprocess.run([sys.executable, "-u", path], cwd=ROOT,
                           capture_output=True, text=True, timeout=3600)
        out = p.stdout + p.stderr
        rc_ok = (p.returncode != 0) == (exp_rc != 0)
        str_ok = need in out
        tag = "PASS" if (rc_ok and str_ok) else ("NARRATED" if rc_ok else "GUARD DEAD")
        if not (rc_ok and str_ok):
            ok = False
        print(f"\n  {'✅' if rc_ok and str_ok else '⛔'} {name:24} rc={p.returncode} "
              f"(want {'!=0' if exp_rc else '0'})  [{tag}]")
        print(f"     {why}")
        if not str_ok:
            print(f"     ⛔ output never contained {need!r} — the verdict is NARRATED, not computed")
            print("     last lines:")
            for ln in out.strip().splitlines()[-6:]:
                print(f"       | {ln}")
    for f in (MUT, MUT_REPORT):
        if os.path.exists(f):
            os.remove(f)
    print("\n" + "=" * 96)
    print(f"MUTATION TEST: {'ALL ARMS PASS' if ok else 'FAILURES ABOVE'}  ({len(ARMS)} arms)")
    print("=" * 96)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
