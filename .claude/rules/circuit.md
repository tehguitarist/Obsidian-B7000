# Circuit Reference — Darkglass B7K **Ultra** (built on the "Black Mirror VII" B7K clone board)

> This file is the **source of truth** for component values and topology. Fill every `<...>`
> placeholder by reading the schematic directly. Do NOT approximate or copy values from a build
> kit / forum trace without confirming against the primary schematic.
>
> **What this pedal is:** a bass overdrive / DI preamp modelled as the **Darkglass B7K Ultra**.
> Controls: **MASTER**, BLEND, LEVEL, DRIVE, + 4-band active EQ (LO/BASS, LO-MID, HI-MID, HI/TREBLE)
> with **switchable Lo-Mid (250/500/1k Hz) and Hi-Mid (750/1.5k/3k Hz) centre frequencies**, plus a
> 3-way **ATTACK** switch (Boost/Flat/Cut) and a 3-way GRUNT switch, and a balanced XLR DI out with
> ground-lift. Single 9V supply. Clipping is a **CMOS inverter (CD4049UBE) overdrive**, not a diode
> clipper (diodes are input clamps only). Input Z 1MΩ, output Z 1kΩ.
>
> ⚠ **Source-fidelity boundary (read this).** Our schematic is the *original B7K* clone. The Ultra
> features that are NOT on that schematic are **engineered approximations**, tagged **[ENG]** below —
> they reproduce Ultra *behaviour*, not a verified Ultra unit:
> - **MASTER volume** [ENG] — designed post-EQ volume stage (also sets DI level).
> - **3-way ATTACK** [ENG] — the documented 2-position ULTRA-HI network extended with a centre "Flat".
> - **Switchable mid frequencies** [ENG-caps] — 3-position selectors; caps **computed** to hit the real
>   Ultra centres (anchored to the p.3 Ultra-Mod measured f-vs-C tables; f ∝ 1/√C_series). Validate
>   against a filter sim / real-unit capture before trusting exact corners.
> - **Second (DIST) footswitch** [ENG] — the real Ultra has TWO footswitches (main true-bypass +
>   a dedicated one that engages/disengages just the overdrive, independent of bypass — confirmed by
>   web research 2026-07-19, see Validation notes). Our BOM lists only **one** 3PDT stomp switch —
>   this control doesn't exist on our schematic at all and needs its own design (see Footswitches).
>
> **Confidence note:** MASTER, ATTACK wording, and both mid-band frequency sets were independently
> cross-checked against the real Darkglass manual (2026-07-19 web research) and match our `info.txt`
> and computed cap values exactly — high confidence on those three. The DIST footswitch is new
> information not previously in any of our docs.
>
> Everything else (JFET front end, CD4049UBE clipper, base EQ topology, buffers, power) IS
> schematic-verified from primary p.4 — unchanged from the original-B7K analysis.

## Schematics

Both PDFs render right-side-up; text within an element may be rotated 90° (read visually, don't
OCR-assume orientation). The circuit drawing is **page 4** of the primary PDF (dense — rasterise at
≥300 DPI and crop; a reusable `crop.py`/`cropb.py` lives in the session scratchpad `schem_test/`).

| File | Role |
|------|------|
| `Primary BOM and schematic.pdf` (p.1–2 BOM, p.3 Ultra-Mod, **p.4 schematic**) | **Primary source of truth** for values + topology. Board rev 1.1v, 9 May 2023. |
| `Backup-Schematic for node triple checking only (different component labels).pdf` | Node cross-check ONLY. Different revision ("B7X", 23 Apr 2021) + **different R/C designators** and some **different values** (see Validation notes). Confirms topology, NOT values. |

Designator scheme used throughout this file = **primary schematic (p.4) numbering**. The backup's
`U`/`VR`/`R`/`C` numbers differ; a few key equivalences are noted inline where useful.

### Crop index (primary p.4 unless noted; fractional coords are of the full rasterised page)

| Crop region (x0,y0–x1,y1 frac) | Contains |
|-----------|----------|
| 0.13,0.28–0.34,0.45 | Input jack, R1 pulldown, C1/R2 bias, R3, IC1_A buffer, C2/R4, Q1/Q2 JFET stage start |
| 0.27,0.28–0.46,0.47 | JFET drain node + treble network (C5/C9/C6/R12/R14/R7/R8) + ULTRA-HI switch (C8) + R11/C7/R13 |
| 0.44,0.28–0.63,0.47 | IC2_A DRIVE stage (R15/C10 fb, R17/DRIVE/R32 gain leg) + GRUNT switch (C11/C12/C13) + start of clipper |
| 0.518,0.30–0.585,0.45 | **Clipper**: R16, D1/D2 clamps to +9V/GND, IC3 CD4049UBE, R18/C14 fb (D1/D2 both cathode-up) |
| 0.62,0.28–0.80,0.47 | IC2_B recovery (UNITY BUFFER + passive bridged-T, see correction note) + IC4_B Sallen-Key LPF start |
| 0.77,0.28–0.97,0.50 | IC4_A Sallen-Key LPF + LEVEL (VR2) + BLEND (VR1) pots |
| 0.13,0.47–0.34,0.68 | IC5_A buffer, IC5_B inverting gain, BASS band (VR4 LO) start |
| 0.30,0.46–0.52,0.70 | TREBLE (VR5 HI), IC5_C summing amp, LO-MID (VR6) start |
| 0.48,0.46–0.70,0.72 | IC5_D (LO-MID), HI-MID (VR7), IC6_A |
| 0.66,0.44–0.86,0.74 | IC6_B output buffer → C37 → R47 → OUT; IC6_C/D XLR DI (skip) |
| 0.21,0.19–0.42,0.32 | Power: D3 Schottky, +9V filter, R30/R31 VD divider, status LED |

---

## ⚠ Schematic-reading gotchas (these caused real bugs)

- **Resistor value notation:** `2m2` / `2M2` means **2.2 MΩ**, `2k2` = 2.2 kΩ, `2R2` = 2.2 Ω. The
  letter is the decimal point AND the multiplier. Misreading `2m2` as 2.2 Ω (or 2.2 mΩ) is an easy
  ~6-orders-of-magnitude error. Double-check every R against its neighbours' magnitudes.
- **Series vs pulldown:** a large resistor (e.g. 2.2 MΩ) at the input is usually a **pulldown to
  ground** (bias/pop suppression), not a series element. A 2.2 MΩ *series* resistor would attenuate
  ~14 dB and roll off treble hard — if your model does that, you've mis-traced the topology.
- **Pot wiring:** confirm pin1/pin3/wiper → node mapping for every pot. "Rheostat" (wiper jumpered
  to an end, no ground leg) behaves very differently from a "divider". Trace it; don't assume.
- **Taper:** note the designation (A = audio/log, B = linear). Kits sometimes substitute — follow
  the schematic, not the kit.
- **Op-amp inverting vs non-inverting:** verify which input the signal enters. Confirm output
  polarity later with a DC-step test per stage.
- **Power section parts in the signal columns:** supply-filter R/C (and any series Schottky) can be
  mislabelled as signal-path parts. Exclude VREF-divider and supply-filter components from the DSP
  model.
- **Same component VALUES ≠ same TOPOLOGY across schematic sources.** Two traces of "the same"
  pedal (an early-revision trace vs a later kit/clone) can share every R/C value designator-for-
  designator while wiring one network completely differently (e.g. two independent series R+C
  branches to ground vs one shared branch-then-shared-cap-to-ground). Identical values are NOT
  evidence the topology matches — redraw the actual node connections from each source before
  concluding they agree, especially for any network feeding a feedback node.
- **If the pedal has more than one full gain stage in series ("channels"/"sides"), verify the
  ACTUAL signal order from the real unit (continuity trace, or an unambiguous schematic signal-flow
  arrow) — never assume it from the physical/UI layout.** Left-to-right, top-to-bottom, or numbered
  ("1/2", "A/B") layout is a UI/PCB-placement convention and is **not** guaranteed to match which
  stage the input actually reaches first. Getting this backwards still produces a plausible-sounding
  result (both stages are real circuits, so it "works"), which is exactly why it's easy to ship
  before catching it — confirm the order explicitly, early, rather than inferring it.
- **Once you have a component's value, re-reading it again rarely finds a new bug — re-tracing its
  connections often does.** If a stage's R/C/pot values are already captured in the component
  tables below, don't keep re-scanning the schematic image for those values on follow-up passes;
  spend that time on the **node graph** instead (see "Topology — node graphs" below). Most of the
  bugs this template has caught in practice were topology mistakes (a bridging part misread as
  series/parallel, a wiper wired to the wrong leg) with perfectly correctly-read values, not
  misread values themselves.
- **A bridging (feedback-spanning) or shunt component changes the topology, not just a value.** A
  resistor or capacitor that bridges across another part — from one side of an R to the other, or
  from a mid-node to ground in parallel with something already there — turns what looks like a
  simple series chain into a real feedback or divider network. Before modelling any such part,
  redraw the two (or more) nodes it actually touches and confirm whether it's genuinely in
  **series** (same current, no other path), **parallel** (same two nodes as another part), or a
  **shunt to ground/VREF** (a third path off an existing node) — these have very different WDF
  adaptor shapes (`WDFSeriesT`/`WDFParallelT` vs an R-type feedback leg) and are easy to conflate
  when the schematic draws the bridging part as a short diagonal line across an otherwise-straight
  trace.

---

## Signal path summary

Single signal chain (NOT a dual/stacked pedal — one path with a parallel clean tap for BLEND):

```
                                                          ┌────────── clean (unity) ──────────┐
IN ─R1‖ ─C1─(VD bias R2)─R3─▶ IC1_A buffer ─┬─▶ C2/R4 ─▶ Q1/Q2 JFET gain ─▶ treble net + ULTRA-HI
                                            └─(clean tap)┐                                    │
                                                         │   ┌────────────────────────────────┘
   ┌─────────────────────────────────────────────────────┘   ▼
 (to BLEND pin1)                          ─▶ IC2_A DRIVE (non-inv, gain 4–78×) ─▶ GRUNT cap bank
                                                         ▼
     R16 ─▶ IC3 CD4049UBE clipper (D1/D2 = rail clamps; CMOS soft-clip) ─▶ C15/R20 ─▶ IC2_B UNITY BUFFER
                                                         ▼  (then passive bridged-T shaping: C16/R22/R23/C17 — NOT a gain stage; see correction note)
                                                         ▼
        IC4_B Sallen-Key LPF (~10.7k) ─▶ IC4_A Sallen-Key LPF (~3.3k) ─▶ LEVEL(VR2) ─▶ BLEND(VR1) wiper
                                                         ▼
   IC5_A buffer ─▶ IC5_B (inv, −2.2×) ─▶ [BASS+TREBLE around IC5_C] ─▶ [LO-MID IC5_D] ─▶ [HI-MID IC6_A]
                                                         ▼
        MASTER(VR8)[ENG] ─▶ IC6_B buffer ─▶ C37 ─▶ R47(1k) ─▶ OUT   (MASTER also sets XLR DI level; XLR: SKIP)
```

**Switchable mids [ENG-caps]:** LO-MID and HI-MID each get a 3-position selector that swaps the
*series* cap (C33 for lo-mid, C35 for hi-mid) to move the peak centre. The "across" caps (C32=22n,
C34=6n8) and all resistors stay fixed. See the mid-band tables below.

VREF = **VD = +9V/2 ≈ 4.5V**, an unbuffered R30/R31 (10k/10k) divider + 100µF (C24). Model bipolar
(VD = 0 V signal ground). **Supply: single 9 V, no charge pump** (9V → D3 1N5817 Schottky → +9V rail
≈ 8.6 V after the ~0.35 V drop). Op-amp output headroom is set by this rail — see calibration doc §6.
All ICs (TL072ACP dual, TL074ACN quad, CD4049UBE hex inverter) run on +9V / GND.

## Component values (from primary p.4 + BOM — do not approximate)

### Input & buffer (IC1_A)
| Ref | Value | Function |
|-----|-------|----------|
| R1 | 1M | input pulldown to GND (sets ~1MΩ input Z, pop suppression) |
| C1 | 100n | input coupling |
| R2 | 1M | bias input node to VD |
| R3 | 10k | series into IC1_A (+) |
| IC1_A | TL072ACP | **unity-gain buffer** (pin2 −tied to pin1 out). Output splits: drive path (C2) + clean tap (→ BLEND pin1) |

### JFET gain stage (Q1/Q2) — active, mildly nonlinear
| Ref | Value | Function |
|-----|-------|----------|
| C2 | 1n | coupling from buffer into drive path |
| R4 | 100k | series into Q1 gate |
| Q1 | J201 | common-source gain JFET |
| R6 | 3k3 | Q1 source degeneration (to GND) |
| C3 | 220n | ∥ R6, bypasses degeneration at audio freq (raises HF gain) |
| R5 | 1M | Q1 gate/source bias reference (gate leak to GND) |
| Q2 | J201 | **active load** for Q1 (gate fixed at +4.5V, drain +9V, source = Q1 drain = output node) |
| R9 / R10 | 1M / 1M | +9V→GND divider = +4.5V for Q2 gate |
| C4 | 22n | Q2 gate→source(output) bootstrap cap — connects the Q2 gate (4.5V bias node) to the OUTPUT node (Q1 drain / Q2 source), **NOT to GND**. Bootstraps Q2's gate to its source at AC → constant Vgs → higher AC output impedance (better active load). Schematic-verified at pixel zoom 2026-07-19. |

### Treble / pre-clip network + ATTACK switch — VERIFY NODES; 3rd position is [ENG]
| Ref | Value | Function |
|-----|-------|----------|
| R7 | 200k | on JFET-drain signal rail |
| R8 | 470k | on signal rail (C8 bridges across via switch) |
| C5, C9, C6 | 22n, 22n, 22n | treble-shaping ladder (lower rail) |
| R12, R14 | 6k8, 22k | shunt legs to GND in treble ladder |
| C8 | 220pF | HF cap routed by ATTACK switch |
| **ATTACK (SW1)** | **SP3T / On-Off-On** | **3-way Boost/Flat/Cut** [ENG]. Sets treble content into the clipper. |
| R11 | 470k | to GND at IC2_A input side |
| C7 | 100n | coupling into IC2_A |
| R13 | 1M | bias IC2_A (+) to VD |

> **ATTACK 3-way [ENG].** Schematic ships a 2-position SPDT On-On here (BOM: "Ultra Hi — SPDT On-On",
> confirmed). **Node graph now verified (2026-07-19):** switch common (pin1) = the **R7/R8 junction**.
> Boost (pin2) connects C8(220pF) from that junction to the *post-R8* node → **C8 bridges R8** (HF
> bypasses the series R → treble boost into the clipper). Cut (pin3) connects the R7/R8 junction
> **directly to GND** (dumps the treble-ladder HF to ground) — note the mechanism is *grounding the
> node*, not "shunting C8 to GND"; C8 is left dangling in the Cut position. The Ultra needs a 3rd
> **Flat** setting → change to **On-Off-On (SP3T)**, centre = common floating (neither bridge nor
> shunt → flat). This is the minimal, natural extension of the now-verified 2-position network.

### DRIVE gain stage (IC2_A)
| Ref | Value | Function |
|-----|-------|----------|
| IC2_A | TL072ACP | **non-inverting** gain stage |
| R15 | 330k | feedback (out → −) |
| C10 | 47pF | ∥ R15, HF rolloff of feedback |
| R17 | 3k3 | gain-leg series (− → DRIVE) |
| DRIVE (VR3) | 100k **C taper** | gain control (in gain leg; rheostat). Gain ≈ 1+R15/(R17+DRIVE+R32) ≈ **4× (max R) … 78× (min R)** |
| R32 | 1k | gain-leg series (DRIVE → VD/AC-ground) |

### GRUNT switch + coupling into clipper
| Ref | Value | Function |
|-----|-------|----------|
| GRUNT (SW2) | SPDT On-Off-On | selects bass content fed to clipper (3 levels) |
| C11 | 4n7 | always in forward path |
| C12 | 47n | added in GRUNT pos 1 (via switch) |
| C13 | 220n | added in GRUNT pos 3 (via switch) — **primary=220n; backup=22n (rev diff), see Validation** |
| R16 | 6k8 | clipper input resistor (sets 4049 amp gain with R18) |

### CLIPPER — CD4049UBE CMOS inverter overdrive (IC3), NOT a diode clipper
| Ref | Value | Function |
|-----|-------|----------|
| IC3 | **CD4049UBE** | unbuffered hex inverter; one section used as inverting amp. Gain ≈ −R18/R16 ≈ **−48.5**. Self-biases input node to ~VD. **Clips against its own 0–9V CMOS rails (soft)** — this is the distortion source. |
| R18 | 330k | shunt feedback (out pin2 → in pin3 = node W) |
| C14 | 220pF | ∥ R18, HF rolloff |
| D1 | 1N4148 | anode=node W, cathode=**+9V** → clamps positive peak ≈ +9.6V |
| D2 | 1N4148 | anode=**GND**, cathode=node W → clamps negative peak ≈ −0.6V |

> D1/D2 are **input-protection / rail clamps** (window ≈ [−0.6, +9.6] V around the ~4.5V bias), NOT
> tight signal clippers. They only conduct on large excursions. The audible clipping is the 4049
> transition-region saturation. See `dsp.md` for the CMOS-inverter waveshaper model.

### Recovery + bandlimiting (IC2_B, IC4_B, IC4_A)
| Ref | Value | Function |
|-----|-------|----------|
| C15 | 2u2 | coupling from clipper out |
| R20 | 10k | series into IC2_B (+) |
| R21 | 1M | bias IC2_B (+) to VD |
| IC2_B | TL072ACP | ⚠ **UNITY-GAIN BUFFER** — pin6(−) is tied directly to pin7(out) (verified pixel-zoom on BOTH primary p.4 AND backup; no component in the −→out path). **NOT** a +12 dB active gain stage. See correction note below. |
| R22 / R23 / C17 / C16 | 100k / 33k / 22n / 680pF | **passive bridged-T network** hanging off the buffer output (see node graph), NOT an op-amp feedback/gain leg |
| IC4_B | TL072ACP | **2nd-order Sallen-Key LPF ≈ 10.7 kHz** (unity buffer) |
| R24 / R25 | 10k / 22k | IC4_B SK resistors |
| C27 / C18 | 1n / 1n | IC4_B SK caps (C27 to GND, C18 feedback) |
| IC4_A | TL072ACP | **2nd-order Sallen-Key LPF ≈ 3.3 kHz** (unity buffer) — final OD bandlimit |
| R26 / R27 | 22k / 47k | IC4_A SK resistors |
| C20 / C19 | 1n / 2n2 | IC4_A SK caps (C20 to GND, C19 feedback) |

> ⚠ **IC2_B CORRECTION (2026-07-19 verification).** An earlier reading called IC2_B a "non-inv
> high-shelf recovery, ~4× (+12 dB) above ~220 Hz." **That is WRONG** — it was inferred from the
> R22/R23/C17 *values* assuming the textbook active-shelf topology, but the actual wiring (verified at
> pixel zoom on BOTH the primary p.4 AND the backup schematic — they agree exactly) is:
> - **IC2_B is a UNITY-GAIN VOLTAGE FOLLOWER**: pin6(−) ties straight to pin7(out), no component
>   between them. Buffer input = clipper out via C15(2u2)/R20(10k), biased by R21(1M) to VD.
> - The R22/R23/C16/C17 parts form a **passive bridged-T network on the buffer output**, feeding
>   R24 → IC4_B SK:
>   ```
>   Node "buf out" (=pin7=pin6): C16 leg1, R22 leg1
>   Node "Nout"    : C16 leg2, R23 leg1, R24 leg1(→IC4_B SK)
>   Node "Nmid"    : R22 leg2, R23 leg2, C17 leg1   (C17 leg2 → GND)
>   ```
>   i.e. C16(680pF) bridges buf-out→Nout; R22(100k)+R23(33k) is the "T" (buf-out→Nmid→Nout) with
>   C17(22n) the shunt leg (Nmid→GND). This is a bridged-T, not a feedback/gain leg.
> - **There is NO +12 dB of makeup gain here.** This stage is unity + passive shaping. Do not budget
>   a recovery-gain boost into the gain-staging — that changes the whole level calibration (calib doc).
> - **This is exactly the "same VALUES ≠ same TOPOLOGY" trap** warned about in the gotchas above.
> - An ideal-component sim of the bridged-T (into the IC4_B SK) shows a deep midrange notch/scoop
>   (~−28 dB @ ~720 Hz, ideal, tolerance-sensitive) rather than a shelf. That depth is surprising for
>   this pedal, so **the exact response of this section MUST be validated against a real-unit capture**
>   before finalising the model — but the *topology* (unity buffer + bridged-T) is firmly verified.
>   The bridged-T is a live-`ImpedanceCalculator` linear network; model it as passive, not as gain.

### LEVEL, BLEND (crossfade mix)
| Ref | Value | Function |
|-----|-------|----------|
| LEVEL (VR2) | 100k **A taper** | OD volume divider: pin3=IC4_A out, pin1=VD, wiper=leveled OD → BLEND pin3 |
| BLEND (VR1) | 100k **B taper** | crossfade: pin3=leveled OD, pin1=clean (IC1_A out), wiper=mix → IC5_A(+) |

### EQ path — buffer, gain, 4-band active Baxandall (IC5_A/B/C/D, IC6_A)
| Ref | Value | Function |
|-----|-------|----------|
| IC5_A | TL074ACN | unity buffer (post-blend) |
| R28 / R29 | 10k / 22k | IC5_B inverting gain = −R29/R28 = **−2.2×** |
| IC5_B | TL074ACN | inverting gain stage |
| C21 | 100n | coupling into tone stack |
| **BASS** VR4 (LO) | 100k B | R33(10k), R34(10k), C25(22n), C26(22n), out R35(10k). ±12 dB @ ~100 Hz |
| **TREBLE** VR5 (HI) | 100k B | R36(3k3), C28(10n), C29(10n). ±12 dB @ ~5 kHz |
| IC5_C | TL074ACN | Baxandall summing amp for BASS+TREBLE: R37(1M)∥C30(47pF) fb; out C31(2u2) |
| **LO-MID** VR6 | 100k B | R38(2k2), R39(2k2), R40(220k), R41(220k), C32(22n across); around IC5_D. **C33 switchable** (see below) |
| IC5_D | TL074ACN | LO-MID peaking-filter amp |
| **HI-MID** VR7 | 100k B | R42(2k2), R43(2k2), R44(220k), R45(220k), C34(6n8 across); around IC6_A. **C35 switchable** (see below) |
| IC6_A | TL074ACN | HI-MID peaking-filter amp |

**Switchable mid-frequency caps [ENG-caps]** — 3-position selector per band swaps the *series* cap
only (nearest E12; computed from p.3 Ultra-Mod f-vs-C fit, f ∝ 1/√C_series):

| LO-MID (C33) | centre | | HI-MID (C35) | centre |
|---|---|---|---|---|
| 47n | 250 Hz | | 15n ⚠ | 750 Hz (large extrapolation — validate) |
| 10n | 500 Hz (fit-exact; table-confirmed) | | 3n3 | 1.5 kHz (table-confirmed) |
| 2n2 | 1 kHz | | 820pF | 3 kHz |

> Original board's fixed values were C33=22n (~340 Hz) and C35=680pF (~3.3 kHz). Model each mid band
> as a switched topology: the series cap is the only thing that changes → an `ImpedanceCalculator`
> that reads the port impedance live recomputes correctly on cap swap (no per-position precomputed
> matrix needed — see `dsp.md` "Fixed (non-runtime) circuit variants" reasoning, applied per switch
> position). The 750 Hz hi-mid cap is extrapolated well past the documented table floor (1.5 kHz) —
> flag for validation; it may want a different value once the peaking transfer function is simulated.

### MASTER volume [ENG] — designed post-EQ stage
| Ref | Value | Function |
|-----|-------|----------|
| **MASTER (VR8)** | 100k **A taper** [ENG] | overall output volume; also sets the XLR DI level. Post-EQ divider: top = HI-MID (IC6_A) output via C36, bottom = VD, wiper → IC6_B (+). Unity at full CW. |

> **MASTER placement [ENG].** Real Ultra's Master is the last control and governs both the ¼" out and
> the DI. Cleanest faithful placement: insert as a divider between the EQ end (IC6_A → C36) and the
> output buffer IC6_B — so IC6_B buffers the post-Master signal feeding BOTH ¼" (R47) and the XLR DI.
> No new op-amp needed (reuses IC6_B). Calibrate unity/headroom at build (calibration doc §2); a small
> make-up may be wanted since a post-EQ divider can only attenuate.

### Output (¼" jack) — IC6_B
| Ref | Value | Function |
|-----|-------|----------|
| IC6_B | TL074ACN | unity output buffer |
| C37 | 2u2 | output coupling |
| R47 | 1k | series output resistor (= spec's 1kΩ output Z) |
| R46 | 100k | output pulldown to GND |

### NOT MODELLED (per project scope)
- **XLR balanced DI:** IC6_C (buffer, R48 1k), IC6_D (inverting −1, R49/R54 10k), R50/R51/R52/R53,
  C38/C39 (1µF), C37-side network → XLR HOT/COLD/SHIELD, ground-lift switch. Backup note: *"If XLR
  components are not needed, do not populate: U7, R47–R52, C37, C38."* Skip.
- **Parallel/thru out:** none present (only the X2R input jack normalling). Skip.
- **Power section beyond VD/rail:** D3 (1N5817), C22 (100µF), C23 (330n), R30/R31 (VD divider),
  C24 (100µF), R-LED (4k7) + D4 (red LED status). Only relevant fact: **9V unmodified, VD = 4.5V.**

### Nonlinear devices
- **D1, D2 = 1N4148** (rail clamps, rarely conduct): Is≈2.52e-9, Vt≈25.85e-3, n≈1.752. `nDiodes`
  in chowdsp = ideality factor n, NOT a count.
- **D3 = 1N5817** Schottky (supply, not signal). **D4 = 3mm red LED** (status, not signal).
- **IC3 = CD4049UBE** CMOS inverter — the real nonlinearity. Model its transfer curve (fit to
  CD4049UB datasheet Vin/Vout, or to a capture) inside the shunt-feedback gain. See `dsp.md` AND
  **`docs/nonlinear-component-modeling.md` §1** (DAFx-2020 "Red Llama" model + fitted params, TI
  datasheet, recommended asymmetric-tanh-VTC-waveshaper approach; PDFs in `docs/refs/`).
- **Q1, Q2 = J201** N-channel JFETs — active gain stage (Q1 common-source, Q2 active load).
  Modellable; large-signal square-law (Shichman-Hodges) or a fitted gain+soft-waveshaper. See `dsp.md`
  AND **`docs/nonlinear-component-modeling.md` §2** (SPICE param sets, WDF-JFET papers, the ~5:1
  part spread → fit-to-capture; PDFs in `docs/refs/`). **These two (CD4049UBE + J201) are the ONLY
  non-WDF-native parts** — everything else is R/C/ideal-op-amp/diode. See that doc's §4 capture list.

## Topology — node graphs

Confirmed stages (linear op-amp stages are standard non-inv/inv/SK topologies — build directly).
Two areas still need explicit per-terminal node confirmation before WDF (flagged **VERIFY**).

### IC1_A input buffer — **Linear**, trivial (voltage follower)
Non-inverting unity buffer. (+)=input via R3; (−)=output (pin1). Output node feeds C2 (drive) AND
the long clean wire to BLEND lug 1.

### JFET stage (Q1/Q2) — **Nonlinear (active)**, needs a JFET device model
```
Node "Q1 gate"  : R4 leg2, R5 leg1(?), Q1 gate    (signal in from buffer via C2→R4)
Node "Q1 source": Q1 source, R6 leg1, C3 leg1     (R6∥C3 other legs → GND)
Node "OUT/G"    : Q1 drain, Q2 source, R7 leg1     (this is the stage output → treble net)
Node "Q2 gate"  : R9/R10 divider mid (+4.5V), C4 leg1
Node "OUT/G"    : Q1 drain, Q2 source, R7 leg1, **C4 leg2** (C4 bootstraps gate→source, verified — NOT to GND)
Q2 drain → +9V.
```
Not a WDF-native element — implement Q1/Q2 as a coupled JFET pair solve, or fit to captures (`dsp.md`).

### Treble network + ATTACK (SW1) — **Linear, switched** — ✅ **NODES VERIFIED (2026-07-19)**; pos3 [ENG]
Node graph confirmed at pixel zoom (primary p.4):
```
Top rail : OUT/G ─R7(200k)─ M ─R8(470k)─ P ─(→ R11(470k)→GND, C7(100n)→IC2_A)
Lower    : G(pre-R7) ─C5(22n)─ L1 ─C9(22n)─ L2 ─C6(22n)─ L3
           L1 ─R12(6k8)─ GND ;  L2 ─R14(22k)─ GND
Ties     : L3 = M (C6-right tied up to the R7/R8 junction) ;  ULTRA-HI common (pin1) = M
Switch   : Boost(pin2)=C8(220pF) bridges R8 (M↔P) ; Cut(pin3)= M→GND directly ; Flat[ENG]=common open
```
So R7/R8 are the series top-rail; C5/C9/C6 a parallel series-cap ladder (G→M) with R12/R14 shunting
the two intermediate cap nodes to GND. All values match the tables. (Previously the least-confirmed
node graph in the path; now fully traced. Flat centre is the engineered addition, not on schematic.)

### IC2_A DRIVE — **Linear** (non-inv gain), DRIVE pot is a rheostat in the gain leg
```
Node "(−)"     : R15 leg1, C10 leg1, R17 leg1
Node "out"     : IC2_A out(pin1), R15 leg2, C10 leg2
Gain leg: (−) → R17(3k3) → DRIVE(wiper+one lug, rheostat) → R32(1k) → VD.
```
DRIVE = variable resistance to AC ground → gain sweeps. Coupled to level (see Interactive).

### GRUNT (SW2) + clipper input — **Linear switched** feeding **Nonlinear** node
C11 always in forward path; SW2 (On-Off-On) adds C12 or C13 (or neither) in parallel → sets the
HF/bass content into R16. Three positions = three effective coupling caps: 4n7 / 4n7∥47n / 4n7∥220n.

### CLIPPER (IC3 CD4049UBE) — **Nonlinear** (CMOS inverter, shunt feedback)
```
Node "W" (4049 in, pin3): R16 leg2, R18 leg1, C14 leg1, D1 anode, D2 cathode
Node "clip out" (pin2)  : IC3 out, R18 leg2, C14 leg2, C15 leg1
D1 cathode → +9V ; D2 anode → GND.
```
Model: inverter transfer curve (fit) with R16 input / R18‖C14 shunt feedback; D1/D2 as hard clamps
to +9V/GND at node W. Not a standard op-amp — see `dsp.md` CMOS section.

### IC4_B / IC4_A — **Linear** 2nd-order Sallen-Key low-pass (unity gain), build directly.
### IC5_A/B — buffer + inverting gain (−2.2), **Linear**, direct.
### Baxandall BASS/TREBLE (IC5_C), LO-MID (IC5_D), HI-MID (IC6_A) — **Linear active tone**
Standard active Baxandall (bass/treble) + two peaking mid stages. Pots are dividers with end lugs
across the cap networks, wipers to the summing/feedback nodes. Full per-node redraw recommended
before building the tone stack (values captured above; node detail is the remaining work here).
### IC6_B — unity output buffer, **Linear**, direct.

## Op-amp model
- **TL072ACP / TL074ACN**, single +9V/GND supply (VD=4.5V). NOT rail-to-rail → model asymmetric
  output saturation clamped roughly to [~1.2 V, ~7.8 V] (≈1.2–1.5 V from each rail) — calibration §6.
- Use ideal op-amp for the gain/feedback solve; apply rail saturation as a separate output clamp.
- **CD4049UBE** is the exception: model its full soft transfer curve (it IS the clipper), clamped to
  0–9V, not an ideal op-amp.

## Interactive / coupled controls
- **DRIVE (VR3)** sits in IC2_A's feedback gain leg → it changes gain, and (via output level) is
  perceptually coupled to LEVEL. Model the gain-leg resistance directly; re-check output level after.
- **BLEND (VR1) + LEVEL (VR2)**: LEVEL scales the OD, BLEND crossfades OD↔clean. Not a shared WDF
  network (they're plain dividers/crossfade), but model as the crossfade described above, not two
  independent gains.
- **MASTER (VR8) [ENG]**: post-EQ output volume; governs BOTH the ¼" out and the XLR DI level (they
  share IC6_B). Model as a divider before IC6_B, not a per-output gain.
- **4-band EQ**: BASS+TREBLE share the IC5_C summing node (one Baxandall network — model coupled).
  LO-MID and HI-MID are separate peaking stages. Use `ScopedDeferImpedancePropagation` if several
  band pots are updated in one block.
- **ATTACK / GRUNT / mid-freq selectors**: switched topologies (precomputed matrix per position, or
  a live `ImpedanceCalculator` for the mid cap swaps), not continuous.

## Multi-stage / multi-channel series pedals
**N/A** — this is a single signal path, not a dual/stacked pedal. There is one clean tap (for BLEND)
but no second independent gain circuit. Model as one chain with a parallel clean branch summed at
BLEND. **Two footswitches** control it (main true-bypass + a second DIST-engage that overrides the
BLEND crossfade) — see Footswitches below; this is an Ultra-only addition, not a second gain stage.

## Validation notes
- **C33 (LO-MID series cap): primary schematic p.4 = 22n AND BOM = 22n → use 22n.** Backup schematic
  (2021 "B7X" rev) shows 2200pF for the equivalent cap — a **revision difference**, not our board.
  Confirmed by zooming both the schematic symbol and the BOM table.
- **GRUNT cap C13: primary = 220n; backup = 22n.** Different revision. Using primary (220n); re-zoom
  the primary GRUNT symbol if the modelled bass-into-clip corner looks wrong.
- **IC3 marked "4049N" on primary, "CD4049UBE" on backup.** Both = unbuffered CD4049UB. Use the
  **unbuffered (UB)** transfer curve (single inverter stage), NOT the buffered CD4049 (3-stage).
- **Ultra-Mod (primary p.3)** describes optional swappable LO-MID/HI-MID caps (remove C33/C35, add a
  toggle). Those toggles are NOT populated on the stock board → mids are **fixed frequency**. The
  Ultra-Mod table's "stock" values (C33=10n, C35=680pF) are the *real Darkglass* references and
  differ from this clone's actual C33 (22n). Model the board's values (BOM/schematic), not the mod.
- **D1/D2 orientation confirmed at pixel zoom**: both cathode-up (D1 cathode→+9V, D2 cathode→node W),
  i.e. rail clamps around the ~4.5V self-bias — verified because a naïve reading makes them
  permanently forward-biased, which is impossible (see clipper node graph).
- **Q1/Q2 role confirmed** as an active gain stage (Q1 CS + Q2 active load), NOT analog switches —
  do not model as a switched topology.
- **R19 (1k) — OPEN ITEM.** Present in the primary BOM (R19 = 1k) but not located in the traced
  signal path (input→buffer→JFET→treble→drive→grunt→clipper→recovery→SK→SK→level→blend→EQ→out is
  complete without it; the clipper→recovery run is C15/R20 only). Likely a small series/isolation
  resistor in the clean-blend tap or a utility position. Not signal-critical (1k into a high-Z node
  is negligible), but confirm its node during layout/DSP so the BOM fully reconciles.
- **BOM ↔ circuit.md reconciled (2026-07-19):** every R (R1–R54), every C (film + electrolytic),
  all ICs (IC1/2/4=TL072ACP, IC3=4049N, IC5/6=TL074ACN), Q1/Q2=J201, D1/D2=1N4148, D3=1N5817,
  D4=LED, and all pot **tapers** (BLEND 100k B, DRIVE 100k C, LEVEL 100k A, HI/LO/HI-MIDS/LO-MID
  100k B) match. BOM lists **7 pots (no MASTER)**, **Ultra-Hi = SPDT On-On (2-pos)**, and **one
  3PDT stomp** — independently confirming the MASTER volume, the 3-way ATTACK, and the 2nd DIST
  footswitch are all [ENG] (not on this board).

### Ultra build — engineered deviations from the schematic (decided 2026-07-19)
Target = **B7K Ultra**, but our schematic is the original B7K. These parts are **engineered**, not
schematic-verified — behaviourally faithful to the Ultra, tuned/validated later:
- **[ENG] MASTER volume (VR8, 100k A)** — designed post-EQ divider feeding IC6_B (drives both ¼" +
  XLR DI). Not on any schematic. Placement/behaviour per the note in the MASTER table above.
- **[ENG] 3-way ATTACK** — schematic's 2-position ULTRA-HI (Boost/Cut) extended to On-Off-On with a
  centre Flat (C8 disconnected). Base network nodes still need lug-level verification.
- **[ENG-caps] Switchable mid frequencies** — 3-position selectors, caps **computed** (E12) to hit the
  real Ultra centres, anchored to the p.3 Ultra-Mod measured f-vs-C tables (clean fit f ∝ C^−0.49):
  Lo-Mid 250/500/1k = 47n/10n/2n2; Hi-Mid 750/1.5k/3k = **15n(⚠ extrapolated)**/3n3/820pF. The
  10n→500 Hz and 3n3→1.5k points are table-confirmed; 750 Hz is well past the table floor — validate.
- `info.txt` (Ultra spec) is now the **control/behaviour reference** (Master, Attack Boost/Flat/Cut,
  switchable mid ranges). Its mid ranges (Lo 250/500/1k, Hi 750/1.5k/3k) are the switch targets.
- **What did NOT change:** JFET front end, CD4049UBE clipper (+ D1/D2 clamps), IC2_A DRIVE, GRUNT,
  recovery + 2× Sallen-Key LPF, BLEND/LEVEL, base EQ topology, output buffer, power — all remain
  schematic-verified as originally analysed.

## Footswitches [ENG — new, 2026-07-19]

BOM lists only **one** 3PDT stomp switch (true bypass). Web research confirms the real Ultra has a
**second, dedicated footswitch** that engages/disengages just the overdrive section, independent of
main bypass — lets the unit run as an always-on clean EQ/DI preamp with drive stomped in on top,
without disturbing bypass state. Not derivable from our schematic; design as:

- **Main bypass** (existing pattern, `architecture.md` "Bypass"): dry routed around the whole chain,
  ~5ms crossfade, `bypass` APVTS bool.
- **DIST engage [ENG]** (new, second bool `dist_engage`, default true): when disengaged, forces the
  BLEND crossfade to 100% clean (ignoring the BLEND knob position) with its own short crossfade —
  functionally mutes the OD contribution while EQ/MASTER/output stage keep processing the (now-clean)
  signal, matching the reviewed behaviour ("toggle distortion independently without affecting the
  rest of the pedal's preamp and EQ"). NOT a second true-bypass loop — implement as a target-mix
  override on the existing BLEND crossfade, not a second dry/wet path.
- Two independent 3PDT-style momentary/latching footswitch inputs needed in the UI/APVTS layer.
