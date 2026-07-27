#pragma once

// =============================================================================
// GainStaging — the two DAW-domain calibration scalars, shared by the plugin
// and by OfflineRender
// =============================================================================
// `kInputRef` (volts per full scale) and `kOutputMakeup` are deliberately NOT in
// FitParams (see FitParams.h "Scope boundary"): they are processor-domain, not
// chain-domain, and calibration §1 depends on kInputRef cancelling through the
// linear path. But they ARE the two numbers Phase-7 calibration exists to
// measure, and they are consumed in two places — `PluginProcessor::processBlock`
// and `analysis/offline_render.cpp`, which must mirror it exactly. Two copies of
// a number that a fit is about to change is precisely the setup where the fit
// gets applied to one and not the other, and the plugin then quietly sounds
// different from everything that was measured.
//
// So they live here, once, JUCE-free. OfflineRender can still override either at
// runtime (`--input-ref` / `--output-makeup`) — that is how a candidate value is
// swept — but the DEFAULT both sides start from is this file, and committing a
// fitted value means editing exactly one line.
// =============================================================================
namespace GainStaging
{
// Volts (real, at the pedal's input jack) per 1.0 full-scale sample.
// ✅ ANCHORED — Phase-7 calibration step 1 COMPLETE (2026-07-22,
// calibration-and-gain-staging.md §1). Findings:
//   • `analysis/captures/bypass.wav`'s cal_1k tone returns at -0.012 dB vs the
//     test signal (linear 0.9987): the reamp rig is UNITY round-trip, so the
//     capture domain == the DAW-float domain 1:1. The level/makeup reference
//     frame is therefore clean.
//   • With audio-only captures (no scope / no interface send-level measurement),
//     kInputRef is DEGENERATE with the clip ceiling: scaling K and inversely
//     scaling the clip threshold gives bit-identical output. Proven directly —
//     the ref-clean (DIST-off, pure-linear) render sits -3.894 dB under the
//     capture at EVERY level step -36..-3 dBFS with std = 0.000, i.e. K cancels
//     exactly in the linear path. So K cannot be *measured* here; it is *set* to
//     a physically-realistic bass-input voltage and the clip ceiling (step 2) is
//     fit relative to it.
//   • Value 0.87 was the interim anchor the test signal was DESIGNED around
//     (gen_test_signal.py: "0 dBFS ~ 0.87 V peak"). It was adopted (user decision
//     2026-07-22) because K is degenerate with the clip ceiling under audio-only
//     captures and cannot be independently measured.
//
// ** SESSION-17 UPDATE — kInputRef 0.87 -> 3.377 (family fit). ** The degeneracy
// above is exactly why 0.87 was never physical on its own: at 0.87, matching the
// captured harmonic ramp forced the clip ceiling to ~1.3 V/side, far below the
// ~7 V R19-dropped rail. Session 17 broke the degeneracy by fitting kInputRef
// JOINTLY with clipSatLo/clipSatHi/clipA0/clipK and judging PHYSICALITY on the
// whole family (both the implied input volts AND the clipSat volts must be sane
// — handover §3v). The family optimum is kInputRef 3.377 V/FS (1.69 V peak at the
// -6 dBFS 'hot bass' rung, in the hot-active 1-2 V range) with clipSat sum 4.94 V
// (near the rail) — both physical. It supersedes 0.87. NOTE: this changes only the
// nonlinear operating point / OD-vs-clean blend balance; the clean/linear LEVEL is
// unchanged because K cancels through the linear path (proven std=0.000) and the
// makeup below is recalibrated in lockstep (net outputGain = makeup/K ~= 1.09).
// ** SESSION-44 UPDATE — kInputRef 3.377 -> 1.2596 (A5, Phase 9 step 2). SUPERSEDES the above. **
// The session-17 reasoning was sound in METHOD (judge the family, never half a degenerate pair)
// but rested on two numbers that have since been shown false:
//   (1) THE 3.377 WAS NEVER PHYSICAL. Session 41 measured IC5_B's fixed -2.2x, which is upstream
//       of every EQ band and always in circuit: at 3.377 the -3 dBFS rung needs 5.260 V of swing
//       where the 9 V supply (-> 8.65 V, VD 4.325) allows +/-4.325 V. The pedal reads 0.0000 % THD
//       at that rung; the model breaks into 22.9 % at it. The bound is <= 1.509 V/FS
//       (analysis/clean_headroom_bound.py) and it is arithmetic, not a preference.
//   (2) THE "~7 V RAIL" IT WAS JUDGED AGAINST WAS NEVER COMPUTED. The R19-dropped CD4049 supply
//       is a fixed point VDD = 8.65 - I_DD(VDD)*R19, and solving it (session 42,
//       analysis/clipper_rail_selfconsistent.py) gives 5.636 V, not ~7.
// AND THE OD CAPTURES NEVER OBJECTED. Session 43 re-ran session 17's own protocol on today's model
// and K went to 5.972 against a bound of 6.0 — i.e. the harmonic objective does NOT identify K at
// all; it runs to whatever ceiling the box provides, so 3.377 was only ever where that run's box
// and starts happened to stop. The clean path is therefore not a competing constraint but the
// MISSING EQUATION. Re-fitting the whole family with K fenced to the clean bound (session 44,
// analysis/fit_logs/step7_a5_sq2.log) gives K = 1.2596 INTERIOR (0.63 V peak at the -6 dBFS rung,
// a normal passive-bass level) at cost 34.1 vs the shipped family's 649.6 on the same objective,
// with every step-4 acceptance check green and NO parameter resting on a bound.
// ⚠ K IS UPSTREAM OF EVERY NONLINEARITY, so this invalidates any OD number measured before it —
// the 63-capture matrix was re-baselined in the same session. The clean/linear LEVEL is unaffected
// (K cancels through the linear path, proven std = 0.000), so kOutputMakeup below is unchanged.
static constexpr double kInputRefNominal = 1.2596;

// Output make-up applied after the chain, before the output trim.
// ** SESSION-17 CALIBRATED — 0.9 -> 3.684 (+11.33 dB). ** Set by level-matching a
// CLEAN render at master=1.0 to master-1700_base-clean (master_taper_makeup.log):
// R_cap -16.62 dBFS vs R_mdl(makeup=1) -27.94 dBFS. kInputRef cancels in this clean
// path, so this is independent of the kInputRef change above. calibration §2: makeup
// MAY exceed 1.0 and must NOT be padded down for headroom (output above 0 dBFS at
// high drive+volume is faithful behaviour, not a fault).
//
// ** SESSION-41 RE-CALIBRATED — 3.684 -> 2.599 (+11.33 dB -> +8.30 dB). ** The session-17 value
// was 3.03 dB HOT, i.e. the shipped plugin has been 3 dB louder than the pedal at matched settings
// this whole time. Invisible to every Phase-9 grade by construction: `fr_at_bands` gain-matches
// each capture before differencing, so the entire matrix measures SHAPE and absolute level is a
// separate axis (§ "Deltas are SHAPE, not loudness"). Two independent causes, both staleness:
//   • 1.58 dB — `master-1700_gain-n12_base-clean.wav`, the single capture this constant is
//     level-matched against, was a BAD TAKE at session-17 time; session 24 re-recorded it
//     (sweep_clean RMS -16.62 -> -18.20 dBFS) and nothing re-ran the calibration.
//   • 1.44 dB — the clean path itself has moved since: trebleWiperR (s25), the mid cap table +
//     midWiperR + midCapRatio (s26/27), c21R (s28). Every one of those changes the clean chain's
//     broadband gain, and the makeup that level-matches it was never re-derived.
// Confirmed two ways that agree to 0.01 dB: master_taper_makeup.py's sweep_clean RMS match
// (3.684 -> 2.5987) and a direct model-vs-pedal peak comparison on the 1 kHz `lvl_` ladder
// (model +3.016 dB hot at lvl_-12, where the clean path is still linear).
// ⚠ This is a post-chain scalar (outputGain = makeup/kInputRef), so it moves NO nonlinear
// operating point and invalidates no OD fit. It DOES shift the idle floor — recheck the VU
// idle-noise gate (backlog C1) against it.
static constexpr double kOutputMakeupNominal = 2.599;
} // namespace GainStaging
