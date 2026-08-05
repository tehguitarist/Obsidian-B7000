#!/usr/bin/env python3.11
"""A5 step 1 — WHERE is the clean path's headroom, and what does the pedal's own headroom
imply about `kInputRef`?

Session 39 established (analysis/clean_thd_check.py) that with DIST off the PLUGIN breaks up
between -12 and -9 dBFS on the 1 kHz `lvl_` ladder and reaches 11-23% THD by -3 dBFS, while the
real pedal stays at its measurement floor (0.0000%) at EVERY step -36..-3. Root cause was
A/B-confirmed as the session-21 RailClamp (`--fit railEnabled=0` returns every case to the floor)
but was NOT localised to a stage or turned into a number.

This probe turns it into a number, WITHOUT changing anything in src/:

  (1) ONSET, measured not assumed. Render one clean capture's exact settings at a ladder of
      `--input-trim` values and find the input level (in dBFS at the pedal's jack) where the
      clean chain's THD crosses a threshold. Because the DIST-off path is linear apart from the
      RailClamps, that onset is a property of (input volts vs rail volts) alone.

  (2) THE CONSTRAINT ON kInputRef. The onset in VOLTS is fixed by the chain's gain and the rail
      window; the onset in dBFS is onset_volts / kInputRef. The pedal is clean at -3 dBFS, so
          kInputRef  <=  V_onset / 10^(-3/20)
      is a HARD one-sided bound that the clean path alone can supply — and it is INDEPENDENT of
      the clipper, which is what makes it interesting: session 17 set kInputRef = 3.377 V/FS by
      fitting it JOINTLY with the clipper ceilings precisely because the two are degenerate under
      audio-only captures (GainStaging.h). The clean path has no clipper in it, so it breaks that
      degeneracy from the outside.

  (3) A DIRECT CHECK that scaling kInputRef is the same lever. `--input-ref` is swept explicitly
      and the onset must move dB-for-dB with it; if it does not, something else in the clean path
      is nonlinear and the whole framing above is wrong.

⚠ `--input-trim X` and `--input-ref (kInputRef * 10^(X/20))` are EXACTLY equivalent for the chain
(offline_render mirrors processBlock: work = wet * inTrim * kInputRef, and the output gain divides
kInputRef back out), so (1) and (3) measure the same thing two ways on purpose — (3) is the
control for (1).

Run: /opt/homebrew/bin/python3.11 analysis/clean_headroom_probe.py
"""
import sys, os, subprocess, tempfile

sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import captures as C

FS = A.FS
BIN = C.RENDER_BIN
CAP_DIR = "analysis/captures"
NYQ = FS / 2.0
MARGIN = 0.95

# GainStaging.h, mirrored here so the printed volts are honest. Kept as a literal on purpose:
# the point of the probe is to test this number, so it must not be read from the thing under test.
# ⚠⚠ CORRECTED s160 (item 4): this read 3.377 — the SESSION-17 value — for ~120 sessions, while
# GainStaging.h shipped 1.2596 from s44 and 0.90 from s109. So every volt this probe printed was
# 3.75x too high, and its `kInputRef <=` bound was being compared against a number the plugin had
# not carried since session 44. The bound's METHOD is unaffected (it derives an onset in volts from
# the render and divides by K); only the printed volts and the headroom verdict move.
# ⛔ Being a deliberate literal is what let this rot — a literal must still be re-checked against
# the source when the source ships a new value (`verify-the-CONSTANT-not-the-prose`).
K_INPUT_REF_SHIPPED = 0.90

# The pedal's own hottest ladder rung. gen_test_signal.py::LEVEL_STEPS_DB tops out at -3 dBFS,
# and the pedal is at its floor there (session 39) — so this is the level the bound is taken at.
HOTTEST_STEP_DB = -3.0

# Captures to characterise. ref-clean is flat EQ (the cleanest read of the fixed -2.2 EqPreGain
# path); the boost extremes add a band's own gain on top and should rail EARLIER.
CASES = [
    ("ref-clean.wav", "flat EQ"),
    ("bass-1700_gain-n12_base-clean.wav", "BASS boost max"),
    ("treble-1700_gain-n12_base-clean.wav", "TREBLE boost max"),
    ("lomid-1700_gain-n12_base-clean.wav", "LO-MID boost max"),
    ("himid-1700_gain-n12_base-clean.wav", "HI-MID boost max"),
    # ⛔ ("master-1700_gain-n12_base-clean.wav", "MASTER max") was here and is EXCLUDED BY NAME
    # (s160, item 4). Two independent defects, either one fatal to a HEADROOM probe:
    #   * GATE T: the file is a duplicated / mis-dialled knob position reading 4.447 dB LOW, and is
    #     neither top detent — so it understates how hard the chain is actually driven.
    #   * s142: its `lvl_-3` rung is the one segment s115 measured PINNED, i.e. that tone is a
    #     capture-side ceiling. An onset probe reads a ceiling as "the chain broke up here".
    # MASTER is a post-EQ attenuator at unity when max, so it adds no gain the boost cases above
    # do not already cover — nothing is lost by dropping it. Corrected levels for a duplicated
    # detent come from `master_anchor_gate.detent_corrections()`; do NOT re-add this file raw.
]

# THD threshold for "the chain has started to break up". The pedal reads 0.0000% at every rung and
# the plugin's own sub-onset rungs read 0.000% too, so anything above the FFT floor is real; 0.01%
# is ~60 dB below the fundamental, comfortably above numerical noise and far below audibility.
THD_ONSET_PCT = 0.01


def harmonics_db(x, f0, max_order=8):
    """Per-harmonic level re fundamental (dB), Nyquist-guarded. Same estimator as
    clean_thd_check.py / tone_thd_nyquist_check.py so the two tools' numbers compare directly."""
    w = np.hanning(len(x))
    X = np.abs(np.fft.rfft(x * w))
    fr = np.fft.rfftfreq(len(x), 1 / FS)

    def amp(fc):
        i = int(np.argmin(np.abs(fr - fc)))
        return np.max(X[max(0, i - 3): i + 4])

    fund = amp(f0)
    out = {}
    for k in range(2, max_order + 1):
        if f0 * k > NYQ * MARGIN:
            break
        out[k] = 20 * np.log10(amp(f0 * k) / (fund + 1e-20) + 1e-20)
    thd = 100 * np.sqrt(sum((10 ** (v / 20)) ** 2 for v in out.values())) if out else 0.0
    return out, thd


def render(parsed, out_path, extra):
    # --os 1: with distEngage=False the OD region's output is discarded by LevelBlend, and the
    # clean path is base-rate at every factor, so the OS factor changes only the clean-tap delay
    # (which align() removes). Verified: os 1 vs os 8 agree to the bit on these renders. 6x faster,
    # which matters because the bisection below is ~11 renders per case.
    args = [BIN, "analysis/test_signal_48k.wav", out_path, "--os", "1"] + C.render_args(parsed) + extra
    subprocess.run(args, check=True, capture_output=True)


def thd_at(parsed, tmp, tag, extra, seg="lvl_-3", f0=1000.0):
    out_path = os.path.join(tmp, f"{tag}.wav")
    render(parsed, out_path, extra)
    y, _ = A.align(A.load(out_path), A.load(A.ORIG))
    _, thd = harmonics_db(A.seg_of(y, seg), f0)
    return thd


def find_onset_db(parsed, tmp, tag, base_extra, lo=-40.0, hi=+12.0, tol=0.05):
    """Input-trim (dB) at which THD on the hottest rung crosses THD_ONSET_PCT.

    Returns the trim in dB relative to the shipped calibration, i.e. the ladder rung the chain
    would break on is HOTTEST_STEP_DB - onset_trim.  Bisection is valid here because the clean
    path is linear below the rail and monotone-increasing in distortion above it — asserted, not
    assumed: the bracket ends are checked and the caller sees a warning if they do not straddle.
    """
    orig = A.load(A.ORIG)

    def f(trim):
        out_path = os.path.join(tmp, f"{tag}_{trim:+.3f}.wav")
        render(parsed, out_path, base_extra + ["--input-trim", f"{trim:.4f}"])
        y, _ = A.align(A.load(out_path), orig)
        _, thd = harmonics_db(A.seg_of(y, "lvl_-3"), 1000.0)
        return thd

    flo, fhi = f(lo), f(hi)
    if flo >= THD_ONSET_PCT:
        return None, f"already distorting at {lo:+.0f} dB trim (THD {flo:.3f}%)"
    if fhi < THD_ONSET_PCT:
        return None, f"still clean at {hi:+.0f} dB trim (THD {fhi:.3f}%)"
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if f(mid) >= THD_ONSET_PCT:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi), None


def main():
    if not os.path.exists(BIN):
        sys.exit(f"OfflineRender not built at {BIN} — cmake --build build --target OfflineRender")
    tmp = tempfile.mkdtemp(prefix="clean_headroom_")
    orig = A.load(A.ORIG)

    # ---------------------------------------------------------------- (1) onset per case
    print("=" * 108)
    print("(1) CLEAN-PATH ONSET — input trim (dB, re the shipped calibration) at which the")
    print(f"    DIST-off render's 1 kHz THD crosses {THD_ONSET_PCT}% on the hottest rung (lvl_-3)")
    print("=" * 108)
    print(f"{'capture':<40}{'what':<18}{'onset trim':>11}{'breaks at':>11}{'V pk @ jack':>13}"
          f"{'kInputRef bound':>17}")
    print("-" * 108)

    onsets = {}
    for cap_name, what in CASES:
        cap_path = os.path.join(CAP_DIR, cap_name)
        if not os.path.exists(cap_path):
            print(f"{cap_name:<40}(missing capture — skipped)")
            continue
        parsed = C.parse_capture(cap_name)
        trim, err = find_onset_db(parsed, tmp, cap_name.replace(".wav", ""), [])
        if trim is None:
            print(f"{cap_name:<40}{what:<18}  {err}")
            continue
        onsets[cap_name] = trim
        # The rung this chain breaks on, and the jack voltage there. A NEGATIVE onset trim means
        # the render had to be turned DOWN to stay clean, so the chain breaks BELOW the hottest
        # rung: breaks_at = hottest + trim. (Written as `hottest - trim` first, which put the
        # onset at +3.8 dBFS — impossible, since the ladder stops at -3 — and disagreed with the
        # direct THD table three lines down. Sanity-check a derived column against the raw one.)
        breaks_at = HOTTEST_STEP_DB + trim
        v_onset = K_INPUT_REF_SHIPPED * 10 ** (breaks_at / 20.0)
        # Bound: the pedal is clean at the hottest rung IT ACTUALLY SAW — for a gain-n12 capture
        # the interface was 12.071 dB down (session 21: the MEASURED delta, never the dial), so
        # demanding cleanliness at a level that capture never reached would invent a constraint.
        rung_seen = HOTTEST_STEP_DB - C.gain_correction_db(parsed)
        k_bound = v_onset / 10 ** (rung_seen / 20.0)
        print(f"{cap_name:<40}{what:<18}{trim:>+10.2f} {breaks_at:>+10.2f} {v_onset:>12.3f}"
              f"{k_bound:>16.3f}")

    print()
    print(f"  reading: 'breaks at' is the dBFS ladder rung this capture's clean chain first distorts")
    print(f"  on at the SHIPPED kInputRef = {K_INPUT_REF_SHIPPED} V/FS. The pedal is at its floor on")
    print(f"  EVERY rung it was given, so any 'breaks at' above that capture's own hottest rung is a")
    print(f"  defect; the last column is the kInputRef that would move the onset exactly onto it —")
    print(f"  a hard upper bound with zero margin. ⚠ The gain-n12 captures were fed 12.071 dB less,")
    print(f"  so their bound is correspondingly looser and the FLAT-EQ full-level case binds.")

    # ------------------------------------------------- (2) the ladder, shipped vs candidate K
    print()
    print("=" * 108)
    print("(2) THE LADDER — THD% per rung on ref-clean, shipped kInputRef vs candidates")
    print("=" * 108)
    cap_name = "ref-clean.wav"
    parsed = C.parse_capture(cap_name)
    rungs = [-24, -18, -15, -12, -9, -6, -3]

    ped, _ = A.align(C.load_capture(os.path.join(CAP_DIR, cap_name)), orig)
    ped_row = []
    for db in rungs:
        _, t = harmonics_db(A.seg_of(ped, f"lvl_{db}"), 1000.0)
        ped_row.append(t)

    print(f"{'kInputRef':>11} | " + " ".join(f"{db:>8}" for db in rungs))
    print("-" * 108)
    print(f"{'PEDAL':>11} | " + " ".join(f"{t:>8.4f}" for t in ped_row))

    k_candidates = [K_INPUT_REF_SHIPPED, 2.4, 1.7, 1.2, 0.87]
    for k in k_candidates:
        row = []
        out_path = os.path.join(tmp, f"k_{k:.3f}.wav")
        render(parsed, out_path, ["--input-ref", f"{k:.6f}"])
        y, _ = A.align(A.load(out_path), orig)
        for db in rungs:
            _, t = harmonics_db(A.seg_of(y, f"lvl_{db}"), 1000.0)
            row.append(t)
        label = f"{k:.3f}" + (" *" if abs(k - K_INPUT_REF_SHIPPED) < 1e-9 else "")
        print(f"{label:>11} | " + " ".join(f"{t:>8.4f}" for t in row))
    print("  (* = shipped)")

    # -------------------------------------------- (3) control: onset must track --input-ref 1:1
    print()
    print("=" * 108)
    print("(3) CONTROL — does the onset move dB-for-dB with kInputRef? (it must, if the only")
    print("    nonlinearity on this path is a fixed-voltage clamp)")
    print("=" * 108)
    base_trim, _ = find_onset_db(parsed, tmp, "ctrl_base", [])
    print(f"{'kInputRef':>11}{'onset trim':>12}{'expected':>11}{'error':>9}")
    print("-" * 108)
    print(f"{K_INPUT_REF_SHIPPED:>11.3f}{base_trim:>+11.2f}{'—':>11}{'—':>9}")
    worst = 0.0
    for k in (2.4, 1.2):
        t, err = find_onset_db(parsed, tmp, f"ctrl_{k}", ["--input-ref", f"{k:.6f}"])
        if t is None:
            print(f"{k:>11.3f}  {err}")
            continue
        expected = base_trim + 20 * np.log10(K_INPUT_REF_SHIPPED / k)
        print(f"{k:>11.3f}{t:>+11.2f}{expected:>+11.2f}{t - expected:>+9.2f}")
        worst = max(worst, abs(t - expected))
    verdict = "PASS — a pure fixed-voltage clamp" if worst < 0.25 else \
              "FAIL — something else on the clean path is level-dependent"
    print(f"\n  worst error {worst:.2f} dB  =>  {verdict}")


if __name__ == "__main__":
    main()
