#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class SwitchLabelText : public juce::Component
{
public:
    void setLabels(const juce::String& top, const juce::String& mid, const juce::String& bot)
    {
        labels[0] = top;
        labels[1] = mid;
        labels[2] = bot;
        repaint();
    }

    void setFont(const juce::Font& f) { labelFont = f; }

    void setPosition(int pos)
    {
        if (pos != position) { position = pos; repaint(); }
    }

    int getPosition() const { return position; }

    // Fired when the user clicks one of the three label rows (top/mid/bottom third).
    // Wire this to the paired toggle so the label doubles as a click target.
    std::function<void(int)> onSelect;

    void mouseDown(const juce::MouseEvent& e) override
    {
        auto b = getLocalBounds().toFloat();
        if (b.isEmpty()) return;
        const float relY = e.position.y - b.getY();
        if (relY < 0.0f || relY >= b.getHeight()) return;
        const int pos = juce::jlimit(0, 2, (int)(relY / (b.getHeight() / 3.0f)));
        if (onSelect) onSelect(pos);
    }

    void paint(juce::Graphics& g) override
    {
        auto b = getLocalBounds().toFloat();
        if (b.isEmpty()) return;

        g.setFont(labelFont);
        float lineH = g.getCurrentFont().getHeight();
        float gap = lineH * 0.25f;
        float totalH = lineH * 3.0f + gap * 2.0f;
        float startY = b.getCentreY() - totalH * 0.5f;

        for (int n = 0; n < 3; ++n)
        {
            float alpha = (n == position) ? 1.0f : 0.45f;
            g.setColour(juce::Colours::white.withAlpha(alpha));
            float topY = startY + (float)n * (lineH + gap);
            g.drawText(labels[n],
                       juce::Rectangle<float>(b.getX(), topY, b.getWidth(), lineH),
                       juce::Justification::centred, false);
        }
    }

private:
    int position { 0 };
    juce::String labels[3] { "A", "B", "C" };
    juce::Font labelFont { juce::Font(juce::FontOptions(12.0f)) };
};
