#pragma once

#include "MnaSolve.h"
#include "RailClamp.h"

// =============================================================================
// EQ block — LO-MID (IC5_D) / HI-MID (IC6_A) peaking stage — circuit.md
//            "LO-MID (IC5_D) / HI-MID (IC6_A) — NODES VERIFIED; identical
//            topology" + the switchable-mid-cap tables.
// =============================================================================
// One reusable class for both mid bands: an inverting-unity flat path with a
// frequency-selective pot leg whose series cap (LO-MID C33 / HI-MID C35) is
// SWITCHED to move the peak centre. Fixed parts per band:
//   R38=R39=2k2 (pot end legs), R40=R41=220k (flat inverting-unity legs),
//   pot Rp=100k B-taper; LO-MID C32=22n across the pot lugs, HI-MID C34=6n8.
// Switchable series cap (the only thing the 3-way switch changes):
//   LO-MID C33: 47n(250Hz) / 10n(500Hz) / 2n2(1kHz)
//   HI-MID C35: 15n(750Hz) / 3n3(1.5kHz) / 820p(3kHz)
//
// ---- Node solve (MNA, matches eq_reference.py :: mid_stage_tf) ---------------
// Signal ground = VD = 0; ideal op-amp holds the (−) node ("virtual ground") at
// 0 V and Vout is the unknown that satisfies its KCL (no KCL is written at the
// driven op-amp OUTPUT node — same active-filter treatment as SallenKeyLPF).
//   Vin --R38--> P3 ;  P1 --R39--> Vout        (pot end legs)
//   pot Rp: P3 --Ra--> W --Rb--> P1  (a = fraction P3→W ; a→0 = full BOOST)
//   C32 across P3↔P1 ;  W --C33--> (−)=0        (C33 = switchable series cap)
//   flat path: Vin --R41--> (−) ;  (−) --R40--> Vout   (inverting-unity, gain −1)
// Unknowns [P3, P1, W, Vout]. Trapezoidal companion caps → the 4×4 conductance
// matrix is REAL and constant for a fixed (a, C33); frequency dependence is
// carried entirely by the per-sample RHS history currents (ieqC32, ieqC33),
// identical convention to the earlier 2-node stages (gc=2C/T; ieq_new =
// 2·gc·v_ab − ieq_old). C33 bridges node W to the virtual-ground node, so its
// companion stamps BOTH node W's KCL and the Vout-determining (−)-node KCL — and
// because the oracle writes the (−) row as "currents INTO the node = 0" (a sign
// flip vs the natural "currents leaving = 0" used for P3/P1/W), the C33 history
// current lands as +ieqC33 in BOTH rows. This exactly reproduces mid_stage_tf,
// which the FR test validates against.
//
// ---- Why not a WDF tree / precomputed-matrix swap ---------------------------
// dsp.md "Fixed (non-runtime) circuit variants": the mid switch only changes a
// cap VALUE, not the network SHAPE, so a live matrix recompute (mna::invert on
// the dirty flag) is the correct model — no per-position precomputed scattering
// matrix. Same for the continuously-variable pot. invert runs only when a pot or
// the switch moves (setPosition / setSeriesCap set dirty), never per sample.
//
// ---- Rail clamp / polarity --------------------------------------------------
// Op-amp output → RailClamp on Vout (GATE item; disabled by default so the
// linear FR test matches the oracle). At the B-taper centre (a=0.5) the stage is
// flat 0 dB; boost (a→0) peaks, cut (a→1) dips. DC gain = −1 (INVERTING): caps
// open at DC, so it is the flat inverting-unity path (Vout = −Vin). This one
// inversion is one of the EQ block's four (IC5_B, Baxandall, LO-MID, HI-MID) →
// net non-inverting through the whole EQ; confirmed here by the DC-step test.
// =============================================================================
class MidBand
{
public:
    // Fixed component values per band. {R38, R39, R40, R41, C32_acrossLugs}.
    struct Values { double r38, r39, r40, r41, c32; };
    static constexpr Values kLoMid { 2.2e3, 2.2e3, 220.0e3, 220.0e3, 22.0e-9 }; // C32
    static constexpr Values kHiMid { 2.2e3, 2.2e3, 220.0e3, 220.0e3, 6.8e-9 };  // C34

    // Switchable series-cap values (the 3-way selector). circuit.md mid tables.
    static constexpr double kLoMid47n = 47.0e-9;  // 250 Hz
    static constexpr double kLoMid10n = 10.0e-9;   // 500 Hz
    static constexpr double kLoMid2n2 = 2.2e-9;    // 1 kHz
    static constexpr double kHiMid15n = 15.0e-9;   // 750 Hz
    static constexpr double kHiMid3n3 = 3.3e-9;    // 1.5 kHz
    static constexpr double kHiMid820p = 820.0e-12; // 3 kHz
    static constexpr double kRp = 100.0e3;         // pot value

    MidBand() = default;

    // Choose which band this instance is + its initial series cap (before prepare()).
    void configure(const Values& v, double seriesCap) noexcept
    {
        val = v;
        cSeries = seriesCap;
    }

    void prepare(double sampleRate)
    {
        twoOverT = 2.0 * sampleRate;
        gc32 = val.c32 * twoOverT;
        gc33 = cSeries * twoOverT;
        gc31 = cInput * twoOverT;   // 0 when the C31 path is disabled
        dirty = true;
        rebuild();  // establish a valid inverse before the first process()
        reset();
    }

    void reset() noexcept { ieqC32 = ieqC33 = ieq31 = 0.0; }

    // Pot position a ∈ [0,1]: a→0 = full BOOST (wiper at P3/input), a→1 = full CUT
    // (wiper at P1/output), a=0.5 = flat. This is the ELECTRICAL pot fraction; the
    // knob→a mapping (B-taper is linear; knob direction) is applied by the processor.
    void setPosition(double a) noexcept
    {
        const double clamped = a < 1e-6 ? 1e-6 : (a > 1.0 - 1e-6 ? 1.0 - 1e-6 : a);
        if (mna::differs(clamped, posA)) { posA = clamped; dirty = true; }
    }

    // 3-way mid switch: swap the series cap (see kLoMid*/kHiMid* above).
    void setSeriesCap(double c) noexcept
    {
        if (mna::differs(c, cSeries)) { cSeries = c; gc33 = cSeries * twoOverT; dirty = true; }
    }

    // ACROSS-LUG cap (LO-MID C32 / HI-MID C34), switched TOGETHER with the series cap
    // as a scaled PAIR (Phase 9 A2c-3, session 27). configure()'s Values::c32 remains
    // the nominal; this overrides it, so a stage that never calls this is unchanged.
    //
    // WHY THE PAIR. A2c-2 fitted the switched series cap and ONE wiper-leg R per band
    // and capped there, because the peaks stayed ~1.31x too broad and the only way to
    // fix width with those parameters is Rw, which pays for it in range. Letting C32
    // move per position (user-authorised 2026-07-26) removes that trade — and the
    // per-position optimum comes out at a near-CONSTANT C32/C33 ratio at all six
    // positions in both bands (10.4 / 9.4 fitted; pinning both to exactly 10.0 costs
    // 0.001 dB). So this is not a per-position fudge at all: it is ONE 2-pole selector
    // swapping a scaled cap pair, which is precisely the constant-Q alternative
    // circuit.md parked for this stage. Holding the ratio fixed makes the stage's Q —
    // and hence its boost/cut range — identical at every switch position, which is
    // what the captures say the pedal does (~+-12 dB everywhere, the GAP #4 finding
    // that Rw was introduced to force). See FitParams::midCapRatioLo.
    void setAcrossCap(double c) noexcept
    {
        if (c > 0.0 && mna::differs(c, val.c32)) { val.c32 = c; gc32 = val.c32 * twoOverT; dirty = true; }
    }

    // Range-limiting series resistance in the WIPER leg (Phase 9 GAP #4, session 22).
    // Sits between the wiper and the switched cap C33/C35, so the leg is a series
    // R+C from node W to the 0 V virtual ground — stamped as ONE branch via the same
    // Norton reduction TrebleAttack.h uses for its lossy C5, with NO new MNA node:
    //   g33eff = gc33/(1 + gc33*Rw),  ieq' = ieqC33/(1 + gc33*Rw).
    // Rw = 0 reproduces the ideal network EXACTLY (the factor is 1), so the existing
    // FR tests against the unmodified oracle stay valid.
    //
    // WHY IT EXISTS. The captures say the real pedal's mid range is ~+-12 dB at EVERY
    // switch position, while this network's values imply +-14.5...+-28 dB. It is fitted,
    // not derived: `schematic-checker` (2026-07-25) returned TOPOLOGY CONFIRMED FAITHFUL
    // (MidBand.h matches circuit.md node for node; the full R1-R54 BOM census leaves no
    // spare resistor), so there is no unmodelled part to find — and circuit.md tags this
    // whole stage's cap table [ENG-caps], computed and never schematic-verified, so there
    // is no ground truth to defer to. Same posture as c21R / trebleLadderDampR / the rail
    // voltages: dsp.md "fit the corner", the capture is authoritative.
    //
    // WHY THIS ELEMENT AND NOT ANOTHER. Two independent signatures pick it out:
    //   * the excess tracks the ABSOLUTE size of the switched cap (47n +26.6 dB down to
    //     820p +1.5 dB) — a series R is negligible while Xc dominates (small caps) and
    //     dominant once the cap is a short (large caps);
    //   * the measured 4-point POT LAW matches the model to ~1 dB at 25%/75% travel and
    //     only diverges at the ends — exactly where the pot's own series resistance stops
    //     masking the wiper leg. (Rail compression was ruled out: the clamp is bit-inert
    //     on these captures. Knob under-travel was ruled out: pedal/model RISES 0.49->0.93
    //     toward the small caps, a ceiling, not a constant scale.)
    // One resistor must serve all three switch positions of a band, so the two smallest
    // caps are slightly over-corrected — an inherent, accepted trade (see FitParams).
    void setWiperR(double rOhm) noexcept
    {
        const double r = rOhm > 0.0 ? rOhm : 0.0;
        if (mna::differs(r, wiperR)) { wiperR = r; dirty = true; }
    }

    // Rail-clamp passthroughs (calibration §6) — applied to Vout (op-amp output).
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    // ---- C31 input coupling cap (session 177, open-work item 16) ----------------
    // LO-MID ONLY: circuit.md has C31 (2u2) between IC5_C's output and this stage's
    // input node "Min".  HI-MID has NO such cap (its input is IC5_D's output wire),
    // so it never calls this and stays on the 4-unknown path bit-for-bit.
    //
    // ⛔⛔ WHY THIS IS A FIFTH NODE AND NOT A `C21Highpass`-SHAPED BOLT-ON STAGE.
    // A coupling cap into a FIXED resistance is a first-order high-pass and can be a
    // separate one-node stage; that is what C21 and C15 are.  This load is NOT fixed:
    // GATE BG measures |Zin| falling 42.2 kOhm -> 2.2 kOhm across the audio band,
    // because C32 shorts P3 to P1 and collapses the Miller-loaded R38+Rp+R39 ladder
    // onto the bare R38+R39.  So |Zin| and |1/(w*C31)| fall TOGETHER through the bass
    // and the divider ratio does not recover: the true insertion is a broad plateau
    // reaching -1.07 dB at a graded band centre, where a fixed-R first-order HP at the
    // same corner predicts -0.02 dB (54x smaller).  The plateau exists only if C31 and
    // the pot network are solved TOGETHER, which is what this does.
    // ⚠ The DC corner itself is 1.715 Hz and IS pot- and switch-position-independent
    // (Ra+Rb = Rp always, and at DC the wiper leg carries no current so G0 = -1
    // exactly).  Do not read that number as a description of the element — it
    // describes only the very bottom of the response.  GATE BG's docstring has both.
    //
    // c31 <= 0 disables it and restores the exact 4-unknown expressions below.
    void setInputCap(double farads) noexcept
    {
        const double next = (farads > 0.0) ? farads : 0.0;
        if (mna::differs(next, cInput)) { cInput = next; dirty = true; }
        if (twoOverT > 0.0)
            gc31 = cInput * twoOverT;
    }

    inline double process(double vin) noexcept
    {
        if (dirty)
            rebuild();

        if (cInput > 0.0)
            return processWithInputCap(vin);

        // RHS: source (R38, R41) + capacitor history. See header stamping.
        //   rhs[P3] = Vin/R38 + ieqC32 ;  rhs[P1] = -ieqC32
        //   rhs[W]  = ieqC33          ;  rhs[Vout] = -Vin/R41 + ieqC33
        // The wiper leg's Norton source is scaled by the same 1/(1+gc33*Rw) factor as
        // its conductance (setWiperR); at Rw=0 dampDiv is 1 and this is the ideal cap.
        const double ieqC33b = ieqC33 / dampDiv;

        double rhs[4];
        rhs[0] = vin / val.r38 + ieqC32;
        rhs[1] = -ieqC32;
        rhs[2] = ieqC33b;
        rhs[3] = -vin / val.r41 + ieqC33b;

        double x[4];
        mna::matvec<4>(yinv, rhs, x);

        // Capacitor state update: Ieq_new = 2*gc*v_ab − Ieq_old.
        ieqC32 = 2.0 * gc32 * (x[0] - x[1]) - ieqC32; // v_ab = P3 − P1
        // Lossy wiper leg: the CAP voltage is the branch voltage minus the Rw drop.
        // i33 = g33eff*W − ieqC33b ; v_c33 = W − i33*Rw. Rw=0 => v_c33 = W exactly.
        const double i33 = g33eff * x[2] - ieqC33b;
        ieqC33 = 2.0 * gc33 * (x[2] - i33 * wiperR) - ieqC33;

        return rail.process(x[3]); // Vout, then op-amp rails
    }

private:
    // 5-unknown path [Vin, P3, P1, W, Vout] — see setInputCap(). Stamps are the 4×4's
    // with Vin promoted from a known to an unknown: the two places it entered the RHS
    // (P3's Vin/R38 and the (−) row's −Vin/R41) move to the LHS as −1/R38 and +1/R41,
    // and Vin gains its own KCL row carrying C31's companion. Maps 1:1 onto
    // `analysis/c31_corner_gate.py :: mid_tf_through_c31`, which the FR test checks.
    inline double processWithInputCap(double vs) noexcept
    {
        const double ieqC33b = ieqC33 / dampDiv;

        double rhs[5];
        rhs[0] = gc31 * vs - ieq31; // C31 companion: cap from the SOURCE node to Vin
        rhs[1] = ieqC32;
        rhs[2] = -ieqC32;
        rhs[3] = ieqC33b;
        rhs[4] = ieqC33b;

        double x[5];
        mna::matvec<5>(yinv5, rhs, x);

        ieq31 = 2.0 * gc31 * (vs - x[0]) - ieq31;      // v_ab = Vs − Vin
        ieqC32 = 2.0 * gc32 * (x[1] - x[2]) - ieqC32;  // v_ab = P3 − P1
        const double i33 = g33eff * x[3] - ieqC33b;
        ieqC33 = 2.0 * gc33 * (x[3] - i33 * wiperR) - ieqC33;

        return rail.process(x[4]);
    }

    void rebuild() noexcept
    {
        const double Ra = posA * kRp;         // P3 → W
        const double Rb = (1.0 - posA) * kRp; // W  → P1
        const double gRa = 1.0 / Ra, gRb = 1.0 / Rb;

        // Wiper-leg Norton reduction (setWiperR): a series Rw + C33 branch from W to
        // the 0 V virtual ground collapses to one conductance, no extra node.
        // ⚠ HOISTED above the C31 branch (s177) — both matrices need it. Pure statement
        // reordering: same expressions, same inputs, so the 4×4 path is bit-identical.
        dampDiv = 1.0 + gc33 * wiperR;   // == 1 when Rw = 0 -> ideal cap, exactly
        g33eff = gc33 / dampDiv;

        if (cInput > 0.0)
        {
            double Y5[5][5] = {};
            // Row Vin: (gc31 + 1/R38 + 1/R41) Vin − (1/R38) P3
            Y5[0][0] = gc31 + 1.0 / val.r38 + 1.0 / val.r41; Y5[0][1] = -1.0 / val.r38;
            // Row P3: −(1/R38) Vin + (1/R38 + gc32 + 1/Ra) P3 − gc32 P1 − (1/Ra) W
            Y5[1][0] = -1.0 / val.r38; Y5[1][1] = 1.0 / val.r38 + gc32 + gRa;
            Y5[1][2] = -gc32; Y5[1][3] = -gRa;
            // Row P1: unchanged from the 4×4
            Y5[2][1] = -gc32; Y5[2][2] = 1.0 / val.r39 + gc32 + gRb;
            Y5[2][3] = -gRb; Y5[2][4] = -1.0 / val.r39;
            // Row W: unchanged from the 4×4
            Y5[3][1] = -gRa; Y5[3][2] = -gRb; Y5[3][3] = gRa + gRb + g33eff;
            // Row (−)/Vout: + (1/R41) Vin + g33eff W + (1/R40) Vout
            Y5[4][0] = 1.0 / val.r41; Y5[4][3] = g33eff; Y5[4][4] = 1.0 / val.r40;

            double tmp5[5][5];
            if (mna::invert<5>(Y5, tmp5))
            {
                for (int i = 0; i < 5; ++i)
                    for (int j = 0; j < 5; ++j)
                        yinv5[i][j] = tmp5[i][j];
            }
            dirty = false;
            return;
        }

        double Y[4][4] = {};
        // Row P3: (1/R38 + gc32 + 1/Ra) P3 − gc32 P1 − (1/Ra) W
        Y[0][0] = 1.0 / val.r38 + gc32 + gRa; Y[0][1] = -gc32; Y[0][2] = -gRa;
        // Row P1: −gc32 P3 + (1/R39 + gc32 + 1/Rb) P1 − (1/Rb) W − (1/R39) Vout
        Y[1][0] = -gc32; Y[1][1] = 1.0 / val.r39 + gc32 + gRb; Y[1][2] = -gRb; Y[1][3] = -1.0 / val.r39;
        // Row W: −(1/Ra) P3 − (1/Rb) P1 + (1/Ra + 1/Rb + g33eff) W
        Y[2][0] = -gRa; Y[2][1] = -gRb; Y[2][2] = gRa + gRb + g33eff;
        // Row (−)/Vout: g33eff W + (1/R40) Vout   (oracle "currents into node" sign)
        Y[3][2] = g33eff; Y[3][3] = 1.0 / val.r40;

        double tmp[4][4];
        if (mna::invert<4>(Y, tmp))
        {
            for (int i = 0; i < 4; ++i)
                for (int j = 0; j < 4; ++j)
                    yinv[i][j] = tmp[i][j];
        }
        // else: keep the previous good inverse (degenerate pot endpoint).
        dirty = false;
    }

    Values val = kLoMid;
    double cSeries = kLoMid10n;
    double twoOverT = 0.0;
    double gc32 = 0.0, gc33 = 0.0;
    double wiperR = 0.0;             // fitted series R in the wiper leg (setWiperR)
    double dampDiv = 1.0;            // 1 + gc33*wiperR (1 when wiperR = 0)
    double g33eff = 0.0;             // gc33 / dampDiv — the stamped leg conductance
    double posA = 0.5;               // electrical pot fraction (0.5 = flat)
    double yinv[4][4] = {};          // precomputed Y^-1 (rebuilt on dirty)
    double cInput = 0.0;             // C31 input coupling cap (0 = absent, LO-MID only)
    double gc31 = 0.0;               // its companion conductance
    double yinv5[5][5] = {};         // the 5-unknown inverse, used only when cInput > 0
    double ieq31 = 0.0;
    double ieqC32 = 0.0, ieqC33 = 0.0;
    bool dirty = true;
    RailClamp rail;

    MidBand(const MidBand&) = delete;

public:
    // Assignment permitted, construction not — see the identical block in
    // TrebleAttack.h. `PedalChain` primes a shadow MidBand on a mid-frequency
    // selector flip and crossfades the two (`SwitchFade.h`); the copy carries the
    // switched cap PAIR, the precomputed 4x4 inverse and the two companion-cap
    // currents. Defaulted so a future member cannot be missed.
    MidBand& operator=(const MidBand&) = default;
};
