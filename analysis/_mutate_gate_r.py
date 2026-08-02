#!/usr/bin/env python3.11
"""Mutation-test GATE R's guards.  Throwaway; delete after use.

⚠ Run from `analysis/` -- s107: patched copies written to /tmp returned 5-of-5 "PASS", every one a
ModuleNotFoundError that never reached a guard, because the tool puts its OWN directory on
sys.path.  A mutation test scores "did it exit non-zero?", and a crash exits non-zero.

⚠ Every mutation is applied to the DATA the guard reads, never to an arm's --fit list: re-rendering
an arm under a mutated condition would overwrite the real artefact and corrupt the next honest run.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "null_locus_gate.py")

# (name, anchor_line_substring, replacement_block)  -- inserted AFTER the anchor line
MUTS = {
    "CONTROL (unmutated)": (None, None),
    "R1 bt notch must move": (
        '    for tag, fits in ARMS.items():',
        None),  # handled specially below
    "R1 bt must not move under ladder": (None, None),
    "R3 endpoint count": (None, None),
    "R3 defect token matches nothing": (None, None),
    "R4 notch leaves the window": (None, None),
    "R5 clipsym vacuity": (None, None),
    "R6 non-finite wash-out": (None, None),
}

PATCHES = {
    "CONTROL (unmutated)": [],
    # the bridged-T arm becomes a copy of base -> its notch cannot move -> R1's known answer fails
    "R1 bt notch must move": [
        ('    bt_base = notch(', '    arm["bt_half"] = arm["base"]\n')],
    # the ladder arm becomes a copy of the bt arm -> the bt notch DOES move under "ladder" -> fails
    "R1 bt must not move under ladder": [
        ('    bt_base = notch(', '    arm["lad_x2"] = arm["bt_half"]\n')],
    "R3 endpoint count": [
        ('    n_defect = sum(', '    eps = eps[:-1]\n')],
    "R3 defect token matches nothing": [
        ('    n_defect = sum(', '    Q.DEFECT_TOKEN = "zzz-no-such-token"\n')],
    # Push the notch window somewhere the null is not -> every minimum rests on an edge.
    # ⚠ This MUST be patched at MODULE level, not inside main(): the endpoint surface is computed
    # in a ProcessPoolExecutor, whose children re-import the module fresh and never see a global
    # mutated at runtime.  The first version assigned it in main() and the mutation was a silent
    # no-op -- the gate returned a clean OK and the test read "BROKEN guard" when the guard was
    # fine and the MUTATION was vacuous.
    "R4 notch leaves the window": [
        ('# The rank swap that defect exposed', 'NOTCH_WIN = (455.0, 470.0)\n')],
    "R5 clipsym vacuity": [
        ('    d_jfet = r5["base"]', '    r5["clipsym"] = dict(r5["base"])\n')],
    "R6 non-finite wash-out": [
        ('    mw = [r6[str(dv)]', '    r6[str(drives[0])]["model"]["washout"] = float("nan")\n')],
}


def build(name):
    src = open(SRC).read().splitlines(keepends=True)
    for anchor, ins in PATCHES[name]:
        for i, line in enumerate(src):
            if line.startswith(anchor):
                indent = " " * (len(line) - len(line.lstrip()))
                src.insert(i, indent + ins.strip() + "\n")
                break
        else:
            sys.exit(f"mutation {name!r}: anchor {anchor!r} not found -- the mutation would be a "
                     f"no-op and the test would be vacuous")
    p = os.path.join(HERE, "_mut_run.py")
    open(p, "w").write("".join(src))
    return p


def main():
    only = sys.argv[1:] or list(PATCHES)
    for name in only:
        p = build(name)
        # ⚠ The patched copy must LIVE in analysis/ (so its `sys.path.insert` finds its siblings)
        # but must RUN from the repo root (so repo-relative data paths like
        # analysis/test_signal_48k.wav resolve).  Getting only the first half right is how the
        # first version of this test returned 7-of-7 "PASS" on FileNotFoundError -- s107's trap in
        # a new costume, caught only because the unmutated CONTROL also "passed".
        r = subprocess.run([sys.executable, "-u", p, "--json",
                            "/tmp/_mut_gate_r.json", "-j", "8"],
                           capture_output=True, text=True,
                           cwd=os.path.dirname(HERE))
        tail = [l for l in r.stdout.strip().splitlines() if l.strip()][-1:]
        want_fail = name != "CONTROL (unmutated)"
        got_fail = r.returncode != 0
        ok = got_fail == want_fail
        print(f"{'PASS' if ok else 'BROKEN'}  rc={r.returncode:<3} {name:36s} | "
              f"{(tail[0] if tail else '(no output)')[:80]}")
        if not ok:
            print("      stderr:", r.stderr.strip()[-300:])
        os.remove(p)


if __name__ == "__main__":
    main()
