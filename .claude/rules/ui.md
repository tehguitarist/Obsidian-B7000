# UI Rules (generic pedal plugin)

> The full visual spec for the reusable peripheral elements (side panels, halo trim knobs, VU
> meters, oversampling strip, resizable UI, bypass footswitch, LED) lives in
> `docs/ui-peripheral-spec.md`, and the working code is in `src/ui/`. This file is the high-level
> contract; the spec is the detail.
>
> **This project also ships image assets in `ui/`** (knobs, footswitch up/down, LEDs on/off,
> 3-position switches, panel textures, VU trim) — PNGs with alpha, drawn at knob-noon, rotation-safe.
> Follow `ui/ui-replacements.md` when using them: keep 2× resolution at 100% UI scale (sharp up to
> 200%+), crop-to-fit (never stretch), and resize/convert copies to minimise plugin size (preserve
> originals). Prefer these for the centre pedal face; the procedural `PedalLookAndFeel` still owns
> the peripheral chrome (side panels, OS strip, VU bars).

## Centre pedal face (this pedal) — layout source & typography

**Layout will be data-driven, not hand-placed.** The user will provide a base image plus a CSV of
sizes/positions for the centre pedal face; build the layout from that CSV against the base image
rather than guessing coordinates from the `ui/` PNGs individually. Details of exactly which
elements the CSV covers (knobs only vs. knobs+switches+jacks, coordinate origin/units) are TBD until
it arrives — don't pre-build a layout system that assumes a specific CSV schema; confirm the schema
when the file lands.

**No bypass label needed for this pedal** — the base image already has one printed on it. Don't add
a code-rendered "BYPASS" text label near the footswitch the way a from-scratch build might.

**Only the 3-way switch selector options render text on the pedal face** (ATTACK Boost/Flat/Cut,
GRUNT's three positions, LO-MID/HI-MID frequency labels) — no other pedal-face element needs
code-rendered text; everything else is conveyed by the base image/knob graphics. This is exactly
`ThreePositionSwitch`'s label row (`src/ui/ThreePositionSwitch.h`).

- **Colour/opacity, not the current scheme:** selected option = **opaque white**; unselected
  options = **semi-opaque white**. This REPLACES the current `cSWLabelActive` (light blue
  `0x90C0E0`) / `cSWLabelInactive` (dark blue `0x3A5A78`) constants in `PedalLookAndFeel.h` — both
  need to become white at different alphas (exact unselected alpha TBD at implementation time, e.g.
  ~40–50%, confirm visually against the base image before locking a value).
- **Typeface: "Lexend Exa"**, for pedal-face text ONLY (i.e. these switch labels) — do NOT apply it
  to peripheral chrome text (OS/RENDER combo boxes, scale button, VU/trim labels, tooltips), which
  keep the existing default JUCE font per `docs/ui-peripheral-spec.md`. Lexend Exa is a Google Font
  (OFL-licensed) and is not a system font — embed the `.ttf` as binary data (`juce_add_binary_data`
  / `BinaryData.h`) and load it via `juce::Typeface::createSystemTypefaceFor()` rather than
  assuming it's installed on the build/user machine; don't skip this and fall back silently to a
  system font if the embed is missing.

Further pedal-face elements (knob arrangement, jacks, footswitch/LED placement) to be worked out
once the base image + CSV arrive — don't design that layout speculatively ahead of them.

## Principles

- One custom `LookAndFeel` subclass (`PedalLookAndFeel`) — no default JUCE styling anywhere.
- All drawing in LookAndFeel overrides; zero drawing in component or DSP logic.
- UI fully decoupled from DSP — the visual design must be replaceable without touching DSP.
- No `foleys_gui_magic` / XML-driven builders.
- All colours are named `static constexpr juce::uint32` on `PedalLookAndFeel` — never hardcode hex
  in component code. (The included palette is a dark-navy theme; recolour per pedal.)

## Reusable peripheral elements (provided, drop-in)

These are circuit-agnostic and ship in `src/ui/` — reuse as-is across pedals:
- **`PedalLookAndFeel`** — colour palette, pedal-face background (mottled), rotary knobs (pedal +
  halo trim styles via `componentID == "trim"`), **octagonal-nut + silver-dome bypass footswitch**
  (`componentID == "bypass"`), ComboBox styling, segmented-button styling.
- **`VUMeter`** — 22-segment bar, red/yellow/green zones, proportional gap. `setLevel(0..1)` from a
  `Timer`. ~300 ms release; idle-noise gate in the timer (calibration doc §7).
- **`ThreePositionSwitch`** — generic vertical toggle; `setLabels()`, `onChange(pos)`.
- **`LEDIndicator`** — `setOn(bool)`; green active / dark bypassed, with glow.

## Layout contract

Three-column layout: left side panel (Input: label + halo trim + VU), centre pedal face
(pedal-specific control arrangement), right side panel (Output: label + halo trim + VU), with a
full-width oversampling/scale strip below. Side-panel internals scale with whatever column width
you allocate, so the centre face is free to differ per pedal. See the spec for exact proportions.

**The VU meter and trim knob must stay inside their side-panel column's bounds at every scale
factor** — compute their sizes from the panel column's `Rectangle`, not from fixed pixel constants
that happen to fit at 100%. At the largest supported scale (2.5×, see Resizable UI) neither element
may overlap the centre pedal face or run past the plugin window edge; at the smallest (0.5×) neither
may collapse to an unusable/zero size before the panel itself does. Verify this by rendering the
editor headlessly (see `build.md`) at the min and max scale, not just at 100%.

The bottom strip holds the OS selectors (LIVE/RENDER) on the left and UI-scale on the right. If you
add an **HQ toggle** (see `dsp.md` "HQ / Eco mode"), place it **with the OS selectors** (it's a
quality control, not a window control) — a lit-on / dim-off toggle button immediately after the
RENDER box, with a brief hover tooltip. Keep it visually distinct from the scale/menu buttons. Add
the **Trim Link** toggle (see "Trims" below) to this same strip — it's a control-behaviour toggle
like HQ, so group it with HQ (or immediately after the OS selectors if there's no HQ toggle), not
with the window-management controls on the right.

**All selector-style controls in this strip — the LIVE/RENDER `ComboBox`es and the UI-scale
button — must render with the same visual language**: same rounded-rect background/border colours
(`cOSBtnActiveBg`/`cOSBtnActiveBdr`), same corner radius, same chevron, and the **same font size and
weight** (`getComboBoxFont()`'s 7 pt bold scale-derived size — don't let the scale button default to
a different `TextButton` font). Implement the scale button's background/border/chevron by routing it
through the same `drawComboBox`-shaped painting as the OS combo boxes (e.g. give it `componentID ==
"os-selector"` and branch on that in the relevant LookAndFeel overrides) rather than hand-rolling a
second, slightly-different style — see `docs/ui-peripheral-spec.md` for the exact styling code.

## Resizable UI

- `setResizable(true,true)` + `getConstrainer()->setFixedAspectRatio()` + `setSizeLimits()`
  (e.g. 0.5×–2.5× of a base size).
- Derive a scale factor in `resized()` from `getWidth() / kBaseW`; multiply every layout constant
  by it; call `refreshFonts(sc)` at the top of `resized()` (fonts must be re-set on resize, not in
  the constructor).
- Persist scale: per-session in `apvts.state` (`uiScale` property), cross-session default in
  `juce::ApplicationProperties`. Offer a scale popup with presets + "set current as default".
- **Corner-drag resize must update the stored size too, not just the scale popup path.** Both entry
  points (dragging the window corner and picking a preset from the scale popup) end up calling
  `resized()`, so writing `apvts.state.setProperty("uiScale", ...)` unconditionally inside
  `resized()` (not inside the popup's callback) already covers per-session persistence for both —
  don't gate that write on "came from the menu". For the cross-session default, debounce a save to
  `ApplicationProperties` off the same `resized()` call (e.g. a short `Timer` restarted on every
  call, firing ~500 ms after the last resize) so a drag-resize is remembered on next plugin open
  the same way "set current as default" is, without a disk write on every intermediate frame of the
  drag. Keep the explicit "set current as default" menu item too — it's still useful for saving a
  popup-picked preset immediately rather than waiting on the debounce.

## Metering & threading

- `juce::Timer` (~30 ms) reads `getInputLevel`/`getOutputLevel` and the **`bypass` parameter**
  (read APVTS directly so the LED updates immediately, even before audio runs — do NOT rely on the
  `bypassed` atomic, which is only written in `processBlock`).
- Parameter binding via `SliderParameterAttachment` / `ComboBoxParameterAttachment` /
  `ButtonParameterAttachment`. No direct DSP calls from UI.
- Apply the VU idle-noise gate (calibration doc §7) and re-check its threshold whenever the output
  makeup changes.

## Tooltips

Every knob — every pedal-face rotary AND both halo trim knobs — shows its current value as a
tooltip while dragging, formatted to **two decimal places** (e.g. `"3.00 dB"`, `"64.20%"`,
`"6800.00 Hz"` for a tapered pot expressed in its real-world unit). Use `Slider::setTextBoxStyle` in
`NoTextBox` mode (the value readout is the tooltip/label described here, not JUCE's built-in
text-entry box, which would clash with the pedal-knob visual style) and drive a
`SettableTooltipClient::setTooltip()` update from the slider's `onValueChange`/`onDragEnd`, e.g.:

```cpp
knob.onValueChange = [this] { knob.setTooltip(juce::String(knob.getValue(), 2) + " dB"); };
```

Pick the unit string per control (dB for trims, the pedal's native unit — %, Hz, or a plain 0–10
dial number — for pot controls) so the tooltip reads as a real-world value, not a raw 0..1.

## Trims

Input and output trim knobs use the **halo** style (`componentID == "trim"`) to stay visually
distinct from the pedal's own controls. Input trim sits pre-DSP (post → meter → chain); output trim
post-DSP (chain → meter → out).

Below each trim knob's "TRIM" sub-label, add a small non-interactive `juce::Label` showing the
current trim value to two decimal places (e.g. `"+3.00 dB"`), updated on the same
`onValueChange` as the tooltip above. This is a permanently-visible readout (unlike the tooltip,
which only shows while dragging) — see `docs/ui-peripheral-spec.md` for exact placement/sizing so
it doesn't collide with the VU bar beneath it.

A **Trim Link** toggle button (bottom strip, see Layout contract above) binds to the `trim_link`
APVTS bool (`architecture.md` "Input/output trim link"). While engaged, dragging either trim knob
nudges the other in the opposite direction by the same dB delta, so raising input drive doesn't
change the overall loudness. Style it like the HQ toggle (lit-on / dim-off `TextButton`,
`componentID == "os"`), labelled "TRIM LINK", with a brief tooltip explaining the compensation
behaviour.

## When a fixed name/position can't change but the underlying fact can

If a control's name or on-screen position is locked for compatibility/familiarity (e.g. it must
keep matching the hardware's physical layout) but you later learn an underlying fact about it has
changed (e.g. which one actually processes first — see `architecture.md`), don't silently rename or
reposition anything. Instead add a small, non-interactive label/badge near the control that states
the real fact directly (e.g. a processing-order marker), so the UI stays legible without requiring
the user to already know the internal correction. Keep it visually secondary (small, muted colour)
to the control's primary identity.
