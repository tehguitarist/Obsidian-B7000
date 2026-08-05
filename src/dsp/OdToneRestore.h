#pragma once

#include <algorithm>
#include <cmath>

// =============================================================================
// OdToneRestore — engineered (NON-SCHEMATIC) drive-tracking notch/peak restore
// =============================================================================
// User-authorised tone-fidelity correction, session 150 (2026-08-04). Not fitted
// to any component value and not claimed as a model of any physical mechanism —
// item 6's search for a physical carrier of this behaviour is EXHAUSTED on every
// named candidate at/around the clipper (CLAUDE.md CLOSED/REFUTED table), so this
// is a deliberate empirical restore rather than another mechanism screen.
//
// WHAT IT FIXES. Measured directly against `analysis/captures/drive-*_base-od.wav`
// (DRIVE ladder 0/.25/.5/.75/1.0, sweep_drv_-12, `feature_locus_gate.py`'s own
// locate() instrument, session 150): the model's 320 Hz null ("mid_notch") and its
// ~450-500 Hz recovery peak ("mid_peak") were both far shallower than the pedal's
// at EVERY drive setting, and the 320 Hz null barely tracked drive at all (pedal
// prominence rises smoothly 0.53 -> 3.24 dB across the ladder; model sat at
// 0.00 -> 0.19 dB throughout). The user confirmed both by ear directly against
// real captures and requires this fixed regardless of mechanism purity. The
// ~800 Hz bridged-T notch ("bt_notch") was already close (gap <= 0.14 dB across
// the ladder) and is NOT touched here.
//
// HOW. Two RBJ (Audio EQ Cookbook) peaking biquads, gain/Q driven directly by the
// DRIVE knob (0..1) via a 5-point piecewise-linear breakpoint table matching the
// measured pedal-minus-model deficit at each ladder rung. Deliberately NOT an
// envelope-follower / dynamic filter — the correction tracks the DRIVE CONTROL,
// not the instantaneous signal level, which is simpler, alias-free, and is what
// "must track drive" means operationally (the user is turning the knob, not
// asking for a compressor-style dynamic notch). Runs inside the oversampled
// region, OD-path only (never touches the clean tap) — inserted in
// PedalChain::runOdSample() between `recovery` and `skB`.
//
// The notch also SHARPENS (Q rises) as it deepens with drive, per the user's own
// recollection of the real pedal's behaviour — modelled as a linear breakpoint
// table on Q, same drive axis as the gain table.
//
// ⛔⛔ SESSION 150's TABLES WERE MEASURED THE WRONG WAY AND ARE RETIRED — session
// 151 re-derived them. Keep this paragraph: both defects are easy to re-commit.
//   (1) WRONG FIT SET. They were read off `drive-*_base-od.wav` / `ref-od.wav`,
//       which sit at LEVEL = 0.5. GATE K2: bleed vanishes only where BOTH LEVEL
//       and BLEND are max, and s113 measured LEVEL-noon/BLEND-max output at ~44 %
//       clean signal. This stage is in the OD path, so roughly half of whatever it
//       does was diluted before the analysis read it — the deficits came out 3-5x
//       too small, AND a fit there silently prices in one LEVEL setting.
//       ⇒ FIT BLEED-FREE (`drive-0700_level-1700`, `level-1700`, `drive-1700_level-1700`),
//         then CHECK across LEVEL and BLEND. `analysis/od_tone_restore_fit.py`.
//   (2) WRONG STATISTIC. They were tuned against GATE W `locate()`'s PROMINENCE,
//       whose `mid_notch` window is a FIXED [285, 358] Hz band and whose prominence
//       is min(rise-to-left-edge, rise-to-right-edge). The model's curve declines
//       across that whole window, so the argmin sat ON the right edge and the
//       statistic read ~0 for ANY notch depth — `measurement-discipline.md`'s
//       "A PROMINENCE MEASURED AT A WINDOW EDGE IS IDENTICALLY ZERO BY CONSTRUCTION"
//       (s126). Chasing it drove Q to 32 (a 10 Hz needle) and the centre down to
//       310 Hz, both purely to buy window room. A prominence is a fine DETECTOR
//       and a bad OBJECTIVE. ⇒ measure DEPTH against the null's own shoulders, with
//       the argmin search (285-372 Hz) decoupled from the shoulder search (210-520).
//   ✅ NOT a defect: the biquad math and the sample rate. The shipped C++ reproduces
//      an independent RBJ implementation to 4e-6 dB (standalone impulse->DFT probe,
//      s151), so session 150's "structural bug" branch is closed.
//
// MEASURED BLEED-FREE, s151 (sweep_drv_-12, 1/48-oct, GATE W's own smooth()):
//   DRIVE      0.00     0.50     1.00
//   pedal depth   8.59    13.92    19.08 dB   <- RISES monotonically with drive
//   model depth  14.54    11.80     2.76 dB   <- FALLS; washes out at max
//   correction   -5.96    +2.12   +16.31 dB   <- CHANGES SIGN
//   pedal Q       5.21     8.65    11.54      <- sharpens as it deepens (user's ear)
//   model Q       4.26     5.28     7.42
// The pedal's centre is stable at 322.8 Hz at all three rungs; the model's own is
// 327.5 Hz. This is GATE R/V's documented "the model's OD path saturates too early,
// so its null washes out where the pedal's deepens", read at one frequency.
//
// AND THE SAME READ AT THE OTHER TWO GRUNT POSITIONS (bleed-free, stage subtracted,
// mean of the three realistic sweeps -18/-12/-6; `--set grunt_flat|grunt_boost`):
//   DRIVE            0.00     0.50     1.00
//   Flat  correction +13.99  +16.56  +21.88 dB   (model has NO null at all at DRIVE max)
//   Boost correction +11.79  +12.58   +9.65 dB
// ⇒ GRUNT is the LARGEST axis of this defect, not a refinement of it: at Cut the
// model's null is roughly the right size and at Flat/Boost it is 10-25 dB short.
// ⚠⚠ AND NOTE THE STIMULUS-LEVEL SPREAD BEHIND THOSE MEANS — it is large and it is
// the architectural limit of a knob-keyed stage (see the caveat block at setDrive()).
//
// ⭐ WHY NOT JUST EXAGGERATE THE EXISTING NULL WITH THE ELEMENTS THAT MAKE IT
// (the obvious question, asked by the user s151): because the correction CHANGES
// SIGN across the ladder. The null is a cancellation in the linear pre-clipper
// treble/ATTACK ladder (GATE R's R2: it moves 329.7 -> 164.2 Hz with the ladder caps
// and ignores the bridged-T), so any static element change adds the SAME amount at
// every drive rung — it cannot be -5.96 at one end and +16.31 at the other. Making
// such an element drive-dependent IS open work item 6, where every named physical
// carrier is refuted (CLAUDE.md CLOSED/REFUTED). And GATE Y (s126) separately
// measured that the ladder constants which DO move this region dissolve the 320 Hz
// null and the mid peak outright (prominence 7.27 -> 0.00 dB). Refuted on both.
// =============================================================================
class OdToneRestore
{
public:
    void prepare(double fs) noexcept
    {
        sampleRate = fs;
        notch.reset();
        peak.reset();
        recompute();
    }

    void reset() noexcept
    {
        notch.resetState();
        peak.resetState();
    }

    // driveKnob in APVTS space, 0..1 (PedalChain::Params::drive).
    void setDrive(double driveKnob) noexcept
    {
        const double x = std::clamp(driveKnob, 0.0, 1.0);
        if (x == lastDrive)
            return;
        lastDrive = x;
        recompute();
    }

    // GRUNT position, as Clipper::Grunt (0 = Cut, 1 = Flat, 2 = Boost).  ⚠ NOT the APVTS index —
    // PedalChain::gruntEnum() maps APVTS {Boost, Cut, Flat} onto {Cut, Flat, Boost}, and this
    // stage is keyed on the PHYSICAL position so its table reads in the same order the captures
    // and `circuit.md` use (Cut < Flat < Boost by bass into the clipper).
    void setGrunt(int gruntPos) noexcept
    {
        const int g = std::clamp(gruntPos, 0, 2);
        if (g == lastGrunt)
            return;
        lastGrunt = g;
        recompute();
    }

    // Fraction of the FINAL output that will be clean-tap signal, in [0,1].  Read straight off
    // the shipped mix stage (`LevelBlend::cleanFraction()`), never recomputed here.
    //
    // ⭐⭐ WHY THIS STAGE NEEDS IT AT ALL (GATE AT, session 156).  This stage is upstream of
    // LEVEL and BLEND, so the cut it must apply to land the COMPOSITE null on the pedal's
    // depends on how much clean signal is summed on top of it afterwards — and until now it
    // could not know that.  Measured, the cut needed at LEVEL noon exceeds the bleed-free cut by
    // 6-13 dB, so the s151 table (fitted bleed-free) was ~8 dB short at the user's own listening
    // condition and at DRIVE 0 had the WRONG SIGN there: it BOOSTED 6.5 dB at 320 Hz where a
    // 1.2 dB cut was wanted.  That is what "the null is worse at low gain" was.
    //
    // ⭐ One scalar is provably enough.  LEVEL and BLEND are both downstream, so the requirement
    // cannot depend on them separately — only on the single number they jointly produce.  GATE
    // AT's AT2 falsification-tested that on captures reaching the same clean fraction by
    // different routes (LEVEL 0.25/BLEND max vs LEVEL max/BLEND 0.50, and two more pairs):
    // worst disagreement 0.05 dB.  ⇒ this covers EVERY LEVEL/BLEND combination, including ones
    // with no capture, which is what the user asked for.
    // ⛔⛔⛔ THE DEPTH CEILING — READ THIS BEFORE INCREASING ANY NUMBER IN kNotchGainDb.
    // At a diluted mix the COMPOSITE null depth SATURATES against the clean tap, and past that
    // point more OD-path cut buys nothing.  Measured two ways at cleanFrac = 0.441 (LEVEL noon,
    // GRUNT cut, DRIVE 0.5, sweep_drv_-12), s156:
    //   (a) a deliberate 40 dB probe on this row produced a composite null of 0.472 dB against
    //       the pedal's 3.533 — SHALLOWER than the 1.600 dB the shipped 12.34 dB cut gives,
    //       because at that depth the RBJ section is narrower than the 1/48-oct analysis (and
    //       the ear) resolves, so the extra depth is averaged away;
    //   (b) +1.20 dB added to this whole row moved the listening-condition depth by 0.03 dB
    //       while moving the BLEED-FREE error by 1.11 dB — it costs accuracy where it acts and
    //       buys nothing where the user listens.  It was tried and reverted.
    // ⇒ the ~1.0-1.5 dB that still separates model from pedal at LEVEL noon is NOT a tuning
    // miss and is NOT reachable from this stage.  It is the mix: the model's OD path is ~4.4 dB
    // quiet (A3 / GATE O), so its null is diluted harder by the clean tap than the pedal's is at
    // the same knob positions.  The lever is A3, not this notch.  ⛔ Do not "fix" it here.
    void setCleanFraction(double cf) noexcept
    {
        const double x = std::clamp(cf, 0.0, 1.0);
        if (x == lastCleanFrac)
            return;
        lastCleanFrac = x;
        recompute();
    }

    inline double process(double x) noexcept
    {
        x = notch.process(x);
        x = peak.process(x);
        return x;
    }

private:
    // ---- breakpoint tables (drive knob 0/.25/.5/.75/1.0) --------------------
    static constexpr double kX[5] = { 0.0, 0.25, 0.5, 0.75, 1.0 };

    // ⚠⚠ ROWS ARE GRUNT POSITIONS {Cut, Flat, Boost} AND THE CORRECTION CHANGES SIGN
    // ACROSS THEM, so one row cannot serve all three.  Measured bleed-free at DRIVE 0
    // with this stage's own response subtracted out, the model's null is **5.7 dB TOO
    // DEEP at Cut** and **15.6 / 19.4 dB TOO SHALLOW at Flat / Boost** (pedal 8.59 /
    // 21.77 / 24.92 dB against model 14.32 / 6.20 / 5.55).  A single row fitted at Cut
    // applies a 6.4 dB BOOST at Flat/Boost, where the null is already far too shallow —
    // measured, that made those two positions **4.5 dB WORSE** than leaving the stage
    // out entirely.  That is what the GRUNT dimension exists to prevent.
    //
    // ⭐ THE CENTRE DOES **NOT** NEED TO TRACK GRUNT — checked, and an earlier s151
    // reading that said it did was ONE CELL.  At GRUNT boost x DRIVE max the pedal's
    // null reads 238.3 Hz at `sweep_drv_-12` but **322.8 / 327.5 / 322.8 Hz at the
    // other three sweeps**, so 322.8 Hz serves every GRUNT position and one anomalous
    // cell was nearly promoted into a "the feature migrates" claim.  Read all four
    // sweeps before calling anything a migration (`an-endpoint-pair-is-not-a-ladder`).
    //
    // ⚠ At Flat/Boost the model has almost NO null of its own (and none at all in
    // several DRIVE-max cells), so the composite is essentially this biquad alone —
    // which is why those Q rows START from the PEDAL's measured Q and converge in one
    // iteration (composite/pedal Q ratio 1.01-1.22), where the Cut row has to fight
    // the model's own broad null (Q ~4-7) and stalls at 1.35-1.51 too broad.
    // ⛔ That Cut residual is STRUCTURAL, not a tuning miss: a single peaking section
    // adding a few dB at the centre cannot narrow a null that is already 14 dB deep
    // and broad. Narrowing it needs a second section shaping the SHOULDERS. Do not
    // spend more gain iterations on it.
    // ⛔⛔ AND THAT SECOND SECTION WAS BUILT, SCREENED AND REFUTED — SESSION 161, GATE AX
    // (`analysis/notch_shoulder_gate.py`).  User-authorised as task A with a 2-iteration cap;
    // it cost one, and NOTHING SHIPPED.  Read this before adding any section here.
    //   ⭐ The sentence above is CONFIRMED on the axis it was written about: with a second
    //     section present the pedal's Q is reachable at **9 of 9** Cut cells against **5 of 9**
    //     for one section (AX2).  So s151's "structural" claim and AQ2's measurement both stand.
    //   ⛔ It is refuted on the four things that only appear once you ask what would SHIP:
    //     (1) the CURVE barely wants it — a free third section buys a **median 0.080 dB** of fit
    //         on `fit_rung`'s own objective, against the 320 Hz term's **1.56 dB**, and s156
    //         REJECTED the ~800 Hz candidate at **0.058 dB**.  This term sits with the rejected
    //         one.  Its fitted gain changes sign (+16.2 … −6.0) and rests on a bound in 2 of 9.
    //     (2) LIKE-FOR-LIKE IT LOSES to simply re-fitting the two sections already here: matched
    //         on (depth, Q), mean curve rms **shipped 1.257 / existing family re-solved 1.167 /
    //         third section 1.222 dB**, and it beats the re-solve in only 3 of 9 cells.
    //         ⚠ A first pass compared the third section against the SHIPPED tables (1.286 → 0.780)
    //         and it looked decisive — but that re-solves two constants WHILE adding a section, so
    //         the gain is not attributable (`verify-the-BASELINE-not-its-LABEL`).
    //     (3) IN THE SHIPPABLE FORM IT FAILS TASK A's OWN ACCEPTANCE.  One (cut, broad) pair per
    //         DRIVE rung across all three stimulus sweeps — which is what these tables can express
    //         — given its fairest shot (both its Q and its gain swept, cut re-solved so the depth
    //         holds) moves mean |Q error| **0.97 → 0.81, 4.09 → 3.05, 5.15 → 3.49**: real, nowhere
    //         near "below the reader's resolution", and it COSTS depth error at two of three rungs.
    //         The table it asks for has no law — gain **−13.0 / +10.0 / −13.0**, Q 4.5 / 1.5 / 9.0.
    //     (4) ⭐⭐ AND THE REASON NO FURTHER ITERATION IS OWED: **the shipped Q error is already
    //         SMALLER than the target's own across-stimulus spread at 3 of 3 rungs** (spreads
    //         1.46 / 5.52 / 10.20 against errors 0.98 / 4.04 / 5.19).  A knob-keyed entry is
    //         already inside the ambiguity of the thing it is fitting, so "closer to the pedal's
    //         Q" is not well defined for ANY single number, whatever family produces it.  That is
    //         s151 §6's architectural limit on a FOURTH axis, after AQ2b's Q, AR6's metric
    //         residual and AU's peak gain — and AQ2b already said to read it as an argument for
    //         leaving `kNotchQ` ALONE.
    //   ⚠ SCOPE: this refutes A SECOND PEAKING SECTION AT THE NULL'S OWN CENTRE, which is the
    //     family s151/s153 named and the user authorised.  It does not refute every conceivable
    //     shoulder treatment (two off-centre sections, an asymmetric or non-biquad shape) — but
    //     (4) bounds the VALUE of all of them: none can beat the target's own spread.
    //
    // ⭐⭐ SESSION 153 (GATE AQ, `analysis/notch_shape_gate.py`) TESTED ALL THREE OF THE
    // CLAIMS ABOVE.  The "STRUCTURAL" verdict SURVIVES and is now a measured LIMIT rather
    // than a stalled iteration — but the two numbers around it do not survive as stated:
    //   (1) ⛔⛔ "1.35-1.51 too broad" WAS MEASURED ON A QUANTISED READER AND IS ONE TO TWO
    //       OF ITS STEPS.  `notch_geometry`'s `q` snapped both half-depth crossings to whole
    //       1/48-oct GRID CELLS, so it could only ever return 1/(2^(m/48) − 2^(−n/48)) for
    //       integer (m, n) — above Q~8 the attainable values are {8.65, 11.54, 17.31} and
    //       NOTHING between, and true Q of 8, 10 and 11 all read 8.651 (errors to −42 %).
    //       ⇒ use `q_interp` (same definition, crossings interpolated in log-f; strictly
    //       monotone, recovers an injected Q to ±0.003 %).  On it the Cut ratios read
    //       0.85-1.68 at DRIVE 0/0.5 and 0.66-1.44 at DRIVE max — i.e. the defect changes
    //       SIGN across the stimulus rungs, which the quantised reading concealed.
    //   (2) ⛔ "EXACTLY on the pedal's 11.54 at DRIVE max" (kNotchQ's own comment below) is
    //       a QUANTISATION COINCIDENCE — 11.538 is one of the eight values `q` can return.
    //   (3) ⭐ REACHABILITY, measured rather than inferred: sweeping the section's Q to 120
    //       with the DEPTH re-solved at every rung, the pedal's Q is attainable by ONE
    //       section in 21 of 26 cells.  All 5 failures are in the CUT row — and Cut × DRIVE
    //       0.50 fails at ALL THREE sweeps (pedal Q 13.91 against an attainable 3.50-9.46),
    //       so that entry has no shape-matched solution at any Q.  ⇒ the "second section
    //       shaping the shoulders" is owed at CUT ONLY; Flat and Boost reach at every cell,
    //       so do NOT generalise the structural claim to them.
    // ⚠⚠ AND BEFORE SPENDING ANY OF THAT: AQ2b measured whether "the pedal's Q at this
    // entry" is even a single number.  It is not — at FIXED (GRUNT, DRIVE) the pedal's own
    // Q spans **1.29x-2.93x across the three stimulus rungs**, which is as large as the
    // defect being chased and larger in 8 of 9 cells.  That is s151 §6's architectural limit
    // (a knob-keyed stage cannot track a stimulus-dependent feature) measured for the first
    // time on the Q axis, and it bounds what any (gain, Q) table here can achieve.
    //
    // ⭐ AND NOTE WHICH REFERENCE GOVERNS HERE. `reference-sources.md` §1 makes
    // **HARDWARE**, not ND, the authority for this null's DEPTH, and §3 records
    // hardware deeper than ND in all six measured conditions — **+1.6 dB at GRUNT
    // cut rising to ~26 dB at GRUNT boost**.  So the ND-matched numbers below are a
    // LOWER BOUND on what hardware wants, and increasingly so as GRUNT opens up.
    // ⛔ §3 is a PNG read: sign and rough size only, never a fit target (§5 rule 3).
    //
    // ⛔⛔ USER DECISION, SESSION 153 — **THESE VALUES STAY AS THEY ARE.  DO NOT RE-SOLVE
    // THEM AGAINST THE AREA METRIC.**  GATE AP (s152) measured what a censor-robust
    // 1/6-octave POWER-INTEGRATED depth asks for instead, in this table's own unit, and
    // 7 of 9 entries wanted LESS gain (to −4.92 dB at Boost × DRIVE 0).  It was put to the
    // user and declined, on three grounds now on record:
    //   (1) the trade is a WASH — pooled mean |error| is 4.03 point / 2.06 area for this
    //       table against 4.54 / 1.54 for the area-solved one, i.e. entries move by up to
    //       4.92 dB while achieved error moves ~0.5 dB ⇒ the constant is WEAKLY IDENTIFIED,
    //       which is s151 §6's stimulus-level limit priced in the constant's own units;
    //   (2) HARDWARE is the authority for this feature (above) and is DEEPER than ND, so
    //       the smaller area-solved table moves AWAY from the governing reference;
    //   (3) which metric the EAR follows is established by nothing measured so far.
    // ⚠ What is NOT refuted: the censoring itself is real (16 of 26 pedal readings bottom
    // at or below the residue) and the area estimator is 4.1x less sensitive to it.  The
    // decision is about which target to fit, not about whether the censoring exists.
    // ⛔ And do NOT re-open this as "the shape was wrong" — s153 (GATE AQ) tested that; see
    // the GATE AQ block above.
    // ⚠⚠ SIZE CORRECTED, s154 (GATE AR): that test's "only 20 %" is an UNPAIRED statistic —
    // AQ4 averages each metric over the three stimulus sweeps BEFORE differencing, and the
    // shipped-Q gap CHANGES SIGN across that axis (-6.85 / -6.56 / +5.94 dB), so the mean
    // cancels it.  Paired, the SAME numbers read 6.83 -> 2.13 dB, i.e. matching Q closes
    // 69 %, and AP6's shape attribution is largely REHABILITATED rather than refuted.
    // ⭐⭐ THE DECISION ABOVE IS UNTOUCHED, and the reason matters at this constant: this
    // table has ONE entry per (GRUNT, DRIVE), so a mean over sweeps is exactly what gets
    // SHIPPED => AQ4's pooled figure is the right statistic for the shipping question and
    // the wrong one for a mechanism claim.  Only the mechanism inference moved, and the
    // paired residual (2.13 dB) still exceeds the fit's own +/-0.83 dB.
    // ⛔ Do NOT free the notch CENTRE to chase the remainder (s153's own proposed successor):
    // AR5a measures pedal and composite centres agreeing to within the reader's resolution
    // in 21 of 26 cells.  And AR6 measures the remainder CHANGING SIGN across stimulus, so
    // it is not a shape coordinate at all -- it is s151 section 6's architectural limit on a
    // third axis.  `analysis/notch_residual_gate.py`; `docs/session-log.md` SESSION 154.
    // ⭐⭐⭐ RE-FITTED AS A MIX-KEYED LAW, SESSION 156 (GATE AT, `analysis/od_notch_mix_law.py`).
    // These are no longer the whole answer: the cut actually applied is
    //
    //     cut(grunt, drive, cleanFrac) = kNotchGainDb[g][d] + kNotchMixK[g][d] * S(cleanFrac)
    //
    // with S pinned to 0 at kMixCfRef.  So THIS table is the cut at the REFERENCE clean fraction
    // (LEVEL noon / BLEND max = the user's listening condition), NOT the bleed-free cut the s151
    // table held.  ⚠⚠ The name survived a MEANING change — s146's `masterTaperBreak` lesson —
    // so anything reading these numbers as "the cut" is now wrong by up to 13 dB.  The Python
    // side parses all three tables together and refuses if any is missing, rather than falling
    // back to a two-table shape.
    static constexpr double kNotchGainDb[3][5] = {
        {  1.16,  6.18, 12.34, 20.27, 27.98 },  // Cut   — fitted s156 at cleanFrac = kMixCfRef
        { 18.33, 20.65, 23.07, 26.45, 29.83 },  // Flat  — fitted s156 at cleanFrac = kMixCfRef
        // ⚠⚠ Boost's DRIVE-max entry rests on ONE cell, not the "TWO valid cells" this
        // comment claimed until s153 — counted against the shipped build with the stage
        // subtracted (GATE AP's AP4): at `sweep_drv_-18` the MODEL reads "no null" and at
        // `sweep_drv_-12` BOTH sides do, leaving only `sweep_drv_-6`.  An unreadable cell is
        // NOT a correction of zero.  ⚠ AND FLAT's DRIVE-max entry is ALSO n=1 (model "no
        // null" at both -18 and -12) and went unflagged entirely.  These are the two weakest
        // numbers in this table.
        // ⭐ A SOLVE does better than the difference method here and the reason generalises:
        // it needs only the PEDAL side, because the candidate gain is what CREATES the
        // composite's null — so AP3 recovers Flat at n=3 and Boost at n=2.  A model-side
        // refusal is not missing data about the target; it is the model having no feature.
        { 17.15, 18.06, 18.74, 17.24, 15.74 },  // Boost — fitted s156 at cleanFrac = kMixCfRef
    };

    // How much the required cut moves as the mix changes, in dB per unit of S.  Measured as
    // cut(cleanFrac = 0) - cut(kMixCfRef) at each cell that has both captures; cells with only
    // one are interpolated ACROSS DRIVE and the tool prints which (never silently).
    // ⚠ GRUNT flat's DRIVE 0.25/0.75/1.0 entries are interpolated from the 0.0 and 0.5 rungs —
    // the thinnest numbers in this block.
    // ⭐ RE-DERIVED FROM THE ACCEPTANCE MEASUREMENT, not from the curve fit.  K only controls the
    // cleanFrac -> 0 end (S is pinned to 0 at kMixCfRef), so it is solved directly from the
    // residual depth error measured AT cleanFrac = 0 with the stage running:
    //     K = (cut_currently_applied_at_0 + measured_shortfall - base) / S(0)
    // That is a closed loop on the quantity actually being judged, and it CANNOT disturb the
    // listening condition, where S = 0 by construction.
    // ⚠⚠ It is one measurement per cell, not a fit — and the ⛔ block at setCleanFraction()
    // explains why another blind fit iteration was the wrong move here.  Cells with no bleed-free
    // capture at that drive are interpolated across drive; GRUNT boost DRIVE 0.75/1.0 have no
    // readable bleed-free null at all (the pedal's is past the reader's core bound there), so they
    // carry the DRIVE-0.5 value forward and are the weakest entries in this table.
    static constexpr double kNotchMixK[3][5] = {
        { -7.87, -8.61, -9.34, -9.50,  -9.65 },  // Cut
        { -1.56,  0.71,  2.97,  1.97,   0.97 },  // Flat
        {  3.40,  4.61,  5.81,  5.81,   5.81 },  // Boost
    };

    // S(cleanFrac): the shared, dimensionless shape of the mix dependence, pinned to 0 at
    // kMixCfRef.  Measured on the one densely-sampled axis (GRUNT cut, DRIVE noon, 18 distinct
    // clean fractions from the LEVEL ladder, the BLEND ladder and the LEVEL x BLEND grid), then
    // reduced to these nodes.
    //
    // ⚠⚠ THIS TABLE IS NON-MONOTONE ON PURPOSE: S RISES TOWARD THE BLEED-FREE CORNER (S(0) =
    // +0.951) AFTER DIPPING TO −0.525 AT cleanFrac ≈ 0.21.  With K negative on the Cut row that
    // makes the required cut PEAK at intermediate mix and fall toward cleanFrac → 0.  Do not
    // "repair" it into a monotone curve — the shape is physically expected, and the fix has
    // already been built once and reversed:
    //
    // ⛔⛔ THE CLAMP WAS BUILT, MEASURED AND REVERSED IN SESSION 156 — DO NOT RE-ADD ONE.
    // Three independent arguments said to hold S flat below its peak so the law would err DEEP at
    // LEVEL/BLEND max: the user's explicit instruction that session ("if they need to be too deep,
    // I'd prefer that"); the CENSORING (GATE AT's AT1d measured the pedal's null bottom sitting
    // 0.10 dB above the deconvolution residue at that corner, so its depth is a LOWER bound); and
    // `reference-sources.md` §1/§3, which make HARDWARE the authority for this null's depth and
    // record it DEEPER than ND by +1.6 dB at GRUNT cut rising to ~26 dB at boost.  All three
    // pointed the same way and all three were outvoted by the measurement: clamped, the composite
    // null came out **9.6–11.6 dB TOO DEEP** at LEVEL/BLEND max while every other mix landed
    // within 1–3 dB.  ⭐ Re-examined, the raw non-monotone shape is what the physics predicts —
    // the required cut peaks at INTERMEDIATE mix because that is where the model's own null is
    // diluted hardest while the pedal's target is still deep; at cleanFrac → 0 the model's own
    // null is already close, and at → 1 both wash out together.  A middle peak follows from that
    // with nothing to correct.
    // ⇒ `S_CLAMP_CF = 0.0` in `analysis/od_notch_mix_law.py` IS the shipped state (one named
    // constant, and the clamp is reproducible by setting it to 0.21 if anyone wants to re-measure
    // it).  ⚠ The censoring itself is NOT refuted — the bleed-free corner is still the least
    // resolvable reading in the set; what is refuted is clamping as the response to it.
    static constexpr int kMixNodes = 8;
    static constexpr double kMixCfRef = 0.441;
    static constexpr double kMixCf[kMixNodes] = { 0.000, 0.210, 0.320, 0.440, 0.560,
                                                  0.730, 0.870, 1.000 };
    static constexpr double kMixS[kMixNodes] = { 0.951, -0.525, -0.195, 0.000, 0.017,
                                                  0.177, 0.224, 0.252 };
    // The pedal's own measured null Q at GRUNT cut (5.21 / 8.65 / 11.54 at the three
    // measured drive rungs) — it SHARPENS as it deepens, which the user identified by
    // ear before any of it was measured.  The composite (the model's own null plus
    // this biquad) is narrower than either, so these were iterated against a
    // re-measure rather than derived: they land the composite Q within 1.36x at
    // DRIVE 0/0.5 and EXACTLY on the pedal's 11.54 at DRIVE max.
    // ⛔ s153: "EXACTLY on 11.54" IS A QUANTISATION COINCIDENCE, not a convergence —
    // 11.538 is one of only eight values the reader used here could return.  See the
    // GATE AQ block above; re-read any Q number in this file with `q_interp`.
    // ⭐ Re-fitted s156 at cleanFrac = kMixCfRef, jointly with the gain (the same solve returns
    // both, so they are not two independent guesses).
    // ⚠ Q is deliberately NOT given a mix axis, although one is measurable (it runs 15.9-21.4
    // across the clean fraction at GRUNT cut / DRIVE noon).  GATE AQ's AQ2b measured the PEDAL's
    // own null Q spanning 1.29x-2.93x across stimulus at FIXED (GRUNT, DRIVE) — larger than the
    // defect in 8 of 9 cells — so a Q axis here would be fitting a mean over a quantity that
    // moves further than the thing it corrects.  Depth is what the ear tracks and depth is what
    // is keyed.
    static constexpr double kNotchQ[3][5] = {
        {  3.05, 10.01, 16.07, 18.19, 17.95 },  // Cut
        { 14.62, 14.85, 15.77, 16.44, 17.10 },  // Flat
        { 16.71, 17.02, 17.68, 15.91, 14.15 },  // Boost
    };
    // ✅ ZERO ON PURPOSE, AND MEASURED — DO NOT ADD PEAK BOOST HERE.  The ~450 Hz peak
    // is largely the recovery BETWEEN the two notches, so it follows the notch on its
    // own.  The user's original "the peak isn't tall enough" was heard against a model
    // whose 320 Hz null was absent — a contrast complaint, not a height one, and fixing
    // the null fixed it.
    //
    // ⛔⛔ THE ORIGINAL REASON FOR THIS ZERO IS REFUTED — THE VALUE IS NOT.  s151 zeroed it
    // on a BLEED-FREE reading ("the model's peak is MORE prominent than the pedal's in 8 of
    // 9 GRUNT x DRIVE cells, so boosting would OVERSHOOT"), and s156 then proved this whole
    // stage's bleed-free-only fit wrong at the listening condition for the NOTCH.  GATE AU
    // (s157, `analysis/peak_identifiability_gate.py`) checked whether the peak had the same
    // disease.  It does: measured bound-free, the requested peak gain is **+1.44 dB at the
    // listening condition against −4.30 dB bleed-free** — it CHANGES SIGN with the mix, so
    // the bleed-free argument above cannot carry the decision.  ⇒ do not re-quote it.
    //
    // ⭐⭐⭐ WHAT REPLACES IT, AND WHY THIS STILL SHIPS AS ZERO — THREE MEASUREMENTS:
    //  (1) THE STATISTIC THAT REPORTED A DEFICIT CANNOT SEE THE PEAK'S HEIGHT.  GATE W's
    //      `mid_peak` prominence walks are bound-terminated in **48 of 48** readings — and
    //      that is STRUCTURAL, not a property of these captures: `locate()` takes `j` as the
    //      argmin over the window and then breaks each walk on `dd[k] < dd[j]`, which is
    //      unreachable by construction.  So `prom` is `min(left max-descent, right
    //      max-descent)` inside a FIXED [358, 620] Hz window; here the curves are monotone to
    //      both bounds, so it reduces EXACTLY to `min(d[peak]−d[358], d[peak]−d[620])` — a
    //      two-point read of the window's own bounds, i.e. of the 320 Hz null's and the
    //      bridged-T's flanks.  ⚠ `locate`'s `edge` flag does not catch this (it fires on the
    //      EXTREMUM, which is interior in 24 of 24 rows).
    //  (2) READ ANYWAY, THE DEFICIT CHANGES SIGN ACROSS DRIVE (+1.08 … −0.85 dB at the
    //      listening condition), so it names no direction to correct.
    //  (3) ⭐ DECISIVE — THE TERM IS NOT IDENTIFIABLE.  A peak of this shape is not separable
    //      from the quadratic-in-log-f trend the fit deliberately discards, and THAT TREND IS
    //      A3.  At the shipped Q = 2.2 it keeps only **31 %** of its own norm after that trend
    //      is projected out, against the notch term's **85 %** (2.71x).  A fitted +1.3 dB
    //      would therefore deliver ~+0.41 dB of shape the trend could not already explain; the
    //      rest is A3 handed to a biquad — `one-knob-two-jobs-is-compensating`, and exactly how
    //      s156 §3 rejected the 800 Hz candidate ("A3 seen as a shape").
    //      ⭐⭐ And it is STRUCTURAL: separability rises monotonically with Q on this band and
    //      only reaches the notch's 85 % above Q ≈ 20 — while this feature is BROAD by nature
    //      (it is the recovery between two notches).  The shape that would be identifiable
    //      here is not the shape the feature has.  ⇒ no (gain, Q) choice fixes this.
    // ⚠ Corroborating, not load-bearing: 15 of 24 joint fits rest a parameter on a bound, and
    // the requested gain spans **15.25 dB** across the three stimulus sweeps at one fixed
    // (set, DRIVE) cell — s151 §6's architectural limit on a third axis, after AQ2b's Q and
    // AR6's metric residual.
    //
    // ⚠ What remains at that feature is a CENTRE error (model/pedal median **1.093x**, 22 of
    // 24 readings high — GATE AU's AU1b, on a wider set than s151's 507.6 / 453.5 / 381.9 Hz
    // vs 466.7 / 418.0 / 362.8), which this stage does not address and which GATE W has
    // already classified as NOT a corner error.
    static constexpr double kPeakGainDb[5] = { 0.0, 0.0, 0.0, 0.0, 0.0 };

    static constexpr double kNotchFreq = 323.0; // the PEDAL's own centre, stable across the ladder
    static constexpr double kPeakFreq = 405.0;  // the pedal's recovery-peak locus at DRIVE noon
    static constexpr double kPeakQ = 2.2;

    static double lerp5(const double* table, double x) noexcept
    {
        if (x <= kX[0]) return table[0];
        if (x >= kX[4]) return table[4];
        for (int i = 0; i < 4; ++i)
        {
            if (x <= kX[i + 1])
            {
                const double t = (x - kX[i]) / (kX[i + 1] - kX[i]);
                return table[i] + t * (table[i + 1] - table[i]);
            }
        }
        return table[4];
    }

    // S(cleanFrac), piecewise-linear over kMixCf/kMixS, flat outside the node range.
    static double mixShape(double cf) noexcept
    {
        if (cf <= kMixCf[0]) return kMixS[0];
        if (cf >= kMixCf[kMixNodes - 1]) return kMixS[kMixNodes - 1];
        for (int i = 0; i < kMixNodes - 1; ++i)
        {
            if (cf <= kMixCf[i + 1])
            {
                const double t = (cf - kMixCf[i]) / (kMixCf[i + 1] - kMixCf[i]);
                return kMixS[i] + t * (kMixS[i + 1] - kMixS[i]);
            }
        }
        return kMixS[kMixNodes - 1];
    }

    void recompute() noexcept
    {
        const int gi = std::clamp(lastGrunt, 0, 2);
        // cut(grunt, drive, cleanFrac) = base + K * S(cleanFrac).  See setCleanFraction().
        const double cutDb = lerp5(kNotchGainDb[gi], lastDrive)
                             + lerp5(kNotchMixK[gi], lastDrive) * mixShape(lastCleanFrac);
        const double notchGainDb = -cutDb;                             // CUT at the notch
        const double notchQ = lerp5(kNotchQ[gi], lastDrive);
        const double peakGainDb = lerp5(kPeakGainDb, lastDrive);        // BOOST at the peak

        notch.setPeaking(sampleRate, kNotchFreq, notchQ, notchGainDb);
        peak.setPeaking(sampleRate, kPeakFreq, kPeakQ, peakGainDb);
    }

    // ---- RBJ (Audio EQ Cookbook) peaking biquad, direct-form I, double precision.
    struct PeakingBiquad
    {
        void setPeaking(double fs, double f0, double q, double gainDb) noexcept
        {
            if (fs <= 0.0) return;
            const double A = std::pow(10.0, gainDb / 40.0);
            const double w0 = 2.0 * M_PI * f0 / fs;
            const double alpha = std::sin(w0) / (2.0 * std::max(q, 1e-6));
            const double cosw0 = std::cos(w0);

            const double b0 = 1.0 + alpha * A;
            const double b1 = -2.0 * cosw0;
            const double b2 = 1.0 - alpha * A;
            const double a0 = 1.0 + alpha / A;
            const double a1 = -2.0 * cosw0;
            const double a2 = 1.0 - alpha / A;

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

    double sampleRate = 48000.0;
    double lastDrive = -1.0; // force recompute on first setDrive()
    int lastGrunt = 0;       // Clipper::Grunt::Cut — matches captures.py's own default
    // ⚠ Defaults to the REFERENCE clean fraction, not to 0 — so a host or test that never calls
    // setCleanFraction() gets the listening-condition table rather than silently the bleed-free
    // extreme (S(kMixCfRef) = 0, i.e. the base table is used verbatim).
    double lastCleanFrac = kMixCfRef;
    PeakingBiquad notch, peak;
};
