#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>

#include "PluginProcessor.h"
#include "ui/PedalLookAndFeel.h"
#include "ui/PedalFace.h"
#include "ui/VUMeter.h"

class ObsidianB7000AudioProcessorEditor : public juce::AudioProcessorEditor,
                                          private juce::Timer
{
public:
    explicit ObsidianB7000AudioProcessorEditor(ObsidianB7000AudioProcessor&);
    ~ObsidianB7000AudioProcessorEditor() override;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;
    void refreshFonts(float sc);
    void showScaleMenu();

    static constexpr int kBaseW = 765;
    static constexpr int kBaseH = 475;

    // Trim knob range, +/- dB. Must match the trim NormalisableRange in createParameterLayout().
    static constexpr double kTrimRange = 18.0;

    ObsidianB7000AudioProcessor& audioProcessor;
    PedalLookAndFeel lnf;
    juce::ApplicationProperties appProps;
    float currentScale { 1.0f };
    float vuInDecay { 0.0f }, vuOutDecay { 0.0f };

    juce::Label inputSectionLabel, outputSectionLabel;
    juce::Slider inputTrim, outputTrim;
    juce::Label inputTrimSub, outputTrimSub;
    juce::Label inputTrimValue, outputTrimValue;
    VUMeter inputVU, outputVU;
    std::unique_ptr<juce::SliderParameterAttachment> inputTrimAttach, outputTrimAttach;

    // Applies the equal-and-opposite CHANGE to the other trim, preserving the pair's existing
    // offset (delta-linked, so enabling the lock never snaps). No-op when off. `trimLinkBusy`
    // breaks the A->B->A feedback loop the two parameter attachments would otherwise bounce through.
    void mirrorTrim(bool sourceIsInput);
    bool   trimLinkBusy   { false };
    double lastInputTrim  { 0.0 };
    double lastOutputTrim { 0.0 };

    juce::Label osLabel, osLiveLabel, osRenderLabel, osSizeLabel, osVersionLabel;
    juce::Label trimLinkLabel;
    juce::ComboBox osRealtimeBox, osRenderBox;
    juce::TextButton scaleBtn;
    juce::TextButton trimLockButton { "LINK" };
    std::unique_ptr<juce::ComboBoxParameterAttachment> osRealtimeAttach, osRenderAttach;
    std::unique_ptr<juce::ButtonParameterAttachment> trimLockAttach;

    std::unique_ptr<PedalFace> pedalFace;
    juce::Rectangle<int> pedalFaceArea, osStripArea;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ObsidianB7000AudioProcessorEditor)
};
