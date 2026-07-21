// Renders the real plugin editor off-screen at a few UI scales and writes PNGs, so layout
// changes (e.g. a new bottom-strip control) can be checked without a DAW or a display attached.
// NOT registered with add_test() — it's a visual-inspection tool, not a pass/fail gate.
#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_gui_extra/juce_gui_extra.h>

#include "../src/PluginProcessor.h"
#include "../src/PluginEditor.h"

int main(int argc, char** argv)
{
    juce::ScopedJuceInitialiser_GUI juceInit;

    const juce::String outDir = argc > 1 ? juce::String(argv[1]) : juce::String(".");

    ObsidianB7000AudioProcessor processor;
    auto editor = std::unique_ptr<juce::AudioProcessorEditor>(processor.createEditor());

    struct ScaleCase { float scale; const char* name; };
    const ScaleCase cases[] = { { 0.5f, "min" }, { 1.0f, "default" }, { 2.5f, "max" } };

    for (const auto& c : cases)
    {
        editor->setSize(juce::roundToInt(765.0f * c.scale), juce::roundToInt(475.0f * c.scale));
        editor->setVisible(true);

        auto image = editor->createComponentSnapshot(editor->getLocalBounds());

        juce::PNGImageFormat png;
        juce::File outFile(outDir + "/editor_" + juce::String(c.name) + ".png");
        std::unique_ptr<juce::FileOutputStream> stream(outFile.createOutputStream());
        if (stream != nullptr)
        {
            stream->setPosition(0);
            stream->truncate();
            png.writeImageToStream(image, *stream);
            std::cout << "Wrote " << outFile.getFullPathName() << " ("
                      << image.getWidth() << "x" << image.getHeight() << ")\n";
        }
    }

    return 0;
}
