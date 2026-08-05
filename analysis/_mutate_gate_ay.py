#!/usr/bin/env python3.11
"""Mutation test for GATE AY (analysis/level_taper_reshape.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain — or, for two of
them, one it must NOT contain, because the claim being armed is the ABSENCE of a line and
`must_contain` cannot express that.

  * `expect_rc != 0` arms test the REFUSALS: the imported-coefficient invariant, the bleed-free
    anchor, the EPOCH guard, the well-posedness screen, the known answer, and its vacuity check.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate is quoted for four statements and
    every one must be able to come back as its opposite (`computed-verdicts-not-narrated`, five
    prior occurrences — and s161 committed it *inside* a gate written to apply that rule):
      - "the model MUTES at LEVEL min"                    -> ay2-mute
      - "THE FAMILY IS WHAT DECIDES IT" (vs GATE K)       -> ay3-family
      - "the requirement moves the pot TOWARD the band"   -> ay4-band
      - "0 of 2 REACH, at the family's own SUPREMUM"      -> ay5-reaches

⚠⚠ THE MOST IMPORTANT ARM IS `ay5-reaches`.  AY5(c) is the reason task D closes as specified, so a
hard-coded "0 of 2 REACH" would retire an open work item on narration.  The arm shrinks item 9's
own sensitivity ratios until the bound clears them, which must flip the verdict to "reach".

⚠ THE SECOND MOST IMPORTANT IS `ay1b-epoch`, and it is the only arm that mutates NOTHING: it runs
the unmodified gate against `s146_mastertaper.json`, a report rendered before s156's DSP change.
Every number this gate prints is an absolute level, so the epoch guard is what licenses all of
them — and a guard that has never been seen to fire is a guard nobody has tested (s119).

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139: a fixed mutant filename cannot be run twice
    concurrently, and the arms then score whatever the other run wrote).
  * NO report redirect is needed here, unlike GATE AP/AQ/AR/AX — this gate takes its output path
    as `--json` with NO default, so a mutant invoked without it writes nothing.  That is ASSERTED
    below rather than assumed, because a later default would silently re-arm the s153 hazard
    (a mutant leaving a deliberately falsified report on disk wearing the real gate's name).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **The headroom bound's PREMISE is not mechanically checkable.** That (1-L) is the mixed
    clean-re-OD ratio comes from GATE L's reduction, and AY1 asserts this gate agrees with GATE K
    on the coefficients — but "the LEVEL sensitivity item 9 measures is driven by that ratio" is a
    NECESSARY-condition argument, and the gate says so in AY5(b) in its own words.
  * **The refused hottest column is not armed.** Whether `dB_model(L)` is non-monotone at
    `drv_-6` is a property of the reference and the model, not of this tool; what IS armed is that
    the refusal changes the printed membership (the control's "3 of 4" string).

Run:  python3.11 analysis/_mutate_gate_ay.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "level_taper_reshape.py")
MUT = os.path.join(HERE, f"_mutated_gate_ay_{os.getpid()}.py")

CURRENT = "analysis/reports/s162_shipped.json"     # current-epoch, rendered this session
STALE = "analysis/reports/s146_mastertaper.json"   # pre-s156 DSP change — AY1b must refuse it

# (name, why, [(pattern, replacement), ...], expect_rc, must_contain, must_absent, report)
ARMS = [
    ("control", "unmutated — if this does not pass, nothing below is attributable",
     [], 0, "0 of 2 REACH", None, CURRENT),

    # ---- AY1: the imported invariant and the anchor the whole gate is referred to ---------------
    ("ay1-coef-drift",
     "level_taper_gate's reduction is nudged off level_law_gate's coef_closed, so the two imported "
     "modules disagree and no number below may be quoted",
     [(r'abs\(a - L\.a_of\(Lv\)\)', 'abs(a - L.a_of(Lv) - 1e-9)')],
     1, "AY1 FAIL", None, CURRENT),

    ("ay1-anchor",
     "the anchor test is pointed just below LEVEL max, where the clean coefficient is NOT exactly "
     "zero — the exact zero every absolute instrument in the project reads at must be checked AT "
     "the anchor",
     [(r'if L\.b_of\(1\.0\) != 0\.0:', 'if L.b_of(0.999) != 0.0:')],
     1, "bleed-free anchor", None, CURRENT),

    # ---- AY1b: THE licence.  Mutates nothing; runs against a pre-s156 report. -------------------
    ("ay1b-epoch",
     "the UNMODIFIED gate is run against a report rendered before s156's DSP change — every "
     "number here is an absolute level, so a stale epoch must be REFUSED, not read",
     [], 1, "AY1b", None, STALE),

    # ---- AY2: the well-posedness screen, and the MUTE classification ----------------------------
    ("ay2-all-ambiguous",
     "every detent's across-stimulus spread is inflated past its own requirement, so a knob-keyed "
     "correction is inside the ambiguity of the thing it would fit EVERYWHERE — the gate must "
     "refuse rather than fit (this is task A's closing argument, applied here)",
     [(r'float\(max\(need\) - min\(need\)\)', '1e3')],
     1, "not well posed", None, CURRENT),

    ("ay2-mute",
     "the mute threshold is pushed below any reachable level, so LEVEL min is no longer classified "
     "as a mute — the 'MODEL MUTES' line must disappear, proving it is read from the data and not "
     "printed for a detent chosen by hand",
     [(r'^MUTE_DB = -100\.0$', 'MUTE_DB = -1e9')],
     0, None, "MODEL MUTES", CURRENT),

    # ---- AY3: the known answer, its vacuity, and the family verdict -----------------------------
    ("ay3-ka-broken",
     "the inversion is given a small constant offset, so it no longer returns the shipped taper "
     "when run against the model's own levels — the recovered curve would not be a measurement",
     [(r'return float\(math\.exp\(float\(np\.interp\(target, dB, lo\)\)\)\), "interp"',
       'return float(math.exp(float(np.interp(target, dB, lo)))) + 1e-6, "interp"')],
     1, "does not return the shipped taper", None, CURRENT),

    ("ay3-ka-vacuous",
     "the known answer is made to check ZERO points — it can then neither pass nor fail, and a "
     "known answer that checked nothing licenses nothing (`empty-gate-must-fail`)",
     [(r'            if x not in res\[sw\] or not np\.isfinite\(res\[sw\]\[x\]\[0\]\) or '
       r'res\[sw\]\[x\]\[0\] < MUTE_DB:', '            if True:')],
     1, "empty-gate-must-fail", None, CURRENT),

    ("ay3-family",
     "the required taper is replaced by the SHIPPED one, so the free curve can buy nothing and the "
     "verdict must fall back to GATE K's closure — otherwise 'THE FAMILY IS WHAT DECIDES IT' is a "
     "caption, and it is the sentence that re-opens a question closed since s103",
     [(r'score\(\{x: need_tap\[x\]\["mean"\] for x in need_tap\}\)',
       'score({x: (0.0 if x <= 0.0 else x ** p) for x in need_tap})')],
     0, "STANDS on this epoch", None, CURRENT),

    # ---- AY4: the outside corroboration -------------------------------------------------------
    ("ay4-band",
     "the textbook taper band is moved so the SHIPPED value sits inside it and the required value "
     "does not — the 'moves TOWARD the band' line must then read AWAY FROM, or the one piece of "
     "outside corroboration in this gate is narration",
     [(r'^A_TAPER_LO, A_TAPER_HI = 0\.10, 0\.15$', 'A_TAPER_LO, A_TAPER_HI = 0.20, 0.25')],
     0, "AWAY FROM", None, CURRENT),

    # ---- AY5(c): THE arm.  This verdict is why task D closes as specified. ----------------------
    ("ay5-reaches",
     "item 9's own sensitivity ratios are shrunk until the taper family's supremum clears them, so "
     "the bound must report that the lever REACHES — if it still says 0 of 2, the refutation of "
     "task D is hard-coded",
     [(r'targets = \{"bass notch \(s125\)": 30\.0 / 17\.2, '
       r'"treble_notch \(s133 AE4\)": 24\.3 / 9\.1\}',
       'targets = {"bass notch (s125)": 1.05, "treble_notch (s133 AE4)": 1.10}')],
     0, "reach at the supremum", None, CURRENT),

    # ---- AY6: the corner nothing may move ------------------------------------------------------
    ("ay6-corner",
     "the recovered curve's top is nudged off 1.0 where only AY6 looks, so the bleed-free corner "
     "moves — GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho| and OdToneRestore's base row all "
     "read there",
     [(r'a1, b1 = K\.coef_closed\(1\.0, Lm\.get\(TOP, 1\.0\)\)',
       'a1, b1 = K.coef_closed(1.0, Lm.get(TOP, 1.0) * 0.99)')],
     1, "AY6 FAIL", None, CURRENT),
]


def preflight():
    """Assert the property that makes a report redirect unnecessary (see the docstring)."""
    src = open(SRC).read()
    m = re.search(r'ap\.add_argument\("--json",\s*default=([^)\s,]+)', src)
    if m is None:
        sys.exit("_mutate_gate_ay: could not find the --json argument at all — the assumption that "
                 "a mutant writes no report is unverified, so refusing to run")
    if m.group(1) != "None":
        sys.exit(f"_mutate_gate_ay: --json now defaults to {m.group(1)} — a mutant would write a "
                 f"falsified report over the real gate's (s153).  Add a PID-unique redirect before "
                 f"running this again.")
    print(f"  preflight OK  --json has no default, so a mutant invoked without it writes nothing")


def build(muts):
    src = open(SRC).read()
    for pat, rep in muts:
        new, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None
        src = new
    open(MUT, "w").write(src)
    return MUT


def main():
    n_cv = sum(1 for a in ARMS if a[3] == 0) - 1
    print(f"MUTATION TEST — GATE AY  ({len(ARMS)} arms, {n_cv} computed-verdict)\n")
    preflight()
    print()
    bad = []
    for name, why, muts, exp_rc, need, absent, report in ARMS:
        if build(muts) is None:
            print(f"  ❌ {name:18} PATCH DID NOT APPLY — the arm tests nothing")
            bad.append(name)
            continue
        r = subprocess.run([sys.executable, os.path.relpath(MUT, ROOT), report],
                           cwd=ROOT, capture_output=True, text=True)
        out = r.stdout + r.stderr
        ok_rc = (r.returncode != 0) if exp_rc else (r.returncode == 0)
        ok_txt = (need is None or need in out) and (absent is None or absent not in out)
        if ok_rc and ok_txt:
            print(f"  ✅ {name:18} rc={r.returncode}  {why[:64]}")
        else:
            reason = ("rc" if not ok_rc else
                      ("missing " + repr(need) if need and need not in out
                       else "did not suppress " + repr(absent)))
            print(f"  ❌ {name:18} rc={r.returncode} ({reason})  — {why[:54]}")
            bad.append(name)
        if os.path.exists(MUT):
            os.remove(MUT)

    print(f"\n  {len(ARMS) - len(bad)}/{len(ARMS)} arms behaved as specified")
    if bad:
        sys.exit(f"MUTATION TEST FAILED: {', '.join(bad)}")


if __name__ == "__main__":
    main()
