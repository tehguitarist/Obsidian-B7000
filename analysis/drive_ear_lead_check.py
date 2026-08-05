#!/usr/bin/env python3.11
"""Task F (session 160, item 11) -- is the session-120 "DRIVE/distortion" ear-matched lead still
true on the current build?

The lead, verbatim from CLAUDE.md's carry-forwards: "plugin needs ~=0.8 to match the [ND capture]'s
distortion at DRIVE max; tracks closely at DRIVE~=0.5." It was volunteered ahead of losing pedal
access, never measured, and its own follow-up cited a dead pointer ("open work item 11" -- a
retired ~90-session-old numbering scheme). This is the first measurement against it.

Method: take `drive-1700_base-od.wav`'s own settings (DRIVE=1.0, everything else nominal, BLEND=1.0
i.e. bleed-free -- captures.parse_capture, not retyped) and render the CURRENT build twice: once at
DRIVE=1.0 (a control -- this must reproduce whatever the matrix already reports for this capture)
and once at DRIVE=0.8 (the ear's claim). Compare EACH render's per-tone harmonic content against the
ND CAPTURE at the embedded discrete tones (gen_test_signal.TONE_FREQS), same estimator as
clean_thd_check.py / clean_headroom_probe.py so the numbers are directly comparable to prior work.
No new capture needed -- there is no ND capture AT drive=0.8, so the test is necessarily "which
model render sits closer to the ND drive=1.0 capture", not a three-way match.

Also prints the s128-corrected GATE Z direction (model UNDER-distorts at drive-max/hot-stimulus) as
an explicit tension check -- that finding points the OPPOSITE way from "needs LESS drive to match",
so this script does not assume the two agree.

Read-only: renders only, no src/ change, no capture write.
Run: /opt/homebrew/bin/python3.11 analysis/drive_ear_lead_check.py
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.io import wavfile
import analyze as A
import captures as C
import gen_test_signal as G

FS = A.FS
BIN = C.RENDER_BIN
CAP_DIR = "analysis/captures"
NYQ = FS / 2.0
MARGIN = 0.95

CAPTURE = "drive-1700_base-od.wav"      # DRIVE=1.0, BLEND=1.0 (bleed-free), everything else flat
EAR_DRIVE = 0.8                          # the ear's claimed match point
TONES = list(G.TONE_FREQS)               # (82.41, 110, 220, 440, 1000, 2000, 4000, 8000)
_TIMES = G.segment_times()


def load(path):
    fs, x = wavfile.read(path)
    if x.dtype.kind == "i":
        x = x.astype(np.float64) / np.iinfo(x.dtype).max
    else:
        x = x.astype(np.float64)
    return fs, (x[:, 0] if x.ndim > 1 else x)


def seg(path, name):
    fs, x = load(path)
    t0, t1 = _TIMES[name]
    return x[int(t0 * fs):int(t1 * fs)]


def harmonics_db(x, f0, max_order=6):
    """Per-harmonic level re fundamental (dB), Nyquist-guarded, near-bin-peak amplitude.
    Same estimator as clean_thd_check.py / clean_headroom_probe.py -- numbers compare directly."""
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


def render(parsed, out_path):
    args = [BIN, "analysis/test_signal_48k.wav", out_path, "--os", "8"] + C.render_args(parsed)
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"OfflineRender rc={r.returncode}\n{r.stderr}")


def main():
    parsed = C.parse_capture(CAPTURE)
    if parsed.get("drive") != 1.0:
        raise RuntimeError(f"{CAPTURE} does not parse to drive=1.0 (got {parsed.get('drive')}) -- "
                            f"the whole comparison rests on this being the DRIVE-max capture")

    print("=" * 94)
    print("TASK F -- session-120 DRIVE/distortion ear-lead vs. the current build")
    print("=" * 94)
    print(f"reference: {CAPTURE}  (settings: {parsed})")

    pedal_path = os.path.join(CAP_DIR, CAPTURE)
    if not os.path.exists(pedal_path):
        raise RuntimeError(f"missing capture: {pedal_path}")

    render(parsed, "/tmp/f_drive_100.wav")
    p08 = dict(parsed, drive=EAR_DRIVE)
    render(p08, "/tmp/f_drive_080.wav")

    print(f"\n{'tone':>8s}  {'pedal H2':>9s} {'H3':>7s} {'H4':>7s} {'THD%':>7s} |"
          f"  {'m@1.0 H2':>9s} {'H3':>7s} {'H4':>7s} {'THD%':>7s} |"
          f"  {'m@0.8 H2':>9s} {'H3':>7s} {'H4':>7s} {'THD%':>7s} |  closer to pedal")

    rows = []
    for f0 in TONES:
        if f0 * 2 > NYQ * MARGIN:
            continue
        seg_name = f"tone_{f0:g}"
        if seg_name not in _TIMES:
            continue
        pedal_x = seg(pedal_path, seg_name)
        m10_x = seg("/tmp/f_drive_100.wav", seg_name)
        m08_x = seg("/tmp/f_drive_080.wav", seg_name)

        p_h, p_thd = harmonics_db(pedal_x, f0)
        m10_h, m10_thd = harmonics_db(m10_x, f0)
        m08_h, m08_thd = harmonics_db(m08_x, f0)

        def fmt(h, thd):
            return f"{h.get(2, float('nan')):9.2f} {h.get(3, float('nan')):7.2f} " \
                   f"{h.get(4, float('nan')):7.2f} {thd:7.4f}"

        err10 = abs(m10_thd - p_thd)
        err08 = abs(m08_thd - p_thd)
        closer = "0.8" if err08 < err10 else "1.0" if err10 < err08 else "tie"
        rows.append((f0, err10, err08, closer))

        print(f"{f0:8.2f}  {fmt(p_h, p_thd)} |  {fmt(m10_h, m10_thd)} |  "
              f"{fmt(m08_h, m08_thd)} |  {closer}")

    n08 = sum(1 for r in rows if r[3] == "0.8")
    n10 = sum(1 for r in rows if r[3] == "1.0")
    n = len(rows)
    print(f"\n=> DRIVE=0.8 closer to the pedal on {n08}/{n} tones; DRIVE=1.0 closer on {n10}/{n}")
    print( "   (a 'tie' means neither -- excluded from both counts, so n08+n10 may be < n)")
    if n08 > n:
        raise RuntimeError("count exceeds n -- bug in the tally")

    print("\n" + "-" * 94)
    print("TENSION CHECK -- s128's corrected GATE Z direction (not assumed, stated for the reader):")
    print("  GATE Z found the model UNDER-distorts at DRIVE-max x hot stimulus (model THD < ND's),")
    print("  which is the OPPOSITE direction from 'plugin needs LESS drive to match'. If this probe")
    print("  agrees with the ear (0.8 closer), the two are measuring DIFFERENT things (perceived")
    print("  saturation character vs. raw THD%) -- not a contradiction, but worth stating plainly")
    print("  rather than reconciling by assumption.")
    print("=" * 94)


if __name__ == "__main__":
    main()
