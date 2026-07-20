#include "PedalFace.h"

#include <BinaryData.h>

using namespace juce;

static const float kPi = MathConstants<float>::pi;

PedalFace::PedalFace(AudioProcessorValueTreeState& apvts)
    : state(apvts)
{
    baseTexture = ImageCache::getFromMemory(
        BinaryData::b7k_texture_base_png,
        BinaryData::b7k_texture_base_pngSize);

    {
        auto tf = Typeface::createSystemTypefaceFor(
            BinaryData::LexendExaRegular_ttf,
            BinaryData::LexendExaRegular_ttfSize);
        if (tf != nullptr)
            lexendFont = Font(FontOptions(tf));
        if (lexendFont.getTypefacePtr() == nullptr)
            lexendFont = Font(FontOptions(14.0f));
    }

    buildComponents();
}

void PedalFace::buildComponents()
{
    // ── Knobs ──
    for (int i = 0; i < kNumKnobs; ++i)
    {
        auto& s = knobSliders[i];
        s.setSliderStyle(Slider::RotaryHorizontalVerticalDrag);
        s.setRotaryParameters(kPi * 1.25f, kPi * 2.75f, true);
        s.setTextBoxStyle(Slider::NoTextBox, false, 0, 0);
        s.setPopupDisplayEnabled(true, false, this);
        addAndMakeVisible(s);
        knobAttachments[i] = std::make_unique<SliderParameterAttachment>(
            *state.getParameter(kKnobParamIDs[i]), s);
        s.textFromValueFunction = [](double v) { return String(v, 2); };
    }

    // ── Footswitches ──
    auto setupFS = [this](TextButton& btn) {
        btn.setComponentID("bypass");
        btn.setClickingTogglesState(true);
        addAndMakeVisible(btn);
    };
    setupFS(bypassFS);
    setupFS(distFS);
    bypassAttach = std::make_unique<ButtonParameterAttachment>(
        *state.getParameter("bypass"), bypassFS);
    distAttach = std::make_unique<ButtonParameterAttachment>(
        *state.getParameter("dist_engage"), distFS);

    // ── LEDs ──
    auto loadLED = [](const char* data, int sz) -> Image {
        return data ? ImageCache::getFromMemory(data, sz) : Image{};
    };
    Image onImg  = loadLED(BinaryData::blue_led_on_png,  BinaryData::blue_led_on_pngSize);
    Image offImg = loadLED(BinaryData::blue_led_off_png, BinaryData::blue_led_off_pngSize);
    bypassLED.setImages(onImg, offImg);
    distLED.setImages(onImg, offImg);
    addAndMakeVisible(bypassLED);
    addAndMakeVisible(distLED);

    // ── Icons & text (added before toggles so toggles draw on top) ──
    addAndMakeVisible(attackIcons);
    addAndMakeVisible(gruntIcons);
    loMidText.setLabels("500 Hz", "1 kHz", "250 Hz");
    hiMidText.setLabels("1.5 kHz", "3 kHz", "750 Hz");
    addAndMakeVisible(loMidText);
    addAndMakeVisible(hiMidText);

    // ── Switch toggles ──
    Image switchImgs[3] = {
        loadLED(BinaryData::switch_up_png,   BinaryData::switch_up_pngSize),
        loadLED(BinaryData::switch_Mid_png,  BinaryData::switch_Mid_pngSize),
        loadLED(BinaryData::switch_down_png, BinaryData::switch_down_pngSize)
    };
    auto setupToggle = [&](SwitchToggle& t, int def) {
        t.setImages(switchImgs[0], switchImgs[1], switchImgs[2]);
        t.setPosition(def);
        addAndMakeVisible(t);
    };
    setupToggle(attackToggle, 0);
    setupToggle(gruntToggle,  0);
    setupToggle(loMidToggle,  2);
    setupToggle(hiMidToggle,  2);

    attackToggle.onChange = [this](int pos) {
        if (auto* p = dynamic_cast<AudioParameterChoice*>(state.getParameter("attack")))
        {
            p->beginChangeGesture();
            p->setValueNotifyingHost(p->getNormalisableRange().convertTo0to1((float)pos));
            p->endChangeGesture();
        }
    };
    gruntToggle.onChange = [this](int pos) {
        if (auto* p = dynamic_cast<AudioParameterChoice*>(state.getParameter("grunt")))
        {
            p->beginChangeGesture();
            p->setValueNotifyingHost(p->getNormalisableRange().convertTo0to1((float)pos));
            p->endChangeGesture();
        }
    };
    loMidToggle.onChange = [this](int pos) {
        static constexpr int m[] = { 1, 2, 0 };
        if (auto* p = dynamic_cast<AudioParameterChoice*>(state.getParameter("lo_mid_freq")))
        {
            p->beginChangeGesture();
            p->setValueNotifyingHost(p->getNormalisableRange().convertTo0to1((float)m[pos]));
            p->endChangeGesture();
        }
    };
    hiMidToggle.onChange = [this](int pos) {
        static constexpr int m[] = { 1, 2, 0 };
        if (auto* p = dynamic_cast<AudioParameterChoice*>(state.getParameter("hi_mid_freq")))
        {
            p->beginChangeGesture();
            p->setValueNotifyingHost(p->getNormalisableRange().convertTo0to1((float)m[pos]));
            p->endChangeGesture();
        }
    };

    // ── Position map (ratios of 1960×1540 base texture) ──
    components = {
        { &knobSliders[0], { 0.165816f, 0.165584f, 0.158163f, 0.0f       } },
        { &knobSliders[1], { 0.390306f, 0.165584f, 0.158163f, 0.0f       } },
        { &knobSliders[2], { 0.611224f, 0.165584f, 0.158163f, 0.0f       } },
        { &knobSliders[3], { 0.837755f, 0.165584f, 0.158163f, 0.0f       } },
        { &knobSliders[4], { 0.165816f, 0.451299f, 0.158163f, 0.0f       } },
        { &knobSliders[5], { 0.390306f, 0.451299f, 0.158163f, 0.0f       } },
        { &knobSliders[6], { 0.611224f, 0.451299f, 0.158163f, 0.0f       } },
        { &knobSliders[7], { 0.837755f, 0.451299f, 0.158163f, 0.0f       } },
        { &distFS,         { 0.175510f, 0.859091f, 0.135204f, 0.0f       } },
        { &bypassFS,       { 0.825000f, 0.859091f, 0.135204f, 0.0f       } },
        { &distLED,        { 0.165306f, 0.679221f, 0.043367f, 0.0f       } },
        { &bypassLED,      { 0.835204f, 0.679221f, 0.043367f, 0.0f       } },
        { &attackToggle,   { 0.278061f, 0.325974f, 0.074490f, 0.0f       } },
        { &attackIcons,    { 0.278061f, 0.407663f, 0.056122f, 0.050000f  } },
        { &gruntToggle,    { 0.725510f, 0.325974f, 0.074490f, 0.0f       } },
        { &gruntIcons,     { 0.725510f, 0.407663f, 0.056122f, 0.050000f  } },
        { &loMidToggle,    { 0.278061f, 0.569481f, 0.074490f, 0.0f       } },
        { &loMidText,      { 0.278061f, 0.653766f, 0.085000f, 0.071429f  } },
        { &hiMidToggle,    { 0.725510f, 0.569481f, 0.074490f, 0.0f       } },
        { &hiMidText,      { 0.725510f, 0.653766f, 0.085000f, 0.071429f  } },
    };

    positionComponents();
}

void PedalFace::positionComponents()
{
    const float FW = (float)getWidth();
    const float FH = (float)getHeight();
    if (FW <= 0.0f || FH <= 0.0f) return;

    for (auto& cp : components)
    {
        float cw = cp.pos.rw * FW;
        float ch = cp.pos.rh > 0.0f ? cp.pos.rh * FH : cw;
        float cx = cp.pos.rx * FW;
        float cy = cp.pos.ry * FH;
        cp.comp->setBounds(roundToInt(cx - cw * 0.5f), roundToInt(cy - ch * 0.5f),
                           roundToInt(cw), roundToInt(ch));
    }
}

void PedalFace::paint(Graphics& g)
{
    auto b = getLocalBounds().toFloat();
    if (b.isEmpty()) return;

    if (baseTexture.isValid())
    {
        g.drawImage(baseTexture, b, RectanglePlacement::stretchToFit, false);
    }
    else
    {
        g.setColour(Colour(PedalLookAndFeel::cPedalFace));
        g.fillRoundedRectangle(b, 8.0f);
    }
}

void PedalFace::resized()
{
    positionComponents();
}

void PedalFace::refresh(float sc)
{
    scale = sc;
    auto lex = [this, sc](float sz) {
        auto f = lexendFont;
        f.setHeight(jmax(5.0f, sz * sc));
        return f;
    };
    loMidText.setFont(lex(9.0f));
    hiMidText.setFont(lex(9.0f));
}

void PedalFace::updateLEDs()
{
    auto read = [this](const char* id) {
        auto* p = state.getRawParameterValue(id);
        return p != nullptr && p->load() > 0.5f;
    };
    bypassLED.setOn(!read("bypass"));
    distLED.setOn(read("dist_engage"));

    auto syncChoice = [this](const char* id, SwitchToggle& t,
                              AttackGruntIcons* icons, SwitchLabelText* text,
                              const int* map) {
        if (auto* p = dynamic_cast<AudioParameterChoice*>(state.getParameter(id)))
        {
            int val = p->getIndex();
            int pos = val;
            if (map) for (int i = 0; i < 3; ++i) if (map[i] == val) { pos = i; break; }
            t.setPosition(pos, false);
            if (icons) icons->setPosition(pos);
            if (text)  text->setPosition(pos);
        }
    };
    static constexpr int midMap[] = { 2, 0, 1 };
    syncChoice("attack",      attackToggle,  &attackIcons, nullptr,       nullptr);
    syncChoice("grunt",       gruntToggle,   &gruntIcons,  nullptr,       nullptr);
    syncChoice("lo_mid_freq", loMidToggle,   nullptr,      &loMidText,    midMap);
    syncChoice("hi_mid_freq", hiMidToggle,   nullptr,      &hiMidText,    midMap);
}
