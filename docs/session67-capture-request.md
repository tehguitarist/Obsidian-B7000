# Capture request — **2 files**, the ATTACK pair at drive noon / LEVEL max

> Raised session 67. **Two files, ~3 minutes.** Everything else needed is already on disk. This is
> the "Optional" pair session 59 flagged and never required — it is now the decisive test for the
> open A3 broadband-SHAPE question (session 66 item (a) / session 60 item 11 / session 61 item 5).

## The two files

Put them in `analysis/captures/`. Filenames follow the existing grammar exactly (no `drive-` token
= drive noon, the default):

```
level-1700_attack-boost_base-od.wav
level-1700_attack-cut_base-od.wav
```

## Settings

Identical to the existing `level-1700_base-od.wav` take in every respect **except** the ATTACK
switch:

| control | setting |
|---|---|
| DRIVE | **noon** (the default — do NOT set to minimum this time) |
| **LEVEL** | **fully clockwise (maximum, 5 o'clock)** |
| BLEND | **fully clockwise (maximum OD, 5 o'clock)** |
| ATTACK | **Boost** (file 1) then **Cut** (file 2) — mechanical CENTRE is Boost, DOWN is Cut |
| MASTER | noon |
| LO / LO-MID / HI-MID / HI | all noon |
| LO-MID freq / HI-MID freq | centre (1 kHz / 3 kHz) |
| GRUNT | **Cut** (mechanical centre — the least-bass position) |
| DIST footswitch | engaged |

⚠ **Check LEVEL and BLEND are both at MAX before each take**, and that the only knob you move
between the two files is ATTACK. Session 54 lost a file to MASTER being left at 1430 instead of
BLEND, caught only by a purpose-built geometric test — worth a visual double-check here too.

**Headroom is fine** — `level-1700_base-od.wav` (the existing flat-ATTACK reference at this exact
operating point) already peaks at 0.417 at drive noon. No need to drop the interface send.

## Why this pair, and what it decides

At **LEVEL max the wiper shorts to the OD source, so the clean BLEND bleed is EXACTLY zero**
regardless of DRIVE (`eq_reference.level_blend_tf`), and **LEVEL sits after every nonlinearity**
(circuit.md), so raising it cannot move the clipper's operating point. So at BLEND max the output
simply **is** the OD path at whatever drive is set — the same bleed-free mechanism session 60 used
at drive min, now at drive **noon**, where the clipper is doing real work instead of idling.

```
h(f)  =  pedal_db(level-1700_attack-boost_base-od)  −  pedal_db(level-1700_base-od)
h(f)  =  pedal_db(level-1700_attack-cut_base-od)     −  pedal_db(level-1700_base-od)
```

**The open question this settles:** at drive min (the pair already captured and analysed through
session 66), the model's ATTACK cut throw shows broadband slope **≈0 dB/dec** against the pedal's
measured **−1.38 dB/dec** (spread 5.14 dB vs the pedal's 2.62 — 2–3× too broad), while boost is
close. Two live explanations, and this pair tells them apart:

1. **A genuine ATTACK-network defect** (the two-pole topology's cut throw is structurally wrong) —
   if so, the drive-noon `h(f)` for cut should show the **same** near-zero slope / wide spread the
   drive-min data already shows.
2. **An LF common-mode error in the reference or extraction machinery**, not the ATTACK network
   itself — session 60 item 11 found the drive-min bleed-free route disagrees with session 58's
   drive-noon de-convolved route by an offset that is **positive at every band and largest at LF**
   (the signature of a shared-reference or `b0`/taper error, not a per-throw one). If that is the
   real cause, this pair — same bleed-free method, same throws, different drive — should show
   **cut's slope much closer to the pedal's −1.38** than the drive-min data does, because it removes
   whatever is specific to the drive-min operating point.

Either answer moves the investigation forward: (1) means the cut-throw topology needs more work;
(2) means the drive-min extraction (or the `flat` reference it divides by) has an error to chase
down, and it is NOT the ATTACK network's fault.

## Already on disk — do not re-record

- `level-1700_base-od.wav` — the flat-ATTACK reference for the subtraction, at this exact operating
  point (drive noon / LEVEL max / BLEND max)
- `drive-0700_level-1700_attack-{boost,cut}_base-od.wav` — the drive-min companion pair, already
  captured and analysed (sessions 60–66)
- Everything from sessions 53, 58, 59, 60

## Known gaps this request deliberately does NOT cover

- **320 Hz stays a notch-window exclusion, not a gain read**, in every condition — see
  `analysis/attack_notch_probe.py` / `attack_render_gate.py`'s NOTCH WINDOW handling. Do not read a
  band average across it as a level.
- **Phase is still unmeasured.** This axis is magnitude-only, so `h(f)` remains a minimum-phase
  specification.
- **ATTACK remains `[ENG]`** — the 3-way switch is not on our schematic at all, so `h(f)` is a
  specification a topology proposal must MEET, not a disagreement with a drawn circuit.
