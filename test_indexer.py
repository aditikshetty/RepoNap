
import unittest

from indexer import index_files


class TestIndexer(unittest.TestCase):
    def test_preserves_line_numbers(self):
        files = [{
            "path": "main.py",
            "content": "line1\nline2\nline3",
        }]

        chunks = index_files(files, chunk_size=2, overlap=0)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertEqual(chunks[0]["end_line"], 2)
        self.assertEqual(chunks[1]["start_line"], 3)
        self.assertEqual(chunks[1]["content"], "line3")

    def test_overlapping_chunks(self):
        files = [{
            "path": "main.py",
            "content": "\n".join(f"line{i}" for i in range(1, 7)),
        }]

        chunks = index_files(files, chunk_size=4, overlap=2)

        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertEqual(chunks[0]["end_line"], 4)
        self.assertEqual(chunks[1]["start_line"], 3)
        self.assertEqual(chunks[1]["end_line"], 6)

    def test_empty_file(self):
        chunks = index_files([{
            "path": "empty.py",
            "content": "",
        }])

        self.assertEqual(chunks, [])

    def test_rejects_invalid_overlap(self):
        with self.assertRaises(ValueError):
            index_files([], chunk_size=5, overlap=5)


if __name__ == "__main__":
    unittest.main()
