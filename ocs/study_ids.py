"""
Stable persistent study-ID registry for Zeya OCS exports.

Maintains an append-only mapping from opaque participant key (Zeya legacy user UUID
or OCS "ocs:<public_id>" key) to a sequential STUDY_#### identifier.

Design guarantees
-----------------
- **Stable**: once a key is assigned STUDY_0017, it stays STUDY_0017 across all
  future exports, regardless of which other keys appear or disappear.
- **Append-only**: new keys receive the next available number; existing entries are
  never renumbered or removed.
- **Fail-closed**: ``open_registry`` and ``locked_registry`` raise ``RegistryLostError``
  when the file is absent rather than silently bootstrapping a fresh mapping.
- **Atomic writes**: the registry is written to a temporary file (mode 0o600) and
  renamed into place; a crash during save leaves the previous content intact.
  Temporary files are always removed on failure, including rename failure.
  No directory fsync is performed; durability on power loss is not guaranteed.
- **Concurrent safety**: an advisory ``fcntl`` lock (bounded by ``timeout_s``) plus a
  per-path ``threading.Lock`` serialise allocations within and across threads; cross-host
  or cross-filesystem atomicity is not guaranteed.
- **Read-only snapshots**: ``open_registry`` returns a snapshot whose ``allocate`` and
  ``save`` methods raise ``RegistryError``; mutations require ``locked_registry``.
- **Post-exit invalidation**: the handle yielded by ``locked_registry`` is set
  read-only after the context exits (clean or exception), preventing unlocked mutations.
- **Plain regular files only**: registry paths that are symlinks are rejected; the
  caller must supply the canonical path so lock files are consistent.

Migration limits
----------------
If the registry file is lost after exports have been distributed:

1. You **cannot** reconstruct the mapping from the CSV alone — it no longer contains
   the original participant keys.
2. An operator must supply an authoritative mapping (e.g. from a backup) or accept
   that the next ``create_registry`` call will produce a **new, incompatible** numbering.
3. Use ``create_registry`` only for the initial bootstrap.  For all subsequent exports,
   use ``locked_registry`` which refuses to create a fresh mapping if the file is absent.

The registry file is **sensitive** (it links opaque keys to study IDs).  Exclude it
from version control, CSVs, reports and logs.  The ``0o600`` permission is a defence-in-
depth measure, not a substitute for proper key management.
"""

import csv
import errno
import fcntl
import json
import os
import re
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

REGISTRY_VERSION = 1
# [0-9] restricts to ASCII digits only; \d would also match Unicode digit characters.
_STUDY_ID_RE = re.compile(r"^STUDY_([0-9]{4,})$")
_LOCK_TIMEOUT_S: float = 30.0
_LOCK_POLL_S: float = 0.05

_process_locks: dict[str, threading.Lock] = {}
_process_locks_mutex = threading.Lock()


def _get_thread_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _process_locks_mutex:
        if key not in _process_locks:
            _process_locks[key] = threading.Lock()
        return _process_locks[key]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RegistryError(Exception):
    """Base class for all registry failures."""


class RegistryLostError(RegistryError):
    """Registry file absent after prior use — refusing silent re-bootstrap."""


class RegistryConflictError(RegistryError):
    """Registry file already exists; use ``locked_registry`` to modify it."""


class RegistrySchemaError(RegistryError):
    """Registry content fails schema, format, uniqueness or consistency checks."""


class RegistryLockError(RegistryError):
    """Exclusive lock could not be acquired within the allotted timeout."""


# ---------------------------------------------------------------------------
# Key and path validation helpers
# ---------------------------------------------------------------------------


def _validate_key(key: object) -> None:
    """Raise ``RegistryError`` if *key* is not a valid plain non-empty string.

    Rejects: bool, non-str, empty string, whitespace-only string.
    The rejected value is never included in the error message.
    """
    if isinstance(key, bool) or not isinstance(key, str):
        raise RegistryError(
            "registry keys must be plain non-empty strings (bool/int/None/other types are not valid identifiers)"
        )
    if not key.strip():
        raise RegistryError("registry keys must be non-empty and non-whitespace")


def _reject_noncanonical_registry(path: Path) -> None:
    """Raise ``RegistryError`` if *path* is a symlink, non-regular file, or hardlink alias.

    Checks are ordered to avoid blocking I/O:
    1. Symlink: divergent lock namespace.
    2. Non-regular file type (FIFO, device, socket, directory): ``path.is_file()`` uses
       ``os.stat()`` which does not block; ``open()`` or ``read_text()`` on a FIFO would
       block indefinitely waiting for a writer.
    3. Hardlink (``st_nlink > 1``): multiple names → different ``.lock`` siblings.
    """
    if path.is_symlink():
        raise RegistryError(
            "registry path must not be a symlink; resolve it to the canonical "
            "regular-file path so all callers derive the same lock file"
        )
    # Non-regular types (FIFO, device, socket, directory) must be rejected BEFORE any
    # read/open call; os.stat does not block, but open() on a FIFO would.
    if path.exists() and not path.is_file():
        raise RegistryError(
            "registry path must be a plain regular file; FIFOs, devices, sockets and directories are not supported"
        )
    if path.exists():
        try:
            if os.stat(path).st_nlink > 1:
                raise RegistryError(
                    "registry path is a hardlink alias (st_nlink > 1); "
                    "use the sole canonical path so all callers derive the same lock file"
                )
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------


class StudyIdRegistry:
    """In-memory view of a loaded registry.

    Do not construct directly; use ``create_registry``, ``open_registry``, or
    ``locked_registry``.
    """

    def __init__(
        self,
        path: Path,
        mapping: dict[str, str],
        next_n: int,
        *,
        read_only: bool = False,
    ) -> None:
        self._path = path
        self._mapping: dict[str, str] = mapping
        self._next_n = next_n
        self._read_only = read_only
        self._committed = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def next_n(self) -> int:
        return self._next_n

    def keys(self) -> frozenset[str]:
        return frozenset(self._mapping)

    def lookup(self, key: str) -> str | None:
        """Return the existing study ID for *key*, or ``None``."""
        return self._mapping.get(key)

    def allocate(self, key: str) -> str:
        """Return the existing study ID for *key*, or allocate the next available one.

        Idempotent for existing keys (does not change ``_committed``).
        A **new** allocation resets ``_committed`` to ``False`` so
        ``locked_registry`` auto-saves on clean exit even after an explicit
        ``save()`` call earlier in the same transaction (F2).

        Raises ``RegistryError`` on invalid keys or read-only instances.
        """
        if self._read_only:
            raise RegistryError(
                "allocate() is not permitted on a read-only instance; use locked_registry() to mutate the registry"
            )
        _validate_key(key)
        if key in self._mapping:
            return self._mapping[key]  # idempotent — _committed unchanged
        study_id = f"STUDY_{self._next_n:04d}"
        self._mapping[key] = study_id
        self._next_n = self._next_n + 1
        self._committed = False  # F2: dirty after new allocation
        return study_id

    def save(self) -> None:
        """Atomic save with mode 0o600.  Sets ``_committed = True``.

        Raises ``RegistryError`` on read-only instances.
        """
        if self._read_only:
            raise RegistryError(
                "save() is not permitted on a read-only instance; use locked_registry() to mutate the registry"
            )
        _atomic_write(
            self._path,
            {
                "version": REGISTRY_VERSION,
                "next_n": self._next_n,
                "mapping": self._mapping,
            },
        )
        self._committed = True


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, data: dict) -> None:
    """Write *data* as JSON to *path* atomically with mode 0o600."""
    parent = path.parent
    fd, tmp_str = tempfile.mkstemp(prefix=".studyids-tmp-", suffix=".json", dir=parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            json.dump(data, fh, indent=2, ensure_ascii=True, sort_keys=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_str, path)
        tmp_str = None
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except BaseException:
        if fd >= 0:
            os.close(fd)
        if tmp_str is not None:
            try:
                os.unlink(tmp_str)
            except OSError:
                pass
        raise


# ---------------------------------------------------------------------------
# Duplicate-key JSON hook
# ---------------------------------------------------------------------------


def _detect_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """``object_pairs_hook`` that raises ``RegistrySchemaError`` on duplicate keys."""
    result: dict = {}
    for k, v in pairs:
        if k in result:
            raise RegistrySchemaError("registry contains duplicate JSON keys — file may be tampered or corrupt")
        result[k] = v
    return result


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def _validate(data: object, path: Path) -> tuple[dict[str, str], int]:
    """Validate registry *data* and return (mapping, next_n) or raise RegistrySchemaError."""
    if not isinstance(data, dict):
        raise RegistrySchemaError(f"registry is not a JSON object: {path}")

    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version != REGISTRY_VERSION:
        raise RegistrySchemaError(f"unsupported registry version (expected plain int {REGISTRY_VERSION}): {path}")

    next_n = data.get("next_n")
    if not isinstance(next_n, int) or isinstance(next_n, bool) or next_n < 1:
        raise RegistrySchemaError(f"registry 'next_n' must be a plain positive integer (>= 1): {path}")

    raw_mapping = data.get("mapping")
    if not isinstance(raw_mapping, dict):
        raise RegistrySchemaError(f"registry 'mapping' must be a JSON object: {path}")

    mapping: dict[str, str] = {}
    max_seq = 0
    seen_values: set[str] = set()
    for k, v in raw_mapping.items():
        if not isinstance(k, str):
            raise RegistrySchemaError(f"registry mapping key is not a string: {path}")
        if not k.strip():
            raise RegistrySchemaError(f"registry mapping contains an empty or whitespace-only key: {path}")
        if not isinstance(v, str):
            raise RegistrySchemaError(f"registry mapping value for a key is not a string: {path}")
        m = _STUDY_ID_RE.fullmatch(v)
        if m is None:
            raise RegistrySchemaError(f"registry study-id value does not match STUDY_[0-9]{{4,}} format: {path}")
        seq = int(m.group(1))
        if seq < 1:
            raise RegistrySchemaError(f"registry study-id sequence must be >= 1: {path}")
        # F4: canonicality check — f'STUDY_{seq:04d}' must equal v exactly.
        # Rejects STUDY_00001 (extra leading zero) and Unicode digit forms like STUDY_０００１.
        canonical = f"STUDY_{seq:04d}"
        if v != canonical:
            raise RegistrySchemaError(
                f"registry study-id is not in canonical format "
                f"(STUDY_NNNN, minimum 4 digits, no extra leading zeros): {path}"
            )
        if v in seen_values:
            raise RegistrySchemaError(f"registry contains duplicate study-id value (uniqueness violated): {path}")
        seen_values.add(v)
        mapping[k] = v
        if seq > max_seq:
            max_seq = seq

    if mapping and next_n <= max_seq:
        raise RegistrySchemaError(f"registry 'next_n' must exceed highest allocated sequence ({max_seq}): {path}")

    return mapping, next_n


# ---------------------------------------------------------------------------
# Internal mutable loader
# ---------------------------------------------------------------------------


def _load_registry_mutable(path: Path) -> StudyIdRegistry:
    if not path.exists():
        raise RegistryLostError(f"Registry file not found — refusing to bootstrap a new mapping: {path}")
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_detect_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise RegistrySchemaError(f"registry JSON is malformed: {path}") from exc
    mapping, next_n = _validate(raw, path)
    return StudyIdRegistry(path, mapping, next_n, read_only=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_registry(path: Path, keys_in_order: list[str]) -> "StudyIdRegistry":
    """Create a new registry at *path*, seeding *keys_in_order* as STUDY_0001, STUDY_0002, …

    All keys are validated **before** any file is created (F3): an invalid key raises
    ``RegistryError`` without creating the registry file.

    Returns a **read-only snapshot**; further mutations require ``locked_registry``.

    Raises ``RegistryError`` if *path* is a symlink.
    Raises ``RegistryConflictError`` if *path* already exists.
    Raises ``RegistryLockError`` if the advisory lock cannot be acquired.
    """
    _reject_noncanonical_registry(path)

    # F3: validate ALL keys before acquiring lock or touching any file
    for key in keys_in_order:
        _validate_key(key)

    lock_path = path.with_suffix(".lock")
    thread_lock = _get_thread_lock(path)

    if not thread_lock.acquire(timeout=_LOCK_TIMEOUT_S):
        raise RegistryLockError(f"Could not acquire thread lock for {path}")
    try:
        with _fcntl_lock(lock_path, timeout_s=_LOCK_TIMEOUT_S):
            if path.exists():
                raise RegistryConflictError(f"Registry already exists; use locked_registry to modify: {path}")
            mapping: dict[str, str] = {}
            next_n = 1
            for key in keys_in_order:
                if key not in mapping:
                    mapping[key] = f"STUDY_{next_n:04d}"
                    next_n = next_n + 1
            reg = StudyIdRegistry(path, mapping, next_n, read_only=False)
            reg.save()
            return StudyIdRegistry(path, dict(mapping), next_n, read_only=True)
    finally:
        thread_lock.release()


def open_registry(path: Path) -> "StudyIdRegistry":
    """Load an existing registry as a **read-only snapshot** (no lock held).

    Raises ``RegistryError`` if *path* is a symlink.
    Raises ``RegistryLostError`` if *path* does not exist.
    Raises ``RegistrySchemaError`` on malformed or tampered content.
    """
    _reject_noncanonical_registry(path)
    if not path.exists():
        raise RegistryLostError(f"Registry file not found — refusing to bootstrap a new mapping: {path}")
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_detect_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise RegistrySchemaError(f"registry JSON is malformed: {path}") from exc
    mapping, next_n = _validate(raw, path)
    return StudyIdRegistry(path, mapping, next_n, read_only=True)


@contextmanager
def locked_registry(path: Path, *, timeout_s: float = _LOCK_TIMEOUT_S) -> Iterator[StudyIdRegistry]:
    """Context manager: acquire exclusive lock, yield mutable registry, save on clean exit.

    **F1 (post-exit invalidation)**: the yielded handle is set read-only in ``finally``
    so post-exit ``allocate()``/``save()`` raise ``RegistryError``.

    **F2 (allocation after explicit save)**: ``allocate()`` resets ``_committed=False``
    on each new allocation.  ``locked_registry`` auto-saves on clean exit whenever
    ``_committed`` is False — including after an explicit ``save()`` followed by more
    allocations.

    Raises ``RegistryError`` if *path* is a symlink.
    Raises ``RegistryLostError`` if *path* does not exist.
    Raises ``RegistryLockError`` if the lock cannot be acquired within *timeout_s*.
    """
    _reject_noncanonical_registry(path)
    lock_path = path.with_suffix(".lock")
    thread_lock = _get_thread_lock(path)

    if not thread_lock.acquire(timeout=timeout_s):
        raise RegistryLockError(f"Could not acquire thread lock for {path} within {timeout_s}s")
    reg: StudyIdRegistry | None = None
    try:
        with _fcntl_lock(lock_path, timeout_s=timeout_s):
            reg = _load_registry_mutable(path)
            try:
                yield reg
            except BaseException:
                raise
            else:
                if not reg._committed:
                    reg.save()
    finally:
        # F1: always invalidate the yielded handle after context exit
        if reg is not None:
            reg._read_only = True
        thread_lock.release()


# ---------------------------------------------------------------------------
# Lock helper
# ---------------------------------------------------------------------------


@contextmanager
def _fcntl_lock(lock_path: Path, *, timeout_s: float) -> Iterator[None]:
    """Acquire an exclusive advisory flock on *lock_path*, bounded by *timeout_s*.

    Raises ``RegistryError`` if *lock_path* is already a symlink — a symlink lock
    would update a different file's mtime and corrupt lock identity.
    """
    if lock_path.is_symlink():
        raise RegistryError(
            "lock file must not be a symlink; a symlink lock would change the "
            "target file's mtime and create incorrect lock identity"
        )
    # Non-regular lock file (FIFO, device, etc.) must be rejected before os.open(),
    # which would block on a FIFO.
    if lock_path.exists() and not lock_path.is_file():
        raise RegistryError("lock file must be a plain regular file; FIFOs, devices and sockets are not supported")
    lock_path.touch(mode=0o600, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR)
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    raise RegistryLockError(f"Could not acquire file lock within {timeout_s}s") from exc
                time.sleep(_LOCK_POLL_S)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Seed CSV reader
# ---------------------------------------------------------------------------


def _read_seed_keys(seed_path: str) -> list[str]:
    """Read sorted user IDs from a seed CSV, accepting 'user_id' or 'id' column.

    F7: Rejects conflicting dual columns, header-only files, and any blank identifier.
    Participant identifiers are never echoed in error messages.
    """
    import sys

    path = Path(seed_path)
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise RegistryError(f"seed CSV is empty or missing header row: {path}")
            fieldnames = list(reader.fieldnames)

            # Reject duplicate column headers before any other processing
            if len(fieldnames) != len(set(fieldnames)):
                raise RegistryError("seed CSV has duplicate column headers; each column must appear exactly once")

            has_user_id = "user_id" in fieldnames
            has_id = "id" in fieldnames

            # F7: reject ambiguous dual-column input without guessing
            if has_user_id and has_id:
                raise RegistryError(
                    "seed CSV has both 'user_id' and 'id' columns; "
                    "include only one identifier column "
                    "(see docs/study-export-operations.md)"
                )

            if has_user_id:
                col = "user_id"
            elif has_id:
                col = "id"
                print(
                    "warning: seed CSV uses column 'id'; prefer 'user_id' (see docs/study-export-operations.md)",
                    file=sys.stderr,
                )
            else:
                raise RegistryError("seed CSV must have a 'user_id' column (see docs/study-export-operations.md)")

            all_rows = list(reader)

            # F7: header-only seed is not valid
            if not all_rows:
                raise RegistryError(
                    "seed CSV has no data rows; header-only seed is not valid — "
                    "use 'python -m ocs.study_ids create --registry R.json' "
                    "without --seed for empty initialization"
                )

            # Validate entire row shape before any cell access:
            # - Extra cells: DictReader stores overflow under restkey=None.
            # - Missing cells: DictReader fills gaps with restval=None (not a string).
            # Reject both without echoing any cell content.
            for row in all_rows:
                if None in row:
                    raise RegistryError(
                        f"seed CSV row has more values than headers in column "
                        f"{col!r}; every row must match the header column count exactly"
                    )
                if any(not isinstance(v, str) for v in row.values()):
                    raise RegistryError(
                        f"seed CSV row is missing one or more cells for column "
                        f"{col!r}; every row must have a value for every header column"
                    )

            # F7/F3: do NOT strip — surrounding whitespace is a distinct identity error.
            # Stripping would silently normalize ' opaque-a ' into 'opaque-a', treating
            # two different literal strings as the same participant.
            raw_keys = [row.get(col, "") for row in all_rows]

            # Guard malformed rows: DictReader fills missing cells with restval=None.
            # An extra-column row stores extra values under restkey; the named column
            # may still be a valid string in that case, so we check per-cell.
            non_string = [i for i, k in enumerate(raw_keys) if not isinstance(k, str)]
            if non_string:
                raise RegistryError(
                    f"seed CSV has a malformed row with a missing or non-string cell "
                    f"in column {col!r}; every row must have exactly one value per column "
                    f"(not echoing row content)"
                )

            # Reject blank identifiers (empty after strip — checked after type guard)
            if any(not k.strip() for k in raw_keys):
                raise RegistryError(
                    f"seed CSV contains blank or missing identifier values in "
                    f"column {col!r}; every row must have a non-empty identifier"
                )
            # Reject surrounding whitespace without normalising identity
            if any(k != k.strip() for k in raw_keys):
                raise RegistryError(
                    f"seed CSV identifier in column {col!r} has surrounding whitespace; "
                    "preserve the exact literal value or strip it in the source data, "
                    "not silently here"
                )

            keys = sorted(raw_keys)

    except (OSError, csv.Error) as exc:
        raise RegistryError(f"could not read seed CSV (not echoing content): {path}") from exc
    return keys


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Entry-point: python -m ocs.study_ids create|check --registry R.json [--seed S.csv]"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m ocs.study_ids",
        description=main.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Create a new registry (fails if already exists)")
    p_create.add_argument("--registry", required=True)
    p_create.add_argument(
        "--seed",
        help=(
            "CSV with user_id (or id) column.  All rows must have non-empty identifiers; "
            "header-only files are rejected.  For empty initialization omit --seed."
        ),
    )

    p_check = sub.add_parser("check", help="Validate an existing registry and print stats")
    p_check.add_argument("--registry", required=True)

    args = parser.parse_args(argv)

    if args.command == "create":
        reg_path = Path(args.registry)
        keys: list[str] = []
        if args.seed:
            try:
                keys = _read_seed_keys(args.seed)
            except RegistryError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
        try:
            reg = create_registry(reg_path, keys)
        except RegistryConflictError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except RegistryLockError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        n = reg.next_n - 1
        print(f"Created registry at {reg_path} with {n} seeded key(s).")
        return 0

    if args.command == "check":
        reg_path = Path(args.registry)
        try:
            reg = open_registry(reg_path)
        except RegistryLostError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except RegistrySchemaError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        except RegistryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        n = reg.next_n - 1
        print(f"Registry OK: {n} allocated ID(s), next_n={reg.next_n}, path={reg_path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
