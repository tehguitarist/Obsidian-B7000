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

    // Bypass dry-path delay compensation (dsp.md "Dry/wet phase alignment across
    // the oversampled region") — same fix as PedalDSP's internal BLEND clean-tap
    // delay, applied at the plugin I/O so the bypass crossfade doesn't comb-filter
    // during its transition at nonzero OS latency.
    std::array<juce::dsp::DelayLine<float, juce::dsp::DelayLineInterpolationTypes::None>, 2> bypassDelay;
    juce::AudioBuffer<float> dryDelayedBuffer;

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
    // Build the per-block chain param set from the cached APVTS pointers.
    PedalChain::Params readParams() const;

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
