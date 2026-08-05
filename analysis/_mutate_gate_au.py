#!/usr/bin/env python3.11
"""Mutation test for GATE AU (analysis/peak_identifiability_gate.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128):

  * `expect_rc != 0` arms test the REFUSALS (AU0's bound transcription, AU1a's walk identity,
    AU4a's estimator known answers).
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's whole value is four statements
    a reader would quote forward — "the walks are bound-terminated", "the deficit changes sign",
    "the requested gain changes sign with the mix", and "the peak term is NOT separable from A3" —
    and a verdict that cannot become its opposite is narration (`computed-verdicts-not-narrated`).
    ⚠ AU4's verdict WAS narration in the first draft (it printed the "mostly A3" paragraph
    unconditionally); arm 7 exists because writing this runner is what exposed it.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139).
  * the mutant's REPORT path is redirected and the redirect REFUSES if its pattern does not apply
    — a mutant runs `main()`, so without this the last arm's forced-false output is left on disk
    wearing the real gate's filename (s153).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).
  * data-level mutations are preferred to predicate-level ones: `if False:` DISABLES a guard
    rather than firing it (s114), and a mutation on a threshold nowhere near the data does
    nothing (s110's vacuity case).

⚠⚠ WHAT IS **NOT** COVERED, stated rather than left to be discovered:
  * **AU1b has no arm.**  Its verdict branches on a 5 % centre bar that is not this gate's to
    defend — GATE W owns that reading and AU1b only re-reads it as context.  Arming it would test
    GATE W's locator through a proxy.
  * **AU3's stimulus-span figure is printed, not gated.**  It is a spread, and s129's rule is that
    a dispersion statistic may RANK reliability and may not GATE a verdict; the sign-change
    verdict beside it is what carries the conclusion and IS armed (arm 6).
  * **The separability estimator's blindness is structural**: `keep` measures a candidate against
    THIS trend basis over THIS band, so it cannot tell "the device has no peak" from "this band
    cannot see one".  The gate says so in its own docstring; no mutation can reach it.

Run:  python3.11 analysis/_mutate_gate_au.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "peak_identifiability_gate.py")
MUT = os.path.join(HERE, f"_mutated_gate_au_{os.getpid()}.py")
MUT_REPORT = os.path.join(HERE, "reports", f"_mutant_au_{os.getpid()}.json")

# (name, why, [(pattern, replacement), ...], expect_rc, must_contain)
ARMS = [
    ("control", "unmutated — if this does not pass, nothing below is attributable",
     [], 0, "GATE AU"),

    ("au0-bounds-drift",
     "fit_rung's bounds move under the gate; the bound-resting verdict must refuse, not re-scale",
     [(r"F_BOUNDS = \(\[295\.0", "F_BOUNDS = ([296.0")], 1, "AU0"),

    ("au1a-structural",
     "break the closed-form claim that locate()'s walk-break is unreachable (argmin -> argmax in "
     "the adversarial sweep); the gate rests on it and must die rather than proceed",
     [(r"n_breaks \+= int\(np\.any\(dd < dd\[int\(np\.argmin\(dd\)\)\]\)\)",
       "n_breaks += int(np.any(dd < dd[int(np.argmax(dd))]))")], 1, "AU1a"),

    ("au1a-walk-identity",
     "the walk re-implementation reports LESS descent than the drop to its own bound, i.e. it has "
     "drifted from locate(); the inequality guard must void the gate",
     [(r'out\[name \+ "_stop"\] = stop',
       'out[name + "_stop"] = stop\n        out[name] = rise - 0.5')], 1, "AU1a"),

    ("au1-nonmonotone",
     "COMPUTED VERDICT: inject a dip between the peak and the upper bound so the walk's MAX "
     "descent exceeds its drop-to-bound.  The walks stay bound-terminated (that is structural), "
     "but the 'two-point read of the bounds' reduction must NO LONGER be claimed.",
     [(r"^import numpy as np$",
       "import numpy as np\n"
       "def _au_dip(d):\n"
       "    import feature_locus_gate as _W\n"
       "    return d - 12.0 * np.exp(-0.5 * ((np.log(_W.GRID / 600.0)) / 0.01) ** 2)\n")],
     0, "the prominence is a max-descent rather than a"),

    ("au2-one-signed",
     "COMPUTED VERDICT: force the prominence deficit one-signed — the gate must stop saying it "
     "changes sign",
     [(r"        d = pp - mp$", "        d = abs(pp - mp) + 1e-6")],
     0, "the deficit is one-signed in every set"),

    ("au3-no-sign-change",
     "COMPUTED VERDICT: make both mix sets request the same sign — the sign-change verdict, which "
     "is what refutes s151's stated reason, must flip to its opposite",
     [(r"            clean\.setdefault\(r\[.set.\], \[\]\)\.append\(x\[5\]\)",
       "            clean.setdefault(r['set'], []).append(abs(x[5]))")],
     0, "no sign change across the mix"),

    ("au4-separable",
     "COMPUTED VERDICT: make the peak term as separable as the notch — the DECISIVE verdict must "
     "become SEPARABLE.  ⚠ This arm is why AU4's verdict is a branch at all: the first draft "
     "printed 'mostly A3' unconditionally and this arm passed against it.",
     [(r'peak_keep = keep_frac\(F\.rbj_peak_db\(f, fs, T\["kPeakFreq"\], T\["kPeakQ"\], 1\.0\), B\)',
       'peak_keep = keep_frac(F.rbj_peak_db(f, fs, T["kNotchFreq"], 20.0, 1.0), B)')],
     0, "VERDICT: SEPARABLE"),

    ("au4a-estimator",
     "the separability estimator fails its own known answers; the gate must die rather than read "
     "a single candidate",
     [(r"    return float\(np\.linalg\.norm\(r - B @ co\) / n\)",
       "    return float(np.linalg.norm(r - B @ co) / n) + 0.01")],
     1, "AU4a"),
]


def build(patches):
    src = open(SRC).read()
    # Redirect the mutant's report so it cannot overwrite the real gate's artefact (s153).
    src, n = re.subn(r'"s157_peak_identifiability\.json"',
                     f'"_mutant_au_{os.getpid()}.json"', src)
    if n != 1:
        sys.exit("_mutate_gate_au: report-path redirect did not apply — refusing to run, because "
                 "a mutant would otherwise overwrite the real gate's report (s153)")
    for pat, rep in patches:
        src, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None, f"PATCH DID NOT APPLY: {pat}"
    # The non-monotone arm is a DATA-level mutation (s114: `if False:` disables a guard rather
    # than firing it), applied at the one place both curves enter the gate.
    if any("_au_dip" in r for _, r in patches):
        src = src.replace("                g, ped, mod = F.curves(fname, sweep)",
                          "                g, ped, mod = F.curves(fname, sweep)\n"
                          "                ped, mod = _au_dip(ped), _au_dip(mod)")
    return src, None


def main():
    print("GATE AU — mutation test\n" + "=" * 78)
    ok = True
    for name, why, patches, rc_want, needle in ARMS:
        src, err = build(patches)
        if err:
            print(f"  {name:<20} ⛔ {err}")
            ok = False
            continue
        open(MUT, "w").write(src)
        try:
            p = subprocess.run([sys.executable, MUT], cwd=ROOT, capture_output=True, text=True,
                               timeout=3600)
        finally:
            pass
        out = p.stdout + p.stderr
        rc_ok = (p.returncode != 0) == (rc_want != 0)
        needle_ok = needle in out
        if rc_ok and needle_ok:
            verdict = "✅ PASS"
        elif rc_ok and not needle_ok:
            # exit code right, message wrong: the guard fired but a verdict was NARRATED, or a
            # different guard fired first (s117's wrong-guard case).
            verdict = "⛔ NARRATED / WRONG GUARD"
            ok = False
        else:
            verdict = f"⛔ GUARD DEAD (rc={p.returncode}, wanted {'nonzero' if rc_want else '0'})"
            ok = False
        print(f"  {name:<20} {verdict}")
        print(f"  {'':<20}   {why}")
        if verdict != "✅ PASS":
            tail = [ln for ln in out.splitlines() if ln.strip()][-6:]
            for ln in tail:
                print(f"  {'':<20}   | {ln}")
    for f in (MUT, MUT_REPORT):
        if os.path.exists(f):
            os.remove(f)
    print("=" * 78)
    print("ALL ARMS PASS" if ok else "SOME ARMS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
