# Circuit Reference — <PEDAL NAME>  (TEMPLATE — fill in from the schematic)

> This file is the **source of truth** for component values and topology. Fill every `<...>`
> placeholder by reading the schematic directly. Do NOT approximate or copy values from a build
> kit / forum trace without confirming against the primary schematic.

## Schematics

List every image in `schematics/` and its role (which is authoritative for what):

| File | Role |
|------|------|
| `<primary>.png` | Primary source of truth for values + topology |
| `<switch_ref>.jpg` | Authoritative for switch/diode network |
| `<older>.png` | Cross-reference only — values may differ |

### Crop index (for fast lookup — fill in as you crop)

When you crop sections out of a schematic image for closer reading, record what each crop actually
contains so a later question ("where's the tone stack drawn?") is a table lookup, not a re-scan of
the full image:

| Crop file | Source image | Contains |
|-----------|--------------|----------|
| `<e.g. crop_input.png>` | `<primary>.png` | `<e.g. input jack -> bias network -> stage 1 input>` |
| `<crop_clip.png>` | `<primary>.png` | `<e.g. clipping diode network + drive pot feedback leg>` |
| `<crop_tone.png>` | `<primary>.png` | `<e.g. tone stack + recovery stage>` |
| `<crop_switch.png>` | `<switch_ref>.jpg` | `<e.g. mode switch + diode selection network>` |

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

```
IN → <input/bias> → <stage 1 ...> → <clip?> → <tone?> → <recovery> → <volume> → OUT
```
VREF = VCC/2 virtual ground; model bipolar (VREF = 0 V signal ground). Note the supply (e.g. single
9 V, no charge pump) since it sets op-amp output headroom — see calibration doc §6.

## Component values (from `<primary>` — do not approximate)

### <Stage / network name>
| Ref | Value | Function |
|-----|-------|----------|
| `<R?>` | `<value>` | `<role>` |
| `<C?>` | `<value>` | `<role>` |
| `<pot>` | `<A/B + value>` | `<taper + role>` |

(Repeat a table per network: input, each gain stage, clipping/diode network, tone, recovery,
output volume.)

### Nonlinear devices
- Diode/transistor type: `<e.g. 1N4148>`. **Use exact datasheet/Shockley params** (Is, Vt, n, Rs).
  `nDiodes` in chowdsp = ideality factor n, NOT a count.

## Topology — node graphs

Describe each stage's connections at the node level (use these directly to build the WDF tree).
Mark each stage **Linear** or **Nonlinear**, and which adaptor type it needs (series/parallel tree
vs R-type for feedback). For switched sub-circuits, list each position as a distinct topology →
precomputed scattering matrix.

**This is the section worth the most re-checking effort.** If the component list (values, refs)
for a stage is already filled in above, don't spend more analysis time re-confirming those values —
put it into the node graph instead: for every named node in the stage, list every part terminal
that lands on it. A minimal per-node entry looks like:

```
Node <name> (e.g. "op-amp (-) input"):
  <R1> leg 2, <C3> leg 1, <pot P1> wiper — no other connection
```

Pay special attention to two node-reading mistakes that are easy to make from a schematic image and
hard to catch later without a redraw:

- **Pot wiper wiring.** For every pot, state explicitly which node each of the three terminals
  (lug 1, lug 3, wiper) connects to, and whether the wiper feeds a **divider** (both end lugs
  connected, wiper taps between them) or a **rheostat** (one end lug jumpered to the wiper or left
  open, so only a variable series/shunt resistance is in play). These two wirings produce very
  different transfer functions from the same pot value, and the schematic symbol looks almost
  identical for both — trace the actual lug connections, don't infer from context.
- **Bridging capacitors/resistors.** Any part that connects two nodes that aren't simply "next in
  the chain" (e.g. a small cap from an op-amp output back to its own (−) input, or a resistor from
  a tone pot wiper to a node in a different stage) changes the topology at both ends it touches —
  it usually means an R-type feedback adaptor is needed rather than a plain series/parallel tree.
  List these explicitly with BOTH nodes they touch, not just "near <stage>".

For switched sub-circuits, apply the same node-level treatment to each position independently
before precomputing its scattering matrix — a position that looks like a value swap can actually
reroute a bridging part to a different node.

## Op-amp model

- Part + supply; not rail-to-rail → model asymmetric output saturation (calibration doc §6).
- Ideal op-amp for the gain/feedback solve; rails as a separate output clamp.

## Interactive / coupled controls

List any controls that share a network and MUST be modelled coupled (not independent), e.g. a tone
control inside a feedback web. Note `ScopedDeferImpedancePropagation` when updating them together.

## Multi-stage / multi-channel series pedals

If the unit is actually two (or more) complete, otherwise-independent gain circuits in series —
each with its own controls and its own bypass — model each as its own instance of the same
per-channel DSP class, instantiated once per stage, NOT as a single wider circuit. Each instance
needs its own independent bypass/crossfade so the hardware's independent footswitches are honoured.

A fixed factory/kit modification present on only ONE of the otherwise-identical stages (not a
runtime-switchable mode) belongs at **construction time**, not as an APVTS parameter — see
`dsp.md` "Fixed (non-runtime) circuit variants".

Document the verified real processing order explicitly here (see the gotcha above) and keep it
separate from whatever names/labels the UI uses for each stage — naming and signal order are
independent facts and don't have to agree (see `architecture.md` / `ui.md` if the two diverge).

## Validation notes

Record anything that differs between schematic versions, any component absent from some traces, and
any value you had to resolve by measurement/judgement (with the reasoning).
