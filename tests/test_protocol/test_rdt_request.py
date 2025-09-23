import unittest
from protocol.rdt import RDTRequest

class TestRDTRequest(unittest.TestCase):
    def test_happy_path_rdt_request(self):
        rdt = RDTRequest(b"042|7_hello")
        self.assertFalse(rdt.ack_flag)
        self.assertEqual(rdt.sequence_number, 42)
        self.assertEqual(rdt.reference_number, 7)
        self.assertEqual(rdt.data, b"hello")

    def test_invalid_missing_sep_rdt_request(self):
        with self.assertRaises(ValueError):
            RDTRequest(b"0" + b"1|2" + b"no_underscore")

    def test_invalid_ack_rdt_request(self):
        with self.assertRaises(ValueError):
            RDTRequest(b"x1|2_payload")
