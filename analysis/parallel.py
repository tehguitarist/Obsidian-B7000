"""Shared parallel-map helper for the analysis harnesses.

Almost every heavy tool in `analysis/` has the same shape: a loop over INDEPENDENT items
(drive settings, candidate values, captures, knob positions, bands) where each item is one
`OfflineRender` subprocess plus a bit of numpy on the result. That is embarrassingly parallel
and the serial form is pure wall-clock waste -- session 28 took `comprehensive_report.py` from
~30 min to 5m42s this way, bit-identical.

This module exists so a new tool gets that for free, in ONE consistent shape, per the
`.claude/rules/build.md` rule "Authoring or editing a test/harness: build in parallelism,
don't retrofit it".

    from parallel import pmap, add_jobs_arg, DEFAULT_JOBS

    ap.add_argument(...); add_jobs_arg(ap)          # gives --jobs/-j with the house default
    results = pmap(render_one, drives, jobs=args.jobs)   # in-order list, same as [f(x) for x]

WHY THREADS, NOT PROCESSES. The per-item work is `subprocess.run(OfflineRender ...)` -- the
calling thread is blocked on a child PROCESS, so the GIL is released for essentially the whole
item and threads scale just as well as processes here. Threads also avoid the two things that
make a process pool intrusive: the callable and its arguments must be picklable (so closures
and locally-defined cost objects break -- see `attack_notch_screen.py`'s note about keeping a
Cost class at module level for exactly this reason), and module-level state has to be re-seeded
in every worker via an `initializer`. `comprehensive_report.py` legitimately uses PROCESSES
because each worker also holds a ~600 MB reference capture and does heavy numpy; for a
render-bound sweep, threads are the cheaper correct answer.

** BIT-IDENTITY. ** `pmap` returns results in ITEM ORDER, never completion order, so a caller
that builds a dict/array from the result is unchanged. That is the whole safety argument: the
renders were already independent (each writes its own output file), and the only thing serial
order was buying was the ordering of the result list, which is preserved. The two ways this
goes wrong are (a) two items writing the SAME scratch file and (b) items mutating shared state
-- see `race_check()` below, and use it rather than assuming.

** NESTING. ** `jfet_even_screen.py` and `joint_even_fit.py` already run their CANDIDATES in a
process pool, and each candidate calls `harmonic_ladder.measure_all`, which now parallelises its
own renders. Nested pools multiply: 8 candidates x 7 drives = 56 concurrent renders on a 10-core
machine, which is slower than either level alone and can exhaust file descriptors. So `pmap`
DETECTS that it is already running inside a worker (process or thread) and runs serially there,
with no cooperation needed from the outer tool. An outer pool therefore always wins, which is
the right call -- it has more items and so parallelises better.
"""
import concurrent.futures as cf
import multiprocessing
import os
import threading

# Same default as comprehensive_report.py: leave a couple of cores for the machine, and don't
# run away on a big box (the renders are I/O + memory heavy, not purely CPU bound).
DEFAULT_JOBS = max(1, min(8, (os.cpu_count() or 2) - 2))


def in_worker():
    """True when this process/thread is ALREADY a pool worker, so pmap should stay serial.

    Detected rather than declared, so an existing parallel caller needs no changes:
      * `multiprocessing.current_process().name` is 'MainProcess' only in the parent -- a
        ProcessPoolExecutor / multiprocessing.Pool worker is 'SpawnProcess-N' / 'ForkProcess-N'.
      * a ThreadPoolExecutor worker is not `threading.main_thread()`.
    """
    if multiprocessing.current_process().name != "MainProcess":
        return True
    return threading.current_thread() is not threading.main_thread()


def resolve_jobs(jobs=None):
    """Turn a caller's --jobs (or None) into an effective worker count.

    Precedence: explicit argument > PEDAL_JOBS env var > DEFAULT_JOBS, then forced to 1 if we
    are inside someone else's pool. PEDAL_JOBS exists so a whole multi-tool shell sweep can be
    pinned to one degree of parallelism without editing every script's flags.
    """
    if in_worker():
        return 1
    if jobs is None:
        env = os.environ.get("PEDAL_JOBS")
        jobs = int(env) if env else DEFAULT_JOBS
    return max(1, int(jobs))


def pmap(fn, items, jobs=None, ordered=True):
    """`[fn(x) for x in items]`, evaluated concurrently, results IN ITEM ORDER.

    Exceptions propagate to the caller exactly as the serial form would -- which matters here
    because several tools deliberately catch `subprocess.CalledProcessError` from a render to
    score an infeasible parameter point as a large cost rather than crashing the fit
    (`fit_nonlinear.cost`). The first failure is re-raised; remaining work is cancelled.

    `jobs=1` (or being inside another pool) runs the plain serial loop in THIS thread -- not a
    1-worker pool -- so a debugging run has no concurrency in the stack at all.
    """
    items = list(items)
    n = resolve_jobs(jobs)
    if n <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    with cf.ThreadPoolExecutor(max_workers=min(n, len(items))) as pool:
        # executor.map yields in submission order and re-raises on iteration.
        return list(pool.map(fn, items))


def pmap_cpu(fn, items, jobs=None, ordered=True, initializer=None, initargs=()):
    """`pmap` for CPU-BOUND work: same contract, but PROCESSES instead of threads.

    ** Pick this one when the per-item work is numpy, not a subprocess. ** The distinction is not
    stylistic, it is the difference between a speedup and a slowdown, and it was measured on this
    repo's own `a3_phase_solve.fit_band` workload (160 beta candidates x 23 bands, each a
    181 x 1201 grid):

            serial   8.05 s
            threads 13.12 s   (0.61x -- SLOWER)
            procs    1.80 s   (4.47x)          ... identical results either way

    `fit_band` runs 181 small numpy ops per call, and numpy only releases the GIL around big
    contiguous ufunc loops -- on arrays this small the interpreter holds it nearly the whole time,
    so threads just add contention. A render sweep is the opposite: the thread is parked in
    `subprocess.run` waiting on a child PROCESS, holding no GIL at all, and threads win because
    they skip pickling entirely.

    ** COST: `fn` and every item must be PICKLABLE, and `fn` must be importable by name. ** So it
    has to be a module-level function (not a closure or a lambda), and its arguments plain data.
    Under `spawn` (the macOS default) each worker re-imports the parent module, so a script using
    this needs its top-level work behind `if __name__ == "__main__":` or it runs once per worker.
    That is exactly why several tools here keep their cost objects at module level -- see the note
    in `attack_notch_screen.py`.

    ** CHUNKSIZE IS NOT OPTIONAL HERE. ** `ProcessPoolExecutor.map` defaults to chunksize=1, i.e.
    one pickle round-trip per item -- fine for 7 renders, pathological for the hundreds of small
    items this path is for. Measured on `a3_phase_solve --selftest` (160 candidates, a SMALL
    synthetic workload where each item is milliseconds): chunksize=1 turned a 6 s serial run into
    34 s. Batching the items so each worker gets a handful amortises both the IPC and the one-off
    spawn cost, and changes nothing about the results or their order.

    ** KEEP THE PER-ITEM PAYLOAD SMALL -- use `initializer` for anything shared. ** Every item is
    pickled and shipped separately, so folding a constant payload into each one multiplies it by
    the item count. Measured on `a3_phase_solve.fit_beta` (160 candidates sharing one band table):
    payload-in-every-item gave 1.46x, the same run with the table sent once per worker via
    `initializer` gave 6.5x. `chunksize` cannot rescue that -- it batches the round-trips, not
    the bytes.
    """
    items = list(items)
    n = resolve_jobs(jobs)
    if n <= 1 or len(items) <= 1:
        if initializer is not None:
            initializer(*initargs)
        return [fn(x) for x in items]
    workers = min(n, len(items))
    # A few chunks per worker: enough to keep them evenly fed when item costs vary, few enough
    # that per-task IPC is negligible. chunksize=1 is the default and is pathological for the
    # hundreds-of-small-items case this path exists for.
    chunk = max(1, len(items) // (workers * 8))
    with cf.ProcessPoolExecutor(max_workers=workers, initializer=initializer,
                                initargs=initargs) as pool:
        return list(pool.map(fn, items, chunksize=chunk))


def add_jobs_arg(ap, help_extra=""):
    """Register the house-standard --jobs/-j flag on an argparse parser."""
    ap.add_argument("--jobs", "-j", type=int, default=None,
                    help=f"parallel workers for the render sweep (default {DEFAULT_JOBS}; "
                         f"--jobs 1 = serial, identical results, easier to debug). {help_extra}")
    return ap


def race_check(paths):
    """Assert a set of per-item scratch paths are DISTINCT before handing them to a pool.

    The single way this project's naive parallelisation has actually broken (session 73): a new
    `tag` parameter on `harmonic_ladder.measure_all` was silently rebound by that function's own
    loop, so every render after the first went to ONE shared `render#b_*.wav` and 8 workers tore
    it. ** It was invisible serially ** -- the array is read straight back from the writer, so
    the filenames were wrong and every number was right, which is why it survived a bit-identical
    single-process A/B. Call this where the paths are built, so the collision is a loud failure
    at the start of the sweep instead of a torn WAV somewhere in the middle.
    """
    paths = list(paths)
    if len(set(paths)) != len(paths):
        dupes = sorted({p for p in paths if paths.count(p) > 1})
        raise AssertionError(
            "parallel render targets COLLIDE -- these paths are written by more than one item, "
            f"so workers would tear each other's output: {dupes}")
    return paths
