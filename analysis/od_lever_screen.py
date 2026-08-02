#!/usr/bin/env python3.11
"""Session 109 -- which shipped constant moves GATE Q's OD absolute-error surface, and how?

GATE Q (od_absolute_gate.py) measures the OD path's ABSOLUTE error and splits it into

    L(f)  the error at -30 dBFS      -- a LINEAR element could carry this
    D(f)  error(-6) - error(-30)     -- only a NONLINEARITY can carry this

and Q5/Q6 say D is a SATURATION defect: the model's OD path compresses 1.0-4.2 dB more than the
pedal's over 500 Hz-8 kHz, worst at DRIVE MIN, and its 320 Hz cancellation null washes out with
level (9.6 -> 4.4 dB) where the pedal's deepens (6.0 -> 8.1).

This screen does NOT reason about which element that implicates.  It renders each candidate
perturbation over GATE Q's own scored endpoints and MEASURES the resulting change in the surface,
so the lever is selected by its SHAPE against the target rather than by a mechanism argument.
`localise-before-fitting-a-constant`.

Each row prints, per candidate:
    score      GATE Q's rms |model - pedal| (the thing to minimise)
    dL, dD     how much of the LINEAR / LEVEL-DEPENDENT half it moved, rms
    cos L/D    the cosine between what it moved and what needs moving -- a lever that is large
               but points the wrong way is worse than useless, and a raw score cannot say which
    excess@drv the excess compression per DRIVE setting (Q5's column), which is what separates a
               pre-DRIVE stage from the clipper

Run:
    python3.11 analysis/od_lever_screen.py                       # the default lever list
    python3.11 analysis/od_lever_screen.py --only clipSat,jfetCeil
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import od_absolute_gate as Q          # noqa: E402

PY = "/opt/homebrew/bin/python3.11"
SCRATCH = "analysis/reports/s109_screen"

# GATE Q's scored endpoints, as --only substrings.  Kept explicit rather than derived so the render
# set is visible in the command that produces the artefact.
ONLY = ("drive-0700_level-1700,drive-1700_level-1700,level-1700_attack,"
        "level-1700_grunt,level-1700_base-od")

# Candidate levers.  Each is a NAME -> list of (label, [fit overrides]).  The two saturation
# ceilings are scaled as PAIRS because their ratio is the fitted asymmetry (the even-order
# structure reference-sources.md §4 governs) and scaling one alone would move that too.
SHIP = {"clipSatLo": 0.4377, "clipSatHi": 0.59791, "clipA0": 24.871, "clipK": 2.4653,
        "jfetCeilPos": 2.0111, "jfetCeilNeg": 0.65743, "jfetExpandBeta": 0.46279,
        "railPos": 2.7, "railNeg": 2.9, "jfetGm": 0.10e-3, "jfetRo": 200.0e3}


def levers():
    L = {}
    for k in (1.5, 2.0, 3.0, 5.0):
        L[f"clipSat x{k}"] = [f"clipSatLo={SHIP['clipSatLo'] * k:.6g}",
                              f"clipSatHi={SHIP['clipSatHi'] * k:.6g}"]
    for k in (1.5, 2.5, 4.0):
        L[f"jfetCeil x{k}"] = [f"jfetCeilPos={SHIP['jfetCeilPos'] * k:.6g}",
                               f"jfetCeilNeg={SHIP['jfetCeilNeg'] * k:.6g}"]
    for k in (1.5, 2.5):
        L[f"rail x{k}"] = [f"railPos={SHIP['railPos'] * k:.6g}",
                           f"railNeg={SHIP['railNeg'] * k:.6g}"]
    for v in (15.0, 40.0):
        L[f"clipA0 {v}"] = [f"clipA0={v}"]
    for v in (1.6, 4.0):
        L[f"clipK {v}"] = [f"clipK={v}"]
    for v in (0.2, 0.8):
        L[f"jfetExpandBeta {v}"] = [f"jfetExpandBeta={v}"]
    # kInputRef (K) is NOT a FitParams field -- it lives in GainStaging.h by design, because it is
    # a DAW-domain scalar and the chain must stay chain-domain.  It reaches the render through
    # `--render-arg`.  It is the only knob that moves EVERY nonlinear operating point at once (the
    # CD4049 ceiling, both J201 ceilings, the TL07x rails and the D1/D2 window) while cancelling
    # exactly in the linear path -- `outputGain = makeup/K` compensates it, so a DIST-off clean
    # render is bit-identical across K (measured: 1.1e-08 over a 2x change).  That is precisely
    # what "the OD path saturates too early" needs and no single ceiling can give.
    for v in (0.45, 0.63, 0.80, 0.90, 1.00, 1.10):
        L[f"kInputRef {v}"] = [("raw", f"--input-ref {v}")]
    return L


def render(tag, fits, jobs):
    out = f"{SCRATCH}/{tag}.json"
    if os.path.exists(out):
        return out
    os.makedirs(SCRATCH, exist_ok=True)
    cmd = [PY, "-u", "analysis/comprehensive_report.py", "--only", ONLY,
           "--out", out, "-j", str(jobs)]
    for f in fits:
        # A lever is either a FitParams assignment (a plain "k=v" string) or a raw OfflineRender
        # flag, tagged ("raw", "--flag value").  The raw form exists for kInputRef, which is not a
        # FitParams field; --render-arg takes the whole flag+value as ONE quoted argument because
        # argparse would otherwise swallow the leading "--" as an option of its own.
        cmd += ["--render-arg", f[1]] if isinstance(f, tuple) else ["--fit", f]
    # argv printed, not just the joined string: `zsh-does-not-word-split` has cost this project
    # five sessions, and a --fit list arriving as ONE argv is invisible in a joined echo.
    print(f"   [{len(cmd)} argv] {' '.join(cmd[-2 * len(fits):]) if fits else '(baseline)'}",
          flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        sys.exit(f"render failed for {tag}: rc={r.returncode}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return out


def read(path):
    _b, caps, absfr, nonhf, fb, files, drops = Q.load_surface(path)
    keep = [f for f in files if all((f, s) not in drops for s in Q.STIM_DB)]
    Elo = Q.od_error(absfr, keep, nonhf, Q.LO, drops).mean(axis=0)
    Ehi = Q.od_error(absfr, keep, nonhf, Q.HI, drops).mean(axis=0)
    total, per, _ = Q.score(absfr, files, nonhf, drops)
    band = np.array([500.0 <= f < Q.HF_HZ for f in fb])
    ex = {}
    for drv in sorted({caps[f]["settings"]["drive"] for f in keep}):
        fs = [f for f in keep if caps[f]["settings"]["drive"] == drv]
        mc = (np.mean([absfr[(f, Q.HI)][0][nonhf] for f in fs], axis=0) - Q.STIM_DB[Q.HI]) - \
             (np.mean([absfr[(f, Q.LO)][0][nonhf] for f in fs], axis=0) - Q.STIM_DB[Q.LO])
        pc = (np.mean([absfr[(f, Q.HI)][1][nonhf] for f in fs], axis=0) - Q.STIM_DB[Q.HI]) - \
             (np.mean([absfr[(f, Q.LO)][1][nonhf] for f in fs], axis=0) - Q.STIM_DB[Q.LO])
        ex[drv] = float(np.mean((mc - pc)[band]))
    return {"fb": fb, "L": Elo, "D": Ehi - Elo, "score": total, "per": per, "excess": ex,
            "n_keep": len(keep)}


def cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 1e-12 and nb > 1e-12 else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=None, help="comma-separated lever-name substrings")
    ap.add_argument("--jobs", "-j", type=int, default=8)
    ap.add_argument("--json", default="analysis/reports/s109_lever_screen.json")
    a = ap.parse_args()

    print("-- baseline (shipped defaults) --")
    base = read(render("base", [], a.jobs))
    print(f"   score {base['score']:.3f}   |L| rms {np.sqrt(np.mean(base['L'] ** 2)):.2f}   "
          f"|D| rms {np.sqrt(np.mean(base['D'] ** 2)):.2f}   n={base['n_keep']}")
    print(f"   excess compression by DRIVE: " +
          ", ".join(f"{k}: {v:+.2f}" for k, v in sorted(base['excess'].items())))

    # The target is the NEGATIVE of the current error: what the model must move by to land on the
    # pedal.  A lever is good if it moves the surface ALONG that direction, not merely a lot.
    tgtL, tgtD = -base["L"], -base["D"]

    L = levers()
    if a.only:
        pats = [p.strip() for p in a.only.split(",")]
        L = {k: v for k, v in L.items() if any(p in k for p in pats)}

    print(f"\n-- screening {len(L)} candidate perturbations over {base['n_keep']} endpoints --")
    print(f"\n   {'lever':<22}{'score':>8}{'d score':>9}{'|dL|':>7}{'cos L':>7}{'|dD|':>7}"
          f"{'cos D':>7}   excess@drv 0.0/0.5/1.0")
    print(f"   {'(shipped)':<22}{base['score']:>8.3f}{0.0:>9.3f}{'-':>7}{'-':>7}{'-':>7}{'-':>7}"
          f"   " + " / ".join(f"{base['excess'][d]:+.2f}" for d in sorted(base['excess'])))
    rows = {}
    for name, fits in L.items():
        tag = name.replace(" ", "_").replace(".", "p")
        r = read(render(tag, fits, a.jobs))
        dL, dD = r["L"] - base["L"], r["D"] - base["D"]
        rows[name] = {"fits": fits, "score": r["score"], "dscore": r["score"] - base["score"],
                      "dL_rms": float(np.sqrt(np.mean(dL ** 2))), "cosL": cos(dL, tgtL),
                      "dD_rms": float(np.sqrt(np.mean(dD ** 2))), "cosD": cos(dD, tgtD),
                      "excess": r["excess"]}
        print(f"   {name:<22}{r['score']:>8.3f}{r['score'] - base['score']:>9.3f}"
              f"{rows[name]['dL_rms']:>7.2f}{rows[name]['cosL']:>7.2f}"
              f"{rows[name]['dD_rms']:>7.2f}{rows[name]['cosD']:>7.2f}"
              f"   " + " / ".join(f"{r['excess'][d]:+.2f}" for d in sorted(r["excess"])),
              flush=True)

    best = min(rows, key=lambda k: rows[k]["score"])
    print(f"\n   best single perturbation: {best}  score {base['score']:.3f} -> "
          f"{rows[best]['score']:.3f}")
    print( "   ⚠ a single-perturbation ranking is a SCREEN, not a fit: the levers interact, and a")
    print( "     large |d| with a low cos is a lever pointing the wrong way.  Read the cosines.")
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump({"base": {"score": base["score"], "excess": base["excess"],
                            "L": [float(x) for x in base["L"]],
                            "D": [float(x) for x in base["D"]],
                            "fb": [float(x) for x in base["fb"]]},
                   "levers": rows}, fh, indent=1, default=float)
    print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
