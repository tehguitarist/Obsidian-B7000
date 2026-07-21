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
// ⚠ NOMINAL — the template's starting point, NOT yet anchored to this pedal's
// bypass capture. Phase-7 calibration step 1 (calibration-and-gain-staging.md §1)
// replaces it with a measured value derived from `analysis/captures/bypass.wav`.
static constexpr double kInputRefNominal = 0.87;

// Output make-up applied after the chain, before the output trim. ⚠ NOMINAL.
// Phase-7 step 5 sets this by LEVEL-MATCHING renders to the captures; it may
// legitimately exceed 1.0 and must NOT be padded down for headroom
// (calibration-and-gain-staging.md §2 — output above 0 dBFS at high drive+volume
// is faithful behaviour, not a fault).
static constexpr double kOutputMakeupNominal = 0.9;
} // namespace GainStaging
