"""Tests for transfer history recording and persistence."""

from pathlib import Path

from warpradar.utils.history import TransferHistory, TransferRecord


class TestTransferHistory:
    def test_add_transfer(self, tmp_path):
        h = TransferHistory(history_file=tmp_path / "history.json")
        h.add_transfer(
            direction="sent",
            filename="test.txt",
            filesize=1024,
            peer_hostname="bob-pc",
            peer_ip="192.168.1.10",
            success=True,
            duration_seconds=2.0,
            speed_bps=512.0,
        )
        records = h.get_all()
        assert len(records) == 1
        assert records[0].filename == "test.txt"
        assert records[0].peer_hostname == "bob-pc"

    def test_persistence(self, tmp_path):
        path = tmp_path / "history.json"
        h1 = TransferHistory(history_file=path)
        h1.add_transfer(
            direction="received",
            filename="data.bin",
            filesize=2048,
            peer_hostname="alice",
            peer_ip="10.0.0.5",
            success=True,
            duration_seconds=1.0,
            speed_bps=2048.0,
        )
        # Create a new instance reading the same file
        h2 = TransferHistory(history_file=path)
        records = h2.get_all()
        assert len(records) == 1
        assert records[0].filename == "data.bin"

    def test_filtering(self, tmp_path):
        h = TransferHistory(history_file=tmp_path / "history.json")
        h.add_transfer("sent", "a.txt", 100, "p1", "1.1.1.1", True, 1.0, 100.0)
        h.add_transfer("received", "b.txt", 200, "p2", "2.2.2.2", True, 2.0, 100.0)
        h.add_transfer("sent", "c.txt", 300, "p1", "1.1.1.1", False, 0.0, 0.0, "err")

        assert len(h.get_all()) == 3
        assert len(h.get_sent()) == 2
        assert len(h.get_received()) == 1
        assert len(h.get_successful()) == 2
        assert len(h.get_failed()) == 1

    def test_success_rate(self, tmp_path):
        h = TransferHistory(history_file=tmp_path / "history.json")
        h.add_transfer("sent", "a.txt", 100, "p1", "1.1.1.1", True, 1.0, 100.0)
        h.add_transfer("sent", "b.txt", 200, "p2", "2.2.2.2", False, 0.0, 0.0)
        assert h.success_rate == 50.0

    def test_record_format_methods(self):
        r = TransferRecord(
            timestamp="2025-01-01",
            direction="sent",
            filename="file.txt",
            filesize=1536,
            peer_hostname="host",
            peer_ip="1.2.3.4",
            success=True,
            duration_seconds=2.5,
            speed_bps=614.4,
        )
        assert "KB" in r.format_size()
        assert "/s" in r.format_speed()

    def test_clear(self, tmp_path):
        h = TransferHistory(history_file=tmp_path / "history.json")
        h.add_transfer("sent", "a.txt", 100, "p1", "1.1.1.1", True, 1.0, 100.0)
        assert len(h.get_all()) == 1
        h.clear()
        assert len(h.get_all()) == 0
