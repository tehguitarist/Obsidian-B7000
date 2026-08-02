# Measurement discipline — the traps, each paid for by a real session

> Consolidated in session 89 (2026-07-31) from ~88 session handovers and the project memory files.
> **Every entry below cost at least one session to discover, and several inverted a conclusion that
> had already been written down as fact.** They are ordered by how often they have recurred.
>
> This is a rules file, not a reading list: skim it when you start, and re-read the relevant
> section before you (a) build a new instrument, (b) trust an aggregate, or (c) ship a constant.
> Per-incident detail is in `docs/session-log.md` and `docs/phase9-gap-log.md`.

---

## 1. Before you trust an instrument

- **Verify the baseline reproduces BEFORE ranking anything.** Every tool that ranks candidates must
  first re-score the shipped point against its own recorded value and REFUSE to print if it moves.
  (`SHIP_RECORD` pattern, s77.) A baseline that has silently moved makes every comparison a fiction.
- **Verify the CONSTANT, not the prose.** A handover saying "SHIPPED" is a claim about a file; it is
  one `grep` to check. `trebleC7` was documented as shipped for a whole session while `FitParams.h`
  still read the old value. (s35)
- **Verify the BASELINE, not its LABEL.** A row labelled `none (H = 1)` was fitting a free broadband
  gain; four sessions of "improvement over baseline" measured the wrong thing. (s37)
- **Verify the PREMISE, not the prior session's framing of it — SEVEN occurrences.** A
  14-session-old gap characterisation had expired — unrelated fixes had dissolved it — and
  re-measuring took one command. A stale premise is the most expensive kind, because it selects the
  whole next workplan. (s38)
  - ⭐⭐ **AND A BACKLOG LINE CAN OUTLIVE ITS OWN DISSOLUTION BY 70 SESSIONS, BECAUSE THE LABEL
    TRAVELS AND THE REFUTATION DOES NOT.** "GRUNT off-flat — 1.68–1.85×, GAP #3b" sat at the head of
    the queue as the next item to open. Both halves were dead: session 38 had **dissolved GAP #3b**
    (and proved no GRUNT cap can reach the target — the C12 locus moves the peak right-and-DOWN,
    the pedal sits right-and-UP, off the curve in both coordinates at once), and the 1.68–1.85×
    came from a set conditioned on a premise session 103 **refuted** (`blend = 1.0` is not
    bleed-free). Neither refutation had been written back into the line that cites it. ⭐ GENERAL:
    when an item is about to be opened, grep the gap/session log for its own NAME first — a
    dissolution is usually recorded where the work happened, not where the item is listed. Cost
    here: one grep against a whole session. ⚠ And when you find it, **fix the line and the source
    comments**, or the next session pays again. (s108)
- ⭐ **"THE TEST ASSERTS IT" IS A CLAIM ABOUT ONE OPERATING POINT.** `Clipper.h`'s header says the
  D1/D2 clamps "essentially never fire (the test asserts it)". Measured at drive 0.85 / 8×, disabling
  them changes the output and removes an aperiodic regime — they fire, and `ClipperTest` passes
  because it probes a gentler point. A passing assertion bounds the region it was run in, nothing
  more; when a header cites a test as proof of an *always* statement, check the test's own
  conditions before relying on it. (s92, same family as `verify-the-CONSTANT-not-the-prose`)
- **An iteration budget justified at one sample rate is not justified at another.** The same
  header predicts "~2–4 iters" for its Newton solve; true at 48 kHz, false at the 384 kHz
  oversampled rate, where 6 iterations left a measurable residual (0.35 dB on the alias figure) and
  a 4-of-21-tone aperiodic regime. Re-check any convergence claim at the rate the stage actually
  runs at, not the rate it was designed at. (s92)
- **A gate must be calibrated against the defect's SIGNATURE, not a proxy for it.** A flat-topping
  gate keyed on "16 consecutive samples above 0.985×peak" rejected a long-trusted reference capture
  peaking 7.6 dB below full scale — a sine spends ~5.5 % of its period up there. The real signature
  is a plateau *pinned* at the converter's ceiling. (s68)
- **Run a new gate against a case whose answer you already know.** A gate demanding "every OD capture
  moves" failed on a render already proven sound, because 6 rows are inert *by construction*
  (BLEND=0 ⇒ OD out of circuit). That is the only thing separating "the candidate is bad" from "my
  gate is bad". (s84)
- ⭐⭐ **A DEFECT ATTRIBUTED TO AN INSTRUMENT IS A HYPOTHESIS, AND IT IS USUALLY CHEAPER TO TEST THAN
  TO FIX.** "`transfer()` is a CSD, so it cannot reject harmonics" was written down as fact, selected
  a whole session's workplan, and is **wrong**: an exponential sweep separates orders **in time**
  (~1 s/octave here) against a 170 ms Welch window, so the CSD passes a known-answer test with H2/H3
  at −10/−14 dB re the fundamental. The replacement instrument moved the headline **the wrong way**
  (2.95 → 2.99 dB). The one-line version: *an argument for why an instrument must be wrong is not a
  measurement of it being wrong* — synthesise the contaminated case first, and only build the
  replacement if the old read actually fails. (s90)
- ⭐⭐ **WHEN YOU LAND A FITTED POINT AS THE NEW DEFAULT, PROVE IT BY RENDERING — AND EXERCISE EVERY
  SWITCH POSITION, BECAUSE PER-POSITION CONSTANTS ARE DEAD IN THE OTHERS.** Transcribing 17 values
  from a fit log into `FitParams.h` is exactly the kind of mechanical step that looks unfalsifiable
  and is not: render once with the new defaults and once with the original `--fit` list, and require
  **bit-identity**. That catches a value in the wrong field, a dropped digit, or a flag that never
  reaches the DSP (the session-20 `--input-trim` defect). ⚠ The trap is scope: the first run here
  used ONE ATTACK throw, so `attackC5TrimCut` and `attackDampCut` — live only in the cut throw —
  were never evaluated and the check would have passed with either of them wrong. Loop the switch.
  ⚠ And keep a **mutation control** (`attackDampCut ×2` must change the render): without it a
  constant that silently never reaches the stage makes both sides equal and the check reads PASS for
  the very defect it exists to catch. ⭐ The payoff is that the prior matrix report then IS the
  shipped grade, with no 25-minute re-render — but only because bit-identity was measured, not
  assumed. (s100)
- ⭐⭐ **A KNOWN ANSWER THAT STARTS AT ITS OWN ANSWER IS A FIXED POINT, NOT A TEST — AND IT LOOKS
  PERFECT.** GATE L's inverse was validated by "run it on the MODEL and it must return the shipped
  `L = x^2.25`". It did, to **±0.00000, rms 0.000 dB** — and the check was worthless as written,
  because the optimiser was *initialised* at `x^2.25`. A stationary point reproduces itself; that
  says nothing about whether any other taper fits equally well. The repair is one line and it
  changes the check from decorative to load-bearing: start from vectors that do **not** resemble
  the answer (here p = 0.5 and p = 4.0, which bracket it, plus three random monotone vectors) and
  require them all to land in the same place. They did, to **1e-3**, which is what makes the
  recovered curve a measurement rather than an initialisation artefact. ⭐ GENERAL: for any
  iterative recovery, the known answer must include a **start far from the truth**; "it reproduced
  the reference" is only evidence if it could have failed to. Same family as
  `imposed-checks-cannot-corroborate` — there the fit was constrained to satisfy its own check,
  here it was *seeded* with it. (s104)
- ⭐⭐⭐ **AN UNSIGNED AGGREGATE NEVER SAID WHICH WAY, AND A HANDOVER WILL EVENTUALLY SUPPLY A SIGN
  IT DOES NOT HAVE.** The gated "THD level term = 3.663 dB" is `abs(c[0])/sqrt(n)` RMS'd over 228
  rows — a MAGNITUDE. `CLAUDE.md` glossed it for eighteen sessions as *"the model's distortion
  amount being systematically low"*, and item 3 of the open-work list was written around that
  reading. The **signed** mean of the same decomposition (`level_signed`, already computed and
  already stored by `shape_gate.py`) is **+1.263 dB**: the model distorts **MORE** than the
  reference, not less. Measured independently on the bleed-free OD endpoints the gap is **+2.94 dB**,
  same sign. ⇒ every candidate reasoned about as "we need more distortion" was pointed backwards.
  ⭐ GENERAL: an `abs()` in a headline statistic is a one-way door — the direction has to be
  carried alongside it or the next reader invents one, and the invented sign is 50 % likely to
  select the whole next workplan wrong. Print the signed term beside every unsigned one. Same
  family as `abs()-on-an-unobservable-sign-is-fine-differencing-it-is-not` (s33), one level up:
  there the sign was lost in the data, here it was lost in the summary. (s109)
- ⭐⭐ **A THRESHOLD YOU GUESSED IS NOT A GUARD — MEASURE THE DISTRIBUTION AND PLACE THE BAR IN ITS
  GAP, THEN ASSERT THE GAP.** GATE Q's reference-dropout guard was first written at "12 dB, and
  that is deliberately generous". It printed a clean pass and **missed the defect by 0.41 dB**.
  Measured, the statistic is cleanly bimodal — the worst healthy rung sags **−0.35 dB** and the
  defect sits at **+11.59**, an 11.94 dB gap with nothing between — so any bar in that gap gives
  the identical answer and the honest guard asserts the SEPARATION rather than a count. ⭐ The
  corollary is the useful half: if the population is NOT bimodal, no threshold is defensible and
  the gate should say so instead of trimming a tail (`self-selecting-scores`). A generous bar feels
  conservative and is not — it is just a different arbitrary number, and it fails in the flattering
  direction. (s109, GATE Q3)
  - ⭐⭐⭐ **AND THE FOLLOW-ON THAT COST SESSION 113 A WRONG CLASSIFICATION: "THE BIGGEST GAP IN THE
    SORTED VALUES" IS NOT A BIMODALITY TEST.** GATE S needed to separate condition-matched twin
    pairs from re-dialled ones, and its first bar was the largest ratio between adjacent sorted
    residuals, gated at ≥ 20×. That is satisfied by **any** population with one big step in it —
    including a smooth continuum — so it is a gap-*hunt* dressed as the entry above. It split at
    0.00002/0.00900 and classified a **0.009 dB** pair as mis-dialled when the gate had *already
    measured* recording repeatability at **0.0099 dB** from two takes of one condition. ⭐ The fix
    is the generalisable part: **take the bar from a quantity measured INDEPENDENTLY of the thing
    being classified** — here a take-to-take floor, which says what "the same thing twice" looks
    like — and then report anything within 3× of it as not robustly classified. The s109 entry
    above is about placing a bar in a gap you have *shown* exists; this is about not inferring the
    gap from the very ranking you are about to cut. (s113, GATE S3)
- ⭐⭐⭐ **A DESIGNED COINCIDENCE BETWEEN TWO AXES IS A FREE CONDITION-MATCH TEST, AND IT SURVIVES
  THE NONLINEARITY — USE IT BEFORE TRUSTING ANY MATCHED PAIR.** The capture set's stimulus rungs are
  12 dB apart and the interface-send pad is also 12 dB, so a `gain-n12` capture at `drv_-6` and its
  full-send twin at `drv_-18` present the **same absolute level to the same device**. Their outputs
  must therefore agree — *however nonlinear the path is*, with no linearity assumed anywhere, which
  is why it reaches the OD path where every clean-path known answer stops. Measured, it returns
  **0.00000 / 0.00000 / 0.00002 dB at DRIVE min / noon / max** and **0.066 / 0.322 dB at DRIVE 0.25
  / 0.75** ⇒ the knob was re-dialled between capture sessions and reproduced exactly **only where
  the pot has a mechanical reference** (both hard stops and the centre detent). ⭐ Two lessons:
  **(a)** a "matched pair" is an assumption until something tests it, and a twin-pair instrument
  built on a mismatched pair mixes the axis under test with a knob step that no averaging removes;
  **(b)** the same construction gives the MODEL side a known answer with **no free parameter** —
  the harness pad exceeds the ladder step by 0.071 dB, so the model's residual must be −0.0710 and
  it measures −0.0705. One subtraction certified the absolute reconstruction, the rung mapping and
  the pad at once. ⚠ Note what this does NOT touch: the 153-capture matrix never differences two
  captures against each other, so a mis-dialled twin is invisible there and is a **capture** fact,
  not a model one. (s113, GATE S3)
- ⭐⭐ **A SHIPPED STAGE'S CLOSED FORM TAKES THE STAGE'S INPUT, NOT THE UI's — AND A TAPER SITS
  BETWEEN THEM.** GATE S computed each capture's clean-bleed fraction by calling
  `level_law_gate.coef_closed` (the shipped `LevelBlend` algebra, correctly imported rather than
  re-derived) with the **knob** value stored in the capture's settings. That function takes the
  **tapered** level. At LEVEL noon the knob is 0.5 but the stage sees `0.5 ** 2.25 = 0.21`, so the
  call returned clean/OD = **−6.02 dB** where the shipped stage actually delivers **−2.05** — every
  bleed fraction wrong, in a plausible, monotone, entirely reasonable-looking way. ⭐ It was caught
  only by diffing against GATE K2's own recorded table, which is the argument for keeping such
  tables in the handover at all. **When importing a stage's algebra, check what domain its argument
  is in**, and read the taper exponent from the module that validates it against the source rather
  than applying one you assume. (s113)
- ⭐⭐ **"OUT OF SAMPLE MUST REPRODUCE" IS THE WRONG FRAME WHEN THE OUT-OF-SAMPLE ROWS SIT AT A
  DIFFERENT OPERATING POINT — AND SCORING IT THAT WAY REPORTS PHYSICS AS FAILURE.** GATE S's first
  S6 required the non-ladder OD twins to reproduce the DRIVE ladder's compression at their own
  DRIVE, and duly reported departures up to 23 dB as a corroboration failure. They sit at different
  LEVEL, i.e. at a different **mix**: the clean tap does not compress, so it dilutes the measured
  law, and the departure IS the dilution being measured. ⭐ Re-framed, it became the session's
  second-largest finding — at LEVEL noon / BLEND max the output is **44.1 % clean signal**, so the
  compression measured there is **3.6× shallower** than the bleed-free reading of the same
  condition, and any statistic taken at LEVEL noon understates the OD path by that much. **Before
  writing a reproduction test, ask what else differs between the two sets and whether the model
  predicts them to differ.** (s113, GATE S6)
- ⭐⭐ **ONE BAD (capture, sweep) CELL WAS THE WORST ROW IN THE MATRIX FOR AN UNKNOWN NUMBER OF
  SESSIONS, AND NOTHING LOOKED FOR IT BECAUSE NOTHING KNEW THE LADDER WAS A LADDER.** The four
  sweeps are the SAME sweep at −30/−18/−12/−6 dBFS, so the reference's band-median must be monotone
  — a compressive path cannot lose 25 dB in the middle and get it back. Testing exactly that found
  `drive-1700_level-1700_grunt-boost_base-od.wav @ sweep_drv_-12` reading +3.5 dB against +15…+23
  at both neighbours. It is **the worst FR row and the second-worst THD row of the shipped
  `shape_gate` decomposition**, and it was carrying **0.70 dB of GATE Q's 5.36 dB score on its
  own**. ⭐ GENERAL: when a capture set contains a designed monotone axis (a level ladder, a pot
  detent sweep, a drive sweep), that monotonicity is a FREE per-row validity check on the
  reference — cheap, assumption-light, and it catches dropouts no aggregate ever will. Look for one
  in every matrix. ⚠ It is NOT the session-48 `gain-n12` defect: different file, session and
  signature, and it means the standing "one known-bad group" framing was incomplete. (s109)
- ⭐⭐ **A `nan` DOES NOT TRIP A THRESHOLD, SO ONE BAD VALUE CAN DISABLE A WHOLE GATE BRANCH WHILE
  EVERYTHING PRINTS FINE.** GATE N guards its bands with `value <= FLOOR`; the report carries three
  **non-finite** THD entries per record, and `nan <= 0.05` is **False**, so they sailed through.
  They then poisoned the power median to `nan` — and `nan < MIN_POWER_DB` is **also False**, which
  silently disabled the UNDERPOWERED branch the gate exists to enforce. The gate reported a clean
  PASS on a check that could not fire. ⭐ GENERAL: **test `isfinite` explicitly and first**, never
  rely on a comparison to exclude a non-finite; and treat a `nan` appearing anywhere in a printed
  column as a gate failure, not as a cosmetic blemish. Every comparison against `nan` is False, so
  a poisoned statistic fails *open* — the direction that flatters. Same family as
  `empty-gate-must-fail`, but harder to spot, because the gate produced plenty of data and only the
  guard was dead. (s106, GATE N3)
- ⭐⭐ **SWEEP A THRESHOLD OVER A RANGE THAT ACTUALLY BINDS, AND ASSERT THAT IT BINDS.** GATE N's
  robustness column swept the THD floor 0.02 → 0.20 % and printed **four identical rows**, which
  reads as an unusually strong result. It was nothing: the lowest real THD in the data is ~0.25 %,
  so no band was ever excluded at any of those settings and the knob was not turning. A robustness
  sweep whose parameter never changes the membership is not a robustness check — it is a constant
  printed four times. ⭐ Fix: print the surviving count beside every row and **exit** if the count
  is the same at every setting. (s106, GATE N5 — the second occurrence of s105 M4's
  `an implausible coincidence is a bug report`, and again the broken version was the flattering one.)
- ⭐⭐ **A "KNOWN-BAD" LABEL IS A CLAIM WITH A DATE ON IT, AND THE FIX THAT RETIRES IT OFTEN LANDS
  WITHOUT ANYONE RE-RUNNING THE TEST.** The 16 `gain-n12` OD rows were excluded from every project
  headline for **58 sessions**. Both halves of the documented fix had since landed — the harness
  started emitting `--input-trim`, and the four files were re-captured — and the check that would
  clear them was written down as a next step and never run. Re-measuring took one command and the
  rows are healed; retiring the exclusion moves the headline **0.020 dB**. ⭐ GENERAL: when a
  handover carries an exclusion, check the *remedy's* status, not just the finding's — an exclusion
  is the most expensive kind of stale premise because it silently shrinks every aggregate downstream
  of it. ⚠ And say what the re-test cannot do: the defective files were overwritten by the
  re-capture, so this certifies the current files and does **not** contradict the original finding.
  (s106, GATE N; same family as `verify-the-PREMISE-not-the-prior-session's-framing-of-it`)
- ⭐⭐⭐ **THE TOPOLOGY WILL HAND YOU A FREE KNOWN ANSWER IF YOU ASK WHAT IT *FORBIDS* — AND ONE
  COMPARISON CAN VALIDATE A WHOLE INSTRUMENT.** MASTER is a post-EQ, attenuation-only divider into a
  unity buffer with nothing nonlinear downstream (C36 corners at 0.72 Hz), so a MASTER law error is
  a **pure gain** and is *forbidden* to have frequency structure. Measured between two captures from
  the same session it is **2.0240 dB at every band, span 0.0002 dB over 25 Hz – 16 kHz**. That
  single check simultaneously certifies the absolute reconstruction, the band mapping, the sweep
  handling, the provenance correction, **and** circuit.md's own claim about the stage — none of
  which it was built to test. ⭐ GENERAL: before building a validation, look down the signal chain
  for a stage whose physics forbids some structure, and measure that structure. It costs one
  subtraction and it fails loudly. ⚠ This is the constructive twin of
  `a-recovered-quantity-that-must-be-invariant-and-isnt-is-a-refutation` (s104 L6): there a broken
  invariance killed a model form, here an intact one certifies an instrument. Both are worth more
  than any absolute residual, because neither has a threshold to argue about. (s107, GATE O6)
- ⭐⭐ **AN IMPLAUSIBLE COINCIDENCE IS A BUG REPORT — AND CHASING IT IS RIGHT EVEN WHEN IT TURNS OUT
  NOT TO BE A BUG.** Two different band selections (100–400 Hz and broadband non-HF) reported the
  MASTER law as **exactly 2.024 dB**, which should not happen for a quantity whose raw per-band
  curve spans 0.33 dB. It was not a bug: the provenance-corrected law is algebraically a
  **same-session** difference, and same-session the divider genuinely is flat. But the only way to
  learn that was to go and look — and what the look produced was the strongest known answer in the
  gate plus the discovery that the *raw* ladder is not the taper. ⭐ GENERAL: treat exact agreement
  between two things that had no reason to agree as something to **explain**, not to enjoy; the
  explanation is either a defect or a structure you did not know you had. Second occurrence of
  s105's M4 entry, and the first where the answer was benign. (s107, GATE O5/O6)
- ⭐⭐⭐ **A FAILING GATE IS A HYPOTHESIS ABOUT THE MODEL *OR* ABOUT THE GUARD, AND FIVE SESSIONS
  ASSUMED THE FIRST.** GATE I exited non-zero from session 109 to 113. Session 111 bisected it across
  four reports, found it passed on s99 and failed on s109 onward, and concluded *"session 109's
  `kInputRef` change broke it"* — sound arithmetic, and the conclusion was carried forward by three
  more sessions as a standing item. It is **refuted**: the guard required the **whole OD path** to
  hold the rolloff rate of **two of its elements** (the post-clipper Sallen-Keys), when the path also
  contains the treble/ATTACK ladder, C7, C10, C14 and the recovery bridged-T — and **ATTACK is
  literally an HF control**. Measured, the model's rate spans **18.9 dB/oct within a single cell**
  across ATTACK and GRUNT, so the quantity the guard constrained is not required to hold on *any*
  version of the model. Rebuilt, the gate passes on **every report from s91 to s113**. ⭐ GENERAL: a
  bisection tells you *when* a statistic started failing, never *whether the statistic was valid* —
  and a guard that goes red right after a real change is maximally convincing, because the change
  supplies a ready mechanism. **Before attributing a gate failure to the thing that changed, re-derive
  what the guard assumes and check the physics still requires it.** ⚠ Note the shape of the near-miss:
  the tempting repair was widening the 6 dB/oct bar, which would have kept the gate green *and*
  preserved the false diagnosis. The right repair deleted the quantity. (s114; same family as
  `an-instrument-defect-is-a-hypothesis`, one level up — there the instrument was suspected and was
  fine, here it was trusted and was not)
- ⭐⭐ **WHEN A GUARD'S PREMISE IS WRONG, DELETE THE QUANTITY — DO NOT LOOSEN THE BAR.** The two are
  indistinguishable from the failing number alone and completely different in consequence: loosening
  keeps a meaningless statistic alive and silently absorbs whatever it was masking, while deleting
  forces you to find what the gate is actually *for*. GATE I's replacement needs **no threshold at
  all** — at the hottest stimulus every one of the 15 pedal conditions gains with frequency and every
  one of the model's rolls off, a complete separation (gap +17.44 dB/oct) — and it is a **min-vs-max**
  over all conditions, i.e. **stricter** than the median comparison it replaced. ⭐ That is the tell
  worth keeping: **if the rebuilt test is harder than the one it replaces and still passes, it is a
  correction; if it is easier, it is a concession.** Same lesson as the s95/s96 CLEAN row split, on a
  guard rather than a pool. ⭐ And look for a free **dose-response** while you are there: the
  separation grows monotonically with stimulus (−0.67 → +7.46 → +11.92 → +17.44), which a
  drive-generated artefact must do and a fixed filter difference cannot — a parameter-free validity
  check that fell out of the same numbers. (s114)
- ⭐⭐⭐ **SELECTING ROWS BY FILENAME SUBSTRING IS A TIME BOMB: IT DOES NOT FAIL WHEN IT IS WRITTEN, IT
  FAILS WHEN SOMEONE ADDS CAPTURES.** GATE I picked its "bleed-free OD" rows with `"level-1700" in
  fname` and its clean control with `"base-clean" in fname`. Both were correct on the capture set that
  existed when they were written. Three later batches broke them, and **every break was invisible**:
  (a) s112's `level-1700_blend-0930/1200/1430` joined the *bleed-free* classes carrying 25–75 % clean
  signal — GATE K2 had already established that bleed vanishes only where BOTH BLEND and LEVEL are
  max — and duly read ~0 dB/oct, i.e. they ARE the clean path sitting in the OD row; (b) `gain-n12`
  twins joined the same cells at an operating point 12 dB down the compression curve (s108 P4);
  (c) a MASTER-only duplicate double-weighted one condition (s110 R7, found and fixed in GATE R and
  never propagated here). ⭐ And the clean control was worse in the other direction: `"base-clean"`
  **excludes `ref-clean.wav`** (no such token) while **including 36 EQ-swept captures**, so "is our
  clean HF right?" was a median over a set whose 4.3 dB spread *is the TREBLE knob*. ⇒ **resolve
  membership from SETTINGS, then ASSERT it** (exact counts, named exclusions, one vote per condition)
  — a substring is a guess about a naming convention, and naming conventions are not versioned.
  (s114; the same root cause as `aggregate-moved-check-membership-first`, but here nothing moved
  because nothing was ever right)
- ⭐⭐ **WHEN YOU COLLAPSE DUPLICATES, PICK THE REPRESENTATIVE BY USABLE DATA — NOT ALPHABETICALLY —
  AND ASSERT THEY AGREE INSTEAD OF DISCARDING THEM.** Session 114's first dedup took `sorted(...)[0]`,
  which in the MASTER ladder selects `master-0700_gain-n12`: at MASTER minimum **the model mutes**
  (max plugin −640 dB, GATE L7's finding on the second `[ENG]` divider). The silent-row guard then
  dropped all four sweeps and **the whole condition vanished**, leaving the control at n=1 with
  nothing printed to say anything had been lost. Which capture represents a condition is a real
  choice (s112's `PREFER_FULL_SEND_NOON`) and it must be made on the data, not on filename order.
  ⭐ The other half is free value: MASTER is a pure gain and both statistics were contrasts, so the
  duplicates **must** agree — asserting it (measured **1.16e−07 dB/oct** across nine detents) turns a
  discard into a known answer, and it is the 4th independent confirmation of circuit.md's pure-gain
  claim. A dedup that throws information away is a missed check. (s114)
- **Mutation-test a guard.** A new `assert_anchors_match` read the wrong JSON key, returned `None` on
  every real report and fell through to its "cannot verify" branch — a warning that reads as
  diligence while checking nothing. (s88, same class as s80)
  - ⚠ **And mutate the guard's predicate TRUE, not FALSE — `if False:` DISABLES a guard rather than
    firing it.** Two of session 114's ten mutations did exactly that and reported "GUARD DEAD"
    against two perfectly good guards. s110's rule applied again: **suspect the mutation before the
    guard.** For an exit-on-empty guard the meaningful mutation is at the *data* level (make the
    class genuinely empty), not at the predicate. (s114)
- **A control measured on the quantity the instrument ANCHORS on cannot fail.** An odd-order control
  scored H3 and returned `+0.00` everywhere: every side is anchored on its own H3/H1 crossing, so H3
  is pinned by construction. Rebuilt on H5 it moved. (s80)
- **A suggestion with the right shape can still be wrong; the check is the cheap part.** (s83)

- ⭐⭐ **A BOUND DERIVED FOR A COMPONENT IN ISOLATION IS NOT A BOUND ON THE COMBINED SHAPE.**
  `JfetStage.h` documents `|a|*s < 2.598` for the even bump, derived for the bump alone and quoted
  for eight sessions as if it bounded `waveshape()`. Scanned on a 3 µV grid at the shipped
  s/cPos/cNeg/beta, the combined map folds back at **a = 5.333 (|a|*s = 2.431)** — the core's own
  negative curvature near the cutoff knee subtracts from the bump's slope before the bump alone
  would turn over. Session 73's rejected `a ≈ 5.7` was therefore **non-monotone**, not merely
  worse-scoring. **Scan the real function, not the sub-term's algebra**, and gate it three ways:
  the shipped point as a known answer, the candidate, and a value that MUST fold (mutation). (s91)

## 2. Aggregates, membership and range

- ⭐⭐⭐ **ADDING VALID CAPTURES CAN CLOSE A GATE ROW WITH NO MODEL CHANGE — AND THE POOLED HEADLINE'S
  WEIGHTS ARE NOTHING BUT THE CAPTURE INVENTORY.** Session 112 re-rendered the matrix onto 26 new
  captures. OD band-RMS fell **2.327 → 2.154** and the OD 100 Hz–8 kHz median went from `over` back
  to **STRETCH** — i.e. the one OD row the project has ever closed appeared to close again. Nothing
  in `src/` moved. **12 of the new captures sit at intermediate BLEND**, where the clean bleed
  dilutes the OD path's error (their own band-RMS is **0.798** against the existing set's 2.432), and
  they drag the pooled mean down on their own. ⭐ The check that settles it in one command: **re-grade
  the new report restricted to the captures the old one had.** Every gated cell came back
  byte-identical, so 100 % of the movement was membership. ⭐⭐ The durable fix is not to exclude the
  data — that is backwards — but to **print the composition of the pool along the dominant axis**, so
  a weight shift can never again read as progress. Here BLEND spans **0.225 → 3.499 dB, 15.6×**,
  which is far larger than the defect being measured. ⇒ this is session 108's P4 rule (*do not pool
  over an operating point the pedal itself sets*) applied to the **headline gate**, not to a one-off
  instrument, and it is `aggregate-moved-check-membership-first`'s **ninth** occurrence — the first
  where the aggregate moved the *flattering* way because the data set grew. (s112)
- ⭐⭐⭐ **A SATURATED CAPTURE READS AS A *FLAT REGION OF THE CONTROL LAW*, WHICH IS A PLAUSIBLE
  PHYSICAL RESULT — SO CHECK A LADDER'S ENDS FOR PINNING BEFORE READING ITS SHAPE.** The MASTER
  ladder's top two detents, `master-1545_gain-n12` and `master-1700_gain-n12`, both peak at exactly
  **0.98850 (−0.10 dBFS)** and both read **+14.053 dB re noon — step +0.000**. A pot whose top eighth
  of travel does nothing is odd but not absurd, and nothing in the pipeline objected; the two files
  had been in the matrix since July. They are two takes of ONE output: the audio differs by
  **1.5e−04 (−76 dBFS)**. ⭐ Two checks settle it in under a minute: **(a)** the peak sample — two
  detents landing on the *same* peak to five decimals is not a taper; **(b)** the waveform difference
  — a limiter engaging harder at the louder setting would change the SHAPE, so identical-to-−76 dB
  means the recorder saw the same signal, not a squashed one.
  ⚠⚠ **AND THE OBVIOUS THIRD CHECK — CAPTURE THE SAME DETENT AT A LOWER SEND, WHICH ESCAPES THE
  CEILING — TURNED OUT TO NEED ITS OWN VALIDATION, BECAUSE AN UNUSABLE CAPTURE CAN STILL "CONFIRM"
  THE RIGHT ANSWER BY COINCIDENCE.** An archived lower-send capture of the same detent read
  **+15.5 dB, above the pinned +14.053** — exactly the direction expected of an escape, so it was
  accepted on the spot. It was caught only because a SECOND, unrelated defect at the same session
  forced a closer look (see the entry below on the send-pad constant): that session's
  `ref-clean_gain-n18` had a 12.3 dB span against a pure-gain requirement of ~0. Direct comparison of
  the suspect master file against a freshly re-captured replacement of the SAME detent gave an
  **11 dB span with a ±5 dB ripple** — physically impossible for a pure-gain stage (asserted, GATE
  O6) — so the whole archived session was contaminated, and the "confirming" +15.5 had been noise
  that happened to land on the right side of +14.053. ⭐ GENERAL: a check built to catch a pinned
  ceiling assumes its OWN capture is clean; verify that assumption with the same rigor (a
  physically-forbidden-structure test, or a second independent capture of the identical condition).
  Two fresh, cross-validated replacement captures resolved the ladder for real: **+16.480 /
  +18.500 dB**, monotone, with the top step (+2.02 dB) decelerating exactly as an A-taper approaching
  full CW should.
  ⚠⚠ The expensive part is downstream: a shipped constant (`kOutputMakeup = 2.599`) was calibrated
  at that very detent and re-confirmed as "+0.007 dB" there — a reading that may be measuring the
  ceiling. **When a calibration anchor sits at the END of a control's range, check that end for
  pinning first**; the ends are exactly where a capture chain runs out of headroom, and exactly where
  anchors are conventionally placed. Same family as `defective-rows-must-not-vote`, but the defect is
  invisible because it is *quiet and self-consistent* rather than wild. (s112)
- ⭐⭐ **A CONSTANT MEASURED FROM ONE PAIR IS A CONSTANT MEASURED FROM ONE PAIR, AND THE PAIR IT CAME
  FROM IS THE LEAST LIKELY TO CONTRADICT IT.** `captures.py` pads every `gain-n12` render by
  **12.071 dB**, annotated "measured 2026-07-22, ref-clean.wav vs ref-clean_gain-n12.wav" — a single
  cross-session pair. Four fresh linear twins say the send is **12.000 dB with a span of 0.0003 dB**,
  and a second instrument sharing no machinery (THD turnover, nonlinear, immune to any record gain)
  independently returns **12.000 / 12.000 / 12.001**. The original pair reads 12.158 with a 0.334 dB
  tilt — it is the **outlier**, and because it was the only pair available, its idiosyncrasy became
  both the constant *and* a recorded claim about the device (GATE O5: "ND's clean path is not
  level-invariant"), which is now refuted. ⭐ GENERAL: when a calibration constant has exactly one
  source, the first replicate is worth more than any amount of downstream analysis built on it — and
  if that replicate disagrees, check whether a *finding* was also derived from the same source.
  ⚠ Note what made this safe to spot: the twins are on a **linear** path, so the difference is
  *required* to be flat, and flatness (sd 0.000) is what certifies the measurement before its value
  is read. (s112)
- ⭐⭐ **RESOLVE A CAPTURE'S IDENTITY BY ITS SETTINGS, NOT ITS FILENAME — ONE CONDITION CAN HAVE TWO
  LEGITIMATE NAMES.** Two gates hard-exited on session 111's new captures, both from the same cause.
  GATE N looked for `drive-1200_gain-n12`'s full-send twin by transforming the filename and refused
  when `drive-1200_base-od.wav` did not exist — but the twin is **`ref-od.wav`**, because DRIVE noon
  *is* the reference baseline. GATE O2's MASTER ladder refused "two captures at master=0.5" when a
  new `master-1200_gain-n12` joined `ref-clean.wav` at noon — a real ambiguity, but only because the
  two sit at **different sends**, which the detent key did not carry. ⭐ Both fixes are the same
  shape: try the name transform **first** (so every prior pairing resolves identically and old quotes
  stay reproducible), then fall back to matching the settings dict on everything except the axis in
  question, and make an **ambiguous** match a hard failure rather than a pick-the-first. ⚠ And when
  the choice genuinely re-bases a recorded result — which capture serves master noon moves GATE O's
  ledger — make it a **named constant defaulting to the old behaviour**, with the trade-off written
  at the constant, instead of taking it as a side effect of a re-render. (s112)
- ⭐⭐⭐ **POOL vs EXCLUDE IS A FALSE CHOICE — WHEN TWO SUB-POPULATIONS DISAGREE, *SPLIT*. AND THE
  TEST FOR WHICH IS "DOES POOLING FLIP THE VERDICT ON THE POPULATION THE BAR WAS WRITTEN FOR?"**
  The THD gate row pooled full-send rows with `gain-n12` rows: pooled **2.974 = SHIP**, full-send
  alone **3.084 = over**, `gain-n12` alone **1.748**. The bar (3.0) was agreed in session 89 against
  a membership that excluded `gain-n12` outright — so pooling was letting a 33-row group with a
  different operating point overturn the verdict on the 289 rows the bar actually describes.
  ⭐ The decisive point is that the disagreement was **signal**: GATE S measured the model's
  distortion rising with input faster than the reference's, so 12 dB down the send its excess
  distortion nearly vanishes (+1.53 → +0.03). Averaging destroyed exactly the second-operating-point
  information that made those rows worth grading in the first place. ⇒ **excluding loses data,
  pooling hides the defect, splitting does neither** — the session-96 CLEAN move, and the same tell
  applies: **keep the original bar on both halves.** Inventing a new threshold for the new row is how
  a split quietly becomes a concession. ⚠ Expect it to COST a row (6 over SHIP → 7); a gate getting
  more accurate usually looks like a gate getting worse. ⚠ And re-check the sub-populations' own
  numbers before quoting the *reason* for the split: s111 justified the warning with "two
  OPPOSITE-signed populations" (−0.772 at n=15), and by s114 the group was n=33 at **+0.032** — near
  zero, not negative. The split still stood, on the disagreement and the flipped verdict, but the
  recorded rationale had gone stale exactly the way a headline does. (s114)
- ⭐⭐ **A CONSTANT THAT PADS *ONE SIDE* OF A COMPARISON IS INVISIBLE TO A GAIN-MATCHED AGGREGATE AND
  VERY VISIBLE TO AN ABSOLUTE ONE — SO "the matrix does not move" IS NOT EVIDENCE IT DOES NOT
  MATTER.** The send-pad constant renders the MODEL 0.071 dB quieter than the pedal was driven on
  every gain-session capture. `comprehensive_report` gain-matches every row, so the headline moved
  **2.149 → 2.149** — and GATE K/M/O/Q's absolute ledgers, which are not gain-matched, were wrong by
  that amount the whole time. ⭐ The acceptance check that makes such a fix safe is a **scope** check,
  not a size check: against the previous baseline on identical membership, **122 captures
  bit-identical, 40 `gain-n12` moved, 0 non-`gain-n12` moved** — if anything outside the intended set
  moves, the constant reaches further than you thought. ⚠ And check the magnitude of the outliers
  rather than accepting them: the median move was **0.0000 dB** but the worst was **2.27 dB**, a 32×
  amplification of a 0.071 dB input. That is real and explainable (DRIVE max × hottest stimulus, at a
  level-sensitive cancellation null — s110 GATE R), but "surprisingly large" always needs looking at
  before it is trusted. (s114)
- ⚠⚠ **A "MOVED +X dB" COST ESTIMATE IS ITSELF A MEMBERSHIP-DEPENDENT AGGREGATE, AND CARRYING IT
  FORWARD ACROSS A BASELINE CHANGE IS THE SAME TRAP ONE LEVEL UP.** Session 106 measured the cost of
  retiring the `gain-n12` exclusion as "+0.020 dB, n 320 → 336" on the s109 report. Session 110 added
  a re-captured twin of the worst file in that group before the exclusion was actually retired, so by
  the time session 111 retired it the group was 20 rows, not 16 — and the real cost was **+0.062 dB,
  three times the recorded figure.** The recorded number was correct when written; it went stale the
  moment an unrelated session changed what it was counting, and nobody re-measured it before quoting
  it as "the cost". ⭐ GENERAL: a decision that has been sitting open across baseline changes carries
  its own membership dependency — re-measure the cost against the CURRENT baseline at the moment the
  decision is finally taken, don't carry forward a number computed on an older one. Same root cause
  as `aggregate-moved-check-membership-first`, but the aggregate here is a *delta between two
  aggregates*, which makes it doubly easy to forget it has a membership at all.
- ⭐⭐ **RETIRING AN EXCLUSION CAN TURN A GATED STATISTIC INTO A MIXTURE OF OPPOSITE-SIGNED
  POPULATIONS, AND AN UNSIGNED STATISTIC CANNOT SHOW YOU THAT — PRINT THE SPLIT EVERY TIME.**
  Retiring the `gain-n12` exclusion moved the THD gate's unsigned `level` term from 3.065 (over its
  3.0 bar) to 2.986 (SHIP) — a movement that reads as the model improving. It is not: the 20
  retired rows have a SIGNED mean of −0.772 dB (the model under-distorts there, recorded 12.071 dB
  further down the compression curve) against the pre-existing +1.414 dB (the model over-distorts
  everywhere else). An rms over the union of two opposite-signed populations is smaller than either
  population's own error by construction, so the row met its bar for a membership reason, not a
  physics one. ⭐ GENERAL: whenever a membership change moves an unsigned/magnitude statistic in the
  flattering direction, check the signed sub-populations before believing it — the two entries this
  pairs with are `unsigned-aggregates-have-no-sign` (s109, the same row) and this file's
  `aggregate-moved-check-membership-first`; this is what happens when both fire on the same number
  at once. ⭐⭐ And the retired rows turned out to be the more valuable half: because they are the
  only captures in the matrix at a SECOND interface-send level, they are the only rows that can see
  the *slope* of the distortion-vs-input law rather than one point on it — paired against their own
  full-send twins (same settings, 12.071 dB apart, so every nuisance cancels), the model's THD level
  term moves −1.106 dB mean / −1.039 median, 11 of 14 pairs same-signed. A population that looked
  like noise to exclude was actually the only free second operating point in the whole capture set.
- ⚠⚠ **`aggregate-moved-check-membership-first` — TEN occurrences, and this list itself had gone
  stale (it read "SEVEN" while CLAUDE.md had already logged nine — the counter is a claim with a
  date on it, same as any other).** An aggregate that fails to reproduce has usually gained or lost
  rows, not changed value. Every shared row was bit-identical each time. **Never quote a matrix
  total without its capture count.**
  - ⭐ **Tenth, and the sharpest version yet: valid, correctly-captured data moved a gate row ACROSS
    its own bar with zero model change, in the very session that had just named this trap.** Session
    113's requested capture plus 8 unrelated hedge captures (added independently by the user for a
    different, unopened purpose) together moved the THD level term from 3.064 (over) to 2.975
    (SHIP). Isolating the 8 hedge captures showed why: their own 32 OD rows read band-RMS mean 1.778
    against the existing population's 2.243 — they are quieter-than-average rows (mild EQ
    perturbations, not the extreme settings the matrix is built from), so their addition dilutes the
    pool exactly as session 112's 12 intermediate-BLEND captures did. ⭐ GENERAL: knowing the trap
    exists does not immunise a session against it **within days** — the check (restrict to the
    shared-membership subset, confirm byte-identity, then decompose the new rows' own contribution)
    has to be run every time captures change, not recalled from memory as "already learned". (s113)
- ⭐⭐ **A CONTAMINATED MEMBERSHIP CAN LEAVE THE AGGREGATE EXACTLY RIGHT AND ONLY SHOW UP ONE LEVEL
  DOWN — SO "the headline still reproduces" IS NOT A MEMBERSHIP CHECK.** Building the LEVEL ladder
  by hand with a 4-key settings match (instead of GATE K's 13-key `find_level_groups`) pulled in
  the `gain-n12` rows — the session-48 capture defect the project has a standing rule against
  fitting to — *and* duplicate detents that a dict build silently overwrote. The band-MEAN law
  computed off that set still reproduced K3's printed table **to the digit at every detent**, so
  the usual check passed. The damage appeared only per band, as a **7.5 dB** residual where the
  correct membership gives **0.000**, and it was briefly mistaken for a failure of the physics.
  ⭐ The rule that would have caught it costs nothing: **assert the membership** (exact counts,
  named exclusions, one capture per detent) rather than inferring it from a statistic that
  survived. ⚠ Note the direction of the trap — this is the mirror of
  `aggregate-moved-check-membership-first`: there the aggregate moved and membership was the
  cause; here the aggregate did **not** move and membership was *still* the cause. (s104, GATE L2)
- **An aggregate's RANGE can be the problem, not its membership.** A tool's self-validation was
  quoted over 40–1700 Hz and omitted the three bands where it failed — which were the bands the
  claim rested on. (s52)
- ⭐ **A range boundary justified only by a COMMENT is an untested exclusion, and the excluded band is
  as likely to be the worst as the quietest.** `GRADE_HI = 12901.6` carried "the 16 kHz band sits in
  the sweep/cab noise floor" — there is no cab in this pedal (leftover template text) and it had
  never been measured. Measured, 16255 Hz is perfectly readable (CLEAN median 0.62 dB) and is now
  **the single worst band in the matrix**: 11 of the 12 worst OD band values, p90 16.6 dB. Widening
  the range was expected to shrink a failing row and it doubled it. **Measure the band before you
  exclude it, and expect widening to cost.** (s90)
- ⭐⭐ **RE-AIMING A CONSTANT AT A NEW REFERENCE NEEDS `target − MODEL`, NOT the published
  `target − old_reference`.** The published delta assumes the model sits ON the old reference; it
  usually does not, because other constants have already moved it partway. §2 asks for −1.10 dB at
  20 Hz and −0.75 at 30 Hz (HW − ND); fitting that raw gave `c21R` = **121 k**. But the model was
  already 0.40 / 0.16 dB below ND at those bands — a third of the move was done — and fitting the
  REMAINDER gave **133 k** (E24 130 k), which the render confirmed to 0.17 dB. The raw-delta answer
  would have overshot the target it was aimed at. Print three columns — published target, measured
  `model − old_ref`, and the remainder — all referenced to a band where the published comparison
  reads zero. ⚠ The handover's flagged range happened to bracket the right answer while being
  derived the wrong way, so **agreeing with a recorded range is not evidence the derivation was
  sound**. (s91)
- ⭐ **EXCLUDING A REGION FROM AN AGGREGATE CAN MAKE IT WORSE — CHECK BEFORE ASSUMING IT'S A
  CONCESSION.** Carving the hardware-governed 25–100 Hz bands out of the CLEAN gate pool was
  proposed (and approved) as relieving a failing row. Measured, it makes the row **harder**: those
  bands carried SMALLER errors than the midband and were diluting the pooled p90 downward, so the
  p90 goes 0.77 → 0.802 on the BASELINE and the baseline retroactively fails too. The bar had been
  passing on dilution. **Compute the post-exclusion figure on the baseline as well as the candidate
  before describing an exclusion as a loosening or a tightening.** (s91, and see §2's
  `aggregate-moved-check-membership-first`)
- ⭐⭐ **A GATE THAT FAILS THE BASELINE IT EXISTS TO PROTECT IS A FALSE ALARM, NOT A REGRESSION
  DETECTOR — AND A POOLED BAR CANNOT SAY WHICH HALF FAILED.** The CLEAN row read p90 **0.808** against
  ≤0.80 and had done since before the change it appeared to indict: the two shipped constants moved it
  **0.006 dB**, and the s90 baseline read **0.802**, i.e. over as well. The number was an average of a
  19-band midband at **0.719** and a 4-band tail at **1.308**, and *neither is recoverable from
  0.808*. Splitting the row made both verdicts honest — and the originally agreed bars **passed
  unchanged** on the midband, which is the tell that a split is a correction rather than a concession:
  **if the old threshold survives on the sub-pool it was written for, the pool was the defect, not the
  threshold.** ⚠ The discipline that makes this safe is refusing the easy move — session 91 declined
  to retune the bar to make its own just-shipped change pass, and the split was put to the user before
  it was executed. **Check a failing gate against the BASELINE before treating it as a regression, and
  split a pooled row before loosening it.** (s95/s96, `docs/clean-gate-split-handover.md`; the sharper
  form of the entry above)
- **Split the aggregate and check reachability BEFORE fitting.** One band was 82 % of a metric and
  the parameter about to be fitted provably could not move it. Use a member-matched control, not a
  whole-band one. (s40)
- **`defective-rows-must-not-vote`.** A constant fitted over rows containing a known unfixed defect
  lands on a compensating error. `clipC15` was selected at 1.5 nF by 28 GRUNT flat/boost rows
  carrying an unrelated gap; the correct value was ~5.2 nF. (s36/s37)
- **A robustness subset must be defined by the REFERENCE SET's own agreement, not by prose about
  which targets look unreliable.** My "robust" subset dropped exactly the two statistics a second
  reference corroborated — and exactly where the candidate paid its cost. It inverted the verdict.
  (s77)
- **`self-selecting-scores`.** A scan that scores candidates on "the points that fit" lets the worst
  one win by shrinking its own scoring set. Freeze the band/row set at the shipped baseline. (s33)
- **Check `n` before reading a trend.** A smooth, physical-looking V-shaped curve turned out to rest
  on ONE band value. Bin labels report only one order's count. **A suggestive shape is not support,
  and that is exactly when the wrong conclusion is most attractive.** (s82)
- **`difference-statistics-hide-common-mode`.** H2−H3 read "94 % of target" while every order was
  ~10 dB low. Print absolutes beside every difference statistic. (s74/s75)
- **A mean can hide the finding.** "Mean shortfall ≈ 0" concealed +80°/−50° per band. (s33)
- ⭐⭐ **A MARGINAL OVER ONE KNOB IS CONFOUNDED BY EVERY OTHER KNOB UNTIL YOU CONDITION ON THE
  DOMINANT ONE — AND IN THIS MATRIX THE DOMINANT ONE IS `blend`.** Raw marginals over the 320 OD
  rows made GRUNT look 2.3× worse off-flat, ATTACK 1.6× worse at idx 0, and LEVEL 3.8× worse at
  max. But `blend` alone spans band-RMS **0.200 → 3.120** (pure clean → pure OD, monotone over five
  values), the other axes are not balanced across it, and any axis whose rows happen to carry more
  blend-max lands looking bad for that reason alone. Conditioned on bleed-free (`blend = 1.0`),
  ATTACK collapses to a 1.23× spread — i.e. **most of the apparent ATTACK effect was the mix, not
  the ladder** — while LEVEL (2.08×) and GRUNT (1.85×) survive. ⭐ And surviving conditioning is
  still not enough: cross-tab the two survivors, because the level-varying captures include grunt
  variants. Here both held **within every cell of the other** (LEVEL 2.07/2.09/1.88× at grunt
  0/1/2; GRUNT 1.66× and 1.52× at each level), and the grunt composition of the two level buckets
  was proportionally identical — which is what makes them two real main effects rather than one
  effect seen twice. **Report the conditional read, not the marginal.** (s102, GATE J9/J11)
- ⭐⭐ **A MEAN OF SQUARE ROOTS DOES NOT DECOMPOSE INTO SHARES — DECOMPOSE THE MEAN SQUARE AND SAY SO.**
  The gated headline `band-RMS` is the mean over ROWS of sqrt(mean over BANDS of d²), so there is no
  honest "band X is N % of 2.409". The pooled MEAN SQUARE does decompose exactly, and its per-band
  shares sum to 100 %. The two are not interchangeable and are not even close here — pooled RMS is
  **3.673 dB** against the headline's **2.409**, and HF is **48.1 %** of the pooled mean square while
  removing it moves the headline only 2.409 → 2.005. Quote the statistic the share was computed on,
  print both side by side, and check the decomposition recombines (with a dropped-band mutation, or
  the check passes for anything that happens to total correctly). (s102, GATE J1/J2)
- ⭐⭐⭐ **A PER-ROW GAIN MATCH MAKES EVERY CONTROL-LAW ERROR INVISIBLE — SO THE GRADING HARNESS
  CANNOT BE THE ARBITER OF A POT TAPER, AN END-STOP, OR A PATH-TO-PATH BALANCE.** This is not a
  subtlety, it is a 9.3 dB blind spot that survived 102 sessions. `comprehensive_report` fits a
  broadband null gain per row and ADDS it to `plugin_db` before anything is differenced, so
  band-RMS, every gated median/p90 and the THD terms all sit downstream of it. Measured on the
  9-point LEVEL ladder, the model is **9.3 dB quiet at LEVEL 0.125** and the fitted gain at that row
  is **+9.03 dB** — it removes the defect exactly, by construction. ⭐ The instrument that CAN see it
  costs nothing extra: undo the stored gain (`plugin_db − gain_db_applied`) and compare captures
  that differ in ONLY the control under test, so there is no anchor to choose and no anchor-dependent
  contamination to argue about. ⚠ The corollary is a rule about what to quote: when a question is
  about a control's LAW, saying "the matrix does not show it" is not evidence — the matrix
  structurally cannot. Same family as `a-cost-can-live-entirely-outside-the-matrix` (s91/s92), but
  where that was about a quantity the matrix never measures, this is about one it actively removes.
  (s103, GATE K)
- ⭐⭐⭐ **A CONCLUSION *ABOUT FREQUENCY* CANNOT BE DRAWN FROM A STATISTIC THAT AVERAGES OVER
  FREQUENCY — AND WHEN IT IS, IT WRITES THE NEXT SESSION'S WORKPLAN.** GATE K7 measures the A3
  clean/OD balance at the mixing network's two exact-zero endpoints, which is an excellent
  construction — no fit, no gain match, no model form. It then reports ONE number per stimulus
  level: the mean over 25 bands. From that single number the handover recorded *"K7 says the defect
  is a LEVEL one. Do not re-run those [frequency-shaping] searches"*, retiring the search space
  three earlier sessions had worked in. Measured per band, the curve under that mean **spans 9–14 dB**
  and its shape/offset ratio is **0.47–0.90 on every band selection**, against the 0.25 bar the
  project's own GATE K5 used to justify exactly that phrase elsewhere. ⭐ The decomposition is
  also the finding, not just the correction: the residual splits into a **stimulus-independent**
  term (100–400 Hz, spread 0.47 dB — genuinely a level error, and the one the external reference
  records) and a **stimulus-dependent** term (508–1016 Hz, swinging 5.4 dB, peak migrating
  254 → 640 Hz), so the pooled mean's rise with stimulus was the *mixture moving*, not the defect
  growing. ⚠ Two guards make it quotable rather than suggestive: a **leave-one-out correlation**
  across the contributing pairs (+0.64…+0.89, so the shape is coherent structure and not noise in a
  4-row mean) and a **band-edge robustness column** (0.2–0.4 dB). **Before quoting a pooled residual
  as evidence about WHERE a defect lives, plot it.** Same family as
  `difference-statistics-hide-common-mode` and `median-over-linear-bins`, but sharper: those were
  statistics that could not see a region; this one cannot see the axis the conclusion was about.
  (s105, GATE M)
- ⭐⭐ **`defective-rows-must-not-vote` APPLIES TO THE INSTRUMENT YOU TRUST MOST, AND A NAME FILTER IS
  NOT A SETTINGS FILTER.** GATE K7 selects its captures by `blend`/`level`/`is_od` — all correct,
  all structural — and thereby pulled in `level-1700_gain-n12`, the session-48 capture defect, as
  **1 of its 5 pairs**: 20 % of the headline the whole A3 case is quoted from. ⭐ Excluding it moved
  A3 **up** 0.20–0.27 dB at every stimulus level, so the conclusion survived — but that is luck, not
  method, and the direction is only knowable by measuring it. **A defective capture is excluded by
  NAME; no combination of setting predicates will do it**, because what is wrong with it is not in
  its settings. And assert the exclusion **found** something (s105's M2 exits if the token matches
  nothing) — a substring filter that silently matches nothing is `empty-gate-must-fail` in a costume.
  (s105, M2/M3)
- ⭐ **AN IMPLAUSIBLE COINCIDENCE IS A BUG REPORT.** A band-edge robustness column selected with
  `f > 25`; the lowest band is **25.2 Hz**, so it dropped nothing and printed a figure **identical**
  to the unrestricted row — which reads as a reassuring "the headline is robust". It is arithmetically
  impossible: removing a 10.25 dB band from a 25-band mean of 3.36 must move it. ⭐ The repair is to
  **assert the size of every selection** rather than trust the predicate; the general habit is to
  treat "two independent computations agreed exactly" as something to explain, not to enjoy. ⚠ Note
  the direction again — the broken check was the flattering one, so nothing else would have prompted
  a second look. (s105, M4)
- ⭐⭐ **CONDITION ON THE PHYSICAL QUANTITY, NOT ON THE KNOB THAT USUALLY SETS IT.** Session 102
  correctly found `blend` dominates the OD residual, conditioned on `blend = 1.0`, and called that
  set "bleed-free" on the topology argument that the clean tap is then out of circuit. Evaluating
  the shipped stage instead of quoting its header: the BLEND pot's body bridges the LEVEL wiper to
  the clean source at EVERY blend position, so bleed vanishes only where the wiper's source
  impedance is zero — at LEVEL max and LEVEL min. Inside the supposedly bleed-free set the clean
  signal runs from **−0.08 dB re the OD** (LEVEL 0.125, i.e. half the output) to −inf (LEVEL max),
  **ordered by LEVEL**, giving r(LEVEL, clean fraction) = **−0.961**. ⇒ the conditioning did not
  remove the confound, it *reparameterised* it onto the next axis, and the cross-tab built on top
  could never have separated the two. ⭐ GENERAL: a second knob that moves the same physical
  quantity is not conditioned away by fixing the first. Compute the quantity from the stage and bin
  on THAT; if the data cannot break the collinearity, say so and refuse the verdict rather than
  reporting the confounded number. (s103, GATE K2/K6, and the sharper form of the
  conditional-vs-marginal entry below)
- ⭐ **A RATIO CAN MOVE BECAUSE ITS DENOMINATOR MOVED.** GATE J10's LEVEL-max penalty ratio grows
  1.49 → 1.66 → 2.65 → 3.26 across rising stimulus level, which reads exactly like a nonlinearity
  engaging. It is not: the LEVEL-max column is **flat at 4.5–5.5 dB** and the growth is the
  LEVEL-noon column *improving* 3.03 → 1.51. The correct conclusion — a stimulus-INDEPENDENT defect
  at LEVEL max — is the opposite of the one the ratio suggests. **Print both columns beside every
  ratio, and read which one moved.** (s102, and the mirror of
  `ratio-statistics-need-a-denominator-guard`, which is about the denominator being at a floor
  rather than merely moving)
- ⭐⭐⭐ **A POOLED MEAN OVER N OPERATING POINTS HIDES THE SPREAD *ACROSS* THEM, AND THAT SPREAD IS
  THE UNCERTAINTY OF ANY CONSTANT YOU FIT TO IT.** GATE M/K7's A3 headline is a mean over 4 capture
  pairs, and it is quoted to two decimals (5.54 / 5.38 / 5.07 / 5.14 dB) with a 0.47 dB
  stimulus-level spread — which reads as a tightly-determined number. But those 4 pairs also differ
  in the pedal's **own DRIVE and ATTACK controls**, and the gate pools over that axis while
  reporting the other one. Printed per pair, the same headline spans **4.48 to 6.68 dB — 2.21 dB,
  i.e. ±1.10 about the pooled 5.34** — so the target a static correction was about to be fitted to
  carries five times the uncertainty its published spread implies. ⭐ GENERAL: when a summary
  averages over conditions the *device itself* controls, print the per-condition column before
  fitting any constant to the average; the pooled spread bounds only the axis that was varied on
  purpose. ⚠ And do not then attribute the spread to one knob without a control: here DRIVE beats
  the ATTACK control 4.6× at the clean stimulus (1.80 vs 0.39 dB) and **loses to it at drv_−6**
  (1.04 vs 2.12), so "operating-point dependent" is supported and "drive-dependent" is not.
  (s108, GATE P4; same family as `aggregate-moved-check-membership-first`, one level up — there the
  membership changed, here it never varied and was never reported)
- ⭐⭐ **"QUIET" AND "REPRODUCIBLE" ARE DIFFERENT CRITERIA, AND THEY CAN BE DISJOINT — CHECK THE
  INTERSECTION IS NON-EMPTY BEFORE CLAIMING A PEDESTAL.** Separating a level pedestal from a peak
  needs a band that is both *clear of the feature* and *agreed on by the replicates*. In A3's excess
  those two sets do not overlap: the quiet bands (40–101, 2560–3225 Hz) are precisely the ones the
  four pairs disagree on (across-pair sd 1.6–4.3 dB), and the bands they agree on (127–508 Hz, sd
  ≤1.25) all sit on the feature. **13 of 20 threshold combinations give an empty intersection.**
  ⇒ the pedestal is not small, it is **unmeasured**, and no amount of re-averaging fixes that.
  ⭐ GENERAL: state both criteria explicitly, take the intersection, and if it is empty say the
  quantity cannot be measured with this data rather than reporting whichever window was
  convenient. (s108, GATE P5/P6)
- ⭐ **SELECT BANDS ON PRECISION, NEVER ON VALUE — AND SWEEP THE PRECISION BAR.** Choosing an
  analysis window by across-replicate spread is legitimate where choosing it by the answer is not:
  precision is independent of the quantity being estimated. It still needs the bar swept and the
  selection size asserted to change, or it is `self-selecting-scores` wearing a lab coat. (s108, P3/P6)
- ⭐⭐ **A "SHARE" ABOVE 100 % IS A BUG REPORT.** GATE P5's first draft measured the pedestal from
  "the reproducible bands OUTSIDE the (A) window" and reported it as **146 % of the window mean** —
  read past quickly, that is just a strong result meaning "it is all pedestal". It is arithmetically
  impossible for a component of a mean, and the cause was that the only reproducible bands outside
  the window (403, 508 Hz) sit on the feature's *upper flank*, not clear of it. **"Outside the
  window" is not "outside the feature"** when the feature is wider than the window. ⚠ Note the
  direction once more: the broken construction returned the flattering answer — it *confirmed* the
  head item — and only the impossible share gave it away. (s108; the third occurrence of
  `an implausible coincidence is a bug report`)

## 3. Gates, controls and verdicts

- ⭐⭐ **HARD-EXIT ON THE GATE'S OWN VALIDITY, NOT ON HOW THE PHYSICS COMES OUT — OR A FINDING
  SILENTLY SUPPRESSES EVERY MEASUREMENT BELOW IT.** GATE P's first P5 `sys.exit`ed on "the per-pair
  pedestal spreads 3.38 dB, so the mean is not describing a shared quantity". That is *the result*,
  not a malfunction — and because it exited, P6's threshold sweep never ran and the finding was
  reported as a crash. The tempting repair is equally wrong: raising the bar to keep the gate green
  would have deleted the finding outright. ⭐ The rule that resolves it: **exit only on things that
  make the numbers below meaningless** (a floor breach, a membership error, a failed known answer, a
  vacuous mutation control); anything that is an outcome of the measurement gets a **computed
  verdict** and execution continues. Ask of every `sys.exit`: "if this fires, have I learned
  something about my instrument, or about the device?" Only the first belongs there. (s108)

- ⭐⭐⭐ **"THERE IS NO FLOOR HERE" IS A LEGITIMATE ANSWER, AND TWO SUCCESSIVE FLOOR GUARDS THAT
  INVENTED ONE BOTH FAILED IN THE FLATTERING-THEN-DESTRUCTIVE DIRECTION.** GATE R needed to know
  whether a cancellation null's bottom was a measurement or an artefact. Guard v1 took the 5th
  percentile of the H1 curve over the analysis band — **self-referential**, because the null *is*
  that curve's bottom — and duly reported 101 of 120 cells "at the floor" with margins to −17 dB.
  Guard v2 used the deconvolution residue below the sweep's own 20 Hz start, which is at least
  somewhere the signal is not; measured, it **tracks the stimulus almost 1:1** (−35.4 → −15.1 dB re
  the in-band level across a 24 dB ladder), so it is signal-proportional regularisation residue and
  not a floor either — and using it as one **deleted exactly the cells carrying the session's
  finding**. ⭐ The resolution is to notice what the system actually is: **both sides are
  deterministic renders** (ours, and ND's — five ND renders agree to −147…−164 dBFS), so there is
  no noise floor to find, and a guard that insists on one is guarding a fiction. ⭐⭐ What replaced
  it is the generalisable move: **stop depending on the fragile quantity.** The scored statistic
  became a 1/6-octave POWER-INTEGRATED deficit — set by the notch's *area*, not by the exact depth
  of its bottom — with the point sample kept as a control. The qualitative conclusion survived the
  swap while the magnitudes changed by up to 15 dB, and reporting both is what makes that
  legible. **Before writing a floor guard, ask what the noise actually is; if the answer is "there
  isn't any", re-engineer the statistic instead of inventing a threshold.** (s110, GATE R4)
- ⭐⭐ **A MUTATION TEST HAS TWO PLACES TO GO WRONG AND THE CONTROL ONLY CATCHES ONE OF THEM.**
  s107 recorded that patched copies must run where the tool runs, or every "failure" is a
  `ModuleNotFoundError`. GATE R's first mutation run obeyed that — patched copy in `analysis/`,
  `cwd=analysis/` — and returned **7 of 7 "PASS", every one a `FileNotFoundError`**, because the
  tool's data paths are repo-relative. The copy must **LIVE** in the module's directory (so sibling
  imports resolve) and **RUN** from the repo root (so data paths resolve); those are two different
  requirements and satisfying one is the natural way to break the other. ⭐ The unmutated CONTROL
  caught it instantly and is the only thing that did. ⚠ **Second failure mode, which the control
  CANNOT catch: a vacuous mutation.** One mutation patched a module constant inside `main()`, but
  the surface it affects is computed in a `ProcessPoolExecutor` whose children **re-import the
  module fresh** and never see a runtime-mutated global — so the mutation was a silent no-op and
  read as a broken guard when the guard was fine. **Patch module-level constants at module level,
  and treat "this guard didn't fire" as a hypothesis about the mutation before it is one about the
  guard.** (s110)
- **`computed-verdicts-not-narrated` — FOUR occurrences.** A conclusion hard-coded into a tool's
  output outlives the condition it described and prints above a table contradicting it. Derive every
  verdict line from the data, and make it state the opposite when the data says so. (s34, s61, s68)
- ⭐⭐ **A MUTATION TEST MUST RUN WHERE THE TOOL RUNS, AND IT NEEDS AN UNMUTATED CONTROL — OR EVERY
  MUTATION "PASSES" FOR A REASON THAT HAS NOTHING TO DO WITH THE GUARDS.** Mutation-testing GATE O's
  five guards by writing patched copies to `/tmp` returned a clean **5 of 5 PASS**. All five were
  `ModuleNotFoundError` — the copy sits in `/tmp`, and the tool puts *its own directory* on
  `sys.path`, so it never reached a single guard. A mutation test scores "did it exit non-zero?", and
  a crash exits non-zero. ⭐ Two fixes, both one line: write the patched copy **into the tool's own
  directory**, and run the **unmutated** copy from the same place first — if the control does not
  PASS, no failure below is attributable to the mutation. Re-run properly, all five guards fired with
  their own messages. ⚠ Note the direction yet again: the broken version was the flattering one, and
  it was caught only because the last line of each run was printed rather than just the exit code.
  `empty-gate-must-fail`, committed inside the mutation test written to enforce it. (s107)
- ⭐⭐ **A GATE THAT PRODUCES NO DATA MUST FAIL, NOT FALL THROUGH TO ITS ELSE-BRANCH.** An empty
  central difference passed three checks silently, narrated "ALL THREE BANDS WANT β HIGHER" over zero
  rows, and printed its own ±99 initialiser as a value. (s87, s40)
- **A sentinel is not a measurement.** `need = +24.00` was the unreachable flag; `√1e9 = 31622.777`
  printed as a residual. Check the span before quoting. (s40, s85)
- **Gate the property the CONCLUSION rests on, not an absolute accuracy the statistic does not
  have.** "Boost roughly doubles the depth" needs monotonicity and scale, not calibrated dB;
  asserting the latter hid a real definitional bias behind a passing test. (s61)
- **A flat threshold on an interval-identified quantity is the wrong gate.** A red self-test meant
  the data was flat, not the solver wrong. Gate on residual + interval membership. (s47)
- **`gate-domain-must-cover-candidate-reach`.** A score computed over bands ≤806 Hz preferred a
  candidate whose cost landed at 3–13 kHz — it measured the benefit and was blind to the cost *by
  construction*. (s49)
- **`ratio-statistics-need-a-denominator-guard`.** Searches kill the denominator; gates manufacture
  failures by differencing floor-level numerators. A dB number computed from something at the
  numerical floor is not a measurement. (s40, s54, s72)
- **A measurement CONDITION needs its own gate.** A headline finding was a missing `--grunt` flag.
  "Present in all three throws" and "level-independent" are satisfied just as well by a shared
  *render-condition* error as by a shared *circuit* error. Derive render args from
  `captures.render_args`, never type them. (s65)
- **Anchored quantities cannot register a cost.** Check what an instrument normalises on; a "free"
  verdict on a difference statistic must be re-scored per component. (s84)
- ⭐⭐ **IF EVERY TERM OF AN OBJECTIVE IS RELATIVE, NOTHING IN IT SEES ABSOLUTE LEVEL — AND A FIT
  WILL SPEND THAT BLINDNESS TO THE LAST dB.** `attack_shape_screen`'s objective is (a) the notch
  triple, each referred to its OWN 200–270 Hz shoulder, and (b) `h`, a throw-to-throw RATIO. Both
  are relative, so a change shared by all three throws is invisible to the WHOLE objective, not
  just to one term. Session 94's fit met the corrected ATTACK requirement on the real render to
  0.72 Hz of f0 and 0.24 dB of depth — and the 129-capture matrix read **OD band-RMS 2.664 →
  6.174 dB, THD level 4.279 → 18.685, worst row +27.04 dB**, because it had quietly re-scaled the
  shared treble ladder (R7 ×5.16, C6 ×9.92, C7 ×0.1, C5 ×0.33, C9 ×0.25) and put the OD path
  **40–47 dB down below 400 Hz**. ⭐ The tell was already in the tool's own docstring — `--tilt`
  says in as many words that `h` is a ratio "which is exactly why every ATTACK instrument since
  session 57 has been blind to a shared error" — and it was written about a DIAGNOSTIC gap, not
  read as a constraint the OPTIMISER would exploit. ⚠ And the localisation is only half the
  obvious story: pinning C7 back alone recovers **28.87 → 15.18 dB** on the worst row, so C7 is
  the largest single contributor and roughly half of it is the rest of the ladder. **Before
  optimising, list what the objective CANNOT see and check the search cannot reach it; a
  documented blind spot in a diagnostic becomes a degeneracy the moment a search is pointed at
  it.** (s94, and the sharper form of `difference-statistics-hide-common-mode` and
  `gate-domain-must-cover-candidate-reach`)
- ⭐⭐ **A MEDIAN OVER LINEARLY-SPACED BINS IS A HIGH-FREQUENCY STATISTIC, WHATEVER ITS BAND IS
  CALLED — AND "the pathology is still visible in these bins" IS A CLAIM ABOUT THE BINS, NOT ABOUT
  THE STATISTIC COMPUTED OVER THEM.** Session 95's absolute-level term is
  `median(gabs[G_BAND])` over 100 linearly-spaced bins from 87.9 to 1599.6 Hz. **8** of them lie
  below 200 Hz and **69** above 800, so the median bin sits at **1019.5 Hz**: the term is a ~1 kHz
  reading wearing a broadband name. Measured on the fitted candidate, it reported the render
  **satisfied to 1.06 dB** while the same render was **21–23 dB short over 88–200 Hz**, and the
  129-capture matrix duly read OD 25–100 Hz p90 **6.065 → 20.958**. ⚠ The code comment beside the
  band asserts the opposite in as many words — *"a 40 dB collapse below 400 Hz is still fully
  visible in the 88-175 Hz bins"* — which is true of the bins and false of the median: 8 in 100
  cannot move it. ⭐ Decompose any pooled summary into sub-bands **before** trusting it as an
  acceptance criterion, and prefer a per-sub-band residual to one pooled number whenever the
  quantity can fail in one region and pass in another. Same family as the CLEAN pooled-p90 split
  (s95/s96) — and note it is the THIRD time this project has shipped a blind objective, each one
  found only when the matrix rejected the fit it produced. (s98, `attack_d_extrapolation_gate.py`
  GATE H4)
  - ⭐⭐ **AND WHEN YOU REPAIR IT, THE *TARGET* HAS TO BE DECOMPOSED TOO, NOT JUST THE RESIDUAL.**
    Session 99 split `g` into four sub-bands; the obvious half-fix is to score four sub-band
    residuals against the one pooled target already on record. Measured, that target runs
    **+8.3 … +12.4 dB** across the same four bands — a 4.1 dB spread against the term's own 1.0 dB
    floor — so re-using the pooled figure would have injected up to **3.7 dB** of systematic error
    into exactly the LF band the repair exists to expose. **A pooled statistic on either side of a
    residual is a pooled statistic.**
  - ⭐ **A SUB-BAND WITH FEW BINS IS NOT THEREBY UNRELIABLE — CHECK, DON'T ASSUME.** The LF band
    carries 8 bins of 100 and is weighted equally with bands of 23/28/41, which looks reckless and
    is not: measured at two stimulus levels it is the **most** stable of the four (0.007 dB, against
    0.383 dB at 1130–1600). Bin count bounds *sampling noise*, and against a deterministic renderer
    there is none. `check-n-before-reading-a-trend` is about support for a *shape*; it does not
    license discounting a band that a control shows is repeatable. (s99)
  - ⭐⭐ **REPAIRING A BLIND OBJECTIVE INVERTS WHICH READING IS THE HEADLINE AND WHICH IS THE
    CONTROL — MOVE THEM, DON'T LEAVE THE GATE TESTING THE RETIRED STATISTIC.** GATE H's H3 asked
    the sufficiency question against the pooled median because that was what shipped, and H4
    decomposed it and found the pooled median *was* the defect. Once the shipped term became
    per-sub-band, H3 had to become the per-sub-band promise and the pooled reading had to become a
    labelled control — otherwise the gate keeps certifying a statistic nothing uses, which is
    `verify-the-BASELINE-not-its-LABEL` pointed the other way. Keep the superseded reading printed
    every run so pre-repair quotes stay reproducible. (s99)
- ⭐⭐ **AN INVARIANCE IS ESTABLISHED ONLY OVER THE REGION IT WAS MEASURED IN, AND A FIT WILL WALK
  OUT OF THAT REGION BECAUSE NOTHING IN THE OBJECTIVE KNOWS WHERE THE REGION ENDS.** GATE F founds
  the absolute term on `D(f) = render − ladder` being ladder-invariant, measured between two C8=0
  ladders that are "very different" from each other yet **both close to the drawn network**
  (worst 0.183 dB). The fitted winner sits at R7 ×7.28 / C7 ×0.244, far outside that region, and
  there the invariance fails by **3.84 dB** — an INTERPOLATION check relied on as an EXTRAPOLATION
  guarantee. ⚠ Re-check the premise **at the candidate**, not only at the reference points that
  justified it. (s98, GATE H2)
  - ⭐ **AND WHERE THE FULL CHECK NEEDS AN ARTEFACT THE GATE CANNOT PRODUCE, MAKE IT MEASURE AND
    PRINT ITS REGION OF VALIDITY INSTEAD OF GOING QUIET.** GATE F cannot test D at the candidate —
    the candidate does not exist when F runs, and testing it needs a render. What F *can* do is
    measure the envelope against the one wild ladder already on disk and state the limit:
    invariance holds to **0.183 dB out to 0.23 decades** and degrades to **3.84 dB at 1.00**. The
    fitted winner then gets its ladder distance printed against that limit **at selection time**,
    so an extrapolation is visible before the matrix discovers it. ⚠ Say plainly that this does
    **not** close the hole — the at-candidate render check stays a required step. An unstated
    assumption turned into a stated, measured limit is the win; pretending the limit is the check
    is how the assumption comes back. (s99, GATE F4)
- ⭐⭐ **A KNOWN ANSWER MUST BE A PROPERTY OF THE MEASUREMENT, NOT OF THE THING BEING MEASURED —
  AND WHEN IT FAILS, SUSPECT THE CHECK FIRST IF THE CHECK IS THE NEW PART.** GATE K3 gated "a pot
  law is monotone, so both columns must be monotone in LEVEL", which is true of a pot and false of
  what was tabulated: the end-to-end **H1 transfer**, which FALLS when a stage downstream of the pot
  saturates, because the fundamental's energy moves into harmonics the Farina read rejects. The
  gate duly failed against entirely correct data. ⭐ The fix is not to loosen the tolerance but to
  scope the check to the region where the property actually holds (here: the reference at all
  stimulus levels, and both sides at/below noon, where nothing is saturating) — and then to REPORT
  the violation above noon as the second finding it is, rather than as a failure or, worse, as a
  tolerance to widen. ⚠ Note the near-miss: the tempting repair is `TOL = 3.5` instead of `0.35`,
  which would have kept the check green and silently deleted a real stimulus-dependent defect.
  Third occurrence of the family — see GATE I's asserted −24 dB/oct and s93's swept-vs-stepped
  instrument, both textbook properties quoted outside their conditions. (s103)
- ⭐⭐ **A NUISANCE PARAMETER FITTED FROM ONE CURVE IS NOT MEASURED, AND A DIRECT READ WILL SAY SO
  BY AN ORDER OF MAGNITUDE.** Fitting (taper exponent, clean/OD ratio) jointly to the 8-point LEVEL
  law gave a good residual (0.335 dB rms) at ratio **0.14**; measuring the same ratio directly —
  pure-clean vs pure-OD captures, both traversing the same downstream chain, no fit at all — gives
  **1.53**. Both "fit well"; only one is the quantity. Two parameters against one smooth curve trade
  off, and the sum being COHERENT was assumed and is false besides (the two paths are not in phase,
  so the law involves |a·H₁ + b·H₂|, between the coherent and incoherent limits). ⭐ Before quoting a
  fitted nuisance parameter as a physical measurement, look for a configuration where it is the ONLY
  thing varying — an exact-zero endpoint of the mixing network is usually available and turns a
  2-parameter fit into a subtraction. ⚠ And when the two disagree, they may be different quantities
  rather than one of them being wrong: say which is which instead of picking. (s103, GATE K7)
- ⭐⭐ **WHEN A FIT WON'T CLOSE, FREE THE NUISANCE PARAMETER AS A CONTROL — IT SEPARATES "MY
  MEASUREMENT OF IT IS WRONG" FROM "THE MODEL IS WRONG", AND THOSE HAVE OPPOSITE NEXT STEPS.**
  GATE L's inverse takes the clean/OD ratio |ρ(f)| as MEASURED from two endpoint captures. When
  the pedal's ladder would not fit below 1.6–2.4 dB, the cheap and tempting conclusion was "the
  endpoint captures are off". Re-running with |ρ| **free per band** — 25 extra parameters, i.e.
  the measurement discarded entirely — moved the residual only 1.63 → 1.50 dB. So the endpoint
  measurement is exonerated and the *topology* is implicated, which is a completely different
  workplan. ⚠ The control needs its own control: freeing ρ must NOT break the known answer, or it
  is too loose to arbitrate anything. Here the model still recovered `x^2.25` exactly with the 25
  extra parameters in play, which is what makes the pedal's non-collapse readable. (s104, GATE L5)
- ⭐⭐ **A RECOVERED QUANTITY THAT MUST BE INVARIANT AND ISN'T IS A REFUTATION OF THE MODEL FORM,
  NOT A MEASUREMENT — AND IT IS OFTEN THE ONLY CLEAN REFUTATION AVAILABLE.** An absolute residual
  is always arguable ("1.6 dB is small", "the devices differ"). An invariance is not: a
  potentiometer's taper cannot depend on the stimulus level driving it. GATE L recovers the
  pedal's apparent taper at four stimulus levels and gets **L(0.625) = 0.503 / 0.631 / 0.377 /
  0.341** — a 0.29 spread — where the same machinery on the model returns the identical value to
  **0.00000** at all four. That single comparison kills the model form outright, with no threshold
  to argue about, and it converts the recovered curve from "the pedal's taper" (quotable, and
  wrong) into "a quantity absorbing something the form omits" (not quotable). ⭐ GENERAL: when
  fitting a physical parameter, find something it is *forbidden* to depend on and recover it
  separately at several values of that thing. The known-answer side supplies the floor. (s104,
  GATE L6)
- ⭐ **A DEFECT THAT IS REAL AND A DEFECT THAT IS SUFFICIENT ARE TWO DIFFERENT CLAIMS.** Having
  found the 3.84 dB invariance failure above, the pressure to report it as *the* explanation for a
  26–47 dB regression was considerable, and it would have been wrong — the medians move only
  0.03–0.52 dB. The gate now carries an explicit sufficiency check (H3: did the render actually
  move by what the term asked for? +8.98/+8.12/+9.09 against +8.66/+9.18/+8.73 — **it did**), which
  is what forced the search onward to the real cause. **When a gate finds a defect while hunting a
  regression, make it measure whether that defect is big enough to BE the regression.** (s98)
- ⭐⭐ **A RATIO-ONLY OBJECTIVE CANNOT CHOOSE WHICH SIDE OF THE RATIO TO MOVE, AND A FIT WILL PICK
  THE WRONG ONE SILENTLY.** This is the sharper, older form of the entry above. Measured bleed-free,
  the pedal wants ATTACK's **boost** throw 10.30 dB hotter while **cut** is already right to 0.47 dB
  — but `h` is a throw-to-throw ratio, so "raise boost 10" and "lower cut and flat 8" score
  identically, and session 62's proposal took the second branch, landing h-correct to 0.45 dB while
  sitting ~8.7 dB below the pedal at **every throw at once**. Nothing in three sessions of ATTACK
  work could see it, because the notch triple is referred to each throw's own shoulder and is
  equally blind. ⭐ The fix is one absolute term, and the fact that makes it legitimate is worth
  checking for generally: the downstream transfer `D = render − ladder` is INVARIANT to the stage
  being fitted (0.183 dB across two very different ladders), so an absolute target for a SUB-STAGE
  can be derived from an absolute measurement of the WHOLE chain. **Before fitting any stage on
  ratios, ask what sets the absolute level, and check whether the objective can see it.** (s95)
- ⭐⭐ **A GATE'S OWN MUTATION CAN BE PATHOLOGICAL, AND SCORING THAT AS "NO MOVEMENT" IS
  `empty-gate-must-fail` COMMITTED INSIDE THE GATE WRITTEN TO ENFORCE IT.** A mutation gate asked
  "must a known ladder change MOVE the new term?" and used `R7 ×10`. R7 ×3 and beyond destroy the
  null outright (width → nan), so the stats function returned None and the term was never measured —
  and the draft scored `dg = 0.0`, i.e. FAIL, for a reason that had nothing to do with the term. The
  gate was right to fail and its message was wrong, which is the dangerous combination: a correct
  red light with a misleading label sends the next session after the wrong defect. **A mutation that
  produces no measurement is a distinct hard failure with its own message, never a zero.** ⚠ And
  pick the mutation for the LEVER, not the nearest constant: the tap divider moves absolute level
  13–15 dB with every width intact to ~1 %, which is what the gate actually needed. (s95)
- ⭐ **A TIE-BREAK ON A PLAUSIBILITY HEURISTIC CAN OUTRANK IDENTIFIABILITY.** `best_point`'s ranking
  key ends in `box`, preferring the smaller search — sensible, and added for a good reason (s66).
  But with the new term in, box 1.0 and box 3.0 tied on every quantised term and box 1.0 won, while
  resting **three of thirteen values on their bounds** where box 3.0 rested none. A parameter on its
  bound is unidentified (`bound-resting-means-unidentified`), which is a stronger objection than
  "the search was wider". **Rank identifiability ahead of any plausibility tie-break.** (s95)
- ⭐⭐ **SCORE THE CANDIDATE YOU WILL ACTUALLY EMIT — A TWO-STAGE FIT WHOSE SECOND STAGE IS *ARGUED*
  HARMLESS MUST PRINT THE HARM.** `best_point` ranked ten candidates on their stage-1 statistics and
  then re-fitted the tap **once**, on the winner, justified in its own docstring by "the tap moves
  width by ≤0.5 Hz and f0 by 0.00 Hz, so it cannot undo stage 1". That is a **census number measured
  at PROP**, and it does not survive at the fitted points: measured, stage 2 moves cut/flat width by
  2.3–2.5 Hz at one candidate and **8.5 Hz — 17× the quoted bound —** at another. ⭐ The damage is not
  that the numbers were stale, it is that the perturbation is **candidate-dependent and therefore
  reorders the field**: one row went width rms 1.19 → **0.41** under stage 2 while another went
  0.40 → **1.19**, so the pre-stage-2 ranking was ranking on numbers the tool does not deliver. Fix:
  run the later stage per candidate, rank on its output, print both columns, and keep the scored
  residuals in ONE function shared by the objective and the ranking. ⚠ Same family as
  `imposed-checks-cannot-corroborate`: a claim that stage B cannot disturb stage A is a
  **measurement**, not a design argument, and it expires exactly where the fit goes. (s97)
- ⭐⭐ **RANK FEASIBILITY FIRST — "PRINTED" IS NOT "SCORED".** The screen had *printed* a realisability
  warning since session 62 ("recorded not hidden") for candidates whose three per-throw C5 values the
  C++ side cannot express (one base plus two trims ⇒ the third throw must be the smallest), and never
  ranked on it. 2 of 10 rows failed it, and the moment an unrelated ranking fix changed the winner,
  it picked one of the two. ⭐ Feasibility does not belong among the quality terms: a candidate that
  cannot be rendered cannot be judged by the render **or** the matrix, so it is not a worse candidate,
  it is not a candidate. ⚠ And note the shape of the failure — **fixing one blind spot moved the
  selection into a second one**, which is the normal case, not bad luck: a ranking key that has been
  wrong is usually wrong in more than one place, and the terms that never bound anything are the ones
  nobody has checked. **When you change a ranking key, re-derive the whole key, not the term you came
  for.** (s97)
- ⭐ **WHEN A SEARCH SETTING IS SWEPT, EVERY MAPPING THAT READS IT MUST READ THE SWEPT VALUE.**
  `build()` normalised the linear C5-trim dimensions by the module-level default `BOX` while the
  search box was a swept argument, so its documented codomain `[0, 0.3·C5]` silently became
  `[−0.3·C5, +0.6·C5]` at box 3.0 — half of it a **negative additive parallel cap**. It survived 31
  sessions because every winner since the sweep was introduced happened to be a box-1.0 row, where
  the swept value and the default are equal and the code is exactly right. **A hardcoded copy of a
  default is invisible until the sweep first wins** — grep for the constant's name after making it a
  parameter, and re-check any mapping whose units are NOT the ones the setting is expressed in (here:
  decades of log-multiplier, applied to a dimension that is linear). (s97, and the corollary to
  `search-settings-are-derived-artefacts`)
- ⭐ **QUANTISE EVERY TERM OF A RANKING KEY, NOT THE ONE THAT WAS EMBARRASSING LAST TIME.** Session
  66 quantised the f0 term of `best_point`'s key and left width at full precision. Session 94's
  first stepped run then picked box 3.0 / w_f0 100 over box 1.0 / w_f0 1 on **width rms 0.33 vs
  0.34** — 0.1 % of a width, against a statistic whose own recovery error is 0.94 % and whose
  transfer to the render is ±5–10 % — and the winner wanted R7 ×28.6, C6 ×200, C7 ×0.023 where the
  loser wanted at most ×10. An unquantised tail term is a lottery with a plausible face. (s94)

## 4. Fits, searches and degeneracy

- **A monotone objective with no interior minimum is a degeneracy, not a fit.** "Make the clipper see
  less" killed the s5/s6 clipper fits, the GAP #3b C13 candidate and the rail-voltage fit. Require
  the objective to push back from BOTH sides. (many)
- **`bound-resting-means-unidentified`.** A parameter on its bound is not a constraint to trade off —
  the outside bound is the missing equation. But: **a folded parameter's endpoint is a SYMMETRY
  point, not a fence** (θ measured at 0.000e+00). Check which you have. (s47, s86)
- ⭐⭐ **AND IT IS A HYPOTHESIS, NOT A MEASUREMENT — PIN THE PARAMETER AND RE-FIT EVERYTHING ELSE
  BEFORE WIDENING ANYTHING.** Session 97 left exactly two of seventeen values on their bounds, both
  at the SMALL end, and concluded "the box is the missing equation"; the pre-registered next step
  was a per-dimension floor sweep. Measured, **neither dimension is box-limited** — outside the box
  no point dominates the reference (`C9` collapses beyond ×0.03: post-tap f0 rms 0.04 → 5.8 → 23.1;
  `Ra` degrades monotonically on the absolute-level term, g 0.19 → 1.70 dB). The optimum simply
  **coincides** with the bound. ⭐ GENERAL: a rail caused by the box shows a LOWER cost outside; a
  coincident optimum shows a HIGHER one — and the two are **indistinguishable from the fitted point
  alone**, which is the whole reason the heuristic exists and the whole reason it must be checked.
  One profile answered in minutes what the proposed sweep would have spent a session on. ⚠ And note
  which way the error ran: the heuristic was about to make the project *discard* a good point.
  (s98, `attack_shape_screen.py --floor-probe`)
- ⭐ **A 1-D SLICE THROUGH A RAILED PARAMETER IS THE LEAST TRUSTWORTHY SLICE THERE IS.** The other
  coordinates were chosen by the optimiser **while** that one was railed, so they have already
  adapted to it, and a genuine joint optimum further out then shows up on the slice as a RISE. Here
  the slice and the re-optimised profile agreed — that is a result, not a licence. Run both, print
  both, and let only the re-optimised column carry a verdict. (s98)
- ⭐⭐⭐ **A DEGENERACY IS A LEVER THE MOMENT YOU LOOK AT THE AXIS IT IS *NOT* DEGENERATE ON — AND
  "cannot be measured here" GETS FILED AS "cannot be used".** `kInputRef` (K) is documented, in the
  source, as **degenerate with the clip ceiling**: scaling K and inversely scaling the ceiling gives
  bit-identical output, and K cancels exactly through the linear path (proven std = 0.000, and
  re-proven here at **1.1e−08** across a 2× change). Three sessions (17, 43, 44) therefore treated K
  as a thing to *pin* — session 43 measured that the harmonic objective does not identify it at all,
  and session 44 fenced it with an arithmetic clean-headroom bound. All correct, and all about how
  to CHOOSE it. What nobody asked is what it *does*: because it cancels in the linear path, K is the
  **only** knob that moves every nonlinear operating point at once — the CD4049 ceiling, the J201
  ceilings, the TL07x rails and the D1/D2 window — while provably changing nothing linear. That
  makes it the exact and unique lever for "the OD path saturates too early", and it beat every
  single-element ceiling in a 13-point screen (GATE Q score 4.663 → 3.973, interior at 0.90 against
  0.80/1.00). ⭐ GENERAL: when a constant is recorded as unidentifiable, write down *which* statistic
  fails to identify it and *what it is invariant on* — that invariance is usually the reason it is
  a clean lever somewhere else. A parameter that cancels in the path you were measuring is a
  parameter with no side effects in that path. (s109)
- ⭐⭐ **A REACHABILITY RESULT OBTAINED WITH A BLIND OBJECTIVE IS NOT A REACHABILITY RESULT — IT IS
  A MEASUREMENT OF WHAT THE OBJECTIVE WAS WILLING TO SPEND.** Session 94 reported the corrected
  ATTACK requirement REACHED — "all nine numbers AT ONCE", width rms 0.34 — and session 97 improved
  on it at 0.41. Both were scored by objectives that could not see the OD path's absolute low-end
  level, and both had quietly paid for the notch shape with it: measured per sub-band, the LF
  residual at those two winners is **−42 dB** and **−22 dB**. Give the objective an LF-visible term
  and the same search reaches LF to **−1.4 dB** and width collapses from 0.41 to **4.25**, in
  **all ten** rows of a sweep spanning 100× in f0 weight and 3× in box — the saturation signature.
  ⇒ the notch shape and the absolute level are in genuine CONFLICT in this topology, and three
  sessions of "reachable" were an artefact of not scoring one axis. ⭐ GENERAL: before quoting a
  fit as evidence that a requirement is reachable, list what the objective could NOT see and ask
  what the optimum spent there — a fit does not decline to pay in a currency it cannot count.
  ⚠ Corollary for the other direction: when a newly-added term makes a previously-"reached"
  requirement unreachable, that is the earlier result being corrected, not the new term being too
  strict. (s99, and the sharper form of `if-every-term-is-relative-nothing-sees-absolute-level`)
- **`search-settings-are-derived-artefacts`.** A search box justified by a measurement expires with
  it. Sweep the setting instead of inheriting the choice — a box "known to be constraining" was
  chosen against a calibration that had since been corrected. (s66)
- **Gate a search before trusting its failure.** A random search "refuted" a topology while
  recovering a *definitionally reachable* target to only 0.73 dB. Synthesise a target you know is
  reachable and require recovery under the noise floor first. (s57)
- **Quantise a ranking key to the resolution of what it ranks.** 0.06 bins beat 0.07 bins and picked
  the worse candidate; 0.01 bins is 0.06 Hz and does not exist in the data. (s66)
- ⭐⭐ **BUT QUANTISE TO COMPARE *CANDIDATES*, NEVER TO COMPARE A MEASUREMENT WITH ITS OWN
  REFERENCE.** The two uses look identical and are not. A ranking key rounds each term into bins so
  a converged field can be ORDERED; re-using that same key to ask "did this change anything?" turns
  a difference far below the term's own floor into a verdict whenever it straddles a bin edge. A
  re-fit that reproduced its reference to **0.06 of width rms — inside the declared 0.10 tie
  scale —** was reported as a KNOWN-ANSWER FAILURE *and* as evidence that "the floor BINDS", purely
  because 0.406 rounds to 0.4 and 0.466 to 0.5. Both conclusions were artefacts of the rounding and
  both were the opposite of the truth. ⭐ Use the raw statistic against an explicit per-term
  tolerance (a `dominates()`, not a `key <`) for any reproduce-or-improve question. **A rounding
  boundary is not a finding.** (s98)
- ⚠ **EXCLUDE A PINNED COORDINATE BY INDEX, NEVER BY SUBTRACTING ONE FROM THE COUNT** — and check a
  reference index against the vector it actually indexes. Two defects in one gate, both silent:
  a profile pinned a dimension in a 1e-9-wide window and did `n_on_bound - 1`, which is right only
  when the polish lands exactly on the window edge (it does sometimes and not others, so the column
  was off by one on *some* rows); and `TAP.index("Ra")` applied to the **stage-1** vector returned
  R7's coordinate, centring the entire Ra profile on the wrong value and producing a plausible,
  monotone, completely irrelevant column. ⭐ The tell for the second was the KNOWN-ANSWER row never
  firing — a gate whose self-check silently never runs is the failure mode `empty-gate-must-fail`
  describes, and it is worth making the "reference row identified" line print explicitly. (s98)
- **Imposed checks cannot corroborate.** Constraining a fit to satisfy its own independent check
  makes "it passes" circular. Free it again from that basin. (s44)
- **A joint-fit shortfall may be ARBITRATION, not reachability.** One requirement missed can be 6
  residuals losing to 216. Separate the fits when the parameter groups do not interact. (s62)
- **Free BOTH magnitude and angle before declaring a two-phasor target unreachable.** Pinning one
  turns "not at this level" into a false impossibility. (s29)
- **A two-phasor magnitude solve is BIMODAL — grid both axes.** A golden-section search silently
  picked the wrong branch and returned 7° of error on data synthesised from the model itself. (s31)
- **`one-knob-two-jobs-is-compensating`.** A constant that trades feature A against B with no value
  good for both is propping up a different unfixed defect. (s46)
- **Don't fit jointly across levels when the element is level-invariant** — it drags the fit toward
  absorbing a defect it cannot fix. Fit at one level, then CHECK at the others. (s35)

## 5. Artefacts, staleness and tooling

- ⭐⭐ **REUSING A SHARED LOADER IS RIGHT; ASSUMING ITS CONTRACT IS NOT. `|delta|` AND SIGNED
  `delta` ARE DIFFERENT QUANTITIES AND ONE OF THEM SILENTLY RUINS AN OFFSET.** GATE J imports
  `release_gate.deltas` so the two tools cannot drift — correct, and it is what makes J1's
  reproduction meaningful. But that function returns **|delta|**, which is right for every
  magnitude statistic and wrong for the level/shape split: `mean(|d|)` is not an offset, it is just
  another magnitude, so the "level term" column came out as plausible, monotone, wrongly-scaled
  numbers that disagreed with an independent hand computation by up to 2.6 dB while looking
  entirely reasonable on their own. ⭐ The tell was **only** that a one-off shell read had been done
  first and the two did not match — so keep the independent read, and when a second loader is
  needed, GATE IT AGAINST THE FIRST (`|signed| == |delta|` elementwise) rather than trusting that
  the new one agrees. Same family as `verify-the-BASELINE-not-its-LABEL`, one level down: the
  label here is the function name. (s102, GATE J12)
- ⭐⭐⭐ **`rebaseline-all-derived-artefacts` RUNS BACKWARDS TOO: THE DERIVED ARTEFACT CAN BE FINE
  AND THE *SOURCE* CAN MOVE UNDER IT — AND NOW THAT CAPTURES ARE CHEAP AND RE-RECORDABLE, THAT IS
  THE LIKELIER DIRECTION.** GATE R takes its membership and its dropout exclusions from a stored
  129-capture report and reads the pedal side straight off the capture wavs. Those are two
  different epochs. Three captures were re-recorded on 2026-08-02 at 09:45–09:50; the baseline was
  written at **09:29**. So the gate was excluding a named (file, sweep) cell that no longer exists
  while reading a file the report had never seen, and one of the re-captured files sat in the group
  carrying the session's headline. ⭐ The guard is three lines — compare each input capture's mtime
  against the report's and refuse — and it is the mirror of the `.args.json` stamp the project
  already puts on every render: **stamp what a derived artefact was made FROM, and check the source
  has not moved since.** ⚠ The corollary that bites hardest: `reference-sources.md` §4's "captures
  are now cheap, stop rationing them" is correct and it makes every stored report a **perishable**
  object. Any tool that mixes a stored report with live capture reads needs an epoch check.
  ⚠ And check what the re-capture actually did before assuming it fixed anything: here the dropout
  did not disappear — it came back at the SAME rung, the NEW capture of the same condition has it
  too, and only the twin recorded 12 dB quieter is clean. That turns "one bad cell, exclude it" into
  "this CONDITION reproducibly misbehaves at level", a different finding with a different remedy.
  ⛔ **And an intermediate claim in that session — that the defect had MOVED rung — was WRONG, from
  `median-over-linear-bins` (below) committed a second time.** The scratch check took a median of
  the full-resolution Farina curve over a LINEARLY-spaced rfft grid, which is an HF statistic
  wearing a broadband name; it put the dropout at `drv_-18` where the project's own 29-band read
  puts it at `drv_-12` (3.34 dB against 13.4/13.7/14.4 either side). ⭐ The lesson that survives is
  the design one, and it is unchanged: **detect the defect, never name it** — here that paid off not
  because the cell moved but because a NEW capture with the same defect appeared, which a hardcoded
  filename would have missed. ⚠ The lesson that is ADDED: when a quick scratch statistic disagrees
  with the pipeline's own instrument, **the scratch one is the suspect** — reproduce the
  disagreement both ways before writing the conclusion into a handover. (s110, GATE R3b)
- **`rebaseline-all-derived-artefacts`.** Changing an upstream global expires the intermediate CSVs
  and the fixed-amplitude gates too, not just the headline baseline. Three occurrences (s35, s45,
  s65). Fix: every render writes a `.args.json` stamp of its exact argv; every read checks it.
- **`check-for-unread-data-first` — SIX occurrences** (s60, 78, 81, 82, 84, 88). A whole stimulus
  level, a 12-point tone ladder, and three complete 129-capture renders each sat unread on disk
  while a session prepared to generate them. **Check what exists before rendering or capturing.**
- **Check what a tool already PRINTS before adding to it.** The number about to be added had been
  printed for four sessions. (s76)
- **A cache key that omits the thing you changed makes the change a silent no-op.** `_cache_key`
  hashes bands but not anchors: editing `THD_ANCHORS` and re-running returns the OLD records and
  prints a plausible table. Probe the key live, with a control that confirms it *does* move. (s88)
- ⭐ **NEVER REBUILD THE RENDER BINARY WHILE A MATRIX RENDER IS IN FLIGHT** — not even for a
  comment-only edit. `_cache_key` hashes `_file_sig(binpath)` (size + mtime_ns), so a relink
  mid-run splits the run's cache entries across two binary signatures and swaps the executable
  under live workers. The output is *probably* fine; "probably" is not a provenance for the
  artefact every later session diffs against. Cheapest clean fix: let the run finish, then re-run
  the same command — captures rendered after the relink hit cache, so only the pre-relink ones
  re-render. Keep the mixed-binary report beside it and diff the two as a control. (s91)
- **A COST CAN LIVE ENTIRELY OUTSIDE THE MATRIX.** `jfetSatNeg` 0.76 → 1.9 moved
  `OSValidationTest`'s 8× alias/signal floor −23.6 → −17.3 dB. The 129-capture matrix renders at
  OS=8 and grades FR/THD/harmonics **at bands** — it never measures inharmonic energy, so no amount
  of matrix work could have caught it. Before shipping a nonlinearity change, ask which gates
  measure a quantity the matrix structurally cannot. ⚠ And attribute by reverting the ONE constant:
  that is what showed `c21R` contributed nothing and reproduced the 45-session record to the digit.
  (s91) ⭐ **s92 measured it with a real instrument and the COST IS CONFIRMED REAL** — median
  **+1.87 dB** of extra fold-down at 8× over 21 tones, worst +13.6 dB — so this entry is now a
  worked example, not a caution. See the three entries below for what the instrument had to fix
  first.
- ⭐⭐ **A METRIC'S "FLOOR" IS A HYPOTHESIS TOO — MEASURE IT WITH A KNOWN-ANSWER SIGNAL.**
  `OSValidationTest` printed **−40.5 dB** in twelve cells across 46 sessions and everyone (this file
  included) read it as the measurement floor. It is the metric's own **window leakage**: f0 was
  2500 Hz against a 2.9297 Hz bin = 853.33 bins, so every harmonic whose order is not a multiple of
  3 sat a third of a bin off-centre and its Hann skirt escaped the ±3-bin "signal" mask. Measured on
  a synthetic signal with **zero** alias content: bin-exact reads −99 dB, off-grid reads **−40.65**.
  The true floor at those operating points is −86 dB. **One-third of a bin of misalignment cost
  59 dB**, and the artefact was indistinguishable from a physical floor because it was flat and
  reproducible. Run the analysis code on a pure tone with no DSP in the loop before believing any
  floor. (s92, `analysis/alias_gate.py` KA-1/KA-2)
- ⭐ **WHEN THE SYSTEM IS PERIODIC, BIN-EXACT + RECTANGULAR BEATS EVERY WINDOW CHOICE.** A tone at
  `f0 = k·fs/N` is periodic in exactly N samples; a time-invariant chain (including the oversampler,
  whose factor divides N) then has an output periodic in N, so a RECTANGULAR window has zero leakage
  and every harmonic **and every fold of a harmonic** lands dead on a bin. No ±m-bin mask is needed,
  therefore no mask width can be got wrong, and the classifier becomes `b % k == 0` — exact instead
  of tolerant. Gate it with a start-offset-invariance check; the read must not move at all. (s92)
- ⭐ **A WINDOW IS NOT A SUBSTITUTE FOR SETTLING.** An exponential DC transient is not periodic in the
  analysis window, so *no* window makes it disappear — only time does. `OSValidationTest` discarded
  0.3 s against `MasterOut`'s two ~0.72 Hz high-passes (τ = 0.22 s), so an asymmetric clipper's DC
  step was still decaying through the read and its energy landed in bins 1–50, which the harmonic
  mask classified as **alias**. Gate the claim both ways: the repaired metric must ALSO fail at the
  old settle (it does, −52.7 dB) and pass at the new one (−198.8 dB). ⚠ Here it turned out not to be
  the culprit — the LF bucket sits 12–15 dB below the alias bucket everywhere — which is exactly why
  it had to be measured rather than argued. (s92)
- ⭐⭐ **FOLD ARITHMETIC AND A BEAT NOTE PREDICT THE SAME BINS AT ONE f0 — MOVE f0.** Inharmonic energy
  at `n·f0 ± δ` is equally consistent with "harmonic N folding about the OS rate" and "the tone
  beating against an autonomous oscillation at δ", because `|N·f0 − m·fs_os|` **is** a sideband
  offset. The two are degenerate until the stimulus moves: a fold tracks f0, a beat note does not.
  One extra render at each of three f0 settled it — the dominant bins matched
  `|N·f0 − m·8·fs|` **to the bin** at all three (H152–156 at 2499 Hz, H190/193 at 2001 Hz, H117–120
  at 3249 Hz), and the offsets went 849.6 → 187.5 → 615.2 Hz. Corroborated independently by a
  192 kHz-base render (1.536 MHz internal) reading −65.9 dB where 48 kHz/8× reads −17.1. (s92)
- ⚠ **A BIN-EXACT SWEEP HAS DEGENERATE TONES — FLAG THEM, DON'T AVERAGE THEM.** At fs = 48 kHz a
  fundamental that exactly divides the rate (1500, 3000 Hz) puts every harmonic *and every fold* on
  a harmonic bin, so inharmonic content is impossible **by construction**: those rows read −213 and
  −3067 dB. Spectacular numbers that mean nothing. (s92)
- ⭐⭐ **CHECK THAT THE OUTPUT HAS THE PROPERTY YOUR WHOLE INSTRUMENT ASSUMES — IN THE TIME DOMAIN.**
  The bin-exact design rests on one premise: a stimulus periodic in M through a time-invariant chain
  gives an output periodic in M. That is one line to verify (`||y[n+M] − y[n]|| / ||y||` must sit at
  the storage floor) and it found a defect nothing spectral could have named — at 8× the chain is
  **aperiodic at 4 of 21 tones** (worst 0.69, i.e. 69 % RMS non-repetition) while 2× is exactly
  periodic at 21/21. At those points the "alias" reading is not aliasing and oversampling makes it
  worse. ⚠ The tell was a **control that was supposed to be boring**: a degenerate tone that can only
  read −200 dB read −23 dB, and its energy was broadband where fold-down is a handful of discrete
  peaks. **When a control comes back interesting, that is the finding.** (s92)
- **`wallclock-is-not-runtime`.** A healthy 30-min run was killed as a "17× regression"; the laptop
  had clamshell-slept. Diagnose with per-artefact mtimes + `pmset -g log`, never elapsed time.
- **`background-job-silence-is-buffering`.** An empty log after 10 min means block-buffered stdout.
  Launch with `python3 -u`.
- **`nohup … &` inside a backgrounded tool call reports the LAUNCHER's exit, not the job's.** Check
  the artefact, never the exit code. Likewise **`pgrep -f script.py` matches its own waiter.**
- **zsh does NOT word-split unquoted `$var`.** A loop passed `"1 0.0 -18"` as ONE argv, so every
  render silently fell back to defaults and overwrote 7 good CSVs. Any scan script must REFUSE to run
  with zero overrides. (s36, s37, s59, s98 — a 17-flag `--fit` list built into `$FITS` arrived as
  one argument; **argparse's own error message hides it**, because it prints the unrecognised list
  space-joined and a single bad argv is indistinguishable from many. Write the tokens one per line
  and `xargs` them, and PROBE the argv with a one-line `print(sys.argv)` before spending a 25-minute
  render on it. **s100, FIFTH occurrence** — an `ARGS="--master 0.5 ..."` string reached
  `OfflineRender` as one argv, both renders exited rc=2, and the comparison then printed **"❌
  DIFFER"** from its own else-branch on two files that did not exist. ⭐ Note the compounding: a
  word-splitting bug produced a *wrong verdict about the thing under test* rather than an obvious
  crash. In `zsh` use an ARRAY — `ARGS=(...)` expanded as `"${ARGS[@]}"` — echo `${#ARGS[@]}` against
  the expected count, and make any comparison assert its inputs EXIST before comparing them.)
  ⚠ **The mirror-image trap, s109: an argparse option whose VALUE starts with `--` is swallowed as
  an option.** A new `--render-arg` passthrough called as `--render-arg --input-ref --render-arg 0.9`
  fails with *"expected one argument"* — argparse cannot tell a value from a flag. That one at
  least errors loudly; the fix is to take ONE quoted string and `shlex.split` it
  (`--render-arg '--input-ref 0.9'`), which is also what makes the call readable. **Design any
  raw-passthrough option to take the whole flag+value as a single quoted argument.**
- **A concurrency-only bug passes every serial verification you have.** A new parameter was rebound
  by the function's own loop variable; filenames were wrong and every number was right. **Check a new
  parameter against the function's own LOCAL names, not just its callers.** (s73)
- **Artefact hygiene: the archived JSON must match the prose beside it.** A handover quoted
  bleed-free numbers next to a mixed-BLEND file that flatly contradicted them; both were correct.
  State the mode. (s82)

## 6. Reading physical measurements

- ⭐⭐⭐ **A SIGN PREDICTED FROM "WHERE THE NULL IS" IS REALLY A PREDICTION ABOUT WHERE THE
  *SOURCE* IS — AND IN A CHAIN WITH TWO NONLINEARITIES THOSE ARE DIFFERENT QUESTIONS.** GATE R was
  built on a clean-looking derivation: a null upstream of the nonlinearity starves it, so `Hn/H1`
  must DIP at the null; a null downstream leaves the harmonics untouched, so it must PEAK. Measured,
  our own model — whose null is provably pre-clipper (R2: it moves 329.7 → 164.2 Hz with the ladder
  caps and ignores the bridged-T) — gave a **+19.4 dB PEAK**, the opposite of the prediction. The
  derivation was not wrong, it was **pointed at the wrong device**: this chain has a J201 *and* a
  CD4049, the ladder sits between them, and the H2 at the null is made **entirely by the J201
  upstream** (removing its even term moves the statistic 59.011 dB; making the clipper symmetric
  moves it 0.001 dB). With the upstream source removed the null duly DIPS (−32.55), i.e. the
  algebra recovers the moment the second nonlinearity is taken out. ⭐ GENERAL: before reading a
  harmonic-referred statistic as a statement about topology, **measure which device is actually
  generating that harmonic at that frequency** — one arm per candidate generator, each shown
  non-vacuous elsewhere first. `verify-the-PREMISE`, applied to one's own derivation rather than to
  a handover. (s110, GATE R5)
- ⭐⭐ **AN `argmin` OVER A WINDOW SILENTLY CHANGES WHAT IT TRACKS THE MOMENT THE FEATURE STOPS
  BEING THE MINIMUM — AND NAMING THE FREQUENCY DOES NOT PREVENT IT.** GATE R named its notch at
  320 Hz (GATE Q's own rule, so that a candidate which MOVES the null cannot re-point the
  statistic) and then located the prominence by `argmin` over 200–520 Hz. Under drive the
  pre-clipper null washes out so far that the **post-clipper bridged-T notch at ~712 Hz** becomes
  the deepest thing nearby, and the estimator walked out to the window edge in **18 of 120 cells,
  all of them model cells** — the statistic quietly stopped being "the 320 Hz null" and became "the
  deepest feature in reach". ⭐ Two fixes, both worth having: **bound the window to what the feature
  can actually do** (here 290–370 Hz, containing every f0 measured on either side, and unable to
  reach the other notch), and **check for minima resting on an edge** — a bound is not a
  measurement. ⭐⭐ And the escaped feature was itself the finding: the two nulls straddle the
  compressor, so their RANK must invert with drive, which became a free prediction with no
  parameters. `a-positional-index-is-a-shape-claim`, one level up. (s110, GATE R4/R6b)
- ⚠ **TWO PROMINENCES MEASURED AGAINST DIFFERENT BASELINES CANNOT BE RANKED AGAINST EACH OTHER.**
  R6b's first version compared the 320 Hz null's prominence (referred to its named 202/508 Hz
  shoulders) with the bridged-T's (referred to its own window edges) and reported "no rank swap"
  while the **absolute** levels had plainly swapped. When the question is "which feature is
  deeper", compare absolute levels; a prominence is a *contrast* against a chosen reference and
  carries that reference with it. (s110)
- **Never read a peak's frequency, or a notch's depth, off the 1/3-octave grid.** It locates a peak
  to ±1/6 octave and understated one notch by 20 dB. Interpolate (parabolic vertex on the log-f
  axis). Check height, centre AND bandwidth. (s26, s46)
- **Normalise to something the feature under test does not itself move.** A baseline anchored inside
  the feature's own skirt manufactured a "wrong shoulder slope" finding and flattered a whole
  session's numbers. (s27, s63)
- **Peak-bin amplitude scallops.** Non-integer-cycle tones lose up to 1.42 dB on the peak FFT bin,
  growing with harmonic order. Sum mainlobe POWER. (s88)
- ⭐⭐ **A RATE DISCRIMINATES WHERE A LEVEL CANNOT — AND A LINEAR FILTER HAS EXACTLY ONE RATE.**
  Twelve sessions treated "our HF is ~26 dB light at 16 kHz under drive" as possibly a Sallen-Key
  value error, because a LEVEL is compatible with almost any story: a trim, a gain match, an anchor
  choice, a wrong corner. The rolloff **rate** over one octave is not — it is immune to the per-row
  gain match, to the anchor band, and to how hard the nonlinearity is working, and it carries a
  structural impossibility proof. Measured, the pedal's rate spans **18.5 dB/oct** with stimulus
  level and turns POSITIVE; ours holds −15…−23. **A rate that MOVES with drive cannot be a filter at
  all**, so the entire linear branch dies in one table, with no fitting and no render. ⭐ When a
  disagreement could be "wrong value" or "wrong mechanism", look for a statistic the two hypotheses
  must differ on *structurally* rather than one they merely differ on numerically. (s101, GATE I)
  - ⚠ **AND DERIVE THE REFERENCE RATE FROM THE ACTUAL NETWORK, NOT THE TEXTBOOK ASYMPTOTE.** Two
    cascaded 2nd-order LPFs are "4th order, −24 dB/oct" — true asymptotically, false over the octave
    actually measured, because the 8127.5 Hz end is not yet past the 10.7 kHz corner. The computed
    figure is **−18.25**, and asserting −24 gave the gate a **false FAIL against a correct model**.
    `rebuild-targets-dont-transcribe`, applied to a number that looked far too obvious to check.
  - ⭐ **The CLEAN-path control is what makes the whole argument readable and must run FIRST.** With
    the OD stage out of circuit our HF matches to 0.57 dB and is bit-invariant across all four
    stimulus levels — so the instrument is not level-dependent and the linear response is not the
    defect. Without that, "the rate moves with drive" is equally consistent with the *instrument*
    moving with drive.
- ⚠⚠ **A "LOCALISED FEATURE" TEST RUN ON A SIGMOID WILL FIND ONE — TWICE, IF YOU LET IT.** Hunting a
  predicted narrow spike (an alias fold at `fs/(N+1)`) inside a smooth drive-induced shelf, the first
  draft scored **|2nd difference|** and fired **27×** at the H6 locus — which is merely where the
  sigmoid's dip bottoms out — and printed "the fold mechanism is live" over a curve flat to 0.73 dB
  across the 6 kHz containing the locus that mattered. The second draft switched to local prominence
  against a symmetric annulus and *still* fired at H4, because an annulus straddling a curved flank
  returns prominence from the **curvature alone**. ⭐ The valid form is a **NULL**: compute the same
  statistic at non-locus frequencies on the same curve and ask whether the loci are outliers in that
  distribution — parameter-free, and immune to the curve's shape. ⛔ And note the failure mode
  lurking behind all three drafts: with six candidate loci scattered across the band, *some* locus
  always lands near a smooth feature. **Pre-register which locus the hypothesis actually needs**
  (here H2 — the strongest order, and the only one inside the band under investigation) instead of
  scoring "worst of six". ⚠ When the null then comes back thin (10 controls), say **underpowered**
  and scope the verdict; "100th percentile of 10" is not evidence, and *not tested* is not *negative*.
  (s101)
- ⭐ **HOW you sample a curve at a reporting band depends on the CURVE'S RESOLUTION, not on taste.**
  A point sample and a band average are indistinguishable on a 5.9 Hz-bin CSD (the point sample IS
  already a local average) and differ by **24 dB** on a 0.046 Hz-bin Farina read, where a point can
  land in the bottom of a notch. Changing an instrument's resolution silently changes what its
  "value at 50 Hz" means — **power-average over the band's own width whenever the curve is finer
  than the band.** (s90, same family as s26/s46) (`analyze.band_read`)
- ⭐⭐ **WHEN A REFERENCE IS RE-MEASURED WITH A BETTER INSTRUMENT, THE MODEL SIDE MUST BE RE-MEASURED
  WITH IT TOO — OR THE INSTRUMENT'S OWN ERROR IS BOOKED AS MODEL ERROR.** Session 70 replaced the
  ATTACK spec with a stepped-sine read and recorded the instrument-only delta on the pedal
  (boost **−29.1 %** width, **+5.28 dB** depth; cut/flat within 5.2 % and 0.43 dB). Every ATTACK
  candidate since session 63 is scored by `attack_render_gate.py`, which reads the RENDER with the
  old **swept** instrument — so the corrected spec was about to be compared against a swept-read
  model. Measured on the same audio with both instruments (`analysis/attack_stepped_gate.py`): the
  pedal's boost null narrows −29.1 % (reproducing s70 to 0.1 %) while the **render's WIDENS +11.1 %**,
  because smearing scales with how narrow the feature is and the model's null is ~2.5× broader.
  ⭐ The consequence is not a scale factor, it is a **different conclusion**: the width excess is
  worst at **flat (1.98×)** under swept-vs-swept and worst at **boost (2.70×)** under
  stepped-vs-stepped — and "which throw is worst" is exactly what selects a shared ladder element
  versus a per-throw one. **Re-measure both sides, and print both instruments' verdicts side by
  side so an ordering change cannot hide.** ⚠ Corollary: any ratio in a handover that divides a
  model number by a reference number inherits both instruments — check they are the same one before
  quoting it. (s93)
- **A band-limited Bode/Hilbert phase reconstruction is decided by its unmeasured TAILS** — worth
  36–91° at the band edges, i.e. the entire size of a "no passive network can do this" result. Never
  quote such a ceiling without a closed-form self-test and an explicit tail sweep. (s32)
- ⭐⭐ **A MIXING NETWORK'S OWN COEFFICIENT CAN BE NON-MONOTONE, AND THEN "the output fell when I
  turned it up" IS NOT EVIDENCE OF SATURATION.** GATE K3 recorded that the model's H1 transfer
  FALLS above LEVEL noon where the pedal's does not, and read it as "a stage downstream of LEVEL
  is saturating harder in the model" — a second, distinct, stimulus-dependent defect. It is
  neither second nor distinct. The shipped stage's clean coefficient `b(L) = a(L)(1−L)` **peaks at
  L = 0.5 and is exactly 0 at LEVEL max**, so raising LEVEL past halfway *removes* the clean
  signal from the output; if the clean tap is hotter than the OD path the sum genuinely falls, in
  a strictly linear network with no saturating element anywhere. The tell was already on the
  bench: a purely linear inverse reproduces the model's law **at that same stimulus** to ~1e-10.
  ⇒ the "fall" is A3 (the too-hot clean tap) seen through the network's bleed turnover, and it
  shrinks when A3 is corrected. ⭐ GENERAL: before attributing a non-monotone response to a
  nonlinearity, write down the linear network's coefficient as a function of the control and check
  whether *it* is monotone. Same family as `computed-verdicts-not-narrated`: the saturation
  reading was plausible, was written into a handover, and was never computed. (s104, GATE L8)
- **Cancellation shows up as non-monotonicity.** Sweep the driving control; a monotonic model where
  the device nulls means a phase problem, not a level one. (s29)
- **Dilution fakes a resonance.** A flat effect read through a mixer looks peaked wherever the
  measured path is strongest — three sessions chased a resonator that was the clean bleed. (s60)
- **`abs()` on a quantity whose sign is unobservable is fine; DIFFERENCING it against one whose sign
  IS observable is not.** Two sessions designed against a target with a lost sign. (s33)
- **Rebuild targets, don't transcribe them.** A target pasted in as literal arrays lost a sign; the
  tool that imports and recomputes it did not. (s33)
- ⭐⭐ **A RESIDUAL IS NOT RESOLVED BETTER THAN THE CORRECTIONS YOU SUBTRACTED TO GET IT — QUOTE THE
  BOUND, NOT THE RESIDUAL.** Session 106 recorded the clean path as *"exonerated to 0.007 dB"*. The
  0.007 is real, but it was obtained by subtracting a MASTER-law term of 2.02 dB and a provenance
  term of 0.225 dB, and the capture it was read on sits on a **different capture route** and a
  **different capture session** from the rows the exoneration is about — each worth 0.17–0.23 dB.
  The honest figure is **0.41 dB**, 60× larger. ⭐ Nothing about the conclusion changed (the deficit
  is 13× the bound either way), which is exactly why the overclaim was easy to make and would have
  gone unchallenged. GENERAL: when a small number is the difference of large ones, its error bar is
  set by the terms that were removed and by every basis change between the measurement and the
  claim — carry them, and state the bound. (s107, GATE O8)
- ⭐⭐ **A CONTROL SUMMARISED AS A SCALAR WILL UNDERSTATE ITSELF EXACTLY WHERE THE FINDING LIVES.**
  The `gain-n12` provenance control was recorded as *"agree to 0.107 dB"*. That is the **broadband
  mean** of a curve running **+0.247 dB below 100 Hz to −0.067 dB at 1–8 kHz** — and the band the
  whole A3 case is quoted in, 100–400 Hz, reads **+0.225**, i.e. the recorded figure understates the
  correction by 2.1× precisely where it is applied. A scalar correction would have left most of it
  behind. ⭐ GENERAL: a control is a *curve* until proven otherwise; print it per band before
  reducing it, and apply it per band. Same family as `pooled-statistic-cannot-answer-about-its-own-
  axis`, one level down — there the pooled statistic was the finding, here it was the correction.
  ⚠ And check whose it is: the model side of that same comparison is a pure level shift to
  **1.8e−08 dB**, so the entire residue is the reference's, which is a different fact with a
  different consequence. (s107, GATE O5)
- **One capture is not the population.** A yield inferred from a single capture read as ZERO; over 81
  captures it was 65 %. (s88)
- **Removing a confound can destroy sensitivity.** The extreme setting that idles the clipper also
  buries the signal 15 dB under the bleed. Prefer a knob that decouples the two — drive noon is the
  sweet spot, not an unfortunate compromise. (s59)

## 7. Process

- ⭐⭐ **A handover that is not updated is worse than absent, because the stale version reads as
  current.** Session 75 closed without updating `CLAUDE.md`; it cost most of session 76 to
  rediscover. (s76)
- **Exclude explicitly, with the evidence recorded, never silently.** (s40)
- ⭐ **A GATE THAT LIVES IN A MARKDOWN TABLE IS A TRANSCRIPTION, AND TRANSCRIPTIONS ROT.** The Phase 9
  release gate's "now" column was hand-read into `CLAUDE.md`. Re-measured from the same file, same
  range, same rows: every OD cell reproduced **to the digit**, and CLEAN's percentiles did not
  (0.21/0.66/1.99 quoted, 0.23/0.76/2.17 measured; three plausible alternate pools reproduce none of
  them, and the provenance was unrecorded). Put the thresholds in a script, compute every cell beside
  them, and exit non-zero — `rebuild-targets-dont-transcribe` applied to the one table that decides
  when a phase closes. (s90, `analysis/release_gate.py`)
- **A failing acceptance check is a BLOCKER, not a footnote.** A fit printed
  `worst |err| = 3.71 dB (CHECK)` and was shipped anyway; the plugin stayed 3 dB too loud for 24
  sessions. (s41)
- **A harness fix can silently break a tool outside the harness.** A correct shared-render fix
  double-counted 12 dB in a standalone calibration script nobody re-ran. (s41)
- **`capture-outranks-schematic` — with one carve-out.** Fitting to the captures is right for
  linear/EQ work. It is **wrong for even-order harmonic structure**, where the capture is the thing
  that is broken (`reference-sources.md` §4).
- **"Schematic verified" never implies "the captured unit matches".** There is always a third branch:
  *the document is right AND the unit differs*. Four occurrences in five sessions. (s21–s25)
- **Localise before fitting a constant.** An aggregate win does not localise a cause: check the error
  persists with the part out of circuit, and that the objective has an interior minimum. (s23)
- ⭐ **Know when to stop measuring.** Sessions 75–88 followed a pattern — build an instrument, get a
  caveat, build an instrument to resolve the caveat. Each closed an item honestly and nothing
  shipped. **If a session's next step is a refinement of a component of a defect that has no
  candidate fix, that is the signal to go and ship something instead.**
