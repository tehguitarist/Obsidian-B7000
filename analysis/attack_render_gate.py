#!/usr/bin/env python3.11
"""Does the BUILT two-pole ATTACK topology meet the measured record, through the REAL chain?
Session 63, Phase 9 / A3 step 20 -- the acceptance gate for session 62's next-step (a).

WHAT IS DIFFERENT ABOUT THIS TOOL, AND WHY IT EXISTS
----------------------------------------------------
Every ATTACK screen up to session 62 was a PYTHON network solve. That is the right instrument for a
reachability question (it is fast enough for differential evolution) but it is not the shipped DSP:
it has no clipper, no oversampling, no bilinear discretisation, no LevelBlend. Session 62's own §7
says so in as many words -- "a LINEAR, PRE-clipper screen ... it says nothing about behaviour at
drive noon/max, which only a real render through the full chain tests."

This tool renders the ACTUAL PedalChain (via OfflineRender) at the measurement's own operating point
and scores it against the pedal the identical way attack_notch_probe.py scores the captures: plain
subtraction of full-resolution transfers, no solve, no taper, no bleed model, no `b0`.

⭐⭐ AND IT SCORES THE CURVE, NOT A HANDFUL OF BANDS.
This is the point the user made in session 63, and it is the correct reading of this project's own
history: the ~320 Hz notch hid for FORTY-SIX sessions behind gates that each read ONE number.
Session 19 fitted `trebleLadderDampR` against a "-3.4 dB" figure that was a 1/3-octave POINT SAMPLE
of a notch centred 316-334 Hz -- understating it by up to 20 dB (session 46). Session 47 then had to
invent `a3_shape_gate.py` because "A3 is below ~200 Hz" had survived on single-feature gates, and
session 60 item 8b was found BY THE USER READING A GRAPH, not by any gate in the tree. So:

  * every comparison here is over the whole 40 Hz - 2 kHz curve at the measurement's own 5.86 Hz
    bins, and the residual is reported as an rms AND a peak AND the frequency where the peak is;
  * SHAPE descriptors are reported beside the level ones -- slope in dB/decade over the flat region,
    residual curvature, and the spread -- because a model can match a median and still have the
    wrong tilt (session 60 item 11's unexplained cut-shape disagreement is exactly that);
  * a PNG overlay is written, because that is the representation the notch was finally found in;
  * and the coarse table is printed too, so the curve read and the band read can be compared rather
    than one silently replacing the other.

⚠ THE 320 Hz WINDOW IS EXCLUDED FROM THE BROADBAND READ BY NAME, NEVER SILENTLY (the session-40
rule). It is a notch, not a gain: it is scored separately, as (f0, depth) per throw.

GATES -- run before any number is read
-------------------------------------
  1 LIVENESS   the shipped default (drawn network) and the proposal must give DIFFERENT h. A gate
               that cannot see the change it is testing measures nothing (session 62's own
               liveness lesson, and session 56's L-009).
  2 IDENTITY   at its defaults the built stage must reproduce the DRAWN network's h -- i.e. the
               topology change is a no-op until it is asked for. Cross-checked against ctest's
               bit-identity result rather than assumed.
  3 BLEED      at LEVEL max / BLEND max the clean bleed is zero BY TOPOLOGY, so h is the ATTACK
               ratio. Verified on the render, not trusted: the model's own OD/bleed split is
               checked by re-rendering at BLEND=0 and confirming it is silent.
  4 CONVERGED  the read is taken from the two QUIETEST stimulus levels and they must agree, because
               boost pushes ~8 dB more into the J201 -- which sits UPSTREAM of DRIVE and never
               idles (session 59 item 3), so compression reaches boost first (session 61 item 3).

SCOPE
-----
  ATTACK is [ENG]; this tests a PROPOSAL against a measurement, not a schematic. Notch depths are
  LOWER bounds (probe gate 1(b) -- shoulder contamination and bin smearing both UNDERSTATE), so the
  depth RANKING carries the claim, not calibrated dB. h is a RATIO between throws, so anything
  common to all three cancels by construction and is not identified here.

Usage:
  python3.11 analysis/attack_render_gate.py [--proposal|--default] [--png OUT] [--json OUT]
  python3.11 analysis/attack_render_gate.py --both        # default AND proposal, side by side
"""
import argparse
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                                    # noqa: E402
import captures as C                                   # noqa: E402  (the capture -> render-args map)
with redirect_stdout(io.StringIO()):
    import attack_notch_probe as P                     # noqa: E402  (locator, windows, floors)
from parallel import pmap, race_check                  # noqa: E402

RENDER = "build/OfflineRender_artefacts/Release/OfflineRender"
OUTDIR = "build/attack_render_gate"

# The operating point the measurement was taken at: drive MIN (clipper idle), LEVEL MAX (the wiper
# shorts to the OD source, so the clean bleed is EXACTLY zero -- session 59 item 6), BLEND MAX.
#
# ⚠⚠ DERIVED FROM THE CAPTURE, NOT HAND-WRITTEN -- session 65. The first version of this list was
# `["--drive","0.0","--level","1.0","--blend","1.0"]`, which is correct as far as it goes and
# SILENTLY WRONG in what it omits: every flag left off falls back to OfflineRender's own default,
# and those defaults are NOT the captures' settings. `gruntIdx` defaults to 0 = BOOST while these
# captures are GRUNT CUT -- a first-order highpass at ~36 Hz instead of ~896 Hz, i.e. a 6.6 dB
# difference in slope across 200 -> 480 Hz alone. That is the whole of session 64's "GAP #1b
# reopened, the OD path is 6.2 dB too dark" finding (see §4 "A3 step 22"). `loMidFreq`/`hiMidFreq`
# default to 2 where the captures use 1; harmless only because the mid stages are unity at the
# flat knob, which is now asserted rather than assumed (GATE 0).
#
# ⭐ THE FIX IS STRUCTURAL, NOT A CORRECTED CONSTANT: build the argument list by asking
# `captures.render_args` what THIS capture file's settings are, so the render condition cannot
# drift from the measurement condition again. `--attack` is dropped because it is the variable.
def _base_args():
    """Every non-ATTACK flag of the FLAT reference capture, straight from the filename parser."""
    args = C.render_args(C.parse_capture(P.FLAT))
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "--attack":
            skip = True
            continue
        out.append(a)
    return out


BASE = _base_args()
ATTACK_IDX = {"flat": "0", "boost": "1", "cut": "2"}

# Session 62's proposed point. Realised as FitParams: trebleC5 is the base cap and the trims are
# ADDITIVE (a small parallel cap on the same pole), which is how a +-7 % move should be built.
PROPOSAL = [
    "attackTapRa=470e3", "attackTapRb=506e3", "attackTapRc=78.5e3", "attackTapR11=212e3",
    "trebleC5=19.7e-9", "attackC5TrimBoost=1.1e-9", "attackC5TrimCut=2.7e-9",
    "trebleLadderDampR=6.14e3", "attackDampBoost=478", "attackDampCut=6.04e3",
    "trebleC8=0",          # session 62 screened with C8 REMOVED; leaving it in is a different model
]

BROAD = P.BROAD_WIN                                    # (80, 1600) -- where h is claimed flat
CURVE = (40.0, 2000.0)                                 # the whole compared curve


# =============================================================================================
# rendering
# =============================================================================================
def stamp(out, cmd):
    """Write the exact argv that produced a render, beside it.

    ⚠ WHY: session 65 fixed the GRUNT condition, re-rendered THIS tool's `dflt_*`/`prop_*`, and
    then read attack_shape_screen's GATE C -- which silently mixed those fresh renders with its own
    `cal_*` anchor, still on disk from the previous condition. The half-refreshed set produced a
    plausible table (out-of-sample width error "+29..+49 %") that was pure artefact; re-rendering
    the anchor moved it to -1.6..+15.7 %. That is `rebaseline-all-derived-artefacts` again, and the
    reason a render must carry its own condition rather than depend on someone remembering which
    files a change invalidated -- the same habit as `a3_blend_decompose` printing `grunt=CUT` into
    its CSV header. `check_stamp` is what makes it a gate rather than a note.
    """
    with open(out + ".args.json", "w") as fh:
        json.dump({"argv": cmd}, fh, indent=1)


def check_stamp(path, expect):
    """Refuse a render whose recorded argv is not `expect` (argv minus in/out paths)."""
    side = path + ".args.json"
    if not os.path.exists(side):
        sys.exit("%s has no .args.json stamp -- it predates the condition gate and cannot be "
                 "trusted. Delete it and re-render." % path)
    got = json.load(open(side))["argv"][3:]
    if got != expect:
        sys.exit("%s was rendered at a DIFFERENT condition and would silently corrupt this run:\n"
                 "   on disk: %s\n   wanted : %s\nDelete it and re-render."
                 % (path, " ".join(got), " ".join(expect)))


def render(tag, pos, fits, quiet=True):
    """Render one ATTACK position through the real chain; returns the aligned signal."""
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "%s_%s.wav" % (tag, pos))
    cmd = [RENDER, A.ORIG, out] + BASE + ["--attack", ATTACK_IDX[pos]]
    for f in fits:
        cmd += ["--fit", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("render failed for %s/%s:\n%s\n%s" % (tag, pos, " ".join(cmd), r.stderr))
    stamp(out, cmd)
    if not quiet:
        print("    " + r.stdout.strip().splitlines()[-1])
    return out


def transfer_of(path, orig, seg):
    x = A.load(path)
    if not A.is_full_length(x, orig):
        sys.exit("%s is TRUNCATED" % path)
    x, _ = A.align(x, orig)
    return A.transfer(A.seg_of(x, seg), A.seg_of(orig, seg))


def _curves_one(job):
    """One ATTACK position: render it and take its transfer at every level. Unit of parallelism."""
    tag, pos, fits, orig, levels = job
    path = render(tag, pos, fits)
    return pos, {L: transfer_of(path, orig, seg) for L, seg in levels}


def model_curves(tag, fits, orig, levels, jobs=None):
    """{position: {level: (f, mag_dB)}} for the rendered model.

    The three ATTACK positions render CONCURRENTLY -- they are independent conditions, each
    writing its own `<tag>_<pos>.wav` (plus its own `.args.json` condition stamp), so the
    parallel form is bit-identical. race_check() pins that the paths really are distinct, since
    a `tag` collision here would put two positions in one file and the stamp check would then
    happily validate whichever wrote last.
    """
    jobs_list = [(tag, pos, fits, orig, levels) for pos in P.POSITIONS]
    race_check([os.path.join(OUTDIR, "%s_%s.wav" % (tag, pos)) for pos in P.POSITIONS])
    return dict(pmap(_curves_one, jobs_list, jobs=jobs))


# =============================================================================================
# curve + shape statistics -- the substance of this tool
# =============================================================================================
def h_curve(tf, pos, level):
    """h(f) = throw - flat, over the compared band, by plain subtraction."""
    f, m = tf[pos][level]
    _, mf = tf["flat"][level]
    sel = (f >= CURVE[0]) & (f <= CURVE[1])
    return f[sel], (m - mf)[sel]


def broad_mask(f):
    """The claimed-flat region with the notch window removed BY NAME (never silently)."""
    return ((f >= BROAD[0]) & (f <= BROAD[1])
            & ~((f >= P.NOTCH_EXCLUDE[0]) & (f <= P.NOTCH_EXCLUDE[1])))


def shape(f, h):
    """Level AND shape descriptors. A model can hit a median and have the wrong tilt."""
    m = broad_mask(f)
    fb, hb = f[m], h[m]
    lg = np.log10(fb)
    # slope/curvature from a quadratic in log10(f): a median alone cannot see either.
    c2, c1, _ = np.polyfit(lg, hb, 2)
    return dict(median=float(np.median(hb)), mean=float(np.mean(hb)),
                spread=float(hb.max() - hb.min()),
                slope_db_per_decade=float(c1 + 2.0 * c2 * float(np.mean(lg))),
                curvature=float(c2), n=int(len(fb)))


def residual(f, hm, hp):
    """Model-vs-pedal residual as a CURVE: rms, peak and WHERE the peak is."""
    m = broad_mask(f)
    r = (hm - hp)[m]
    i = int(np.argmax(np.abs(r)))
    return dict(rms=float(np.sqrt(np.mean(r ** 2))), peak=float(r[i]),
                peak_hz=float(f[m][i]), n=int(len(r)))


def notch_triple(tf, level):
    """locate_notch returns a dict of every quantity the verdict uses; keep (f0, depth) as the
    parabola-REFINED frequency and the shoulder-relative depth -- the probe's own definitions, not
    re-derived here."""
    out = {}
    for pos in P.POSITIONS:
        f, m = tf[pos][level]
        n = P.locate_notch(f, m)
        # ⚠ f_bin, NOT f_ref. The record (sessions 60-62: 316.4 / 328.1 / 334.0 Hz) is quoted on
        # the measurement's own 5.86 Hz bin grid, and those three values are exactly bins 54/56/57.
        # Silently switching to the parabola-refined frequency here would move every comparison by
        # ~1-2 Hz against a record measured the other way -- the session-33 transcription trap in a
        # new guise. The refined value is carried alongside as `f_ref` for anyone who wants it.
        #
        # ⚠ WIDTH now comes from `locate_notch` too (session 64). It used to be a private copy in
        # this file, and session 64 needed the SAME statistic inside a fast network screen to fit
        # against -- two implementations of one definition is the silent-divergence trap session 62
        # called out for the network solver. One oracle, three callers.
        out[pos] = (n["f_bin"], n["depth"], n["f_ref"], n["width"], n["width_i"])
    return out


# =============================================================================================
def pedal_reference(orig, levels):
    """The pedal's own curves, loaded and gated by attack_notch_probe's own loader."""
    with redirect_stdout(io.StringIO()) as buf:
        caps = P.load_all(orig)
    if "all three full length" not in buf.getvalue():
        sys.exit("the pedal captures did not pass attack_notch_probe's own gate:\n" + buf.getvalue())
    tf = {}
    for pos, x in caps.items():
        tf[pos] = {L: A.transfer(A.seg_of(x, seg), A.seg_of(orig, seg)) for L, seg in levels}
    return tf


def report_curve(tag, tfm, tfp, level, note=""):
    print("\n  %s%s" % (tag, note))
    print("  MODEL row then PEDAL row; slope is dB/decade over the flat region, so a matching")
    print("  median with a mismatched slope is visible instead of averaging away.")
    print("  %-6s %8s %8s %8s %9s %9s   %s"
          % ("throw", "median", "spread", "slope", "resid rms", "resid pk", "peak at"))
    rows = {}
    for pos in ("boost", "cut"):
        f, hm = h_curve(tfm, pos, level)
        _, hp = h_curve(tfp, pos, level)
        sm, sp = shape(f, hm), shape(f, hp)
        rs = residual(f, hm, hp)
        print("  %-6s %+8.2f %8.2f %+8.2f %9.2f %+9.2f   %7.1f Hz"
              % (pos, sm["median"], sm["spread"], sm["slope_db_per_decade"],
                 rs["rms"], rs["peak"], rs["peak_hz"]))
        print("  %-6s %+8.2f %8.2f %+8.2f   <- PEDAL (%d bins, floor %.3f dB)"
              % ("", sp["median"], sp["spread"], sp["slope_db_per_decade"], sm["n"], P.DIFF_FLOOR))
        rows[pos] = dict(model=sm, pedal=sp, resid=rs)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", action="store_true")
    ap.add_argument("--default", action="store_true")
    ap.add_argument("--both", action="store_true")
    ap.add_argument("--png", default="build/attack_render_gate/h_curves.png")
    ap.add_argument("--json", default=None)
    # ⭐ Score an arbitrary candidate. attack_shape_screen.py emits its point as a `fits` list, and
    # gate C over there shows the fast screen is only a LEVER FINDER (+-10-27 % on width), so a
    # candidate has to be landed HERE. Passing the list through a file rather than retyping it
    # keeps the session-33 transcription trap out of the loop.
    ap.add_argument("--fits-json", default=None,
                    help="JSON with a 'fits' list (or {'best': {'fits': [...]}}) to render as a "
                         "third variant, tagged 'cand'")
    args = ap.parse_args()
    if not (args.proposal or args.default or args.both):
        args.both = True

    if not os.path.exists(RENDER):
        sys.exit("OfflineRender not built: cmake --build build --target OfflineRender")
    if not os.path.exists(A.ORIG):
        sys.exit("reference stimulus not found at %s" % A.ORIG)
    orig = A.load(A.ORIG)
    levels = [(L, seg) for L, seg in P.LEVELS if L in P.QUIET]

    print("=" * 104)
    print("DOES THE BUILT TWO-POLE ATTACK TOPOLOGY MEET THE RECORD? -- scored as a CURVE")
    print("=" * 104)
    print("  chain: OfflineRender (the real PedalChain), drive MIN / LEVEL MAX / BLEND MAX")
    print("  curve: %.0f-%.0f Hz at %.2f Hz bins; broadband read over %.0f-%.0f Hz EXCLUDING the"
          % (CURVE[0], CURVE[1], (A.FS / 8192.0), BROAD[0], BROAD[1]))
    print("         %.0f-%.0f Hz notch window BY NAME (it is a null, not a gain)"
          % P.NOTCH_EXCLUDE)
    print("  floor: h is a difference of two measurements => %.3f dB" % P.DIFF_FLOOR)

    print("\n  loading the PEDAL reference through attack_notch_probe's own capture gate...")
    tfp = pedal_reference(orig, levels)
    print("  ok.")

    variants = []
    if args.default or args.both:
        variants.append(("DRAWN (shipped defaults)", "dflt", []))
    if args.proposal or args.both:
        variants.append(("TWO-POLE PROPOSAL", "prop", PROPOSAL))
    if args.fits_json:
        d = json.load(open(args.fits_json))
        fits = d.get("fits") or (d.get("best") or {}).get("fits")
        if not fits:
            sys.exit("%s has no 'fits' list (nor best.fits)" % args.fits_json)
        print("\n  candidate from %s:\n    %s" % (args.fits_json, " ".join(fits)))
        variants.append(("CANDIDATE (%s)" % os.path.basename(args.fits_json), "cand", fits))

    print("\n  rendering %d variant(s) x 3 throws..." % len(variants))
    tfm = {}
    for name, tag, fits in variants:
        tfm[tag] = model_curves(tag, fits, orig, levels)
    print("  ok.")

    # ---- GATE 0 CONDITION --------------------------------------------------------------
    # ⚠⚠ THE GATE SESSION 64 DID NOT HAVE, AND IT IS WHY ITS HEADLINE DID NOT SURVIVE. Every
    # comparison in this file assumes the render sits at the captures' own operating point. That
    # was hand-written as four flags, and the flags NOT written silently took OfflineRender's
    # defaults -- `--grunt 0` (Boost) against captures at `--grunt 1` (Cut). The check is now:
    # the flags actually handed to the renderer must equal, term for term, what
    # `captures.render_args` says this capture file is, with ATTACK the only difference.
    print("\n" + "=" * 104)
    print("GATES")
    print("=" * 104)
    want = C.render_args(C.parse_capture(P.FLAT))
    got = BASE + ["--attack", ATTACK_IDX["flat"]]
    wd = dict(zip(want[0::2], want[1::2]))
    gd = dict(zip(got[0::2], got[1::2]))
    diff = sorted(k for k in set(wd) | set(gd) if wd.get(k) != gd.get(k))
    print("  0 CONDITION  render flags vs %s: %d flag(s) differ   %s"
          % (P.FLAT, len(diff), "OK" if not diff else "FAIL: " + ", ".join(diff)))
    if diff:
        for k in diff:
            print("      %-16s capture=%s  render=%s" % (k, wd.get(k), gd.get(k)))
        sys.exit("render condition does not match the capture -- every number below would be void")
    print("      (%s)" % " ".join(BASE))

    live = None
    if len(variants) == 2:
        f, a = h_curve(tfm["dflt"], "boost", P.MAIN)
        _, b = h_curve(tfm["prop"], "boost", P.MAIN)
        live = float(np.max(np.abs(a - b)))
        print("  1 LIVENESS   drawn vs proposal, worst |d h| = %.2f dB   %s"
              % (live, "OK" if live > 1.0 else "FAIL -- the gate cannot see the change"))
        if live <= 1.0:
            sys.exit(1)
    else:
        print("  1 LIVENESS   skipped (single variant; run --both)")

    # ---- GATE 3 BLEED ------------------------------------------------------------------
    # ⚠ A FIRST DRAFT OF THIS GATE TESTED NOTHING AND IS RECORDED HERE SO IT IS NOT REWRITTEN.
    # It rendered BLEND = 0 and asserted the result was far below BLEND = max, on the reasoning
    # that this proved "the OD path is what is being measured". But BLEND = 0 is not silence --
    # it is 100 % CLEAN, the full-level dry signal -- so at drive MIN (where the OD path is
    # quiet) the two are naturally within a few dB and the check reported -5.7 dB / "CHECK" for
    # a model that is perfectly fine. It measured the drive knob, not the bleed.
    #
    # The premise that actually matters is a property of the LevelBlend NETWORK: at LEVEL max
    # the wiper shorts to the OD source, so the clean bleed coefficient is EXACTLY zero and the
    # output at BLEND max IS the OD path (session 59 item 6). That is checkable directly against
    # the same oracle LevelBlendTest uses -- so check it, rather than a proxy that cannot fail
    # for the right reason.
    with redirect_stdout(io.StringIO()):
        import eq_reference as EQ
    bleed = float(EQ.level_blend_tf(level=1.0, blend=1.0, vo=0.0, vc=1.0))
    odgain = float(EQ.level_blend_tf(level=1.0, blend=1.0, vo=1.0, vc=0.0))
    print("  3 BLEED      at LEVEL=1/BLEND=1 the clean coefficient is %.3e and the OD coefficient"
          % bleed)
    print("               is %.6f  =>  %s" % (odgain,
          "OK -- h IS the ATTACK ratio, no bleed to dilute it" if abs(bleed) < 1e-12
          else "FAIL -- a nonzero bleed dilutes h toward zero"))
    if abs(bleed) >= 1e-12:
        sys.exit(1)
    print("               (a common bleed could only shrink |h|, never manufacture +8.6 dB --")
    print("                session 60 item 2 -- so every h below is also a LOWER bound on |h|.)")

    # ---- GATE 4 CONVERGED -------------------------------------------------------------
    # ⚠ AND THE THRESHOLD ON THIS ONE WAS WRONG TOO, IN A WAY WORTH KEEPING. The first draft
    # gated |h(-36) - h(-30)| against the 0.204 dB difference floor and reported CHECK for both
    # variants -- but the PEDAL fails that same threshold (0.469 dB at boost), so it was testing
    # something neither the model nor the device does. Two reasons: (a) session 61 item 3 measured
    # that boost's depth genuinely spreads across level because boost pushes ~8 dB more into the
    # J201, which sits upstream of DRIVE and never idles; (b) a WORST-over-249-bins statistic is
    # dominated by per-bin noise, which is why session 60's 1/3-octave read of the same thing was
    # 0.065 dB. So: gate the RMS, against the PEDAL'S OWN value as the yardstick, and print the
    # worst bin beside it as information.
    print("  4 CONVERGED  the two quietest levels must agree AS WELL AS THE PEDAL'S DO:")
    ped_conv = {}
    for pos in ("boost", "cut"):
        f, h36 = h_curve(tfp, pos, -36.0)
        _, h30 = h_curve(tfp, pos, -30.0)
        m = broad_mask(f)
        d = (h36 - h30)[m]
        ped_conv[pos] = float(np.sqrt(np.mean(d ** 2)))
        print("      %-26s rms %.3f dB, worst bin %.3f dB   <- the yardstick"
              % ("PEDAL " + pos, ped_conv[pos], float(np.max(np.abs(d)))))
    conv_ok = True
    for name, tag, _ in variants:
        for pos in ("boost", "cut"):
            f, h36 = h_curve(tfm[tag], pos, -36.0)
            _, h30 = h_curve(tfm[tag], pos, -30.0)
            m = broad_mask(f)
            d = (h36 - h30)[m]
            r = float(np.sqrt(np.mean(d ** 2)))
            ok = r <= max(2.0 * ped_conv[pos], P.DIFF_FLOOR)
            conv_ok &= ok
            print("      %-20s %-5s rms %.3f dB, worst bin %.3f dB   %s"
                  % (tag, pos, r, float(np.max(np.abs(d))), "OK" if ok else "CHECK"))

    # ---- the broadband curve ----------------------------------------------------------
    print("\n" + "=" * 104)
    print("THE BROADBAND CURVE -- h(f) model vs pedal, whole-band, level AND shape")
    print("=" * 104)
    out = {}
    for name, tag, _ in variants:
        out[tag] = dict(name=name, broadband=report_curve(name, tfm[tag], tfp, P.MAIN))

    # ---- the broadband median PER LEVEL ------------------------------------------------
    # ⭐ Session 61 item 3's lesson applied: quote the QUIETEST row. If the model's boost falls
    # short of the pedal's +8.63 dB because the extra level is being COMPRESSED away somewhere
    # in the real chain (the tap raises what IC2_A sees, and RailClamp has been enabled since
    # session 21), the shortfall must SHRINK toward the quiet end. If it does not, the shortfall
    # is the network's and not the operating point's. This distinguishes the two for the cost of
    # reading rows the tool has already rendered.
    print("\n" + "=" * 104)
    print("BROADBAND MEDIAN vs STIMULUS LEVEL -- is a shortfall the NETWORK or COMPRESSION?")
    print("=" * 104)
    print("  %-22s %-6s %9s %9s %9s   %s" % ("variant", "throw", "-36 dBFS", "-30 dBFS",
                                             "-18 dBFS", "trend toward quiet"))
    for src, nm in ([(tfp, "PEDAL")] + [(tfm[t], t) for _, t, _ in variants]):
        for pos in ("boost", "cut"):
            meds = []
            for L in (-36.0, -30.0, -18.0):
                f, h = h_curve(src, pos, L)
                meds.append(float(np.median(h[broad_mask(f)])))
            print("  %-22s %-6s %+9.2f %+9.2f %+9.2f   %+.2f dB from -18 to -36"
                  % (nm, pos, meds[0], meds[1], meds[2], meds[0] - meds[2]))

    # ---- the notch triple ------------------------------------------------------------
    print("\n" + "=" * 104)
    print("THE NOTCH TRIPLE -- (f0, depth) per throw. Depth is a LOWER BOUND, so the RANKING")
    print("carries the claim, not the calibrated dB.")
    print("=" * 104)
    ped = notch_triple(tfp, P.MAIN)
    print("  %-26s %-24s %-24s %s" % ("variant", "f0 cut/boost/flat Hz", "depth cut/boost/flat dB",
                                      "f0 spread"))
    pf = [ped[p][0] for p in P.POSITIONS]
    print("  %-26s %6.1f %6.1f %6.1f    %6.2f %6.2f %6.2f    %6.2f Hz"
          % ("PEDAL", ped["cut"][0], ped["boost"][0], ped["flat"][0],
             ped["cut"][1], ped["boost"][1], ped["flat"][1], max(pf) - min(pf)))
    for name, tag, _ in variants:
        n = notch_triple(tfm[tag], P.MAIN)
        mf = [n[p][0] for p in P.POSITIONS]
        print("  %-26s %6.1f %6.1f %6.1f    %6.2f %6.2f %6.2f    %6.2f Hz"
              % (name, n["cut"][0], n["boost"][0], n["flat"][0],
                 n["cut"][1], n["boost"][1], n["flat"][1], max(mf) - min(mf)))
        out[tag]["notch"] = {p: dict(f0=n[p][0], depth=n[p][1]) for p in P.POSITIONS}
        out[tag]["notch_err"] = {p: dict(df0=n[p][0] - ped[p][0], ddepth=n[p][1] - ped[p][1])
                                 for p in P.POSITIONS}
    print("\n  ⚠ AND THE WIDTH, which (f0, depth) cannot express and the OVERLAY PLOT made obvious.")
    print("     Bin span is the RECORD's definition; the interpolated column is what a fit should")
    print("     use, because the pedal's boost null is only ~4 bins wide (see locate_notch).")
    print("  %-26s %-24s %-24s" % ("variant", "half-depth BIN span (Hz)", "INTERPOLATED (Hz)"))
    print("  %-26s %6.1f %6.1f %6.1f    %6.1f %6.1f %6.1f"
          % ("PEDAL", ped["cut"][3], ped["boost"][3], ped["flat"][3],
             ped["cut"][4], ped["boost"][4], ped["flat"][4]))
    for name, tag, _ in variants:
        n = notch_triple(tfm[tag], P.MAIN)
        print("  %-26s %6.1f %6.1f %6.1f    %6.1f %6.1f %6.1f"
              % (name, n["cut"][3], n["boost"][3], n["flat"][3],
                 n["cut"][4], n["boost"][4], n["flat"][4]))
        out[tag]["notch_width"] = {p: n[p][3] for p in P.POSITIONS}
        out[tag]["notch_width_i"] = {p: n[p][4] for p in P.POSITIONS}
        out[tag]["notch_width_err"] = {p: n[p][4] - ped[p][4] for p in P.POSITIONS}
    print("  ⭐ ORDER is the structural claim: the pedal moves the null DOWN in BOTH throws re flat")
    print("     and makes boost ~2x DEEPER. Session 61 found 0 of 782 random draws of the DRAWN")
    print("     topology reproduce that pattern, so matching the ORDER is the real result.")

    # ---- the coarse table, printed BESIDE the curve read ------------------------------
    print("\n" + "=" * 104)
    print("COARSE TABLE -- the same thing at named frequencies, so the curve read and the band read")
    print("can be COMPARED rather than one silently replacing the other")
    print("=" * 104)
    hdr = "  %9s %10s" % ("f Hz", "pedal")
    for name, tag, _ in variants:
        hdr += " %12s" % tag
    print(hdr + "     <- h boost")
    for target in P.H_SHOW:
        f, hp = h_curve(tfp, "boost", P.MAIN)
        i = int(np.argmin(np.abs(f - target)))
        inwin = P.NOTCH_EXCLUDE[0] <= f[i] <= P.NOTCH_EXCLUDE[1]
        line = "  %9.1f %+10.2f" % (f[i], hp[i])
        for name, tag, _ in variants:
            _, hm = h_curve(tfm[tag], "boost", P.MAIN)
            line += " %+12.2f" % hm[i]
        print(line + ("   (NOTCH WINDOW -- not a gain)" if inwin else ""))

    # ---- the graph -------------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
        for pos, col in (("boost", "tab:red"), ("cut", "tab:blue")):
            f, hp = h_curve(tfp, pos, P.MAIN)
            ax[0].semilogx(f, hp, col, lw=2.2, label="pedal %s" % pos)
            for name, tag, _ in variants:
                _, hm = h_curve(tfm[tag], pos, P.MAIN)
                ls = "--" if tag == "prop" else ":"
                ax[0].semilogx(f, hm, col, ls=ls, lw=1.4, alpha=0.9,
                               label="%s %s" % (tag, pos))
        ax[0].axvspan(*P.NOTCH_EXCLUDE, color="0.85", zorder=0)
        ax[0].set_ylabel("h = throw - flat  (dB)")
        ax[0].set_title("ATTACK broadband ratio h(f): built model vs pedal\n"
                        "(grey = the notch window, excluded from the broadband read by name)")
        ax[0].grid(True, which="both", alpha=0.3)
        ax[0].legend(fontsize=7, ncol=3)
        # ⚠ Normalise to the LOWER SHOULDER (the 200-270 Hz max -- locate_notch's own definition
        # of the depth reference), NOT to the band median. A first draft used the median over
        # 200-500 Hz, which INCLUDES the null: a model with a deeper null pulls that median down
        # and so paints its shoulders as several dB higher than the pedal's. That artefact read as
        # a real "wrong shoulder slope" finding until it was checked. Same class as session 62's
        # ratio-denominator rule -- normalise to something the feature under test does not move.
        def shoulder_ref(f_, m_):
            _, ms_ = P.band(f_, m_, *P.SHOULDER_WIN)
            return float(np.max(ms_))
        for pos in P.POSITIONS:
            f, m = tfp[pos][P.MAIN]
            sel = (f >= 200.0) & (f <= 500.0)
            ax[1].semilogx(f[sel], m[sel] - shoulder_ref(f, m), lw=2.2, label="pedal %s" % pos)
        for name, tag, _ in variants:
            if tag != "prop":
                continue
            for pos in P.POSITIONS:
                f, m = tfm[tag][pos][P.MAIN]
                sel = (f >= 200.0) & (f <= 500.0)
                ax[1].semilogx(f[sel], m[sel] - shoulder_ref(f, m), "--", lw=1.4,
                               label="model %s" % pos)
        pass
        ax[1].set_xlabel("Hz")
        ax[1].set_ylabel("dB re LOWER SHOULDER (200-270 Hz max)")
        ax[1].set_title("The cancellation null, 200-500 Hz -- SHAPE, not one band "
                "(width is measured at each null's own half-depth)")
        ax[1].grid(True, which="both", alpha=0.3)
        ax[1].legend(fontsize=7, ncol=2)
        os.makedirs(os.path.dirname(args.png) or ".", exist_ok=True)
        fig.tight_layout()
        fig.savefig(args.png, dpi=120)
        print("\n  wrote %s" % args.png)
    except ImportError:
        print("\n  (matplotlib not available -- no plot written)")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        # ⚠ `bleed_sep_db=sep` used to live here and `sep` no longer exists -- it was the first
        # draft's separation-from-BLEND=0 number, deleted when that gate was replaced (see GATE 3),
        # leaving --json a NameError that only fires on the path nobody ran. Now records what the
        # replacement gate actually establishes.
        json.dump(dict(liveness=live, bleed_clean_coeff=bleed, bleed_od_coeff=odgain,
                       converged=bool(conv_ok), pedal_converged=ped_conv,
                       floor=P.DIFF_FLOOR, variants=out),
                  open(args.json, "w"), indent=1, default=float)
        print("  wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
