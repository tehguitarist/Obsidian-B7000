#pragma once

#include <cmath>

#include "FitParams.h"
#include "InputBuffer.h"
#include "JfetStage.h"
#include "TrebleAttack.h"
#include "DriveStage.h"
#include "Clipper.h"
#include "RecoveryBridgedT.h"
#include "SallenKeyLPF.h"
#include "LevelBlend.h"
#include "EqPreGain.h"
#include "Baxandall.h"
#include "MidBand.h"
#include "MasterOut.h"

// =============================================================================
// PedalChain — the complete per-channel B7K Ultra signal chain (JUCE-free)
// =============================================================================
// Assembles every validated Phase-4/5 stage in the verified signal order
// (circuit.md "Signal path summary"). Deliberately has NO JUCE dependency so it
// stays console-testable like the individual stages; the oversampler, the
// clean-tap delay line, and all DAW-domain gain/metering live one level up in
// PedalDSP (JUCE-aware).
//
//   IN ─▶ InputBuffer(IC1_A) ─┬─ clean tap ──────────────────────────┐
//                             │                                       │
//        [── OVERSAMPLED REGION (runOdSample) ──────────────]         │
//        └▶ JFET ─▶ Treble/ATTACK ─▶ DRIVE ─▶ Clipper(GRUNT) ─▶       │
//           Recovery/bridged-T ─▶ SK-LPF(10.7k) ─▶ SK-LPF(3.3k) ─┐    │
//                                                                 ▼    ▼
//                                              LevelBlend(LEVEL + BLEND crossfade)
//                                                                 ▼
//        EqPreGain(IC5_A/B) ─▶ C21 ─▶ Baxandall ─▶ LO-MID ─▶ HI-MID ─▶ MasterOut ─▶ OUT
//
// **Split-rate prepare.** The nonlinear stages plus the downstream HF-cap linear
// stages (Recovery, both SK LPFs) run INSIDE the oversampled region — they are
// prepared at `osRate`. Everything before it (InputBuffer) and after it
// (LevelBlend, EQ, MasterOut) is prepared at `baseRate` (dsp.md "Oversampling":
// only oversample the aliasing source + downstream audible-HF-cap stages; leave
// out stages with no audible-band caps). For a plain base-rate run (the console
// test, or a 1× realtime factor) pass baseRate == osRate.
//
// **Clean-tap delay.** The clean BLEND tap splits at InputBuffer, BEFORE the
// oversampled region, so PedalDSP delay-compensates it to the oversampler's FIR
// latency before calling processPostBlend (dsp.md "Dry/wet phase alignment").
// This class exposes runInputBuffer / runOdSample / processPostBlend separately
// so PedalDSP can insert the oversampler + delay between them; processSample()
// is the fused base-rate convenience path (no OS, no delay) for the tests.
//
// **Polarity (net):** JFET(−) + Clipper(−) = OD reaches BLEND net non-inverting
// vs the clean tap → the two sum in phase (dsp.md). EQ: EqPreGain(−2.2) +
// Baxandall(−) + LO-MID(−) + HI-MID(−) = 4 inversions = net non-inverting.
// End-to-end DC-step / BLEND-null verification is the PedalDSP-level Phase-6 test.
//
// **RailClamps** stay disabled here (each stage defaults off) — the op-amp rail
// voltages are a Phase-7 capture calibration; enabling them before kInputRef is
// anchored would clip against an arbitrary reference (calibration §6). Flagged.
// **All amplitude constants inside the nonlinear stages are still NOMINAL** —
// this assembly does not change that; Phase-7 capture fitting is unaffected.
//
// ---- Anti-aliasing strategy (Phase 6) ---------------------------------------
// Two nonlinearities, handled differently (dsp.md "Apply ADAA where the hardest
// nonlinearity is"):
//  • **J201 waveshaper** — a MEMORYLESS SQUARE-LAW even-shaper (reshaped from the
//    former per-polarity tanh, 2026-07-22) with a closed-form Gudermannian
//    antiderivative → gets 1st-order ADAA (jfet.setADAA above) on top of
//    oversampling. Cheap, exact, glitch-free.
//    ⚠ Because its odd part is EXACTLY linear, ADAA1 degenerates to a 2-point
//    average (|H| = cos(pi*f/fs)) over the whole linear region — negligible at the
//    4x default (-0.12 dB @10 kHz) but -2.0 dB @10 kHz / -12 dB @20 kHz at OS=1x.
//    Account for this when fitting the Phase-8 low-OS top-octave shelf; consider
//    gating ADAA off at order 0. (dsp-validator finding, 2026-07-22.)
//  • **CD4049 clipper VTC** — the harder aliaser, but it lives INSIDE an implicit
//    RC-coupled shunt-feedback loop solved per-sample by Newton on node W (it is
//    NOT a memoryless function of one input), so the Esqueda 1st-order ADAA form
//    (F(x)-F(xPrev))/(x-xPrev) does not apply — state-space ADAA would be needed
//    and is out of Phase-6 scope. Its antialiasing is carried by OVERSAMPLING
//    (this whole region), which OSValidationTest confirms drops the alias floor
//    with factor. Revisit state-space ADAA only if low-OS listening reveals
//    residual clipper aliasing (dsp.md leaves exactly this door open).
//  • **AccurateOmega is N/A here** — there are NO chowdsp DiodePairT/omega solves
//    in the signal path (D1/D2 are hard clamps that never conduct; both shapers
//    are std::tanh, already exact). The dsp.md omega4/AccurateOmega gotcha and
//    the HQ/Eco lever it implies simply don't arise for this pedal.
// =============================================================================
class PedalChain
{
public:
    // Runtime control state, mapped from APVTS by PedalDSP. Pots are raw 0..1
    // (tapers live in the stages); switches are the APVTS choice indices.
    struct Params
    {
        double master = 0.5, blend = 0.5, level = 0.5, drive = 0.5;
        double lo = 0.5, loMid = 0.5, hiMid = 0.5, hi = 0.5;
        int attackIdx = 0;   // APVTS: 0=Flat, 1=Boost, 2=Cut
        int gruntIdx = 0;    // APVTS: 0=Boost, 1=Cut, 2=Flat
        int loMidFreq = 2;   // APVTS: 0=250Hz, 1=500Hz, 2=1kHz
        int hiMidFreq = 2;   // APVTS: 0=750Hz, 1=1.5kHz, 2=3kHz
        bool distEngage = true;
    };

    PedalChain() = default;

    // baseRate = host sample rate; osRate = oversampled rate for the nonlinear
    // region (== baseRate for a 1× / no-oversampling run).
    void prepare(double baseRate, double osRate)
    {
        prepareBase(baseRate);
        prepareOd(osRate); // also re-applies params
    }

    // Base-rate stages (outside the oversampled region). Prepared once at the
    // host sample rate; unaffected by OS-factor changes.
    void prepareBase(double baseRate)
    {
        inputBuffer.prepare(baseRate);
        levelBlend.prepare(baseRate);
        c21.prepare(baseRate);
        eqPreGain.prepare(baseRate);
        baxandall.prepare(baseRate);
        loMid.configure(MidBand::kLoMid, MidBand::kLoMid2n2);
        loMid.prepare(baseRate);
        hiMid.configure(MidBand::kHiMid, MidBand::kHiMid820p);
        hiMid.prepare(baseRate);
        masterOut.prepare(baseRate);
    }

    // Oversampled-region stages. Re-prepared at the new osRate whenever the OS
    // factor changes (dsp.md: re-discretise every oversampled cap at the OS rate;
    // a one-block gap on the switch is acceptable). Re-applies params afterwards
    // so the switched OD topologies (DRIVE/GRUNT/ATTACK) survive the reset.
    void prepareOd(double osRate)
    {
        jfet.prepare(osRate);
        jfet.setADAA(true); // 1st-order ADAA on the J201 square-law shaper (in
                            // addition to oversampling — dsp.md "ADAA"); memoryless
                            // map w/ closed-form Gudermannian antiderivative.
        treble.prepare(osRate);
        drive.prepare(osRate);
        clipper.prepare(osRate);
        recovery.prepare(osRate);
        skB.configure(SallenKeyLPF::kIC4B);
        skB.prepare(osRate);
        skA.configure(SallenKeyLPF::kIC4A);
        skA.prepare(osRate);

        applyParams(cur);
    }

    void reset() noexcept
    {
        inputBuffer.reset();
        jfet.reset();
        treble.reset();
        drive.reset();
        clipper.reset();
        recovery.reset();
        skB.reset();
        skA.reset();
        levelBlend.reset();
        c21.reset();
        eqPreGain.reset();
        baxandall.reset();
        loMid.reset();
        hiMid.reset();
        masterOut.reset();
    }

    // Map APVTS-domain params onto the stage setters. Cheap (per-block, not
    // per-sample); the MNA-based stages only re-invert on an actual change.
    void applyParams(const Params& p)
    {
        cur = p;

        drive.setDrive(p.drive);
        clipper.setGrunt(gruntEnum(p.gruntIdx));
        treble.setAttack(attackEnum(p.attackIdx));

        levelBlend.setLevel(p.level);
        levelBlend.setBlend(p.blend);
        levelBlend.setDistEngage(p.distEngage);

        baxandall.setBass(p.lo);
        baxandall.setTreble(p.hi);
        loMid.setPosition(p.loMid);
        loMid.setSeriesCap(loMidCap(p.loMidFreq));
        hiMid.setPosition(p.hiMid);
        hiMid.setSeriesCap(hiMidCap(p.hiMidFreq));
        masterOut.setMaster(p.master);
    }

    // Apply the Phase-7 capture-fit constants (FitParams.h) to every stage that
    // owns one. Independent of applyParams() — fit params are CALIBRATION (set
    // once per render / once at load), knob params are CONTROL (set per block).
    // Safe to call before or after prepare(): each stage's setter either stores a
    // plain value or re-derives its own coefficients from the stored sample rate,
    // and prepare() recomputes from whatever is stored.
    //
    // ⚠ The rail clamps are the one entry here that can INVALIDATE other fits if
    // enabled at the wrong time — see FitParams.h (enable only after kInputRef is
    // anchored, else every stage clips against an arbitrary reference).
    void setFitParams(const FitParams& f)
    {
        fit = f;

        clipper.setNonlinear(f.clipA0, f.clipSatLo, f.clipSatHi);
        jfet.setNonlinear(f.jfetGm, f.jfetRo, f.jfetRq2, f.jfetSatPos, f.jfetSatNeg);
        // The J201 drain's output impedance is stamped into the treble net's nodal
        // matrix (TrebleAttack.h "Stage boundary"), so it has to follow every gm/ro
        // change. setSourceZ() early-outs when nothing moved — no per-block rebuild.
        {
            const auto z = jfet.getSourceZ();
            treble.setSourceZ(z.ro, z.rq2, z.rp, z.cp);
        }

        drive.setTaperExp(f.driveTaperExp);
        levelBlend.setTaperExp(f.levelTaperExp);
        masterOut.setTaperExp(f.masterTaperExp);

        c21.r = f.c21R;
        recovery.setComponents(f.btR22, f.btR23, f.btC16, f.btC17);

        // RailClamp on EVERY op-amp output (calibration §6 / GATE-4 item). The
        // J201 and CD4049 are deliberately absent: neither is an op-amp, and
        // their own soft saturation IS their limiting.
        drive.setRailVoltages(f.railNeg, f.railPos);
        recovery.setRailVoltages(f.railNeg, f.railPos);
        skB.setRailVoltages(f.railNeg, f.railPos);
        skA.setRailVoltages(f.railNeg, f.railPos);
        eqPreGain.setRailVoltages(f.railNeg, f.railPos);
        baxandall.setRailVoltages(f.railNeg, f.railPos);
        loMid.setRailVoltages(f.railNeg, f.railPos);
        hiMid.setRailVoltages(f.railNeg, f.railPos);
        masterOut.setRailVoltages(f.railNeg, f.railPos);

        drive.setRailClampEnabled(f.railEnabled);
        recovery.setRailClampEnabled(f.railEnabled);
        skB.setRailClampEnabled(f.railEnabled);
        skA.setRailClampEnabled(f.railEnabled);
        eqPreGain.setRailClampEnabled(f.railEnabled);
        baxandall.setRailClampEnabled(f.railEnabled);
        loMid.setRailClampEnabled(f.railEnabled);
        hiMid.setRailClampEnabled(f.railEnabled);
        masterOut.setRailClampEnabled(f.railEnabled);
    }

    const FitParams& getFitParams() const noexcept { return fit; }

    // ---- Split interface (PedalDSP inserts OS + clean-tap delay between) -----

    // Base-rate: IC1_A buffer output — the node that feeds BOTH the OD path and
    // the clean BLEND tap.
    inline double runInputBuffer(double x) noexcept { return inputBuffer.process(x); }

    // Oversampled region: JFET → … → SK-LPF(3.3k). Called once per OVERSAMPLED
    // sample (or per base sample at 1×). The chain's aliasing lives here.
    inline double runOdSample(double buf) noexcept
    {
        double s = jfet.process(buf);
        s = treble.process(s);
        s = drive.process(s);
        s = clipper.process(s);
        s = recovery.process(s);
        s = skB.process(s);
        s = skA.process(s);
        return s;
    }

    // Base-rate: LevelBlend crossfade (clean tap already delay-compensated by the
    // caller) → EQ → MasterOut → OUT.
    inline double processPostBlend(double cleanDelayed, double odDown) noexcept
    {
        double s = levelBlend.process(cleanDelayed, odDown);
        s = c21.process(s);          // C21 100n inter-stage HP (bass shaping)
        s = eqPreGain.process(s);
        s = baxandall.process(s);
        s = loMid.process(s);
        s = hiMid.process(s);
        return masterOut.process(s);
    }

    // Fused base-rate convenience path (no oversampling, no clean-tap delay) —
    // used by the console integration test and a 1× fallback.
    inline double processSample(double x) noexcept
    {
        const double buf = runInputBuffer(x);
        const double od = runOdSample(buf);
        return processPostBlend(buf, od);
    }

private:
    // ---- C21 (100n) inter-stage coupling: first-order highpass --------------
    // Excluded from the isolated EqPreGain/Baxandall oracles (their boundary);
    // circuit.md/build-plan: C21 into the ~10k tone-stack input is a ~150 Hz HP
    // that shapes bass audibly, so it lives HERE at the EqPreGain→Baxandall
    // boundary. R is the effective stack input impedance (NOMINAL ~10k → ~159 Hz
    // corner) — capture-fit at Phase 7 alongside the tone stack. Trapezoidal
    // companion cap at a single node, same convention as MasterOut's HPFs.
    struct C21Highpass
    {
        static constexpr double kC21 = 100.0e-9; // schematic-verified
        static constexpr double kR = 10.0e3;     // NOMINAL stack input Z (fit @P7)

        void prepare(double fs) noexcept
        {
            gc = kC21 * 2.0 * fs;
            reset();
        }
        void reset() noexcept { ieq = 0.0; }

        // Node = cap source-side into R to GND; OUT is the AC-coupled node.
        inline double process(double x) noexcept
        {
            const double v = (gc * x - ieq) / (gc + 1.0 / r);
            ieq = 2.0 * gc * (x - v) - ieq; // v_ab = x - v
            return v;
        }
        double gc = 0.0, ieq = 0.0;
        double r = kR; // Phase-7 capture fit (FitParams.h)
    };

    // APVTS choice index → stage enum / cap value.
    static TrebleAttack::Attack attackEnum(int idx) noexcept
    {
        // APVTS {Flat, Boost, Cut} → enum {Boost, Flat, Cut}
        switch (idx)
        {
            case 1: return TrebleAttack::Attack::Boost;
            case 2: return TrebleAttack::Attack::Cut;
            default: return TrebleAttack::Attack::Flat;
        }
    }
    static Clipper::Grunt gruntEnum(int idx) noexcept
    {
        // APVTS {Boost, Cut, Flat} → enum {Cut, Flat, Boost}
        switch (idx)
        {
            case 0: return Clipper::Grunt::Boost;
            case 2: return Clipper::Grunt::Flat;
            default: return Clipper::Grunt::Cut;
        }
    }
    static double loMidCap(int idx) noexcept
    {
        // APVTS {250, 500, 1k}
        switch (idx)
        {
            case 0: return MidBand::kLoMid47n;
            case 1: return MidBand::kLoMid10n;
            default: return MidBand::kLoMid2n2;
        }
    }
    static double hiMidCap(int idx) noexcept
    {
        // APVTS {750, 1.5k, 3k}
        switch (idx)
        {
            case 0: return MidBand::kHiMid15n;
            case 1: return MidBand::kHiMid3n3;
            default: return MidBand::kHiMid820p;
        }
    }

    // Stages, in signal order.
    InputBuffer inputBuffer;   // 1  IC1_A (base rate; clean tap here)
    JfetStage jfet;            // 2  Q1/Q2      ┐
    TrebleAttack treble;       // 3  treble+ATTACK
    DriveStage drive;          // 4  IC2_A DRIVE │ oversampled
    Clipper clipper;           // 5  IC3 + GRUNT │ region
    RecoveryBridgedT recovery; // 6  IC2_B       │
    SallenKeyLPF skB;          // 7a IC4_B 10.7k │
    SallenKeyLPF skA;          // 7b IC4_A 3.3k  ┘
    LevelBlend levelBlend;     // 8/9 LEVEL + BLEND (base rate)
    C21Highpass c21;           //    C21 inter-stage coupling
    EqPreGain eqPreGain;       // 10 IC5_A/B
    Baxandall baxandall;       // 11 BASS+TREBLE
    MidBand loMid;             // 12 LO-MID IC5_D
    MidBand hiMid;             // 13 HI-MID IC6_A
    MasterOut masterOut;       // 14 MASTER + IC6_B + output HP

    Params cur;
    // Phase-7 capture-fit calibration (FitParams.h). Every stage that owns a fit
    // constant keeps its own copy; this is the authoritative set applied to them,
    // retained so getFitParams() can report what a render actually ran with.
    // Stage prepare() calls re-derive coefficients from their STORED fit values,
    // so an OS-factor change (prepareOd) preserves the calibration.
    FitParams fit;

    PedalChain(const PedalChain&) = delete;
    PedalChain& operator=(const PedalChain&) = delete;
};
