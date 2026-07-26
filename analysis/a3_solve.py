#!/usr/bin/env python3
"""a3_solve — session 29 (Phase 9 / A3): read a3_blend_decompose's phasors and ask
what the pedal's measured OD-vs-clean balance actually DEMANDS of the model.

The A3 handover left two hypotheses:
  (a) the BLEND clean bleed's LF magnitude is too high;
  (b) the OD path and the bleed partially CANCEL at LF in the real pedal and add
      in the model (frequency-dependent phase near the GRUNT-cut coupling corner).

Neither was ever tested against the geometry. At each band the output is an exact
two-term sum  full = od + bleed  (LevelBlend is linear in its inputs; the probe
asserts this to <-280 dB), so with |bleed| known from the model we can SOLVE for
the OD phasor the pedal's own total demands, and read off whether any phase can
get there at all. Three outcomes are distinguishable:

  * required |od| is real and the required phase is modest  -> the gap is LEVEL
  * no solution exists at any phase (bleed alone already exceeds the pedal total)
    -> the BLEED is necessarily part of the fix, hypothesis (a) is forced
  * a solution exists but only at a large phase angle -> hypothesis (b), and we
    get the actual angle it needs rather than an appeal to "~87 degrees".

Usage: a3_solve.py [decompose.csv]   (default: reads build/a3_decompose.csv)
"""
import sys
import cmath
import math

# The A3 target: ref-od minus blend-0700, per band, from the pedal captures.
# docs/phase9-validation.md section 4 "A3 handover".
PEDAL_DB = {
    20: -17.8, 25: -18.2, 32: -19.1, 40: -20.5, 50: -21.2, 64: -19.2,
    80: -15.7, 101: -12.8, 127: -10.7, 160: -9.4, 202: -8.8, 254: -9.9,
}


def db(x):
    return 20.0 * math.log10(max(abs(x), 1e-18))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "build/a3_decompose.csv"
    rows = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            v = [float(t) for t in line.strip().split(",")]
            rows.append({
                "f": v[0],
                "ref": complex(v[1], v[2]),
                "full": complex(v[3], v[4]),
                "od": complex(v[5], v[6]),
                "cl": complex(v[7], v[8]),
            })

    print("Model decomposition at BLEND max, all dB relative to the full-clean")
    print("reference (= the blend-0700 capture), so these are directly comparable")
    print("to the A3 handover table.\n")
    hdr = ("f", "plugin", "pedal", "err", "od", "bleed", "ph(od-bl)")
    print("%6s %8s %8s %8s %10s %10s %10s" % hdr)

    solves = []
    for r in rows:
        f = r["f"]
        ref = abs(r["ref"])
        plug = db(r["full"] / ref)
        ped = PEDAL_DB[r["f"]]
        odd = db(r["od"] / ref)
        bld = db(r["cl"] / ref)
        ph = math.degrees(cmath.phase(r["od"]) - cmath.phase(r["cl"]))
        ph = (ph + 180.0) % 360.0 - 180.0
        print("%6.0f %8.2f %8.2f %8.2f %10.2f %10.2f %10.1f"
              % (f, plug, ped, plug - ped, odd, bld, ph))
        solves.append((f, ref, r, ped, bld))

    # ---- the geometry -----------------------------------------------------
    # Work in units of the model's bleed phasor: rotate+scale so bleed = 1. Then
    # total = 1 + z with z the OD contribution, and |1 + z| = T (T = pedal total
    # over model bleed). With z = m e^{i0}:
    #        m^2 + 2 m cos0 + 1 = T^2
    #
    # NOTE (corrected): letting BOTH m and 0 vary, every T >= 0 is reachable --
    # |1 + m e^{i0}| sweeps [|1-m|, 1+m], and those intervals cover [0, inf) as m
    # varies. So "the bleed exceeds the pedal total" does NOT make an OD-side fix
    # impossible, and an earlier version of this script wrongly said so. What it
    # DOES force is the SIGN of the interaction, which is the useful result:
    #
    #   T < 1  =>  m^2 + 2 m cos0 < 0  =>  cos0 < -m/2 < 0  =>  0 > 90 deg.
    #
    # i.e. wherever the pedal's total sits below the model's own bleed, the OD
    # contribution MUST be partially cancelling the bleed, not adding to it. That
    # is hypothesis (b), forced by geometry rather than merely plausible -- unless
    # the bleed's own level comes down, which is hypothesis (a).
    #
    # The cheapest admissible OD is m_min = |T - 1| at exactly anti-phase (T<1)
    # or in-phase (T>1); we report that alongside the angle required if the OD
    # magnitude were left at the model's current value.
    print("\n\nGEOMETRY: what does the pedal's total DEMAND of the OD contribution,")
    print("if the model's clean bleed is left as it is? Units: bleed = 1.0.")
    print("T = pedal total / model bleed.  m = OD magnitude in the same units.")
    print("'min m' is the smallest admissible OD (at anti-phase if T<1).")
    print("'phase @ model m' keeps the OD level the model already has.\n")
    print("%6s %8s %8s %8s %9s %9s %14s"
          % ("f", "T(lin)", "T(dB)", "m(model)", "min m", "forced?", "phase @ model m"))

    cancel = []
    for f, ref, r, ped, bld in solves:
        T = 10 ** ((ped - bld) / 20.0)
        m_model = abs(r["od"]) / abs(r["cl"])
        m_min = abs(T - 1.0)
        # required phase if the OD magnitude were kept at the model's value
        c = (T * T - 1.0 - m_model * m_model) / (2.0 * m_model)
        if -1.0 <= c <= 1.0:
            need = "%.0f deg" % math.degrees(math.acos(c))
        else:
            need = "none at this m"
        forced_lbl = ">90 deg" if T < 1.0 else "-"
        if T < 1.0:
            cancel.append(f)
        print("%6.0f %8.3f %8.2f %8.3f %9.3f %9s %14s"
              % (f, T, ped - bld, m_model, m_min, forced_lbl, need))

    print()
    if cancel:
        lo = ", ".join("%d" % f for f in cancel)
        print("=> At %s Hz the pedal's TOTAL output sits BELOW the model's own" % lo)
        print("   clean bleed. With the bleed unchanged, the OD contribution there")
        print("   is geometrically FORCED to be more than 90 deg out of phase with")
        print("   it -- i.e. partially cancelling. The model currently has both the")
        print("   wrong sign of interaction (adding) and far too much OD level.")
        print("   So the two handover hypotheses are not alternatives: either the")
        print("   bleed's LF level comes down (a), or the OD goes anti-phase (b),")
        print("   and (b) now has a hard numeric requirement rather than an appeal")
        print("   to the ~87 deg GRUNT-cut corner lead.")
    else:
        print("=> The pedal total never falls below the model bleed; no cancellation")
        print("   is forced. An OD-level fix alone is geometrically sufficient.")


if __name__ == "__main__":
    main()
