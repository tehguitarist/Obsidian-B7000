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

    // Fired when the user clicks one of the three glyph rows (top/mid/bottom third).
    // Wire this to the paired toggle so the icon column doubles as a click target.
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
        if (b.isEmpty())
            return;

        float sc = b.getHeight() / 77.0f;
        float section = b.getHeight() / 3.0f;

        float pad = 7.0f * sc;
        float left = b.getX() + pad;
        float right = b.getRight() - pad;

        // Narrowed, kept centred.
        float cx = b.getCentreX();
        left = cx - (cx - left) * 0.72f;
        right = cx + (right - cx) * 0.72f;

        // A smooth "shelf" glyph: flat segment -> S-transition -> flat segment.
        // yL/yR are the heights of the two flat runs (screen coords, smaller y =
        // higher). cc is the transition CENTRE as a fraction of the width, so a
        // late cc gives a long leading (left) flat, an early cc a long trailing
        // (right) flat. Horizontal tangents at both flats give a clean S.
        auto shelf = [&](juce::Path& p, float yL, float yR, float cc)
        {
            float w = right - left;
            float tw = 0.44f * w;                 // transition width (wider = gentler S)
            float x1 = left + cc * w - tw * 0.5f; // curve start (end of left flat)
            float x2 = left + cc * w + tw * 0.5f; // curve end (start of right flat)
            float xm = (x1 + x2) * 0.5f;
            p.startNewSubPath(left, yL);
            p.lineTo(x1, yL);
            p.cubicTo(xm, yL, xm, yR, x2, yR);
            p.lineTo(right, yR);
        };

        constexpr float ccLate = 0.64f;  // long flat on the LEFT  (Attack)
        constexpr float ccEarly = 0.36f; // long flat on the RIGHT (Grunt)

        // Per-glyph shape: dir = 0 flat, -1 curves up at the end, +1 curves down.
        int dir[3];
        float cc[3];
        if (iconType == Type::Attack)
        {
            dir[0] = 0;  cc[0] = 0.5f;    // flat
            dir[1] = -1; cc[1] = ccLate;  // flat, then curve up
            dir[2] = +1; cc[2] = ccLate;  // flat, then curve down
        }
        else // Grunt
        {
            dir[0] = +1; cc[0] = ccEarly; // down curve, then flat
            dir[1] = -1; cc[1] = ccEarly; // up curve, then flat
            dir[2] = 0;  cc[2] = 0.5f;    // flat
        }

        // Lay out by INK EXTENT, not centreline: each glyph occupies a vertical
        // band of height `h` (dev for a curved glyph, 0 for a flat line), and the
        // GAPS between adjacent bands are made equal, with the group centred. This
        // keeps the whitespace above/below each icon consistent even though the
        // curves reach into the gaps by different amounts.
        float H = b.getHeight();
        float dev = section * 0.27f;
        float mg = 0.07f * H; // top/bottom margin

        float h[3];
        for (int n = 0; n < 3; ++n)
            h[n] = (dir[n] == 0) ? 0.0f : dev;
        float gap = ((H - 2.0f * mg) - (h[0] + h[1] + h[2])) * 0.5f;

        float cursor = b.getY() + mg;
        for (int n = 0; n < 3; ++n)
        {
            float alpha = (n == position) ? 1.0f : 0.45f;
            g.setColour(juce::Colours::white.withAlpha(alpha));

            float tOff = (dir[n] < 0) ? -dev : 0.0f; // ink top relative to baseline
            float baseY = cursor - tOff;             // left flat level
            float yR = baseY + (float)dir[n] * dev;  // curved end level

            juce::Path p;
            shelf(p, baseY, yR, cc[n]);
            g.strokePath(p, juce::PathStrokeType(juce::jmax(2.0f, 2.9f * sc),
                                                 juce::PathStrokeType::curved,
                                                 juce::PathStrokeType::rounded));

            cursor += h[n] + gap;
        }
    }

private:
    Type iconType;
    int position { 0 };
};
