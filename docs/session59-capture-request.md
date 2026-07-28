# Capture request — **2 files**, the ATTACK pair at drive min / LEVEL max

> Raised session 59. **Two files, ~3 minutes.** Everything else needed is already on disk.
> This request supersedes `docs/session58-capture-request.md`, whose six files were captured,
> verified sound, and could not be read — see "Why the last request didn't work" below.

## The two files

Put them in `analysis/captures/`. Both verified to parse through `captures.parse_capture` and to
emit the correct `--attack 1` / `--attack 2` **and** `--level 1.000000` to `OfflineRender`.

```
drive-0700_level-1700_attack-boost_base-od.wav
drive-0700_level-1700_attack-cut_base-od.wav
```

## Settings

Identical to the existing `drive-0700_level-1700_base-od.wav` take in every respect **except** the
ATTACK switch:

| control | setting |
|---|---|
| DRIVE | **fully counter-clockwise (minimum, 7 o'clock)** |
| **LEVEL** | **fully clockwise (maximum, 5 o'clock)** ← the one that changed vs last time |
| BLEND | **fully clockwise (maximum OD, 5 o'clock)** |
| ATTACK | **Boost** (file 1) then **Cut** (file 2) — mechanical CENTRE is Boost, DOWN is Cut |
| MASTER | noon |
| LO / LO-MID / HI-MID / HI | all noon |
| LO-MID freq / HI-MID freq | centre (1 kHz / 3 kHz) |
| GRUNT | **Cut** (mechanical centre — the least-bass position) |
| DIST footswitch | engaged |

⚠ **Check LEVEL and BLEND are both at MAX before each take**, and that the knob you moved between
the two files is ATTACK. Session 54 lost a file to MASTER being left at 1430 instead of BLEND, and
it took a purpose-built geometric test to catch it.

**Headroom is fine** — the existing `level-1700_base-od.wav` peaks at 0.417 at drive *noon*, and
drive min is quieter still. No need to drop the interface send.

## Why these two, and why they will work

At **LEVEL max the wiper shorts to the OD source, so the clean BLEND bleed is EXACTLY zero**
(`eq_reference.level_blend_tf`: bleed −4.03 dB at LEVEL noon, −17.09 at 0.90, −36.91 at 0.99, **zero
at 1.00**). And **LEVEL sits after every nonlinearity** (circuit.md: `… → IC4_A SK → LEVEL → BLEND`),
so turning it up cannot move the clipper's operating point. So at BLEND max the output simply **is**
the OD path, and

```
h(f)  =  pedal_db(drive-0700_level-1700_attack-boost_base-od)
       − pedal_db(drive-0700_level-1700_base-od)
```

is the ATTACK network's linear transfer **directly** — no ladder, no BLEND taper, no bleed level
`b0`, no solve, no de-convolution, and no describing-function caveat. Two subtractions.

**This is validated, not predicted.** `drive-0700_level-1700_base-od.wav` already exists, so the
instrument was tested on it before this request was written (`analysis/attack_drive_axis.py` step 6).
Referencing it to `blend-0700_base-od.wav` (pure clean, LEVEL-independent) gives the OD path
directly:

| |G|, drive min / LEVEL max | 80 | 101 | 127 | 160 | 202 | 254 | 403 | 508 | 640 | bridged-T scoop |
|---|---|---|---|---|---|---|---|---|---|---|
| −30 dBFS | −14.5 | −11.3 | −9.2 | −7.9 | −7.3 | −8.6 | −13.5 | −12.5 | −14.1 | **6.0 dB** |
| −18 dBFS | −14.5 | −11.3 | −9.1 | −7.9 | −7.3 | −8.5 | −13.5 | −12.6 | −14.2 | **6.1 dB** |
| −6 dBFS | −14.3 | −11.0 | −8.7 | −7.8 | −6.5 | −10.7 | −15.2 | −14.9 | −16.2 | 9.0 dB |

Three things to read there: the **IC2_B bridged-T scoop is present at 6.0 dB** (it was *absent*,
0.7 dB, in the failed LEVEL-noon route — the known-feature test that condemned it); **|G| is up
~8 dB** into the well-conditioned range; and the **−30 and −18 dBFS rows agree to ~0.1 dB**, which is
the near-linearity drive min was wanted for in the first place. (The −6 dBFS row does compress —
that is the J201, which sits *upstream* of DRIVE and so never idles. Read −18 dBFS.)

## Why the last request didn't work — worth reading before designing the next one

`docs/session58-capture-request.md` argued: at drive min the compression budget → 0, so the measured
boost/flat ratio simply **is** `h(f)`. The clipper half of that is true. What it missed is that the
**same low drive that idles the clipper also drops the OD path ~15 dB below the clean bleed**, and
the blend axis measures precisely that ratio. The ladder `t(B) = |β(B) + B·G|` then degenerates to
`β(B) + B·Re(G)`: only the projection survives, `(r, θ)` collapse to a ridge, and the fitted BLEND
taper absorbs the ATTACK effect. Session 47 item 11's small-µ degeneracy, at a new operating point.

⭐ **The general lesson: the DRIVE axis trades compression against sensitivity in BOTH directions.**
Drive min removes the clipper but buries the signal; drive max exposes the signal but compresses the
effect away (measured: a +8 dB `h` arrives as +0.45 dB). Drive noon is the sweet spot, not an
unfortunate compromise. **LEVEL is the right knob for this job** because it changes the OD/bleed
balance *without* touching the clipper at all.

## Already on disk — do not re-record

- `drive-0700_level-1700_base-od.wav` — the flat-ATTACK reference for the subtraction
- `blend-0700_base-od.wav` — pure clean, the reference that turns the pair into absolute `|G|`
- Everything from sessions 53 and 58, including all 15 files captured for the last request

## Optional, if you are set up anyway (not required)

- `level-1700_attack-boost_base-od.wav` and `level-1700_attack-cut_base-od.wav` — the same pair at
  **drive noon**, which would re-measure session 58's de-convolved `h(f)` with a bleed-free
  instrument and so test that de-convolution head-on at the condition it was derived from. Valuable,
  but the two required files above are what decide 403–640 Hz.

## Known gaps this request deliberately does NOT cover

- **320 Hz stays blind** on the blend axis in every condition (null-dominated). Note the LEVEL-max
  route does *not* inherit that limitation, since it involves no cancellation solve — 320 Hz should
  be readable for the first time, but that is a bonus, not a promise.
- **Phase is still unmeasured.** This axis is magnitude-only, so `h(f)` remains a minimum-phase
  specification.
- **ATTACK remains `[ENG]`** — the 3-way switch is not on our schematic at all, so `h(f)` is a
  specification a topology proposal must MEET, not a disagreement with a drawn circuit.
