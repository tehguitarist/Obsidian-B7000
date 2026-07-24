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
static constexpr double kInputRefNominal = 3.377;

// Output make-up applied after the chain, before the output trim.
// ** SESSION-17 CALIBRATED — 0.9 -> 3.684 (+11.33 dB). ** Set by level-matching a
// CLEAN render at master=1.0 to master-1700_base-clean (master_taper_makeup.log):
// R_cap -16.62 dBFS vs R_mdl(makeup=1) -27.94 dBFS. kInputRef cancels in this clean
// path, so this is independent of the kInputRef change above. calibration §2: makeup
// MAY exceed 1.0 and must NOT be padded down for headroom (output above 0 dBFS at
// high drive+volume is faithful behaviour, not a fault).
static constexpr double kOutputMakeupNominal = 3.684;
} // namespace GainStaging
