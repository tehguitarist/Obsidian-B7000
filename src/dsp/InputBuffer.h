#pragma once

#include <chowdsp_wdf/chowdsp_wdf.h>

// =============================================================================
// Stage 1 — Input buffer + bias network (IC1_A, R1/C1/R2/R3)
// =============================================================================
// circuit.md "Input & buffer (IC1_A)":
//   R1 = 1M   input pulldown to GND (sets ~1 MΩ input Z, pop suppression)
//   C1 = 100n input coupling
//   R2 = 1M   bias input node to VD
//   R3 = 10k  series into IC1_A (+)
//   IC1_A = TL072ACP unity-gain buffer; output splits into the OD path (C2)
//           and the clean tap (long wire to BLEND pin1).
//
// ---- Isolated linear transfer function (ideal source, unloaded output) ------
// The only frequency-shaping elements that affect the isolated stage response
// are C1 and R2:
//   * R1 (input pulldown) sits ACROSS the source. With an ideal voltage-source
//     drive it carries current but cannot change any downstream node voltage,
//     so it does not appear in the isolated TF. (It sets input impedance, which
//     only matters once a real, finite source impedance is modelled.)
//   * R3 feeds the op-amp (+) input, which draws no current, so there is no
//     drop across R3 and it does not appear in the isolated TF either (it forms
//     only a negligible LP with the op-amp input capacitance).
//   * IC1_A is an ideal unity buffer (output Z ~ 0), so downstream loads (C2,
//     the clean tap) do not load this node — unity gain regardless.
//
// What remains is a single first-order high-pass formed by C1 into R2:
//        H(s) = s R2 C1 / (1 + s R2 C1)
//        fc   = 1 / (2 pi R2 C1) = 1 / (2 pi * 1e6 * 100e-9) ~= 1.5915 Hz
//   passband gain = unity (0 dB), non-inverting.
//
// WDF realisation: ideal voltage source -> series(C1, R2); the stage output is
// the voltage across R2 (the high-pass output = IC1_A output).
// =============================================================================
class InputBuffer
{
public:
    // Component values (circuit.md). Public so tests reference the single source
    // of truth rather than re-declaring their own (avoids silent oracle drift).
    static constexpr double kR2 = 1.0e6;    // bias resistor to VD -> HP resistor
    static constexpr double kC1 = 100.0e-9; // input coupling cap -> HP cap

    InputBuffer() = default;

    void prepare(double sampleRate)
    {
        c1.prepare(sampleRate);
        reset();
    }

    void reset()
    {
        c1.reset();
    }

    // Process one sample (real volts in, real volts out). Non-inverting.
    inline double process(double x) noexcept
    {
        vs.setVoltage(x);

        vs.incident(p1.reflected());
        p1.incident(vs.reflected());

        // Output node = IC1_A (+) input = voltage across R2 (the HP output).
        return chowdsp::wdft::voltage<double>(r2);
    }

private:
    chowdsp::wdft::ResistorT<double> r2 { kR2 };
    chowdsp::wdft::CapacitorT<double> c1 { kC1 };
    chowdsp::wdft::WDFSeriesT<double, decltype(c1), decltype(r2)> s1 { c1, r2 };
    chowdsp::wdft::PolarityInverterT<double, decltype(s1)> p1 { s1 };
    chowdsp::wdft::IdealVoltageSourceT<double, decltype(p1)> vs { p1 };

    // JUCE-free (this header is compiled into pure chowdsp_wdf console tests too).
    InputBuffer(const InputBuffer&) = delete;
    InputBuffer& operator=(const InputBuffer&) = delete;
};
