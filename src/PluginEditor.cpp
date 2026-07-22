#include "PluginEditor.h"

#include <BinaryData.h>

using namespace juce;

namespace
{
const StringArray kOsChoices { "1x", "2x", "4x", "8x" };
constexpr float kScales[] = { 0.50f, 0.75f, 1.00f, 1.25f, 1.50f, 1.75f, 2.00f, 2.25f, 2.50f };
constexpr const char* kScaleLabels[] = { "50%", "75%", "100%", "125%", "150%",
                                          "175%", "200%", "225%", "250%" };
} // namespace

ObsidianB7000AudioProcessorEditor::ObsidianB7000AudioProcessorEditor(ObsidianB7000AudioProcessor& p)
    : AudioProcessorEditor(&p), audioProcessor(p)
{
    setLookAndFeel(&lnf);

    // ── Load images for LnF ──
    auto load = [](const char* data, int sz) -> Image {
        return data ? ImageCache::getFromMemory(data, sz) : Image{};
    };
    lnf.setKnobImage(load(BinaryData::T_Knob_png, BinaryData::T_Knob_pngSize));
    lnf.setFootswitchImages(
        load(BinaryData::Footswitch_up_png,   BinaryData::Footswitch_up_pngSize),
        load(BinaryData::footswitch_down_png, BinaryData::footswitch_down_pngSize));
    lnf.setTrimImage(load(BinaryData::vol_trim_png, BinaryData::vol_trim_pngSize));

    // ── Cross-session scale ──
    PropertiesFile::Options opts;
    opts.applicationName = "ObsidianB7000";
    opts.filenameSuffix = ".settings";
    opts.folderName = "LeighPierce";
    opts.osxLibrarySubFolder = "Application Support";
    appProps.setStorageParameters(opts);

    if (const auto v = audioProcessor.apvts.state.getProperty("uiScale"); !v.isVoid())
        currentScale = (float)(double)v;
    else
        currentScale = (float)appProps.getUserSettings()->getDoubleValue("defaultScale", 1.0);
    currentScale = jlimit(0.5f, 2.5f, currentScale);

    // ── Side panels ──
    auto setupSection = [this](Label& l, const String& text) {
        l.setText(text, dontSendNotification);
        l.setJustificationType(Justification::centred);
        l.setColour(Label::textColourId, Colour(PedalLookAndFeel::cTrimLabel));
        addAndMakeVisible(l);
    };
    setupSection(inputSectionLabel, "INPUT");
    setupSection(outputSectionLabel, "OUTPUT");

    auto setupTrimSub = [this](Label& l) {
        l.setText("TRIM", dontSendNotification);
        l.setJustificationType(Justification::centred);
        l.setColour(Label::textColourId, Colour(PedalLookAndFeel::cTrimLabel).darker(0.25f));
        addAndMakeVisible(l);
    };
    setupTrimSub(inputTrimSub);
    setupTrimSub(outputTrimSub);

    auto setupTrimValue = [this](Label& l) {
        l.setJustificationType(Justification::centred);
        l.setColour(Label::textColourId, Colour(PedalLookAndFeel::cTrimLabel));
        addAndMakeVisible(l);
    };
    setupTrimValue(inputTrimValue);
    setupTrimValue(outputTrimValue);

    auto setupTrim = [this](Slider& s) {
        s.setComponentID("trim");
        s.setSliderStyle(Slider::RotaryHorizontalVerticalDrag);
        s.setRotaryParameters(MathConstants<float>::pi * 1.25f,
                              MathConstants<float>::pi * 2.75f, true);
        s.setTextBoxStyle(Slider::NoTextBox, false, 0, 0);
        s.setDoubleClickReturnValue(true, 0.0);
        s.textFromValueFunction = [](double v) { return String(v, 2) + " dB"; };
        addAndMakeVisible(s);
    };
    setupTrim(inputTrim);
    setupTrim(outputTrim);
    inputTrimAttach = std::make_unique<SliderParameterAttachment>(
        *audioProcessor.apvts.getParameter("input_trim"), inputTrim);
    outputTrimAttach = std::make_unique<SliderParameterAttachment>(
        *audioProcessor.apvts.getParameter("output_trim"), outputTrim);

    // Seed AFTER the attachments exist so a restored session with non-zero trims doesn't read
    // as a jump on the first move.
    lastInputTrim = inputTrim.getValue();
    lastOutputTrim = outputTrim.getValue();

    auto formatTrim = [](double dB) { return String(dB, 1) + " dB"; };
    inputTrimValue.setText(formatTrim(inputTrim.getValue()), dontSendNotification);
    outputTrimValue.setText(formatTrim(outputTrim.getValue()), dontSendNotification);
    inputTrim.onValueChange = [this, formatTrim] {
        inputTrimValue.setText(formatTrim(inputTrim.getValue()), dontSendNotification);
        mirrorTrim(true);
    };
    outputTrim.onValueChange = [this, formatTrim] {
        outputTrimValue.setText(formatTrim(outputTrim.getValue()), dontSendNotification);
        mirrorTrim(false);
    };

    // ── Editable trim value labels ──
    auto setupEditableTrim = [](Label& valLabel, Slider& s) {
        valLabel.setEditable(false, true, false);
        valLabel.onEditorShow = [&valLabel] {
            auto* ed = valLabel.getCurrentTextEditor();
            if (ed != nullptr)
            {
                ed->setJustification(Justification::centred);
                ed->setColour(TextEditor::textColourId, Colours::white);
                ed->setColour(TextEditor::backgroundColourId, Colours::black);
                ed->setInputRestrictions(5, "-0123456789.");
            }
        };
        valLabel.onEditorHide = [&valLabel, &s] {
            auto text = valLabel.getText(true).trim().unquoted();
            if (text.isEmpty()) return;
            double dB = text.getDoubleValue();
            dB = jlimit(-kTrimRange, kTrimRange, dB);
            s.setValue(dB, sendNotification);
        };
    };
    setupEditableTrim(inputTrimValue, inputTrim);
    setupEditableTrim(outputTrimValue, outputTrim);

    addAndMakeVisible(inputVU);
    addAndMakeVisible(outputVU);

    // ── Oversampling strip ──
    auto setupOSLabel = [this](Label& l, const String& text, Justification j) {
        l.setText(text, dontSendNotification);
        l.setJustificationType(j);
        l.setColour(Label::textColourId, Colour(PedalLookAndFeel::cOSLabel));
        addAndMakeVisible(l);
    };
    setupOSLabel(osLabel, "OS", Justification::centredLeft);
    setupOSLabel(osLiveLabel, "LIVE", Justification::centredRight);
    setupOSLabel(osRenderLabel, "RENDER", Justification::centredRight);
    setupOSLabel(trimLinkLabel, "Trim", Justification::centredRight);
    setupOSLabel(osSizeLabel, "UI SIZE", Justification::centredRight);
    setupOSLabel(osVersionLabel, "v" JucePlugin_VersionString, Justification::centred);
    osVersionLabel.setColour(Label::textColourId, Colour(PedalLookAndFeel::cOSLabel).withAlpha(0.55f));

    auto setupOSBox = [this](ComboBox& box) {
        box.addItemList(kOsChoices, 1);
        box.setJustificationType(Justification::centred);
        box.setColour(ComboBox::textColourId, Colour(PedalLookAndFeel::cOSBtnActive));
        addAndMakeVisible(box);
    };
    setupOSBox(osRealtimeBox);
    setupOSBox(osRenderBox);
    osRealtimeAttach = std::make_unique<ComboBoxParameterAttachment>(
        *audioProcessor.apvts.getParameter("oversampling"), osRealtimeBox);
    osRenderAttach = std::make_unique<ComboBoxParameterAttachment>(
        *audioProcessor.apvts.getParameter("render_oversampling"), osRenderBox);

    trimLockButton.setComponentID("os");
    trimLockButton.setClickingTogglesState(true);
    trimLockButton.setTooltip("TRIM LINK: ties the input and output trims together - raising one "
                              "lowers the other by the same amount.");
    addAndMakeVisible(trimLockButton);
    trimLockAttach = std::make_unique<ButtonParameterAttachment>(
        *audioProcessor.apvts.getParameter("trim_link"), trimLockButton);

    scaleBtn.setComponentID("scale");
    scaleBtn.setColour(TextButton::buttonColourId, Colour(PedalLookAndFeel::cOSBtnActiveBg));
    scaleBtn.setColour(TextButton::textColourOffId, Colour(PedalLookAndFeel::cOSBtnActive));
    scaleBtn.onClick = [this] { showScaleMenu(); };
    addAndMakeVisible(scaleBtn);

    // ── Pedal face ──
    pedalFace = std::make_unique<PedalFace>(audioProcessor.apvts);
    addAndMakeVisible(*pedalFace);

    setResizable(true, true);
    if (auto* c = getConstrainer())
    {
        c->setFixedAspectRatio((double)kBaseW / (double)kBaseH);
        c->setSizeLimits(roundToInt(kBaseW * 0.5f), roundToInt(kBaseH * 0.5f),
                         roundToInt(kBaseW * 2.5f), roundToInt(kBaseH * 2.5f));
    }
    setSize(roundToInt(kBaseW * currentScale), roundToInt(kBaseH * currentScale));

    startTimerHz(33);
}

ObsidianB7000AudioProcessorEditor::~ObsidianB7000AudioProcessorEditor()
{
    setLookAndFeel(nullptr);
}

void ObsidianB7000AudioProcessorEditor::mirrorTrim(bool sourceIsInput)
{
    Slider& src = sourceIsInput ? inputTrim : outputTrim;
    double& srcLast = sourceIsInput ? lastInputTrim : lastOutputTrim;
    const double dstLast = sourceIsInput ? lastOutputTrim : lastInputTrim;

    // Cache the new source value FIRST and unconditionally — the delta must be measured against
    // the previous position even when the lock is off, otherwise the first move after enabling it
    // would be computed from a stale reference and jump the other knob.
    const double delta = src.getValue() - srcLast;
    srcLast = src.getValue();

    // trimLinkBusy: this call is the echo of our own write to the other parameter — its slider's
    // onValueChange has just refreshed that side's cache above, which is all this pass needs to do.
    if (trimLinkBusy || ! trimLockButton.getToggleState() || delta == 0.0)
        return;

    // Equal and opposite CHANGE, relative to where the other knob already sits — so the pair's
    // existing offset is preserved and the starting values don't matter. Clamped at the rails.
    const auto target = (float) jlimit(-kTrimRange, kTrimRange, dstLast - delta);

    if (auto* param = audioProcessor.apvts.getParameter(sourceIsInput ? "output_trim" : "input_trim"))
    {
        const ScopedValueSetter<bool> guard(trimLinkBusy, true);
        param->beginChangeGesture();
        param->setValueNotifyingHost(param->convertTo0to1(target));
        param->endChangeGesture();
    }
}

void ObsidianB7000AudioProcessorEditor::paint(Graphics& g)
{
    g.fillAll(Colour(PedalLookAndFeel::cBackground));
    g.setColour(Colour(PedalLookAndFeel::cOSBackground));
    g.fillRoundedRectangle(osStripArea.toFloat(), 6.0f);
    g.setColour(Colour(PedalLookAndFeel::cOSBorder));
    g.drawRoundedRectangle(osStripArea.toFloat().reduced(0.5f), 6.0f, 1.0f);
}

void ObsidianB7000AudioProcessorEditor::refreshFonts(float sc)
{
    auto bold = [](float sz) { return Font(FontOptions(sz, Font::bold)); };
    inputSectionLabel.setFont(bold(8.0f * sc).withExtraKerningFactor(0.20f));
    outputSectionLabel.setFont(bold(8.0f * sc).withExtraKerningFactor(0.20f));
    inputTrimSub.setFont(bold(7.5f * sc).withExtraKerningFactor(0.15f));
    outputTrimSub.setFont(bold(7.5f * sc).withExtraKerningFactor(0.15f));
    inputTrimValue.setFont(bold(8.5f * sc));
    outputTrimValue.setFont(bold(8.5f * sc));
    osLabel.setFont(bold(8.0f * sc));
    osLiveLabel.setFont(bold(7.0f * sc).withExtraKerningFactor(0.10f));
    osRenderLabel.setFont(bold(7.0f * sc).withExtraKerningFactor(0.10f));
    trimLinkLabel.setFont(bold(7.0f * sc).withExtraKerningFactor(0.10f));
    osSizeLabel.setFont(bold(7.0f * sc).withExtraKerningFactor(0.10f));
    osVersionLabel.setFont(bold(7.0f * sc).withExtraKerningFactor(0.10f));
}

void ObsidianB7000AudioProcessorEditor::resized()
{
    currentScale = (float)getWidth() / (float)kBaseW;
    const float sc = currentScale;
    const auto i = [sc](int v) { return roundToInt((float)v * sc); };
    refreshFonts(sc);

    const int W = getWidth(), H = getHeight();
    const int margin = i(10);
    const int panelW = i(74);
    const int osH = i(24);
    const int faceGap = i(10);
    const int colGap = i(8);

    const int topY = margin;
    const int topH = H - margin - osH - faceGap - margin;

    osStripArea = Rectangle<int>(margin, H - margin - osH, W - 2 * margin, osH);

    const Rectangle<int> inPanel(margin, topY, panelW, topH);
    const Rectangle<int> outPanel(W - margin - panelW, topY, panelW, topH);
    pedalFaceArea = Rectangle<int>(margin + panelW + colGap, topY,
                                   W - 2 * (margin + panelW + colGap), topH);
    if (pedalFace != nullptr)
    {
        pedalFace->setBounds(pedalFaceArea);
        pedalFace->refresh(sc);
    }

    auto layoutPanel = [&](Rectangle<int> panel, Label& sec, Slider& knob, Label& sub,
                           Label& val, VUMeter& vu) {
        auto r = panel;
        sec.setBounds(r.removeFromTop(i(14)));
        r.removeFromTop(i(2));
        const int knobD = jmin(i(70), r.getWidth());
        auto knobRow = r.removeFromTop(knobD);
        knob.setBounds(knobRow.withSizeKeepingCentre(knobD, knobD));
        sub.setBounds(r.removeFromTop(i(12)));
        val.setBounds(r.removeFromTop(i(12)));
        r.removeFromTop(i(2));
        const int vuW = jmin(i(34), r.getWidth());
        vu.setBounds(r.withSizeKeepingCentre(vuW, r.getHeight()));
    };
    layoutPanel(inPanel, inputSectionLabel, inputTrim, inputTrimSub, inputTrimValue, inputVU);
    layoutPanel(outPanel, outputSectionLabel, outputTrim, outputTrimSub, outputTrimValue, outputVU);

    // ── OS strip content ──
    auto os = osStripArea.reduced(i(6), 0);
    const int boxVPad = i(2);
    osLabel.setBounds(os.removeFromLeft(i(20)));
    os.removeFromLeft(i(8));
    osLiveLabel.setBounds(os.removeFromLeft(i(26)));
    os.removeFromLeft(i(5));
    osRealtimeBox.setBounds(os.removeFromLeft(i(36)).reduced(0, boxVPad));
    os.removeFromLeft(i(12));
    osRenderLabel.setBounds(os.removeFromLeft(i(40)));
    os.removeFromLeft(i(5));
    osRenderBox.setBounds(os.removeFromLeft(i(36)).reduced(0, boxVPad));
    os.removeFromLeft(i(8));
    trimLinkLabel.setBounds(os.removeFromLeft(i(26)));
    os.removeFromLeft(i(5));
    trimLockButton.setBounds(os.removeFromLeft(jmax(i(36), 30)).reduced(0, boxVPad));
    scaleBtn.setBounds(os.removeFromRight(i(48)).reduced(0, boxVPad));
    os.removeFromRight(i(5));
    osSizeLabel.setBounds(os.removeFromRight(i(42)));
    osVersionLabel.setBounds(os);
    scaleBtn.setButtonText(String(roundToInt(currentScale * 100.0f)) + "%");

    audioProcessor.apvts.state.setProperty("uiScale", (double)currentScale, nullptr);
}

void ObsidianB7000AudioProcessorEditor::timerCallback()
{
    constexpr float kNoiseFl = 5.0e-4f;

    float in = jmax(audioProcessor.getInputLevel(0), vuInDecay * 0.90f);
    if (in < kNoiseFl) in = 0.0f;
    vuInDecay = in;
    inputVU.setLevel(in);

    float out = jmax(audioProcessor.getOutputLevel(0), vuOutDecay * 0.90f);
    if (out < kNoiseFl) out = 0.0f;
    vuOutDecay = out;
    outputVU.setLevel(out);

    if (pedalFace != nullptr)
        pedalFace->updateLEDs();
}

void ObsidianB7000AudioProcessorEditor::showScaleMenu()
{
    PopupMenu menu;
    for (int n = 0; n < 9; ++n)
        menu.addItem(n + 1, kScaleLabels[n], true, std::abs(currentScale - kScales[n]) < 0.01f);
    menu.addSeparator();
    menu.addItem(100, "Set current scale as default");

    menu.showMenuAsync(PopupMenu::Options().withTargetComponent(&scaleBtn), [this](int r) {
        if (r >= 1 && r <= 9)
            setSize(roundToInt(kBaseW * kScales[r - 1]), roundToInt(kBaseH * kScales[r - 1]));
        else if (r == 100)
            appProps.getUserSettings()->setValue("defaultScale", (double)currentScale);
    });
}
