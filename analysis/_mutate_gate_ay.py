#!/usr/bin/env python3.11
"""Mutation test for GATE AY (analysis/level_taper_reshape.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain — or, for two of
them, one it must NOT contain, because the claim being armed is the ABSENCE of a line and
`must_contain` cannot express that.

  * `expect_rc != 0` arms test the REFUSALS: the imported-coefficient invariant, the bleed-free
    anchor, the EPOCH guard, the well-posedness screen, the known answer, and its vacuity check.
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate is quoted for four statements and
    every one must be able to come back as its opposite (`computed-verdicts-not-narrated`, five
    prior occurrences — and s161 committed it *inside* a gate written to apply that rule):
      - "the model MUTES at LEVEL min"                    -> ay2-mute
      - "THE FAMILY IS WHAT DECIDES IT" (vs GATE K)       -> ay3-family
      - "the requirement moves the pot TOWARD the band"   -> ay4-band
      - "0 of 2 REACH, at the family's own SUPREMUM"      -> ay5-reaches

⚠⚠ THE MOST IMPORTANT ARM IS `ay5-reaches`.  AY5(c) is the reason task D closes as specified, so a
hard-coded "0 of 2 REACH" would retire an open work item on narration.  The arm shrinks item 9's
own sensitivity ratios until the bound clears them, which must flip the verdict to "reach".

⚠ THE SECOND MOST IMPORTANT IS `ay1b-epoch`, and it is the only arm that mutates NOTHING: it runs
the unmodified gate against `s146_mastertaper.json`, a report rendered before s156's DSP change.
Every number this gate prints is an absolute level, so the epoch guard is what licenses all of
them — and a guard that has never been seen to fire is a guard nobody has tested (s119).

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) — two different requirements (s110).
  * the mutant path is PID-UNIQUE (s139: a fixed mutant filename cannot be run twice
    concurrently, and the arms then score whatever the other run wrote).
  * NO report redirect is needed here, unlike GATE AP/AQ/AR/AX — this gate takes its output path
    as `--json` with NO default, so a mutant invoked without it writes nothing.  That is ASSERTED
    below rather than assumed, because a later default would silently re-arm the s153 hazard
    (a mutant leaving a deliberately falsified report on disk wearing the real gate's name).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not merely a non-zero exit (s117).

⚠ WHAT IS NOT COVERED, stated rather than left to be discovered:
  * **The headroom bound's PREMISE is not mechanically checkable.** That (1-L) is the mixed
    clean-re-OD ratio comes from GATE L's reduction, and AY1 asserts this gate agrees with GATE K
    on the coefficients — but "the LEVEL sensitivity item 9 measures is driven by that ratio" is a
    NECESSARY-condition argument, and the gate says so in AY5(b) in its own words.
  * **The refused hottest column is not armed.** Whether `dB_model(L)` is non-monotone at
    `drv_-6` is a property of the reference and the model, not of this tool; what IS armed is that
    the refusal changes the printed membership (the control's "3 of 4" string).

Run:  python3.11 analysis/_mutate_gate_ay.py
"""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(HERE, "level_taper_reshape.py")
MUT = os.path.join(HERE, f"_mutated_gate_ay_{os.getpid()}.py")

# ⚠⚠ s189: `STALE` WAS A TRANSCRIBED FILENAME AND IT ROTTED, EXACTLY AS `CURRENT` DID AT s173 --
# in the same file, one constant apart, and s173 fixed only the one it was looking at.
# `analysis/reports/*.json` is gitignored and regenerable, so `s146_mastertaper.json` had simply
# been cleaned up; the arm then died in `json.load` with a FileNotFoundError and was scored
# rc=1 -- a CRASH counted as a firing epoch guard, which is s117's "check guard IDENTITY, not a
# non-zero exit" arriving through the back door.  Derived instead, and it REFUSES rather than
# passing vacuously when no stale report exists (`empty-gate-must-fail`).
def oldest_stale_matrix_report(srcs_newest):
    """The oldest full matrix report that PREDATES the newest src/ file -- i.e. one AY1b must
    refuse.  A structural test cannot go stale the way a filename does."""
    best, best_mt = None, float("inf")
    for path in glob.glob(os.path.join(ROOT, "analysis", "reports", "*.json")):
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except Exception:
            continue
        if not (isinstance(doc, dict) and {"captures", "meta", "summary"} <= set(doc)):
            continue
        if len(doc.get("captures") or []) < 100:
            continue
        mt = os.path.getmtime(path)
        if mt < srcs_newest and mt < best_mt:
            best, best_mt = path, mt
    if best is None:
        sys.exit("MUTATION TEST FAIL: no matrix report on disk PREDATES the newest src/ file, so "
                 "the epoch arm has nothing the guard could refuse and would pass vacuously.  "
                 "Render one against an older build, or drop the arm deliberately -- do not let "
                 "it report a green light for an untested guard (`empty-gate-must-fail`).")
    return os.path.relpath(best, ROOT)


# ⚠⚠ s173: `CURRENT` used to be the transcribed literal `s162_shipped.json`, and by this session
# it was THREE epochs stale (s163's taper, s166's `OdDriveTilt`, s172's `OdMakeup`).  AY1b duly
# refused it — correctly — which broke the CONTROL, and with the control broken every arm below
# was unattributable: the three arms that "passed" expect rc != 0 and were getting it from the
# EPOCH guard rather than from their own mutation (s117: check guard IDENTITY, not just a non-zero
# exit).  A runner that names an epoch has to be re-pointed every time an epoch ends, and nothing
# was making that happen, so it is DERIVED instead: newest report on disk that is STRUCTURALLY a
# matrix report.  A structural test cannot go stale the way a filename does.
def newest_matrix_report():
    best, best_mt = None, -1.0
    for path in glob.glob(os.path.join(ROOT, "analysis", "reports", "*.json")):
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except Exception:
            continue                       # a gate's own artefact, or a partial write
        if not (isinstance(doc, dict) and {"captures", "meta", "summary"} <= set(doc)):
            continue
        if len(doc.get("captures") or []) < 100:      # a --only subset is not the matrix
            continue
        mt = os.path.getmtime(path)
        if mt > best_mt:
            best, best_mt = path, mt
    if best is None:
        sys.exit("MUTATION TEST FAIL: no full matrix report found under analysis/reports/ -- the "
                 "control has nothing current-epoch to run against, so no arm below would be "
                 "attributable (`empty-gate-must-fail`)")
    return os.path.relpath(best, ROOT)


CURRENT = newest_matrix_report()
_SRC_GLOBS = ("src/dsp/*.h", "src/*.cpp", "analysis/offline_render.cpp")
_NEWEST_SRC = max(os.path.getmtime(f)
                  for g in _SRC_GLOBS
                  for f in glob.glob(os.path.join(ROOT, g)))
STALE = oldest_stale_matrix_report(_NEWEST_SRC)

# (name, why, [(pattern, replacement), ...], expect_rc, must_contain, must_absent, report)
ARMS = [
    # ⚠ s173: the control used to assert `"0 of 2 REACH"` — AY5's headroom VERDICT, which was true
    # on the s162 epoch and is a computed outcome that legitimately flips (it now reads 1 of 2).
    # A control asserts that the unmutated gate RAN TO COMPLETION; an epoch-dependent verdict
    # belongs in an arm that mutates the data behind it, not here.  `AY6 OK` is the last line of
    # the last sub-gate and `sup/need =` proves it reached AY5's computed block — both invariant.
    ("control", "unmutated — if this does not pass, nothing below is attributable",
     [], 0, "AY6 OK", None, CURRENT),

    # ---- AY1: the imported invariant and the anchor the whole gate is referred to ---------------
    ("ay1-coef-drift",
     "level_taper_gate's reduction is nudged off level_law_gate's coef_closed, so the two imported "
     "modules disagree and no number below may be quoted",
     [(r'abs\(a - L\.a_of\(Lv\)\)', 'abs(a - L.a_of(Lv) - 1e-9)')],
     1, "AY1 FAIL", None, CURRENT),

    # ⚠ s189: RE-POINTED.  The retired arm patched `if L.b_of(1.0) != 0.0:` -- the invariant s181
    # made false.  The invariant is now "b at the anchor EQUALS the shipped end stop", which ties
    # GATE L's reduction to FitParams.h through GATE K's single resolver; reading it just below
    # the anchor must still refuse, and for the same reason (the anchor's own clean content is
    # not what the header says).
    ("ay1-anchor",
     "the anchor test is pointed just below LEVEL max, so the clean coefficient read there no "
     "longer matches the shipped end stop — the anchor's own contents must be checked AT the "
     "anchor, or every level below is referred to a corner the gate cannot locate",
     [(r'b_top = L\.b_of\(1\.0\)', 'b_top = L.b_of(0.999)')],
     1, "disagrees with the header", None, CURRENT),

    # ⭐⭐ s189, NEW AND IT REPRODUCES THIS SESSION'S OWN HEADLINE DEFECT.  `level_taper_gate`'s
    # reduction was a THIRD mirror of the LevelBlend network and it sat on the pre-s181 topology
    # for eight sessions while s182 fixed only the two inside `level_law_gate`.  The arm makes the
    # mirror ideal again while GATE K stays shipped; AY1's divergence check must catch it.
    # ⚠ The patch lands in an IMPORTED module (s128), so it is applied to `level_taper_gate.py`
    # rather than to the gate under test.
    # ⚠ The mutation targets an IMPORTED module (s128), and it is injected as a module-level
    # override INTO THE MUTANT rather than written over `level_taper_gate.py` on disk (s139): the
    # override then lives and dies with the subprocess, so a crashed arm cannot leave a patched
    # dependency behind for every later run to inherit.
    ("ay1-third-mirror",
     "level_taper_gate's reduction is pinned to the IDEAL network while level_law_gate keeps the "
     "shipped end stop — s181's defect, reproduced.  Two correct implementations of two DIFFERENT "
     "stages, which is the one configuration a closed-vs-nodal known answer cannot see",
     [(r'^NOON = K\.NOON$', 'L.ENDSTOP = (0.0, 0.0)\nNOON = K.NOON')],
     1, "modules has drifted", None, CURRENT),

    # ---- AY1b: THE licence.  Mutates nothing; runs against a pre-s156 report. -------------------
    ("ay1b-epoch",
     "the UNMODIFIED gate is run against a report rendered before s156's DSP change — every "
     "number here is an absolute level, so a stale epoch must be REFUSED, not read",
     [], 1, "AY1b", None, STALE),

    # ---- AY2: the well-posedness screen, and the MUTE classification ----------------------------
    ("ay2-all-ambiguous",
     "every detent's across-stimulus spread is inflated past its own requirement, so a knob-keyed "
     "correction is inside the ambiguity of the thing it would fit EVERYWHERE — the gate must "
     "refuse rather than fit (this is task A's closing argument, applied here)",
     [(r'float\(max\(need\) - min\(need\)\)', '1e3')],
     1, "not well posed", None, CURRENT),

    ("ay2-mute",
     "the mute threshold is pushed below any reachable level, so LEVEL min is no longer classified "
     "as a mute — the 'MODEL MUTES' line must disappear, proving it is read from the data and not "
     "printed for a detent chosen by hand",
     [(r'^MUTE_DB = -100\.0$', 'MUTE_DB = -1e9')],
     0, None, "MODEL MUTES", CURRENT),

    # ---- AY3: the known answer, its vacuity, and the family verdict -----------------------------
    ("ay3-ka-broken",
     "the inversion is given a small constant offset, so it no longer returns the shipped taper "
     "when run against the model's own levels — the recovered curve would not be a measurement",
     [(r'return float\(math\.exp\(float\(np\.interp\(target, dB, lo\)\)\)\), "interp"',
       'return float(math.exp(float(np.interp(target, dB, lo)))) + 1e-6, "interp"')],
     1, "does not return the shipped taper", None, CURRENT),

    ("ay3-ka-vacuous",
     "the known answer is made to check ZERO points — it can then neither pass nor fail, and a "
     "known answer that checked nothing licenses nothing (`empty-gate-must-fail`)",
     [(r'            if x not in res\[sw\] or not np\.isfinite\(res\[sw\]\[x\]\[0\]\) or '
       r'res\[sw\]\[x\]\[0\] < MUTE_DB:', '            if True:')],
     1, "empty-gate-must-fail", None, CURRENT),

    # ⚠⚠ s173, TWO stale things in this one arm, both from the same root as the control's:
    #  (a) its replacement was `x ** p`, written when `p` was an EXPONENT.  s163 made `p` the
    #      shipped PWL CALLABLE, so the mutant died on a TypeError and scored rc=1 — the arm was
    #      "failing" for a reason that had nothing to do with the guard it aims at.
    #  (b) it broke the FREE CURVE only, which forced the fallback on the s162 epoch because the
    #      exponent family was outside the ambiguity there.  On this epoch the exponent family
    #      REACHES on its own (that is AY3's headline), so nuking the free curve alone leaves the
    #      verdict at "AN EXPONENT IS ENOUGH" and the fallback branch is never reached.  Both
    #      non-shipped families are replaced now, which is what the arm's own description meant.
    ("ay3-family",
     "BOTH non-shipped families are replaced by the SHIPPED taper, so neither can buy anything and "
     "the verdict must fall back to GATE K's closure — otherwise 'THE FAMILY IS WHAT DECIDES IT' "
     "is a caption, and it is the sentence that re-opens a question closed since s103",
     [(r'score\(\{x: need_tap\[x\]\["mean"\] for x in need_tap\}\)',
       'score({x: p(x) for x in need_tap})'),
      (r'^    best_rms, best_exp = min\(scored\)$',
       '    best_rms, best_exp = min(scored); best_rms = ship_rms')],
     0, "STANDS on this epoch", None, CURRENT),

    # ⭐ s173, NEW: the first branch only became reachable when the exponent family started to
    # reach, so it has never been mutation-tested.  Degrade the exponent alone and the verdict must
    # move to the OTHER branch — which is what proves the three-way verdict reads its three inputs
    # rather than printing whichever sentence the epoch it was written on happened to need.
    ("ay3-exponent",
     "the exponent family alone is degraded, so the free curve becomes the only one inside the "
     "ambiguity and the verdict must read 'THE FAMILY IS WHAT DECIDES IT'",
     [(r'^    best_rms, best_exp = min\(scored\)$',
       '    best_rms, best_exp = min(scored); best_rms = ship_rms')],
     0, "THE FAMILY IS WHAT DECIDES IT", None, CURRENT),

    # ---- AY4: the outside corroboration -------------------------------------------------------
    # ⚠⚠ s173: this arm used to MOVE THE BAND to a hard-coded 20-25 % and assert the literal string
    # "AWAY FROM".  That configuration was chosen on the s162 epoch, where shipped sat inside the
    # moved band and required outside.  On this epoch the two half-rotations are 15.41 % and
    # 23.74 %, so the same moved band puts REQUIRED inside and the arm asserts a string the
    # unmutated gate ALREADY prints — a mutation that cannot discriminate, dressed as one.
    # ⇒ mutate the RELATION instead of the constants: swap the two operands' roles.  A computed
    # verdict must then flip, on any epoch and for any band, and the runner checks it against what
    # the CONTROL actually printed rather than against a transcribed word (see FLIP below).
    # ⚠ It would fail spuriously if the two values were exactly equidistant from the band centre;
    # that is a measure-zero coincidence and it fails in the safe direction (a false alarm, not a
    # false pass).
    ("ay4-band",
     "the shipped and required half-rotations swap roles in the TOWARD/AWAY comparison — the "
     "printed direction must flip, or the one piece of outside corroboration in this gate is "
     "narration",
     [(r'moved_in = \(not ship_band\) and band', 'moved_in = (not band) and ship_band'),
      (r'moved_toward = abs\(half - centre\) < abs\(ship_half - centre\)',
       'moved_toward = abs(ship_half - centre) < abs(half - centre)')],
     0, None, None, CURRENT),

    # ---- AY5(c): THE arm.  This verdict is why task D closes as specified. ----------------------
    # ⚠⚠ s189: RE-POINTED, and the reason is the session's second finding.  The retired arm shrank
    # item 9's targets until a FINITE supremum cleared them.  There is no finite supremum any more
    # -- s181's end stop made the mixed ratio unbounded as L -> 0 -- so that arm could no longer
    # test anything, and the verdict it guarded ("0 of 2 REACH") has been WITHDRAWN.  What must be
    # armed now is the withdrawal itself: is "NO VERDICT IS AVAILABLE" a computed consequence of
    # the supremum being infinite, or narration?  Restore a finite supremum and the gate must go
    # back to grading the targets against it.
    ("ay5-sup-finite",
     "the supremum is forced FINITE again (the pre-s181 value), so the gate must abandon its "
     "no-verdict branch and grade item 9's targets against the bound — if it still refuses, the "
     "withdrawal is hard-coded rather than computed",
     [(r'sup_fold = float\("inf"\)', 'sup_fold = 1.0 / old_ship')],
     0, None, "NO VERDICT IS AVAILABLE", CURRENT),
    # ⚠⚠ s190: THE NEEDLE WAS "REACH, at the family's own SUPREMUM" (i.e. the arm assumed the
    # finite supremum would land in the 0-of-N REACH sub-branch) UNTIL item 9's targets were
    # RE-POINTED at s190's smaller, current-epoch pair -- at which point the SAME finite supremum
    # legitimately clears both of them, the code correctly takes the OTHER sub-branch ("N of M
    # reach"), and the old needle went missing on a gate that was working perfectly. This is the
    # arm depending on `targets` without saying so (`suspect-the-mutation-before-the-guard`, s110):
    # the load-bearing thing this arm exists to prove is "the vacuous no-verdict branch was
    # actually LEFT", not "which of its two live sub-branches fired" -- so the check now asserts
    # the ABSENCE of the no-verdict text, which is true under a finite supremum regardless of
    # which target pair is loaded, on this epoch or the next one that re-measures item 9.

    # ---- s189: the two NEW distinctions this session introduced, both load-bearing -------------
    # `invert_dB`'s low-side status was ONE value ('below') until s181's end stop put a finite
    # floor under dB_model(L).  'below-floor' is a statement about the DEVICE (unreachable by any
    # taper) and 'below-sample' one about the LADDER (reachable, unsampled); collapsing them is
    # what let a fabricated `required L = 0.0000` look like a reading.
    ("ay3-floor-split",
     "the floor comparison is disabled, so every low-side refusal collapses back to the single "
     "'below-sample' status — the DEVICE-vs-LADDER distinction must disappear with it, or the "
     "gate is printing a status it did not compute",
     [(r'if floor is not None and target <= floor:', 'if False:')],
     0, None, "below-floor", CURRENT),

    # The ambiguity bar and the families it grades must share a population.  Pooled over every
    # well-defined detent the bar is inflated by the two the solve cannot place -- whose spreads
    # are the largest in the table, precisely because that is where s181's bleed floor sits -- and
    # the SHIPPED family crosses from OUTSIDE to INSIDE on that alone.
    ("ay3-amb-membership",
     "the ambiguity bar is re-pooled over every well-defined detent instead of the detents the "
     "families were actually scored on — the shipped family's verdict must flip, or the bar is "
     "not being computed on the population it grades",
     [(r'amb = \[rows\[x\]\["need_spread"\] for x in members',
       'amb = [rows[x]["need_spread"] for x in rows')],
     0, None, None, CURRENT),

    # ---- AY6: the corner nothing may move ------------------------------------------------------
    ("ay6-corner",
     "the recovered curve's top is nudged off 1.0 where only AY6 looks, so the bleed-free corner "
     "moves — GATE K7's ratio, GATE O's A3 ledger, GATE L's |rho| and OdToneRestore's base row all "
     "read there",
     [(r'a1, b1 = K\.coef_closed\(1\.0, Lm\.get\(TOP, 1\.0\)\)',
       'a1, b1 = K.coef_closed(1.0, Lm.get(TOP, 1.0) * 0.99)')],
     1, "AY6 FAIL", None, CURRENT),
]


def preflight():
    """Assert the property that makes a report redirect unnecessary (see the docstring)."""
    src = open(SRC).read()
    m = re.search(r'ap\.add_argument\("--json",\s*default=([^)\s,]+)', src)
    if m is None:
        sys.exit("_mutate_gate_ay: could not find the --json argument at all — the assumption that "
                 "a mutant writes no report is unverified, so refusing to run")
    if m.group(1) != "None":
        sys.exit(f"_mutate_gate_ay: --json now defaults to {m.group(1)} — a mutant would write a "
                 f"falsified report over the real gate's (s153).  Add a PID-unique redirect before "
                 f"running this again.")
    print(f"  preflight OK  --json has no default, so a mutant invoked without it writes nothing")


def build(muts):
    src = open(SRC).read()
    for pat, rep in muts:
        new, n = re.subn(pat, rep, src, flags=re.M)
        if n == 0:
            return None
        src = new
    open(MUT, "w").write(src)
    return MUT


# ⭐ s173: arms whose verdict is EPOCH-DEPENDENT cannot assert a transcribed word — that is how
# `ay4-band` came to assert a string the unmutated gate already printed.  Instead, name a regex
# with one capture group; the arm passes iff the token it captures DIFFERS from the token the
# CONTROL captured on the same run.  The comparison is against measured output, so it stays sharp
# on every epoch and needs no maintenance when a verdict legitimately flips.
FLIP = {
    "ay4-band": r"the requirement moves the pot (INTO|TOWARD|AWAY FROM) the band",
    # s189: the shipped family's INSIDE/OUTSIDE verdict must move when the bar's population does.
    "ay3-amb-membership": r"shipped exponent\s+[\d.]+ dB\s+(INSIDE|OUTSIDE)",
}


def _flip_token(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None


def main():
    n_cv = sum(1 for a in ARMS if a[3] == 0) - 1
    print(f"MUTATION TEST — GATE AY  ({len(ARMS)} arms, {n_cv} computed-verdict)\n")
    preflight()
    print()
    bad = []
    control_out = ""
    for name, why, muts, exp_rc, need, absent, report in ARMS:
        if build(muts) is None:
            print(f"  ❌ {name:18} PATCH DID NOT APPLY — the arm tests nothing")
            bad.append(name)
            continue
        r = subprocess.run([sys.executable, os.path.relpath(MUT, ROOT), report],
                           cwd=ROOT, capture_output=True, text=True)
        out = r.stdout + r.stderr
        if name == "control":
            control_out = out
        ok_rc = (r.returncode != 0) if exp_rc else (r.returncode == 0)
        ok_txt = (need is None or need in out) and (absent is None or absent not in out)
        flip_msg = None
        if name in FLIP:
            pat = FLIP[name]
            was, now = _flip_token(pat, control_out), _flip_token(pat, out)
            if was is None or now is None:
                ok_txt, flip_msg = False, (
                    f"the flip pattern matched neither the control ({was!r}) nor the arm ({now!r}) "
                    f"-- the arm can neither pass nor fail (`empty-gate-must-fail`)")
            elif was == now:
                ok_txt, flip_msg = False, (
                    f"the verdict did NOT flip: control and arm both read {was!r}, so the direction "
                    f"is narrated rather than computed from its two operands")
        if ok_rc and ok_txt:
            print(f"  ✅ {name:18} rc={r.returncode}  {why[:64]}")
        else:
            reason = ("rc" if not ok_rc else
                      flip_msg if flip_msg else
                      ("missing " + repr(need) if need and need not in out
                       else "did not suppress " + repr(absent)))
            print(f"  ❌ {name:18} rc={r.returncode} ({reason})  — {why[:54]}")
            bad.append(name)
        if os.path.exists(MUT):
            os.remove(MUT)

    print(f"\n  {len(ARMS) - len(bad)}/{len(ARMS)} arms behaved as specified")
    if bad:
        sys.exit(f"MUTATION TEST FAILED: {', '.join(bad)}")


if __name__ == "__main__":
    main()
