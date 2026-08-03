#!/usr/bin/env python3.11
"""Mutation test for GATE AB (analysis/bt_pair_shape_gate.py).

Discipline, each rule paid for by a named session:
  * DATA-level mutations only, never a predicate — `if False:` DISABLES a guard rather
    than firing it, and reads as GUARD DEAD against a good guard (s114).
  * The patched copy LIVES in analysis/ (so sibling imports resolve) and RUNS from the
    repo root (so data paths resolve) — two different requirements, and satisfying one
    is the natural way to break the other (s110).
  * An UNMUTATED CONTROL runs first.  If it does not pass, no failure below is
    attributable to a mutation (s107).
  * Guard IDENTITY is checked, not merely a non-zero exit — a crash also exits non-zero
    (s117).
  * s128's addition: arms with `expect_rc = 0` that demand the OPPOSITE VERDICT, so a
    conclusion which has quietly become hard-coded narration FAILS the test instead of
    surviving it.  A well-built gate's headline findings deliberately never change the
    exit code (s108), so without these arms a mutation runner can only test plumbing.

Usage:  python3.11 analysis/_mutate_gate_ab.py
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "bt_pair_shape_gate.py")
COPY = os.path.join(HERE, "_bt_pair_shape_gate_mutant.py")

ORIG = open(SRC).read()


def run(text):
    open(COPY, "w").write(text)
    try:
        p = subprocess.run([sys.executable, COPY], cwd=REPO,
                           capture_output=True, text=True, timeout=600)
        return p.returncode, p.stdout + p.stderr
    finally:
        os.remove(COPY)


# (name, mutation fn, expected rc, substring the output MUST contain, why)
ARMS = [
    ("AB1 known answer — break the cascade's peak",
     # Move the SK 3.3 kHz corner far off: the peak must leave s125's closed-form value.
     lambda t: t.replace('SK_A = dict(R1=22.0e3, R2=47.0e3, C1=2.2e-9, C2=1.0e-9)',
                         'SK_A = dict(R1=22.0e3, R2=47.0e3, C1=6.6e-9, C2=1.0e-9)'),
     1, "AB1", "a wrong cascade must not reproduce 2934.8 Hz"),

    ("AB1 known answer — break the cascade's notch",
     lambda t: t.replace('BT_C17 = _read_fitparam("btC17")',
                         'BT_C17 = _read_fitparam("btC17") * 4.0'),
     1, "AB1", "a wrong bridged-T must not land the notch in W6's window"),

    ("AB2 NULL — make a post-cascade gain move a feature",
     # A gain that is applied BEFORE the log is still a pure scalar; to break the null we
     # must make it frequency-dependent, which is what the null exists to forbid.
     lambda t: t.replace("    return gain * h", "    return (gain ** (1.0 + 0.3 * np.log10(f / 1000.0))) * h"),
     1, "AB2", "a frequency-dependent 'gain' must break the NULL control"),

    ("AB3 tau partition — drop a time constant from the partition",
     # C14 is a genuine tau in the cascade; removing it from TAU_CLASSES must break the
     # sum-to--1 known answer, because the partition is then incomplete.
     lambda t: t.replace('    ("clipper pole (C14)", lambda k: dict(c14=C14 * k),\n'
                         '     "the shunt-feedback stage\'s own pole, 6.30 kHz at the shipped a0"),\n', ''),
     1, "AB3-sum", "an incomplete tau partition cannot sum to -1"),

    ("FitParams desync — the constant reader must refuse, not guess",
     lambda t: t.replace('_read_fitparam("btC16")', '_read_fitparam("btC16_NOT_A_REAL_PARAM")'),
     1, "REFUSED", "a gate desynchronised from the shipped constants must refuse"),

    # ---- s128 opposite-verdict arms (expect_rc = 0) ------------------------
    ("AB5 sign verdict — make the pedal's two features move the SAME way",
     lambda t: t.replace('PEDAL = dict(notch_lo=695.7, notch_hi=745.4, peak_lo=2498.5, peak_hi=2696.4)',
                         'PEDAL = dict(notch_lo=695.7, notch_hi=745.4, peak_lo=2696.4, peak_hi=2498.5)'),
     0, "AB5-MEMBERSHIP refuted=['clipper a0 (supply sag route)',",
     "with a SAME-signed target the classification must INVERT: the bridged-T classes become "
     "admissible and the rolloff classes become refuted.  Asserted on MEMBERSHIP, not on a "
     "count -- the two groups have 5 members each, so every printed count is unchanged by the "
     "swap and a count-based assertion passed this arm vacuously."),

    ("AB4 ratio premise — make the peak a pure bridged-T feature",
     # Push both SK corners and the clipper pole far above the band so the peak is set by
     # the bridged-T alone.  Then AA6's 'ratio is invariant' premise becomes TRUE and the
     # measured departure must collapse toward zero.
     lambda t: t.replace('    h = h * sallen_key(f, scale=sk_scale, **SK_B)\n'
                         '    h = h * sallen_key(f, scale=sk_scale, **SK_A)\n'
                         '    h = h * clipper_closed_loop(f, a0, c14=c14)\n',
                         '    h = h * sallen_key(f, scale=sk_scale * 0.02, **SK_B)\n'
                         '    h = h * sallen_key(f, scale=sk_scale * 0.02, **SK_A)\n'
                         '    h = h * clipper_closed_loop(f, a0, c14=c14 * 0.02)\n'),
     1, "AB1",
     "with the rolloffs removed the peak moves out of the window, so AB1 refuses first — "
     "defence in depth (s119); the arm is kept because the refusal is the correct outcome"),
]


def main():
    print("=" * 92)
    print("MUTATION TEST — GATE AB")
    print("=" * 92)

    rc, out = run(ORIG)
    ctrl_ok = rc == 0 and "all guards passed" in out
    print(f"\nCONTROL (unmutated): rc={rc}  {'PASS' if ctrl_ok else 'FAIL'}")
    if not ctrl_ok:
        print("  ⛔ the control did not pass — no failure below is attributable to a mutation.")
        print(out[-2000:])
        sys.exit(1)

    npass = 0
    for name, fn, exp_rc, need, why in ARMS:
        text = fn(ORIG)
        if text == ORIG:
            print(f"\n  {name}\n    ⛔ VACUOUS — the mutation changed nothing (s110).")
            continue
        rc, out = run(text)
        got = (rc == exp_rc) and (need in out)
        if rc != exp_rc:
            verdict = f"WRONG RC (got {rc}, want {exp_rc})"
        elif need not in out:
            verdict = f"NARRATED — rc is right but {need!r} never printed"
        else:
            verdict = "PASS"
            npass += 1
        print(f"\n  {name}")
        print(f"    expect rc={exp_rc}, output must contain {need!r}")
        print(f"    why: {why}")
        print(f"    => {verdict}")

    print("\n" + "=" * 92)
    print(f"MUTATION TEST: {npass}/{len(ARMS)}")
    print("=" * 92)
    sys.exit(0 if npass == len(ARMS) else 1)


if __name__ == "__main__":
    main()
