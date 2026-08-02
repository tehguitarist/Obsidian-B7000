#!/usr/bin/env python3.11
"""Score the ATTACK notch with ONE instrument on both sides — the stepped sine, on the REAL render.

Session 93, Phase 9 backlog item 4 (the two-pole ATTACK re-fit against session 70's corrected spec).

WHY THIS TOOL HAS TO EXIST BEFORE ANY RE-FIT
--------------------------------------------
Session 70 replaced the ATTACK specification with a stepped-sine measurement:

    drive-min, -30 dBFS   f0  323.03 / 326.41 / 330.17 Hz   (cut / boost / flat, spread 7.13)
                          dep  15.27 /  37.98 /  15.58 dB
                          wid   75.4 /   19.2 /   75.6 Hz

The OLD swept record it replaces was f0 316.4 / 328.1 / 334.0, depth 14.93 / 32.70 / 16.01, width
77.9 / 27.1 / 71.9. Session 70's item (5) measured the difference on the SAME audio with both
instruments, so it is an instrument-only delta with no take-to-take or knob term in it:

    boost  +5.28 dB deeper and -29.1 % narrower ;  cut/flat within 0.43 dB and 5.2 %.

⛔⛔ AND THAT IS EXACTLY THE SIZE OF THE RESIDUAL THE RE-FIT IS AIMED AT. `attack_render_gate.py`
— the arbiter for every ATTACK candidate since session 63 — measures the RENDER with the SWEPT
instrument (`attack_notch_probe.locate_notch` on a 5.86 Hz CSD of the main test signal's
`sweep_clean`). Scoring a stepped-sine PEDAL spec against a swept-read RENDER would book the
instrument's own smearing as model error, on the one throw (boost) whose width the whole re-fit is
about. That is `band-sampling-depends-on-curve-resolution` (s90) and `verify-the-BASELINE-not-its-
LABEL` (s37) in the same place.

⇒ this tool renders the real chain through the STEPPED stimulus and reads it with the STEPPED
locator, so the pedal and the model are measured by one instrument and the smearing cancels. That
is the same logic session 70 used for its own GATE 2, applied to the render side.

⭐ THE PRE-REGISTERED PREDICTION (stated here before the run, so it can fail)
---------------------------------------------------------------------------
Bin smearing understates a null's depth and overstates its width, and it does so IN PROPORTION TO
HOW NARROW THE FEATURE IS relative to the 5.86 Hz grid — which is why session 70 saw -29 % on the
pedal's 19 Hz boost null and <6 % on its ~75 Hz cut/flat nulls. Session 63's built topology is
~2x too broad (59.6 Hz at boost in swept units), i.e. its boost null is a CUT/FLAT-sized feature
on that grid. So:

    the render's swept->stepped width delta should be SMALL at every throw (single-digit %),
    NOT the -29 % the pedal showed at boost.

If that holds, the corrected spec makes the boost width residual LARGER (19.2 Hz demanded against
~59 Hz delivered, ~3.1x, where the old pairing read 2.20x) and item 4 is a real, harder target.
If instead the render also narrows by ~29 %, then a large part of what sessions 63-66 called a
width excess was the instrument, and the re-fit's premise has to be rewritten before any fitting.
Either way the answer comes from a measurement, not from the argument above.

GATES — all run and printed before any comparison number is read
----------------------------------------------------------------
  0 LOCATOR     `read_notch_sweep.selftest()` — recovers synthesised notches of known f0, depth AND
                width. Not re-implemented here: one oracle, not a second copy (session 62's rule).
  1 CONDITION   every render carries a `.args.json` stamp of its exact argv and it is re-checked
                (`rebaseline-all-derived-artefacts`, s65's half-refreshed-anchor incident).
  2 ALIGNMENT   the stepped read is a per-tone projection at an exact frequency, so a misalignment
                does not show up as leakage — it shows up as nothing at all. Lag is asserted small
                and CONSISTENT across throws rather than assumed.
  3 LIVENESS    shipped default vs the session-62 proposal must give DIFFERENT notch stats. A gate
                that cannot see the change it is testing measures nothing (s62/s56 L-009).
  4 SWAP        the instrument-swap control above, run on BOTH sides. This is the gate the tool
                exists for; it is reported per throw and the verdict is COMPUTED, never narrated.

SCOPE — read before quoting anything here
-----------------------------------------
  * ATTACK is [ENG]. This scores a PROPOSAL against a measurement; there is no schematic to defer
    to (`circuit.md`).
  * Magnitude only, at drive MIN / LEVEL max / BLEND max, where the clean bleed is exactly zero by
    topology (session 59 item 6) and the clipper is idle. Nothing here is a claim about drive noon.
  * Depth is referred to the 200-270 Hz lower shoulder, as every depth in this project is. The
    stepped read removes bin smearing but NOT shoulder contamination — session 70 item (4) is
    explicit that depth became a value from a fix in the READER, not in the stimulus.
  * The render condition is taken from `captures.render_args` of the flat reference capture, never
    hand-written (session 65's GRUNT-default incident).

Usage:
    /opt/homebrew/bin/python3.11 analysis/attack_stepped_gate.py --selftest
    /opt/homebrew/bin/python3.11 analysis/attack_stepped_gate.py [--json OUT] [-j N]
"""
import argparse
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import read_notch_sweep as R                              # noqa: E402  (stepped instrument)
with redirect_stdout(io.StringIO()):                      # both print a report at import
    import attack_render_gate as G                        # noqa: E402  (render condition + proposal)
from parallel import pmap, add_jobs_arg                   # noqa: E402

OUTDIR = "build/attack_stepped_gate"
OUT_JSON = "analysis/reports/s93_attack_stepped.json"
OUT_JSON_CAND = "analysis/reports/s94_attack_stepped_cand.json"

# The spec's own operating point. LEVELS_DB[0] = -30 dBFS: the quiet, near-linear read every ATTACK
# number in this project is quoted at. -18 is carried as the level CONTROL, exactly as session 70
# quotes it (there the boost null moves 37.98 -> 31.95 dB and 19.2 -> 27.1 Hz while cut/flat barely
# move, which is session 61 item 3's compression mechanism and NOT a network property).
LEVELS = list(R.LEVELS_DB)
SPEC_LEVEL = R.LEVELS_DB[0]
THROWS = R.THROWS                                          # ["cut", "boost", "flat"]
PEDAL_PAT = R.CONDS["drive-min"]                           # notch_drive-0700_level-1700_attack-{throw}.wav

# What "the model" means here. `[]` is the shipped default (the DRAWN network); PROPOSAL is session
# 62's two-pole point, imported rather than retyped so it cannot drift from the arbiter's copy.
# `--fits-json` adds a third, `cand` -- session 94, so a re-fit can be LANDED on this instrument
# instead of on `attack_render_gate.py`, which reads the render with the swept one. The two
# reference variants are always kept beside it: a candidate is only readable against the point it
# is meant to improve on, and GATE 3 needs both of them regardless.
VARIANTS = {"default": [], "proposal": list(G.PROPOSAL)}
REFERENCE_VARIANTS = tuple(VARIANTS)                       # frozen BEFORE any candidate is added

# Session 70's instrument-only delta on the PEDAL, for the swap gate to compare against. Restated
# from the run this session reproduced to the digit; it is a COMPARISON, never a target.
PEDAL_SWAP = {"cut": -3.2, "boost": -29.2, "flat": +5.2}   # % width, swept -> stepped
SWAP_NARROW_PCT = -15.0                                    # "materially narrower" boundary (see verdict)

# The SWEPT record's own widths, used ONLY as the denominator of the swept-vs-swept ratio column so
# the two instruments' verdicts can be compared like for like. Imported from the stepped reader's
# copy rather than retyped. ⚠ Never mix these with a stepped model width — that is the very error
# this tool exists to remove.
PEDAL_SWEPT_WIDTH = {t: R.SWEPT_RECORD[t][2] for t in THROWS}


# =============================================================================================
# rendering
# =============================================================================================
def render_one(job):
    """Render one (variant, throw) through the STEPPED stimulus. Returns the output path."""
    variant, throw = job
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "%s_%s.wav" % (variant, throw))
    cmd = [G.RENDER, R.STIMULUS, out] + G.BASE + ["--attack", G.ATTACK_IDX[throw]]
    for f in VARIANTS[variant]:
        cmd += ["--fit", f]
    expect = cmd[3:]
    if os.path.exists(out) and os.path.exists(out + ".args.json"):
        G.check_stamp(out, expect)                         # GATE 1 on the cached path
        return out
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("render failed for %s/%s:\n%s\n%s" % (variant, throw, " ".join(cmd), r.stderr))
    G.stamp(out, cmd)
    return out


def read_both(path, stim):
    """Read one signal with BOTH instruments. Returns (stepped-per-level, swept, lag)."""
    x = R.load_raw(path)
    x, lag = R.align_to_stim(x, stim)
    stepped = {}
    for lvl in LEVELS:
        f, mag = R.curve(x, stim, lvl)
        stepped[lvl] = R.locate(f, mag)
    return stepped, R.swept_locate(x, stim), lag


def _read_job(job):
    tag, path = job
    stim = _read_job.stim
    return tag, read_both(path, stim)


# =============================================================================================
# gates
# =============================================================================================
def gate_alignment(lags):
    """Lag must be CONSISTENT WITHIN a side — never equal ACROSS sides.

    ⚠ The first version of this gate asserted one spread over pedal AND render together and failed
    at 71 samples. That was the gate being wrong, not the data: the render carries the oversampler's
    anti-imaging/anti-aliasing FIR latency and the pedal capture cannot (`dsp.md`, "Dry/wet phase
    alignment across the oversampled region"). MEASURED rather than assumed, by re-rendering one
    throw at three factors:  OS 1 -> +10,  OS 2 -> +59,  OS 8 -> +74 samples.  It tracks the factor,
    and OS 1 lands on the pedal's own +3..+9 — so the offset IS the FIR latency and `align_to_stim`
    removes it. (It also pins OfflineRender's default at OS = 8, the factor the 129-capture matrix
    renders at.) What a real defect would look like is a lag that varies BETWEEN THROWS of one side,
    since the throws differ only by a switch position; that is what this gates.
    """
    print("=" * 108)
    print("GATE 2. ALIGNMENT — the stepped read projects onto an exact frequency, so a bad lag")
    print("        produces a plausible-looking curve rather than an obvious failure.")
    print("=" * 108)
    sides = {}
    for tag, lag in sorted(lags.items()):
        print("   %-24s lag %+6d samples" % (tag, lag))
        sides.setdefault("pedal" if tag.startswith("pedal") else "render", []).append(lag)
    ok = True
    for side, vals in sorted(sides.items()):
        spread, worst = max(vals) - min(vals), max(abs(v) for v in vals)
        good = spread <= 8 and worst <= 256
        ok = ok and good
        print("   %-6s spread %d samples, worst |lag| %d  (limits: spread <= 8, |lag| <= 256)   %s"
              % (side, spread, worst, "PASS" if good else "FAIL"))
    off = int(np.median(sides["render"]) - np.median(sides["pedal"]))
    print("   render - pedal offset %+d samples = the OS-8 FIR latency (measured above), removed by"
          " align_to_stim" % off)
    return ok


def gate_liveness(stats):
    print()
    print("=" * 108)
    print("GATE 3. LIVENESS — the shipped default and the session-62 proposal must differ.")
    print("=" * 108)
    worst = 0.0
    for throw in THROWS:
        d = stats[("default", throw)]["stepped"][SPEC_LEVEL]
        p = stats[("proposal", throw)]["stepped"][SPEC_LEVEL]
        df, dd, dw = d["f_ref"] - p["f_ref"], d["depth"] - p["depth"], d["width"] - p["width"]
        # ⚠ nan-safe: `default`'s width is nan BY CONSTRUCTION (see below), and a nan silently
        # poisoning a max() would turn a passing gate into a FAIL for the wrong reason.
        worst = max([worst] + [abs(v) for v in (df, dd, dw) if np.isfinite(v)])
        print("   %-6s  Δf0 %+7.2f Hz   Δdepth %+7.2f dB   Δwidth %+9s Hz"
              % (throw, df, dd, "%+.1f" % dw if np.isfinite(dw) else "n/a"))
    ok = worst > 0.5
    print("   largest single difference %.2f  (limit > 0.5)   %s" % (worst, "PASS" if ok else "FAIL"))
    # ⭐ NOT AN ERROR, AND WORTH SAYING OUT LOUD: the shipped DEFAULT has no measurable null at all
    # (depth ~3 dB against the pedal's 15-38), so its half-depth contour never closes and `width` is
    # nan. That is session 57's finding — the DRAWN [ENG] ladder cannot make this feature — showing
    # up here as a missing statistic rather than a bad one. Printed so a nan is never read as a bug.
    dep = [stats[("default", t)]["stepped"][SPEC_LEVEL]["depth"] for t in THROWS]
    if not any(np.isfinite(stats[("default", t)]["stepped"][SPEC_LEVEL]["width"]) for t in THROWS):
        print("   note: DEFAULT width is nan at every throw — its null is only %.1f-%.1f dB deep, so"
              % (min(dep), max(dep)))
        print("         the half-depth contour never closes. The drawn ladder has no notch to widen.")
    return ok


def gate_swap(stats, pedal):
    """⭐ THE GATE THIS TOOL EXISTS FOR. Same audio, two instruments, both sides."""
    print()
    print("=" * 108)
    print("GATE 4. INSTRUMENT-SWAP CONTROL — swept vs stepped on the SAME audio, both sides.")
    print("=" * 108)
    print("   Session 70 measured this on the PEDAL: the boost null narrows -29 % and cut/flat")
    print("   barely move, because smearing scales with how narrow the feature is. The PREDICTION")
    print("   registered in this tool's header is that the render — whose nulls are ~2x broader —")
    print("   narrows only single digits at every throw. This table decides it.\n")
    print("   %-16s %-7s | %-9s %-9s %-9s | %-9s %-9s %-9s"
          % ("side", "throw", "swept wid", "stepped", "Δ %", "swept dep", "stepped", "Δ dB"))
    print("   " + "-" * 100)
    swap = {}
    rows = [("PEDAL", t, pedal[t]) for t in THROWS]
    rows += [("render/%s" % v, t, stats[(v, t)]) for v in VARIANTS for t in THROWS]
    for side, throw, s in rows:
        sw, st = s["swept"], s["stepped"][SPEC_LEVEL]
        dw = 100.0 * (st["width"] - sw["width"]) / sw["width"]
        dd = st["depth"] - sw["depth"]
        swap.setdefault(side, {})[throw] = dict(width_pct=dw, depth_db=dd,
                                                swept_width=sw["width"], stepped_width=st["width"])
        fmt = (lambda v, n=1: ("%.*f" % (n, v)) if np.isfinite(v) else "n/a")
        print("   %-16s %-7s | %-9s %-9s %-9s | %-9s %-9s %+.2f"
              % (side, throw, fmt(sw["width"]), fmt(st["width"]),
                 ("%+.1f" % dw) if np.isfinite(dw) else "n/a",
                 fmt(sw["depth"], 2), fmt(st["depth"], 2), dd))

    # COMPUTED verdict: does the render reproduce the pedal's boost-specific narrowing, or not?
    # ⚠ A nan width is NOT evidence either way — it means the null was too shallow to measure, so
    # that variant is reported as UNDECIDABLE rather than silently counted as "does not narrow".
    ped_boost = swap["PEDAL"]["boost"]["width_pct"]
    print()
    print("   pedal boost swept->stepped width: %+.1f %%   (session 70 record %+.1f %%)"
          % (ped_boost, PEDAL_SWAP["boost"]))
    reproduced, decidable = [], []
    for v in VARIANTS:
        rb = swap["render/%s" % v]["boost"]["width_pct"]
        # ⚠⚠ THE VERDICT IS SCORED OVER THE REFERENCE VARIANTS ONLY -- session 94, and this is a
        # real defect the first candidate run exposed, not a tidy-up. The question this gate asks
        # is "was sessions 63-66's width excess partly the INSTRUMENT?", and it is answered by how
        # the renders those sessions actually scored (`default`, `proposal`) behave. A `cand` whose
        # null has been FITTED to the pedal's 19 Hz width will narrow like the pedal by
        # construction -- narrowing IS what a narrow feature does on a 5.86 Hz grid -- so counting
        # it would let a SUCCESSFUL fit print "the prediction is REFUTED, re-scope item 4", which
        # is the opposite of what it means. Measured: cand reads -31.8 % against the pedal's
        # -29.1 % and the proposal's +11.1 %. That is a CONSEQUENCE of the fit, reported below the
        # verdict as an observation. (`computed-verdicts-not-narrated`, s34/s61/s68 -- here the
        # verdict was computed but over the wrong population.)
        if v not in REFERENCE_VARIANTS:
            print("   render/%-9s boost swept->stepped width: %+.1f %%   (candidate -- NOT scored in"
                  " the verdict; see the note in gate_swap)" % (v, rb))
            continue
        if not np.isfinite(rb):
            print("   render/%-9s boost swept->stepped width: n/a      -> UNDECIDABLE (no measurable null)"
                  % v)
            continue
        decidable.append(v)
        reproduced.append(rb <= SWAP_NARROW_PCT)
        print("   render/%-9s boost swept->stepped width: %+.1f %%   -> %s"
              % (v, rb, "ALSO narrows materially" if rb <= SWAP_NARROW_PCT else "does NOT narrow materially"))
    if not decidable:
        print("\n   ⇒ VERDICT: UNDECIDABLE — no rendered variant has a null deep enough to measure a")
        print("      width. The swap question cannot be answered from this run.")
        return swap, None
    if any(reproduced):
        print("\n   ⇒ VERDICT: at least one render narrows like the pedal. The prediction in this")
        print("      tool's header is REFUTED, and part of the width excess sessions 63-66 fitted")
        print("      is INSTRUMENT, not model. Re-scope item 4 before fitting anything.")
    else:
        print("\n   ⇒ VERDICT: the render does NOT narrow materially at boost while the pedal does.")
        print("      The prediction HOLDS: the smearing is a property of the pedal's NARROW null,")
        print("      so the corrected spec makes the boost width residual LARGER, not smaller,")
        print("      and the swept-vs-stepped mismatch was a real scoring error worth fixing.")
    return swap, (not any(reproduced))


# =============================================================================================
# report
# =============================================================================================
def report(stats, pedal):
    print()
    print("=" * 108)
    print("THE COMPARISON, IN MATCHED UNITS (stepped sine, both sides, drive-min / -30 dBFS)")
    print("=" * 108)
    print("   %-10s %-7s | %-9s %-9s %-9s | %-9s %-9s %-9s"
          % ("side", "throw", "f0 Hz", "depth dB", "width Hz", "Δf0", "Δdepth", "Δwidth"))
    print("   " + "-" * 96)
    # ⚠ `locate` takes an argmin inside SEARCH_WIN, so a curve with NO interior minimum rails at a
    # window edge and returns that edge as "f0". That is a sentinel, not a measurement
    # (`sentinel-is-not-a-measurement`, s40/s85) — flag it rather than letting 380.00 read as a
    # located null next to the pedal's 326.41.
    edge = lambda r: min(abs(r["f_ref"] - R.SEARCH_WIN[0]), abs(r["f_ref"] - R.SEARCH_WIN[1])) < 0.5

    out = {}
    for throw in THROWS:
        p = pedal[throw]["stepped"][SPEC_LEVEL]
        print("   %-10s %-7s | %-9.2f %-9.2f %-9.1f | %-9s %-9s %-9s"
              % ("PEDAL", throw, p["f_ref"], p["depth"], p["width"], "-", "-", "-"))
    for v in VARIANTS:
        print("   " + "-" * 96)
        for throw in THROWS:
            p = pedal[throw]["stepped"][SPEC_LEVEL]
            m = stats[(v, throw)]["stepped"][SPEC_LEVEL]
            rail = edge(m)
            out.setdefault(v, {})[throw] = dict(
                f0=m["f_ref"], depth=m["depth"], width=m["width"], f0_railed=bool(rail),
                d_f0=m["f_ref"] - p["f_ref"], d_depth=m["depth"] - p["depth"],
                width_ratio=m["width"] / p["width"])
            print("   %-10s %-7s | %-9s %-9.2f %-9s | %-9s %-+9.2f %s"
                  % (v, throw, ("%.2f!" % m["f_ref"]) if rail else "%.2f" % m["f_ref"],
                     m["depth"], ("%.1f" % m["width"]) if np.isfinite(m["width"]) else "n/a",
                     "RAILED" if rail else "%+.2f" % (m["f_ref"] - p["f_ref"]),
                     m["depth"] - p["depth"],
                     ("%.2fx" % (m["width"] / p["width"])) if np.isfinite(m["width"]) else "n/a"))

    if any(out[v][t]["f0_railed"] for v in VARIANTS for t in THROWS):
        print("   ! = f0 railed at a SEARCH_WIN edge (%g-%g Hz): the curve has no interior minimum,"
              % R.SEARCH_WIN)
        print("       so that value is a WINDOW BOUND, not a located null. Δf0 is not defined for it.")

    # ⭐ WHICH THROW IS WORST decides which element to look at — a UNIFORM excess points at a SHARED
    # ladder element (session 63 item 5b), a per-throw one does not. The instrument swap can move
    # that ordering, so both readings are COMPUTED here side by side rather than argued.
    print()
    print("   WIDTH RATIO (model / pedal) under each instrument — same audio, same locator:")
    print("      %-10s %-24s | %-24s | worst throw" % ("variant", "swept vs swept record", "STEPPED vs stepped"))
    for v in VARIANTS:
        sw, st = [], []
        for t in THROWS:
            sw.append(stats[(v, t)]["swept"]["width"] / PEDAL_SWEPT_WIDTH[t])
            st.append(stats[(v, t)]["stepped"][SPEC_LEVEL]["width"]
                      / pedal[t]["stepped"][SPEC_LEVEL]["width"])
        if not all(np.isfinite(x) for x in sw + st):
            print("      %-10s %-24s | %-24s | n/a (no measurable null)" % (v, "n/a", "n/a"))
            continue
        w_sw, w_st = THROWS[int(np.argmax(sw))], THROWS[int(np.argmax(st))]
        out[v]["width_ratio_swept"] = dict(zip(THROWS, sw))
        out[v]["worst_throw_swept"], out[v]["worst_throw_stepped"] = w_sw, w_st
        print("      %-10s %-24s | %-24s | swept=%s  stepped=%s%s"
              % (v, " / ".join("%.2f" % x for x in sw), " / ".join("%.2f" % x for x in st),
                 w_sw, w_st, "   ⭐ MOVED" if w_sw != w_st else ""))

    print()
    print("   f0 SPREAD across throws (the statistic the whole ATTACK spec rests on):")
    ps = [pedal[t]["stepped"][SPEC_LEVEL]["f_ref"] for t in THROWS]
    print("      PEDAL      %.2f Hz   [%s]" % (max(ps) - min(ps), ", ".join("%.2f" % x for x in ps)))
    for v in VARIANTS:
        ms = [stats[(v, t)]["stepped"][SPEC_LEVEL]["f_ref"] for t in THROWS]
        railed = any(out[v][t]["f0_railed"] for t in THROWS)
        out[v]["spread"] = max(ms) - min(ms)
        out[v]["spread_railed"] = bool(railed)
        print("      %-10s %.2f Hz   [%s]%s" % (v, max(ms) - min(ms),
                                               ", ".join("%.2f" % x for x in ms),
                                               "   (RAILED — not a spread)" if railed else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="locator gate only")
    ap.add_argument("--json", default=OUT_JSON)
    ap.add_argument("--fits-json", default=None,
                    help="JSON with a 'fits' list (or {'best': {'fits': [...]}}) to render and "
                         "score as a third variant, tagged 'cand' -- e.g. attack_shape_screen's "
                         "--best output. This is how an ATTACK candidate is LANDED on the stepped "
                         "instrument; attack_render_gate.py reads it with the swept one.")
    add_jobs_arg(ap)
    args = ap.parse_args()

    if args.fits_json:
        d = json.load(open(args.fits_json))
        fits = d.get("fits") or (d.get("best") or {}).get("fits")
        if not fits:
            sys.exit("%s has no 'fits' list (nor best.fits)" % args.fits_json)
        VARIANTS["cand"] = list(fits)
        # ⚠ Do not overwrite session 93's baseline artefact with a candidate run. The default
        # output name changes with the run's CONTENT, not silently with its arguments.
        if args.json == OUT_JSON:
            args.json = OUT_JSON_CAND
        print("\n   CANDIDATE from %s:\n      %s" % (args.fits_json, " ".join(fits)))

    if not R.selftest():                                   # GATE 0 — always, never optional
        print("\n⛔ locator self-test failed — refusing to report measurements")
        return 1
    if args.selftest:
        return 0
    if not os.path.exists(G.RENDER):
        sys.exit("OfflineRender not built: cmake --build build --target OfflineRender")

    print()
    print("   render condition (from captures.render_args, NOT hand-written):")
    print("      " + " ".join(G.BASE))

    jobs = [(v, t) for v in VARIANTS for t in THROWS]
    paths = pmap(render_one, jobs, jobs=args.jobs)

    sr, stim = wavfile.read(R.STIMULUS)
    stim = stim.astype(np.float64)
    _read_job.stim = stim

    stats, lags = {}, {}
    for (v, t), path in zip(jobs, paths):
        st, sw, lag = read_both(path, stim)
        stats[(v, t)] = dict(stepped=st, swept=sw)
        lags["render/%s/%s" % (v, t)] = lag

    pedal = {}
    for t in THROWS:
        p = os.path.join(R.CAP_DIR, PEDAL_PAT.format(throw=t))
        st, sw, lag = read_both(p, stim)
        pedal[t] = dict(stepped=st, swept=sw)
        lags["pedal/%s" % t] = lag

    print()
    ok_align = gate_alignment(lags)
    ok_live = gate_liveness(stats)
    swap, pred_holds = gate_swap(stats, pedal)
    if not (ok_align and ok_live):
        print("\n⛔ a gate failed — the comparison below is NOT reportable")
        return 1

    res = report(stats, pedal)

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as fh:
        json.dump(dict(
            level_db=SPEC_LEVEL, throws=THROWS, condition=G.BASE,
            prediction_holds=bool(pred_holds), swap=swap, compare=res,
            pedal={t: {str(l): pedal[t]["stepped"][l] for l in LEVELS} for t in THROWS},
            render={"%s/%s" % (v, t): {str(l): stats[(v, t)]["stepped"][l] for l in LEVELS}
                    for v in VARIANTS for t in THROWS},
        ), fh, indent=1)
    print("\nwrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
