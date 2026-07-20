#pragma once
#include <juce_gui_basics/juce_gui_basics.h>

class AttackGruntIcons : public juce::Component
{
public:
    enum class Type { Attack, Grunt };

    AttackGruntIcons(Type type) : iconType(type) {}

    void setPosition(int pos)
    {
        if (pos != position)
        {
            position = pos;
            repaint();
        }
    }

    int getPosition() const { return position; }

    void paint(juce::Graphics& g) override
    {
        auto b = getLocalBounds().toFloat();
        if (b.isEmpty())
            return;

        float sc = b.getHeight() / 77.0f;
        float section = b.getHeight() / 3.0f;

        for (int n = 0; n < 3; ++n)
        {
            float alpha = (n == position) ? 1.0f : 0.45f;
            g.setColour(juce::Colours::white.withAlpha(alpha));

            juce::Path p;
            float topY = b.getY() + (float)n * section;
            float pad = 6.0f * sc;
            float left = b.getX() + pad;
            float right = b.getRight() - pad;
            float midX = (left + right) * 0.5f;
            float yOff = section * 0.3f;

            if (iconType == Type::Attack)
            {
                float lineY = topY + section * 0.4f;
                if (n == 0)
                {
                    p.startNewSubPath(left, lineY);
                    p.lineTo(right, lineY);
                }
                else if (n == 1)
                {
                    p.startNewSubPath(left, lineY + yOff);
                    p.lineTo(midX, lineY + yOff * 0.3f);
                    p.lineTo(right, lineY);
                }
                else
                {
                    p.startNewSubPath(left, lineY);
                    p.lineTo(midX, lineY + yOff * 0.7f);
                    p.lineTo(right, lineY + yOff);
                }
            }
            else
            {
                float baseY = topY + section * 0.5f;
                float amp = section * 0.25f;
                if (n == 0)
                {
                    p.startNewSubPath(left, baseY + amp);
                    p.quadraticTo(left * 0.75f + right * 0.25f, baseY - amp,
                                  midX, baseY - amp * 0.3f);
                    p.quadraticTo(left * 0.25f + right * 0.75f, baseY + amp * 0.2f,
                                  right, baseY + amp);
                }
                else if (n == 1)
                {
                    p.startNewSubPath(left, baseY);
                    p.quadraticTo(left * 0.75f + right * 0.25f, baseY + amp * 0.5f,
                                  midX, baseY);
                    p.quadraticTo(left * 0.25f + right * 0.75f, baseY - amp * 0.8f,
                                  right, baseY);
                }
                else
                {
                    p.startNewSubPath(left, baseY + amp * 0.3f);
                    p.quadraticTo(left * 0.75f + right * 0.25f, baseY - amp * 0.3f,
                                  midX, baseY - amp * 0.7f);
                    p.quadraticTo(left * 0.25f + right * 0.75f, baseY + amp * 0.3f,
                                  right, baseY + amp);
                }
            }

            g.strokePath(p, juce::PathStrokeType(juce::jmax(1.5f, 2.0f * sc)));
        }
    }

private:
    Type iconType;
    int position { 0 };
};
