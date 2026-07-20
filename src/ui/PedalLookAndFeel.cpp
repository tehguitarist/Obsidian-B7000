#include "PedalLookAndFeel.h"

using namespace juce;

PedalLookAndFeel::PedalLookAndFeel()
{
    setColour(PopupMenu::backgroundColourId, Colour(0xFF0A1628u));
    setColour(PopupMenu::textColourId, Colour(cOSBtnActive));
    setColour(PopupMenu::highlightedBackgroundColourId, Colour(cOSBtnActiveBg));
    setColour(PopupMenu::highlightedTextColourId, Colour(0xFFF5F5F5u));
}

// ============================ drawTrimHalo (shared-look) ============================

void PedalLookAndFeel::drawTrimHalo(Graphics& g, Rectangle<float> bounds, float sliderPos,
                                     float startAngle, float endAngle)
{
    const float diameter = jmin(bounds.getWidth(), bounds.getHeight());
    const float cx = bounds.getCentreX();
    const float cy = bounds.getCentreY();
    const float arcW = diameter * (5.0f / 70.0f);
    const float arcR = diameter * 0.5f - arcW * 0.5f - 1.0f;
    const float capR = diameter * (18.0f / 70.0f);
    const float toAngle = startAngle + sliderPos * (endAngle - startAngle);

    Path track;
    track.addCentredArc(cx, cy, arcR, arcR, 0.0f, startAngle, endAngle, true);
    g.setColour(Colour(cTrimArcTrack));
    g.strokePath(track, PathStrokeType(arcW, PathStrokeType::curved, PathStrokeType::rounded));

    Path value;
    value.addCentredArc(cx, cy, arcR, arcR, 0.0f, startAngle, toAngle, true);
    g.setColour(Colour(cTrimArc));
    g.strokePath(value, PathStrokeType(arcW, PathStrokeType::curved, PathStrokeType::rounded));

    if (trimImage.isValid())
    {
        const float noonAngle = 0.5f * (startAngle + endAngle);
        const Rectangle<float> dest(cx - capR, cy - capR, capR * 2.0f, capR * 2.0f);
        Graphics::ScopedSaveState save(g);
        g.addTransform(AffineTransform::rotation(toAngle - noonAngle, cx, cy));
        g.drawImage(trimImage, dest, RectanglePlacement::centred, false);
    }
}

// ============================ drawKnobFromImage ============================

void PedalLookAndFeel::drawKnobFromImage(Graphics& g, const Image& img, Rectangle<float> bounds,
                                          float sliderPos, float startAngle, float endAngle)
{
    if (!img.isValid()) return;

    const float d = jmin(bounds.getWidth(), bounds.getHeight());
    const float toAngle = startAngle + sliderPos * (endAngle - startAngle);
    const float noonAngle = 0.5f * (startAngle + endAngle);
    const Rectangle<float> dest(bounds.getCentreX() - d * 0.5f, bounds.getCentreY() - d * 0.5f, d, d);

    Graphics::ScopedSaveState save(g);
    g.addTransform(AffineTransform::rotation(toAngle - noonAngle, bounds.getCentreX(), bounds.getCentreY()));
    g.drawImage(img, dest, RectanglePlacement::centred, false);
}

// ============================ drawRotarySlider ============================

void PedalLookAndFeel::drawRotarySlider(Graphics& g, int x, int y, int w, int h,
                                         float sliderPos, float startAngle, float endAngle,
                                         Slider& s)
{
    const auto bounds = Rectangle<int>(x, y, w, h).toFloat();
    const auto id = s.getComponentID();
    if (id == "trim")
        drawTrimHalo(g, bounds, sliderPos, startAngle, endAngle);
    else
        drawKnobFromImage(g, knobImage, bounds, sliderPos, startAngle, endAngle);
}

// ============================ drawButtonBackground ============================

void PedalLookAndFeel::drawButtonBackground(Graphics& g, Button& button, const Colour& bg,
                                              bool highlighted, bool isDown)
{
    if (button.getComponentID() == "bypass")
    {
        const Image& img = isDown ? fsDownImage : fsUpImage;
        if (!img.isValid()) return;
        const auto b = button.getLocalBounds().toFloat();
        const float d = jmin(b.getWidth(), b.getHeight());
        const Rectangle<float> dest(b.getCentreX() - d * 0.5f, b.getCentreY() - d * 0.5f, d, d);
        g.drawImage(img, dest, RectanglePlacement::centred, false);
        return;
    }
    if (button.getComponentID() == "scale")
    {
        const auto bounds = button.getLocalBounds().toFloat();
        const float corner = 4.0f;
        g.setColour(isDown ? Colour(cOSBtnActiveBdr).withAlpha(0.4f) : bg);
        g.fillRoundedRectangle(bounds, corner);
        g.setColour(Colour(cOSBtnActiveBdr));
        g.drawRoundedRectangle(bounds.reduced(0.5f), corner, 1.0f);
        return;
    }
    if (button.getComponentID() == "os")
    {
        const auto b = button.getLocalBounds().toFloat();
        const bool active = button.getToggleState();
        const float corner = 4.0f;
        g.setColour(active ? Colour(cOSBtnActiveBg) : Colour(0xFF0C1828u));
        g.fillRoundedRectangle(b, corner);
        g.setColour(active ? Colour(cOSBtnActiveBdr) : Colour(0xFF182840u));
        g.drawRoundedRectangle(b.reduced(0.5f), corner, 1.0f);
        if (active)
        {
            g.setColour(Colour(cOSBtnActiveBdr).withAlpha(0.3f));
            g.drawRoundedRectangle(b.expanded(1.5f), corner + 1.5f, 1.5f);
        }
        return;
    }
    LookAndFeel_V4::drawButtonBackground(g, button, bg, highlighted, isDown);
}

// ============================ drawButtonText ============================

void PedalLookAndFeel::drawButtonText(Graphics& g, TextButton& button, bool, bool down)
{
    if (button.getComponentID() == "scale")
    {
        g.setColour(Colour(cOSBtnActive));
        g.setFont(Font(FontOptions(jmax(7.0f, (float)button.getHeight() * 0.38f), Font::bold)));
        auto area = button.getLocalBounds();
        if (down) area = area.translated(0, 1);
        g.drawText(button.getButtonText(), area, Justification::centred, false);
        return;
    }
    const bool active = button.getToggleState();
    const Colour col = active ? Colour(cOSBtnActive) : Colour(cOSLabel);
    g.setColour(col);
    g.setFont(Font(FontOptions(8.0f, Font::bold)));
    auto area = button.getLocalBounds();
    if (down) area = area.translated(0, 1);
    g.drawText(button.getButtonText(), area, Justification::centred, false);
}

// ============================ drawLabel ============================

void PedalLookAndFeel::drawLabel(Graphics& g, Label& label)
{
    if (!label.isBeingEdited())
    {
        g.setColour(label.findColour(Label::textColourId));
        g.setFont(label.getFont());
        g.drawText(label.getText(), label.getLocalBounds(), label.getJustificationType(), true);
    }
}

// ============================ drawComboBox ============================

void PedalLookAndFeel::drawComboBox(Graphics& g, int width, int height, bool isButtonDown,
                                      int, int, int, int, ComboBox&)
{
    const float corner = 4.0f;
    auto bounds = Rectangle<float>(0.0f, 0.0f, (float)width, (float)height);
    g.setColour(isButtonDown ? Colour(cOSBtnActiveBdr).withAlpha(0.4f) : Colour(cOSBtnActiveBg));
    g.fillRoundedRectangle(bounds, corner);
    g.setColour(Colour(cOSBtnActiveBdr));
    g.drawRoundedRectangle(bounds.reduced(0.5f), corner, 1.0f);

    const float arrowCX = bounds.getRight() - 8.0f, arrowCY = bounds.getCentreY();
    Path arrow;
    arrow.startNewSubPath(arrowCX - 2.5f, arrowCY - 1.5f);
    arrow.lineTo(arrowCX, arrowCY + 1.5f);
    arrow.lineTo(arrowCX + 2.5f, arrowCY - 1.5f);
    g.setColour(Colour(cOSLabel));
    g.strokePath(arrow, PathStrokeType(1.2f, PathStrokeType::curved, PathStrokeType::rounded));
}

Font PedalLookAndFeel::getComboBoxFont(ComboBox& box)
{
    return Font(FontOptions(jmax(7.0f, (float)box.getHeight() * 0.38f), Font::bold));
}

void PedalLookAndFeel::positionComboBoxText(ComboBox& box, Label& label)
{
    label.setBounds(0, 0, box.getWidth(), box.getHeight());
    label.setFont(getComboBoxFont(box));
}
