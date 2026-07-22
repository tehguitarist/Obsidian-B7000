#pragma once

#include <juce_audio_basics/juce_audio_basics.h>
#include <juce_audio_processors/juce_audio_processors.h>
#include <array>
#include <atomic>

#include "dsp/GainStaging.h"
#include "dsp/PedalDSP.h"

class ObsidianB7000AudioProcessor : public juce::AudioProcessor
{
public:
    ObsidianB7000AudioProcessor();
    ~ObsidianB7000AudioProcessor() override;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override;

    const juce::String getName() const override;

    bool acceptsMidi() const override;
    bool producesMidi() const override;
    bool isMidiEffect() const override;
    double getTailLengthSeconds() const override;

    int getNumPrograms() override;
    int getCurrentProgram() override;
    void setCurrentProgram(int index) override;
    const juce::String getProgramName(int index) override;
    void changeProgramName(int index, const juce::String& newName) override;

    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    juce::AudioParameterBool* getBypassParameter() const override;
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;

    juce::AudioProcessorValueTreeState apvts;
    static juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

    juce::AudioBuffer<double> scratch;
    juce::AudioParameterBool* bypassParam;
    juce::SmoothedValue<float> bypassMix;
    juce::SmoothedValue<float> inputGain, outputGain;

    // Block-rate smoothing for the 8 continuous pots. PedalChain::applyParams()
    // is deliberately called once per block, not per sample (dsp.md/PedalChain.h:
    // the MNA-based stages — Baxandall/MidBand — only re-invert their matrix on a
    // dirty flag, and doing that per sample would be a real CPU regression). So a
    // fast knob sweep (or automation) can still jump the raw APVTS value a lot
    // between one block and the next, and every stage recomputes its coefficients
    // from whatever value it's handed with no interpolation — an audible zipper
    // click on a quick turn, worse the bigger the stage's gain/effect range
    // (DRIVE's 4x-78x is the most audible). Smoothing the KNOB value itself
    // (not per-sample, just via skip(numSamples) once per block, same pattern as
    // bypassMix/inputGain) bounds how far it can move in one block regardless of
    // how fast it's turned, without changing the "recompute once per block" cost
    // structure. Switch params (attack/grunt/mid-freq/bypass) are deliberately
    // NOT smoothed here — they're discrete topology swaps, not a smoothing gap;
    // their own click-on-switch issue is a separate, already-flagged problem
    // (circuit.md/TrebleAttack.h "glitch-free crossfade", deferred).
    juce::SmoothedValue<float> smMaster, smBlend, smLevel, smDrive;
    juce::SmoothedValue<float> smLo, smLoMid, smHiMid, smHi;

    // Bypass dry-path delay compensation (dsp.md "Dry/wet phase alignment across
    // the oversampled region") — same fix as PedalDSP's internal BLEND clean-tap
    // delay, applied at the plugin I/O so the bypass crossfade doesn't comb-filter
    // during its transition at nonzero OS latency.
    std::array<juce::dsp::DelayLine<float, juce::dsp::DelayLineInterpolationTypes::None>, 2> bypassDelay;
    juce::AudioBuffer<float> dryDelayedBuffer;

    // Per-block ramps for inputGain/outputGain/bypassMix. Filled ONCE per block
    // (not once per channel) by actually stepping the SmoothedValue members —
    // see processBlock: a per-channel *copy* of a SmoothedValue must never be the
    // thing that calls getNextValue(), because the copy's advancement is thrown
    // away at the end of the channel loop and the member's own currentValue never
    // moves. With a stale currentValue, the next block's setTargetValue() (a
    // no-op whenever the target hasn't changed) leaves the ramp re-starting from
    // the same frozen point every block instead of continuing — an audible click
    // train once bypassMix's target ever differs from 0, i.e. from the first
    // bypass press onward.
    std::vector<float> inGainRamp, outGainRamp, bypassMixRamp;

    std::atomic<float> inputLevel { 0.0f };
    std::atomic<float> outputLevel { 0.0f };
    std::atomic<bool> bypassed { false };

    float getInputLevel(int /*ch*/) const { return inputLevel.load(); }
    float getOutputLevel(int /*ch*/) const { return outputLevel.load(); }

    // Shared with analysis/offline_render.cpp via dsp/GainStaging.h — the fit
    // that sets these must not be able to land in only one of the two.
    static constexpr float kInputRef = (float) GainStaging::kInputRefNominal;
    static constexpr float kOutputMakeup = (float) GainStaging::kOutputMakeupNominal;

private:
    // Build the per-block chain param set. The 8 continuous pots come in
    // pre-smoothed (already knob-space, pre-EQ-inversion); switches are read
    // directly from the cached APVTS pointers.
    PedalChain::Params readParams(float master, float blend, float level, float drive,
                                   float lo, float loMid, float hiMid, float hi) const;

    std::array<PedalDSP, 2> dsp;

    // Cached parameter pointers (avoid string lookups on the audio thread).
    std::atomic<float>* pMaster = nullptr;
    std::atomic<float>* pBlend = nullptr;
    std::atomic<float>* pLevel = nullptr;
    std::atomic<float>* pDrive = nullptr;
    std::atomic<float>* pLo = nullptr;
    std::atomic<float>* pLoMid = nullptr;
    std::atomic<float>* pHiMid = nullptr;
    std::atomic<float>* pHi = nullptr;
    std::atomic<float>* pAttack = nullptr;
    std::atomic<float>* pGrunt = nullptr;
    std::atomic<float>* pLoMidFreq = nullptr;
    std::atomic<float>* pHiMidFreq = nullptr;
    std::atomic<float>* pDistEngage = nullptr;
    std::atomic<float>* pInputTrim = nullptr;
    std::atomic<float>* pOutputTrim = nullptr;
    std::atomic<float>* pOversampling = nullptr;
    std::atomic<float>* pRenderOversampling = nullptr;

    int reportedLatency = -1; // last value pushed to the host via setLatencySamples

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ObsidianB7000AudioProcessor)
};
