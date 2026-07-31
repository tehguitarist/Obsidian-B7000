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
- **Verify the PREMISE, not the prior session's framing of it.** A 14-session-old gap
  characterisation had expired — unrelated fixes had dissolved it — and re-measuring took one
  command. A stale premise is the most expensive kind, because it selects the whole next workplan.
  (s38)
- **A gate must be calibrated against the defect's SIGNATURE, not a proxy for it.** A flat-topping
  gate keyed on "16 consecutive samples above 0.985×peak" rejected a long-trusted reference capture
  peaking 7.6 dB below full scale — a sine spends ~5.5 % of its period up there. The real signature
  is a plateau *pinned* at the converter's ceiling. (s68)
- **Run a new gate against a case whose answer you already know.** A gate demanding "every OD capture
  moves" failed on a render already proven sound, because 6 rows are inert *by construction*
  (BLEND=0 ⇒ OD out of circuit). That is the only thing separating "the candidate is bad" from "my
  gate is bad". (s84)
- **Mutation-test a guard.** A new `assert_anchors_match` read the wrong JSON key, returned `None` on
  every real report and fell through to its "cannot verify" branch — a warning that reads as
  diligence while checking nothing. (s88, same class as s80)
- **A control measured on the quantity the instrument ANCHORS on cannot fail.** An odd-order control
  scored H3 and returned `+0.00` everywhere: every side is anchored on its own H3/H1 crossing, so H3
  is pinned by construction. Rebuilt on H5 it moved. (s80)
- **A suggestion with the right shape can still be wrong; the check is the cheap part.** (s83)

## 2. Aggregates, membership and range

- ⚠⚠ **`aggregate-moved-check-membership-first` — SEVEN occurrences.** An aggregate that fails to
  reproduce has usually gained or lost rows, not changed value. Every shared row was bit-identical
  each time. **Never quote a matrix total without its capture count.**
- **An aggregate's RANGE can be the problem, not its membership.** A tool's self-validation was
  quoted over 40–1700 Hz and omitted the three bands where it failed — which were the bands the
  claim rested on. (s52)
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

## 3. Gates, controls and verdicts

- **`computed-verdicts-not-narrated` — FOUR occurrences.** A conclusion hard-coded into a tool's
  output outlives the condition it described and prints above a table contradicting it. Derive every
  verdict line from the data, and make it state the opposite when the data says so. (s34, s61, s68)
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

## 4. Fits, searches and degeneracy

- **A monotone objective with no interior minimum is a degeneracy, not a fit.** "Make the clipper see
  less" killed the s5/s6 clipper fits, the GAP #3b C13 candidate and the rail-voltage fit. Require
  the objective to push back from BOTH sides. (many)
- **`bound-resting-means-unidentified`.** A parameter on its bound is not a constraint to trade off —
  the outside bound is the missing equation. But: **a folded parameter's endpoint is a SYMMETRY
  point, not a fence** (θ measured at 0.000e+00). Check which you have. (s47, s86)
- **`search-settings-are-derived-artefacts`.** A search box justified by a measurement expires with
  it. Sweep the setting instead of inheriting the choice — a box "known to be constraining" was
  chosen against a calibration that had since been corrected. (s66)
- **Gate a search before trusting its failure.** A random search "refuted" a topology while
  recovering a *definitionally reachable* target to only 0.73 dB. Synthesise a target you know is
  reachable and require recovery under the noise floor first. (s57)
- **Quantise a ranking key to the resolution of what it ranks.** 0.06 bins beat 0.07 bins and picked
  the worse candidate; 0.01 bins is 0.06 Hz and does not exist in the data. (s66)
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
- **`wallclock-is-not-runtime`.** A healthy 30-min run was killed as a "17× regression"; the laptop
  had clamshell-slept. Diagnose with per-artefact mtimes + `pmset -g log`, never elapsed time.
- **`background-job-silence-is-buffering`.** An empty log after 10 min means block-buffered stdout.
  Launch with `python3 -u`.
- **`nohup … &` inside a backgrounded tool call reports the LAUNCHER's exit, not the job's.** Check
  the artefact, never the exit code. Likewise **`pgrep -f script.py` matches its own waiter.**
- **zsh does NOT word-split unquoted `$var`.** A loop passed `"1 0.0 -18"` as ONE argv, so every
  render silently fell back to defaults and overwrote 7 good CSVs. Any scan script must REFUSE to run
  with zero overrides. (s36, s37, s59)
- **A concurrency-only bug passes every serial verification you have.** A new parameter was rebound
  by the function's own loop variable; filenames were wrong and every number was right. **Check a new
  parameter against the function's own LOCAL names, not just its callers.** (s73)
- **Artefact hygiene: the archived JSON must match the prose beside it.** A handover quoted
  bleed-free numbers next to a mixed-BLEND file that flatly contradicted them; both were correct.
  State the mode. (s82)

## 6. Reading physical measurements

- **Never read a peak's frequency, or a notch's depth, off the 1/3-octave grid.** It locates a peak
  to ±1/6 octave and understated one notch by 20 dB. Interpolate (parabolic vertex on the log-f
  axis). Check height, centre AND bandwidth. (s26, s46)
- **Normalise to something the feature under test does not itself move.** A baseline anchored inside
  the feature's own skirt manufactured a "wrong shoulder slope" finding and flattered a whole
  session's numbers. (s27, s63)
- **Peak-bin amplitude scallops.** Non-integer-cycle tones lose up to 1.42 dB on the peak FFT bin,
  growing with harmonic order. Sum mainlobe POWER. (s88)
- **A band-limited Bode/Hilbert phase reconstruction is decided by its unmeasured TAILS** — worth
  36–91° at the band edges, i.e. the entire size of a "no passive network can do this" result. Never
  quote such a ceiling without a closed-form self-test and an explicit tail sweep. (s32)
- **Cancellation shows up as non-monotonicity.** Sweep the driving control; a monotonic model where
  the device nulls means a phase problem, not a level one. (s29)
- **Dilution fakes a resonance.** A flat effect read through a mixer looks peaked wherever the
  measured path is strongest — three sessions chased a resonator that was the clean bleed. (s60)
- **`abs()` on a quantity whose sign is unobservable is fine; DIFFERENCING it against one whose sign
  IS observable is not.** Two sessions designed against a target with a lost sign. (s33)
- **Rebuild targets, don't transcribe them.** A target pasted in as literal arrays lost a sign; the
  tool that imports and recomputes it did not. (s33)
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
