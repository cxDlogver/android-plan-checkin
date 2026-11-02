"""Snapshot consistency tests; no product actions are executed."""
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from input_snapshot import InputSnapshot


class ReadSnapshot(unittest.TestCase):
    def test_reads_reuse_bytes_but_changed_input_blocks_return(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'input.txt'
            file.write_bytes(b'original')
            stamp = file.stat()
            snapshot = InputSnapshot()
            with snapshot:
                self.assertEqual(file.read_text(encoding='utf-8'),'original')
                file.write_bytes(b'modified')
                os.utime(file,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
                self.assertEqual(file.read_bytes(),b'original')
            self.assertFalse(snapshot.current())
            self.assertIsNone(InputSnapshot.active())

    def test_missing_file_and_changed_link_conditions_invalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'missing.txt'
            snapshot = InputSnapshot()
            with snapshot:
                self.assertFalse(file.is_file())
            self.assertTrue(snapshot.current())
            file.write_bytes(b'created')
            self.assertFalse(snapshot.current())


    def test_resolution_reuses_one_snapshot_but_changed_target_blocks_return(self):
        alias = Path.cwd()/'alias'
        first, second = Path.cwd()/'first', Path.cwd()/'second'
        with patch.object(Path, 'resolve', side_effect=[first,second]) as resolver:
            snapshot = InputSnapshot()
            with snapshot:
                self.assertEqual(alias.resolve(),first)
                self.assertEqual(alias.resolve(),first)
            self.assertEqual(resolver.call_count,1)
            self.assertFalse(snapshot.current())
            self.assertEqual(resolver.call_count,2)


    def test_direct_candidate_review_blocks_mid_review_source_change(self):
        import route
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'source.txt'
            file.write_bytes(b'before')
            def inspect_candidate(record,workspace):
                self.assertEqual(file.read_bytes(),b'before')
                file.write_bytes(b'after!')
                return {'candidate':'not authorized yet'}
            with patch.object(route, '_inspect', side_effect=inspect_candidate):
                with self.assertRaisesRegex(ValueError,'input changed while reviewing candidate'):
                    route.inspect({},Path(directory))
            self.assertIsNone(InputSnapshot.active())


if __name__ == '__main__':
    unittest.main()
