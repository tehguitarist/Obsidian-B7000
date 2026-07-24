#!/usr/bin/env python3.11
"""Phase-7 SESSION 17 — §3j GATE: is the residual drive-axis ramp a CLIPPER INPUT-COUPLING
(GRUNT cap bank + R16) drive-dependent MEMORY effect?

╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║ ⚠⚠ OUTCOME (recorded the SAME session, after `clipa0_grunt_corner_probe.py`):                ║
║ THIS GATE PRINTS "PASSED" AND THAT VERDICT IS NOT ACTIONABLE. DO NOT BUILD ON IT.            ║
║                                                                                              ║
║ The flaw is in condition (B). It establishes authority by sweeping the GRUNT position, i.e.  ║
║ by changing the coupling CAPACITANCE Cg — but Cg is C11/C12/C13, BOM- and schematic-verified ║
║ and NOT an adjustable model quantity. So (B) measured the authority of something that cannot ║
║ be changed. The actionable question is narrower and was not asked: **does any ADMISSIBLE     ║
║ change to the coupling network have authority?**                                             ║
║                                                                                              ║
║ The only free parameter in that network is clipA0 (it sets the input-node impedance          ║
║ R18/(1+A0), hence the corner). Sweeping it 3..30 x kInputRef 0.87..2.40 moves the corner     ║
║ 379..1941 Hz and the min->noon leg NOT AT ALL (+0.9..+2.7 dB against the capture's +12.6).   ║
║ The reason is structural and exact: lowering A0 drops the corner (MORE 220 Hz reaches the    ║
║ clipper, ~+13 dB) while simultaneously dropping the closed-loop gain                         ║
║ -(R18/R16)*A0/(A0+1+R18/R16) by ~15 dB. **The two effects cancel.** clipA0 is not a coupling ║
║ knob; it is a knob whose two roles annihilate each other.                                     ║
║                                                                                              ║
║ => The input-coupling candidate is REFUTED as the ramp mechanism, despite this gate's PASS.  ║
║    The §3v drive-axis candidate list is now EXHAUSTED (taper, rails, onset, coupling).       ║
║                                                                                              ║
║ WHAT IS STILL WORTH KEEPING from this script: the model over-produces the GRUNT boost-vs-cut ║
║ effect (+19.7 dB vs the capture's +11.6) and matches it at clipA0 ~ 8-12, NOT at the 20-30   ║
║ circuit.md asserts. That is a real, separate finding about A0 — see the probe's own notes.   ║
║                                                                                              ║
║ LESSON (generalises): a §3j authority test must sweep a quantity the fit is ALLOWED to        ║
║ change. Sweeping a fixed circuit value proves the mechanism matters physically while telling ║
║ you nothing about whether you can DO anything with it.                                        ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝

WHERE THIS COMES FROM. Session 16 re-diagnosed the blocker (§3v.4): DRIVE sits DOWNSTREAM of the
J201, so at low drive H3-H2 is a J201-intrinsic constant and the model is STRUCTURALLY OBLIGED to
be flat across min/9:30/noon. It is; the capture is not (+12.6 dB min->noon leg). Session 16 then
gated three drive-axis mechanisms: the DRIVE taper (refuted — wrong direction), the DRIVE op-amp
rail clamp (refuted — moves only 2:30/max), and clipper ONSET POSITION via kInputRef (NECESSARY,
NOT SUFFICIENT — best physical ramp rms 6.26 vs 13.97, but no single K works jointly).

That leaves exactly ONE untested candidate on the drive axis: a drive-dependent MEMORY effect in
the clipper's INPUT COUPLING. The mechanism is real and specific:

    the GRUNT high-pass corner is  1/(2*pi*Cg*(R16 + R18/(1+A_eff)))

and A_eff is the CD4049's *effective* gain, which COLLAPSES as the clipper saturates. So as DRIVE
rises, the input impedance R18/(1+A_eff) RISES, the corner FALLS, and more of the 220 Hz fit tone
reaches the clipper. That is a genuinely drive-dependent, frequency-dependent gain change that no
memoryless VTC can produce -- and it acts hardest exactly where the model is too flat.

⚠ HONEST FRAMING — THE MECHANISM IS ALREADY IN THE MODEL. `Clipper.h` solves R16 + the Cg bank +
the finite-gain VTC + R18||C14 as ONE coupled network (both caps trapezoidal companions) via a
per-sample Newton iteration on node W. So this gate is NOT "does the model lack the mechanism"; it
is the sharper question: **does the input-coupling network have AUTHORITY over the drive-axis ramp
at all, and if so does the model already reproduce the real pedal's version of it?** If the model
already matches, the coupling is not the residual's source and there is nothing to build.

THE MEASUREMENT — a matched 2x2 factorial that already exists on disk, no new captures:

        drive \\ grunt |  cut (4n7)                  boost (224.7n)
        --------------+-----------------------------------------------------------
        noon          |  ref-od.wav                 grunt-boost_base-od.wav
        max           |  drive-1700_base-od.wav     drive-1700_grunt-boost_base-od.wav

GRUNT moves the coupling cap by 48x while changing NOTHING else in the circuit, so it is a clean
instrument for the coupling network. The INTERACTION term of the 2x2,

        I = [ (H3-H2)|boost,max - (H3-H2)|cut,max ] - [ (H3-H2)|boost,noon - (H3-H2)|cut,noon ]

is precisely "how much does the coupling's effect DEPEND ON DRIVE" -- the quantity this candidate
claims is mis-modelled. Both differences are harmonic-TO-harmonic, so the BLEND clean bleed, the
makeup and both tapers cancel EXACTLY (the session-10 objective fix), and the interaction cancels
any drive-independent GRUNT modelling error on top of that. It is a difference of differences: it
is immune to essentially everything except the thing being tested.

⚠ SCOPE LIMIT, STATED UP FRONT: grunt-boost was captured at drive noon and max only, so the 2x2
constrains the noon->max leg, while the residual deficit is the min->noon leg. The inference is
one-directional and stated as such: the corner shift is DRIVEN by clipper saturation, so it is
largest at high drive -- if the coupling shows no drive-interaction between noon and max, it
cannot be supplying a bigger one between min and noon. Part (B) probes the min->noon leg directly,
but MODEL-ONLY (no capture exists there); it is an authority test, not a validation.

PRE-REGISTERED SIGNATURE — all three must hold, or STOP and do not build:
  (A) LIVENESS (L-009 — check the knob is live BEFORE trusting any null). The model's GRUNT
      difference |Delta| must exceed 1.0 dB at at least one drive setting. A null from a dead
      knob is not evidence.
  (B) MODEL AUTHORITY over the leg that is actually wrong. Sweeping GRUNT cut->boost (48x of
      coupling cap) must move the model's min->noon leg by >= 4.0 dB -- a third of the 12.6 dB
      deficit. If a 48x change in the coupling network barely moves the leg, then NO refinement
      of that network can supply the missing ramp, and the candidate is dead on authority alone.
  (C) CAPTURE-vs-MODEL DISCREPANCY. |I_capture - I_model| must be >= 2.0 dB. This is the
      discriminating half: if the model ALREADY reproduces the real pedal's coupling x drive
      interaction, the coupling network is modelled correctly and cannot be where the residual
      lives -- STOP, regardless of how much authority (B) found.

(B) and (C) are deliberately opposed: (B) fails if the mechanism is too WEAK to matter, (C) fails
if it is already RIGHT. The candidate survives only by being both consequential and wrong.

Run:  /opt/homebrew/bin/python3.11 analysis/clipper_input_coupling_gate.py [--point a,b,c,...]
Log:  analysis/fit_logs/step7_clipper_input_coupling_gate.log
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import fit_nonlinear as F
from captures import parse_capture, render_args, load_capture, RENDER_BIN

FS = 48000
LOG = "analysis/fit_logs/step7_clipper_input_coupling_gate.log"
CAP = "analysis/captures"
LABELS = ["min", "9:30", "noon", "2:30", "max"]

# GRUNT index -> (name, coupling cap). captures._GRUNT_IDX = {"boost": 0, "cut": 1, "flat": 2};
# Clipper.h: Cut = C11 alone, Flat = C11+C12, Boost = C11+C13.
GRUNTS = [(1, "cut", 4.7e-9), (2, "flat", 51.7e-9), (0, "boost", 224.7e-9)]

# FULLY PHYSICAL clipper (clipA0 in circuit.md's 20-30, clipSat summing to the ~7 V R19-dropped
# rail) + the session-15 branch-B JFET core. 10th element is kInputRef (session 17). The gate is
# run at the physical point because that is the point the fit is being asked to reach; --point
# overrides it with the session-17 fitted vector once that fit lands.
POINT_PHYSICAL = [0.30, 4.0, 1.0, 0.5, 1.8, 25.0, 3.15, 3.85, 1.5, 0.87]

LIVENESS_DB = 1.0     # (A) pre-registered bar
AUTHORITY_DB = 4.0    # (B) pre-registered bar
DISCREP_DB = 2.0      # (C) pre-registered bar

# Own stimulus path, NOT fit_nonlinear's /tmp/fit_tone220.wav — this gate is routinely run while a
# fit is in flight, and rewriting the file a live optimiser is reading is a race that would corrupt
# one render silently rather than fail loudly.
TONE_IN = "/tmp/cicg_tone220.wav"

# The 2x2: (capture file, drive label, grunt index, grunt name)
FACTORIAL = [
    ("ref-od.wav",                          "noon", 1, "cut"),
    ("grunt-boost_base-od.wav",             "noon", 0, "boost"),
    ("drive-1700_base-od.wav",              "max",  1, "cut"),
    ("drive-1700_grunt-boost_base-od.wav",  "max",  0, "boost"),
]


def model_ratio(point, cap_file, grunt_idx):
    """Model H3-H2 (dB) at 220 Hz for one capture's control settings, GRUNT overridden."""
    extra, own = F._split_flags(point)
    parsed = dict(parse_capture(cap_file))
    parsed["gruntIdx"] = grunt_idx
    o = "/tmp/cicg.wav"
    subprocess.run([RENDER_BIN, TONE_IN, o, "--os", "8"] + own + render_args(parsed, extra),
                   check=True, capture_output=True)
    p = F._profile(A.load(o)[int(0.5 * FS):int(1.15 * FS)])
    return p["H3"] - p["H2"]


def capture_ratio(cap_file):
    c = load_capture(f"{CAP}/{cap_file}")
    p = F._profile(A.seg_of(c, "tone_220"))
    return p["H3"] - p["H2"]


def main():
    point = POINT_PHYSICAL
    for arg in sys.argv[1:]:
        if arg.startswith("--point="):
            point = [float(v) for v in arg.split("=", 1)[1].split(",")]

    F._short_tone(TONE_IN, F.F0)
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 100)
    emit("SESSION-17 §3j GATE — clipper INPUT COUPLING (GRUNT cap bank + R16) as a")
    emit("drive-dependent MEMORY effect: the last untested mechanism on the drive axis")
    emit("=" * 100)
    emit("Point under test: " + ", ".join(f"{k}={v:g}" for k, v in zip(F.FIT_KEYS, point)))
    emit("")
    emit("PRE-REGISTERED (all three required, or STOP):")
    emit(f"  (A) LIVENESS  : model |GRUNT delta| > {LIVENESS_DB:.1f} dB somewhere (L-009)")
    emit(f"  (B) AUTHORITY : GRUNT cut->boost moves the MODEL min->noon leg by >= {AUTHORITY_DB:.1f} dB")
    emit(f"  (C) DISCREPANCY: |I_capture - I_model| >= {DISCREP_DB:.1f} dB  (else the coupling is")
    emit("                   already modelled correctly and cannot be the residual)")
    emit("")

    # ---------------- (B) MODEL authority: GRUNT x full drive sweep ----------------
    emit("-" * 100)
    emit("(B) MODEL authority — H3-H2 across the FULL drive sweep at each GRUNT position")
    emit("    (model only; no capture exists at grunt-boost below noon — authority test, not a")
    emit("     validation). The min->noon leg is the quantity that is +12.6 dB in the capture and")
    emit("     structurally ~0 in the model.")
    emit("-" * 100)
    emit(f"  {'GRUNT':>6} {'Cg':>9} | " + " ".join(f"{l:>7}" for l in LABELS) + f" | {'min->noon':>10}")
    legs, noon_by_cg = {}, []
    for gidx, gname, cg in GRUNTS:
        row = {}
        for cap_file, lbl in F.DRIVE_CAPS:
            row[lbl] = model_ratio(point, cap_file, gidx)
        legs[gname] = row["noon"] - row["min"]
        noon_by_cg.append((cg, row["noon"]))
        emit(f"  {gname:>6} {cg*1e9:>7.1f}nF | " + " ".join(f"{row[l]:>+7.1f}" for l in LABELS)
             + f" | {legs[gname]:>+10.1f}")
    leg_span = max(legs.values()) - min(legs.values())
    emit("")
    emit(f"  capture min->noon leg = +12.6 dB;  model leg spans {leg_span:.1f} dB across a 48x "
         f"coupling-cap change")

    # ---- The ACTIONABLE quantity: what coupling cap would the model need at GRUNT=cut? ----
    # This is the robust discriminator (no interaction statistic, no saturated cells): the capture
    # at GRUNT=cut / drive=noon reads -10.6, and the model's noon value is monotone in Cg, so
    # log-interpolating the model's own (Cg -> noon) curve says what Cg the real pedal's "cut"
    # position BEHAVES like. If that lands far above the 4n7 the schematic gives C11, the model's
    # cut-position coupling is too attenuating at 220 Hz -- a concrete, falsifiable target.
    # ⚠ Interpolate ONLY over the cut->flat segment. The model's noon value is NOT monotone in Cg
    # across the whole bank (cut -23.9 -> flat -3.1 -> boost -4.2: it turns over once the corner is
    # already well below 220 Hz and further cap buys nothing), so a whole-range np.interp would
    # silently interpolate against a fold and return a meaningless capacitance.
    tgt = capture_ratio("ref-od.wav")          # capture, GRUNT=cut, drive=noon
    (c0, v0), (c1, v1) = noon_by_cg[0], noon_by_cg[1]
    if v0 <= tgt <= v1:
        c_eff = 10 ** (np.log10(c0) + (np.log10(c1) - np.log10(c0)) * (tgt - v0) / (v1 - v0))
        emit(f"  ** implied effective coupling at GRUNT=cut: {c_eff*1e9:.1f} nF "
             f"(schematic C11 = 4.7 nF, ratio {c_eff/4.7e-9:.1f}x) **")
        emit(f"     i.e. to reach the capture's noon value ({tgt:+.1f} dB) the model needs the cut")
        emit("     position to pass 220 Hz as if its coupling cap were that large — equivalently")
        emit("     its GRUNT corner (1/(2*pi*Cg*(R16 + R18/(1+A_eff)))) is too HIGH.")
    else:
        emit(f"  (capture noon/cut {tgt:+.1f} dB is outside the model's cut->flat span "
             f"[{v0:+.1f}, {v1:+.1f}] — no effective coupling cap implied)")

    # ---------------- (A)+(C) the capture 2x2 interaction ----------------
    emit("")
    emit("-" * 100)
    emit("(A)+(C) The matched 2x2 factorial — capture vs model, H3-H2 (dB) at 220 Hz")
    emit("-" * 100)
    emit(f"  {'drive':>6} {'grunt':>6} | {'capture':>9} {'model':>9} {'c-m':>8}")
    cv, mv = {}, {}
    for cap_file, dlbl, gidx, gname in FACTORIAL:
        c = capture_ratio(cap_file)
        m = model_ratio(point, cap_file, gidx)
        cv[(dlbl, gname)] = c
        mv[(dlbl, gname)] = m
        emit(f"  {dlbl:>6} {gname:>6} | {c:>+9.1f} {m:>+9.1f} {c-m:>+8.1f}")

    d_noon_c = cv[("noon", "boost")] - cv[("noon", "cut")]
    d_max_c = cv[("max", "boost")] - cv[("max", "cut")]
    d_noon_m = mv[("noon", "boost")] - mv[("noon", "cut")]
    d_max_m = mv[("max", "boost")] - mv[("max", "cut")]
    I_cap = d_max_c - d_noon_c
    I_mdl = d_max_m - d_noon_m
    # ---- CEILING CHECK on the capture cells (added after first run; do NOT drop) ----
    # The capture's H3-H2 SATURATES at about +1 dB: noon/boost, max/cut and max/boost all read
    # ~+1.0-2.0 while noon/cut reads -10.6. With 3 of the 4 cells pinned on that ceiling, the
    # INTERACTION term (C) is largely measuring "only one cell is unsaturated" rather than a clean
    # coupling x drive effect. That does not invalidate the gate — (B) and the direct cut-position
    # discrepancy below are unaffected — but (C) must NOT be quoted as a clean measurement.
    ceil_cells = [k for k, v in cv.items() if v > -3.0]
    emit("")
    emit(f"  ⚠ CEILING CHECK: capture H3-H2 saturates ~+1 dB; cells at/near the ceiling: "
         f"{', '.join('/'.join(k) for k in ceil_cells)} ({len(ceil_cells)} of 4)")
    if len(ceil_cells) >= 3:
        emit("     => (C)'s interaction is CONFOUNDED by saturation and is reported as WEAK")
        emit("        evidence only. The robust findings are (B) and the direct cut-position gap.")
    emit("")
    emit(f"  GRUNT effect (boost - cut)   at noon : capture {d_noon_c:+.1f}   model {d_noon_m:+.1f}")
    emit(f"  GRUNT effect (boost - cut)   at max  : capture {d_max_c:+.1f}   model {d_max_m:+.1f}")
    emit(f"  ** INTERACTION (how much the coupling's effect DEPENDS ON DRIVE) **")
    emit(f"     I_capture = {I_cap:+.1f} dB      I_model = {I_mdl:+.1f} dB      "
         f"|difference| = {abs(I_cap - I_mdl):.1f} dB")

    # ---------------- verdict ----------------
    live = max(abs(d_noon_m), abs(d_max_m))
    okA = live > LIVENESS_DB
    okB = leg_span >= AUTHORITY_DB
    okC = abs(I_cap - I_mdl) >= DISCREP_DB
    emit("")
    emit("=" * 100)
    emit("VERDICT")
    emit("=" * 100)
    emit(f"  (A) LIVENESS    : model |delta| max {live:.1f} dB  (bar {LIVENESS_DB:.1f})   "
         f"{'PASS' if okA else 'FAIL'}")
    emit(f"  (B) AUTHORITY   : model min->noon leg span {leg_span:.1f} dB  (bar {AUTHORITY_DB:.1f})   "
         f"{'PASS' if okB else 'FAIL'}")
    emit(f"  (C) DISCREPANCY : |I_cap - I_mdl| {abs(I_cap - I_mdl):.1f} dB  (bar {DISCREP_DB:.1f})   "
         f"{'PASS' if okC else 'FAIL'}")
    emit("")
    if okA and okB and okC:
        emit("  ** GATE PASSES AS WRITTEN — BUT THE VERDICT IS NOT ACTIONABLE. See the OUTCOME box")
        emit("  at the top of this file. (B) establishes authority by sweeping the coupling CAP,")
        emit("  which is BOM-fixed; the only ADMISSIBLE knob in this network is clipA0, and its two")
        emit("  roles (corner position vs closed-loop gain) cancel — analysis/clipa0_grunt_corner_")
        emit("  probe.py measures the leg as immobile at +0.9..+2.7 dB across A0 3-30 x K 0.87-2.40.")
        emit("  Treat this as REFUTED for the ramp; keep only the A0-vs-GRUNT-effect finding.")
    else:
        emit("  ** GATE FAILED — STOP. Do NOT build the input-coupling refinement. **")
        if not okA:
            emit("  (A) failed: the GRUNT knob is not live at this point — fix the probe before")
            emit("      drawing ANY conclusion from a null here (L-009).")
        if not okB:
            emit("  (B) failed: a 48x change in the coupling cap barely moves the min->noon leg, so")
            emit("      no refinement of that network can supply the +12.6 dB the capture shows.")
            emit("      The mechanism is real but INCONSEQUENTIAL for the quantity that is wrong.")
        if not okC:
            emit("  (C) failed: the model already reproduces the real pedal's coupling x drive")
            emit("      interaction, so the coupling network is NOT mis-modelled and cannot be")
            emit("      where the residual lives.")
        emit("")
        emit("  With taper, rails, onset-alone and now input coupling all gated, the drive-axis")
        emit("  candidate list from §3v is EXHAUSTED. Report that plainly rather than fitting past")
        emit("  it — the next session needs a NEW hypothesis (or a measurement that produces one),")
        emit("  not another parameter set forced through an unexplained ramp.")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
