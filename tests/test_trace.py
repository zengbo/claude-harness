import unittest
import os
import json
import tempfile
import shutil

from harness.trace import record_success, record_failure, record_checkpoint, list_traces


class TestRecordSuccess(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_success_file(self):
        path = record_success(
            harness_dir=self.harness_dir,
            task="Add /api/users endpoint",
            steps="create types -> write service -> add handler",
            files_changed="types/user.go,services/user.go",
            validation="all passed",
            review="PASS",
        )
        self.assertTrue(os.path.exists(path))

    def test_success_file_is_valid_json(self):
        path = record_success(
            harness_dir=self.harness_dir,
            task="Add endpoint",
            steps="step1 -> step2",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["task"], "Add endpoint")
        self.assertEqual(data["type"], "success")

    def test_success_file_in_correct_directory(self):
        path = record_success(
            harness_dir=self.harness_dir,
            task="test task",
            steps="step1",
        )
        self.assertIn("successes", path)

    def test_success_includes_timestamp(self):
        path = record_success(
            harness_dir=self.harness_dir,
            task="test",
            steps="step1",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertIn("timestamp", data)

    def test_optional_fields_default_none(self):
        path = record_success(
            harness_dir=self.harness_dir,
            task="test",
            steps="step1",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertIsNone(data.get("files_changed"))


class TestRecordFailure(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_failure_file(self):
        path = record_failure(
            harness_dir=self.harness_dir,
            task="Refactor cache",
            steps="move file -> update imports",
            error="Layer 1 -> Layer 3 violation",
            root_cause="Moving file changed layer",
            resolution="abandoned",
        )
        self.assertTrue(os.path.exists(path))

    def test_failure_type_is_failure(self):
        path = record_failure(
            harness_dir=self.harness_dir,
            task="test",
            steps="step1",
            error="some error",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["type"], "failure")
        self.assertEqual(data["error"], "some error")

    def test_failure_in_correct_directory(self):
        path = record_failure(
            harness_dir=self.harness_dir,
            task="test",
            steps="step1",
            error="err",
        )
        self.assertIn("failures", path)


class TestRecordCheckpoint(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_checkpoint_file(self):
        path = record_checkpoint(
            harness_dir=self.harness_dir,
            task="Refactor auth",
            stage="Stage 1: types complete",
            decisions="Chose JWT over sessions",
            next_step="Stage 2: middleware",
        )
        self.assertTrue(os.path.exists(path))

    def test_checkpoint_has_decisions(self):
        path = record_checkpoint(
            harness_dir=self.harness_dir,
            task="test",
            stage="stage 1",
            decisions="decision A",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["decisions"], "decision A")
        self.assertEqual(data["type"], "checkpoint")


class TestListTraces(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_list_empty(self):
        result = list_traces(self.harness_dir)
        self.assertEqual(result["successes"], [])
        self.assertEqual(result["failures"], [])

    def test_list_after_recording(self):
        record_success(self.harness_dir, task="t1", steps="s1")
        record_failure(self.harness_dir, task="t2", steps="s2", error="e")
        result = list_traces(self.harness_dir)
        self.assertEqual(len(result["successes"]), 1)
        self.assertEqual(len(result["failures"]), 1)


if __name__ == "__main__":
    unittest.main()
