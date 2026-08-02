# Reference Sources — what the captures ARE, and which reference wins where

> **Read this before treating any capture-derived number as "the pedal".** It is the standing
> authority rule for the whole project, not a Phase-9 note. Established 2026-07-29 (session 71).

---

## 0. The fact that changes everything downstream

**`analysis/captures/` is a recording of the Neural DSP Darkglass plugin, not of a Darkglass B7K
Ultra.** Every "the pedal" / "the real pedal" / "the captured unit" statement in `circuit.md`,
`docs/phase9-validation.md`, `docs/phase7-calibration-handover.md`, the memory files and 70 sessions
of `CLAUDE.md` handover means **the Neural DSP emulation**, unless that specific entry says
otherwise. Confirmed by the user 2026-07-29.

This is not a disaster — ND is very close, and §2 quantifies exactly how close — but several
load-bearing project facts read differently once you know it:

| Fact as recorded | How it reads now |
|---|---|
| **0.144 dB "take-to-take floor"** — quoted as the noise floor in ~40 sessions | Not a converter/analogue floor. Against a deterministic renderer it is at most a **knob-repositioning** floor. Treat as an upper bound on repeatability error, not a physical limit. ⭐⭐ **MEASURED, SESSION 112, AND IT IS TWO DIFFERENT NUMBERS.** `drive-1200_gain-n12_base-od.wav` and `ref-od_gain-n12.wav` are the same condition (settings dicts identical) captured four days apart: they differ by **0.010 dB mean, worst band 0.026 dB**, across all four sweeps ⇒ the **RECORDING** side is essentially deterministic, ~14× better than 0.144. But re-setting a knob is not free: the four MASTER detents re-captured in session 111 differ from their archived predecessors by a *flat* offset (sd 0.000 — pure gain, as the topology requires) of **12.000 / 10.455 / 12.612 / 12.330 dB** against a 12.071 send, i.e. up to **1.62 dB** at the steep low end of the taper. ⇒ **quote 0.010 dB for repeatability and ≤1.6 dB for re-dialling; they are not interchangeable, and which one applies depends on whether the knob was touched.** |
| Session 70 **rejected the §2 repeatability set** because five "takes" agreed to −147…−164 dBFS with lag exactly 0, arguing no two analogue re-recordings can agree better than ~−90 dBFS | **That discriminator is invalid.** Five renders of a plugin *can* agree to float32 rounding. The set is probably fine; the rejection should be re-examined before anyone re-records it. |
| `docs/final-capture-window.md` — "the pedal is available for ~5 days, then never again" | ⛔⛔ **RE-INSTATED, SESSION 111 (2026-08-02). THIS ROW WAS VOID; IT IS NOT ANYMORE.** The "unlimited, perfectly repeatable, do not ration" framing held from 2026-07-29 to session 111 — it does not hold now. **The user is losing access to the capture source (the ND plugin) and confirmed this in session 111.** A large capture batch was made in that session specifically because access was ending (full inventory + rationale: CLAUDE.md "Project-specific carry-forwards" → "Capture access status"). ⚠ **Treat captures as scarce again until this row is updated to say otherwise.** If any future session wants a capture that is not already on disk (`analysis/captures/`) or not in the inventory below, that is a BLOCKING question for the user, asked immediately — not deferred, not assumed obtainable "whenever". |
| **§0 PCB photos "declined and closed permanently"**; the four large departures (`trebleC7` 147×, `clipC15` 423×, `c21R` 10×, `R36` 1.42×) as *"fitted to a real unit whose board can never be inspected"* | They are **fitted to another emulation's behaviour.** Still not resolvable by photos — but they are no longer claims about a physical board, and §2/§3 below can partly adjudicate them. |
| Bad-take forensics (session 24's odd-harmonic file, session 54's MASTER-at-1430 file) | Still real — wrong knob in the ND UI, same failure, same fix. Unaffected. |

⚠ If any subset of `analysis/captures/` turns out to be genuine hardware, the first two rows above
go back in play. Nothing else in this file depends on it.

---

## 1. THE AUTHORITY SPLIT (the operative rule)

We now have two references and they disagree in known, bounded ways. **Neither is "the" reference.**

| Domain | Authority | Why |
|---|---|---|
| EQ centres, ranges, switch topology, pot laws | **Captures (ND)** | Clean-path FR agrees with hardware to ≤1.4 dB everywhere (§2), and our capture-measured mid centres (545 / 1090 / 784 / 1613 / 3026 Hz) match the independent hardware measurements (550 / 1.1k / 800 / 1.5k / 2.8k) |
| Broadband linear tilt, LF and HF corners | **Hardware**, captures as fallback | The ±1 dB divergence is systematic, monotone and readable (§2) |
| OD-path low-mids (150–250 Hz) | **Hardware** | ND is 2.8–4.8 dB LOW in every driven condition where the GRUNT caps are in circuit (§3) |
| ~320 Hz cancellation-null DEPTH | **Hardware** | ND's null is shallower in all six measured conditions (§3) |
| **Harmonic structure / clipping asymmetry** | **Hardware, overriding the captures outright** | ND's even-order ladder is **~27 dB low** (§4). This is not a refinement. |
| Absolute level, gain staging, makeup | **Captures** | No hardware anchor exists for it, and ND is level-consistent |
| **OD-vs-clean mixing balance (A3)** | **Captures** | ⛔⛔ **SESSION 112 — ONE CLAUSE FURTHER DOWN THIS ROW IS REFUTED, AND IT IS A CLAIM *ABOUT THE REFERENCE*, SO IT MATTERS HERE MORE THAN ANYWHERE. GATE O5's "ND's clean path is NOT level-invariant across a 12 dB input change (it scales by 12.178, not 12.071)" IS WRONG.** That reading rested on ONE cross-session pair (`ref-clean.wav` vs `ref-clean_gain-n12.wav`), which is also the pair `captures.py`'s send-pad constant was derived from. Session 111's capture batch added four fresh clean twins, and the clean path is LINEAR, so old−new must be flat *and* equal to the send. Measured: `bass-0700`, `treble-0700`, `lomid-0700`, `himid-0700` all read **12.000 dB with a span of ≤0.0003 dB over 29 bands**, against `ref-clean`'s 12.158 / 0.334. ⇒ **ND's clean path IS level-invariant, to 0.0003 dB**, and the 0.334 dB tilt is a property of that one pair, not of the device. ⭐ Corroborated on a second instrument sharing no machinery: GATE N's THD turnover (nonlinear, immune to any record or output gain) returns **12.000 / 12.000 / 12.001** on the three new full-send-twinned DRIVE pairs. ⇒ **the true `gain-n12` send is 12.000 dB, not the harness's 12.071**, and §0's "at most a knob-repositioning floor" is vindicated — measured directly at **0.010 dB** (worst band 0.026) between two captures of one condition four days apart. ⚠ **What SURVIVES from O5:** its model-side known answer (our render is a pure 12.0710 dB shift to 1.8e−08) and its *practice* of correcting per band rather than by a scalar. ⚠ **What must NOT be carried forward:** the attribution, and the derived claim that "no absolute clean-path claim about this reference can ever be resolved better than ~0.3 dB" — that bound was set by the refuted tilt; the *other* half of it (O7's DIST-engage non-transparency, ~0.17 dB) is untouched and still stands. ✅ **CHANGED IN SESSION 114, on the user's "whatever increases accuracy" decision: `captures._GAIN_SESSION_MEASURED_DB[-12]` is now −12.000.** The constant pads the MODEL, so at 12.071 the model was rendered 0.071 dB quieter than the pedal was actually driven on every gain-session capture. New baseline `analysis/reports/s114_baseline.json`. ⭐ The change is **exactly scoped** — against s113 on identical membership, 122 captures are bit-identical on the model side, 40 `gain-n12` moved, **0 non-n12 moved** — and the median worst-band move is **0.0000 dB**, with three outliers (2.27/1.42/1.31 dB) all at DRIVE max × hottest stimulus where a compressing chain amplifies a small input change. ⚠ `comprehensive_report` gain-matches every row, so the matrix is blind to it by construction (headline 2.149 → 2.149); it is a correctness fix for GATE K/M/O/Q's **absolute** ledgers, which are not gain-matched. **Re-quote any absolute figure on a `gain-n12` row against s114.** *(Everything below stands and is unchanged, including A3's size and GATE O's attribution.)* ⭐⭐⭐ **SESSION 109 (GATE Q, `analysis/od_absolute_gate.py`) — THE OD PATH'S ABSOLUTE ERROR IS TWO DEFECTS, AND THE BIGGER ONE IS A *SATURATION* ERROR THAT NO LINEAR ELEMENT CAN CARRY. THIS IS WHY EVERY LINEAR SEARCH SINCE SESSION 50 HAS FAILED.** GATE O made the OD path's own absolute error readable (the clean side is bounded at 0.41 dB), and GATE Q reads it directly off the **15** pure-OD endpoints — BLEND = 1 and LEVEL = 1, where the mix coefficient is exactly 1 (GATE K2) — instead of through GATE M's 4 settings-matched pairs. Split by what it depends on rather than pooled: **L(f)** = the error at the lowest stimulus (a linear element could carry this, **rms 2.72 dB**) and **D(f)** = error(−6) − error(−30) (**rms 3.01 dB**, and only a nonlinearity can carry it). ⭐ **The mechanism, measured three ways that share no arithmetic.** (a) The **compression law**: from −30 to −6 dBFS the model's OD path loses **4.17 / 3.25 / 1.00 dB MORE** than the pedal's over 500 Hz–8 kHz at DRIVE 0 / 0.5 / 1. (b) The **320 Hz null**, referred to each side's own 202/508 Hz shoulders so it is immune to any absolute-level error and to the matrix's gain match: the model's **washes out** with level (9.63 → 4.36 dB) while the pedal's **DEEPENS** (6.00 → 8.06) — a fixed network's null depth cannot depend on stimulus, and compression is what fills a cancellation null. (c) **THD on the same endpoints runs +2.94 dB — the model over-distorts**, the same sign as over-compressing. ⇒ **the model's OD path saturates too early**, and that single statement explains the level deficit, the null behaviour and the THD excess at once. ⛔ **Do NOT read this as contradicting sessions 50/52** — those ruled out single elements and post-clipper LINEAR elements against a pooled residual that contained D. It is the reason they could not succeed, not evidence against them. ⚠ **A3's SIZE (5.1–5.5 dB over 100–400 Hz) and GATE O's attribution are untouched**; what is new is that the deficit decomposes, and that the larger half has a mechanism and a lever. ⚠ Two corrections fall out and both are recorded in the discipline file: the gated **THD "level term" is an UNSIGNED rms** and its signed mean is **+1.263 dB** (the model distorts MORE, not less — `CLAUDE.md`'s prose had the sign backwards for eighteen sessions), and one **(capture, sweep) cell is a reference dropout** — `drive-1700_level-1700_grunt-boost_base-od.wav @ sweep_drv_-12`, worth **+0.055 dB** of the shipped OD headline and the worst single row in the matrix. *(Everything below stands and is unchanged.)* ⛔⛔ **SESSION 108 (GATE P, `analysis/a3_pedestal_gate.py`) — THE 5.1–5.5 dB FIGURE IS NOT WRONG, BUT IT IS NOT A TARGET A STATIC CORRECTION CAN BE FITTED TO, AND EVERY SESSION SINCE 105 HAS BEEN PLANNING TO DO EXACTLY THAT.** Three measured reasons, none of which touches the SIZE or the ATTRIBUTION: **(i)** it is a mean over 100–400 Hz whose two dominant bands are **320 Hz (10.10 dB) and 254 Hz (8.96)** against ~2 dB in the bands either side — a window mean over a peak, not a level; and those two bands are the **least reproducible in the set** (across-pair sd 1.85/1.51 at clean, **5.17**/2.27 under drive). **(ii)** it pools 4 capture pairs that differ in the pedal's **own DRIVE and ATTACK controls**; per pair the same headline spans **4.48–6.68 dB (±1.10 about 5.34)**, a spread never printed, and ~5× the 0.47 dB stimulus-level spread it *is* quoted with. **(iii)** no band is both clear of the feature and agreed on by the pairs — the quiet bands are the ones they disagree on, the agreed bands are on the feature, and **13 of 20 threshold combinations give an empty intersection** ⇒ the pedestal/feature split is **UNMEASURED**, not small. ⭐ Measured consequence: the best a static broadband gain can do is the A3 residual **5.48 → 2.86 dB rms** (48 %, at +4.66 dB over 40–3300 Hz — note **4.66, not 5.1**, the window figure) and it **cannot close A3** — which corroborates session 52's "no post-clipper linear element closes it" through an instrument sharing none of its machinery. ⛔ **Do not fit a constant to 5.1–5.5 dB.** ⚠ §1's own "≈5–7 dB over 100–400 Hz" below is a chart read over the *same window* and inherits the same property; it remains right as a description and must not be used as a fit target either. *(Everything below stands: the size is unchanged and GATE O's attribution is untouched.)* ⭐⭐⭐ **SESSION 107 (GATE O, `analysis/a3_decomposition_gate.py`) — "MIXING BALANCE" IS NOW THE WRONG NAME FOR THIS ROW, AND THAT IS THE POINT.** GATE M's excess regroups from *(model's clean/OD ratio − reference's)* into *(clean path's absolute error − OD path's)*, and the clean side is now **bounded at 0.41 dB against a 5.28 dB deficit (8 %; the deficit is 13× the bound)**, by a ledger that reconstructs the measured clean-side reading to **2e−16**. ⇒ **A3 is NOT a two-sided balance in which either path could be at fault: the OD PATH IS QUIET, ABSOLUTELY, BY 5.1–5.5 dB OVER 100–400 Hz.** ⚠ **A3's SIZE is unchanged** — MASTER is asserted matched within every pair, so it is common-mode and cancels; only the ATTRIBUTION moved. ⛔ **Do NOT quote session 106's "exonerated to 0.007 dB"** — that is the master-unity reading alone, and it sits on a different capture route AND a different capture session from the A3 pairs; **quote 0.41 dB.** ⚠ Two ~0.2–0.3 dB **reference-side** properties were found in passing and are folded into that bound, not into A3: ND's DIST-engage at BLEND min is **not transparent** (our model is, bit-identically, as GATE K2 requires) and ND's clean path is **not level-invariant** across a 12 dB input change (our render is, to 1.8e−08). ⇒ **no absolute clean-path claim about this reference can ever be resolved better than ~0.3 dB.** *(Everything below stands and is unchanged.)* ⭐⭐⭐ **SESSION 105 (GATE M) — READ THIS BEFORE QUOTING ANY A3 NUMBER BELOW.** The "≈5–7 dB over 100–400 Hz" recorded in this row is **confirmed, on a third instrument** (`analysis/a3_balance_gate.py`, the mixing network's two exact-zero endpoints — no fit, no gain match, no model form): **5.54 / 5.38 / 5.07 / 5.14 dB** across four stimulus levels, i.e. **stimulus-independent to 0.47 dB**, and offset-dominated within that band (shape/offset 0.18 under drive). ⭐ So §1's figure is right and IS a level statement **inside its own band**. ⛔ **But session 103's GATE K7 broadband figure is two different things added together and must not be quoted as one:** per band the residual carries **0.47–0.90 of shape per unit offset** on every selection, and splits into **(A)** that stimulus-independent 100–400 Hz level term and **(B)** a **stimulus-DEPENDENT** term at 508–1016 Hz swinging **5.4 dB** with drive, its peak migrating 254 → 640 Hz. K7's mean rising 3.4 → 5.1 dB with stimulus is **the mixture moving, not A3 growing**. ⚠ And K7's shipped headline (3.1–4.9 dB) pools the session-48 `gain-n12` defect as 1 of 5 pairs; excluded it reads **3.4–5.1 dB**. ⛔ **(B) is a separate, unclaimed defect** — do not fold it into A3, and do not aim a static gain at the broadband mean. *(The rest of this row stands and is unchanged.)* A linear-path quantity, where §2 puts ND within ≤1.4 dB of hardware. Measured on the harmonic axis in session 85 at **k ≈ −6.5 dB** (the model's OD too weak vs its own bleed) — see `docs/phase9-validation.md` §4 "THE HARMONIC-AXIS A3 INSTRUMENT IS BUILT". ⭐ **Session 86 corroborated it against the DRIVE axis** (`a3_shape_gate`): on the harmonic axis's own robust order subset all three anchor bands OVERLAP, so the two instruments describe ONE curve — **quote A3 as ≈ 5–7 dB over 100–400 Hz, and do NOT fit a slope to either column** (the intervals are 1.8–9.9 dB wide; compatibility is established, a shape is not). ⚠ Session 85's **k = −10.64 dB at 100 Hz is superseded — quote ≈ −8 dB or not at all**; that band fails the harmonic axis's own order-independence premise (3.23 dB of H2H3-vs-H6H7 split against 0.8–0.9 elsewhere). This is one of the few places the 129-capture matrix has FULL authority, so do not carry the even-order caveats into it. ⭐⭐ **Session 87 re-derived the C1/C2/C3 component budget against that corroborated curve and the corroboration reaches C2 ONLY** — `a3_harmonic_axis.ANCHOR_HZ` **is** `comprehensive_report.THD_ANCHORS` = (100, 200, 400) Hz, so C1 (50/64 Hz) and C3 (20–32 Hz) have **zero** anchors *as currently rendered*. ⚠⚠ **SESSION 88 CORRECTS THE REASON AND THE PROGNOSIS — "and stay single-instrument numbers" DOES NOT SURVIVE.** `THD_ANCHORS` is a property of the **REPORT**, not of the stimulus: `harmonics_at_anchors` samples a **continuous** Farina curve (`idx = argmin|fr − ahz|`) that already spans 0.046 Hz upward in every capture on disk. Measured per-band (`analysis/lf_anchor_gate.py`, known-answer Chebyshev recovery + an 81-capture reference-yield census): **50, 64, 32 and 25 Hz are all READABLE** (extractor error ≤0.58 dB, reference yield 54–63 % against 100 Hz's 69 %) ⇒ **C1 can go 0/2 → 2/2 anchors and C3 0/3 → 2/3, with no re-capture** — only a `THD_ANCHORS` edit and a re-render **with `--no-cache`** (the cache key does NOT hash the anchors, so without it the change is a silent no-op). ⛔ **Only 20 Hz is genuinely unreachable**, because it *is* `SWEEP_F0` and the deconvolution has no reference energy below it — that one band needs a real re-capture. ⚠ And 20 Hz shows why the yield column must never be read alone: its yield is the *highest* in C3 while its extractor error is 5.9 dB, because yield merely counts orders above a floor and the edge artefact is large. What the second instrument does do is **narrow β to [−17.40, −16.95] dB** (the two axes bound opposite sides; the drive axis's own optimum −16.80 is **outside** it), and **the whole of that lands on C3**: C1 moves 0.03 dB, C2 0.20, **C3 2.24**. Re-derived: **C1 +2.69…+2.72 | C2 +3.30…+3.50 (+2.06 on its well-conditioned bands alone) | C3 +4.99…+7.23 dB**, against session 50's +2.68 / +3.20 / +7.86. ⚠ **Never quote a C3 size without the β it was read at**, and note the corroborated curve pushes C3 DOWN where session 51's `r_ped` pushed it UP — both from below 40 Hz, where session 52 measured the blend axis unreliable. **C3's size is OPEN.** |
| 5–6 kHz null | **Neither — unresolved** | Absent from the clean sweep, so drive-dependent; the driven charts disagree between conditions and are PNG reads |

**The one-line version:** *the captures get us into the right region for everything linear; the
hardware data governs anything that comes out of a nonlinearity. Failing to match the captures is
acceptable — and correct — when we are moving toward a documented hardware trend.*

---

## 2. The clean-path anchor (quantitative, usable)

Source: an independent third-party comparison sweep ("DefaultSweep"), four traces — two hardware
pedals (VU2, B7K) and the ND plugin models of both, flat EQ, clean. Total plot span 4 dB.

Reading (HW − ND), hardware = red/green, ND = blue:

| f | HW | ND | HW − ND |
|---|---|---|---|
| 15 Hz | 73.3 | 74.72 | **−1.4** |
| 20 | 73.7 | 74.80 | −1.1 |
| 30 | 74.15 | 74.90 | −0.75 |
| ~65 | — | — | **0 (crossover)** |
| 200 | 75.40 | 75.40 | 0 |
| 800–1k | 75.82 | 75.51 | **+0.32** |
| ~2.7k | — | — | **0 (crossover)** |
| 5k | 75.35 | 75.74 | −0.39 |
| 10k | 75.05 | 75.86 | −0.81 |
| 16k | ~74.9 | 76.02 | **−1.1** |

⇒ **hardware carries a gentle mid-emphasis relative to ND: ±~1 dB, hinged at ~65 Hz and ~2.7 kHz.**
Hardware's own total deviation over the band is only ~2 dB, so the clean path of both is nearly flat.

Three concrete consequences:

1. ✅ **`c21R` HAD gone the wrong way, and was RE-AIMED AT HARDWARE IN SESSION 91 — 220k → 130k**
   (corner 7.2 → 12.2 Hz). This is the first constant in the project shipped *because* of this file,
   and the worked example of §5 rule 2. Hardware is −1.35 dB at 20 Hz re 100 Hz; ND is −0.40; 220k
   put C21 at 7.2 Hz → −0.53, i.e. **matched to ND**.
   ⚠⚠ **The bullet this replaces said "hardware wants ~11–12 Hz ≈ 130–150k". That range brackets the
   right answer but was derived the WRONG WAY — off ONE frequency, and by applying §2's published
   `HW − ND` delta raw, which silently assumes the model sits ON ND.** It does not: measured over
   the 168 CLEAN rows of `s90_baseline129_h1.json`, the model was **already 0.40 dB below ND at
   20 Hz and 0.16 at 30 Hz**, so roughly a third of the move had been made by constants fitted for
   other reasons. The target is `HW − MODEL`. Fitting the raw delta gives **121k and overshoots**;
   fitting the remainder over all three LF anchors gives **133.1k / 11.96 Hz**, E24 **130k**.
   `analysis/c21_hw_anchor.py` does this, with 6 known-answer gates and a `--verify` acceptance
   check that runs against the RENDER. **Agreeing with a recorded range is not evidence the
   derivation was sound.**
   **Measured at 130k** (129 captures, 504 rows, membership identical): worst remaining error vs §2
   **0.70 → 0.17 dB**; OD improves on *every* gate row (band-RMS 2.697 → 2.652, OD 25–100 Hz median
   1.13 → 1.03, THD level 6.20 → 6.16) because the OD path's LF ran hot vs ND — the A3/GAP #3
   symptom — and this pulls it down; CLEAN pays median 0.23 → 0.26 and p90 0.77 → 0.82, confined to
   25–100 Hz. No row worse by >0.5 dB. `bypass.wav` bit-identical in all 4 sweeps (inert by
   construction — the known-answer control). 150k was also rendered and **rejected**: it takes only
   55 % of the move and is outside what either individual §2 anchor asks for (139k @20 Hz, 116k
   @30 Hz), i.e. chosen to protect a gate row rather than supported by the reference.
2. **A2e's flat-EQ half is already leaning the right way.** Our plugin reads −0.29 dB @10k /
   −0.38 @16k *below* the ND captures, and hardware is 0.8–1.1 dB below ND there. **Lean further
   toward hardware, do not correct back toward the captures.** (A2e's real item — the mid-boost
   skirt, −6.03 dB @16k at HI-MID 3k — is untouched by this and still open.)
3. **ND's ripple above 6 kHz is an artefact** (75.88 @7k, 76.04 @13k, 76.02 @18k, in a 4 dB window).
   Do not model it. If a fit ever wants HF ripple, it is chasing ND's oversampling filter.

Also noted: the ND plugin gives **both** its pedal models (VU2 and B7K) the same flat-EQ response —
the "Plugin VU2" trace sits exactly under "Plugin B7K". Treat ND's model-to-model differences as
less trustworthy than its absolute response.

---

## 3. Driven-condition FR divergences (directional, not fit-grade)

Source: six ATTACK/GRUNT overlay charts, hardware vs ND, at drive. Positions inferred and
**self-checked**: charts 2 and 5 are the same curve to the pixel (both switches at reference), which
pins Attack = {Cut, Flat, Boost} for 1/2/3 and Grunt = {Cut, Flat, Boost} for 4/5/6.

| Region | HW vs ND | Maps onto |
|---|---|---|
| **150–250 Hz** | HW **+2.8 to +4.8 dB** in every condition — and **exactly 0 dB at GRUNT cut** | A3 / GAP #3b |
| ~305–320 Hz null | HW deeper in **all six**: +1.6 (grunt cut) → +3.5/+3.8/+4.8 → **~26 dB at grunt boost** | GAP #2 / the ATTACK notch |
| 2–2.5 kHz | ND **+1.4 to +2.8 dB** hotter | new, small |
| 5–6 kHz null | Inconsistent — ND ~11 dB deeper at Attack cut, HW far deeper at Grunt cut | session 30's 5.1–6.4 kHz collapse; session 69's 4064/6451 sign dipole |
| LF null position | Grunt boost: HW at **18 Hz**, ND at **35 Hz**. Attack boost: same freq (~43 Hz), ND ~10 dB deeper | A3's migrating null |

⚠ **Read the 150–250 Hz row precisely.** It is not "GRUNT has extra bass" — it is present in every
driven condition, it is **zero at GRUNT cut** (where C12/C13 are out of circuit), and it is **zero on
the clean sweep** (§2 has both at 75.40 dB at 200 Hz). ⇒ it is an **OD-path low-mid** difference
gated by the GRUNT coupling, of which grunt-boost is merely the most extreme case. That is the same
region as A3 and GAP #3b, and it means **hardware wants MORE low-mid OD than ND does, and our model
already under-delivers vs ND.** The two corrections compound; they do not fight.

⭐⭐ **SESSION 110 (GATE R, `analysis/null_locus_gate.py`) — A PROPERTY OF **ND** AT THE ~320 Hz NULL
THAT ANY FIT AGAINST THESE CAPTURES MUST KNOW: ND's NULL DEPTH IS LEVEL-DEPENDENT, AND NO FIXED
LINEAR NETWORK CAN REPRODUCE IT.** Measured bleed-free (BLEND = LEVEL = 1, where the mix coefficient
is exactly 1 — GATE K2), on the 15 pure-OD endpoints, as a 1/6-octave power-integrated deficit
referred to the null's own 202/508 Hz shoulders. At DRIVE 0 and 0.5 ND's null **washes out** with
stimulus (+5.61 / +4.69 dB from the quietest sweep to the loudest), exactly as our model's does and
exactly as a cancellation feeding a compressor must. At **DRIVE max it reverses and DEEPENS**
(4.99 → 12.37 dB, i.e. −7.38). ⇒ **quote ND's null behaviour per DRIVE, never pooled** — GATE Q's
recorded "the reference's null deepens with level" is the DRIVE-max rows only, and pooling over
DRIVE turned a switch-dependent property into an apparent device property. ⚠ A cancellation whose
depth GROWS with level cannot come from a fixed network at any position, so this is not a
"the null is in the wrong place" difference and must not be fitted as one: session 110 rendered
both obvious candidates (a global saturation change, and relocating our post-clipper notch to
320 Hz) and **neither closes it** — the second lands ND's *driven* depth to 0.42 dB while
overshooting the quiet end by ~17 dB. ⚠ n = 5 captures at one DRIVE setting: located, not
characterised.

⛔ **These are PNG reads. Use them for SIGN and rough SIZE only.** They are a veto and a direction,
never a fit target. Do not run an optimiser against a number in this section.

---

## 4. The harmonic finding — this is the big one

Source: three spectrum overlays, hardware @997 Hz (green) vs ND @800 Hz (white), ATTACK and GRUNT
flat, three drive settings. Levels **relative to the fundamental**:

| | **low drive** HW / ND | **mid drive** HW / ND |
|---|---|---|
| H2 | **−22.5 / −42** | **−12 / −39** |
| H3 | −41 / −42 | **−12 / −12** |
| H4 | −60.5 / −57 | **−24 / −52** |
| H5 | −75.5 / −71 | **−24 / −24** |

**At mid drive the odd harmonics match to the dB (H3 −12 both, H5 −24 both) and the evens are offset
by 27–28 dB.** Hardware's evens sit at the level of its adjacent odds (H2 = H3, H4 = H5) — the
textbook signature of a symmetric clipper plus a genuine offset/asymmetry. ND has essentially **no
even-order mechanism.**

This splits the project's nonlinear work cleanly:

- ✅ **The odd-order half is fitted to a correct target.** Session 13's phase-aware analysis, session
  15's `jfetExpandBeta` expansive odd core, the whole H3-sign investigation — all odd structure, and
  ND's odd structure matches hardware. **That work stands. Do not re-open it on this basis.**
- ⛔ **The even-order half is fitted to a target ~27 dB low.** Sessions 5–7's even-harmonic ladder,
  and session 44's fitted asymmetry (`clipSatLo` 0.4377 / `clipSatHi` 0.5979 = 1.37×;
  `jfetSatPos` 0.4559 / `jfetSatNeg` 0.7605) were all chasing an emulator with no asymmetry.
  Session 7's standing bound — a monotone map with a quadratic even part caps H2/H1 at −12.04 dB —
  is **exactly where hardware sits at mid drive**. We were never going to reach it fitting to ND.

⚠ One correction to the source's own summary ("hardware early harmonics, software late"): that holds
only at **low** drive, where ND's H4/H5 run 4–5 dB above hardware's. At **mid** drive hardware has
the *longer* series (out past H20 at −78 re fundamental) while ND's dies after H5. At **high** drive
ND shows dense inharmonic content that reads as **aliasing**, not harmonics.

⚠ **And that low-drive H4/H5 difference is largely THE TONE, not the device** (measured session 72):
the two columns were taken at different fundamentals (HW 997 Hz, ND 800 Hz) and this chain's 2nd
Sallen-Key sits at ~3.3 kHz, so a HW-column harmonic is filtered **H2 −3.2 / H3 −4.9 / H4 −6.7 /
H5 −8.1 dB** harder than the same order in the ND column. HW's H4 reading 3.5 dB below ND's sits well
inside that. **Correct for the tone before reading any cross-column late-harmonic gap as a device
difference.**

> ⭐⭐ **MEASURED AGAINST OUR PLUGIN, SESSION 72 — AND IT SPLITS BY DRIVE. Read this before acting on
> "the even-order half is aimed at a target ~27 dB low".** `analysis/harmonic_ladder.py`, anchored on
> the ODD orders (where the two references agree, so no drive/level guess is needed) and scored on
> **even-minus-adjacent-odd** (so this chain's own known-too-deep mid scoop cannot contaminate it):
> - **At MID drive we already deliver hardware's asymmetry, not ND's** — H2−H3 = **−1.7 / −1.5 dB**
>   at 997/800 Hz against ND's −27 and HW's 0, i.e. **94 %** of the way to hardware at both tones
>   (H4−H5: 99 % / 112 %). ✅ **Session 44's fitted asymmetry did NOT inherit ND's symmetry — do not
>   re-open it on that premise.**
> - **At LOW drive we DO sit at ND** — H2−H3 = **+0.4 / +2.3 dB** against hardware's **+18.5**, i.e.
>   2–12 %. Hardware is strongly even-dominant while the clipper is barely working; we are not.
>
> ⇒ the even-order item is **low-drive-specific**, and its natural carrier is the **J201 stage**
> (upstream of the DRIVE pot, so it never idles — session 59 item 3), *not* the clipper, which is
> near-linear there. Any candidate must be gated on **leaving mid drive alone**. Full detail:
> `docs/phase9-validation.md` §4 "HARMONIC LADDER".
>
> ⭐⭐ **SESSION 73 GATED THAT CARRIER AND IT IS CONFIRMED BUT INSUFFICIENT — read this before
> proposing an even-order correction.** A pre-registered pivot gate passed all five arms, and the
> mechanism is now localised precisely: it is the J201's **small-signal quadratic `a/2`
> (`jfetSatNeg`)**, with `jfetSatPos` and `jfetCeil*` shown **exactly inert (0.00 dB)** at low drive,
> as the small-signal algebra requires. ⛔ **But hardware's low-drive target is NOT reachable from it:
> the required selectivity is 5.72× and the best available 5.43×, declining as the lever is pushed
> (robust at every mid-drive tolerance from 2 to 5 dB).** ⭐ What exists instead is a **genuine
> interior optimum at `jfetSatNeg` ≈ 4.0–5.6 (worse on both sides), ~7.9 dB better than shipped across
> all four HW statistics — while the only point that DOES reach the low-drive target is WORSE THAN
> SHIPPED**, because it wrecks mid-drive H4−H5. ⚠ And the **physically coherent** form of the move
> (honouring `2·a·cn = 1`, which holds exactly at the shipped point) is **jointly infeasible** — 3 of
> 4 candidates fold back into a rectifier. ⇒ a correction here must choose between that corroboration
> and the correction, and **nothing was proposed for shipping**; the 104-capture ND matrix has not
> judged it and, per §1(0), must regress. Detail: §4 "J201 EVEN-ORDER PIVOT GATE".

> ⛔⛔ **SESSION 78 — THE NUMBERS IN THIS SECTION ARE DEMOTED. DO NOT SCORE A CANDIDATE AGAINST THEM.**
> The chart's H2−H3 / H4−H5 columns were tested against the real ND device at **the chart's own tone
> and its own stated operating point**, and they do not survive it. Read this before using any figure
> above as a target.
>
> **The instrument.** `analysis/nd_tone_ladder.py` reads the **1 kHz level ladder** (`lvl_-36 … lvl_-3`)
> that `gen_test_signal.py` has written into every capture since the first capture session and that
> `comprehensive_report.py` never reads for harmonic structure. 1 kHz is the chart's **HW tone
> (997 Hz) to 0.3 %**, and — the load-bearing part — **at a 1 kHz fundamental H2 and H3 land at 2 and
> 3 kHz, close together on ND's mid plateau, so the H2−H3 filter correction `g(3f) − g(2f)` is
> SMALL** — **+0.56 dB**. The swept 100/200/400 Hz anchors the project had been using need **14 dB**,
> and their bridge to the chart's 800 Hz tone is **−9 … −24 dB and capture-dependent**.
>
> > ⚠⚠ **CORRECTED IN SESSION 79 — session 78 recorded that correction as −0.02 dB and BOTH halves of
> > that figure were wrong, though its conclusion survives.** (a) It was measured on the **blended**
> > output FR. A harmonic is generated at the clipper and reaches the output **only down the OD path**;
> > the clean bleed carries none, and H2−H3 is a difference of two Hn/H1 ratios so H1 — the one thing
> > the bleed contributes to — cancels exactly. Read off a blended capture, the bleed **fills the
> > recovery bridged-T's scoop that the 1 kHz fundamental sits in** and the slope collapses to −0.07 dB
> > and changes sign. Measured on the 15 captures that are bleed-free BY TOPOLOGY (BLEND = LEVEL = max,
> > session 59 item 6), it is **+0.56 dB**. (b) The correction was applied with the **wrong sign**
> > (`out − c23`, which *doubles* the chain's tilt instead of removing it; `gen = out + c23`) — harmless
> > at −0.02 dB, a real 2·c23 error at +0.56. Both are now pinned by gates: GATE 3 prints the blended
> > figure as a labelled CONTROL, GATE 3b checks the sign against a closed-form case.
> > ⇒ ND's mid-drive H2−H3 moves **−12.5 → −11.9 dB** (30 captures), so |Δ| to chart ND is **15.1** and
> > to chart HW **11.9**: **still contradicts both, and still ~midway.** The session-78 H2−H3 verdict is
> > unaffected. ⚠ **But the mid-drive H4−H5 verdict DOES change**: its correction moves −3.82 → **−3.16**
> > and, more importantly, its spread **tightens from −9.99…+0.03 to −4.39…−2.55** on the bleed-free
> > transfer, so corrected H4−H5 = **+2.2 dB** and now reads *consistent with chart HW only* (|Δ| HW 2.2,
> > ND 30.2) rather than session 78's *contradicts both*. Treat that as a better-determined but still
> > WEAKER read: the measurability guard drops 3 of 30 and biases H4−H5 downward, and the full-chain
> > stand-in is worst at 4f/5f where the Sallen-Keys are rolling off. **Quote H2−H3.**
> > ⚠ Standing limitation on both figures: the correction uses a **full-chain** FR as a stand-in for the
> > **post-clipper** transfer a harmonic actually sees, so treat ~1 dB as its accuracy, not exact.
>
> **The result**, anchored on H3/H1 exactly as the chart defines its own operating point, first upward
> crossing only (H3 is non-monotone in level on the reference too — it peaks before the last level in
> **68 of 76** captures):
>
> | chart condition | ND measured H2−H3 | 10–90 spread | chart ND | chart HW |
> |---|---|---|---|---|
> | **mid drive** (H3 = −12 dB), 30 captures | **−11.9 dB** | −23.9 … −7.4 | −27.0 | 0.0 |
> | low drive (H3 = −42 dB), 24 captures | +10.1 dB | −1.8 … +18.1 | 0.0 | +18.5 |
>
> > ⭐⭐ **SESSION 79 — AND OUR OWN MODEL IS NOW ON THIS AXIS, WHICH CHANGES A STANDING GATING RULE.**
> > `nd_tone_ladder.py --model` renders our plugin at each capture's own condition and compares
> > cell-by-cell. The two sides' filter corrections are **+1.48 dB (model) vs +0.56 (ND) ⇒ net 0.92 dB**,
> > so the comparison is essentially correction-free — and the model's +1.48 independently corroborates
> > `harmonic_ladder.py`'s render-based **+1.18 dB** at 997 Hz (like-for-like: both are our chain at
> > blend/level max). Anchored on each side's own H3/H1 crossing:
> >
> > | anchor | ND | **our model** | d = model − ND | 10–90 of d | chart HW |
> > |---|---|---|---|---|---|
> > | low drive (H3 = −42) | +10.12 | **+1.42** | **−7.93** | −12.05 … −3.51 | +18.5 |
> > | mid drive (H3 = −12) | −11.51 | **−1.33** | **+10.94** | +5.86 … +22.31 | 0.0 |
> >
> > ⚠ The ND column here (−11.51 / +10.12) differs slightly from the table above (−11.9 / +10.1)
> > **because the membership differs, not the measurement**: this is the median over only the captures
> > where BOTH sides reach the anchor (16 mid, 22 low), against 30 / 24 reference-only
> > (`aggregate-moved-check-membership-first`). Pairing is the point — see below.
> >
> > **Both signs are robust** (each 10–90 interval excludes zero), and they are **OPPOSITE** — so the
> > pooled cell-matched figure (−2.9 dB over 629 cells) is a MIXTURE that cancels ~7.9 dB of real error
> > and **must not be used as a gate**. The tool detects the sign split and refuses to summarise.
> >
> > ⭐⭐ **THE CONSEQUENCE: "an even-order correction MUST regress the ND matrix" IS ONLY TRUE AT MID
> > DRIVE.** That expectation (§1(0), repeated as sessions 72(a) / 73(6) / 76(7)) assumed the model
> > already sits AT ND on this statistic at low drive — session 72 measured "2–12 % of the way from ND
> > to hardware" using the chart's ND column of **0.0**. Measured, ND's own low-drive H2−H3 is **+10.1**,
> > and our model is **+1.4** — i.e. **on the far side of ND, ~−104 % rather than +2 %.** So at low drive
> > the first **~7.9 dB** of the correction moves toward **both** references at once and should **IMPROVE**
> > the 129-capture matrix. At mid drive the model is already **88 %** of the way from ND to hardware
> > (session 72's 94 %, recomputed against measured ND — its finding survives), so there the regression
> > expectation stands. **Gate the two drive regimes separately, and expect opposite matrix signs.**
> > ⚠ Not claimed: this is model vs ND, so "matching ND" is not the target on an even-order statistic —
> > what it gives is the size and sign of our departure from the column the matrix encodes.
> >
> > ⭐⭐ **SESSION 80 SPENT THAT FREE MOVE, AND IT IS A LOCATED CANDIDATE — `jfetSatNeg` ≈ 1.9 … 3.0.**
> > `analysis/even_low_screen.py` sweeps the J201 small-signal even coefficient on this axis, gated at
> > both anchors SEPARATELY (there is deliberately no combined column, for the sign-split reason above),
> > with the shipped point reproducing the session-79 record to **0.00 dB** before anything was ranked:
> >
> > | `jfetSatNeg` | d(low) | d(mid) | selectivity |
> > |---|---|---|---|
> > | 0.76054 (shipped) | **−7.93** | **+10.94** | — |
> > | 1.2 | −5.47 | +11.53 | 4.15× |
> > | 1.9 | −2.38 | +12.40 | 3.81× |
> > | 3.0 | +1.61 | +13.46 | 3.79× |
> > | 4.5 | +5.15 | +14.94 | 3.27× |
> >
> > **d(low) crosses zero at `a` ≈ 2.56 and is worse on BOTH sides** (non-degeneracy), and the two
> > controls — `jfetSatPos`, `jfetCeilNeg` — move it by **−0.45 / +0.28 dB**, i.e. the mechanism is the
> > small-signal quadratic exactly as session 73's algebra requires. ⭐ **This is the first even-order
> > candidate in the project that costs nothing against EITHER reference at its own anchor**, and it is
> > the statistic session 73 declared unreachable — reachable now because the REQUIREMENT changed, not
> > the lever: session 73 needed +17.2 dB at 5.72× to reach the chart's HW column, against measured ND
> > it needs +7.9 dB, which 3.8× delivers. ⛔ **Not proposed** — the 129-capture matrix has not judged
> > it (expect the two-signed result above), it breaks the `2·a·cn = 1` square-law identity that holds
> > exactly at the shipped point, and the pair statistic is blind to **H4**, where the model already
> > sits **+4.3 dB ABOVE** ND at this anchor so the same lever improves H2 and worsens H4.
> >
> > ⭐⭐ **SESSION 81 RAN THE 129-CAPTURE MATRIX ON IT, AND THE FREE MOVE IS SMALLER THAN THE LADDER
> > IMPLIED.** `matrix_harmonics.py` gained a drive-regime split binned on the REFERENCE's own H3/H1 —
> > the anchors' own coordinate — and **forced bleed-free**, because on the mixed-BLEND population the
> > clean bleed shifts that coordinate by **8.8 dB** (median −34.8 vs −26.0) and a genuinely hot cell
> > then lands in a "low-drive" bin purely because A3 diluted it. Median `model − ND` on **H2**:
> >
> > | reference H3/H1 | n | ship | `a`=1.9 | `a`=2.0 | `a`=3.0 | `a`=4.0 |
> > |---|---|---|---|---|---|---|
> > | ≤ −42 (LOW) | 22 | **−6.54** | **+0.53** | +0.92 | +4.42 | +6.90 |
> > | > −12 (MID) | 20 | +2.03 | +4.26 | +4.50 | +6.61 | +8.07 |
> >
> > ⭐ **The sign reversal reproduces on an instrument sharing no machinery with the ladder** (ship's
> > H2−H3 runs −2.61 at the low bin to +4.66 at the mid), and the two agree on the LEVER's size — the
> > ladder moves d(low) +5.55 dB at `a`=1.9, the matrix +7.74 at `a`=2.0. ⛔ **But in the matrix's own
> > output domain the low-drive H2 deficit is 6.5 dB, not the ladder's 9.7** — tone-dependent (H2 lands
> > at 200–800 Hz here, 2 kHz there), and **the matrix's domain is the one a regression check is asked
> > in.** So the free move is spent by **`a` ≈ 1.81** (interpolated crossing), `a`=1.9 lands H2 on ND at
> > +0.53, and **`a`=3.0 overshoots by 4.4 dB.** ⇒ session 80's "admissible 1.9 … 3.0" narrows to
> > **`a` ≈ 1.8–2.0 at the EDGE of free**, and the 1.9-vs-3.0 question is settled against 3.0.
> > ⚠⚠ **The POOLED paired bootstrap cannot see this** — 1.9, 2.0 and 3.0 are all statistically
> > indistinguishable from shipped (only `a`=4.0 is significant, +0.81 dB on the authoritative odd
> > column). Pooling averages the one bin where headroom is being spent with five where the model is
> > already past ND. **Gate on the split, not the total.**
> >
> > ⭐⭐ **SESSION 82 — THREE OF THE SEVEN RENDERS HAD NEVER BEEN READ, AND THEY MOVE TWO OF THOSE
> > NUMBERS.** `a` = 2.5, 3.5 and 5.6 were on disk at 129 captures the whole time
> > (`check-for-unread-data-first`, fourth occurrence). Baseline verified first: session 81's
> > five-report run reproduces with **0 differing leaves**, membership unchanged.
> > **(a) ⛔ THE POOLED ACCEPTANCE TEST DEFINES NO FREE REGION — IT IS NON-MONOTONE IN `a`.** A ninth
> > render (**`a`=1.3**, made this session to bracket the crossing) shows **1.3 is SIGNIFICANT on the
> > authoritative odd column (+0.35 [+0.03,+0.72]) while 1.9, 2.0, 2.5, 3.0 AND 3.5 are not.**
> > Significant = {1.3, 4.0, 5.6}. ⭐ Mechanism: odd Δ dips in the middle (+0.35 → … → +0.16 at 3.0 →
> > … → +1.34) while the **CI width grows monotonically 0.69 → 2.05** — significance tracks
> > *coherence across cells*, not size. ⇒ **"significant / not significant" cannot be read as
> > "costly / free"**; this is session 81 item (6)'s warning shown as a shape property of the
> > statistic. **Gate on the split, not the total.** ⚠ Only **5.6** is robustly significant (all three
> > groups); 1.3 and 4.0 are marginal (odd CI lower bounds +0.03 / +0.04); **2.5 and 3.5 are as
> > indistinguishable from shipped as 1.9 and 2.0**, so the matrix does not penalise 3.0 or 3.5 ⇒
> > read "3.0 overshoots" precisely: it overshoots **ND's own H2 at the low anchor**, and costs
> > **nothing measurable**. Two different claims.
> > **(b) THE CROSSING IS MEASURED AT 1.77, AND A PREDICTION HELD.** Session 81 read it off the
> > shipped→1.9 chord — **1.14 wide with no render in it**, and the steepest segment of the curve.
> > Before `a`=1.3 landed, concavity predicted the true crossing would fall **below** 1.81;
> > **measured 1.77**, now bracketed 1.30→1.90. Local slope **+8.41 → +4.22 → +3.93 → +3.84 → +3.15 →
> > +2.66 → +2.31 → +1.82** falls at all eight segments, so 1.77 is still an **upper bound**, just a
> > tight one. Per-band-value crossings: **20 of 22, median 1.81, 10–90 1.08 … 2.07** (the 2 that
> > never cross are the `grunt-flat` GAP #3b rows). ⇒ **quote `a` ≈ 1.8, not a point estimate.**
> > ⭐ Robustness is stronger than recorded: **22 of 22 band values strictly increase in `a` at every
> > step**, not "20 of 22 at `a`=2.0".
> > ⚠⚠ **(c) AND THE BIN LABEL IS THE H2 COUNT ONLY.** In the low-drive bin the per-order support is
> > **H2 22 | H3 17 | H4 5 | H5 1 | H6 1 | H7 1.** So session 81's H6/H7 "contaminated" cells are
> > **n = 1**, and — the load-bearing one — **H4-low is n = 5, spanning 31.5 dB with trajectories that
> > disagree in sign**, which is what makes it non-monotone once you have eight points. ⇒ **the
> > matrix's half of the open H4 disagreement (ladder +4.3 ABOVE vs matrix −6.85 BELOW) is far more
> > weakly supported than the handover implies — do not quote the two at equal weight.** H2 is
> > unaffected and monotone in every bin.
> >
> > ⛔⛔ **SESSION 83 — AND THE LADDER HALF DOES NOT SURVIVE EITHER, SO THERE IS NO H4 DISAGREEMENT
> > LEFT TO ADJUDICATE. Stop treating this as an open question between two instruments.** The
> > ladder's H4 row had never been guarded (`even_low_screen.py`'s anchor subsets select on `ok23`
> > and never consult the `ok45` they compute), but the obvious suspicion — that it was floored —
> > is **refuted**: the reference's H4 clears its own residual in **21 of 22** low-anchor cells and
> > **16 of 16** mid, and the model's in **22/22**. What kills it instead is DISPERSION: the
> > per-cell `d(H4)` runs **−18.1 … +23.8 dB, 41.9 dB wide**, and dropping the single unmeasurable
> > cell moves the median **1.4–1.9 dB**. ⇒ the matrix half is THIN (n = 5, 31.5 dB) and the ladder
> > half is DISPERSED (n = 21, 41.9 dB), and **the ~11 dB gap between the two is smaller than
> > either instrument's own spread** — two weak summaries of one badly-dispersed quantity, not a
> > contradiction. ⭐ What survives is the **TREND**: H4 rises monotonically in `a` under both the
> > guarded and unguarded reads and at BOTH anchors (low guarded +2.43 → +2.55 → +3.06 → +4.32 →
> > +6.35 across `a` = ship/1.2/1.9/3.0/4.5), so session 80 item (5)'s *direction* — the lever
> > improves H2 and worsens H4 — stands. **Quote the direction; never the level.**
> > `matrix_harmonics.py` now prints per-order `n` on every split row and flags rows under 10, so
> > the H4 row can no longer be read as if it had the header's H2 count.
> >
> > ⭐⭐ **SESSION 83 — AND THE OTHER HALF OF SESSION 82's NEXT STEP: `2·a·cn = 1` IS NO LONGER A
> > CHOICE AGAINST THE CORRECTION.** Session 73 recorded the identity-honouring family as JOINTLY
> > INFEASIBLE, and sessions 80–82 carried that as "a proposal must CHOOSE between the corroboration
> > and the correction". **It does not survive**, for two reasons that are not re-measurements of the
> > shaper: (a) it was scored against the CHART's **+17.2 dB** requirement, since demoted (session 78)
> > and remeasured at **7.9 dB** vs ND (79) and **6.5 dB** in the matrix's own domain (81), spent by
> > `a` ≈ **1.77–1.81** (82); and (b) its feasibility test was a 4-point Vov grid that only BRACKETED
> > the fold-back boundary in `a` ∈ [1.667, 3.333]. ⭐ Located exactly — **`a` ≤ 1.7709 at shipped
> > `s`**, validated to 5 dp against a finite-difference of an independent transcription of
> > `JfetStage.h`. ⭐ **And the cap is on the PRODUCT, not on `a`: `a·s ≲ 0.80`, against `< 2.598`
> > unconstrained — the identity costs a 3.25× tighter fold-back budget** (reproducing session 44's
> > recorded 0.80–0.95 β-dependent figure; `cp` has no influence at all, so `cn` is the binding side).
> > ⇒ session 73's `a` ≈ 5.7 needed `a·s` ≈ 2.6 = **3.25× over budget**; the corrected requirement
> > needs `a·s` ≈ 0.82 = **~2 % over**. ⭐⭐ **And it is free in practice, not just affordable:**
> > `SQ a=1.9 s=0.40` (identity exact) reads d(low) **−2.28** / d(mid) **+12.40** against the free
> > `a`=1.9's **−2.38 / +12.40** — 0.10 dB and 0.00 dB apart despite tightening `cn` 2.5× — and it
> > **wins the screen's computed verdict** (by 0.10 dB, i.e. indistinguishable, not better). Even at
> > shipped `s`, `SQ a=1.75` closes **62 %** of the low-drive gap. ⚠ **Still NOT proposed** — the
> > 129-capture matrix has not judged either point, and §1(0) still requires the two drive regimes to
> > be reported separately and never pooled. ⚠ The cap (1.7709) and the measured crossing (1.77) agree
> > to 0.1 %: that is a **COINCIDENCE** — waveshaper algebra vs a measurement against ND captures,
> > sharing no machinery — and the argument above rests on the `a·s` budget, not on it.
> >
> > ⛔⛔ **SESSION 84 — THE 129-CAPTURE MATRIX HAS NOW JUDGED THE IDENTITY, AND "FREE IN PRACTICE" DOES
> > NOT SURVIVE IT. This is the §1 authority split doing exactly the work it exists for, so read it
> > before quoting session 83's 0.10 dB.** Baseline verified to the leaf first (927 shared leaves, 0
> > differing, membership unchanged); free `a`=1.9 was **already on disk** so only the identity point
> > needed rendering; the SQ point was confirmed **monotone** before its render was read (and
> > `SQ a=1.9` at *shipped* `s` confirmed to fold back, which is why `s` moves). Paired medians of
> > `(candidate − shipped)` per cell, on the rows with real support:
> >
> > | regime | order | n | free `a`=1.9 | **`SQ a=1.9 s=0.40`** | authority per §1 |
> > |---|---|---|---|---|---|
> > | LOW (H3/H1 ≤ −42) | H2 | 22 | +7.92 | **+8.15** | **NONE** — ND ~27 dB below hardware |
> > | LOW | **H3** | 17 | **−0.10** | **−3.27** | **AUTHORITATIVE** — ND == hardware |
> > | MID (H3/H1 > −12) | H2 | 20 | +2.28 | **+2.63** | NONE |
> > | MID | **H3** | 20 | **−0.66** | **−1.44** | **AUTHORITATIVE** |
> > | MID | H5 | 20 | −0.75 | −0.80 | **AUTHORITATIVE** |
> >
> > ⇒ **the identity buys a fraction of a dB on the column that carries NO authority and pays a
> > multiple of it on the one that does, in BOTH regimes.** Directly paired against the free move it is
> > **+0.23 dB bought for −1.45 dB paid** at the low anchor (**+0.30 / −0.42** at the mid), coherent
> > across cells (14/17 and 17/20 same-signed, so not a median hop — checked, because the adjacent bin
> > moves the other way), heavy-tailed (paired mean −5.37 / −2.71), and **concentrated at drive MIN**
> > (n=11, paired median −4.27, worst −24.79) where the clipper is idle and the J201's own map
> > dominates. ⭐ Mechanism: the identity forces `cn` down 2.5× as `a` rises, which moves the
> > cutoff-side compression knee **4.6× closer to the origin** (|w| at slope<0.10: 1.90 → 0.41) — so
> > the extra even-order content and the odd-order suppression are **two faces of one mechanism**, not
> > effects that could be traded apart.
> > ⭐⭐ **AND THE SCREEN COULD NOT HAVE SEEN THIS — it ANCHORS on H3/H1, so H3 is pinned BY
> > CONSTRUCTION** (session 80 item 4a, which is why its odd control was vacuous). The identity's cost
> > lands exactly on the quantity that anchoring makes unobservable. **A candidate that scores "free"
> > on H2−H3 must be re-scored PER ORDER before that is believed.**
> > ⚠ What still stands from session 83: the identity is **AFFORDABLE** (session 73's joint-infeasibility
> > verdict has expired, and the `a·s` budget is 3.25× tighter but reachable). What falls is only
> > **"free"**. ⚠ Nothing proposed; this does not select free `a`=1.9 either. ⛔ The pooled bootstrap
> > calls SQ **not significant in every group** (odd +0.44 [−0.37,+1.26]) — a third demonstration that
> > it ranks nothing; and THD *prefers* SQ, which is session 82 item (6)'s amount-vs-shape artefact a
> > third time. **Gate on the split, per order, per regime.** Detail: `docs/phase9-validation.md` §4
> > "SESSION 83's NEXT-STEP (a)".
>
> ⇒ **at mid drive NEITHER column lies inside the measured range** — the chart's ND column is out by
> **14.5 dB** and its HW column by 12.5 dB, on the chart's own tone with a ~0 dB filter correction. At
> low drive the spread over conditions (19.8 dB) **exceeds the entire HW-vs-ND separation** (18.5 dB),
> so that statistic cannot discriminate the columns at all.
>
> ⭐ **And "the two columns agree" is NOT evidence that either is right.** At low-drive H4−H5 the two
> columns agree to 1.0 dB (+14.0 / +15.0) — the case sessions 76/77 treated as *authority-free* and
> corroborated — yet ND's own device reads **≥ +16.9 dB** there (a one-sided bound: the measurability
> guard drops exactly the cells with large H4−H5, biasing the survivor downward). The columns can
> share an error, which session 77 item (7) had flagged as possible and is now measured.
>
> ⭐⭐ **AND NO CAPTURE CAN FIX THIS, because the chart under-specifies its own operating point by more
> than the quantity in dispute.** With H3 pinned to the chart's value **and** the DRIVE knob pinned,
> ND's own H2−H3 still spreads **7.8 dB (mid) / 18.4 dB (low)**; the chart states no blend, level, EQ
> or switch condition. ⇒ session 77's next-step (a) — "capture ND hot enough to reach H3/H1 ≈ −12 dB" —
> was aimed at the wrong obstacle: that operating point is already present **153 times** in the tone
> ladder and 20 times on the swept anchors (ND's H3/H1 maxes out at **−2.5 dB**, not the "never above
> ≈ −25 dB" recorded in session 75 §5 or the "~ −35 dB" that `matrix_harmonics.py` printed as a
> hardcoded string — both were **medians quoted as a maximum**).
>
> ⇒ **What survives §4 is the STRUCTURE, not the numbers**: hardware is even-dominant where ND is
> essentially not, hardware's evens sit at the level of its adjacent odds, and session 7's bound caps
> H2/H1 at −12.04 dB for any monotone map with a quadratic even part. **That is exactly what rule 3 in
> §5 below has always said — sessions 73–77 drifted from it by building scored objectives on chart
> reads. Come back to the rule.** Full detail: `docs/phase9-validation.md` §4 "THE REFERENCE IS
> RESOLVED".

---

## 5. Rules of engagement

1. **Never write "the pedal" again without saying which.** Use **HW** for hardware-derived and
   **ND** for capture-derived. Retrofitting old text is not required; new text must be explicit.
2. **A candidate that moves away from the captures toward a documented hardware trend is a PASS,
   not a regression.** The 63/104-capture matrix grade is still the arbiter *within* the ND-authority
   domains of §1 — but it has no authority over the harmonic structure, and a matrix regression
   caused by a §4 correction is expected and must be reported as such, not "fixed".
3. **Do not fit to §3 or §4 numbers directly.** They are chart reads with unknown exact conditions.
   Use them to set the SIGN and the ORDER OF MAGNITUDE of a target, then gate the candidate on a
   physically-derived model and on the ND matrix for everything the correction should NOT move.
4. **Captures are now cheap and perfectly repeatable.** Any missing condition is a re-render away.
   Stop treating the capture matrix as a fixed, scarce asset — but DO re-verify that a newly-added
   condition does not silently change a membership-based aggregate
   (`aggregate-moved-check-membership-first`).
5. **The `capture-outranks-schematic` doctrine still holds — with a carve-out.** Fitting a constant
   to the captures remains right for linear/EQ work. It is **wrong** for even-order harmonic
   structure, where the capture is the thing that is broken.

---

## 6. What is NOT claimed

- We have **images only**, no underlying measurement data, and no statement of the exact drive /
  blend / level conditions behind §3 and §4.
- The source's provenance is a third-party comparison. Its *internal* consistency is good (charts 2
  and 5 identical; the odd-harmonic ladders matching to the dB across two independent drive
  settings is a strong self-check), but it has not been reproduced by us.
- **§2 is the only section precise enough to fit against**, because it is a 4 dB window with
  gridlines and two independent hardware units agreeing.
- Nothing here says the ND captures are *wrong* as a target for reaching the right region. The user's
  framing stands: they get us very close, and where we miss them but track hardware, that is fine.
