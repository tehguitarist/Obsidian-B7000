// =============================================================================
// OfflineRender — render a WAV through the REAL plugin chain from the CLI
// =============================================================================
// Phase-7's workhorse. Every calibration fit (kInputRef anchor, CD4049/J201
// nonlinear params, taper shapes, output make-up) is a search over constants
// scored by comparing a render against a real-pedal capture — so the fit needs a
// way to render at an arbitrary knob/switch/FitParams combination without a
// rebuild and without a DAW. That is all this is.
//
// **It mirrors `PluginProcessor::processBlock` deliberately, not incidentally.**
// The comparison is only meaningful if the render's gain staging is the SAME
// gain staging the plugin ships: input trim (DAW domain) -> dry copy (delay-
// compensated) -> * kInputRef (volts) -> PedalDSP -> * outputMakeup * outTrim /
// kInputRef -> bypass crossfade. Each step below is annotated with the
// processBlock line it mirrors; if processBlock changes, change this too, or
// every subsequent measurement is of a chain the plugin doesn't run.
// The two shared scalars come from `dsp/GainStaging.h` so at least those cannot
// silently diverge.
//
// ---- The four traps this file exists to get right ---------------------------
// 1. **EQ knob-space inversion.** `readParams()` does `p.lo = 1.0f - pLo->load()`
//    for lo/loMid/hiMid/hi: the DSP stages are boost-AT-ZERO while the knob is
//    CW-is-boost. `captures.py` hands out KNOB-space values (it mirrors APVTS),
//    so this CLI takes knob space and inverts internally, exactly as
//    readParams() does. Feeding CLI values straight into PedalChain::Params
//    would invert every EQ fit and still look completely plausible.
//    `--print-fit` prints BOTH spaces side by side so the mapping is checkable
//    rather than assumed.
// 2. **Smoothing ramps.** inputGain/outputGain (20 ms) and bypassMix (5 ms) ramp
//    from prepareToPlay defaults. In a static offline render that ramp is a pure
//    start-of-file artifact, so every smoother is seeded with
//    setCurrentAndTargetValue() — the render begins at its final gain.
// 3. **Latency.** `analysis/analyze.py::align()` cross-correlates and removes
//    the lag itself. So this renders UNCOMPENSATED by default; trimming
//    getLatencySamples() here as well would double-compensate and shift the
//    render EARLY by the OS FIR latency. `--trim-latency` exists for callers
//    that do their own alignment-free comparison, and is opt-in for that reason.
// 4. **bypass.wav.** `parse_capture("bypass.wav")` returns `{"bypass": True}`
//    and nothing else, so `--bypass 1` must be renderable with no other flag
//    present — every knob flag here is optional and defaults to the APVTS
//    default, and at `--bypass 1` the crossfade is seeded fully dry.
//
// Output is ALWAYS 32-bit float WAV (validation-and-capture.md §2): renders at
// high drive+volume legitimately exceed 0 dBFS, and integer PCM would silently
// hard-clip exactly the captures where clipping accuracy matters most.
//
// Usage:
//   OfflineRender <in.wav> <out.wav> [options]     (positional — what the
//   OfflineRender --in <wav> --out <wav> [options]  analysis/ orchestrators use)
//   OfflineRender --print-fit                      (no render; dump defaults)
// =============================================================================

#include <juce_audio_formats/juce_audio_formats.h>
#include <juce_dsp/juce_dsp.h>

#include "../src/dsp/GainStaging.h"
#include "../src/dsp/PedalDSP.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

// -----------------------------------------------------------------------------
// Options
// -----------------------------------------------------------------------------
struct Options
{
    std::string inPath, outPath;

    // Pots in KNOB space (0..1, CW = clockwise = higher), i.e. APVTS space —
    // NOT PedalChain::Params space for the four EQ pots. Defaults match
    // createParameterLayout().
    double master = 0.5, blend = 0.5, level = 0.5, drive = 0.5;
    double lo = 0.5, loMid = 0.5, hiMid = 0.5, hi = 0.5;

    // Switch choice indices (APVTS StringArray order, PluginProcessor.cpp).
    int attackIdx = 0;   // {Flat, Boost, Cut}
    int gruntIdx = 0;    // {Boost, Cut, Flat}
    int loMidFreq = 2;   // {250Hz, 500Hz, 1kHz}
    int hiMidFreq = 2;   // {750Hz, 1.5kHz, 3kHz}

    bool distEngage = true;
    bool bypass = false;

    double inputTrimDb = 0.0, outputTrimDb = 0.0;

    int osFactor = 8; // validation default: take aliasing off the table
    int blockSize = 512;

    double inputRef = GainStaging::kInputRefNominal;
    double outputMakeup = GainStaging::kOutputMakeupNominal;

    bool trimLatency = false;
    bool printFit = false;

    FitParams fit {};
};

// -----------------------------------------------------------------------------
// Small parsing helpers — every one of these fails LOUDLY. A calibration run
// that silently ignores a misspelled flag fits the wrong thing and reports a
// number with no warning attached, which is the worst outcome available here.
// -----------------------------------------------------------------------------
[[noreturn]] static void fail(const std::string& msg)
{
    std::fprintf(stderr, "OfflineRender: %s\n", msg.c_str());
    std::exit(2);
}

static double parseDouble(const std::string& flag, const std::string& s)
{
    try
    {
        size_t used = 0;
        const double v = std::stod(s, &used);
        if (used != s.size())
            fail(flag + ": '" + s + "' is not a number");
        return v;
    }
    catch (const std::exception&)
    {
        fail(flag + ": '" + s + "' is not a number");
    }
}

static int parseInt(const std::string& flag, const std::string& s)
{
    try
    {
        size_t used = 0;
        const int v = std::stoi(s, &used);
        if (used != s.size())
            fail(flag + ": '" + s + "' is not an integer");
        return v;
    }
    catch (const std::exception&)
    {
        fail(flag + ": '" + s + "' is not an integer");
    }
}

static bool parseBool(const std::string& flag, const std::string& s)
{
    if (s == "1" || s == "true" || s == "on" || s == "yes") return true;
    if (s == "0" || s == "false" || s == "off" || s == "no") return false;
    fail(flag + ": '" + s + "' is not a boolean (0/1)");
}

static double parseKnob(const std::string& flag, const std::string& s)
{
    const double v = parseDouble(flag, s);
    if (! (v >= 0.0 && v <= 1.0))
        fail(flag + ": knob value " + s + " outside 0..1");
    return v;
}

static std::string lower(std::string s)
{
    for (auto& c : s) c = (char) std::tolower((unsigned char) c);
    return s;
}

// A switch flag accepts either the APVTS choice INDEX or the label, so a
// hand-typed command is readable and captures.py can emit plain indices.
// `names` is in StringArray order; index i == names[i].
static int parseChoice(const std::string& flag, const std::string& s,
                       const std::vector<std::string>& names)
{
    const std::string t = lower(s);
    for (size_t i = 0; i < names.size(); ++i)
        if (t == names[i])
            return (int) i;

    if (! t.empty() && (std::isdigit((unsigned char) t[0]) != 0))
    {
        const int v = parseInt(flag, t);
        if (v >= 0 && v < (int) names.size())
            return v;
    }

    std::string opts;
    for (size_t i = 0; i < names.size(); ++i)
        opts += (i ? ", " : "") + std::to_string(i) + "/" + names[i];
    fail(flag + ": '" + s + "' is not a valid position — expected one of {" + opts + "}");
}

// -----------------------------------------------------------------------------
// --fit name=value — the whole point of FitParams being runtime-settable.
// Names are the FitParams FIELD names verbatim (FitParams.h), matched
// case-insensitively so `--fit clipa0=27` works from a shell script.
// -----------------------------------------------------------------------------
struct FitField
{
    const char* name;
    double FitParams::* member;
};

static const FitField kFitFields[] = {
    {"clipA0", &FitParams::clipA0},
    {"clipSatLo", &FitParams::clipSatLo},
    {"clipSatHi", &FitParams::clipSatHi},
    // jfetG0/jfetGmR6 were REMOVED by the 2026-07-22 restructure (FitParams.h) —
    // deliberately not aliased, so a stale --fit jfetG0=... fails loudly.
    {"jfetGm", &FitParams::jfetGm},
    {"jfetRo", &FitParams::jfetRo},
    {"jfetRq2", &FitParams::jfetRq2},
    {"jfetSatPos", &FitParams::jfetSatPos},
    {"jfetSatNeg", &FitParams::jfetSatNeg},
    // Asymmetric drain-current ceiling (2026-07-22). Gate-volt equivalent, x gm
    // for amps; >= 1e6 disables a side exactly (A/B against the pre-ceiling model).
    {"jfetCeilPos", &FitParams::jfetCeilPos},
    {"jfetCeilNeg", &FitParams::jfetCeilNeg},
    {"driveTaperExp", &FitParams::driveTaperExp},
    {"levelTaperExp", &FitParams::levelTaperExp},
    {"masterTaperExp", &FitParams::masterTaperExp},
    {"c21R", &FitParams::c21R},
    {"btR22", &FitParams::btR22},
    {"btR23", &FitParams::btR23},
    {"btC16", &FitParams::btC16},
    {"btC17", &FitParams::btC17},
    {"railNeg", &FitParams::railNeg},
    {"railPos", &FitParams::railPos},
};

static void applyFitAssignment(FitParams& fit, const std::string& assignment)
{
    const auto eq = assignment.find('=');
    if (eq == std::string::npos || eq == 0 || eq + 1 >= assignment.size())
        fail("--fit expects name=value, got '" + assignment + "'");

    const std::string name = assignment.substr(0, eq);
    const std::string value = assignment.substr(eq + 1);
    const std::string key = lower(name);

    if (key == "railenabled")
    {
        // The one entry that can invalidate every other fit if flipped at the
        // wrong point in the calibration order — see FitParams.h.
        fit.railEnabled = parseBool("--fit railEnabled", value);
        return;
    }

    for (const auto& f : kFitFields)
    {
        if (key == lower(f.name))
        {
            fit.*(f.member) = parseDouble("--fit " + name, value);
            return;
        }
    }

    std::string known = "railEnabled";
    for (const auto& f : kFitFields)
        known += std::string(", ") + f.name;
    fail("--fit: unknown parameter '" + name + "' — known: " + known);
}

// -----------------------------------------------------------------------------
static void printUsage()
{
    std::printf(
        "OfflineRender — render a WAV through the Obsidian-B7000 chain.\n"
        "\n"
        "  OfflineRender <in.wav> <out.wav> [options]\n"
        "  OfflineRender --in <wav> --out <wav> [options]\n"
        "  OfflineRender --print-fit            (no render; dump the defaults)\n"
        "\n"
        "Pots (0..1 KNOB space, CW = higher — the EQ pots are inverted internally\n"
        "to DSP space exactly as PluginProcessor::readParams() does):\n"
        "  --master --blend --level --drive --lo|--bass --lo-mid --hi-mid --hi|--treble\n"
        "\n"
        "Switches (APVTS choice index or label):\n"
        "  --attack       0/flat  1/boost  2/cut\n"
        "  --grunt        0/boost 1/cut    2/flat\n"
        "  --lo-mid-freq  0/250   1/500    2/1k\n"
        "  --hi-mid-freq  0/750   1/1p5k   2/3k\n"
        "\n"
        "Routing / staging:\n"
        "  --dist-engage 0|1     --bypass 0|1\n"
        "  --input-trim <dB>     --output-trim <dB>\n"
        "  --input-ref <V>       --output-makeup <gain>\n"
        "  --os 1|2|4|8          --block <samples>\n"
        "\n"
        "Calibration:\n"
        "  --fit name=value      repeatable; any FitParams field (see --print-fit)\n"
        "  --print-fit           dump the fit params + resolved knob mapping used\n"
        "  --trim-latency        opt-in; do NOT use with analyze.py::align()\n");
}

static Options parseArgs(int argc, char** argv)
{
    Options o;
    std::vector<std::string> positional;

    for (int i = 1; i < argc; ++i)
    {
        const std::string a = argv[i];

        auto value = [&]() -> std::string {
            if (i + 1 >= argc)
                fail(a + " requires a value");
            return argv[++i];
        };

        if (a == "-h" || a == "--help") { printUsage(); std::exit(0); }
        else if (a == "--in") o.inPath = value();
        else if (a == "--out") o.outPath = value();
        else if (a == "--master") o.master = parseKnob(a, value());
        else if (a == "--blend") o.blend = parseKnob(a, value());
        else if (a == "--level") o.level = parseKnob(a, value());
        else if (a == "--drive") o.drive = parseKnob(a, value());
        else if (a == "--lo" || a == "--bass") o.lo = parseKnob(a, value());
        else if (a == "--lo-mid") o.loMid = parseKnob(a, value());
        else if (a == "--hi-mid") o.hiMid = parseKnob(a, value());
        else if (a == "--hi" || a == "--treble") o.hi = parseKnob(a, value());
        else if (a == "--attack") o.attackIdx = parseChoice(a, value(), {"flat", "boost", "cut"});
        else if (a == "--grunt") o.gruntIdx = parseChoice(a, value(), {"boost", "cut", "flat"});
        else if (a == "--lo-mid-freq") o.loMidFreq = parseChoice(a, value(), {"250", "500", "1k"});
        else if (a == "--hi-mid-freq") o.hiMidFreq = parseChoice(a, value(), {"750", "1p5k", "3k"});
        else if (a == "--dist-engage") o.distEngage = parseBool(a, value());
        else if (a == "--bypass") o.bypass = parseBool(a, value());
        else if (a == "--input-trim") o.inputTrimDb = parseDouble(a, value());
        else if (a == "--output-trim") o.outputTrimDb = parseDouble(a, value());
        else if (a == "--input-ref") o.inputRef = parseDouble(a, value());
        else if (a == "--output-makeup") o.outputMakeup = parseDouble(a, value());
        else if (a == "--os") o.osFactor = parseInt(a, value());
        else if (a == "--block") o.blockSize = parseInt(a, value());
        else if (a == "--fit") applyFitAssignment(o.fit, value());
        else if (a == "--print-fit") o.printFit = true;
        else if (a == "--trim-latency") o.trimLatency = true;
        else if (! a.empty() && a[0] == '-') fail("unknown option '" + a + "'");
        else positional.push_back(a);
    }

    // Positional in/out (the form analysis/*.py already uses) fills whatever the
    // flags didn't.
    size_t p = 0;
    if (o.inPath.empty() && p < positional.size()) o.inPath = positional[p++];
    if (o.outPath.empty() && p < positional.size()) o.outPath = positional[p++];
    if (p < positional.size())
        fail("unexpected extra argument '" + positional[p] + "'");

    if (o.osFactor != 1 && o.osFactor != 2 && o.osFactor != 4 && o.osFactor != 8)
        fail("--os must be 1, 2, 4 or 8");
    if (o.blockSize < 1)
        fail("--block must be >= 1");
    if (o.inputRef <= 0.0)
        fail("--input-ref must be > 0 (it divides back out of the output gain)");

    return o;
}

// -----------------------------------------------------------------------------
// Knob space -> PedalChain::Params. MIRRORS PluginProcessor::readParams().
// The four EQ pots invert here and ONLY here, same as in the plugin.
// -----------------------------------------------------------------------------
static PedalChain::Params toChainParams(const Options& o)
{
    PedalChain::Params p;
    p.master = o.master;
    p.blend = o.blend;
    p.level = o.level;
    p.drive = o.drive;
    p.lo = 1.0 - o.lo;
    p.loMid = 1.0 - o.loMid;
    p.hiMid = 1.0 - o.hiMid;
    p.hi = 1.0 - o.hi;
    p.attackIdx = o.attackIdx;
    p.gruntIdx = o.gruntIdx;
    p.loMidFreq = o.loMidFreq;
    p.hiMidFreq = o.hiMidFreq;
    p.distEngage = o.distEngage;
    return p;
}

static void printFitReport(const Options& o, const PedalChain::Params& p, int latency)
{
    const FitParams& f = o.fit;
    std::printf("# OfflineRender configuration\n");
    std::printf("os=%d\n", o.osFactor);
    std::printf("latency_samples=%d  (trim_latency=%d)\n", latency, o.trimLatency ? 1 : 0);
    std::printf("input_ref=%.9g\n", o.inputRef);
    std::printf("output_makeup=%.9g\n", o.outputMakeup);
    std::printf("input_trim_db=%.9g\noutput_trim_db=%.9g\n", o.inputTrimDb, o.outputTrimDb);
    std::printf("bypass=%d\ndist_engage=%d\n", o.bypass ? 1 : 0, o.distEngage ? 1 : 0);

    // Knob space (what the CLI took, == APVTS) vs DSP space (what the chain got).
    // The EQ rows must differ by the 1-x inversion; that is the visible proof
    // that trap #1 is honoured, so it is printed rather than described.
    std::printf("# pots: knob_space -> dsp_space (EQ pots invert, readParams())\n");
    std::printf("master=%.6f -> %.6f\n", o.master, p.master);
    std::printf("blend=%.6f -> %.6f\n", o.blend, p.blend);
    std::printf("level=%.6f -> %.6f\n", o.level, p.level);
    std::printf("drive=%.6f -> %.6f\n", o.drive, p.drive);
    std::printf("lo=%.6f -> %.6f\n", o.lo, p.lo);
    std::printf("lo_mid=%.6f -> %.6f\n", o.loMid, p.loMid);
    std::printf("hi_mid=%.6f -> %.6f\n", o.hiMid, p.hiMid);
    std::printf("hi=%.6f -> %.6f\n", o.hi, p.hi);
    std::printf("attack_idx=%d\ngrunt_idx=%d\nlo_mid_freq_idx=%d\nhi_mid_freq_idx=%d\n",
                p.attackIdx, p.gruntIdx, p.loMidFreq, p.hiMidFreq);

    std::printf("# FitParams (src/dsp/FitParams.h)\n");
    for (const auto& ff : kFitFields)
        std::printf("fit.%s=%.9g\n", ff.name, f.*(ff.member));
    std::printf("fit.railEnabled=%d\n", f.railEnabled ? 1 : 0);
}

// -----------------------------------------------------------------------------
int main(int argc, char** argv)
{
    const Options o = parseArgs(argc, argv);
    const PedalChain::Params params = toChainParams(o);

    const bool wantRender = ! (o.inPath.empty() && o.outPath.empty());
    if (! wantRender && ! o.printFit)
    {
        printUsage();
        return 2;
    }
    if (wantRender && (o.inPath.empty() || o.outPath.empty()))
        fail("need both an input and an output path");

    if (! wantRender)
    {
        // --print-fit alone: report the resolved configuration without touching
        // any audio. Latency is unknown without a prepared chain, so report -1.
        printFitReport(o, params, -1);
        return 0;
    }

    // ---- Read input ---------------------------------------------------------
    juce::File inFile = juce::File::getCurrentWorkingDirectory().getChildFile(juce::String(o.inPath));
    if (! inFile.existsAsFile())
        fail("input file not found: " + o.inPath);

    juce::AudioFormatManager fm;
    fm.registerBasicFormats();
    std::unique_ptr<juce::AudioFormatReader> reader(fm.createReaderFor(inFile));
    if (reader == nullptr)
        fail("could not read '" + o.inPath + "' as audio");

    const int numChannels = juce::jlimit(1, 2, (int) reader->numChannels);
    const int numSamples = (int) reader->lengthInSamples;
    const double sampleRate = reader->sampleRate;
    if (numSamples <= 0)
        fail("input file is empty");

    juce::AudioBuffer<float> buffer(numChannels, numSamples);
    reader->read(&buffer, 0, numSamples, 0, true, numChannels > 1);

    // ---- Prepare the chain (mirrors prepareToPlay) --------------------------
    const int blockSize = juce::jmin(o.blockSize, numSamples);
    const int osOrder = (int) std::lround(std::log2((double) o.osFactor)); // 1/2/4/8 -> 0..3

    std::vector<std::unique_ptr<PedalDSP>> dsp;
    for (int ch = 0; ch < numChannels; ++ch)
    {
        auto d = std::make_unique<PedalDSP>();
        d->prepare(sampleRate, blockSize);
        d->setFactorOrder(osOrder);
        d->setFitParams(o.fit); // calibration first, then control
        d->setParams(params);
        d->reset();
        dsp.push_back(std::move(d));
    }

    const int latency = dsp[0]->getLatencySamples();

    // Bypass dry-path delay compensation, exactly as the processor does it
    // (dsp.md "Dry/wet phase alignment") — the dry copy is pre-DSP and therefore
    // zero-latency, so it is delayed to match the wet chain before the crossfade.
    std::vector<juce::dsp::DelayLine<float, juce::dsp::DelayLineInterpolationTypes::None>> bypassDelay;
    for (int ch = 0; ch < numChannels; ++ch)
    {
        juce::dsp::DelayLine<float, juce::dsp::DelayLineInterpolationTypes::None> dl;
        dl.prepare({sampleRate, (juce::uint32) blockSize, 1});
        dl.setMaximumDelayInSamples(juce::jmax(1, dsp[0]->getMaxLatencySamples()));
        dl.setDelay((float) latency);
        dl.reset();
        bypassDelay.push_back(std::move(dl));
    }

    // Trap #2: seed every smoother at its FINAL value. A static render has no
    // parameter movement, so the plugin's 20 ms / 5 ms ramps would only paint a
    // gain ramp over the head of the file — right where the cal tone lives.
    juce::SmoothedValue<float> inputGainRef, outputGainRef, bypassMixRef;
    inputGainRef.reset(sampleRate, 0.02);
    outputGainRef.reset(sampleRate, 0.02);
    bypassMixRef.reset(sampleRate, 0.005);
    inputGainRef.setCurrentAndTargetValue(juce::Decibels::decibelsToGain((float) o.inputTrimDb));
    outputGainRef.setCurrentAndTargetValue((float) (o.outputMakeup
                                                    * juce::Decibels::decibelsToGain(o.outputTrimDb)
                                                    / o.inputRef));
    bypassMixRef.setCurrentAndTargetValue(o.bypass ? 1.0f : 0.0f);

    // ---- Render (mirrors processBlock, block by block) ----------------------
    std::vector<double> work((size_t) blockSize, 0.0);
    std::vector<float> dryDelayed((size_t) blockSize, 0.0f);
    float peakOut = 0.0f;
    bool sawNonFinite = false;

    for (int start = 0; start < numSamples; start += blockSize)
    {
        const int n = juce::jmin(blockSize, numSamples - start);

        for (int ch = 0; ch < numChannels; ++ch)
        {
            auto inGain = inputGainRef;
            auto outGain = outputGainRef;
            auto bMix = bypassMixRef;

            float* io = buffer.getWritePointer(ch, start);

            // a/b. input trim (DAW domain) -> dry copy (delay-compensated) ->
            //      chain volts. NOTE the dry copy is the RAW input, pre-trim —
            //      true bypass, same as processBlock.
            for (int i = 0; i < n; ++i)
            {
                const float wet = io[i] * inGain.getNextValue();
                work[(size_t) i] = (double) wet * o.inputRef;

                bypassDelay[(size_t) ch].pushSample(0, io[i]);
                dryDelayed[(size_t) i] = bypassDelay[(size_t) ch].popSample(0, (float) latency, true);
            }

            // c. the chain.
            dsp[(size_t) ch]->processBlock(work.data(), n);

            // e/f. output make-up + trim, then the bypass crossfade against the
            //      delay-compensated dry copy (same NaN-safe branch structure).
            for (int i = 0; i < n; ++i)
            {
                const float dry = dryDelayed[(size_t) i];
                const float processed = (float) work[(size_t) i] * outGain.getNextValue();
                const float mix = bMix.getNextValue();
                const float out = mix >= 1.0f ? dry
                                : mix <= 0.0f ? processed
                                              : processed * (1.0f - mix) + dry * mix;
                io[i] = out;
                if (! std::isfinite(out))
                    sawNonFinite = true;
                peakOut = juce::jmax(peakOut, std::abs(out));
            }
        }
    }

    // Trap #3: OFF by default. analyze.py::align() removes the lag by cross-
    // correlation; trimming here as well would shift the render early.
    // The file KEEPS its length either way (the tail is zero-padded), so a
    // trimmed render still lines up sample-for-sample with the reference signal.
    const int written = numSamples;
    if (o.trimLatency && latency > 0 && latency < numSamples)
    {
        for (int ch = 0; ch < numChannels; ++ch)
        {
            float* d = buffer.getWritePointer(ch);
            std::memmove(d, d + latency, sizeof(float) * (size_t) (numSamples - latency));
            juce::FloatVectorOperations::clear(d + (numSamples - latency), latency);
        }
    }

    // ---- Write 32-bit FLOAT WAV (validation-and-capture.md §2) --------------
    juce::File outFile = juce::File::getCurrentWorkingDirectory().getChildFile(juce::String(o.outPath));
    outFile.deleteFile();
    auto fileStream = std::make_unique<juce::FileOutputStream>(outFile);
    if (! fileStream->openedOk())
        fail("could not open output file '" + o.outPath + "' for writing");

    std::unique_ptr<juce::OutputStream> stream(std::move(fileStream));
    juce::WavAudioFormat wav;
    const auto writerOpts = juce::AudioFormatWriterOptions {}
                                .withSampleRate(sampleRate)
                                .withNumChannels(numChannels)
                                .withBitsPerSample(32)
                                .withSampleFormat(juce::AudioFormatWriterOptions::SampleFormat::floatingPoint);
    auto writer = wav.createWriterFor(stream, writerOpts);
    if (writer == nullptr)
        fail("could not create a 32-bit float WAV writer for '" + o.outPath + "'");
    if (! writer->writeFromAudioSampleBuffer(buffer, 0, written))
        fail("failed writing '" + o.outPath + "'");
    writer.reset(); // flush + close before we report success

    if (o.printFit)
        printFitReport(o, params, latency);

    std::printf("rendered %d samples x %dch @ %.0f Hz, os=%d, latency=%d, peak=%.6f\n",
                written, numChannels, sampleRate, o.osFactor, latency, peakOut);

    if (sawNonFinite)
    {
        // A non-finite sample means the fit candidate blew the chain up. Fail
        // loudly so a parameter sweep records it as a rejected point rather than
        // scoring a file full of NaNs.
        std::fprintf(stderr, "OfflineRender: non-finite samples in the output\n");
        return 1;
    }
    return 0;
}
