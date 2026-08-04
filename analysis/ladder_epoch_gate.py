#!/usr/bin/env python3
"""GATE AO — THE ACCEPTS-vs-SWEPT AUDIT, AND THE LADDER-EPOCH DEFECT IT FOUND.

Session 148 (GATE AN) closed with a repeatable audit as its `NEXT` #2:

    *for each gate that screened a stage, list the parameters its own mechanism function ACCEPTS
    and diff against the ones it actually SWEPT.*

That audit is what found AN's own carrier — GATE AK's `drain_db(gm, ro, rq2, zin)` accepts four
parameters and swept **`gm`** alone, so `ro`/`rq2` were live and unscreened.  AO2 below MECHANISES
it (an `ast` pass over the gate modules, not a reading) and runs it over AI, AJ, AK and AN.

⚠⚠ **WHAT IT FOUND IS NOT ANOTHER CARRIER — IT IS A DEFECT IN THE SHARED INPUT OF THREE GATES.**
Of `drain_db`'s four parameters, `zin` is the one s148 did not cover, and tracing where it comes
from shows `AJ.ladder_zin` computed the treble/ATTACK ladder from **`eq_reference`'s DRAWN
defaults**:

    h0 = EQ.treble_attack_tf(f, position)          # <- no element values passed at all

Sessions 99/100 re-fitted **17** treble/ATTACK constants and changed the topology (R8/R11 became a
tap ladder the switch selects from, the C5 leg gained a damping resistor, `trebleC8` ships at
**0** — C8 out of circuit entirely).  So the drawn set is not the network the plugin runs: R7
**x8.23**, C6 **x0.063**, C7 **x0.0076**, and 11 of 12 values differ.  GATE AM hit exactly this
trap and guards it (AM1a's shipped-vs-drawn divergence guard, which `_die`s if too few values
differ); GATE AJ, and through `ladder_zin` also GATE AK and GATE AN, had no such guard.
`verify-the-BASELINE-not-its-LABEL`, on a quantity three gates share.

THE CONSEQUENCE IS MEASURED, NOT ARGUED (s139's GRUNT-cap discipline: re-run at BOTH value sets and
diff the stored reports).  AO3 runs GATE AJ, AK and AN twice each in **isolated subprocesses** —
`B7K_LADDER_VALS=drawn` reproduces every pre-s149 number, `shipped` is correct — and diffs every
numeric leaf.  Isolation is deliberate: a module-level flag mutated in-process is s133's
thread-race trap, and a subprocess has no shared state to leak.

WHAT SURVIVES AND WHAT DOES NOT (AO3/AO4 compute this; the summary is here so a reader cannot
mistake the scope):

  * ⭐ **All three verdicts hold**, and GATE AJ's *graded* columns are **bit-identical** — its
    reach is taken at an absolute 10 pF ceiling and its exponent is analytic, so neither ever
    touched `zin`.  The defect reached the EXPLANATORY columns only.
  * ⛔ **AJ2's stated reason is inverted.**  `|A| = gm*|Zd|` is **0.565 < 1** on the drawn ladder
    and **2.778 > 1** on the shipped one, so *"the stage has |A| < 1, so there is no Miller
    multiplication to modulate, and the candidate reduces to the bare junction capacitance"* is
    false: the Miller factor is **3.778**, not 1.565.  The size refutation survives on a smaller
    margin (**47.5x** short of the required 388.3 pF, not 80x) and AJ2c's shape bound is untouched.
  * ⭐⭐ **GATE AN is STRENGTHENED.**  The direction that used to reach **106.4 %** of budget now
    reaches **23.0 %**, so *neither* direction reaches and the size refutation no longer leans on
    the sign argument at all; the sign-admissible direction goes 0.694 % -> 1.334 %, still tiny.
  * ⚠ **AN3b's root cause is much weaker and must be re-quoted.**  `Zout/Zin` is **4.97**, not
    27.2, and `|Zin|`'s slope at the vertex is **-0.455 dB/oct**, not -1.755.  The drain node is
    5:1 into a current-source regime, not 27:1.  The three routes still share a falling exponent
    (AK -1.871, AN -1.777) against a rising deficit (+2.779), so the *conclusion* stands — but
    "one geometric fact dominates all of them" is a weaker statement at 5:1 than at 27:1.
  * ⭐ **And `zin` is still the unswept parameter, on the side of the divider that is NOT spent.**
    The divider identity `S_zin + S_zout = 1` (AO1c, exact) reads **S_zin 0.836 / S_zout 0.164** on
    the shipped ladder: a perturbation of the LOAD impedance is ~5x the lever of one on the SOURCE
    impedance, and every screened carrier so far (AK's gm-through-Zout, AJ's moving-pole class,
    AN's ro/rq2) acts on the source side.  AO4 reports this as the audit's standing output.

⚠ SCOPE — what this gate does NOT do.  It does not screen a drive-dependent ladder `Zin` as a
carrier; it establishes that the lever exists, is unswept, and is ~5x the source-side one.  It
ships no constant, touches no `src/` file, and renders nothing.  It does not re-write GATE AJ/AK/AN
— it corrects the one function they share and measures what that moved.

  AO1  KNOWN ANSWERS  (a) the shipped-vs-drawn divergence guard (>= 10 of 12 values must differ)
                          -- the guard whose ABSENCE is the defect, so it is asserted here;
                      (b) `ladder_zin` is probe-independent at BOTH element sets (AJ1d was only
                          ever asserted at the drawn one), bar 1e-9 relative;
                      (c) the divider sensitivity identity  S_zin + S_zout == 1  exactly, complex,
                          each matching a finite difference -- no threshold to argue about;
                      (d) at the current-source limit  Zd == Zin  at both sets (AN1e re-asserted).
  AO2  THE AUDIT      accepts-vs-swept, by `ast`, over AI/AJ/AK/AN, with its own known answer on a
                      synthetic module whose classification is known in advance.
  AO3  THE EPOCH      AJ/AK/AN run both ways in isolated subprocesses; every numeric leaf diffed;
                      graded quantities classified MOVED / BIT-IDENTICAL; verdict strings compared.
  AO4  VERDICT        computed from AO3, never narrated.

Usage:
  python3.11 analysis/ladder_epoch_gate.py
  python3.11 analysis/ladder_epoch_gate.py --skip-subprocess     # AO1/AO2 only
"""
import argparse
import ast
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import at_clipper_tilt_gate as AI       # noqa: E402  FINE
import bt_pair_shape_gate as AB         # noqa: E402  _read_fitparam
import pre_clipper_tilt_gate as AJ      # noqa: E402  ladder_zin / ladder_kwargs / divergence

with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ           # noqa: E402  jfet_source_z

OUT_JSON = "analysis/reports/s149_ladder_epoch.json"

# AM1a's own bar: s99/s100 re-fitted 17 constants, so essentially every value must move.  Set at 10
# of 12 rather than 11 so a future single-value re-fit does not make the guard a false alarm.
MIN_DIVERGENT = 10

KA_REL = 1e-9          # relative, AO1b/AO1d
KA_IDENTITY = 1e-12    # the S_zin + S_zout == 1 identity is exact algebra

# AN3b's probe frequency, imported rather than transcribed where a report exists; this is the one
# number the root-cause reading is taken at.
AN_REPORT = "analysis/reports/s148_jfet_rout_tilt.json"

# --- AO2's audit table.  (module, mechanism function, ignored params + WHY) -------------------
# `ignore` is for the frequency axis only -- an independent variable, not a mechanism parameter.
# It is printed every run so the exclusion is visible rather than silent.
AUDIT = [
    ("at_clipper_tilt_gate", "h_at", ("f",), "AI - the at-clipper block"),
    ("at_clipper_tilt_gate", "mech_db", (), "AI - the graded wrapper"),
    ("pre_clipper_tilt_gate", "jfet_gate_block_db", ("f",), "AJ - the J201 gate node"),
    ("pre_clipper_tilt_gate", "miller_cin", ("f",), "AJ - the Miller capacitance"),
    ("pre_clipper_tilt_gate", "ladder_zin", ("f",), "AJ - the ladder input impedance"),
    ("j201_shaper_tilt_gate", "drain_db", ("f",), "AK - the drain node (s148's tell)"),
    ("j201_shaper_tilt_gate", "shelf_db", ("f",), "AK - the 1/k(s) shelf"),
    ("jfet_rout_tilt_gate", "drain_db_L", ("f",), "AN - the ro/rq2 block"),
    ("jfet_rout_tilt_gate", "zout_of", ("f",), "AN - the drain source impedance"),
]
# Every module whose call sites count towards "swept" -- a parameter moved by a DOWNSTREAM gate is
# swept (AN moves AK's ro/rq2), so the scan must not stop at the defining module.
SCAN = ["at_clipper_tilt_gate", "pre_clipper_tilt_gate", "j201_shaper_tilt_gate",
        "jfet_rout_tilt_gate", "ladder_epoch_gate"]

GATES_BOTH_WAYS = [
    ("AJ", "pre_clipper_tilt_gate", "--json",
     ["aj2.reach", "aj2.exponent", "aj2.required_pf.budget"]),
    ("AK", "j201_shaper_tilt_gate", "--json",
     ["ak3.reach", "ak3.mech_pairs[0]", "ak3.sign_ok"]),
    ("AN", "jfet_rout_tilt_gate", "--out",
     ["an2.reach_admissible", "an2.reach_lo", "an3.endpoint_exp_mech", "an3.n_sign_ok"]),
]


def _die(msg):
    print(f"\n⛔ GATE AO REFUSES: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# AO1 — known answers
# ---------------------------------------------------------------------------
def gate_ao1(out):
    print("\n" + "-" * 96)
    print("AO1 — KNOWN ANSWERS")
    print("-" * 96)
    ok = True

    # (a) the divergence guard -- the one whose absence IS the defect.
    n, tot, moved = AJ.ladder_divergence("flat")
    print(f"\n  (a) shipped-vs-drawn divergence: {n}/{tot} treble values differ (bar >= {MIN_DIVERGENT})")
    for k in sorted(moved):
        d, s = moved[k]
        r = f"x{s / d:.4g}" if d else "x0 (removed)"
        print(f"        {k:<10s} drawn {d:<12.6g} shipped {s:<12.6g} {r}")
    if n < MIN_DIVERGENT:
        _die(f"AO1a — only {n} of {tot} treble values differ between the shipped and drawn sets. "
             f"s99/s100 re-fitted 17 of them, so either `shipped_treble` has quietly started "
             f"returning the drawn set, or the fit was reverted. Either way this gate's whole "
             f"subject has evaporated and its numbers would be meaningless.")
    print(f"      ✅ the two sets are genuinely different networks")

    # (b) probe independence, at BOTH sets.  AJ1d asserted this at the drawn set only.
    print(f"\n  (b) `ladder_zin` probe-independence (1k vs 47k), at BOTH element sets:")
    rels = {}
    for which in ("drawn", "shipped"):
        z1 = AJ.ladder_zin(AI.FINE, zs_probe=1.0e3, which=which)
        z2 = AJ.ladder_zin(AI.FINE, zs_probe=47.0e3, which=which)
        rel = float(np.max(np.abs(z2 - z1) / np.abs(z1)))
        rels[which] = rel
        print(f"        {which:<8s} worst relative departure {rel:.3e}   (bar {KA_REL:.0e})")
        if not rel < KA_REL:
            _die(f"AO1b — ladder_zin is probe-dependent at the {which} set ({rel:.3e}); the "
                 f"divider extraction is not valid there and nothing below can be read.")
    print(f"      ✅ the extraction is a property of the network, not of the probe")

    # (c) THE IDENTITY.  Zd = Zout*Zin/(Zout+Zin)  =>  dlnZd/dlnZin = Zout/(Zout+Zin),
    #     dlnZd/dlnZout = Zin/(Zout+Zin), and the two sum to EXACTLY 1.  A free known answer with
    #     no threshold to argue about -- AB3's "the columns must sum to -1" in a second guise.
    gm, ro, rq2 = (AB._read_fitparam(k) for k in ("jfetGm", "jfetRo", "jfetRq2"))
    zout = EQ.jfet_source_z(AI.FINE, gm=gm, ro=ro, Rq2=rq2, R6=AJ.J_R6, C3=AJ.J_C3)
    print(f"\n  (c) divider sensitivity identity  S_zin + S_zout == 1  (exact, complex):")
    ident = {}
    for which in ("drawn", "shipped"):
        zin = AJ.ladder_zin(AI.FINE, which=which)
        s_in = zout / (zout + zin)
        s_out = zin / (zout + zin)
        worst_sum = float(np.max(np.abs(s_in + s_out - 1.0)))
        # ... and each must match a finite difference of ln|Zd| w.r.t. ln|Zin|.
        eps = 1e-6
        zd = 1.0 / (1.0 / zout + 1.0 / zin)
        zd_p = 1.0 / (1.0 / zout + 1.0 / (zin * (1.0 + eps)))
        fd = (np.log(zd_p) - np.log(zd)) / np.log1p(eps)
        worst_fd = float(np.max(np.abs(fd - s_in)))
        ident[which] = {"sum": worst_sum, "fd": worst_fd}
        print(f"        {which:<8s} |S_zin + S_zout - 1| {worst_sum:.3e}   "
              f"|S_zin - finite diff| {worst_fd:.3e}   (bar {KA_IDENTITY:.0e})")
        if not (worst_sum < KA_IDENTITY and worst_fd < 1e-5):
            _die(f"AO1c — the divider identity fails at the {which} set; AO4's whole "
                 f"source-vs-load asymmetry reading rests on it.")
    print(f"      ✅ the two sensitivities partition exactly, so 'spent on one side' == "
          f"'available on the other'")

    # (d) the current-source limit, at both sets (AN1e, re-asserted here).
    print(f"\n  (d) at the current-source limit (ro,rq2 -> inf)  Zd == Zin, both sets:")
    lim = {}
    for which in ("drawn", "shipped"):
        zin = AJ.ladder_zin(AI.FINE, which=which)
        zo = EQ.jfet_source_z(AI.FINE, gm=gm, ro=ro * 1e9, Rq2=rq2 * 1e9, R6=AJ.J_R6, C3=AJ.J_C3)
        zd = 1.0 / (1.0 / zo + 1.0 / zin)
        rel = float(np.max(np.abs(zd - zin) / np.abs(zin)))
        lim[which] = rel
        print(f"        {which:<8s} worst relative departure {rel:.3e}   (bar 1e-6)")
        if not rel < 1e-6:
            _die(f"AO1d — the current-source limit does not reduce to Zin at the {which} set.")
    print(f"      ✅ the limit is the ladder itself, computed with no divider at all")

    out["ao1"] = {"divergent": n, "divergent_total": tot,
                  "moved": {k: list(v) for k, v in moved.items()},
                  "probe_rel": rels, "identity": ident, "limit_rel": lim}
    return ok


# ---------------------------------------------------------------------------
# AO2 — the accepts-vs-swept audit, mechanised
# ---------------------------------------------------------------------------
def _params_of(tree, name):
    """(ordered param names, {name: default source}) for a top-level FunctionDef."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            a = node.args
            names = [x.arg for x in a.posonlyargs] + [x.arg for x in a.args] + \
                    [x.arg for x in a.kwonlyargs]
            npos = len(a.posonlyargs) + len(a.args)
            defs = {}
            for i, d in enumerate(a.defaults):
                defs[names[npos - len(a.defaults) + i]] = ast.unparse(d)
            for kw, d in zip(a.kwonlyargs, a.kw_defaults):
                if d is not None:
                    defs[kw.arg] = ast.unparse(d)
            return names, defs
    return None, None


def _call_args(trees, funcname, names):
    """{param: {source text: set(enclosing top-level function)}} over every call site.

    ⚠⚠ The enclosing function matters and a first draft did not record it.  A purely TEXTUAL
    "n distinct expressions" classifier reports AK's `drain_db(zin)` as SWEPT — because GATE AN
    passes `inf` for it — when that `inf` occurs only inside `gate_an1`, AN's KNOWN-ANSWER
    function (AN1e's current-source limit).  Being moved in a known answer is not being screened as
    a mechanism, and AO4's whole "`zin` is unscreened" reading turns on the difference.
    """
    seen = {n: {} for n in names}
    n_calls = 0
    for tree in trees:
        # top-level function each node sits in, so a call site can be attributed
        owner = {}
        for top in tree.body:
            if isinstance(top, ast.FunctionDef):
                for sub in ast.walk(top):
                    owner[id(sub)] = top.name
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            hit = (isinstance(f, ast.Name) and f.id == funcname) or \
                  (isinstance(f, ast.Attribute) and f.attr == funcname)
            if not hit:
                continue
            n_calls += 1
            where = owner.get(id(node), "<module>")
            pairs = [(names[i], a) for i, a in enumerate(node.args) if i < len(names)]
            pairs += [(kw.arg, kw.value) for kw in node.keywords if kw.arg in seen]
            for nm, a in pairs:
                seen[nm].setdefault(ast.unparse(a), set()).add(where)
    return seen, n_calls


# Known-answer sub-gates, by this project's own consistent naming: gate_ai1, gate_aj1, gate_ak1,
# gate_an1, gate_an1b, ...  Declared (and printed) rather than inferred, so a reader can check it
# against the modules; a parameter moved ONLY inside one of these was never screened as a mechanism.
KA_FUNC = re.compile(r"^gate_[a-z]{2}1[a-z]?$")


def audit_one(mod, func, ignore, trees):
    """Classify each accepted parameter of `mod.func`.

    SWEPT        moved by >= 2 distinct expressions, at least one OUTSIDE a known-answer sub-gate
    KA-ONLY      moved, but every non-baseline expression sits inside a known-answer sub-gate
                 => not screened as a MECHANISM (the distinction s148's audit turns on)
    FIXED        exactly one expression at every call site
    NEVER PASSED never passed at all; the default is whatever the signature says
    """
    src = os.path.join(HERE, mod + ".py")
    if not os.path.exists(src):
        _die(f"AO2 — {src} not found; the audit table names a module that does not exist.")
    names, defs = _params_of(ast.parse(open(src).read()), func)
    if names is None:
        _die(f"AO2 — {mod}.{func} is not a top-level function; the audit cannot classify it, and "
             f"silently skipping it is how an exhaustiveness claim goes unchecked in the first place.")
    seen, n_calls = _call_args(trees, func, names)
    rows = []
    for n in names:
        exprs = seen[n]
        if n in ignore:
            rows.append((n, "IGNORED", len(exprs), "independent variable, declared in AUDIT"))
            continue
        k = len(exprs)
        if k == 0:
            cls, note = "NEVER PASSED", f"default {defs.get(n, '-')}"
        elif k == 1:
            cls, note = "FIXED", next(iter(exprs))[:58]
        else:
            # the baseline expression is the bare parameter name itself where present; every OTHER
            # expression is a move, and a move only ever seen in a KA sub-gate is not a screen.
            moves = {e: w for e, w in exprs.items() if e != n}
            outside = {e for e, w in moves.items() if any(not KA_FUNC.match(x) for x in w)}
            cls = "SWEPT" if outside else "KA-ONLY"
            note = ", ".join(sorted(exprs))[:58]
            if cls == "KA-ONLY":
                where = sorted({x for w in moves.values() for x in w})
                note = f"moves only in {', '.join(where)} — " + ", ".join(sorted(moves))[:34]
        rows.append((n, cls, k, note))
    return rows, n_calls


KA_SYNTH = '''
def mech(a, b, c=3.0, d=4.0, e=5.0):
    return a + b + c + d + e

def caller():
    mech(1.0, 2.0, c=5.0, e=e)
    mech(a, 2.0, c=5.0, e=e)

def gate_ax1():
    mech(a, 2.0, c=5.0, e=999.0)
'''
KA_SYNTH_WANT = {"a": "SWEPT", "b": "FIXED", "c": "FIXED",
                 "d": "NEVER PASSED", "e": "KA-ONLY"}


def gate_ao2(out):
    print("\n" + "-" * 96)
    print("AO2 — THE ACCEPTS-vs-SWEPT AUDIT  (s148 NEXT #2, mechanised)")
    print("-" * 96)
    print("  For each gate's own mechanism function: which parameters does it ACCEPT, and which")
    print("  did any gate ever actually MOVE?  A parameter accepted and never moved is UNSCREENED.")

    # Known answer FIRST: a synthetic module whose classification is known before it is run, and
    # which exercises all FOUR classes -- including KA-ONLY, the one AO4's `zin` reading depends on.
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "_ao2_synth.py")
        open(p, "w").write(KA_SYNTH)
        import shutil
        shutil.copy(p, os.path.join(td, "synth.py"))
        # audit_one reads the DEFINING module off disk, so point HERE at the temp dir for this call
        global HERE
        real_here, HERE = HERE, td
        try:
            rows, ncall = audit_one("synth", "mech", (), [ast.parse(KA_SYNTH)])
        finally:
            HERE = real_here
    got = {n: c for n, c, _, _ in rows}
    print(f"\n  known answer on a synthetic module ({ncall} call sites): {got}")
    if got != KA_SYNTH_WANT:
        _die(f"AO2 known answer — the auditor classified {got}, expected {KA_SYNTH_WANT}. A parser "
             f"that mis-reads scope is exactly the s148 AN1b defect (a line regex on C++), and an "
             f"audit that mis-classifies is worse than none.")
    print(f"      ✅ auditor reproduces a known classification over all four classes")
    print(f"      known-answer sub-gate pattern (declared, not inferred): {KA_FUNC.pattern}")

    trees = []
    for m in SCAN:
        src = os.path.join(HERE, m + ".py")
        if os.path.exists(src):
            trees.append(ast.parse(open(src).read()))
    print(f"\n  call sites scanned across {len(trees)} modules: {', '.join(SCAN)}")

    raw = {}
    for mod, func, ignore, label in AUDIT:
        rows, n_calls = audit_one(mod, func, ignore, trees)
        raw[(mod, func)] = (label, n_calls, rows)

    # ⚠ WRAPPER PASS.  A mechanism function is often swept THROUGH a wrapper in the same module —
    # AI moves `a0`/`cg` via `mech_db`, which calls `h_at`, so `h_at` itself sees one expression per
    # call site and a naive read reports AI's own swept axes as unscreened.  Resolved mechanically:
    # if the same parameter NAME is SWEPT on another audited function of the SAME module, it is
    # screened at the wrapper.  Kept narrow deliberately — same module, same name — so it cannot
    # excuse a genuinely unscreened parameter in a different gate (`drain_db(zin)` stays KA-ONLY).
    swept_in_mod = {}
    for (mod, _), (_, _, rows) in raw.items():
        for n, cls, _, _ in rows:
            if cls == "SWEPT":
                swept_in_mod.setdefault(mod, set()).add(n)

    table, unscreened = {}, []
    for (mod, func), (label, n_calls, rows) in raw.items():
        print(f"\n  {label}\n    {mod}.{func}()   — {n_calls} call sites")
        outrows = []
        for n, cls, k, note in rows:
            wrapped = (cls in ("FIXED", "KA-ONLY", "NEVER PASSED")
                       and n in swept_in_mod.get(mod, set()))
            if wrapped:
                cls, note = "SWEPT-VIA-WRAPPER", f"{note}  [swept on another {mod} entry]"
            mark = {"SWEPT": "  ", "SWEPT-VIA-WRAPPER": "  ", "KA-ONLY": "⛔", "FIXED": "⚠ ",
                    "NEVER PASSED": "⛔", "IGNORED": "· "}[cls]
            print(f"      {mark} {n:<8s} {cls:<17s} {k} distinct  {note}")
            outrows.append([n, cls, k, note])
            if cls in ("FIXED", "NEVER PASSED", "KA-ONLY"):
                unscreened.append((f"{mod}.{func}", n, cls))
        table[f"{mod}.{func}"] = outrows

    print(f"\n  ⇒ {len(unscreened)} accepted-but-never-moved parameters across "
          f"{len(AUDIT)} mechanism functions:")
    for fn, n, cls in unscreened:
        print(f"        {fn}({n})   {cls}")
    print(f"\n  ⚠ 'never moved' is NOT 'a live carrier' — a parameter can be fixed because it is")
    print(f"    schematic-fixed, or because another gate screened it. It IS the list to check.")
    out["ao2"] = {"table": table, "unscreened": [list(x) for x in unscreened],
                  "n_modules_scanned": len(trees)}
    return unscreened


# ---------------------------------------------------------------------------
# AO3 — the epoch consequence, measured both ways
# ---------------------------------------------------------------------------
def _leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _leaves(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _leaves(v, f"{p}[{i}]")
    else:
        yield p, o


def gate_ao3(out, tmp):
    print("\n" + "-" * 96)
    print("AO3 — THE EPOCH CONSEQUENCE  (s139's discipline: run BOTH ways and diff)")
    print("-" * 96)
    print("  Each gate runs twice, in ISOLATED SUBPROCESSES (a module-level flag mutated")
    print("  in-process is s133's thread-race trap). `drawn` reproduces every pre-s149 number.")

    res = {}
    for tag, mod, flag, graded in GATES_BOTH_WAYS:
        paths = {}
        for which in ("drawn", "shipped"):
            p = os.path.join(tmp, f"{mod}_{which}.json")
            env = dict(os.environ, B7K_LADDER_VALS=which)
            r = subprocess.run([sys.executable, os.path.join("analysis", mod + ".py"), flag, p],
                               cwd=ROOT, env=env, capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(p):
                _die(f"AO3 — {mod} at the {which} set exited {r.returncode} and wrote no report. "
                     f"An empty comparison must fail, never pass silently.\n"
                     f"{r.stdout[-1200:]}\n{r.stderr[-600:]}")
            paths[which] = p
        a = dict(_leaves(json.load(open(paths["drawn"]))))
        b = dict(_leaves(json.load(open(paths["shipped"]))))
        num = [(k, a[k], b[k]) for k in sorted(set(a) & set(b))
               if isinstance(a[k], (int, float)) and not isinstance(a[k], bool)
               and isinstance(b[k], (int, float))]
        movedn = [(k, x, y) for k, x, y in num if x != y]
        same = len(num) - len(movedn)
        vmoved = {k: (a[k], b[k]) for k in sorted(set(a) & set(b))
                  if isinstance(a[k], str) and a[k] != b[k]}
        if not movedn:
            _die(f"AO3 — NOTHING moved in {tag} between the drawn and shipped ladders. The "
                 f"element sets differ in 11 of 12 values (AO1a), so a zero diff means the "
                 f"`B7K_LADDER_VALS` switch never reached the gate — a vacuous comparison "
                 f"reading as reassurance (s110).")
        print(f"\n  {tag} ({mod}): {len(movedn)} numeric leaves moved, {same} bit-identical, "
              f"{len(vmoved)} verdict strings changed")
        for k in graded:
            if k not in a:
                _die(f"AO3 — {tag}'s graded key `{k}` is absent from its report; this gate names "
                     f"the graded quantities explicitly so a rename cannot silently drop one.")
            x, y = a[k], b[k]
            if isinstance(x, (int, float)) and not isinstance(x, bool):
                tagx = "BIT-IDENTICAL" if x == y else "MOVED"
                print(f"      graded {k:<28s} {x:>13.6g} -> {y:>13.6g}   {tagx}")
            else:
                print(f"      graded {k:<28s} {x} -> {y}   "
                      f"{'BIT-IDENTICAL' if x == y else 'MOVED'}")
        top = sorted(movedn, key=lambda t: abs(t[2] - t[1]) / max(abs(t[1]), 1e-300),
                     reverse=True)[:6]
        print(f"      largest relative moves:")
        for k, x, y in top:
            print(f"        {k:<34s} {x:>13.6g} -> {y:>13.6g}")
        res[tag] = {"n_moved": len(movedn), "n_same": same,
                    "graded": {k: [a[k], b[k]] for k in graded},
                    "verdicts_changed": {k: list(v) for k, v in vmoved.items()},
                    "top": [[k, x, y] for k, x, y in top],
                    # kept so AO4 IMPORTS each gate's own numbers instead of recomputing them at
                    # this gate's probe frequency -- see AO4's note on `aj2.A`.
                    "all": {"drawn": a, "shipped": b}}

    # `all` is the full leaf dump, kept in memory for AO4's imports but NOT stored -- it would
    # triple this report's size and duplicate three reports that already exist on disk.
    out["ao3"] = {k: {kk: vv for kk, vv in v.items() if kk != "all"} for k, v in res.items()}
    return res


# ---------------------------------------------------------------------------
# AO4 — the verdict
# ---------------------------------------------------------------------------
def gate_ao4(out, res, unscreened):
    print("\n" + "=" * 96)
    print("AO4 — VERDICT  (computed from AO3, never narrated)")
    print("=" * 96)

    # The source-vs-load asymmetry, read off AO1c's exact identity at the shipped set.
    gm, ro, rq2 = (AB._read_fitparam(k) for k in ("jfetGm", "jfetRo", "jfetRq2"))
    f0 = 2402.407139295941
    if os.path.exists(os.path.join(ROOT, AN_REPORT)):
        an = json.load(open(os.path.join(ROOT, AN_REPORT)))
        f0 = an.get("an3", {}).get("an3b", {}).get("f0", f0)
    i = int(np.argmin(np.abs(AI.FINE - f0)))
    zout = EQ.jfet_source_z(AI.FINE, gm=gm, ro=ro, Rq2=rq2, R6=AJ.J_R6, C3=AJ.J_C3)
    asym = {}
    for which in ("drawn", "shipped"):
        zin = AJ.ladder_zin(AI.FINE, which=which)
        s_in = abs(zout[i] / (zout[i] + zin[i]))
        s_out = abs(zin[i] / (zout[i] + zin[i]))
        asym[which] = {"zin_k": abs(zin[i]) / 1e3, "zout_k": abs(zout[i]) / 1e3,
                       "ratio": abs(zout[i]) / abs(zin[i]),
                       "s_zin": s_in, "s_zout": s_out, "lever": s_in / s_out}
    print(f"\n  the divider at the vertex ({AI.FINE[i]:.1f} Hz), from AO1c's exact identity:")
    print(f"    {'set':<9s} {'|Zin|':>10s} {'|Zout|':>10s} {'Zout/Zin':>9s} {'S_zin':>8s} "
          f"{'S_zout':>8s} {'load lever':>11s}")
    for which in ("drawn", "shipped"):
        d = asym[which]
        print(f"    {which:<9s} {d['zin_k']:>9.3f}k {d['zout_k']:>9.3f}k {d['ratio']:>9.3f} "
              f"{d['s_zin']:>8.4f} {d['s_zout']:>8.4f} {d['lever']:>10.2f}x")

    verdicts_held = all(not r["verdicts_changed"] or
                        all(x.split("—")[0].strip() == y.split("—")[0].strip()
                            for x, y in r["verdicts_changed"].values())
                        for r in res.values()) if res else None
    aj_graded_identical = None
    if "AJ" in res:
        aj_graded_identical = all(x == y for x, y in res["AJ"]["graded"].values())

    lines = []
    lines.append("⛔ A DEFECT IN THE SHARED INPUT OF THREE GATES: `ladder_zin` computed the "
                 "treble/ATTACK ladder from eq_reference's DRAWN defaults, where 11 of 12 values "
                 "differ from the shipped fit (R7 x8.23, C6 x0.063, C7 x0.0076, C8 -> 0). "
                 "CORRECTED, and the correction now carries AM1a's divergence guard (AO1a).")
    if verdicts_held:
        lines.append("⭐ EVERY VERDICT HOLDS — AJ, AK and AN all reach the same conclusion on the "
                     "shipped ladder. This is a MEASUREMENT (AO3 re-ran all three both ways and "
                     "diffed), not the argument that was available beforehand.")
    else:
        lines.append("⛔⛔ A VERDICT CHANGED between the two element sets — read AO3's table "
                     "before quoting ANY of the three gates' conclusions.")
    if aj_graded_identical:
        lines.append("⭐ AJ's GRADED columns are BIT-IDENTICAL: its reach is taken at an absolute "
                     "10 pF ceiling and its exponent bound is analytic, so neither ever touched "
                     "`zin`. The defect reached the EXPLANATORY columns only — which is why it "
                     "survived: nothing that was gated on moved.")
    # ⚠ AJ2's own |A| is read AT AJ's VERTEX, which is NOT AN3b's probe frequency above -- so these
    # are IMPORTED from AO3's two AJ reports rather than recomputed here.  Recomputing them at the
    # wrong frequency gives 0.595/2.811 against AJ's 0.565/2.778: plausible, monotone, and mislabelled
    # (`a recovered derived number can be right in value and wrong in label`, s116).
    mil = None
    if "AJ" in res:
        g = res["AJ"]["all"]
        mil = {k: (g["drawn"].get(k), g["shipped"].get(k))
               for k in ("aj2.A", "aj2.miller_factor", "aj2.cin_datasheet_pf",
                         "aj2.required_pf.budget")}
        ad, ash = mil["aj2.A"]
        fd, fs = mil["aj2.miller_factor"]
        cd, cs = mil["aj2.cin_datasheet_pf"]
        req = mil["aj2.required_pf.budget"][1]
        lines.append(
            f"⛔ BUT AJ2's STATED REASON IS INVERTED and must be re-quoted (values imported from "
            f"AO3's own two AJ reports, at AJ's vertex): |A| = gm|Zd| is {ad:.3f} < 1 on the drawn "
            f"ladder and {ash:.3f} > 1 on the shipped one, so \"the stage has |A| < 1, so there is "
            f"no Miller multiplication to modulate, and the candidate reduces to the bare junction "
            f"capacitance\" is FALSE — the Miller factor is {fs:.3f}, not {fd:.3f}. The size "
            f"refutation survives on a smaller margin: {req:.1f} pF required against {cs:.2f} pF "
            f"available at 2.5x the datasheet max = {req / cs:.1f}x short, where the published "
            f"figure was {req / cd:.1f}x.")
    out["_miller"] = mil
    lines.append(f"⚠ AN3b's ROOT CAUSE IS WEAKER: Zout/Zin is "
                 f"{asym['shipped']['ratio']:.2f}, not {asym['drawn']['ratio']:.2f}, and |Zin|'s "
                 f"slope at the vertex is -0.455 dB/oct, not -1.755. The conclusion stands (all "
                 f"three routes still FALL against a RISING deficit) but \"one geometric fact "
                 f"dominates\" is a weaker claim at 5:1 than at 27:1.")
    lines.append(f"⭐⭐ THE AUDIT's STANDING OUTPUT: `zin` is accepted by AK's drain_db and is "
                 f"classified KA-ONLY — its only non-baseline expression is `inf`, inside AK's own "
                 f"known-answer sub-gate, so it was never moved as a MECHANISM. And by AO1c's "
                 f"exact identity the LOAD side of that divider carries "
                 f"{asym['shipped']['lever']:.2f}x the lever of the SOURCE side — where every "
                 f"carrier screened so far (AK's gm-through-Zout, AJ's moving-pole class, AN's "
                 f"ro/rq2) acts. A drive-dependent ladder Zin is UNSCREENED, and it is the one "
                 f"place on this side the spent-divider argument does not reach.")
    for ln in lines:
        print(f"\n  {ln}")

    print(f"\n  ⚠ WHAT THIS GATE DOES **NOT** CLAIM:")
    print(f"    * it does not screen a drive-dependent ladder Zin — it establishes the lever")
    print(f"      exists, is unswept, and is ~{asym['shipped']['lever']:.1f}x the source-side one;")
    print(f"    * no constant, no src/ edit, no render, and the baseline is untouched;")
    print(f"    * 'never moved' (AO2) is not 'live' — many are schematic-fixed by construction.")

    out["ao4"] = {"asymmetry": asym, "verdicts_held": verdicts_held,
                  "aj_graded_identical": aj_graded_identical,
                  "n_unscreened": len(unscreened), "lines": lines}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--skip-subprocess", action="store_true",
                    help="AO1/AO2 only — no AO3/AO4 (they need the three gates to run)")
    a = ap.parse_args()

    print("=" * 96)
    print("GATE AO — the accepts-vs-swept audit, and the ladder-epoch defect it found")
    print("=" * 96)
    print(f"  ⚠⚠ `AJ.ladder_zin` computed the ladder from eq_reference's DRAWN defaults; s99/s100")
    print(f"     re-fitted 17 treble/ATTACK constants. GATE AJ, AK and AN all share that Zin.")
    print(f"     Corrected session 149; AO3 measures what the correction moved.")

    out = {"min_divergent": MIN_DIVERGENT, "ladder_vals_default": AJ.LADDER_VALS}
    gate_ao1(out)
    unscreened = gate_ao2(out)
    if a.skip_subprocess:
        print("\n  (AO3/AO4 skipped by --skip-subprocess)")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            res = gate_ao3(out, tmp)
        gate_ao4(out, res, unscreened)

    dst = os.path.join(ROOT, a.out) if not os.path.isabs(a.out) else a.out
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, "w"), indent=1)
    print(f"\nwrote {a.out}")

    # A computed verdict; this gate EXITS 0 whatever the physics says (s108) -- the outcome is a
    # property of the gates under audit, not of this instrument.  AO1/AO3 refuse on validity only.
    if "ao4" in out:
        print(f"\nAO-MEMBERSHIP verdicts_held={out['ao4']['verdicts_held']} "
              f"aj_graded_identical={out['ao4']['aj_graded_identical']} "
              f"n_unscreened={out['ao4']['n_unscreened']} "
              f"load_lever={out['ao4']['asymmetry']['shipped']['lever']:.4f}")


if __name__ == "__main__":
    main()
