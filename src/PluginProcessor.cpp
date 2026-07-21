#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "dsp/PedalDSP.h"

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

PedalChain::Params ObsidianB7000AudioProcessor::readParams() const
{
    PedalChain::Params p;
    p.master = pMaster->load();
    p.blend = pBlend->load();
    p.level = pLevel->load();
    p.drive = pDrive->load();
    p.lo = pLo->load();
    p.loMid = pLoMid->load();
    p.hiMid = pHiMid->load();
    p.hi = pHi->load();
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
        juce::ParameterID{"trim_link", 1}, "Trim Link", false));
    params.add(std::make_unique<juce::AudioParameterBool>(
        juce::ParameterID{"hq", 1}, "HQ", true));

    // Trims
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"input_trim", 1}, "Input Trim",
        juce::NormalisableRange<float>(-12.0f, 12.0f, 0.1f), 0.0f));
    params.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID{"output_trim", 1}, "Output Trim",
        juce::NormalisableRange<float>(-12.0f, 12.0f, 0.1f), 0.0f));

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

int ObsidianB7000AudioProcessor::getNumPrograms() { return 1; }
int ObsidianB7000AudioProcessor::getCurrentProgram() { return 0; }
void ObsidianB7000AudioProcessor::setCurrentProgram(int) {}
const juce::String ObsidianB7000AudioProcessor::getProgramName(int) { return {}; }
void ObsidianB7000AudioProcessor::changeProgramName(int, const juce::String&) {}

void ObsidianB7000AudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    scratch.setSize(2, samplesPerBlock);
    dryDelayedBuffer.setSize(2, samplesPerBlock);

    const int startOrder = (int) pOversampling->load();
    for (auto& d : dsp)
    {
        d.prepare(sampleRate, samplesPerBlock);
        d.setFactorOrder(startOrder);
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
    const auto params = readParams();
    for (auto& d : dsp)
        d.setParams(params);

    const float inTrimDb = pInputTrim->load();
    const float outTrimDb = pOutputTrim->load();
    inputGain.setTargetValue(juce::Decibels::decibelsToGain(inTrimDb));
    // MASTER is inside the chain (MasterOut); output makeup + trim only here.
    outputGain.setTargetValue(kOutputMakeup * juce::Decibels::decibelsToGain(outTrimDb) / kInputRef);

    bypassMix.setTargetValue(bypassParam->get() ? 1.0f : 0.0f);
    bypassed.store(bypassParam->get());

    // ---- Snapshot smoothed values so every channel steps identically --------
    const auto inGainStart = inputGain;
    const auto outGainStart = outputGain;
    const auto bypassStart = bypassMix;

    float peakIn = 0.0f, peakOut = 0.0f;
    const int numChans = juce::jmin(numIn, numOut, 2);

    for (int ch = 0; ch < numChans; ++ch)
    {
        auto inGain = inGainStart;
        auto outGain = outGainStart;
        auto bMix = bypassStart;

        float* io = buffer.getWritePointer(ch);
        double* work = scratch.getWritePointer(ch);
        float* dryDelayed = dryDelayedBuffer.getWritePointer(ch);

        // a/b. input trim (DAW domain) → dry copy (delay-compensated for bypass,
        // dsp.md "Dry/wet phase alignment") → meter → chain volts.
        for (int n = 0; n < numSamples; ++n)
        {
            const float wet = io[n] * inGain.getNextValue();
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
            const float processed = (float) work[n] * outGain.getNextValue();
            const float mix = bMix.getNextValue();
            const float out = processed * (1.0f - mix) + dry * mix;
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


