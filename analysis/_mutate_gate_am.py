#!/usr/bin/env python3.11
"""Mutation test for GATE AM (analysis/resonance_census.py).

Every arm carries an expected EXIT CODE **and** a string the output must contain (s128), plus an
optional string it must NOT contain -- because two of this gate's verdicts are distinguished by
which of two labels it prints, and a positive-only match cannot see a label that failed to change.

  * `expect_rc != 0` arms test the REFUSALS (GATE AM refuses with rc = 2 via its `_die`).
  * `expect_rc == 0` arms test the COMPUTED VERDICTS.  This gate's headline is a NEGATIVE result
    ("no resonance at or upstream of the clipper"), which is exactly the shape that can be true of
    the sentence rather than of the circuit -- so three arms drive AM5 to its other outcomes and
    one drives AM1c's overdamped/complex label.

Mechanics, each paid for by an earlier session:
  * the patched copy LIVES in analysis/ (sibling imports) and RUNS from the repo root (data
    paths) -- two different requirements (s110).
  * the mutant path is PID-unique (s139).
  * an unmutated CONTROL runs first; if it does not pass, nothing below is attributable (s107).
  * failures are scored on the guard's own tag, not on a non-zero exit alone (s117).
  * ⚠ this gate does NO rendering and reads no capture, so no arm can trigger a re-render and
    none rebuilds anything.

Run:  python3.11 analysis/_mutate_gate_am.py
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(HERE, "resonance_census.py")
TMP = os.path.join(HERE, f"_mutated_gate_am_{os.getpid()}.py")
SCRATCH = tempfile.mkdtemp(prefix="am_mut_")

# A patch is (name, why, [(pattern, replacement)], expect_rc, must_contain, must_absent, argv).
ARMS = [
    # ---------------- REFUSAL ARMS (rc = 2) -------------------------------
    ("AM1a  a mis-stamped netlist must not reach the census",
     "move R7 by 1 % in the treble netlist only.  The whole licence for writing netlists in this "
     "file rather than refactoring eq_reference is that AM1a compares the two -- if a 1 % value "
     "error can pass, the topology is being trusted rather than checked, and every pole "
     "frequency below it is decoration.",
     [(r'e \+= \[\("R", "G", "M", v\["R7"\]\),',
       'e += [("R", "G", "M", v["R7"] * 1.01),')],
     2, "AM1a", None, []),

    ("AM1a  the census must run on the SHIPPED values, not the drawn ones",
     "make `shipped_treble` return the drawn values.\n"
     "    ⚠ This arm is aimed at the DIVERGENCE guard, not at the transfer comparison, and the "
     "distinction is the point: AM1a evaluates my netlist and the oracle AT THE SAME VALUES, so "
     "the two move together and a swapped value set agrees PERFECTLY.  The transfer check "
     "validates TOPOLOGY and structurally cannot see this -- which is why the divergence guard "
     "exists and why this arm was GUARD DEAD until it was added.",
     [(r'^    return dict\(R7=_fp\("trebleR7"\), R8=rtop, R11=rbot,',
       '    return drawn_treble()\n'
       '    return dict(R7=_fp("trebleR7"), R8=rtop, R11=rbot,')],
     2, "censusing the DRAWN network", None, []),

    ("AM1b  the classifier must recover a KNOWN complex pair",
     "discard the imaginary part inside `Net.poles`.  Every 'all real' row in AM2 and the whole "
     "of AM5's negative headline would then be produced by the instrument rather than measured, "
     "and nothing else in the gate would notice -- AM1a's transfer check is untouched by it.",
     [(r'^        return np\.asarray\(\[p for p in w if np\.isfinite\(p\)\], dtype=complex\)$',
       '        return np.asarray([complex(p.real, 0.0) for p in w if np.isfinite(p)], '
       'dtype=complex)')],
     2, "AM1b", None, []),

    ("AM1c  the pencil must agree with AL5's own closed form",
     "perturb AL5's `sk_params` Q by 1 % at the point of comparison.\n"
     "    ⚠ The obvious arm — swapping the Sallen-Key's C1/C2, which moves Q but not f0 — is "
     "caught by AM1a first, because a Q change IS a transfer change.  That is s119's case (the "
     "gate being better than the test's model of it), so the arm was re-pointed rather than the "
     "guard weakened: AM1c is reachable only by corrupting the COMPARISON, since any network "
     "mutation that moves Q also moves the transfer.",
     [(r'^        f0r, qr = AL\.sk_params\(kw\["R1"\], kw\["R2"\], kw\["C1"\], kw\["C2"\]\)$',
       '        f0r, qr = AL.sk_params(kw["R1"], kw["R2"], kw["C1"], kw["C2"])\n'
       '        qr *= 1.01')],
     2, "AM1c", None, []),

    ("AM3  a stage claimed passive must actually BE passive",
     "let `is_passive_rc` accept a controlled source, so the Sallen-Keys are censused as passive "
     "RC.  AM3's whole content is that the RC theorem is asserted on the SHIPPED stamps rather "
     "than cited at them; if the predicate that decides which stages the theorem covers is "
     "wrong, the assertion covers nothing.",
     [(r'^        return all\(e\[0\] in \("R", "C", "V", "I"\) for e in self\.elements\)$',
       '        return all(e[0] in ("R", "C", "V", "I", "OP", "VCVS") for e in self.elements)')],
     2, "AM3", None, []),

    ("AM3  the mutation control must stay able to fire",
     "clamp the bootstrap gain sweep to 0.  A negative result needs a control that CAN produce "
     "the positive, and this is the arm that stops 'every passive stage is real' from being a "
     "statement about the classifier.",
     [(r'^    for g in \(0\.0, 0\.5, 0\.9, 1\.0, 1\.5\):$', '    for g in (0.0, 0.0, 0.0):')],
     2, "vacuous", None, []),

    ("AM4  the discriminant algebra must be transcribed correctly",
     "drop the R18*C14 term from b, which breaks the AM-GM bound.  AM4 is the only claim in the "
     "gate that holds for ALL parameter values rather than the shipped ones, so the random sweep "
     "is not decoration -- it is the mutation-proof of a hand-done algebra step.",
     [(r'^        b = \(1 \+ a0\) \* \(r16 \* cg \+ r18 \* c14\) \+ cg \* r18$',
       '        b = (1 + a0) * (r16 * cg) + cg * r18')],
     2, "AM4", None, []),

    ("AM5  the target must be IMPORTED from AL's report, never transcribed",
     "DATA-level: point --al at a path that does not exist.  A gate that fell back on a "
     "hardcoded 2.685 would be checking a handover against itself.",
     [], 2, "must be IMPORTED", None, ["--al", os.path.join(SCRATCH, "nope.json")]),

    ("AM6  the inductor scan must be able to find something",
     "stop excluding L1/L2/L3, which are the treble ladder's NODE names in circuit.md's own node "
     "graph.  The gate must then refuse rather than quietly proceed -- 'no inductors, therefore "
     "controlled sources are the only route to a resonance' is load-bearing for AM5's headline, "
     "so its scan has to be falsifiable.",
     [(r'^    ls = \[x for x in ls if x not in \("L1", "L2", "L3"\)\]',
       '    ls = list(ls)  #')],
     2, "AM6", None, []),

    # ---------------- COMPUTED-VERDICT ARMS (rc = 0) -----------------------
    ("VERDICT  AM5 must be able to find a resonance BEFORE the clipper",
     "relabel Sallen-Key IC4_A as a `pre` stage.  AM5's headline is decided by POSITION, and if "
     "'0 resonances at or upstream of the clipper' cannot become a non-zero count then it is a "
     "property of the sentence.  ⚠ This mutates only the LABEL, which is the point: the physics "
     "is unchanged and the verdict must still flip.",
     [(r'^        \("Sallen-Key IC4_A", "post", net_sk\(\*\*AB\.SK_A\)\[0\], None\),$',
       '        ("Sallen-Key IC4_A", "pre", net_sk(**AB.SK_A)[0], None),')],
     0, "resonance(s) exist at or before the clipper", "NO resonance exists anywhere", []),

    ("VERDICT  AM5 must be able to report a resonance that REACHES the target",
     "retune the 3.3 kHz Sallen-Key's caps by a common factor 1.335 -- f0 moves 3337 -> 2500 Hz "
     "and Q is UNCHANGED (scaling both caps scales Q's numerator and denominator alike), putting "
     "the vertex at w ~ 1.17, inside the band AL5 itself derives.  Without this arm the "
     "per-Q admissibility columns are unfalsifiable decoration.  (Same construction as GATE AL's "
     "own AL5 arm, deliberately, so the two gates are shown to agree on a POSITIVE case as well "
     "as on the negative one.)\n"
     "    ⚠ SK_A lives in the IMPORTED bt_pair_shape_gate, so the mutation is a module-level "
     "monkey-patch injected into the MUTANT after its imports (s139's form) -- it lives and dies "
     "with the subprocess, so there is nothing to restore and no leak into a concurrent run.",
     [(r'^_fp = AB\._read_fitparam',
       'AB.SK_A = dict(R1=22.0e3, R2=47.0e3, C1=2.937e-9, C2=1.335e-9)\n'
       '_fp = AB._read_fitparam')],
     0, "DO reach at their own Q", "NO resonance in the chain reaches", []),

    ("VERDICT  AM1c's OVERDAMPED label must be measured, not printed",
     "raise IC4_B's C1 to 4n7, which lifts its Q from 0.4635 to above 0.5 and makes it a genuine "
     "complex pair.  'Q < 0.5 is overdamped' is the sharpening this gate adds to AL5's IC4_B row, "
     "and a label that cannot change is narration.",
     [(r'^_fp = AB\._read_fitparam',
       'AB.SK_B = dict(R1=10.0e3, R2=22.0e3, C1=4.7e-9, C2=1.0e-9)\n'
       '_fp = AB._read_fitparam')],
     0, "IC4_B", "OVERDAMPED", []),
]


def run(path, extra):
    p = subprocess.run([sys.executable, path, "--json", os.path.join(SCRATCH, "out.json")] + extra,
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    src = open(SRC).read()

    open(TMP, "w").write(src)
    rc, out = run(TMP, [])
    tail = [l for l in out.strip().splitlines() if l.strip()][-1:]
    print(f"CONTROL   rc={rc}, gate passes from {os.path.relpath(TMP, REPO)}  "
          f"{'✓' if rc == 0 else '✗ ' + str(tail)}")
    if rc != 0:
        print("\n⛔ the UNMUTATED control does not pass — no failure below is attributable to any "
              "mutation (s107).  Fix this first.")
        return 1

    bad = 0
    for name, why, patches, exp_rc, must, absent, extra in ARMS:
        mutated = src
        for pat, rep in patches:
            new, n = re.subn(pat, rep, mutated, count=1, flags=re.M)
            if n != 1:
                print(f"✗ {name}\n    PATCH DID NOT APPLY ({n} matches) — the arm is testing "
                      f"nothing.  Pattern: {pat[:70]}")
                bad += 1
                mutated = None
                break
            mutated = new
        if mutated is None:
            continue
        open(TMP, "w").write(mutated)
        rc, out = run(TMP, extra)
        hit = must in out
        gone = (absent is None) or (absent not in out)
        ok = (rc == exp_rc) and hit and gone
        if ok:
            if exp_rc == 0:
                print(f"✓ {name}\n    VERDICT CHANGED as required (rc=0, saw '{must}'"
                      f"{', and no longer ' + repr(absent) if absent else ''})")
            else:
                print(f"✓ {name}\n    REFUSED as required (rc={rc}, saw '{must}')")
        else:
            bad += 1
            if exp_rc != 0 and rc == 0:
                kind = "GUARD DEAD — the mutant ran clean"
            elif exp_rc == 0 and rc != 0:
                kind = f"CRASHED (rc={rc}) — the arm was meant to change a verdict, not refuse"
            elif exp_rc == 0 and not hit:
                kind = "NARRATED — the gate passed but never printed the opposite verdict"
            elif not gone:
                kind = f"STALE LABEL — the gate printed the NEW verdict and kept {absent!r} too"
            elif rc != exp_rc:
                kind = f"WRONG EXIT (rc={rc}, wanted {exp_rc})"
            else:
                kind = f"WRONG GUARD — refused without '{must}'"
            print(f"✗ {name}\n    {kind}")
            for l in [l for l in out.strip().splitlines() if l.strip()][-3:]:
                print(f"      | {l[:110]}")

    if os.path.exists(TMP):
        os.remove(TMP)
    n = len(ARMS)
    print(f"\n{n - bad}/{n} arms behaved as required.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
