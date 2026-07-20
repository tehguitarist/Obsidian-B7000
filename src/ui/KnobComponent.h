#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class KnobComponent : public juce::Component
{
public:
    void setImage(const juce::Image& img) { knobImage = img; }

    void setParameter(juce::RangedAudioParameter* p)
    {
        parameter = p;
        if (parameter != nullptr)
            currentValue = parameter->getValue();
    }

    void updateValue()
    {
        if (parameter == nullptr) return;
        float v = parameter->getValue();
        if (std::abs(v - currentValue) > 0.001f)
        {
            currentValue = v;
            repaint();
        }
    }

    float getNormalizedValue() const { return currentValue; }

    void paint(juce::Graphics& g) override
    {
        auto b = getLocalBounds().toFloat();
        if (!knobImage.isValid() || b.isEmpty())
            return;

        float cx = b.getCentreX();
        float cy = b.getCentreY();
        float angle = (currentValue - 0.5f) * juce::MathConstants<float>::pi * 1.5f;
        float scale = juce::jmin(b.getWidth() / knobImage.getWidth(),
                                 b.getHeight() / knobImage.getHeight());

        float iw = (float)knobImage.getWidth();
        float ih = (float)knobImage.getHeight();
        auto t = juce::AffineTransform::translation(-iw * 0.5f, -ih * 0.5f)
                    .scaled(scale, scale)
                    .rotated(-angle)
                    .translated(cx, cy);

        g.drawImageTransformed(knobImage, t, false);
    }

    void mouseDown(const juce::MouseEvent& e) override
    {
        if (parameter == nullptr) return;
        dragStartValue = parameter->getValue();
        dragStartMouseY = e.position.y;
        parameter->beginChangeGesture();
    }

    void mouseUp(const juce::MouseEvent&) override
    {
        if (parameter) parameter->endChangeGesture();
    }

    void mouseDrag(const juce::MouseEvent& e) override
    {
        if (parameter == nullptr) return;
        float delta = (dragStartMouseY - e.position.y) / 200.0f;
        float newVal = juce::jlimit(0.0f, 1.0f, dragStartValue + delta);
        currentValue = newVal;
        parameter->setValueNotifyingHost(newVal);
        repaint();
    }

private:
    juce::Image knobImage;
    juce::RangedAudioParameter* parameter = nullptr;
    float currentValue = 0.5f;
    float dragStartValue = 0.5f;
    float dragStartMouseY = 0.0f;
};
