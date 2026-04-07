import unittest
import os
import json
import tempfile
import shutil

from harness.memory import save_memory, query_memory, list_memory, delete_memory


class TestSaveMemory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_save_episodic(self):
        path = save_memory(
            harness_dir=self.harness_dir,
            memory_type="episodic",
            title="macOS symlink trap",
            content="/var is a symlink to /private/var",
            context="Discovered during verify stage",
        )
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["type"], "episodic")
        self.assertEqual(data["title"], "macOS symlink trap")

    def test_save_procedural(self):
        path = save_memory(
            harness_dir=self.harness_dir,
            memory_type="procedural",
            title="Add Go API endpoint",
            steps="1.create type 2.write service 3.add handler 4.register route 5.write test",
            success_rate="3/3",
            language="go",
            project_type="web-api",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["type"], "procedural")
        self.assertEqual(data["success_rate"], "3/3")

    def test_save_failure(self):
        path = save_memory(
            harness_dir=self.harness_dir,
            memory_type="failure",
            title="Layer 0 config import",
            pattern="types/ files importing config package",
            frequency=3,
            fix="Move config logic to Layer 2+",
        )
        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["type"], "failure")
        self.assertEqual(data["frequency"], 3)

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            save_memory(
                harness_dir=self.harness_dir,
                memory_type="invalid",
                title="test",
            )

    def test_save_creates_directory(self):
        save_memory(
            harness_dir=self.harness_dir,
            memory_type="episodic",
            title="test",
            content="test content",
        )
        self.assertTrue(
            os.path.isdir(os.path.join(self.harness_dir, "memory", "episodic"))
        )


class TestQueryMemory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")
        # Seed some memories
        save_memory(self.harness_dir, "procedural", "Add Go API endpoint",
                     steps="create type -> write service -> add handler",
                     language="go")
        save_memory(self.harness_dir, "failure", "Layer 0 config import",
                     pattern="types/ importing config", fix="move to Layer 2+")
        save_memory(self.harness_dir, "episodic", "handler test needs mock DB",
                     content="Use interfaces for injection")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_query_finds_relevant(self):
        results = query_memory(self.harness_dir, "API endpoint")
        self.assertGreater(len(results), 0)
        titles = [r["title"] for r in results]
        self.assertIn("Add Go API endpoint", titles)

    def test_query_finds_failure_by_pattern(self):
        results = query_memory(self.harness_dir, "config import")
        titles = [r["title"] for r in results]
        self.assertIn("Layer 0 config import", titles)

    def test_query_no_results(self):
        results = query_memory(self.harness_dir, "kubernetes deployment")
        self.assertEqual(results, [])

    def test_query_empty_dir(self):
        empty = os.path.join(self.tmpdir, "empty_harness")
        results = query_memory(empty, "anything")
        self.assertEqual(results, [])


class TestListMemory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")
        save_memory(self.harness_dir, "episodic", "mem1", content="c1")
        save_memory(self.harness_dir, "procedural", "mem2", steps="s1")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_list_all(self):
        result = list_memory(self.harness_dir)
        self.assertEqual(len(result["episodic"]), 1)
        self.assertEqual(len(result["procedural"]), 1)
        self.assertEqual(len(result["failure"]), 0)


class TestDeleteMemory(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.harness_dir = os.path.join(self.tmpdir, ".harness")
        self.path = save_memory(
            self.harness_dir, "episodic", "to delete", content="tmp"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_delete_removes_file(self):
        self.assertTrue(os.path.exists(self.path))
        delete_memory(self.path)
        self.assertFalse(os.path.exists(self.path))

    def test_delete_nonexistent_no_error(self):
        delete_memory("/nonexistent/file.json")  # Should not raise


if __name__ == "__main__":
    unittest.main()
