#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lock_plan.py: freeze ANALYSIS-PLAN.md with a SHA-256 so the prespecification is provably
older than the first count.

Runs LOCALLY, always. Nothing in this file runs inside the All of Us perimeter, nothing in it
touches participant data, and it makes no network call. It reads one Markdown file and writes
one text file beside it.

Why this exists
---------------
The whole claim of `ANALYSIS-PLAN.md` is that the choice of arm, estimand, model ladder and
exhibit set was fixed before any number from the study existed. A date typed into a document is
not evidence of that; a content hash recorded in `SESSION-LOG.md` before Phase 2 runs is. The
Methods cite the plan by hash and date, so a reader can be handed the file and check it.

    python3 lock_plan.py              lock: hash the plan, write PLAN-HASH.txt, print the
                                      SESSION-LOG line for the orchestrator to paste
    python3 lock_plan.py --check      verify: recompute and compare against PLAN-HASH.txt,
                                      non-zero exit if the plan has moved since the lock
    python3 lock_plan.py --self-test  the house self-test, in a temporary directory

Exit codes, so a caller can branch on the reason rather than on stderr text:

    0   locked, or the check passed
    1   the plan's hash no longer matches the recorded one (a silent post-lock edit)
    2   a required file is missing (no plan, or no recorded hash to check against)
    3   the plan or the record is unreadable: a house prose rule fired, the plan is not valid
        UTF-8, or PLAN-HASH.txt is missing a line or carries an unreadable value
   64   the command line was not understood (the BSD sysexits convention for a usage error,
        chosen so that a typo cannot be mistaken for a missing file)

Two deliberate non-features. This is NOT installed as a `git` hook: a hook that rewrites or
blocks a commit is a surprise, and the lock is a research act that belongs in the session log
with a human's knowledge, not in a hook that fires silently. And it never touches
`SESSION-LOG.md` itself; it prints the line and the orchestrator pastes it, so the log keeps a
single writer.

The two modes run the prose guard at opposite ends, and the asymmetry is deliberate.

In `lock()` the guard runs FIRST, because a plan that violates the house rules would have to be
edited after the lock to fix them, which is exactly the event the hash exists to make impossible.
Nothing is written when it fires.

In `check()` the hash comparison runs first and the guard runs only after the bytes have been
confirmed identical to the locked ones. The reason is that a tamper is far more likely to introduce
a prose violation than a clean edit is: if the guard ran first, appending one sentence with an
em-dash would exit 3, "a house prose rule fired", and never say that the hash had moved. A caller
branching on exit 1, which this docstring invites, would not fire, and stop condition 1 of the
plan's section 11 is precisely "the plan hash does not match". The tamper signal outranks the
typography signal, so it is tested first.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

PLAN_NAME = "ANALYSIS-PLAN.md"
HASH_NAME = "PLAN-HASH.txt"

# Written as `chr(...)` rather than as the literal character, so this file honours "no em-dash
# anywhere" literally rather than by exemption, and so a grep for U+2014 across the repo returns
# nothing at all. `disclosure.py` uses the same form; one convention, not two.
EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_MISSING = 2
EXIT_PROSE = 3
EXIT_USAGE = 64  # BSD sysexits EX_USAGE: a bad command line is not a missing file


class LockError(RuntimeError):
    """A stop condition. Never a warning: nothing continues past one of these."""


# ===========================================================================
# A. PRIMITIVES.
# ===========================================================================
def plan_dir() -> Path:
    """The directory this script lives in, so the tool works from any working directory."""
    return Path(__file__).resolve().parent


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_stamp(now: datetime | None = None) -> str:
    """ISO-8601 UTC to the second, with a trailing Z rather than +00:00.

    Seconds resolution on purpose: the stamp is a provenance record a human reads and retypes,
    not a benchmark.
    """
    moment = now if now is not None else datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_plan(path: Path) -> Tuple[bytes, str]:
    """Return the plan's exact bytes and its decoded text.

    The hash is taken over bytes, never over decoded-then-re-encoded text, so an encoding
    round trip cannot silently change what was locked.
    """
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_bytes()
    if not raw.strip():
        raise LockError(f"{path.name} is empty, so there is nothing to lock")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LockError(f"{path.name} is not valid UTF-8: {exc}") from None
    return raw, text


# ===========================================================================
# B. THE HOUSE PROSE GUARD.
# ===========================================================================
def assert_house_prose(text: str, where: str) -> int:
    """Refuse to lock a plan that breaks the two typographic rules, and report what was checked.

    Rule 1: no em-dash anywhere. Rule 2: the en-dash survives only as a range separator, which
    means a digit on each side of it. Both are asserted on the rendered string rather than
    grepped afterwards, which is the house pattern: a grep tells you about a file you already
    shipped.

    Returns the number of en-dashes inspected, so the caller can print evidence that the rule
    was exercised rather than merely not triggered.
    """
    if EM_DASH in text:
        line = text[: text.index(EM_DASH)].count("\n") + 1
        raise LockError(f"{where}: em-dash (U+2014) at line {line}. The house rule is none, anywhere")

    offenders: List[int] = []
    checked = 0
    for i, ch in enumerate(text):
        if ch != EN_DASH:
            continue
        checked += 1
        before = text[i - 1] if i else ""
        after = text[i + 1] if i + 1 < len(text) else ""
        if not (before.isdigit() and after.isdigit()):
            offenders.append(text[:i].count("\n") + 1)
    if offenders:
        raise LockError(
            f"{where}: en-dash (U+2013) used as something other than a range separator at "
            f"line(s) {', '.join(str(n) for n in offenders[:5])}"
        )
    return checked


# ===========================================================================
# C. THE RECORD FILE.
# ===========================================================================
def render_hash_file(digest: str, n_bytes: int, stamp: str, plan_name: str = PLAN_NAME) -> str:
    """Key-and-value lines, because --check has to parse this back without a dependency."""
    return (
        f"file: {plan_name}\n"
        f"sha256: {digest}\n"
        f"bytes: {n_bytes}\n"
        f"locked: {stamp}\n"
        f"tool: lock_plan.py\n"
    )


def parse_hash_file(text: str) -> Dict[str, str]:
    record: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        record[key.strip()] = value.strip()
    for required in ("file", "sha256", "bytes", "locked"):
        if required not in record:
            raise LockError(f"{HASH_NAME} is missing its '{required}' line and cannot be trusted")
    # Validate here rather than at the point of use.  An unvalidated `int(record["bytes"])` in
    # check() raised a bare ValueError traceback on a corrupt record, which is not an exit code and
    # so is not something a caller can branch on.  A record that cannot be parsed is a stop
    # condition like any other.
    digest = record["sha256"]
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        raise LockError(f"{HASH_NAME} carries a 'sha256' line that is not 64 hexadecimal "
                        f"characters, so there is nothing trustworthy to compare against")
    try:
        if int(record["bytes"]) < 0:
            raise ValueError
    except ValueError:
        raise LockError(f"{HASH_NAME} carries a 'bytes' line that is not a non-negative "
                        f"integer: {record['bytes']!r}") from None
    return record


def render_session_log_line(digest: str, n_bytes: int, stamp: str) -> str:
    """One line, already in the log's voice, so the orchestrator pastes rather than composes."""
    return (
        f"- **Prespecification locked.** `prespecification/{PLAN_NAME}`, {n_bytes:,} bytes, "
        f"SHA-256 `{digest}`, locked {stamp}. "
        f"Verify with `python3 prespecification/lock_plan.py --check`."
    )


# ===========================================================================
# D. THE TWO MODES.
# ===========================================================================
def lock(directory: Path | None = None) -> int:
    """Hash the plan, write the record, print the line to paste. Returns an exit code."""
    here = directory if directory is not None else plan_dir()
    plan_path = here / PLAN_NAME
    hash_path = here / HASH_NAME

    try:
        raw, text = read_plan(plan_path)
    except FileNotFoundError:
        print(f"FAIL: no {PLAN_NAME} at {plan_path}", file=sys.stderr)
        return EXIT_MISSING
    except LockError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return EXIT_PROSE

    try:
        en_checked = assert_house_prose(text, PLAN_NAME)
    except LockError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        print("Nothing was written. Fix the plan, then lock it.", file=sys.stderr)
        return EXIT_PROSE

    digest = sha256_of(raw)
    n_bytes = len(raw)
    stamp = utc_stamp()

    previous = None
    if hash_path.is_file():
        try:
            previous = parse_hash_file(hash_path.read_text(encoding="utf-8"))
        except LockError:
            previous = None

    hash_path.write_text(render_hash_file(digest, n_bytes, stamp), encoding="utf-8")

    print("=" * 78)
    print(f"PLAN LOCKED: {PLAN_NAME}")
    print("=" * 78)
    print(f"  SHA-256                    : {digest}")
    print(f"  bytes                      : {n_bytes:,}")
    print(f"  lines                      : {text.count(chr(10)) + 1:,}")
    print(f"  locked at                  : {stamp}")
    print(f"  record written to          : {hash_path.name}")
    print(f"  house prose guard          : no em-dash; {en_checked} en-dash(es), all between digits")
    if previous is not None:
        if previous.get("sha256") == digest:
            print(f"  previous record           : identical hash, re-stamped from {previous.get('locked')}")
        else:
            print(f"  previous record           : DIFFERENT hash {previous.get('sha256', '')[:16]}... "
                  f"from {previous.get('locked')}")
            print("  ATTENTION                  : the plan changed since the last lock. This is an")
            print("                               amendment. Record it in section 13 of the plan and")
            print("                               keep BOTH hashes in SESSION-LOG.md.")
    print()
    print("PASTE INTO SESSION-LOG.md:")
    print(render_session_log_line(digest, n_bytes, stamp))
    return EXIT_OK


def check(directory: Path | None = None) -> int:
    """Recompute and compare. Non-zero exit means the plan moved after the lock.

    The order of the two guards is load-bearing: see the module docstring. The hash is compared
    before the plan is decoded or prose-checked, so a tamper that also breaks a typographic rule
    still reports itself as a tamper.
    """
    here = directory if directory is not None else plan_dir()
    plan_path = here / PLAN_NAME
    hash_path = here / HASH_NAME

    if not hash_path.is_file():
        print(f"FAIL: no {HASH_NAME} at {hash_path}. The plan has never been locked, so there is "
              f"nothing to check it against.", file=sys.stderr)
        return EXIT_MISSING

    if not plan_path.is_file():
        print(f"FAIL: {HASH_NAME} exists but {PLAN_NAME} does not. The locked plan is gone.",
              file=sys.stderr)
        return EXIT_MISSING

    try:
        record = parse_hash_file(hash_path.read_text(encoding="utf-8"))
    except LockError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return EXIT_PROSE

    # Bytes, not text.  An emptied or re-encoded plan is a tamper, and the hash is what says so;
    # decoding it first would turn that tamper into a decoding complaint.
    raw = plan_path.read_bytes()
    digest = sha256_of(raw)
    n_bytes = len(raw)
    recorded = record["sha256"]
    recorded_bytes = int(record["bytes"])

    if digest != recorded:
        print("=" * 78, file=sys.stderr)
        print("FAIL: THE PLAN HAS CHANGED SINCE IT WAS LOCKED", file=sys.stderr)
        print("=" * 78, file=sys.stderr)
        print(f"  recorded SHA-256           : {recorded}", file=sys.stderr)
        print(f"  current  SHA-256           : {digest}", file=sys.stderr)
        print(f"  recorded bytes             : {recorded_bytes:,}", file=sys.stderr)
        print(f"  current  bytes             : {n_bytes:,}  ({n_bytes - recorded_bytes:+,})",
              file=sys.stderr)
        print(f"  locked at                  : {record['locked']}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  This is stop condition 1 of the plan's section 11. Either restore the locked", file=sys.stderr)
        print("  file, or record the change in the plan's amendment log with a date and a", file=sys.stderr)
        print("  reason, re-run the lock, and keep BOTH hashes in SESSION-LOG.md.", file=sys.stderr)
        return EXIT_MISMATCH

    # The bytes are now known to be exactly what was locked, so the prose guard can only fire on a
    # plan that was locked in violation, which lock() refuses to do.  It runs anyway, because the
    # guard is cheap and a firing here would mean the record and the plan were replaced together.
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"FAIL: {PLAN_NAME} is not valid UTF-8: {exc}", file=sys.stderr)
        return EXIT_PROSE
    try:
        assert_house_prose(text, PLAN_NAME)
    except LockError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return EXIT_PROSE

    age = ""
    try:
        locked_at = datetime.fromisoformat(record["locked"].replace("Z", "+00:00"))
        elapsed = datetime.now(timezone.utc) - locked_at
        age = f"  ({elapsed.days} day(s), {elapsed.seconds // 3600} hour(s) ago)"
    except ValueError:
        age = ""

    print("=" * 78)
    print(f"CHECK PASSED: {PLAN_NAME} is byte-identical to the locked version")
    print("=" * 78)
    print(f"  SHA-256                    : {digest}")
    print(f"  bytes                      : {n_bytes:,}")
    print(f"  locked at                  : {record['locked']}{age}")
    print(f"  record read from           : {hash_path.name}  (not rewritten)")
    return EXIT_OK


# ===========================================================================
# E. SELF-TEST.
# ===========================================================================
def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_self_test() -> None:
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout

    n = 0
    good_plan = (
        "# A plan\n\nThe tier boundaries are 20–49 and 50–99 events.\n"
        "Nothing here uses a long dash.\n"
    )

    def quietly(fn, *args) -> Tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = fn(*args)
        return code, out.getvalue() + err.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        here = Path(tmp)
        plan = here / PLAN_NAME
        record = here / HASH_NAME

        # -- nothing to lock, nothing to check -------------------------------
        _expect(quietly(check, here)[0] == EXIT_MISSING, "check with no record must exit 2")
        _expect(quietly(lock, here)[0] == EXIT_MISSING, "lock with no plan must exit 2")
        n += 2

        # -- the happy path --------------------------------------------------
        plan.write_text(good_plan, encoding="utf-8")
        code, text = quietly(lock, here)
        _expect(code == EXIT_OK, "a clean plan must lock")
        _expect(record.is_file(), "the lock must write the record file")
        _expect("PASTE INTO SESSION-LOG.md:" in text, "the lock must print a line to paste")
        n += 3

        parsed = parse_hash_file(record.read_text(encoding="utf-8"))
        expected = hashlib.sha256(good_plan.encode("utf-8")).hexdigest()
        _expect(parsed["sha256"] == expected, "the recorded hash must be the SHA-256 of the bytes")
        _expect(int(parsed["bytes"]) == len(good_plan.encode("utf-8")), "byte length must be recorded")
        _expect(parsed["file"] == PLAN_NAME, "the record must name the file it locked")
        _expect(parsed["locked"].endswith("Z") and "T" in parsed["locked"], "the stamp must be ISO-8601 UTC")
        n += 4

        before = record.read_bytes()
        _expect(quietly(check, here)[0] == EXIT_OK, "an untouched plan must pass the check")
        _expect(record.read_bytes() == before, "--check must not rewrite the record")
        n += 2

        # -- the case this tool exists for: a silent post-lock edit -----------
        plan.write_text(good_plan + "One quiet extra sentence.\n", encoding="utf-8")
        code, text = quietly(check, here)
        _expect(code == EXIT_MISMATCH, "an edited plan must fail the check")
        _expect("HAS CHANGED SINCE IT WAS LOCKED" in text, "the failure must say what happened")
        n += 2

        # -- the case the old ordering MASKED: a tamper that also breaks prose.
        # The fixture above is prose-clean, so it could not catch a guard that ran first.
        # This one is not: it must still report the hash, not the typography.
        plan.write_text(good_plan + "A tampered sentence " + EM_DASH + " with an em-dash.\n",
                        encoding="utf-8")
        code, text = quietly(check, here)
        _expect(code == EXIT_MISMATCH,
                "a tamper that also breaks a prose rule must report the TAMPER, exit 1, not exit 3")
        _expect("HAS CHANGED SINCE IT WAS LOCKED" in text,
                "the tamper message must survive a coincident prose violation")
        _expect("em-dash" not in text,
                "the prose guard must not speak before the hash comparison has")
        n += 3

        # -- a tamper that also breaks the en-dash rule, same requirement -----
        plan.write_text(good_plan + "Cervical" + EN_DASH + "lumbar was appended.\n",
                        encoding="utf-8")
        _expect(quietly(check, here)[0] == EXIT_MISMATCH,
                "a non-range en-dash in a tampered plan must still exit 1")
        n += 1

        # -- a missing plan under an existing record -------------------------
        plan.unlink()
        _expect(quietly(check, here)[0] == EXIT_MISSING, "a deleted plan must exit 2, not 1")
        n += 1

        # -- the house prose guard, both rules --------------------------------
        # The banned characters are spelled with the constants, never typed, so this file stays
        # clean under a repo-wide grep for U+2014 and U+2013.
        plan.write_text("# A plan\n\nA sentence " + EM_DASH + " with an em-dash.\n",
                        encoding="utf-8")
        code, text = quietly(lock, here)
        _expect(code == EXIT_PROSE, "an em-dash must refuse the lock")
        _expect("Nothing was written" in text, "a refused lock must say it wrote nothing")
        n += 2

        plan.write_text("# A plan\n\nCervical" + EN_DASH + "lumbar is not a range.\n",
                        encoding="utf-8")
        _expect(quietly(lock, here)[0] == EXIT_PROSE, "a non-range en-dash must refuse the lock")
        n += 1

        plan.write_text("# A plan\n\nDays 1–35 is a range.\n", encoding="utf-8")
        _expect(quietly(lock, here)[0] == EXIT_OK, "an en-dash between digits is allowed")
        n += 1

        _expect(assert_house_prose("20–49 and 50–99", "x") == 2,
                "the guard must report how many en-dashes it inspected")
        n += 1

        # -- an empty plan is not a lockable plan -----------------------------
        plan.write_text("   \n", encoding="utf-8")
        _expect(quietly(lock, here)[0] == EXIT_PROSE, "an empty plan must refuse the lock")
        n += 1

        # -- a corrupted record is a stop condition, not a silent pass --------
        plan.write_text(good_plan, encoding="utf-8")
        quietly(lock, here)
        good_record = record.read_text(encoding="utf-8")
        record.write_text("file: ANALYSIS-PLAN.md\n", encoding="utf-8")
        _expect(quietly(check, here)[0] == EXIT_PROSE, "a record missing its hash must not pass")
        n += 1

        # A record whose 'bytes' line is not an integer used to raise a raw ValueError, which is a
        # traceback and not an exit code.  Same for a truncated digest.
        record.write_text(good_record.replace("bytes: ", "bytes: not-a-number "), encoding="utf-8")
        code, text = quietly(check, here)
        _expect(code == EXIT_PROSE, "a non-integer bytes line must exit 3, not raise")
        _expect("non-negative" in text, "the failure must name what was wrong with the record")
        record.write_text(good_record.replace(good_record.split("sha256: ")[1][:64], "beef"),
                          encoding="utf-8")
        _expect(quietly(check, here)[0] == EXIT_PROSE, "a truncated digest must exit 3, not pass")
        n += 3

    # -- pure functions, no filesystem ---------------------------------------
    _expect(sha256_of(b"") ==
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "sha256_of must be the standard digest")
    stamp = utc_stamp(datetime(2026, 8, 25, 21, 14, 3, tzinfo=timezone.utc))
    _expect(stamp == "2026-08-25T21:14:03Z", f"utc_stamp must render a Z-suffixed stamp, got {stamp}")
    line = render_session_log_line("a" * 64, 82094, stamp)
    _expect("82,094 bytes" in line, "the paste line must use house numeral style")
    _expect(EM_DASH not in line, "the paste line must obey the house prose rules itself")
    n += 4

    # -- the command line ------------------------------------------------------
    # An unrecognised argument used to return 2, documented as "a required file is missing", which
    # sends a caller looking for a file that is present.  It is a usage error and says so.
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        usage_code = main(["--no-such-flag"])
    _expect(usage_code == EXIT_USAGE, "an unrecognised argument must exit 64, not 2")
    _expect("unrecognised" in err.getvalue(), "a usage error must name the offending argument")
    n += 2

    print("=" * 78)
    print("lock_plan.py SELF-TEST: PASS")
    print("=" * 78)
    print(f"  assertions executed        : {n}")
    print( "  exercised                  : lock, check, both prose rules, a post-lock edit, a")
    print( "                               post-lock edit that ALSO breaks a prose rule, a deleted")
    print( "                               plan, an empty plan, three corrupted records, a usage")
    print( "                               error")
    print( "  wrote                      : nothing outside a temporary directory")


# ===========================================================================
# F. ENTRY POINT.
# ===========================================================================
def main(argv: List[str]) -> int:
    if not argv:
        return lock()
    if len(argv) == 1 and argv[0] == "--check":
        return check()
    if len(argv) == 1 and argv[0] == "--self-test":
        _run_self_test()
        return EXIT_OK
    print(__doc__ or "", file=sys.stderr)
    print(f"FAIL: unrecognised arguments {argv}", file=sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
