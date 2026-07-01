"""Tests for SHA-256 file integrity checksums."""

from pathlib import Path

from warpradar.security.integrity import compute_checksum, StreamingChecksum


class TestChecksum:
    def test_compute_deterministic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello warpradar")
        h1 = compute_checksum(f)
        h2 = compute_checksum(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_verify_correct(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello warpradar")
        checksum = compute_checksum(f)
        assert compute_checksum(f) == checksum

    def test_verify_incorrect(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello warpradar")
        assert compute_checksum(f) != "0" * 64

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("content A")
        f2.write_text("content B")
        assert compute_checksum(f1) != compute_checksum(f2)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        h = compute_checksum(f)
        assert len(h) == 64


class TestStreamingChecksum:
    def test_incremental_matches_full(self, tmp_path):
        f = tmp_path / "test.txt"
        content = b"hello warpradar streaming test"
        f.write_bytes(content)
        full_hash = compute_checksum(f)

        sc = StreamingChecksum()
        sc.update(content[:10])
        sc.update(content[10:])
        assert sc.hexdigest() == full_hash

    def test_verify_method(self):
        sc = StreamingChecksum()
        sc.update(b"test data")
        digest = sc.hexdigest()
        assert sc.verify(digest) is True
        assert sc.verify("0" * 64) is False

    def test_total_bytes_tracked(self):
        sc = StreamingChecksum()
        sc.update(b"abc")
        sc.update(b"defgh")
        assert sc.total_bytes == 8
