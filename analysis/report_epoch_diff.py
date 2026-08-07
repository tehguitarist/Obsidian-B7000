#!/usr/bin/env python3.11
"""Diff two matrix reports the way this project's own rules require (session 177).

Every session that ships a constant has to answer the same three questions about two
`comprehensive_report.py` reports, and the project has got them wrong enough times to
have named the failure modes:

  1. MEMBERSHIP FIRST. `aggregate-moved-check-membership-first` has twelve recorded
     occurrences. A pooled OD number moves with the capture inventory's BLEND
     composition, not only with the model, so two reports must be shown to have the
     SAME membership before any total is differenced -- and s159 added the sharper
     case, where the conditions are identical by construction and it is an admission
     BAR that moves the population. This REFUSES on any membership difference.

  2. SCOPE, PER CAPTURE, NOT IN AGGREGATE. s114/s163/s166's discipline: a change is
     scoped only if the captures it should NOT reach are BIT-IDENTICAL. An aggregate
     that "barely moved" is consistent with two large offsetting moves. So this counts
     identical vs moved rows and breaks them out by capture class.

  3. THE GRADED ROWS, from `release_gate.py` itself -- never transcribed (s90).

Usage:
  /opt/homebrew/bin/python3.11 analysis/report_epoch_diff.py BASE.json CAND.json
"""
import json
import math
import subprocess
import sys

PY = sys.executable


def load(path):
    with open(path) as fh:
        return json.load(fh)


def key_of(cap):
    return cap.get("capture") or cap.get("name") or cap.get("file")


def blend_composition(caps):
    comp = {}
    for c in caps:
        b = (c.get("settings") or {}).get("blend")
        comp[b] = comp.get(b, 0) + 1
    return comp


def numeric_leaves(obj, prefix=""):
    """Every finite number in a capture record, addressed by path."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(numeric_leaves(v, f"{prefix}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(numeric_leaves(v, f"{prefix}[{i}]"))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if math.isfinite(obj):
            out[prefix] = float(obj)
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    base_path, cand_path = sys.argv[1], sys.argv[2]
    base, cand = load(base_path), load(cand_path)
    bc, cc = base["captures"], cand["captures"]

    print("=" * 88)
    print(f"BASE {base_path}\nCAND {cand_path}")
    print("=" * 88)

    # ---- 1. MEMBERSHIP -------------------------------------------------------
    bk = [key_of(c) for c in bc]
    ck = [key_of(c) for c in cc]
    print(f"\n[1] MEMBERSHIP  base n={len(bk)}  cand n={len(ck)}")
    only_b, only_c = sorted(set(bk) - set(ck)), sorted(set(ck) - set(bk))
    comp_b, comp_c = blend_composition(bc), blend_composition(cc)
    print(f"    BLEND composition base: {dict(sorted(comp_b.items(), key=lambda kv: str(kv[0])))}")
    print(f"    BLEND composition cand: {dict(sorted(comp_c.items(), key=lambda kv: str(kv[0])))}")
    if only_b or only_c:
        print(f"    only in base ({len(only_b)}): {only_b[:8]}")
        print(f"    only in cand ({len(only_c)}): {only_c[:8]}")
        sys.exit("REFUSE: membership differs — no aggregate below is attributable "
                 "(aggregate-moved-check-membership-first).")
    if comp_b != comp_c:
        sys.exit("REFUSE: BLEND composition differs at identical membership.")
    print("    => identical membership AND identical BLEND composition.")

    # ---- 2. PER-CAPTURE SCOPE ------------------------------------------------
    print("\n[2] SCOPE — per capture, bit-identity of every finite numeric leaf")
    bmap = {key_of(c): c for c in bc}
    cmap = {key_of(c): c for c in cc}
    identical, moved = [], []
    worst = (0.0, None, None)
    for k in bk:
        lb, lc = numeric_leaves(bmap[k]), numeric_leaves(cmap[k])
        if set(lb) != set(lc):
            sys.exit(f"REFUSE: capture {k} has a different leaf SET between reports.")
        d = 0.0
        for path, v in lb.items():
            dv = abs(lc[path] - v)
            if dv > d:
                d, dpath = dv, path
        if d == 0.0:
            identical.append(k)
        else:
            moved.append(k)
            if d > worst[0]:
                worst = (d, k, dpath)
    print(f"    bit-identical: {len(identical)} / {len(bk)}")
    print(f"    moved        : {len(moved)} / {len(bk)}")
    if worst[1]:
        print(f"    worst single leaf: {worst[0]:.6g} at {worst[1]} {worst[2]}")

    def classify(k):
        s = str(k)
        if "base-clean" in s or "ref-clean" in s:
            return "CLEAN"
        return "OD/other"

    for cls in ("CLEAN", "OD/other"):
        ident = sum(1 for k in identical if classify(k) == cls)
        mv = sum(1 for k in moved if classify(k) == cls)
        print(f"    {cls:9s}: {ident} identical, {mv} moved")
    if moved:
        print(f"    sample moved: {sorted(moved)[:6]}")

    # ---- 3. THE GRADED ROWS --------------------------------------------------
    print("\n[3] GRADED ROWS — from release_gate.py itself, not transcribed")
    for label, path in (("BASE", base_path), ("CAND", cand_path)):
        r = subprocess.run([PY, "analysis/release_gate.py", path],
                           capture_output=True, text=True)
        print(f"\n--- {label} ({path})  rc={r.returncode} ---")
        print(r.stdout.rstrip())
        if r.stderr.strip():
            print(r.stderr.rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
