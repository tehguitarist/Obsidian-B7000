#!/usr/bin/env python3.11
"""Session-15 branch-B §3j discriminating GATE (handover §3t.6) — BEFORE any fit.

Branch B replaced the JFET core's COMPRESSIVE ceiling with an EXPANSIVE-then-bounded
rational map (JfetStage.h coreLimit(), session 15):
    T(w) = w*(1+c*w^2)/(1+(w/L)^2)^1.5,  c = beta + 1.5/L^2,  small-signal T = w + beta*w^3
`beta = jfetExpandBeta` is the cubic coefficient DIRECTLY; beta > 0 makes EXPANSIVE H3.

WHY THIS GATE (the sessions-7-14 lesson, re-earned by the session-14 pivot failure):
NEVER fit past a shape whose discriminating signature hasn't been confirmed. Session 14's
hardness `k` failed its own pre-registered gate; this one must PASS before fit_nonlinear.py
runs, or STOP and reconsider the shape family (option C, the coupled-Newton rewrite, is
still on the table — §3t.4).

THE PRE-REGISTERED SIGNATURE (must hold, or STOP and do NOT fit):
  (A) PHASE FLIP. Isolate the JFET CORE's H3 contribution by coherent complex subtraction
      (full render minus a core-linear render, exactly as phase_harmonics.py isolates the
      "ceiling") and measure its phase relative to the clipper's H3. As beta RISES, the
      core<->clipper relative phase must move from ~180 deg (anti-phase, the compressive
      regime that failed) TOWARD ~0 deg (in-phase). This is the whole point of branch B:
      a COMPRESSIVE core's H3 is intrinsically ~180 deg from the clipper's (session 14),
      and only flipping the cubic SIGN (beta > 0) can bring it in-phase.
  (B) MAGNITUDE RISE, NO NEW NULL. Full-chain drive-min H3-H2 must RISE toward the
      capture's -23.2 dB as beta rises, MONOTONICALLY (no deep interior dip = no
      anti-phase null re-created), AND no OTHER drive setting (9:30/noon/2:30/max) may
      develop a null as beta sweeps. A null anywhere = core-H3 still cancelling the
      clipper-H3 somewhere = wrong sign somewhere = STOP.

If both hold: proceed to the phase-aware complex fit (fit_nonlinear.py, §3t.6 step 3).

Run: /opt/homebrew/bin/python3.11 analysis/expandbeta_gate.py [--point=s,a,cp,cn,A0,satLo,satHi]
     --point defaults to a PROPER-clipper point (clipA0=25, satLo/Hi 3.15/3.85, the
     physically-nominal clipper) — the session-14 pivot showed the frozen bad clipper was
     not the confound, so gate on the real one.
Log: analysis/fit_logs/step5_expandbeta_gate.log
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import fit_nonlinear as F
import phase_harmonics as PH

# beta values to sweep. 0 = neutral (cubic-free core, ~no core H3 — the baseline); rising
# beta grows the expansive cubic. Spread wide enough to see the phase settle and the
# magnitude approach -23.2 without overshooting into instability.
BETA_SWEEP = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

# Default gate point = the PHYSICALLY-NOMINAL clipper (not the session-11 starved fit).
# FIT_KEYS order: s, a, cp, cn, clipA0, clipSatLo, clipSatHi.
DEFAULT_POINT = [0.30, 4.0, 1.0, 0.5, 25.0, 3.15, 3.85]

# Tones for the phase check. 1000 Hz is the conclusive clean tone (§3t.5: capSNR 47,
# notch-free); 110 corroborates (its H3=330 Hz is clear of the 717 Hz bridged-T notch).
PHASE_TONES = [110.0, 1000.0]


def _reshape_implemented():
    try:
        r = subprocess.run([F.RENDER_BIN, "--print-fit", "--fit", "jfetExpandBeta=1"],
                           capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False


def core_vs_clipper_phase(point, beta, hot=True):
    """Coherent complex subtraction: isolate the JFET CORE's H3 (full - core-linear) and
    return its phase relative to the clipper's H3, per PHASE_TONE. Uses the HOT input (the
    core's and clipper's H3 phases are both level-stable, so a hotter input just improves
    SNR of the subtraction — same trick as phase_harmonics.py)."""
    fits = dict(zip(F.FIT_KEYS, point))
    fits["jfetExpandBeta"] = beta
    # core-linear = ceilings off (coreLimit returns w exactly) -> JFET makes NO odd content,
    # only the clipper makes H3. Beta is irrelevant when the core is bypassed, but pass it
    # so the two renders differ ONLY in whether the core shapes.
    clip_fits = dict(fits); clip_fits["jfetCeilPos"] = 1e6; clip_fits["jfetCeilNeg"] = 1e6
    inp = PH.HOT_IN if hot else None
    if hot:
        PH.make_hot_input()
    full = PH.render_variant(PH.DRIVE_MIN_CAP, fits, "/tmp/eb_full.wav", inp)
    clip = PH.render_variant(PH.DRIVE_MIN_CAP, clip_fits, "/tmp/eb_clip.wav", inp)
    out = {}
    for f0 in PHASE_TONES:
        Hf, _, _ = PH.fit_harmonics(PH.steady_window(A_seg(full, f0)), f0)
        Hc, _, _ = PH.fit_harmonics(PH.steady_window(A_seg(clip, f0)), f0)
        phi1 = np.angle(Hf[1])
        H3f = Hf[3] * np.exp(-1j * 3 * phi1)          # psi-framed full H3
        H3c = Hc[3] * np.exp(-1j * 3 * phi1)          # clipper H3 in full's frame
        H3core = H3f - H3c                            # coherent core contribution
        rel = abs(PH._deg_err(np.degrees(np.angle(H3core)), np.degrees(np.angle(H3c))))
        d_core = 20 * np.log10(abs(H3core) / abs(Hf[1]) + 1e-30)
        out[f0] = dict(rel=rel, d_core=d_core, p_core=np.degrees(np.angle(H3core)),
                       p_clip=np.degrees(np.angle(H3c)))
    return out


def A_seg(sig, f0):
    import analyze as A
    return A.seg_of(sig, f"tone_{f0:g}")


def main():
    if not _reshape_implemented():
        print("jfetExpandBeta is NOT implemented — OfflineRender rejects --fit jfetExpandBeta=.")
        print("Land the branch-B core in JfetStage.h (+ plumbing) first.")
        return 2

    point = list(DEFAULT_POINT)
    for arg in sys.argv[1:]:
        if arg.startswith("--point="):
            point = [float(v) for v in arg.split("=", 1)[1].split(",")]

    F.make_short_input()
    targets = F.capture_targets()
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open("analysis/fit_logs/step5_expandbeta_gate.log", "w")

    def emit(s):
        print(s); log.write(s + "\n")

    emit("=" * 78)
    emit("SESSION-15 branch-B §3j GATE — expansive-then-bounded JFET core (jfetExpandBeta)")
    emit("=" * 78)
    emit("Point: " + ", ".join(f"{k}={v:g}" for k, v in zip(F.FIT_KEYS, point)))
    cap_min = targets["min"]["H3"] - targets["min"]["H2"]
    emit(f"Capture targets (tone_220, H3-H2 dB):  " +
         "  ".join(f"{l}={targets[l]['H3']-targets[l]['H2']:+.1f}" for l in targets))

    # ---- PART A: full-chain H3-H2 vs beta, all 5 drive settings ---------------------
    emit("\n" + "-" * 78)
    emit("(A) MAGNITUDE — full-chain H3-H2 (dB) vs beta, per drive setting")
    emit("-" * 78)
    labels = list(targets.keys())
    emit(f"  {'beta':>6} | " + " | ".join(f"{l:>6s}" for l in labels))
    A_rows = {}
    for beta in BETA_SWEEP:
        F.HELD["jfetExpandBeta"] = beta
        try:
            prof = F.render_profiles(point)
        finally:
            F.HELD.pop("jfetExpandBeta", None)
        A_rows[beta] = [prof[l]["H3"] - prof[l]["H2"] for l in labels]
        emit(f"  {beta:>6.1f} | " + " | ".join(f"{v:>6.1f}" for v in A_rows[beta]))

    # ---- PART B: core<->clipper H3 phase vs beta ------------------------------------
    emit("\n" + "-" * 78)
    emit("(B) PHASE — JFET-core H3 vs clipper H3 relative phase (deg) vs beta")
    emit("    core = full - core-linear (coherent); want 180 -> 0 as beta rises (IN-PHASE)")
    emit("-" * 78)
    emit(f"  {'beta':>6} | " + " | ".join(f"{f:g}Hz rel  |Hc|dB" for f in PHASE_TONES))
    B_rows = {}
    for beta in BETA_SWEEP:
        ph = core_vs_clipper_phase(point, beta)
        B_rows[beta] = ph
        cells = []
        for f0 in PHASE_TONES:
            cells.append(f"{ph[f0]['rel']:>7.1f}  {ph[f0]['d_core']:>6.1f}")
        emit(f"  {beta:>6.1f} | " + " | ".join(cells))

    # ---- VERDICT --------------------------------------------------------------------
    emit("\n" + "=" * 78)
    emit("VERDICT")
    emit("=" * 78)
    betas = sorted(A_rows.keys())
    mn = [A_rows[b][labels.index("min")] for b in betas]

    # (A1) drive-min rises toward -23.2 as beta rises
    min_rise = mn[-1] - mn[0]
    emit(f"  (A1) drive-min H3-H2 rises with beta : {min_rise:+.1f} dB "
         f"(from {mn[0]:+.1f} to {mn[-1]:+.1f}; capture {cap_min:+.1f})")

    # (A2) drive-min is MONOTONE (no interior null). A null shows as a dip: some interior
    #      beta strictly below BOTH its neighbours by a margin.
    dips = [(betas[i], mn[i]) for i in range(1, len(mn) - 1)
            if mn[i] < mn[i - 1] - 1.0 and mn[i] < mn[i + 1] - 1.0]
    emit(f"  (A2) drive-min monotone (no interior null) : "
         f"{'YES' if not dips else 'NO — dips at ' + str(dips)}")

    # (A3) no OTHER drive setting develops a deep null across the sweep. Flag any column
    #      whose min-over-beta is > 3 dB below both its endpoints (a swept-through null).
    null_cols = []
    for j, lbl in enumerate(labels):
        col = [A_rows[b][j] for b in betas]
        interior_min = min(range(len(col)), key=lambda i: col[i])
        if 0 < interior_min < len(col) - 1 and \
           col[interior_min] < col[0] - 3.0 and col[interior_min] < col[-1] - 3.0:
            null_cols.append((lbl, betas[interior_min], col[interior_min]))
    emit(f"  (A3) no drive setting develops a swept null : "
         f"{'YES' if not null_cols else 'NO — ' + str(null_cols)}")

    # (B1) phase flips 180 -> 0 as beta rises, at the conclusive 1 kHz tone
    rel_1k = [B_rows[b][1000.0]['rel'] for b in betas]
    rel_110 = [B_rows[b][110.0]['rel'] for b in betas]
    phase_flip_1k = rel_1k[0] - rel_1k[-1]      # >0 means moved toward 0 (in-phase)
    emit(f"  (B1) 1kHz core<->clip phase: {rel_1k[0]:.0f} -> {rel_1k[-1]:.0f} deg "
         f"(moved {phase_flip_1k:+.0f} toward in-phase; want large +, ending < 90)")
    emit(f"       110Hz corroboration : {rel_110[0]:.0f} -> {rel_110[-1]:.0f} deg")

    # Combined verdict. The phase flip and the in-phase endpoint are the core claim; the
    # magnitude rise + no-null confirm it isn't cancelling.
    passA = (min_rise > 3.0) and (not dips) and (not null_cols)
    passB = (phase_flip_1k > 45.0) and (rel_1k[-1] < 90.0)
    ok = passA and passB
    emit("")
    emit(f"  PART A (magnitude, no null): {'PASS' if passA else 'FAIL'}")
    emit(f"  PART B (phase flip to in-phase): {'PASS' if passB else 'FAIL'}")
    emit("")
    emit(f"  GATE {'CONFIRMED — proceed to the phase-aware complex fit (§3t.6 step 3)' if ok else '** NOT CONFIRMED — STOP, do NOT fit; reconsider the shape family (§3t.4 option C) **'}")
    log.close()
    print("\n[log] analysis/fit_logs/step5_expandbeta_gate.log")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
