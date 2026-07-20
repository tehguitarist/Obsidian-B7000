#pragma once

class PedalDSP
{
public:
    PedalDSP() = default;
    ~PedalDSP() = default;

    void prepare(double /*sampleRate*/, int /*samplesPerBlock*/) {}
    void reset() {}

private:
    JUCE_DECLARE_NON_COPYABLE(PedalDSP)
};
