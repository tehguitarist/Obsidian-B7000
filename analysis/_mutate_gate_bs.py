#!/usr/bin/env python3.11
"""Mutation runner for GATE BS (analysis/hf_null_frontier_gate.py), session 195.

Disciplines carried in (measurement-discipline.md §3), same as `_mutate_gate_bh.py`:
  * the mutant LIVES in analysis/ (sibling imports resolve) and RUNS from the repo root
    (data paths resolve) -- s110, both halves.
  * the mutant path and its OUTPUT path are PID-unique -- s139/s153, so two concurrent runs cannot
    score each other's file and a faithful copy cannot overwrite the real gate's report.
  * an UNMUTATED control runs first; if it does not pass, no arm below is attributable.
  * arms check GUARD IDENTITY (a token the failure must contain), not just rc != 0 -- s117.
  * arms with expect_rc == 0 test a COMPUTED VERDICT: they break the data behind a conclusion and
    require the gate to print the OPPOSITE one -- s128.  Three of the five arms here are of that
    kind, because this gate's load-bearing outputs are verdicts, not exits (s108).

⚠ This gate RENDERS.  Every arm re-runs the whole sweep against the shared, binary-stamped render
cache, so a full run is minutes rather than seconds; that is the price of mutating a gate whose
statistics are measurements rather than arithmetic.

Run: /opt/homebrew/bin/python3.11 analysis/_mutate_gate_bs.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "hf_null_frontier_gate.py")
MUTANT = os.path.join(HERE, f"_mutated_gate_bs_{os.getpid()}.py")

# (name, pattern, replacement, expect_rc, must_contain, why)
ARMS = [
    ("bs0-grunt-imbalance",
     r'if min\(by\.values\(\)\) < 8:',
     'if min(by.values()) < 99:',
     1, "BS0",
     "tighten the GRUNT-balance guard past what the capture set can supply.  It must REFUSE -- "
     "this gate's whole correction to s178 is that a cut-heavy pool cannot carry a statistic "
     "whose sign changes across GRUNT, so the balance guard is load-bearing, not decorative."),

    ("bs1-membership-floor",
     r'if min\(by\.get\(g, 0\) for g in GRUNTS\) < 3:',
     'if min(by.get(g, 0) for g in GRUNTS) < 99:',
     1, "BS1",
     "require an unreachable per-position membership.  It must REFUSE rather than proceed to a "
     "balanced aggregate resting on a position that is barely measured."),

    ("bs2-one-signed-centre",
     r'signs = \{np\.sign\(r - 1\.0\) for _, _, r in a\["per"\]\.values\(\)\}',
     'signs = {1.0}',
     0, "one-signed across GRUNT",
     "COMPUTED VERDICT.  Force the sign test to see a single sign; the gate must then print the "
     "one-signed branch instead of the sign-change branch.  Without this arm the sign-change "
     "sentence -- which is the whole reason this gate exists rather than BH4 -- could be "
     "narration that happens to be true."),

    ("bs3-no-dominator",
     r'    if strict:\n',
     '    strict = dom = better = []\n    if strict:\n',
     0, "NO DOMINATING CANDIDATE ANYWHERE",
     "COMPUTED VERDICT.  Empty ALL THREE candidate sets; the gate must print the NO-DOMINATING "
     "branch (s178's own verdict) rather than continuing to claim a shippable candidate.  This is "
     "the arm that proves the headline is derived from the counts and not written into the output."
     "  ⚠ A first draft emptied `dom` ALONE and read NARRATED against a working gate: with `dom` "
     "empty and `better` still populated the gate correctly takes the PARTIAL-WIN branch, so the "
     "arm was vacuous for the token it asserted (s110 — suspect the mutation first; s119 — fix the "
     "EXPECTATION, not the guard).  Emptying all three is what actually reaches the final branch."),

    ("bs4-pinning-inverted",
     r'if sp\(mog\) < sp\(ndg\):',
     'if sp(mog) > sp(ndg):',
     0, "does NOT hold on this axis",
     "COMPUTED VERDICT.  Invert the pinning comparison; the gate must print the branch that "
     "WITHDRAWS the pinning claim.  A pinning finding that survives its own comparison being "
     "flipped is narration -- and this one bounds what the whole family can achieve, so it is "
     "the most expensive sentence in the gate to get wrong."),

    ("bs5-band-median-to-rms",
     r'e = float\(np\.median\(d\)\)',
     'e = float(np.sqrt(np.mean(d ** 2)))',
     0, "MEDIAN over the band's points",
     "Swap s173's MEDIAN band statistic for an rms.  ⚠ This arm is NOT expected to fail: it "
     "exists to keep the alternative REACHABLE and to prove the caveat text is printed either "
     "way, because the rms reading is dominated by the null and reported the opposite ranking on "
     "this gate's own first draft.  The banner must survive the swap."),
]


def run(path):
    return subprocess.run([sys.executable, "-u", path,
                           "--json", f"/tmp/_bs_mutant_{os.getpid()}.json"],
                          cwd=ROOT, capture_output=True, text=True)


def main():
    src = open(GATE).read()

    # s153: redirect the mutant's OWN artefact, and REFUSE if the redirect does not apply --
    # a redirect that silently no-ops restores the exact bug it was added to prevent.
    marker = 'BH.REN_DIR = "build/s195_hf_frontier"'
    if marker not in src:
        sys.exit("_mutate_gate_bs: the render-dir marker is gone; the redirect would silently "
                 "no-op and the mutant would write into the real gate's cache")

    print("=" * 92)
    print("MUTATION RUNNER — GATE BS (hf_null_frontier_gate.py)")
    print("=" * 92)
    print("running the UNMUTATED control first — if it fails, nothing below is attributable\n")
    open(MUTANT, "w").write(src)
    ctl = run(MUTANT)
    if ctl.returncode != 0:
        os.remove(MUTANT)
        sys.exit(f"CONTROL FAILED (rc={ctl.returncode}) — fix the gate before reading any arm\n"
                 + ctl.stdout[-3000:] + ctl.stderr[-2000:])
    print(f"  control: rc=0 ✓  ({len(ctl.stdout.splitlines())} lines)\n")

    ok = 0
    for name, pat, rep, want_rc, token, why in ARMS:
        mutated, n = re.subn(pat, rep, src, count=1)
        if n != 1:
            print(f"  {name:24s} ⛔ PATCH DID NOT APPLY — the arm targets code that has moved; "
                  f"fix the ARM, not the gate")
            continue
        open(MUTANT, "w").write(mutated)
        r = run(MUTANT)
        out = r.stdout + r.stderr
        rc_ok = (r.returncode != 0) if want_rc else (r.returncode == 0)
        tok_ok = token in out
        if rc_ok and tok_ok:
            print(f"  {name:24s} ✓ PASS   (rc={r.returncode}, '{token}' present)")
            ok += 1
        elif not rc_ok:
            print(f"  {name:24s} ⛔ GUARD DEAD (rc={r.returncode}, wanted "
                  f"{'non-zero' if want_rc else 'zero'}) — suspect the MUTATION first (s110)")
        else:
            print(f"  {name:24s} ⛔ {'NARRATED' if want_rc == 0 else 'WRONG GUARD'} — "
                  f"'{token}' absent from the output")
        print(f"      {why}")

    os.remove(MUTANT)
    for junk in (f"/tmp/_bs_mutant_{os.getpid()}.json",):
        if os.path.exists(junk):
            os.remove(junk)
    print(f"\n{ok}/{len(ARMS)} arms pass")
    sys.exit(0 if ok == len(ARMS) else 1)


if __name__ == "__main__":
    main()
