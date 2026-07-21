#!/usr/bin/env python3
"""OfflineRender smoke check — prove the CLI->DSP mapping before trusting any fit.

Run:  /opt/homebrew/bin/python3.11 analysis/render_smoke_check.py

This is NOT a fit and NOT a ctest gate. It answers one question: does OfflineRender
actually do what its flags say? A render that runs, produces finite audio, and
silently mis-maps a knob is the failure mode that Phase-7 calibration cannot detect
on its own — every fit downstream would just absorb the error into a constant.

Four checks, in order of how badly a failure would poison the calibration:

  1. EQ KNOB DIRECTION (the big one). `PluginProcessor::readParams()` inverts
     lo/loMid/hiMid/hi (`p.lo = 1.0f - knob`) because the stages are boost-at-zero
     while the knob is CW-is-boost. captures.py emits KNOB space. If OfflineRender
     forgot the inversion, every EQ capture would be fitted against a mirrored
     curve and still look plausible. So: drive a multitone through each EQ band at
     knob 0.0 / 0.5 / 1.0 and assert the band gain rises MONOTONICALLY with the
     knob, i.e. CW = boost, for all four bands.
  2. SWITCH MAPPING. Move each mid-frequency selector and assert the peak actually
     lands near the labelled centre (250/500/1k, 750/1.5k/3k), so a reversed or
     off-by-one choice index can't hide.
  3. BYPASS. `--bypass 1` must reproduce the input exactly (parse_capture on
     bypass.wav yields no other setting, so this path is rendered alone).
  4. ALIGNMENT vs a real capture. Render ref-clean's settings, align() it against
     the reference signal, and confirm the recovered lag equals the oversampler
     latency the render reported — proving the render is uncompensated (trap #3:
     analyze.py::align() does the compensation, not the renderer) and that
     capture-vs-render comparison lines up.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A          # noqa: E402
import captures as C         # noqa: E402

BIN = C.RENDER_BIN
FS = 48000
FAILURES = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        FAILURES.append(msg)


def render(in_wav, out_wav, args):
    cmd = [BIN, in_wav, out_wav] + [str(a) for a in args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"render failed ({r.returncode}): {' '.join(cmd)}\n{r.stderr}")
    return r.stdout


def load(path):
    sr, x = wavfile.read(path)
    assert sr == FS, f"{path}: {sr} Hz"
    if x.dtype.kind in "iu":
        x = x.astype(np.float64) / np.iinfo(x.dtype).max
    return np.asarray(x, dtype=np.float64)


def goertzel_db(x, f):
    """Magnitude of x at f, in dB. Windowed FFT bin sum — robust to phase/latency."""
    w = np.hanning(len(x))
    mag = np.abs(np.fft.rfft(x * w))
    freqs = np.fft.rfftfreq(len(x), 1.0 / FS)
    i = int(np.argmin(np.abs(freqs - f)))
    band = mag[max(0, i - 2):i + 3]
    return 20.0 * np.log10(max(float(band.sum()), 1e-30))


# Band centres: the frequency each EQ knob is expected to move most, at the
# DEFAULT mid-frequency switch positions (loMidFreq=2 -> 1 kHz, hiMidFreq=2 -> 3 kHz).
EQ_BANDS = {"--lo": 60.0, "--lo-mid": 1000.0, "--hi-mid": 3000.0, "--hi": 8000.0}
PROBE_TONES = sorted(set(EQ_BANDS.values()) | {250.0, 500.0, 750.0, 1500.0})


def make_probe(path, seconds=2.0, amp=0.02):
    """Low-level multitone: the clean path (DIST off) is fully linear, so a small
    amplitude keeps every stage far from its (currently disabled) rails and the
    measured band gains are pure linear transfer."""
    n = int(seconds * FS)
    t = np.arange(n) / FS
    x = np.zeros(n)
    for f in PROBE_TONES:
        x += np.sin(2 * np.pi * f * t)
    x *= amp
    fade = int(0.05 * FS)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    wavfile.write(path, FS, x.astype(np.float32))


def steady(x):
    """Middle 50% of a probe render — past the fade-in and any settling."""
    a, b = int(0.4 * len(x)), int(0.9 * len(x))
    return x[a:b]


CLEAN_BASE = ["--dist-engage", 0, "--os", 2, "--blend", 1.0,
              "--master", 0.5, "--level", 0.5, "--drive", 0.5]


def main():
    if not os.path.isfile(BIN):
        sys.exit(f"OfflineRender not found at {BIN} — cmake --build build --target OfflineRender")

    tmp = tempfile.mkdtemp(prefix="b7k_smoke_")
    probe = os.path.join(tmp, "probe.wav")
    make_probe(probe)

    # ---- 1. EQ knob direction -------------------------------------------------
    print("\n1. EQ knob direction (CW must boost — the readParams() 1-x inversion)")
    for flag, fc in EQ_BANDS.items():
        levels = []
        for knob in (0.0, 0.5, 1.0):
            out = os.path.join(tmp, f"eq{flag.strip('-')}{knob}.wav")
            render(probe, out, CLEAN_BASE + [flag, knob])
            levels.append(goertzel_db(steady(load(out)), fc))
        ccw, mid, cw = levels
        print(f"   {flag:10s} @ {fc:6.0f} Hz:  CCW {ccw:7.2f}  noon {mid:7.2f}  CW {cw:7.2f} dB")
        check(cw > mid > ccw,
              f"{flag} monotonic CW=boost at {fc:.0f} Hz "
              f"(got CCW={ccw:.2f} noon={mid:.2f} CW={cw:.2f} dB)")
        check(cw - ccw > 6.0,
              f"{flag} full-range span > 6 dB at {fc:.0f} Hz (got {cw - ccw:.2f} dB)")

    # ---- 2. Mid-frequency switch mapping -------------------------------------
    print("\n2. Mid-frequency selector mapping (boosted peak lands on the label)")
    for flag, knob, labels in (("--lo-mid-freq", "--lo-mid", {0: 250.0, 1: 500.0, 2: 1000.0}),
                               ("--hi-mid-freq", "--hi-mid", {0: 750.0, 1: 1500.0, 2: 3000.0})):
        for idx, target in labels.items():
            out = os.path.join(tmp, f"sw{flag.strip('-')}{idx}.wav")
            render(probe, out, CLEAN_BASE + [flag, idx, knob, 1.0])
            flat = os.path.join(tmp, f"sw{flag.strip('-')}{idx}_flat.wav")
            render(probe, flat, CLEAN_BASE + [flag, idx, knob, 0.5])
            boosted, ref = steady(load(out)), steady(load(flat))
            # Which probe tone gained the most when this band was boosted?
            gains = {f: goertzel_db(boosted, f) - goertzel_db(ref, f) for f in PROBE_TONES}
            peak_f = max(gains, key=gains.get)
            print(f"   {flag}={idx} (label {target:6.0f} Hz): peak tone {peak_f:6.0f} Hz "
                  f"(+{gains[peak_f]:.2f} dB)")
            check(peak_f == target,
                  f"{flag}={idx} peaks at its labelled {target:.0f} Hz (got {peak_f:.0f} Hz)")

    # ---- 3. Bypass ------------------------------------------------------------
    # A bypassed render is the input DELAYED by the oversampler's FIR latency, not
    # a bit-copy: the plugin delay-compensates its dry path so the bypassed output
    # matches the latency it reports to the host for PDC (architecture.md
    # "Bypass" / dsp.md "Dry/wet phase alignment"). Compare against that shift —
    # requiring a zero-lag copy here would be asserting the wrong behaviour.
    print("\n3. Bypass (bypass.wav parses to {'bypass': True} and nothing else)")
    out = os.path.join(tmp, "bypass.wav")
    stdout = render(probe, out, ["--bypass", 1])
    lat = int(stdout.split("latency=")[1].split(",")[0])
    src, got = load(probe), load(out)
    err = float(np.max(np.abs(got[lat:] - src[:len(src) - lat])))
    print(f"   max |bypass_render(delayed {lat}) - input| = {err:.3e}")
    check(err < 1e-6, f"bypass render reproduces the input, delayed by the reported {lat}-sample latency")

    # ---- 4. Alignment against a real capture ---------------------------------
    print("\n4. ref-clean settings: full render, alignment vs the capture")
    cap_path = os.path.join(C.CAPTURE_DIR, "ref-clean.wav")
    if not os.path.isfile(cap_path):
        print("   (skipped — analysis/captures/ref-clean.wav not on disk)")
    else:
        parsed = C.parse_capture(cap_path)
        args = C.render_args(parsed)
        out = os.path.join(tmp, "ref-clean_render.wav")
        stdout = render(A.ORIG, out, ["--os", 8] + args)
        print("   " + stdout.strip())
        latency = int(stdout.split("latency=")[1].split(",")[0])

        ren = load(out)
        orig = A.load(A.ORIG)
        cap = C.load_capture(cap_path)
        check(np.all(np.isfinite(ren)), "render is finite everywhere")
        check(len(ren) == len(orig), "render length matches the reference signal")

        aligned, lag = A.align(ren, orig)
        print(f"   align(render, orig): lag = {lag} samples (render reported latency={latency})")
        check(lag == latency,
              f"recovered lag == the OS latency the render reported "
              f"(uncompensated render + align() = exactly one compensation)")

        _, cap_lag = A.align(cap, orig)
        print(f"   align(capture, orig): lag = {cap_lag} samples")
        # Level/shape are NOT asserted here — they are what Phase-7 calibration is
        # for, and the fit constants are still nominal. Reported for context only.
        a, b = A.T["sweep_clean"]
        seg = slice(int(a * FS), int(b * FS))
        cap_al, _ = A.align(cap, orig)
        print(f"   sweep_clean RMS: render {A.rms_db(aligned[seg]):7.2f} dB   "
              f"capture {A.rms_db(cap_al[seg]):7.2f} dB   "
              f"(difference is the un-calibrated gain staging — Phase 7's job)")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("All OfflineRender smoke checks PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
