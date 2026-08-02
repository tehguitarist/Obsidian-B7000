#!/usr/bin/env python3.11
"""Can the two-pole ATTACK topology be made to match the null's WIDTH as well as its (f0, depth)?
Session 64, Phase 9 / A3 step 21 -- session 63's next-step (a).

THE QUESTION
------------
Session 63 built the two-pole topology and it met the notch requirement TO THE BIN at all three
throws (f0 316.4 / 328.1 / 334.0 Hz, spread 17.58 Hz) and the broadband gain at the quiet end
(+8.28 vs +8.91 dB boost, -2.29 vs -2.38 cut). What it did NOT meet is the SHAPE:

  * every null is ~2x too BROAD -- half-depth width (interpolated) 150.6 / 59.6 / 138.6 Hz against
    the pedal's 77.9 / 27.1 / 71.9 (cut / boost / flat), i.e. 1.93 / 2.20 / 1.93;
  * the broadband slope has the WRONG SIGN on both throws (boost -1.39 dB/dec vs the pedal's +1.23,
    cut +0.10 vs -1.38).

⭐ The width excess is a nearly UNIFORM factor across all three throws, and the throws differ only
in pole B (Rd, C5). A per-throw element cannot produce a uniform error; a SHARED one can. So session
63's next step was named as a SHARED-element fit -- the ladder RC / R12 / R14 -- not a switch fit.
This tool tests that, and it tests it in the order that can produce a NEGATIVE result: census
first, then the SMALLEST structure that could work, then larger ones.

⛔ AND IT IS BUILT TO BE ABLE TO REFUTE, WHICH IS THE POINT. 12 free values against 9 notch numbers
hit them by construction (session 61 item 10b's own warning, and session 62 item 4's control where
adding R12 to the switched set reached notch cost 0.000 via broadband nonsense). So the families are
tried in increasing size and the FIRST one that works is the claim -- an over-parameterised success
is reported as such and is not evidence.

⚠⚠ THE CALIBRATION, WHICH IS THIS SESSION'S LOAD-BEARING METHOD FINDING
----------------------------------------------------------------------
The fast network solve is NOT interchangeable with the shipped chain on the quantities being fitted
here, and every ATTACK screen since session 61 has implicitly assumed it is:

    at session 62's own proposal point, treble-ladder-only vs the REAL RENDER --
      f0     316.25 / 327.75 / 333.75   vs   316.4 / 328.1 / 334.0   -> agrees to 0.35 Hz
      depth   14.74 /  32.63 /  15.85   vs    18.51 / 36.62 / 20.31  -> the render is ~4 dB DEEPER
      width  121.3  /  52.3  / 139.6    vs   150.6 /  59.6 / 138.6   -> and up to 24 % wider

Cause, measured not guessed: `D(f) = render_dB - ladder_dB` is one shared downstream transfer to
within ~0.6 dB (six curves, two very different ladder settings x three throws) and it FALLS 17.1 dB
across 150-700 Hz -- the IC2_B bridged-T scoop heading for its 717 Hz minimum, plus the two
Sallen-Keys. Depth and width are both measured against a shoulder at 200-270 Hz, so that tilt is
inside them: it deepens the apparent null and drags its upper skirt out.

⇒ SESSION 62 FITTED DEPTH ON AN INSTRUMENT ~4 dB OFFSET FROM WHAT SHIPS. Its reported 0.18 dB worst
depth error was real in the ladder solve and became 3.6-4.3 dB through the chain -- which session 63
observed and (correctly, since depth is a lower bound) allowed, without noting that the two
instruments disagree. They do, and a width fit cannot survive a 24 % scale error, so the requirement
is transferred into the SCREEN'S OWN UNITS by a calibration measured at the proposal point:

    f0     passes straight through (0.35 Hz)
    depth  additive offset      (python = render + d)
    width  multiplicative       (python = render * k)

and the screen's verdict is then always re-checked on the REAL RENDER (`attack_render_gate.py`),
because a render is 17.6 s and an optimiser needs thousands of evaluations -- the screen FINDS the
lever, the render LANDS the value. GATE C below is that calibration's own out-of-sample test.

GATES -- none optional, all run before any number is read
--------------------------------------------------------
  A SOLVER      the collapsed/degenerate tap network must reproduce `eq_reference.treble_attack_tf`.
                Delegated to attack_tap_screen, whose gate already proves this to ~1e-14 dB -- not
                re-implemented here (one oracle, not a second copy: session 62's own rule).
  B WIDTH       `locate_notch`'s width must recover a SYNTHESISED notch of known width. A statistic
                nobody has checked cannot carry a 2x claim.
  C CALIBRATION out-of-sample and in BOTH directions between two different C8 = 0 ladders (see the
                ⚠⚠ note at CAL for why the DRAWN default cannot be the anchor). A calibration
                fitted and tested at the same point proves nothing (session 43's imposed-check
                lesson). ⚠ IT CHECKS, at +-5 Hz f0 / +-3.3 dB depth / +-10-27 % width -- so this
                screen is a LEVER FINDER and `attack_render_gate.py` is the arbiter. Stated by the
                tool rather than assumed away.
  D SEARCH      recover a target the family DEFINITIONALLY makes, so a large residual is readable as
                unreachability rather than a weak optimiser (sessions 57/58/61). ⚠ Scored on the
                NOTCH ONLY: a first draft left an unmatchable broadband term in the objective and
                the gate then failed on its own construction.
  E PATHOLOGY   inherited from attack_tap_screen.stats -- a dead or wildly-rippling response can
                fake an arbitrarily deep null (session 57 item 5).
  + BOX SWEEP   a large residual is only UNREACHABILITY if widening the search does not shrink it
                (session 57 item 4). ⚠ This is what stopped session 64 calling the width
                unreachable: at +-1 decade it looks like a hard conflict, and at +-3 decades the
                nine numbers are all met -- see `--best`.

SCOPE
-----
  ATTACK is [ENG] -- this proposes a topology and disagrees with no drawn circuit. Magnitude only.
  Notch depths are LOWER bounds (probe gate 1(b)), so the depth RANKING carries the claim. h is a
  ratio between throws, so anything common to all three cancels by construction.

WHAT IT FOUND (session 64) -- read this before re-running any of it
------------------------------------------------------------------
  * NO shared ladder element is a width lever: all of them move width and f0 TOGETHER at
    ~0.5-1.5 Hz per Hz, and f0 already matches to the bin. Only C7 is width-selective
    (11.4 Hz of width per Hz of f0) and its authority is small. The TAP divider is
    width-NEUTRAL (<=0.5 Hz) and f0-neutral (0.00 Hz), extending session 62's pole
    independence to the width statistic.
  * The nine notch numbers ARE reachable -- f0 to 0.25-1.0 Hz, width to 0.8-11.9 % -- but only
    at R7 x572 (200k -> 114 MOhm), C6 x62, C5/C9/C7 x0.02-0.03, with the tap on its bound and
    the broadband at 3.5x floor. That is session 62 item 4's "reachable via nonsense" control,
    not a candidate. ⇒ NOT a refutation (the box sweep forbids that reading) and NOT shippable.
  * ⭐⭐ AND THE BIGGER FINDING IS NOT ATTACK'S AT ALL -- see `--tilt`. The OD path's own
    absolute shape falls 11.05 dB over 200->480 Hz where the pedal falls 4.88, in ALL THREE
    throws, level-independent, and the IC2_B bridged-T accounts for 10.79 of those 11.05 dB.
    GAP #1b, reopened on an axis that can see it.
  * ⚠ The obvious mechanism -- "the excess tilt IS the width excess, both are ~2.1x" -- was
    TESTED AND REFUTED here: de-tilting moves the ratio only 1.93 -> 1.69. Coincidence.

⛔⛔ SESSION 94 -- THE INSTRUMENT IS NOW SWITCHABLE AND DEFAULTS TO **STEPPED**. READ THIS BEFORE
QUOTING ANY NUMBER ABOVE, INCLUDING THE CALIBRATION TABLE AT LINE 34.
--------------------------------------------------------------------------------------------------
Everything above was measured with the SWEPT instrument: the requirement came from
`attack_notch_probe`'s 5.86 Hz-bin CSD record, and GATE C's calibration mapped the python solve onto
renders of the MAIN test signal read the same way. Session 70 replaced the ATTACK specification with
a STEPPED-SINE measurement, and session 93 measured what that swap is worth ON THE SAME AUDIO, both
sides (`attack_stepped_gate.py`): the pedal's boost null narrows **-29.1 %** and deepens +5.28 dB
under the stepped read, while the RENDER's boost null **widens +11.1 %** -- because smearing scales
with how narrow the feature is, and the model's null is ~2.5x broader than the pedal's.

⇒ a swept-read model scored against a stepped-read pedal books the instrument's own smearing as
model error, on the one throw the whole re-fit is about. That is not a scale factor: the width ratio
is worst at FLAT (1.98x) under swept-vs-swept and worst at BOOST (2.70x) under stepped-vs-stepped,
and which throw is worst is exactly what selects a SHARED ladder element vs a per-throw one.

What `--instrument stepped` (the default) changes, and NOTHING else moves:
  * the SOLVE GRID becomes the stimulus's own tone grid (`read_notch_sweep.FREQS`, 2 Hz through the
    core, 150-550 Hz) instead of a 0.25 Hz synthetic one, and the LOCATOR becomes `read_notch_sweep.
    locate`. So the model, the calibration anchor and the pedal are read by ONE instrument on ONE
    grid, and the calibration now carries only the python-vs-chain difference -- not, as before, an
    instrument mismatch as well.
  * the TARGET is MEASURED from the three drive-min captures (never transcribed) and cross-checked
    against session 70's published spec.
  * the f0 residual is normalised by the instrument's OWN resolution, 2.0 Hz instead of 5.86 -- so
    the f0 term carries ~2.9x the weight it did. That is the honest consequence of a finer
    instrument, it is printed, and `--fit`'s frontier sweeps `w_f0` anyway so nothing rests on it.
  * the calibration anchor and the `prop`/`dflt` renders are read through the NOTCH stimulus. The
    `prop`/`dflt` ones already exist -- `attack_stepped_gate.py` made them -- so only the CAL ladder
    needs `--render-cal` (3 renders).

⚠ `--instrument swept` reproduces the old behaviour exactly and is kept as the control, not as an
option to prefer: it is the wrong instrument for the current spec. ⚠ `--tilt` and the broadband `h`
term are NOT affected either way -- both are read on the MAIN test signal over 80-1600 Hz EXCLUDING
the notch window (`attack_multipole_screen.load_record`), so they are disjoint from the notch triple
and no stepped equivalent of them exists (this stimulus spans 150-550 Hz only).

⭐⭐ SESSION 95 -- THE OBJECTIVE NOW HAS AN ABSOLUTE TERM, AND IT BREAKS A TWO-WAY DEGENERACY THAT
PREDATES SESSION 94. READ THIS BEFORE RUNNING ANY FIT.
--------------------------------------------------------------------------------------------------
Everything above scores RELATIVE quantities only: the notch triple is referred to each throw's own
200-270 Hz shoulder, and `h` is a throw-to-throw ratio. A change shared by all three throws is
therefore invisible to the WHOLE objective -- which is how session 94's fit met the ATTACK
requirement on the real render (f0 to 0.72 Hz, depth to 0.24 dB) while the 129-capture matrix read
OD band-RMS 2.664 -> 6.174 and THD level 4.279 -> 18.685, with the OD path 40-47 dB down below
400 Hz.

⭐⭐ AND THE DEGENERACY IS OLDER AND MORE SPECIFIC THAN THAT. Measured bleed-free (drive MIN /
LEVEL max / BLEND max, where the clean bleed is exactly zero by topology) as `pedal - render`,
median over the notch-remote bins:

      render                cut      boost      flat
      DRAWN default       +0.47     +10.30     +2.51
      session 62 PROPOSAL +8.66      +9.18     +8.73

The drawn model is already ABSOLUTELY RIGHT at cut and 2.5 dB low at flat; the whole real defect is
BOOST, 10.3 dB light. But `h` only sees differences, so "raise boost by 10" and "lower cut and flat
by 8" score IDENTICALLY -- and session 62 took the second branch, which is why its proposal reads
h-correct to 0.45 dB while sitting ~9 dB below the pedal at every throw at once.

`g` is that missing constraint: the ladder's ABSOLUTE level over the notch-remote broadband bins,
against a target derived from the measurement above. It is scored in BOTH fit stages (stage 2
matters most -- the tap is a DIVIDER, i.e. the very element that trades the two branches). GATE F
gates it: F1 the downstream transfer's invariance (0.183 dB across two very different ladders,
which is what makes the transfer legitimate at all), F2 a known answer at the PROP point, F3 a
mutation that must move `g`, and F3b the blind spot itself -- a 14.88 dB shared re-scaling that the
notch triple absorbs 1.4 % of.

⚠ `--no-absgain` restores the pre-95 objective EXACTLY and is kept as the CONTROL, not as an option
to prefer: without it a shared re-scaling is free and a search will spend it.
⛔ The first re-fit under `g` reaches all nine notch numbers AND the absolute level (f0 0.12 Hz,
depth 0.76 dB, width 8.1 %, g 0.26 dB) but rests THREE of thirteen values on their bounds and still
moves C7 x0.243 -- NOT proposable, and not sent to the matrix. See CLAUDE.md item 4 for the two
specific next steps (the ranking key's last tie-break prefers the smaller BOX over fewer parameters
on a bound, which is what selected the unidentified point).

Usage:
  python3.11 analysis/attack_shape_screen.py --render-cal    # once per instrument: the cal anchor
  python3.11 analysis/attack_shape_screen.py --census        # the sensitivity table only
  python3.11 analysis/attack_shape_screen.py --tilt          # is the residual even ATTACK's?
  python3.11 analysis/attack_shape_screen.py --fit [--quick] [--json OUT]
  python3.11 analysis/attack_shape_screen.py --best [--json OUT]   # then:
  python3.11 analysis/attack_stepped_gate.py --fits-json <that JSON>       # stepped arbiter
  python3.11 analysis/attack_render_gate.py --both --fits-json <that JSON> # swept control
"""
import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout

import numpy as np
from scipy.io import wavfile
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                                       # noqa: E402
import read_notch_sweep as R                              # noqa: E402  (the STEPPED instrument)
with redirect_stdout(io.StringIO()):
    import eq_reference as E                              # noqa: E402
    import attack_multipole_screen as M                   # noqa: E402  (solver-free: record, db)
    import attack_tap_screen as T                         # noqa: E402  (the PROVEN tap solver)
    import attack_notch_probe as P                        # noqa: E402  (locate_notch = one oracle)
    import attack_render_gate as RG                       # noqa: E402  (ONE render-condition source)
from parallel import pmap                                 # noqa: E402

POSITIONS = P.POSITIONS                                   # cut, boost, flat
THROWS = ["boost", "cut"]
RENDER_DIR = "build/attack_render_gate"                   # attack_render_gate.py's own renders
CALDIR = "build/attack_shape_screen"                      # the SWEPT calibration anchor
CALDIR_STEP = "build/attack_shape_screen_stepped"         # the STEPPED one (session 94)
STEPDIR = "build/attack_stepped_gate"                     # attack_stepped_gate.py's own renders

# ---- the reference ladder points ------------------------------------------------------------
PROP = dict(Ra=470.0e3, Rb=506.0e3, Rc=78.5e3, R11=212.0e3, R7=200e3, R12=6.8e3, R14=22e3,
            C5=19.7e-9, C9=22e-9, C6=22e-9, C7=680e-12)
PROP_RD = dict(boost=478.0, flat=6.14e3, cut=6.04e3)
PROP_C5T = dict(boost=1.1e-9, flat=0.0, cut=2.7e-9)

# ⚠⚠ THE CALIBRATION ANCHOR MUST HAVE C8 = 0, AND THE SHIPPED DEFAULT DOES NOT -- a first draft
# used the DRAWN default as the anchor and GATE C failed by 62 Hz of f0 at every throw, identically.
# That identical-across-throws error is the tell: `tf_tap` takes ONE optional `c8` spanning M<->T3,
# so it can express the drawn BOOST throw (C8 bridges R8) and cannot express CUT (C8 shunts P->GND)
# or FLAT (C8 open) at all. Passing c8 = 0 therefore models a drawn network with C8 REMOVED, which
# is a different circuit from the one that renders -- so the "calibration" was measuring a
# structural mismatch, not a downstream transfer. (The C++ stage hangs C8 off the SELECTED tap;
# attack_topology_goldens.py records that the two implementations disagree BY CONSTRUCTION when C8
# is in circuit, and that the proposal used neither.) The anchor below is therefore a genuinely
# DIFFERENT ladder at C8 = 0, where both implementations model the same network.
CAL = dict(PROP, R12=PROP["R12"] * 1.7, C9=PROP["C9"] * 0.6, C5=PROP["C5"] * 1.15)
CAL_RD = dict(PROP_RD, boost=700.0, flat=3.2e3)
CAL_C5T = dict(PROP_C5T)
CAL_FITS = ["attackTapRa=470e3", "attackTapRb=506e3", "attackTapRc=78.5e3", "attackTapR11=212e3",
            "trebleC5=%.6g" % CAL["C5"], "attackC5TrimBoost=1.1e-9", "attackC5TrimCut=2.7e-9",
            "trebleLadderDampR=3.2e3", "attackDampBoost=700", "attackDampCut=6.04e3",
            "trebleC8=0", "trebleLadderR12=%.6g" % CAL["R12"], "trebleC9=%.6g" % CAL["C9"]]

# ---- grids ---------------------------------------------------------------------------------
# SWEPT: the notch stats want resolution the 5.86 Hz measurement grid does not have (the pedal's
# boost null is 4 bins wide), so the SCREEN runs fine and the calibration carries the difference.
# STEPPED: the opposite choice, and it is the right one once the pedal is read at 2 Hz -- solve on
# the STIMULUS'S OWN grid so the model and both measured sides share one grid AND one locator, and
# the calibration is left carrying only the python-vs-chain difference. See the session-94 block.
FNOTCH_SWEPT = np.arange(180.0, 500.01, 0.25)
FNOTCH_STEP = np.asarray(R.FREQS, dtype=float)            # 150-550 Hz, 2 Hz through the core
FBB = M.FBB                                               # the record's own broadband bins
ZBB = M.ZSA[-M.NBB:]
REC = M.REC
SEG = "sweep_clean"                                       # the -30 dBFS row the record quotes

# ---- THE INSTRUMENT ---------------------------------------------------------------------------
# Set once by `set_instrument()`; everything downstream reads these globals at call time, so the
# swept path is bit-for-bit what it was and the stepped path never has to be threaded through by
# hand (which is how a half-swapped instrument would get shipped).
INSTRUMENT = "stepped"
FNOTCH = FNOTCH_STEP
ZNOTCH = E.jfet_source_z(FNOTCH, **M.ZS)
RES_HZ = 2.0                                              # the f0 residual's normaliser
STIM = R.STIMULUS
CAL_HOME = CALDIR_STEP


def set_instrument(name):
    """Bind the grid, the locator's resolution, the stimulus and the render directories."""
    global INSTRUMENT, FNOTCH, ZNOTCH, RES_HZ, STIM, CAL_HOME
    INSTRUMENT = name
    if name == "stepped":
        FNOTCH, RES_HZ, STIM, CAL_HOME = FNOTCH_STEP, 2.0, R.STIMULUS, CALDIR_STEP
    elif name == "swept":
        FNOTCH, RES_HZ, STIM, CAL_HOME = FNOTCH_SWEPT, M.BIN_HZ, A.ORIG, CALDIR
    else:
        sys.exit("unknown instrument %r" % name)
    ZNOTCH = E.jfet_source_z(FNOTCH, **M.ZS)


# =============================================================================================
# statistics -- ONE definition per instrument, taken from that instrument's own locator
# =============================================================================================
def notch_stats(mag):
    """(f0, depth, width) for a magnitude curve sampled on the ACTIVE grid.

    ⚠ The two branches are not interchangeable and must never be mixed inside one comparison --
    that is the defect session 94 exists to remove. `locate_notch` reports f0 as the raw bin
    (`f_bin`) because on a 5.86 Hz grid the refined vertex was not trusted; `read_notch_sweep.
    locate` reports the parabolic vertex (`f_ref`), which is what session 70's spec and every
    number in `attack_stepped_gate.py` are quoted as.
    """
    if INSTRUMENT == "stepped":
        n = R.locate(FNOTCH, mag, fit_depth=False)         # depth_base unused here; see locate()
        return n["f_ref"], n["depth"], n["width"]
    n = P.locate_notch(FNOTCH, mag)
    return n["f_bin"], n["depth"], n["width_i"]


ZNOTCH_OVERRIDE = None    # set only by scale_diagnostic(); None = the shipped J201 boundary


def solve(base, rd, c5t, pos, f, zs):
    p = dict(base)
    p["Rd"] = rd[pos]
    p["C5"] = base["C5"] + c5t[pos]
    if ZNOTCH_OVERRIDE is not None and len(f) == len(FNOTCH):
        zs = ZNOTCH_OVERRIDE
    return M.db(T.tf_tap(f, zs, T.TAP_OF[pos], p, 0.0))


def full_stats(base, rd, c5t):
    """(f0, depth, width) per throw + the broadband h curve and its shape descriptors."""
    out, hb = {}, {}
    for pos in POSITIONS:
        m = solve(base, rd, c5t, pos, FNOTCH, ZNOTCH)
        if not np.all(np.isfinite(m)):
            return None
        if m.max() < -160.0 or (m.max() - m.min()) > 80.0:        # GATE E PATHOLOGY
            return None
        st = notch_stats(m)
        # ⚠⚠ GATE E, SECOND CLAUSE -- ADDED SESSION 94, AND IT IS A REAL BUG THE INSTRUMENT SWAP
        # EXPOSED RATHER THAN CREATED. `half_depth_width` returns nan when the half-depth contour
        # does not CLOSE inside the grid -- a null too shallow, or so broad its skirts run off the
        # 150-550 Hz span. On the old 180-500 Hz synthetic grid `locate_notch.width_i` still
        # returned a number there, so nothing downstream had ever seen a nan; on the stepped grid
        # the first `--fit` produced `width rms nan` at EVERY row and the search random-walked,
        # because a nan cost neither wins nor loses a comparison -- it is silently skipped
        # (`if best is None or key < best[0]` is False for nan) and differential_evolution's own
        # ranking is undefined. A candidate with no measurable null is not a candidate, so it is
        # rejected HERE as a pathology and scores 1e6 like every other one, rather than becoming
        # an unranked hole in the search space. (`empty-gate-must-fail`: a computation that
        # produces no value must FAIL, not fall through.)
        if not all(np.isfinite(v) for v in st):
            return None
        out[pos] = st
        hb[pos] = solve(base, rd, c5t, pos, FBB, ZBB)
    h = {q: hb[q] - hb["flat"] for q in THROWS}
    lg = np.log10(FBB)
    shape = {}
    for q in THROWS:
        c2, c1, _ = np.polyfit(lg, h[q], 2)
        shape[q] = (float(np.median(h[q])), float(c1 + 2.0 * c2 * float(np.mean(lg))))
    # `gabs` is `hb` BEFORE the flat throw is differenced out of it -- i.e. the one quantity the
    # whole objective used to throw away. Free: `hb` is already solved for `h` (session 95).
    return dict(notch=out, h=h, shape=shape, gabs=hb)


# =============================================================================================
# GATE B -- does the WIDTH statistic recover a known width?
# =============================================================================================
GATE_B_CASES = ((320.0, 16.0, 1.2), (320.0, 33.0, 4.0), (330.0, 16.0, 0.7), (300.0, 20.0, 2.0))


def gate_width_stepped():
    """GATE B for the stepped grid: does the width statistic survive being sampled at 2 Hz?

    ⭐ This is a different question from the swept gate's and it is the one that matters here. The
    screen now solves on the STIMULUS'S grid rather than a 0.25 Hz synthetic one, so the grid is no
    longer effectively continuous and the quantisation is inside every width it reports. The gate
    therefore drives the SHIPPED code path -- `notch_stats`, i.e. `read_notch_sweep.locate` on
    FNOTCH -- against `read_notch_sweep.true_width`, which evaluates the same filter's own
    half-depth width on a 0.05 Hz grid. The narrowest case (Qp 4, ~12 Hz) is deliberately NARROWER
    than the pedal's boost null (19.2 Hz), so it bounds the error at the sharpest feature the fit
    will ever be asked for.
    """
    print("  B WIDTH       recover a SYNTHESISED notch of known width, ON THE STEPPED GRID")
    print("      (%d tones, %g Hz through the core -- the quantisation is inside every width below)"
          % (len(FNOTCH), R.N.CORE_STEP))
    print("      %8s %8s %10s %10s %9s %9s" % ("f0 Hz", "depth", "true w", "recovered", "err %",
                                               "f0 err"))
    ok = True
    for f0, depth, Qp in GATE_B_CASES:
        b, a = R.notch_ba(f0, depth, Qp, A.FS)
        w = np.exp(1j * 2.0 * np.pi * FNOTCH / A.FS)
        mag = 20.0 * np.log10(np.abs((b[0] + b[1] / w + b[2] / w ** 2)
                                     / (a[0] + a[1] / w + a[2] / w ** 2)))
        true_w = R.true_width(f0, depth, Qp, A.FS)
        got_f0, _, got = notch_stats(mag)
        err = 100.0 * (got - true_w) / true_w
        print("      %8.1f %8.1f %10.2f %10.2f %+9.2f %+9.2f"
              % (f0, depth, true_w, got, err, got_f0 - f0))
        ok &= abs(err) < 5.0
    print("      => %s" % ("OK -- width survives the 2 Hz grid to <5 % at every synthesised null"
                           if ok else
                           "FAIL -- the 2 Hz grid does not carry the width statistic; the screen\n"
                           "                cannot be solved on it and the grid choice must be "
                           "revisited"))
    return ok


def gate_width():
    if INSTRUMENT == "stepped":
        return gate_width_stepped()
    print("  B WIDTH       recover a SYNTHESISED notch of known half-depth width")
    print("      %8s %8s %10s %10s %9s" % ("f0 Hz", "depth", "true w", "recovered", "err %"))
    ok = True
    for f0, depth, Qp in GATE_B_CASES:
        b, a = P.notch_ba(f0, depth, Qp, A.FS)
        w = np.exp(1j * 2.0 * np.pi * FNOTCH / A.FS)
        Hs = ((b[0] + b[1] / w + b[2] / w ** 2) / (a[0] + a[1] / w + a[2] / w ** 2))
        mag = 20.0 * np.log10(np.abs(Hs))
        # closed form: |H| dips to 10^(-depth/20) at f0 and the half-depth contour is at
        # -depth/2 dB, so the TRUE width is found on a 100x finer grid of the same expression.
        ff = np.arange(180.0, 500.001, 0.0025)
        wf = np.exp(1j * 2.0 * np.pi * ff / A.FS)
        mf = 20.0 * np.log10(np.abs((b[0] + b[1] / wf + b[2] / wf ** 2)
                                    / (a[0] + a[1] / wf + a[2] / wf ** 2)))
        sh = float(np.max(mf[(ff >= P.SHOULDER_WIN[0]) & (ff <= P.SHOULDER_WIN[1])]))
        sel = (ff >= P.WIDTH_WIN[0]) & (ff <= P.WIDTH_WIN[1])
        cont = sh - 0.5 * (sh - float(np.min(mf[sel])))
        idx = np.flatnonzero(mf[sel] < cont)
        true_w = float(ff[sel][idx[-1]] - ff[sel][idx[0]])
        _, got = P.notch_width(FNOTCH, mag)
        err = 100.0 * (got - true_w) / true_w
        print("      %8.1f %8.1f %10.2f %10.2f %+9.2f" % (f0, depth, true_w, got, err))
        ok &= abs(err) < 5.0
    print("      => %s" % ("OK -- width is recovered to <5 %% at every synthesised null" if ok
                           else "FAIL -- the width statistic itself is not trustworthy"))
    return ok


# =============================================================================================
# GATE C -- the python->render calibration, tested OUT OF SAMPLE
# =============================================================================================
RENDER = "build/OfflineRender_artefacts/Release/OfflineRender"
# ⚠⚠ Taken from attack_render_gate, which DERIVES it from the capture filename rather than
# hand-writing it (session 65). The hand-written version omitted `--grunt`, so every render this
# tool made -- including GATE C's calibration anchor -- ran at GRUNT BOOST against captures taken
# at GRUNT CUT, a ~36 Hz vs ~896 Hz first-order highpass. See attack_render_gate._base_args().
BASE_ARGS = RG.BASE                                                 # the record's own point
ATTACK_IDX = {"flat": "0", "boost": "1", "cut": "2"}


def render_cal():
    """Render the CALIBRATION anchor -- 3 throws -- through the ACTIVE instrument's stimulus.

    ⚠ Two anchors now exist, in two directories, because they are renders of two DIFFERENT
    stimuli. They cannot be told apart by `RG.check_stamp`, which compares `argv[3:]` and so never
    sees the input file -- that is why `_check_stim` below exists and why the directories differ.
    """
    os.makedirs(CAL_HOME, exist_ok=True)
    print("  rendering the %s calibration anchor, 3 throws, in parallel ..." % INSTRUMENT)
    pmap(_render_one_cal, list(POSITIONS))
    print("  ok.")


def _render_one_cal(pos):
    """One throw of the calibration anchor. Module level so `pmap` can hand it to a worker."""
    import subprocess
    out = os.path.join(CAL_HOME, "cal_%s.wav" % pos)
    cmd = [RENDER, STIM, out] + BASE_ARGS + ["--attack", ATTACK_IDX[pos]]
    for f in CAL_FITS:
        cmd += ["--fit", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("render failed:\n%s\n%s" % (" ".join(cmd), r.stderr))
    RG.stamp(out, cmd)
    return out


def _check_stim(path):
    """GATE 1's missing half: `RG.check_stamp` compares argv[3:], so it CANNOT see which stimulus a
    render was made from -- a swept and a stepped render of the same fits have identical stamps.
    With two instruments in one tool that is no longer a theoretical hole, so the input path is
    checked explicitly. (`rebaseline-all-derived-artefacts`, and session 65's own incident.)"""
    got = json.load(open(path + ".args.json"))["argv"][1]
    if os.path.abspath(got) != os.path.abspath(STIM):
        sys.exit("%s was rendered from %s but the %s instrument reads %s -- delete it and "
                 "re-render." % (path, got, INSTRUMENT, STIM))


_STEP_STIM = None


def _stepped_read(path):
    """Read one render/capture with the stepped instrument. The stimulus is cached: it is a 34 MB
    wav and GATE C alone reads six files."""
    global _STEP_STIM
    if _STEP_STIM is None:
        _, s = wavfile.read(R.STIMULUS)
        _STEP_STIM = s.astype(np.float64)
    x, _ = R.align_to_stim(R.load_raw(path), _STEP_STIM)
    n = R.locate(*R.curve(x, _STEP_STIM, R.LEVELS_DB[0]))
    return n["f_ref"], n["depth"], n["width"]


def rendered(tag, pos):
    """Read a render, returning (f0, depth, width) in the ACTIVE instrument's units.

    `dflt_*`/`prop_*` come from another tool at the same operating point, so nothing is re-rendered
    -- `attack_render_gate.py` under swept, `attack_stepped_gate.py` under stepped (where the tags
    are `default`/`proposal`). `cal_*` is this tool's own anchor.

    ⚠ EVERY read is condition-checked against its own `.args.json` stamp, INCLUDING the stimulus.
    GATE C mixes renders from two different producers, so a stale one on either side silently
    corrupts the calibration -- which is exactly what happened in session 65 when the `dflt`/`prop`
    side was re-rendered at the corrected GRUNT and this `cal_*` anchor was not.
    """
    stepped = INSTRUMENT == "stepped"
    if tag == "cal":
        path, how = os.path.join(CAL_HOME, "cal_%s.wav" % pos), \
            "python3.11 analysis/attack_shape_screen.py --instrument %s --render-cal" % INSTRUMENT
    elif stepped:
        path = os.path.join(STEPDIR, "%s_%s.wav" % ({"prop": "proposal", "dflt": "default"}[tag], pos))
        how = "python3.11 analysis/attack_stepped_gate.py"
    else:
        path, how = os.path.join(RENDER_DIR, "%s_%s.wav" % (tag, pos)), \
            "python3.11 analysis/attack_render_gate.py --both"
    if not os.path.exists(path):
        sys.exit("missing %s -- run: %s" % (path, how))
    fits = CAL_FITS if tag == "cal" else (RG.PROPOSAL if tag == "prop" else [])
    expect = list(BASE_ARGS) + ["--attack", ATTACK_IDX[pos]]
    for f in fits:
        expect += ["--fit", f]
    RG.check_stamp(path, expect)
    _check_stim(path)
    if stepped:
        return _stepped_read(path)
    orig = A.load(A.ORIG)
    x = A.load(path)
    x, _ = A.align(x, orig)
    f, m = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
    n = P.locate_notch(f, m)
    return n["f_bin"], n["depth"], n["width_i"]


def calibrate(tag, base, rd, c5t):
    """(d_f0, d_depth, k_width) per throw: python = render + d, python = render * k."""
    cal = {}
    for pos in POSITIONS:
        rf, rdep, rw = rendered(tag, pos)
        f0, dep, w = notch_stats(solve(base, rd, c5t, pos, FNOTCH, ZNOTCH))
        cal[pos] = (f0 - rf, dep - rdep, w / rw)
    return cal


def predict(cal, base, rd, c5t, tag):
    """Apply a calibration to the screen and compare against `tag`'s render."""
    rows, ok = {}, True
    for pos in POSITIONS:
        rf, rdep, rw = rendered(tag, pos)
        f0, dep, w = notch_stats(solve(base, rd, c5t, pos, FNOTCH, ZNOTCH))
        d0, dd, kw = cal[pos]
        pf, pd, pw = f0 - d0, dep - dd, w / kw
        rows[pos] = (pf, rf, pd, rdep, pw, rw)
        ok &= (abs(pf - rf) < 3.0 and abs(pd - rdep) < 1.5 and abs(pw - rw) / rw < 0.12)
    return rows, ok


def gate_calibration():
    print("\n  C CALIBRATION out-of-sample, BOTH directions between two very different C8=0")
    print("      ladders. A calibration tested where it was fitted proves nothing (session 43).")
    cal_c = calibrate("cal", CAL, CAL_RD, CAL_C5T)
    cal_p = calibrate("prop", PROP, PROP_RD, PROP_C5T)
    print("      from CAL : %s"
          % " | ".join("%s df0 %+.2f dep %+.2f kw %.3f" % (p, *cal_c[p]) for p in POSITIONS))
    print("      from PROP: %s"
          % " | ".join("%s df0 %+.2f dep %+.2f kw %.3f" % (p, *cal_p[p]) for p in POSITIONS))
    ok = True
    for cal, base, rd, c5t, tag, lab in ((cal_c, PROP, PROP_RD, PROP_C5T, "prop", "CAL -> PROP"),
                                         (cal_p, CAL, CAL_RD, CAL_C5T, "cal", "PROP -> CAL")):
        rows, good = predict(cal, base, rd, c5t, tag)
        ok &= good
        print("      %-11s %-6s | %-24s | %-24s | %s"
              % (lab, "throw", "f0 Hz pred/rend", "depth dB pred/rend", "width Hz pred/rend"))
        for pos in POSITIONS:
            pf, rf, pd, rdp, pw, rw = rows[pos]
            print("      %-11s %-6s | %7.2f /%7.2f (%+5.2f) | %7.2f /%7.2f (%+5.2f) |"
                  " %6.1f /%6.1f (%+5.1f%%)"
                  % ("", pos, pf, rf, pf - rf, pd, rdp, pd - rdp, pw, rw,
                     100.0 * (pw - rw) / rw))
    print("      => %s" % (
        "OK -- one calibration transfers between two very different ladder points"
        if ok else "CHECK -- the calibration does NOT transfer well enough to fit ABSOLUTE width\n"
                   "                on. Treat the screen as a LEVER FINDER and land every value on\n"
                   "                attack_render_gate.py (which is the arbiter regardless)."))
    # The PROP-anchored calibration is the one used for targets: it is anchored at the point
    # the fit starts from, so first-order it is exact there.
    return cal_p, ok


# =============================================================================================
# targets, expressed in the SCREEN's own units via the calibration
# =============================================================================================
# Session 70's published stepped spec, at drive-min / -30 dBFS. Used ONLY as a known-answer check
# on the measurement below -- never as the target itself (`rebuild-targets-dont-transcribe`, s33).
S70_SPEC = {"cut": (323.03, 15.27, 75.4), "boost": (326.41, 37.98, 19.2), "flat": (330.17, 15.58, 75.6)}


def pedal_record():
    """The pedal's (f0, depth, width) per throw, in the ACTIVE instrument's own units.

    ⚠⚠ MEASURED, NOT TRANSCRIBED, on both branches. The swept branch reads
    `attack_notch_probe`'s saved record; the stepped branch reads the three drive-min captures
    through `read_notch_sweep` -- the same files, the same locator and the same level that
    `attack_stepped_gate.py` scores against, so the requirement and the arbiter cannot drift
    apart. The transcribed session-70 numbers are then used the only way a transcription safely
    can be: as a KNOWN ANSWER the fresh measurement has to reproduce.
    """
    if INSTRUMENT != "stepped":
        d = REC["raw"]["notch"]
        return {p: (float(d[p]["f_bin"]), float(d[p]["depth"]), float(d[p]["width_i"]))
                for p in POSITIONS}
    out, worst = {}, 0.0
    print("\n  the PEDAL, measured through the stepped instrument (drive-min, %d dBFS), against"
          % R.LEVELS_DB[0])
    print("  session 70's published spec as a known answer:")
    print("      %-6s %-24s %-24s %s" % ("throw", "f0 Hz  meas / s70", "depth dB  meas / s70",
                                         "width Hz  meas / s70"))
    for pos in POSITIONS:
        path = os.path.join(R.CAP_DIR, R.CONDS["drive-min"].format(throw=pos))
        if not os.path.exists(path):
            sys.exit("missing pedal capture %s" % path)
        f0, dep, w = _stepped_read(path)
        s = S70_SPEC[pos]
        out[pos] = (f0, dep, w)
        worst = max(worst, abs(f0 - s[0]), abs(dep - s[1]), abs(w - s[2]))
        print("      %-6s %8.2f / %-13.2f %8.2f / %-13.2f %8.1f / %.1f"
              % (pos, f0, s[0], dep, s[1], w, s[2]))
    ok = worst < 0.5
    print("      => worst |meas - s70| = %.2f  (limit < 0.5)   %s"
          % (worst, "OK -- the record reproduces" if ok else
             "FAIL -- this is NOT session 70's measurement; do not fit to it"))
    if not ok:
        sys.exit(1)
    return out


def screen_targets(cal):
    """The pedal's requirement mapped into python-solve units."""
    rec = pedal_record()
    t = {}
    for pos in POSITIONS:
        d0, dd, kw = cal[pos]
        f0, dep, w = rec[pos]
        t[pos] = (f0 + d0, dep + dd, w * kw)
    return t


# =============================================================================================
# ⭐⭐ THE ABSOLUTE OD-MAGNITUDE TERM -- session 95, and it breaks a TWO-WAY DEGENERACY
# =============================================================================================
# Session 94's fit met the corrected ATTACK requirement on the real render (f0 to 0.72 Hz, depth
# to 0.24 dB) and the 129-capture matrix refused it by a mile -- OD band-RMS 2.664 -> 6.174, THD
# level 4.279 -> 18.685 -- because it had re-scaled the shared treble ladder and put the OD path
# 40-47 dB down below 400 Hz. The cause is structural and is stated in this file's own `--tilt`
# docstring: **every term of the objective is RELATIVE.** The notch triple is referred to each
# throw's own 200-270 Hz shoulder, and `h` is a throw-to-throw ratio, so a change shared by all
# three throws is invisible to the WHOLE objective and a search will spend it to the last dB.
#
# ⭐⭐ AND THE DEGENERACY IS OLDER AND MORE SPECIFIC THAN "SESSION 94 WENT WRONG". Measured
# bleed-free (drive MIN / LEVEL max / BLEND max, where the clean bleed is exactly zero by
# topology), as `pedal - render` median over the notch-remote band, at -30 dBFS:
#
#       render                cut      boost      flat
#       DRAWN default       +0.47     +10.30     +2.51
#       session 62 PROPOSAL +8.66      +9.18     +8.73
#
# The drawn model is already ABSOLUTELY RIGHT at cut and 2.5 dB low at flat; what it misses is
# BOOST, by 10.3 dB. `h` only sees differences, so "raise boost by 10" and "lower cut and flat by
# 8" score IDENTICALLY -- and session 62 took the second branch. That is why the proposal reads
# h-correct to 0.45 dB while sitting ~9 dB below the pedal at every throw at once. ⇒ the missing
# constraint is not a refinement of the width fit; it is the half of the requirement that selects
# WHICH of two h-equivalent branches is the physical one.
#
# WHY THE TRANSFER IS LEGITIMATE (gate F). The screen solves the treble ladder alone; the render
# adds a shared downstream transfer D(f) = render_dB - ladder_dB. If D is invariant to the ladder,
# an absolute ladder target can be derived from an absolute RENDER measurement. Measured between
# the two very different C8=0 ladders GATE C already uses (PROP and CAL), over the whole band and
# all three throws: worst |D_cal - D_prop| = 0.28 dB. So it is, and gate F re-computes it.
#
# ⚠ SCOPE, stated rather than assumed. This says the OD path is ~10 dB light AT BOOST and that the
# ATTACK ladder is a lever that can move it; it does NOT localise the whole deficit to ATTACK. The
# matrix is the arbiter of whether this ladder is the right carrier, exactly as for every other
# candidate here.
G_BAND = (FBB < 175.0) | (FBB >= 500.0)
# ⚠ NOTCH-REMOTE, and the exclusion is the load-bearing choice. Delta(f) is broadband (+7..+9 dB
# at 88-125 Hz and at 1-1.6 kHz) but rises to +17..+19 dB over 175-355 Hz -- that hump is the
# PROPOSAL's null being ~2x too broad, i.e. the WIDTH residual the notch terms already score.
# Scoring the full band here would double-count it and let the level term fight the width term.
#
# ⛔⛔ THE NEXT SENTENCE USED TO READ "the pathology this exists to catch is untouched by the
# exclusion: a 40 dB collapse below 400 Hz is still fully visible in the 88-175 Hz bins."
# THAT IS TRUE OF THE BINS AND FALSE OF THE MEDIAN OVER THEM, and session 98 measured the
# difference. G_BAND's 100 bins are LINEARLY spaced: 8 lie below 175 Hz and 92 above 533, so the
# median bin sits at 1019.5 Hz. `median(gabs[G_BAND])` was therefore a ~1 kHz statistic wearing a
# broadband name, and 8 bins in 100 cannot move it. Measured on the session-97 winner, the pooled
# median read the term SATISFIED (+0.34 / -0.03 / +0.39 dB) while the same ladder was
# -22.7 / -22.4 / -21.8 dB at 88-175 Hz and +3.0 / +2.5 / +2.7 at 1130-1600 -- i.e. the residual
# is a TILT whose ends cancel in the median. The 129-capture matrix duly read OD 25-100 Hz p90
# 6.065 -> 20.958 (`analysis/reports/s98_attack_cand.json`).
# ⭐ GENERAL: decompose a pooled summary into sub-bands BEFORE trusting it as an acceptance
# criterion, and prefer a per-sub-band residual whenever the quantity can fail in one region and
# pass in another. Same family as the CLEAN pooled-p90 split (s95/s96) -- and this is the THIRD
# blind objective this project has shipped, each found only when the matrix rejected its fit.
#
# ⭐⭐ SESSION 99 -- THE TERM IS NOW SCORED PER SUB-BAND. The cut points are on the REAL LINE, not
# on G_BAND, so the sub-bands tile it by construction and `check_g_partition()` only has to police
# the code, not a hope. Intersected with G_BAND they hold 8 / 23 / 28 / 41 = 100 bins.
# ⚠ The LF band carries only 8 bins and is nonetheless weighted equally with the other three --
# that IS the fix, and it is sound here because these are deterministic renders: measured at two
# stimulus levels the LF sub-band is the most stable of the four (0.007 dB, against 0.383 at
# 1130-1600). Bin COUNT is not evidence about a statistic's reliability when there is no noise.
G_SUBS = (("LF    88-170", 0.0, 175.0),
          ("LM   533-793", 175.0, 800.0),
          ("M    805-1125", 800.0, 1130.0),
          ("HM  1137-1600", 1130.0, 1e9))
# The pre-session-99 objective, kept as `--g-pooled`: a ONE-element partition, so the control runs
# the same code path and is not a second implementation that could drift.
G_POOL = (("POOLED 88-1600", 0.0, 1e9),)
G_ACTIVE = G_SUBS
G_SEL = [G_BAND & (FBB >= lo) & (FBB < hi) for _, lo, hi in G_ACTIVE]
G_FLOOR_DB = 1.0
# ⚠ NOT the 0.204 dB take-to-take floor. That figure is a knob-repositioning bound against a
# deterministic renderer (`reference-sources.md` §0), and it is far tighter than this term's own
# transfer accuracy: gate F's D-invariance is 0.28 dB and the Delta measurement's own
# level-dependence is 0.27 dB. 1.0 dB is the same floor the DEPTH residual uses and is a bound on
# the quantity, not a claim about noise. `--fit`/`--best` sweep `wt_g` on top of it.
_G_REC = None


def check_g_partition(subs=None, band=None):
    """The sub-bands must TILE G_BAND EXACTLY -- disjoint, and covering every bin.

    ⚠⚠ NOT DECORATION, AND THE ASYMMETRY IS THE REASON. A silently DROPPED band improves every g
    statistic at once (`aggregate-moved-check-membership-first` in its most flattering form), and
    an OVERLAP silently double-weights whatever region it covers -- both look like a better fit and
    neither shows up in any printed number. `release_gate.check_clean_partition` exists for exactly
    this and was mutation-tested three ways; so is this one (see `gate_g_partition`).
    Returns the bin count per sub-band; raises on any partition defect.
    """
    subs = G_ACTIVE if subs is None else subs
    band = G_BAND if band is None else band
    sels = [band & (FBB >= lo) & (FBB < hi) for _, lo, hi in subs]
    counts = [int(s.sum()) for s in sels]
    union = np.zeros_like(band)
    for s in sels:
        if bool((union & s).any()):
            raise AssertionError("g sub-bands OVERLAP: %d bins counted twice"
                                 % int((union & s).sum()))
        union = union | s
    if not np.array_equal(union, band):
        raise AssertionError("g sub-bands do NOT tile G_BAND: %d of %d bins uncovered, %d extra"
                             % (int((band & ~union).sum()), int(band.sum()),
                                int((union & ~band).sum())))
    if any(c == 0 for c in counts):
        raise AssertionError("an empty g sub-band is not a sub-band: %s"
                             % [s[0] for s, c in zip(subs, counts) if c == 0])
    return counts


def set_g_partition(pooled):
    """Bind the ACTIVE g partition. `pooled=True` restores the pre-session-99 single median."""
    global G_ACTIVE, G_SEL, _G_REC
    G_ACTIVE = G_POOL if pooled else G_SUBS
    G_SEL = [G_BAND & (FBB >= lo) & (FBB < hi) for _, lo, hi in G_ACTIVE]
    _G_REC = None                      # the record is per-partition -- never carry it across
    check_g_partition()
    return G_ACTIVE


def g_labels():
    return [s[0] for s in G_ACTIVE]


def print_g_table(gg, tgt_g, indent="    "):
    """`got / want (residual)` per throw AND per sub-band -- ONE printer, so a caller cannot
    accidentally re-collapse the vector into the pooled number the repair exists to remove."""
    print("%sg abs, per sub-band (got / want / residual dB):" % indent)
    print("%s  %-14s %s" % (indent, "sub-band", "  ".join("%-24s" % p for p in POSITIONS)))
    for i, (lab, _, _) in enumerate(G_ACTIVE):
        print("%s  %-14s %s"
              % (indent, lab, "  ".join("%+7.2f /%+7.2f (%+5.2f) "
                                        % (gg[p][i], tgt_g[p][i], gg[p][i] - tgt_g[p][i])
                                        for p in POSITIONS)))
    allv = np.concatenate([gg[p] - tgt_g[p] for p in POSITIONS])
    print("%s  worst %+.2f dB   rms %.2f dB over %d values"
          % (indent, allv[int(np.argmax(np.abs(allv)))],
             float(np.sqrt(np.mean(np.square(allv)))), allv.size))


def g_json(d):
    """Vectors -> lists, so a report is readable and json.dump does not need `default=float`."""
    return {p: (v.tolist() if hasattr(v, "tolist") else v) for p, v in d.items()}


def abs_gain_record():
    """Delta = pedal - PROP render, absolute and bleed-free, per throw. MEASURED, never quoted.

    Two soundness gates, both from this project's own history and both COMPUTED here:
      * it must be present in ALL THREE throws, or it is not a shared error;
      * it must be LEVEL-independent, or it is an operating point (session 61 item 3).
    ⚠ Neither gate can distinguish a shared CIRCUIT error from a shared RENDER-CONDITION error
    (session 65's missing `--grunt` flag satisfied both). What rules that out here is that the
    renders are condition-stamped against `captures.render_args` -- `RG.check_stamp` below.
    """
    global _G_REC
    if _G_REC is not None:
        return _G_REC
    orig = A.load(A.ORIG)
    with redirect_stdout(io.StringIO()):
        caps = P.load_all(orig)

    def on_fbb(sig, seg):
        x, _ = A.align(sig, orig)
        f, m = A.transfer(A.seg_of(x, seg), A.seg_of(orig, seg))
        return np.interp(FBB, f, m)

    counts = check_g_partition()
    print("\n  the ABSOLUTE OD magnitude, bleed-free (drive min / LEVEL max / BLEND max), as")
    print("  Delta = pedal - PROP render, PER SUB-BAND over the %d notch-remote bins of the"
          % int(G_BAND.sum()))
    print("  broadband band. `h` is a ratio and cannot see this; the notch triple is referred to")
    print("  each throw's own shoulder and cannot either; and the POOLED median could not see")
    print("  WHERE it sits in frequency (session 98 -- see the note beside G_SUBS).")
    print("      %-14s %5s %10s %10s %10s %10s"
          % ("sub-band", "bins", "cut", "boost", "flat", "worst lvl"))
    # ⚠ The TARGET is per sub-band too, not the pooled Delta re-used four times. Measured, Delta
    # runs +8.3..+12.4 dB across these bands -- a 4.1 dB spread against a 1.0 dB floor -- so a
    # pooled target would inject up to 3.7 dB of systematic error into the LF residual and the
    # repaired term would be scoring the wrong requirement.
    rec = {p: np.zeros(len(G_SEL)) for p in POSITIONS}
    lo36 = {p: np.zeros(len(G_SEL)) for p in POSITIONS}
    curves = {}
    for pos in POSITIONS:
        path = os.path.join(RENDER_DIR, "prop_%s.wav" % pos)
        expect = list(BASE_ARGS) + ["--attack", ATTACK_IDX[pos]]
        for f in RG.PROPOSAL:
            expect += ["--fit", f]
        RG.check_stamp(path, expect)        # a render from another condition is not a datum
        r = A.load(path)
        curves[pos] = (on_fbb(caps[pos], "sweep_clean_-36") - on_fbb(r, "sweep_clean_-36"),
                       on_fbb(caps[pos], SEG) - on_fbb(r, SEG))
    worst_lvl = 0.0
    for i, sel in enumerate(G_SEL):
        row36 = [float(np.median(curves[p][0][sel])) for p in POSITIONS]
        row30 = [float(np.median(curves[p][1][sel])) for p in POSITIONS]
        dep = max(abs(a - b) for a, b in zip(row36, row30))
        worst_lvl = max(worst_lvl, dep)
        for j, p in enumerate(POSITIONS):
            rec[p][i], lo36[p][i] = row30[j], row36[j]
        print("      %-14s %5d %+10.2f %+10.2f %+10.2f %10.3f"
              % (G_ACTIVE[i][0], counts[i], *row30, dep))
    allv = np.concatenate([rec[p] for p in POSITIONS])
    ok_all = float(np.min(np.abs(allv))) > 2.0 * G_FLOOR_DB
    ok_lvl = worst_lvl < 0.5
    print("      => present in every throw AND every sub-band: %s (smallest |Delta| %.2f dB vs"
          " 2x floor %.1f)" % ("YES" if ok_all else "NO", float(np.min(np.abs(allv))),
                               2.0 * G_FLOOR_DB))
    print("      => level-independent: %s (worst %.3f dB, limit 0.5); band spread %.2f dB"
          % ("YES" if ok_lvl else "NO", worst_lvl, float(allv.max() - allv.min())))
    if not ok_lvl:
        sys.exit("  the absolute deficit moves with LEVEL -- it is an operating point, not a "
                 "shape error, and must not be fitted as one.")
    _G_REC = rec
    return rec


def g_of(st):
    """The candidate's own absolute ladder level per throw, on the same bins as the target.

    ⭐ Returns one value PER SUB-BAND (a vector), not one pooled median. In `--g-pooled` the
    partition has a single element, so the vector has length 1 and the arithmetic downstream is
    identical to the pre-session-99 scalar -- which is what makes the control exact rather than a
    re-implementation.
    """
    return {p: np.array([float(np.median(st["gabs"][p][sel])) for sel in G_SEL])
            for p in POSITIONS}


def g_targets():
    """Absolute ladder level the pedal asks for, per throw AND per sub-band, in screen units.

    target = ladder_PROP + Delta. Exact given gate F: the render is ladder + D with D invariant,
    so (pedal - render) is the offset the LADDER has to move by, whatever D happens to be.
    ⚠ That invariance is measured between two MILD ladders and the fit walks well outside them --
    see GATE F's F4 and `attack_d_extrapolation_gate.py`.
    """
    rec = abs_gain_record()
    ref = full_stats(PROP, PROP_RD, PROP_C5T)
    if ref is None:
        sys.exit("the PROP reference point is pathological -- the g target cannot be built")
    g0 = g_of(ref)
    return {p: g0[p] + rec[p] for p in POSITIONS}


def gate_absgain(tgt):
    """GATE F -- is the downstream transfer D(f) = render - ladder INVARIANT to the ladder?

    Five checks, in the order that can produce a negative:
      F1 INVARIANCE  D measured at PROP and at CAL (two very different C8=0 ladders) must agree,
                     or no absolute ladder target can be transferred from a render measurement
                     and this whole term is unfounded.
      F2 KNOWN ANSWER  scored at the PROP point itself, the g residual must equal Delta exactly
                     -- the definitional check that catches a sign or reference slip. Now checked
                     PER SUB-BAND, so a partition that silently drops a region cannot pass it.
      F3 MUTATION    a ladder re-scaled by a known amount must MOVE g -- a term that cannot
                     register the change it exists to police is `empty-gate-must-fail` -- AND
                     the pre-session-95 objective must be shown NOT to see the same change.
                     That second clause is the whole claim of this section, computed rather than
                     asserted: if the old terms move as much as the new one, there was no blind
                     spot and this term is redundant.
      F4 REGION OF VALIDITY  (session 99) F1 measures the invariance between two ladders that are
                     "very different" from EACH OTHER and both CLOSE TO the drawn network. The fit
                     walks far outside that region, and there the premise fails: measured at the
                     session-97 winner (R7 x7.28, C7 x0.244) the worst |D_cand - D_prop| is
                     3.84 dB against F1's 0.183 (GATE H2). F4 measures D at that WILD ladder too,
                     from renders already on disk, and PRINTS the envelope as a function of ladder
                     distance -- so an unstated interpolation assumption becomes a stated,
                     measured limit that `best_point` can report its winner against.
      F5 BLIND SPOT  (session 99) the pooled median must be shown NOT to see a defect the
                     per-sub-band residual does -- the same computed-not-asserted standard F3b
                     applies to the session-95 term, now applied to the session-99 one, using the
                     session-97 winner as the known answer.
    ⚠ The mutation is the TAP (Ra x10), not a ladder element. A first draft used R7 x10 and the
    gate FAILED -- correctly, but for its own reason: R7 x3 and beyond destroy the null outright
    (width -> nan), so `full_stats` returns None at the pathology gate and g cannot be read at
    ALL. The draft scored that as `dg = 0.0`, i.e. it turned "no measurement" into "no movement"
    -- `empty-gate-must-fail` committed inside the gate written to enforce it. A None mutation is
    now a distinct hard failure. Ra is the right lever anyway: it is a divider leg outside the
    notch network, so it moves absolute level ~13-15 dB with every width intact to ~1 %.
    """
    print("\n  F ABS GAIN    is the downstream transfer D = render - ladder invariant to the")
    print("      ladder? If not, an ABSOLUTE ladder target cannot come from a render.")
    orig = A.load(A.ORIG)
    zb = M.ZSA[-M.NBB:]

    def d_of(tag, base, rd, c5t, d):
        out = {}
        for pos in POSITIONS:
            x = A.load(os.path.join(d, "%s_%s.wav" % (tag, pos)))
            x, _ = A.align(x, orig)
            f, m = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
            p = dict(base)
            p["Rd"] = rd[pos]
            p["C5"] = base["C5"] + c5t[pos]
            out[pos] = np.interp(FBB, f, m) - M.db(T.tf_tap(FBB, zb, T.TAP_OF[pos], p, 0.0))
        return out
    dp = d_of("prop", PROP, PROP_RD, PROP_C5T, RENDER_DIR)
    dc = d_of("cal", CAL, CAL_RD, CAL_C5T, CALDIR)     # ⚠ the SWEPT cal dir: both are main-signal
    worst = max(float(np.max(np.abs(dc[p] - dp[p]))) for p in POSITIONS)
    print("      F1 D median: %s"
          % " | ".join("%s prop %+.2f cal %+.2f" % (p, float(np.median(dp[p])),
                                                    float(np.median(dc[p]))) for p in POSITIONS))
    f1 = worst < 1.0
    print("      F1 worst |D_cal - D_prop| over the band = %.3f dB (limit 1.0)   %s"
          % (worst, "OK" if f1 else "FAIL -- the term is unfounded, do not fit it"))

    tgt_g = g_targets()
    ref = full_stats(PROP, PROP_RD, PROP_C5T)
    resid = {p: g_of(ref)[p] - tgt_g[p] for p in POSITIONS}
    rec = abs_gain_record()
    # ⚠ PER SUB-BAND, not pooled: a partition that silently dropped a region would still satisfy a
    # pooled F2, because the dropped region never enters either side of the identity.
    f2 = max(float(np.max(np.abs(resid[p] + rec[p]))) for p in POSITIONS) < 1e-9
    print("      F2 at PROP the g residual must BE -Delta, in every sub-band: worst |resid+Delta|"
          " %.2e over %d values   %s"
          % (max(float(np.max(np.abs(resid[p] + rec[p]))) for p in POSITIONS),
             len(POSITIONS) * len(G_SEL), "OK" if f2 else "FAIL"))

    mut = full_stats(dict(PROP, Ra=PROP["Ra"] * 10.0), PROP_RD, PROP_C5T)
    if mut is None:
        sys.exit("      F3 FAIL -- the mutation is PATHOLOGICAL, so g was never measured on it. "
                 "That is not a passing gate and must not be scored as 'no movement'.")
    dg = max(float(np.max(np.abs(g_of(mut)[p] - g_of(ref)[p]))) for p in POSITIONS)
    f3 = dg > 3.0
    print("      F3 mutation (tap Ra x10) must MOVE g: worst %.2f dB (limit > 3)   %s"
          % (dg, "OK" if f3 else "FAIL -- the term cannot see what it exists to police"))
    # ⭐⭐ F3b -- THE BLIND SPOT ITSELF, MEASURED. Score the SAME mutation with the pre-session-95
    # terms (the notch triple, each referred to its own shoulder, and h, a throw-to-throw ratio)
    # and with g. If the old terms barely move while g moves 13-15 dB, the degeneracy is
    # demonstrated on this file's own code path rather than argued from session 94's matrix run.
    def old_terms(st):
        rms = lambda v: float(np.sqrt(np.mean(np.square(v))))          # noqa: E731
        n = rms([(st["notch"][p][0] - tgt[p][0]) / RES_HZ for p in POSITIONS]
                + [(st["notch"][p][1] - tgt[p][1]) / M.DEPTH_FLOOR_DB for p in POSITIONS]
                + [(st["notch"][p][2] - tgt[p][2]) / (0.10 * tgt[p][2]) for p in POSITIONS])
        b = rms(np.concatenate([REC["h"][q] - st["h"][q] for q in THROWS]) / REC["floor"])
        return n, b
    n0, b0 = old_terms(ref)
    n1, b1 = old_terms(mut)
    print("      F3b the SAME mutation, scored by the PRE-95 terms vs by g:")
    print("          notch rms %6.2f -> %6.2f (%+.2f) | h rms %6.2f -> %6.2f (%+.2f) |"
          " g %+7.2f dB" % (n0, n1, n1 - n0, b0, b1, b1 - b0, dg))
    # ⚠ Reported per TERM, not as one combined threshold. A first version summed the two moves
    # against 25 % of dg and passed by 0.09 -- a verdict that close to its own bar is not a
    # finding. Separating them is also the truer statement, because the two terms are not scored
    # together anywhere: `best_point` stage 1 (which SELECTS the candidate) runs `wt_bb = 0.0`
    # with the tap PINNED, so the notch triple is the ONLY thing scoring the ladder there.
    blind_n, blind_h = abs(n1 - n0) < 0.1 * dg, abs(b1 - b0) < 0.5 * dg
    print("          => notch triple absorbs %.1f %% of the %.1f dB move (it is the ONLY term"
          % (100.0 * abs(n1 - n0) / dg, dg))
    print("             scoring stage 1, where the candidate is selected) -- %s"
          % ("BLIND" if blind_n else "NOT blind, re-read before relying on F3b"))
    print("             h absorbs %.1f %% (stage 2 only, and Ra is not a perfectly shared change:"
          % (100.0 * abs(b1 - b0) / dg))
    print("             it moves boost 14.9 dB against cut 12.9, so ~2 dB of it IS a ratio) -- %s"
          % ("blind enough" if blind_h else "NOT blind"))
    blind = blind_n and blind_h
    f4 = gate_region_of_validity(dp, orig, zb, worst)
    f5 = gate_pooled_blind(tgt_g, rec)
    ok = f1 and f2 and f3
    if not ok:
        sys.exit(1)
    print("      => OK. The absolute requirement, per throw AND sub-band (screen units, dB):")
    print("         %-14s %s" % ("sub-band",
                                 "  ".join("%-22s" % ("%s: now / want / move" % p)
                                           for p in POSITIONS)))
    for i, (lab, _, _) in enumerate(G_ACTIVE):
        print("         %-14s %s"
              % (lab, "  ".join("%+7.2f %+7.2f %+6.2f "
                                % (g_of(ref)[p][i], tgt_g[p][i], tgt_g[p][i] - g_of(ref)[p][i])
                                for p in POSITIONS)))
    return tgt_g, dict(d_invariance=worst, mutation_dg=dg, blind=bool(blind),
                       partition=[list(s) for s in G_ACTIVE],
                       bins=check_g_partition(),
                       region_of_validity=f4, pooled_blind=f5,
                       delta={p: rec[p].tolist() for p in POSITIONS},
                       target={p: tgt_g[p].tolist() for p in POSITIONS},
                       prop_now={p: g_of(ref)[p].tolist() for p in POSITIONS})


# ---- FitParams --fit list -> the screen's own ladder parameterisation -------------------------
# ⚠ ONE definition, used by GATE F4/F5 here AND by attack_d_extrapolation_gate.py. A second copy
# is how a gate and the thing it gates stop describing the same network (the `resid()` lesson,
# session 97, applied to the ladder itself).
FIT_MAP = {"attackTapRa": "Ra", "attackTapRb": "Rb", "attackTapRc": "Rc", "attackTapR11": "R11",
           "trebleR7": "R7", "trebleLadderR12": "R12", "trebleLadderR14": "R14",
           "trebleC9": "C9", "trebleC6": "C6", "trebleC7": "C7", "trebleC5": "C5"}
RD_MAP = {"trebleLadderDampR": "flat", "attackDampBoost": "boost", "attackDampCut": "cut"}
C5T_MAP = {"attackC5TrimBoost": "boost", "attackC5TrimCut": "cut"}
WILD_FITS = "analysis/reports/s97_attack_best_posttap.json"
WILD_DIR = "build/attack_d_extrap"


def ladder_from_fits(fits, strict=True):
    """-> (base, rd, c5t) in the screen's parameterisation. Unmapped names are a hard error:
    a silently unmapped element leaves that value at PROP, making the modelled ladder a DIFFERENT
    network from the rendered one -- the one error these gates cannot survive."""
    base, rd, c5t = dict(PROP), dict(PROP_RD), {p: 0.0 for p in POSITIONS}
    for f in fits:
        k, _, v = f.partition("=")
        v = float(v)
        if k in FIT_MAP:
            base[FIT_MAP[k]] = v
        elif k in RD_MAP:
            rd[RD_MAP[k]] = v
        elif k in C5T_MAP:
            c5t[C5T_MAP[k]] = v
        elif k == "trebleC8":
            if v != 0.0:
                sys.exit("trebleC8 = %g: these gates model the C8 = 0 network only" % v)
        elif strict:
            sys.exit("unmapped --fit name %r -- refusing (see FIT_MAP)" % k)
    return base, rd, c5t


def _load_wild():
    """The one WILD ladder this project has both fitted AND rendered. None if either is absent."""
    if not os.path.exists(WILD_FITS):
        return None
    d = json.load(open(WILD_FITS))
    fits = d.get("fits") or (d.get("best") or {}).get("fits")
    if not fits:
        return None
    return ladder_from_fits(fits)


def ladder_distance(base):
    """How far a ladder sits from PROP, in decades: max |log10 multiplier| over SHARED + TAP.

    ⚠ A MAX, not an rms. The question F4 asks is whether the fit has left the region where the
    invariance was measured, and one element three decades out does that on its own -- averaging
    it against six mild ones is `difference-statistics-hide-common-mode` in the units of the very
    thing being policed.
    """
    return max(abs(np.log10(base[e] / PROP[e])) for e in SHARED + list(TAP))


def gate_region_of_validity(dp, orig, zb, worst_mild):
    """F4 -- OVER WHAT REGION IS F1's INVARIANCE ACTUALLY ESTABLISHED?

    ⚠⚠ F1 compares PROP and CAL. They are very different FROM EACH OTHER and BOTH close to the
    drawn network, so F1 is an INTERPOLATION check -- and session 95 onward relied on it as an
    EXTRAPOLATION guarantee, which is what `imposed-checks-cannot-corroborate` warns about one
    level up. Session 98 measured the gap (GATE H2): at the session-97 winner the worst
    |D_cand - D_prop| is 3.84 dB, 21x F1's own 0.183.
    ⛔ This does NOT close the hole, and saying so is the point. The only complete check is D
    measured at the ACTUAL candidate, which needs a render of it -- that is
    `attack_d_extrapolation_gate.py`, and it stays a REQUIRED step between `--best` and the
    matrix. What F4 does is turn an unstated assumption into a stated, measured limit, so
    `best_point` can report how far its winner sits outside it instead of nobody asking.
    """
    print("      F4 REGION OF VALIDITY -- F1 compares two MILD ladders. Where does D stop being")
    print("         invariant? (the one WILD ladder with a render on disk: the s97 winner)")
    print("         %-26s %9s %11s" % ("ladder", "distance", "worst |dD|"))
    print("         %-26s %8.2f %11.3f   <- F1's own pair" % ("CAL vs PROP", ladder_distance(CAL),
                                                              worst_mild))
    wild = _load_wild()
    if wild is None or not all(os.path.exists(os.path.join(WILD_DIR, "cand_%s.wav" % p))
                               for p in POSITIONS):
        print("         ⚠ SKIPPED, not silently: %s / %s absent. The envelope is UNMEASURED and"
              % (WILD_FITS, WILD_DIR))
        print("           the term is being used as an extrapolation on an untested premise.")
        return dict(measured=False, mild=float(worst_mild), mild_distance=ladder_distance(CAL))
    wb, wrd, wc5t = wild
    dw = {}
    for pos in POSITIONS:
        x = A.load(os.path.join(WILD_DIR, "cand_%s.wav" % pos))
        x, _ = A.align(x, orig)
        f, m = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
        p = dict(wb)
        p["Rd"] = wrd[pos]
        p["C5"] = wb["C5"] + wc5t[pos]
        dw[pos] = np.interp(FBB, f, m) - M.db(T.tf_tap(FBB, zb, T.TAP_OF[pos], p, 0.0))
    wild_worst = max(float(np.max(np.abs(dw[p] - dp[p]))) for p in POSITIONS)
    dist = ladder_distance(wb)
    print("         %-26s %8.2f %11.3f   <- the fit's own reach" % ("s97 winner vs PROP", dist,
                                                                    wild_worst))
    print("         => the invariance holds to %.3f dB out to %.2f decades and degrades to"
          " %.2f dB\n            at %.2f decades. Treat %.2f dec as the tested limit; beyond it"
          % (worst_mild, ladder_distance(CAL), wild_worst, dist, ladder_distance(CAL)))
    print("            `g` is an extrapolation and MUST be re-checked at the candidate by"
          " attack_d_extrapolation_gate.py.")
    return dict(measured=True, mild=float(worst_mild), mild_distance=ladder_distance(CAL),
                wild=float(wild_worst), wild_distance=float(dist))


def gate_pooled_blind(tgt_g, rec):
    """F5 -- can the POOLED median see what the per-sub-band residual does? (session 99)

    The same computed-not-asserted standard F3b applied to the session-95 term, now applied to the
    session-99 one -- and with a KNOWN ANSWER rather than a synthetic mutation: the session-97
    winner is a ladder the pooled term scored as SATISFIED (+0.34 / -0.03 / +0.39 dB) and the
    129-capture matrix rejected at OD 25-100 Hz p90 6.065 -> 20.958.
    ⚠ Runs on the LADDER only -- both statistics are ladder-side -- so it needs no render and is
    not affected by F4's invariance question.
    """
    wild = _load_wild()
    if wild is None:
        print("      F5 SKIPPED, not silently: %s absent, so the blind spot is UNDEMONSTRATED"
              % WILD_FITS)
        return dict(measured=False)
    if len(G_SEL) == 1:
        print("      F5 n/a -- the ACTIVE partition IS the pooled one (--g-pooled control run)")
        return dict(measured=False, pooled_run=True)
    st = full_stats(*wild)
    if st is None:
        print("      F5 FAIL -- the known-answer ladder is pathological in this screen; it cannot")
        print("         be scored, which is a hard failure, not 'no movement' (empty-gate-must-fail)")
        return dict(measured=False, pathological=True)
    ref = full_stats(PROP, PROP_RD, PROP_C5T)
    gw, g0 = g_of(st), g_of(ref)
    print("      F5 BLIND SPOT, on the KNOWN ANSWER (the s97 winner the matrix rejected):")
    print("         %-14s %10s %10s %10s" % ("sub-band", "cut", "boost", "flat"))
    per = {}
    for i, (lab, _, _) in enumerate(G_ACTIVE):
        row = [float((gw[p][i] - g0[p][i]) - rec[p][i]) for p in POSITIONS]
        per[lab] = row
        print("         %-14s %+10.2f %+10.2f %+10.2f" % (lab, *row))
    allv = np.concatenate([gw[p] - g0[p] - rec[p] for p in POSITIONS])
    sub_rms = float(np.sqrt(np.mean(np.square(allv))))
    # The SAME ladder scored by the pre-99 pooled median: (pooled ladder move) - (pooled Delta).
    pd = _pooled_delta()
    pooled = [float(np.median(st["gabs"][p][G_BAND]) - np.median(ref["gabs"][p][G_BAND]) - pd[p])
              for p in POSITIONS]
    pooled_rms = float(np.sqrt(np.mean(np.square(pooled))))
    print("         pooled median (the pre-99 term): %s   rms %.2f dB"
          % ("  ".join("%s %+6.2f" % (p, v) for p, v in zip(POSITIONS, pooled)), pooled_rms))
    print("         per sub-band                   : worst %+.2f dB   rms %.2f dB"
          % (allv[int(np.argmax(np.abs(allv)))], sub_rms))
    blind = abs(pooled_rms) < 0.2 * sub_rms
    print("         => the pooled median absorbs %.1f %% of what the sub-band residual sees -- %s"
          % (100.0 * pooled_rms / max(sub_rms, 1e-9),
             "BLIND, as session 98 measured" if blind else
             "NOT blind: re-read before relying on the repair"))
    return dict(measured=True, pooled_rms=pooled_rms, subband_rms=sub_rms,
                blind=bool(blind), per_band=per)


_PD = None


def _pooled_delta():
    """Delta measured the PRE-99 way -- ONE median over the whole of G_BAND -- for F5's control.
    Independent of the ACTIVE partition by construction, which is what makes it a control."""
    global _PD
    if _PD is not None:
        return _PD
    orig = A.load(A.ORIG)
    with redirect_stdout(io.StringIO()):
        caps = P.load_all(orig)

    def on_fbb(sig):
        x, _ = A.align(sig, orig)
        f, m = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
        return np.interp(FBB, f, m)
    _PD = {}
    for pos in POSITIONS:
        r = A.load(os.path.join(RENDER_DIR, "prop_%s.wav" % pos))
        _PD[pos] = float(np.median((on_fbb(caps[pos]) - on_fbb(r))[G_BAND]))
    return _PD


# =============================================================================================
# the fit
# =============================================================================================
SHARED = ["R7", "R12", "R14", "C5", "C9", "C6", "C7"]
TAP = ["Ra", "Rb", "Rc", "R11"]
BOX = 1.0                                                 # decades, each side (see box_sweep)
TAP_BOX = 1.0                                             # decades -- STAGE 2's own box
# ⭐⭐ SESSION 98 -- THE BOX IS NOW PER-DIMENSION, AND THE REASON IS A SPECIFIC ONE, NOT TIDINESS.
# Session 97's winner rested exactly two of seventeen values on their bounds -- `C9` at the ladder
# box floor (x0.1) and `Ra` at the tap box floor (x0.1) -- and BOTH at the SMALL end, i.e. the
# search wants them smaller than the box allows. A parameter on its bound is not a value, it is a
# missing equation (`bound-resting-means-unidentified`), so the point cannot be proposed; and with
# ONE global box the only way to free them is to widen every dimension at once, which is precisely
# what buys the R7 x119 / R12 x402 candidates session 97 rejected. A per-dimension FLOOR frees the
# two dimensions that are asking, and nothing else.
# ⚠ Deepening a floor is NOT a fix in itself. If the cost is monotone toward zero in that
# dimension, a deeper floor just moves the rail further out and the parameter stays unidentified
# (`a monotone objective with no interior minimum is a degeneracy, not a fit`). That is what
# `bound_profile()` is for, and it runs BEFORE any floor sweep.
FLOOR_DIMS = ("C9", "Ra")                                 # what session 97 left on a bound
DEF_ROWS = "analysis/reports/s97_attack_best_posttap.json"   # the point --floor-probe profiles


def dim_names(shared, fit_tap):
    """The x-vector's coordinate names, in order. ⚠ ONE definition -- `show()`, `best_point()` and
    the bounds all used to build this list inline, which is how a coordinate and its label drift
    apart."""
    n = list(shared) + ["Rd " + p for p in POSITIONS] + ["C5t " + p for p in POSITIONS]
    return n + (list(TAP) if fit_tap else [])


def dim_bounds(shared, fit_tap, box=BOX, floors=None):
    """Per-dimension search bounds, as a list of (lo, hi) in x-space.

    `floors[name] = d` deepens THAT dimension's lower bound to -d decades; every other dimension
    stays symmetric at +-box. With `floors` empty this returns exactly `[(-box, box)] * nd`, which
    is the known-answer control every caller below is checked against.
    ⛔ A floor on a `C5t` dimension is REFUSED: those coordinates are LINEAR, mapped onto
    [0, 0.3*C5] by build(), so moving their bound silently redefines the codomain rather than
    widening a search -- the session-97 defect in a new costume.
    """
    out = []
    for nm in dim_names(shared, fit_tap):
        lo, hi = -box, box
        if floors and nm in floors:
            if nm.startswith("C5t"):
                raise ValueError("floor on a LINEAR C5-trim dimension (%s) -- see dim_bounds" % nm)
            lo = -float(floors[nm])
        out.append((lo, hi))
    return out


def on_bound_mask(x, bnds, tol=0.03):
    """Which coordinates rest on a bound. Generalised from `abs(abs(xi) - box) < 0.03 * box`,
    which it reproduces EXACTLY for symmetric bounds (half = box; the min-distance to either end
    equals |‌|xi| - box| inside the range)."""
    m = []
    for xi, (lo, hi) in zip(x, bnds):
        half = 0.5 * (hi - lo)
        m.append(bool(min(abs(xi - lo), abs(xi - hi)) < tol * half))
    return m
# ⚠ The record quotes f0 on the 5.86 Hz measurement grid, so an f0 rms below a quarter bin is
# not a real difference between two candidates -- see the ranking note in best_point().
F0_TIE_BINS = 0.25
# ⚠ The same rule for WIDTH: `w_rms` is in units of 10 % of the target width, so 0.1 = 1 % of
# width -- just above GATE B's demonstrated 0.94 % worst recovery error on the stepped grid, and
# far inside GATE C's +-5-10 % transfer to the render. Anything under that is a tie. See the
# ranking note in best_point() for the run that made this necessary.
W_TIE_RMS = 0.1
# ⚠ And the same rule for the ABSOLUTE level (session 95): `g_rms` is in units of G_FLOOR_DB, so
# 1.0 = 1 dB -- at the scale of the term's own transfer accuracy (gate F's 0.28 dB D-invariance
# plus the 0.27 dB level-dependence of the measurement). Below that two candidates are tied.
G_TIE_RMS = 1.0


def build(x, shared, fit_tap, box=BOX, bnds=None):
    """x = [shared multipliers..., Rd per throw..., C5trim per throw..., tap multipliers...]

    ⚠⚠ `box` IS NOT DECORATION -- the C5-trim dims are LINEAR, not log, so they are the one
    group whose physical range does NOT follow the search box, and normalising them by the
    module-level BOX instead of the ACTIVE box is a real defect (found session 97). The
    docstring below promises a codomain of [0, 0.3*C5]; at box = 3.0 the old line delivered
    [-0.3*C5, +0.6*C5] instead -- half of it a NEGATIVE additive cap, and the top of it a trim
    no box-1.0 candidate could ever reach. It went unnoticed for 31 sessions because every
    winner since session 66 was a box-1.0 row, where box == BOX and the two agree exactly; the
    session-97 ranking-key fix selected the project's first box-3.0 winner and 3 of the 5
    box-3.0 rows were sitting outside the documented range (trims 0.322, 0.312, 0.465 x C5).
    ⭐ GENERAL: when a search SETTING is swept, every mapping that reads it has to read the
    swept value -- a hardcoded copy of the default is invisible until the sweep first wins.
    ⭐ SESSION 98 generalises that fix rather than repeating it: the trim now reads its OWN
    dimension's (lo, hi) out of `bnds`, so a per-dimension box cannot reintroduce the same defect.
    With symmetric bounds mid = 0.0 and half = box EXACTLY (both are power-of-two operations on
    the same float), so the expression below is bit-identical to the session-97 line -- which is
    the control that keeps every box-1.0 row reproducible across the change.
    """
    if bnds is None:
        bnds = [(-box, box)] * ndim(shared, fit_tap)
    base = dict(PROP)
    k = 0
    for e in shared:
        base[e] = PROP[e] * 10.0 ** x[k]; k += 1
    rd = {}
    for pos in POSITIONS:
        rd[pos] = PROP_RD[pos] * 10.0 ** x[k]; k += 1
    c5t = {}
    for pos in POSITIONS:
        # Trims are ADDITIVE parallel caps on the same pole (session 62 item 7), so they must
        # stay >= 0. ⚠ Mapped LINEARLY onto [0, 0.3*C5] rather than as a log multiplier: a
        # `max(0, C5*(10**x - 1))` form (a first draft) sends the whole negative half of the box
        # to exactly 0, i.e. half the search space is one flat point -- a self-inflicted
        # degeneracy of the kind session 52 item 3(c) had to diagnose in real data.
        lo, hi = bnds[k]
        mid, half = 0.5 * (hi + lo), 0.5 * (hi - lo)
        c5t[pos] = base["C5"] * 0.3 * 0.5 * ((x[k] - mid) / half + 1.0); k += 1
    if fit_tap:
        for e in TAP:
            base[e] = PROP[e] * 10.0 ** x[k]; k += 1
    return base, rd, c5t


def resid(st, tgt, tgt_g=None):
    """The five scored residuals of a BUILT network -- ONE definition, so the ranking and the
    objective cannot drift apart. Returns (notch_rms, f0_rms, w_rms, dep_rms, g_rms).

    ⚠ Factored out in session 97 because `best_point` now has to score a network it did NOT get
    from `Cost` (the POST-tap one -- see the stage-2 note there). A second copy of this arithmetic
    is exactly how a ranking silently stops measuring what the objective measures.
    """
    f0r, depr, wr = [], [], []
    for pos in POSITIONS:
        f0, dep, w = st["notch"][pos]
        tf0, tdep, tw = tgt[pos]
        # ⚠ RES_HZ, not M.BIN_HZ: the normaliser is the ACTIVE instrument's own resolution
        # (5.86 Hz swept, 2.0 Hz stepped), so a finer instrument weights f0 harder. Printed by
        # main(); the frontier sweeps w_f0 on top of it, so no conclusion rests on the choice.
        f0r.append((f0 - tf0) / RES_HZ)                    # in units of the read's resolution
        depr.append((dep - tdep) / M.DEPTH_FLOOR_DB)       # dB, floor 1 dB (a bound)
        wr.append((w - tw) / (0.10 * tw))                  # 10 % of the target width
    rms = lambda v: float(np.sqrt(np.mean(np.square(v))))   # noqa: E731
    gr = ([(g_of(st)[p] - tgt_g[p]) / G_FLOOR_DB for p in POSITIONS] if tgt_g else [0.0])
    return rms(f0r + depr + wr), rms(f0r), rms(wr), rms(depr), rms(gr)


def realisable(x, box=BOX, bnds=None):
    """Can `FitParams` express this point's three per-throw C5 values AT ALL?

    ⛔⛔ SESSION 97 -- THIS IS A HARD FEASIBILITY TEST, NOT A QUALITY SCORE, AND IT HAD TO BECOME
    THE FIRST TERM OF THE RANKING KEY. The C++ realisation is ONE base `trebleC5` plus TWO
    additive parallel trims, `attackC5TrimBoost` and `attackC5TrimCut` -- there is no
    `attackC5TrimFlat`. Trims are parallel caps so they must be >= 0, which means the base has to
    be rebased on the SMALLEST of the three throws, which means **flat must BE the smallest** or
    the flat throw needs a trim that does not exist. The screen has printed that gap since
    session 62 ("recorded not hidden") but never RANKED on it -- and the moment session 97's
    identifiability fix changed the selection, the new winner was one of the 2 rows in 10 that
    fail it, off by 0.25 nF (~4 %) on flat. ⭐ A candidate that cannot be rendered cannot be
    judged by the render or by the matrix, so it is not merely a worse candidate than an
    unidentified one -- it is not a candidate. Rank feasibility ahead of everything discretionary.
    ⚠ Deliberately a RANKING term rather than a search constraint: constraining the fit would hide
    how much the requirement costs, and the failing rows stay printed and stay in `rows`.
    """
    c5t = build(x, SHARED, False, box, bnds)[2]
    return c5t["flat"] <= min(c5t.values()) + 1e-18


def ndim(shared, fit_tap):
    return len(shared) + 2 * len(POSITIONS) + (len(TAP) if fit_tap else 0)


class Cost:
    """Notch triple in the screen's units + the broadband h + the ABSOLUTE OD magnitude.

    `w_f0` scales the f0 term ONLY, so the f0-vs-width conflict can be traced as a PARETO
    FRONTIER instead of being hidden inside one weighted number (session 49/52's move: report
    the frontier, because a single weight silently picks a trade for you).

    ⭐⭐ `wt_g` IS SESSION 95's ADDITION AND IT IS NOT A REFINEMENT. Every other term here is
    RELATIVE -- the notch triple to each throw's own shoulder, `h` to the flat throw -- so a
    change shared by all three throws is invisible to the whole objective, which is how session
    94's fit met the ATTACK requirement while putting the OD path 40-47 dB down. `g` is the
    ladder's ABSOLUTE level against a bleed-free measurement of the pedal's (see `g_targets`).
    ⚠ `wt_g = 0` reproduces the pre-session-95 objective exactly and is kept as the control.
    """

    def __init__(self, shared, tgt, fit_tap=True, wt_bb=1.0, override=None, w_f0=1.0,
                 tgt_g=None, wt_g=1.0, box=BOX, bnds=None):
        self.shared, self.tgt, self.fit_tap, self.wt_bb = list(shared), tgt, fit_tap, wt_bb
        self.override, self.w_f0 = override, w_f0
        self.tgt_g, self.wt_g = tgt_g, (wt_g if tgt_g else 0.0)
        self.box = box                       # the ACTIVE box -- see build()'s docstring
        self.bnds = bnds                     # the ACTIVE per-dimension bounds (session 98)

    def parts(self, x):
        base, rd, c5t = build(x, self.shared, self.fit_tap, self.box, self.bnds)
        st = full_stats(base, rd, c5t)
        if st is None:
            return None
        t = self.override if self.override is not None else self.tgt
        notch, f0r, wr, depr, gr = resid(st, t, self.tgt_g)
        br = np.concatenate([REC["h"][q] - st["h"][q] for q in THROWS]) / REC["floor"]
        rms = lambda v: float(np.sqrt(np.mean(np.square(v))))   # noqa: E731
        return (notch, rms(br), st, f0r, wr, depr, gr)

    def __call__(self, x):
        r = self.parts(x)
        if r is None:
            return 1e6
        _, b, _, f0, w, dep, g = r
        n = float(np.sqrt((self.w_f0 * f0 * f0 + w * w + dep * dep) / (self.w_f0 + 2.0)))
        c = float(np.sqrt((n * n + self.wt_bb * b * b + self.wt_g * g * g)
                          / (1.0 + self.wt_bb + self.wt_g)))
        # BACKSTOP for the same class of failure as GATE E's second clause: a nan that reaches the
        # optimiser is worse than a large cost, because it is not ORDERED against anything.
        return c if np.isfinite(c) else 1e6


def run(shared, tgt, fit_tap=True, quick=False, seed=17, override=None, wt_bb=1.0, w_f0=1.0,
        box=None, tgt_g=None, wt_g=1.0, floors=None):
    box = BOX if box is None else box
    # ⚠ box AND the bounds are resolved BEFORE Cost is built -- Cost hands them to build() for the
    # linear C5-trim dims, so constructing Cost first (as a draft did) would silently pin them to
    # the default. ⚠ ONE bounds list feeds both the optimiser and build(); a second copy is how a
    # search space and its coordinate mapping drift apart.
    bnds = dim_bounds(shared, fit_tap, box, floors)
    c = Cost(shared, tgt, fit_tap, wt_bb, override, w_f0, tgt_g, wt_g, box, bnds)
    r = differential_evolution(c, bnds, seed=seed,
                               maxiter=80 if quick else 200, popsize=12 if quick else 20,
                               tol=1e-10, polish=True, init="sobol", workers=-1,
                               updating="deferred")
    return r.fun, r.x, c.parts(r.x)


def frontier(tgt, quick, tgt_g=None):
    """⭐ THE DECIDING MEASUREMENT. Is the width reachable WHILE the notch triple is held?

    The tap is PINNED here, and that is not a shortcut -- the census proves it moves width by
    <=0.5 Hz and f0 by 0.00 Hz, so it carries no notch information at all, and session 62 item 4
    established the rule: when a joint objective under-delivers on one requirement, SEPARATE the
    fits before calling it unreachable, because scoring non-interacting groups jointly buys
    nothing and costs arbitration. The broadband is therefore dropped from this objective too
    (wt_bb = 0) and re-checked afterwards with the tap free.

    Sweeping the f0 weight traces the frontier: if a point exists with f0 held to the bin AND the
    width right, some weight finds it. If instead width is stuck near its current value whenever
    f0 is held, the two requirements are in CONFLICT inside this topology -- which is a structural
    statement, not a fit failure.
    """
    print("\n" + "=" * 104)
    print("⭐ THE FRONTIER -- can WIDTH be reached while the NOTCH TRIPLE is held? (tap PINNED:")
    print("   the census says it carries no notch information, so scoring it here only arbitrates)")
    print("=" * 104)
    print("  %6s | %8s %8s %8s %8s | %-22s | %s"
          % ("w_f0", "f0 rms", "width", "depth", "g abs", "f0 cut/boost/flat Hz",
             "width cut/boost/flat Hz"))
    print("  %6s | %8s %8s %8s %8s | want %5.1f %5.1f %5.1f    | want %5.1f %5.1f %5.1f"
          % ("", "(bins)", "(rms)", "(rms)", "(rms dB)",
             *[tgt[p][0] for p in POSITIONS], *[tgt[p][2] for p in POSITIONS]))
    rows = []
    for w_f0 in (0.0, 0.3, 1.0, 3.0, 10.0, 100.0):
        c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=w_f0,
                          tgt_g=tgt_g)
        if parts is None:
            continue
        _, _, st, rf0, rw, rdep, rg = parts
        f0s = [st["notch"][p][0] for p in POSITIONS]
        ws = [st["notch"][p][2] for p in POSITIONS]
        print("  %6.1f | %8.2f %8.2f %8.2f %8.2f | %6.1f %6.1f %6.1f  | %6.1f %6.1f %6.1f"
              "  (spread %.1f Hz)"
              % (w_f0, rf0, rw, rdep, rg, *f0s, *ws, max(f0s) - min(f0s)))
        rows.append(dict(w_f0=w_f0, f0_rms=rf0, w_rms=rw, dep_rms=rdep, g_rms=rg,
                         f0=f0s, width=ws, spread=max(f0s) - min(f0s),
                         x=[float(v) for v in x]))
    print("\n  required f0 spread = %.2f Hz (the pedal's, session 61). The DRAWN topology gives"
          % (max(tgt[p][0] for p in POSITIONS) - min(tgt[p][0] for p in POSITIONS)))
    print("  0.00 Hz and session 61 found 0 of 782 random draws reproducing the pedal's pattern,")
    print("  so a fit that reaches the width by COLLAPSING the spread has given up the requirement")
    print("  that made the two-pole topology necessary in the first place -- read the spread column.")

    # ⭐⭐ THE BOX SWEEP. A large residual with all 13 values free is only readable as
    # UNREACHABILITY if widening the search does not shrink it. Session 57 item 4's own test:
    # there the cost moved 0.001 dB across 7.5 orders of magnitude of box widening, which is what
    # "the objective cannot reach this direction" looks like. Run at the weight that scores all
    # nine numbers equally.
    print("\n  BOX SWEEP at w_f0 = 1 (all 9 numbers scored equally, %d free values):"
          % ndim(SHARED, False))
    print("  %8s | %8s %8s %8s %8s %8s | %s"
          % ("box", "cost", "f0 rms", "width", "depth", "g abs", "on a bound"))
    sweep = []
    for box in (0.5, 1.0, 2.0, 3.0):
        c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=1.0, box=box,
                          tgt_g=tgt_g)
        if parts is None:
            continue
        ob = [e for e, m in zip(dim_names(SHARED, False),
                                on_bound_mask(x, dim_bounds(SHARED, False, box))) if m]
        print("  %8.1f | %8.4f %8.2f %8.2f %8.2f %8.2f | %s"
              % (box, c, parts[3], parts[4], parts[5], parts[6], ", ".join(ob) if ob else "-"))
        sweep.append(dict(box=box, cost=float(c), f0_rms=parts[3], w_rms=parts[4],
                          dep_rms=parts[5], g_rms=parts[6], on_bound=ob))
    if len(sweep) > 1:
        span = max(s["cost"] for s in sweep) - min(s["cost"] for s in sweep)
        print("  ⇒ cost moves %.4f across %.0fx of box widening in EVERY one of %d free values."
              % (span, (sweep[-1]["box"] / sweep[0]["box"]), ndim(SHARED, False)))
        print("    %s" % ("SATURATED -- read the residual as UNREACHABILITY, not a weak search."
                          if span < 0.35 else
                          "NOT saturated -- the search is still finding room; do not call this "
                          "unreachable yet."))
    return dict(frontier=rows, box_sweep=sweep)


# =============================================================================================
# ⭐⭐ WHY the conflict, if there is one: the ladder is exactly frequency-scale-invariant, and
# exactly ONE cap in the path cannot be scaled with it.
# =============================================================================================
def scale_diagnostic(tgt, quick, tgt_g=None):
    """Localise the f0-vs-width conflict to the J201 drain pole.

    THE ALGEBRA. This network is R and C only, so scaling EVERY capacitance by 1/k with every
    resistance fixed maps H(s) -> H(ks) exactly: the curve is translated in frequency with its
    SHAPE (and therefore every Q, every half-depth width in octaves) untouched. That is the same
    scale invariance A2c-3 used to make the mid stage constant-Q at all three switch positions.

    ⇒ If the shape were reachable at ANY frequency, it would be reachable at the RIGHT frequency,
    just by scaling the caps -- unless some capacitance in the path cannot be scaled. Three caps
    are candidates: C5/C9/C6 (the ladder, free), C7 (the coupling cap, free) and `Cp` -- the
    J201 drain network's own pole, Rp*Cp = R6*C3, which is NOT part of the treble stage at all.
    It is the JfetStage boundary, anchored by session 4's gm fit, and its corner sits at
    ~220-720 Hz, i.e. INSIDE the notch region.

    So this runs the frontier's own objective twice: once as shipped, and once with a single extra
    free value that scales `Cp` together with the ladder caps. ⚠ THE SECOND RUN IS A DIAGNOSTIC,
    NOT A PROPOSAL -- Cp is the J201 boundary and moving it is a claim about the JFET, not about
    ATTACK. It is here to answer WHERE the constraint lives, exactly as session 40 used a
    rails-off render to localise a level-axis residual without proposing to ship rails off.
    """
    print("\n" + "=" * 104)
    print("⭐⭐ WHERE THE CONSTRAINT LIVES -- the ladder is scale-invariant, so a shape reachable at")
    print("   ANY frequency is reachable at the RIGHT one, UNLESS an unscalable cap is in the path.")
    print("   The only one is the J201 drain's Cp (Rp*Cp = R6*C3, corner ~220-720 Hz = in the notch")
    print("   region). ⚠ Freeing it is a DIAGNOSTIC, not a proposal: it is the JfetStage boundary.")
    print("=" * 104)
    rows = {}
    for lab, free_cp in (("Cp FIXED (as shipped)", False), ("Cp scalable (DIAGNOSTIC)", True)):
        best = None
        for kscale in ([0.0] if not free_cp else [-0.30, -0.20, -0.10, 0.0, 0.10, 0.20]):
            zs = ZNOTCH if not free_cp else E.jfet_source_z(
                FNOTCH, **dict(M.ZS, C3=220.0e-9 * 10.0 ** kscale))
            global ZNOTCH_OVERRIDE
            ZNOTCH_OVERRIDE = zs
            c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=1.0,
                              tgt_g=tgt_g)
            ZNOTCH_OVERRIDE = None
            if parts is None:
                continue
            if best is None or c < best[0]:
                best = (c, kscale, parts)
        if best is None:
            continue
        c, kscale, parts = best
        f0s = [parts[2]["notch"][p][0] for p in POSITIONS]
        ws = [parts[2]["notch"][p][2] for p in POSITIONS]
        print("  %-26s cost %.4f | f0 rms %.2f bins  width rms %.2f  depth rms %.2f"
              % (lab, c, parts[3], parts[4], parts[5]))
        print("  %-26s f0 %6.1f %6.1f %6.1f (spread %.1f)  width %6.1f %6.1f %6.1f%s"
              % ("", *f0s, max(f0s) - min(f0s), *ws,
                 "" if not free_cp else "   C3 x%.2f" % (10.0 ** kscale)))
        rows[lab] = dict(cost=float(c), f0_rms=parts[3], w_rms=parts[4], dep_rms=parts[5],
                         f0=f0s, width=ws, c3_scale=10.0 ** kscale)
    print("  want%22s f0 %6.1f %6.1f %6.1f (spread %.1f)  width %6.1f %6.1f %6.1f"
          % ("", *[tgt[p][0] for p in POSITIONS],
             max(tgt[p][0] for p in POSITIONS) - min(tgt[p][0] for p in POSITIONS),
             *[tgt[p][2] for p in POSITIONS]))
    if len(rows) == 2:
        a, b = [rows[k]["cost"] for k in rows]
        print("\n  ⇒ %s" % ("freeing Cp does NOT relieve the conflict (%.4f -> %.4f), so the "
                            "constraint is\n    NOT the J201 drain pole -- look elsewhere."
                            % (a, b) if b > 0.75 * a else
                            "freeing Cp RELIEVES the conflict (%.4f -> %.4f) ⇒ the notch's absolute\n"
                            "    frequency is pinned against the J201 DRAIN POLE, and the ladder can "
                            "set the\n    null's frequency or its Q but not both. That is a "
                            "PRE-treble constraint, not an\n    ATTACK one -- and it is a NEW place "
                            "to look, not a value to ship." % (a, b)))
    return rows


def show(tag, cost, x, parts, shared, fit_tap, tgt, tgt_g=None, box=BOX):
    n, b, st = parts[0], parts[1], parts[2]
    print("\n  %s" % tag)
    print("    cost %.4f   (notch %.4f, broadband %.4f, g abs %.4f)   dof %d vs 9 notch numbers"
          % (cost, n, b, parts[6], ndim(shared, fit_tap)))
    print("    %-6s | %-22s | %-22s | %s"
          % ("throw", "f0 Hz  got / want", "depth dB  got / want", "width Hz  got / want"))
    for pos in POSITIONS:
        f0, dep, w = st["notch"][pos]
        tf0, tdep, tw = tgt[pos]
        print("    %-6s | %7.2f / %7.2f (%+5.2f) | %7.2f / %7.2f (%+5.2f) | %6.1f / %6.1f (%+5.1f%%)"
              % (pos, f0, tf0, f0 - tf0, dep, tdep, dep - tdep, w, tw, 100.0 * (w - tw) / tw))
    for q in THROWS:
        med, slp = st["shape"][q]
        pm = float(np.median(REC["h"][q]))
        print("    h %-4s median %+6.2f (pedal %+6.2f)   slope %+6.2f dB/dec"
              % (q, med, pm, slp))
    # ⭐ THE ABSOLUTE LEVEL, printed beside the relative terms so an h-correct-but-absolutely-wrong
    # candidate cannot read as a success again (session 95; the whole of session 94's failure).
    if tgt_g:
        print_g_table(g_of(st), tgt_g)
    base, rd, c5t = build(x, shared, fit_tap, box)
    # ⚠ bound-check EVERY free value, not just the shared ones. A first draft checked only
    # `shared` and the TAP was quietly running to x1/10 (x ~= -0.975 of a 1-decade box) --
    # a parameter on its bound is unidentified, not a value (bound-resting-means-unidentified).
    # ⚠ Against the ACTIVE box, not the module default -- same defect as build()'s, and harmless
    # here today only because every caller of show() uses the default box (session 97).
    names = dim_names(shared, fit_tap)
    on_bound = [e for e, m in zip(names, on_bound_mask(x, dim_bounds(shared, fit_tap, box))) if m]
    print("    shared: %s" % "  ".join("%s %.3g (x%.2f)" % (e, base[e], base[e] / PROP[e])
                                       for e in shared))
    print("    per throw Rd: %s" % "  ".join("%s %.0f" % (p, rd[p]) for p in POSITIONS))
    print("    per throw C5: %s" % "  ".join("%s %.3g" % (p, base["C5"] + c5t[p])
                                             for p in POSITIONS))
    if fit_tap:
        print("    tap: %s" % "  ".join("%s %.3g" % (e, base[e]) for e in TAP))
    if on_bound:
        print("    ⚠ ON A BOUND (unidentified, not a value): %s" % ", ".join(on_bound))
    return dict(cost=cost, notch=n, broadband=b, g_abs=parts[6], on_bound=on_bound,
                g=g_json(g_of(st)), g_bands=g_labels(),
                got={p: list(st["notch"][p]) for p in POSITIONS},
                shape={q: list(st["shape"][q]) for q in THROWS},
                shared={e: base[e] for e in shared},
                rd=dict(rd), c5={p: base["C5"] + c5t[p] for p in POSITIONS},
                tap=({e: base[e] for e in TAP} if fit_tap else None))


# =============================================================================================
def grunt_term(orig, curve):
    """The GRUNT coupling's OWN contribution to the 200 -> 480 Hz drop, MEASURED.

    Rendered twice at the drawn defaults, identical but for `--grunt`: CUT (the captures'
    position, ~896 Hz first-order corner) minus BOOST (~36 Hz, i.e. essentially flat across this
    window). The difference of the two drops IS the GRUNT term, with everything else in the chain
    cancelling exactly. Cached -- it is one 18 s render and it never changes.
    """
    import subprocess
    path = os.path.join(RENDER_DIR, "gruntctl_boost.wav")
    if not os.path.exists(path):
        os.makedirs(RENDER_DIR, exist_ok=True)
        cmd = ([RENDER, A.ORIG, path]
               + [("0" if a == "1" and BASE_ARGS[i - 1] == "--grunt" else a)
                  for i, a in enumerate(BASE_ARGS)]
               + ["--attack", ATTACK_IDX["flat"]])
        print("  (rendering the GRUNT control %s ...)" % path)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("GRUNT control render failed:\n%s\n%s" % (" ".join(cmd), r.stderr))
        RG.stamp(path, cmd)

    def drop(p):
        x = A.load(p)
        x, _ = A.align(x, orig)
        f, m = curve(x, "sweep_clean_-36")
        i = int(np.argmin(np.abs(f - 200.0)))
        j = int(np.argmin(np.abs(f - 480.0)))
        return float(m[j] - m[i])

    return drop(os.path.join(RENDER_DIR, "dflt_flat.wav")) - drop(path)


def tilt_probe():
    """⭐⭐ IS THE WIDTH RESIDUAL EVEN ATTACK'S? Measure the OD path's OWN absolute shape.

    `h` is a RATIO between throws, so everything shared by all three cancels out of it by
    construction -- which is exactly why every ATTACK instrument since session 57 has been blind
    to a shared error. But WIDTH is not a ratio: it is measured on ONE throw's own magnitude,
    against that throw's own 200-270 Hz shoulder, so the ABSOLUTE shape through the notch window
    is inside it. So compare that shape directly, pedal vs model, each referred to its own 200 Hz
    value. Bleed-free by topology at LEVEL max / BLEND max (render gate GATE 3).

    Two gates on the reading itself, both from this project's own history:
      * it must be present in ALL THREE throws, or it is not a shared error;
      * it must be LEVEL-independent, or it is an operating point (session 61 item 3).

    Then the mechanism test: remove ONLY the tilt DIFFERENCE (a first-order rotation about
    200 Hz, which cannot create or destroy a null) and re-measure the width with the same
    locator. ⚠ That test REFUTED the obvious hypothesis when it was run (session 64): the tilt
    accounts for about a quarter of the width excess, not for it. Reported either way.

    ⚠⚠ WHAT THIS PROBE FIRST REPORTED, AND WHY IT WAS WRONG -- session 65, kept because the
    failure mode is general. On its first run (session 64) it read PEDAL -4.88 vs MODEL -11.05 dB
    and concluded a 6.2 dB shape error attributable to the IC2_B bridged-T, i.e. GAP #1b reopened.
    The renders it read were made by attack_render_gate.py, whose operating point was hand-written
    as four flags -- and the flag it did NOT write, `--grunt`, fell back to OfflineRender's default
    of 0 = BOOST while every capture here is GRUNT CUT. That is a first-order highpass at ~36 Hz
    instead of ~896 Hz, worth ~6.7 dB of slope across exactly this window. The whole finding was
    the missing flag. At the captures' own GRUNT the model drops -4.02 / -3.71 / -3.93 against the
    pedal's -4.92 / -5.32 / -4.87, i.e. ~1 dB and in the OPPOSITE direction (the model's scoop is
    slightly SHALLOWER), which is the same direction session 21 closed GAP #1b on.
    ⭐ TWO GENERAL LESSONS, both already in this project's own rules and both re-learned here:
      * the probe's two soundness gates -- present in all three throws, level-independent -- are
        satisfied EXACTLY as well by a shared render-condition error as by a shared circuit error,
        so neither gate could ever have caught this. What catches it is asserting that the render
        condition IS the capture's condition (attack_render_gate GATE 0), which is now done by
        deriving the flags from `captures.render_args` rather than typing them.
      * this function's verdict paragraph was NARRATED, so it kept asserting "the bridged-T
        accounts for it to 0.26 dB" above a table that no longer said that. Every number in the
        verdict is now COMPUTED from the run (`computed-verdicts-not-narrated`, third occurrence).
    """
    print("\n" + "=" * 104)
    print("⭐⭐ IS THE WIDTH RESIDUAL EVEN ATTACK'S? -- the OD path's OWN shape, 200 -> 480 Hz")
    print("   (h is a ratio and cancels everything shared; WIDTH is not a ratio and does not)")
    print("=" * 104)
    orig = A.load(A.ORIG)
    with redirect_stdout(io.StringIO()):
        caps = P.load_all(orig)

    def curve(x, seg):
        return A.transfer(A.seg_of(x, seg), A.seg_of(orig, seg))

    def read(f, m):
        i = int(np.argmin(np.abs(f - 200.0)))
        j = int(np.argmin(np.abs(f - 480.0)))
        sel = (f >= 180.0) & (f <= 500.0)
        ex = sel & ~((f >= P.NOTCH_EXCLUDE[0]) & (f <= P.NOTCH_EXCLUDE[1]))
        return float(m[j] - m[i]), float(np.polyfit(np.log10(f[ex]), (m - m[i])[ex], 1)[0])

    def rendered_curve(tag, pos, seg):
        path = os.path.join(RENDER_DIR, "%s_%s.wav" % (tag, pos))
        expect = list(BASE_ARGS) + ["--attack", ATTACK_IDX[pos]]
        for f in (RG.PROPOSAL if tag == "prop" else []):
            expect += ["--fit", f]
        RG.check_stamp(path, expect)          # a render from another condition is not a datum
        x = A.load(path)
        x, _ = A.align(x, orig)
        return curve(x, seg)

    print("  drop over 200->480 Hz, and the ex-null slope, per throw and per LEVEL:")
    print("  %-14s %-22s %-22s" % ("", "-36 dBFS drop / slope", "-30 dBFS drop / slope"))
    rows = {}
    for pos in POSITIONS:
        a = read(*curve(caps[pos], "sweep_clean_-36"))
        b = read(*curve(caps[pos], "sweep_clean"))
        rows["PEDAL " + pos] = b
        print("  %-14s %+9.2f / %+9.2f  %+9.2f / %+9.2f" % ("PEDAL " + pos, *a, *b))
    for tag in ("dflt", "prop"):
        for pos in POSITIONS:
            a = read(*rendered_curve(tag, pos, "sweep_clean_-36"))
            b = read(*rendered_curve(tag, pos, "sweep_clean"))
            rows["%s %s" % (tag, pos)] = b
            print("  %-14s %+9.2f / %+9.2f  %+9.2f / %+9.2f" % (tag + " " + pos, *a, *b))

    # ---- WHICH ELEMENT: a CLOSED accounting, not a single-element attribution ----------------
    # ⚠ The GRUNT coupling is a first-order highpass at ~896 Hz in the CUT position, so it is
    # worth several dB across this very window and must appear in the sum. Session 64's version
    # omitted it -- and, because its renders were accidentally at GRUNT BOOST (~36 Hz, i.e. flat
    # here), omitting it happened to close. It does not close at the captures' own GRUNT unless
    # the term is there. It is MEASURED, not modelled: the same render at `--grunt 0`.
    bt = E.bridged_t_tf(np.array([200.0, 480.0]))
    btd = float(20.0 * np.log10(np.abs(bt[1]) / np.abs(bt[0])))
    sk = [E.sallen_key_lpf_tf(np.array([200.0, 480.0]), 10e3, 22e3, 1e-9, 1e-9),
          E.sallen_key_lpf_tf(np.array([200.0, 480.0]), 22e3, 47e3, 2.2e-9, 1e-9)]
    skd = sum(float(20.0 * np.log10(np.abs(s[1]) / np.abs(s[0]))) for s in sk)
    gd = grunt_term(orig, curve)
    tot = rows["dflt flat"][0]
    acct = btd + skd + gd
    print("\n  WHICH ELEMENT -- every named contribution to the DRAWN model's own drop, summed:")
    print("    IC2_B bridged-T (analytic)      %+7.2f dB" % btd)
    print("    two Sallen-Keys (analytic)      %+7.2f dB" % skd)
    print("    GRUNT cut coupling (measured)   %+7.2f dB   <- absent from session 64's accounting"
          % gd)
    print("    %-30s %+7.2f dB" % ("SUM", acct))
    print("    %-30s %+7.2f dB   residual %.2f dB" % ("MODEL, measured", tot, abs(acct - tot)))
    print("  ⇒ the bridged-T is still the only element with real authority here (%.1fx the SKs),"
          % (abs(btd) / max(abs(skd), 1e-9)))
    print("    but it is opposed by the GRUNT highpass, and the two nearly cancel.")
    resid = rows["PEDAL flat"][0] - tot
    print("\n  PEDAL %+.2f dB vs MODEL %+.2f ⇒ residual %+.2f dB (floor ~%.2f). %s"
          % (rows["PEDAL flat"][0], tot, resid, 2.0 * P.DIFF_FLOOR,
             "The model's scoop is SHALLOWER than the pedal's through this window."
             if resid < 0 else "The model's scoop is DEEPER than the pedal's here."))
    print("  ⚠ Session 64 read this as %+.1f dB with the model far DEEPER and reopened GAP #1b on"
          % -6.2)
    print("    it; that was the missing --grunt flag (see the docstring). The sign here agrees")
    print("    with session 21's closure, which also found the plugin's dip ~0.5 dB SHALLOWER.")

    print("\n  MECHANISM TEST -- does the excess tilt EXPLAIN the ~2x width? Rotate each model")
    print("  curve about 200 Hz until its ex-null background slope equals the pedal's, then")
    print("  re-measure the width with the SAME locator. A rotation cannot create/destroy a null.")
    print("  %-14s %10s %10s %10s %12s" % ("throw", "width now", "de-tilted", "PEDAL", "ratio after"))
    out = {}
    for tag in ("dflt", "prop"):
        for pos in POSITIONS:
            fm, mm = rendered_curve(tag, pos, "sweep_clean")
            fp, mp = curve(caps[pos], "sweep_clean")
            _, sm = read(fm, mm)
            _, sp = read(fp, mp)
            corr = (sp - sm) * np.log10(fm / 200.0)
            w0 = P.notch_width(fm, mm)[1]
            w1 = P.notch_width(fm, mm + corr)[1]
            wp = P.notch_width(fp, mp)[1]
            print("  %-14s %10.1f %10.1f %10.1f %11.2fx"
                  % (tag + " " + pos, w0, w1, wp, w1 / wp))
            out["%s %s" % (tag, pos)] = dict(w=w0, w_detilted=w1, w_pedal=wp,
                                             ratio_before=w0 / wp, ratio_after=w1 / wp)
    pb = [out["prop %s" % p]["ratio_before"] for p in POSITIONS]
    pa = [out["prop %s" % p]["ratio_after"] for p in POSITIONS]
    print("\n  ⇒ de-tilting moves the PROPOSAL's ratio %s -> %s, so the excess tilt is worth"
          % ("/".join("%.2f" % v for v in pb), "/".join("%.2f" % v for v in pa)))
    print("    about %.0f %% of the width excess and the rest is a genuine null-Q difference."
          % (100.0 * (1.0 - (np.mean(pa) - 1.0) / max(np.mean(pb) - 1.0, 1e-9))))
    print("    ⚠ The tempting reading -- that the tilt excess and the width excess are the same")
    print("    ~2x, so one causes the other -- is REFUTED by this test. Coincidence.")
    print("  ⇒ AND THE TILT ITSELF IS NOW SMALL: %+.2f dB (flat throw), against session 64's"
          % resid)
    print("    -6.2 dB. GAP #1b stays CLOSED; what remains is the null-Q difference above,")
    print("    which is ATTACK's network and not the bridged-T's.")
    return dict(drop_slope={k: list(v) for k, v in rows.items()},
                bridged_t_drop=btd, sk_drop=skd, grunt_drop=gd, accounted=acct,
                model_drop=tot, residual=resid, detilt=out)


class TapCost:
    """The broadband h AND the absolute level, with the notch section frozen. Module level so it
    can be pickled by differential_evolution(workers=-1).

    ⭐⭐ THIS IS WHERE THE DEGENERACY ACTUALLY LIVED, and scoring `h` alone here is what let it
    through. The tap is a DIVIDER -- it is the ladder's natural absolute-gain lever, and it is
    fitted on nothing but a throw-to-throw ratio. Measured bleed-free, the pedal wants BOOST
    ~10.3 dB hotter than the drawn model while CUT is already right to 0.47 dB; "raise boost by
    10" and "lower cut and flat by 8" are the same `h` to 0.45 dB, and session 62's proposal took
    the second branch. Adding `g` here is what picks the branch. ⚠ `tgt_g = None` restores the
    ratio-only behaviour exactly, for the control run.
    """

    def __init__(self, base, rd, c5t, tgt_g=None, wt_g=1.0):
        self.base, self.rd, self.c5t = dict(base), dict(rd), dict(c5t)
        self.tgt_g, self.wt_g = tgt_g, (wt_g if tgt_g else 0.0)

    def parts(self, xt):
        b2 = dict(self.base)
        for e, xi in zip(TAP, xt):
            b2[e] = PROP[e] * 10.0 ** xi
        st = full_stats(b2, self.rd, self.c5t)
        if st is None:
            return None
        br = np.concatenate([REC["h"][q] - st["h"][q] for q in THROWS]) / REC["floor"]
        gr = ([(g_of(st)[p] - self.tgt_g[p]) / G_FLOOR_DB for p in POSITIONS]
              if self.tgt_g else [0.0])
        rms = lambda v: float(np.sqrt(np.mean(np.square(v))))   # noqa: E731
        return rms(br), rms(gr), st

    def __call__(self, xt):
        r = self.parts(xt)
        if r is None:
            return 1e6
        b, g, _ = r
        c = float(np.sqrt((b * b + self.wt_g * g * g) / (1.0 + self.wt_g)))
        return c if np.isfinite(c) else 1e6


def tap_stage(base, rd, c5t, tgt_g, quick, tap_bnds=None):
    """Stage 2 in isolation: re-fit the TAP on the broadband `h` and the absolute level `g`,
    with the notch section frozen. Returns (base_with_tap, xt, tparts, st).

    ⚠ TapCost lives at MODULE level, not inside this function: differential_evolution(workers=-1)
    pickles the objective across processes and a local class is unpicklable.
    ⭐ `tgt_g` is what stops this stage picking an h-equivalent branch at the wrong absolute
    level -- the tap IS a divider, so it is the very element that trades those two (session 95).
    """
    tc = TapCost(base, rd, c5t, tgt_g)
    if tap_bnds is None:
        tap_bnds = [(-TAP_BOX, TAP_BOX)] * len(TAP)
    rt = differential_evolution(tc, tap_bnds, seed=23,
                                maxiter=80 if quick else 200, popsize=12 if quick else 20,
                                tol=1e-10, polish=True, init="sobol", workers=-1,
                                updating="deferred")
    tparts = tc.parts(rt.x)
    out = dict(base)
    for e, xi in zip(TAP, rt.x):
        out[e] = PROP[e] * 10.0 ** xi
    return out, rt.x, tparts, full_stats(out, rd, c5t), float(rt.fun)


PROF_GRID = np.round(np.arange(-3.0, 1.0 + 1e-9, 0.05), 6)   # decades, DELIBERATELY past the box
PROF_TOL = 0.15          # decades -- argmin must agree with the optimiser to this, or G3 fails
PROF_FLAT = 0.002        # cost rise at +-0.2 dec below which the direction is FLAT, not located


def _prof_row(fn, x, i, x0):
    """One coordinate's 1-D profile: (argmin, cost_at_argmin, cost_at_x0, rise at x0 +- 0.2 dec).

    ⚠ A pathological point is recorded as +inf, NOT skipped and NOT scored as a large number:
    `empty-gate-must-fail` says a missing measurement must stay distinguishable from a bad one.
    """
    cs = []
    for v in PROF_GRID:
        xx = list(x); xx[i] = float(v)
        c = fn(xx)
        cs.append(float(c) if np.isfinite(c) and c < 1e5 else float("inf"))
    cs = np.array(cs)
    j = int(np.argmin(cs))
    c0 = float(fn(x))
    rise = []
    for d in (-0.2, +0.2):
        xx = list(x); xx[i] = x0 + d
        c = fn(xx)
        rise.append((float(c) if np.isfinite(c) and c < 1e5 else float("inf")) - c0)
    return float(PROF_GRID[j]), float(cs[j]), c0, rise, cs


def bound_profile(tgt, tgt_g, rows_json, quick=False):
    """⭐⭐ GATE G -- IS THE BOX ACTUALLY THE BINDING CONSTRAINT? Run this BEFORE any floor sweep.

    Session 97 left `C9` and `Ra` resting on their box floors and concluded "the box is the missing
    equation". That is a HYPOTHESIS, and it has a cheap decisive test that a floor sweep does not:
    profile the objective along each coordinate, straight THROUGH the bound and out to -3 decades,
    with everything else held at the winner. Three outcomes, and only one of them says "widen it":

      AT-OPTIMUM        the minimum sits where the optimiser put it  -> identified, nothing to do
      BEYOND-BOX        the minimum is interior but OUTSIDE the box  -> the box IS the equation;
                        a per-dimension floor will find a real value
      PINNED / FLAT     the cost falls monotonically to the grid edge, or does not move at all
                        -> DEGENERATE. A deeper floor only moves the rail (`a monotone objective
                        with no interior minimum is a degeneracy, not a fit`), and no box setting
                        will ever identify it. Report it; do not fit around it.

    ⚠⚠ THE SLICE ABOVE IS THE CHEAP HALF AND IT CANNOT CARRY THE VERDICT ON ITS OWN -- it holds the
    other 15 coordinates at values the optimiser chose WHILE this one was railed, so they have
    already adapted to it and a genuine joint optimum further out reads as a RISE. G4 below repeats
    the question with everything else RE-FITTED, which is the form that decides it. Run both, print
    both; when they agree that is a result, not a licence to skip G4 next time.
    ⚠ The `C5t` coordinates are LINEAR and are deliberately NOT profiled -- pushing them past the
    box does not widen a search, it redefines build()'s codomain (see dim_bounds).
    """
    print("\n" + "=" * 104)
    print("GATE G  BOUND PROFILE -- is the BOX the binding constraint, or is the direction flat?")
    print("=" * 104)
    rec = json.load(open(rows_json))
    b = rec["best"]
    rows = [r for r in b["rows"] if r["box"] == b["box"] and r["w_f0"] == b["w_f0"]]
    if len(rows) != 1:
        print("  cannot identify the winning row in %s (%d matches) -- refusing" % (rows_json, len(rows)))
        return None
    row, box = rows[0], float(b["box"])
    x, xt = list(row["x"]), list(row["xt"])
    bnds = dim_bounds(SHARED, False, box)
    tap_bnds = [(-TAP_BOX, TAP_BOX)] * len(TAP)
    print("  point: %s  box %.1f  w_f0 %.0f  (%d on bound: %s)"
          % (os.path.basename(rows_json), box, row["w_f0"], row["n_on_bound"],
             ", ".join(e for e, m in zip(dim_names(SHARED, False) + list(TAP),
                                         on_bound_mask(x, bnds) + on_bound_mask(xt, tap_bnds))
                       if m) or "-"))

    # --- G1  the stored row must REPRODUCE under the session-98 code path -------------------
    # ⚠ This is the load-bearing control for the whole per-dimension-bounds refactor: if `build()`
    # now maps x to a different network, every number below is measured on a different point from
    # the one the record describes, and nothing downstream would say so.
    cost = Cost(SHARED, tgt, False, 0.0, None, float(row["w_f0"]), tgt_g, 1.0, box, bnds)
    p1 = cost.parts(x)
    if p1 is None:
        print("  G1 FAIL -- the stored stage-1 point is pathological under this code path")
        return None
    ref1 = (row["f0_rms"], row["w_rms"], row["dep_rms"], row["g_rms"])
    got1 = (p1[3], p1[4], p1[5], p1[6])
    d1 = max(abs(a - c) for a, c in zip(ref1, got1))
    base, rd, c5t = build(x, SHARED, False, box, bnds)
    tb = dict(base)
    for e, xi in zip(TAP, xt):
        tb[e] = PROP[e] * 10.0 ** xi
    st2 = full_stats(tb, rd, c5t)
    d2 = float("inf")
    if st2 is not None:
        ref2 = (row["post_f0_rms"], row["post_w_rms"], row["post_dep_rms"], row["post_g_rms"])
        _, g2f0, g2w, g2dep, g2g = resid(st2, tgt, tgt_g)
        d2 = max(abs(a - c) for a, c in zip(ref2, (g2f0, g2w, g2dep, g2g)))
    print("  G1 REPRODUCE the stored row under the new per-dimension code path:")
    print("     stage 1 worst |Δ| %.3e   stage 2 (post-tap) worst |Δ| %.3e   %s"
          % (d1, d2, "OK" if max(d1, d2) < 1e-9 else "FAIL"))
    if not (max(d1, d2) < 1e-9):
        print("     ⛔ the refactor MOVED the point -- every profile below would be of a different")
        print("        network from the one the record describes. Refusing.")
        return None

    # --- G2  build() is BIT-identical to the session-97 line at symmetric bounds ------------
    old = [base["C5"] * 0.3 * 0.5 * (x[len(SHARED) + len(POSITIONS) + j] / box + 1.0)
           for j in range(len(POSITIONS))]
    new = [c5t[p] for p in POSITIONS]
    g2 = all(a == c for a, c in zip(old, new))       # `==`, not isclose: the claim is bit-identity
    print("  G2 build() C5-trim mapping vs the session-97 expression at symmetric bounds: %s"
          % ("BIT-IDENTICAL" if g2 else "DIFFERS -- refusing"))
    if not g2:
        return None

    # --- the profiles ----------------------------------------------------------------------
    tc = TapCost(base, rd, c5t, tgt_g)
    print("\n  %-6s %-8s %6s %8s %8s %9s %9s | %s"
          % ("stage", "dim", "at", "argmin", "cost@min", "rise -0.2", "rise +0.2", "verdict"))
    out, ka_fail = {}, []
    jobs = [("1", e, i, cost, x, bnds[i]) for i, e in enumerate(SHARED)] \
        + [("1", "Rd " + p, len(SHARED) + i, cost, x, bnds[len(SHARED) + i])
           for i, p in enumerate(POSITIONS)] \
        + [("2", e, i, tc, xt, tap_bnds[i]) for i, e in enumerate(TAP)]
    for stage, name, i, fn, xv, (lo, hi) in jobs:
        am, cm, c0, rise, cs = _prof_row(fn, xv, i, xv[i])
        onb = min(abs(xv[i] - lo), abs(xv[i] - hi)) < 0.03 * 0.5 * (hi - lo)
        flat = max(rise) < PROF_FLAT
        edge = am <= PROF_GRID[0] + 1e-9
        if flat:
            v = "FLAT -- unidentified at any box"
        elif edge:
            v = "PINNED at the grid edge -- DEGENERATE, a deeper floor only moves the rail"
        elif abs(am - xv[i]) <= PROF_TOL:
            v = "AT-OPTIMUM"
        elif am < lo - 1e-9:
            v = "BEYOND-BOX at %.2f dec (x%.3g) -- the box IS the equation" % (am, 10.0 ** am)
        else:
            v = "argmin %.2f dec INSIDE the box but not at x -- optimiser did not converge here" % am
        # ⚠ G3: on a dimension the optimiser left FREE, a 1-D profile through a converged optimum
        # MUST return that optimum. If it does not, the profiler is not measuring the objective the
        # optimiser minimised and nothing else on this table can be believed. A FLAT direction is
        # exempt -- there the argmin is not defined by the data, which is itself the finding.
        if (not onb) and (not flat) and abs(am - xv[i]) > PROF_TOL:
            ka_fail.append(name)
        print("  %-6s %-8s %6.2f %8.2f %8.4f %+9.4f %+9.4f | %s"
              % (stage, name, xv[i], am, cm, rise[0], rise[1], v))
        out[name] = dict(stage=stage, at=float(xv[i]), argmin=am, cost_at_min=cm, cost_at=c0,
                         rise=[float(r) for r in rise], on_bound=bool(onb), flat=bool(flat),
                         verdict=v, curve=[float(c) for c in cs])
    print("  (C5t x3 not profiled: LINEAR coordinates -- past the box they redefine the codomain,")
    print("   they do not widen a search. See dim_bounds().)")
    print("\n  G3 free dimensions must profile to their own optimum: %s"
          % ("OK -- the profiler reproduces the optimiser on every free dimension"
             if not ka_fail else "FAIL on %s" % ", ".join(ka_fail)))
    if ka_fail:
        return None
    beyond = [k for k, v in out.items() if v["verdict"].startswith("BEYOND-BOX")]
    dead = [k for k, v in out.items()
            if v["verdict"].startswith("PINNED") or v["verdict"].startswith("FLAT")]
    print("\n  ⇒ on the SLICE, a floor is justified for: %s" % (", ".join(beyond) or "NOTHING"))
    print("  ⇒ SLICE-degenerate:                        %s" % (", ".join(dead) or "-"))

    # --- G4  the SAME question, with the other dimensions RE-OPTIMISED ----------------------
    onb = [k for k, v in out.items() if v["on_bound"]]
    print("\n" + "-" * 104)
    print("  ⛔⛔ G4 -- THE SLICE ABOVE CANNOT ANSWER THE QUESTION ON ITS OWN, AND MUST NOT BE")
    print("  QUOTED AS IF IT COULD. A 1-D profile holds the other 15 coordinates at values the")
    print("  optimiser chose WHILE the dimension was railed, so a rail is exactly the case where")
    print("  the slice is least trustworthy: the rest of the ladder has already adapted to it, and")
    print("  a joint optimum further out shows up as a RISE on the slice. The decisive test pins")
    print("  the dimension and RE-FITS everything else -- a genuine profile of the WIDENED search,")
    print("  not a section through the narrow one. Only G4's column may be used to justify a floor.")
    print("-" * 104)
    prof = {}
    for name in onb:
        prof[name] = profile_refit(tgt, tgt_g, name, box, float(row["w_f0"]), x, xt, quick,
                                   row)
    ok = all(p and p["ka_ok"] for p in prof.values())
    justified = sorted(k for k, p in (prof or {}).items() if p and p["improves"])
    print("\n  ⇒ RE-OPTIMISED verdict -- a per-dimension floor is justified for: %s"
          % (", ".join(justified) or "NOTHING"))
    if not ok:
        print("  ⛔ at least one G4 known-answer check FAILED -- do not read the column above.")
    return dict(rows_json=rows_json, box=box, w_f0=row["w_f0"], g1=d1, g1_tap=d2,
                g2_bit_identical=bool(g2), dims=out, refit=prof, ka_ok=bool(ok),
                slice_floor_justified=beyond, slice_degenerate=dead,
                floor_justified=justified,
                floors=({k: 3.0 for k in justified} if justified else None))


def rank_key(real, pg, pf0, pw, nb, box, tgt_g=True):
    """`best_point`'s ranking key, in ONE place so the profile below cannot rank on something the
    selection does not (the session-97 lesson, applied to the gate that judges the selection)."""
    return (0 if real else 1,
            round(pg / max(G_TIE_RMS, 1e-9)) if tgt_g else 0,
            max(round(pf0, 2), F0_TIE_BINS), max(round(pw, 1), W_TIE_RMS), nb, box)


TIE = dict(post_g_rms=G_TIE_RMS, post_f0_rms=F0_TIE_BINS, post_w_rms=W_TIE_RMS)


def dominates(a, b):
    """Is row `a` strictly better than row `b`, judged at each term's OWN tie scale?

    ⚠⚠ THIS IS NOT `rank_key(a) < rank_key(b)`, AND THE DIFFERENCE MATTERS HERE. The ranking key
    ROUNDS each term into bins so that a converged field can be ordered; that is right for
    SELECTING among independent fits, and wrong for asking "did this change anything?", because a
    difference far below the term's own floor can still straddle a bin edge. The first version of
    G4 did exactly that: a re-fit reproduced its reference to 0.06 of width rms -- inside the
    declared 0.10 tie scale -- and was reported as a KNOWN-ANSWER FAILURE and as evidence that
    "the floor BINDS", purely because 0.406 rounds to 0.4 and 0.466 to 0.5.
    ⭐ GENERAL: quantise to compare CANDIDATES, but use the raw statistic and an explicit tolerance
    to compare a MEASUREMENT with its own reference. A rounding boundary is not a finding.
    """
    if bool(a["realisable"]) != bool(b["realisable"]):
        return bool(a["realisable"])
    if any(a[k] > b[k] + t for k, t in TIE.items()):
        return False
    if any(a[k] < b[k] - t for k, t in TIE.items()):
        return True
    return a["n_on_bound_other"] < b["n_on_bound_other"]


def profile_refit(tgt, tgt_g, name, box, w_f0, x_ref, xt_ref, quick, ref_row):
    """Pin ONE dimension at a series of values and RE-FIT everything else -- the profile of the
    WIDENED search, which is the only form that can justify (or refuse) a per-dimension floor.

    Scored on the POST-TAP statistics AND on `best_point`'s own RANKING KEY, i.e. on what the
    selection actually uses (`score-what-you-emit`, session 97). ⚠ A first draft scored these rows
    on the notch cost alone, which stage 2 does NOT minimise -- stage 2 minimises h + g -- so the
    pinned rows were being compared to the free fit on a quantity the free fit was not optimising.
    That is the same defect one level down, and it made a pinned point look like an improvement
    when it had merely traded away `h`. `h` is printed beside the key for exactly that reason.

    ⚠ KNOWN ANSWER: pinned AT the reference value the re-fit must recover the reference row. If a
    constrained re-fit at the optimiser's own point comes back materially worse, the re-fit is
    under-converged and every other row of the profile is noise.
    """
    stage2 = name in TAP
    ref = (xt_ref[list(TAP).index(name)] if stage2
           else x_ref[dim_names(SHARED, False).index(name)])
    # ⚠ ROUND the reference before building the grid, and compare against the ROUNDED value: the
    # stored coordinate is a converged float (-0.99987...), so `v == ref` never fires and the
    # known-answer row is silently never identified -- which is exactly what the first run did.
    ref = round(float(ref), 3)
    vals = sorted({round(ref + d, 3) for d in (0.25, 0.0, -0.25, -0.5, -1.0, -1.5, -2.0)},
                  reverse=True)
    rkey = rank_key(ref_row["realisable"], ref_row["post_g_rms"], ref_row["post_f0_rms"],
                    ref_row["post_w_rms"], ref_row["n_on_bound"], box, tgt_g)
    print("\n  G4 %s -- pinned at %+.2f dec in the record, everything else RE-FITTED (%d points)"
          % (name, ref, len(vals)))
    print("     the record's own row ranks %s with %d on bound"
          % (str(rkey), ref_row["n_on_bound"]))
    print("     %8s %9s %8s %8s %8s %8s %7s %7s %6s | %s"
          % ("pin dec", "x mult", "f0", "width", "depth", "g dB", "h rms", "onbnd", "real", "note"))
    rows, base_key, base = [], None, None
    for v in vals:
        if stage2:
            lfl, tfl = None, {name: max(TAP_BOX, -v)}
        else:
            lfl, tfl = ({name: max(box, -v)} if v < -box else None), None
        bnds = dim_bounds(SHARED, False, box, lfl)
        i1 = dim_names(SHARED, False).index(name) if not stage2 else None
        if not stage2:
            bnds[i1] = (v, v + 1e-9)              # pinned: a 1e-9-decade window, not a bound
        tap_bnds = [(-float((tfl or {}).get(e, TAP_BOX)), TAP_BOX) for e in TAP]
        if stage2:
            j = list(TAP).index(name)
            tap_bnds[j] = (v, v + 1e-9)
        c1 = Cost(SHARED, tgt, False, 0.0, None, w_f0, tgt_g, 1.0, box, bnds)
        r1 = differential_evolution(c1, bnds, seed=17, maxiter=80 if quick else 200,
                                    popsize=12 if quick else 20, tol=1e-10, polish=True,
                                    init="sobol", workers=-1, updating="deferred")
        p1 = c1.parts(r1.x)
        if p1 is None:
            print("     %8.2f  pathological stage 1 -- point dropped (NOT scored as a large cost)"
                  % v)
            continue
        tb, xt, tparts, tst, _ = tap_stage(*build(r1.x, SHARED, False, box, bnds),
                                           tgt_g, quick, tap_bnds)
        if tst is None:
            print("     %8.2f  pathological stage 2 -- point dropped" % v)
            continue
        pn, pf0, pw, pdep, pg = resid(tst, tgt, tgt_g)
        # ⚠ The PINNED dimension is not a free value, so it must be EXCLUDED BY INDEX -- not
        # subtracted. A first draft did `- 1`, which assumed the 1e-9 pin window always trips
        # `on_bound_mask`; it trips it when the polish lands exactly on the edge and does not when
        # it lands mid-window, so the column was off by one on some rows and not on others -- and
        # `n_on_bound` is the very statistic this whole gate exists to move.
        m1, m2 = on_bound_mask(r1.x, bnds), on_bound_mask(xt, tap_bnds)
        (m2 if stage2 else m1)[list(TAP).index(name) if stage2
                               else dim_names(SHARED, False).index(name)] = False
        nb = sum(m1) + sum(m2)
        real = realisable(r1.x, box, bnds)
        key = rank_key(real, pg, pf0, pw, nb, box, tgt_g)
        isref = (v == ref)
        print("     %8.2f %9.4g %8.3f %8.3f %8.3f %8.3f %7.3f %7d %6s | %s"
              % (v, 10.0 ** v, pf0, pw, pdep, pg, tparts[0], nb, "yes" if real else "NO",
                 "<- reference (KNOWN ANSWER)" if isref
                 else ("outside the box" if v < -box else "")))
        row = dict(pin=v, post_f0_rms=pf0, post_w_rms=pw, post_dep_rms=pdep, post_g_rms=pg,
                   h_rms=float(tparts[0]), n_on_bound_other=nb, realisable=bool(real),
                   key=[float(t) for t in key], is_ref=bool(isref),
                   x=[float(t) for t in r1.x], xt=[float(t) for t in xt])
        if isref:
            base_key, base = key, row
        rows.append(row)
    if base_key is None or not rows:
        print("     ⛔ the reference pin produced no point -- G4 cannot be read for %s" % name)
        return dict(name=name, rows=rows, ka_ok=False, improves=False)
    # ⚠ KA: pinned at the record's own value, the re-fit must land back ON the record -- compared
    # at each term's own tie scale, NOT on the rounded key (see dominates()).
    recrow = dict(ref_row, n_on_bound_other=ref_row["n_on_bound"])
    ka = not dominates(recrow, base)
    print("     KA pinned at the record's value the re-fit reproduces it: "
          "f0 %.3f/%.3f  w %.3f/%.3f  g %.3f/%.3f  %s"
          % (base["post_f0_rms"], recrow["post_f0_rms"], base["post_w_rms"], recrow["post_w_rms"],
             base["post_g_rms"], recrow["post_g_rms"],
             "OK" if ka else "FAIL -- the re-fit is under-converged, do not read this column"))
    out = [r for r in rows if r["pin"] < -box - 1e-9]
    ins = [r for r in rows if r["pin"] > -box + 1e-9 and not r["is_ref"]]
    binds = [r for r in out if dominates(r, base)]
    inside = [r for r in ins if dominates(r, base)]
    print("     OUTSIDE the box (%d points): %s"
          % (len(out), "%d dominate the reference -- the floor BINDS, widen this dimension"
             % len(binds) if binds else
             "none dominates the reference -- THE FLOOR DOES NOT BIND, widening buys nothing"))
    if inside:
        # ⭐ The outcome neither session 97 nor this gate was designed to expect, and the one that
        # actually names the defect: the dominating point is INSIDE the existing box. Then the rail
        # is not the box at all -- some term is driving the dimension out that the RANKING does not
        # score, and no box setting will fix that.
        b = min(inside, key=lambda r: (r["n_on_bound_other"], r["post_w_rms"]))
        print("     ⭐⭐ INSIDE the box, %d point(s) DOMINATE the reference -- best at %+.2f dec"
              " (x%.4g): %d on bound vs %d, h %.3f vs %.3f."
              % (len(inside), b["pin"], 10.0 ** b["pin"], b["n_on_bound_other"],
                 base["n_on_bound_other"], b["h_rms"], base["h_rms"]))
        print("        ⇒ the rail is NOT the box. The dimension is being driven out by a term the"
              " ranking never scores.")
    return dict(name=name, ref=ref, rows=rows, ka_ok=bool(ka), improves=bool(binds),
                dominating_inside=[r["pin"] for r in inside],
                base_key=[float(t) for t in base_key])


def best_point(tgt, quick, boxes=(1.0, 3.0), tgt_g=None, floors=None, rov=None):
    """The best available compromise, with f0 weighted hard because f0 is the requirement that
    already matches TO THE BIN and the one session 61 proved the drawn topology cannot reach at
    all (0 of 782 draws).

    Two stages, because the census proves the groups do not interact (session 62 item 4's rule):
      1 NOTCH   shared ladder + per-throw pole B, tap PINNED, scored on the 9 notch numbers only.
      2 BROADBAND  tap alone re-fitted on h, with the notch section frozen -- the tap moves width
                by <=0.5 Hz and f0 by 0.00 Hz, so it cannot undo stage 1.

    ⚠⚠ THE SEARCH BOX IS NOW SWEPT, NOT FIXED AT 3.0 -- session 66. The old version searched box
    3.0 only, justified in its own header as "the sweep showed 1.0 was still constraining". That
    justification came from session 64's box sweep, which was run against a requirement transferred
    through a calibration built on a WRONG RENDER CONDITION (session 65: a missing `--grunt` flag).
    At the corrected calibration box 1.0 is NOT constraining -- it reaches the nine numbers with no
    element on a bound -- while box 3.0 wanders three decades out to values that are worse on the
    f0/width ranking AND unrealisable in FitParams. ⭐ GENERAL: a SEARCH SETTING justified by a
    measurement is as perishable as any other number derived from it; when the measurement is
    corrected the setting has to be re-derived, not carried. Sweeping removes the choice entirely
    and puts the comparison in the tool's own output, where the next session can see it.

    ⚠⚠ SESSION 98 -- `n_on_bound` IS A FLAG, NOT A VERDICT, AND IT IS THE LAST TERM THAT SHOULD
    DISQUALIFY A CANDIDATE ON ITS OWN. It stays in the key (a bound-rester is still the thing to
    look at first), but session 97 read two bound-resters as "unidentified, the box is the missing
    equation" and pre-registered a per-dimension floor sweep on that basis. `--floor-probe` pinned
    each of them and RE-FITTED everything else: neither is box-limited -- outside the box nothing
    dominates, `C9` collapses beyond x0.03 and `Ra` degrades monotonically on `g`. The optimum
    simply COINCIDES with the bound. ⭐ So: when this key reports a bound-rester, run
    `--floor-probe` before either widening the box OR discarding the candidate. Both are wrong here.
    """
    print("\n" + "=" * 104)
    print("THE BEST AVAILABLE POINT -- box SWEPT (see the docstring: fixing it at 3.0 was")
    print("justified by session 64's now-void calibration), f0 weighted hard, then the tap")
    print("re-fitted on h AND the absolute OD magnitude (session 95 -- on h alone the tap")
    print("cannot tell 'raise boost 10 dB' from 'lower cut and flat 8 dB').")
    if floors:
        print("⭐ PER-DIMENSION FLOORS ACTIVE (session 98): %s"
              % ", ".join("%s to -%.1f dec" % (k, v) for k, v in sorted(floors.items())))
        print("   Every other dimension is unchanged. See dim_bounds() and bound_profile().")
    print("=" * 104)
    best, rows = None, []
    lfl = {k: v for k, v in (floors or {}).items() if k not in TAP}
    tfl = {k: v for k, v in (floors or {}).items() if k in TAP}
    tap_bnds = [(-float(tfl.get(e, TAP_BOX)), TAP_BOX) for e in TAP]
    for box in boxes:
        for w_f0 in (1.0, 3.0, 10.0, 30.0, 100.0):
            bnds = dim_bounds(SHARED, False, box, lfl)
            c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=w_f0,
                              box=box, tgt_g=tgt_g, floors=lfl)
            if parts is None:
                continue
            f0s = [parts[2]["notch"][p][0] for p in POSITIONS]
            ws = [parts[2]["notch"][p][2] for p in POSITIONS]
            nb = sum(on_bound_mask(x, bnds))
            worst = max(abs(xi) for xi in x[:len(SHARED)])
            real = realisable(x, box, bnds)
            # ⛔⛔ STAGE 2 IS RUN PER ROW AND THE RANKING SCORES ITS OUTPUT, NOT STAGE 1's --
            # session 97. This function used to rank the ten rows on their stage-1 statistics and
            # re-fit the tap ONCE, on the winner, justified by the docstring's "the tap moves width
            # by <=0.5 Hz and f0 by 0.00 Hz, so it cannot undo stage 1". That figure is a CENSUS
            # number, measured at PROP, and it does NOT survive at the fitted points: measured here,
            # the tap moves cut/flat width by 2.3-2.5 Hz at the session-95 winner and by 6.9-7.1 Hz
            # -- 14x the quoted bound -- at the box-3.0 rows. Since the size of the perturbation is
            # CANDIDATE-DEPENDENT it can and does reorder the field, so ranking on stage-1 numbers
            # was ranking on numbers the tool does not deliver. Both columns are printed below so
            # the size of the stage-2 move stays visible per row instead of being asserted.
            # ⭐ GENERAL: score the candidate you will actually emit. A two-stage fit whose second
            # stage is argued to be harmless must PRINT the harm, not cite a census taken elsewhere.
            tbase, xt, tparts, tst, tfun = tap_stage(*build(x, SHARED, False, box, bnds),
                                                     tgt_g, quick, tap_bnds)
            if tst is None:
                print("  box %4.1f w_f0 %6.1f | stage 2 pathological -- row dropped" % (box, w_f0))
                continue
            pnotch, pf0, pw, pdep, pg = resid(tst, tgt, tgt_g)
            pws = [tst["notch"][p][2] for p in POSITIONS]
            nbt = sum(on_bound_mask(xt, tap_bnds))
            print("  box %4.1f w_f0 %6.1f | stage1 f0 %5.2f w %5.2f g %5.2f | POST-TAP f0 %5.2f"
                  " w %5.2f dep %5.2f g %5.2f | widths %5.1f %5.1f %5.1f (was %5.1f %5.1f %5.1f)"
                  " | spread %4.1f Hz | worst shared x%.3g | %d on bound (%d ladder + %d tap) | %s"
                  % (box, w_f0, parts[3], parts[4], parts[6], pf0, pw, pdep, pg, *pws, *ws,
                     max(f0s) - min(f0s), 10.0 ** worst, nb + nbt, nb, nbt,
                     "realisable" if real else "NOT REALISABLE"))
            # ⚠⚠ RANK f0 TO THE RESOLUTION THE RECORD HAS, NOT TO FULL PRECISION -- session 66.
            # A first version ranked on round(f0_rms, 2) and 0.06 bins beat 0.07 bins, which then
            # decided the winner AGAINST a point with 8.2 % width error in favour of one with
            # 12.7 %. 0.01 bins is 0.06 Hz; the pedal's f0 is quoted on a 5.86 Hz grid, so that
            # difference does not exist in the measurement. Anything at or under a QUARTER bin is
            # therefore treated as equally on-the-bin and width breaks the tie. ⭐ GENERAL: a
            # ranking key must be quantised to the resolution of the quantity it ranks, or search
            # noise in the tightest term silently outvotes a real difference in the next one.
            # ⚠⚠ AND THE SAME RULE HAD TO BE APPLIED TO **WIDTH** -- session 94. The line above
            # quantised f0 and left width at full precision, and the first stepped run showed why
            # that is not half a fix: box 3.0 / w_f0 100 beat box 1.0 / w_f0 1 by **0.33 vs 0.34**
            # -- 0.1 % of a width, against a statistic whose own demonstrated accuracy on this grid
            # is 0.94 % (GATE B) and whose transfer to the render is +-5-10 % (GATE C) -- and the
            # winner it picked wanted R7 x28.6, R12 x0.018, C6 x200, C7 x0.023 where the loser
            # wanted at most x10. A meaningless difference in the second term outvoted a 20x
            # difference in physical plausibility. `parts[4]` is an rms in units of 10 % of the
            # target width, so rounding to 1 dp quantises it to 1 % of width, just above the
            # instrument's floor; ties then fall through to `n_on_bound`, and only then to `box`.
            # ⭐ GENERAL: quantise EVERY term of a ranking key, not the one that was
            # embarrassing last time -- an unquantised tail term is a lottery with a plausible face.
            # ⭐⭐ AND `n_on_bound` NOW OUTRANKS `box` -- session 97. Session 66 added `box` as the
            # last tie-break because the SMALLER search is the more plausible one, which is a fair
            # heuristic and was added for a good reason. But with the session-95 `g` term in, box 1.0
            # / w_f0 3 and box 3.0 / w_f0 3 tie on EVERY quantised term (g 0.03 vs 0.02, f0 0.03 vs
            # 0.04, width 0.35 vs 0.39 -- all inside their own instruments' floors) and box 1.0 won
            # purely on being the smaller search, while resting THREE of thirteen values on their
            # bounds where box 3.0 rested NONE. A parameter on its bound is not a value, it is a
            # missing equation (`bound-resting-means-unidentified`), and that is a stronger objection
            # than "the search was wider": an unidentified point cannot be proposed at all, whereas an
            # implausible-looking identified one can at least be judged by the matrix. ⭐ GENERAL:
            # rank IDENTIFIABILITY ahead of any plausibility tie-break.
            # ⚠ This does NOT reach the row a human would pick on plausibility alone -- box 1.0 /
            # w_f0 1 has 0 on bound and worst shared x9.3 (against x45.7) -- because it gives up
            # 1.2 bins of f0 and so loses at the f0 term, several places earlier. That is the key
            # working as specified, not a defect; the row is printed above and in `rows`.
            # ⛔⛔ AND `realisable` OUTRANKS EVEN `g` -- session 97, see realisable(). Ranking on
            # identifiability alone selected a point FitParams cannot express (flat is not its
            # smallest C5, and there is no attackC5TrimFlat), i.e. the fix for one blind spot
            # walked straight into a second one that the tool had been PRINTING for 35 sessions
            # without ever scoring. Feasibility is not a quality term and does not belong among
            # the quantised ones: a point that cannot be rendered cannot be judged at all.
            # ⭐⭐ AND THE ABSOLUTE LEVEL IS NOW THE FIRST TERM OF THE KEY -- session 95. It is
            # quantised to G_FLOOR_DB for the same reason the other two are quantised (nothing
            # under the term's own transfer accuracy is a real difference), and it sorts FIRST
            # because it is the one requirement with a physical floor under it: a candidate that
            # is absolutely wrong is not a better candidate for having a slightly rounder f0.
            # Session 94's winner was chosen by a key that could not see this at all.
            key = (0 if real else 1,
                   round(pg / max(G_TIE_RMS, 1e-9)) if tgt_g else 0,
                   max(round(pf0, 2), F0_TIE_BINS), max(round(pw, 1), W_TIE_RMS),
                   nb + nbt, box)
            rows.append(dict(box=box, w_f0=w_f0,
                             f0_rms=parts[3], w_rms=parts[4],          # stage 1, the CONTROL
                             dep_rms=parts[5], g_rms=parts[6],
                             post_f0_rms=pf0, post_w_rms=pw,           # what is RANKED and emitted
                             post_dep_rms=pdep, post_g_rms=pg, post_notch_rms=pnotch,
                             f0=f0s, width=ws, post_width=pws,
                             spread=max(f0s) - min(f0s),
                             worst_shared=10.0 ** worst, n_on_bound=nb + nbt,
                             n_on_bound_ladder=nb, n_on_bound_tap=nbt, realisable=bool(real),
                             x=[float(v) for v in x], xt=[float(v) for v in xt]))
            if best is None or key < best[0]:
                best = (key, w_f0, x, parts, box, tbase, tparts, tst, xt, tfun)
    if best is None:
        return None
    _, w_f0, x, parts, box, base, tparts, st, xt, tfun = best
    bnds = dim_bounds(SHARED, False, box, lfl)
    _, rd, c5t = build(x, SHARED, False, box, bnds)
    print("\n  chosen (box = %.1f, w_f0 = %.0f), tap re-fitted on h + absolute level"
          " (h %.3f x floor, g %.2f dB):"
          % (box, w_f0, tparts[0] if tparts else float("nan"),
             tparts[1] if tparts else float("nan")))
    print("    %-6s | %-22s | %-22s | %s"
          % ("throw", "f0 Hz got/want", "depth dB got/want", "width Hz got/want"))
    for pos in POSITIONS:
        f0, dep, w = st["notch"][pos]
        tf0, tdep, tw = tgt[pos]
        print("    %-6s | %7.2f /%7.2f (%+5.2f) | %7.2f /%7.2f (%+5.2f) | %6.1f /%6.1f (%+5.1f%%)"
              % (pos, f0, tf0, f0 - tf0, dep, tdep, dep - tdep, w, tw, 100.0 * (w - tw) / tw))
    for q in THROWS:
        print("    h %-5s median %+6.2f (pedal %+6.2f)  slope %+6.2f dB/dec"
              % (q, st["shape"][q][0], float(np.median(REC["h"][q])), st["shape"][q][1]))
    if tgt_g:
        print_g_table(g_of(st), tgt_g)
    names = dim_names(SHARED, False)
    ob = [e for e, m in zip(names, on_bound_mask(x, bnds)) if m] \
        + [e for e, m in zip(TAP, on_bound_mask(xt, tap_bnds)) if m]
    print("    shared: %s" % "  ".join("%s %.4g (x%.3g)" % (e, base[e], base[e] / PROP[e])
                                       for e in SHARED))
    print("    Rd: %s" % "  ".join("%s %.4g" % (p, rd[p]) for p in POSITIONS))
    print("    C5: %s" % "  ".join("%s %.4g" % (p, base["C5"] + c5t[p]) for p in POSITIONS))
    print("    tap: %s" % "  ".join("%s %.4g" % (e, base[e]) for e in TAP))
    if ob:
        print("    ⚠ ON A BOUND (unidentified, not a value): %s" % ", ".join(ob))

    # ⚠ The FitParams realisation makes trebleC5 the base and the two trims ADDITIVE parallel
    # caps, so both trims must be >= 0. The screen's three per-throw C5 values are unordered, so
    # rebase on the SMALLEST of them rather than on `flat` -- rebasing on flat can emit a negative
    # trim, which FitParams would silently clamp and the render would then not be the fitted point.
    c5min = min(c5t.values())
    fits = ["attackTapRa=%.6g" % base["Ra"], "attackTapRb=%.6g" % base["Rb"],
            "attackTapRc=%.6g" % base["Rc"], "attackTapR11=%.6g" % base["R11"],
            "trebleR7=%.6g" % base["R7"], "trebleLadderR12=%.6g" % base["R12"],
            "trebleLadderR14=%.6g" % base["R14"], "trebleC9=%.6g" % base["C9"],
            "trebleC6=%.6g" % base["C6"], "trebleC7=%.6g" % base["C7"],
            "trebleC5=%.6g" % (base["C5"] + c5min),
            "attackC5TrimBoost=%.6g" % (c5t["boost"] - c5min),
            "attackC5TrimCut=%.6g" % (c5t["cut"] - c5min),
            "trebleLadderDampR=%.6g" % rd["flat"], "attackDampBoost=%.6g" % rd["boost"],
            "attackDampCut=%.6g" % rd["cut"], "trebleC8=0"]
    if abs((base["C5"] + c5t["flat"]) - (base["C5"] + c5min)) > 1e-15:
        print("  ⚠ NOTE: flat is not the smallest C5, so trebleC5 is rebased on the smallest throw")
        print("    and the FLAT throw would need its own trim -- which FitParams does NOT have.")
        print("    That is a REALISABILITY gap in this candidate, recorded not hidden.")
    print("\n  as --fit (⚠ SCREEN units -- the RENDER is the arbiter, gate C says this screen is")
    print("  only a lever finder; land it with attack_render_gate.py --fits-json):")
    print("    " + " ".join("--fit " + f for f in fits))
    # ⭐ SESSION 99 -- report the winner's ladder DISTANCE against GATE F4's measured envelope, so
    # an extrapolation is visible AT SELECTION TIME rather than discovered by the matrix. This is
    # a flag, not a veto: the complete check needs a render and stays
    # attack_d_extrapolation_gate.py, which is a REQUIRED step before the matrix.
    # ⚠ EVERY number in this paragraph is COMPUTED from GATE F4's own measurement, never typed.
    # A first draft transcribed "0.183 dB at 0.23 dec" and "3.84 dB at 1.00 dec" into the format
    # string -- which is `computed-verdicts-not-narrated` / `a gate that lives in a table is a
    # transcription`, in a line whose entire job is to tell the next session whether to trust the
    # term. Those two figures move the moment the CAL ladder or the wild reference changes.
    dist = ladder_distance(base)
    rov = rov or {}
    lim = rov.get("mild_distance")
    print("\n  ⚠ ladder distance from PROP: %.2f decades (max |log10 x| over SHARED + TAP)."
          % dist)
    if lim is None:
        print("    GATE F4 did not run, so the region of validity is UNMEASURED -- `g`'s transfer"
              " to the render is an untested assumption at ANY distance.")
    else:
        print("    GATE F1 measured D-invariance to %.3f dB at %.2f dec%s."
              % (rov["mild"], lim,
                 (" and F4 to %.2f dB at %.2f dec" % (rov["wild"], rov["wild_distance"]))
                 if rov.get("measured") else " (no wild reference measured)"))
        print("    %s" % ("INSIDE the tested region." if dist <= lim else
                          "OUTSIDE it -- `g` is an EXTRAPOLATION here and must be re-checked at"
                          " this\n    candidate by attack_d_extrapolation_gate.py before the"
                          " matrix."))
    return dict(w_f0=w_f0, box=box, floors=(dict(floors) if floors else None),
                on_bound=ob, fits=fits, tap_bb_rms=tfun, rows=rows,
                got={p: list(st["notch"][p]) for p in POSITIONS},
                shape={q: list(st["shape"][q]) for q in THROWS},
                g=g_json(g_of(st)), g_bands=g_labels(),
                g_target=(g_json(tgt_g) if tgt_g else None),
                ladder_distance=float(dist),
                mild_distance=(None if lim is None else float(lim)),
                g_rms=(tparts[1] if tparts else None))


def census(tgt):
    print("\n" + "=" * 104)
    print("SENSITIVITY CENSUS -- which SHARED element is a WIDTH lever, and is it width-SELECTIVE?")
    print("=" * 104)
    b = full_stats(PROP, PROP_RD, PROP_C5T)
    print("  at the proposal point, screen units: width cut/boost/flat %.1f / %.1f / %.1f Hz"
          % tuple(b["notch"][p][2] for p in POSITIONS))
    print("  target (pedal, mapped through the calibration):        %.1f / %.1f / %.1f Hz"
          % tuple(tgt[p][2] for p in POSITIONS))
    print("\n  %-5s %-5s | %8s %8s %8s | %9s %9s | %8s"
          % ("elem", "dir", "dw cut", "dw bst", "dw flt", "df0 flat", "ddep flat", "dh bst"))
    sel = {}
    for e in SHARED + TAP:
        for mult, lab in ((1.2, "+20%"), (0.8, "-20%")):
            p = dict(PROP); p[e] = PROP[e] * mult
            s = full_stats(p, PROP_RD, PROP_C5T)
            if s is None:
                continue
            dw = [s["notch"][q][2] - b["notch"][q][2] for q in POSITIONS]
            df = s["notch"]["flat"][0] - b["notch"]["flat"][0]
            dd = s["notch"]["flat"][1] - b["notch"]["flat"][1]
            dh = s["shape"]["boost"][0] - b["shape"]["boost"][0]
            print("  %-5s %-5s | %+8.1f %+8.1f %+8.1f | %+9.2f %+9.2f | %+8.2f"
                  % (e, lab, dw[0], dw[1], dw[2], df, dd, dh))
            if mult == 1.2:
                sel[e] = (float(np.mean(np.abs(dw))), abs(df), abs(dh))
    print("\n  ⭐ WIDTH-SELECTIVITY: width moved per Hz of f0 dragged. A lever that moves width only")
    print("     by moving f0 is not a width lever -- f0 already matches TO THE BIN and must not move.")
    print("  %-5s %10s %10s %14s %10s" % ("elem", "mean|dw|", "|df0|", "dw per Hz f0", "|dh bst|"))
    for e, (mw, df, dh) in sorted(sel.items(), key=lambda kv: -kv[1][0]):
        print("  %-5s %10.2f %10.3f %14s %10.2f"
              % (e, mw, df, ("%.1f" % (mw / df)) if df > 1e-3 else "inf (f0-neutral)", dh))
    return sel


def gate_g_partition():
    """⭐ MUTATION-TEST THE PARTITION, because a partition defect is INVISIBLE in every printed
    number and always flatters the fit.

    A dropped band removes whichever region is worst; an overlap double-weights one; an extra band
    outside G_BAND silently changes what "the notch-remote band" means. `check_g_partition` refuses
    all three -- and a guard that has never been shown to FAIL is not a guard (session 88's
    `assert_anchors_match` returned None on every real report and fell through to its own
    "cannot verify" branch, which reads as diligence while checking nothing).
    """
    print("=" * 104)
    print("GATE  g SUB-BAND PARTITION -- mutation-tested, because a defect here is invisible")
    print("=" * 104)
    ok = True
    counts = check_g_partition(G_SUBS)
    print("  the shipped partition tiles G_BAND: %s = %d bins (G_BAND has %d)   %s"
          % (" + ".join(str(c) for c in counts), sum(counts), int(G_BAND.sum()),
             "OK" if sum(counts) == int(G_BAND.sum()) else "FAIL"))
    for lab, c in zip([s[0] for s in G_SUBS], counts):
        print("     %-14s %4d bins" % (lab, c))
    print("  the POOLED control tiles it too: %s   OK" % check_g_partition(G_POOL))

    muts = [("DROPPED band (the LF one, the region the repair exists for)", G_SUBS[1:]),
            ("OVERLAP (LM widened over M)",
             (G_SUBS[0], ("LM'", 175.0, 1130.0), G_SUBS[2], G_SUBS[3])),
            ("EXTRA band beyond G_BAND's top",
             tuple(G_SUBS) + (("XX 1600+", 1600.0, 1e9),)),
            ("GAP (M removed from the middle)", (G_SUBS[0], G_SUBS[1], G_SUBS[3]))]
    for name, mut in muts:
        try:
            check_g_partition(mut)
            print("  ⛔ MUTATION NOT CAUGHT: %s -- the guard is vacuous" % name)
            ok = False
        except AssertionError as e:
            print("  caught: %-58s (%s)" % (name, str(e).split(":")[0]))
    # ⚠ The EXTRA-band mutation is expected to fail as an EMPTY band, not as an overlap -- there
    # are no G_BAND bins above 1600 Hz. Stated because a mutation that passes for the wrong reason
    # is not a passing mutation test.
    print("\n  ⇒ %s" % ("all four partition defects are refused."
                        if ok else "THE GUARD IS NOT SOUND -- fix it before trusting any g number."))

    # ---- the INERTNESS control: --g-pooled must reproduce the STORED pre-99 statistic ----------
    # ⭐ The whole session's conclusion is only readable if the refactor is proven inert where it
    # should be inert. The session-97 winner's `post_g_rms` is on disk (0.189624...); rebuilt from
    # its own emitted `--fit` list and re-scored through the REWRITTEN vectorised code path under
    # the pooled partition, it must come back. Then the same ladder under the sub-band partition
    # must come back LARGE -- that is the repair, measured on a known answer rather than asserted.
    print("\n  INERTNESS -- does --g-pooled reproduce the STORED s97 statistic through the new")
    print("  vectorised path, and does the sub-band partition then see the defect?")
    if not os.path.exists(WILD_FITS):
        print("  ⚠ SKIPPED, not silently: %s absent. The refactor is UNPROVEN inert." % WILD_FITS)
        return 1
    rec_json = json.load(open(WILD_FITS))
    stored = rec_json["best"]
    row = [r for r in stored["rows"]
           if r["box"] == stored["box"] and r["w_f0"] == stored["w_f0"]]
    if len(row) != 1:
        print("  ⚠ cannot identify the stored winning row (%d matches) -- refusing" % len(row))
        return 1
    want = float(row[0]["post_g_rms"])
    wild = _load_wild()
    st = full_stats(*wild)
    if st is None:
        print("  ⛔ the stored winner is pathological in this screen -- a hard failure")
        return 1
    # ⚠ Scored through `resid()` itself, not by a second copy of the arithmetic -- `resid` is the
    # ONE definition shared by the objective and the ranking (session 97), so it is the thing that
    # has to be proven inert. The notch target is the candidate's OWN stats, which zeroes the
    # notch residuals and leaves the g term the only thing measured.
    tgt_self = {p: st["notch"][p] for p in POSITIONS}
    got = {}
    for pooled in (True, False):
        set_g_partition(pooled)
        got["pooled" if pooled else "subband"] = resid(st, tgt_self, g_targets())[4]
    set_g_partition(False)
    d = abs(got["pooled"] - want)
    inert = d < 1e-3
    print("  --g-pooled   g_rms %.6f   stored %.6f   |diff| %.2e   %s"
          % (got["pooled"], want, d, "INERT" if inert else "⛔ NOT INERT -- the refactor MOVED it"))
    print("  sub-band     g_rms %.6f   = %.1fx the pooled reading   %s"
          % (got["subband"], got["subband"] / max(got["pooled"], 1e-9),
             "the repair SEES it" if got["subband"] > 10.0 * got["pooled"] else
             "⛔ the repair does NOT see the known defect"))
    ok = ok and inert and got["subband"] > 10.0 * got["pooled"]
    print("\n  ⇒ %s" % ("GATE PASSES." if ok else "GATE FAILS -- do not fit with this."))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--render-cal", action="store_true",
                    help="render the calibration anchor (3 throws, ~1 min); needed once")
    ap.add_argument("--best", action="store_true",
                    help="search the best available compromise and emit it as --fit")
    ap.add_argument("--tilt", action="store_true",
                    help="is the width residual even ATTACK's? the OD path's own absolute shape")
    ap.add_argument("--instrument", choices=("stepped", "swept"), default="stepped",
                    help="stepped (session 70's spec, the DEFAULT) or swept (the old control)")
    ap.add_argument("--no-absgain", action="store_true",
                    help="drop the ABSOLUTE OD-magnitude term (session 95) -- the pre-95 "
                         "objective exactly, kept as the CONTROL, not as an option to prefer: "
                         "without it every term is relative and a shared re-scaling is free")
    ap.add_argument("--g-pooled", action="store_true",
                    help="score the absolute term as ONE median over the whole of G_BAND -- the "
                         "pre-session-99 objective exactly, kept as the CONTROL. ⚠ Not an option "
                         "to prefer: 8 of those 100 bins lie below 175 Hz and 92 above 533, so the "
                         "median sits at 1019.5 Hz and cannot register an LF collapse (session 98)")
    ap.add_argument("--g-selftest", action="store_true",
                    help="GATE: mutation-test the sub-band partition and reproduce the pooled "
                         "term's stored numbers, then exit")
    ap.add_argument("--floor-probe", metavar="ROWS_JSON", nargs="?", const=DEF_ROWS, default=None,
                    help="GATE G: profile the objective THROUGH each coordinate's bound, at a "
                         "stored winner, and say which dimensions a per-dimension floor could "
                         "actually identify. Run this BEFORE --floor.")
    ap.add_argument("--floor", metavar="DIM=DEC", action="append", default=None,
                    help="deepen ONE dimension's lower bound to -DEC decades, e.g. --floor C9=3 "
                         "--floor Ra=3. Repeatable. Only meaningful with --best. ⚠ RETAINED BUT "
                         "CURRENTLY UNJUSTIFIED: session 98's --floor-probe measured that neither "
                         "bound-rester is box-limited, so do not reach for this until a probe says "
                         "a dimension's optimum is actually OUTSIDE its box.")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    floors = None
    if args.floor:
        floors = {}
        for s in args.floor:
            k, _, v = s.partition("=")
            floors[k.strip()] = float(v)
        unknown = [k for k in floors if k not in dim_names(SHARED, True)]
        if unknown:
            print("unknown floor dimension(s): %s" % ", ".join(unknown))
            return 1
    set_instrument(args.instrument)
    set_g_partition(args.g_pooled)
    if args.g_selftest:
        return gate_g_partition()
    if args.render_cal:
        render_cal()
        if not (args.census or args.fit):
            return 0
    if not (args.census or args.fit or args.best or args.tilt or args.floor_probe):
        args.census = args.fit = True

    print("=" * 104)
    print("CAN THE TWO-POLE ATTACK TOPOLOGY MATCH THE NULL'S WIDTH? -- a SHARED-element screen")
    print("=" * 104)
    print("  solver: attack_tap_screen.tf_tap (8-node, gated there to ~1e-14 dB)")
    if INSTRUMENT == "stepped":
        print("  ⭐ INSTRUMENT: STEPPED (session 70's spec; session 93 showed the swept read is worth")
        print("     -29.1 % of width on the pedal's boost null and +11.1 % on the render's)")
        print("  stats : read_notch_sweep.locate -- ONE definition, shared with attack_stepped_gate")
        print("  grid  : the STIMULUS's own %d tones, %g Hz core, %g-%g Hz; the record's bins for h"
              % (len(FNOTCH), R.N.CORE_STEP, FNOTCH[0], FNOTCH[-1]))
    else:
        print("  ⚠ INSTRUMENT: SWEPT -- the OLD control. Session 70's spec is a stepped-sine read,")
        print("     so this scores the corrected requirement with the wrong instrument. Use it to")
        print("     reproduce sessions 64-66, not to select a candidate.")
        print("  stats : attack_notch_probe.locate_notch -- shared with attack_render_gate")
        print("  grid  : %.2f Hz over %g-%g Hz for the null; the record's own bins for h"
              % (FNOTCH[1] - FNOTCH[0], FNOTCH[0], FNOTCH[-1]))
    print("  f0 residual normalised by %.2f Hz (this instrument's resolution); depth floor %.1f dB;"
          % (RES_HZ, M.DEPTH_FLOOR_DB))
    print("  width residual by 10 % of each target width")

    print("\n" + "=" * 104)
    print("GATES")
    print("=" * 104)
    print("  A SOLVER      delegated to attack_tap_screen's own gate (not re-implemented here)")
    if not gate_width():
        return 1
    cal, cal_ok = gate_calibration()
    tgt = screen_targets(cal)
    print("\n  the requirement, in the screen's own units (f0 Hz / depth dB / width Hz):")
    for pos in POSITIONS:
        print("      %-6s %8.2f %8.2f %8.1f" % (pos, *tgt[pos]))

    tgt_g, g_rec = (None, None)
    if not args.no_absgain:
        tgt_g, g_rec = gate_absgain(tgt)

    out = dict(calibration={p: list(cal[p]) for p in POSITIONS}, cal_ok=bool(cal_ok),
               targets={p: list(tgt[p]) for p in POSITIONS},
               absgain=g_rec)

    if args.floor_probe:
        out["floor_probe"] = bound_profile(tgt, tgt_g, args.floor_probe, args.quick)
        if out["floor_probe"] is None:
            return 1

    if args.tilt:
        out["tilt"] = tilt_probe()

    if args.census:
        out["census"] = {k: list(v) for k, v in census(tgt).items()}

    if args.best:
        print("\n" + "=" * 104)
        print("GATE D SEARCH -- recover a target this family DEFINITIONALLY makes")
        print("=" * 104)
        made = full_stats(dict(PROP, R12=PROP["R12"] * 1.7, C9=PROP["C9"] * 0.6),
                          dict(PROP_RD, boost=700.0), PROP_C5T)
        if made is None:
            print("  the self-generated target is itself pathological -- GATE D cannot run")
            return 1
        synth = {p: made["notch"][p] for p in POSITIONS}
        _, _, gparts = run(["R12", "C9"], tgt, fit_tap=False, quick=True, override=synth,
                           wt_bb=0.0)
        print("  recovering a self-generated (f0, depth, width) triple x3: cost %.5f  %s"
              % (gparts[0], "OK" if gparts[0] < 0.15 else "FAIL -- failures unreadable"))
        if gparts[0] >= 0.15:
            return 1
        out["best"] = best_point(tgt, args.quick, tgt_g=tgt_g, floors=floors,
                                 rov=(g_rec or {}).get("region_of_validity"))

    if args.fit:
        print("\n" + "=" * 104)
        print("GATE D SEARCH -- recover a target this family DEFINITIONALLY makes")
        print("=" * 104)
        made = full_stats(*(lambda b, r, c: (b, r, c))(
            dict(PROP, R12=PROP["R12"] * 1.7, C9=PROP["C9"] * 0.6),
            dict(PROP_RD, boost=700.0), PROP_C5T))
        if made is None:
            print("  the self-generated target is itself pathological -- GATE D cannot run")
            return 1
        synth = {p: made["notch"][p] for p in POSITIONS}
        # ⚠ wt_bb = 0: score the NOTCH ONLY. A first draft left the broadband term in with the
        # tap PINNED, so the objective also carried an unmatchable h residual and traded notch
        # accuracy against it -- it reported 0.857 and read as "weak optimiser" when it was the
        # gate's own construction. A search gate must ask exactly the question whose failure it
        # is meant to make readable (sessions 57/58/61 all had to tighten this same gate).
        c, x, parts = run(["R12", "C9"], tgt, fit_tap=False, quick=True, override=synth, wt_bb=0.0)
        print("  recovering a self-generated (f0, depth, width) triple x3: cost %.5f  %s"
              % (parts[0], "OK" if parts[0] < 0.15 else "FAIL -- weak optimiser, failures unreadable"))
        if parts[0] >= 0.15:
            return 1

        out["frontier"] = frontier(tgt, args.quick, tgt_g)
        out["scale_diagnostic"] = scale_diagnostic(tgt, args.quick, tgt_g)

        print("\n" + "=" * 104)
        print("THE FIT -- SMALLEST STRUCTURE FIRST. 6 per-throw dof already exist (Rd, C5 x3),")
        print("so a family with FEWER free values than the 9 notch numbers is real evidence;")
        print("one with more hits them by construction and is reported as such.")
        print("=" * 104)
        fits = {}
        for shared in ([], ["R12"], ["C9"], ["R7"], ["R12", "C9"], ["R7", "R12"],
                       ["R12", "C9", "C6"], SHARED):
            nd = ndim(shared, True)
            tag = "shared = %-28s (%d dof)" % ("{" + ", ".join(shared) + "}" if shared else "{}", nd)
            c, x, parts = run(shared, tgt, fit_tap=True, quick=args.quick, tgt_g=tgt_g)
            if parts is None:
                print("\n  %s -> pathological" % tag)
                continue
            fits[",".join(shared)] = show(tag + ("  ⚠ OVER-PARAMETERISED" if nd > 9 + 4 else ""),
                                         c, x, parts, shared, True, tgt, tgt_g)
        out["fits"] = fits

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        json.dump(out, open(args.json, "w"), indent=1, default=float)
        print("\n  wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
