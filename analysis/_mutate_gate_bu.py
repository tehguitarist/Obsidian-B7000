#!/usr/bin/env python3.11
"""Mutation runner for GATE BU (`mix_balance_gate.py`).

Scores each arm on (exit code, guard IDENTITY) — s117: a runner that scores `rc != 0` alone cannot
tell a firing guard from a crash, and this project has counted a `FileNotFoundError` as a passing
epoch guard exactly that way (s189).

⭐ THREE arms are COMPUTED-VERDICT arms (s128): they break the DATA behind a conclusion, expect
`rc == 0`, and require the gate to print the OPPOSITE verdict.  Without those the s108 rule (exit
only on what makes the numbers below meaningless) guarantees that this gate's whole argument — the
verdict block — is exactly the part no mutation can reach.

⚠ The mutant LIVES in `analysis/` so sibling imports resolve and RUNS from the repo root so data
paths resolve (s110); its filename is PID-unique so two concurrent runs cannot score each other's
file, and its REN_DIR is redirected so it can never write into the real gate's cache (s153).

⚠⚠ `pgrep -f _mutated_gate_bu` before editing `mix_balance_gate.py` while this is running — a
runner re-reads the gate's source once per arm, so an edit mid-run gives a mixed-epoch,
unattributable tally that still reads PASS on every line (s184's own defect 8).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "mix_balance_gate.py")
PY = "/opt/homebrew/bin/python3.11"

#: Injection anchor — the gate's last import line.
ANCHOR = "import od_tone_restore_fit as F          # noqa: E402"


class Arm:
    def __init__(self, name, expect_rc, token, subs=(), inject=None, note=""):
        self.name, self.expect_rc, self.token = name, expect_rc, token
        self.subs, self.inject, self.note = subs, inject, note


ARMS = [
    # ---- known answers: these MUST make the gate refuse -----------------------------------------
    Arm("bu0b-identity-broken", 1, "❌ BU0b",
        inject="""
_orig_coef = K.coef_closed
K.coef_closed = lambda B, L, endstop=None: (
    (lambda t: (t[0] * 1.001, t[1]))(_orig_coef(B, L, endstop)))
""",
        note="the e0 balance identity is this gate's whole mechanism; perturbing the coefficients "
             "must make BU0b refuse"),

    Arm("bu0c-s184-pair-lost", 1, "❌ BU0c",
        subs=[(r"S184_PAIR = \(0\.03099, 0\.0300, 1\.033\)",
               "S184_PAIR = (0.03099, 0.0300, 1.25)")],
        note="s184's published pair must stop reproducing if the ratio it was quoted at moves — "
             "otherwise BU0c's cross-session known answer is satisfiable by any number"),

    Arm("bu0d-vacuous-arms", 1, "❌ BU0d",
        subs=[(r'E0 = \("--fit", "blendEndStop=0"\)',
               'E0 = ("--fit", "blendEndStop=0.02418")')],
        note="with the e0 arm set to the SHIPPED value the two arms are identical and every "
             "column below compares nothing — `empty-gate-must-fail`"),

    Arm("bu0e-skirt-unbounded", 1, "❌ BU0e",
        subs=[(r"G\[gi\]\[di\] \+ off \+ abs\(Kt\[gi\]\[di\]\) \* 0\.951",
               "G[gi][di] + off + abs(Kt[gi][di]) * 0.951 + 30.0")],
        note="inflating the cut must push the notch skirt past the 0.10 dB bar, or the scope "
             "bound on the e0 arm's kMixCf[0] inconsistency is not actually being tested"),

    # ⚠ The FIRST draft of this arm renamed the capture in LADDER.  That made the gate exit 1 —
    # but from a CRASH in BU2's render, three sub-gates before the guard it was aimed at, which
    # a runner scoring `rc != 0` alone would have counted as a pass (s117).  The membership has
    # to be broken where BU3 READS it, leaving the render path intact.
    Arm("bu3-ladder-not-graded", 1, "❌ BU3",
        subs=[(r'caps = \{c\["file"\]: c for c in d\["captures"\]\}',
               'caps = {c["file"]: c for c in d["captures"] '
               'if c["file"] != "level-0815_base-od.wav"}')],
        note="BU3 must refuse when the ladder is not fully present in the report, rather than "
             "silently testing s184's 'invisible' claim on a different membership"),

    # ---- computed verdicts (s128): rc == 0, and the OPPOSITE line must be printed ---------------
    Arm("bu3-invisible-supported", 0, "is SUPPORTED",
        subs=[(r'pct = 100\.0 \* float\(np\.mean\(med <= np\.median\(v\)\)\)',
               'pct = 100.0 * float(np.mean(med <= np.median(v)))\n'
               '        if n == "level-0815_base-od.wav":\n'
               '            pct = 1.0')],
        note="if the flagged row sat BELOW the population median, s184's 'invisible to the "
             "release gate' would be supported and BU3 must say so instead of REFUTED"),

    # ⚠ This arm only became meaningful once the gate stopped taking `near[0]`: with the lower of
    # the two steps touching the balance, no restriction of the sweep could make the balance the
    # maximum, so the arm read NARRATED against a working gate and the defect was the GATE's
    # arbitrary selection, not the mutation's aim (s110, resolved as "both were wrong").
    Arm("bu4-balance-is-the-hazard", 0, "THE sensitive place",
        subs=[(r"knobs = sorted\(\{0\.30, 0\.35, 0\.375, 0\.40, balance_knob, "
               r"0\.45, 0\.50, 0\.55, 0\.60\}\)",
               "knobs = sorted({0.375, 0.40, balance_knob, 0.45})")],
        note="restricted to steps around the balance, the balance step becomes the swept maximum "
             "and BU4 must report it as THE sensitive place rather than a benign one"),

    Arm("bu6-not-acceptable", 0, "NOT ACCEPTABLE",
        subs=[(r'acceptable = \(r2\["worst_flagged_lf"\] < 3\.0',
               'acceptable = (r2["worst_flagged_lf"] < 0.5')],
        note="tightening the acceptance bar past the measured error must flip the verdict — "
             "otherwise 'CHARACTERISE AND ACCEPT' is narrated rather than computed"),
]


def build_mutant(arm, pid):
    src = open(GATE).read()
    src, n = re.subn(r'REN_DIR = "build/s197_mix_balance"',
                     f'REN_DIR = "build/_mut_bu_{pid}"', src, count=1)
    if n != 1:
        sys.exit("runner: the REN_DIR redirect did NOT apply — refusing to run a mutant that "
                 "would write into the real gate's cache (a redirect that silently no-ops "
                 "restores the exact bug it was added to prevent)")
    for pat, rep in arm.subs:
        new, k = re.subn(pat, rep, src, count=1)
        if k != 1:
            return None
        src = new
    if arm.inject:
        if ANCHOR not in src:
            return None
        src = src.replace(ANCHOR, ANCHOR + "\n" + arm.inject, 1)
    path = os.path.join(HERE, f"_mutated_gate_bu_{pid}_{arm.name.replace('-', '_')}.py")
    open(path, "w").write(src)
    return path


def run(path):
    return subprocess.run([PY, "-u", path], cwd=ROOT, capture_output=True, text=True, timeout=4000)


def main():
    print("=" * 92)
    print("MUTATION RUNNER — GATE BU")
    print("=" * 92)

    print("\n  control (unmutated) ...", end=" ", flush=True)
    c = run(GATE)
    if c.returncode != 0:
        print(f"❌ rc={c.returncode}\n{c.stdout[-2500:]}\n{c.stderr[-1500:]}")
        return 1
    print("✅ rc=0")

    npass, results = 0, []
    for arm in ARMS:
        m = build_mutant(arm, os.getpid())
        if m is None:
            print(f"  {arm.name:<26} ⚠ PATCH DID NOT APPLY — the gate's text moved; re-point the "
                  f"arm (fix the EXPECTATION, not the guard, s119)")
            results.append((arm.name, "NOT APPLIED"))
            continue
        try:
            r = run(m)
            out = r.stdout + r.stderr
            rc_ok = (r.returncode != 0) if arm.expect_rc else (r.returncode == 0)
            tok_ok = arm.token in out
            if rc_ok and tok_ok:
                print(f"  {arm.name:<26} ✅ rc={r.returncode}, matched {arm.token!r}")
                npass += 1
                results.append((arm.name, "PASS"))
            elif not rc_ok:
                print(f"  {arm.name:<26} ❌ GUARD DEAD (rc={r.returncode}, wanted "
                      f"{'non-zero' if arm.expect_rc else 'zero'}) — {arm.note}")
                results.append((arm.name, "GUARD DEAD"))
            else:
                print(f"  {arm.name:<26} ❌ NARRATED (rc={r.returncode} as expected, but "
                      f"{arm.token!r} never printed) — {arm.note}")
                results.append((arm.name, "NARRATED"))
        finally:
            if os.path.exists(m):
                os.remove(m)

    # sweep the mutants' render dirs (s153) — confirm no orphan child first (s184 defect 8)
    import shutil
    d = f"build/_mut_bu_{os.getpid()}"
    if os.path.isdir(os.path.join(ROOT, d)):
        shutil.rmtree(os.path.join(ROOT, d))

    print(f"\n  {npass}/{len(ARMS)} arms pass")
    return 0 if npass == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
