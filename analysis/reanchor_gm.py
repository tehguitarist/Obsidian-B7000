#!/usr/bin/env python3.11
"""Phase-7 step 2 — RE-ANCHOR jfetGm against the corrected mixer.

Why this exists
---------------
Every jfetGm estimate on record (0.551 / 0.090 / 0.0274 mS) is contaminated by the BLEND
clean bleed: at BLEND = max-OD the output is alpha*OD + beta*CLEAN, and the three fits were
really measuring the OD/clean MIX RATIO, not the OD path (docs/phase7-calibration-handover.md,
"THE PATH FORWARD FOR THE J201", steps 1-2). Step 1 (analysis/mixer_law.py) SETTLED the mixer:
the topology is faithful, the bleed is real, and the LEVEL taper is p ~= 2.25, not the shipped
1.43 -> L(noon) 0.371 -> 0.210, i.e. the modelled bleed was UNDERSTATED. So gm must be re-fit
with the corrected mixer before the shaper is touched (step 3).

The measurement (bleed-aware, scale-free)
-----------------------------------------
The clean tap (IC1_A) is gm-INDEPENDENT and everything after BLEND is linear, so for one tone
at the OUTPUT:

    |H1(drive OD capture)| / |H1(B=0 clean capture)|
        = | alpha(noon) * OD_1(gm) / CLEAN_1  +  beta(noon) |          (B=max, L=noon)

The right side is a pure ratio: makeup, masterTaperExp, kInputRef and the interface gain all
cancel because each side is normalised to ITS OWN clean reference (B=0). No cross-file complex
subtraction is needed -- the phase of alpha*OD + beta*CLEAN is computed by the DSP itself when
we RENDER the chain at a trial gm, with the corrected taper. So:

    target(role,tone) = |H1_cap(drive-* )| / |H1_cap(blend-0700)|        <- captures, fixed
    model(gm,tone)    = |H1_mdl(drive-*,gm)| / |H1_mdl(blend-0700)|      <- blend-0700 once/gm-indep
    solve  model(gm) = target.

drive-min (drive-0700) is the plan's primary anchor because the OD path is LINEAR there, so the
fundamental is pure gm-gain with ZERO clipper/shaper coupling. Its weakness: the OD path is at
its quietest, so the clean bleed dominates and the ratio is only weakly sensitive to gm -- the
scan below prints the ratio ERROR at every gm so that (in)sensitivity is VISIBLE, not hidden in
a single reported minimum. drive-noon (ref-od) is a better-conditioned CROSS-CHECK (OD ~5x
louder), at the cost of ~0.3 dB of clipper compression on the fundamental (THD ~= -31 dB there).

Speed: the MODEL side renders a compact 3-tone input (110/220/440 Hz, -14 dBFS to match the
capture's tone segments), NOT the full 84 s signal -- a full OS-8 render is ~2 min, a 4 s tone
render is well under a second. Capture targets come from the real tone segments (measured once).

Run: /opt/homebrew/bin/python3.11 analysis/reanchor_gm.py
"""
import os
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import RENDER_BIN, load_capture, parse_capture, render_args

CAP = "analysis/captures"
FS = A.FS
ORIG = "analysis/test_signal_48k.wav"

# LEVEL taper: shipped 1.43 vs the step-1 measured ~2.25. Run both so the effect of correcting
# the mixer on the gm estimate is explicit, not asserted.
TAPERS = {"shipped 1.43": 1.43, "corrected 2.25": 2.25}
PRIMARY_TAPER = 2.25

# ro/rq2 are NOT identifiable from this data (session 4: cost flat to <=0.01 dB over 16x) -> held
# at nominal. Only gm is fit.
RO_NOM, RQ2_NOM = 200.0e3, 1.0e6

GM_SCAN = [0.03e-3, 0.05e-3, 0.07e-3, 0.09e-3, 0.12e-3, 0.16e-3, 0.20e-3, 0.30e-3, 0.50e-3,
           0.69e-3]

# Extended across the band to expose FREQUENCY STRUCTURE in the OD/clean ratio error — a
# notch-shaped error near ~322/717 Hz would confirm the open treble-net / bridged-T discrepancy
# is what breaks the per-tone gm agreement, and 1k/2k (above both notches) offer a cleaner anchor.
TONES = [("tone_82.41", 82.41), ("tone_110", 110.0), ("tone_220", 220.0), ("tone_440", 440.0),
         ("tone_1000", 1000.0), ("tone_2000", 2000.0)]

# capture roles
CLEAN_CAP = "blend-0700_base-od.wav"   # BLEND = 0 -> pure clean output (the OD/clean denominator)
DMIN_CAP = "drive-0700_base-od.wav"    # drive MIN, B=max, L=noon -> linear OD + bleed
DNOON_CAP = "ref-od.wav"               # drive NOON, B=max, L=noon -> OD (mild clip) + bleed

# --- compact model input: 110/220/440 Hz tones, -14 dBFS (matches gen_test_signal tone level) ---
TONE_SEC = 1.0
GAP_SEC = 0.3
MODEL_IN = "/tmp/reanchor_tones.wav"
MODEL_F = [f for _, f in TONES]


def make_model_input():
    parts = [np.zeros(int(0.3 * FS))]
    win = {}
    cursor = 0.3
    for f in MODEL_F:
        n = int(TONE_SEC * FS)
        t = np.arange(n) / FS
        x = (10 ** (-14 / 20)) * np.sin(2 * np.pi * f * t)
        k = int(0.02 * FS)
        env = np.ones(n); env[:k] = np.linspace(0, 1, k); env[-k:] = np.linspace(1, 0, k)
        win[f] = (cursor, cursor + TONE_SEC)
        parts += [x * env, np.zeros(int(GAP_SEC * FS))]
        cursor += TONE_SEC + GAP_SEC
    sig = np.concatenate(parts)
    wavfile.write(MODEL_IN, FS, sig.astype(np.float32))
    return win


def h1_at(x, t0, t1, f0):
    """|H1| of a steady tone in [t0,t1] s (trim edges, Hann-windowed exact-bin projection)."""
    seg = x[int((t0 + 0.15) * FS):int((t1 - 0.05) * FS)]
    n = len(seg)
    w = np.hanning(n)
    t = np.arange(n) / FS
    return abs(np.sum(seg * w * np.exp(-2j * np.pi * f0 * t)) * (2.0 / np.sum(w)))


def h1_cap(cap, orig, seg_name, f0):
    """|H1| for a captured tone segment (aligned)."""
    x, _lag = A.align(cap, orig)
    seg = A.seg_of(x, seg_name)
    seg = seg[int(0.15 * FS):len(seg) - int(0.05 * FS)]
    n = len(seg)
    w = np.hanning(n)
    t = np.arange(n) / FS
    return abs(np.sum(seg * w * np.exp(-2j * np.pi * f0 * t)) * (2.0 / np.sum(w)))


def render_model(cap_file, gm, taper, win, tag):
    """Render the compact tone input through a capture's control settings; return {f0: |H1|}."""
    parsed = parse_capture(cap_file)
    extra = ["--fit", f"levelTaperExp={taper:.6g}",
             "--fit", f"jfetGm={gm:.9g}",
             "--fit", f"jfetRo={RO_NOM:.9g}",
             "--fit", f"jfetRq2={RQ2_NOM:.9g}"]
    out = f"/tmp/reanchor_m_{tag}.wav"
    subprocess.run([RENDER_BIN, MODEL_IN, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    r = A.load(out)
    return {f: h1_at(r, *win[f], f) for f in MODEL_F}


def main():
    win = make_model_input()
    orig = A.load(ORIG)

    print("Loading captures + computing OD/clean fundamental targets...")
    clean_cap = load_capture(f"{CAP}/{CLEAN_CAP}")
    dmin_cap = load_capture(f"{CAP}/{DMIN_CAP}")
    dnoon_cap = load_capture(f"{CAP}/{DNOON_CAP}")

    clean_h1c = {f0: h1_cap(clean_cap, orig, seg, f0) for seg, f0 in TONES}
    tgt = {}
    for role, cap in (("dmin", dmin_cap), ("dnoon", dnoon_cap)):
        for seg, f0 in TONES:
            tgt[(role, f0)] = h1_cap(cap, orig, seg, f0) / clean_h1c[f0]

    print("\nCAPTURE OD/clean fundamental ratio (dB) — the bleed-aware anchor targets:")
    print(f"  {'':8s}" + "".join(f"{f0:>9.0f}Hz" for _, f0 in TONES))
    for role in ("dmin", "dnoon"):
        print(f"  {role:8s}" + "".join(f"{20*np.log10(tgt[(role,f0)]):>10.2f}" for _, f0 in TONES))
    print("  (dmin = drive-min = the LINEAR anchor; dnoon = drive-noon = better-conditioned "
          "cross-check, ~0.3 dB clip compression)")

    for tlabel, taper in TAPERS.items():
        print("\n" + "=" * 78)
        print(f"gm SCAN  —  levelTaperExp = {taper}  ({tlabel})")
        print("=" * 78)

        # B=0 clean model render is gm-independent (clean tap upstream of gm): render once.
        clean_m = render_model(CLEAN_CAP, GM_SCAN[len(GM_SCAN) // 2], taper, win, "clean")

        print(f"  {'gm(mS)':>7} | dmin: " + " ".join(f"{int(f0):>6}" for _, f0 in TONES)
              + "  | dnoon: " + " ".join(f"{int(f0):>6}" for _, f0 in TONES))
        print(f"  {'':7} | OD/clean ratio ERROR  model - capture  (dB; 0 = gm matches). Hz across top.")
        errs = {(role, f0): [] for role in ("dmin", "dnoon") for _, f0 in TONES}
        for gm in GM_SCAN:
            dmin_m = render_model(DMIN_CAP, gm, taper, win, "dmin")
            dnoon_m = render_model(DNOON_CAP, gm, taper, win, "dnoon")
            row = []
            for role, m in (("dmin", dmin_m), ("dnoon", dnoon_m)):
                for _, f0 in TONES:
                    err = 20 * np.log10((m[f0] / clean_m[f0]) / tgt[(role, f0)])
                    errs[(role, f0)].append(err)
                    row.append(f"{err:>+7.2f}")
            nt = len(TONES)
            print(f"  {gm*1e3:>7.3f} | " + " ".join(row[:nt]) + " | " + " ".join(row[nt:]))

        print("\n  Per-tone gm where OD/clean ratio error crosses 0 (linear interp on the scan):")
        gmm = np.array(GM_SCAN) * 1e3
        for role in ("dmin", "dnoon"):
            out = []
            for _, f0 in TONES:
                e = np.array(errs[(role, f0)])
                s = np.where(np.sign(e[:-1]) != np.sign(e[1:]))[0]
                if len(s):
                    i = s[0]
                    g = gmm[i] - e[i] * (gmm[i + 1] - gmm[i]) / (e[i + 1] - e[i])
                    out.append(f"{f0:.0f}Hz->{g:.3f}mS")
                else:
                    out.append(f"{f0:.0f}Hz->none[{e.min():+.1f},{e.max():+.1f}]")
            print(f"    {role:6s} " + "  ".join(out))


if __name__ == "__main__":
    main()
