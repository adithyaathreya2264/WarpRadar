"""Tests for the beacon packet format (v2 with timestamps)."""

import time
from warpradar.discovery.beacon import (
    create_heartbeat_packet,
    create_goodbye_packet,
    parse_packet,
    PACKET_SIZE,
    MSG_TYPE_HEARTBEAT,
    MSG_TYPE_GOODBYE,
)
from warpradar.utils.system import OperatingSystem


class TestBeaconPacket:
    def test_heartbeat_roundtrip(self):
        pkt = create_heartbeat_packet("my-host", OperatingSystem.WINDOWS, 5556)
        assert len(pkt) == PACKET_SIZE
        parsed = parse_packet(pkt)
        assert parsed is not None
        assert parsed["hostname"] == "my-host"
        assert parsed["os"] == OperatingSystem.WINDOWS
        assert parsed["port"] == 5556
        assert parsed["msg_type"] == MSG_TYPE_HEARTBEAT
        assert parsed["timestamp"] > 0

    def test_goodbye_roundtrip(self):
        pkt = create_goodbye_packet("bye-host", OperatingSystem.LINUX, 9999)
        parsed = parse_packet(pkt)
        assert parsed is not None
        assert parsed["hostname"] == "bye-host"
        assert parsed["msg_type"] == MSG_TYPE_GOODBYE

    def test_timestamp_is_recent(self):
        before = time.time()
        pkt = create_heartbeat_packet("ts-test", OperatingSystem.DARWIN, 5556)
        after = time.time()
        parsed = parse_packet(pkt)
        assert before <= parsed["timestamp"] <= after

    def test_invalid_magic(self):
        pkt = bytearray(create_heartbeat_packet("x", OperatingSystem.UNKNOWN, 1234))
        pkt[0:4] = b"FAKE"
        assert parse_packet(bytes(pkt)) is None

    def test_short_packet(self):
        assert parse_packet(b"") is None
        assert parse_packet(b"WARP") is None

    def test_long_hostname_truncated(self):
        long_name = "a" * 100
        pkt = create_heartbeat_packet(long_name, OperatingSystem.LINUX, 5556)
        parsed = parse_packet(pkt)
        assert len(parsed["hostname"]) <= 32
