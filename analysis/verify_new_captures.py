#!/usr/bin/env python3.11
"""Phase-9 SESSION 70 — GATE every capture that landed in the final recording window, BEFORE any
of them is read for a measurement.

WHY THIS EXISTS AS ITS OWN TOOL. Three separate sessions lost real time to a capture that looked
fine and was not, and in each case the defect was found late, by a purpose-built test, after it had
already moved a number:

  * session 24  14 files lost to the interface's own input headroom, every one pinned at 0.98850.
                The `gain-n12` token exists solely because of that.
  * session 54  `attack-cut_blend-1430_base-od.wav` had MASTER set where BLEND should have been.
                Caught only by a geometric test (a straight line's modulus has at most ONE interior
                minimum) -- and the FIRST re-capture attempt was still wrong.
  * session 68  the flat-topping gate itself was a false-positive generator and REJECTED a
                reference capture that had been in the matrix since session 22.

So this runs first, reports everything, and condemns nothing it cannot justify.

⚠ THE GATE IS CALIBRATED AGAINST THE DEFECT'S SIGNATURE, NOT A PROXY FOR IT (session 68's general
lesson). "A long run of samples near the peak" is a PROXY and it fires on clean signal: a sine
spends ~5.5 % of its period above 98.5 % of its own peak, which at the 20 Hz end of a log sweep is
~30 samples at 48 kHz -- entirely normal. The SIGNATURE of converter clipping is a plateau PINNED at
the converter's ceiling: a tight threshold (0.9995x peak) AND a near-full-scale peak. A plateau
BELOW full scale is the PEDAL's own rail limiting -- real signal -- so it is reported, never
rejected.

Run from repo root:
    /opt/homebrew/bin/python3.11 analysis/verify_new_captures.py
    /opt/homebrew/bin/python3.11 analysis/verify_new_captures.py --since 2026-07-29T12:50
"""
import argparse
import os
import sys
import datetime as dt

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import captures as C  # noqa: E402

CAPTURE_DIR = "analysis/captures"

# ---- expected durations, by family ----------------------------------------------------------
# The matrix grammar's files are all one frozen stimulus; the two side stimuli have their own
# lengths. A short file is NOT a cosmetic problem: missing segments read as ZEROS and fake features
# (protocol item 5), which is exactly the failure mode that is invisible in a spectrum.
MATRIX_SEC = 83.700
# ⚠ DERIVED FROM THE STIMULUS ON DISK, NOT TRANSCRIBED. A first draft of this gate hardcoded
# 175.9 s -- the figure quoted in `docs/final-capture-window.md` §3 -- and FAILED all ten notch
# captures, which are 176.100 s. The captures were right and the gate was wrong: the doc's number
# was rounded/mis-stated at the time it was written. Reading the length off the generator's own
# output makes the two impossible to drift apart (the session-33 transcribed-constant trap).
NOTCH_STIMULUS = "analysis/notch_sweep_48k.wav"
NOTCH_SEC_FALLBACK = 176.100
JFET_SEC = 85.5          # gen_jfet_ladder.py's own length; asserted loosely, see expected_sec
DUR_TOL = 0.05

# ---- duplicate-take gate ---------------------------------------------------------------------
# ⭐ WHY THIS EXISTS (session 70). The §2 repeatability set arrived as ten files whose peak and RMS
# agreed to four decimal places. That is not what five independent takes look like, and it was not:
# within each family all five differ by rms -148..-164 dBFS, i.e. FLOAT32 ROUNDING, roughly 40-60 dB
# BELOW any physical converter noise floor -- and `repeat_ref-od_*` proved to be copies of the
# existing `ref-od.wav` from a prior session. Zero take-to-take information in a set whose entire
# purpose is to measure take-to-take variation.
#
# The discriminator is the NOISE FLOOR, and it is not a tunable threshold -- it is a physical fact.
# Two genuine analogue re-recordings cannot agree better than the converter's own noise, which is
# ~-90 to -110 dBFS on any interface. Anything quieter than DUP_RMS_DB is arithmetic, not audio.
DUP_RMS_DB = -120.0      # rms(a-b) below this => the two files are the same audio


def notch_sec():
    try:
        sr, x = wavfile.read(NOTCH_STIMULUS)
        return len(x) / float(sr)
    except Exception:  # noqa: BLE001
        return NOTCH_SEC_FALLBACK

# ---- flat-topping gate (session 68's rebuilt version; see the module docstring) ---------------
PIN_TH = 0.9995          # "pinned" = within 0.05 % of this file's own peak
PIN_MIN_RUN = 8          # consecutive pinned samples to call it a plateau
NEAR_FS_PEAK = 0.95      # scope: the CONVERTER's ceiling, not the pedal's
LOOSE_TH = 0.985         # reported ONLY -- this is the proxy that produced the false positive


def longest_run(x, th):
    """Longest run of consecutive samples with |x| >= th."""
    m = np.abs(x) >= th
    if not m.any():
        return 0
    # run lengths via diff of the indices where the mask changes
    d = np.diff(np.concatenate(([0], m.view(np.int8), [0])))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return int(np.max(ends - starts))


def family(name):
    if name.startswith("notch_"):
        return "notch"
    if name.startswith("jfet_ladder_"):
        return "jfet"
    if name.startswith("repeat_"):
        return "repeat"
    if name.startswith("a3tones_"):
        return "a3tones"
    return "matrix"


def expected_sec(fam):
    return {"notch": notch_sec(), "jfet": JFET_SEC}.get(fam, MATRIX_SEC)


def audio_of(path):
    """Raw mono float64, no resampling -- we are comparing files, not measuring the pedal."""
    sr, raw = wavfile.read(path)
    x = raw.astype(np.float64) if raw.dtype.kind == "f" else raw.astype(np.float64) / np.iinfo(raw.dtype).max
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x


def duplicate_scan(paths):
    """Find files that are the SAME AUDIO as another file (see DUP_RMS_DB).

    Deliberately compares every replicate family against the whole capture set, not just against its
    own siblings: `repeat_ref-od_*` turned out to be copies of `ref-od.wav`, which a
    siblings-only check would have reported as five perfectly consistent takes.
    """
    groups = {}
    for p in paths:
        x = audio_of(p)
        # bucket by (length, peak) so the O(n^2) compare only runs on plausible pairs
        key = (len(x), round(float(np.max(np.abs(x))), 6))
        groups.setdefault(key, []).append((p, x))

    dups = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (pa, a), (pb, b) = items[i], items[j]
                d = a - b
                rms = 20.0 * np.log10(float(np.sqrt(np.mean(d ** 2))) + 1e-30)
                if rms < DUP_RMS_DB:
                    dups.append((os.path.basename(pa), os.path.basename(pb), rms))
    return dups


def check_one(path):
    """Return a dict of every measured property plus a list of (level, message) findings."""
    name = os.path.basename(path)
    fam = family(name)
    out = dict(name=name, family=fam)
    findings = []

    sr, raw = wavfile.read(path)
    out["sr"] = int(sr)
    out["dtype"] = str(raw.dtype)
    out["channels"] = 1 if raw.ndim == 1 else int(raw.shape[1])
    x = raw.astype(np.float64) if raw.dtype.kind == "f" else raw.astype(np.float64) / np.iinfo(raw.dtype).max
    if x.ndim > 1:
        x = x.mean(axis=1)
    out["sec"] = len(x) / float(sr)

    if sr != 48000:
        findings.append(("FAIL", f"sample rate {sr}, expected 48000"))
    if raw.dtype.kind != "f":
        findings.append(("WARN", f"dtype {raw.dtype}, expected float32"))
    if out["channels"] != 1:
        findings.append(("WARN", f"{out['channels']} channels, expected mono"))

    want = expected_sec(fam)
    # jfet's length is asserted loosely because that stimulus predates this gate and its exact
    # length is a property of gen_jfet_ladder.py, not of the recording.
    tol = DUR_TOL if fam != "jfet" else 2.0
    if abs(out["sec"] - want) > tol:
        findings.append(("FAIL", f"duration {out['sec']:.3f} s, expected {want:.3f} s (+-{tol})"))

    peak = float(np.max(np.abs(x)))
    out["peak"] = peak
    out["peak_db"] = 20.0 * np.log10(peak + 1e-20)
    out["rms_db"] = 20.0 * np.log10(float(np.sqrt(np.mean(x ** 2))) + 1e-20)
    if peak >= 0.999:
        findings.append(("FAIL", f"peak {peak:.5f} is at/over full scale"))

    # --- the flat-topping gate ---------------------------------------------------------------
    out["run_pin"] = longest_run(x, PIN_TH * peak)
    out["run_loose"] = longest_run(x, LOOSE_TH * peak)
    if out["run_pin"] >= PIN_MIN_RUN:
        if peak >= NEAR_FS_PEAK:
            findings.append(("FAIL", f"CONVERTER CLIPPING: {out['run_pin']} samples pinned within "
                                     f"0.05% of a {peak:.4f} peak"))
        else:
            # A plateau well below full scale cannot be the converter. Report it -- it is the
            # pedal's own rail limiting, i.e. real signal we WANT.
            findings.append(("INFO", f"plateau of {out['run_pin']} samples at peak {peak:.4f} "
                                     f"({out['peak_db']:.1f} dBFS) -- below full scale, so this is "
                                     f"the pedal's limiting, not the converter's"))

    # --- silence / dropout -------------------------------------------------------------------
    if peak < 1e-4:
        findings.append(("FAIL", "file is silent"))
    n_zero = int(np.sum(np.abs(x) < 1e-9))
    out["zero_frac"] = n_zero / float(len(x))

    # --- filename grammar (matrix files only) -------------------------------------------------
    out["parsed"] = None
    if fam == "matrix":
        try:
            out["parsed"] = C.parse_capture(name)
        except Exception as exc:  # noqa: BLE001
            findings.append(("FAIL", f"does not parse: {exc}"))

    out["findings"] = findings
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-07-29T12:50",
                    help="only check files modified at/after this ISO timestamp")
    ap.add_argument("--all", action="store_true", help="check every capture on disk")
    args = ap.parse_args()

    since = None if args.all else dt.datetime.fromisoformat(args.since).timestamp()

    paths = []
    for fn in sorted(os.listdir(CAPTURE_DIR)):
        if not fn.endswith(".wav"):
            continue
        p = os.path.join(CAPTURE_DIR, fn)
        if since is None or os.path.getmtime(p) >= since:
            paths.append(p)

    if not paths:
        print("no captures matched -- nothing to verify")
        return 0

    print(f"VERIFYING {len(paths)} captures"
          + ("" if args.all else f" modified at/after {args.since}"))
    print()

    rows = [check_one(p) for p in paths]

    hdr = f"{'capture':52s} {'fam':7s} {'sec':>8s} {'peak':>7s} {'dBFS':>7s} {'rms dB':>8s} {'pin':>4s} {'loose':>6s}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['name']:52s} {r['family']:7s} {r['sec']:8.3f} {r['peak']:7.4f} "
              f"{r['peak_db']:7.1f} {r['rms_db']:8.2f} {r['run_pin']:4d} {r['run_loose']:6d}")

    print()
    n_fail = n_warn = n_info = 0
    for r in rows:
        for lvl, msg in r["findings"]:
            print(f"  [{lvl}] {r['name']}: {msg}")
            n_fail += lvl == "FAIL"
            n_warn += lvl == "WARN"
            n_info += lvl == "INFO"
    if not any(r["findings"] for r in rows):
        print("  (no findings)")

    # --- family summaries ---------------------------------------------------------------------
    print()
    print("BY FAMILY")
    fams = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    for fam, rs in sorted(fams.items()):
        peaks = [r["peak"] for r in rs]
        print(f"  {fam:7s} n={len(rs):3d}  peak {min(peaks):.4f}-{max(peaks):.4f}  "
              f"durations {min(r['sec'] for r in rs):.3f}-{max(r['sec'] for r in rs):.3f} s")

    # --- duplicate-take scan ------------------------------------------------------------------
    # Scanned against EVERY capture on disk, not just the ones under test -- see duplicate_scan.
    print()
    print("DUPLICATE-TAKE SCAN (rms(a-b) < %.0f dBFS => same audio, not a re-recording)" % DUP_RMS_DB)
    all_paths = sorted(os.path.join(CAPTURE_DIR, f)
                       for f in os.listdir(CAPTURE_DIR) if f.endswith(".wav"))
    dups = duplicate_scan(all_paths)
    if dups:
        for a, b, rms in dups:
            print(f"  [FAIL] {a}  ==  {b}   (rms diff {rms:.1f} dBFS)")
            n_fail += 1
        print()
        print("  ⛔ A converter's own noise floor is ~-90 to -110 dBFS, so two genuine analogue")
        print("     re-recordings CANNOT agree better than that. These pairs are the same audio.")
    else:
        print("  none -- every capture is distinct audio")

    print()
    print(f"VERDICT: {n_fail} FAIL, {n_warn} WARN, {n_info} INFO over {len(rows)} captures")
    if n_fail:
        print("  ⛔ do NOT read a measurement out of a FAIL capture until it is re-taken.")
    else:
        print("  ✅ every capture passes the structural gate. INFO lines are real signal, not defects.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
