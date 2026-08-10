#!/usr/bin/env python3.11
"""Mutation runner for GATE BX (`n1_flat_boost_gate.py`).

Conventions this file inherits, each paid for by a real session:
  * the mutant LIVES in the gate's own directory (sibling imports) and RUNS from the repo root
    (data paths) -- s110, where a /tmp copy scored 5/5 PASS on 5 ModuleNotFoundErrors;
  * its path is PID-UNIQUE -- s139, where two concurrent runs shared one filename;
  * its `--json` is redirected to a PID-unique path and the redirect REFUSES if it does not apply
    -- s153, where a faithful mutant overwrote the real gate's artefact with a deliberately
    falsified one;
  * an unmutated CONTROL runs first -- s107;
  * every arm names the GUARD it expects, and a non-zero exit with the WRONG tag is a failure, not
    a pass -- s117;
  * `expect_rc == 0` arms break the DATA behind a computed verdict and require the gate to print
    the OPPOSITE verdict -- s128, because s108's rule guarantees the load-bearing statements never
    change the exit code.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "n1_flat_boost_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_bx_{os.getpid()}.py")
JSON = f"/tmp/_bx_mutant_{os.getpid()}.json"

# (label, [(pattern, replacement), ...], expect_rc, must_contain)
ARMS = [
    ("control", [], 0, "NOTHING TO SHIP"),

    # ---- refusal arms ---------------------------------------------------------------------
    ("bx0-stale-binary",
     # ⚠ Patches the SOURCE-SCAN, not the result line.  A first draft patched `newer = [...]`
     # directly and passed against a guard that was VACUOUS (`hasattr(W, "_src_files")` was False,
     # so the real computation returned [] and could never fire).  Mutate the INPUT to a guard,
     # never its output, or the arm tests the `if` and not the thing feeding it.
     [(r'bmt = os\.stat\(binp\)\.st_mtime', 'bmt = 0.0')],
     1, "postdate the render binary"),

    ("bx0-scan-empty",
     # The vacuity the first draft had: if the scan finds nothing, the guard must REFUSE rather
     # than silently pass.
     [(r'glob\.glob\("src/\*\*/\*", recursive=True\)', 'glob.glob("NO_SUCH_DIR/**/*", recursive=True)')],
     1, "would be vacuous"),

    ("bx0c-vacuous-arm",
     # An arm that changes nothing must be caught: the scope check requires flat/boost to MOVE.
     [(r'probe = \("--fit", "clipC15=2200e-9", "--fit", "odMakeupLowCutDb=2\.2"\)',
       'probe = ()')],
     1, "BX0c"),

    ("bx0-forbidden-dir",
     # Rendering into a read-only epoch must be refused by assertion, not merely discouraged.
     [(r'^REN_DIR = "build/n1_frontier"', 'REN_DIR = BV.REN_DIR')],
     1, "refusing to render into the READ-ONLY cache"),

    ("bx1-known-answer",
     # Perturb the comparison against GATE BV's stored numbers.
     [(r'got, want, n_w = med\(cells\), st\.get\("area_db"\), st\.get\("n"\)',
       'got, want, n_w = med(cells) + 1.0, st.get("area_db"), st.get("n")')],
     1, "BX1"),

    # ---- computed-verdict arms (rc == 0; the VERDICT must flip) ------------------------------
    ("bx2-carrier-flips",
     # Make the neighbour carry the difference: the headline must stop surviving.
     [(r'dp\.append\(cell\["comb_m"\]\[NEIGHBOUR\]\["area_db"\]\n\s*- cell\["comb_p"\]\[NEIGHBOUR\]\["area_db"\]\)',
       'dp.append(99.0 * (cell["comb_m"][FEAT]["area_db"] - cell["comb_p"][FEAT]["area_db"]))')],
     0, "is REFUTED -- it is the neighbour, not N1"),

    ("bx3-no-selection",
     # Equalise the two floor-margin populations: the selection verdict must stand down.
     [(r'ref_fm\.append\(m\["floor_margin_db"\]\)', 'ref_fm.append(-99.0)')],
     0, "no selection detected"),

    ("bx4-model-is-short",
     # Push the MODEL's LF far below the pedal's: BX4 must then AGREE the null is deeper.
     # ⚠⚠ A first draft subtracted 50 dB inside `bandv` itself.  `bandv` is called for BOTH sides
     # and the readings are a DIFFERENCE, so the perturbation cancelled EXACTLY and the arm read
     # `WRONG GUARD / NARRATED` against a working gate -- `difference-statistics-hide-common-mode`
     # (s74/s75) committed inside a mutation arm, and s110's "suspect the mutation before the
     # guard" resolving to a vacuous mutation for the second time in this project's runners.
     # The perturbation must land on ONE OPERAND, at the call site.
     # The lookbehind excludes gate_bx5's `bacc[b].append(...)`, which ends in the same three
     # characters -- `\b` cannot separate them, both sides being word characters.
     [(r'(?<![a-z])acc\[b\]\.append\(bandv\(cell\["model"\], lo, hi\)',
       'acc[b].append(bandv(cell["model"], lo, hi) - 50.0')],
     0, "SHORT of LF, consistent with a genuinely deeper null"),

    ("bx5-dominating-arm",
     # Make one arm beat SHIP everywhere: the frontier must name it and the verdict must change.
     [(r'ship = res\[g\]\["arms"\]\[SHIP_ARM\]',
       'ship = dict(res[g]["arms"][SHIP_ARM]);\n'
       '        ship.update({k: 99.0 for k in list(BANDS) + ["mean_abs_40_80"]})')],
     0, "a dominating arm EXISTS"),

    ("bx6-s187-breaks",
     # Move the published window off the measurement: the cross-session answer must fail loudly.
     [(r'^S187_GLOBAL_LO, S187_GLOBAL_HI = 3\.2, 9\.7',
       'S187_GLOBAL_LO, S187_GLOBAL_HI = 30.0, 90.0')],
     0, "does NOT reproduce -- re-open it"),
]


def build(subs):
    src = open(SRC).read()
    for pat, rep in subs:
        new, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None, f"PATCH DID NOT APPLY: {pat[:70]}"
        src = new
    # s153: redirect the mutant's artefact, and REFUSE if the redirect is a no-op.
    src, n = re.subn(r'ap\.add_argument\("--json"\)',
                     f'ap.add_argument("--json", nargs="?", const={JSON!r}, default={JSON!r})', src)
    if n == 0:
        return None, "JSON REDIRECT DID NOT APPLY -- refusing to run (it would clobber the real artefact)"
    return src, None


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    arms = [a for a in ARMS if only is None or only in a[0]]
    if not arms:
        print(f"⛔ no arm matches {only!r}")
        sys.exit(1)
    print(f"GATE BX mutation runner — mutant {os.path.basename(MUT)}"
          + (f"  [filter: {only}]" if only else "") + "\n")
    npass = 0
    for label, subs, want_rc, needle in arms:
        src, err = build(subs)
        if err:
            print(f"  ⛔ {label:22s} {err}")
            continue
        open(MUT, "w").write(src)
        try:
            p = subprocess.run([sys.executable, MUT, "--json"], cwd=ROOT,
                               capture_output=True, text=True, timeout=3600)
            out = p.stdout + p.stderr
            rc_ok = (p.returncode != 0) == (want_rc != 0)
            hit = needle in out
            if rc_ok and hit:
                print(f"  ✅ {label:22s} rc={p.returncode} — guard/verdict identified")
                npass += 1
            elif not rc_ok:
                print(f"  ⛔ {label:22s} rc={p.returncode}, wanted {'non-zero' if want_rc else '0'}"
                      f"  → GUARD DEAD (or the mutation is VACUOUS — suspect the mutation first, s110)")
            else:
                print(f"  ⛔ {label:22s} rc={p.returncode} but the expected text is absent"
                      f"  → WRONG GUARD / NARRATED: {needle!r}")
                tail = [l for l in out.splitlines() if l.strip()][-3:]
                for l in tail:
                    print(f"        | {l[:110]}")
        except subprocess.TimeoutExpired:
            print(f"  ⛔ {label:22s} TIMEOUT")
    for p in (MUT, JSON):
        if os.path.exists(p):
            os.remove(p)
    print(f"\n  {npass}/{len(arms)} arms")
    sys.exit(0 if npass == len(arms) else 1)


if __name__ == "__main__":
    main()
