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

    juce::Label osLabel, osLiveLabel, osRenderLabel, osSizeLabel, osVersionLabel;
    juce::ComboBox osRealtimeBox, osRenderBox;
    juce::TextButton scaleBtn;
    std::unique_ptr<juce::ComboBoxParameterAttachment> osRealtimeAttach, osRenderAttach;

    std::unique_ptr<PedalFace> pedalFace;
    juce::Rectangle<int> pedalFaceArea, osStripArea;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ObsidianB7000AudioProcessorEditor)
};
