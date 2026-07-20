#!/usr/bin/env python3
"""Pedal-specific capture I/O and render argument mapping.

Replace this file with your pedal's implementation. The template scripts
(comprehensive_report.py, farina_validate.py, etc.) import from here.

You MUST implement:
  - find_captures(directory) -> [(path, parsed_dict), ...]
  - load_capture(path, expect_fs=48000) -> np.float64 mono audio
  - render_args(parsed, extra_args=None) -> list of CLI flags for OfflineRender

You MAY override:
  - RENDER_BIN (str) -- path to your OfflineRender binary
  - parse_capture(filename) -> dict of settings
"""
import os
import glob

import numpy as np
from scipy.io import wavfile
from scipy import signal as sps

RENDER_BIN = "build/OfflineRender_artefacts/Release/OfflineRender"
CAPTURE_DIR = "analysis/captures"


def parse_capture(filename):
    """Parse YOUR capture filenames into a dict of settings.

    The template provides analyze.parse_filename() for the clock-HHMM
    and 0-10 scale conventions. Use it or write your own parser here.

    Example return: {"rev": "V1", "drive": 0.5, "tone": 0.7}
    """
    raise NotImplementedError(
        "Implement parse_capture() for your pedal's filename convention"
    )


def find_captures(directory=CAPTURE_DIR):
    """Return sorted [(path, parsed_dict), ...] for every .wav under directory."""
    if not os.path.isdir(directory):
        return []
    return [
        (p, parse_capture(p))
        for p in sorted(glob.glob(os.path.join(directory, "*.wav")))
    ]


def load_capture(path, expect_fs=48000):
    """Load a capture as float64 mono at ``expect_fs``.

    Some NAM modelers export 44.1 kHz audio inside a 48 kHz-labeled WAV.
    This function detects the speed error from the cal_1k tone (~1088 Hz
    on a mislabeled file) and resamples back to ``expect_fs``.
    A correctly-labeled file passes through untouched.
    """
    sr, x = wavfile.read(path)
    if x.dtype.kind in "iu":
        x = x.astype(np.float64) / np.iinfo(x.dtype).max
    else:
        x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)

    # Rate-mislabel detection via 1 kHz cal tone
    cal_win = (0.5, 1.45)
    seg = x[int(cal_win[0] * sr) : int(cal_win[1] * sr)]
    if len(seg) > 64:
        w = np.hanning(len(seg))
        mag = np.abs(np.fft.rfft(seg * w))
        peak_hz = np.fft.rfftfreq(len(seg), 1.0 / sr)[int(np.argmax(mag))]
        ratio = peak_hz / 1000.0
    else:
        ratio = 1.0

    _COMMON_RATES = (44100, 48000, 88200, 96000)
    if abs(ratio - 1.0) > 0.005:
        est = sr / ratio
        true_rate = min(_COMMON_RATES, key=lambda r: abs(r - est))
        x = sps.resample_poly(x, expect_fs, true_rate)
    elif sr != expect_fs:
        x = sps.resample_poly(x, expect_fs, sr)

    return np.asarray(x, dtype=np.float64)


def render_args(parsed, extra_args=None):
    """Parsed settings -> flat list of CLI flags for your OfflineRender.

    Example: ["--rev", "V1", "--drive", "0.5000", "--tone", "0.7000"]

    Append extra_args (e.g. calibration overrides such as --sat-*) at the end.
    """
    raise NotImplementedError(
        "Implement render_args() for your pedal's OfflineRender CLI"
    )


if __name__ == "__main__":
    caps = find_captures()
    print(f"{len(caps)} captures in {CAPTURE_DIR}/")
    for path, d in caps:
        print(f"  {os.path.basename(path)}  ->  {d}")
