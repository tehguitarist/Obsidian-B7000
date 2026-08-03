#!/usr/bin/env python3.11
"""Mutation test for GATE O's session-119 anchor repair (O6b) and the ledger wiring.

House rules this runner obeys, each paid for by a real session:
  * the patched copy must LIVE in analysis/ (so sibling imports resolve) and RUN from the repo
    root (so repo-relative capture paths resolve).  Getting only the first half right is s107's
    trap; getting only the second is s110's.
  * an UNMUTATED CONTROL runs first.  If it does not pass, no failure below is attributable to a
    mutation -- it is the harness.
  * every needle is asserted present EXACTLY ONCE, so a mutation that silently matches nothing
    reports as vacuous rather than as a dead guard (s110).
  * the failure must come from the guard the mutation was AIMED at, matched on its own tag, not
    merely from a non-zero exit -- a crash exits non-zero too (s117).

Run:  /opt/homebrew/bin/python3.11 analysis/_mutate_gate_o.py [report]
"""
import re
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "a3_decomposition_gate.py")
TMP = os.path.join(HERE, "_mutant_gate_o.py")          # LIVES in analysis/, RUNS from ROOT
REPORT = sys.argv[1] if len(sys.argv) > 1 else "analysis/reports/s118_clampfix.json"

# (label, needle, replacement, tag the failure must carry)
MUTATIONS = [
    # NB: aimed at O8 (a zero correction restores the pre-s119 ledger), but O6b's positivity
    # guard catches it FIRST -- which is the better outcome, so the expected tag is O6b.
    ("O6b: correction silently dropped",
     "    corr = T.detent_corrections()[det[0]]",
     "    corr = 0.0  # mutated",
     "O6b"),

    ("O6b: correction applied with the WRONG SIGN",
     "    corr = T.detent_corrections()[det[0]]",
     "    corr = -T.detent_corrections()[det[0]]  # mutated",
     "O6b"),  # negative correction: a corrupted detent reads LOW, so this must be refused

    # The one that exposed the vacuous first draft: master-1200 is a genuine, different detent, so
    # its pedal side does NOT cancel.  The retired span test passed this; the taper-step test must
    # refuse it, which is the whole reason the check was rebuilt.
    ("O6b: duplication known answer broken (compare against a NON-duplicate)",
     "    other = [f for f in caps\n"
     "             if any(f\"master-{d}_\" in f for d in T.DUP_DETENTS) and f != u_file]",
     "    other = [f for f in caps if 'master-1200' in f]  # mutated",
     "O6b"),

    ("O6b: pure-gain bar loosened past the point of meaning",
     "DUP_PURE_GAIN_MAX_SPAN_DB = 0.01",
     "DUP_PURE_GAIN_MAX_SPAN_DB = 1e-9  # mutated",
     "O6b"),  # tighter than the render's own float32 storage -> must refuse

    ("O6b: taper constants read from a header that no longer ships them",
     "    src = open(K.FITPARAMS, encoding=\"utf-8\").read()",
     "    src = ''  # mutated",
     "O6b"),   # a stale power-law reader must fail loudly, not default silently

    ("O8: correction threaded into the residual only, NOT the law",
     "        lw = lw + corr",
     "        lw = lw  # mutated",
     "O8"),   # the ledger must then fail to reconstruct the measurement

    ("O8: correction threaded into the law only, NOT the residual",
     "        residual = raw_resid - corr",
     "        residual = raw_resid  # mutated",
     "O8"),

    ("GATE T: the shared correction is poisoned at its ONE definition",
     None,   # patched in master_anchor_gate.py instead -- see below
     None,
     "O6b"),
]

T_SRC = os.path.join(HERE, "master_anchor_gate.py")
T_TMP = os.path.join(HERE, "_mutant_gate_t.py")


def run(path, extra_env=None):
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run([sys.executable, path, REPORT],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout + p.stderr)


def tail(out, n=3):
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    return " | ".join(lines[-n:])[:300]


def main():
    src = open(SRC, encoding="utf-8").read()
    fails = 0

    # ---- CONTROL: unmutated copy, same path, same cwd ----------------------------------------
    open(TMP, "w", encoding="utf-8").write(src)
    rc, out = run(TMP)
    if rc != 0:
        print(f"CONTROL FAILED (rc={rc}) -- the harness is broken, not the guards.\n  {tail(out)}")
        os.remove(TMP)
        return 1
    print("CONTROL  PASS  (unmutated copy runs clean from the repo root)\n")

    for label, needle, repl, tag in MUTATIONS:
        if needle is None:
            # the cross-module mutation: poison GATE T's ONE definition and check GATE O refuses
            tsrc = open(T_SRC, encoding="utf-8").read()
            tneedle = "    pad = _pad_quiet()"
            if tsrc.count(tneedle) != 1:
                print(f"VACUOUS  {label}\n  needle appears {tsrc.count(tneedle)}x in GATE T")
                fails += 1
                continue
            open(T_TMP, "w", encoding="utf-8").write(
                tsrc.replace(tneedle, "    pad = float('nan')  # mutated"))
            mutated = src.replace("import master_anchor_gate as T",
                                  "import _mutant_gate_t as T")
            open(TMP, "w", encoding="utf-8").write(mutated)
            rc, out = run(TMP)
            os.remove(T_TMP)
        else:
            if src.count(needle) != 1:
                print(f"VACUOUS  {label}\n  needle appears {src.count(needle)}x -- fix the "
                      f"mutation, do not conclude the guard is dead")
                fails += 1
                continue
            open(TMP, "w", encoding="utf-8").write(src.replace(needle, repl))
            rc, out = run(TMP)

        if rc == 0:
            print(f"GUARD DEAD  {label}\n  the gate PASSED under mutation")
            fails += 1
            continue
        # identity: the refusal must carry the tag of the guard this mutation targets
        hit = re.search(rf"GATE {tag}\b", out)
        if not hit:
            print(f"WRONG GUARD  {label}\n  exited {rc} but not via GATE {tag}: {tail(out)}")
            fails += 1
            continue
        print(f"OK       {label}\n           -> refused by GATE {tag}")

    os.remove(TMP)
    print(f"\n{'ALL MUTATIONS CAUGHT' if not fails else f'{fails} PROBLEM(S)'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
