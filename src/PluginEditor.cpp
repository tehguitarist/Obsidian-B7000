#include "PluginEditor.h"
#include "PluginProcessor.h"

#include <BinaryData.h>

static constexpr const char* kKnobParamIDs[8] = {
    "master", "blend", "level", "drive",
    "lo", "lo_mid", "hi_mid", "hi"
};

// ================================================================
// Constructor
// ================================================================
ObsidianB7000AudioProcessorEditor::ObsidianB7000AudioProcessorEditor(
    ObsidianB7000AudioProcessor& p)
    : AudioProcessorEditor(&p),
      processor(p),
      apvts(p.apvts),
      scaleSaveDebounce(appProps)
{
    setLookAndFeel(&laf);

    // ── Load Lexend Exa font ──
    {
        auto tf = juce::Typeface::createSystemTypefaceFor(
            BinaryData::LexendExaRegular_ttf,
            BinaryData::LexendExaRegular_ttfSize);
        if (tf != nullptr)
            lexendFont = juce::Font(juce::FontOptions(tf));
        if (lexendFont.getTypefacePtr() == nullptr)
            lexendFont = juce::Font(juce::FontOptions(14.0f));
    }

    // ── Load images from BinaryData ──
    auto loadImg = [](const char* data, int size) -> juce::Image
    {
        if (data != nullptr && size > 0)
            return juce::ImageCache::getFromMemory(data, size);
        return {};
    };

    baseTexture  = loadImg(BinaryData::b7k_texture_base_png,  BinaryData::b7k_texture_base_pngSize);
    knobImage    = loadImg(BinaryData::T_Knob_png,             BinaryData::T_Knob_pngSize);
    fsUpImage    = loadImg(BinaryData::Footswitch_up_png,      BinaryData::Footswitch_up_pngSize);
    fsDownImage  = loadImg(BinaryData::footswitch_down_png,    BinaryData::footswitch_down_pngSize);
    ledOnImage   = loadImg(BinaryData::blue_led_on_png,        BinaryData::blue_led_on_pngSize);
    ledOffImage  = loadImg(BinaryData::blue_led_off_png,       BinaryData::blue_led_off_pngSize);
    volTrimImage = loadImg(BinaryData::vol_trim_png,           BinaryData::vol_trim_pngSize);

    juce::Image switchImgs[3] = {
        loadImg(BinaryData::switch_up_png,    BinaryData::switch_up_pngSize),
        loadImg(BinaryData::switch_Mid_png,   BinaryData::switch_Mid_pngSize),
        loadImg(BinaryData::switch_down_png,  BinaryData::switch_down_pngSize)
    };

    // ── Knobs ──
    for (int i = 0; i < kNumKnobs; ++i)
    {
        auto& k = knobSliders[i];
        k.setImage(knobImage);
        if (auto* param = apvts.getParameter(kKnobParamIDs[i]))
        {
            k.setParameter(param);
            k.updateValue();
        }
        addAndMakeVisible(k);
    }

    // ── Footswitches ──
    auto setupFS = [&](juce::ImageButton& btn, const char* paramId)
    {
        btn.setImages(false, true, false,
                      fsUpImage, 1.0f, juce::Colours::transparentWhite,
                      fsUpImage, 1.0f, juce::Colours::transparentWhite,
                      fsDownImage, 1.0f, juce::Colours::transparentWhite);
        btn.setClickingTogglesState(true);
        addAndMakeVisible(btn);
    };
    setupFS(bypassFS, "bypass");
    setupFS(distFS,   "dist_engage");
    bypassAttach = std::make_unique<juce::ButtonParameterAttachment>(
        *apvts.getParameter("bypass"), bypassFS);
    distAttach = std::make_unique<juce::ButtonParameterAttachment>(
        *apvts.getParameter("dist_engage"), distFS);

    // ── LEDs ──
    bypassLED.setImages(ledOnImage, ledOffImage);
    distLED.setImages(ledOnImage, ledOffImage);
    addAndMakeVisible(bypassLED);
    addAndMakeVisible(distLED);

    // ── Switch toggles ──
    auto setupToggle = [&](SwitchToggle& toggle, int defaultValue)
    {
        toggle.setImages(switchImgs[0], switchImgs[1], switchImgs[2]);
        toggle.setPosition(defaultValue);
        addAndMakeVisible(toggle);
    };
    setupToggle(attackToggle, 0);
    setupToggle(gruntToggle,  0);
    setupToggle(loMidToggle,  2);
    setupToggle(hiMidToggle,  2);

    // ── Switch → APVTS ──
    attackToggle.onChange = [this](int pos) {
        auto* cp = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("attack"));
        if (cp == nullptr) return;
        cp->beginChangeGesture();
        cp->setValueNotifyingHost(cp->getNormalisableRange().convertTo0to1((float)pos));
        cp->endChangeGesture();
    };
    gruntToggle.onChange = [this](int pos) {
        auto* cp = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("grunt"));
        if (cp == nullptr) return;
        cp->beginChangeGesture();
        cp->setValueNotifyingHost(cp->getNormalisableRange().convertTo0to1((float)pos));
        cp->endChangeGesture();
    };
    loMidToggle.onChange = [this](int pos) {
        static constexpr int map[] = { 1, 2, 0 };
        auto* cp = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("lo_mid_freq"));
        if (cp == nullptr) return;
        cp->beginChangeGesture();
        cp->setValueNotifyingHost(cp->getNormalisableRange().convertTo0to1((float)map[pos]));
        cp->endChangeGesture();
    };
    hiMidToggle.onChange = [this](int pos) {
        static constexpr int map[] = { 1, 2, 0 };
        auto* cp = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("hi_mid_freq"));
        if (cp == nullptr) return;
        cp->beginChangeGesture();
        cp->setValueNotifyingHost(cp->getNormalisableRange().convertTo0to1((float)map[pos]));
        cp->endChangeGesture();
    };

    // ── Attack/Grunt icons ──
    addAndMakeVisible(attackIcons);
    addAndMakeVisible(gruntIcons);

    // ── Lo-mid / Hi-mid text labels ──
    loMidText.setLabels("500Hz", "1k", "250Hz");
    hiMidText.setLabels("1.5k", "3k", "750Hz");
    addAndMakeVisible(loMidText);
    addAndMakeVisible(hiMidText);

    // ── Side panels ──
    auto setupTrim = [&](KnobComponent& knob, const char* paramId)
    {
        knob.setImage(volTrimImage);
        if (auto* param = apvts.getParameter(paramId))
        {
            knob.setParameter(param);
            knob.updateValue();
        }
        addAndMakeVisible(knob);
    };
    setupTrim(inputTrimKnob,  "input_trim");
    setupTrim(outputTrimKnob, "output_trim");

    inputPanelLabel.setText("INPUT", juce::dontSendNotification);
    outputPanelLabel.setText("OUTPUT", juce::dontSendNotification);
    inputTrimSubLabel.setText("TRIM", juce::dontSendNotification);
    outputTrimSubLabel.setText("TRIM", juce::dontSendNotification);
    inputTrimValue.setText("+0.00 dB", juce::dontSendNotification);
    outputTrimValue.setText("+0.00 dB", juce::dontSendNotification);

    addAndMakeVisible(inputPanelLabel);
    addAndMakeVisible(outputPanelLabel);
    addAndMakeVisible(inputTrimSubLabel);
    addAndMakeVisible(outputTrimSubLabel);
    addAndMakeVisible(inputTrimValue);
    addAndMakeVisible(outputTrimValue);
    addAndMakeVisible(inputVU);
    addAndMakeVisible(outputVU);

    // ── Bottom strip ──
    osLabel.setText("OS", juce::dontSendNotification);
    osLiveLabel.setText("LIVE", juce::dontSendNotification);
    osRenderLabel.setText("RENDER", juce::dontSendNotification);
    uiSizeLabel.setText("UI SIZE", juce::dontSendNotification);

    addAndMakeVisible(osLabel);
    addAndMakeVisible(osLiveLabel);
    addAndMakeVisible(osRenderLabel);
    addAndMakeVisible(uiSizeLabel);

    auto setupOSBox = [&](juce::ComboBox& box, const char* paramId)
    {
        box.addItemList({"1x", "2x", "4x", "8x"}, 1);
        box.setJustificationType(juce::Justification::centred);
        addAndMakeVisible(box);
    };
    setupOSBox(osRealtimeBox, "oversampling");
    setupOSBox(osRenderBox,   "render_oversampling");
    osRealtimeAttach = std::make_unique<juce::ComboBoxParameterAttachment>(
        *apvts.getParameter("oversampling"), osRealtimeBox);
    osRenderAttach = std::make_unique<juce::ComboBoxParameterAttachment>(
        *apvts.getParameter("render_oversampling"), osRenderBox);

    auto setupToggleBtn = [&](juce::TextButton& btn, const char* label, const char* paramId)
    {
        btn.setButtonText(label);
        btn.setComponentID("os");
        btn.setClickingTogglesState(true);
        btn.setTooltip(label);
        addAndMakeVisible(btn);
    };
    setupToggleBtn(trimLinkBtn, "TRIM LINK", "trim_link");
    setupToggleBtn(hqBtn, "HQ", "hq");
    trimLinkAttach = std::make_unique<juce::ButtonParameterAttachment>(
        *apvts.getParameter("trim_link"), trimLinkBtn);
    hqAttach = std::make_unique<juce::ButtonParameterAttachment>(
        *apvts.getParameter("hq"), hqBtn);

    scaleBtn.setButtonText("100%");
    scaleBtn.setComponentID("os-selector");
    scaleBtn.setTooltip("UI Scale");
    addAndMakeVisible(scaleBtn);

    versionLabel.setText("v" JucePlugin_VersionString, juce::dontSendNotification);
    versionLabel.setInterceptsMouseClicks(false, false);
    addAndMakeVisible(versionLabel);

    // ── Hardcoded face positions (ratios of base texture 1960×1540) ──
    // cx,cy = centre ratio; w,h = size ratio (0 = square, equals w)
    faceComps = {
        { &knobSliders[0], 0.165816f, 0.165584f, 0.158163f, 0.0f      }, // Master knob
        { &knobSliders[1], 0.390306f, 0.165584f, 0.158163f, 0.0f      }, // Blend knob
        { &knobSliders[2], 0.611224f, 0.165584f, 0.158163f, 0.0f      }, // level knob
        { &knobSliders[3], 0.837755f, 0.165584f, 0.158163f, 0.0f      }, // drive knob
        { &knobSliders[4], 0.165816f, 0.451299f, 0.158163f, 0.0f      }, // bass knob
        { &knobSliders[5], 0.390306f, 0.451299f, 0.158163f, 0.0f      }, // Lo Mids Knob
        { &knobSliders[6], 0.611224f, 0.451299f, 0.158163f, 0.0f      }, // Hi mids knob
        { &knobSliders[7], 0.837755f, 0.451299f, 0.158163f, 0.0f      }, // Treble knob
        { &distFS,         0.175510f, 0.859091f, 0.135204f, 0.0f      }, // distortion footswitch
        { &bypassFS,       0.825000f, 0.859091f, 0.135204f, 0.0f      }, // bypass footswitch
        { &distLED,        0.165306f, 0.679221f, 0.043367f, 0.0f      }, // distortion LED
        { &bypassLED,      0.835204f, 0.679221f, 0.043367f, 0.0f      }, // bypass LED
        { &attackToggle,   0.278061f, 0.325974f, 0.074490f, 0.0f      }, // attack switch
        { &attackIcons,    0.278061f, 0.425325f, 0.056122f, 0.050000f }, // attack icons
        { &gruntToggle,    0.725510f, 0.325974f, 0.074490f, 0.0f      }, // grunt switch
        { &gruntIcons,     0.725510f, 0.425325f, 0.056122f, 0.050000f }, // grunt icons
        { &loMidToggle,    0.278061f, 0.569481f, 0.074490f, 0.0f      }, // low mids switch
        { &loMidText,      0.278061f, 0.667532f, 0.056122f, 0.071429f }, // low mids text
        { &hiMidToggle,    0.725510f, 0.569481f, 0.074490f, 0.0f      }, // hi mids switch
        { &hiMidText,      0.725510f, 0.667532f, 0.056122f, 0.071429f }, // hi mids text
    };

    // ── Resizable window ──
    setResizable(true, true);
    if (auto* c = getConstrainer())
    {
        c->setFixedAspectRatio((double)kBaseW / (double)kBaseH);
        c->setSizeLimits(juce::roundToInt(kBaseW * 0.5f), juce::roundToInt(kBaseH * 0.5f),
                         juce::roundToInt(kBaseW * 2.5f), juce::roundToInt(kBaseH * 2.5f));
    }

    // ── Load saved scale ──
    juce::PropertiesFile::Options propsOpts;
    propsOpts.applicationName = "ObsidianB7000";
    propsOpts.osxLibrarySubFolder = "ApplicationSupport";
    propsOpts.folderName = "ObsidianB7000";
    propsOpts.filenameSuffix = ".settings";
    appProps.setStorageParameters(propsOpts);
    if (auto* settings = appProps.getUserSettings())
        currentScale = (float)settings->getDoubleValue("defaultScale", 1.0);
    currentScale = juce::jlimit(0.5f, 2.5f, currentScale);
    setSize(juce::roundToInt(kBaseW * currentScale), juce::roundToInt(kBaseH * currentScale));

    startTimerHz(33);
}

ObsidianB7000AudioProcessorEditor::~ObsidianB7000AudioProcessorEditor()
{
    setLookAndFeel(nullptr);
    stopTimer();
}

// ================================================================
// resized
// ================================================================
void ObsidianB7000AudioProcessorEditor::resized()
{
    currentScale = (float)getWidth() / (float)kBaseW;
    const float sc = currentScale;
    refreshFonts(sc);

    apvts.state.setProperty("uiScale", (double)currentScale, nullptr);
    scaleSaveDebounce.savedScale = currentScale;
    scaleSaveDebounce.startTimer(500);

    auto i = [sc](int v) { return juce::roundToInt((float)v * sc); };

    int panelH = getHeight() - i(kStripH);
    auto leftPanel  = juce::Rectangle<int>(0, 0, i(kPanelW), panelH);
    auto rightPanel = juce::Rectangle<int>(getWidth() - i(kPanelW), 0, i(kPanelW), panelH);

    // Face rect: force correct aspect ratio from base texture
    int faceRectX = i(kPanelW);
    int faceRectY = 0;
    int faceRectW = getWidth() - 2 * i(kPanelW);
    int faceRectH = faceRectW * kBaseTextureH / kBaseTextureW;
    if (faceRectH > panelH)
    {
        float fix = (float)panelH / (float)faceRectH;
        faceRectW = juce::roundToInt((float)faceRectW * fix);
        faceRectH = panelH;
        faceRectX = (getWidth() - faceRectW) / 2;
    }
    auto faceRect = juce::Rectangle<int>(faceRectX, faceRectY, faceRectW, faceRectH);
    auto stripRect = juce::Rectangle<int>(0, panelH, getWidth(), i(kStripH));

    // ── Centre face (ratio-based positions) ──
    for (auto& fc : faceComps)
    {
        int cw = juce::roundToInt(fc.w * (float)faceRectW);
        int ch = fc.h > 0.0f ? juce::roundToInt(fc.h * (float)faceRectH) : cw;
        int cx = juce::roundToInt(fc.cx * (float)faceRectW) + faceRectX;
        int cy = juce::roundToInt(fc.cy * (float)faceRectH) + faceRectY;
        fc.comp->setBounds(cx - cw / 2, cy - ch / 2, cw, ch);
    }

    // ── Left panel ──
    {
        int x = leftPanel.getX();
        int w = leftPanel.getWidth();
        int y = leftPanel.getY() + i(6);

        inputPanelLabel.setBounds(x, y, w, i(16));
        y += i(20);

        int trimSize = juce::jmin(w - i(8), i(64));
        inputTrimKnob.setBounds(x + (w - trimSize) / 2, y, trimSize, trimSize);
        y += trimSize + i(4);

        inputTrimSubLabel.setBounds(x, y, w, i(14));
        y += i(14);

        inputTrimValue.setBounds(x, y, w, i(12));
        y += i(16);

        inputVU.setBounds(x + i(4), y, w - i(8), leftPanel.getBottom() - y);
    }

    // ── Right panel ──
    {
        int x = rightPanel.getX();
        int w = rightPanel.getWidth();
        int y = rightPanel.getY() + i(6);

        outputPanelLabel.setBounds(x, y, w, i(16));
        y += i(20);

        int trimSize = juce::jmin(w - i(8), i(64));
        outputTrimKnob.setBounds(x + (w - trimSize) / 2, y, trimSize, trimSize);
        y += trimSize + i(4);

        outputTrimSubLabel.setBounds(x, y, w, i(14));
        y += i(14);

        outputTrimValue.setBounds(x, y, w, i(12));
        y += i(16);

        outputVU.setBounds(x + i(4), y, w - i(8), rightPanel.getBottom() - y);
    }

    // ── Bottom strip ──
    {
        int x = stripRect.getX() + i(6);
        int y = stripRect.getY();
        int h = stripRect.getHeight();

        auto placeLabel = [&](juce::Label& lbl, int w) {
            lbl.setBounds(x, y, w, h); x += w;
        };
        auto placeCombo = [&](juce::ComboBox& box, int w) {
            box.setBounds(x, y + i(2), w, h - i(4)); x += w + i(6);
        };
        auto placeBtn = [&](juce::TextButton& btn, int w) {
            btn.setBounds(x, y + i(2), w, h - i(4)); x += w + i(4);
        };

        placeLabel(osLabel, i(22));
        placeLabel(osLiveLabel, i(30));
        placeCombo(osRealtimeBox, i(36));
        placeLabel(osRenderLabel, i(44));
        placeCombo(osRenderBox, i(36));
        placeBtn(trimLinkBtn, i(62));
        placeBtn(hqBtn, i(30));

        int versionW = stripRect.getRight() - i(120) - x;
        if (versionW > i(10))
            versionLabel.setBounds(x, y, juce::jmin(i(80), versionW), h);
        x = stripRect.getRight() - i(120);

        placeLabel(uiSizeLabel, i(46));
        scaleBtn.setBounds(x, y + i(2), juce::jmax(i(48), i(48)), h - i(4));
    }

    refreshFonts(sc);
}

// ================================================================
// paint
// ================================================================
void ObsidianB7000AudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour(PedalLookAndFeel::cBackground));

    const float sc = currentScale;
    auto i = [sc](int v) { return juce::roundToInt((float)v * sc); };

    int panelH = getHeight() - i(kStripH);

    g.setColour(juce::Colour(0xFF080E1Au));
    g.fillRect(0, 0, i(kPanelW), panelH);
    g.fillRect(getWidth() - i(kPanelW), 0, i(kPanelW), panelH);

    int faceRectX = i(kPanelW);
    int faceRectY = 0;
    int faceRectW = getWidth() - 2 * i(kPanelW);
    int faceRectH = faceRectW * kBaseTextureH / kBaseTextureW;
    if (faceRectH > panelH)
    {
        float fix = (float)panelH / (float)faceRectH;
        faceRectW = juce::roundToInt((float)faceRectW * fix);
        faceRectH = panelH;
        faceRectX = (getWidth() - faceRectW) / 2;
    }
    auto faceRect = juce::Rectangle<int>(faceRectX, faceRectY, faceRectW, faceRectH);

    if (baseTexture.isValid())
    {
        g.drawImage(baseTexture,
                    faceRectX, faceRectY, faceRectW, faceRectH,
                    0, 0, baseTexture.getWidth(), baseTexture.getHeight(),
                    false);
    }
    else
    {
        g.setColour(juce::Colour(PedalLookAndFeel::cPedalFace));
        g.fillRoundedRectangle(faceRect.toFloat(), 16.0f);
    }

    auto stripR = juce::Rectangle<int>(0, panelH, getWidth(), i(kStripH));
    g.setColour(juce::Colour(PedalLookAndFeel::cOSBackground));
    g.fillRoundedRectangle(stripR.toFloat(), 4.0f);
    g.setColour(juce::Colour(PedalLookAndFeel::cOSBorder));
    g.drawRoundedRectangle(stripR.reduced(1).toFloat(), 4.0f, 1.0f);
}

// ================================================================
// Font scaling
// ================================================================
void ObsidianB7000AudioProcessorEditor::refreshFonts(float sc)
{
    auto bold = [sc](float sz) {
        return juce::Font(juce::FontOptions(sz * sc, juce::Font::bold));
    };
    auto plain = [sc](float sz) {
        return juce::Font(juce::FontOptions(sz * sc, juce::Font::plain));
    };
    auto lex = [sc, this](float sz) {
        auto f = lexendFont;
        f.setHeight(sz * sc);
        return f;
    };

    inputPanelLabel.setFont(bold(8.0f).withExtraKerningFactor(0.20f));
    outputPanelLabel.setFont(bold(8.0f).withExtraKerningFactor(0.20f));
    inputTrimSubLabel.setFont(bold(7.5f));
    outputTrimSubLabel.setFont(bold(7.5f));
    inputTrimValue.setFont(bold(7.0f));
    outputTrimValue.setFont(bold(7.0f));
    osLabel.setFont(bold(8.0f).withExtraKerningFactor(0.15f));
    osLiveLabel.setFont(bold(7.0f));
    osRenderLabel.setFont(bold(7.0f));
    uiSizeLabel.setFont(bold(7.0f));
    loMidText.setFont(lex(14.0f));
    hiMidText.setFont(lex(14.0f));
    versionLabel.setFont(plain(7.0f).withExtraKerningFactor(0.1f));
}

// ================================================================
// trimToDB: convert normalized 0..1 to -12..+12 dB
// ================================================================
float ObsidianB7000AudioProcessorEditor::trimToDB(float normalized)
{
    return (normalized - 0.5f) * 24.0f;
}

// ================================================================
// Timer (VU + LEDs + knobs + labels)
// ================================================================
void ObsidianB7000AudioProcessorEditor::timerCallback()
{
    // Sync knob values from APVTS
    for (int i = 0; i < kNumKnobs; ++i)
        knobSliders[i].updateValue();
    inputTrimKnob.updateValue();
    outputTrimKnob.updateValue();

    // Trim value labels
    auto fmtTrim = [this](const KnobComponent& knob) -> juce::String
    {
        float db = trimToDB(knob.getNormalizedValue());
        return (db >= 0.0f ? "+" : "") + juce::String(db, 2) + " dB";
    };
    inputTrimValue.setText(fmtTrim(inputTrimKnob), juce::dontSendNotification);
    outputTrimValue.setText(fmtTrim(outputTrimKnob), juce::dontSendNotification);

    // LEDs
    auto* pBypass = apvts.getRawParameterValue("bypass");
    auto* pDist   = apvts.getRawParameterValue("dist_engage");
    bool bypassed = (pBypass && pBypass->load() > 0.5f);
    bool distOn   = (pDist   && pDist->load() > 0.5f);
    bypassLED.setOn(!bypassed);
    distLED.setOn(distOn);

    // Sync toggle states
    auto syncSwitch = [](juce::AudioParameterChoice* p, SwitchToggle& toggle,
                         AttackGruntIcons* icons, SwitchLabelText* text,
                         const int* posMap)
    {
        if (p == nullptr) return;
        int val = p->getIndex();
        int pos = val;
        if (posMap)
        {
            for (int i = 0; i < 3; ++i)
                if (posMap[i] == val) { pos = i; break; }
        }
        toggle.setPosition(pos);
        if (icons) icons->setPosition(pos);
        if (text)  text->setPosition(pos);
    };

    auto* attackP = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("attack"));
    auto* gruntP  = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("grunt"));
    auto* loMidP  = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("lo_mid_freq"));
    auto* hiMidP  = dynamic_cast<juce::AudioParameterChoice*>(apvts.getParameter("hi_mid_freq"));

    static constexpr int loMidMap[] = { 2, 0, 1 };
    static constexpr int hiMidMap[] = { 2, 0, 1 };

    syncSwitch(attackP, attackToggle, &attackIcons, nullptr, nullptr);
    syncSwitch(gruntP,  gruntToggle,  &gruntIcons,  nullptr, nullptr);
    syncSwitch(loMidP,  loMidToggle,  nullptr,      &loMidText, loMidMap);
    syncSwitch(hiMidP,  hiMidToggle,  nullptr,      &hiMidText, hiMidMap);

    // VU
    static float inLevel = 0.0f, outLevel = 0.0f;
    static constexpr float kNoiseFloor = 5e-4f;

    inLevel = juce::jmax(processor.inputLevel.load(), inLevel * 0.90f);
    outLevel = juce::jmax(processor.outputLevel.load(), outLevel * 0.90f);
    if (inLevel < kNoiseFloor)  inLevel = 0.0f;
    if (outLevel < kNoiseFloor) outLevel = 0.0f;

    inputVU.setLevel(inLevel);
    outputVU.setLevel(outLevel);
}
