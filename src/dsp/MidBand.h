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
        dirty = true;
        rebuild();  // establish a valid inverse before the first process()
        reset();
    }

    void reset() noexcept { ieqC32 = ieqC33 = 0.0; }

    // Pot position a ∈ [0,1]: a→0 = full BOOST (wiper at P3/input), a→1 = full CUT
    // (wiper at P1/output), a=0.5 = flat. This is the ELECTRICAL pot fraction; the
    // knob→a mapping (B-taper is linear; knob direction) is applied by the processor.
    void setPosition(double a) noexcept
    {
        const double clamped = a < 1e-6 ? 1e-6 : (a > 1.0 - 1e-6 ? 1.0 - 1e-6 : a);
        if (clamped != posA) { posA = clamped; dirty = true; }
    }

    // 3-way mid switch: swap the series cap (see kLoMid*/kHiMid* above).
    void setSeriesCap(double c) noexcept
    {
        if (c != cSeries) { cSeries = c; gc33 = cSeries * twoOverT; dirty = true; }
    }

    // Rail-clamp passthroughs (calibration §6) — applied to Vout (op-amp output).
    void setRailClampEnabled(bool e) noexcept { rail.setEnabled(e); }
    void setRailVoltages(double vNeg, double vPos) noexcept { rail.setRailVoltages(vNeg, vPos); }

    inline double process(double vin) noexcept
    {
        if (dirty)
            rebuild();

        // RHS: source (R38, R41) + capacitor history. See header stamping.
        //   rhs[P3] = Vin/R38 + ieqC32 ;  rhs[P1] = -ieqC32
        //   rhs[W]  = ieqC33          ;  rhs[Vout] = -Vin/R41 + ieqC33
        double rhs[4];
        rhs[0] = vin / val.r38 + ieqC32;
        rhs[1] = -ieqC32;
        rhs[2] = ieqC33;
        rhs[3] = -vin / val.r41 + ieqC33;

        double x[4];
        mna::matvec<4>(yinv, rhs, x);

        // Capacitor state update: Ieq_new = 2*gc*v_ab − Ieq_old.
        ieqC32 = 2.0 * gc32 * (x[0] - x[1]) - ieqC32; // v_ab = P3 − P1
        ieqC33 = 2.0 * gc33 * x[2] - ieqC33;          // v_ab = W − (−)=0

        return rail.process(x[3]); // Vout, then op-amp rails
    }

private:
    void rebuild() noexcept
    {
        const double Ra = posA * kRp;         // P3 → W
        const double Rb = (1.0 - posA) * kRp; // W  → P1
        const double gRa = 1.0 / Ra, gRb = 1.0 / Rb;

        double Y[4][4] = {};
        // Row P3: (1/R38 + gc32 + 1/Ra) P3 − gc32 P1 − (1/Ra) W
        Y[0][0] = 1.0 / val.r38 + gc32 + gRa; Y[0][1] = -gc32; Y[0][2] = -gRa;
        // Row P1: −gc32 P3 + (1/R39 + gc32 + 1/Rb) P1 − (1/Rb) W − (1/R39) Vout
        Y[1][0] = -gc32; Y[1][1] = 1.0 / val.r39 + gc32 + gRb; Y[1][2] = -gRb; Y[1][3] = -1.0 / val.r39;
        // Row W: −(1/Ra) P3 − (1/Rb) P1 + (1/Ra + 1/Rb + gc33) W
        Y[2][0] = -gRa; Y[2][1] = -gRb; Y[2][2] = gRa + gRb + gc33;
        // Row (−)/Vout: gc33 W + (1/R40) Vout   (oracle "currents into node" sign)
        Y[3][2] = gc33; Y[3][3] = 1.0 / val.r40;

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
    double posA = 0.5;               // electrical pot fraction (0.5 = flat)
    double yinv[4][4] = {};          // precomputed Y^-1 (rebuilt on dirty)
    double ieqC32 = 0.0, ieqC33 = 0.0;
    bool dirty = true;
    RailClamp rail;

    MidBand(const MidBand&) = delete;
    MidBand& operator=(const MidBand&) = delete;
};
