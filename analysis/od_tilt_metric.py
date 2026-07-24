#!/usr/bin/env python3.11
"""A3 metric: the OD-path BASS TILT.

For every valid OD capture, delta = plugin_db - pedal_db per 1/3-oct band
(already gain-matched, so this is pure shape). The A3 signature is a low-vs-mid
TILT: the plugin is bass-heavy below ~60 Hz and mid-light above ~200 Hz.

  tilt = mean(delta over 20-50 Hz) - mean(delta over 202-1613 Hz)

Reported per sweep level, plus a low-band RMS. NO bands are excluded: the 320 Hz
dip in the OD captures was checked and is a REAL notch in the pedal (the
TrebleAttack cancellation notch, -5.5 dB median in base-od rows, 0.00 dB in
clean ones), not a measurement artifact.
"""
import json
import sys

BAD_BANDS = set()


def load(path):
    d = json.load(open(path))
    return d["meta"]["bands"], {c["file"]: c for c in d["captures"]}


def idx(bands, lo, hi):
    return [i for i, b in enumerate(bands) if lo <= b <= hi and b not in BAD_BANDS]


def report(path, label, only_sub=("ref-od", "drive-", "grunt-", "attack-", "blend-")):
    bands, caps = load(path)
    LOW = idx(bands, 20, 50)
    MID = idx(bands, 202, 1613)
    ALLLOW = idx(bands, 20, 160)
    rows = []
    for f, c in sorted(caps.items()):
        if not any(s in f for s in only_sub):
            continue
        if "base-od" not in f and f != "ref-od.wav":
            continue
        for sw, fr in c["fr"].items():
            p, q = fr["plugin_db"], fr["pedal_db"]
            if max(p) < -60 or max(q) < -60:
                continue
            dl = [a - b for a, b in zip(p, q)]
            tilt = sum(dl[i] for i in LOW) / len(LOW) - sum(dl[i] for i in MID) / len(MID)
            lrms = (sum(dl[i] ** 2 for i in ALLLOW) / len(ALLLOW)) ** 0.5
            mrms = (sum(dl[i] ** 2 for i in MID) / len(MID)) ** 0.5
            rows.append((f.replace("_base-od.wav", "").replace(".wav", ""), sw, tilt, lrms, mrms))
    print(f"\n### {label}   ({path})")
    print(f"{'capture':<28}{'sweep':<16}{'tilt dB':>9}{'lowRMS':>9}{'midRMS':>9}")
    for r in rows:
        print(f"{r[0]:<28}{r[1]:<16}{r[2]:9.2f}{r[3]:9.2f}{r[4]:9.2f}")
    n = len(rows)
    print(f"{'MEAN over ' + str(n) + ' rows':<44}{sum(r[2] for r in rows)/n:9.2f}"
          f"{sum(r[3] for r in rows)/n:9.2f}{sum(r[4] for r in rows)/n:9.2f}")
    return sum(r[2] for r in rows) / n, sum(r[3] for r in rows) / n, sum(r[4] for r in rows) / n


if __name__ == "__main__":
    for p in sys.argv[1:]:
        report(p, p.split("/")[-1])
