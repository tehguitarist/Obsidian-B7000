#!/usr/bin/env python3.11
"""Mutation runner for GATE K's K2 sub-gate (analysis/level_law_gate.py), session 182.

⭐⭐ WHY THIS EXISTS AT ALL, 79 SESSIONS AFTER THE GATE. GATE K predates the runner convention,
and s181 showed what that cost: `coef_closed` and `coef_nodal` are two derivations of ONE
network and K2 requires them to agree — a real check of the ALGEBRA that is structurally blind
to the NETWORK, because both take the topology as INPUT (s145 AM1a / s149 AO2). When s181 gave
the shipped stage a BLEND wiper end stop, neither mirror knew, they went on agreeing to
5.6e-17, and K2 kept printing `clean coef is exactly 0 at LEVEL max` — the retired value — as
its own discrimination line. The repair is a divergence guard against FitParams.h; a guard with
no mutation test is the thing this file's own §1 warns about.

Disciplines carried in (measurement-discipline.md §3):
  * the mutant LIVES in analysis/ (sibling imports resolve) and RUNS from the repo root
    (data paths resolve) -- s110, both halves.
  * the mutant path is PID-unique -- s139.
  * an UNMUTATED control runs first; if it does not pass, no arm below is attributable.
  * arms check GUARD IDENTITY (a token the failure must contain), not just rc != 0 -- s117.
  * arms with expect_rc == 0 test a COMPUTED VERDICT -- s128.
  * GATE K writes nothing unless `--json` is passed, so there is no artefact to redirect
    (s153's trap does not apply here) -- stated so the omission is not read as an oversight.

Run: /opt/homebrew/bin/python3.11 analysis/_mutate_gate_k.py [report.json]
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "level_law_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_k_{os.getpid()}.py")
DEFAULT_REPORT = "analysis/reports/s181_blendendstop.json"

# (name, pattern, replacement, expect_rc, must_contain, why)
ARMS = [
    ("k2-endstop-drift",
     r"SHIPPED_BLEND_END_STOP = \(0\.02418, 0\.0\)",
     "SHIPPED_BLEND_END_STOP = (0.0300, 0.0)",
     1, "ships BLEND end stop",
     "drift the transcribed end stop off FitParams.h. The new divergence guard must REFUSE — "
     "this is the whole defect s181 created and s182 closed."),

    ("k2-endstop-prefix",
     r'if re\.search\(rf"\\bdouble\\s\+\{re\.escape\(nm\)\}\\b", lhs\):',
     'if f"double {nm}" in lhs:',
     1, "ships BLEND end stop",
     "revert the word-boundary match to the naive substring. `blendEndStop` is a PREFIX of "
     "`blendEndStopClean`, so the second line overwrites the first with 0.0 and the guard would "
     "pass against a stage that HAS an end stop. Proves the regex is load-bearing, not tidiness."),

    # ⚠ s119 — the FIRST version of this arm broke the closed form ALONE and was caught by the
    # closed-vs-nodal known answer instead of the anchor assertion: the gate being better than
    # the test's model of it. The expectation was fixed, not the guard. Mutating the SINGLE
    # RESOLVER reproduces s181's actual defect — both mirrors ideal, the tool's constant still
    # matching FitParams — which is the one configuration no cross-check between them can see,
    # so only the anchor assertion is left to catch it.
    ("k2-both-mirrors-ideal",
     r"    end_hi, end_lo = SHIPPED_BLEND_END_STOP if endstop is None else endstop\n"
     r"    return end_hi, end_lo, 1\.0 - end_lo - end_hi",
     "    return 0.0, 0.0, 1.0",
     1, "clean coefficient at LEVEL max is",
     "s181's defect, exactly: give BOTH derivations the ideal pot while the transcribed constant "
     "still matches the header. The divergence guard passes, closed-vs-nodal agree to 1e-17, and "
     "the anchor assertion (clean coef at LEVEL max MUST equal endHi) is the only thing left — "
     "it must fire, or s181's accepted price can go silent again."),

    ("k2-nodal-ideal",
     r"    r_track = R_BLEND / k               # traversable Rp = R_BLEND; Rl and Rh are extra track",
     "    r_track = R_BLEND",
     1, "closed form and nodal solve disagree",
     "give the nodal solve the ideal track while the closed form keeps the end stop. The "
     "closed-vs-nodal known answer must break — which is what proves the two derivations are "
     "still INDEPENDENT after both were taught the same new element, rather than one being the "
     "other rearranged."),

    ("k2-no-contrast",
     r"    a_mid, b_mid = coef_closed\(1\.0, level_taper\(NOON\)\)",
     "    a_mid, b_mid = coef_closed(1.0, 1.0)",
     1, "no bleed CONTRAST",
     "read the noon coefficient at LEVEL max instead, so the ladder has no contrast. The "
     "vacuity guard must fire (empty-gate-must-fail) rather than reporting a flat table."),
]


def run(path, report):
    return subprocess.run([sys.executable, path, report], cwd=ROOT,
                          capture_output=True, text=True, timeout=900)


def main():
    report = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPORT
    if not os.path.exists(os.path.join(ROOT, report)):
        sys.exit(f"_mutate_gate_k: report not found: {report}")
    src = open(GATE).read()

    print(f"CONTROL (unmutated copy, run from the repo root, report={report}):")
    open(MUTANT, "w").write(src)
    try:
        r = run(MUTANT, report)
        if r.returncode != 0:
            print(r.stdout[-3000:] + r.stderr[-3000:])
            print("  => CONTROL FAILED — no arm below is attributable. Stopping.")
            return 1
        print("  => PASS\n")

        bad = 0
        for name, pat, rep, exp_rc, token, why in ARMS:
            mutated, n = re.subn(pat, rep, src, count=1)
            if n != 1:
                print(f"[{name}] PATCH DID NOT APPLY (pattern matched {n}x) — arm is broken, "
                      f"not the gate.")
                bad += 1
                continue
            open(MUTANT, "w").write(mutated)
            r = run(MUTANT, report)
            out = r.stdout + r.stderr
            ok_rc = (r.returncode == exp_rc)
            ok_tok = token in out
            verdict = "PASS" if (ok_rc and ok_tok) else (
                "GUARD DEAD" if r.returncode == 0 and exp_rc != 0 else
                "NARRATED" if ok_rc and not ok_tok else "WRONG GUARD")
            if verdict != "PASS":
                bad += 1
            print(f"[{name}] rc={r.returncode} (want {exp_rc}), token {token!r} "
                  f"{'found' if ok_tok else 'MISSING'} => {verdict}")
            print(f"    why: {why}")
        print(f"\n{len(ARMS) - bad}/{len(ARMS)} arms PASS.")
        return 1 if bad else 0
    finally:
        if os.path.exists(MUTANT):
            os.remove(MUTANT)


if __name__ == "__main__":
    sys.exit(main())
