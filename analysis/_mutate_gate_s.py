#!/usr/bin/env python3.11
"""Mutation test for GATE S's guards, with an unmutated CONTROL.

Two lessons are baked into the mechanics here, both paid for by earlier sessions:

  * s107 -- a patched copy written to /tmp returns "FAIL" for a ModuleNotFoundError that never
    reaches a guard, so every mutation "passes" for the wrong reason.  The copy must LIVE in
    `analysis/` so its sibling imports resolve.
  * s110 -- ...and it must RUN from the repo root so the repo-relative data paths resolve.  Getting
    only the first half right produced 7-of-7 FileNotFoundError "passes".
  * s110 -- a mutation applied inside main() never reaches code that reads a MODULE-level constant.
    Every mutation below is a source-level edit to a module-level definition.

The CONTROL is the only thing that can tell "the guard fired" from "the copy is broken": if the
unmutated copy does not PASS from the same place, no failure below is attributable to a mutation.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = HERE / "compression_law_gate.py"
COPY = HERE / "_gate_s_mutated.py"
REPORT = "analysis/reports/s112_baseline.json"

PY = "/opt/homebrew/bin/python3.11"

# (label, needle, replacement, which guard must fire)
MUTATIONS = [
    ("S1 ladder count",
     'if len({d for d, _, _ in ladder}) != 5:',
     'if len({d for d, _, _ in ladder}) != 4:',
     "the five-detent assertion"),
    ("S1 noon twin identity",
     'REF_OD = "ref-od.wav"',
     'REF_OD = "NOT-A-FILE.wav"',
     "the DRIVE-noon = ref-od known answer"),
    ("S2 model pad known answer",
     'if worst_val > PAD_TOL_DB or worst_flat > FLAT_TOL_DB:',
     'if worst_val > -1.0 or worst_flat > FLAT_TOL_DB:',
     "the harness-pad reproduction"),
    ("S2 admissibility (flatness)",
     'FLAT_TOL_DB = 0.01',
     'FLAT_TOL_DB = 10.0',
     "the pure-gain requirement -- the contaminated pair would enter the consensus"),
    ("S2 four-independent-pairs rule",
     'if len(flat) < 4:',
     'if len(flat) < 99:',
     "the single-source guard"),
    ("S3 model interlock known answer",
     'want = -(pad_model - pad_pedal)',
     'want = -(pad_model - pad_pedal) + 0.5',
     "the no-free-parameter interlock prediction"),
    ("S4 step-mismatch bound",
     'if bound > 0.5 * biggest:',
     'if bound > 0.0 * biggest:',
     "the comparability bound"),
    ("S6 bleed-free existence",
     'bleedfree = [r for r in rows if r[0] < 1e-12]',
     'bleedfree = [r for r in rows if r[0] < -1.0]',
     "the 'the OD path is unreadable' refusal"),
    ("S7 matched bleed-free existence",
     'bf_pairs = [(n, f) for n, f in od if n in bleedfree and n in matched]',
     'bf_pairs = []',
     "the refusal to print a verdict with no usable pair"),
]


def run(path: pathlib.Path):
    p = subprocess.run([PY, str(path.relative_to(ROOT)), REPORT],
                       cwd=ROOT, capture_output=True, text=True)
    tail = [l for l in (p.stdout + p.stderr).strip().splitlines() if l.strip()]
    return p.returncode, (tail[-1] if tail else "<no output>")


def main():
    src = SRC.read_text()

    # -- CONTROL first.  Without this every result below is uninterpretable.
    COPY.write_text(src)
    rc, last = run(COPY)
    print(f"CONTROL (unmutated copy, run from {ROOT.name}/): rc={rc}")
    print(f"   {last}")
    if rc != 0:
        COPY.unlink(missing_ok=True)
        sys.exit("MUTATION TEST ABORTED: the unmutated copy does not pass, so nothing below would "
                 "be attributable to a mutation (s107/s110's trap).")
    print()

    bad = []
    for label, needle, repl, guard in MUTATIONS:
        if needle not in src:
            bad.append(f"{label}: needle not found in source -- the mutation is VACUOUS and tests "
                       f"nothing (suspect the mutation before the guard)")
            print(f"⛔ {label:32s} VACUOUS -- needle absent")
            continue
        if src.count(needle) != 1:
            bad.append(f"{label}: needle matches {src.count(needle)} times -- ambiguous mutation")
            print(f"⛔ {label:32s} AMBIGUOUS -- {src.count(needle)} matches")
            continue
        COPY.write_text(src.replace(needle, repl))
        rc, last = run(COPY)
        ok = rc != 0
        print(f"{'✅' if ok else '❌'} {label:32s} rc={rc}  ({guard})")
        print(f"      {last[:150]}")
        if not ok:
            bad.append(f"{label}: mutation did NOT fire {guard}")

    COPY.unlink(missing_ok=True)
    print()
    if bad:
        print("MUTATION TEST FAILED:")
        for b in bad:
            print(f"  - {b}")
        sys.exit(1)
    print(f"== all {len(MUTATIONS)} mutations fired; the unmutated control passed ==")


if __name__ == "__main__":
    main()
