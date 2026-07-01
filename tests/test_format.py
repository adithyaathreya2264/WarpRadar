"""Tests for shared formatting utilities."""

from warpradar.utils.format import format_bytes, format_speed, format_duration


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(500) == "500.0 B"

    def test_kilobytes(self):
        assert format_bytes(1536) == "1.5 KB"

    def test_megabytes(self):
        assert format_bytes(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert format_bytes(2.5 * 1024**3) == "2.5 GB"

    def test_terabytes(self):
        assert format_bytes(1024**4) == "1.0 TB"

    def test_zero(self):
        assert format_bytes(0) == "0.0 B"


class TestFormatSpeed:
    def test_format_speed(self):
        assert format_speed(1024) == "1.0 KB/s"

    def test_format_speed_zero(self):
        assert format_speed(0) == "0.0 B/s"


class TestFormatDuration:
    def test_seconds(self):
        assert format_duration(30) == "30s"

    def test_minutes(self):
        assert format_duration(125) == "2m 5s"

    def test_hours(self):
        assert format_duration(7200) == "2h 0m"

    def test_zero(self):
        assert format_duration(0) == "0s"
