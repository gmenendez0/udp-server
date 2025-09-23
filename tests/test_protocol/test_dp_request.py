import unittest
from protocol.dp import DPRequest, FunctionFlag

class TestDPRequest(unittest.TestCase):
    def test_happy_path(self):
        raw = b"1_abc123_hello"
        dp = DPRequest(raw)
        self.assertEqual(dp.function_flag, FunctionFlag.CLOSE_CONN)
        self.assertEqual(dp.uuid, "abc123")
        self.assertEqual(dp.payload, b"hello")

    def test_bad_separators(self):
        with self.assertRaises(ValueError):
            DPRequest(b"1abc123_hello")  # falta '_'

    def test_unknown_flag_fallsback_none(self):
        dp = DPRequest(b"99_id_payload")
        self.assertEqual(dp.function_flag, FunctionFlag.NONE)
