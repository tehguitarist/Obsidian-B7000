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
//   • Value 0.87 is the anchor the whole test signal was DESIGNED around
//     (gen_test_signal.py: "0 dBFS ~ 0.87 V peak"; the -36..-6 dBFS sweep bank is
//     labelled soft-to-hot bass playing). Bypass's unity round-trip confirms that
//     design is internally consistent. Adopted as the anchor (user decision
//     2026-07-22) rather than an independent measurement, which audio-only
//     captures cannot provide. K only affects clip-onset vs real-instrument
//     volts — never the clean/linear level (that's makeup, §2 / step 5).
static constexpr double kInputRefNominal = 0.87;

// Output make-up applied after the chain, before the output trim. ⚠ NOMINAL.
// Phase-7 step 5 sets this by LEVEL-MATCHING renders to the captures; it may
// legitimately exceed 1.0 and must NOT be padded down for headroom
// (calibration-and-gain-staging.md §2 — output above 0 dBFS at high drive+volume
// is faithful behaviour, not a fault).
static constexpr double kOutputMakeupNominal = 0.9;
} // namespace GainStaging
