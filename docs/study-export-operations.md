# Study export operations

Operator guide for the stable persistent study-ID registry introduced in #54.

## Background

`export_adapter.py` exports OCS chatbot transcripts as `conversations_export.csv`.
Every participant needs a stable `STUDY_####` identifier across all exports — the same
person must appear as `STUDY_0017` in every CSV produced, now and in the future.

The old `assign_study_ids()` function re-sorted all keys on every call.  Adding a new
participant whose internal key sorts before an existing one would shift every later
participant's number.  This broke any downstream analysis that referenced study IDs from
earlier exports.  `assign_study_ids()` now **raises `TypeError`** with migration guidance;
it cannot be called.  Use `--study-id-registry` instead.

---

## First use: create the registry

Run once, before the first export:

```sh
# Without legacy Zeya users:
python -m ocs.study_ids create --registry /secure/path/study_ids.json

# With legacy Zeya users (seeds them in sorted user_id order):
python -m ocs.study_ids create \
    --registry /secure/path/study_ids.json \
    --seed zeya_users.csv
```

`zeya_users.csv` must have a `user_id` column.  **Bootstrap from the same authoritative
legacy participant roster used in earlier analyses** — the ordering of this initial seed
determines STUDY_0001, STUDY_0002, … and must remain consistent with any prior
publications or analysis that referenced those numbers.

The exact SQL query that produced the legacy cohort export (preserved verbatim to
maintain authoritative ordering):

```sql
\copy (SELECT DISTINCT u.id AS user_id, u.whatsapp_id
       FROM users u
       JOIN conversations c ON c.user_id = u.id)
  TO 'zeya_users.csv' CSV HEADER
```

Do not substitute a different query (e.g. `SELECT * FROM users`) — that would include
participants not in the original analysis cohort and change the authoritative ordering.
If the original roster is unavailable, contact the study coordinator before creating a
new registry; a new STUDY_#### sequence is incompatible with earlier outputs.

Legacy users are seeded in sorted `user_id` order as STUDY_0001, STUDY_0002, … before
any OCS allocations.  All rows must have non-empty `user_id` values without surrounding
whitespace; blank or padded rows are rejected.  A CSV with both `user_id` and `id`
columns is also rejected (use only one).

**The registry file is sensitive.** It links opaque participant keys to study IDs.
Exclude it from version control, CSVs, reports and logs.  It is created with mode
`0o600` (owner read/write only).

---

## Exporting

Add `--study-id-registry` to every export command:

```sh
python -m ocs.export_adapter \
    --ocs-export ocs_sessions.csv \
    --zeya-users zeya_users.csv \
    --study-id-registry /secure/path/study_ids.json \
    --out conversations_export_ocs.csv
```

`--study-id-registry` is **required**.  Omitting it exits non-zero with a clear message
rather than silently using the unstable fallback.

New participants encountered during export are appended to the registry (allocated the
next available STUDY_#### number) and the registry is saved atomically before the CSV is
written.

---

## Checking the registry

```sh
python -m ocs.study_ids check --registry /secure/path/study_ids.json
```

Validates schema, format, uniqueness and consistency and prints the number of allocated
IDs.

---

## Concurrency

The registry uses an advisory `fcntl` file lock (`.lock` sibling file) plus a
per-path threading lock.  Only one process or thread can allocate IDs at a time.  The
lock times out after 30 seconds.

**Limitations:**

- Cross-host locking is not supported.  Run one exporter at a time per registry file.
- Cross-filesystem atomicity is not guaranteed.  Keep the registry on a local filesystem.
- Do not store the registry on a network-mounted filesystem (NFS, SMB, etc.).

---

## Write order and atomicity

The export follows this order:

1. Acquire lock.
2. Load registry; allocate IDs for all new participants in memory.
3. Render the CSV into an **in-memory buffer** (no file created yet).
4. **Commit the registry atomically to disk** (while still under lock).
5. Release lock.
6. Write the CSV from the buffer to `--out` (temp file then rename) or to stdout.

**If the registry commit fails (step 4):** no CSV is written and the registry file is
unchanged.  The in-memory allocations are discarded; re-running produces the same IDs
(monotonically increasing, never recycled).

**If the CSV write fails (step 6, after registry commit):** the registry retains the
newly allocated IDs; no output file is created (the temp file is cleaned up).  Re-running
produces the **same** study IDs (they are already in the registry).

**If the final CSV rename fails** after a successful write to temp: the registry is
committed but the temp file is cleaned up and `--out` does not exist.  The IDs are
in the registry; re-run the export to produce a new output file.

**stdout output:** when `--out` is omitted, the CSV buffer is written to stdout after
the registry is committed.  A process crash after commit but before stdout write leaves
the registry updated with no visible output — re-run to produce the CSV.

---

## Migration from earlier exports

If the registry file is **lost** after exports have been distributed:

1. You **cannot** reconstruct the mapping from the CSV alone.  The CSV no longer
   contains the original participant keys (only study IDs).
2. Supply an authoritative mapping from a backup, or accept that
   `create --registry` will produce a **new, incompatible** numbering.
3. `locked_registry` and `open_registry` both refuse to operate on a missing file
   (they raise `RegistryLostError`) rather than silently starting fresh.  This is a
   deliberate safeguard.

If you have an earlier CSV that uses the old numbered identifiers alongside a backup of
the original participant list (UUID-to-study-ID correspondence), contact the study
coordinator.  Automated inference from the CSV is not supported.

---

## Alias/symlink safety

The CLI rejects `--out` when it resolves (via `os.stat`) to the same inode as
`--ocs-export`, `--study-id-registry`, or `--zeya-users`.  This prevents accidental
overwriting of input files through symlinks or hard links.

---

## Security note

Sequential public study IDs (`STUDY_0001`, `STUDY_0002`, …) are **not** a
cryptographic anonymisation claim.  An adversary who knows the total participant count
and the range of study IDs can infer approximate ordering.  If strong pseudonymisation
is required, use a separate hashing or permutation step before publication.
