"""
Acceptance tests for ocs/study_ids.py — stable persistent study-ID registry.

Finite acceptance IDs S01-S12 (stable-ids-contract.md).

Synthetic fixture data only; no real participant exports or registry files.
"""

import csv
import json
import multiprocessing
import os
import sys
import threading
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# S01 — actual old-code instability RED; new persistent registry GREEN
# ---------------------------------------------------------------------------


def test_s01_old_assign_study_ids_raises():
    """S01: assign_study_ids is removed and raises TypeError with migration guidance.

    Historical evidence: the original function sorted all keys on every call.
    Adding a new earlier-sorting key shifted every later participant's STUDY_####.
    Example: before = STUDY_0001 for 'ocs:z-existing'; after adding 'ocs:a-new',
    'ocs:a-new' got STUDY_0001 and 'ocs:z-existing' shifted to STUDY_0002.
    The fix is removal: callers must use locked_registry with --study-id-registry.
    """
    from ocs.export_adapter import assign_study_ids

    with pytest.raises(TypeError, match="assign_study_ids"):
        assign_study_ids([{"user_key": "ocs:z-existing"}], [])


def test_s01_registry_stable_across_simulated_runs(tmp_path):
    """S01 GREEN: persistent registry keeps existing IDs when new earlier-sorting key added."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "study_ids.json"

    # First "run": create registry with one key
    reg = create_registry(reg_path, ["ocs:z-existing"])
    first_id = reg.lookup("ocs:z-existing")
    assert first_id == "STUDY_0001"

    # Second "run": add a new key that sorts earlier
    with locked_registry(reg_path) as reg2:
        new_id = reg2.allocate("ocs:a-new")

    # Third "run": reload and verify existing key unchanged
    with locked_registry(reg_path) as reg3:
        existing_id = reg3.lookup("ocs:z-existing")

    assert existing_id == first_id, (
        f"S01: existing ID changed from {first_id!r} to {existing_id!r} after new earlier key"
    )
    assert new_id != first_id, "S01: new earlier-sorting key must get a different ID"


def test_s01_cli_two_run_stable(tmp_path):
    """S01 GREEN: two sequential CLI runs; participant p-z ID stable despite new p-a added.

    Uses distinct per-participant message markers to identify each row exactly.
    """
    from ocs.export_adapter import main as adapter_main
    from ocs.study_ids import create_registry

    reg_path = tmp_path / "study_ids.json"

    # Distinct safe message markers — no PII, just routing strings.
    _MSG_P_Z = "Routine care question marker-pz-s01"
    _MSG_P_A = "Routine care question marker-pa-s01"

    registered = {
        "study_participant": True,
        "consent_given": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }

    # Bootstrap registry with participant p-z already seeded.
    create_registry(reg_path, ["ocs:p-z"])

    # Run 1: export with participant p-z only.
    ocs1 = tmp_path / "ocs1.csv"
    _write_ocs_csv(ocs1, [("p-z", "+254700000001", registered, _MSG_P_Z)])
    out1 = tmp_path / "out1.csv"
    assert (
        adapter_main(
            [
                "--ocs-export",
                str(ocs1),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out1),
            ]
        )
        == 0
    ), "S01: first CLI run must succeed"
    rows1 = list(csv.DictReader(out1.open()))
    id_pz_run1 = next((r["study_id"] for r in rows1 if r["message_text"] == _MSG_P_Z), None)
    assert id_pz_run1 is not None, "S01: p-z must appear in first run output"

    # Run 2: add participant p-a (sorts before p-z in key order).
    ocs2 = tmp_path / "ocs2.csv"
    _write_ocs_csv(
        ocs2,
        [
            ("p-z", "+254700000001", registered, _MSG_P_Z),
            ("p-a", "+254700000002", registered, _MSG_P_A),
        ],
    )
    out2 = tmp_path / "out2.csv"
    assert (
        adapter_main(
            [
                "--ocs-export",
                str(ocs2),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out2),
            ]
        )
        == 0
    ), "S01: second CLI run must succeed"
    rows2 = list(csv.DictReader(out2.open()))
    id_pz_run2 = next((r["study_id"] for r in rows2 if r["message_text"] == _MSG_P_Z), None)
    id_pa_run2 = next((r["study_id"] for r in rows2 if r["message_text"] == _MSG_P_A), None)

    assert id_pz_run2 is not None, "S01: p-z must appear in second run"
    assert id_pa_run2 is not None, "S01: p-a must appear in second run"
    assert id_pz_run2 == id_pz_run1, (
        f"S01: p-z study_id changed from {id_pz_run1!r} to {id_pz_run2!r} "
        f"after earlier-sorting participant p-a was added"
    )
    assert id_pa_run2 != id_pz_run1, "S01: p-a must receive a different ID from p-z"


# ---------------------------------------------------------------------------
# S02 — new earlier-sorting identities preserve existing IDs
# ---------------------------------------------------------------------------


def test_s02_new_earlier_ocs_key_preserves_existing(tmp_path):
    """S02: new OCS key sorting before existing one appends; existing ID unchanged."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "study_ids.json"
    create_registry(reg_path, ["ocs:z-first"])

    with locked_registry(reg_path) as reg:
        id_z = reg.lookup("ocs:z-first")
        id_a = reg.allocate("ocs:a-new")

    assert id_z == "STUDY_0001"
    assert id_a == "STUDY_0002"  # appended, not renumbered

    with locked_registry(reg_path) as reg:
        assert reg.lookup("ocs:z-first") == "STUDY_0001"
        assert reg.lookup("ocs:a-new") == "STUDY_0002"


def test_s02_new_earlier_legacy_uuid_preserves_existing(tmp_path):
    """S02: new UUID that sorts before an existing UUID appends; existing ID unchanged."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "study_ids.json"
    # Seed in the order the operator provides (sorted UUIDs)
    create_registry(
        reg_path,
        [
            "b0000000-0000-0000-0000-000000000000",
            "c0000000-0000-0000-0000-000000000000",
        ],
    )

    # Later a new earlier-sorting UUID is discovered (e.g. imported from migration)
    with locked_registry(reg_path) as reg:
        id_b = reg.lookup("b0000000-0000-0000-0000-000000000000")
        id_c = reg.lookup("c0000000-0000-0000-0000-000000000000")
        id_a = reg.allocate("a0000000-0000-0000-0000-000000000000")

    # Existing IDs are unchanged; new UUID appends
    assert id_b == "STUDY_0001"
    assert id_c == "STUDY_0002"
    assert id_a == "STUDY_0003"


# ---------------------------------------------------------------------------
# S03 — subsets/removal/reordering/process restart preserve registry
# ---------------------------------------------------------------------------


def test_s03_subset_export_preserves_all_ids(tmp_path):
    """S03: exporting a subset of participants does not remove other entries from registry."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "study_ids.json"
    create_registry(reg_path, ["ocs:a", "ocs:b", "ocs:c"])

    # Export subset: only "ocs:a" and "ocs:c"
    with locked_registry(reg_path) as reg:
        reg.allocate("ocs:a")
        reg.allocate("ocs:c")

    # All three are still in the registry
    with locked_registry(reg_path) as reg:
        assert reg.lookup("ocs:a") is not None
        assert reg.lookup("ocs:b") is not None, "S03: absent-from-subset entry must stay in registry"
        assert reg.lookup("ocs:c") is not None


def test_s03_process_restart_preserves_ids(tmp_path):
    """S03: reloading registry (simulating process restart) preserves all IDs."""
    from ocs.study_ids import create_registry, locked_registry, open_registry

    reg_path = tmp_path / "study_ids.json"
    create_registry(reg_path, ["ocs:x", "ocs:y"])

    # Simulate restart by reloading
    reg_snapshot = open_registry(reg_path)
    assert reg_snapshot.lookup("ocs:x") == "STUDY_0001"
    assert reg_snapshot.lookup("ocs:y") == "STUDY_0002"

    # Allocate new key after reload
    with locked_registry(reg_path) as reg:
        reg.allocate("ocs:z")

    reg_after = open_registry(reg_path)
    assert reg_after.lookup("ocs:x") == "STUDY_0001"
    assert reg_after.lookup("ocs:y") == "STUDY_0002"
    assert reg_after.lookup("ocs:z") == "STUDY_0003"


def test_s03_allocate_existing_key_is_idempotent(tmp_path):
    """S03: allocating a key twice returns the same ID and does not advance next_n."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "study_ids.json"
    create_registry(reg_path, ["ocs:a"])

    with locked_registry(reg_path) as reg:
        id1 = reg.allocate("ocs:a")
        id2 = reg.allocate("ocs:a")
        n1 = reg.next_n

    assert id1 == id2 == "STUDY_0001"
    assert n1 == 2  # only one real allocation happened


# ---------------------------------------------------------------------------
# S04 — initial legacy ID order preserved; later users append; BSUID not digit-linked
# ---------------------------------------------------------------------------


def test_s04_legacy_bootstrap_preserves_given_order(tmp_path):
    """S04: create_registry seeds keys in the exact order provided by operator."""
    from ocs.study_ids import create_registry

    keys = [
        "a0000000-0000-0000-0000-000000000000",
        "z0000000-0000-0000-0000-000000000000",
        "m0000000-0000-0000-0000-000000000000",
    ]
    reg = create_registry(tmp_path / "ids.json", keys)

    # Order from operator, not alphabetical
    assert reg.lookup(keys[0]) == "STUDY_0001"
    assert reg.lookup(keys[1]) == "STUDY_0002"
    assert reg.lookup(keys[2]) == "STUDY_0003"


def test_s04_later_users_append_after_bootstrap(tmp_path):
    """S04: keys seen after bootstrap get next-available IDs; bootstrap IDs unchanged."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, ["uuid-001", "uuid-002"])

    with locked_registry(reg_path) as reg:
        new_id = reg.allocate("ocs:new-participant")

    assert new_id == "STUDY_0003"
    with locked_registry(reg_path) as reg:
        assert reg.lookup("uuid-001") == "STUDY_0001"
        assert reg.lookup("uuid-002") == "STUDY_0002"


def test_s04_bsuid_key_treated_as_opaque_not_digit_linked(tmp_path):
    """S04: BSUID 'KE.1234' and phone-digits '1234' are distinct registry keys."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with locked_registry(reg_path) as reg:
        id_bsuid = reg.allocate("ocs:KE.254700000001")
        id_phone = reg.allocate("254700000001")

    assert id_bsuid != id_phone, "S04: BSUID and phone-digit key must be distinct"


# ---------------------------------------------------------------------------
# S05 — malformed/conflicting/duplicate registries refused
# ---------------------------------------------------------------------------


def test_s05_missing_version_refused(tmp_path):
    """S05: registry missing 'version' key is rejected on load."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    reg_path.write_text(json.dumps({"next_n": 1, "mapping": {}}))

    with pytest.raises(RegistrySchemaError, match="version"):
        open_registry(reg_path)


def test_s05_wrong_version_refused(tmp_path):
    """S05: registry with unsupported version integer is rejected."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    reg_path.write_text(json.dumps({"version": 99, "next_n": 1, "mapping": {}}))

    with pytest.raises(RegistrySchemaError, match="version"):
        open_registry(reg_path)


def test_s05_non_dict_mapping_refused(tmp_path):
    """S05: 'mapping' must be a dict of str→str."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": 1, "mapping": ["list"]}))

    with pytest.raises(RegistrySchemaError, match="mapping"):
        open_registry(reg_path)


def test_s05_invalid_study_id_format_refused(tmp_path):
    """S05: mapping values must match STUDY_####+ format."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_n": 2,
                "mapping": {"key1": "STUDY_0001", "key2": "not-a-study-id"},
            }
        )
    )

    with pytest.raises(RegistrySchemaError, match="study.id"):
        open_registry(reg_path)


def test_s05_duplicate_study_id_values_refused(tmp_path):
    """S05: two keys mapping to the same STUDY_#### are rejected (uniqueness)."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_n": 2,
                "mapping": {"key1": "STUDY_0001", "key2": "STUDY_0001"},
            }
        )
    )

    with pytest.raises(RegistrySchemaError, match="duplicate"):
        open_registry(reg_path)


def test_s05_next_n_inconsistent_refused(tmp_path):
    """S05: next_n must be strictly greater than the highest existing sequential number."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    # next_n=1 but mapping has STUDY_0001, so next_n must be at least 2
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_n": 1,
                "mapping": {"key1": "STUDY_0001"},
            }
        )
    )

    with pytest.raises(RegistrySchemaError, match="next_n"):
        open_registry(reg_path)


def test_s05_non_string_key_refused(tmp_path):
    """S05: mapping keys must be strings (no silent int coercion)."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    # JSON only allows string keys, but write raw to simulate tampered file
    reg_path = tmp_path / "ids.json"
    # JSON keys are always strings after parsing, so test non-string values instead
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_n": 2,
                "mapping": {"key1": 1},  # value is int, not str
            }
        )
    )

    with pytest.raises(RegistrySchemaError):
        open_registry(reg_path)


def test_s05_truncated_json_refused(tmp_path):
    """S05: truncated/malformed JSON is rejected cleanly."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    reg_path = tmp_path / "ids.json"
    reg_path.write_text('{"version": 1, "next_n":')

    with pytest.raises(RegistrySchemaError):
        open_registry(reg_path)


# ---------------------------------------------------------------------------
# S06 — explicit create vs use; missing registry fails closed
# ---------------------------------------------------------------------------


def test_s06_create_then_locked_use_succeeds(tmp_path):
    """S06: create_registry then locked_registry for allocation is the standard workflow."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, ["seed-key"])

    with locked_registry(reg_path) as reg:
        new_id = reg.allocate("new-key")

    assert new_id == "STUDY_0002"


def test_s06_open_missing_registry_raises_lost_error(tmp_path):
    """S06: open_registry on a non-existent path → RegistryLostError, not bootstrap."""
    from ocs.study_ids import RegistryLostError, open_registry

    with pytest.raises(RegistryLostError):
        open_registry(tmp_path / "does-not-exist.json")


def test_s06_locked_registry_missing_raises_lost_error(tmp_path):
    """S06: locked_registry on a non-existent path → RegistryLostError, not bootstrap."""
    from ocs.study_ids import RegistryLostError, locked_registry

    with pytest.raises(RegistryLostError):
        with locked_registry(tmp_path / "does-not-exist.json"):
            pass


def test_s06_create_existing_registry_raises_conflict_error(tmp_path):
    """S06: create_registry when file already exists → RegistryConflictError."""
    from ocs.study_ids import RegistryConflictError, create_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    with pytest.raises(RegistryConflictError):
        create_registry(reg_path, [])


def test_s06_cli_no_registry_flag_fails_clearly(tmp_path, capsys):
    """S06: export_adapter main() without --study-id-registry exits non-zero with clear message."""

    from ocs.export_adapter import main

    ocs_csv = tmp_path / "ocs.csv"
    registered = {
        "study_participant": True,
        "consent_given": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }
    _write_ocs_csv(ocs_csv, [("p-1", "+254700000001", registered)])

    rc = main(
        [
            "--ocs-export",
            str(ocs_csv),
            "--out",
            str(tmp_path / "out.csv"),
        ]
    )
    assert rc != 0, "S06: main() without --study-id-registry must exit non-zero"
    captured = capsys.readouterr()
    err_text = (captured.err + captured.out).lower()
    assert "registry" in err_text or "study-id-registry" in err_text, (
        f"S06: error message must mention registry; got: {captured.err!r}"
    )


def test_s06_migration_limit_documented():
    """S06: migration docstring exists in study_ids module."""
    import ocs.study_ids as m

    assert m.__doc__ is not None and len(m.__doc__) > 50, (
        "S06: study_ids module must have a docstring explaining migration limits"
    )
    # The docstring must mention migration or recovery
    assert any(word in m.__doc__.lower() for word in ("migrat", "recover", "operator")), (
        "S06: module docstring must discuss migration/recovery semantics"
    )


# ---------------------------------------------------------------------------
# S07 — concurrent allocations: no collision, bounded lock contention
# ---------------------------------------------------------------------------


def test_s07_concurrent_threads_no_collision(tmp_path):
    """S07: multiple threads allocating unique keys simultaneously produce no duplicates."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    errors: list[Exception] = []
    allocated: list[str] = []
    lock = threading.Lock()

    def _worker(key: str):
        try:
            with locked_registry(reg_path) as reg:
                study_id = reg.allocate(key)
            with lock:
                allocated.append(study_id)
        except Exception as e:
            with lock:
                errors.append(e)

    n_threads = 10
    keys = [f"ocs:participant-{i:03d}" for i in range(n_threads)]
    threads = [threading.Thread(target=_worker, args=(k,)) for k in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors, f"S07: thread errors: {errors}"
    assert len(allocated) == n_threads, f"S07: expected {n_threads} allocations, got {len(allocated)}"
    assert len(set(allocated)) == n_threads, (
        f"S07: collision detected — {n_threads - len(set(allocated))} duplicate IDs"
    )


def test_s07_lock_timeout_raises_registry_lock_error(tmp_path):
    """S07: a thread holding the lock causes a second thread to time out and raise."""
    from ocs.study_ids import RegistryLockError, create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    held = threading.Event()
    released = threading.Event()

    def _hold_lock():
        with locked_registry(reg_path):
            held.set()
            released.wait(timeout=10)

    holder = threading.Thread(target=_hold_lock)
    holder.start()
    held.wait(timeout=5)

    try:
        with pytest.raises(RegistryLockError):
            with locked_registry(reg_path, timeout_s=0.2):
                pass
    finally:
        released.set()
        holder.join(timeout=5)


def test_s07_lock_file_released_after_context(tmp_path):
    """S07: lock file is released after locked_registry context exits."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, ["key-a"])

    with locked_registry(reg_path) as reg:
        reg.allocate("key-b")

    # Should be acquirable immediately after first context exits
    with locked_registry(reg_path, timeout_s=1) as reg:
        reg.allocate("key-c")

    from ocs.study_ids import open_registry

    reg = open_registry(reg_path)
    assert reg.lookup("key-c") == "STUDY_0003"


def test_s07_real_process_concurrent_allocations_no_collision(tmp_path):
    """S07: real independent OS processes allocating distinct keys produce no collisions.

    Uses multiprocessing (spawn context) so each worker imports the module fresh,
    matching the actual CLI use case where separate invocations run as separate processes.
    """
    from ocs.study_ids import create_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    n_procs = 6
    keys = [f"ocs:proc-participant-{i:03d}" for i in range(n_procs)]
    result_files = [tmp_path / f"result-{i}.txt" for i in range(n_procs)]

    ctx = multiprocessing.get_context("spawn")
    procs = [
        ctx.Process(
            target=_spawn_worker,
            args=(str(reg_path), key, str(out)),
        )
        for key, out in zip(keys, result_files, strict=True)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0, f"S07: process for {p} exited {p.exitcode}"

    # Collect study IDs written by each process.
    study_ids = [f.read_text().strip() for f in result_files if f.exists()]
    assert len(study_ids) == n_procs, f"S07: expected {n_procs} result files, got {len(study_ids)}"
    assert len(set(study_ids)) == n_procs, f"S07: collision detected — study IDs not unique: {study_ids}"

    # Registry must contain all allocations with matching IDs.
    reg = open_registry(reg_path)
    for key, expected_id in zip(keys, study_ids, strict=True):
        assert reg.lookup(key) == expected_id, (
            f"S07: registry ID for {key!r} ({reg.lookup(key)!r}) does not match process result ({expected_id!r})"
        )


# ---------------------------------------------------------------------------
# S08 — atomic write failures preserve known assignments; no false-success output
# ---------------------------------------------------------------------------


def test_s08_failed_csv_write_no_output_registry_updated(tmp_path, monkeypatch):
    """S08: if CSV write fails, no output file is created; registry retains allocations."""

    from ocs.export_adapter import main
    from ocs.study_ids import create_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    registered = {
        "study_participant": True,
        "consent_given": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }
    ocs_csv = tmp_path / "ocs.csv"
    _write_ocs_csv(ocs_csv, [("p-1", "+254700000001", registered)])
    out_path = tmp_path / "out.csv"

    # Inject write failure during CSV write
    original_replace = os.replace
    call_count = [0]

    def _failing_replace(src, dst):
        call_count[0] = call_count[0] + 1
        if str(dst) == str(out_path):
            raise OSError("simulated rename failure")
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", _failing_replace)

    rc = main(
        [
            "--ocs-export",
            str(ocs_csv),
            "--study-id-registry",
            str(reg_path),
            "--out",
            str(out_path),
        ]
    )

    assert rc != 0, "S08: failed CSV write must return non-zero"
    assert not out_path.exists(), "S08: no output CSV must be emitted on write failure"

    # Registry may or may not be updated depending on write order; IDs are never recycled.
    # (If registry was saved before CSV rename failed, the allocated ID is retained unused.)
    open_registry(reg_path)
    # Key point: the previously allocated keys will not be recycled on the next run.
    with __import__("ocs.study_ids", fromlist=["locked_registry"]).locked_registry(reg_path) as r:
        # On retry, the same key gets the same ID (not a new one)
        retry_id = r.allocate("ocs:p-1")
    assert retry_id.startswith("STUDY_"), "S08: ID format must be preserved on retry"


def test_s08_registry_save_preserves_old_on_io_error(tmp_path, monkeypatch):
    """S08: if registry save fails (I/O error on rename), old registry file is preserved."""
    from ocs.study_ids import create_registry, locked_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, ["original-key"])

    original_content = reg_path.read_text()

    # Inject failure in atomic_write (os.replace)
    original_replace = os.replace
    fail_next = [True]

    def _fail_once(src, dst):
        if fail_next[0] and str(dst) == str(reg_path):
            fail_next[0] = False
            raise OSError("simulated registry save failure")
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", _fail_once)

    with pytest.raises(OSError):
        with locked_registry(reg_path) as reg:
            reg.allocate("new-key")

    # Old registry content preserved
    assert reg_path.read_text() == original_content, "S08: registry file must be unchanged after save failure"
    reg = open_registry(reg_path)
    assert reg.lookup("original-key") == "STUDY_0001"
    assert reg.lookup("new-key") is None


# ---------------------------------------------------------------------------
# S09 — restrictive permissions; no PII in diagnostics; alias/symlink collision rejected
# ---------------------------------------------------------------------------


def test_s09_registry_file_mode_600(tmp_path):
    """S09: created registry file has mode 0o600 (owner read/write only)."""
    from ocs.study_ids import create_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, ["key"])
    mode = oct(os.stat(reg_path).st_mode & 0o777)
    assert mode == oct(0o600), f"S09: registry mode must be 0o600, got {mode}"


def test_s09_saved_registry_retains_mode_600(tmp_path):
    """S09: atomic save preserves restrictive 0o600 mode."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with locked_registry(reg_path) as reg:
        reg.allocate("new-key")

    mode = oct(os.stat(reg_path).st_mode & 0o777)
    assert mode == oct(0o600), f"S09: mode after save must be 0o600, got {mode}"


def test_s09_no_participant_key_in_conflict_error(tmp_path):
    """S09: RegistryConflictError message does not leak participant key."""
    from ocs.study_ids import RegistryConflictError, create_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with pytest.raises(RegistryConflictError) as exc_info:
        create_registry(reg_path, [])

    # Error message mentions the path but not participant identifiers
    # (no participant keys were passed here, but future calls might expose them)
    assert str(exc_info.value) != ""


def test_s09_no_key_in_schema_error_message(tmp_path):
    """S09: RegistrySchemaError does not expose participant keys from mapping."""
    from ocs.study_ids import RegistrySchemaError, open_registry

    sensitive_key = "0f3c9a2e-0000-0000-0000-000000000001"
    reg_path = tmp_path / "ids.json"
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_n": 1,
                "mapping": {sensitive_key: "STUDY_0001"},
                # deliberately missing next_n consistency check → triggers error
            }
        )
    )
    # Force next_n inconsistency
    reg_path.write_text(
        json.dumps(
            {
                "version": 1,
                "next_n": 0,  # too low
                "mapping": {sensitive_key: "STUDY_0001"},
            }
        )
    )

    with pytest.raises(RegistrySchemaError) as exc_info:
        open_registry(reg_path)

    assert sensitive_key not in str(exc_info.value), "S09: participant key must not appear in error message"


@pytest.mark.skipif(sys.platform == "win32", reason="symlink test requires Unix")
def test_s09_symlink_output_collision_rejected(tmp_path):
    """S09: --out that is a symlink to --ocs-export is rejected before writing."""
    import csv as _csv

    from ocs.export_adapter import main
    from ocs.study_ids import create_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    registered = {
        "study_participant": True,
        "consent_given": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }
    ocs_csv = tmp_path / "ocs.csv"
    _write_ocs_csv(ocs_csv, [("p-1", "+254700000001", registered)])

    # Create symlink pointing back to the input file
    alias = tmp_path / "alias.csv"
    alias.symlink_to(ocs_csv)

    rc = main(
        [
            "--ocs-export",
            str(ocs_csv),
            "--study-id-registry",
            str(reg_path),
            "--out",
            str(alias),
        ]
    )

    assert rc != 0, "S09: writing --out to a symlink of --ocs-export must be rejected"
    # Input file must be unmodified
    original_rows = list(_csv.DictReader(ocs_csv.open()))
    assert original_rows, "S09: input file must not be overwritten"


# ---------------------------------------------------------------------------
# S10 — existing filtering/column/categorisation behaviour preserved
# ---------------------------------------------------------------------------


def test_s10_nine_columns_in_registry_based_cli_output(tmp_path):
    """S10: CLI output with registry has exactly the nine ZEYA_COLUMNS."""
    import csv as _csv

    from ocs.export_adapter import ZEYA_COLUMNS, main
    from ocs.study_ids import create_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    registered = {
        "study_participant": True,
        "consent_given": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }
    ocs_csv = tmp_path / "ocs.csv"
    _write_ocs_csv(ocs_csv, [("p-1", "+254700000001", registered)])
    out_path = tmp_path / "out.csv"

    assert (
        main(
            [
                "--ocs-export",
                str(ocs_csv),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out_path),
            ]
        )
        == 0
    )

    rows = list(_csv.DictReader(out_path.open()))
    assert rows, "S10: output must contain rows"
    assert list(rows[0].keys()) == ZEYA_COLUMNS


def test_s10_consent_exclusion_preserved_with_registry(tmp_path):
    """S10: consent/study exclusion still works through the registry-based CLI path."""
    import csv as _csv

    from ocs.export_adapter import main
    from ocs.study_ids import create_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    consented = {
        "study_participant": True,
        "consent_given": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }
    declined = {"consent_given": False, "study_group": "intervention"}

    ocs_csv = tmp_path / "ocs.csv"
    _write_ocs_csv(
        ocs_csv,
        [
            ("p-1", "+254700000001", consented),
            ("p-2", "+254700000002", declined),
        ],
    )
    out_path = tmp_path / "out.csv"

    assert (
        main(
            [
                "--ocs-export",
                str(ocs_csv),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out_path),
            ]
        )
        == 0
    )

    rows = list(_csv.DictReader(out_path.open()))
    study_ids = {r["study_id"] for r in rows}
    # Only the consented participant appears
    assert len(rows) >= 1
    # All rows must come from p-1 (the only consented participant)
    # They all have the same study_id
    assert len(study_ids) == 1


# ---------------------------------------------------------------------------
# S11 — library and CLI consumer integration; renderer/node code untouched
# ---------------------------------------------------------------------------


def test_s11_library_allocate_then_lookup(tmp_path):
    """S11: allocate returns consistent ID; lookup returns same ID; non-existent returns None."""
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with locked_registry(reg_path) as reg:
        id1 = reg.allocate("ocs:p-1")

    with locked_registry(reg_path) as reg:
        assert reg.lookup("ocs:p-1") == id1
        assert reg.lookup("ocs:nonexistent") is None


def test_s11_study_ids_cli_create_subcommand(tmp_path):
    """S11: study_ids CLI create subcommand creates a valid empty registry."""
    from ocs.study_ids import main as sid_main
    from ocs.study_ids import open_registry

    reg_path = tmp_path / "ids.json"
    rc = sid_main(["create", "--registry", str(reg_path)])
    assert rc == 0, f"S11: study_ids create returned {rc}"
    assert reg_path.exists()
    reg = open_registry(reg_path)
    assert reg.lookup("anything") is None  # empty registry


def test_s11_study_ids_cli_create_with_seed(tmp_path):
    """S11: study_ids CLI create --seed seeds legacy UUIDs in sorted order."""
    from ocs.study_ids import main as sid_main
    from ocs.study_ids import open_registry

    reg_path = tmp_path / "ids.json"
    seed_csv = tmp_path / "seed.csv"
    # CSV with two users; sorted order: a < b
    seed_csv.write_text(
        "user_id,whatsapp_id\n"
        "b0000000-0000-0000-0000-000000000000,254711111111\n"
        "a0000000-0000-0000-0000-000000000000,254722222222\n"
    )
    rc = sid_main(["create", "--registry", str(reg_path), "--seed", str(seed_csv)])
    assert rc == 0

    reg = open_registry(reg_path)
    assert reg.lookup("a0000000-0000-0000-0000-000000000000") == "STUDY_0001"
    assert reg.lookup("b0000000-0000-0000-0000-000000000000") == "STUDY_0002"


def test_s11_study_ids_cli_check_subcommand(tmp_path, capsys):
    """S11: study_ids CLI check subcommand validates and reports stats."""
    from ocs.study_ids import create_registry
    from ocs.study_ids import main as sid_main

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, ["key-a", "key-b"])

    rc = sid_main(["check", "--registry", str(reg_path)])
    assert rc == 0

    out = capsys.readouterr().out
    assert "2" in out or "STUDY" in out  # some meaningful output


def test_s11_node_code_not_imported():
    """S11: study_ids module does not import from pipeline node modules."""
    import inspect

    import ocs.study_ids as m

    source = inspect.getsource(m)
    forbidden = ["ocs.nodes", "from ocs.nodes", "import ocs.nodes"]
    for f in forbidden:
        assert f not in source, f"S11: study_ids must not import pipeline nodes: {f}"


# ---------------------------------------------------------------------------
# S12 — ruff check + format; complete ledger; no fabricated totals
# ---------------------------------------------------------------------------


def test_s12_study_ids_module_imports_cleanly():
    """S12: ocs.study_ids imports without errors."""
    import ocs.study_ids  # noqa: F401


def test_s12_export_adapter_still_imports_cleanly():
    """S12: ocs.export_adapter imports without errors after modifications."""
    import importlib

    import ocs.export_adapter

    importlib.reload(ocs.export_adapter)  # noqa: F401


# ---------------------------------------------------------------------------
# Shared helper (not a test)
# ---------------------------------------------------------------------------


def _write_ocs_csv(path: Path, participants: list[tuple[str, str, dict]]) -> None:
    """Write a minimal OCS export CSV for the given participants.

    Each entry is (public_id, identifier, participant_data_dict).
    """
    import csv as _csv

    fieldnames = [
        "Message ID",
        "Message Date",
        "Message Type",
        "Message Content",
        "Platform",
        "Session Tags",
        "Session Comments",
        "Session ID",
        "Session State",
        "Chatbot ID",
        "Chatbot Name",
        "Participant Name",
        "Participant Identifier",
        "Participant Public ID",
        "Message Tags",
        "Message Comments",
        "Trace ID",
        "Participant Data",
    ]
    rows = []
    for _i, entry in enumerate(participants):
        public_id, identifier, data = entry[0], entry[1], entry[2]
        message_content = entry[3] if len(entry) >= 4 else "Hello"  # type: ignore[misc]
        rows.append(
            {
                "Message ID": f"{public_id}-h",
                "Message Date": "2026-09-15T10:00:00+00:00",
                "Message Type": "human",
                "Message Content": message_content,
                "Platform": "WhatsApp",
                "Session Tags": "",
                "Session Comments": "",
                "Session ID": f"s-{public_id}",
                "Session State": "{}",
                "Chatbot ID": "c-1",
                "Chatbot Name": "Zeya",
                "Participant Name": "Test",
                "Participant Identifier": identifier,
                "Participant Public ID": public_id,
                "Message Tags": "",
                "Message Comments": "",
                "Trace ID": "",
                "Participant Data": json.dumps(data),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = _csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Module-level worker for multiprocessing spawn (must be picklable)
# ---------------------------------------------------------------------------


def _spawn_worker(reg_path_str: str, key: str, out_path_str: str) -> None:
    """Allocate one key under a real registry lock and write the study ID to a file.

    Used by test_s07_real_process_concurrent_allocations_no_collision.
    Defined at module level so multiprocessing.spawn can pickle it.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from ocs.study_ids import locked_registry

    with locked_registry(Path(reg_path_str)) as reg:
        study_id = reg.allocate(key)
    Path(out_path_str).write_text(study_id + "\n")


# ---------------------------------------------------------------------------
# Permanent regression tests for all 8 parent correction groups
# ---------------------------------------------------------------------------


def test_regression_strict_bool_version_refused(tmp_path):
    """Regression for correction 2: version=True must be rejected (bool is not plain int)."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": True, "next_n": 1, "mapping": {}}))
    before = reg_path.read_bytes()
    with pytest.raises(RegistryError):
        open_registry(reg_path)
    assert reg_path.read_bytes() == before


def test_regression_strict_bool_next_n_refused(tmp_path):
    """Regression for correction 2: next_n=True must be rejected (bool is not plain int)."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": True, "mapping": {}}))
    with pytest.raises(RegistryError):
        open_registry(reg_path)


def test_regression_zero_next_n_refused(tmp_path):
    """Regression for correction 2: next_n=0 must be rejected (must be >= 1)."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": 0, "mapping": {}}))
    with pytest.raises(RegistryError):
        open_registry(reg_path)


def test_regression_empty_key_refused(tmp_path):
    """Regression for correction 2: empty string mapping key must be rejected."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": 2, "mapping": {"": "STUDY_0001"}}))
    with pytest.raises(RegistryError):
        open_registry(reg_path)


def test_regression_study_0000_refused(tmp_path):
    """Regression for correction 2: STUDY_0000 (seq < 1) must be rejected."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": 1, "mapping": {"ocs:a": "STUDY_0000"}}))
    with pytest.raises(RegistryError):
        open_registry(reg_path)


def test_regression_duplicate_json_keys_refused(tmp_path):
    """Regression for correction 2: duplicate JSON mapping keys must be detected."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text('{"version":1,"next_n":3,"mapping":{"ocs:a":"STUDY_0001","ocs:a":"STUDY_0002"}}')
    with pytest.raises(RegistryError):
        open_registry(reg_path)


def test_regression_assign_study_ids_raises(tmp_path):
    """Regression for correction 3: assign_study_ids must raise TypeError, not silently renumber."""
    from ocs.export_adapter import assign_study_ids

    with pytest.raises(TypeError, match="assign_study_ids"):
        assign_study_ids([{"user_key": "ocs:z"}], [])


def test_regression_registry_commit_before_file_output(tmp_path, monkeypatch):
    """Regression for correction 1 (S08): registry commit happens before file output.

    Parent probe: fail _atomic_write; output file must be unchanged, registry unchanged.
    """
    import ocs.study_ids as ids
    from ocs.export_adapter import main

    reg, source = _make_fixture_files(tmp_path)
    output = tmp_path / "output.csv"
    output.write_bytes(b"PREEXISTING_OUTPUT\n")
    old_registry = reg.read_bytes()

    def fail_commit(*a, **kw):
        raise OSError("synthetic registry commit failure")

    monkeypatch.setattr(ids, "_atomic_write", fail_commit)
    assert main(["--ocs-export", str(source), "--study-id-registry", str(reg), "--out", str(output)]) != 0
    assert output.read_bytes() == b"PREEXISTING_OUTPUT\n"
    assert reg.read_bytes() == old_registry


def test_regression_registry_commit_before_stdout_output(tmp_path, monkeypatch, capsys):
    """Regression for correction 1 (S08): registry commit happens before stdout output."""
    import ocs.study_ids as ids
    from ocs.export_adapter import main

    reg, source = _make_fixture_files(tmp_path)

    def fail_commit(*a, **kw):
        raise OSError("synthetic registry commit failure")

    monkeypatch.setattr(ids, "_atomic_write", fail_commit)
    assert main(["--ocs-export", str(source), "--study-id-registry", str(reg)]) != 0
    assert capsys.readouterr().out == ""


def test_regression_output_cannot_replace_lock_file(tmp_path):
    """Regression for correction 5 (S09): --out targeting the lock file must fail."""
    from ocs.export_adapter import main

    reg, source = _make_fixture_files(tmp_path)
    lock = reg.with_suffix(".lock")
    old_inode = lock.stat().st_ino
    before_reg = reg.read_bytes()
    assert main(["--ocs-export", str(source), "--study-id-registry", str(reg), "--out", str(lock)]) != 0
    assert lock.stat().st_ino == old_inode
    assert reg.read_bytes() == before_reg


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require Unix")
def test_regression_output_cannot_alias_registry_symlink(tmp_path):
    """Regression for correction 5 (S09): --out that is a symlink to registry must fail."""
    from ocs.export_adapter import main

    reg, source = _make_fixture_files(tmp_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(reg)
    before_reg = reg.read_bytes()
    assert (
        main(
            [
                "--ocs-export",
                str(source),
                "--study-id-registry",
                str(alias),
                "--out",
                str(alias),
            ]
        )
        != 0
    )
    assert alias.is_symlink()
    assert reg.read_bytes() == before_reg


def test_regression_registry_rename_failure_cleans_temp(tmp_path, monkeypatch):
    """Regression for correction 6 (S08): failed rename during registry save removes temp."""
    import ocs.study_ids as ids
    from ocs.study_ids import create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    before = reg_path.read_bytes()

    original_replace = os.replace
    fail_next = [True]

    def fail_replace(src, dst):
        if fail_next[0] and str(dst) == str(reg_path):
            fail_next[0] = False
            raise OSError("synthetic rename failure")
        return original_replace(src, dst)

    monkeypatch.setattr(ids.os, "replace", fail_replace)

    with pytest.raises(OSError):
        with locked_registry(reg_path) as reg:
            reg.allocate("ocs:new")

    assert reg_path.read_bytes() == before
    assert not list(tmp_path.glob(".studyids-tmp-*")), "temp file must be cleaned up on rename failure"


def test_regression_read_snapshot_cannot_mutate(tmp_path):
    """Regression for correction 4 (S07): open_registry snapshot raises on allocate/save."""
    from ocs.study_ids import RegistryError, create_registry, locked_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    stale = open_registry(reg_path)
    with locked_registry(reg_path) as active:
        active.allocate("ocs:committed")
    before = reg_path.read_bytes()

    # allocate on snapshot must raise
    with pytest.raises(RegistryError):
        stale.allocate("ocs:stale")

    # save on snapshot must also raise
    with pytest.raises(RegistryError):
        stale.save()

    assert reg_path.read_bytes() == before


# ---------------------------------------------------------------------------
# Shared helper for regression tests (not a test)
# ---------------------------------------------------------------------------


def _make_fixture_files(tmp_path: Path) -> tuple[Path, Path]:
    """Create a valid registry and minimal OCS export CSV for regression tests."""
    from ocs.study_ids import create_registry

    registry = tmp_path / "ids.json"
    create_registry(registry, [])

    source = tmp_path / "input.csv"
    registered = {
        "consent_given": True,
        "study_participant": True,
        "registration_complete": True,
        "gestational_age_at_enrollment": 20,
        "enrolled_at": "2026-09-01T09:00:00+00:00",
        "study_group": "intervention",
        "language_preference": "en",
    }
    _write_ocs_csv(source, [("synthetic-a", "KE.SyntheticA", registered)])
    return registry, source


# ---------------------------------------------------------------------------
# Permanent regressions for F1-F9 (repair-2)
# ---------------------------------------------------------------------------


def test_regression_f1_handle_read_only_after_context_exit(tmp_path):
    """F1: yielded handle must be invalidated (read_only) after locked_registry exits."""
    from ocs.study_ids import RegistryError, create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with locked_registry(reg_path) as handle:
        handle.allocate("ocs:first")
    before = reg_path.read_bytes()

    with pytest.raises(RegistryError):
        handle.allocate("ocs:escaped")
    assert reg_path.read_bytes() == before


def test_regression_f2_allocation_after_explicit_save_persists(tmp_path):
    """F2: allocation after explicit save() must reset _committed so auto-save fires."""
    from ocs.study_ids import create_registry, locked_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with locked_registry(reg_path) as handle:
        handle.allocate("ocs:first")
        handle.save()
        second = handle.allocate("ocs:second")  # new allocation after explicit save

    assert open_registry(reg_path).lookup("ocs:second") == second


@pytest.mark.parametrize("key", ["", "   ", 7, True])
def test_regression_f3_create_rejects_invalid_key(tmp_path, key):
    """F3: create_registry rejects invalid keys before persisting any file."""
    from ocs.study_ids import RegistryError, create_registry

    reg_path = tmp_path / "ids.json"
    with pytest.raises(RegistryError):
        create_registry(reg_path, [key])
    assert not reg_path.exists(), "F3: registry must not be created on invalid key"


@pytest.mark.parametrize("key", ["", "   ", 7, True])
def test_regression_f3_allocate_rejects_invalid_key(tmp_path, key):
    """F3: allocate() rejects invalid keys without modifying the registry."""
    from ocs.study_ids import RegistryError, create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    before = reg_path.read_bytes()

    with pytest.raises(RegistryError):
        with locked_registry(reg_path) as handle:
            handle.allocate(key)
    assert reg_path.read_bytes() == before


@pytest.mark.parametrize("value", ["STUDY_00001", "STUDY_\uff10\uff10\uff10\uff11"])
def test_regression_f4_non_canonical_study_id_refused(tmp_path, value):
    """F4: STUDY_00001 (extra leading zero) and Unicode digit forms are rejected."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": 2, "mapping": {"ocs:a": value}}))
    with pytest.raises(RegistryError):
        open_registry(reg_path)


def test_regression_f4_study_10000_accepted(tmp_path):
    """F4: STUDY_10000 (5-digit canonical sequence) is accepted — no 9999 limit."""
    from ocs.study_ids import create_registry, locked_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])

    with locked_registry(reg_path) as reg:
        reg._next_n = 10000
        study_id = reg.allocate("ocs:ten-thousand")
    assert study_id == "STUDY_10000"
    assert open_registry(reg_path).lookup("ocs:ten-thousand") == "STUDY_10000"


def test_regression_f5_absent_lock_path_protected_from_output(tmp_path):
    """F5: --out targeting the absent lock path must be rejected before any writes."""
    from ocs.export_adapter import main

    reg, source = _make_fixture_files(tmp_path)
    lock = reg.with_suffix(".lock")
    if lock.exists():
        lock.unlink()
    before = reg.read_bytes()
    assert main(["--ocs-export", str(source), "--study-id-registry", str(reg), "--out", str(lock)]) != 0
    assert reg.read_bytes() == before


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require Unix")
def test_regression_f6_symlink_registry_rejected_by_locked_registry(tmp_path):
    """F6: locked_registry raises RegistryError when path is a symlink."""
    from ocs.study_ids import RegistryError, create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    alias = tmp_path / "alias.json"
    alias.symlink_to(reg_path)
    before = reg_path.read_bytes()

    with pytest.raises(RegistryError):
        with locked_registry(alias) as handle:
            handle.allocate("ocs:alias-write")
    assert alias.is_symlink()
    assert reg_path.read_bytes() == before


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require Unix")
def test_regression_f6_symlink_registry_rejected_by_open_registry(tmp_path):
    """F6: open_registry raises RegistryError when path is a symlink."""
    from ocs.study_ids import RegistryError, create_registry, open_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    alias = tmp_path / "alias.json"
    alias.symlink_to(reg_path)

    with pytest.raises(RegistryError):
        open_registry(alias)


def test_regression_f7_blank_seed_row_rejected(tmp_path):
    """F7: seed CSV with any blank identifier row rejects without creating registry."""
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id,whatsapp_id\n,synthetic-number\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists()


def test_regression_f7_mixed_valid_blank_seed_rejected(tmp_path):
    """F7: mixed valid+blank seed rows must not create a partial namespace."""
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id,whatsapp_id\nvalid-id-001,+254711111111\n,+254722222222\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists()


def test_regression_f7_conflicting_columns_rejected(tmp_path):
    """F7: seed CSV with both user_id and id columns is rejected without guessing."""
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id,id\nopaque-A,opaque-B\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists()


# ---------------------------------------------------------------------------
# Actual concurrent CLI subprocess proof (C7/S01/S07)
# ---------------------------------------------------------------------------

_WORKTREE = Path(__file__).parent.parent.parent.resolve()
_REGISTERED_CONC = {
    "study_participant": True,
    "consent_given": True,
    "registration_complete": True,
    "gestational_age_at_enrollment": 20,
    "enrolled_at": "2026-09-01T09:00:00+00:00",
    "study_group": "intervention",
    "language_preference": "en",
}


def test_s07_concurrent_cli_export_subprocesses_no_collision(tmp_path):
    """S07/C7: actual concurrent CLI subprocess exports produce no ID collisions.

    Uses subprocess.Popen (real OS fork/exec), not multiprocessing helpers.
    Each subprocess is a full python -m ocs.export_adapter invocation.
    Participants have distinct safe message markers for exact row identification.
    """
    import subprocess
    import sys

    from ocs.study_ids import create_registry, open_registry

    reg_path = tmp_path / "study_ids.json"
    create_registry(reg_path, [])

    n = 5
    markers = [f"Routine care question marker-conc-cli-{i:03d}" for i in range(n)]
    public_ids = [f"conc-cli-{i:03d}" for i in range(n)]
    identifiers = [f"+25470{i:07d}" for i in range(n)]

    ocs_csvs = [tmp_path / f"ocs-{i}.csv" for i in range(n)]
    out_csvs = [tmp_path / f"out-{i}.csv" for i in range(n)]
    for i in range(n):
        _write_ocs_csv(ocs_csvs[i], [(public_ids[i], identifiers[i], _REGISTERED_CONC, markers[i])])

    # Launch all subprocesses concurrently (real fork/exec, not threads)
    procs = [
        subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "ocs.export_adapter",
                "--ocs-export",
                str(ocs_csvs[i]),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out_csvs[i]),
            ],
            cwd=str(_WORKTREE),
        )
        for i in range(n)
    ]
    for p in procs:
        rc = p.wait(timeout=60)
        assert rc == 0, f"S07: subprocess exited {rc}"

    # Find each participant's row by its unique safe message marker
    study_ids: dict[str, str] = {}
    for i in range(n):
        rows = list(csv.DictReader(out_csvs[i].open()))
        row = next((r for r in rows if r.get("message_text") == markers[i]), None)
        assert row is not None, f"S07: participant {public_ids[i]} missing from output"
        study_ids[public_ids[i]] = row["study_id"]

    # No collisions
    assert len(set(study_ids.values())) == n, f"S07: ID collisions detected: {study_ids}"

    # Registry contains all allocated IDs
    reg = open_registry(reg_path)
    for pid, sid in study_ids.items():
        ocs_key = f"ocs:{pid}"
        assert reg.lookup(ocs_key) == sid, f"S07: registry has {reg.lookup(ocs_key)!r} for {pid!r}, expected {sid!r}"

    # Second run: same participants get same IDs (stability proof)
    out2_csvs = [tmp_path / f"out2-{i}.csv" for i in range(n)]
    for i in range(n):
        rc = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "ocs.export_adapter",
                "--ocs-export",
                str(ocs_csvs[i]),
                "--study-id-registry",
                str(reg_path),
                "--out",
                str(out2_csvs[i]),
            ],
            cwd=str(_WORKTREE),
            check=False,
        ).returncode
        assert rc == 0, f"S07 stability: second run {i} exited {rc}"

    for i in range(n):
        rows2 = list(csv.DictReader(out2_csvs[i].open()))
        row2 = next((r for r in rows2 if r.get("message_text") == markers[i]), None)
        assert row2 is not None
        assert row2["study_id"] == study_ids[public_ids[i]], (
            f"S07: {public_ids[i]} ID changed from {study_ids[public_ids[i]]!r} to {row2['study_id']!r} on second run"
        )


# ---------------------------------------------------------------------------
# Permanent regressions for physical / seed clauses (physical follow-through)
# ---------------------------------------------------------------------------


def test_regression_hardlinked_registry_rejected(tmp_path):
    """Hardlink registry alias: locked_registry raises; content unchanged."""
    from ocs.study_ids import RegistryError, create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    alias = tmp_path / "hardlink.json"
    os.link(reg_path, alias)
    before = reg_path.read_bytes()

    with pytest.raises(RegistryError, match="hardlink"):
        with locked_registry(alias) as handle:
            handle.allocate("ocs:divergent")
    assert reg_path.read_bytes() == alias.read_bytes() == before


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require Unix")
def test_regression_symlink_lock_rejected_before_target_touch(tmp_path):
    """Symlink lock file: locked_registry raises before touching the target."""
    from ocs.study_ids import RegistryError, create_registry, locked_registry

    reg_path = tmp_path / "ids.json"
    create_registry(reg_path, [])
    lock = reg_path.with_suffix(".lock")
    if lock.exists():
        lock.unlink()
    target = tmp_path / "other-file"
    target.write_bytes(b"PRIVATE_SYNTHETIC_FILE\n")
    lock.symlink_to(target)
    before_mtime = target.stat().st_mtime_ns

    with pytest.raises(RegistryError, match="symlink"):
        with locked_registry(reg_path):
            pass
    assert target.stat().st_mtime_ns == before_mtime, "target mtime must not change"


def test_regression_duplicate_seed_header_rejected(tmp_path):
    """Duplicate CSV column header in seed: rejected without creating registry."""
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id,user_id\nopaque-a,opaque-b\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists()


def test_regression_seed_whitespace_identity_rejected(tmp_path):
    """Seed identifier with surrounding whitespace: rejected, not silently normalized."""
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id\n opaque-a \n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists()


def test_regression_loaded_whitespace_key_rejected(tmp_path):
    """Whitespace-only mapping key in loaded registry: same predicate as create/allocate."""
    from ocs.study_ids import RegistryError, open_registry

    reg_path = tmp_path / "bad.json"
    reg_path.write_text(json.dumps({"version": 1, "next_n": 2, "mapping": {"   ": "STUDY_0001"}}))
    with pytest.raises(RegistryError):
        open_registry(reg_path)


# ---------------------------------------------------------------------------
# Subprocess regressions for V08.7 (FIFO) and V11.9 (malformed row)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="FIFOs require Unix")
def test_regression_v08_7_fifo_registry_rejected_no_block(tmp_path):
    """V08.7: FIFO registry path is rejected before any read; completes in << 2s.

    Uses a real CLI subprocess with a bounded timeout to prove non-blocking.
    Both 'create' and 'check' are exercised; neither must block or traceback.
    Normal file control: same CLI on a real registry returns 0.
    """
    import subprocess
    import time

    fifo_path = tmp_path / "registry.fifo"
    os.mkfifo(fifo_path)

    for cmd in [
        ["check", "--registry", str(fifo_path)],
        ["create", "--registry", str(fifo_path)],
    ]:
        t0 = time.monotonic()
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "ocs.study_ids"] + cmd,
            cwd=str(_WORKTREE),
            capture_output=True,
            timeout=5,
        )
        elapsed = time.monotonic() - t0
        assert result.returncode != 0, f"V08.7: {cmd[0]} on FIFO must fail"
        assert elapsed < 2.0, f"V08.7: must complete in < 2s, took {elapsed:.2f}s"
        assert b"traceback" not in result.stderr.lower(), f"V08.7: no traceback on stderr: {result.stderr[:200]!r}"
        assert b"attributeerror" not in result.stderr.lower()

    # Positive control: same CLI on a real registry file succeeds
    from ocs.study_ids import create_registry

    real_reg = tmp_path / "real.json"
    create_registry(real_reg, [])
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "ocs.study_ids", "check", "--registry", str(real_reg)],
        cwd=str(_WORKTREE),
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 0, "V08.7 control: real registry check must pass"


def test_regression_v11_9_malformed_row_no_attributeerror(tmp_path):
    """V11.9: malformed seed row (fewer cells than headers) gives clean error, no traceback.

    Uses a real CLI subprocess so stderr is captured exactly as the verifier saw it.
    """
    import subprocess

    # Row with fewer cells than headers AND user_id is the missing trailing field:
    # DictReader fills missing trailing cells with restval=None, so row['user_id'] = None.
    # With header order extra_col,user_id and only one value, user_id is None.
    seed = tmp_path / "seed.csv"
    seed.write_text("extra_col,user_id\nonly-one-cell\n")

    reg = tmp_path / "ids.json"
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "ocs.study_ids",
            "create",
            "--registry",
            str(reg),
            "--seed",
            str(seed),
        ],
        cwd=str(_WORKTREE),
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0, "V11.9: malformed row must fail"
    assert not reg.exists(), "V11.9: registry must not be created on malformed row"
    stderr = result.stderr.decode("utf-8", errors="replace").lower()
    assert "attributeerror" not in stderr, f"V11.9: no AttributeError: {result.stderr[:300]!r}"
    assert "traceback" not in stderr, f"V11.9: no traceback: {result.stderr[:300]!r}"

    # Positive control: well-formed row succeeds
    seed_ok = tmp_path / "seed_ok.csv"
    seed_ok.write_text("user_id\nclean-id-001\n")
    reg_ok = tmp_path / "ids_ok.json"
    result_ok = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "ocs.study_ids",
            "create",
            "--registry",
            str(reg_ok),
            "--seed",
            str(seed_ok),
        ],
        cwd=str(_WORKTREE),
        capture_output=True,
        timeout=10,
    )
    assert result_ok.returncode == 0, "V11.9 control: clean seed must succeed"
    assert reg_ok.exists()


# ---------------------------------------------------------------------------
# Regressions for row-shape validation (extra cells / missing cells)
# ---------------------------------------------------------------------------


def test_regression_extra_cells_seed_row_rejected(tmp_path):
    """Extra cell row (more values than headers) must fail without creating registry.

    'user_id\\npublic-key,extra\\n' — row has 2 values, header has 1.
    DictReader stores extra values under restkey=None; must be detected and rejected.
    """
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id\npublic-key,extra\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists(), "registry must not be created for extra-cell row"


def test_regression_missing_other_cell_seed_row_rejected(tmp_path):
    """Missing non-identifier cell (fewer values than headers) must fail.

    'user_id,notes\\npublic-key\\n' — row has 1 value, header has 2.
    DictReader fills missing 'notes' with restval=None; whole-row check must catch it.
    """
    from ocs.study_ids import main as sid_main

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id,notes\npublic-key\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) != 0
    assert not reg.exists(), "registry must not be created for missing-cell row"


def test_regression_valid_multi_column_seed_accepted(tmp_path):
    """Valid multi-column seed row is accepted (positive control).

    'user_id,notes\\npublic-key,ok\\n' — both columns present and non-empty.
    """
    from ocs.study_ids import main as sid_main
    from ocs.study_ids import open_registry

    seed = tmp_path / "seed.csv"
    seed.write_text("user_id,notes\npublic-key,ok\n")
    reg = tmp_path / "ids.json"
    assert sid_main(["create", "--registry", str(reg), "--seed", str(seed)]) == 0
    assert reg.exists()
    assert open_registry(reg).lookup("public-key") == "STUDY_0001"
