# Architecture Rules (generic pedal plugin)

## Threading

- DSP on the **audio thread**; UI on the **message thread**.
- Cross-thread only via `std::atomic` — no locks/mutexes/allocations on the audio thread.
- Meter levels: `std::atomic<float>` written by audio thread, read by a UI `Timer`.
- Bypass: `std::atomic<bool>` (but the UI should read the APVTS `bypass` parameter directly for
  immediate visual response — see UI note below).
- Parameter changes via `AudioProcessorValueTreeState` (APVTS) with **smoothed** values.

## Plugin structure (template)

```
PedalAudioProcessor : AudioProcessor
  AudioProcessorValueTreeState apvts
  std::array<PedalDSP, 2> dsp          // one inner WDF chain per channel
  juce::AudioBuffer<double> scratch    // double work buffer (WDF is double)
  SmoothedValue<float> inputGain, outputGain, bypassMix
  std::atomic<float>* cached param pointers (avoid string lookups on audio thread)
  std::atomic<float> inputLevelL/R, outputLevelL/R
  std::atomic<bool>  bypassed
  static constexpr float kInputRef     = 0.87f; // volts per full-scale — template starting point;
                                                 // measure YOUR rig and replace (calibration doc §1)
  static constexpr float kOutputMakeup // ~0.9 (calibration doc §2)
```

`PedalDSP` is the per-channel inner chain (input network → gain/clip stage (oversampled) → tone →
recovery stage). Volume/trim/metering live in the processor (plain gains + level reads), not in the
WDF tree.

### Multiple full gain stages in series ("dual"/"stacked" pedals)

If the pedal is actually two or more complete, independently-bypassable gain circuits chained
together (not just stereo L/R), instantiate one `PedalDSP`-style object per **stage**, fed into each
other in series, each with its own bypass crossfade — not stereo channels of one circuit. The order
they're wired in `processBlock` must be the **verified real signal order** (see `circuit.md` —
trace it from the hardware/schematic, never assume it from physical layout or numbering). A fixed
per-stage build variant (e.g. one stage has a permanent factory mod the other doesn't) is a
constructor-time flag on that stage's class, not a parameter — see `dsp.md` "Fixed (non-runtime)
circuit variants".

If you discover **after shipping parameters** that your assumed signal order (or any other
assumption baked into IDs/labels) was wrong, fix the runtime *behaviour* (which object processes
first) without renaming the APVTS parameter IDs or reordering member declarations that match them —
existing saved sessions reference parameters by ID, and renaming/reordering breaks recall silently.
Keep the old IDs/order for compatibility and document the now-stale name↔order mismatch clearly in
comments and project notes so a future reader isn't misled by the names.

## Parameters (APVTS)

Typical set — adapt to the pedal. Use `0..1` `AudioParameterFloat` for pot controls and apply the
taper in DSP (keeps host automation linear and the taper in one place):

| ID | Type | Notes |
|----|------|-------|
| pot controls (`gain`, `tone`, `volume`, …) | `AudioParameterFloat` 0..1 | taper applied in DSP |
| mode switch | `AudioParameterChoice` | precomputed topologies |
| `input_trim` / `output_trim` | `AudioParameterFloat` dB | distinct from pedal controls |
| `trim_link` | `AudioParameterBool` default true | see "Input/output trim link" below |
| `oversampling` | `AudioParameterChoice` 1×/2×/4×/8× | realtime factor |
| `render_oversampling` | `AudioParameterChoice` | offline-bounce factor (see below) |
| `bypass` | `AudioParameterBool` | APVTS supports bool via this type |
| `hq` (optional) | `AudioParameterBool` default true | accurate vs fast diode solve — add ONLY if `FeatureProfile` shows a real CPU/accuracy lever (`dsp.md` "HQ / Eco mode") |

## processBlock structure

```
1. Pick OS factor: isNonRealtime() ? render_oversampling : oversampling. Reinit if changed.
2. Read smoothed params; apply tapers to pot values.
3. Update WDF node values (defer impedance propagation for coupled controls).
4. Per channel:
   a. input trim -> wet (DAW domain); take dry copy for bypass; update INPUT meter (DAW domain)
   b. work = wet * kInputRef          // -> real volts (calibration doc §1)
   c. run WDF chain (input -> oversampled clip -> tone -> recovery)
   d. optional silence gate (zero the block if all |samples| are sub-threshold)
   e. work * outputGain, outputGain = kOutputMakeup * volumeGain * dbToGain(outTrim) / kInputRef
   f. crossfade against dry copy for bypass; update OUTPUT meter (DAW domain)
```
Keep meters + bypass dry path in DAW domain; only the WDF chain sees `kInputRef` volts.

## Oversampling: realtime vs render

Expose two choice params. In `processBlock`, `isNonRealtime()` returns true during offline bounce
(Logic and most DAWs), so the render factor applies automatically with no extra UI action:
```cpp
const int wantFactor = isNonRealtime()
    ? (pRenderOs != nullptr ? (int)pRenderOs->load() : 3)   // default 8x offline
    : (int)pOversampling->load();
```

## Bypass

- True bypass: dry input routed to output, DSP skipped when bypassed.
- ~5 ms crossfade (`SmoothedValue bypassMix`) on transitions to avoid clicks.
- On DAW recall, the UI must reflect the restored `bypass` parameter — read APVTS, not a stale flag.
- **The dry copy used for this crossfade must be delay-compensated to the wet chain's current
  oversampling latency before summing** — see `dsp.md` "Dry/wet phase alignment across the
  oversampled region". The dry copy is taken pre-DSP (zero latency); the wet chain includes the
  oversampled nonlinear stage (nonzero latency), so an uncompensated crossfade phase-cancels during
  the transition. Same fix, same rule as the BLEND control (circuit.md) — one shared delay line
  sized off `getLatencyInSamples()` can serve both summing points.

## Input/output trim link

`trim_link` (bottom-bar "TRIM LINK" button, `"trim_link"` `AudioParameterBool`, default **true**,
see `ui.md`) lets a player raise input trim to push the circuit harder without the overall loudness
jumping: while linked, nudging one trim by `Δ dB` nudges the *other* trim by `−Δ dB`, clamped to its
own `[-18, +18]` range (the trim range as of the trim-lock feature — was `[-12, +12]`). This is a
UI/parameter convenience only — it does not change `processBlock`'s gain-staging math (input trim
still scales `wet` pre-`kInputRef`, output trim still folds into `outputGain` exactly as before); it
just keeps the two APVTS values moving in opposite lockstep.

**Delta-linked, not listener-linked.** Implemented editor-side, hooked into each trim knob's
existing `onValueChange` (which already drives the value-label text) rather than an
`AudioProcessorValueTreeState::Listener::parameterChanged` override — that keeps the mirror tied
to the exact slider `getValue()` the user is dragging, with no cross-thread dispatch to reason
about. A `mirrorTrim(bool sourceIsInput)` method mirrors the **delta** (`newValue − lastValue`),
applied to the *other* knob's **last** value — not `−source` — so the pair's existing offset is
preserved and enabling the lock never snaps a knob:

```cpp
void Editor::mirrorTrim(bool sourceIsInput)
{
    Slider& src = sourceIsInput ? inputTrim : outputTrim;
    double& srcLast = sourceIsInput ? lastInputTrim : lastOutputTrim;
    const double dstLast = sourceIsInput ? lastOutputTrim : lastInputTrim;

    // Cache unconditionally, even when the lock is off or this is the echoed write — otherwise
    // the first move after enabling the lock measures against a stale reference and jumps.
    const double delta = src.getValue() - srcLast;
    srcLast = src.getValue();

    if (trimLinkBusy || ! trimLockButton.getToggleState() || delta == 0.0)
        return;

    const auto target = (float) jlimit(-kTrimRange, kTrimRange, dstLast - delta);
    if (auto* param = apvts.getParameter(sourceIsInput ? "output_trim" : "input_trim"))
    {
        const ScopedValueSetter<bool> guard(trimLinkBusy, true);   // breaks the A->B->A bounce
        param->beginChangeGesture();
        param->setValueNotifyingHost(param->convertTo0to1(target));
        param->endChangeGesture();
    }
}
```

Clamping at the compensating side's range edge means the two trims can drift out of exact mirror
symmetry at the extremes — that's expected (a real compensating pair does the same once one side
hits its stop), not a bug to chase.

## prepareToPlay responsibilities

- `.prepare(sampleRate)` on every capacitor in every stage (missing this = silence).
- `oversampler.initProcessing(samplesPerBlock)`.
- Reset smoothed values to current APVTS values (no first-block ramp artefact).
- Reset bypass crossfade state.
- `setLatencySamples()` from the oversampler's reported latency.

## State save/restore

- Full state via `apvts.state` (standard XML serialise). All controls + OS + bypass round-trip.
- Optionally persist UI scale: per-session in `apvts.state` property, cross-session default in
  `ApplicationProperties` (see ui.md).
