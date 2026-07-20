#include <chowdsp_wdf/chowdsp_wdf.h>
#include <cmath>
#include <cstdlib>
#include <iostream>

using namespace chowdsp::wdft;

static constexpr double PI = 3.14159265358979323846;

template <typename C1, typename P1, typename VS>
static double measureMagnitudeAtFreq(C1& c1,
                                      P1& p1,
                                      VS& vs,
                                      double freq,
                                      double fs)
{
    c1.reset();
    double magnitude = 0.0;
    const int totalSamples = static_cast<int>(fs);
    const int skipSamples = totalSamples / 2;

    for (int n = 0; n < totalSamples; ++n)
    {
        const auto x = std::sin(2.0 * PI * freq * static_cast<double>(n) / fs);
        vs.setVoltage(x);
        vs.incident(p1.reflected());
        p1.incident(vs.reflected());

        const auto y = voltage<double>(c1);
        if (n >= skipSamples)
            magnitude = std::max(magnitude, std::abs(y));
    }

    return (magnitude > 0.0) ? 20.0 * std::log10(magnitude) : -200.0;
}

int main()
{
    constexpr double R = 10000.0;          // 10 kΩ
    constexpr double C = 15.915494309e-9;   // ~15.9 nF
    constexpr double fcExact = 1.0 / (2.0 * PI * R * C);  // 1000 Hz

    std::cout << "RC Lowpass: R=" << R << " Ω, C=" << C << " F, fc=" << fcExact << " Hz\n\n";

    int failures = 0;

    // Test 1: −3 dB point within 1% at each sample rate
    constexpr double sampleRates[] = {44100.0, 48000.0, 96000.0};

    for (double fs : sampleRates)
    {
        CapacitorT<double> c1(C);
        ResistorT<double> r1(R);
        WDFSeriesT<double, decltype(r1), decltype(c1)> s1(r1, c1);
        PolarityInverterT<double, decltype(s1)> p1(s1);
        IdealVoltageSourceT<double, decltype(p1)> vs(p1);

        c1.prepare(fs);

        const double magAtFc = measureMagnitudeAtFreq(c1, p1, vs, fcExact, fs);

        const bool pass = std::abs(magAtFc - (-3.0)) <= 0.30;
        std::cout << "fs=" << fs << " Hz  mag@fc=" << magAtFc << " dB"
                  << "  (expected -3 dB)  " << (pass ? "PASS" : "FAIL") << "\n";

        if (! pass)
        {
            std::cerr << "  FAIL: magnitude at fc deviates by "
                      << std::abs(magAtFc + 3.0) << " dB (>0.3 dB)\n";
            ++failures;
        }
    }

    // Test 2: regression for the classic "forgot prepare() = silence" bug
    {
        std::cout << "\n--- prepare() regression test ---\n";

        const double fs = 48000.0;
        CapacitorT<double> c1(C);
        ResistorT<double> r1(R);
        WDFSeriesT<double, decltype(r1), decltype(c1)> s1(r1, c1);
        PolarityInverterT<double, decltype(s1)> p1(s1);
        IdealVoltageSourceT<double, decltype(p1)> vs(p1);

        // Deliberately skip c1.prepare(fs) — test that output is NOT silent.

        double maxOutput = 0.0;
        for (int n = 0; n < 1000; ++n)
        {
            const auto x = std::sin(2.0 * PI * 1000.0 * static_cast<double>(n) / fs);
            vs.setVoltage(x);
            vs.incident(p1.reflected());
            p1.incident(vs.reflected());
            maxOutput = std::max(maxOutput, std::abs(voltage<double>(c1)));
        }

        if (maxOutput < 1.0e-6)
        {
            std::cerr << "FAIL: missing prepare() caused silent output (max = "
                      << maxOutput << ") — regression!\n";
            ++failures;
        }
        else
        {
            std::cout << "PASS: output with missing prepare() = "
                      << maxOutput << " (not silent)\n";
        }
    }

    // Test 3: missing prepare() at a non-default sample rate shifts the cutoff
    {
        std::cout << "\n--- prepare() mismatch detection ---\n";

        const double fsActual = 48000.0;
        const double fsWrong = 96000.0;

        CapacitorT<double> c1(C, fsWrong);  // deliberately wrong
        ResistorT<double> r1(R);
        WDFSeriesT<double, decltype(r1), decltype(c1)> s1(r1, c1);
        PolarityInverterT<double, decltype(s1)> p1(s1);
        IdealVoltageSourceT<double, decltype(p1)> vs(p1);

        const double magAtFc = measureMagnitudeAtFreq(c1, p1, vs, fcExact, fsActual);
        const double deviation = std::abs(magAtFc - (-3.0));

        // With wrong sample rate (×2), the -3 dB point should be off by >1 dB
        const bool pass = deviation > 1.0;
        std::cout << "fsUsed=48000, capacitorPreparedAt=96000  mag@fc=" << magAtFc << " dB"
                  << "  (deviation=" << deviation << " dB)  "
                  << (pass ? "PASS (mismatch detectable)" : "FAIL (mismatch undetected)") << "\n";

        if (! pass)
            ++failures;
    }

    std::cout << "\n" << (failures == 0 ? "All tests passed." : "Some tests FAILED.") << "\n";
    return (failures > 0) ? 1 : 0;
}
