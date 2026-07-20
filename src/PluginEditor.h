#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_gui_basics/juce_gui_basics.h>

class ObsidianB7000AudioProcessor;

class ObsidianB7000AudioProcessorEditor : public juce::AudioProcessorEditor
{
public:
    explicit ObsidianB7000AudioProcessorEditor(ObsidianB7000AudioProcessor&);
    ~ObsidianB7000AudioProcessorEditor() override;

    void paint(juce::Graphics&) override;
    void resized() override;
};
