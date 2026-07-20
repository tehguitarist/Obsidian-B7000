#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>

#include "PluginProcessor.h"
#include "ui/PedalLookAndFeel.h"
#include "ui/VUMeter.h"
#include "ui/KnobComponent.h"
#include "ui/ImageLED.h"
#include "ui/SwitchToggle.h"
#include "ui/AttackGruntIcons.h"
#include "ui/SwitchLabelText.h"

class ObsidianB7000AudioProcessorEditor : public juce::AudioProcessorEditor,
                                          private juce::Timer
{
public:
    explicit ObsidianB7000AudioProcessorEditor(ObsidianB7000AudioProcessor&);
    ~ObsidianB7000AudioProcessorEditor() override;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    static constexpr int kBaseTextureW = 1960;
    static constexpr int kBaseTextureH = 1540;
    static constexpr int kPanelW = 140;
    static constexpr int kStripH = 32;
    static constexpr int kFaceW = 980;
    static constexpr int kFaceH = kFaceW * kBaseTextureH / kBaseTextureW;
    static constexpr int kBaseW = kFaceW + 2 * kPanelW;
    static constexpr int kBaseH = kFaceH + kStripH;

    ObsidianB7000AudioProcessor& processor;
    juce::AudioProcessorValueTreeState& apvts;
    PedalLookAndFeel laf;
    juce::ApplicationProperties appProps;

    float currentScale { 1.0f };

    class ScaleDebounce : public juce::Timer
    {
    public:
        ScaleDebounce(juce::ApplicationProperties& p) : props(p) {}
        void timerCallback() override
        {
            props.getUserSettings()->setValue("defaultScale", (double)savedScale);
            stopTimer();
        }
        double savedScale = 1.0;
    private:
        juce::ApplicationProperties& props;
    } scaleSaveDebounce;

    juce::Font lexendFont;
    juce::Image baseTexture;
    juce::Image knobImage, fsUpImage, fsDownImage;
    juce::Image ledOnImage, ledOffImage, volTrimImage;

    juce::Label inputPanelLabel, outputPanelLabel;
    KnobComponent inputTrimKnob, outputTrimKnob;
    juce::Label inputTrimSubLabel, outputTrimSubLabel;
    juce::Label inputTrimValue, outputTrimValue;
    VUMeter inputVU, outputVU;

    struct FaceComp { juce::Component* comp; float cx, cy, w, h; };
    std::vector<FaceComp> faceComps;

    static constexpr int kNumKnobs = 8;
    KnobComponent knobSliders[kNumKnobs];

    juce::ImageButton bypassFS, distFS;
    std::unique_ptr<juce::ButtonParameterAttachment> bypassAttach, distAttach;
    ImageLED bypassLED, distLED;
    SwitchToggle attackToggle, gruntToggle, loMidToggle, hiMidToggle;
    AttackGruntIcons attackIcons { AttackGruntIcons::Type::Attack };
    AttackGruntIcons gruntIcons { AttackGruntIcons::Type::Grunt };
    SwitchLabelText loMidText, hiMidText;

    juce::Label osLabel, osLiveLabel, osRenderLabel, uiSizeLabel;
    juce::ComboBox osRealtimeBox, osRenderBox;
    std::unique_ptr<juce::ComboBoxParameterAttachment> osRealtimeAttach, osRenderAttach;
    juce::TextButton trimLinkBtn, hqBtn;
    std::unique_ptr<juce::ButtonParameterAttachment> trimLinkAttach, hqAttach;
    juce::TextButton scaleBtn;
    juce::Label versionLabel;

    void refreshFonts(float sc);
    float trimToDB(float normalized);
    void timerCallback() override;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(ObsidianB7000AudioProcessorEditor)
};
