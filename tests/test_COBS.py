import unittest
from isles.isleExpansions import Peer

class TestCobs(unittest.TestCase):
    # https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing
    def setUp(self):
        self.encoding = [
            (b"\x00\x00",                   b"\x01\x01\x00"),                                   # Test 1
            (b"\x00\x00\x00",               b"\x01\x01\x01\x00"),                               # Test 2
            (b"\x11\x22\x33\x44\x00",       b"\x05\x11\x22\x33\x44\x00"),                       # Test 3
            (b"\x11\x22\x00\x33\x00",       b"\x03\x11\x22\x02\x33\x00"),                       # Test 4
            (b"\x11\x00\x00\x00\x00",       b"\x02\x11\x01\x01\x01\x00"),                       # Test 5
            (bytes(range(1,255)) + b"\x00", b"\xFF" + bytes(range(1,255)) + b"\x00"),           # Test 6
            (bytes(range(0,255)) + b"\x00", b"\x01\xFF" + bytes(range(1,255)) + b"\x00"),       # Test 7
            (bytes(range(1,256)) + b"\x00", b"\xFF" + bytes(range(1,255)) + b"\x02\xFF\x00"),   # Test 8
        ]

    def test_COBS_encode(self):
        for i, representation in enumerate(self.encoding):
            key, value = representation
            self.assertEqual(Peer.COBS_encode(None, key), value, f"Failed on test: {i + 1}")

    def test_COBS_decode(self):
        for i, representation in enumerate(self.encoding):
            key, value = representation
            self.assertEqual(Peer.COBS_decode(None, value), key, f"Failed on test: {i + 1}")
