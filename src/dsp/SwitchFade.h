#pragma once

#include <algorithm>

// =============================================================================
// SwitchFade — the per-stage dual-instance crossfade ramp (open-work item 14, S2)
// =============================================================================
// `dist_engage` (s171) is a MIX override, so smoothing it was one coefficient
// ramp inside `LevelBlend`. The four SELECTOR switches are not: ATTACK and GRUNT
// swap capacitor networks inside `TrebleAttack` / `Clipper`, and the two
// mid-frequency selectors swap `MidBand`'s series/across cap PAIR. Each of those
// re-solves an MNA matrix, so there is no coefficient to interpolate — the stage
// simply *is* a different circuit either side of the flip.
//
// `architecture.md` names the remedy: a **dual-instance crossfade**. On a flip the
// live stage is copied into a SHADOW (state and topology both), the live stage
// takes the new position, and for the fade window both are driven by the same
// input while their outputs are crossfaded. So:
//
//   mix = 0  →  exactly what the pedal would have produced had nothing been flipped
//   mix = 1  →  exactly what the pedal produces in the new position
//
// ⭐ Copying rather than starting the shadow from rest is the physically right
// move, not a convenience: a mechanical switch does not discharge the caps around
// it, so the old network's stored charge IS the correct initial condition for the
// arm that keeps running. Starting the shadow at zero state would replace one
// discontinuity with a different one.
//
// ⚠⚠ THE SETTLED PATH MUST BE THE IDENTICAL CODE PATH, not this crossfade
// evaluated at mix = 1 — the same design constraint `LevelBlend::processAt` carries
// and for the same reason. `OfflineRender` never flips a switch mid-render and
// calls `reset()` after `setParams()`, so every rendered sample runs with every
// fade SETTLED; each call site below is therefore written as an `active()` branch
// around the untouched pre-change expression. That is what makes the 162-capture
// matrix bit-identical and is why this change owes NO re-baseline, unlike
// s162/s163/s166.
//
// ⚠ `tick()` lands EXACTLY on 1.0 rather than approaching it (`std::min`), because
// `active()` is a strict `< 1.0` test — an asymptotic ramp would leave the shipped
// steady state permanently inside the interpolating arm and silently destroy the
// property above. Same trap, same fix, as `LevelBlend::tickSmoothing`.
//
// ⚠ RE-FLIP DURING A FADE is handled but is not seamless, and that is stated
// rather than papered over: `start()` re-primes the shadow from the live stage and
// restarts at 0, so the output steps by `(1 - mix)` of the *previous* pair's
// divergence — bounded by, and strictly smaller than, the unsmoothed step this
// whole mechanism exists to remove. Reaching it needs two flips of the same switch
// inside `kSeconds`; a foot or a finger cannot, and no test covers it.
// =============================================================================
struct SwitchFade
{
    // ⚠ NOT inherited from `LevelBlend::kDistFadeSeconds` (12 ms) — that one was
    // swept against its OWN worst cell, and these four switches have far larger
    // divergences (hiMidFreq @mids-boost read 39.47x unsmoothed against
    // `dist_engage`'s worst 53.8x but at a much smaller absolute step). Swept
    // against `SwitchTransitionTest`'s own bar, worst selector cell of 32:
    //
    //     8 ms 0.98x | 10 ms 1.00x | 12 ms 0.83x | 15 ms 0.66x | 20 ms 0.50x
    //    25 ms 0.40x | 30 ms 0.33x
    //
    // ⭐⭐ FROM 12 ms UP THE STATISTIC IS PURELY FADE-RATE-LIMITED, and that is what
    // makes this a measurement rather than a preference: `ratio x t` reads
    // 9.96 / 9.90 / 10.00 / 9.90 / 9.90 ms across 12-30 ms — constant to 1 %, i.e.
    // an exact 1/t law. A floor artefact does not scale with fade speed (s154), so
    // the bar is genuinely tracking the ramp here. ⚠ Below 12 ms it LEAVES that law
    // (8 ms measures 0.98x where 1/t predicts 1.24x), so those two points are not
    // on the mechanism the bar measures and were not used to choose the value.
    //
    // ⭐ The worst cell is NOT phase-sampled noise: re-run at 16 flip phases instead
    // of 4, every figure above is IDENTICAL. That is a free validation of the
    // instrument's own `n`, not just of this constant.
    //
    // ⇒ 20 ms: a 2x margin inside the 1/t region, and the top of the "~5-20 ms"
    // band item 14 states for this class of transition rather than headroom
    // invented outside it. ⚠ A 12 ms choice would sit at 0.83x — thinner than it
    // looks, because the bar's own operands are measured at 4 pot configs, not a
    // continuum.
    static constexpr double kSeconds = 0.020;

    // Begin a fade at the sample rate the OWNING STAGE runs at. ATTACK and GRUNT
    // live inside the oversampled region and the two mid selectors do not, so the
    // rate is passed per call rather than stored once — an OS-factor change moves
    // it for two of the four and not the other two.
    //
    // ⚠ A non-positive rate would make `step` non-finite and the ramp would never
    // land ON 1.0, i.e. the bit-identical settled branch would stop being
    // reachable — a silent loss of the property this design rests on, not a crash.
    // Refuse to start rather than fade with a broken step.
    void start(double sampleRate) noexcept
    {
        if (! (sampleRate > 0.0))
        {
            mix = 1.0;
            return;
        }
        step = 1.0 / (kSeconds * sampleRate);
        mix = 0.0;
    }

    // A rate change is not a switch flip, and neither is a transport reset.
    void reset() noexcept { mix = 1.0; }

    bool active() const noexcept { return mix < 1.0; }

    inline double blend(double shadowOut, double liveOut) const noexcept
    {
        return shadowOut + mix * (liveOut - shadowOut);
    }

    // Call ONCE per sample per fade, after every `blend()` that reads this mix —
    // GRUNT crossfades at two points in the chain (the clipper's cap network and
    // `OdToneRestore`'s grunt-keyed table) and both must see the same mix.
    inline void tick() noexcept { mix = std::min(1.0, mix + step); }

    double mix = 1.0;   // 0 = shadow (pre-flip topology), 1 = live (post-flip)
    double step = 1.0;
};
