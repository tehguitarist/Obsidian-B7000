#!/usr/bin/env python3.11
"""Mutation runner for GATE AD (`analysis/hw_trend_gate.py`).  Session 130.

Every mutation is at the DATA level -- it patches a COPY of the report JSON and runs the UNMODIFIED
gate against it via `--report`.  Nothing patches the gate's own source, so s114's "mutate the data,
not the predicate" holds by construction and the `if False:` failure mode is unavailable.  It also
sidesteps s110's patched-copy trap entirely (the gate always runs from its real path, so sibling
imports and repo-relative data paths both resolve).

Two arm kinds, per s128:
  * `rc=1` arms break a PREMISE and require the named guard to REFUSE.  Scored on exit code AND on
    the guard's own `[TAG]`, so "fired for the right reason" is checked, not just "exited" (s117).
  * `rc=0` arms break the DATA BEHIND A VERDICT and require the gate to print the OPPOSITE verdict.
    s108's rule means a well-built gate's headline findings deliberately never touch the exit code,
    so WITHOUT these arms a runner can only test plumbing and every conclusion could have quietly
    become hard-coded narration.  Each such arm names a string that must APPEAR and one that must
    DISAPPEAR -- the second is the half that actually catches narration.

An unmutated CONTROL runs first.  If the control does not pass, no failure below is attributable to
a mutation (s107).

Run:  /opt/homebrew/bin/python3.11 analysis/_mutate_gate_ad.py
"""
import json
import math
import os
import subprocess
import sys

PY = "/opt/homebrew/bin/python3.11"
GATE = "analysis/hw_trend_gate.py"
SRC = "analysis/reports/s124_ship.json"
# Named so GATE AD's own baseline-epoch guard parses "124" from the leading token and admits it --
# that guard is not what these arms are testing, and tripping it would mask every one of them.
TMP = "analysis/reports/s124_mutscratch_ad.json"

LOWMID = (160.0, 201.6, 254.0)
DRIVEN = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")


def flat_eq(s):
    return all(abs(s.get(k, 0.5) - 0.5) < 1e-9 for k in ("lo", "loMid", "hiMid", "hi"))


def bleed_free(s):
    return s.get("blend") == 1.0 and s.get("level") == 1.0


def od_rows(d):
    for c in d["captures"]:
        s = c.get("settings", {})
        if bleed_free(s) and s.get("distEngage") is True and flat_eq(s):
            yield c, s


def clean_rows(d):
    for c in d["captures"]:
        s = c.get("settings", {})
        if (s.get("distEngage") is False or s.get("blend") == 0.0) and flat_eq(s):
            yield c, s


# ---------------------------------------------------------------------------------------------
# Mutations -- each mutates the loaded report dict IN PLACE.
# ---------------------------------------------------------------------------------------------
def m_empty_clean_route(d):
    """Delete the DIST-disengaged clean route -> AD2's empty-group guard."""
    d["captures"] = [c for c in d["captures"]
                     if not (c.get("settings", {}).get("distEngage") is False
                             and flat_eq(c.get("settings", {})))]


def m_move_a_band(d):
    """Shift the 320 Hz band off-grid -> AD2's required-band guard.

    NOT a threshold mutation (s110's vacuity trap): it makes a band the gate anchors on genuinely
    absent, which is exactly what happens when a report's band list is re-derived.
    """
    b = d["meta"]["bands"]
    b[b.index(320.0)] = 321.0


def m_partial_sweeps(d):
    """Give ONE bleed-free OD capture 2 of 3 driven sweeps -> AD2's PARTIAL branch (s129).

    The arm's point is that this must REFUSE rather than silently exclude: a capture that LOST a
    rung is a malformed report, a different outcome from one that never had it.
    """
    for c, s in od_rows(d):
        if s.get("gruntIdx") == 1 and c["fr"].get("sweep_drv_-12"):
            c["fr"].pop("sweep_drv_-12")
            return
    raise RuntimeError("vacuous mutation: found no capture to make partial")


def m_break_route_agreement(d):
    """Tilt ONE clean route by 3 dB/decade -> AD1's route-invariance known answer.

    3 dB/decade is far above GATE O's 0.30 dB route bar, so the arm binds hard; a sub-bar tilt
    would be a vacuous mutation and would read as GUARD DEAD against a good guard.
    """
    bands = d["meta"]["bands"]
    for c, s in clean_rows(d):
        if s.get("blend") == 0.0:
            fr = c["fr"].get("sweep_clean")
            if fr:
                fr["plugin_db"] = [v + 3.0 * math.log10(f / 200.0)
                                   for v, f in zip(fr["plugin_db"], bands)]


def m_flip_tilt_sign(d):
    """Mirror the clean tilt about its 200 Hz reference -> AD3 must flip its verdict.

    rc=0 arm.  The shipped baseline leans HARDWARE on 5 of 7 graded bands; mirrored, those bands
    must lean ND instead.  If AD3's verdict were narration, this passes unchanged.
    """
    bands = d["meta"]["bands"]
    ref = bands.index(201.6)
    for c, _ in clean_rows(d):
        fr = c["fr"].get("sweep_clean")
        if not fr:
            continue
        g = fr["gain_db_applied"]
        nd = fr["pedal_db"]
        delta = [p - g - r for p, r in zip(fr["plugin_db"], nd)]
        mirrored = [2.0 * delta[ref] - x for x in delta]
        fr["plugin_db"] = [r + x + g for r, x in zip(nd, mirrored)]


def m_grunt_contrast_sign(d):
    """Invert the model's GRUNT span -> AD4(b) must report OPPOSITE SIGN TO HARDWARE.

    rc=0 arm.  Touches only the 160-254 Hz bands of the bleed-free boost/flat rows, i.e. exactly
    the statistic AD4(b) computes -- a broader mutation would also move AD3 and AD5 and the arm
    would stop being attributable.
    """
    bands = d["meta"]["bands"]
    lm = [bands.index(f) for f in LOWMID]
    for c, s in od_rows(d):
        if s.get("gruntIdx") in (0, 2):
            for sw in DRIVEN:
                fr = c["fr"].get(sw)
                if fr:
                    for i in lm:
                        fr["plugin_db"][i] -= 6.0


def m_unfreeze_hf_null(d):
    """Make the MODEL's 4.5-6 kHz null drive-dependent -> AD5b must stop saying FROZEN 3 of 3.

    rc=0 arm, and the sharpest one here: "our HF null is frozen while ND's swings monotonically"
    is this session's headline finding, so it is the conclusion most worth proving is computed
    rather than asserted.
    """
    j = d["meta"]["bands"].index(6450.8)
    step = {"sweep_drv_-18": 0.0, "sweep_drv_-12": -3.0, "sweep_drv_-6": -7.0}
    for c, _ in od_rows(d):
        for sw, dv in step.items():
            fr = c["fr"].get(sw)
            if fr:
                fr["plugin_db"][j] += dv


ARMS = [
    # (name, mutation, expected rc, guard tag, must-appear, must-disappear)
    ("CONTROL (unmutated)", None, 0, None, "DIRECTION OF TRAVEL", None),
    ("empty clean route", m_empty_clean_route, 1, "AD2", "is EMPTY", None),
    ("320 Hz band off-grid", m_move_a_band, 1, "AD2", "not on this report's grid", None),
    ("partial driven sweeps", m_partial_sweeps, 1, "AD2", "SOME but not", None),
    ("route shapes disagree", m_break_route_agreement, 1, "AD1", "disagree on SHAPE", None),
    ("tilt mirrored", m_flip_tilt_sign, 0, None,
     "WRONG SIDE OF ND", "5 of 7 graded bands lean HARDWARE"),
    ("GRUNT span inverted", m_grunt_contrast_sign, 0, None,
     "OPPOSITE SIGN TO HARDWARE", "6 of 6 cells share hardware's sign"),
    ("HF null unfrozen", m_unfreeze_hf_null, 0, None,
     "FROZEN (span < 0.1 dB) in 0 of 3", "FROZEN (span < 0.1 dB) in 3 of 3"),
]


def run(mut, exp_rc, tag, need, forbid):
    with open(SRC) as fh:
        d = json.load(fh)
    if mut is not None:
        mut(d)
    with open(TMP, "w") as fh:
        json.dump(d, fh)
    try:
        p = subprocess.run([PY, GATE, "--report", TMP], capture_output=True, text=True)
    finally:
        if os.path.exists(TMP):
            os.remove(TMP)
    out = p.stdout + p.stderr

    if p.returncode != exp_rc:
        return "GUARD DEAD", f"rc={p.returncode}, expected {exp_rc}"
    if tag and f"[{tag}]" not in out:
        fired = [ln.strip() for ln in out.splitlines() if "REFUSED" in ln]
        return "WRONG GUARD", (fired[0] if fired else "no guard tag in output")
    if need and need not in out:
        return "NARRATED", f"missing required line: {need!r}"
    if forbid and forbid in out:
        return "NARRATED", f"verdict did not move: still printed {forbid!r}"
    return "PASS", ""


def main():
    if not os.path.exists(SRC):
        sys.exit(f"no baseline report at {SRC}")
    print()
    print("=" * 92)
    print("MUTATION TEST -- GATE AD.  All mutations are DATA-level (a patched copy of the report).")
    print("=" * 92)
    w = max(len(a[0]) for a in ARMS)
    bad = 0
    for i, (name, mut, exp_rc, tag, need, forbid) in enumerate(ARMS):
        status, detail = run(mut, exp_rc, tag, need, forbid)
        kind = "control" if mut is None else (f"refuse[{tag}]" if exp_rc else "verdict")
        print(f"  {name:<{w}}  {kind:>12}  {status:<11} {detail}")
        if status != "PASS":
            bad += 1
        if i == 0 and status != "PASS":
            print("\n  ⛔ THE CONTROL FAILED -- no result below is attributable to a mutation.")
            sys.exit(1)
    print()
    print(f"  {len(ARMS) - bad} of {len(ARMS)} arms PASS.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
