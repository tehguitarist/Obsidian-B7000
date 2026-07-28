# Capture request — 6 files, the ATTACK drive-min blend ladder

> Raised session 57 (§5), re-scoped and made more urgent by session 58. **Six files, one sitting,
> ~10 minutes.** Everything else needed already exists on disk.

## Why these six

The ATTACK switch is `[ENG]` — it is not on our schematic at all — so the only way to model it is
to measure it. Sessions 55–57 established *what it does* but every one of those numbers is a
**describing-function** ratio: all six existing `attack-*_blend-*` captures are at **drive noon**,
where the clipper has already compressed part of the effect away before it reaches the output.

Session 58 de-convolved the clipper arithmetically (`analysis/attack_linear_extract.py`) and it
works over **80–254 Hz**, but it runs out of resolving power at **403–640 Hz** — exactly the bands
where the pedal's own OD transfer barely compresses (its "compression budget" there is 0.75–1.42 dB),
so there is nothing for the de-convolution to work with, and the measured level swing of 4.9–6.9 dB
cannot be attributed cleanly.

**At drive min the problem disappears rather than shrinking.** The OD path is near-linear, so the
compression budget goes to ~0 at every band and the measured ratio **is** the ATTACK network's
linear transfer directly — no de-convolution, no describing-function caveat, no arithmetic at all.
That is the difference between "h ≈ +7 to +8 dB over 80–254 Hz, with 403–640 Hz undecidable" and a
clean linear transfer across the whole band.

It is also a **falsification test**, not just a refinement: if the drawn ladder topology were right,
the drive-min ratio would have to equal the ladder's own linear ratio *exactly* (−0.02 dB at 80 Hz,
+0.43 dB at 640). Session 57 measured +6.82 and −1.26 at drive noon and had to argue the gap was not
a clipper artefact. At drive min there is no argument left to have.

## The six files

Put them in `analysis/captures/`. All six have been verified to parse through
`captures.parse_capture` and to emit the correct `--attack 1` / `--attack 2` to `OfflineRender`
(checked session 58 — the switch position is genuinely carried through, not silently dropped).

```
drive-0700_attack-boost_blend-0930_base-od.wav
drive-0700_attack-boost_blend-1200_base-od.wav
drive-0700_attack-boost_blend-1430_base-od.wav
drive-0700_attack-cut_blend-0930_base-od.wav
drive-0700_attack-cut_blend-1200_base-od.wav
drive-0700_attack-cut_blend-1430_base-od.wav
```

## Settings

Identical to the existing `drive-0700_blend-*_base-od` takes in every respect **except** the ATTACK
switch. From the reference OD setup:

| control | setting |
|---|---|
| DRIVE | **fully counter-clockwise (minimum, 7 o'clock)** |
| BLEND | **0930 / 1200 / 1430** — the three interior positions, one per file |
| ATTACK | **Boost** (3 files) then **Cut** (3 files) — mechanical CENTRE is Boost, DOWN is Cut |
| LEVEL | noon |
| MASTER | noon |
| LO / LO-MID / HI-MID / HI | all noon |
| LO-MID freq / HI-MID freq | centre (1 kHz / 3 kHz) |
| GRUNT | **Cut** (mechanical centre — the least-bass position) |
| DIST footswitch | engaged |

⚠ **The one that has bitten this project twice: check BLEND is the knob you moved.** Session 54 lost
`attack-cut_blend-1430_base-od.wav` to MASTER being left at 1430 instead of BLEND, and it took a
purpose-built geometric test to catch it. After each take, glance at BLEND and MASTER before moving on.

## Already on disk — do not re-record

- Drive-min FLAT ladder: `drive-0700_blend-{0930,1200,1430}_base-od.wav` + `drive-0700_base-od.wav`
- Both B=1 ATTACK anchors: `drive-0700_attack-{boost,cut}_base-od.wav`
- The shared B=0 normaliser: `blend-0700_base-od.wav`

## Known gaps this request deliberately does NOT cover

Recorded so they are not lost, none of them blocking:

- **320 Hz is blind on this axis in every condition** (null-dominated — an instrument property, no
  capture fixes it). 254 and 403 Hz bracket it.
- **Drive-min identifiability covers 101–1613 Hz**, losing 80 and 806 Hz relative to drive noon. The
  peak region survives, which is what matters here.
- `drive-1700_attack-cut_base-od.wav` is absent while `..._attack-boost_...` exists — an asymmetry in
  the matrix, not needed for this test.
- **There is no ATTACK-position B=0 control.** ATTACK should be exactly inert at BLEND=0 (the OD path
  is fully out of circuit), but that is an assumption; session 53 spent a capture verifying the
  equivalent assumption for DRIVE and it passed. Worth one extra file
  (`drive-0700_attack-boost_blend-0700_base-od.wav`) if you are set up anyway — it would let the
  ATTACK conditions be normalised against their own B=0 rather than the shared one.
