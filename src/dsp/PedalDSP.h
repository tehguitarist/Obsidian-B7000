#pragma once

#include <juce_dsp/juce_dsp.h>
#include <array>
#include <memory>
#include <vector>

#include "PedalChain.h"

// =============================================================================
// PedalDSP — per-channel DSP wrapper: PedalChain + oversampling + delay comp
// =============================================================================
// Owns one full mono PedalChain and wraps its NONLINEAR REGION (JFET → … → SK,
// PedalChain::runOdSample) in a JUCE oversampler. Everything before it
// (InputBuffer) and after it (LevelBlend, EQ, MasterOut) runs at base rate.
//
// **Oversampled region + clean-tap delay (dsp.md "Oversampling" + "Dry/wet phase
// alignment").** The clean BLEND tap splits at the InputBuffer output, BEFORE the
// oversampled region, so it must be delayed by the oversampler's FIR latency
// (reported at base rate) before it meets the OD path at LevelBlend — otherwise
// the crossfade comb-filters. A base-rate integer DelayLine on the clean tap does
// this; its length tracks the active factor's latency and is updated in lockstep
// with any OS-factor change (one-block gap, same policy as the OS reinit).
//
// **Runtime factor switching.** One `juce::dsp::Oversampling<double>` per factor
// (2×/4×/8×) is created and `initProcessing`'d up front, so switching between them
// is allocation-free (RT-safe). 1× has no oversampler — the OD region runs
// per-sample at base rate. On a factor change, only the OD region is re-prepared
// at the new rate (PedalChain::prepareOd); base-rate stages keep their state.
//
// The volume/trim/kInputRef/metering DAW-domain work stays in the processor
// (architecture.md); PedalDSP works purely in the chain's internal-volts domain.
// =============================================================================
class PedalDSP
{
public:
    PedalDSP() = default;
    ~PedalDSP() = default;

    // maxOrder 3 → factors 1×/2×/4×/8× available (order = log2 factor).
    void prepare(double sampleRate, int samplesPerBlock)
    {
        baseRate = sampleRate;
        maxBlock = juce::jmax(1, samplesPerBlock);

        chain.prepareBase(sampleRate);

        // FIR half-band (linear phase → integer latency, dsp.md), max quality.
        using OS = juce::dsp::Oversampling<double>;
        for (int order = 1; order <= kMaxOrder; ++order)
        {
            os[(size_t) order] = std::make_unique<OS>(
                1, (size_t) order, OS::filterHalfBandFIREquiripple, true);
            os[(size_t) order]->initProcessing((size_t) maxBlock);
            os[(size_t) order]->reset();
        }

        odIn.assign((size_t) maxBlock, 0.0);
        odDown.assign((size_t) maxBlock, 0.0);
        cleanDelayed.assign((size_t) maxBlock, 0.0);

        cleanDelay.prepare({sampleRate, (juce::uint32) maxBlock, 1});
        cleanDelay.setMaximumDelayInSamples(maxCleanDelay());

        curOrder = -1;
        setFactorOrder(defaultOrder); // prepares OD region + delay length
    }

    void reset()
    {
        chain.reset();
        cleanDelay.reset();
        for (int order = 1; order <= kMaxOrder; ++order)
            if (os[(size_t) order] != nullptr)
                os[(size_t) order]->reset();
    }

    void setParams(const PedalChain::Params& p) { chain.applyParams(p); }

    // Choose the oversampling factor for this block (order = log2 factor, 0..3).
    // Cheap when unchanged; re-prepares the OD region + delay length on a change.
    void setFactorOrder(int order)
    {
        order = juce::jlimit(0, kMaxOrder, order);
        if (order == curOrder)
            return;
        curOrder = order;

        const double osRate = baseRate * (double) (1 << order);
        chain.prepareOd(osRate);

        latencySamples = (order == 0 || os[(size_t) order] == nullptr)
                             ? 0
                             : (int) std::lround(os[(size_t) order]->getLatencyInSamples());
        cleanDelay.setDelay((float) latencySamples);
        cleanDelay.reset();
    }

    int getLatencySamples() const noexcept { return latencySamples; }

    // Process a block in place (chain-internal volts).
    void processBlock(double* data, int numSamples) noexcept
    {
        jassert(numSamples <= maxBlock);

        // 1. Base-rate InputBuffer → OD input + delay-compensated clean tap.
        for (int n = 0; n < numSamples; ++n)
        {
            const double buf = chain.runInputBuffer(data[n]);
            odIn[(size_t) n] = buf;
            cleanDelay.pushSample(0, buf);
            cleanDelayed[(size_t) n] = cleanDelay.popSample(0, (float) latencySamples, true);
        }

        // 2. Oversampled region: JFET → … → SK, per OS-sample.
        if (curOrder == 0)
        {
            for (int n = 0; n < numSamples; ++n)
                odDown[(size_t) n] = chain.runOdSample(odIn[(size_t) n]);
        }
        else
        {
            auto& osr = *os[(size_t) curOrder];
            double* inPtr = odIn.data();
            juce::dsp::AudioBlock<double> inBlock(&inPtr, 1, (size_t) numSamples);
            auto osBlock = osr.processSamplesUp(inBlock);

            double* s = osBlock.getChannelPointer(0);
            const size_t osN = osBlock.getNumSamples();
            for (size_t i = 0; i < osN; ++i)
                s[i] = chain.runOdSample(s[i]);

            double* outPtr = odDown.data();
            juce::dsp::AudioBlock<double> outBlock(&outPtr, 1, (size_t) numSamples);
            osr.processSamplesDown(outBlock);
        }

        // 3. Base-rate LevelBlend crossfade → EQ → MasterOut.
        for (int n = 0; n < numSamples; ++n)
            data[n] = chain.processPostBlend(cleanDelayed[(size_t) n], odDown[(size_t) n]);
    }

private:
    static constexpr int kMaxOrder = 3;    // up to 8×
    static constexpr int defaultOrder = 1; // 2× default (matches APVTS default)

    int maxCleanDelay() const noexcept
    {
        // Largest FIR latency across the prepared factors (order kMaxOrder).
        int m = 0;
        for (int order = 1; order <= kMaxOrder; ++order)
            if (os[(size_t) order] != nullptr)
                m = juce::jmax(m, (int) std::lround(os[(size_t) order]->getLatencyInSamples()));
        return juce::jmax(1, m);
    }

    PedalChain chain;

    std::array<std::unique_ptr<juce::dsp::Oversampling<double>>, kMaxOrder + 1> os;
    juce::dsp::DelayLine<double, juce::dsp::DelayLineInterpolationTypes::None> cleanDelay;

    std::vector<double> odIn, odDown, cleanDelayed;

    double baseRate = 48000.0;
    int maxBlock = 512;
    int curOrder = -1;
    int latencySamples = 0;

    JUCE_DECLARE_NON_COPYABLE(PedalDSP)
};
