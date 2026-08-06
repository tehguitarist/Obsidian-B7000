#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "dsp/PedalDSP.h"

#include <utility>
#include <vector>

namespace
{
// Factory presets transcribed from https://www.guitarchalk.com/darkglass-microtubes-b7k-ultra-v2-settings/
// (0-10 knob readings -> normalised 0..1 pot position; "Grunt: None" has no
// off position on this switch, so it maps to Cut, the minimum-bass setting).
// Every id here must match a real apvts parameter ID (PluginProcessor::createParameterLayout).
struct FactoryPreset
{
    const char* name;
    std::vector<std::pair<const char*, float>> values;
};

const std::array<FactoryPreset, 5> kFactoryPresets { {
    { "Modern",
      { { "master", 0.6f }, { "blend", 0.7f }, { "level", 0.6f }, { "drive", 0.7f },
        { "lo", 0.6f }, { "lo_mid", 0.7f }, { "hi_mid", 0.8f }, { "hi", 0.7f },
        { "attack", 1.0f }, { "grunt", 2.0f }, { "lo_mid_freq", 1.0f }, { "hi_mid_freq", 1.0f },
        { "bypass", 0.0f }, { "dist_engage", 1.0f }, { "trim_link", 1.0f }, { "hq", 1.0f },
        { "input_trim", 0.0f }, { "output_trim", 0.0f },
        { "oversampling", 1.0f }, { "render_oversampling", 3.0f } } },
    { "Vintage",
      { { "master", 0.6f }, { "blend", 0.6f }, { "level", 0.5f }, { "drive", 0.5f },
        { "lo", 0.7f }, { "lo_mid", 0.6f }, { "hi_mid", 0.4f }, { "hi", 0.3f },
        { "attack", 0.0f }, { "grunt", 0.0f }, { "lo_mid_freq", 0.0f }, { "hi_mid_freq", 2.0f },
        { "bypass", 0.0f }, { "dist_engage", 1.0f }, { "trim_link", 1.0f }, { "hq", 1.0f },
        { "input_trim", 0.0f }, { "output_trim", 0.0f },
        { "oversampling", 1.0f }, { "render_oversampling", 3.0f } } },
    { "Slap",
      { { "master", 0.7f }, { "blend", 0.5f }, { "level", 0.7f }, { "drive", 0.3f },
        { "lo", 0.8f }, { "lo_mid", 0.3f }, { "hi_mid", 0.4f }, { "hi", 0.8f },
        { "attack", 1.0f }, { "grunt", 1.0f }, { "lo_mid_freq", 1.0f }, { "hi_mid_freq", 0.0f },
        { "bypass", 0.0f }, { "dist_engage", 1.0f }, { "trim_link", 1.0f }, { "hq", 1.0f },
        { "input_trim", 0.0f }, { "output_trim", 0.0f },
        { "oversampling", 1.0f }, { "render_oversampling", 3.0f } } },
    { "Doom",
      { { "master", 0.5f }, { "blend", 0.9f }, { "level", 0.8f }, { "drive", 0.9f },
        { "lo", 0.9f }, { "lo_mid", 0.4f }, { "hi_mid", 0.3f }, { "hi", 0.2f },
        { "attack", 0.0f }, { "grunt", 0.0f }, { "lo_mid_freq", 0.0f }, { "hi_mid_freq", 0.0f },
        { "bypass", 0.0f }, { "dist_engage", 1.0f }, { "trim_link", 1.0f }, { "hq", 1.0f },
        { "input_trim", 0.0f }, { "output_trim", 0.0f },
        { "oversampling", 1.0f }, { "render_oversampling", 3.0f } } },
    { "Clean",
      { { "master", 0.7f }, { "blend", 0.3f }, { "level", 0.8f }, { "drive", 0.2f },
        { "lo", 0.6f }, { "lo_mid", 0.5f }, { "hi_mid", 0.6f }, { "hi", 0.6f },
        { "attack", 0.0f }, { "grunt", 1.0f }, { "lo_mid_freq", 1.0f }, { "hi_mid_freq", 2.0f },
        { "bypass", 0.0f }, { "dist_engage", 1.0f }, { "trim_link", 1.0f }, { "hq", 1.0f },
        { "input_trim", 0.0f }, { "output_trim", 0.0f },
        { "oversampling", 1.0f }, { "render_oversampling", 3.0f } } },
} };
} // namespace

ObsidianB7000AudioProcessor::ObsidianB7000AudioProcessor()
    : AudioProcessor(BusesProperties()
                        .withInput("Input", juce::AudioChannelSet::stereo(), true)
                        .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, juce::Identifier("PARAMETERS"), createParameterLayout())
{
    bypassParam = static_cast<juce::AudioParameterBool*>(apvts.getParameter("bypass"));

    pMaster = apvts.getRawParameterValue("master");
    pBlend = apvts.getRawParameterValue("blend");
    pLevel = apvts.getRawParameterValue("level");
    pDrive = apvts.getRawParameterValue("drive");
    pLo = apvts.getRawParameterValue("lo");
    pLoMid = apvts.getRawParameterValue("lo_mid");
    pHiMid = apvts.getRawParameterValue("hi_mid");
    pHi = apvts.getRawParameterValue("hi");
    pAttack = apvts.getRawParameterValue("attack");
    pGrunt = apvts.getRawParameterValue("grunt");
    pLoMidFreq = apvts.getRawParameterValue("lo_mid_freq");
    pHiMidFreq = apvts.getRawParameterValue("hi_mid_freq");
    pDistEngage = apvts.getRawParameterValue("dist_engage");
    pInputTrim = apvts.getRawParameterValue("input_trim");
    pOutputTrim = apvts.getRawParameterValue("output_trim");
    pOversampling = apvts.getRawParameterValue("oversampling");
    pRenderOversampling = apvts.getRawParameterValue("render_oversampling");
}

PedalChain::Params ObsidianB7000AudioProcessor::readParams(float master, float blend, float level,
                                                            float drive, float lo, float loMid,
                                                            float hiMid, float hi) const
{
    PedalChain::Params p;
    p.master = master;
    p.blend = blend;
    p.level = level;
    p.drive = drive;
    // EQ pot fraction is BOOST-AT-0 internally (Baxandall.h / MidBand.h: "ab/at/a
    // ->0 = boost"), but the knob param itself must read CW=higher (0=CCW..1=CW)
    // to match the physical control and its tooltip readout — invert here, at the
    // single point where the UI-facing value becomes the DSP-facing one, so CW
    // rotation maps to boost.
    p.lo = 1.0f - lo;
    p.loMid = 1.0f - loMid;
    p.hiMid = 1.0f - hiMid;
    p.hi = 1.0f - hi;
    p.attackIdx = (int) pAttack->load();
    p.gruntIdx = (int) pGrunt->load();
    p.loMidFreq = (int) pLoMidFreq->load();
    p.hiMidFreq = (int) pHiMidFreq->load();
    p.distEngage = pDistEngage->load() >= 0.5f;
    return p;
}

ObsidianB7000AudioProcessor::~ObsidianB7000AudioProcessor() = default;

juce::AudioProcessorValueTreeState::ParameterLayout ObsidianB7000AudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout params;

    // Pots (0..1, taper applied in DSP)
    const auto potAttrs = juce::AudioParameterFloatAttributes().withStringFromValueFunction(
        [] (float v, int) { return juce::String(v, 2); });

    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"master", 1}, "Master",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"blend", 1}, "Blend",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"level", 1}, "Level",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"drive", 1}, "Drive",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"lo", 1}, "Lo",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"lo_mid", 1}, "Lo Mid",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"hi_mid", 1}, "Hi Mid",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"hi", 1}, "Hi",
        juce::NormalisableRange<float>(0.0f, 1.0f), 0.5f, potAttrs));

    // Switches
    params.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{"attack", 1}, "Attack",
        juce::StringArray{"Flat", "Boost", "Cut"}, 0));
    params.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{"grunt", 1}, "Grunt",
        juce::StringArray{"Boost", "Cut", "Flat"}, 0));
    params.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{"lo_mid_freq", 1}, "Lo Mid Freq",
        juce::StringArray{"250Hz", "500Hz", "1kHz"}, 2));
    params.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{"hi_mid_freq", 1}, "Hi Mid Freq",
        juce::StringArray{"750Hz", "1.5kHz", "3kHz"}, 2));

    // Bools
    params.add(std::make_unique<juce::AudioParameterBool>(
        juce::ParameterID{"bypass", 1}, "Bypass", false));
    params.add(std::make_unique<juce::AudioParameterBool>(
        juce::ParameterID{"dist_engage", 1}, "Dist Engage", true));
    params.add(std::make_unique<juce::AudioParameterBool>(
        juce::ParameterID{"trim_link", 1}, "Trim Link", true));
    params.add(std::make_unique<juce::AudioParameterBool>(
        juce::ParameterID{"hq", 1}, "HQ", true));

    // Trims
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"input_trim", 1}, "Input Trim",
        juce::NormalisableRange<float>(-18.0f, 18.0f, 0.1f), 0.0f));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"output_trim", 1}, "Output Trim",
        juce::NormalisableRange<float>(-18.0f, 18.0f, 0.1f), 0.0f));

    // Oversampling
    params.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{"oversampling", 1}, "Oversampling",
        juce::StringArray{"1x", "2x", "4x", "8x"}, 1));
    params.add(std::make_unique<juce::AudioParameterChoice>(
        juce::ParameterID{"render_oversampling", 1}, "Render Oversampling",
        juce::StringArray{"1x", "2x", "4x", "8x"}, 3));

    return params;
}

const juce::String ObsidianB7000AudioProcessor::getName() const
{
    return JucePlugin_Name;
}

bool ObsidianB7000AudioProcessor::acceptsMidi() const { return false; }
bool ObsidianB7000AudioProcessor::producesMidi() const { return false; }
bool ObsidianB7000AudioProcessor::isMidiEffect() const { return false; }
double ObsidianB7000AudioProcessor::getTailLengthSeconds() const { return 0.0; }

int ObsidianB7000AudioProcessor::getNumPrograms() { return (int) kFactoryPresets.size(); }
int ObsidianB7000AudioProcessor::getCurrentProgram() { return currentProgramIndex; }

void ObsidianB7000AudioProcessor::setCurrentProgram(int index)
{
    if (index < 0 || index >= (int) kFactoryPresets.size())
        return;

    currentProgramIndex = index;
    for (const auto& [id, value] : kFactoryPresets[(size_t) index].values)
    {
        if (auto* param = apvts.getParameter(id))
        {
            param->beginChangeGesture();
            param->setValueNotifyingHost(param->convertTo0to1(value));
            param->endChangeGesture();
        }
    }
}

const juce::String ObsidianB7000AudioProcessor::getProgramName(int index)
{
    if (index < 0 || index >= (int) kFactoryPresets.size())
        return {};
    return kFactoryPresets[(size_t) index].name;
}

void ObsidianB7000AudioProcessor::changeProgramName(int, const juce::String&) {}
// Factory presets are fixed; renaming is not supported (isProgramNameEditable defaults to
// false-equivalent for a JUCE-wrapped plugin because host UIs never call this without an
// editable-name affordance we haven't added).

void ObsidianB7000AudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    scratch.setSize(2, samplesPerBlock);
    dryDelayedBuffer.setSize(2, samplesPerBlock);
    inGainRamp.resize((size_t) samplesPerBlock);
    outGainRamp.resize((size_t) samplesPerBlock);
    bypassMixRamp.resize((size_t) samplesPerBlock);

    const int startOrder = (int) pOversampling->load();
    for (auto& d : dsp)
    {
        d.prepare(sampleRate, samplesPerBlock);
        // Apply the Phase-7 CAPTURE-FIT calibration (FitParams.h defaults). This is
        // the ONE place the shipped plugin picks up the fitted chain-domain constants;
        // without it every stage runs its pre-fit `constexpr kXxx` nominal and the
        // plugin silently ignores FitParams (OfflineRender applies it via --fit, so the
        // two would otherwise diverge). Called after prepare() so each stage re-derives
        // its coefficients from the stored sample rate. The DAW-domain scalars
        // (kInputRef/kOutputMakeup) are deliberately NOT here — they live in GainStaging.h.
        d.setFitParams(FitParams{});
        d.setFactorOrder(startOrder);
        // Seed the CONTROL state at the knobs' actual current positions before
        // reset(), for the same reason the pot smoothers are seeded below: reset()
        // snaps the dist_engage footswitch crossfade to its target, so applying the
        // real switch position first is what stops prepareToPlay (a sample-rate
        // change, or playback simply starting) from painting a 5 ms fade over the
        // head of the first block on a session recalled with the OD disengaged.
        d.setParams(readParams(pMaster->load(), pBlend->load(), pLevel->load(), pDrive->load(),
                               pLo->load(), pLoMid->load(), pHiMid->load(), pHi->load()));
        d.reset();
    }
    reportedLatency = dsp[0].getLatencySamples();
    setLatencySamples(reportedLatency);

    const int maxBypassDelay = juce::jmax(1, dsp[0].getMaxLatencySamples());
    for (auto& bd : bypassDelay)
    {
        bd.prepare({sampleRate, (juce::uint32) samplesPerBlock, 1});
        bd.setMaximumDelayInSamples(maxBypassDelay);
        bd.setDelay((float) reportedLatency);
        bd.reset();
    }

    bypassMix.reset(sampleRate, 0.005); // ~5 ms bypass crossfade
    bypassMix.setCurrentAndTargetValue(bypassParam->get() ? 1.0f : 0.0f);

    inputGain.reset(sampleRate, 0.02);
    outputGain.reset(sampleRate, 0.02);
    inputGain.setCurrentAndTargetValue(1.0f);
    outputGain.setCurrentAndTargetValue(1.0f);

    // Pot smoothers (see PluginProcessor.h) — start already at the knob's actual
    // current position so prepareToPlay (SR change, playback start) doesn't
    // itself introduce a fade.
    constexpr double kPotSmoothingSeconds = 0.02;
    for (auto* s : { &smMaster, &smBlend, &smLevel, &smDrive, &smLo, &smLoMid, &smHiMid, &smHi })
        s->reset(sampleRate, kPotSmoothingSeconds);
    smMaster.setCurrentAndTargetValue(pMaster->load());
    smBlend.setCurrentAndTargetValue(pBlend->load());
    smLevel.setCurrentAndTargetValue(pLevel->load());
    smDrive.setCurrentAndTargetValue(pDrive->load());
    smLo.setCurrentAndTargetValue(pLo->load());
    smLoMid.setCurrentAndTargetValue(pLoMid->load());
    smHiMid.setCurrentAndTargetValue(pHiMid->load());
    smHi.setCurrentAndTargetValue(pHi->load());
}

void ObsidianB7000AudioProcessor::releaseResources() {}

void ObsidianB7000AudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;

    const int numIn = getTotalNumInputChannels();
    const int numOut = getTotalNumOutputChannels();
    const int numSamples = buffer.getNumSamples();

    for (int i = numIn; i < numOut; ++i)
        buffer.clear(i, 0, numSamples);

    // ---- OS factor: render factor offline, live factor realtime -------------
    const int wantOrder = isNonRealtime() ? (int) pRenderOversampling->load()
                                          : (int) pOversampling->load();
    for (auto& d : dsp)
        d.setFactorOrder(wantOrder);

    // Report latency to the host (PDC) whenever it changes — distinct from the
    // internal clean-tap delay (dsp.md "do NOT over-correct").
    const int lat = dsp[0].getLatencySamples();
    if (lat != reportedLatency)
    {
        reportedLatency = lat;
        setLatencySamples(lat);
        for (auto& bd : bypassDelay)
        {
            bd.setDelay((float) lat);
            bd.reset(); // one-block gap on the switch, same policy as the OS reinit
        }
    }

    // ---- Params + gain-staging targets (architecture.md processBlock) --------
    // Advance the pot smoothers by one block (skip(), not per-sample — these
    // feed a once-per-block coefficient recompute, see PluginProcessor.h) so a
    // fast knob turn can't jump a stage's coefficients further than one block's
    // worth of ramp, however far the raw APVTS value moved between blocks.
    smMaster.setTargetValue(pMaster->load());
    smBlend.setTargetValue(pBlend->load());
    smLevel.setTargetValue(pLevel->load());
    smDrive.setTargetValue(pDrive->load());
    smLo.setTargetValue(pLo->load());
    smLoMid.setTargetValue(pLoMid->load());
    smHiMid.setTargetValue(pHiMid->load());
    smHi.setTargetValue(pHi->load());

    const auto params = readParams(smMaster.skip(numSamples), smBlend.skip(numSamples),
                                    smLevel.skip(numSamples), smDrive.skip(numSamples),
                                    smLo.skip(numSamples), smLoMid.skip(numSamples),
                                    smHiMid.skip(numSamples), smHi.skip(numSamples));
    for (auto& d : dsp)
        d.setParams(params);

    const float inTrimDb = pInputTrim->load();
    const float outTrimDb = pOutputTrim->load();
    inputGain.setTargetValue(juce::Decibels::decibelsToGain(inTrimDb));
    // MASTER is inside the chain (MasterOut); output makeup + trim only here.
    outputGain.setTargetValue(kOutputMakeup * juce::Decibels::decibelsToGain(outTrimDb) / kInputRef);

    bypassMix.setTargetValue(bypassParam->get() ? 1.0f : 0.0f);
    bypassed.store(bypassParam->get());

    // ---- Advance the shared smoothers ONCE per sample, not once per channel --
    // (see PluginProcessor.h comment on inGainRamp/outGainRamp/bypassMixRamp —
    // a per-channel copy must never be what calls getNextValue(), or the ramp
    // resets every block instead of continuing). Both channels then read the
    // same precomputed ramp, so they still step identically.
    for (int n = 0; n < numSamples; ++n)
    {
        inGainRamp[(size_t) n] = inputGain.getNextValue();
        outGainRamp[(size_t) n] = outputGain.getNextValue();
        bypassMixRamp[(size_t) n] = bypassMix.getNextValue();
    }

    float peakIn = 0.0f, peakOut = 0.0f;
    const int numChans = juce::jmin(numIn, numOut, 2);

    for (int ch = 0; ch < numChans; ++ch)
    {
        float* io = buffer.getWritePointer(ch);
        double* work = scratch.getWritePointer(ch);
        float* dryDelayed = dryDelayedBuffer.getWritePointer(ch);

        // a/b. input trim (DAW domain) → dry copy (delay-compensated for bypass,
        // dsp.md "Dry/wet phase alignment") → meter → chain volts.
        for (int n = 0; n < numSamples; ++n)
        {
            const float wet = io[n] * inGainRamp[(size_t) n];
            peakIn = juce::jmax(peakIn, std::abs(wet));
            work[n] = (double) wet * (double) kInputRef;

            bypassDelay[(size_t) ch].pushSample(0, io[n]);
            dryDelayed[n] = bypassDelay[(size_t) ch].popSample(0, (float) reportedLatency, true);
        }

        // c. run the WDF chain.
        dsp[(size_t) ch].processBlock(work, numSamples);

        // e/f. output makeup+trim, bypass crossfade (delay-compensated dry), output meter.
        for (int n = 0; n < numSamples; ++n)
        {
            const float dry = dryDelayed[n];               // delay-compensated pre-DSP
            const float processed = (float) work[n] * outGainRamp[(size_t) n];
            const float mix = bypassMixRamp[(size_t) n];
            // Branch instead of processed*(1-mix): at full bypass (mix==1) this must
            // be immune to a non-finite `processed` (the chain keeps running even
            // while bypassed, to stay warm for re-engage) — 0.0f * NaN/Inf is NOT
            // zero under IEEE 754, so a naive crossfade can leak chain instability
            // into an otherwise-silent bypass output.
            const float out = mix >= 1.0f ? dry
                             : mix <= 0.0f ? processed
                             : processed * (1.0f - mix) + dry * mix;
            io[n] = out;
            peakOut = juce::jmax(peakOut, std::abs(out));
        }
    }

    inputLevel.store(peakIn);
    outputLevel.store(peakOut);
}

bool ObsidianB7000AudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    if (layouts.getMainInputChannelSet() != juce::AudioChannelSet::mono()
        && layouts.getMainInputChannelSet() != juce::AudioChannelSet::stereo())
        return false;
    if (layouts.getMainOutputChannelSet() != layouts.getMainInputChannelSet())
        return false;
    return true;
}

juce::AudioProcessorEditor* ObsidianB7000AudioProcessor::createEditor()
{
    return new ObsidianB7000AudioProcessorEditor(*this);
}

bool ObsidianB7000AudioProcessor::hasEditor() const { return true; }

void ObsidianB7000AudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = apvts.copyState();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void ObsidianB7000AudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xml(getXmlFromBinary(data, sizeInBytes));
    if (xml != nullptr)
        apvts.replaceState(juce::ValueTree::fromXml(*xml));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new ObsidianB7000AudioProcessor();
}

juce::AudioParameterBool* ObsidianB7000AudioProcessor::getBypassParameter() const
{
    return bypassParam;
}


