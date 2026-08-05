#!/usr/bin/env python3.11
"""Mutation test for GATE AX (analysis/notch_shoulder_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain — or, for two of
them, a string it must NOT contain, because the claim being armed is the ABSENCE of a warning and
`must_contain` cannot express that (a verdict that can only ever fire one way is narration).

  * `expect_rc != 0` arms test the REFUSALS: the inertness known answer that licenses every
    difference this gate reports, and the empty-membership guard.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate exists to be quoted for five
    statements — "the section IS reachable", "it buys ~nothing on the curve", "it loses
    like-for-like", "the table it wants has no law", and "the shipped error is already inside the
    target's own spread" — and every one of them must be able to come back as its opposite
    (`computed-verdicts-not-narrated`, four prior occurrences).

⚠⚠ THE MOST IMPORTANT ARM IS `ax6-spread`.  AX6 is the reason task A closes without a second fit
iteration, so a hard-coded "INSIDE the spread" would retire an open work item on narration.  The
arm flattens the pedal's Q across the stimulus sweeps, which must flip the verdict to "outside".

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path and its REPORT path are PID-UNIQUE, and the report redirect REFUSES if its
    pattern does not apply: a mutant runs `main()` and would otherwise leave a deliberately
    falsified report on disk wearing the real gate's filename (s153).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **AX2's reachability is armed only in the direction that matters.** The arm removes the second
    section's gain range so it cannot beat one section; there is no arm proving the ONE-section
    number is right, because that is GATE AQ's AQ2 and is armed in `_mutate_gate_aq.py`.
  * **The refutation's SCOPE is not mechanically checkable.** That this screens a second peaking
    section AT THE NULL'S OWN CENTRE — and not every conceivable shoulder treatment — is a
    statement about the family, and the gate says so in its own docstring.

Run:  python3.11 analysis/_mutate_gate_ax.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "notch_shoulder_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_ax_{os.getpid()}.py")
MUT_REPORT = os.path.join(HERE, "reports", f"_mutant_ax_{os.getpid()}.json")

# (name, why, [(pattern, replacement), ...], expect_rc, must_contain, must_absent)
ARMS = [
    ("control", "unmutated — if this does not pass, nothing below is attributable",
     [], 0, "REFUTED ON TASK A", None),

    # ---- AX1: the known answer that licenses every difference the gate reports ------------------
    ("ax1-not-inert",
     "the candidate section is no longer inert at gb = 0, so 'shipped' and 'with a section' are "
     "not the same object and every comparison below is between two different chains",
     [(r'(\+ F\.rbj_peak_db\(g, FS, T\["kNotchFreq"\], qb, gb\)\n)', r'\1            + 0.5\n')],
     1, "AX1", None),

    ("ax1-empty",
     "no readable Cut cell — the gate must REFUSE rather than average an empty list "
     "(`empty-gate-must-fail`)",
     [(r'(\"\"\"-> \{drive: \(cut_ship, qn, \[\(g, ped, mod_off, ped_geo, sweep\)\]\)\} for the '
       r'bleed-free Cut set\.\"\"\"\n)', r'\1    return {}\n')],
     1, "empty-gate-must-fail", None),

    # ---- AX2: reachability is a RESULT and must be able to come back negative -------------------
    ("ax2-no-reach",
     "the second section is given no gain range, so it cannot beat one section — AX2 must say the "
     "premise was not reproduced instead of printing the confirmation unconditionally",
     [(r'for gb in \(4\.0, 8\.0, 12\.0, 16\.0\):', 'for gb in (0.0,):')],
     0, "did not improve reachability", None),

    # ---- AX3: "it buys ~nothing on the curve" ---------------------------------------------------
    ("ax3-buys-nothing",
     "the third section is made structurally inert inside the FIT, so the fit it buys must read "
     "0.000 dB — proves the number is computed from the two fits and not printed from memory",
     [(r'return r \+ F\.rbj_peak_db\(f, FS, fn, p\[6\], p\[7\]\) if with_broad else r',
       'return r')],
     0, "0.000 dB median", None),

    ("ax3-one-signed",
     "the free fit is denied negative broad gains, so the 'CHANGES SIGN' finding must disappear "
     "from AX3's own count — the sign change is a measurement, not a caption",
     [(r'\(\[0\.3, -6\.0\] if with_broad else \[\]\)', '([0.3, 0.0] if with_broad else [])')],
     0, "0 negative", None),

    # ---- AX4: the like-for-like control ---------------------------------------------------------
    ("ax4-c-wins",
     "arm C's curve residual is forced to zero, so the third section must beat the re-solve and "
     "AX4 must SAY so — the 'it LOSES' line is otherwise unfalsifiable",
     [(r'            rc = \(curve_rms\(', '            rc = (0.0 * curve_rms(')],
     0, "beat the re-solve", None),

    # ---- AX5: "the requested table has no law" --------------------------------------------------
    ("ax5-one-signed",
     "the broad-gain ladder is made one-signed, so the sign-change warning must NOT fire — a "
     "warning that prints whatever the data says is not a finding",
     # ⚠ the absent string is AX5's OWN wording, not the phrase "changes sign" — AX3 legitimately
     # reports a sign change of a different quantity in the same run, and a first draft of this arm
     # armed on the shared phrase and duly failed against a correct gate.
     [(r'^GB_LADDER = np\.arange\(-14\.0, 18\.01, 1\.0\)$',
       'GB_LADDER = np.arange(1.0, 18.01, 1.0)')],
     0, None, "NO LAW TO SHIP"),

    # ---- AX6: THE arm.  This verdict is why task A closes. --------------------------------------
    ("ax6-spread",
     "the pedal's Q is flattened across the stimulus sweeps, so its spread collapses and the "
     "shipped error must fall OUTSIDE it — if this still prints INSIDE, the reason task A closes "
     "is narration",
     [(r'qs = \[pg\[AQ\.QKEY\] for _, _, _, pg, _ in cs\]',
       'qs = [10.0 for _, _, _, pg, _ in cs]')],
     0, "outside", None),
]


def build(muts):
    src = open(SRC).read()
    for pat, rep in muts:
        new, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None
        src = new
    # PID-unique report path, and REFUSE if the redirect does not apply (s153) — a mutant runs
    # main() and would otherwise overwrite the real gate's report with a falsified one.
    new, n = re.subn(r'^REPORT = os\.path\.join\(.*?\)$',
                     f'REPORT = {MUT_REPORT!r}', src, flags=re.M | re.S)
    if n != 1:
        sys.exit("_mutate_gate_ax: the report redirect did not apply — refusing to run a mutant "
                 "that would write the real gate's report")
    open(MUT, "w").write(new)
    return MUT


def main():
    print(f"MUTATION TEST — GATE AX  ({len(ARMS)} arms, {sum(1 for a in ARMS if a[3] == 0) - 1} "
          f"computed-verdict)\n")
    bad = []
    for name, why, muts, exp_rc, need, absent in ARMS:
        if build(muts) is None:
            print(f"  ❌ {name:18} PATCH DID NOT APPLY — the arm tests nothing")
            bad.append(name)
            continue
        r = subprocess.run([sys.executable, os.path.relpath(MUT, ROOT)],
                           cwd=ROOT, capture_output=True, text=True)
        out = r.stdout + r.stderr
        ok_rc = (r.returncode != 0) if exp_rc else (r.returncode == 0)
        ok_txt = (need is None or need in out) and (absent is None or absent not in out)
        if ok_rc and ok_txt:
            print(f"  ✅ {name:18} rc={r.returncode}  {why[:66]}")
        else:
            reason = ("rc" if not ok_rc else
                      ("missing " + repr(need) if need and need not in out
                       else "did not suppress " + repr(absent)))
            print(f"  ❌ {name:18} rc={r.returncode} ({reason})  — {why[:56]}")
            bad.append(name)
        for p in (MUT, MUT_REPORT):
            if os.path.exists(p):
                os.remove(p)

    print(f"\n  {len(ARMS) - len(bad)}/{len(ARMS)} arms behaved as specified")
    if bad:
        sys.exit(f"MUTATION TEST FAILED: {', '.join(bad)}")


if __name__ == "__main__":
    main()
