#!/usr/bin/env python3.11
"""Mutation runner for GATE BI (analysis/grunt_mix_gate.py), session 179, open item 18.

Disciplines carried in (measurement-discipline.md §3):
  * the mutant LIVES in analysis/ (sibling imports resolve) and RUNS from the repo root
    (data paths resolve) -- s110, both halves.
  * the mutant path is PID-unique -- s139, so two concurrent runs cannot score each other's file.
  * the mutant's OUTPUT path is redirected to a PID-unique name and the redirect REFUSES if its
    pattern does not apply -- s153, so a faithful copy cannot overwrite the real gate's report.
  * an UNMUTATED control runs first; if it does not pass, no arm below is attributable.
  * arms check GUARD IDENTITY (a token the failure must contain), not just rc != 0 -- s117.
  * arms with expect_rc == 0 test a COMPUTED VERDICT: they break the data behind a conclusion and
    require the gate to print the OPPOSITE one.  s128's rule -- without these, a conclusion that
    has silently become hard-coded narration passes.

Run: /opt/homebrew/bin/python3.11 analysis/_mutate_gate_bi.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "grunt_mix_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bi_{os.getpid()}.py")

# (name, pattern, replacement, expect_rc, must_contain, why)
ARMS = [
    # ---- the CONTROL for a guard's own reachability ------------------------------------------
    ("bi0-guard-control",
     r'    if bad:\n        die\("BI0a", "GRUNT label/settings mismatch',
     '    if False:\n        die("BI0a", "GRUNT label/settings mismatch',
     0, "MATCHES its label (15/15)",
     "disable the GRUNT-label guard with the labels CORRECT.  The gate must still pass, which "
     "proves the guard is not what is producing the pass."),

    # ---- validity guards ----------------------------------------------------------------------
    ("bi0a-grunt-label",
     r'\("flat",  "bleedfree"\): "level-1700_grunt-flat_base-od\.wav",',
     '("flat",  "bleedfree"): "level-1700_grunt-boost_base-od.wav",',
     1, "BI0a",
     "label a GRUNT-boost capture as flat.  ⚠⚠ THE s151 TRAP: every capture without a `grunt-` "
     "token defaults to CUT and a label is a guess about a naming convention (s114).  BI0a must "
     "read the position out of parse_capture and refuse."),

    ("bi0a-mix-order",
     r'MIX_ORDER = \("bleedfree", "blendmax", "blend1430", "blend1200", "blend0930"\)',
     'MIX_ORDER = ("blendmax", "bleedfree", "blend1430", "blend1200", "blend0930")',
     1, "BI0a",
     "shuffle the mix ladder out of clean-fraction order.  BI0a must refuse: the bleed-free/mixed "
     "decomposition the whole gate rests on needs cf = 0 to be one end of a real ordering."),

    ("bi0b-known-answer",
     r'    return float\(np\.max\(d\[pk\]\) - np\.min\(d\[nt\]\)\)',
     '    return float(np.max(d[pk]) - np.min(d[nt])) + 0.4',
     1, "BI0b",
     "bias the C1 estimator by 0.4 dB.  The CROSS-SESSION known answer (s172 §1's pedal-side "
     "13.92, binary-independent) must refuse — without it this gate's C1 is not s172's C1 and "
     "none of the comparisons to s172/s178 transfer."),

    ("bi0c-nonvacuity",
     r'    bf_model = \[c1_of\(curves\(CAPS\[\(g, "bleedfree"\)\]\)\[2\]\) for g in GRUNTS\]',
     '    bf_model = [7.0 for g in GRUNTS]',
     1, "BI0c",
     "flatten the model's bleed-free C1 across GRUNT.  The non-vacuity guard must refuse: an "
     "inert axis makes every comparison below a comparison between identical things (s110)."),

    ("bi0d-clean-leak",
     r'CLEAN_ONLY = "blend-0700_base-od\.wav"',
     'CLEAN_ONLY = "ref-od.wav"',
     1, "BI0d",
     "point the clean control at a BLEND=max capture, where the OD branch IS in circuit.  BI0d "
     "must refuse — every ratio in BI2/BI6 differences against this curve, so if it carries the "
     "OD-path terms the ratio is measuring them against themselves."),

    # ---- computed-verdict arms: expect_rc 0, the OPPOSITE verdict must be printed -------------
    ("bi2-verdict-mix",
     r'        dm = ratio\[\("boost", n\)\]\[1\] - ratio\[\("cut", n\)\]\[1\]',
     '        dm = 5.0 * (ratio[("boost", n)][1] - ratio[("cut", n)][1])',
     0, "CONSISTENT with item 18's attribution",
     "inflate the model's OD:clean GRUNT dependence 5x.  BI2 must then SUPPORT item 18's "
     "attribution instead of refuting it — the refutation is the session's load-bearing claim and "
     "if it survives this it is narration."),

    ("bi3-verdict-branch",
     r'        rows\[g\] = \(c1_of\(ped\), c1_of\(mod\)\)',
     '        rows[g] = (c1_of(ped), c1_of(mod) + 5.0)',
     0, "at 0 of 3 positions",
     "push the model's bleed-free C1 5 dB off at every position.  BI3 must report 0 of 3 matched "
     "rather than 2 of 3, or its 'the OD branch is right at flat and boost' is hard-coded."),

    ("bi4-verdict-wander",
     r'            f_bf\[\(g, side\)\], f_mix\[\(g, side\)\] = nb, nm',
     '            f_bf[(g, side)], f_mix[(g, side)] = nb, (nm if side == "ped" else nb)',
     0, "NO added cancellation is indicated",
     "pin the MODEL's composite notch to its own bleed-free null.  BI4 must then report no added "
     "cancellation — the mechanism half of this session's finding."),

    ("bi4a-window-artefact",
     r'            vals = \[extrema_f\(dmx, w\)\[1\] for w in NT_WIDE\]',
     '            vals = [extrema_f(dmx, w)[1] + 3.0 * i for i, w in enumerate(NT_WIDE)]',
     0, "NOT READ",
     "make the composite notch move with the analysis window.  BI4a must flag it and BI4 must "
     "REFUSE to read the wander — s151's 'a minimum resting on a bound is a refusal', which is "
     "the objection BI4's headline has to survive."),

    ("bi5-verdict-licence",
     r'HW_LICENCE = \{"cut": \(1\.6, 1\.6\), "flat": \(3\.5, 4\.8\), "boost": \(None, None\)\}',
     'HW_LICENCE = {"cut": (1.6, 1.6), "flat": (0.0, 0.5), "boost": (None, None)}',
     0, "OVER the hardware licence",
     "tighten the flat licence below the measured value.  BI5 must print OVER and withdraw the "
     "PASS — the verdict that closes item 18 must come from the comparison, not from the text."),

    ("bi5-identity",
     r'S178_MODEL_MINUS_ND = \{"cut": 0\.24, "flat": 4\.51, "boost": 5\.38\}',
     'S178_MODEL_MINUS_ND = {"cut": 0.24, "flat": 9.99, "boost": 5.38}',
     0, "the two columns DIFFER",
     "break session 178's recorded column.  BI5 must report the identity FAILING and withdraw the "
     "transfer of item 17's grading — an identity asserted rather than measured is the whole risk."),
]


def run(path, out_json):
    return subprocess.run([sys.executable, path, "--json", out_json],
                          cwd=ROOT, capture_output=True, text=True)


def main():
    src = open(GATE).read()
    out_json = f"analysis/reports/_mutate_bi_{os.getpid()}.json"

    print("=" * 92)
    print("MUTATION RUNNER — GATE BI (grunt_mix_gate.py)")
    print("=" * 92)

    open(MUTANT, "w").write(src)
    ctl = run(MUTANT, out_json)
    if ctl.returncode != 0:
        print("⛔ CONTROL FAILED — no arm below is attributable.\n")
        print(ctl.stdout[-3000:], ctl.stderr[-2000:])
        os.remove(MUTANT)
        sys.exit(1)
    print("control (unmutated): PASS\n")

    fails = []
    for name, pat, rep, exp_rc, must, why in ARMS:
        mutated, n = re.subn(pat, rep, src, count=1)
        if n != 1:
            print(f"  {name:24s} ⛔ PATCH DID NOT APPLY (pattern matched {n} times)")
            fails.append(name)
            continue
        open(MUTANT, "w").write(mutated)
        r = run(MUTANT, out_json)
        blob = r.stdout + r.stderr
        if r.returncode != exp_rc:
            print(f"  {name:24s} ⛔ rc {r.returncode}, expected {exp_rc}"
                  + (" — GUARD DEAD" if exp_rc else " — crashed where a verdict was wanted"))
            print(f"        tail: {blob.strip().splitlines()[-1][:150] if blob.strip() else '(no output)'}")
            fails.append(name)
        elif must not in blob:
            kind = "WRONG GUARD" if exp_rc else "NARRATED"
            print(f"  {name:24s} ⛔ {kind} — output never contained {must!r}")
            fails.append(name)
        else:
            print(f"  {name:24s} ✅ rc={r.returncode}, matched {must!r}")

    os.remove(MUTANT)
    for stray in (os.path.join(ROOT, out_json),):
        if os.path.exists(stray):
            os.remove(stray)

    print()
    print(f"{len(ARMS) - len(fails)}/{len(ARMS)} arms behaved as specified")
    if fails:
        print("⛔ " + ", ".join(fails))
        sys.exit(1)
    print("✅ every guard fires on its own defect and every graded verdict is computed")


if __name__ == "__main__":
    main()
