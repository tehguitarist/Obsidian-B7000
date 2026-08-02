# Phase 9 — Reference validation (plugin vs the capture matrix)

> **The GATE-9 report: numbers, not adjectives.** How the plugin is A/B'd against the captures, the
> gaps found (with dB), the fixes shipped, and what is left.
>
> **Rewritten in session 89 (2026-07-31).** This file had reached 10,981 lines and its method and
> backlog were unreadable under ~9,000 lines of session narrative. That narrative is now
> **`docs/phase9-gap-log.md`** (verbatim, nothing deleted); the per-session handovers are
> **`docs/session-log.md`**; the generalisable traps are
> **`.claude/rules/measurement-discipline.md`**. Keep this file about METHOD and STATUS.
>
> **Read with:** `CLAUDE.md` (status + the release gate + next steps),
> `.claude/rules/reference-sources.md` (what the captures are),
> `docs/validation-and-capture.md` (measurement method), `.claude/rules/dsp.md` (fix rules).

> ⚠⚠⚠ **`analysis/captures/` IS A RECORDING OF THE NEURAL DSP DARKGLASS PLUGIN, NOT HARDWARE**
> (user-confirmed, session 71). Every "the pedal" in this file and in the gap log means the ND
> emulation. ND tracks hardware to ≤1.4 dB on the clean linear path — so the EQ, taper, level and
> topology work here is sound — but three things are aimed at the wrong target:
> **(a)** the "0.144 dB take-to-take floor" quoted throughout is not a physical noise floor;
> **(b)** session 70's rejection of the §2 repeatability set used a discriminator that is invalid
> against a deterministic renderer; **(c)** ⛔ **the even-order harmonic target is ~27 dB low.**
> ⇒ **a candidate that moves AWAY from the captures toward a documented hardware trend is a PASS,
> not a regression.** The matrix keeps authority only inside `reference-sources.md` §1's ND domains.

---

## 0. Status and backlog — START HERE

**The live status block, the agreed release gate and the ordered next steps are in `CLAUDE.md`
"Current step".** They are deliberately kept in one place; this section is the Phase-9-specific
detail behind them.

### Current grade (129 captures, shipped defaults, `analysis/reports/s91_shipped.json`)

Graded **25 Hz – 16.3 kHz** on the **H1-only, band-averaged** FR read (session 90 — see "The FR
instrument" below). Membership is identical to the s90 and s74 baselines (504 shared rows, 0
exclusive), so all three ARE comparable; the s74 figures were 2.743 / 0.408 measured at
25 Hz – 12.9 kHz on the CSD read.

| subset | rows | band-RMS | median \|Δ\| | p90 | max | s90 shipped, for the diff |
|---|---|---|---|---|---|---|
| OD ex gain-n12 | 320 | **2.664** | 0.79 | 5.49 | 40.8 | 2.697 / 0.81 / 5.62 / 40.2 |
| CLEAN | 168 | **0.453** | 0.26 | 0.82 | 3.15 | 0.432 / 0.23 / 0.77 / 3.15 |
| THD (OD) | 228 | 7.520 | — | — | level term **4.279** | 9.292, level **6.202** |

⚠ **SESSION 91 SHIPPED TWO CONSTANTS** — `c21R` 220k → 130k (hardware-directed, `reference-sources.md`
§2) and `jfetSatNeg` 0.76054 → 1.9 (low-drive even-order). The CLEAN cost is the deliberate, priced
consequence of the first; the **THD collapse 6.202 → 4.279 is a side effect of the second** and was
not the objective. See `CLAUDE.md` "Where we are".

Reproduce with:

```bash
/opt/homebrew/bin/python3.11 analysis/release_gate.py analysis/reports/s91_shipped.json
```

`release_gate.py` is the release gate itself — thresholds in its `GATE` constant, every reported cell
computed, non-zero exit while any gated row is over. `matrix_grade.py` still gives the per-row
band-RMS and the A-vs-B row movement.

✅ **CLEAN's gated row was SPLIT IN TWO in session 96 and all four rows now SHIP on both baselines** —
`100 Hz–8 kHz ≤0.30/≤0.80` (s91 0.215/0.719, s90 0.226/0.727) and `8–16.3 kHz ≤0.40/≤1.40` (s91
0.340/1.308, s90 0.347/1.309). The pooled `100 Hz–16.3 kHz` row it replaces failed BOTH baselines
(0.808 / 0.802) because it averaged a fine 19-band midband with a bad 4-band tail; the session-89
midband bars survive the split unchanged. Decided with the user in session 95, derivation of record
in `docs/clean-gate-split-handover.md`. ⚠ Session 91's pool change (25–100 Hz excluded as
hardware-governed) made the row HARDER, not easier — that is the trap that produced the split, not a
carve-out. CLEAN remains otherwise finished: regression-guard it, do not fit it. ⚠ Its 8–16.3 kHz
region is now explicitly gated rather than diluted, and is still CLEAN's worst.

### The FR instrument (session 90, Phase 9 item 0) — repaired, validated, and it changed little

`analyze.transfer()` is a cross-spectral-density estimate. Session 89 reasoned that it could not
separate a swept sine's harmonics from its fundamental, so every FR number taken at drive — the whole
release gate — carried unknown nonlinear contamination, and "ND aliases" vs "our instrument is
contaminated" were indistinguishable.

**Built:** `analyze.transfer_h1()`, an H1-only read that rejects harmonics structurally — after
Farina deconvolution the N-th harmonic response sits `T·ln(N)/R` ahead of the linear one in TIME
(1.00 s for H2 on this sweep), so a window narrower than that spacing contains the linear response
and nothing else. `farina_deconv()` is now shared with `harmonic_thd_curve()` so an FR number and a
THD number from one capture cannot silently come from different deconvolutions.

**Gated:** `analysis/h1_fr_gate.py --selftest` — KA-1 linear recovery, KA-2 harmonic rejection at a
brutal H2/H3 = −10/−14 dB, KA-3 a mutation (widening the gate past the H1→H2 spacing must FAIL
KA-2), KA-4 the spacing assumption asserted against `gen_test_signal`'s own constants, KA-5 a real
static nonlinearity whose known answer is the tanh describing function.

**Result — the premise did not survive.** Graded on the same 129 renders, all three reads stored per
row so membership is identical by construction:

| | CSD (old) | H1 | H1 band-avg |
|---|---|---|---|
| OD band-RMS | 2.95 | 2.99 | 2.70 |
| OD 8–16.3 kHz p90 | 8.73 | 8.50 | 8.07 |
| 12901.6 Hz max, OD | 36.18 | 35.32 | 33.23 |

Harmonic rejection moves the HF tail by 0.1–0.9 dB and the headline the *wrong* way; the modest gain
is from band-averaging, a sampling choice. KA-2 explains it: an exponential sweep already separates
orders in time (~1 s/octave) against a 170 ms Welch window, and **the CSD passes KA-2 as well**.

⚠ The one mechanism that defeats both instruments is an alias folding **onto** the fundamental at
`f = FS/(N+1)` — 16.0 kHz (H2), 12.0 kHz (H3) — coincident in both time and frequency, a limit of the
STIMULUS rather than of either estimator (KA-5's 1× arms). It is the only measurement-side
explanation left for the HF tail, and no better read can remove it.

⚠ **Two reporting choices to know.** (1) `band_read(mode="band")` power-averages each band over its
own 1/3-octave width, because `transfer_h1` returns a 0.046 Hz grid where a point sample can land in
the bottom of a notch — measured 24 dB of difference on one row, which would be a sampling artefact
read as an error. The CSD's 5.9 Hz bins made a point sample already a local average, which is why
this never mattered before. (2) `harmonic_thd_curve` keeps its own ±40 ms Hann H1 gate: its H1 is
only the denominator of `Hn/H1` and every historical harmonic number was read through it. **The two
H1s must not be quoted interchangeably.**

### The work, in order

Full detail in `CLAUDE.md` "Open work, in order". In brief:

0. ✅ **DONE session 90** — the FR instrument (above). Nothing shipped from it; it was a measurement
   correction, and it refuted its own motivating premise.
1. `c21R` 220k → ~130–150k (hardware-authoritative; we are matched to ND).
2. `jfetSatNeg` → ≈1.9 — blocked on a weighting judgement, **not** on more matrix runs.
3. The THD `level` term (6.2 dB) — the largest number on the board, never had its own session.
4. ⭐ **RE-SCOPED session 93.** The two-pole ATTACK re-fit. The arbiter was scoring a **stepped-sine**
   pedal spec against a **swept**-read render — an instrument-only delta of −29.1 % width at boost,
   i.e. the whole residual. Fixed by `analysis/attack_stepped_gate.py` (both sides stepped, 5 computed
   gates). In matched units the s62/63 proposal misses **f0 spread 17.72 vs 7.13 Hz (2.49×)** —
   the statistic session 63 called closed — plus widths 1.66 / **2.70** / 2.00× and boost depth
   −5.73 dB. The width excess is worst at **boost**, not flat as the swept read said, which changes
   which element the fit should target. **Not a width-only problem.** See `CLAUDE.md` item 4.
5. **A3** — one timeboxed carrier hunt inside/before the clipper, then a fitted correction network.
6. A4 re-grade + the GATE-9 report → the `OSValidationTest` decision → Phase 10.

### What is CLOSED

See §4's index. The short version: GAP #1, #1b (twice), #3a, #3b, #4, A2c, A2d, A5, the "63 % LOCAL"
lead, the reference chart's harmonic columns, the `2·a·cn = 1` question, the H4 disagreement and
A3's apparent shape disagreement are all **closed**. Do not re-open them without new evidence —
several were re-opened once already and closed again at the cost of a session each.

### Known-bad rows (excluded explicitly, never silently)

✅ **THE `gain-n12` EXCLUSION IS RETIRED — SESSION 111, on the user's decision. Those rows are GRADED.**
Session 48 localised a real defect (the session ran with the interface SEND 12.071 dB down while the
harness rendered the model at full level, so every *nonlinear* comparison on those files was invalid).
Both halves of the fix have since landed — `captures.render_args` emits `--input-trim` from the
MEASURED delta whenever `gainSessionDb` is non-zero, and the four exposed files were re-captured
2026-07-29 — and session 106's **GATE N** (`analysis/gain_session_gate.py`) re-ran session 48's *own*
instrument, THD turnover, which no record or output gain can move: 4 of 4 discriminating pairs
recover **12.376 / 11.412 / 12.016 / 12.012 dB** against the harness's 12.071, with the inversion
calibrated at 0 / 6 / 12.071 on known answers. Session 48's "implied pad 3–9 dB" does not reproduce.

⛔ **What GATE N does NOT certify**, stated because retiring an exclusion is where an overclaim goes
unchallenged: it certifies the CURRENT files (the defective ones were overwritten by the re-capture,
so it is *not* evidence session 48 was wrong), and it certifies them on a **nonlinear** statistic. On
the absolute/linear axis GATE O5 bounds the residual provenance offset at a **0.334 dB span** across
bands — a *tilt*, which the report's per-row gain match does not remove — and that residue is the
**reference's**: our model side is a pure 12.0710 dB shift to 1.8e-08. These rows are **cheap, not
clean.**

**Measured cost at `s110_baseline.json`** (131 captures; `release_gate.py`, dropout cell excluded):

| | ex `gain-n12` (pre-s111) | **graded (s111)** | |
|---|---|---|---|
| OD rows | 322 | **342** | |
| OD band-RMS | 2.265 | **2.327** | ⚠ +0.062 |
| OD 100 Hz–8 kHz median | 0.489 ✅ STRETCH | **0.531 ⚠ over** | ⛔ **re-opens the one OD row s109 closed** |
| OD 25–100 Hz median | 0.825 | 0.917 | ⚠ |
| OD 8–16.3 kHz p90 | 7.101 | 7.451 | ⚠ |
| OD p99 | 12.893 | **12.809** | ⭐ |
| THD (OD) level term | 3.065 ⚠ over | **2.986 ✅ SHIP** | ⛔ see the warning below |
| CLEAN, all four rows | 0.453 | **0.453** unchanged | ✅ (n12 CLEAN rows were never excluded) |
| rows over SHIP | 7 | **7** | composition changed, count did not |

⚠ **That is NOT session 106's "+0.020 dB, n 320 → 336"**, which was measured on the s109 report. s110
added a re-captured `drive-1700_level-1700_grunt-boost_gain-n12` twin, so the group is **20 rows now,
not 16**, and that twin is the worst of it (per-row band-RMS 3.41 / 4.29 / 4.90 / 8.95). It is also
the **only healthy capture of DRIVE max × LEVEL max × GRUNT boost at the `drv_-12` rung** — both
full-send captures of that condition are reference dropouts there — so retiring the exclusion
**restores coverage the session-110 dropout exclusion had removed.**

⛔⛔ **DO NOT BOOK THE THD ROW'S NEW `SHIP` AS A MODEL IMPROVEMENT.** The gated term is an UNSIGNED
rms, and the two populations it now pools have **opposite signs**: at full send the model
over-distorts (**signed +1.414 dB**, n 229) and at the 12.071 dB lower send it **under**-distorts
(**−0.772 dB**, n 15). An rms over that union is smaller than either population's own error, so the
number fell for a membership reason. `release_gate.py` prints the three-way split under the row on
every run so the mixture cannot be misread.

⭐⭐ **AND THAT MIXTURE IS ITSELF THE FINDING — the retired rows are the only ones in the matrix at a
second operating point, so they are the only rows that can see the SLOPE of the distortion-vs-input
law.** Paired against their own full-send twins (identical settings, send 12.071 dB apart, so every
nuisance cancels): dropping the send moves the model's signed THD level term by **−1.106 dB mean /
−1.039 median, 11 of 14 same-signed.** ⇒ the model's distortion rises with input level **faster than
the reference's** — too little at low input, too much at high input. That is the same defect GATE Q
named ("the OD path saturates too early") measured on an **independent axis**: GATE Q varies the
sweep's own level, this varies the interface send. ⚠ Quote the **sign**, not the size — per-pair
scatter runs −3.1 … +2.4 dB, and GATE N's own send calibration carries up to 0.66 dB of error on one
pair. **Measured, not gated.**

⚠ Still excluded, on their own separate grounds: the **2 reference ladder dropout cells** (session
109/110 — detected per render by `matrix_grade.find_dropouts`, never named) and, inside **GATE M
only**, the `gain-n12` A3 pair — whose exclusion now rests on session 108's P4 (do not pool over an
operating point the pedal itself sets), **not** on the retired capture defect.

## 1. Method

`analysis/comprehensive_report.py` renders the shipped plugin (`OfflineRender`, which now applies
the same `FitParams` the plugin does — session-17 wiring) through `analysis/test_signal_48k.wav`
at every capture's knob/switch settings, then grades plugin-vs-pedal per 1/3-octave band and per
THD anchor. `analysis/gap_audit.py` (and the session-18 aggregation probes) turn the JSON into a
prioritized gap list.

- **Deltas are SHAPE, not loudness.** Each capture is gain-matched to the plugin before
  differencing (`fr_at_bands` applies `null_depth`'s best-fit gain), so a band Δ is a voicing/FR
  error, not a level error. Absolute level is a separate axis (calibration §2 / makeup).
- **Grading thresholds** (`gap_audit.py`): `|Δ| > 3 dB` = real problem, `> 1.5 dB` = worth
  improving, `<= 1 dB` = good. Graded band 25 Hz–12.9 kHz (outside that the sweep energy / cab
  rolloff put both signals near the noise floor).
- **Trust anchors.** `bypass.wav` matches the plugin to **0.2 dB across all bands** — proof the
  pipeline (align, transfer, band extraction) is sound and resolves even 25 Hz correctly.

## 2. Running it cheaply (do NOT do full serial runs to iterate)

**The full 63-capture matrix now runs in ~6 min, not ~30** — `comprehensive_report.py` analyses
captures in a **process pool** (session 28). Captures are independent (one render + one analysis
against a shared read-only reference), so it is embarrassingly parallel. `--jobs N` / `-j N`,
default `min(8, cores−2)` = 8 here; each worker peaks ~600 MB. **Measured: 63 captures 768 % CPU,
5 m 42 s (was ~30 min serial); a 4-capture A/B went 116 s → 39 s.** `--jobs 1` restores the old
serial path for debugging. **Verified bit-identical** to serial output including capture ORDER
(the reference is loaded once per worker by the pool initialiser rather than pickled per task, and
results are re-indexed into capture order). The cache write is now atomic (tmp + `os.replace`) so
concurrent workers and Ctrl-C can't leave a truncated record that later reads as valid.

> ⚠ **Wall-clock is NOT runtime on this machine — check for sleep before diagnosing a "slowdown".**
> Session 28 killed a perfectly healthy full run after reading 10 captures in 87 minutes as a
> 9–17× regression. It was not: `pmset -g log` showed **`Entering Sleep state due to 'Clamshell
> Sleep'`** at 08:16 (lid closed, on battery) through 09:38, with only ~2 s DarkWake blips. The
> cache-file mtimes showed the true cadence — an exact **29 s per capture before AND after** the
> sleep window. Diagnose with per-capture cache mtimes (`find analysis/reports/cache -newermt ...
> -exec stat -f "%Sm %N" -t "%H:%M:%S" {} \;`) and `pmset -g log`, not elapsed wall-clock. Prefix
> long runs with `caffeinate -ims` (note: that still won't stop *clamshell* sleep on battery).

For iteration, use these (all `comprehensive_report.py`):

- **Per-capture result CACHE** — keyed by `(capture file identity + render args + OS factor +
  OfflineRender binary mtime)`. Captures are static, so a record only recomputes when the *plugin*
  output for those settings changes: a rebuild (new baked-in FitParams) or a `--fit` override busts
  only the affected records. Measured: 8-cap subset **189 s uncached → 0.83 s fully cached**. Cache
  lives in `analysis/reports/cache/` (gitignored).
- `--only SUBSTR[,SUBSTR]` — run just the captures whose filename matches (fast subset).
- `--fit K=V` (repeatable) — pass a `FitParams` override to EVERY render, so a candidate value can
  be tested **across the matrix without rebuilding** (the override is in the cache key).
- `--out PATH` — write to a scratch JSON so a subset/candidate run doesn't clobber the baseline
  `reports/comprehensive_data.json`.

Typical iterate loop: `python3.11 analysis/comprehensive_report.py --os 4 --only ref,bass,drive
--fit c21R=100000 --out /tmp/cand.json` → seconds after the first render, then aggregate.

Cache-key caveat: because the key includes the *binary* mtime, a `--fit c21R=X` render (old binary)
and a no-fit render from a rebuilt binary with that same value baked in get **different keys** even
though the output is identical — a rebuild won't reuse pre-rebuild `--fit` results. It never returns
stale data (the safe direction); it just occasionally re-renders what it could have reused. Key on
the *effective* FitParams (via `OfflineRender --print-fit`) if this ever becomes worth it.

**Session-23 tools.** `analysis/matrix_grade.py A.json [B.json ...]` prints the OD / CLEAN / ALL
band-RMS + tilt aggregate this document's tables quote (silent zero-knob rows excluded, graded
25 Hz–12.9 kHz), and with two reports the **row movement** (how many rows better/worse by >0.5 dB,
biggest mover each way, `--rows N` to list them) — the acceptance evidence to record beside any
aggregate, since an aggregate win built from a few big gains and many small losses is a different
result. `analysis/grunt_span_probe.py A.json [B.json ...]` prints the GRUNT **matched-pair span**
(position minus cut, per band, pedal vs plugin) at every drive setting, including the boost-vs-flat
ordering check — the GAP #4 span method generalised, and the metric that rejected C13 = 22n. It
un-applies the report's per-capture `gain_db_applied` before differencing, which a naive cross-capture
diff must also do. Both need no captures beyond the existing reports.

**Session-20 tools.** `analysis/od_tilt_metric.py <report.json>...` prints the GAP #3 tilt / low-band
RMS / mid-band RMS per OD capture and the mean, for any number of report JSONs side by side — the
metric every candidate above was scored on. `analysis/od_level_probe.cpp` (standalone:
`c++ -std=c++17 -O2 -I libs/chowdsp_wdf/include analysis/od_level_probe.cpp -o od_level`) measures
the OD chain's own transfer over an amplitude ladder, i.e. how the model's internal voicing moves as
it is driven — the gate that separated GAP #3a from #3b. Both need no captures.

## 3. Tooling caveats (must-know)

- **✅ HARNESS DEFECT — FIXED (session 21).** `render_args()` now emits
  `--input-trim -<measured dB>` whenever `gainSessionDb != 0` (the MEASURED
  `gain_correction_db`, −12.071, not the nominal dial), and the baseline
  `reports/comprehensive_data.json` was regenerated on it. Effect exactly as predicted: the 15
  `base-clean` n12 rows moved **< 0.05 dB** (linear ⇒ a level change is invisible after
  gain-matching) while the OD n12 rows moved a lot — `level-1700_gain-n12` drv−6 **18.27 → 5.80 dB**
  band-RMS, drv−12 12.04 → 6.76, `ref-od_gain-n12` drv−18 8.96 → 5.27; two rows got *worse*
  (`ref-od_gain-n12` drv−6 4.34 → 10.25, `level-0930_gain-n12` drv−6 2.50 → 4.19) — real
  drive-dependence error now measured honestly rather than accidentally cancelled. All-240-row mean
  band-RMS 4.386 → 4.298. **The rail-clamp verdict flipped on this fix — see GAP #3a.**
  The original defect, for the record: `render_args()` emitted every pot and switch but **never
  `--input-trim` for `gainSessionDb`**, so `OfflineRender` always ran at full test-signal level.
  The report then gain-matches the *output* by a scalar, which hides it completely for a linear
  capture — and silently invalidates **every nonlinear comparison** on those files.
  **Proof the SEND was lowered (the pedal saw less), not the record gain** — this is the one thing
  the fix depends on, so session 21 re-derived it from the raw WAVs and added a third, stronger leg:
  1. **cal_1k anchor, re-measured:** ref-clean → ref-clean_gain-n12 = **−12.071 dB**, but
     ref-od → ref-od_gain-n12 = **−2.854 dB**. A record-gain change is a scalar on the file and
     *must* give the same number on both; only compression INSIDE the pedal can shrink it.
  2. **Same pair on the quieter `sweep_clean` segment:** clean −12.146, OD **−9.362** — i.e. the OD
     shortfall tracks level (more compression at the hotter cal tone), the signature of a real
     input-level change.
  3. **⭐ Within-file, immune to session/take noise:** the pedal's own level-dependence collapses in
     the n12 file. The normalised band shape moves **2.59 dB RMS** across the drv−18→drv−6 sweep step
     in `ref-od.wav` but only **0.86 dB** in `ref-od_gain-n12.wav`. Under a record-gain change the
     pedal is driven identically in both files and those two numbers would be equal.
  **⚠ A tempting test that does NOT work (don't repeat it):** comparing the pedal's normalised band
  SHAPE of `ref-od_gain-n12` @drv−6 against `ref-od` @drv−18 (nominally the same absolute level).
  It appears to favour the wrong answer (@drv−6 matches at 1.89 dB, @drv−18 at 3.76) but it has **no
  discriminating power** — leg 3 shows a full 12 dB level step only moves the shape 2.6 dB, which is
  *below* the 3–4 dB take-to-take spread between the two capture sessions. Level anchors (high SNR,
  absolute) beat shape correlations here.
  **Scope:** ~15 of the 20 are `base-clean` (DIST disengaged → genuinely linear → unaffected); the
  exposed ones are `ref-od_gain-n12` and the four `level-*_gain-n12`, **plus any clean capture the
  model drives into a nonlinearity that the real pedal never reached** — which is exactly what the
  GAP #3a rail-clamp trial did (see below). **Fix: emit `--input-trim` from `render_args()`** (the
  flag exists) and re-baseline; this busts the cache for those 20 records only.
- **`gap_audit.py` does NOT exclude zero-knob SILENT captures.** `master-0700` (master=0),
  `level-0700` (OD volume=0) render to true silence → empty FFT bins → −640 dB → a **635 dB
  aggregate spread** that swamps `gap_audit`'s raw mean. Aggregate over VALID captures with a
  `min(plugin_db) > -60` filter (as the session-18 probes do), not `gap_audit`'s mean.
- **`gap_audit.py` / `cascade_analysis.py` DOCSTRINGS are template cruft** from a *different*
  pedal the template shipped with (they mention "PRESENCE", a "twin-T ~800 Hz notch", "V1/V2/V1E
  revisions", `phase10-gap-audit.md`). The **grading math is generic and correct**; ignore the
  topology narrative. `cascade_analysis.py`'s BLEND-discriminator logic is still valid for us.
- **`find_captures` skips non-matrix `.wav`** — the session-13 `jfet_ladder_*` diagnostic captures
  use underscore stimulus names (not `key-value`), so they're skipped with a note (a real matrix
  typo still surfaces as a skipped-file line).
- **The 320 Hz band dip in the OD captures is REAL, not an artifact — do NOT exclude it** (session 20
  checked, having first assumed the opposite). Across all 240 valid rows the pedal's 320 Hz band sits
  **−5.5 dB median** below the mean of its 254/403 Hz neighbours in **DIST-engaged (`base-od`)
  captures** and **0.00 dB median** in clean ones (min −1.3). Present only in the OD path, at the
  frequency of the TrebleAttack two-path cancellation notch → this is that notch (GAP #2), measured.
  **The plugin does not reproduce it** (its own 320 Hz dev is ~0 in the same OD captures). Useful as
  a *bleed-sensitive* probe: an OD-path notch only survives into the output if the OD sits above the
  clean bleed there, so "pedal shows its notch, plugin doesn't" says the plugin's OD is too weak
  relative to bleed in the mids — consistent with GAP #3b.
- **Driven low-band FR is contaminated by clipping harmonics** — sub-knee fundamentals get clipped,
  so the driven sweep's low bands are NOT a clean measure of a *linear* filter. Fit linear
  low-frequency shaping (e.g. coupling caps) on the CLEAN sweep; use driven only as a cross-check.
- **⚠ THE REPORT'S BROADBAND GAIN-MATCH CAN MANUFACTURE A FAKE "INCREASING HF ROLLOFF" WHILE A3 IS
  OPEN — read any chart with this in mind (session 30, 2026-07-26).** `fr_at_bands()` computes ONE
  scalar `gain_db` per capture via `null_depth()` (a broadband time-domain least-squares fit over the
  WHOLE sweep) and bakes it into every `plugin_db` value before it ever reaches a chart. On `ref-od`,
  re-anchoring that scalar to bands ≥200 Hz instead of the whole sweep collapses an apparent −3…−6 dB
  "rolloff" above 300 Hz down to ≤~1 dB — i.e. the LF excess from the still-open A3 cancellation null
  (below) drags the *one* broadband scalar down, which then reads as a phantom mid/high shortfall on
  every band above it, even though the mid/high match is actually fine. **Any "the plugin is quieter
  and quieter as frequency rises" read on a current chart should be re-checked with an LF-excluded
  gain-match before it's treated as a real, separate error** — most of it should evaporate once A3
  ships. See §4 "A3 chart-review corroboration" for the worked numbers (both `ref-od` and
  `ref-od_gain-n12`).

## 4. Gap log — INDEX

> ⚠ **The full narrative moved to `docs/phase9-gap-log.md` in session 89** (it was ~9,000 of this
> file's 11,000 lines). Nothing was deleted. This is the index: what was found, what state it is in,
> and where the evidence lives. **Search the gap-log file by the section titles below.**

### Closed — do not re-open without new evidence

| Gap | Verdict | Closed |
|---|---|---|
| **GAP #1** — low end 6–15 dB light | FIXED, `c21R` 10k → 100k (later 220k) | s18 |
| **GAP #1b** — bridged-T ~717 Hz notch | NOT A GAP. Closed s19, re-opened s20, re-closed s21 on 116 OD rows; re-opened s64 on a 6.2 dB shape error and **re-closed s65 — that was a missing `--grunt` flag**, not a circuit error | s21 / s65 |
| **GAP #3a** — drive-dependent bass tilt | FIXED, rail clamp enabled (`railNeg` 2.9 / `railPos` 2.7, DERIVED not fitted) | s21 |
| **GAP #3b** — GRUNT bump-vs-shelf | DISSOLVED — the premise was 14 sessions stale; the BLEND sum turns a monotone OD shelf into an output bump for free | s23 / s38 |
| **GAP #4** — mid positions over-deliver range | FIXED, `midWiperR` + cap table | s22 |
| **A2c** — clean-baseline accuracy | **CLOSED, TARGET MET.** The mid selector is a 2-POLE switched cap PAIR (`midCapRatioLo/Hi = 10`) | s27 |
| **A2d** — sub-60 Hz clean deficit | FIXED, `c21R` → 220k | s28 |
| **A5** — clean path distorts at hot levels | FIXED, `kInputRef` 3.377 → 1.2596 + the whole clipper/JFET family re-fitted | s44 |
| **"63 % LOCAL" lead** | ANSWERED, negatively — not one unexplored feature; 18.5 % is a polynomial edge artefact, 16.4 % is 320 Hz, the rest is incoherent per-row spread | s69 |
| **The reference chart's H2−H3 columns** | DEMOTED — neither column survives a test against the real ND device at the chart's own tone | s78 |
| **`2·a·cn = 1` identity** | AFFORDABLE but NOT FREE — costs the authoritative odd column in both drive regimes | s83 / s84 |
| **The H4 disagreement** | NOT A DISAGREEMENT — both halves are medians over 30–40 dB spreads | s83 |
| **A3's "shape disagreement"** | NOT REAL — the two instruments describe ONE curve; quote A3 as ≈5–7 dB over 100–400 Hz | s86 |

### Open

| Gap | State | Next move |
|---|---|---|
| **A3** — OD too weak vs the clean bleed, ≈5–7 dB over 100–400 Hz | MEASURED to death by two corroborating instruments; **no carrier found in ~20 sessions.** No single element (s50) and no post-clipper linear element of any order (s52) can supply it. Only region not ruled out: **inside/before the clipper** | ONE timeboxed session, then fall back to a fitted correction network |
| **GAP #2 / ATTACK** — the ~320 Hz notch, +26 dB, largest single-band error | ⛔⛔ **RE-SCOPED s99: the notch shape and the OD path's ABSOLUTE low-end level are in CONFLICT in this topology.** Re-fitted against the corrected s70 spec three times; each "reachable" result was bought by spending the LF level (s94 width rms 0.34 at **LF −42 dB**; s97 0.41 at **−22 dB**). With an LF-visible term the same search reaches **LF −1.4 dB** and width collapses to **4.25 in all ten rows** of a sweep spanning 100× in `w_f0` and 3× in box — saturated, i.e. unreachable, not a weight choice. f0 and its spread hold throughout (6.78 Hz vs the pedal's 7.13) | **Not "re-fit again."** Either accept a level-correct / shape-approximate point, or find the missing degree of freedom — the width+depth deficit is now a TOPOLOGY question, not a fitting one |
| **Even-order, low drive** — `jfetSatNeg` | LOCATED (≈1.9) and matrix-judged. ⛔ Stop rendering `a` candidates — the matrix has said all it can | A weighting judgement, not a measurement |
| **THD `level` term, 6.2 dB** | The largest single number in the project. Never had a dedicated session | Own pass, from the THD decomposition |
| **`c21R`** | We sit at 7.2 Hz, matched to ND; hardware wants ~11–12 Hz ≈ 130–150k | One constant + one matrix run |
| **A2e** — >10 kHz mid-boost skirt | QUANTIFIED (−6.03 dB @16 kHz at HI-MID 3k), element NOT identified. Bilinear warp RULED OUT by measurement | after A3 |
| **A2f** — ±0.2 dB clean tilt | CHARACTERISED, PARKED. ~3× the take-to-take floor | park |
| **A3-adjacent** — `gain-n12` HF collapse | Localised s48 as a **capture defect** (THD turnover differs by up to 15.6 dB, which no gain can move) | re-capture 4 files |
| **>8 kHz OD error** | ⭐ NEW s89 — probably **ND's aliasing, not ours** (see `CLAUDE.md`). Reported, not gated | verify before any work |

## 5. Performance / HQ pass (not started)

`PerfBenchmark` / `FeatureProfile` / `OSFidelity` → the `hq` toggle decision (omega4 vs
AccurateOmega is usually the only real lever) + README perf table. Plus the deferred OS-fidelity
work: the session-17 4× narrow-band aliasing residual at the amp-0.5 extreme corner (8× is pristine;
recommend 8× for extreme high-drive) — see the OSValidationTest header.

**⚠ Also required (added 2026-07-27, per user request): explicit NO-OS and LOW-OS sweeps, with a
documented compensation decision — not just the 8×-reference OSFidelity comparison already planned.**
`dsp.md`'s "Low-OS top-octave restore" pattern is written up as a design option but has never been
run or decided on for this pedal. Before GATE 9 closes the perf pass:
1. Run `OSFidelity` (or extend it) at **OS = 1× (no oversampling) and 2×**, not only the existing
   1×/2×/4× vs 8× comparison implied by its description — read both the aliasing/harmonic-vs-clean
   picture (its existing job) AND the plain linear-stage top-octave droop from bilinear cap warping
   (`dsp.md` "Top-octave accuracy") at each factor, since a low-CPU/low-latency user may run the
   plugin at 1× or 2× routinely, not just transiently.
2. **Decide, in writing, whether the droop measured at 1×/2× is large enough to need the low-OS
   shelf compensation** `dsp.md` describes (a single fixed-shape high-shelf biquad at base rate,
   gain set per OS factor, ~0 at 4×/8× so the default is untouched) — implement it if so, or record
   the measured droop and an explicit "accepted, not worth the extra stage" if not. Do not leave
   this an open design note; GATE 9 needs a decision, not just the option on record.
3. Keep A5 (above) in view while doing this: A5 is NOT an OS-dependent defect. **Verified directly
   (session 39): `ref-clean.wav`'s `lvl_-3` render is bit-identical across OS 1×/2×/4×/8×
   (THD = 22.8546% and H2/H3 to 4 decimal places at every factor)** — confirming it lives entirely
   in the base-rate EQ block, so fixing it will not appear in, and should not be conflated with,
   this OS-fidelity/compensation work.

## 6. Carry-forward from Phase 8

Re-verify the **VU idle-noise gate threshold against the new makeup** (0.9 → 3.684 shifted the idle
floor ~4×; calibration §7 / build-plan Phase-8 item 3). The meter may show idle noise as activity
until the threshold is re-checked.

---

