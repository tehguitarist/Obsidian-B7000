#!/usr/bin/env python3.11
"""a3_clipper_joint_scan -- Phase 9 / A3 (session 39): scan the clipper VTC
ceilings JOINTLY with kInputRef against the LEVEL-AXIS gate.

WHY JOINT, AND WHY THESE TWO
----------------------------
Session 37 item (4) established that the clipper VTC is a real lever on the
level axis -- the first parameter family that is -- but that a ONE-PARAMETER
scan of the ceiling pair cannot be accepted:

    "two subsets are monotone in OPPOSITE directions (the CONTROL keeps
     improving down to 0.55x = the degeneracy signature; hot 101-254 at
     -12->-6 improves the other way), so it trades regions rather than
     fixing one defect."

That is the session-5/6 "make the clipper see less" degeneracy wearing a new
hat: shrinking the ceilings makes the clipper engage later, which flatters any
subset whose defect is "too much compression" while starving the ones whose
defect is "not enough". A scan along that one axis has no interior optimum to
find, so it will always terminate on whichever subset you happened to rank.

kInputRef is the degenerate PARTNER (GainStaging.h / session 16 §3v.5,
session 17): for the clipper ALONE, scaling kInputRef by a and the ceilings by
a is exactly a no-op. That is precisely why it opens the search rather than
closing it -- the invariance is only exact for the clipper, because:

  * the JFET stage upstream has its OWN fixed thresholds (jfetSat*/jfetCeil*),
    so a kInputRef change moves how hard the J201 is driven while leaving the
    clipper's operating point alone if the ceilings follow;
  * the op-amp RailClamps have fixed volts and do not scale either.

So the 2-D family {satScale, krScale} really spans "how hard is the JFET
driven" x "how hard is the clipper driven", and the anti-diagonal
satScale == krScale is the near-invariant direction that isolates the JFET.
A 1-D ceiling scan is the projection of this onto one axis, which is why it
could only ever trade regions.

  ⚠ The near-invariance is the thing to WATCH, not just to exploit. Along
  satScale == krScale the gate should move only a little (it is the JFET's
  contribution alone). If a scan reports a large win exactly along that
  direction, suspect the override plumbing before believing it -- see the
  liveness guard below.

WHAT IT RANKS ON
----------------
Session 37 item (9)'s standing limit applies: below 80 Hz at high drive neither
dT nor the null argmin is a reliable ranker alone (both are cliff-dominated
there). So `lf_hot` is REPORTED but never ranked on.

⚠⚠ AND `mf_hot` AS ORIGINALLY DEFINED (101-254 Hz, drives 2:30+max, shipped
0.94 dB) MUST NOT BE RANKED ON EITHER -- session 40 audited its membership
before fitting to it, and **82 % of its mean-square is the single 254 Hz band**
(1.90 dB rms there against 0.35-0.54 dB at 101-202).

Two candidate explanations were tested and BOTH were settled by measurement, not
by argument:

  * NOT a cliff. Session 37's reason for demoting `lf_hot` does not apply here:
    at 254 Hz the amplification S = d(total)/d(OD gain) is 0.27, the LOWEST of
    the whole band set (101 Hz is 0.47), with m ~ 0.43 and theta ~ 45-53 deg --
    nowhere near the anti-phase cancellation. The residual is real signal, not
    an amplified measurement error, and the pedal's own 254 Hz totals are smooth
    across drive.
  * NOT A COMPRESSION DEFECT -- this is the decisive one. A clipper-side
    compression error must vanish at drive min/9:30, where the clipper barely
    engages; that is the entire basis for using `ctrl` as the control. The
    254 Hz residual at -12->-6 is +1.60 dB at drive MIN and +1.41 at 9:30,
    against +1.21 at 2:30 and +2.40 at max. It is level-dependent but very
    nearly DRIVE-INDEPENDENT, so no clipper VTC parameter can be responsible
    for it. (DRIVE sits downstream of the J201, so a drive-independent
    nonlinearity points upstream of DriveStage, not at the clipper.)

Ranking on `mf_hot` would therefore have let one band that the clipper provably
cannot fix cast 82 % of the vote -- exactly `defective-rows-must-not-vote`, the
trap session 36/37 already paid for once with `clipC15`. So the target is:

    mf_ex254 @ -12->-6  (drives 2:30+max, 101-202 Hz)  shipped: 0.44 dB

reported against a BAND-MATCHED control (`ctrl_ex` = the same 101-202 Hz bands
at drives min+9:30, shipped 0.29 dB) rather than the whole-band `ctrl`, so the
comparison is like for like. `b254` is printed alongside as the CONTAMINANT
column: any candidate whose `mf_hot` improves while `mf_ex254` does not is
moving 254 Hz, i.e. compensating for an error of a different kind.

  ⚠ Note the shipped margin: mf_ex254 0.44 dB against a 0.29 dB matched control
  is 0.15 dB, which is INSIDE this project's 0.144 dB take-to-take capture
  repeatability floor. Treat "no candidate beats the baseline" as the expected
  outcome, and a large apparent win as a reason to check what moved.

`ctrl` remains the DEGENERACY DETECTOR, not a score to maximise: a candidate
whose CONTROL improves monotonically as the ceilings shrink is re-finding the
session-5/6 corner, however good its headline looks.

LIVENESS GUARD (session 36 item 8)
----------------------------------
Eight candidates once came back bit-identical after being liveness-checked as
live, because `set -- $spec` in a zsh loop does not word-split, so no
key=value ever reached the tool and each candidate silently re-rendered the
shipped defaults under its own name. This scan therefore (a) builds argv as a
real list, never a string, and (b) asserts that every non-identity candidate's
CSVs actually DIFFER from the shipped baseline, aborting if not. A bit-identical
A/B must be a measurement, never an accident.

Usage:
    python3.11 analysis/a3_clipper_joint_scan.py [--jobs 8] [--quick]
"""
import argparse
import concurrent.futures as cf
import contextlib
import io
import itertools
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_level_axis as la                                          # noqa: E402
import a3_phase_solve as ps                                         # noqa: E402

BIN = "build/a3_blend_decompose"

# Shipped defaults (FitParams.h / GainStaging.h) -- read, not transcribed, below.
SHIP_SAT_LO = 2.0067
SHIP_SAT_HI = 2.9321
SHIP_KINPUTREF = 3.377

LEVELS = la.LEVELS
DRIVES = [d for d, _ in ps.DRIVES]


def read_shipped():
    """Read the shipped constants from the SOURCE, so the scan cannot drift from
    what the plugin actually runs (session 35: verify the CONSTANT, not the prose)."""
    vals = {}
    src = open("src/dsp/FitParams.h").read()
    for key in ("clipSatLo", "clipSatHi"):
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("double %s" % key):
                vals[key] = float(s.split("=")[1].split(";")[0])
                break
    src = open("src/dsp/GainStaging.h").read()
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("static constexpr double kInputRefNominal"):
            vals["kInputRef"] = float(s.split("=")[1].split(";")[0])
            break
    missing = {"clipSatLo", "clipSatHi", "kInputRef"} - set(vals)
    if missing:
        sys.exit("could not read shipped constants: %s" % sorted(missing))
    return vals


def render_one(args):
    outdir, level, drive, overrides = args
    path = os.path.join(outdir, "a3_lvl%d_drv%s.csv" % (level, drive))
    argv = [BIN, "1", str(drive), str(level)] + list(overrides)
    with open(path, "w") as fh:
        subprocess.run(argv, check=True, stdout=fh)
    return path


def render_candidate(outdir, overrides, jobs):
    os.makedirs(outdir, exist_ok=True)
    tasks = [(outdir, L, d, overrides) for L in LEVELS for d in DRIVES]
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(render_one, tasks))
    return os.path.join(outdir, "a3_lvl")


def body(path):
    return [l for l in open(path).read().splitlines() if not l.startswith("#")]


def differs_from_baseline(outdir):
    for L in LEVELS:
        for d in DRIVES:
            f = "a3_lvl%d_drv%s.csv" % (L, d)
            if body(os.path.join(outdir, f)) != body(os.path.join("build", f)):
                return True
    return False


MF_EX = [101, 127, 160, 202]      # mf_hot with the 254 Hz contaminant removed
B254 = [254]


def subset_rms(tabs, step, blist, drives):
    """dT residual rms (model - pedal) over an explicit band x drive subset."""
    rows = tabs[step]
    v = [rows[b][k]["dT_mdl"] - rows[b][k]["dT_ped"]
         for b in blist if b not in la.EXCLUDE for k in drives]
    a = np.array(v, dtype=float)
    return float(np.sqrt(np.mean(a * a)))


def metrics(prefix, pedal, bands):
    model = la.load_model_levels(prefix)
    with contextlib.redirect_stdout(io.StringIO()):        # gate() prints a table
        g = la.gate(model, pedal, bands, "")
    r = g["res"]

    # The corrected subsets (see WHAT IT RANKS ON): the 254 Hz band is excluded
    # from the target because its residual is present at full size at the
    # CONTROL drives, so it is not clipper-reachable. It is reported separately
    # rather than silently dropped -- a silent cap reads as "covered everything".
    tabs = la.build_tables(model, pedal, bands)
    step = (-6, -12)
    return dict(match=g["match"],
                ctrl12=r[(-12, "ctrl")], ctrl6=r[(-6, "ctrl")],
                noon12=r[(-12, "noon")], noon6=r[(-6, "noon")],
                lf12=r[(-12, "lf_hot")], lf6=r[(-6, "lf_hot")],
                mf12=r[(-12, "mf_hot")], mf6=r[(-6, "mf_hot")],
                all12=r[(-12, "all")], all6=r[(-6, "all")],
                mf_ex=subset_rms(tabs, step, MF_EX, [3, 4]),          # THE TARGET
                ctrl_ex=subset_rms(tabs, step, MF_EX, [0, 1]),        # matched control
                b254=subset_rms(tabs, step, B254, [3, 4]),            # contaminant
                b254c=subset_rms(tabs, step, B254, [0, 1]))           # its own control


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--quick", action="store_true", help="coarse 3x3 grid")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    ship = read_shipped()
    print("shipped constants read from source: clipSatLo=%.4f clipSatHi=%.4f kInputRef=%.4f"
          % (ship["clipSatLo"], ship["clipSatHi"], ship["kInputRef"]))
    print("(sum = %.3f V against the ~7 V R19-dropped rail -- physicality is judged on the"
          % (ship["clipSatLo"] + ship["clipSatHi"]))
    print(" FAMILY, both implied input volts AND clipSat volts, never clipSat with K pinned)\n")

    if args.quick:
        sat_scales = [0.8, 1.0, 1.2]
        kr_scales = [0.85, 1.0, 1.15]
    else:
        sat_scales = [0.70, 0.85, 1.00, 1.15, 1.30]
        kr_scales = [0.70, 0.85, 1.00, 1.15, 1.30]

    pedal = la.load_pedal_levels()
    bands = list(ps.PROBE_BANDS)

    base = metrics("build/a3_lvl", pedal, bands)
    print("BASELINE (shipped), level step -12 -> -6 dBFS:")
    print("  TARGET   mf_ex254 (101-202, hot)  %.2f dB   vs matched control %.2f dB"
          " -> margin %.2f dB" % (base["mf_ex"], base["ctrl_ex"],
                                  base["mf_ex"] - base["ctrl_ex"]))
    print("  EXCLUDED b254     (254, hot)      %.2f dB   its own control    %.2f dB"
          "  <- not clipper-reachable" % (base["b254"], base["b254c"]))
    print("  context: mf_hot %.2f/%.2f  ctrl %.2f/%.2f  noon %.2f/%.2f  lf_hot %.2f/%.2f"
          "  all %.2f/%.2f  null %d/15\n"
          % (base["mf12"], base["mf6"], base["ctrl12"], base["ctrl6"],
             base["noon12"], base["noon6"], base["lf12"], base["lf6"],
             base["all12"], base["all6"], base["match"]))

    tmp = tempfile.mkdtemp(prefix="a3_joint_")
    rows = []
    hdr = ("%6s %6s | %7s %7s | %7s | %11s | %11s | %11s | %4s"
           % ("satSc", "krSc", "mf_ex", "ctrl_ex", "b254", "mf_hot(x)", "lf_hot(*)",
              "all", "null"))
    print(hdr)
    print("%6s %6s | %7s %7s | %7s | %11s | %11s | %11s | %4s"
          % ("", "", "TARGET", "matched", "excl", "contaminated", "cliff", "", ""))
    print("-" * len(hdr))

    try:
        for ss, ks in itertools.product(sat_scales, kr_scales):
            ov = ["clipSatLo=%.6f" % (ship["clipSatLo"] * ss),
                  "clipSatHi=%.6f" % (ship["clipSatHi"] * ss),
                  "kInputRef=%.6f" % (ship["kInputRef"] * ks)]
            outdir = os.path.join(tmp, "s%.2f_k%.2f" % (ss, ks))
            prefix = render_candidate(outdir, ov, args.jobs)

            identity = (abs(ss - 1.0) < 1e-9 and abs(ks - 1.0) < 1e-9)
            live = differs_from_baseline(outdir)
            if identity and live:
                sys.exit("GUARD FAILED: the identity candidate (1.00, 1.00) is NOT "
                         "bit-identical to the shipped baseline -- the baseline CSVs "
                         "in build/ are stale, or an override leaked in.")
            if not identity and not live:
                sys.exit("GUARD FAILED: candidate satScale=%.2f krScale=%.2f rendered "
                         "bit-identical to the shipped baseline. The overrides are not "
                         "reaching the binary (session 36 item 8). Args were: %s"
                         % (ss, ks, ov))

            m = metrics(prefix, pedal, bands)
            rows.append((ss, ks, m))
            mark = " <-- shipped" if identity else ""
            print("%6.2f %6.2f | %7.2f %7.2f | %7.2f | %5.2f %5.2f | %5.2f %5.2f | "
                  "%5.2f %5.2f | %2d/15%s"
                  % (ss, ks, m["mf_ex"], m["ctrl_ex"], m["b254"],
                     m["mf12"], m["mf6"], m["lf12"], m["lf6"],
                     m["all12"], m["all6"], m["match"], mark))
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print("\n(candidate renders kept in %s)" % tmp)

    print("""
READING THIS
------------
  * (x) mf_hot is REPORTED, NEVER RANKED ON -- 82 % of it is the 254 Hz band,
    whose residual is present at FULL SIZE at the control drives (+1.60 dB at
    drive min) and so cannot be a clipper-compression error. Rank on mf_ex254.
    If a candidate improves mf_hot while mf_ex254 is flat, it moved 254 Hz.
  * (*) lf_hot is REPORTED, NEVER RANKED ON -- session 37 item (9): below 80 Hz
    at high drive both dT and the null argmin are cliff-dominated and move
    non-monotonically in an order that does not track the null match.
  * The DEGENERACY SIGNATURE is `ctrl` improving monotonically as satSc falls.
    ctrl is the CONTROL (drives min+9:30, both devices near-linear) -- it should
    be near the method's noise floor and roughly FLAT. A candidate that "wins" by
    driving ctrl down as the ceilings shrink is re-finding the session-5/6
    "make the clipper see less" corner, not fixing the defect.
  * A credible fix improves mf_hot at -12->-6 WITHOUT trading ctrl or the null,
    and sits at an INTERIOR minimum (worse on BOTH sides) in at least one axis.
  * Any accepted candidate must still clear the OTHER two A3 gates before it
    ships: a3_lead_fit (raw-capture fit, k pinned) and grunt_span_probe's
    bump-peak LOCATION (session 38's crossover sub-gate).
""")


if __name__ == "__main__":
    main()
