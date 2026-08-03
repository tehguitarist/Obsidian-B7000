#!/usr/bin/env python3
"""Mutation-test GATE V's guards.

Each mutation must make the gate exit non-zero.  An UNMUTATED CONTROL runs first: if the control
does not PASS, no failure below is attributable to a mutation (s107 -- five "passes" that were all
ModuleNotFoundError).  The patched copy LIVES in analysis/ so its sibling imports resolve, and RUNS
from the repo root so its repo-relative data paths resolve -- getting only one of those right is
s110's trap.  Every needle is asserted present EXACTLY ONCE, so a vacuous mutation reports as
vacuous rather than as a dead guard (s110/s113).

⚠ Mutate a guard's PREMISE or its DATA, never write `if False:` over its predicate -- that DISABLES
a guard rather than making it fire, and reports a healthy guard as dead (s114's two backwards
mutations).  ⚠ And every constant patched here is patched at MODULE level, because GATE V measures
in a ProcessPoolExecutor whose children re-import the module and would never see a runtime-mutated
global (s110's vacuous mutation).
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "null_drive_plane_gate.py")

MUTATIONS = [
    # V1a -- the reproduction must be against the report GATE R's stored table was built on.
    ("V1a report/membership match",
     "    report = a.report or r_report",
     '    report = "analysis/reports/s113_baseline.json"'),
    # V1a -- corrupt the statistic itself: the reproduction of GATE R's r6 table must break.
    ("V1a reproduces GATE R",
     '    return {"f0": f0, "prom": prom, "prom_point": prom_pt, "edge": bool(edge),',
     '    return {"f0": f0, "prom": prom + 0.01, "prom_point": prom_pt, "edge": bool(edge),'),
    # V1a -- make its own mutation control a no-op.  The gate must report that V1a has gone vacuous
    # rather than reporting a PASS on a check that can no longer fail.
    ("V1a non-vacuity control",
     "            val = val + shoulders            # a deliberate, uniform corruption",
     "            val = val + 0.0                  # a deliberate, uniform corruption"),
    # V0 -- the asserted endpoint count, which is GATE R's and must not be inferred.
    ("V0 endpoint-count assertion",
     'BASELINE = "analysis/reports/s114_baseline.json"',
     'BASELINE = "analysis/reports/s114_baseline.json"\nR.EXPECT_ENDPOINTS = 99'),
    # V0 -- collapse the DRIVE axis.  The whole plane is the DRIVE conditioning, so a set spanning
    # one DRIVE must be refused, not silently pooled (s108's P4 as a hard guard).
    ("V0 DRIVE-spread assertion",
     '    rec = {"file": fname, "drive": parsed.get("drive"), "pedal": {}}',
     '    rec = {"file": fname, "drive": 1.0, "pedal": {}}'),
    # V0 -- the reference-dropout detector matching nothing (`empty-gate-must-fail` in a costume).
    ("V0 dropout-detector non-empty",
     '           "dropouts": sorted(f"{f}@{s}" for f, s in drops),',
     '           "dropouts": [],'),
    # V0 -- the MASTER-only duplicate.  If none is found, the condition de-duplication that R7
    # exists to enforce is never exercised and would pass vacuously.
    ("V0 dedup-exercised assertion",
     '           "dupes": {" == ".join(sorted(v)): len(v) for v in conds.values() if len(v) > 1}}',
     '           "dupes": {}}'),
    # V0 -- GATE R's capture-epoch guard (R3b), running backwards: the source moving under the
    # derived artefact.
    ("V0 capture-epoch guard",
     "    rep_mt = os.path.getmtime(report)",
     "    rep_mt = 0.0"),
    # V1 -- the vacuity guard on the whole V1a/V1b pair.  With GATE R's cache gone, V1a has nothing
    # to reproduce against and V1b would compare the fresh renders with themselves.
    ("V1 cached-render vacuity",
     'EP_FRESH = "build/s117_null_plane"',
     'EP_FRESH = "build/s117_null_plane"\nR.EP_DIR = "build/_absent_s117"'),
    # V4 -- a notch minimum resting on a window EDGE is a bound, not a measurement.
    ("V4 window-edge guard",
     '"edge": bool(edge),',
     '"edge": True,'),
]


def run(path):
    """-> (rc, [the gate's own '!' failure lines]).

    ⚠ Returning the LAST line of output is not enough: the tail here is a scipy WavFileWarning, so
    a mutation that fired the WRONG guard -- or crashed -- would read as a success on rc alone.
    The failure lines are what let the caller check guard IDENTITY (s109: a mutation must land on
    the code path the guard actually reads)."""
    r = subprocess.run([sys.executable, path,
                        "--json", os.path.join(tempfile.gettempdir(), "mv.json")],
                       cwd=ROOT, capture_output=True, text=True)
    lines = (r.stdout + r.stderr).splitlines()
    hits = [l.strip()[2:] for l in lines if l.strip().startswith("! ")]
    if r.returncode and not hits:                       # crashed rather than refused
        tail = [l for l in lines if l.strip()][-1:]
        hits = ["CRASH (no computed failure): " + (tail[0][:90] if tail else "")]
    return r.returncode, hits


def main():
    src = open(SRC).read()
    tmp = os.path.join(HERE, "_gate_v_mutant.py")

    print("=" * 100)
    open(tmp, "w").write(src)
    rc, hits = run(tmp)
    print(f"CONTROL (unmutated): rc={rc}  "
          f"{'PASS' if rc == 0 else '** BROKEN -- results below mean nothing'}")
    for h in hits:
        print(f"   ! {h}")
    if rc != 0:
        os.remove(tmp)
        return 1

    print("=" * 100)
    bad = 0
    for name, needle, repl in MUTATIONS:
        n = src.count(needle)
        if n != 1:
            print(f"{name:34s} ** VACUOUS -- needle appears {n} times (expected exactly 1)")
            bad += 1
            continue
        open(tmp, "w").write(src.replace(needle, repl))
        rc, hits = run(tmp)
        tag = name.split()[0]                       # the guard this mutation is aimed at
        right = any(h.startswith(tag + ":") for h in hits)
        ok = rc != 0 and right
        note = ("FIRES" if ok else
                "** GUARD DEAD" if rc == 0 else
                f"** WRONG GUARD -- expected {tag}, got {[h.split(':')[0] for h in hits]}")
        print(f"{name:34s} rc={rc}  {note}")
        for h in hits:
            print(f"   ! {h[:104]}")
        if not ok:
            bad += 1

    os.remove(tmp)
    print("=" * 100)
    print(f"{len(MUTATIONS) - bad}/{len(MUTATIONS)} mutations fire; control passes."
          if not bad else f"** {bad} PROBLEM(S) -- see above")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
