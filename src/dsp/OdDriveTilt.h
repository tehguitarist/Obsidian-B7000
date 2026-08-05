#pragma once

#include <algorithm>
#include <cmath>

// =============================================================================
// OdDriveTilt — engineered (NON-SCHEMATIC) LEVEL-DEPENDENT treble tilt
// =============================================================================
// User-authorised tone-fidelity correction, session 166 (2026-08-06), and the
// THIRD architecture tried for open work item 6's treble half.  The first two
// were refuted by measurement before anything was built; that history is what
// this stage's shape is, so it is recorded here rather than only in the log.
//
// ---------------------------------------------------------------------------
// WHAT IT FIXES
// ---------------------------------------------------------------------------
// The pedal's treble peak WALKS with stimulus level (2696 -> 2498 Hz across the
// 24 dB ladder) and the model's is FIXED to 0.2 % (GATE W6).  In the right
// units that is a missing DRIVE-DEPENDENT SLOPE: the reference's log-magnitude
// tilt near 2935 Hz moves -1.944 dB/oct from the quietest rung to the hottest
// while the model's moves +0.094, a deficit of -2.038 dB/oct, same-signed in
// 13 of 14 captures (GATE AG).  A vertex sits where the total slope crosses
// zero, so a tilt moves it with NO corner moving anywhere — which is why every
// corner-based frame failed for ~20 sessions (CLAUDE.md item 6).
//
// ---------------------------------------------------------------------------
// ⛔⛔ WHY IT HAS TO BE LEVEL-DEPENDENT — TWO REFUTATIONS, BOTH MEASURED
// ---------------------------------------------------------------------------
// A Farina sweep presents one frequency at a time, so the OD path factorises as
//     H1(f, A) = P(f) * g(A*|P(f)|) * Q(f)
// with P the pre-clipper response, g the clipper's fundamental-gain law and Q
// everything linear DOWNSTREAM of it.  Differentiating in log-frequency,
//     drive-tilt(f) = P'(f) * [ gamma(hot) - gamma(quiet) ],  gamma = dlog g/dlog x
//
//  (1) Q DROPS OUT EXACTLY (GATE BA, s164).  A fixed linear stage adds the same
//      log-magnitude to EVERY stimulus rung, and the drive-tilt is a DIFFERENCE
//      between rungs.  Measured: a wild probe (a 4 dB/oct tilt + a 6 dB shelf +
//      a 9 dB peak sitting ON the vertex) added to every rung moves the
//      drive-tilt by 2.04e-14 dB/oct.  ⇒ a section in `OdToneRestore`'s slot
//      carries NONE of this, at any gain, any Q, any centre, on any knob.
//      ⛔ Do not "simplify" this stage into a static drive-keyed table — that is
//      exactly the refuted architecture, and it will measure as zero.
//
//  (2) A FIXED PRE-CLIPPER PRE-EMPHASIS CANNOT SERVE THE DRIVE KNOB (GATE BB,
//      s165).  Such a section supplies one fixed P', and the chain converts it
//      at a rate set by the clipper's own operating point — which COLLAPSES as
//      the DRIVE knob comes up, because the clipper is then already limiting at
//      BOTH stimulus rungs so changing what it is fed cannot change the
//      DIFFERENCE between them.  Measured coefficient: -0.909 (DRIVE min) /
//      -0.481 (noon) / -0.027 (max), so the required P' is +0.92 / +2.44 /
//      +45.8 dB/oct — a factor of 50, and a fixed section has ONE.  Stated with
//      no bar in it: a section sized to close DRIVE min delivers 2.0 % of the
//      requirement at DRIVE max.  ⚠ Its collateral was also priced: 6 of 6
//      probes more than HALVED a named feature's prominence, with `mid_peak`
//      going 2.27 -> 0.00 dB in four of them (GATE Y reproduced).
//
// ⇒ what is left is a section whose OWN COEFFICIENTS move with signal level, so
//   that its contribution does not cancel between rungs.  That is this stage.
//
// ---------------------------------------------------------------------------
// HOW
// ---------------------------------------------------------------------------
// One RBJ (Audio EQ Cookbook) HIGH-SHELF biquad whose gain is driven by an
// envelope follower.  Louder in ⇒ more high-shelf CUT ⇒ the OD path's top end
// tilts down with level, which is the missing behaviour.
//
// ⭐ THE SHAPE IS FITTED, NOT CHOSEN.  Item 6's gate 1 refutes a CONSTANT
// drive-dependent tilt outright: the deficit STEEPENS with frequency
// (-0.39 / -0.78 / -1.44 dB/oct at 1613 / 2032 / 2560 Hz, GATE AG's AG4), so a
// constant-tilt correction lands on target at one frequency and is wrong at the
// others by a growing amount.  Fitted against that profile, scaled so the vertex
// lands on gate 2's POSITION ceiling (-1.185 dB/oct, beyond which the peak
// overshoots its target), over the families that could carry it:
//
//     family                              rms error vs the required profile
//     CONSTANT tilt (gate 1's class)              0.627 dB/oct
//     two cascaded 1st-order shelves              0.093
//     one 1st-order shelf                         0.109
//     RBJ 2nd-order high shelf  (SHIPPED)         0.0051      <- 124x the constant
//
// ⇒ f0 = 5388 Hz, S = 0.85, and a gain swing of -4.87 dB across the ladder's
//   24 dB, i.e. 0.203 dB of shelf gain per dB of stimulus.  A gentle tilt, not
//   a compressor.
//
// ⚠⚠ THE ENVELOPE IS TAKEN ON THE OD REGION'S *INPUT*, AND THAT IS DELIBERATE.
// Two candidate taps were rejected for reasons that will otherwise be
// re-discovered:
//   * the CLIPPER's input moves with the DRIVE knob as well as with stimulus,
//     so the section's operating point would slide ~24 dB across the knob and
//     clamp at one end — losing exactly the differential action it exists for,
//     at DRIVE max, which GATE BB identified as the hardest condition;
//   * the TREBLE LADDER's output is not flat in frequency (its own slope at the
//     vertex is +0.51 dB/oct and it varies far more across the band), so during
//     a sweep the envelope would track the LADDER'S SHAPE rather than the
//     stimulus level and inject an unintended frequency dependence comparable
//     in size to the whole correction.
// The OD region's input is flat by construction and moves 1:1 with stimulus at
// every DRIVE setting, which is what "tilt with how hard it is being driven"
// operationally means here.
//
// ⛔ SCOPE.  This is an [ENG] correction targeting the TREBLE-PEAK SLOPE ONLY
// (item 6's own scope note).  The bridged-T notch-depth collapse, the bass-peak
// walk and the missing HF null are separate, independently-sized symptoms of the
// same gap and are NOT addressed here.  It is OD-path only and never touches the
// clean tap, so CLEAN is bit-identical by construction (item 6's gate 3).
// =============================================================================

class OdDriveTilt
{
public:
    void prepare(double fs) noexcept
    {
        sampleRate = fs;
        // One SYMMETRIC one-pole coefficient — see setTime().  A log sweep has
        // CONSTANT amplitude, so any time constant well above one sweep period
        // reads the rung's level.
        smooth = coefFor(timeMs);
        shelf.reset();
        env2 = 0.0;
        lastGainDb = 1e9;      // force a recompute on the first sample
        recompute(0.0);
    }

    void reset() noexcept
    {
        shelf.resetState();
        env2 = 0.0;
    }

    void setEnabled(bool on) noexcept { enabled = on; }

    // f0 (Hz), S (RBJ shelf slope), dB of shelf gain per dB of envelope, the
    // envelope level (dBV) at which the shelf is flat, and the cut limit (dB).
    void setLaw(double f0Hz, double slopeS, double dbPerDb, double refDbv,
                double maxCutDb) noexcept
    {
        f0 = f0Hz;
        S = slopeS;
        k = dbPerDb;
        ref = refDbv;
        maxCut = maxCutDb;
        lastGainDb = 1e9;
        recompute(currentEnvDb());
    }

    // ⚠⚠ ONE time constant, deliberately — the follower is SYMMETRIC and reads a
    // true mean square.  An asymmetric attack/release follower rides ABOVE the RMS
    // (up to +3.01 dB on a sine at the instant-attack limit; measured +2.11 dB at
    // 5/50 ms), which does NOT change the level DIFFERENCE the correction depends
    // on — both rungs are biased identically — but it does mean `refDbv` stops
    // naming the level at which the shelf is flat.  This stage's law is calibrated
    // in absolute dBV, so a well-defined reading is worth more than compressor-style
    // envelope behaviour; it is a slow tone tilt, not a compressor.
    void setTime(double ms) noexcept
    {
        timeMs = ms;
        smooth = coefFor(timeMs);
    }

    // Envelope observation.  ⚠ Called with the OD REGION'S INPUT, not this
    // stage's input — see the header note; taking it locally would make the
    // envelope depend on everything upstream, including the clipper.
    inline void observe(double odRegionInput) noexcept
    {
        if (! enabled)
            return;
        const double sq = odRegionInput * odRegionInput;
        env2 += smooth * (sq - env2);
    }

    inline double process(double x) noexcept
    {
        if (! enabled)
            return x;
        // The biquad is recomputed only when the gain has moved materially.  At
        // the oversampled rate a per-sample RBJ solve would dominate this
        // stage's cost, and the envelope moves far slower than the audio.
        const double g = gainFor(currentEnvDb());
        if (std::abs(g - lastGainDb) > kRecomputeDb)
            recompute(currentEnvDb());
        return shelf.process(x);
    }

    // Diagnostic only — the gain the law is currently asking for, in dB.
    double currentGainDb() const noexcept { return gainFor(currentEnvDb()); }

private:
    static constexpr double kRecomputeDb = 0.02;   // coefficient-update hysteresis
    static constexpr double kEnvFloor = 1e-20;

    double coefFor(double ms) const noexcept
    {
        if (sampleRate <= 0.0 || ms <= 0.0)
            return 1.0;
        return 1.0 - std::exp(-1.0 / (1e-3 * ms * sampleRate));
    }

    double currentEnvDb() const noexcept
    {
        return 10.0 * std::log10(env2 + kEnvFloor);
    }

    // The law: flat at and below `ref`, then a progressive high-shelf CUT.  It
    // is one-sided on purpose — a BOOST below the reference would lift the top
    // end at low level, which is not what the reference does and would move the
    // static response in the one region the model already gets right.
    double gainFor(double envDb) const noexcept
    {
        return std::clamp(-k * (envDb - ref), -maxCut, 0.0);
    }

    void recompute(double envDb) noexcept
    {
        const double g = gainFor(envDb);
        lastGainDb = g;
        shelf.setHighShelf(sampleRate, f0, S, g);
    }

    // ---- RBJ (Audio EQ Cookbook) high-shelf biquad, direct-form I -----------
    struct ShelfBiquad
    {
        void setHighShelf(double fsIn, double cornerHz, double slopeS, double gainDb) noexcept
        {
            if (fsIn <= 0.0 || cornerHz <= 0.0 || cornerHz >= 0.5 * fsIn)
                return;
            const double A = std::pow(10.0, gainDb / 40.0);
            const double w0 = 2.0 * M_PI * cornerHz / fsIn;
            const double cosw0 = std::cos(w0);
            const double sinw0 = std::sin(w0);
            const double Ss = std::max(slopeS, 1e-3);
            const double alpha = 0.5 * sinw0 * std::sqrt((A + 1.0 / A) * (1.0 / Ss - 1.0) + 2.0);
            const double sq = 2.0 * std::sqrt(A) * alpha;

            const double b0 = A * ((A + 1.0) + (A - 1.0) * cosw0 + sq);
            const double b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw0);
            const double b2 = A * ((A + 1.0) + (A - 1.0) * cosw0 - sq);
            const double a0 = (A + 1.0) - (A - 1.0) * cosw0 + sq;
            const double a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw0);
            const double a2 = (A + 1.0) - (A - 1.0) * cosw0 - sq;

            B0 = b0 / a0; B1 = b1 / a0; B2 = b2 / a0;
            A1 = a1 / a0; A2 = a2 / a0;
        }

        inline double process(double x) noexcept
        {
            const double y = B0 * x + z1;
            z1 = B1 * x - A1 * y + z2;
            z2 = B2 * x - A2 * y;
            return y;
        }

        void reset() noexcept { resetState(); B0 = 1.0; B1 = B2 = A1 = A2 = 0.0; }
        void resetState() noexcept { z1 = z2 = 0.0; }

        double B0 = 1.0, B1 = 0.0, B2 = 0.0, A1 = 0.0, A2 = 0.0;
        double z1 = 0.0, z2 = 0.0;
    };

    ShelfBiquad shelf;
    double sampleRate = 48000.0;
    double env2 = 0.0;
    double smooth = 1.0;
    double timeMs = 50.0;
    double lastGainDb = 1e9;

    bool enabled = false;
    double f0 = 5388.0, S = 0.85, k = 0.203, ref = -33.9, maxCut = 6.0;
};
