#!/usr/bin/env python3.11
"""Mutation runner for GATE BT (`mix_corner_gate.py`).

Scores each arm on (exit code, guard IDENTITY) — s117: a runner that scores `rc != 0` alone cannot
tell a firing guard from a crash, and this project has counted a `FileNotFoundError` as a passing
epoch guard exactly that way (s189).

⭐ Two arms are COMPUTED-VERDICT arms (s128): they break the DATA behind a conclusion, expect
`rc == 0`, and require the gate to print the OPPOSITE verdict.  Without those, the s108 rule (exit
only on things that make the numbers meaningless) guarantees that a gate's most important
statements are exactly the ones no mutation can reach.

⚠ MUTATING AN IMPORTED MODULE.  Some arms must break `od_tone_restore_fit`, not the gate.  Patching
a dependency ON DISK needs a `finally` restore and can leak into a concurrent run, so instead the
mutant carries a module-level MONKEY-PATCH injected after its own imports (s139): the override then
lives and dies with the subprocess and there is no shared state at all.

⚠ The mutant LIVES in `analysis/` so sibling imports resolve, and RUNS from the repo root so data
paths resolve — two different requirements, and satisfying one is the natural way to break the
other (s110).  Its path is PID-unique so two concurrent runs cannot score each other's file (s139),
and its render dir is redirected so a mutant can never write into the real gate's cache (s153).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "mix_corner_gate.py")
PY = "/opt/homebrew/bin/python3.11"

#: Marker the injection is appended after — the gate's last import line.
ANCHOR = "import od_tone_restore_fit as F  # noqa: E402"


class Arm:
    def __init__(self, name, expect_rc, token, subs=(), inject=None, note=""):
        self.name, self.expect_rc, self.token = name, expect_rc, token
        self.subs, self.inject, self.note = subs, inject, note


ARMS = [
    # ---- known answers: these MUST make the gate refuse -----------------------------------------
    Arm("bt0a-law-drift", 1, "❌ BT0a",
        inject="""
_orig_cut_db = F.cut_db
F.cut_db = lambda T, g, d, clean_frac=None: 0.5 * _orig_cut_db(T, g, d, clean_frac)
""",
        note="the single resolver drifts from the law's own algebra"),

    Arm("bt0c-emulation-broken", 1, "❌ BT0c",
        subs=[(r'emulated = F\.cut_db\(T, GI\[g\], d, clean_frac=cf\) \+ dk \* F\.mix_shape\(cf, T\)',
               'emulated = F.cut_db(T, GI[g], d, clean_frac=cf) + dk')],
        note="the odNotchDepthDb stand-in stops being identical to a real K change"),

    Arm("bt0d-scope-leak", 1, "❌ BT0d",
        subs=[(r'if h\["ship"\] != h\["cand"\]:', 'if h["ship"] == h["cand"]:')],
        note="the OD-out-of-circuit control inverts"),

    # ---- computed verdicts (s128): rc == 0, and the OPPOSITE line must be printed ---------------
    Arm("bt5-sign-not-resolved", 0, "BT5 supports nothing",
        subs=[(r'new_k = \{k: ship_k\[k\] \+ v for k, v in dK\.items\(\)\}',
               'new_k = {k: ship_k[k] + v for k, v in dK.items()}\n'
               '    new_k[sorted(new_k)[0]] = +1.0')],
        note="one candidate cell left sign-positive ⇒ the coherence verdict must stand down"),

    # ⚠ The FIRST draft of this arm re-closed BT4's interval and asserted the token "@ cf 0.024".
    # It passed — and it was VACUOUS, because the unmutated gate prints that same token (S is near
    # its max just above the corner, so the open and closed extrema round to the same cf).  s110:
    # suspect the mutation before the guard.  What is actually load-bearing in BT4 is the SIGN
    # SPLIT — column 3 exists only because it is opposite-signed to column 2 — so the arm now
    # breaks the selection that makes the split mean anything, and requires the verdict to invert.
    Arm("bt4-sign-split-dead", 0, "column 3 supports nothing",
        subs=[(r'if s < 0\.0 and abs\(v\) > abs\(wflip\):',
               'if abs(v) > abs(wflip):')],
        note="with the sign selection removed both columns pick the same extremum, so the split "
             "separates nothing and BT4 must say so"),
]


def build_mutant(arm, pid):
    src = open(GATE).read()
    # sandbox the render dir so a mutant cannot touch the real gate's cache (s153)
    src, n = re.subn(r'REN_DIR = "build/s196_mix_corner"',
                     f'REN_DIR = "build/_mut_bt_{pid}"', src, count=1)
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
    path = os.path.join(HERE, f"_mutated_gate_bt_{pid}_{arm.name.replace('-', '_')}.py")
    open(path, "w").write(src)
    return path


def run(path):
    return subprocess.run([PY, "-u", path], cwd=ROOT, capture_output=True, text=True, timeout=4000)


def main():
    print("=" * 92)
    print("MUTATION RUNNER — GATE BT")
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
                print(f"  {arm.name:<26} ❌ NARRATED — ran but never printed {arm.token!r}")
                results.append((arm.name, "NARRATED"))
        finally:
            if os.path.exists(m):
                os.remove(m)

    print(f"\n  {npass}/{len(ARMS)} arms pass")
    return 0 if npass == len(ARMS) else 1


if __name__ == "__main__":
    sys.exit(main())
