#pragma once

#include <array>
#include <cmath>
#include <cstring>
#include <cstddef>
#include <utility>

// =============================================================================
// Stage 3 — Treble network + ATTACK switch (R7/R8, C5/C9/C6, R12/R14, C8,
//           R11/C7/R13) — circuit.md "Treble network + ATTACK (SW1)"
// =============================================================================
// Linear, passive, switched. Sits between the J201 drain (node G) and the
// IC2_A DRIVE stage ((+) input = node Q). Shapes the treble content fed into
// the distortion; the 3-way ATTACK switch reroutes C8 (220pF):
//
//   circuit.md CORRECTED topology (2026-07-20 — the switch POLE is C8's bottom
//   plate; C8's top plate is fixed to node P; throws are node M and GND):
//     Boost : pole -> M   -> C8 bridges R8 (spans M<->P)  -> treble boost
//     Flat  : pole open    -> C8 inert                     -> flat  ([ENG] centre)
//     Cut   : pole -> GND  -> C8 shunts P to ground        -> treble cut
//   The forward path G-R7-M-R8-P-C7-Q is intact in ALL positions (no mute).
//
// ---- The TWO-POLE ATTACK proposal (Phase 9 / A3 step 19-20) -----------------
// ⚠ ATTACK is [ENG] — the 3-way switch is not on our schematic at all, so what
// follows PROPOSES a topology; it disagrees with no drawn circuit, and equally
// nothing corroborates it. Every value below defaults to the DRAWN network, so a
// default-constructed stage is the shipped stage exactly (see setAttackTap /
// setNotchLeg).
//
// The measured record is that ATTACK does TWO things a single element cannot do at once:
//   (i)  a broadband gain of +8.65 dB (boost) / -2.39 dB (cut) re flat, flat to
//        ~1 dB across 80 Hz - 1.6 kHz, and
//   (ii) a cancellation NULL that moves 316.4 / 328.1 / 334.0 Hz (cut/boost/flat)
//        with depth >= 14.9 / 32.7 / 16.0 dB.
// Session 61 refuted every value-changing family on a SIGN (0 of 782 random draws
// reproduce the pedal's pattern; "cut moves the null DOWN" is structurally
// unreachable when the switch only reroutes C8), and session 62 showed the two
// requirements are carried by three provably NON-INTERACTING element groups:
//   the top-rail divider  -> owns the broadband gain (d f0 0.01-0.02 Hz)
//   the C5-leg damping Rd -> owns the depth          (d h 0.00 dB)
//   the ladder RC values  -> own  the frequency      (d h 0.00 dB)
// So the switch is proposed as TWO POLES:
//   Pole A — a MOVING TAP on the top rail. The drawn R8 is split and the switch
//            selects which node C7 hangs off:
//              G -R7- M -Ra- T1 -Rb- T2 -Rc- T3 -R11- GND
//              boost -> T1 (highest/loudest), flat -> T2, cut -> T3
//            ⭐ The throw ORDER is forced, not fitted: g(boost) > 0 > g(cut) is
//            measured and a resistive tap can only attenuate downward.
//   Pole B — the C5 ladder leg: its damping Rd AND C5 switch per throw. Read
//            physically as "the switch SHORTS the damping resistor in BOOST only"
//            (cut and flat's fitted Rd agree to 2 %, from two independent fits).
//
// ⭐ WHY THIS NEEDS NO NEW NODES — the series collapse, which is exact.
// Only the SELECTED tap carries a load (C7, and C8 when it is in circuit); T1/T2/
// T3 are otherwise bare interior points of one series chain. Series resistors with
// no loaded intermediate node combine EXACTLY, so per throw the split rail is
// identically the drawn two-resistor rail M -Rtop- P -Rbot- GND with P = the
// selected tap:
//   boost (T1): Rtop = Ra           Rbot = Rb + Rc + R11
//   flat  (T2): Rtop = Ra + Rb      Rbot = Rc + R11
//   cut   (T3): Rtop = Ra + Rb + Rc Rbot = R11
// That keeps N = 7, keeps ONE matrix per position (no extra inversions), and makes
// the default (Ra = R8, Rb = Rc = 0, R11 = R11) stamp BIT-IDENTICAL values into
// the same 7x7 as the shipped stage — a true no-op default, not a
// numerically-close one. (analysis/attack_tap_screen.py solves the uncollapsed
// 8-node network instead; the two agree, and that cross-check is the derivation
// gate — see tests/TrebleAttackTest.cpp Test 8.)
// ⚠ Rb/Rc are only ever SUMMED here, never inverted, so zero is exact and safe —
// which is precisely what the screen tool could not do (its 8-node solve needed a
// numerical short, and session 62 found that SHRINKING the short made the error
// WORSE: 1e-12 ohm puts a 1e12 conductance against a 2e-6 rail and the solve
// loses every digit). Rtop/Rbot are floored at 1 ohm for that reason.
//
// ---- Stage boundary: the J201 drain is a CURRENT source ---------------------
// ** CHANGED 2026-07-22 (Phase-7 calibration), discharging the Phase-4 deferral
//    that used to read "Input node G (J201 drain) = IDEAL voltage source (source
//    Z = 0); revisit with an explicit J201 output impedance at Phase 7." **
//
// Node G is now a real unknown node driven by the J201's Norton current, with
// that device's output impedance stamped in alongside it:
//
//        i_drain (from JfetStage::process)  ->  node G
//        node G --[ro]-- node H --[Rp || Cp]-- GND        = ro*k(s), the
//        node G --[Rq2]-------------------- GND             degeneration-shaped
//                                                           drain resistance,
//                                                           in parallel with the
//                                                           C4-bootstrapped Q2
//                                                           active load.
//
// This matters a great deal, not marginally: the ladder's input impedance falls
// from ~35 kOhm at 200 Hz to ~6.5 kOhm at 2 kHz, so an ideal (0 ohm) source let
// the C5/C9/C6 HF bypass of R7 through at full strength AND let JfetStage apply
// its C3 shelf on top — double-counting, worth ~+23 dB of excess HF in the OD
// path (docs/phase7-calibration-handover.md). See JfetStage.h's header for the
// device algebra (Gm*Rout = gm*ro is flat; only the LOADED gain shelves).
//
// Output is still V(Q), the voltage at IC2_A(+), which draws no current — a
// clean stage boundary; the DRIVE stage multiplies V(Q).
//
// ---- Why MNA rather than a WDF tree --------------------------------------
// R7 and the C5/C9/C6 ladder BOTH connect G to node M (a loop), and there are
// several ground-referenced shunts — so this is not a series/parallel WDF tree;
// it would need a hand-derived R-type scattering matrix. For a LINEAR passive
// block with a current source in and an unloaded output, nodal analysis (MNA)
// with trapezoidal-companion capacitors is exact, uses the SAME bilinear cap
// discretisation as chowdsp's CapacitorT (identical warp), maps 1:1 onto the
// analytic oracle in analysis/eq_reference.py (so it validates directly), and
// handles the 3 switch positions by precomputing one nodal matrix inverse per
// position (dsp.md "precompute per topology" — here a plain matrix swap).
//
// Node indices for the 7 unknowns: G=0, H=1, M=2, P=3, L1=4, L2=5, Q=6.
// GND = 0 V. G is no longer a known source.
//
// ⚠ The matrix now depends on the FITTED source-Z values as well as on the
// switch position, so setSourceZ() re-inverts (three 7x7 Gauss-Jordans, stack
// only, no allocation). It is called from setFitParams(), i.e. at most once per
// block and never per sample — and it early-outs when nothing changed.
// =============================================================================
class TrebleAttack
{
public:
    enum class Attack
    {
        Boost = 0, // C8 bridges R8
        Flat,      // C8 open (centre) [ENG]
        Cut        // C8 shunts P->GND
    };

    // Component values (circuit.md "Treble / pre-clip network + ATTACK switch").
    static constexpr double kR7 = 200.0e3;
    static constexpr double kR8 = 470.0e3;
    static constexpr double kR11 = 470.0e3;
    static constexpr double kR12 = 6.8e3;
    static constexpr double kR13 = 1.0e6;
    static constexpr double kR14 = 22.0e3;
    static constexpr double kC5 = 22.0e-9;
    static constexpr double kC9 = 22.0e-9;
    static constexpr double kC6 = 22.0e-9;
    static constexpr double kC7 = 100.0e-9;
    static constexpr double kC8 = 220.0e-12;

    // size_t (not int) so every array subscript below is already the right
    // signedness — std::array::operator[] takes size_type, and an int index
    // would make each of the ~35 subscripts in this file an implicit signed->
    // unsigned conversion (-Wsign-conversion).
    static constexpr size_t N = 7;             // node count
    static constexpr size_t G = 0, H = 1, M = 2, P = 3, L1 = 4, L2 = 5, Q = 6;

    TrebleAttack() = default;

    void prepare(double sampleRate)
    {
        // Trapezoidal companion conductances: gc = 2*C / T.
        twoOverT = 2.0 * sampleRate;
        for (size_t i = 0; i < 3; ++i)
            gc5[i] = c5[i] * twoOverT;  // per ATTACK position (pole B); all equal by default
        gc9 = c9 * twoOverT;        // c9/c6 are fittable (default to kC9/kC6 exactly)
        gc6 = c6 * twoOverT;
        gc7 = c7 * twoOverT;        // c7 is fittable (defaults to kC7 exactly)
        gc8 = c8 * twoOverT;         // c8 is fittable (defaults to kC8 exactly)

        prepared = true;
        rebuild();
        reset();
    }

    // Notch-damping series resistance on the C5 ladder cap (session 19, Phase 9).
    // The R7-vs-(C5/C9/C6-ladder) two-path cancellation gives a ~322 Hz notch
    // that is ~28 dB deep in the ideal model but only -3.4 dB in the capture, and
    // component tolerance cannot explain the gap (circuit.md risk register; Monte
    // Carlo never got shallower than -23 dB). A real series loss in the ladder (cap
    // ESR / PCB / an unmodelled damping R) shallows the cancellation. Modelled as
    // a lossy C5: series Rd + C5 between G and L1, stamped as ONE branch (no new
    // node) via the Norton reduction g5eff = gc5/(1+gc5*Rd), ieq' = ieqC5/(1+gc5*Rd).
    // Rd=0 reproduces the ideal deep notch EXACTLY (the 1+gc5*Rd factor is 1). Fit
    // Rd to the capture's notch DEPTH (dsp.md "the capture is authoritative"); the
    // notch FREQUENCY is set by the cap/resistor ratios and moves little with Rd.
    // ⚠ Sets the SAME damping in all three ATTACK positions (the pre-session-62
    // meaning, kept so every existing tool that does `--fit trebleLadderDampR=`
    // keeps behaving exactly as it did). setNotchLeg() overrides one position.
    void setNotchDamp(double rOhm) noexcept
    {
        const double next = (rOhm > 0.0) ? rOhm : 0.0;
        if (std::memcmp(&next, &ladderDampR, sizeof(double)) == 0)
            return;
        ladderDampR = next;
        for (size_t i = 0; i < 3; ++i)
            rd[i] = next;
        if (prepared)
            rebuild();
    }

    // Pole B — the notch-forming C5 leg, per ATTACK position. Session 62 puts the
    // proposal at Rd = 478 ohm (boost) / 6.14k (flat) / 6.04k (cut) and C5 = 20.8 /
    // 19.7 / 22.4 nF, which reproduces the pedal's null to 0.1 Hz and its depth
    // ranking to 0.18 dB at all three throws. Realise the C5 move as a small
    // PARALLEL TRIM cap on the same pole (19.7n base, +1.1n boost, +2.7n cut) —
    // it is a +-7 % move, not three graded caps.
    //
    // ⚠ Call AFTER setNotchDamp() if both are used: setNotchDamp overwrites all
    // three positions by design (see above), so the order matters. PedalChain does
    // exactly that.
    void setNotchLeg(Attack pos, double c5Farads, double rdOhm) noexcept
    {
        const size_t i = static_cast<size_t>(pos);
        const std::array<double, 2> next { (c5Farads > 0.0) ? c5Farads : kC5,
                                           (rdOhm > 0.0) ? rdOhm : 0.0 };
        const std::array<double, 2> cur { c5[i], rd[i] };
        if (std::memcmp(next.data(), cur.data(), sizeof(cur)) == 0)
            return;
        c5[i] = next[0];
        rd[i] = next[1];
        if (prepared)
        {
            gc5[i] = c5[i] * twoOverT;
            rebuild();
        }
    }

    // Pole A — the moving tap on the top rail (see the header's "TWO-POLE ATTACK
    // proposal"). Ra/Rb/Rc split the drawn R8; R11 is the remaining leg to ground.
    // The DEFAULT (Ra = kR8, Rb = Rc = 0, R11 = kR11) collapses all three taps onto
    // the drawn node P and is the shipped network exactly.
    //
    // Session 62's proposal: Ra 470k (pinned to the drawn R8) / Rb 506k / Rc 78.5k /
    // R11 212k. ⚠ Only the divider's RATIOS are identified — `h` is a ratio between
    // switch positions, so anything common to all three throws cancels out of the
    // measurement by construction, and Ra duly parked on whichever bound it started
    // nearest until it was pinned. This also asks the P-to-ground resistance to be
    // ~797k against the drawn R11 = 470k; since the switch itself is [ENG] the
    // surrounding rail is a proposal too, but that should be stated, not buried.
    void setAttackTap(double ra, double rb, double rc, double r11) noexcept
    {
        const std::array<double, 4> next { (ra > 0.0) ? ra : kR8, (rb >= 0.0) ? rb : 0.0,
                                           (rc >= 0.0) ? rc : 0.0, (r11 > 0.0) ? r11 : kR11 };
        if (std::memcmp(next.data(), tap.data(), sizeof(tap)) == 0)
            return;
        tap = next;
        if (prepared)
            rebuild();
    }

    // The SHARED ladder — R7 and the C5/C9/C6 + R12/R14 network, i.e. everything the
    // ATTACK switch does NOT switch. Session 50's next-step (a), open since then:
    // these were `static constexpr` and reachable from NO analysis tool, so every A3
    // screen that wanted them had to work in Python against a network solve instead
    // of the shipped stage.
    //
    // WHY THEY MATTER NOW (session 64). Session 63's two-pole topology matches the
    // null's (f0, depth) TO THE BIN at all three throws but every null is ~2x too
    // BROAD (half-depth width 150.6/59.6/138.6 Hz against the pedal's 77.9/27.1/71.9).
    // A ~2x error that is nearly UNIFORM across three throws cannot come from a
    // per-throw element — the throws differ only in pole B — so the width lever has to
    // be SHARED, and this is the shared set. Nothing here is switched: the ATTACK
    // switch's own two poles stay setAttackTap() and setNotchLeg().
    //
    // ⚠ Every one of these is SCHEMATIC-VERIFIED (circuit.md "Treble / pre-clip
    // network + ATTACK switch"; covered by the R1-R54 / C1-C39 BOM reconciliation), so
    // moving one is a capture-vs-document disagreement of the same kind as trebleC7 /
    // c21R / trebleWiperR / R36 — NOT a bug fix. The defaults below are the drawn
    // values and a default-valued render is bit-identical to the pre-session-64 stage.
    void setLadder(double r7Ohm, double r12Ohm, double r14Ohm,
                   double c9Farads, double c6Farads) noexcept
    {
        const std::array<double, 5> next { (r7Ohm > 0.0) ? r7Ohm : kR7,
                                          (r12Ohm > 0.0) ? r12Ohm : kR12,
                                          (r14Ohm > 0.0) ? r14Ohm : kR14,
                                          (c9Farads > 0.0) ? c9Farads : kC9,
                                          (c6Farads > 0.0) ? c6Farads : kC6 };
        const std::array<double, 5> cur { r7, r12, r14, c9, c6 };
        if (std::memcmp(next.data(), cur.data(), sizeof(cur)) == 0)
            return;
        r7 = next[0]; r12 = next[1]; r14 = next[2]; c9 = next[3]; c6 = next[4];
        if (prepared)
        {
            gc9 = c9 * twoOverT;
            gc6 = c6 * twoOverT;
            rebuild();
        }
    }

    // C7, the coupling cap from node P into IC2_A(+) — the LAST element of the OD
    // path before the DRIVE stage, and therefore the only place a highpass can sit
    // that both (a) reduces what IC2_A sees at LF and (b) is still upstream of it.
    //
    // WHY IT IS FITTABLE (Phase 9 / A3 step 3a, session 34). At the schematic 100n
    // this cap corners at ~1.2 Hz (into R_src+R_load ~= 1.28M) and is inert across the audio
    // band, so the OD path's response into IC2_A PEAKS at 32-40 Hz (-8.5 dB re the
    // clean tap) and falls to -20.5 dB by 320 Hz. IC2_A therefore rails at LF first
    // at high drive, which eats the whole top half of the DRIVE knob at 40-101 Hz:
    // the model's |OD| turns over at drive 2:30 and FALLS by max, where the pedal's
    // grows +5..6 dB (measured, analysis/a3_drive_axis.py). A smaller C7 puts a
    // first-order highpass exactly there and restores the headroom.
    //
    // ⚠ This is a fit against the CAPTURED UNIT, not a correction to the schematic
    // (which reads 100n and is BOM-reconciled). Same third branch as trebleWiperR /
    // c21R / the [ENG] mid caps: our schematic is a clone of the ORIGINAL B7K, the
    // captured unit is an Ultra. c7 = kC7 reproduces the shipped stage EXACTLY.
    void setC7(double farads) noexcept
    {
        const double next = (farads > 0.0) ? farads : kC7;
        // Bit-compare, like setSourceZ: this is an exact "did it move?" check that
        // skips three matrix inversions when setFitParams re-sends the same value
        // every block, without tripping -Wfloat-equal.
        if (std::memcmp(&next, &c7, sizeof(double)) == 0)
            return;
        c7 = next;
        if (prepared)
        {
            gc7 = c7 * twoOverT;
            rebuild();
        }
    }

    // C8, the 220 pF cap the DRAWN switch reroutes (boost: bridges M<->tap; cut:
    // shunts tap->GND; flat: open). Fittable because the session-62 two-pole
    // proposal does not need it at all and screens with it REMOVED — that has to be
    // renderable, and 0 is the only way to say it. kC8 reproduces the drawn stage.
    //
    // ⚠ Note where C8 attaches when the tap moves: at the SELECTED tap, because in
    // the drawn circuit C8's top plate and C7 share node P. (analysis/
    // attack_tap_screen.py's optional `--c8` mode instead spans M<->T3, i.e. the
    // whole split rail — a different and less faithful choice. The proposal used
    // neither: it runs at C8 = 0, so the two never had to be reconciled.)
    void setC8(double farads) noexcept
    {
        const double next = (farads > 0.0) ? farads : 0.0;
        if (std::memcmp(&next, &c8, sizeof(double)) == 0)
            return;
        c8 = next;
        if (prepared)
        {
            gc8 = c8 * twoOverT;
            rebuild();
        }
    }

    // The J201 drain network (JfetStage::getSourceZ): Zout(s) = [ro + Rp||Cp] || Rq2.
    void setSourceZ(double roOhm, double rq2Ohm, double rpOhm, double cpFarad) noexcept
    {
        // Bit-compare (not ==) so this is an exact "did anything move?" check without
        // tripping -Wfloat-equal: the point is to skip the three matrix inversions when
        // setFitParams() re-sends identical values every block, and any difference at
        // all — however tiny — legitimately needs a rebuild.
        const std::array<double, 4> next { roOhm, rq2Ohm, rpOhm, cpFarad };
        if (std::memcmp(next.data(), srcZ.data(), sizeof(srcZ)) == 0)
            return;
        srcZ = next;
        if (prepared)
            rebuild();
    }

    void reset()
    {
        ieqC5 = ieqC9 = ieqC6 = ieqC7 = ieqC8 = ieqCp = 0.0;
    }

    void setAttack(Attack a) noexcept
    {
        // C8 changes topological role between positions (M<->P bridge, P->GND
        // shunt, or open), so its carried history is meaningless across a swap —
        // zero it to avoid injecting a spurious transient. (The other caps'
        // connections are position-invariant, so their state is safe to keep.)
        // Phase 5 adds the glitch-free crossfade on top of this.
        if (a != attack)
        {
            ieqC8 = 0.0;
            // C5 now switches too (pole B), so its history is equally meaningless
            // across a swap — but ONLY when the leg is actually position-dependent.
            // Guarding on that keeps the default stage bit-identical to the shipped
            // one even across a live switch change, where the old code kept C5's
            // state.
            if (notchLegSwitched)
                ieqC5 = 0.0;
        }
        attack = a;
    }

    // Process one sample. IN: the J201 drain NORTON CURRENT in amps (signed for
    // injection into node G). OUT: real volts at Q.
    inline double process(double iIn) noexcept
    {
        // ---- Build RHS: source current + capacitor history (Ieq) ------------
        // Cap convention (unchanged): for a cap across (a,b) with
        // ieq = 2*gc*(va - vb) - ieq_old, contribute b[a] += ieq, b[b] -= ieq.
        // C5 is a LOSSY cap (series Rd): its Norton current into the (G,L1) branch
        // is ieqC5 * c5damp (= ieqC5/(1+gc5*Rd)); c5damp=1 when Rd=0.
        const size_t pos = static_cast<size_t>(attack);
        const double ieqC5b = ieqC5 * c5damp[pos];
        std::array<double, N> b {};
        b[G] = iIn + ieqC5b;         // Norton drive; C5+Rd (a=G,b=L1)
        b[H] = ieqCp;                // Cp (a=H,b=GND)
        b[M] = -ieqC6;               // C6 (a=L2,b=M)
        b[P] = ieqC7;                // C7 (a=P,b=Q)
        b[L1] = -ieqC5b + ieqC9;     // C5+Rd -> -Ieq ; C9 (a=L1,b=L2) -> +Ieq
        b[L2] = -ieqC9 + ieqC6;      // C9 -> -Ieq ; C6 -> +Ieq
        b[Q] = -ieqC7;               // C7 -> -Ieq

        if (attack == Attack::Boost) // C8 (a=M,b=P)
        {
            b[M] += ieqC8;
            b[P] -= ieqC8;
        }
        else if (attack == Attack::Cut) // C8 (a=P,b=GND)
        {
            b[P] += ieqC8;
        }

        // ---- Solve v = Yinv * b ----
        const auto& A = yInv[pos];
        std::array<double, N> v {};
        for (size_t i = 0; i < N; ++i)
        {
            double acc = 0.0;
            for (size_t j = 0; j < N; ++j)
                acc += A[i][j] * b[j];
            v[i] = acc;
        }

        // ---- Update capacitor states: Ieq_new = 2*gc*v_ab - Ieq_old ----
        // C5 lossy: the CAP voltage is the branch voltage minus the Rd drop.
        // i5 = g5eff*(v[G]-v[L1]) - ieqC5b; v_c5 = (v[G]-v[L1]) - i5*Rd.
        // Rd=0 => v_c5 = v[G]-v[L1] (identical to the ideal cap update).
        const double dv5 = v[G] - v[L1];
        const double i5 = g5eff[pos] * dv5 - ieqC5b;
        const double vc5 = dv5 - i5 * rd[pos];
        ieqC5 = 2.0 * gc5[pos] * vc5 - ieqC5;
        ieqC9 = 2.0 * gc9 * (v[L1] - v[L2]) - ieqC9;
        ieqC6 = 2.0 * gc6 * (v[L2] - v[M]) - ieqC6;
        ieqC7 = 2.0 * gc7 * (v[P] - v[Q]) - ieqC7;
        ieqCp = 2.0 * gcp * (v[H]) - ieqCp;
        if (attack == Attack::Boost)
            ieqC8 = 2.0 * gc8 * (v[M] - v[P]) - ieqC8;
        else if (attack == Attack::Cut)
            ieqC8 = 2.0 * gc8 * (v[P]) - ieqC8;

        return v[Q];
    }

private:
    // (kR8 / kR11 are now the DEFAULTS of the pole-A split rail rather than fixed
    // conductances — see rTop/rBot and setAttackTap. R7/R12/R14 likewise became
    // members in session 64 — see setLadder — so their conductances are computed in
    // rebuild() rather than being constexpr. R13 is still fixed: it is the IC2_A input
    // bias resistor, not part of the ladder.)
    static constexpr double kG13 = 1.0 / kR13;

    using Mat = std::array<std::array<double, N>, N>;

    void rebuild()
    {
        gcp = srcZ[3] * twoOverT;
        // Lossy-C5 (notch damping): series Rd + C5 -> single Norton branch, per
        // ATTACK position (pole B). Rd=0 => c5damp=1 => g5eff=gc5 => exact ideal
        // (undamped) behaviour.
        notchLegSwitched = false;
        for (size_t i = 0; i < 3; ++i)
        {
            c5damp[i] = 1.0 / (1.0 + gc5[i] * rd[i]);
            g5eff[i] = gc5[i] * c5damp[i];
            if (std::memcmp(&c5[i], &c5[0], sizeof(double)) != 0
                || std::memcmp(&rd[i], &rd[0], sizeof(double)) != 0)
                notchLegSwitched = true;
        }
        // Pole A — the series collapse (see the header). Only the selected tap is
        // loaded, so the four-resistor split rail is exactly a two-resistor rail per
        // throw. Rb/Rc are SUMMED, never inverted, so Rb = Rc = 0 is exact.
        const double ra = tap[0], rb = tap[1], rc = tap[2], r11 = tap[3];
        rTop[static_cast<size_t>(Attack::Boost)] = ra;
        rBot[static_cast<size_t>(Attack::Boost)] = rb + rc + r11;
        rTop[static_cast<size_t>(Attack::Flat)] = ra + rb;
        rBot[static_cast<size_t>(Attack::Flat)] = rc + r11;
        rTop[static_cast<size_t>(Attack::Cut)] = ra + rb + rc;
        rBot[static_cast<size_t>(Attack::Cut)] = r11;
        for (size_t i = 0; i < 3; ++i)
        {
            // 1 ohm, not something smaller: session 62 measured that a numerical
            // short below ~1 mohm destroys the solve's conditioning outright, and
            // 1 ohm against a few hundred k is already a 1e-6 relative perturbation.
            rTop[i] = (rTop[i] > 1.0) ? rTop[i] : 1.0;
            rBot[i] = (rBot[i] > 1.0) ? rBot[i] : 1.0;
        }
        for (size_t i = 0; i < 3; ++i)
            invert(buildY(static_cast<Attack>((int) i)), yInv[i]);
    }

    // Build the nodal conductance matrix Y for one ATTACK position.
    Mat buildY(Attack pos) const
    {
        const size_t pi = static_cast<size_t>(pos);
        Mat Y {};
        // ---- J201 drain output network (see header) ----
        const double gro = 1.0 / srcZ[0], gRq2 = 1.0 / srcZ[1], gRp = 1.0 / srcZ[2];
        Y[G][G] += gro; Y[G][H] -= gro; Y[H][G] -= gro; Y[H][H] += gro; // ro (G-H)
        Y[G][G] += gRq2;                                  // Rq2 (G-GND)
        Y[H][H] += gRp;                                   // Rp  (H-GND)
        Y[H][H] += gcp;                                   // Cp  (H-GND)
        // ---- Resistors ----
        const double g7 = 1.0 / r7;
        Y[G][G] += g7; Y[G][M] -= g7; Y[M][G] -= g7; Y[M][M] += g7;     // R7 (G-M)
        // Rtop/Rbot: the collapsed split rail (pole A). Default Rtop = kR8 and
        // Rbot = kR11 in every position => the drawn M-R8-P-R11-GND rail exactly.
        const double gTop = 1.0 / rTop[pi], gBot = 1.0 / rBot[pi];
        Y[M][M] += gTop; Y[M][P] -= gTop; Y[P][M] -= gTop; Y[P][P] += gTop; // Rtop (M-P=tap)
        Y[P][P] += gBot;                                  // Rbot (tap-GND)
        Y[L1][L1] += 1.0 / r12;                           // R12 (L1-GND)
        Y[Q][Q] += kG13;                                  // R13 (Q-GND)
        Y[L2][L2] += 1.0 / r14;                           // R14 (L2-GND)
        // ---- Capacitor companion conductances ----
        const double g5 = g5eff[pi];
        Y[G][G] += g5; Y[G][L1] -= g5; Y[L1][G] -= g5; Y[L1][L1] += g5;         // C5+Rd (G-L1)
        Y[L1][L1] += gc9; Y[L1][L2] -= gc9; Y[L2][L1] -= gc9; Y[L2][L2] += gc9; // C9 (L1-L2)
        Y[L2][L2] += gc6; Y[L2][M] -= gc6; Y[M][L2] -= gc6; Y[M][M] += gc6;     // C6 (L2-M)
        Y[P][P] += gc7; Y[P][Q] -= gc7; Y[Q][P] -= gc7; Y[Q][Q] += gc7;         // C7 (P-Q)
        if (pos == Attack::Boost) // C8 (M-P)
        {
            Y[M][M] += gc8; Y[M][P] -= gc8; Y[P][M] -= gc8; Y[P][P] += gc8;
        }
        else if (pos == Attack::Cut) // C8 (P-GND)
        {
            Y[P][P] += gc8;
        }
        return Y;
    }

    // Gauss-Jordan inverse with partial pivoting (N=7, runs once per position).
    static void invert(Mat src, Mat& dst)
    {
        Mat a = src;
        for (size_t i = 0; i < N; ++i)
            for (size_t j = 0; j < N; ++j)
                dst[i][j] = (i == j) ? 1.0 : 0.0;

        for (size_t col = 0; col < N; ++col)
        {
            size_t piv = col;
            double best = std::abs(a[col][col]);
            for (size_t r = col + 1; r < N; ++r)
            {
                const double v = std::abs(a[r][col]);
                if (v > best) { best = v; piv = r; }
            }
            if (piv != col)
            {
                std::swap(a[piv], a[col]);
                std::swap(dst[piv], dst[col]);
            }
            const double d = a[col][col];
            for (size_t j = 0; j < N; ++j) { a[col][j] /= d; dst[col][j] /= d; }
            for (size_t r = 0; r < N; ++r)
            {
                if (r == col) continue;
                const double f = a[r][col];
                if (f == 0.0) continue;
                for (size_t j = 0; j < N; ++j) { a[r][j] -= f * a[col][j]; dst[r][j] -= f * dst[col][j]; }
            }
        }
    }

    // Source-Z (J201 drain) as { ro, Rq2, Rp, Cp } — nominal-initialised from
    // JfetStage's nominals so a default-constructed stage is self-consistent
    // without an explicit setSourceZ() call.
    std::array<double, 4> srcZ { 200.0e3,
                                 1.0e6,
                                 200.0e3 * (0.69e-3 * 3.3e3),
                                 (3.3e3 * 220.0e-9) / (200.0e3 * (0.69e-3 * 3.3e3)) };

    bool prepared = false;
    double twoOverT = 2.0 * 48000.0;
    // Companion conductances (set in prepare()/rebuild()).
    double gc9 = 0.0, gc6 = 0.0, gc7 = 0.0, gc8 = 0.0, gcp = 0.0;
    // ---- The SHARED ladder (NOT switched by ATTACK) — see setLadder. Defaults are
    // the drawn values, so a default-constructed stage is the pre-session-64 stage.
    double r7 = kR7, r12 = kR12, r14 = kR14, c9 = kC9, c6 = kC6;
    // ---- Pole B: the notch-forming C5 leg, PER ATTACK position (Boost/Flat/Cut).
    // Series resistance rd + cap c5, with the derived branch factor
    // c5damp = 1/(1+gc5*rd) and g5eff = gc5*c5damp (see setNotchDamp/setNotchLeg).
    // All three entries are equal unless setNotchLeg() is used, and `ladderDampR`
    // keeps the shared value so setNotchDamp()'s "did it move?" guard still works.
    std::array<double, 3> c5 { kC5, kC5, kC5 };
    std::array<double, 3> rd { 0.0, 0.0, 0.0 };
    std::array<double, 3> gc5 { 0.0, 0.0, 0.0 };
    std::array<double, 3> c5damp { 1.0, 1.0, 1.0 };
    std::array<double, 3> g5eff { 0.0, 0.0, 0.0 };
    double ladderDampR = 0.0;
    bool notchLegSwitched = false;   // true once any position's (c5, rd) differs
    // ---- Pole A: the top-rail split { Ra, Rb, Rc, R11 } and its per-position
    // series collapse to { Rtop (M-tap), Rbot (tap-GND) }. Default = the drawn rail.
    std::array<double, 4> tap { kR8, 0.0, 0.0, kR11 };
    std::array<double, 3> rTop { kR8, kR8, kR8 };
    std::array<double, 3> rBot { kR11, kR11, kR11 };
    double c7 = kC7;   // fittable coupling cap into IC2_A (see setC7)
    double c8 = kC8;   // fittable ATTACK cap; 0 = removed, which is what the
                       // session-62 two-pole proposal screens with (see setC8)
    // Capacitor history (equivalent-source) currents.
    double ieqC5 = 0.0, ieqC9 = 0.0, ieqC6 = 0.0, ieqC7 = 0.0, ieqC8 = 0.0, ieqCp = 0.0;
    // One precomputed nodal-matrix inverse per ATTACK position (Boost/Flat/Cut).
    std::array<Mat, 3> yInv {};
    Attack attack = Attack::Flat;

    TrebleAttack(const TrebleAttack&) = delete;

public:
    // ⭐ ASSIGNMENT IS PERMITTED, CONSTRUCTION IS NOT (open-work item 14, S2).
    // `PedalChain` primes a SHADOW instance from the live one on an ATTACK flip and
    // crossfades the two (`SwitchFade.h`), which needs an exact memberwise copy of
    // BOTH the topology (the three precomputed nodal inverses, every fitted value)
    // and the state (the six companion-cap currents). Defaulting it — rather than
    // hand-copying fields or `memcpy`ing a non-trivially-copyable object — is what
    // makes it pick up a future member automatically; a hand-written clone is the
    // s146 `masterTaperBreak` trap waiting to happen (a new field silently left
    // behind, with a plausible-looking result and no compile error).
    //
    // ⛔ The copy CONSTRUCTOR stays deleted, so the original guard survives where it
    // earns its keep: a prepared DSP stage still cannot be passed or returned by
    // value, and a shadow can only come into existence beside an already-prepared
    // live stage.
    TrebleAttack& operator=(const TrebleAttack&) = default;
};
