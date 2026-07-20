#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class SwitchToggle : public juce::Component
{
public:
    std::function<void(int)> onChange;

    void setPosition(int pos)
    {
        pos = juce::jlimit(0, 2, pos);
        if (pos != position)
        {
            position = pos;
            repaint();
            if (onChange)
                onChange(position);
        }
    }

    int getPosition() const { return position; }

    void setImages(const juce::Image& up, const juce::Image& mid, const juce::Image& down)
    {
        images[0] = up;
        images[1] = mid;
        images[2] = down;
    }

    void paint(juce::Graphics& g) override
    {
        auto b = getLocalBounds().toFloat();
        if (images[position].isValid())
        {
            auto& img = images[position];
            g.drawImage(img, b, juce::RectanglePlacement::centred | juce::RectanglePlacement::onlyReduceInSize, false);
        }
    }

    void mouseDown(const juce::MouseEvent& e) override { updateFromMouse(e.position.y); }
    void mouseDrag(const juce::MouseEvent& e) override { updateFromMouse(e.position.y); }

private:
    int position { 0 };
    juce::Image images[3];

    void updateFromMouse(float mouseY)
    {
        auto b = getLocalBounds().toFloat();
        float section = b.getHeight() / 3.0f;
        float relY = mouseY - b.getY();

        if (relY >= 0.0f && relY < b.getHeight())
        {
            int newPos = juce::jlimit(0, 2, (int)(relY / section));
            if (newPos != position)
            {
                position = newPos;
                repaint();
                if (onChange)
                    onChange(position);
            }
        }
    }
};
