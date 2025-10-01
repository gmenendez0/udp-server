class DPControlRequest:
    def __init__(self, opcode: int, tlvs: list, sid: int):
        self.opcode = opcode
        self.tlvs = tlvs
        self.sid = sid


def create_dp_control_request(opcode: int, tlvs: list, sid: int) -> DPControlRequest:
    """Factory function para crear un DP control request"""
    return DPControlRequest(opcode, tlvs, sid)