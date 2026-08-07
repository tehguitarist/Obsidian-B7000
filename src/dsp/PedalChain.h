#pragma once

#include <cmath>
#include <cstring>

#include "FitParams.h"
#include "InputBuffer.h"
#include "JfetStage.h"
#include "TrebleAttack.h"
#include "DriveStage.h"
#include "Clipper.h"
#include "RecoveryBridgedT.h"
#include "OdToneRestore.h"
#include "OdDriveTilt.h"
#include "OdMakeup.h"
#include "SallenKeyLPF.h"
#include "LevelBlend.h"
#include "EqPreGain.h"
#include "Baxandall.h"
#include "MidBand.h"
#include "MasterOut.h"
#include "SwitchFade.h"

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
//  • **CD4049 clipper VTC** — the harder aliaser. ⛔⛔ THIS ENTRY USED TO SAY that
//    because the VTC "lives INSIDE an implicit RC-coupled shunt-feedback loop
//    solved per-sample by Newton on node W (it is NOT a memoryless function of one
//    input) ... the Esqueda 1st-order ADAA form does not apply — state-space ADAA
//    would be needed and is out of Phase-6 scope". **THAT IS REFUTED (session
//    123).** It conflates the STAGE with the NONLINEARITY: ADAA1 needs a memoryless
//    map whose ARGUMENT is ~linear between samples, and `vtc` is a memoryless map
//    from node W — W being an internal signal rather than the stage input is
//    irrelevant to the derivation. `Clipper::setADAA` carries the argument, the
//    self-consistency point (node-W KCL makes W a LINEAR combination of x and y, so
//    substituting the mean INSIDE the solve antialiases W too, free) and the
//    measurement. Implemented, gated (GATE X, `analysis/clip_adaa_gate.py`) and
//    MEASURED: 12.6-19.8 dB median improvement over 19 tones at OS 1x/2x.
//    ✅ SESSION 124 SHIPS IT ON, mode Full, **GATED BY OS FACTOR** (on at 1x/2x, off
//    at 4x/8x — FitParams.h::clipAdaaMaxOs has the measured table and applyAdaaPolicy
//    below does the resolving). Enabling it required re-anchoring the fitted
//    clipK 2.4653 -> 2.0, since the antiderivative is elementary only at k = 2; that
//    re-anchor was priced on the 162-capture matrix FIRST and is free (FitParams.h
//    ::clipK). Oversampling still carries the antialiasing at 4x/8x, and carries it
//    alongside ADAA at 1x/2x.
//    ⛔ Do NOT "simplify" this to an unconditional on. The 4x/8x arms were measured
//    and they lose: median benefit collapses and the worst tone costs +9.9/+17.3 dB.
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
        baseSampleRate = baseRate; // the ADAA OS-factor gate's denominator
        inputBuffer.prepare(baseRate);
        levelBlend.prepare(baseRate);
        odMakeup.prepare(baseRate);   // OD:CLEAN ratio correction (s172) — base rate, OD branch
        c21.prepare(baseRate);
        eqPreGain.prepare(baseRate);
        baxandall.prepare(baseRate);
        loMid.configure(MidBand::kLoMid, MidBand::kLoMid2n2);
        loMid.prepare(baseRate);
        hiMid.configure(MidBand::kHiMid, MidBand::kHiMid820p);
        hiMid.prepare(baseRate);
        masterOut.prepare(baseRate);
        // A rate change is not a switch flip, and the two base-rate fades' steps
        // were derived from the OLD rate — snap rather than carry them across.
        loMidFade.reset();
        hiMidFade.reset();
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
        odCoupling.prepare(osRate);
        recovery.prepare(osRate);
        odToneRestore.prepare(osRate);
        odDriveTilt.prepare(osRate);
        skB.configure(SallenKeyLPF::kIC4B);
        skB.prepare(osRate);
        skA.configure(SallenKeyLPF::kIC4A);
        skA.prepare(osRate);

        odSampleRate = osRate;
        applyAdaaPolicy(); // the OS factor just changed => the ADAA gate may flip

        // Same reason as prepareBase: these two fades' steps are OS-rate-derived.
        attackFade.reset();
        gruntFade.reset();

        applyParams(cur);
    }

    void reset() noexcept
    {
        inputBuffer.reset();
        jfet.reset();
        treble.reset();
        drive.reset();
        clipper.reset();
        odCoupling.reset();
        recovery.reset();
        odToneRestore.reset();
        odDriveTilt.reset();
        skB.reset();
        skA.reset();
        levelBlend.reset();
        odMakeup.reset();
        c21.reset();
        eqPreGain.reset();
        baxandall.reset();
        loMid.reset();
        hiMid.reset();
        masterOut.reset();
        // Settle every selector crossfade. This is what `offline_render.cpp` leans
        // on — it calls setParams() THEN reset(), so a static render runs with all
        // four fades at mix = 1 and therefore down the untouched pre-change code
        // path, every sample. The shadows themselves need no reset: they are
        // write-before-read by construction (primed by copy in applyParams, and
        // only ever processed while the fade that priming started is still active).
        attackFade.reset();
        gruntFade.reset();
        loMidFade.reset();
        hiMidFade.reset();
    }

    // Map APVTS-domain params onto the stage setters. Cheap (per-block, not
    // per-sample); the MNA-based stages only re-invert on an actual change.
    void applyParams(const Params& p)
    {
        // ---- Selector-switch crossfades (open-work item 14, S2) -----------------
        // ⚠ ORDER IS LOAD-BEARING, in both directions. Detection must read `cur`
        // BEFORE it is overwritten, and priming must run BEFORE the setters below,
        // because a shadow is only worth anything while it still holds the OUTGOING
        // topology — after `treble.setAttack(...)` there is nothing left to copy.
        //
        // ⚠ The `paramsApplied` guard is not defensiveness about the first block, it
        // is a correctness condition: at construction the stages sit at their own
        // defaults (e.g. `Clipper::grunt` is Cut) while `cur` sits at Params{}'s
        // (gruntIdx 0 = Boost), so the two disagree and a "change" detected against
        // that never-applied state would prime a shadow with a topology the chain
        // has never actually run. `prepareOd()`'s own `applyParams(cur)` is what
        // first makes them agree, and it detects nothing by construction (p == cur).
        const bool attackMoved = paramsApplied && p.attackIdx != cur.attackIdx;
        const bool gruntMoved = paramsApplied && p.gruntIdx != cur.gruntIdx;
        const bool loMidMoved = paramsApplied && p.loMidFreq != cur.loMidFreq;
        const bool hiMidMoved = paramsApplied && p.hiMidFreq != cur.hiMidFreq;

        if (attackMoved)
            trebleShadow = treble;
        if (gruntMoved)
        {
            // GRUNT moves TWO stages, and only one of them is the switch itself:
            // the clipper's cap network, and `OdToneRestore`'s grunt-keyed (gain, Q)
            // table, which jumps a whole row. Both are crossfaded, off the one ramp.
            clipperShadow = clipper;
            odToneShadow = odToneRestore;
        }
        if (loMidMoved)
            loMidShadow = loMid;
        if (hiMidMoved)
            hiMidShadow = hiMid;

        cur = p;
        paramsApplied = true;

        drive.setDrive(p.drive);
        odToneRestore.setDrive(p.drive);
        // ⚠ odToneRestore's MIX key is NOT set here — it depends on levelBlend's state, which is
        // configured further down, and on the LEVEL taper, which applyFitParams() can move
        // independently.  Resolved once in syncOdToneMix() below, called from BOTH, so it cannot
        // depend on which setter ran last (s124: order-dependence between two setters is
        // invisible at each setter and lives only in the callers).
        // Keyed on the PHYSICAL GRUNT position, via the same gruntEnum() the clipper uses, so the
        // stage's table and the captures index the switch the same way (Cut < Flat < Boost).
        // Passing p.gruntIdx raw here would silently permute the rows — APVTS order is
        // {Boost, Cut, Flat}, which is NOT the enum's order.
        odToneRestore.setGrunt(static_cast<int>(gruntEnum(p.gruntIdx)));
        clipper.setGrunt(gruntEnum(p.gruntIdx));
        treble.setAttack(attackEnum(p.attackIdx));

        levelBlend.setLevel(p.level);
        levelBlend.setBlend(p.blend);
        levelBlend.setDistEngage(p.distEngage);
        syncOdToneMix();

        baxandall.setBass(p.lo);
        baxandall.setTreble(p.hi);
        loMid.setPosition(p.loMid);
        loMid.setSeriesCap(loMidCap(p.loMidFreq));
        loMid.setAcrossCap(fit.midCapRatioLo * loMidCap(p.loMidFreq));
        hiMid.setPosition(p.hiMid);
        hiMid.setSeriesCap(hiMidCap(p.hiMidFreq));
        hiMid.setAcrossCap(fit.midCapRatioHi * hiMidCap(p.hiMidFreq));
        masterOut.setMaster(p.master);

        // Arm the ramps LAST, so a fade can never be active over a stage pair that
        // has not finished being reconfigured. Each takes the rate its own stages
        // run at — ATTACK/GRUNT are inside the oversampled region, the two mid
        // selectors are not (`SwitchFade::start`).
        if (attackMoved)
            attackFade.start(odSampleRate);
        if (gruntMoved)
            gruntFade.start(odSampleRate);
        if (loMidMoved)
            loMidFade.start(baseSampleRate);
        if (hiMidMoved)
            hiMidFade.start(baseSampleRate);
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

        clipper.setNonlinear(f.clipA0, f.clipSatLo, f.clipSatHi, f.clipK);
        // Session 123/124: ADAA mode, gated by OS factor. setNonlinear FIRST —
        // adaaExact() reads the hardness this call installs. The mode itself is
        // resolved in applyAdaaPolicy(), which BOTH this and prepareOd() call,
        // because the two are set independently and in OPPOSITE ORDERS by the two
        // callers (OfflineRender: prepare -> setFactorOrder -> setFitParams;
        // PluginProcessor: prepare -> setFitParams -> setFactorOrder). Resolving the
        // policy in one place from the two STORED values is what makes the result
        // independent of that order — an `if` in either setter alone would be
        // silently correct in one caller and wrong in the other.
        applyAdaaPolicy();
        clipper.setC11(f.clipC11);   // fittable GRUNT=Cut coupling cap (session 17)
        clipper.setC12(f.clipC12);   // fittable GRUNT=Flat  add-cap (session 19)
        clipper.setC13(f.clipC13);   // fittable GRUNT=Boost add-cap (session 19)
        clipper.setR16(f.clipR16);   // clipper input R; diagnostic, ships nominal (session 45)
        jfet.setNonlinear(f.jfetGm, f.jfetRo, f.jfetRq2, f.jfetSatPos, f.jfetSatNeg,
                          f.jfetCeilPos, f.jfetCeilNeg, f.jfetExpandBeta);
        // The J201 drain's output impedance is stamped into the treble net's nodal
        // matrix (TrebleAttack.h "Stage boundary"), so it has to follow every gm/ro
        // change. setSourceZ() early-outs when nothing moved — no per-block rebuild.
        {
            const auto z = jfet.getSourceZ();
            treble.setSourceZ(z.ro, z.rq2, z.rp, z.cp);
        }
        treble.setNotchDamp(f.trebleLadderDampR); // session-19: shallow the 322 Hz notch
        // ---- The two-pole ATTACK topology (session 62's proposal; defaults = the
        // drawn network exactly). ⚠ ORDER MATTERS: setNotchDamp() above writes all
        // three throws by design, so the per-throw overrides must follow it.
        treble.setAttackTap(f.attackTapRa, f.attackTapRb, f.attackTapRc, f.attackTapR11);
        {
            // A negative per-throw damping means "inherit trebleLadderDampR" (see
            // FitParams), so the shipped default is a genuine no-op here.
            const double rdBoost = (f.attackDampBoost >= 0.0) ? f.attackDampBoost
                                                              : f.trebleLadderDampR;
            const double rdCut = (f.attackDampCut >= 0.0) ? f.attackDampCut
                                                          : f.trebleLadderDampR;
            treble.setNotchLeg(TrebleAttack::Attack::Flat, f.trebleC5, f.trebleLadderDampR);
            treble.setNotchLeg(TrebleAttack::Attack::Boost,
                               f.trebleC5 + f.attackC5TrimBoost, rdBoost);
            treble.setNotchLeg(TrebleAttack::Attack::Cut,
                               f.trebleC5 + f.attackC5TrimCut, rdCut);
        }
        treble.setC8(f.trebleC8);                 // session-62: 0 removes the drawn ATTACK cap
        // The SHARED ladder (session 64; session 50's next-step (a) finally closed). Not
        // switched by ATTACK — the switch's two poles are setAttackTap/setNotchLeg above.
        treble.setLadder(f.trebleR7, f.trebleLadderR12, f.trebleLadderR14,
                         f.trebleC9, f.trebleC6);
        treble.setC7(f.trebleC7);                 // session-34: A3 step-3a, IC2_A LF headroom
        odCoupling.setC(f.clipC15);                // session-36: A3 step-3b, C15 coupling into IC2_B

        drive.setTaperExp(f.driveTaperExp);
        // ⚠ s163: LEVEL is a 4-segment PWL, not an exponent. `setTaperExp` no longer exists on
        // LevelBlend, so a consumer that missed the change fails to COMPILE rather than silently
        // rebuilding the retired power law (the s146 `masterTaperBreak` lesson, made mechanical).
        levelBlend.setTaper(f.levelTaperBreak1, f.levelTaperFrac1,
                            f.levelTaperBreak2, f.levelTaperFrac2,
                            f.levelTaperBreak3, f.levelTaperFrac3);
        syncOdToneMix();   // the LEVEL taper moves the clean fraction — see applyParams()

        // [ENG] OD-path makeup — the OD:CLEAN ratio (s172, item 10/A3). See OdMakeup.h.
        // Set here and NOT in applyParams(): these are fitted constants, not knobs.
        odMakeup.setLaw(f.odMakeupDb, f.odMakeupLowHz, f.odMakeupLowCutDb,
                        f.odMakeupHighHz, f.odMakeupHighCutDb,
                        f.odMakeupLowS, f.odMakeupHighS);
        odMakeup.setHfMix(f.odMakeupHfHz, f.odMakeupHfQ, f.odMakeupHfAtOdDb,
                          f.odMakeupHfPeakDb, f.odMakeupHfPeakCf, f.odMakeupHfAtCleanDb);
        odToneRestore.setQScale(f.odNotchQScale);   // notch WIDTH multiplier (s172)
        odToneRestore.setDepthOffset(f.odNotchDepthDb);  // uniform extra cut (s172)

        // [ENG] level-dependent treble tilt — see OdDriveTilt.h before changing anything.
        odDriveTilt.setEnabled(f.odTiltEnabled != 0);
        odDriveTilt.setTime(f.odTiltTimeMs);
        odDriveTilt.setLaw(f.odTiltF0, f.odTiltS, f.odTiltDbPerDb, f.odTiltRefDbv,
                           f.odTiltMaxCutDb);
        masterOut.setTaper(f.masterTaperBreak, f.masterTaperFrac,
                           f.masterTaperBreak2, f.masterTaperFrac2);

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

        // Mid-stage range limiter (Phase 9 GAP #4). Both switched CAPS are applied in
        // applyParams() instead, because they depend on the switch position: the series
        // cap through loMidCap()/hiMidCap() (fit.midLoCap* / fit.midHiCap*) and the
        // across-lug cap as fit.midCapRatio* x that, the A2c-3 scaled PAIR.
        loMid.setWiperR(f.midWiperRLo);
        hiMid.setWiperR(f.midWiperRHi);

        // C31 (2u2) — the Baxandall→LO-MID coupling cap (item 16, s177). LO-MID ONLY:
        // circuit.md gives HI-MID's input as IC5_D's output wire, with no coupling cap,
        // so hiMid is deliberately NOT given one and stays on the 4-unknown path.
        // ⚠ Solved INSIDE MidBand rather than added as a C21Highpass-shaped stage — the
        // load is frequency-dependent and a fixed-R HP reproduces ~2% of it (GATE BG).
        loMid.setInputCap(f.c31Enabled ? f.c31 : 0.0);

        // Baxandall TREBLE range limiter (Phase 9 A2c).
        baxandall.setTrebleWiperR(f.trebleWiperR);
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
        // ⚠ The envelope is taken on the OD REGION'S INPUT, not on this stage's own
        // input.  `OdDriveTilt.h` records why both local taps were rejected: the
        // clipper's input slides ~24 dB with the DRIVE knob, and the treble ladder's
        // output is not flat in frequency, so during a sweep it would track the
        // LADDER'S SHAPE instead of the stimulus level.
        odDriveTilt.observe(buf);
        double s = jfet.process(buf);

        // ---- ATTACK crossfade (item 14, S2; SwitchFade.h) -----------------------
        // Every `active()` arm below is a branch AROUND the untouched pre-change
        // expression, never a rewrite of it — a settled fade must run the identical
        // code path, which is what keeps a static render bit-identical.
        if (attackFade.active())
        {
            const double shadowOut = trebleShadow.process(s);
            s = attackFade.blend(shadowOut, treble.process(s));
            attackFade.tick();
        }
        else
        {
            s = treble.process(s);
        }

        s = drive.process(s);

        // ---- GRUNT crossfade: TWO points, ONE ramp ------------------------------
        // Read `active()` once and tick once, at the second point, so both blends in
        // a given sample see the same mix.
        const bool gruntFading = gruntFade.active();
        if (gruntFading)
        {
            const double shadowOut = clipperShadow.process(s);
            s = gruntFade.blend(shadowOut, clipper.process(s));
        }
        else
        {
            s = clipper.process(s);
        }
        s = odCoupling.process(s);
        s = recovery.process(s);
        if (gruntFading)
        {
            const double shadowOut = odToneShadow.process(s);
            s = gruntFade.blend(shadowOut, odToneRestore.process(s));
            gruntFade.tick();
        }
        else
        {
            s = odToneRestore.process(s);
        }

        s = odDriveTilt.process(s);
        s = skB.process(s);
        s = skA.process(s);
        return s;
    }

    // Diagnostic-only per-stage taps of the OD region (session 19, Phase 9). Runs
    // the identical stage order as runOdSample() but records each boundary output,
    // so a probe can localise WHICH OD stage shapes a given band. Not used by the
    // plugin or OfflineRender; state advances exactly like runOdSample().
    struct OdTaps { double jfet, treble, drive, clipper, odCoupling, recovery, odToneRestore, skB, skA; };
    inline OdTaps runOdSampleTapped(double buf) noexcept
    {
        OdTaps t;
        t.jfet = jfet.process(buf);
        t.treble = treble.process(t.jfet);
        t.drive = drive.process(t.treble);
        t.clipper = clipper.process(t.drive);
        t.odCoupling = odCoupling.process(t.clipper);
        t.recovery = recovery.process(t.odCoupling);
        odDriveTilt.observe(buf);
        t.odToneRestore = odDriveTilt.process(odToneRestore.process(t.recovery));
        t.skB = skB.process(t.odToneRestore);
        t.skA = skA.process(t.skB);
        return t;
    }

    // Base-rate: LevelBlend crossfade (clean tap already delay-compensated by the
    // caller) → EQ → MasterOut → OUT.
    inline double processPostBlend(double cleanDelayed, double odDown) noexcept
    {
        // dist_engage footswitch crossfade (item 14, s171). Advanced here rather than
        // inside process() so that process() stays pure — cleanFraction() evaluates it
        // twice per block with unit inputs to recover its own coefficients, and a
        // state-advancing process() would make that accessor eat the fade. A no-op
        // (one compare, early return) whenever the switch is not mid-stomp, which is
        // every sample of every offline render.
        levelBlend.tickSmoothing();
        // OD-path makeup (FitParams::odMakeupDb, s172 — the OD:CLEAN ratio, item 10/A3).
        // ⛔ OUTSIDE levelBlend.process() ON PURPOSE: cleanFraction() recovers its own
        // coefficients by superposition on process() with unit inputs, so folding the
        // makeup in there would silently re-key OdToneRestore's mix law in the same edit.
        // See the FitParams block for why one change at a time matters here.
        // Ships at 1.0 (0 dB) => bit-identical to every prior build.
        double s = levelBlend.process(cleanDelayed, odMakeup.process(odDown));
        s = c21.process(s);          // C21 100n inter-stage HP (bass shaping)
        s = eqPreGain.process(s);
        s = baxandall.process(s);

        // ---- Mid-frequency selector crossfades (item 14, S2; SwitchFade.h) ------
        // Base rate, unlike ATTACK/GRUNT: these two stages sit after LevelBlend and
        // outside the oversampled region. Same branch-around-the-original shape.
        if (loMidFade.active())
        {
            const double shadowOut = loMidShadow.process(s);
            s = loMidFade.blend(shadowOut, loMid.process(s));
            loMidFade.tick();
        }
        else
        {
            s = loMid.process(s);
        }

        if (hiMidFade.active())
        {
            const double shadowOut = hiMidShadow.process(s);
            s = hiMidFade.blend(shadowOut, hiMid.process(s));
            hiMidFade.tick();
        }
        else
        {
            s = hiMid.process(s);
        }

        return masterOut.process(s);
    }

    // Diagnostic-only per-stage taps of the POST-BLEND path (session 41, Phase 9
    // item A5). Exact sibling of runOdSampleTapped above: identical stage order to
    // processPostBlend(), each boundary recorded, state advancing the same way, and
    // used by no production path. Its purpose is to answer "which op-amp output
    // actually reaches its rail" — with the RailClamps DISABLED every tap is the
    // stage's UNCLAMPED output, i.e. the voltage that op-amp would have to swing,
    // which is exactly what a headroom re-derivation needs.
    //
    // ⚠ Two nodes are deliberately NOT tapped, and neither hides anything:
    //  • EqPreGain's IC5_A buffer output is unity, so it equals the `c21` tap.
    //  • MasterOut's IC6_B output is `ntop * divRatio` with divRatio <= 1 and C36
    //    cornering at 0.72 Hz, so it can only ever be SMALLER than the `hiMid` tap
    //    — if IC6_A is inside the rail window, IC6_B necessarily is too.
    struct PostTaps { double blend, c21, eqPre, baxandall, loMid, hiMid, master; };
    inline PostTaps processPostBlendTapped(double cleanDelayed, double odDown) noexcept
    {
        PostTaps t;
        t.blend = levelBlend.process(cleanDelayed, odDown);
        t.c21 = c21.process(t.blend);
        t.eqPre = eqPreGain.process(t.c21);
        t.baxandall = baxandall.process(t.eqPre);
        t.loMid = loMid.process(t.baxandall);
        t.hiMid = hiMid.process(t.loMid);
        t.master = masterOut.process(t.hiMid);
        return t;
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
    // ---- ADAA OS-factor gate (session 124) ----------------------------------
    // Resolve FitParams::clipAdaa (WHICH mode) against clipAdaaMaxOs (WHERE it is
    // worth having) and the OD region's current oversampling factor. Called from
    // BOTH setFitParams() and prepareOd() because either can move independently,
    // and the two production callers set them in opposite orders — see the comment
    // at the setFitParams call site.
    //
    // Policy, measured (FitParams.h::clipAdaaMaxOs has the full GATE X table): ADAA1
    // wins big at 1x/2x with a worst case bounded at +3.3 dB, and at 4x/8x its median
    // collapses while its worst tone COSTS up to +17.3 dB. So the gate is `<=`, not a
    // scale factor: the benefit is not monotone in rate and must not be interpolated.
    //
    // ⚠ Rounds the factor rather than truncating, and guards the base rate — osRate
    // and baseSampleRate are doubles that have been through JUCE's rate plumbing, so
    // 2.0000000001 must not read as 2 while 1.9999999999 reads as 1. A gate that
    // flips on a floating-point crumb would be a nightmare to reproduce from a bug
    // report ("it aliases on his machine and not mine").
    void applyAdaaPolicy() noexcept
    {
        const auto requested = (fit.clipAdaa == 2)   ? Clipper::Adaa::Residue
                               : (fit.clipAdaa == 1) ? Clipper::Adaa::Full
                                                     : Clipper::Adaa::Off;

        // Before prepare() there is no factor to gate on; keep the requested mode so
        // a fit-only unit test (which never calls prepare) still sees what it asked
        // for. prepareOd() re-resolves the moment a real rate arrives.
        int factor = 1;
        if (baseSampleRate > 0.0 && odSampleRate > 0.0)
            factor = (int) std::lround(odSampleRate / baseSampleRate);

        clipper.setADAA(factor <= fit.clipAdaaMaxOs ? requested : Clipper::Adaa::Off);
    }

    double baseSampleRate = 0.0; // host rate; set by prepareBase
    double odSampleRate = 0.0;   // oversampled rate; set by prepareOd

    // ---- C15/R20/R21 clipper-output coupling: first-order highpass ----------
    // Phase 9 / A3 step 3b (session 36). NOT modelled before this session — the
    // clipper output fed straight into RecoveryBridgedT with nothing between them,
    // i.e. C15 (2u2) / R20 (10k) / R21 (1M) were entirely absent, not merely
    // treated as inert. circuit.md: C15 -> R20 -> node X -> IC2_B(+), R21 X->VD;
    // R20 carries no other branch at its near node, so R20+R21 combine into ONE
    // effective series R (same reduction as C21Highpass below), fixed at the
    // schematic value 1.01 MΩ — ruled OUT as a fit target by the step-3b pixel-
    // zoom pass (docs/phase9-validation.md §4): even R21->0 only reaches 7.2 Hz.
    // Only the capacitance is fittable (FitParams::clipC15) — see that field's
    // comment for the null-gate evidence and the honesty caveats on this element.
    // Same trapezoidal-companion single-node convention as C21Highpass; runs at
    // OS RATE (it sits inside the oversampled region, between Clipper and
    // RecoveryBridgedT), unlike C21Highpass which is base-rate/post-BLEND.
    struct OdCoupling
    {
        static constexpr double kR = 10.0e3 + 1.0e6; // R20 + R21, schematic-verified

        void prepare(double fs) noexcept
        {
            fsSeen = fs;
            gc = c * 2.0 * fs;
            reset();
        }
        void reset() noexcept { ieq = 0.0; }

        inline double process(double x) noexcept
        {
            const double v = (gc * x - ieq) / (gc + 1.0 / kR);
            ieq = 2.0 * gc * (x - v) - ieq;
            return v;
        }

        // Bit-compare guard, like TrebleAttack::setC7: skips the coefficient
        // recompute when setFitParams re-sends the same value every block.
        void setC(double farads) noexcept
        {
            const double next = (farads > 0.0) ? farads : kC15Nominal;
            if (std::memcmp(&next, &c, sizeof(double)) == 0)
                return;
            c = next;
            if (fsSeen > 0.0)
                gc = c * 2.0 * fsSeen;
        }

        static constexpr double kC15Nominal = 2.2e-6; // schematic value (inert in-band)
        double gc = 0.0, ieq = 0.0;
        double c = kC15Nominal;
        double fsSeen = 0.0;
    };

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
    // Push the mix key into the OD-path tone-restore stage.  Called from BOTH applyParams() and
    // applyFitParams(), because the clean fraction depends on LEVEL, BLEND, dist-engage AND the
    // fitted LEVEL taper — four inputs set by two different entry points in caller-dependent
    // order.  Resolving it from levelBlend's own stored state, in one place, is what makes the
    // result independent of that order.
    void syncOdToneMix() noexcept
    {
        // ⚠ BOTH mix-keyed stages read the SAME scalar from the SAME place. `OdMakeup`'s
        // HF term joined them at s173; resolving it here rather than at either call site
        // is what stops the two drifting apart (the s124 order-dependence trap).
        const double cf = levelBlend.cleanFraction();
        odToneRestore.setCleanFraction(cf);
        odMakeup.setCleanFraction(cf);
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
    // NOT static: the whole switched-cap table is capture-fitted (FitParams::midLoCap*
    // / midHiCap* — the [ENG] table was computed, never schematic-verified, and the
    // 3-way selectors are [ENG] themselves, so there is no document to defer to). The
    // MidBand::kLoMid*/kHiMid* constexprs remain the [ENG] nominals.
    double loMidCap(int idx) const noexcept
    {
        // APVTS {250, 500, 1k}
        switch (idx)
        {
            case 0: return fit.midLoCap250;
            case 1: return fit.midLoCap500;
            default: return fit.midLoCap1k;
        }
    }
    double hiMidCap(int idx) const noexcept
    {
        // APVTS {750, 1.5k, 3k}
        switch (idx)
        {
            case 0: return fit.midHiCap750;
            case 1: return fit.midHiCap1500;
            default: return fit.midHiCap3k;
        }
    }

    // Stages, in signal order.
    InputBuffer inputBuffer;   // 1  IC1_A (base rate; clean tap here)
    JfetStage jfet;            // 2  Q1/Q2      ┐
    TrebleAttack treble;       // 3  treble+ATTACK
    DriveStage drive;          // 4  IC2_A DRIVE │ oversampled
    Clipper clipper;           // 5  IC3 + GRUNT │ region
    OdCoupling odCoupling;     // 5b C15/R20/R21 │ (session-36, A3 step 3b)
    RecoveryBridgedT recovery; // 6  IC2_B       │
    OdToneRestore odToneRestore; // 6b [ENG, non-schematic] session 150 notch/peak restore
    OdDriveTilt odDriveTilt;   // 6c [ENG, non-schematic] session 166 level-dependent treble tilt
    SallenKeyLPF skB;          // 7a IC4_B 10.7k │
    SallenKeyLPF skA;          // 7b IC4_A 3.3k  ┘
    LevelBlend levelBlend;     // 8/9 LEVEL + BLEND (base rate)
    // OD:CLEAN ratio correction on the OD branch at the summing node (s172, item 10/A3).
    // Ships INERT (0 dB, no shelf cut) => bit-identical to every pre-s172 build.
    OdMakeup odMakeup;
    C21Highpass c21;           //    C21 inter-stage coupling
    EqPreGain eqPreGain;       // 10 IC5_A/B
    Baxandall baxandall;       // 11 BASS+TREBLE
    MidBand loMid;             // 12 LO-MID IC5_D
    MidBand hiMid;             // 13 HI-MID IC6_A
    MasterOut masterOut;       // 14 MASTER + IC6_B + output HP

    // ---- Selector-switch crossfade shadows (open-work item 14, S2) --------------
    // One SHADOW per stage whose TOPOLOGY a 3-way selector changes, plus the one
    // stage whose coefficient TABLE a selector jumps (`OdToneRestore`, keyed on the
    // physical GRUNT position). Each is primed by memberwise copy from its live
    // twin at the instant of a flip and then runs the OUTGOING circuit for the
    // duration of the fade — see SwitchFade.h for why copying, rather than starting
    // from rest, is the physically correct initial condition.
    //
    // ⚠ COST: a shadow doubles its own stage's per-sample work, and only while a
    // fade is running (30 ms). The clipper is the expensive one — a bracketed
    // Newton solve — so a GRUNT flip is the priciest transition in the chain. That
    // is bounded, transient, and buys the click; `PerfBenchmark` measures the
    // SETTLED chain, which is untouched (the `active()` branches are not taken).
    //
    // ⚠ Deliberately NOT prepared or reset anywhere: they are write-before-read by
    // construction. `applyParams` is the only thing that starts a fade, and it
    // primes the shadow in the same call, immediately before doing so. Preparing
    // them separately would introduce a second configuration path that could drift
    // from the live stage's — the failure this design exists to avoid.
    TrebleAttack trebleShadow;
    Clipper clipperShadow;
    OdToneRestore odToneShadow;
    MidBand loMidShadow, hiMidShadow;
    SwitchFade attackFade, gruntFade, loMidFade, hiMidFade;
    // False until the first applyParams() has reconciled the stages with `cur` —
    // see the correctness note at the top of applyParams().
    bool paramsApplied = false;

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
