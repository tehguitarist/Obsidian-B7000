#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class PedalLookAndFeel : public juce::LookAndFeel_V4
{
public:
    static constexpr juce::uint32 cBackground      = 0xFF050912u;
    static constexpr juce::uint32 cPedalFace       = 0xFF070D1Au;
    static constexpr juce::uint32 cPedalBorder     = 0xFF18293Fu;
    static constexpr juce::uint32 cKnobHighlight   = 0xFFF5F5F5u;
    static constexpr juce::uint32 cKnobMid         = 0xFFD8D8D8u;
    static constexpr juce::uint32 cKnobShadow      = 0xFF949494u;
    static constexpr juce::uint32 cKnobIndicator   = 0xFF1A1A30u;
    static constexpr juce::uint32 cLEDActive       = 0xFF00DD55u;
    static constexpr juce::uint32 cLEDInactive     = 0xFF091A09u;
    static constexpr juce::uint32 cLabelText       = 0xFFFFFFFFu;
    static constexpr juce::uint32 cPowerLabel      = 0xFF2E4A60u;
    static constexpr juce::uint32 cTrimLabel       = 0xFF5588AAu;
    static constexpr juce::uint32 cTrimArc         = 0xFF2A5898u;
    static constexpr juce::uint32 cTrimArcTrack    = 0xFF101E30u;
    static constexpr juce::uint32 cSWLabelActive   = 0xFFFFFFFFu;
    static constexpr juce::uint32 cSWLabelInactive = 0x73FFFFFFu;
    static constexpr juce::uint32 cBypassLabel     = 0xFF2E4A60u;
    static constexpr juce::uint32 cMeterLow        = 0xFF44CC44u;
    static constexpr juce::uint32 cMeterMid        = 0xFFCCBA00u;
    static constexpr juce::uint32 cMeterHigh       = 0xFFDD2222u;
    static constexpr juce::uint32 cMeterLowDim     = 0xFF091A09u;
    static constexpr juce::uint32 cMeterMidDim     = 0xFF1E1700u;
    static constexpr juce::uint32 cMeterHighDim    = 0xFF220808u;
    static constexpr juce::uint32 cOSBackground    = 0xFF080E1Au;
    static constexpr juce::uint32 cOSBorder        = 0xFF101C2Eu;
    static constexpr juce::uint32 cOSLabel         = 0xFF3A6080u;
    static constexpr juce::uint32 cOSBtnActive     = 0xFF70A8D8u;
    static constexpr juce::uint32 cOSBtnActiveBg   = 0xFF0C2040u;
    static constexpr juce::uint32 cOSBtnActiveBdr  = 0xFF2A5890u;

    PedalLookAndFeel();

    void setKnobImage(const juce::Image& img) { knobImage = img; }
    void setFootswitchImages(const juce::Image& up, const juce::Image& down) { fsUpImage = up; fsDownImage = down; }
    void setTrimImage(const juce::Image& img) { trimImage = img; }

    void drawRotarySlider(juce::Graphics& g, int x, int y, int w, int h,
                          float sliderPos, float rotaryStartAngle, float rotaryEndAngle,
                          juce::Slider& slider) override;

    void drawButtonBackground(juce::Graphics& g, juce::Button& button,
                              const juce::Colour& backgroundColour,
                              bool shouldDrawButtonAsHighlighted,
                              bool shouldDrawButtonAsDown) override;

    void drawButtonText(juce::Graphics& g, juce::TextButton& button,
                        bool shouldDrawButtonAsHighlighted,
                        bool shouldDrawButtonAsDown) override;

    void drawLabel(juce::Graphics& g, juce::Label& label) override;

    void drawComboBox(juce::Graphics& g, int width, int height, bool isButtonDown,
                      int buttonX, int buttonY, int buttonW, int buttonH,
                      juce::ComboBox& box) override;

    juce::Font getComboBoxFont(juce::ComboBox& box) override;
    void positionComboBoxText(juce::ComboBox& box, juce::Label& label) override;

private:
    void drawTrimHalo(juce::Graphics& g, juce::Rectangle<float> bounds, float sliderPos,
                      float startAngle, float endAngle);
    void drawKnobFromImage(juce::Graphics& g, const juce::Image& img, juce::Rectangle<float> bounds,
                           float sliderPos, float startAngle, float endAngle);

    juce::Image knobImage, fsUpImage, fsDownImage, trimImage;
};
