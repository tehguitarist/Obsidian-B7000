#!/usr/bin/env python3
"""Obsidian-B7000 capture I/O and render argument mapping.

The template scripts (comprehensive_report.py, farina_validate.py, etc.) import from here.

`parse_capture()` implements the EXPLICIT filename grammar defined in
docs/nonlinear-component-modeling.md §4 ("Capture filename grammar") — read that section
alongside this file; the two must stay in sync. Grammar summary:

  Reserved (zero-deviation) filenames:
    bypass.wav, ref-od.wav, ref-clean.wav

  Every other filename = one or more "key-value" deviation tokens joined by "_", ending
  in a REQUIRED "base-od" or "base-clean" token that states which baseline
  (REF-OD / REF-CLEAN) every UNLISTED control sits at. No other implicit state — if a
  control matters for a capture, it has a token. Example:
    lomidfreq-250_lomid-1700_base-clean.wav

  Pot keys  (value = clock code HHMM, 0700=min .. 1700=max, per analyze.py's clock_to_x):
    drive, blend, level, master, bass, treble, lomid, himid
  Switch keys (value = the literal enum label, matching the APVTS StringArray order
  in PluginProcessor.cpp exactly):
    attack      = flat | boost | cut
    grunt       = boost | cut | flat
    lomidfreq   = 250 | 500 | 1k
    himidfreq   = 750 | 1p5k | 3k
  Baseline key (required, last token):
    base        = od | clean      (od => DIST on, clean => DIST off; no separate dist- key)

`CAPTURE_MATRIX_TIER1` / `CAPTURE_MATRIX_TIER2` below are the canonical filename lists —
identical to the tables in the doc. Run `python3 analysis/captures.py` with no captures on
disk yet to self-validate every documented filename parses cleanly; this is the check that
keeps the doc and the parser from silently drifting apart.

You MUST still implement (pedal-specific, not yet done — needs OfflineRender's CLI, which
doesn't exist yet either):
  - render_args(parsed, extra_args=None) -> list of CLI flags for OfflineRender

Already implemented below:
  - parse_capture(filename) -> dict of settings (PedalChain::Params field names)
  - find_captures(directory) -> [(path, parsed_dict), ...]
  - load_capture(path, expect_fs=48000) -> np.float64 mono audio
"""
import os
import re
import glob
from collections import Counter

import numpy as np
from scipy.io import wavfile
from scipy import signal as sps

RENDER_BIN = "build/OfflineRender_artefacts/Release/OfflineRender"
CAPTURE_DIR = "analysis/captures"

# ---- Filename grammar -----------------------------------------------------------------
# Pot token key -> PedalChain::Params field name (src/dsp/PedalChain.h).
_POT_KEYS = {
    "drive": "drive", "blend": "blend", "level": "level", "master": "master",
    "bass": "lo", "treble": "hi", "lomid": "loMid", "himid": "hiMid",
}
# Switch token key -> (Params field, {token value -> enum index}). Index maps must match
# the APVTS juce::StringArray order in PluginProcessor.cpp::createParameterLayout() EXACTLY.
_ATTACK_IDX = {"flat": 0, "boost": 1, "cut": 2}        # StringArray{"Flat","Boost","Cut"}
_GRUNT_IDX = {"boost": 0, "cut": 1, "flat": 2}         # StringArray{"Boost","Cut","Flat"}
_LOMIDFREQ_IDX = {"250": 0, "500": 1, "1k": 2}         # StringArray{"250Hz","500Hz","1kHz"}
_HIMIDFREQ_IDX = {"750": 0, "1p5k": 1, "3k": 2}        # StringArray{"750Hz","1.5kHz","3kHz"}

_TOKEN_RE = re.compile(r"^[a-z0-9]+-[a-z0-9]+$")
_CLOCK_RE = re.compile(r"^(\d{2})(\d{2})$")

# REF-OD baseline (nonlinear-component-modeling.md §4): every pot at noon except Blend
# (full OD / max); Attack Flat; Grunt "mid" physical position = electrical Cut; both
# mid-freq switches at their "up" physical position (500Hz / 1.5kHz); DIST on.
_REF_OD = dict(
    master=0.5, blend=1.0, level=0.5, drive=0.5,
    lo=0.5, loMid=0.5, hiMid=0.5, hi=0.5,
    attackIdx=_ATTACK_IDX["flat"], gruntIdx=_GRUNT_IDX["cut"],
    loMidFreq=_LOMIDFREQ_IDX["500"], hiMidFreq=_HIMIDFREQ_IDX["1p5k"],
    distEngage=True,
)


def _clock_to_x(token):
    m = _CLOCK_RE.match(token)
    if not m:
        raise ValueError(f"'{token}' is not a 4-digit clock code (e.g. 0700, 1200, 1700)")
    h, mm = int(m.group(1)), int(m.group(2))
    if not (7 <= h <= 17 and 0 <= mm <= 59):
        raise ValueError(f"'{token}' out of clock range (hour must be 07..17)")
    return max(0.0, min(1.0, (h + mm / 60.0 - 7.0) / 10.0))


def parse_capture(filename):
    """Parse a capture filename into a dict of PedalChain::Params field values, per the
    explicit grammar in docs/nonlinear-component-modeling.md §4. Raises ValueError with a
    specific reason on anything that doesn't match the documented convention — a capture
    with an unrecognised or ambiguous name should fail loudly here, not silently mis-fit."""
    stem = os.path.splitext(os.path.basename(filename))[0].lower()

    if stem == "bypass":
        return {"bypass": True}
    if stem == "ref-od":
        return dict(_REF_OD, base="od")
    if stem == "ref-clean":
        return dict(_REF_OD, base="clean", distEngage=False)

    tokens = stem.split("_")
    bad = [t for t in tokens if not _TOKEN_RE.match(t)]
    if bad:
        raise ValueError(
            f"{filename}: token(s) {bad} aren't 'key-value' (single hyphen, [a-z0-9]+ "
            f"each side) — see docs/nonlinear-component-modeling.md §4"
        )

    pairs = [t.split("-", 1) for t in tokens]
    dupes = [k for k, n in Counter(k for k, _ in pairs).items() if n > 1]
    if dupes:
        raise ValueError(f"{filename}: key(s) {dupes} given more than once")
    kv = dict(pairs)

    if "base" not in kv:
        raise ValueError(f"{filename}: missing required trailing 'base-od'/'base-clean' token")
    base = kv.pop("base")
    if base not in ("od", "clean"):
        raise ValueError(f"{filename}: base must be 'od' or 'clean', got '{base}'")

    out = dict(_REF_OD, base=base, distEngage=(base == "od"))

    for key, val in kv.items():
        if key in _POT_KEYS:
            out[_POT_KEYS[key]] = _clock_to_x(val)
        elif key == "attack":
            if val not in _ATTACK_IDX:
                raise ValueError(f"{filename}: attack value must be one of {list(_ATTACK_IDX)}")
            out["attackIdx"] = _ATTACK_IDX[val]
        elif key == "grunt":
            if val not in _GRUNT_IDX:
                raise ValueError(f"{filename}: grunt value must be one of {list(_GRUNT_IDX)}")
            out["gruntIdx"] = _GRUNT_IDX[val]
        elif key == "lomidfreq":
            if val not in _LOMIDFREQ_IDX:
                raise ValueError(f"{filename}: lomidfreq value must be one of {list(_LOMIDFREQ_IDX)}")
            out["loMidFreq"] = _LOMIDFREQ_IDX[val]
        elif key == "himidfreq":
            if val not in _HIMIDFREQ_IDX:
                raise ValueError(f"{filename}: himidfreq value must be one of {list(_HIMIDFREQ_IDX)}")
            out["hiMidFreq"] = _HIMIDFREQ_IDX[val]
        else:
            raise ValueError(
                f"{filename}: unknown deviation key '{key}' (no 'dist-' key either — "
                f"DIST state is fully determined by the base-od/base-clean token)"
            )

    return out


# ---- Canonical capture matrix (must match docs/nonlinear-component-modeling.md §4 exactly) ----
CAPTURE_MATRIX_TIER1 = [
    "bypass.wav", "ref-od.wav", "ref-clean.wav",
    "drive-0700_base-od.wav", "drive-0930_base-od.wav",
    "drive-1430_base-od.wav", "drive-1700_base-od.wav",
    "grunt-boost_base-od.wav", "grunt-flat_base-od.wav",
    "attack-boost_base-od.wav", "attack-cut_base-od.wav",
    "bass-0700_base-clean.wav", "bass-1700_base-clean.wav",
    "treble-0700_base-clean.wav", "treble-1700_base-clean.wav",
    "lomid-0700_base-clean.wav", "lomid-1700_base-clean.wav",
    "himid-0700_base-clean.wav", "himid-1700_base-clean.wav",
    "lomidfreq-250_lomid-1700_base-clean.wav", "lomidfreq-1k_lomid-1700_base-clean.wav",
    "himidfreq-750_himid-1700_base-clean.wav", "himidfreq-3k_himid-1700_base-clean.wav",
    "blend-0700_base-od.wav", "blend-1200_base-od.wav",
    "level-0700_base-od.wav", "level-1700_base-od.wav",
    "master-0700_base-clean.wav", "master-1700_base-clean.wav",
]
CAPTURE_MATRIX_TIER2 = [
    "bass-0930_base-clean.wav", "bass-1430_base-clean.wav",
    "treble-0930_base-clean.wav", "treble-1430_base-clean.wav",
    "lomid-0930_base-clean.wav", "lomid-1430_base-clean.wav",
    "himid-0930_base-clean.wav", "himid-1430_base-clean.wav",
    "blend-0930_base-od.wav", "blend-1430_base-od.wav",
    "level-0930_base-od.wav", "level-1430_base-od.wav",
    "master-0930_base-clean.wav", "master-1430_base-clean.wav",
    "lomidfreq-250_lomid-0700_base-clean.wav", "lomidfreq-1k_lomid-0700_base-clean.wav",
    "himidfreq-750_himid-0700_base-clean.wav", "himidfreq-3k_himid-0700_base-clean.wav",
    "drive-1700_grunt-boost_base-od.wav", "drive-1700_attack-boost_base-od.wav",
]
CAPTURE_MATRIX = CAPTURE_MATRIX_TIER1 + CAPTURE_MATRIX_TIER2


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


def _selftest():
    """Parse every filename in the canonical matrix and report PASS/FAIL. Keeps
    parse_capture() and the doc's filename tables from silently drifting apart —
    run this after editing either."""
    ok = 0
    for name in CAPTURE_MATRIX:
        try:
            parse_capture(name)
            ok += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"{ok}/{len(CAPTURE_MATRIX)} matrix filenames parse cleanly "
          f"({len(CAPTURE_MATRIX_TIER1)} tier-1 + {len(CAPTURE_MATRIX_TIER2)} tier-2).")
    return ok == len(CAPTURE_MATRIX)


if __name__ == "__main__":
    caps = find_captures()
    if caps:
        print(f"{len(caps)} captures in {CAPTURE_DIR}/")
        for path, d in caps:
            print(f"  {os.path.basename(path)}  ->  {d}")
    else:
        print(f"No captures in {CAPTURE_DIR}/ yet — self-validating the documented matrix instead.\n")
        _selftest()
