# FINAL CAPTURE WINDOW — everything we need, and everything we might ever need

> ⛔⛔ **SUPERSEDED 2026-07-29 (session 71) — THE PREMISE OF THIS DOCUMENT IS VOID.** The captures are
> recorded from the **Neural DSP Darkglass emulation**, not from a hardware pedal
> (`.claude/rules/reference-sources.md`). **There is no closing window.** Any condition on this list
> can be re-rendered at any time, unlimited, with perfect repeatability. The urgency, the
> Tier 1/2/3 rationing, and the "then never again" framing throughout are all wrong.
> **What survives:** the per-item *content* — the list of conditions still worth having (§6's 8 files
> and §8's 3 files remain unrendered) and the protocol notes about filename grammar and gating.
> **What is dead:** §0 (PCB photos — never obtainable, and now not even about the fitted target),
> the deadline ordering, and §2's repeatability set as framed — session 70 rejected it using a
> discriminator (that two analogue re-recordings cannot agree better than ~−90 dBFS) which does not
> apply to a deterministic renderer. Re-examine that rejection before re-recording anything.
> Keep this file for the condition list; do not act on its urgency.

> **Written 2026-07-29 (session 68).** The pedal is available for **~5–6 more days**, then never
> again. This document is the complete forward-looking list, not just the next session's ask.
> Ordered by value, with an honest note on each about what it decides and what it costs.
>
> **⚠ THE SINGLE HIGHEST-VALUE ITEM IS NOT AN AUDIO CAPTURE — IT IS §0 (PHOTOGRAPH THE BOARD).**
> Read §0 first and decide on it early, because it is the only item that resolves a caveat sitting
> under *four* shipped constants at once, and it needs no recording time at all.
>
> **Totals:** §0 costs ~15 min and no recording. Tier 1 = **22 files ≈ 55 min**. Tier 2 = **20 files
> ≈ 45 min**. Tier 3 = **10 files ≈ 25 min**. All of it is ~2 hours of recording spread over the
> window. **§3's stimulus is written and validated (session 68) — nothing in Tier 1 or 2 is blocked
> on me any more.** Only §11 (96 kHz, Tier 3, optional) still needs a stimulus; ask before recording it.
>
> **Suggested order if you want to stop early at any point:** §0 (photos) → §1 (owed) → §2
> (repeatability) → §3 (notch sweep) → §4 → then Tier 2 as time allows. Everything above the line you
> stop at is self-contained.

---

## ▶ STATUS AS OF 2026-07-29 (session 70) — Tier 1 is essentially COMPLETE

35 captures delivered and gated with `analysis/verify_new_captures.py`. **25 pass cleanly; 10 are
rejected and need re-recording.**

| § | Item | Files | Status |
|---|---|---|---|
| §0 | PCB photographs | — | ⛔ **DECLINED — closed permanently** (not the user's pedal) |
| §1 | `gain-n12` re-captures, owed since session 48 | 4/4 | ✅ **landed, all pass** |
| §2 | Repeatability set | 10 | ⛔⛔ **REJECTED — duplicated takes, please re-record** |
| §3 | Fine-resolution notch sweep | 6 + **4 bonus GRUNT** | ✅ **landed, all pass** |
| §4 | Bleed-free JFET/gm ladder | 2/2 | ✅ **landed, all pass** |
| §5 | `b0` LEVEL midpoints | 4/4 | ✅ **landed, all pass** |
| §6 | Mid-freq at intermediate knob points | 0/8 | ▶ outstanding |
| §7 | ATTACK + GRUNT bleed-free at drive MAX | 5/5 | ✅ **landed, all pass** |
| §8 | MASTER taper midpoints | 0/3 | ▶ outstanding |
| §9–§11 | Tier 3 (day-2 retake, DI, 96 kHz) | 0 | ▶ optional |

**If recording time is short, the priority order for what remains is: §2 (re-record) → §6 → §8.**
§2 first by a wide margin — it is the only rejected item, and the only one whose absence weakens
every gate in the project rather than one measurement.

⭐ **Four bonus files again:** the notch set arrived with `notch_*_grunt-{boost,flat}` at both drive
settings as well as the six requested. GRUNT is the schematic-verified **linear** control that sits
at the **clipper input**, so it is exactly the right operating-point control for the ATTACK reading
— the same role session 68's bonus GRUNT pair played. Genuinely useful, not redundant.

---

## §0 ⛔ PHOTOGRAPH THE PCB — **DECLINED 2026-07-29 (session 70). CLOSED PERMANENTLY.**

> **The user does not own this pedal and is not willing to open it. That is a legitimate and final
> answer, and it is recorded here so no future session re-proposes it.**
>
> **What this makes permanent.** The four departures in the table below are now **unresolvable
> forever**. They keep their current status — each is defensible on its own measurement, and
> collectively they remain four unverified claims about one physical board — but the "third branch"
> (*the document is right AND the captured unit differs*) can now **never be closed in either
> direction**. Quote them that way from here on: not "pending verification", but *"fitted to the
> captures; the physical board was never inspected and never can be."*
>
> **The one consequence with teeth** is the 4049 rail. `analysis/clipper_rail_selfconsistent.py`'s
> **5.636 V** rests on IC3's five spare inverter sections being grounded, which is verified on
> **both schematics** (primary p.4 session 42, backup session 43 — node-for-node, so it is
> triple-checked as a *document* claim) but never on this board. If they floated instead the rail
> collapses to **2.70 V**, at which the shipped `clipSat` sum is physically *impossible* rather than
> merely tight. That remains the standing A5 caveat and it is now **closed as unfalsifiable** — it
> does not block anything, but it must never again be written up as "to be confirmed".
>
> ⚠ **Do not substitute a proxy for this.** No audio capture can settle a component marking or an
> internal DC rail; that was the whole point of §0 being a photograph rather than a recording. If a
> future session finds itself proposing an audio test "to settle C7", it has mis-scoped the problem.

<details>
<summary>Original §0 request, kept for the reasoning (superseded by the decision above)</summary>

### PHOTOGRAPH THE PCB — the highest-value thing available, and it is not a recording

**The problem this solves.** `circuit.md`'s largest standing caveat is that **neither schematic
describes the unit we captured.** Our primary schematic is PCB Guitar Mania's "Black Mirror VII"
clone of the **original B7K**; the captured unit is a real Darkglass **B7K Ultra**. Every Ultra-only
feature is tagged `[ENG]` (engineered, not verified) and — more importantly — **four shipped
constants are large departures from schematic-verified parts**, all currently excused by the same
unfalsifiable "the Ultra differs from the clone" argument:

| Constant | Schematic | Shipped | Departure |
|---|---|---|---|
| `trebleC7` (C7) | 100 n | 680 pF | **147×** |
| `clipC15` (C15) | 2u2 | 5.2 nF | **423×** |
| `c21R` (C21's load) | 10 k | 100 k | **10×** |
| `trebleWiperR` (R36) | 3k3 | 4k7 | 1.42× |

Each was fitted to the captures and each is defensible on its own measurement. But collectively they
are four unverified claims about one physical board, and **they can never be checked once the pedal
is gone.**

**What I'm asking for.** Open the enclosure and take **high-resolution photographs of both sides of
the PCB** — no desoldering, no probing, no powering it up with the lid off. Overlapping shots at the
highest resolution your phone or camera manages, close enough that silkscreen designators and
component markings are legible; the four regions that matter most are the treble/ATTACK network
(around C7/R11/R13/R8), the clipper (IC3/R19/C15/R20/R21), the EQ input (C21) and the Baxandall
treble leg (R36). Wide establishing shots of each side too, so I can register the close-ups.

**What it would decide.** Film caps and resistors are usually marked; SMD parts often are not, so
this may be partial. But even partial results are decisive in either direction:
- If a marking reads 680 pF where the schematic says 100 n, `trebleC7` stops being a 147× fudge and
  becomes a **documented revision difference** — and the same logic transfers to the other three.
- If it plainly reads 100 n, then the 147× is a **real model error being absorbed at the wrong
  node**, and the A3 search has been fitting a compensating value for 34 sessions. That is worth
  knowing even though it is the unwelcome answer.
- Either way it settles whether IC3's five spare inverter sections are grounded on *this* board.
  That is currently verified only on the two schematics, and `analysis/clipper_rail_selfconsistent.py`
  shows the derived 4049 rail collapses **5.636 V → 2.70 V** if they float instead — at which the
  shipped `clipSat` sum becomes physically *impossible* rather than merely tight (open A5 item).

**Risk, stated plainly.** Opening it risks scratched anodising, a stripped screw, or a torn
ribbon/pot nut if the board is awkward to lift. It is your pedal and your call — I am not going to
pretend the risk is zero. If you would rather not, say so and I will keep treating the four
departures as unresolved-forever, which is a legitimate choice.

**If you are willing to go further** (optional, higher risk, only with the pedal unpowered): a
multimeter across R36 and a capacitance meter on C7/C15 in circuit would be even better, though
in-circuit readings are unreliable for caps in parallel with other paths. Photos alone are the
high-value/low-risk item; probing is a bonus.

</details>

---

# TIER 1 — owed, or decisive. Do these first. (22 files, ~50 min)

## §1 ⭐⭐ The four `gain-n12` OD re-captures — OWED SINCE SESSION 48

```
ref-od_gain-n12.wav
level-0930_gain-n12_base-od.wav
level-1430_gain-n12_base-od.wav
level-1700_gain-n12_base-od.wav
```

**Settings:** exactly the matrix default (MASTER noon, BLEND **max**, LEVEL per the filename, DRIVE
noon, all EQ noon, ATTACK Flat, GRUNT Cut, LO-MID 500 Hz, HI-MID 1.5 kHz, DIST engaged) — with the
interface send **12 dB down** from the normal level, which is what the `gain-n12` token means.
`ref-od_gain-n12` is LEVEL **noon**. (`level-0700_gain-n12` is the LEVEL=0 silent null — **skip it**,
it carries no information.)

**Why these are owed.** Session 48 proved with a **zero-free-parameter** test that these four are
*not* −12 dB retakes of their normal-gain twins. THD is a ratio, so a record gain cannot move it at
all and a send pad can only slide the curve sideways — therefore the **value at the THD curve's
interior turning point is invariant** to either. Measured, the implied pad is **+9/+9/+6/+3 dB**
instead of the harness's 12.07, and the turnover value itself differs from the twin by
**+15.6 / +13.6 / +2.9 / +1.0 dB** — a quantity no gain of any kind can move. Suspected cause:
**BLEND left at the wrong setting** on those takes (the error shrinks as LEVEL rises, which is what
clean-bleed dilution looks like).

**What it decides.** These 16 matrix rows are the **only group that votes against changes which
improve every other group monotonically** — they blocked the `btC17` candidate in session 47 and
forced `matrix_grade.py` to permanently split the OD aggregate into `OD ex gain-n12` /
`OD gain-n12 [bad]`. Until they are re-taken, every OD aggregate in the project carries a known-bad
16-row group, and no candidate can be judged on the full matrix. **⚠ Please double-check BLEND is
fully clockwise before each of these four.**

## §2 ⭐⭐ The repeatability set — 10 files, and it cannot be reconstructed later

> ## ⛔⛔ DELIVERED 2026-07-29 AND **REJECTED** — PLEASE RE-RECORD. THIS IS THE ONE ITEM ON THE
> ## LIST THAT STILL NEEDS YOU, AND IT IS THE MOST LOAD-BEARING ONE.
>
> The ten files that arrived carry **zero take-to-take information**. They are not five takes each;
> they are **one take each, duplicated five times**:
>
> * Within `repeat_ref-od_*`, all five differ from one another by **rms −160 to −164 dBFS**.
> * Within `repeat_ref-clean_*`, all five differ by **rms −147 to −150 dBFS**.
> * `repeat_ref-od_*` are additionally **copies of the existing `ref-od.wav`** from a prior session
>   (rms diff −163 dBFS), not new recordings at all.
>
> **Why that is conclusive rather than merely suspicious.** Those numbers are **float32 rounding**,
> not audio. Any interface's own converter noise floor is ~**−90 to −110 dBFS**, so two genuine
> analogue re-recordings *cannot* agree better than that — it is a physical floor, not a tunable
> threshold. −163 dBFS is 50–70 dB below it. The peaks agreeing to six decimal places
> (`0.148862` five times; `0.780394` five times) and the alignment lag being **exactly 0 samples**
> in every pair say the same thing three different ways.
>
> Most likely cause: the five files were **exported/bounced five times from one recorded region**
> rather than recorded five times. (`repeat_ref-clean_*` is at least genuinely *new* audio — it
> matches nothing else on disk — so only the record passes were missed, not the take itself.)
>
> **What to do.** Ten **separate record passes**. Press record, play the stimulus, stop, then
> **physically unplug and re-plug both cables**, and start the next pass. Spread over ≥30 minutes if
> practical. The unplug/replug and the time spread are not fussiness — they are *the quantity being
> measured*: connector contact variation and warm-up drift are exactly what the floor is supposed to
> include, and a re-export includes neither.
>
> **Verify before sending:** `/opt/homebrew/bin/python3.11 analysis/verify_new_captures.py` now has
> a permanent **duplicate-take gate** that catches this in seconds. It reports
> `none -- every capture is distinct audio` when the set is good.

```
repeat_ref-od_1.wav  …  repeat_ref-od_5.wav
repeat_ref-clean_1.wav … repeat_ref-clean_5.wav
```
(These sit outside the matrix grammar deliberately, like `a3tones_*` and `jfet_ladder_*`.)

**Settings:** identical to `ref-od.wav` / `ref-clean.wav` (pure matrix default; `ref-clean` = DIST
disengaged). **Between every take, physically unplug and re-plug both cables**, and if practical
spread the ten takes over **≥30 minutes** rather than back-to-back.

**Why this is the item I would least like to skip.** The **0.144 dB take-to-take floor is the single
most load-bearing number in the entire project.** Every gate, every "is this real or noise"
judgement, every accepted/rejected fit for 50 sessions has been compared against it — and it rests
on a small number of replicate pairs. Worse, session 28 discovered that the five nominally-independent
flat-EQ replicates are **effectively only 2 independent shapes**, because MASTER is a flat divider so
the three master captures and `ref-clean_gain-n12` are all the *same* shape.

**What it decides.** It converts the floor from a point estimate into a measured distribution with a
real standard deviation, and — because of the unplug/replug and the time spread — one that includes
connector contact variation and warm-up drift rather than just converter noise. Several currently-open
findings sit at 2–5× the floor (A2f's ±0.2 dB clean tilt, the ~1 dB GAP #1b residual, the ATTACK
cut-shape spread). Whether those are real *at all* depends on a number this set would finally pin.
Nothing else on this list can be substituted for it, and it is unobtainable once the pedal is gone.

## §3 🔧⭐⭐ Fine-resolution notch sweep — the ATTACK width, measured without the smearing caveat

```
notch_level-1700_attack-flat.wav      notch_drive-0700_level-1700_attack-flat.wav
notch_level-1700_attack-boost.wav     notch_drive-0700_level-1700_attack-boost.wav
notch_level-1700_attack-cut.wav       notch_drive-0700_level-1700_attack-cut.wav
```

**✅ NO LONGER BLOCKED — the stimulus is written, generated and validated (session 68).**
`analysis/gen_notch_sweep.py` → **`analysis/notch_sweep_48k.wav`, 176.100 s, peak −14.0 dBFS.**
(⚠ this line read "175.9 s" until session 70 — a mis-stated figure, not a changed stimulus. It made
`verify_new_captures.py`'s first draft fail all ten perfectly good notch captures, because that gate
had transcribed the number from here instead of reading the generator's own output. The gate now
derives it; do not re-transcribe it.)
Regenerate any time with:

```bash
/opt/homebrew/bin/python3.11 analysis/gen_notch_sweep.py
```

Play **that** file (not the main test signal) and record the output, exactly as with the
`jfet_ladder_*` captures. It carries its own `sweep_clean` alignment anchor and a 1 kHz cal tone, so
the standard loaders work on it unchanged.

⚠ **Its span was corrected during validation and this matters.** My first draft ran 250–450 Hz —
wide enough for a null at 316–334 Hz, yet it read a broad null's depth as **7.56 dB against a true
15**, *worse* than the instrument it replaces, because every depth in this project is referred to the
**200–270 Hz shoulder** and there was no data below 250 Hz to establish it. Now 150–550 Hz (2 Hz
through the 280–380 Hz core, 4 Hz across the skirts).
**Validated against five synthetic notches of known f0/depth/width:** on the sharp null — which is
what boost is, and the throw whose width is the open item — depth error is **0.26 dB vs the swept
instrument's 4.31**, width **12.1 vs 15.6 Hz**, and **f0 exact in all five cases**. A ~30 % width
over-read on a 12 Hz feature is the same size as the 0.87–1.29× discrepancy under argument.

**Settings:** LEVEL **max**, BLEND **max**, GRUNT Cut, EQ flat, MASTER noon; ATTACK per filename;
the left column at DRIVE **noon**, the right column at DRIVE **minimum**.

**Why.** The largest open ATTACK item is now the null's **WIDTH**, and width is exactly the quantity
a 5.86 Hz-bin CSD estimate corrupts worst. The probe's own self-test (session 61) measured **two**
distinct bias mechanisms: bin smearing makes a true 33 dB notch read **28.71 dB**, and shoulder
contamination makes a broad notch's depth understate by **−4.39 dB** definitionally. And the pedal's
boost null is only **4 bins wide**, so its bin-span width is quantised at roughly **±25 %** — which
is why session 63 had to add an interpolated width column, and why session 66's headline
(widths 0.87/1.29/1.03× the pedal's) still carries a resolution caveat it cannot shed.

**What it decides.** A 2 Hz stepped sine has no band-averaging and no smearing, so f0, depth **and**
width all become directly measured rather than estimated-with-a-bias-note. That converts the one
number the whole two-pole ATTACK topology is now being judged on from "±25 % quantised, plus two
understating biases" into a real measurement. It also finally lets the **depth** be quoted as a value
instead of a lower bound, which is the caveat sessions 61–66 all had to carry.

## §4 ⭐ Bleed-free JFET/gm ladder — the last load-bearing unmeasured anchor

```
jfet_ladder_level-1700_drive-min.wav
jfet_ladder_level-1700_drive-noon.wav
```

**Settings:** the existing `analysis/gen_jfet_ladder.py` stimulus (already on disk — no new tooling),
but with **LEVEL fully clockwise** and BLEND **max**, GRUNT Cut, EQ flat. DRIVE min and noon.

**Why.** `jfetGm = 0.10 mS` is an **anchor** — a constant held fixed while everything else is fitted
around it — and session 44 closed A5 with the explicit admission that *"gm-sensitivity is still NOT
flat (34.1 → 68.1/86.6/237.9 at gm 0.09/0.12/0.15 mS), so the session-4 anchor remains
load-bearing."* Meanwhile session 7 showed all three historical gm estimates (0.551 / 0.090 /
0.0274 mS) were really **measurements of the OD/clean mix ratio**, not of the device, because the
clean BLEND bleed contaminated them. The existing `jfet_ladder_*` captures were recorded at the
matrix default — **LEVEL noon** — so they carry that bleed and the fitted LEVEL taper too.

**What it decides.** At LEVEL max the bleed is **exactly zero by topology** and LEVEL sits after
every nonlinearity — the same trick that made the ATTACK measurement clean. So this gives the first
**bleed-free** gm measurement, on a stimulus already designed for it (dense level ladders at
110/220/440 Hz). Drive min is the one that matters most: DRIVE sits *downstream* of the J201, so the
device sees a fixed level and only needs its gm right at one operating point (session 15's own key
simplifier).

---

# TIER 2 — closes named open items, all cheap. (20 files, ~45 min)

## §5 `b0` — finer LEVEL sampling (4 files)

```
level-0815_base-od.wav   level-1045_base-od.wav   level-1315_base-od.wav   level-1545_base-od.wav
```
(= LEVEL 0.125 / 0.375 / 0.625 / 0.875 — the midpoints between the existing points. Matrix default
otherwise.)

**Why.** Item (d) on the standing NEXT list: *settle `b0` between the LEVEL and DRIVE axes before
quoting any absolute A3 magnitude.* Session 54 fitted the LEVEL taper to p = 1.90 ⇒ **b0 = −15.70 dB
[−16.20, −15.25]**, which does **not** overlap the drive axis's **β = −16.75 [−17.25, −16.50]** — and
its law residual (0.33 dB) exceeds the floor, so that interval is optimistic. The fit has **one** free
parameter against **four** usable knob points (LEVEL=0 is a null). Both the DRIVE and MASTER tapers
turned out **not** to be power laws; there is no reason to assume this one is, and 4 points cannot
tell you.

**⚠ An honest limit, so you don't over-invest here:** do **not** try to give me LEVEL = 0.95. Near
L = 1 the OD leg scales as 1/(1−L), so pointer error becomes hypersensitive and the reading is
worthless. The two **mechanical stops** (fully CCW 0700, fully CW 1700) are the only exactly-known
knob positions in this entire project — everything else carries pointer error worth >1 dB on a wide
range. The four midpoints above sit in the well-conditioned region on purpose.

## §6 ⭐ Mid-freq switch positions at intermediate knob points (8 files)

```
lomidfreq-250_lomid-0930_base-clean.wav    lomidfreq-250_lomid-1430_base-clean.wav
lomidfreq-1k_lomid-0930_base-clean.wav     lomidfreq-1k_lomid-1430_base-clean.wav
himidfreq-750_himid-0930_base-clean.wav    himidfreq-750_himid-1430_base-clean.wav
himidfreq-3k_himid-0930_base-clean.wav     himidfreq-3k_himid-1430_base-clean.wav
```
(DIST **disengaged** — these are `base-clean`. Otherwise matrix default with the named switch/knob.)

**Why.** A2c is the second-largest open voicing gap, its remaining **7 captures over 1.5 dB are all
mid-freq-switch extremes**, and per-position fitting was explicitly authorized by you on 2026-07-26.
But each non-default switch position currently has only **two** knob points — full cut (0700) and
full boost (1700). Two points cannot separate **centre** error from **range** error from **width**
error, and that distinction is the entire lesson of session 26 (the residual turned out to be width,
after two sessions assumed it was centre or range). Session 25's own note flagged this: *"check
whether these can move at all before spending fitting budget there."*

**What it decides.** It gives a **pot law per switch position** instead of just endpoints — the exact
method that cracked GAP #4 and the TREBLE range. It also lets the knob-pointer floor be *estimated*
rather than assumed: the pedal's own cut-vs-boost captures currently disagree on peak frequency by
**6.1 % mean / 16 % worst**, and with only two points per position there is no way to tell how much
of that is pointer error.

## §7 ATTACK + GRUNT bleed-free at drive MAX (5 files)

```
drive-1700_level-1700_base-od.wav              <-- the reference; does NOT exist yet
drive-1700_level-1700_attack-boost_base-od.wav
drive-1700_level-1700_attack-cut_base-od.wav
drive-1700_level-1700_grunt-boost_base-od.wav
drive-1700_level-1700_grunt-flat_base-od.wav
```

**Settings:** DRIVE **max**, LEVEL **max**, BLEND **max**, EQ flat, MASTER noon; ATTACK/GRUNT per
filename (the plain reference is ATTACK Flat / GRUNT Cut).

**Why.** We now have the bleed-free LEVEL-max triple at drive **min** (sessions 60–66) and, as of
today, at drive **noon**. Drive max completes the axis. Session 59's finding is what makes it worth
having: **the DRIVE axis trades compression against sensitivity in both directions** — drive min
idles the clipper but buries the OD path 15 dB under the bleed, drive max exposes the path but
compresses the effect away. Drive max is the end where a *pre*-clipper element's effect is squashed
toward zero, which is precisely what made session 59's placement test **90× decisive** (rms residual
0.08 dB pre-clipper vs 7.50 post).

**What it decides.** Session 59 ran that test through the blend-ladder machinery with a fitted taper
and a solved bleed. Bleed-free it becomes a **plain subtraction** — the strongest out-of-sample test
the ATTACK work has, with its machinery removed. The GRUNT pair is the control: GRUNT is
schematic+BOM-verified **linear** but sits at the **clipper input**, so session 65 measured it moving
the operating point (~1 dB on the hot throw) — it bounds how much of any ATTACK reading at high drive
is operating-point rather than network.

## §8 MASTER taper intermediate points (3 files)

```
master-0815_base-clean.wav   master-1100_base-clean.wav   master-1545_base-clean.wav
```

**Why.** Lowest-stakes item here — MASTER is a post-EQ scalar, so it moves no nonlinear operating
point and invalidates no fit. But `masterTaperExp` shipped at 1.998 with a **worst whole-travel error
of 1.95 dB** and per-point exponents that are **non-monotone** (1.929 / 2.322 / 1.734), i.e. no
single power law fits — same as DRIVE and LEVEL. And session 41 found the plugin had been **3 dB too
loud** for 24 sessions partly because *"the taper fit never saw the middle of the knob."* Three files
to stop that recurring.

---

# TIER 3 — speculative, but genuinely irreproducible later. (10 files, ~25 min)

## §9 ⭐ A different-day retake (2 files)

```
retake_ref-od_day2.wav      retake_ref-clean_day2.wav
```

**Settings:** identical to `ref-od.wav` / `ref-clean.wav`, but recorded on a **different day**, after
a full **power cycle** (and ideally a different physical patch of the same interface inputs).

**Why.** Everything in this project is a behavioural match to **one unit, in essentially one
session.** §2's repeatability set measures within-session variation; this measures *between*-session
variation, which is the quantity that actually bounds how much of the four large schematic departures
in §0 could be session artefact. Two files. If they differ from the originals by materially more than
§2's floor, that is a finding in its own right and it recalibrates several confidence claims.

## §10 XLR DI output — a decision, not a request (2 files, optional)

```
di_ref-clean.wav      di_ref-od.wav
```

The balanced XLR DI (IC6_C/IC6_D, sharing IC6_B's node) is **explicitly out of scope** in
`circuit.md` and has never been captured. That is a deliberate choice and I am not asking you to
change it. But it is a choice that becomes **permanent** in ~5 days: the DI cannot be added to the
model later without the pedal. **If there is any chance you will ever want the DI output modelled,
capture these two now** (you would need an XLR→interface input and the ground-lift switch in its
default position). If you are certain you don't want it, skip and I will note it closed forever.

## §11 🔧 96 kHz reference set (6 files, optional)

```
hr96_ref-clean.wav                       hr96_himidfreq-3k_himid-1700_base-clean.wav
hr96_ref-od.wav                          hr96_himidfreq-750_himid-1700_base-clean.wav
hr96_bypass.wav                          hr96_lomidfreq-250_lomid-1700_base-clean.wav
```

**🔧 BLOCKED ON ME** (a 96 kHz stimulus — one constant in `gen_test_signal.py`) **and on your
interface** supporting 96 kHz. Ask me before recording these.

**Why.** **A2e** — the mid stages' HF skirts — is quantified but its element is **unidentified**: the
matched-pair span error grows monotonically above each centre, reaching **−6.03 dB at 16 kHz** on
HI-MID 3k against a ~0 LF plateau. At 48 kHz everything above 20 kHz is invisible, so we cannot see
where those skirts are actually heading — which is the difference between "the model's peak is too
narrow" and "the model has an extra pole up there". A 96 kHz capture shows 20–40 kHz directly. It
would also **independently confirm** session 28's bilinear-warp result, which ruled warp out at
±0.13 dB by *rendering* at 96 k but never *captured* at 96 k. `hr96_bypass.wav` is the mandatory
anchor (see protocol below).

---

# PROTOCOL — the rules that have actually cost us files

Every one of these is here because it went wrong before, not as boilerplate.

1. **⭐ Record a `bypass` take at the START and END of every session** — `bypass_<date>_pre.wav` and
   `bypass_<date>_post.wav`, cables in exactly the recording patch, pedal in true bypass. `bypass.wav`
   is the anchor that proves the capture domain is unity (it round-trips at −0.03 dB and is how
   session 28 proved a sub-60 Hz deficit was the *plugin*, not the rig) and it is the **only** thing
   that pins the chain's latency, which is what any future *phase* measurement depends on. Bracketing
   it makes within-session drift measurable instead of assumed.
2. **One knob at a time.** Every differential method in this project (matched-pair span, pot law,
   bleed-free subtraction) depends on exactly one control differing between two files.
3. **Check LEVEL and BLEND before each take.** Session 54 lost `attack-cut_blend-1430_base-od.wav` to
   **MASTER left at 1430 instead of BLEND** — caught only by a purpose-built geometric test, and the
   first re-capture attempt was *still* wrong. A two-second visual check is cheaper.
4. **No interface clipping.** Session 24 lost **14 files** to the interface's own input headroom (all
   pinned at peak 0.98850). The `gain-n12` token exists solely because of that. If you must drop the
   send, **record a fresh anchor pair (`ref-clean` at both gains)** in the same session — session 22
   found the correction must be measured from **ref-CLEAN, not ref-OD**, because the CD4049's
   compression made the same nominal −12 dB read as −2.857 dB there.
5. **Full length, no truncation.** Every matrix file must be **83.700 s**. Missing segments read as
   zeros and fake features.
6. **⚠⚠ BACK THE CAPTURES UP.** `analysis/captures/` is **gitignored** — every capture from sessions
   53–68 exists **only on this machine**. Flagged at the end of ten consecutive sessions and still
   worth repeating: an external drive or cloud copy, today. Losing them is unrecoverable in a way
   that losing the code is not.

---

# What is NOT on this list, and why

So you can see the coverage is deliberate rather than accidental:

- **The DIST footswitch** — already covered. `base-clean` **is** the DIST-disengaged state (30
  captures), and because they were taken at BLEND **max**, the alternative model ("DIST off just mutes
  the OD path while BLEND keeps crossfading") is already refuted — it would predict silence there.
- **`shape_gate`'s 63 % LOCAL finding**, the `sweep_clean_-36` re-baseline, the A4 re-grade + GATE-9,
  and the `OSValidationTest` decision — all need **analysis, not captures**. `sweep_clean_-36` is
  especially worth noting: it has been present in *every* capture since the first session and simply
  went unread until session 60.
- **The A3 level-trend gap** (pedal +4.43 dB vs model +0.17/+1.28) — read from the five stimulus
  levels already embedded in every capture.
- **`clipSat`'s missing mechanism and the 4049's real rail** — cannot be settled by any audio capture;
  it needs a voltage measurement inside the box. That is what §0 is for.
- **Phase** — measurable in principle from the existing LEVEL-max bleed-free captures plus a
  `bypass` anchor, which is why protocol item 1 matters. No new pedal state required.
