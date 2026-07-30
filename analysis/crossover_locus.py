#!/usr/bin/env python3.11
"""A3 crossover sub-gate: the fast inner loop, and the GRUNT-side element LOCUS.

The acceptance tool for the crossover sub-gate is `grunt_span_probe.py::crossover_gate()`,
which reads a full `comprehensive_report.py` run (63 captures, ~6 min each). That is far
too slow to trace a locus, and it is not necessary: the sub-gate is DEFINED at drive-min
on `sweep_clean` (-30 dBFS), where the OD path is essentially linear, so the exact BLEND
decomposition (`a3_blend_decompose`) reproduces the same three transfers directly from
the model, one tone per band, in ~2 s per GRUNT position.

    span(pos) = 20log10|OD(pos) + bleed|  -  20log10|OD(cut) + bleed|

⚠ THE SELF-CHECK IS THE POINT. `--selfcheck` compares this probe's peak against the
report's own model row before any locus is trusted. If they disagree, the locus is
measuring something else and must not be read.

⚠ SCOPE (session 38 item 5, `grunt_span_probe.py` docstring): this metric is sensitive
to the OD/bleed ratio, so it rewards ANY element that attenuates the OD path. It may
only be used to select GRUNT-SIDE elements -- clipC11 / clipC12 / clipC13 / R16 -- where
the position-to-position difference really is the differential. Never a shared one.

Usage:
    python3.11 analysis/crossover_locus.py --selfcheck
    python3.11 analysis/crossover_locus.py --scan clipC12=47e-9,24e-9,12e-9,6e-9
    python3.11 analysis/crossover_locus.py --crossover        # |OD| vs |bleed| per position
"""
import math
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from grunt_span_probe import peak, SPAN_LO, SPAN_HI, GATE_TARGETS  # noqa: E402
from parallel import pmap  # noqa: E402

BIN = "build/a3_blend_decompose"
DRIVE_MIN = 0.0
DBFS = -30.0                       # sweep_clean's level (gen_test_signal CLEAN_FR_LEVELS_DB[0])
GRUNT = {"boost": 0, "cut": 1, "flat": 2}

# The report's own model row for the drive-min triple on sweep_clean, i.e. what this
# probe must reproduce. Regenerate with:
#   python3.11 analysis/grunt_span_probe.py analysis/reports/comprehensive_data.json
REPORT_MODEL = {"flat": (103.5, 10.60), "boost": (73.4, 15.85)}


def run(gruntIdx, fits):
    """-> {band_hz: (od_complex, bleed_complex)} from the exact BLEND decomposition."""
    cmd = [BIN, str(gruntIdx), str(DRIVE_MIN), str(DBFS)] + [f"{k}={v}" for k, v in fits]
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = {}
    for line in p.stdout.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        c = line.split(",")
        f = float(c[0])
        od = complex(float(c[5]), float(c[6]))
        cl = complex(float(c[7]), float(c[8]))
        out[f] = (od, cl)
    if not out:
        raise RuntimeError(f"no data from {' '.join(cmd)}")
    return out


def span(pos, fits):
    """span(pos) - span(cut) per band, at the BLEND output. Returns (bands, span_db)."""
    a = run(GRUNT[pos], fits)
    b = run(GRUNT["cut"], fits)
    bands = sorted(a)
    s = []
    for f in bands:
        num = abs(a[f][0] + a[f][1])
        den = abs(b[f][0] + b[f][1])
        s.append(20.0 * math.log10(num / den) if num > 0 and den > 0 else float("nan"))
    return bands, s


def locate(pos, fits):
    bands, s = span(pos, fits)
    return peak(bands, s, SPAN_LO, SPAN_HI)


def selfcheck():
    print("### SELF-CHECK — this probe vs the report's own model row (drive-min, sweep_clean)")
    print(f"    {'pos':<6} {'probe Hz':>9} {'dB':>7} | {'report Hz':>10} {'dB':>7}"
          f" | {'d(oct)':>7} {'d(dB)':>7} | verdict")
    ok_all = True
    for pos, (rf, ry) in REPORT_MODEL.items():
        f, y = locate(pos, [])
        doct, ddb = math.log2(f / rf), y - ry
        ok = abs(doct) <= 0.05 and abs(ddb) <= 0.5
        ok_all &= ok
        print(f"    {pos:<6} {f:9.1f} {y:+7.2f} | {rf:10.1f} {ry:+7.2f}"
              f" | {doct:+7.2f} {ddb:+7.2f} | {'PASS' if ok else 'FAIL'}")
    print(f"    => {'probe VALIDATED, locus is readable' if ok_all else 'MISMATCH — do NOT read the locus'}")
    return ok_all


def crossover_table():
    """Where |OD| overtakes the bleed, per GRUNT position — the quantity the gate proxies."""
    print(f"\n### |OD| - |bleed| (dB) per band, drive-min, {DBFS:.0f} dBFS")
    ref = run(GRUNT["cut"], [])
    bands = sorted(ref)
    print(f"    {'pos':<6}" + "".join(f"{b:>8.0f}" for b in bands))
    for pos in ("cut", "flat", "boost"):
        d = run(GRUNT[pos], [])
        row = [20 * math.log10(abs(d[f][0]) / abs(d[f][1])) for f in bands]
        print(f"    {pos:<6}" + "".join(f"{v:8.1f}" for v in row))
        # linear-in-log-f interpolation of the 0 dB crossing
        fx = None
        for i in range(len(bands) - 1):
            if row[i] < 0 <= row[i + 1]:
                t = -row[i] / (row[i + 1] - row[i])
                fx = 2 ** (math.log2(bands[i]) + t * math.log2(bands[i + 1] / bands[i]))
                break
        print(f"    {'':<6}  |OD| = |bleed| at {fx:.1f} Hz" if fx else f"    {'':<6}  no crossing in band")


def _scan_one(job):
    """One swept value: locate the flat and boost peaks. The unit of parallelism.

    Safe to run concurrently because `run()` reads the decomposition off the child's STDOUT
    (capture_output=True) rather than through a scratch file -- there is no per-item path to
    collide on at all, which is why this one needs no race_check().
    """
    key, v = job
    ff, fy = locate("flat", [(key, v)])
    bf, by = locate("boost", [(key, v)])
    return v, ff, fy, bf, by


def scan(spec, jobs=None):
    key, vals = spec.split("=", 1)
    vals = [v.strip() for v in vals.split(",")]
    print(f"\n### LOCUS — {key} swept; peak of the drive-min GRUNT span (flat and boost)")
    print(f"    pedal target: flat {GATE_TARGETS['flat'][0]:.1f} Hz {GATE_TARGETS['flat'][1]:+.2f} dB"
          f" | boost {GATE_TARGETS['boost'][0]:.1f} Hz {GATE_TARGETS['boost'][1]:+.2f} dB")
    print(f"    {key:>12} | {'flat Hz':>8} {'dB':>7} {'d(oct)':>7} | {'boost Hz':>9} {'dB':>7} {'d(oct)':>7}")
    # Swept values are independent (each is its own set of decomposition runs). pmap keeps them
    # in sweep order, so the printed table is byte-identical to the serial one -- the rows are
    # collected first and printed after, rather than streamed as they finish.
    for v, ff, fy, bf, by in pmap(_scan_one, [(key, v) for v in vals], jobs=jobs):
        print(f"    {v:>12} | {ff:8.1f} {fy:+7.2f} {math.log2(ff / GATE_TARGETS['flat'][0]):+7.2f}"
              f" | {bf:9.1f} {by:+7.2f} {math.log2(bf / GATE_TARGETS['boost'][0]):+7.2f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if "--selfcheck" in args:
        selfcheck()
    if "--crossover" in args:
        crossover_table()
    for a in args:
        if a.startswith("--scan"):
            scan(args[args.index(a) + 1] if a == "--scan" else a.split("=", 1)[1])
