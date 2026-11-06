import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pocket_tasks

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".artifacts"


class PocketTasksTests(unittest.TestCase):
    def setUp(self):
        ARTIFACTS.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="test-", dir=ARTIFACTS)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.store = self.folder / "tasks.json"

    def command(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                code = pocket_tasks.main(["--store", str(self.store), *arguments])
            except SystemExit as error:
                code = error.code
        return code, output.getvalue(), errors.getvalue()

    def write_state(self, state):
        self.store.write_text(json.dumps(state), encoding="utf-8")

    @staticmethod
    def valid_state():
        return {
            "version": 1,
            "next_id": 2,
            "tasks": [{"id": 1, "title": "Existing task", "completed": False}],
        }

    def test_listing_missing_store_does_not_create_it(self):
        self.assertEqual(self.command("list"), (0, "No tasks.\n", ""))
        self.assertFalse(self.store.exists())

    def test_add_persists_trimmed_title_and_uncompleted_task(self):
        self.assertEqual(self.command("add", "  First task  "), (0, "Added task 1.\n", ""))
        self.assertEqual(
            json.loads(self.store.read_text()),
            {
                "version": 1,
                "next_id": 2,
                "tasks": [{"id": 1, "title": "First task", "completed": False}],
            },
        )

    def test_two_adds_keep_stable_ids_order_and_unicode(self):
        self.assertEqual(self.command("add", "Plan"), (0, "Added task 1.\n", ""))
        self.assertEqual(self.command("add", "Перевірити"), (0, "Added task 2.\n", ""))
        self.assertEqual(self.command("list"), (0, "1 [ ] Plan\n2 [ ] Перевірити\n", ""))
        self.assertEqual(json.loads(self.store.read_text())["next_id"], 3)

    def test_blank_titles_preserve_existing_store(self):
        for title in ("", " \t\n "):
            with self.subTest(title=title):
                self.write_state(self.valid_state())
                before = self.store.read_bytes()
                code, output, errors = self.command("add", title)
                self.assertEqual((code, output), (2, ""))
                self.assertIn("blank", errors)
                self.assertEqual(self.store.read_bytes(), before)

    def test_blank_title_does_not_create_missing_store(self):
        self.assertEqual(self.command("add", " ")[0], 2)
        self.assertFalse(self.store.exists())
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_completed_tasks_and_id_gaps_are_preserved(self):
        state = self.valid_state()
        state["tasks"][0]["completed"] = True
        state["next_id"] = 8
        self.write_state(state)
        self.assertEqual(self.command("add", "Next")[0], 0)
        saved = json.loads(self.store.read_text())
        self.assertEqual(saved["tasks"][0], state["tasks"][0])
        self.assertEqual(saved["tasks"][1], {"id": 8, "title": "Next", "completed": False})
        self.assertEqual(saved["next_id"], 9)
        self.assertEqual(self.command("list"), (0, "1 [x] Existing task\n8 [ ] Next\n", ""))

    def test_invalid_schemas_fail_without_changing_bytes(self):
        invalid = [None, [], {}, {**self.valid_state(), "extra": 1}]
        for field, values in {
            "version": (True, 1.0, 2),
            "next_id": (True, 2.0, 0, 1),
            "tasks": ({}, None),
        }.items():
            for value in values:
                invalid.append({**self.valid_state(), field: value})
        for field, values in {
            "id": (True, 1.0, 0, -1),
            "title": (None, "", " \t"),
            "completed": (None, 0, 1, "false"),
        }.items():
            for value in values:
                state = copy.deepcopy(self.valid_state())
                state["tasks"][0][field] = value
                invalid.append(state)
        missing = self.valid_state()
        del missing["tasks"][0]["completed"]
        invalid.append(missing)
        extra = self.valid_state()
        extra["tasks"][0]["extra"] = "unexpected"
        invalid.append(extra)
        duplicate = self.valid_state()
        duplicate["tasks"].append(dict(duplicate["tasks"][0]))
        invalid.append(duplicate)
        for state in invalid:
            for command in (("list",), ("add", "New")):
                with self.subTest(state=state, command=command):
                    self.write_state(state)
                    before = self.store.read_bytes()
                    code, output, errors = self.command(*command)
                    self.assertEqual((code, output), (2, ""))
                    self.assertTrue(errors.startswith("Error:"))
                    self.assertEqual(self.store.read_bytes(), before)

    def test_non_strict_json_fails_without_changing_bytes(self):
        documents = [
            b"{",
            b'{"version":1,"version":1,"next_id":1,"tasks":[]}',
            b'{"version":1,"next_id":2,"tasks":[{"id":1,"id":1,"title":"x","completed":false}]}',
            b'{"version":1,"next_id":NaN,"tasks":[]}',
            b'{"version":1,"next_id":Infinity,"tasks":[]}',
            b'{"version":1,"next_id":-Infinity,"tasks":[]}',
            b"\xff",
        ]
        for content in documents:
            for command in (("list",), ("add", "New")):
                with self.subTest(content=content, command=command):
                    self.store.write_bytes(content)
                    code, output, errors = self.command(*command)
                    self.assertEqual((code, output), (2, ""))
                    self.assertTrue(errors.startswith("Error:"))
                    self.assertEqual(self.store.read_bytes(), content)

    def test_atomic_replacement_uses_a_closed_sibling_temporary(self):
        self.write_state(self.valid_state())
        before = self.store.read_bytes()
        replace = os.replace

        def observe(source, destination):
            self.assertEqual(Path(source).parent, self.store.parent)
            self.assertEqual(Path(destination), self.store)
            self.assertEqual(self.store.read_bytes(), before)
            self.assertEqual(json.loads(Path(source).read_text())["next_id"], 3)
            replace(source, destination)

        with mock.patch.object(pocket_tasks.os, "replace", side_effect=observe) as operation:
            self.assertEqual(self.command("add", "Second")[0], 0)
        operation.assert_called_once()
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_failed_replacement_preserves_old_bytes_and_cleans_temporary(self):
        self.write_state(self.valid_state())
        before = self.store.read_bytes()
        with mock.patch.object(
            pocket_tasks.os, "replace", side_effect=PermissionError("blocked")
        ):
            self.assertEqual(self.command("add", "Second")[0], 2)
        self.assertEqual(self.store.read_bytes(), before)
        self.assertEqual(list(self.folder.iterdir()), [self.store])

    def test_failed_first_creation_leaves_no_store_or_temporary(self):
        with mock.patch.object(
            pocket_tasks.os, "replace", side_effect=PermissionError("blocked")
        ):
            self.assertEqual(self.command("add", "First")[0], 2)
        self.assertFalse(self.store.exists())
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_unknown_command_does_not_touch_store(self):
        self.write_state(self.valid_state())
        before = self.store.read_bytes()
        self.assertEqual(self.command("explode")[0], 2)
        self.assertEqual(self.store.read_bytes(), before)

    def test_module_entry_point_round_trips_between_processes(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        prefix = [sys.executable, "-B", "-m", "pocket_tasks", "--store", str(self.store)]
        added = subprocess.run(
            [*prefix, "add", "Fresh process"],
            cwd=ROOT,
            env=environment,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
        )
        listed = subprocess.run(
            [*prefix, "list"],
            cwd=ROOT,
            env=environment,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(
            (added.returncode, added.stdout, added.stderr), (0, "Added task 1.\n", "")
        )
        self.assertEqual(
            (listed.returncode, listed.stdout, listed.stderr),
            (0, "1 [ ] Fresh process\n", ""),
        )


if __name__ == "__main__":
    unittest.main()
