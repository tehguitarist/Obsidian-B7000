#include "PluginEditor.h"
#include "PluginProcessor.h"

ObsidianB7000AudioProcessorEditor::ObsidianB7000AudioProcessorEditor(ObsidianB7000AudioProcessor& p)
    : juce::AudioProcessorEditor(&p)
{
    setSize(800, 600);
}

ObsidianB7000AudioProcessorEditor::~ObsidianB7000AudioProcessorEditor() = default;

void ObsidianB7000AudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::black);
}

void ObsidianB7000AudioProcessorEditor::resized() {}
