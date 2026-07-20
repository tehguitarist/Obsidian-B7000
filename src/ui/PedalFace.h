#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>

#include "AttackGruntIcons.h"
#include "ImageLED.h"
#include "PedalLookAndFeel.h"
#include "SwitchLabelText.h"
#include "SwitchToggle.h"

class PedalFace : public juce::Component
{
public:
    explicit PedalFace(juce::AudioProcessorValueTreeState& apvts);
    ~PedalFace() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;
    void refresh(float scale);
    void updateLEDs();

private:
    struct Pos { float rx, ry, rw, rh; }; // ratios of texture 1960x1540

    juce::AudioProcessorValueTreeState& state;
    float scale { 1.0f };
    juce::Image baseTexture;
    juce::Font lexendFont { juce::FontOptions() };

    static constexpr int kNumKnobs = 8;
    static constexpr const char* kKnobParamIDs[8] = {
        "master", "blend", "level", "drive",
        "lo", "lo_mid", "hi_mid", "hi"
    };

    juce::Slider knobSliders[kNumKnobs];
    std::unique_ptr<juce::SliderParameterAttachment> knobAttachments[kNumKnobs];

    juce::TextButton bypassFS, distFS;
    std::unique_ptr<juce::ButtonParameterAttachment> bypassAttach, distAttach;

    ImageLED bypassLED, distLED;

    SwitchToggle attackToggle, gruntToggle, loMidToggle, hiMidToggle;
    AttackGruntIcons attackIcons { AttackGruntIcons::Type::Attack };
    AttackGruntIcons gruntIcons  { AttackGruntIcons::Type::Grunt };
    SwitchLabelText loMidText, hiMidText;

    struct CompPos { juce::Component* comp; Pos pos; };
    std::vector<CompPos> components;

    void buildComponents();
    void positionComponents();
};
