#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class ImageLED : public juce::Component
{
public:
    void setImages(const juce::Image& on, const juce::Image& off)
    {
        imageOn = on;
        imageOff = off;
    }

    void setOn(bool on)
    {
        if (on != isOn)
        {
            isOn = on;
            repaint();
        }
    }

    void paint(juce::Graphics& g) override
    {
        auto b = getLocalBounds().toFloat();
        auto& img = isOn ? imageOn : imageOff;
        if (img.isValid() && !b.isEmpty())
            g.drawImage(img, b,
                        juce::RectanglePlacement::centred
                            | juce::RectanglePlacement::onlyReduceInSize,
                        false);
    }

private:
    juce::Image imageOn, imageOff;
    bool isOn = false;
};
