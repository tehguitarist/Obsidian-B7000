#!/usr/bin/env python3.11
"""Mutation test for GATE AA (`analysis/drive_locus_gate.py`).  Session 129.

MECHANICS, and why they are what they are -- every one of these is a rule this project paid for:

  * the patched copy LIVES in `analysis/` (so its sibling imports resolve) and RUNS from the repo
    root (so its data paths resolve).  s110 got a clean 7/7 "PASS" from `/tmp` where every arm was
    a `ModuleNotFoundError`, and a 7/7 `FileNotFoundError` from the other ordering.
  * an UNMUTATED CONTROL runs first.  If the control does not pass, no arm below is attributable.
  * every arm mutates the DATA, never a predicate.  `if False:` DISABLES a guard rather than firing
    it (s114), and loosening a comparison makes a guard refuse while printing two identical numbers
    (s122).
  * every arm carries an expected EXIT CODE *and* a string the output must contain.  s108's rule
    means a well-built gate's headline findings deliberately do NOT change the exit code, so an
    rc-only runner can never test a computed verdict -- which is exactly where
    `computed-verdicts-not-narrated` (five occurrences) keeps re-appearing.  Arms 4 and 5 have
    `expect_rc = 0` and demand the OPPOSITE verdict: if a conclusion has quietly become hard-coded
    narration, they fail.
  * the runner checks the guard's IDENTITY (its `[TAG]`), not merely a non-zero exit (s117) -- a
    crash also exits non-zero.

Run:  /opt/homebrew/bin/python3.11 analysis/_mutate_gate_aa.py
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "drive_locus_gate.py")
SRC_REPORT = os.path.join(ROOT, "analysis/reports/s122_feature_locus.json")

COPY = os.path.join(HERE, "_aa_mut.py")
MUT_REPORT = os.path.join(HERE, "reports", "_aa_mut_report.json")
MUT_OUT = os.path.join(HERE, "reports", "_aa_mut_out.json")


# ---- the mutations, all at the DATA level -------------------------------------------------------
def m_none(d):
    return d


def m_drop_rung(d):
    """A rung vanishes from one feature.

    ⚠ THIS ARM WAS FIRST WRITTEN AGAINST AA1 AND WAS CAUGHT BY AA2 INSTEAD -- s119's case, where
    the gate is BETTER than the test's model of it, and the rule is fix the EXPECTATION, not the
    guard.  Here it did both: AA2 was demoting a 3-of-4-rung feature to "unresolved" and excluding
    it silently, which is the very thing AA2 claims to catch, so the gate gained a PARTIAL branch
    and the arm now names AA2.
    """
    d["w6"]["treble_peak"]["pedal"]["medians"].pop()
    return d


def m_bad_verdict(d):
    """W6's stored verdict no longer matches its own medians.  AA1(b) must refuse.

    This is the arm that makes AA1 non-vacuous: arm (a) is exact by construction, so without this
    one AA1 would only ever be testing the rung COUNT.
    """
    d["w6"]["treble_peak"]["pedal"]["verdict"] = "FIXED"
    return d


def m_drop_feature(d):
    """A feature disappears from w6 entirely.  AA2 must refuse rather than quietly reporting 3."""
    del d["w6"]["mid_peak"]
    return d


def m_monotone_midpeak(d):
    """Make the model's mid peak a clean 4/4 dose-response.

    ⚠ expect_rc = 0.  The gate must still run to completion AND must now print the OPPOSITE
    verdict -- item 6's clue HOLDS.  An arm that only checked rc could not see this at all.
    """
    v = d["w6"]["mid_peak"]["model"]["medians"]
    v.sort(reverse=True)
    d["w6"]["mid_peak"]["model"]["span_frac"] = max(v) / min(v) - 1.0
    return d


def m_same_direction(d):
    """Make the pedal's notch and peak move the SAME way (both rising).

    ⚠ expect_rc = 0.  AA6's refutation must evaporate -- scaling a network moves both features the
    same way, which is precisely the case AA6 says it cannot rule out.
    """
    v = d["w6"]["treble_peak"]["pedal"]["medians"]
    v.sort()                       # was falling; now rising, same sense as the notch
    d["w6"]["treble_peak"]["pedal"]["span_frac"] = max(v) / min(v) - 1.0
    return d


ARMS = (
    # name,                  fn,                  expect_rc, must_contain
    ("control (unmutated)",  m_none,              0, "NOT SUPPORTED"),
    ("control (unmutated)2", m_none,              0, "element-value-drift class REFUTED"),
    ("AA2 drop a rung",      m_drop_rung,         1, "[AA2]"),
    ("AA1 stored verdict",   m_bad_verdict,       1, "[AA1]"),
    ("AA2 drop a feature",   m_drop_feature,      1, "[AA2]"),
    ("AA4 mid_peak monotone", m_monotone_midpeak, 0, "localising clue"),
    ("AA6 same direction",   m_same_direction,    0, "NOT REFUTED by this test"),
)

# Arms 6 and 7 assert a verdict FLIP, so the required string alone is not enough -- record what the
# output must NOT say as well, or "localising clue" would match the unmutated line too.
FORBID = {
    "AA4 mid_peak monotone": "clue (\"we already have a drive-dependent mechanism at ~450 Hz\"): NOT SUPPORTED",
    "AA6 same direction": "element-value-drift class REFUTED",
}


def build_copy():
    src = open(GATE).read()
    src = src.replace('W_REPORT = "analysis/reports/s122_feature_locus.json"',
                      f'W_REPORT = {json.dumps(os.path.relpath(MUT_REPORT, ROOT))}')
    src = src.replace('OUT_JSON = "analysis/reports/s129_drive_locus.json"',
                      f'OUT_JSON = {json.dumps(os.path.relpath(MUT_OUT, ROOT))}')
    if "_aa_mut_report" not in src:
        sys.exit("REFUSED: the report path was not re-pointed -- the arms would mutate nothing and "
                 "every one would 'pass' against the real report.")
    open(COPY, "w").write(src)


def run_arm(name, fn, expect_rc, must, forbid):
    d = json.loads(open(SRC_REPORT).read())
    json.dump(fn(d), open(MUT_REPORT, "w"))
    p = subprocess.run([sys.executable, os.path.relpath(COPY, ROOT)],
                       cwd=ROOT, capture_output=True, text=True)
    out = p.stdout + p.stderr
    rc_ok = (p.returncode != 0) == (expect_rc != 0)
    has = must in out
    forbidden = (forbid in out) if forbid else False
    tag = re.search(r"REFUSED \[(\w+)\]", out)
    if not rc_ok:
        return "WRONG RC", f"rc={p.returncode}, expected {'non-zero' if expect_rc else '0'}"
    if not has:
        return "NARRATED", f"output never contained {must!r}"
    if forbidden:
        return "NARRATED", f"verdict did not flip -- output still contains {forbid!r}"
    if expect_rc and tag and f"[{tag.group(1)}]" != must:
        return "WRONG GUARD", f"fired {tag.group(0)}, expected {must}"
    return "PASS", (tag.group(0) if tag else "verdict flipped as required")


def main():
    build_copy()
    print("=" * 92)
    print("MUTATION TEST -- GATE AA")
    print("=" * 92)
    bad = 0
    for name, fn, rc, must in ARMS:
        verdict, why = run_arm(name, fn, rc, must, FORBID.get(name))
        mark = "✅" if verdict == "PASS" else "❌"
        print(f"  {mark} {verdict:<12} {name:<24} {why}")
        if verdict != "PASS":
            bad += 1
        if name.startswith("control") and verdict != "PASS":
            print("\n  ⛔ THE CONTROL FAILED -- no arm below is attributable to its mutation.")
            break
    for f in (COPY, MUT_REPORT, MUT_OUT):
        if os.path.exists(f):
            os.remove(f)
    print("=" * 92)
    print(f"  {len(ARMS) - bad}/{len(ARMS)} arms behaved as specified.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
