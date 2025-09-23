#!/usr/bin/env python3
"""
Handles handshake, sequences and stop-and-wait and go-back-n protocols.
"""

import re
from typing import Optional, Tuple, Dict, Any
from .message import (
    Message, MessageBuilder,
    ProtocolType, OperationType, ErrorCode
)
from .session_manager import SessionManager

# TODO: poner errores adecuados (no recuerdo para qué habíamos definido CONTROL_NOT_FOUND y algunos otros. Revisar bien y poner errores apropiados)
class ProtocolHandler:
    """
    Handles UDP protocol logic for file transfer.
    """
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.max_file_size = 5 * 1024 * 1024  # 5MB
    
    def handle_handshake(self, message: Message) -> Tuple[Message, Optional[str]]:
        """
        Handle initial client handshake.
        
        Args:
            message: Client handshake message
        
        Returns:
            Tuple (response, session_uuid)
        """
        if not message.data:
            return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND), None
        
        try:
            # Parse handshake: "1D archivo.txt" or "2U 500mb archivo.txt"
            parts = message.data.split(' ')
            if len(parts) < 2:
                return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND), None
            
            protocol_op = parts[0]
            if len(protocol_op) != 2:
                return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND), None
            
            # Extract protocol and operation
            protocol_num = int(protocol_op[0])
            operation_char = protocol_op[1]
            
            if protocol_num not in [1, 2]:
                return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND), None
            
            protocol = ProtocolType.STOP_AND_WAIT if protocol_num == 1 else ProtocolType.GO_BACK_N
            operation = OperationType.UPLOAD if operation_char == "U" else OperationType.DOWNLOAD
            
            # Parse file and size (if applicable)
            if operation == OperationType.UPLOAD:
                if len(parts) < 3:
                    return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND), None
                file_size_str = parts[1]
                filename = parts[2]
                
                # Validate file size
                file_size = self._parse_file_size(file_size_str)
                if file_size > self.max_file_size:
                    return self._create_error_response(ErrorCode.TOO_BIG), None
            else:
                filename = parts[1]
            
            # Create session with initial sequence number from client
            session_uuid = self.session_manager.create_session(protocol, operation, message.sequence_number)
            
            # Create successful handshake response
            # ACK confirms the handshake sequence number
            response = MessageBuilder.create_ack_for_message(message, session_uuid)
            
            return response, session_uuid
            
        except (ValueError, IndexError):
            return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND), None
    
    def handle_data_message(self, message: Message) -> Message:
        """
        Handle a data message.
        
        Args:
            message: Data message
        
        Returns:
            ACK response or error
        """
        if not message.session_uuid:
            return self._create_error_response(ErrorCode.UNID)
        
        session_info = self.session_manager.get_session(message.session_uuid)
        if not session_info:
            return self._create_error_response(ErrorCode.UNID)
        
        expected_seq = session_info['expected_seq']
        
        # Verify sequence
        if message.sequence_number != expected_seq:
            # TODO: Para go-back-n, deberíamos implementar lógica diferente acá
            return self._create_error_response(ErrorCode.CONTROL_NOT_FOUND)
        
        # Calculate next expected sequence number using length field
        next_expected_seq = expected_seq + message.length
        
        # Update expected sequence
        self.session_manager.update_expected_seq(message.session_uuid, next_expected_seq)
        
        # Create ACK
        return MessageBuilder.create_ack_for_message(message, message.session_uuid)
    
    def handle_fin_message(self, message: Message) -> Message:
        """
        Handle an end of communication message.
        
        Args:
            message: FIN message
        
        Returns:
            Confirmation response
        """
        if not message.session_uuid:
            return self._create_error_response(ErrorCode.UNID)
        
        session_info = self.session_manager.get_session(message.session_uuid)
        if not session_info:
            return self._create_error_response(ErrorCode.UNID)
        
        # Remove session
        self.session_manager.remove_session(message.session_uuid)
        
        # Create end response
        return MessageBuilder.create_fin_message(message.session_uuid)
    
    def _parse_file_size(self, size_str: str) -> int:
        """
        Parse a file size string to bytes.
        
        Args:
            size_str: String like "500mb", "1gb", "1024kb", etc.
        
        Returns:
            Size in bytes
        """
        size_str = size_str.lower().strip()
        
        # Pattern to extract number and unit
        pattern = r'^(\d+(?:\.\d+)?)\s*(kb|mb|gb|b)?$'
        match = re.match(pattern, size_str)
        
        if not match:
            raise ValueError(f"Invalid size format: {size_str}")
        
        number = float(match.group(1))
        unit = match.group(2) or 'b'
        
        multipliers = {
            'b': 1,
            'kb': 1024,
            'mb': 1024 * 1024,
            'gb': 1024 * 1024 * 1024
        }
        
        return int(number * multipliers[unit])
    
    def _create_error_response(self, error_code: ErrorCode) -> Message:
        """Create an error response"""
        return MessageBuilder.create_error_message(error_code)
    
    def process_message(self, data: bytes) -> bytes:
        """
        Process a received UDP message and return the response.
        
        Args:
            data: Received UDP data
        
        Returns:
            Response in bytes
        """
        try:
            message = Message.from_bytes(data)
            
            # Determine message type and process
            if message.is_ack():
                # ACKs don't require response
                return b""
            elif message.is_finish():
                response = self.handle_fin_message(message)
            elif message.sequence_number == 0 and not message.ack_flag:
                # Initial handshake
                response, _ = self.handle_handshake(message)
            else:
                # Normal data message
                response = self.handle_data_message(message)
            
            return response.to_bytes()
            
        except ValueError as e:
            # Error parsing message
            error_response = MessageBuilder.create_error_message(ErrorCode.CONTROL_NOT_FOUND)
            return error_response.to_bytes()