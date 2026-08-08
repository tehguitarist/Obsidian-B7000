#!/usr/bin/env python3
"""Mutation control for GATE BN (analysis/mix_anchor_reanchor_gate.py).

Scores exit code AND a required output token (s128).  BN's load-bearing statements are COMPUTED
VERDICTS that deliberately leave the exit code at 0 — the membership split, the amplification
ratio, the corner identity — so a runner scoring `rc != 0` alone could only test the plumbing.
An arm with expect_rc = 0 breaks the data behind a verdict and requires the gate to print the
OPPOSITE one, so a conclusion that has quietly become narration fails here.

⭐⭐ TWO ARMS REPRODUCE REAL DEFECTS IN THIS GATE'S OWN DRAFTS, which is the only reason they earn
their lines:
  `bn4-tagcollide`  the first draft tagged the in-band render cells `f"band{int(lk*100)}"`, which
                    maps 0.99, 0.995 and 0.999 onto ONE tag.  That collided the render CACHE (each
                    cell re-rendered over the last, saved from being silently wrong only by
                    `curves()`'s own argv stamp) and mis-paired three rows of the ratio table
                    against the FIRST cell's cf and dcut.  Found by reading the printed table; no
                    guard existed.  The shipped gate asserts tag injectivity, and this arm proves
                    that assertion fires.
  `bn4-vacuous`     a draft of BN4 rendered only the four verification cells and reported
                    "RENDERED BAR: MET".  Every MIXED one of them has `dcut` identically 0, so it
                    confirmed 0 -> 0 and bounded no amplification whatsoever — a tautology wearing
                    a measurement's name (`empty-gate-must-fail`, and s110's vacuous-mutation shape
                    pointed at the gate rather than at the runner).  The shipped gate renders the
                    in-band cells and SAYS SO when the verification cells cannot answer.

⚠ RENDER DIRECTORY: redirected to one PID-unique path shared by every arm (GATE BM's rule).  The
curves are a function of their argv, so an arm that does not change a render's argv is a cache hit.
⛔ Arms that never reach BN4 are ordered first — they exit inside BN0/BN1 and cost no renders.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "mix_anchor_reanchor_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bn_{os.getpid()}.py")
PY = "/opt/homebrew/bin/python3.11"
CURVES = f"build/_mut_bn_{os.getpid()}_curves"
JSON = f"build/_mut_bn_{os.getpid()}.json"

# (name, [(pattern, replacement), ...], expect_rc, must_contain, why)
ARMS = [
    ("control", [], 0, "THE CORNER IS RESTORED EXACTLY",
     "unmutated: every guard passes AND the corner identity reaches its real, COMPUTED answer.  "
     "If this does not hold, no arm below is attributable."),

    # ---- BN0: guards that must REFUSE ---------------------------------------------------
    ("bn0b-crossgate",
     [('worst_k = max(abs(T["kNotchMixK"][g][d] - BM.NOTCH_MIX_K[g][d])',
       'worst_k = max(abs(T["kNotchMixK"][g][d] + 1e-3 - BM.NOTCH_MIX_K[g][d])')],
     1, "disagree with GATE BM",
     "make the PARSED tables disagree with GATE BM's transcribed copies.  The gate must refuse: "
     "s149's defect was three gates screening a value set the plugin does not run, and the only "
     "thing that catches it is a cross-gate comparison that is allowed to fail."),

    ("bn0c-pin",
     # ⚠ THE NODE MATTERS (s110, third shape of a vacuous mutation — GATE BL's and BM's runners
     # both hit it).  S(0.441) interpolates between nodes 3 and 4, so perturbing node 0 or 1
     # CANNOT move the pinning; node 3 is what the pinning is made of.
     [('def gate_bn0(T, e_hi, depth_off, state, cand, base, out):',
       'def gate_bn0(T, e_hi, depth_off, state, cand, base, out):\n'
       '    T["kMixS"][3] = 0.100   # MUTATION: break the pinning at the node that sets it')],
     1, "no longer means",
     "perturb S at the node the pinning is made of.  The gate must refuse rather than compute a "
     "re-anchor off a table whose `kNotchGainDb` no longer means 'the cut at the reference mix'."),

    ("bn0d-mincf",
     # ⚠ A DATA-LEVEL mutation, not a predicate flip (s114): cut LEVEL max out of the swept
     # surface, so the minimum genuinely is not the corner's.  Flipping the `if` would test the
     # guard's MESSAGE while leaving the quantity it guards untouched.
     [('    return np.linspace(0.0, 1.0, n_level), np.linspace(0.0, 1.0, n_blend)',
       '    return np.linspace(0.0, 0.999, n_level), np.linspace(0.0, 1.0, n_blend)')],
     1, "minimum clean fraction",
     "make the swept control surface stop short of LEVEL max, so its minimum clean fraction is no "
     "longer the corner's.  Every 'reachable' statement in BN1/BN2 is conditioned on the corner "
     "being where the gate thinks it is, so this must refuse rather than report a band measured "
     "against the wrong endpoint."),

    ("bn0e-spelling",
     [('        return [e_hi] + cfs[1:], list(ss)',
       '        return [e_hi * 1.5] + cfs[1:], list(ss)')],
     1, "spellings of the re-anchor differ",
     "break ONE of the two spellings of the re-anchor so the abscissa-move and the ordinate-solve "
     "stop describing the same line.  The gate's own known answer must catch it — without it, "
     "'which constant do we edit?' silently becomes a second, unmeasured candidate."),

    ("bn0f-vacuity",
     [('    if abs(d_corner) < 1.0:', '    if abs(d_corner) < 1e9:')],
     1, "Every bar below would pass vacuously",
     "force the non-vacuity guard.  A re-anchor that moved nothing would clear every bar in the "
     "gate trivially, so the guard that says the candidate is live must itself be live."),

    ("bn0g-inert",
     [('    if mode == "noop":\n        return cfs, ss',
       '    if mode == "noop":\n        return cfs, [ss[0] + 1e-6] + ss[1:]')],
     1, "arm machinery is not neutral",
     "make the INERT control non-inert.  Every number in BN2/BN3 is an arm-to-arm difference, so "
     "if the arm machinery itself introduces one, none of them is attributable."),

    # ---- BN1/BN2: the computed verdicts -------------------------------------------------
    ("bn1-membership", [
        # Put a verification cell INSIDE the band by moving GATE BM's ladder detent, so the
        # membership half of the verdict has to change its own answer.
        ('    for lt, lv, bt, bv in BM.MIX_CELLS:\n        cells.setdefault((lv, bv), set()).add',
         '    for lt, lv, bt, bv in BM.MIX_CELLS:\n'
         '        lv = 0.96 if abs(lv - 0.875) < 1e-9 else lv   # MUTATION: a detent in the band\n'
         '        cells.setdefault((lv, bv), set()).add')],
     0, "mixed verification cells are over the bar",
     "⭐ COMPUTED VERDICT.  Move one captured detent into the disturbed band.  BN1's headline — "
     "'0 of 20 mixed cells inside the band' — is the whole membership finding, so it must be "
     "computed from the cells rather than narrated: the gate must now say cells ARE over the bar."),

    ("bn2-bar", [
        # Perturb a node the MIXED cells actually sit on (cf 0.56-0.87), in the SHARED part of
        # `reanchor_nodes` so both spellings move together and BN0e does not fire first.  ⚠ A
        # mutation that moved only `abscissa` would be caught by the spelling known answer and
        # report the wrong guard (s119: the gate being better than the test's model of it).
        ('    if mode == "noop":\n        return cfs, ss',
         '    if mode == "noop":\n        return cfs, ss\n'
         '    ss[5] += 0.5   # MUTATION: move a node the mixed cells sit on')],
     0, "EXCEEDED",
     "⭐ COMPUTED VERDICT.  Move the re-anchor at a node the MIXED verification cells actually "
     "sit on.  BN2's `MET` must be computed from the measured worst |dcut| — if it is narrated, "
     "this arm passes while the cells move by half a unit of S."),

    # ---- BN4: the render arms (these cost renders; ordered last) ------------------------
    ("bn4-tagcollide", [
        ('        cells.append((("band" + f"{lk:.4f}".replace(".", "p")), lk, 1.0,',
         '        cells.append((("band" + str(int(lk * 100))), lk, 1.0,')],
     1, "render tags are not injective",
     "reproduce THIS GATE'S OWN first-draft defect: a non-injective render tag that collides the "
     "cache and mis-pairs the ratio table.  The injectivity assertion must fire."),

    ("bn4-vacuous", [
        ('    for lk in (0.94, 0.96, 0.98, 0.99, 0.995, 0.999):\n        cells.append',
         '    for lk in ():\n        cells.append')],
     0, "CANNOT ANSWER THIS SUB-GATE'S OWN",
     "⭐ COMPUTED VERDICT.  Remove the in-band cells, leaving only verification cells whose dcut "
     "is identically 0.  BN4 must SAY it cannot answer its own question rather than reporting "
     "'RENDERED BAR: MET' as though it had measured an amplification."),
]


def run(name, subs, expect_rc, must, why):
    src = open(SRC).read()
    for pat, rep in subs:
        if pat not in src:
            return "PATCH DID NOT APPLY", f"pattern not found: {pat[:70]}"
        src = src.replace(pat, rep, 1)
    # redirect the report + curve dir so an arm cannot overwrite the real artefacts (s153)
    src = src.replace('ap.add_argument("--json", default="analysis/reports/s185_reanchor.json")',
                      f'ap.add_argument("--json", default="{JSON}")')
    src = src.replace('CURVE_DIR = "build/s185_reanchor_curves"', f'CURVE_DIR = "{CURVES}"')
    open(MUTANT, "w").write(src)
    try:
        p = subprocess.run([PY, MUTANT], cwd=ROOT, capture_output=True, text=True, timeout=3600)
    finally:
        if os.path.exists(MUTANT):
            os.remove(MUTANT)
    out = p.stdout + p.stderr
    if p.returncode != expect_rc:
        return "WRONG RC", f"rc {p.returncode}, expected {expect_rc}"
    if must not in out:
        return "NARRATED", f"rc ok but output lacks {must!r}"
    return "PASS", ""


def main():
    only = sys.argv[1:] or None
    npass = 0
    arms = [a for a in ARMS if not only or a[0] in only]
    for name, subs, rc, must, why in arms:
        status, detail = run(name, subs, rc, must, why)
        flag = "PASS" if status == "PASS" else status
        print(f"  [{flag:>18}]  {name}")
        if status != "PASS":
            print(f"       {detail}")
        print(f"       {why}")
        npass += status == "PASS"
    print(f"\n  {npass}/{len(arms)} arms")
    sys.exit(0 if npass == len(arms) else 1)


if __name__ == "__main__":
    main()
