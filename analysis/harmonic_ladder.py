#!/usr/bin/env python3.11
"""harmonic_ladder — OUR plugin's H2..H5 ladder vs BOTH reference columns (HW and ND).

WHY (session 71 next-step (a); `.claude/rules/reference-sources.md` §4)
-----------------------------------------------------------------------
The third-party hardware-vs-NeuralDSP measurement set says that at mid drive the ODD orders
match to the dB while the EVENS are offset 27-28 dB, with hardware's evens sitting at the level
of its adjacent odds (H2 = H3, H4 = H5):

                    low drive  HW / ND        mid drive  HW / ND
        H2            -22.5   / -42             -12   / -39
        H3            -41     / -42             -12   / -12
        H4            -60.5   / -57             -24   / -52
        H5            -75.5   / -71             -24   / -24        (re fundamental, dB)

`analysis/captures/` IS the ND column. So every even-order fit this project has ever made
(sessions 5-7's even-harmonic ladder, session 44's fitted asymmetry) was aimed at a target
~27 dB low, while the odd-order work (session 13's phase analysis, session 15's
`jfetExpandBeta`) was aimed at a correct one. The one question that decides what to do next:

    ** did we INHERIT ND's symmetry, or does our fitted asymmetry already land between them? **

It needs no new captures and nothing in `src/`. This tool answers it.

THE ANCHORING PROBLEM, AND HOW IT IS SOLVED
-------------------------------------------
The source states no drive setting, no input level and no blend/level condition behind those
numbers -- so "low drive" and "mid drive" are not settings we can dial. Two unknowns, and
guessing either one would let us report whatever we liked.

** The fix is to anchor on the ODD harmonics, which is exactly where the two references AGREE. **
H3/H1 rises monotonically with drive, so instead of guessing a knob we DEFINE:

        "low drive"  == the operating point where our H3/H1 == -41 dB   (both columns agree)
        "mid drive"  == the operating point where our H3/H1 == -12 dB   (both columns agree)

and then READ our H2/H4/H5 there. The comparison becomes a statement about the SHAPE of the
ladder at a matched odd-order reference, not about a knob position -- which is the only claim
the source's own data can support.

That anchoring is only well-posed if H2 is a function of H3 alone (i.e. every (level, drive)
cell reaching a given H3 reports the same H2). GATE 5 TESTS EXACTLY THAT, over a 2-D grid of
input level x drive knob, and prints the spread. If the cells do not collapse onto one curve
the anchor is ambiguous and the tool says so instead of quoting a number.

TONE FREQUENCY IS NOT A DETAIL -- the two reference columns were measured at DIFFERENT tones
(HW at 997 Hz, ND at 800 Hz), and this chain ends in two Sallen-Key low-passes at ~10.7 kHz and
~3.3 kHz. At 997 Hz the 4th harmonic lands at 3988 Hz; at 800 Hz it lands at 3200 Hz -- several
dB further down the same skirt. So we measure at BOTH tones and compare each against its own
column, and we additionally measure the chain's own LINEAR gain at 2f..5f (quiet tones, same
instrument) so the filtering can be removed and the two columns put on one axis. Nothing is
assumed about the filter; it is measured through the shipped chain at every drive setting.

CONDITION: LEVEL max / BLEND max => the clean bleed is EXACTLY zero by topology (GATE 0 proves
it from the LevelBlend oracle rather than asserting it), so every harmonic ratio here is the OD
path's own and carries no dilution term. EQ flat, ATTACK flat, GRUNT flat, MASTER max --
matching the source's stated "ATTACK and GRUNT flat".

WHAT THIS TOOL CANNOT DO
------------------------
  * It cannot validate the reference numbers. They are chart reads with no underlying data.
    Per `reference-sources.md` §5, use them for SIGN and ORDER OF MAGNITUDE.
  * It cannot say what input level the references used, so the ABSOLUTE drive knob position at
    each anchor is ours, not theirs. Only the ladder SHAPE transfers.
  * H4/H5 sit deep in the SK skirts at these tones; the de-embedded column is the one to quote
    for cross-tone comparisons, and it inherits the linear-FR probe's own accuracy.

Run:
  /opt/homebrew/bin/python3.11 analysis/harmonic_ladder.py --selftest     # gates only
  /opt/homebrew/bin/python3.11 analysis/harmonic_ladder.py                # full measurement
  /opt/homebrew/bin/python3.11 analysis/harmonic_ladder.py --json OUT.json
"""
import sys, os, json, argparse, subprocess

sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy.io import wavfile

import analyze as A
from captures import RENDER_BIN
from parallel import pmap, race_check, add_jobs_arg
# eq_reference prints its whole diagnostic report at module level (no __main__ guard -- known
# wart, session 56, shared oracle with 7+ importers so it is not fixed here). Swallow it.
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from eq_reference import level_blend_tf
from phase_harmonics import fit_harmonics, harm_db

FS = 48000
NMAX = 8                     # extract to H8; H6+ is reported but heavily filtered at these tones
WORK = "build/harmonic_ladder"

# --- the reference tables (reference-sources.md §4). dB re fundamental. -----------------------
# The source gives three drive settings but only tabulates two; "high drive" has no numbers
# (it is described qualitatively: ND shows dense inharmonic content that reads as aliasing).
REF = {
    "low":  {"tone_hz": {"HW": 997.0, "ND": 800.0},
             "HW": {2: -22.5, 3: -41.0, 4: -60.5, 5: -75.5},
             "ND": {2: -42.0, 3: -42.0, 4: -57.0, 5: -71.0}},
    "mid":  {"tone_hz": {"HW": 997.0, "ND": 800.0},
             "HW": {2: -12.0, 3: -12.0, 4: -24.0, 5: -24.0},
             "ND": {2: -39.0, 3: -12.0, 4: -52.0, 5: -24.0}},
}

# --- stimulus ---------------------------------------------------------------------------------
TONES_HZ = (997.0, 800.0)             # HW's tone and ND's tone
# Extends to -54 dBFS deliberately: the LOW-drive anchor (H3 = -41 dB) is only reachable from
# quiet cells, and on the first run it was carried by ONE cell at one input level -- too thin to
# quote. The extra rows give it independent replicates at other levels, which is what GATE 5b
# turns into an uncertainty.
LEVELS_DB = (-54, -48, -42, -36, -30, -24, -18, -12, -6)
DRIVES = (0.0, 0.15, 0.30, 0.50, 0.70, 0.85, 1.0)
FR_PROBE_DB = -60.0                   # quiet enough that the chain is linear (5 mV at the jack)
TONE_SEC = 0.5
FADE_SEC = 0.010
# ** GUARD IS LOAD-BEARING, not cosmetic. ** The output coupling network (C37/R46, and C36 into
# the MASTER pot) corners at ~0.72 Hz => a ~220 ms time constant, so the envelope transient from
# a loud segment is still decaying well into the next one. At GUARD 0.25 s the 800 Hz/-42 dBFS
# cell -- which happened to follow the file's LOUDEST segment -- read 60 dB more inharmonic
# content than its 997 Hz twin, which was first in the file and followed only silence.
# GATE 4 (duplicate cells in two orders) is what makes this checkable rather than assumed.
GUARD_SEC = 1.0
ANALYSE_FRAC = 0.5                    # middle half of each segment
# Reliability filter for the anchor. Inharmonic (non-harmonic) residual within this of the
# fundamental means aliasing/IMD is comparable to what we are trying to read, so the harmonic
# fit there is not a clean measurement of the ladder. Reported, and its effect shown.
INHARM_MAX_DB = -25.0
# Minimum HW-vs-ND separation for a "position between the references" percentage to mean anything.
MIN_SPAN_DB = 6.0


def _tone(f0, sec, db):
    n = int(round(sec * FS))
    t = np.arange(n) / FS
    x = (10 ** (db / 20.0)) * np.sin(2 * np.pi * f0 * t)
    nf = int(round(FADE_SEC * FS))
    w = 0.5 * (1 - np.cos(np.pi * np.arange(nf) / nf))
    x[:nf] *= w
    x[-nf:] *= w[::-1]
    return x


def build_stimulus(path, guard_sec=None):
    """One WAV holding every (tone, level) cell plus the linear-FR probe tones at 2f..5f.

    Returns {segment_name: (i0, i1)} sample bounds. Bounds are BY CONSTRUCTION -- there is no
    alignment step and none is needed, because the render is `--trim-latency`'d and we only ever
    read the middle half of a segment (the guard is far larger than any residual latency).

    `guard_sec` overrides GUARD_SEC (default = it, so the shipped path is unchanged and a default
    run stays byte-identical). ** It is a parameter because the guard is the one constant in this
    file whose ADEQUACY depends on the candidate being measured, not just on the stimulus: it is
    sized against the output coupling network's ~220 ms settling, and a harder nonlinearity
    responds to that residual transient more strongly. Session 76 found GATE 4 failing at
    clipK >= 4 on exactly the cells session 72 built GATE 4 for, and being able to RAISE the guard
    is what separates "the transient is still in the window" from "the solve is history-dependent"
    -- two very different findings. A gate whose own tuning cannot be varied cannot tell you
    which of those you are looking at. **"""
    segs, bounds, cur = [], {}, 0
    guard = np.zeros(int(round((GUARD_SEC if guard_sec is None else guard_sec) * FS)))

    def add(name, x):
        nonlocal cur
        segs.append(guard); cur += len(guard)
        bounds[name] = (cur, cur + len(x))
        segs.append(x); cur += len(x)

    # EVERY cell appears TWICE, once ascending in level and once descending, so each read has a
    # neighbour of the opposite loudness. GATE 4 requires the two to agree; that is a
    # threshold-free test for contamination from a neighbouring segment, whatever its cause.
    for f0 in TONES_HZ:
        for db in LEVELS_DB:
            add(f"t{f0:g}_{db}", _tone(f0, TONE_SEC, db))
    for f0 in TONES_HZ:
        for db in reversed(LEVELS_DB):
            add(f"t{f0:g}_{db}#b", _tone(f0, TONE_SEC, db))
    # Linear-FR probes: the chain's own gain at each harmonic frequency, measured with the same
    # instrument at a level where nothing in the chain is working. Used to de-embed the SK skirts
    # so the 997 Hz and 800 Hz columns can be compared on one axis.
    for f0 in TONES_HZ:
        for k in (1, 2, 3, 4, 5):
            add(f"fr{f0:g}_h{k}", _tone(f0 * k, TONE_SEC, FR_PROBE_DB))
    segs.append(guard)

    x = np.concatenate(segs)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wavfile.write(path, FS, x.astype(np.float32))
    return bounds


def window(x, bounds, name):
    i0, i1 = bounds[name]
    n = i1 - i0
    m = int(n * (1 - ANALYSE_FRAC) / 2)
    return x[i0 + m: i1 - m]


# --- render -----------------------------------------------------------------------------------
BASE_ARGS = ["--master", "1.0", "--blend", "1.0", "--level", "1.0",
             "--lo", "0.5", "--lo-mid", "0.5", "--hi-mid", "0.5", "--hi", "0.5",
             "--attack", "flat", "--grunt", "flat",
             "--lo-mid-freq", "500", "--hi-mid-freq", "1p5k",
             "--dist-engage", "1", "--bypass", "0"]


def render(inp, out, drive, os_factor=8, fit=()):
    """`fit` is a tuple of "key=value" strings, passed straight through as --fit pairs.

    ** The empty tuple appends NOTHING **, so a default run is byte-for-byte the argv the
    session-72 measurement used -- the A/B and the recorded baseline stay comparable. Every
    candidate's argv is stamped into the JSON (`fit` key) and printed above the tables, because a
    condition that lives only in a shell history is how this project has produced three
    plausible-looking-but-wrong artefacts (rebaseline-all-derived-artefacts, s45 item 7a; the
    missing --grunt flag, s65)."""
    args = [RENDER_BIN, inp, out, "--os", str(os_factor), "--trim-latency",
            "--drive", f"{drive:.6f}"] + BASE_ARGS
    for kv in fit:
        args += ["--fit", kv]
    subprocess.run(args, check=True, capture_output=True)
    return A.load(out)


# --- gates ------------------------------------------------------------------------------------
def gate_extractor():
    """GATE 1/2/3 -- the harmonic extractor, against shapes whose ladders are known in CLOSED FORM.

    A static polynomial y = x + a2 x^2 + a3 x^3 driven by x = A cos(wt) gives exactly
        H1 = A + (3/4) a3 A^3,  H2 = (1/2) a2 A^2,  H3 = (1/4) a3 A^3,  H4 = H5 = 0.
    So the H2/H1 and H3/H1 ratios are analytic and the tool must recover them; and the H4/H5
    floor is a direct read of the extractor's own leakage between harmonics.
    """
    print("=" * 88)
    print("GATE 1 -- extractor vs a CLOSED-FORM polynomial ladder")
    print("=" * 88)
    ok = True
    f0 = 997.0
    n = int(round(TONE_SEC * ANALYSE_FRAC * FS))
    t = np.arange(n) / FS
    for A_amp, a2, a3 in [(0.30, 0.80, 0.50), (0.10, 2.00, 4.00), (0.05, 0.20, 0.05)]:
        x = A_amp * np.cos(2 * np.pi * f0 * t)
        y = x + a2 * x ** 2 + a3 * x ** 3
        H, _, resid = fit_harmonics(y, f0, fs=FS, nmax=NMAX)
        hd = harm_db(H)
        h1 = A_amp + 0.75 * a3 * A_amp ** 3
        want2 = 20 * np.log10(abs(0.5 * a2 * A_amp ** 2) / h1)
        want3 = 20 * np.log10(abs(0.25 * a3 * A_amp ** 3) / h1)
        e2, e3 = abs(hd[2] - want2), abs(hd[3] - want3)
        leak = max(hd[4], hd[5])
        good = e2 < 0.01 and e3 < 0.01 and leak < -100
        ok = ok and good
        print(f"  A={A_amp:.2f} a2={a2:.2f} a3={a3:.2f}:  "
              f"H2 {hd[2]:+7.3f} (want {want2:+7.3f}, err {e2:.4f})  "
              f"H3 {hd[3]:+7.3f} (want {want3:+7.3f}, err {e3:.4f})  "
              f"H4/H5 leak {leak:+7.1f} dB  {'OK' if good else '** FAIL **'}")

    print()
    print("=" * 88)
    print("GATE 2 -- a SYMMETRIC hard clipper must show NO even orders")
    print("=" * 88)
    x = 0.9 * np.cos(2 * np.pi * f0 * t)
    y = np.clip(x, -0.4, 0.4)
    H, _, _ = fit_harmonics(y, f0, fs=FS, nmax=NMAX)
    hd = harm_db(H)
    even_ok = max(hd[2], hd[4]) < -100
    ok = ok and even_ok
    print(f"  symmetric clip:  H2 {hd[2]:+8.1f}  H3 {hd[3]:+7.2f}  H4 {hd[4]:+8.1f}  "
          f"H5 {hd[5]:+7.2f}   {'OK (evens at floor)' if even_ok else '** FAIL **'}")
    # ...and an ASYMMETRIC clip must show them, or the gate above proves nothing.
    y = np.clip(x, -0.25, 0.4)
    H, _, _ = fit_harmonics(y, f0, fs=FS, nmax=NMAX)
    hda = harm_db(H)
    live = hda[2] > -40
    ok = ok and live
    print(f"  asymmetric clip: H2 {hda[2]:+8.2f}  H3 {hda[3]:+7.2f}  H4 {hda[4]:+8.2f}  "
          f"H5 {hda[5]:+7.2f}   {'OK (evens live)' if live else '** FAIL **'}")

    print()
    print("=" * 88)
    print("GATE 3 -- window insensitivity (the read must not depend on where we look)")
    print("=" * 88)
    # ** Must be driven by a shape that makes ALL of H2..H5 genuinely, or the gate is vacuous. **
    # The cubic polynomial above makes H4/H5 only at the numerical floor (~-296 dB), and a
    # floor-level quantity is not window-stable by construction -- my first version of this gate
    # compared those and "failed" at 13 dB while the extractor was perfect. Gate the orders the
    # measurement actually reads, and PRINT which ones, so it cannot quietly go vacuous later.
    xl = 0.9 * np.cos(2 * np.pi * f0 * (np.arange(3 * n) / FS))
    yl = np.clip(xl, -0.25, 0.40)          # asymmetric clip: every order live (GATE 2 proved it)
    FLOOR_DB = -100.0
    refs, spread, checked = None, 0.0, []
    for off, ln in [(0, n), (n // 3, n), (n, n), (n // 2, 2 * n)]:
        H, _, _ = fit_harmonics(yl[off:off + ln], f0, fs=FS, nmax=NMAX)
        hd = harm_db(H)
        if refs is None:
            refs = hd
            checked = [k for k in (2, 3, 4, 5) if hd[k] > FLOOR_DB]
            continue
        for k in checked:
            spread = max(spread, abs(hd[k] - refs[k]))
    win_ok = bool(checked) and len(checked) == 4 and spread < 0.01
    ok = ok and win_ok
    print(f"  orders above the {FLOOR_DB:.0f} dB floor and therefore CHECKED: "
          f"{', '.join('H' + str(k) for k in checked) if checked else 'NONE'}"
          f"{'  (all four -- gate is not vacuous)' if len(checked) == 4 else '  ** too few **'}")
    print(f"  worst |delta| across 4 windows (offset AND length): {spread:.5f} dB   "
          f"{'OK' if win_ok else '** FAIL **'}")
    print()
    return ok


def gate_bleed():
    """GATE 0 -- the render condition really is bleed-free, from the LevelBlend oracle.

    Not asserted from prose: `level_blend_tf(level, blend, vo, vc)` is the same 1-node KCL solve
    `tests/LevelBlendTest.cpp` uses as its oracle. Feed it a UNIT clean input and a ZERO OD input;
    whatever comes out IS the clean bleed coefficient at that knob pair. It must be exactly 0 at
    LEVEL=1/BLEND=1, and (the control that makes that meaningful) NON-zero just below."""
    print("=" * 88)
    print("GATE 0 -- clean-bleed coefficient at the render condition")
    print("=" * 88)
    rows = []
    for lv in (1.0, 0.99, 0.95, 0.90, 0.50):
        c = level_blend_tf(lv, 1.0, vo=0.0, vc=1.0)
        o = level_blend_tf(lv, 1.0, vo=1.0, vc=0.0)
        rows.append((lv, c, o))
        db = "-inf" if c == 0 else f"{20 * np.log10(abs(c)):.2f}"
        print(f"  LEVEL={lv:.2f} BLEND=1.00:  clean coeff {c:.6e} ({db:>8} dB)   OD coeff {o:.6f}")
    at1, od1 = rows[0][1], rows[0][2]
    below = rows[1][1]
    ok = (at1 == 0.0) and (od1 == 1.0) and (below > 0.0)
    print(f"\n  bleed EXACTLY zero at LEVEL=1 and NON-zero at 0.99 (the discriminating control): "
          f"{'OK' if ok else '** FAIL **'}")
    print("  => every Hn/H1 below is the OD path's own ratio, with no dilution term.\n")
    return ok


# --- measurement ------------------------------------------------------------------------------
def _measure_one(d, inp, bounds, os_factor, fit, stem):
    """ONE drive setting: render it and reduce the whole tone/level grid. Unit of parallelism.

    Returns its own (cells, fr) fragments rather than writing into shared dicts, so there is no
    cross-setting state -- the caller merges them.
    """
    out = f"{WORK}/render{stem}_drv{d:.2f}.wav"
    y = render(inp, out, d, os_factor, fit)
    cells, fr = {}, {}
    for f0 in TONES_HZ:
        # linear FR of the whole chain at f0..5*f0, at a level where nothing is working
        g = {}
        for k in (1, 2, 3, 4, 5):
            H, _, _ = fit_harmonics(window(y, bounds, f"fr{f0:g}_h{k}"), f0 * k,
                                    fs=FS, nmax=2)
            g[k] = 20 * np.log10(abs(H[1]) + 1e-30)
        fr[(f0, d)] = g
        for db in LEVELS_DB:
            rd = []
            for tag in ("", "#b"):
                seg = window(y, bounds, f"t{f0:g}_{db}{tag}")
                H, _, resid = fit_harmonics(seg, f0, fs=FS, nmax=NMAX)
                # residual = everything NOT at a harmonic of f0 = inharmonic (aliasing/IMD)
                inh = 20 * np.log10(np.sqrt(np.mean(resid ** 2)) / (abs(H[1]) + 1e-30) + 1e-30)
                rd.append((harm_db(H), float(abs(H[1])), float(inh)))
            (hdA, h1A, inhA), (hdB, _, inhB) = rd
            rep = float(max(abs(hdA[n] - hdB[n]) for n in (2, 3, 4, 5)))
            cells[(f0, db, d)] = dict(hd=[float(v) for v in hdA], h1=h1A,
                                      inharm=max(inhA, inhB), repeat=rep)
    return cells, fr


def measure_all(bounds, os_factor=8, fit=(), stem="", stim=None, jobs=None):
    """Render every drive setting; return cells[(f0, level_db, drive)] and the per-drive linear FR.

    `stem` suffixes the render filenames so concurrent candidates cannot collide. ** It is NOT
    called `tag`: the duplicate-cell loop below rebinds a local `tag` over ("", "#b"), so a
    parameter of that name is silently overwritten after the first drive setting -- which sent
    every later render to one shared `render#b_*.wav` and had 8 parallel workers writing the same
    file. Harmless serially (the array is read straight back from the writer), which is exactly
    why it survived a bit-identical single-process A/B. **

    `stim` is the stimulus WAV to render (default = the shipped shared path, so every existing
    caller is unchanged). ** It exists because `bounds` and the FILE must agree and nothing used to
    enforce it. `build_stimulus(path, guard_sec)` can write any guard to any path, but this function
    always read ONE path, so a sweep that legitimately needs a longer guard (session 76: GATE 4
    fails at clipK >= 4 until the guard reaches 2.5 s) left a 2.5 s stimulus sitting where the next
    default-guard run would silently render it -- guard-1.0 bounds indexing guard-2.5 audio, i.e.
    every window landing in the wrong place. Session 76 caught it and wrote a warning into the
    handover; a warning is not a mechanism. Guard-stamped paths are
    (memory: `rebaseline-all-derived-artefacts`). **"""
    os.makedirs(WORK, exist_ok=True)
    inp = f"{WORK}/stimulus.wav" if stim is None else stim
    # Every drive setting is an independent render + reduction, and the keys it produces
    # ((f0, db, d) and (f0, d)) are DISJOINT across settings -- so running them concurrently and
    # merging is bit-identical, and `pmap` returns them in DRIVES order so the merge is
    # deterministic too. race_check() pins the one way this breaks: two settings resolving to the
    # same render path, which serially is invisible (the array is read straight back from the
    # writer) and concurrently tears the WAV -- exactly the session-73 `stem`/`tag` defect the
    # docstring above describes.
    race_check([f"{WORK}/render{stem}_drv{d:.2f}.wav" for d in DRIVES])
    per_drive = pmap(lambda d: _measure_one(d, inp, bounds, os_factor, fit, stem),
                     DRIVES, jobs=jobs)
    cells, fr = {}, {}
    for c, g in per_drive:
        cells.update(c)
        fr.update(g)
    return cells, fr


def gate_repeat(cells):
    """GATE 4 -- intra-file repeatability. Every cell was rendered TWICE in the same file with
    opposite-loudness neighbours; the two reads must agree. Disagreement = the reading depends on
    what came before it, i.e. a segment-boundary transient is still inside the analysis window."""
    print("=" * 88)
    print("GATE 4 -- duplicate cells (ascending vs descending neighbours) must agree")
    print("=" * 88)
    worst = max(c["repeat"] for c in cells.values())
    bad = [(k, c["repeat"]) for k, c in cells.items() if c["repeat"] > 0.5]
    print(f"  worst |delta| on H2..H5 across the duplicate pair: {worst:.4f} dB over "
          f"{len(cells)} cells")
    if bad:
        for k, v in sorted(bad, key=lambda x: -x[1])[:8]:
            print(f"    CONTAMINATED  tone {k[0]:g}  {k[1]:+d} dBFS  drive {k[2]:.2f}   "
                  f"delta {v:.2f} dB")
    ok = not bad
    print(f"  {'OK -- no cell depends on its neighbour' if ok else '** ' + str(len(bad)) + ' CELLS CONTAMINATED **'}\n")
    return ok


def deembed(hd, g):
    """Remove the chain's own linear gain shape, so Hn is referred to what the nonlinearity made
    rather than to what survived the Sallen-Keys. de[n] = hd[n] - (g[n] - g[1])."""
    return {n: hd[n] - (g[n] - g[1]) for n in (2, 3, 4, 5)}


def usable(cells, f0, db, d):
    return cells[(f0, db, d)]["inharm"] <= INHARM_MAX_DB


def gate_monotone(cells, f0, quiet=False):
    """GATE 5a -- H3 vs drive, per input level.

    The anchor 'the point where H3 = X' only names ONE operating point if H3 rises monotonically
    with drive. It does not everywhere: at hot input levels H3 CRASHES at high drive (an H3
    cancellation null -- the anti-phase interference between the JFET drain-current ceiling and
    the clipper that session 12 established from amplitudes and session 13 confirmed from phase).
    A target crossed on the far side of that null is a completely different operating point, so
    the anchor must take the FIRST UPWARD crossing and the tool must show where the branch ends.
    """
    if not quiet:
        print(f"  {'in dBFS':>8}  " + "".join(f"{d:8.2f}" for d in DRIVES) + "   branch")
    rising = {}
    for db in LEVELS_DB:
        row = [cells[(f0, db, d)]["hd"][3] for d in DRIVES]
        k = len(row)
        for i in range(1, len(row)):
            if row[i] < row[i - 1] - 0.5:
                k = i
                break
        rising[db] = k
        note = "monotone" if k == len(row) else f"rises to drive {DRIVES[k - 1]:.2f}, then FALLS"
        if not quiet:
            print(f"  {db:8d}  " + "".join(f"{v:8.1f}" for v in row) + f"   {note}")
    return rising


def gate_anchor_collapse(cells, f0, rising, quiet=False):
    """GATE 5b -- on the rising branch, is H2 a function of H3 alone?

    The comparison rests on it. Bin the usable (level, drive) cells by H3 and report the spread of
    H2 within each bin. A large spread means 'the operating point where H3 = -12 dB' does not pick
    out ONE H2 and the anchored table is a range, not a value -- which the tool must say, not hide.
    """
    pts = [(cells[(f0, db, d)]["hd"][3], cells[(f0, db, d)]["hd"][2], db, d)
           for db in LEVELS_DB for d in DRIVES[:rising[db]]
           if usable(cells, f0, db, d) and cells[(f0, db, d)]["hd"][3] > -90]
    if not quiet:
        print(f"  H3 bin        n   H2 mean    H2 spread   contributing (level dBFS, drive)")
    worst, at_anchor = 0.0, 0.0
    anchor_bins = {int(np.floor(REF[l]["HW"][3] / 6.0) * 6) for l in ("low", "mid")}
    for lo in range(-84, 6, 6):
        hi = lo + 6
        grp = [p for p in pts if lo <= p[0] < hi]
        if len(grp) < 2:
            continue
        h2 = np.array([p[1] for p in grp])
        spr = float(h2.max() - h2.min())
        worst = max(worst, spr)
        mark = ""
        if lo in anchor_bins:
            at_anchor = max(at_anchor, spr)
            mark = "  <- ANCHOR BIN"
        who = " ".join(f"({p[2]:+d},{p[3]:.2f})" for p in sorted(grp, key=lambda q: q[0])[:5])
        if not quiet:
            print(f"  [{lo:+3d},{hi:+3d})  {len(grp):3d}   {h2.mean():+7.2f}   {spr:8.2f}   {who}{mark}")
    return worst, at_anchor


def anchor(cells, f0, target_h3, rising):
    """The operating point where H3/H1 == target_h3 -- the FIRST UPWARD crossing along the drive
    axis at each input level, restricted to the rising branch and to cells whose inharmonic
    content is under INHARM_MAX_DB."""
    hits = []
    for db in LEVELS_DB:
        seq = [(d, cells[(f0, db, d)]["hd"]) for d in DRIVES[:rising[db]]]
        for (d0, a), (d1, b) in zip(seq, seq[1:]):
            if a[3] <= target_h3 <= b[3] and b[3] > a[3]:
                w = (target_h3 - a[3]) / (b[3] - a[3])
                dd = d0 + w * (d1 - d0)
                if not (usable(cells, f0, db, d0) and usable(cells, f0, db, d1)):
                    break
                hits.append(dict(level_db=db, drive=dd,
                                 hd={n: a[n] + w * (b[n] - a[n]) for n in (2, 3, 4, 5)}))
                break
    return hits


def measure_verdict(cells, quiet=True):
    """The anchored (raw, de-embedded) ladder at both anchors and both tones, WITHOUT printing.

    Factored out of main() so `analysis/jfet_even_screen.py` scores candidates through the IDENTICAL
    anchor logic rather than a copy of it -- the shared-oracle rule (session 62: a fast private copy
    of a shared solve is a silent-divergence trap). main() still owns all the presentation.
    Returns (verdicts, hits_by_key, gate_by_tone)."""
    verdicts, hits_by, gates = {}, {}, {}
    for f0 in TONES_HZ:
        rising = gate_monotone(cells, f0, quiet=True)
        gates[f0] = gate_anchor_collapse(cells, f0, rising, quiet=True)
        for lbl in ("low", "mid"):
            hits = anchor(cells, f0, REF[lbl]["HW"][3], rising)
            hits_by[(f0, lbl)] = hits
            if not hits:
                verdicts[(f0, lbl)] = None
                continue
            verdicts[(f0, lbl)] = {n: (float(np.mean([h["hd"][n] for h in hits])),
                                       float(np.max([h["hd"][n] for h in hits])
                                             - np.min([h["hd"][n] for h in hits])))
                                   for n in (2, 3, 4, 5)}
    return verdicts, hits_by, gates


def pair_rows(verdicts, fr):
    """EVEN-MINUS-ADJACENT-ODD, the file's headline discriminator, computed in exactly ONE place.

    `corr` removes only the filter's SLOPE between two adjacent harmonics (1-3 dB here) rather than
    the chain's whole linear shape, which is large AND known wrong (session 64: our mid scoop is
    ~2x too deep) -- see the note in main(). `pos` is None when the two references separate by less
    than MIN_SPAN_DB, because a percentage through a ~1 dB denominator is not a measurement."""
    rows = []
    for f0 in TONES_HZ:
        g = fr[(f0, DRIVES[0])]
        for lbl in ("low", "mid"):
            v = verdicts.get((f0, lbl))
            if v is None:
                continue
            for a, b in ((2, 3), (4, 5)):
                ours = v[a][0] - v[b][0]
                filt = g[a] - g[b]
                corr = ours - filt
                hw = REF[lbl]["HW"][a] - REF[lbl]["HW"][b]
                nd = REF[lbl]["ND"][a] - REF[lbl]["ND"][b]
                span = hw - nd
                rows.append(dict(tone=f0, drive=lbl, pair=(a, b), ours=ours, filt=filt, corr=corr,
                                 nd=nd, hw=hw, span=span,
                                 pos=((corr - nd) / span * 100.0) if abs(span) >= MIN_SPAN_DB else None))
    return rows


def level_rows(verdicts, fr):
    """THE THIRD DEGREE OF FREEDOM -- the LATE-HARMONIC LEVEL, relative to the anchor.

    WHY THIS EXISTS (session 76).  The anchor pins H3 to the reference's own H3, so against the HW
    column `e[H3] == 0 EXACTLY, by construction` (verified in the printed table, and by GATE 6).
    That leaves the anchored error vector with exactly THREE degrees of freedom -- e2, e4, e5 -- and
    this file reported only TWO contrasts of them:

        H2-H3  = e2          (pair_rows, (2,3))
        H4-H5  = e4 - e5     (pair_rows, (4,5))

    The third, `(e4 + e5)/2`, is the LEVEL of the late pair rather than its spacing, and nothing in
    this project measured it. It is not an extra statistic of convenience: with the two above it
    SPANS the error vector, so anything it carries is invisible to the other two **by construction**
    -- which is what sessions 72-74 kept walking into from different directions (session 74 read its
    common-mode shadow as a "~9 dB deficit"; session 75 withdrew that reading, correctly, but the
    remaining term was never named).  GATE 6 demonstrates the blindness rather than asserting it.

    Correction convention is EXACTLY pair_rows': subtract the chain's own measured linear gain
    DIFFERENCE between the harmonics being compared -- here the late pair against the anchor,
    `(g4+g5)/2 - g3`.  So this inherits the same bound as the pair statistic, not the whole-filter
    error the absolute Hn/H1 carries (the note in main()).  ** And the two tones are the check on
    that bound: their filter terms have OPPOSITE slopes (-1.21 dB/order at 997 Hz, +0.43 at 800),
    so if the correction were not doing its job the two would not agree after it. **"""
    rows = []
    for f0 in TONES_HZ:
        g = fr[(f0, DRIVES[0])]
        for lbl in ("low", "mid"):
            v = verdicts.get((f0, lbl))
            if v is None:
                continue
            ours = (v[4][0] + v[5][0]) / 2.0 - v[3][0]
            filt = (g[4] + g[5]) / 2.0 - g[3]
            corr = ours - filt
            hw = (REF[lbl]["HW"][4] + REF[lbl]["HW"][5]) / 2.0 - REF[lbl]["HW"][3]
            nd = (REF[lbl]["ND"][4] + REF[lbl]["ND"][5]) / 2.0 - REF[lbl]["ND"][3]
            span = hw - nd
            rows.append(dict(tone=f0, drive=lbl, ours=ours, filt=filt, corr=corr, nd=nd, hw=hw,
                             span=span, vs_hw=corr - hw, vs_nd=corr - nd,
                             pos=((corr - nd) / span * 100.0) if abs(span) >= MIN_SPAN_DB else None))
    return rows


def gate_dof():
    """GATE 6 -- the three anchored statistics SPAN the error vector, and each routes to one mode.

    Two claims, both demonstrated on synthetic error vectors rather than argued:

      (a) COMPLETENESS.  With the anchor forcing e3 = 0, the map (e2,e4,e5) -> (H2-H3, H4-H5,
          late level) is linear and invertible, so nothing in the anchored comparison escapes the
          three.  Checked by round-tripping random vectors back through the inverse.
      (b) ROUTING, and this is the load-bearing half.  A pure late-LEVEL error must land entirely
          in the new statistic and read EXACTLY ZERO in both old ones -- i.e. the instrument this
          file had was blind to it by construction, not merely insensitive to it.

    ** A gate that only asserted (a) would pass for a set of three statistics that all mix the
    modes together, which is useless for attributing a residual. (b) is what makes the split mean
    something -- the same reason session 69's coherence gate needed a discriminating PAIR. **"""
    print("=" * 88)
    print("GATE 6 -- the anchored error vector has 3 dof; do the 3 statistics span and separate it?")
    print("=" * 88)

    def stats(e2, e4, e5):
        return e2, e4 - e5, (e4 + e5) / 2.0

    rng = np.random.default_rng(76)
    worst_rt = 0.0
    for _ in range(2000):
        e2, e4, e5 = rng.normal(0, 8, 3)
        s1, s2, s3 = stats(e2, e4, e5)
        # inverse: e2 = s1, e4 = s3 + s2/2, e5 = s3 - s2/2
        worst_rt = max(worst_rt, abs(e2 - s1), abs(e4 - (s3 + s2 / 2)), abs(e5 - (s3 - s2 / 2)))
    print(f"  (a) COMPLETENESS -- worst round-trip error over 2000 random vectors: {worst_rt:.3e} dB")

    modes = [("pure H2-H3   (e2 only)", (7.0, 0.0, 0.0)),
             ("pure H4-H5 spacing   ", (0.0, +3.5, -3.5)),
             ("pure LATE LEVEL      ", (0.0, -12.0, -12.0))]
    print(f"\n  (b) ROUTING    {'mode':<22}  {'H2-H3':>8} {'H4-H5':>8} {'LATE LEV':>9}")
    ok_route = True
    for name, (e2, e4, e5) in modes:
        s1, s2, s3 = stats(e2, e4, e5)
        print(f"                 {name:<22}  {s1:+8.2f} {s2:+8.2f} {s3:+9.2f}")
    s1, s2, s3 = stats(*modes[2][1])
    blind = (abs(s1) < 1e-12) and (abs(s2) < 1e-12) and abs(s3) > 1.0
    if not blind:
        ok_route = False
    print(f"\n  => a pure LATE-LEVEL error of -12.00 dB reads {s1:+.2f} on H2-H3 and {s2:+.2f} on "
          f"H4-H5:")
    print(f"     {'CONFIRMED BLIND -- the two old statistics cannot see this mode at all' if blind else '** ROUTING FAILED **'}")
    ok = (worst_rt < 1e-9) and ok_route
    print(f"\n  GATE 6: {'OK' if ok else '** FAIL **'}\n")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="run the gates only")
    ap.add_argument("--os", type=int, default=8)
    ap.add_argument("--json", default="analysis/reports/s72_harmonic_ladder.json")
    ap.add_argument("--fit", action="append", default=[], metavar="KEY=VALUE",
                    help="repeatable FitParams override, passed through to OfflineRender. "
                         "Omitting it renders the shipped defaults, identically to session 72.")
    ap.add_argument("--tag", default="", help="suffix for this run's render filenames, so a sweep "
                                             "does not overwrite the baseline renders")
    ap.add_argument("--guard", type=float, default=None, metavar="SEC",
                    help=f"override the inter-segment guard (default {GUARD_SEC} s). Raising it is "
                         "the discriminating test when GATE 4 fails: if the contamination clears, "
                         "it was the coupling network's envelope transient; if it does not, the "
                         "reading is history-dependent for some other reason.")
    add_jobs_arg(ap, "The DRIVES renders are independent, so this is a straight "
                     "wall-clock win with identical output.")
    ap.add_argument("--brief", action="store_true",
                    help="skip the per-cell grids and the filter table; print the anchors and the "
                         "verdict only. For sweeps -- the full tables are 130 lines per candidate.")
    args = ap.parse_args()
    fit = tuple(args.fit)
    for kv in fit:
        if "=" not in kv:
            print(f"** --fit expects KEY=VALUE, got {kv!r} **")
            return 2

    g_ok = gate_extractor()
    b_ok = gate_bleed()
    d_ok = gate_dof()
    if not (g_ok and b_ok and d_ok):
        print("** GATES FAILED -- not measuring. **")
        return 1
    if args.selftest:
        print("GATES PASS.")
        return 0

    bounds = build_stimulus(f"{WORK}/stimulus.wav", args.guard)
    print(f"stimulus: {len(bounds)} segments -> {WORK}/stimulus.wav"
          + ("" if args.guard is None else f"   ** GUARD OVERRIDDEN: {args.guard} s **"))
    print(f"rendering {len(DRIVES)} drive settings at OS {args.os} ...")
    # Stamp the condition ABOVE the numbers, always -- including the empty case, so a log cannot be
    # mistaken for the other kind.
    print(f"CONDITION: {'SHIPPED DEFAULTS (no --fit)' if not fit else 'OVERRIDES ' + ' '.join(fit)}\n")
    cells, fr = measure_all(bounds, args.os, fit, args.tag, jobs=args.jobs)
    if not gate_repeat(cells):
        print("** GATE 4 FAILED -- some cells depend on their neighbour. Not reporting. **")
        return 1

    out = dict(drives=list(DRIVES), levels_db=list(LEVELS_DB), tones=list(TONES_HZ),
               fit=list(fit), cells={}, fr={}, anchors={})
    for k, v in cells.items():
        out["cells"][f"{k[0]:g}|{k[1]}|{k[2]:.2f}"] = v
    for k, v in fr.items():
        out["fr"][f"{k[0]:g}|{k[1]:.2f}"] = {str(n): v[n] for n in v}

    # ---- the chain's own linear shape at the harmonic frequencies ----
    print("=" * 88)
    print("THE FILTER TERM -- chain linear gain at 2f..5f re f (measured, drive min .. max)")
    print("=" * 88)
    print("  Why it matters: HW was measured at 997 Hz and ND at 800 Hz, and the 2nd SK low-pass")
    print("  sits at ~3.3 kHz -- so H4 lands at 3988 Hz for HW and 3200 Hz for ND. Part of the")
    print("  HW-vs-ND late-harmonic difference is the TONE, not the device.")
    for f0 in TONES_HZ:
        print(f"\n  tone {f0:g} Hz")
        print(f"    {'drive':>6}  {'2f':>8} {'3f':>8} {'4f':>8} {'5f':>8}   (dB re gain at f)")
        for d in DRIVES:
            g = fr[(f0, d)]
            print(f"    {d:6.2f}  " + " ".join(f"{g[n] - g[1]:+8.2f}" for n in (2, 3, 4, 5)))
    g997 = fr[(997.0, DRIVES[0])]
    g800 = fr[(800.0, DRIVES[0])]
    print("\n  cross-tone penalty (997 minus 800), drive min:  " +
          "  ".join(f"H{n} {(g997[n] - g997[1]) - (g800[n] - g800[1]):+.2f} dB" for n in (2, 3, 4, 5)))
    print("  => a HW-column harmonic is filtered THIS much harder than the same order in the ND")
    print("     column, purely because of the tone frequency. Subtract it before reading the")
    print("     HW-vs-ND H4/H5 gap as a device difference.")

    # ---- the grid ----
    for f0 in TONES_HZ:
        print()
        print("=" * 88)
        print(f"OUR LADDER, tone {f0:g} Hz (LEVEL max / BLEND max => bleed-free; EQ/ATTACK/GRUNT flat)")
        print("=" * 88)
        print(f"  {'drive':>6} {'in dBFS':>8}   {'H2':>7} {'H3':>7} {'H4':>7} {'H5':>7} "
              f"{'H6':>7} {'H7':>7}   {'inharm':>8}")
        for d in DRIVES:
            for db in LEVELS_DB:
                c = cells[(f0, db, d)]
                hd = c["hd"]
                print(f"  {d:6.2f} {db:8d}   " +
                      " ".join(f"{hd[n]:7.1f}" for n in (2, 3, 4, 5, 6, 7)) +
                      f"   {c['inharm']:8.1f}")

    # ---- GATE 5 + the anchored comparison ----
    verdicts = {}
    for f0, col in ((997.0, "HW"), (800.0, "ND")):
        print()
        print("=" * 88)
        print(f"GATE 5a -- does H3 rise monotonically with drive?  (tone {f0:g} Hz)")
        print("=" * 88)
        rising = gate_monotone(cells, f0, args.brief)
        print()
        print("=" * 88)
        print(f"GATE 5b -- on the rising branch, is H2 a function of H3 alone?  (tone {f0:g} Hz)")
        print("=" * 88)
        worst, at_anchor = gate_anchor_collapse(cells, f0, rising, args.brief)
        # ** Score the gate on the bins the CONCLUSION rests on. ** The worst bin overall is a
        # conservative statistic over regions no anchor lands in; what matters is whether the two
        # anchor bins pick out one H2. Both are printed so the gate cannot be quietly narrowed.
        collapse_ok = at_anchor < 6.0
        print(f"\n  worst within-bin H2 spread, ANY bin:    {worst:.2f} dB")
        print(f"  worst within-bin H2 spread, ANCHOR bins: {at_anchor:.2f} dB  -> anchoring is "
              f"{'WELL-POSED' if collapse_ok else '** AMBIGUOUS -- read the anchored table as a RANGE **'}")
        print("  (the per-anchor +- column below is the operative uncertainty on each quoted value)")

        print()
        print("=" * 88)
        print(f"ANCHORED COMPARISON -- tone {f0:g} Hz vs the {col} column")
        print("=" * 88)
        print("  RAW = at the output, exactly as the references are quoted.")
        print("  DE-EMB = with THIS chain's own measured linear gain at 2f..5f removed, i.e. the")
        print("           ladder the nonlinearity actually made. NOT comparable to the published")
        print("           numbers (those carry the reference device's filter, which we do not have)")
        print("           -- it is here so the two tones can be read on one axis.")
        for lbl in ("low", "mid"):
            tgt = REF[lbl]["HW"][3]                 # H3 target; HW and ND agree by construction
            hits = anchor(cells, f0, tgt, rising)
            print(f"\n  '{lbl} drive'  ==  the point where OUR H3/H1 = {tgt:+.1f} dB "
                  f"({REF[lbl]['HW'][3]:+.0f} HW / {REF[lbl]['ND'][3]:+.0f} ND -- they agree, "
                  f"which is why it is the anchor)")
            if not hits:
                lo = min(cells[(f0, db, d)]["hd"][3] for db in LEVELS_DB for d in DRIVES)
                hi = max(cells[(f0, db, d)]["hd"][3] for db in LEVELS_DB for d in DRIVES)
                print(f"    ** NOT REACHED ** -- our H3/H1 spans {lo:+.1f} .. {hi:+.1f} dB over the "
                      f"whole grid, so this anchor is outside what the model produces.")
                verdicts[(f0, lbl)] = None
                continue
            print(f"    reached at {len(hits)} of {len(LEVELS_DB)} input levels: " +
                  ", ".join(f"{h['level_db']:+d} dBFS @ drive {h['drive']:.3f}" for h in hits))
            g = fr[(f0, DRIVES[0])]
            print(f"    {'order':>6}  {'OURS raw':>16}   {'HW':>7} {'ND':>7}    "
                  f"{'vs HW':>7} {'vs ND':>7}   {'DE-EMB':>8}   authority")
            v = {}
            for n in (2, 3, 4, 5):
                vals = np.array([h["hd"][n] for h in hits])
                ours, spr = float(vals.mean()), float(vals.max() - vals.min())
                hw, nd = REF[lbl]["HW"][n], REF[lbl]["ND"][n]
                de = ours - (g[n] - g[1])
                v[n] = (ours, de)
                # ** reference-sources.md §1 splits authority by ORDER: ND governs the odds (it and
                # hardware agree there to the dB) and has none over the evens (~27 dB low). So the
                # useful question per order is whether the two columns AGREE -- where they do, our
                # error is the same against both and no authority argument is needed to read it.
                # Where they do not, the deficit means different things per column and must be
                # quoted as such. Printing this stops the two from being silently averaged. **
                agree = abs(hw - nd) < MIN_SPAN_DB
                note = "AGREE -> authority-free" if agree else f"split {hw - nd:+.0f} dB"
                print(f"    {'H' + str(n):>6}  {ours:+7.1f} +-{spr:5.1f}   "
                      f"{hw:+7.1f} {nd:+7.1f}    {ours - hw:+7.1f} {ours - nd:+7.1f}   {de:+8.1f}"
                      f"   {note}")
            verdicts[(f0, lbl)] = v
            out["anchors"][f"{f0:g}|{lbl}"] = dict(
                hits=[dict(level_db=h["level_db"], drive=h["drive"],
                           hd={str(n): h["hd"][n] for n in (2, 3, 4, 5)}) for h in hits],
                raw={str(n): v[n][0] for n in v}, deemb={str(n): v[n][1] for n in v},
                spread_ok=bool(collapse_ok))

    # ---- the one question the session asked ----
    print()
    print("=" * 88)
    print("THE QUESTION: did we inherit ND's symmetry, or land between the two?")
    print("=" * 88)
    print("  ** The PARITY discriminator is EVEN-MINUS-ADJACENT-ODD, not the absolute even level. **")
    print("  Absolute Hn/H1 at the output carries the chain's own linear shape, and this chain's")
    print("  is large (+9 to +15 dB at 2f..5f -- the bridged-T scoop the fundamental sits in) AND")
    print("  known to be wrong: session 64 measured our mid scoop ~2x too deep vs the pedal. So an")
    print("  absolute comparison against a published Hn/H1 inherits that error.")
    print("  H2-H3 and H4-H5 do not: the correction is only the filter's SLOPE between two")
    print("  adjacent harmonics (~1-3 dB here, printed below), against a discriminator of 27 dB.")
    print("  ** BUT DO NOT READ THAT AS 'ONLY THE PAIRS ARE READABLE' -- it was read that way for")
    print("     four sessions and it is not what the argument says. The anchored error vector has")
    print("     THREE degrees of freedom (the anchor forces e[H3]=0), these pairs are TWO of them,")
    print("     and the third -- the late-harmonic LEVEL -- takes the SAME small filter correction")
    print("     and is reported in its own block below. See level_rows() and GATE 6. **")
    print("    hardware signature: H2-H3 =   0 dB,  H4-H5 =   0 dB   (evens AT the adjacent odds)")
    print("    ND signature:       H2-H3 = -27 dB,  H4-H5 = -28 dB   (essentially no evens)")
    print(f"\n  {'tone':>6} {'drive':>6}  {'pair':>7}   {'OURS':>7} {'filt':>6} {'OURS corr':>10}"
          f"   {'ND':>7} {'HW':>7}   {'position':>9}")
    # ** DENOMINATOR GUARD lives in pair_rows(): 'position between the references' is only
    # meaningful when the references actually SEPARATE. At low drive HW and ND differ by just 1 dB
    # on H4-H5, and dividing by that turned a sane 7 dB reading into '-668%'. A pair that does not
    # discriminate must say so, not emit a number.
    for r in pair_rows(verdicts, fr):
        a, b = r["pair"]
        ps = f"{r['pos']:8.0f}%" if r["pos"] is not None else f"  n/a({abs(r['span']):.0f}dB)"
        print(f"  {r['tone']:6.0f} {r['drive']:>6}  H{a}-H{b:<4}   {r['ours']:+7.1f} "
              f"{r['filt']:+6.1f} {r['corr']:+10.1f}   {r['nd']:+7.1f} {r['hw']:+7.1f}   {ps}")
    print(f"\n  n/a = the two references are less than {MIN_SPAN_DB:.0f} dB apart on that pair, so it")
    print("        does not discriminate between them; read the raw/corrected columns instead.")
    print("\n  0% = we inherited ND's (near-absent) even-order mechanism.")
    print("  100% = we already deliver hardware's even-at-the-odds asymmetry.")
    print("  ** Read with reference-sources.md §5: the targets are chart reads, so the POSITION is")
    print("     the finding and the exact percentage is not. **")

    # ---- the third degree of freedom ----
    print()
    print("=" * 88)
    print("THE THIRD DEGREE OF FREEDOM -- LATE-HARMONIC LEVEL, (H4+H5)/2 relative to the anchor")
    print("=" * 88)
    print("  The anchor pins H3, so the anchored error vector is (e2, e4, e5) -- three numbers. The")
    print("  block above reports two contrasts of them (H2-H3 = e2, H4-H5 = e4-e5). This is the")
    print("  third, and GATE 6 shows a pure error in it reads EXACTLY ZERO in both of those.")
    print("  Same filter correction as the pairs: (g4+g5)/2 - g3, measured, printed as `filt`.")
    lrows = level_rows(verdicts, fr)
    print(f"\n  {'tone':>6} {'drive':>6}   {'OURS':>7} {'filt':>6} {'OURS corr':>10}   "
          f"{'ND':>7} {'HW':>7}   {'vs HW':>7} {'vs ND':>7}")
    for r in lrows:
        print(f"  {r['tone']:6.0f} {r['drive']:>6}   {r['ours']:+7.1f} {r['filt']:+6.1f} "
              f"{r['corr']:+10.1f}   {r['nd']:+7.1f} {r['hw']:+7.1f}   "
              f"{r['vs_hw']:+7.1f} {r['vs_nd']:+7.1f}")
    hw_low = [r["vs_hw"] for r in lrows if r["drive"] == "low"]
    hw_mid = [r["vs_hw"] for r in lrows if r["drive"] == "mid"]
    if hw_low and hw_mid:
        print(f"\n  vs HW, pooled over both tones:  low drive {np.mean(hw_low):+.1f} dB  "
              f"(tones {hw_low[0]:+.1f} / {hw_low[-1]:+.1f})   "
              f"mid drive {np.mean(hw_mid):+.1f} dB  (tones {hw_mid[0]:+.1f} / {hw_mid[-1]:+.1f})")
        print(f"  drive-dependence of the term: {np.mean(hw_mid) - np.mean(hw_low):+.1f} dB from low "
              f"to mid drive.")
        print("  ** The two tones AGREEING after correction is the check that the correction works:")
        print("     their raw filter slopes differ by ~1.6 dB/order and have OPPOSITE sign. **")
        print("  Positive = our late harmonics run HOTTER than the reference's; negative = our")
        print("  harmonic series decays too fast, i.e. it is too SHORT.")
        print("  ⚠ THIS STATISTIC IS COMPLETE BUT MIXES TWO AUTHORITIES. (H4+H5)/2 averages H4 --")
        print("    where HW and ND are 28 dB apart at mid drive, so the split in")
        print("    reference-sources.md §1 applies -- with H5, where the two columns AGREE. Use it")
        print("    to establish that the mode is LIVE and to size it; quote the per-order rows")
        print("    marked `AGREE -> authority-free` in the anchored tables above for a claim.")
    for r in lrows:
        out.setdefault("late_level", {})[f"{r['tone']:g}|{r['drive']}"] = {
            k: r[k] for k in ("ours", "filt", "corr", "nd", "hw", "vs_hw", "vs_nd")}

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
