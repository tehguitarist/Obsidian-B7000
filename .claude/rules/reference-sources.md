# Reference Sources — what the captures ARE, and which reference wins where

> **Read this before treating any capture-derived number as "the pedal".** It is the standing
> authority rule for the whole project, not a Phase-9 note. Established 2026-07-29 (session 71).
>
> ⚠ **Compressed session 122** (doc-consolidation pass). Table cells now hold the current verdict
> only; the stacked per-session history that used to live inside them is in §1a and §4's table,
> below their sections, in date order, with every ⛔/⭐ refutation preserved. Nothing was deleted —
> the pre-compression version is archived verbatim in `docs/session-log.md`.

---

## 0. The fact that changes everything downstream

**`analysis/captures/` is a recording of the Neural DSP Darkglass plugin, not of a Darkglass B7K
Ultra.** Every "the pedal" / "the real pedal" / "the captured unit" statement in `circuit.md`,
`docs/phase9-validation.md`, `docs/phase7-calibration-handover.md`, the memory files and every
`CLAUDE.md` handover means **the Neural DSP emulation**, unless that specific entry says otherwise.
Confirmed by the user 2026-07-29.

This is not a disaster — ND is very close, and §2 quantifies exactly how close — but several
load-bearing project facts read differently once you know it:

| Fact as recorded | How it reads now |
|---|---|
| **0.144 dB "take-to-take floor"** — quoted as the noise floor in ~40 sessions | Not a converter/analogue floor. Against a deterministic renderer it is at most a **knob-repositioning** floor. **MEASURED, session 112, and it is TWO different numbers**: two captures of one condition, four days apart, agree to **0.010 dB mean** (recording repeatability — ~14× better than 0.144); but re-setting a knob is not free — four re-captured MASTER detents differ from their predecessors by a *flat* offset up to **1.62 dB** (re-dialling repeatability). ⇒ **quote 0.010 dB for repeatability and ≤1.6 dB for re-dialling — not interchangeable; which applies depends on whether the knob was touched.** |
| Session 70 rejected the §2 repeatability set because five "takes" agreed to −147…−164 dBFS with lag exactly 0, arguing no two analogue re-recordings can agree that well | **That discriminator is invalid.** Five renders of a plugin *can* agree to float32 rounding. The set is probably fine; the rejection should be re-examined before anyone re-records it. |
| `docs/final-capture-window.md` — "the pedal is available for ~5 days, then never again" | ⛔⛔ **RE-INSTATED, SESSION 111 (2026-08-02).** The "unlimited, do not ration" framing (2026-07-29 → session 111) does not hold now — the user is losing access to the ND plugin (confirmed session 111; full inventory in `CLAUDE.md` → "Project-specific carry-forwards" → "Capture access status"). **Treat captures as scarce until this row says otherwise.** A capture not already on disk (`analysis/captures/`) or in that inventory is a **blocking question for the user, asked immediately.** |
| §0 PCB photos "declined and closed permanently"; the four large departures (`trebleC7` 147×, `clipC15` 423×, `c21R` 10×, `R36` 1.42×) as *"fitted to a real unit whose board can never be inspected"* | They are **fitted to another emulation's behaviour**, not a physical board — still not resolvable by photos, but §2/§3 below can partly adjudicate them. |
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
| ~320 Hz cancellation-null DEPTH | **Hardware** | ND's null is shallower in all six measured PNG-read conditions (§3); on the render matrix its depth is also level-dependent in a way no fixed network reproduces (§3, GATE R) |
| **Harmonic structure / clipping asymmetry** | **Hardware, overriding the captures outright** | ND's even-order ladder is **~27 dB low** at mid drive (§4). This is not a refinement — see §4 for the low-drive-only carve-out. |
| Absolute level, gain staging, makeup | **Captures** | No hardware anchor exists for it, and ND is level-consistent |
| **OD-vs-clean mixing balance (A3)** | **Captures** | Current verdict: the OD path is quiet, absolutely, by 5.1–5.5 dB over 100–400 Hz (GATE O, session 107); it is NOT a fittable static constant (GATE P, session 108) — see §1a for the full derivation and every superseded claim along the way. |
| 5–6 kHz null | **Neither — unresolved** | Absent from the clean sweep, so drive-dependent; the driven charts disagree between conditions and are PNG reads |

**The one-line version:** *the captures get us into the right region for everything linear; the
hardware data governs anything that comes out of a nonlinearity. Failing to match the captures is
acceptable — and correct — when we are moving toward a documented hardware trend.*

### 1a. How the A3 row got its current wording (date order, refutations preserved)

A3 is the single most re-scoped finding in the project. Read bottom-to-top for "what does the
current session need to know" (it's already at the top of the table above); read top-to-bottom for
the derivation. Full per-session detail: `docs/session-log.md`.

- **s85** — the harmonic-axis instrument is built: A3 ≈ 5–7 dB over 100–400 Hz, k ≈ −6.5 dB (the
  model's OD too weak vs its own bleed). ⚠ s85's own 100 Hz reading (k = −10.64) fails the
  instrument's order-independence premise — **quote ≈ −8 dB or not at all.**
- **s86** — corroborated against the independent DRIVE axis: the two instruments' robust order
  subsets overlap on one curve. **Quote A3 as ≈ 5–7 dB over 100–400 Hz; do NOT fit a slope** — the
  intervals are 1.8–9.9 dB wide, so compatibility is established, a shape is not.
- **s87/s88** — the C1/C2/C3 component-budget derivation from that curve reaches **C2 only** at
  first (`THD_ANCHORS` gap); s88 shows the gap is a report property, not a stimulus one, and
  extends readable anchors to 50/64/32/25 Hz (20 Hz genuinely needs a re-capture). Re-derived:
  C1 +2.69…+2.72 | C2 +3.30…+3.50 | **C3 +4.99…+7.23 dB, and C3's size is OPEN** — it is
  β-dependent and session 52 separately flagged the blend axis unreliable below 40 Hz.
- **s105 (GATE M)** — A3 confirmed **on a third instrument** sharing no machinery with s85/86 (the
  mixing network's two exact-zero endpoints, no fit, no gain match): **5.54/5.38/5.07/5.14 dB**
  across four stimulus levels — stimulus-independent to 0.47 dB. §1's figure is right, *inside its
  own band*. ⛔ **But session 103's GATE K7 broadband figure (3.1–4.9 dB) is TWO things summed**:
  (A) that stimulus-independent 100–400 Hz level term, and (B) a separate, stimulus-**dependent**
  term at 508–1016 Hz swinging 5.4 dB with drive (peak migrating 254→640 Hz). **(B) is unclaimed —
  do not fold it into A3, do not aim a static gain at K7's broadband mean.** K7's headline also
  pools the session-48 `gain-n12` defect as 1 of 5 pairs; excluded it reads **3.4–5.1 dB**.
- **s107 (GATE O)** — "mixing balance" is the wrong name. Regrouped from *(model's clean/OD ratio −
  reference's)* into *(clean path's absolute error − OD path's)*: the clean side is **bounded at
  0.41 dB against a 5.28 dB deficit** (8%; deficit is 13× the bound). ⇒ **A3 is NOT a two-sided
  balance — the OD PATH IS QUIET, ABSOLUTELY, by 5.1–5.5 dB over 100–400 Hz.** Size unchanged
  (MASTER is common-mode within every pair and cancels). ⛔ **Do NOT quote "exonerated to 0.007 dB"**
  (session 106) — that was the master-unity reading alone, on a different capture route/session;
  **quote 0.41 dB** (later re-quoted 0.48 dB, session 119, on the current baseline). Two
  reference-side properties (~0.2–0.3 dB) folded into that bound, not into A3: ND's DIST-engage at
  BLEND min is not transparent (O7, still stands); ND's clean path is "not level-invariant" (O5) —
  **REFUTED, see s112 below.**
- **s108 (GATE P)** — the 5.1–5.5 dB figure is not wrong, but it is **not a target a static
  correction can be fitted to**: it's a window mean over a migrating feature (dominant bands
  320/254 Hz are also the *least* reproducible across pairs), it pools 4 capture pairs differing in
  the pedal's own DRIVE/ATTACK controls (per-pair spread 4.48–6.68 dB, ±1.10 about 5.34, never
  printed before), and the pedestal/feature split is **unmeasured** (13/20 threshold combinations
  give an empty intersection). The best a static broadband gain can do is **5.48 → 2.86 dB rms
  (48%) — it cannot close A3**, corroborating session 52's "no post-clipper linear element closes
  it" through an unrelated instrument. **Do not fit a constant to 5.1–5.5 dB.**
- **s109 (GATE Q)** — the OD path's absolute error decomposes into **two defects**: `L(f)`, the
  error at low stimulus (rms 2.72 dB, a linear element could carry it) and `D(f) = error(−6) −
  error(−30)` (rms 3.01 dB, **only a nonlinearity can carry it**). Mechanism, measured three
  independent ways: the model's OD path **saturates too early** (compression law, the 320 Hz null
  washing out where the pedal's deepens, THD running +2.94 dB hot). ⛔ Does NOT contradict s50/s52
  — it explains why they could not succeed. A3's size and GATE O's attribution are untouched; what's
  new is the deficit decomposes and the larger half has a lever (`kInputRef`, shipped s109 — see
  `CLAUDE.md` SHIPPED CONSTANTS). ⚠ Two corrections fell out: the THD "level term" is an **UNSIGNED**
  rms (signed mean **+1.263 dB** — the model over-distorts, not under); one `(capture, sweep)` cell
  is a reference dropout worth +0.055 dB of the shipped OD headline.
- **s112** — GATE O5's "ND's clean path is not level-invariant" is **REFUTED**. Four fresh clean
  twins read 12.000 dB flat to 0.0003 dB across 29 bands; the 0.334 dB tilt was one contaminated
  pair (`ref-clean.wav`), corroborated on a second instrument sharing no machinery (GATE N's THD
  turnover: 12.000/12.000/12.001). ⇒ the true `gain-n12` send is **12.000 dB**, not the harness's
  12.071. What survives from O5: the model-side known answer and the practice of correcting per
  band. What does NOT survive: the attribution, and the derived claim that "no absolute clean-path
  statement about this reference can beat ~0.3 dB" (O7's DIST-engage non-transparency, ~0.17 dB,
  is untouched and still stands on its own).
- **s114** — on the user's "whatever increases accuracy" decision, `captures.py`'s
  `_GAIN_SESSION_MEASURED_DB[-12]` moved 12.071 → **12.000 dB**. Exactly scoped (0 non-`gain-n12`
  rows moved on the new baseline `s114_baseline.json`); a correctness fix for the **absolute**
  ledgers (GATE K/M/O/Q), invisible to the gain-matched matrix by construction. **Re-quote any
  absolute figure on a `gain-n12` row against s114 or later.**
- **s119** — GATE O re-pointed at session 115's corrected MASTER ladder (its anchor capture had been
  proven 4.447 dB low); A3's clean-side bound re-quotes as **0.48 dB** against a 4.38 dB deficit
  (11%). Ratio and conclusion unchanged from s107; only the number moved with the corrected anchor.

⚠ **A3's exclusions must be quoted together, not piecemeal** — this is the sentence that stops five
different searches being re-opened: *no single element closes A3 (s50), no post-clipper linear
element of ANY order does (s52), no GRUNT-side cap does (s38), its level is not a fittable constant
(s108), and its shape MIGRATES with stimulus so no fixed linear network can produce it (s108
synthesis).*

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

1. ✅ **`c21R` was re-aimed at hardware in session 91 — 220k → 130k** (corner 7.2 → 12.2 Hz). The
   worked example of §5 rule 2, and the first constant in the project shipped *because* of this
   file. ⚠⚠ **Derive `HW − MODEL`, never the raw published `HW − ND` delta** — the model had already
   moved partway (0.40 dB below ND at 20 Hz) by the time this fit ran, so applying the raw delta
   overshoots (121k vs the correct 133.1k/E24 130k, `analysis/c21_hw_anchor.py`). Measured at 130k:
   worst remaining error vs §2 0.70 → 0.17 dB, OD improves on every gate row, CLEAN pays confined to
   25–100 Hz (median 0.23→0.26, p90 0.77→0.82), no row worse by >0.5 dB. 150k was rendered and
   **rejected** — only 55% of the move, outside what either §2 anchor asks for.
2. **A2e's flat-EQ half is already leaning the right way** (−0.29 dB @10k / −0.38 @16k below ND;
   hardware is 0.8–1.1 dB below ND there). **Lean further toward hardware, not back toward ND.**
   (A2e's real item — the mid-boost skirt, −6.03 dB @16k at HI-MID 3k — is untouched, still open.)
3. **ND's ripple above 6 kHz is an artefact** (a 4 dB window's worth). Do not model it — a fit
   chasing HF ripple is chasing ND's oversampling filter.

Also noted: ND gives **both** its pedal models (VU2 and B7K) the same flat-EQ response. Treat ND's
model-to-model differences as less trustworthy than its absolute response.

---

## 3. Driven-condition FR divergences (directional, not fit-grade)

Source: six ATTACK/GRUNT overlay charts, hardware vs ND, at drive. Positions inferred and
self-checked (charts 2 and 5 are the same curve to the pixel, pinning ATTACK/GRUNT = {Cut, Flat,
Boost}).

| Region | HW vs ND | Maps onto |
|---|---|---|
| **150–250 Hz** | HW **+2.8 to +4.8 dB** in every driven condition — and **exactly 0 dB at GRUNT cut / on the clean sweep** | A3 / GAP #3b (an OD-path low-mid gap, not "GRUNT has extra bass" — hardware wants MORE low-mid OD than ND does, and our model already under-delivers vs ND; the two corrections compound, they do not fight) |
| ~305–320 Hz null | HW deeper in **all six**: +1.6 (grunt cut) → +3.5/+3.8/+4.8 → **~26 dB at grunt boost** | GAP #2 / the ATTACK notch |
| 2–2.5 kHz | ND **+1.4 to +2.8 dB** hotter | new, small |
| 5–6 kHz null | Inconsistent — ND ~11 dB deeper at Attack cut, HW far deeper at Grunt cut | session 30's 5.1–6.4 kHz collapse; session 69's 4064/6451 sign dipole |
| LF null position | Grunt boost: HW at **18 Hz**, ND at **35 Hz**. Attack boost: same freq (~43 Hz), ND ~10 dB deeper | A3's migrating null |

⛔ **These are PNG reads. Use them for SIGN and rough SIZE only** — a veto and a direction, never a
fit target.

⭐⭐ **SESSION 110 (GATE R) — a property of ND at the ~320 Hz null that any fit against these
captures must know: ND's null depth is level-DEPENDENT, and no fixed linear network reproduces it.**
Measured bleed-free (BLEND = LEVEL = 1) as a 1/6-octave power-integrated deficit re the null's own
shoulders: at DRIVE 0/0.5 ND's null washes out with stimulus (as ours does — a cancellation feeding
a compressor must); at **DRIVE max it reverses and deepens** (4.99 → 12.37 dB). ⇒ **quote ND's null
behaviour per DRIVE, never pooled** — pooling over DRIVE turned a switch-dependent property into an
apparent device property (session 117 later found the reversal itself is dominated by the pedal's
*quiet*-end collapsing, not the driven end deepening — see `CLAUDE.md`'s CLOSED/REFUTED table). A
cancellation whose depth GROWS with level cannot come from a fixed network at any position — not a
"wrong place" difference, must not be fitted as one. Session 110 rendered both obvious candidates
(global saturation change; relocating the post-clipper notch to 320 Hz) and **neither closes it**.
n = 5 at one DRIVE setting: located, not characterised.

---

## 4. The harmonic finding — this is the big one

Source: three spectrum overlays, hardware @997 Hz (green) vs ND @800 Hz (white), ATTACK/GRUNT flat,
three drive settings. Levels **relative to the fundamental**:

| | **low drive** HW / ND | **mid drive** HW / ND |
|---|---|---|
| H2 | **−22.5 / −42** | **−12 / −39** |
| H3 | −41 / −42 | **−12 / −12** |
| H4 | −60.5 / −57 | **−24 / −52** |
| H5 | −75.5 / −71 | **−24 / −24** |

**At mid drive the odd harmonics match to the dB (H3 −12 both, H5 −24 both) and the evens are offset
by 27–28 dB.** Hardware's evens sit at the level of its adjacent odds — the textbook signature of a
symmetric clipper plus a genuine offset/asymmetry. ND has essentially **no even-order mechanism.**

This splits the project's nonlinear work cleanly:

- ✅ **The odd-order half is fitted to a correct target** (sessions 13/15's phase-aware work, the
  H3-sign investigation). ND's odd structure matches hardware. **That work stands.**
- ⛔ **The even-order half (sessions 5–7, session 44's fitted asymmetry) was fitted to a target
  ~27 dB low.** Session 7's standing bound — a monotone map with a quadratic even part caps H2/H1
  at −12.04 dB — is exactly where hardware sits at mid drive. Fitting to ND could never reach it.

⚠ Correcting for tone matters before reading any cross-column harmonic gap as a device difference:
HW's tone (997 Hz) is filtered harder by this chain's ~3.3 kHz Sallen-Key than ND's tone (800 Hz)
— session 72 measured H2−H5 −3.2/−4.9/−6.7/−8.1 dB of extra filtering on the HW column alone.

### 4a. Sessions 72–84 — locating and testing an even-order lever (date order)

⛔⛔ **HEADLINE, READ FIRST: THE CHART'S OWN H2−H3/H4−H5 NUMBERS ARE DEMOTED (session 78) — DO NOT
SCORE ANY CANDIDATE AGAINST THEM.** They were tested against the real ND device at the chart's own
tone/operating point and do not survive it (§4's structural finding above is unaffected — it comes
from the chart's *shape*, not these two derived numbers).

| session | what it established | status |
|---|---|---|
| **72** | Measured against our own model, split by drive: at **mid** drive we already deliver 94–99% of hardware's asymmetry (session 44's fit stands, do not re-open). At **low** drive we sit AT ND (2–12% of the way). | Even-order item is **low-drive-specific**; natural carrier is the **J201** (upstream, never idles), not the clipper. Gate any candidate on leaving mid drive alone. |
| **73** | Gated the J201 carrier (`jfetSatNeg`, the small-signal quadratic): confirmed as the mechanism, but the chart's low-drive target needs 5.72× selectivity and only 5.43× is available (declining as pushed). A genuine interior optimum exists (a≈4.0–5.6, ~7.9 dB better than shipped) but the point that DOES reach the chart target is *worse* than shipped (wrecks mid-drive H4−H5). The physically-coherent form (`2·a·cn=1` identity) tested **jointly infeasible**. | Confirmed but insufficient. **Nothing proposed.** *(The infeasibility verdict is itself superseded — see session 83.)* |
| **78** | Rebuilt the correction using the actual 1 kHz tone ladder every capture already has, instead of the swept 100/200/400 Hz anchors (whose bridge to the chart's 800 Hz tone needs 14 dB of extrapolation). | ⛔⛔ Chart numbers demoted (see headline above). Correction recorded as −0.02 dB — **later found wrong, session 79.** |
| **79** | Corrected session 78's own correction (right physics — bleed-free captures only — wrong sign; true value +0.56 dB, not −0.02). Put our own model on the same axis for the first time: **mid drive is 88% of the way from ND to hardware; low drive the model sits at +1.42 dB, on the FAR side of ND from hardware (ND itself reads +10.12).** | ⭐⭐ Overturns the standing gating rule: *"an even-order correction MUST regress the ND matrix"* is **only true at mid drive**. At low drive the first ~7.9 dB of correction moves toward BOTH references and should **improve** the matrix. **Gate the two drive regimes separately; expect opposite matrix signs.** |
| **80** | Spent the reachable move: `jfetSatNeg` ≈ 1.9…3.0 costs nothing against either reference at its own low-drive anchor (the chart's 17.2 dB requirement was demoted; the real requirement is 7.9 dB, reachable at 3.8×). | **Not proposed** — matrix hadn't judged it; blind to H4 (model already +4.3 dB above ND there); breaks the `2·a·cn=1` identity. |
| **81** | Ran the 129-capture matrix on it, binned on the REFERENCE's own H3/H1, forced bleed-free. The free move is **smaller than the ladder implied** (matrix low-drive H2 deficit is 6.5 dB, not the ladder's 9.7 — tone-dependent). Sign reversal reproduces on an independent instrument. | Free move spent by **a ≈ 1.81**; narrows session 80's "1.9…3.0" to **1.8–2.0 at the edge of free**, settles against 3.0. Pooled bootstrap can't see this — **gate on the split, not the total.** |
| **82** | Three unread renders (a=2.5/3.5/5.6) moved two numbers. (a) The pooled acceptance test is **non-monotone in `a`** — "significant" tracks cross-cell coherence, not size, so significant ≠ costly/free. (b) Crossing measured at **a ≈ 1.77–1.81** (quote the range, not a point). (c) The matrix's H4 disagreement (+4.3 ladder vs −6.85 matrix) rests on **n=5, 31.5 dB wide** — far weaker support than the handover implied. | Narrows the crossing; downgrades confidence in the H4 disagreement. |
| **83** | (1) The ladder's own H4 half does **not survive either** — it's DISPERSED (41.9 dB), not floored. **There is no H4 disagreement left to adjudicate between the two instruments** — only the *direction* (lever improves H2, worsens H4) survives; quote direction, never level. (2) The `2·a·cn=1` identity is **AFFORDABLE**, not jointly infeasible as session 73 recorded — the real requirement shrank from 17.2 dB (chart) to 6.5 dB (matrix domain), and the identity's true cost is a 3.25×-tighter fold-back budget, reachable. An identity-honouring point (`SQ a=1.9 s=0.40`) ties the free `a=1.9` point (0.10 dB apart). | Session 73's infeasibility verdict **retracted**. "Free in practice" claim not yet matrix-tested. |
| **84** | ⛔⛔ **The 129-capture matrix judged the identity, and "free in practice" does NOT survive it.** The identity buys a fraction of a dB on H2 — the column with **NO authority** (ND is 27 dB below hardware there) — and pays a multiple of it on H3 — the column that **IS authoritative** (ND == hardware) — in both drive regimes: +0.23 dB bought for −1.45 dB paid (low), +0.30/−0.42 (mid). The screen anchors on H3/H1 by construction, so it could never see this cost. | **A candidate scoring "free" on H2−H3 must be re-scored PER ORDER before it is believed.** What survives: the identity is *affordable* (session 83's retraction stands); "free" does not. Nothing proposed. |

**Closing synthesis (no further session has re-opened this):** at mid drive neither chart column
lies inside the model's measured range; agreement between the chart's two columns is not evidence
either is right (they can share an error — measured, at low-drive H4−H5 they agree to 1.0 dB while
ND's own device reads ≥16.9 dB there); and no capture can resolve this further because the chart
under-specifies its own operating point by more than the quantity in dispute. **What survives §4 is
the STRUCTURE, not the two chart numbers**: hardware is even-dominant where ND essentially is not,
hardware's evens sit at the level of its adjacent odds, and session 7's bound caps H2/H1 at
−12.04 dB for any monotone map with a quadratic even part. That is exactly §5 rule 3 — sessions
73–84 drifted from it by building scored objectives on chart reads; come back to the rule rather
than re-deriving a new chart-based target.

---

## 5. Rules of engagement

1. **Never write "the pedal" again without saying which.** Use **HW** for hardware-derived and
   **ND** for capture-derived. Retrofitting old text is not required; new text must be explicit.
2. **A candidate that moves away from the captures toward a documented hardware trend is a PASS,
   not a regression.** The capture matrix grade is still the arbiter *within* the ND-authority
   domains of §1 — but it has no authority over the harmonic structure, and a matrix regression
   caused by a §4 correction is expected and must be reported as such, not "fixed".
3. **Do not fit to §3 or §4 numbers directly.** They are chart reads with unknown exact conditions.
   Use them to set the SIGN and the ORDER OF MAGNITUDE of a target, then gate the candidate on a
   physically-derived model and on the ND matrix for everything the correction should NOT move.
4. **Captures are now cheap and perfectly repeatable when access allows it (see §0's re-instated
   scarcity row).** Any missing condition is a re-render away — but DO re-verify that a newly-added
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
