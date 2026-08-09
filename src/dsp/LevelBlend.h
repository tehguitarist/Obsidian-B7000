#pragma once

#include <algorithm>
#include <cmath>
#include "../utils/TaperUtils.h"
#include "MnaSolve.h" // mna::differs — exact-inequality float compare without -Wfloat-equal

// =============================================================================
// Stage 7/8 — LEVEL (VR2) + BLEND (VR1) — OD volume + clean/OD crossfade
// =============================================================================
// circuit.md "LEVEL, BLEND (crossfade mix)":
//   LEVEL (VR2) | 100k A taper | OD volume divider: pin3=IC4_A out, pin1=VD,
//                                  wiper=leveled OD → BLEND pin3
//   BLEND (VR1) | 100k B taper | crossfade: pin3=leveled OD, pin1=clean
//                                  (IC1_A out), wiper=mix → IC5_A(+)
//
// ---- Resistive network (AC-referenced to VD) --------------------------------
// Both inputs (clean and OD) sit on the same DC bias VD = 4.5 V, so the DC
// component cancels in the crossfade — only the AC signal matters.
//
//   Vo(OD) ── Rup ── Vw ── Rdn ── GND(VD)
//                     │
//                ┌────┴────┐
//                │  BLEND   │  100k B-taper
//                │          │
//          pin3 ◄┤ R_od     ├─ wiper ── Vout ──▶ IC5_A(+)
//                │          │
//          pin1 ◄┤ R_cl     │
//                └────┬─────┘
//   Vc(clean) ────────┘
//
// LEVEL pot (100k A) split: Rup = (1-L)*100k, Rdn = L*100k
// BLEND pot (100k B) split: R_od = (1-B)*100k, R_cl = B*100k
// where L = levelTaper(x_level, ...) ∈ [0,1]  — a 4-segment PWL since s163;
//         ⛔ NOT a power law any more, see the constants block below
//       B = x_blend (linear — B-taper)
//
// KCL at Vw (LEVEL wiper):
//   (Vo - Vw)/Rup = Vw/Rdn + (Vw - Vc)/100k
//
// Solved for Vw:
//   Vw = (Vo/(1-L) + Vc) / (1/(1-L) + 1/L + 1)
//
// Output (BLEND wiper):
//   Vout = (1-B)*Vc + B*Vw
//
// ---- Loading effect ---------------------------------------------------------
// The BLEND pot loads the LEVEL divider because BLEND's OD-side segment
// (R_od = (1-B)*100k) connects the LEVEL wiper to the BLEND wiper. Since the
// BLEND wiper output goes to a high-Z op-amp input (IC5_A+), the entire BLEND
// pot conducts I = (Vw-Vc)/100k, which flows through R_od AND R_cl.
//
// This current through R_od (= (1-B)*100k from LEVEL wiper to BLEND wiper) and
// R_cl (= B*100k from BLEND wiper to clean input) creates the asymmetric OD-vs-
// clean loading effect. At LEVEL=noon/BLEND=noon the OD path gain is ~3.3 dB
// below the ideal unloaded divider prediction (matching the pedal's real
// behaviour — confirmed by the blend-0700/1200 captures at Phase 7).
//
// The clean side has source impedance ~0 Ω (IC1_A op-amp output); the OD side
// has source impedance ~0 Ω (IC4_A op-amp output) but the LEVEL wiper's
// equivalent Thevenin impedance is Rup||Rdn = L*(1-L)*100k, maximal (~25k) at
// mid-rotation. This is why the crossfade law is asymmetric.
//
// ---- BLEND wiper end stop (session 181, open-work item 12) -------------------
// ⭐⭐ [ENG], NON-SCHEMATIC, USER-DECIDED 2026-08-08. The ideal network above makes the
// output EXACTLY zero at LEVEL min / BLEND max — Rdn = L*Rp = 0 shorts the LEVEL wiper
// to VD, and BLEND at max reads that wiper alone. The reference does not mute there: it
// delivers a real signal ~32 dB below its own clean tap.
//
// GATE BK (`analysis/level_min_residual_gate.py`) named the source with no threshold and
// no fit, on the STIMULUS DOSE-RESPONSE. The two candidate sources have completely
// different ones, measured on this capture set: the OD path COMPRESSES (9.8 dB out per
// 24 dB in) and the clean tap is LINEAR (24.0). The residual holds a constant ratio
// against the CLEAN tap (span 1.9 dB across the ladder) and not against the OD path
// (span 16.0) ⇒ it is a CLEAN-SIDE BLEED. ⛔ And the LEVEL-pot end-stop hypothesis is
// REFUTED, not merely unsupported: the shipped taper is linear through the origin, so a
// small LEVEL KNOB *is* that model, and rendered at four values its residual is a MIX of
// both sources (both reach the wiper through ~Rp) and inherits the OD path's compression
// — 14.5-14.9 dB out per 24 dB in against the pedal's 25.8, short by ~11 dB at every L.
//
// THE MODEL, and it is a pot end stop expressed the way a pot actually has one: the
// wiper traverses Rp of a track whose total is Rl + Rp + Rh, so it reaches neither lug.
// With `endHi = Rh/total` (the pin3/OD end), `endLo = Rl/total` (the pin1/clean end) and
// `k = 1 - endLo - endHi` (the traversable span, which is also the body's normalised
// conductance seen from the LEVEL wiper):
//
//     B_eff  = endLo + x*k                       (x=0 -> endLo, x=1 -> 1-endHi)
//     KCL    : Vw*[1/(1-L) + 1/L + k] = Vo/(1-L) + Vc*k
//     Vout   = (1 - B_eff)*Vc + B_eff*Vw
//
// which at endLo = endHi = 0 (k = 1) reduces TERM BY TERM to the expressions above —
// asserted, not argued: `LevelBlendTest` Test 8(a) requires BIT-identity against the
// pre-s181 oracle across an 81-cell pot sweep, and a `--fit blendEndStop=0` render puts
// LEVEL min back to exact digital zero.
// At LEVEL min / BLEND max it gives Vout = endHi*Vc exactly: a pure clean bleed, no OD.
//
// ⚠⚠ THE PRICE, AND IT IS THE REASON THIS WAS A USER DECISION RATHER THAN A FIX. The same
// end stop is present at BLEND max whatever LEVEL does, so the clean coefficient at
// LEVEL = BLEND = max goes 0 -> e. That EXACT ZERO is the bleed-free corner every absolute
// instrument in the project anchors on (GATE K7's ratio, GATE O's A3 ledger, GATE L's
// |rho|, `OdToneRestore`'s base row, GATE W/AE's bleed-free membership, and
// `cleanFraction()` itself). ⛔ There is no way around it inside this topology, and that
// is structural rather than a failure of imagination: at LEVEL min the wiper is 0 ohm to
// VD, so ANY bleed arriving at or before that node is shorted out — a clean bleed that
// survives there must arrive AFTER it, i.e. at the BLEND wiper, i.e. at every LEVEL.
//
// ⚠ ONE-SIDED ON PURPOSE. A real pot has an end stop at BOTH ends, and the pin1 (clean)
// end would put a matching OD leak at BLEND min. It is NOT shipped: at e = 0.0242 that
// leak sits >= 27 dB below the clean tap at every rung and contributes < 0.02 dB of
// level, so THIS CAPTURE SET CANNOT CONFIRM OR REFUTE IT. `blendEndStopClean` exists,
// defaults to 0, and is the place to test it if a capture ever can. Shipping it on
// physical symmetry alone would move every interior BLEND setting for no measured reason.
//
// ---- dist_engage override ---------------------------------------------------
// When dist_engage = false, the output is forced to 100% clean (Vc), ignoring
// the BLEND knob. This implements the [ENG] DIST footswitch behaviour per
// circuit.md "Footswitches".
//
// ⭐⭐ SESSION 171 — THE CROSSFADE IS NOW BUILT (open-work item 14, S2). It was
// "deferred to Phase 6" from the stage's first draft and never picked up, so for
// ~165 sessions this override was a HARD BRANCH on a control that is a FOOTSWITCH
// — stomped live, mid-performance — while `bypass`, the less time-critical of the
// two, had had its 5 ms crossfade since Phase 6. `architecture.md` specifies it as
// "a target-mix override on the existing BLEND crossfade … with its own short
// crossfade"; that is what `distMix` below is.
//
// Measured before it was built (`tests/SwitchTransitionTest.cpp`, the item's own
// pre-registered bar — the per-sample step the switch introduces, against the
// tone's own steady-state step): the hard branch ran **3.2x to 53.8x**, the worst
// of any control in the chain, and it failed in BOTH directions at every pot
// configuration. That is expected rather than surprising: the step is the full
// |OD − clean| difference between two signals that have been through entirely
// different chains, so it is order-unity where a selector switch's is a transient.
//
// ⚠⚠ THE STEADY-STATE PATH MUST BE THE IDENTICAL CODE PATH, not this crossfade
// evaluated at coefficient 1.0 — a design constraint, not an afterthought. That is
// what makes the 162-capture matrix come back BIT-IDENTICAL (OfflineRender never
// flips a switch mid-render, so `distMix` sits pinned at an endpoint for every
// rendered sample) and is why NO re-baseline is owed for this change, unlike
// s162/s163/s166. Both endpoints below are therefore explicit early returns onto
// exactly the pre-change expressions.
//
// ---- Polarity ---------------------------------------------------------------
// Both paths are non-inverting (resistive dividers). The polarity concern at
// the BLEND summing node (J201 unconfirmed sign + clipper's known −48.5 gain)
// will be resolved with an end-to-end DC-step test at Phase 6.
// =============================================================================
class LevelBlend
{
public:
    LevelBlend() = default;

    // ---- LEVEL audio-taper shape — FOUR-SEGMENT PIECEWISE LINEAR -------------
    // ⭐⭐ SESSION 163 — THE POWER LAW IS RETIRED (`kLevelTaperExp = 1.43`, then
    // `FitParams::levelTaperExp = 2.25` from session 8). The wiper reaches
    // `Frac_i` of full resistance at rotation `Break_i`; linear in between and
    // either side. Both endpoints are EXACT by construction and no parameter can
    // move them, which the topology requires:
    //   x = 0 → 0 (wiper on VD, no OD)   x = 1 → 1 (the bleed-free anchor).
    //
    // ⚠⚠ THAT SECOND ENDPOINT IS LOAD-BEARING FAR BEYOND THIS STAGE. L(1) = 1
    // makes the clean coefficient EXACTLY zero at LEVEL = BLEND = max, and that
    // exact zero is the bleed-free corner every absolute instrument in the
    // project anchors on (GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho|,
    // `OdToneRestore`'s base row, GATE W/AE's bleed-free membership). GATE AZ6
    // asserts it is bit-identical across this change.
    //
    // WHY IT MOVED, in one line: measured against the pedal's own LEVEL ladder,
    // the shipped power law is 2.844 dB rms out (worst 7.638) where a free
    // monotone curve reaches 0.344 — and 0.344 is inside the target's OWN
    // across-stimulus ambiguity of 0.755 dB. GATE K's closure (s103, "THE TAPER
    // CANNOT FIX IT") was measured on the single-EXPONENT family, and "no single
    // exponent reaches" is a different claim from "no monotone taper reaches" —
    // the distinction s115/s146 were already forced to draw on the MASTER pot.
    // Full derivation: GATE AY (`analysis/level_taper_reshape.py`, s162) and
    // GATE AZ (`analysis/level_taper_fit.py`, s163).
    //
    // ⭐⭐ WHY FOUR SEGMENTS AND NOT THREE (s146's MASTER precedent is a FAMILY,
    // not a number): 3 segments reaches only 0.480 dB rms and misplaces the
    // 0.875 detent by 0.19 in L, with a sign-alternating residual; 4 reaches
    // 0.340 — the architectural floor — and a 5-segment control returns the
    // 4-segment answer to the digit, so the family SATURATES at 4. That is the
    // stopping proof, not a parameter-count argument. And the fitted curve sits
    // INSIDE the requirement's own per-detent spread at EVERY detent (worst
    // 0.085 of it), which is the overfitting test in the constant's own units.
    //
    // ⛔⛔ RE-FITTED s173, AND THESE DEFAULTS WERE LEFT ON THE RETIRED s163 SET
    // UNTIL s174 (was 0.219415/0.038146, 0.529680/0.166340, 0.857645/0.425688).
    // The shipped plugin was never wrong — `PedalChain::applyFitParams` always
    // calls `setTaper()` from `FitParams.h` — but TWO consumers read these
    // compiled defaults and both were therefore reading a curve nothing runs:
    // `setLevel()`'s invalid-set FALLBACK, and `LevelBlendTest` Test 0, i.e. the
    // one test that exists to catch a lost convexity was asserting the shape of
    // the retired curve. s146's `masterTaperBreak` lesson (a name surviving a
    // VALUE change while its consumers keep rebuilding the old curve), one file
    // over. ⇒ when FitParams' taper moves, move these in the same edit.
    //
    // ⚠⚠ AND THE OUTSIDE CORROBORATION THIS BLOCK USED TO CLAIM HAS INVERTED —
    // STATED, NOT DELETED, because a future session must not re-quote it. It
    // read: "the half-rotation fraction goes 21.02 % → 15.41 %, TOWARD the
    // textbook A-taper 10–15 % band that circuit.md specifies for VR2 (100k A)".
    // Under the s173 re-fit L(0.5) = **23.75 %**, i.e. it moved AWAY from that
    // band and past where the retired power law sat. Convexity survives and is
    // the half that still corroborates — slopes 0.256 → 0.636 → 1.266 → 9.568,
    // rising, a physically buildable track — but the A-taper agreement does not,
    // and it was never a term of the objective in either epoch. ⇒ the taper is
    // fitted to the measured LEVEL law and that is its whole warrant; do not
    // re-derive it from the A-taper band. `LevelBlendTest` Test 0 asserts the
    // shape and FAILS if convexity, monotonicity or an endpoint is lost.
    //
    // ⚠ The last segment is a LOWER bound on its own steepness: GATE AY3 reports
    // the LEVEL-max requirement as `above` (the pedal wants more than L = 1 can
    // deliver), so it is clamped by the anchor rather than met. That clamp is
    // what puts the last break at **98.4 %** of rotation with a slope of 9.568 —
    // the fit pressing against the anchor, not a measured feature of the pot.
    //
    // ✅ RE-CHECKED s174 on the current epoch (GATE AY against
    // `s173c_hfmix.json`): AY2 REFUSES to run — "no detent has a requirement
    // larger than its own across-stimulus spread" (worst need −0.58 dB against a
    // 1.27 dB spread) — so this set still closes the LEVEL law after `OdMakeup`
    // and the mix-keyed HF term moved the OD:CLEAN ratio under it. No re-fit.
    //
    // ✅✅ USER DECISION TAKEN (s174): KEEP, not re-derived toward the A-taper
    // band. AY2's refusal means the current epoch supplies no per-detent
    // requirement to fit a smoother curve AGAINST — the LEVEL law is inside its
    // own measurement noise everywhere, so any alternative shape chosen only to
    // improve the half-rotation number would be an unmeasured, self-selected
    // pick with nothing behind it (`measurement-discipline.md`'s
    // `self-selecting-scores` / `known-answer-must-not-start-at-its-answer`
    // family). The shipped curve is the one thing on record that IS
    // measurement-grounded: it was fitted against the strictest epoch this law
    // has had (s172's, before `OdMakeup` diluted the requirement) and it still
    // satisfies the current one. Trading that for A-taper cosmetics — a
    // property never in either fit's objective — is the worse trade, not the
    // better one.
    // ⛔⛔ THESE MUST EXACTLY EQUAL `FitParams`' SHIPPED TAPER — `LevelBlendTest` Test 0 asserts
    // it, and exact is the right bar because both are literals of ONE fit, so any difference is a
    // missed edit and never a rounding (s174, where these defaults had silently kept the RETIRED
    // s163 curve for a session while the test that exists to catch a lost convexity was asserting
    // the shape of a curve nothing runs, and passing).
    // Re-fitted s190 with `FitParams` (was 0.221598/0.056630, 0.494043/0.229938,
    // 0.984417/0.850908 — s173); the derivation lives at the FitParams block, not duplicated here.
    static constexpr double kLevelTaperBreak1 = 0.206030;
    static constexpr double kLevelTaperFrac1 = 0.026166;
    static constexpr double kLevelTaperBreak2 = 0.543750;
    static constexpr double kLevelTaperFrac2 = 0.223470;
    static constexpr double kLevelTaperBreak3 = 0.775388;
    static constexpr double kLevelTaperFrac3 = 0.528328;

    // The taper itself, as a free function so tests, the oracle and any future
    // consumer read ONE implementation rather than rebuilding the curve from the
    // constants — the s146 `masterTaperBreak` trap, where four consumers would
    // each have silently rebuilt a two-segment curve from a renamed parameter.
    static constexpr double levelTaper(double x, double b1, double f1, double b2, double f2,
                                       double b3, double f3) noexcept
    {
        return (x <= 0.0)  ? 0.0
             : (x >= 1.0)  ? 1.0
             : (x <= b1)   ? (f1 * x / b1)
             : (x <= b2)   ? (f1 + (f2 - f1) * (x - b1) / (b2 - b1))
             : (x <= b3)   ? (f2 + (f3 - f2) * (x - b2) / (b3 - b2))
                           : (f3 + (1.0 - f3) * (x - b3) / (1.0 - b3));
    }

    // ---- dist_engage footswitch crossfade ------------------------------------
    // ⚠⚠ NOT 5 ms. The 5 ms bypass precedent (`architecture.md` "Bypass") was the
    // first guess, and `SwitchTransitionTest`'s full sweep (every pot config, every
    // flip phase, not just one) refuted it: at `blend-noon` (LEVEL/BLEND both near
    // max, the largest measured divergence, 0.66) the settled difference signal's
    // own per-sample step is comparable to the tone's own quiet step regardless of
    // fade speed, so a 5 ms fade landed the gated ratio at 1.00-1.004x — genuinely
    // over the bar, not a floor artefact (verified: a slower fade measurably lowers
    // it, a floor would not move). Swept 8/10/12 ms; 12 ms clears every cell with
    // real margin (worst 0.80x at blend-noon and mids-cut) while 10 ms leaves only
    // ~2% (0.98x). Still well inside item 14's own "~5-20 ms" spec and far too fast
    // to read as a fade-in under a footswitch stomp.
    static constexpr double kDistFadeSeconds = 0.012;

    void prepare(double sampleRate) noexcept
    {
        // ⚠ Guard the rate: a zero/negative would make `distStep` non-finite and the
        // ramp would never land ON an endpoint, so the bit-identical steady-state
        // branches below would stop being reachable — a silent loss of the property
        // this whole design rests on, not a crash.
        distStep = (sampleRate > 0.0) ? 1.0 / (kDistFadeSeconds * sampleRate) : 1.0;
        distMix = distTarget; // a rate change is not a footswitch press
    }

    // Snaps the fade to its target. Called before every render and at the top of
    // playback, which is what keeps a static render free of a head ramp
    // (`offline_render.cpp` does setParams() THEN reset(), in that order).
    void reset() noexcept { distMix = distTarget; }

    void setLevel(double x) noexcept
    {
        // x ∈ [0,1]. L = 0 → wiper at VD (min OD), L = 1 → wiper at OD input.
        knob = x;
        // Fall back to the compiled defaults unless the WHOLE set is ordered and
        // in range — a partially-valid set would silently produce a curve that is
        // not monotone, i.e. not a pot law at all (MasterOut::setMaster's guard,
        // which exists for the same reason).
        const bool ok = tb1 > 1.0e-9 && tb1 < tb2 && tb2 < tb3 && tb3 < 1.0
                        && tf1 > 0.0 && tf1 < tf2 && tf2 < tf3 && tf3 < 1.0;
        L = ok ? levelTaper(x, tb1, tf1, tb2, tf2, tb3, tf3)
               : levelTaper(x, kLevelTaperBreak1, kLevelTaperFrac1, kLevelTaperBreak2,
                            kLevelTaperFrac2, kLevelTaperBreak3, kLevelTaperFrac3);
    }

    // Capture fit (FitParams.h): re-applies the CURRENT knob position through the
    // new curve, so a taper refit doesn't leave a stale L behind.
    void setTaper(double b1, double f1, double b2, double f2, double b3, double f3) noexcept
    {
        tb1 = b1; tf1 = f1;
        tb2 = b2; tf2 = f2;
        tb3 = b3; tf3 = f3;
        setLevel(knob);
    }

    void setBlend(double x) noexcept
    {
        // x ∈ [0,1], B-taper = linear.
        // B = 0 → output = clean, B = 1 → output = leveled OD.
        blendKnob = x;
        // The wiper traverses Rp of a track whose total is Rl + Rp + Rh, so with
        // endLo = Rl/total and endHi = Rh/total the traversable span is k = 1-endLo-endHi:
        //   B_eff = endLo + x*k    (x=0 -> endLo, x=1 -> 1-endHi)
        B = endLo + x * (1.0 - endLo - endHi);
    }

    // ⚠⚠ These MUST equal FitParams' shipped values — `LevelBlendTest` Test 0(e) asserts
    // it exactly, for the s174 reason: the compiled defaults are read by `setLevel()`'s
    // invalid-set fallback and by the test oracle, and a FitParams edit that misses them
    // leaves those two consumers modelling a stage nothing runs, silently and passing.
    static constexpr double kBlendEndStop = 0.02418;
    static constexpr double kBlendEndStopClean = 0.0;

    // BLEND wiper end stop at the pin3 (OD) end, as a fraction of the whole track:
    // e = Rh/(Rp + Rh). 0 restores the pre-s181 ideal pot EXACTLY. See the block above.
    void setBlendEndStop(double e, double eClean = 0.0) noexcept
    {
        // Guard the range rather than trusting a fit: e >= 1 would invert the pot and a
        // negative one would make the bleed a subtraction, neither of which is a pot.
        endHi = (e > 0.0 && e < 0.5) ? e : 0.0;
        endLo = (eClean > 0.0 && eClean < 0.5) ? eClean : 0.0;
        setBlend(blendKnob);
    }

    void setDistEngage(bool engage) noexcept { distTarget = engage ? 1.0 : 0.0; }

    // Advance the footswitch crossfade by one sample. Deliberately SEPARATE from
    // process(): process() must stay pure and const because `cleanFraction()` calls
    // it twice with unit inputs to recover its own coefficients by superposition, and
    // a process() that advanced state would make that accessor corrupt the fade.
    inline void tickSmoothing() noexcept
    {
        if (! mna::differs(distMix, distTarget))
            return;
        // Land exactly ON the endpoint rather than approaching it — the two
        // bit-identical branches in process() are `<= 0.0` and `>= 1.0`, so an
        // asymptotic ramp would leave the shipped steady state permanently inside
        // the interpolating arm and silently break the no-re-baseline property.
        distMix = (distTarget > distMix) ? std::min(distTarget, distMix + distStep)
                                         : std::max(distTarget, distMix - distStep);
    }

    // Fraction of the OUTPUT that is clean-tap signal, in [0,1].
    //
    // ⭐ Derived by EVALUATING `process` itself with unit inputs rather than by re-deriving the
    // divider algebra.  `process` is linear in (cleanIn, odIn) — it is a weighted sum — so
    // superposition gives its two coefficients exactly, and this accessor therefore CANNOT drift
    // from what the stage actually does, including at the analytic endpoints and under
    // dist-disengage (which correctly reports 1.0, i.e. all clean).  Re-deriving it instead
    // would be the s113 trap (a shipped stage's closed form takes the STAGE's input, not the
    // knob) plus a second copy of the network to keep in sync.
    //
    // `OdToneRestore` reads this: it sits in the OD path, upstream of here, so how much cut its
    // 320 Hz notch must apply to land the COMPOSITE null on the pedal's depends entirely on how
    // much clean signal is about to be summed on top of it.  GATE AT measured that dependence
    // and showed it collapses onto this single scalar (many LEVEL/BLEND routes to the same value
    // agree to 0.03-0.05 dB), which is what makes one number sufficient here.
    double cleanFraction() const noexcept
    {
        // ⛔⛔ EVALUATED AT THE **ENGAGED** PATH (dm = 1.0), i.e. dist_engage IS DELIBERATELY
        // IGNORED HERE. It was evaluated at `distTarget` from s171 to s198, and that was the
        // whole of `SwitchTransitionTest`'s standing `distEngage @mids-boost (on)` failure —
        // measured, not argued (session 198, GATE BV):
        //
        //   `setDistEngage()` moves `distTarget` INSTANTLY, so `PedalChain::syncOdToneMix()`
        //   pushed a cf that jumped 0.02418 -> 1.0 in one sample into the two mix-keyed OD
        //   stages — an UNSMOOTHED coefficient jump landing at the flip sample while `distMix`
        //   is still 1.0 and the OD branch is therefore at FULL contribution. The fade below
        //   was never the problem: the transient lands ON the flip sample and is gone in ~8
        //   samples, where a too-fast fade would spread over all 576.
        //
        // ⭐⭐ AND THE OBVIOUS SUSPECT IS EXONERATED BY THE SAME MEASUREMENT. s175's GRUNT
        // precedent makes `OdToneRestore` the stage to reach for (there, fading only the
        // clipper would have left the notch stage's discontinuity wearing the switch's name).
        // Freezing each stage's cf across the flip separates them and it is NOT that stage:
        // freeze `OdToneRestore` alone 2.85x -> **2.85x**, freeze `OdMakeup` alone 2.85x ->
        // **0.58x**, freeze both -> 0.59x. ⇒ **s173's mix-keyed HF peak (5.6 kHz, Q 2.0) is
        // ~100 % of it.** ⛔ Do not re-open this as an `OdToneRestore` problem.
        //
        // ⭐⭐⭐ AND THE EXONERATION IS THE OPPOSITE OF "that stage barely does anything" — THE
        // STAGE THAT MOVES THE OUTPUT **33x MORE** IS THE ONE THAT IS NOT THE CARRIER. Driving
        // the same cf 0.02418 -> 1.0 on each stage alone moves the settled output rms by
        // **-5.121e-03 (OdToneRestore)** against **+1.570e-04 (OdMakeup)** — both live, so
        // neither freeze arm is a dead intervention, and the ranking INVERTS between the two
        // statistics. That is not a paradox, it is what the bar measures: a per-sample STEP is
        // a HIGH-FREQUENCY statistic (d/dn of a component scales with its frequency), so a few
        // dB on a Q-2 section at 5.6 kHz rings hard while several dB on a Q-16 section at
        // 323 Hz barely moves a sample-to-sample difference at all. ⇒ ⛔ never rank candidate
        // carriers for a click by how much they move the response.
        //
        // ⭐ WHY IGNORING THE FOOTSWITCH IS THE *CORRECT* READING, not a workaround: this
        // accessor exists to tell the OD-path stages how much clean signal the BLEND NETWORK
        // is about to sum on top of them. `dist_engage` is a MUTE of the whole OD branch, not
        // a change in that ratio — and `processAt(dm <= 0)` returns `cleanIn` EXACTLY, so
        // while the switch is disengaged the OD branch's tuning is discarded sample for
        // sample and cannot be heard at all. Re-keying it to 1.0 therefore bought nothing at
        // the settled end and cost a click at the only point where the branch IS audible: the
        // fade. ⇒ cf is now a pure function of (LEVEL, BLEND, end stops), which is also what
        // every analysis mirror (GATE AT/BM/BN) has always modelled it as.
        //
        // ⚠ SCOPE, verified by RENDER not by this argument: `base="clean"` captures render at
        // `--dist-engage 0`, so they DO see a different cf — and their output is bit-identical
        // regardless, because the OD branch they re-tune is discarded by the `dm <= 0` early
        // return. `LevelBlendTest` Test 10 asserts both halves.
        const double od = processAt(0.0, 1.0, distTarget);
        const double cl = processAt(1.0, 0.0, distTarget);
        const double sum = od + cl;
        return sum > 0.0 ? cl / sum : 1.0;
    }

    // Process one sample: return mixed output.
    // cleanIn = signal from IC1_A clean tap (VD-referenced AC voltage).
    // odIn    = signal from IC4_A Sallen-Key output (VD-referenced AC voltage).
    inline double process(double cleanIn, double odIn) const noexcept
    {
        return processAt(cleanIn, odIn, distMix);
    }

    // The stage evaluated at an EXPLICIT dist-engage mix, so the two endpoints are
    // reachable independently of where the fade currently sits — which is what
    // cleanFraction() needs (it must key OdToneRestore off the settled mix, not off
    // a mid-fade value that will be gone in a few ms).
    inline double processAt(double cleanIn, double odIn, double dm) const noexcept
    {
        // dist_engage fully DISENGAGED: 100% clean. Unchanged pre-crossfade path.
        if (dm <= 0.0)
            return cleanIn;
        const double engaged = engagedPath(cleanIn, odIn);
        // dist_engage fully ENGAGED: unchanged pre-crossfade path, bit-identical.
        if (dm >= 1.0)
            return engaged;
        // Mid-stomp only. Never reached by a static render.
        return (1.0 - dm) * cleanIn + dm * engaged;
    }

private:
    // The BLEND network proper — everything this stage did before the footswitch
    // crossfade existed, moved wholesale and otherwise untouched.
    inline double engagedPath(double cleanIn, double odIn) const noexcept
    {
        // LEVEL divider wiper voltage (loaded by BLEND pot).
        // Handle endpoints analytically to avoid division by zero.
        double vw;
        if (L <= 0.0)
        {
            vw = 0.0; // wiper at GND (VD)
        }
        else if (L >= 1.0)
        {
            vw = odIn; // wiper at OD input (no drop)
        }
        else
        {
            // `k` is the BLEND body's normalised CONDUCTANCE seen from the LEVEL wiper:
            // the body is Rp/k ohms, so k = 1 at the ideal pot and falls as the end stops
            // add track the wiper cannot reach. At k = 1 every term below is bit-identical
            // to the pre-s181 expression, which Test 8(a) asserts rather than assumes.
            const double k = 1.0 - endLo - endHi;
            const double invRup = 1.0 / (1.0 - L);
            const double invRdn = 1.0 / L;
            const double invTotal = invRup + invRdn + k;
            // Vw = (odIn/(1-L) + k*cleanIn) / (1/(1-L) + 1/L + k)
            vw = (odIn * invRup + cleanIn * k) / invTotal;
        }

        // BLEND wiper voltage = linear crossfade. Branch at the extremes instead of
        // relying on (1-B)*cleanIn / B*vw to reach zero — 0.0*NaN/Inf is NOT zero
        // under IEEE 754, so a non-finite sample on the side being "zeroed out"
        // (e.g. odIn destabilising while BLEND is fully clean) would otherwise leak
        // straight through the crossfade.
        if (B <= 0.0)
            return cleanIn;
        if (B >= 1.0)
            return vw;
        return (1.0 - B) * cleanIn + B * vw;
    }

    double L = 1.0; // LEVEL taper-mapped position [0,1] (default = max OD)
    double B = 0.0; // BLEND wiper position [0,1] AFTER the end stops (default = 100% clean)
    double blendKnob = 0.0;  // the raw knob, kept so setBlendEndStop() can re-apply it
    // BLEND pot end stops as fractions of the WHOLE track (s181, item 12). endHi is the
    // pin3/OD end and is what produces the LEVEL-min clean bleed; endLo is the pin1/clean
    // end and ships at 0 — see the block above for why it is exposed but not shipped.
    double endHi = kBlendEndStop, endLo = kBlendEndStopClean;
    // dist_engage footswitch: 1 = OD engaged (normal BLEND behaviour), 0 = forced
    // clean. `distMix` is where the crossfade (`kDistFadeSeconds`) currently is; `distTarget` is
    // where the switch says it should be.
    double distMix = 1.0, distTarget = 1.0;
    double distStep = 1.0; // 1/(fade samples); prepare() derives it from the rate
    // Capture-fit taper shape + the knob position it was applied to. Defaults are
    // the fitted s173 values, so a default-constructed LevelBlend matches the
    // shipped FitParams. ⚠ That sentence was FALSE from s173 to s174 — see the
    // kLevelTaper* block; keep the two sets in step or it silently goes stale
    // again, and only the fallback and the test oracle will notice.
    double tb1 = kLevelTaperBreak1, tf1 = kLevelTaperFrac1;
    double tb2 = kLevelTaperBreak2, tf2 = kLevelTaperFrac2;
    double tb3 = kLevelTaperBreak3, tf3 = kLevelTaperFrac3;
    double knob = 1.0;

    LevelBlend(const LevelBlend&) = delete;
    LevelBlend& operator=(const LevelBlend&) = delete;
};
