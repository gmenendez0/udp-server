#!/usr/bin/env python3
"""
Message model for file transfer protocol.
Implements format: {ack flag}{function flag}{sequence number}|{reference number}|{length}_{uuid}_{data}
"""

import uuid
import random
from typing import Optional, Union
from enum import Enum


class ProtocolType(Enum):
    """Supported protocol types"""
    STOP_AND_WAIT = 1
    GO_BACK_N = 2


class OperationType(Enum):
    """Operation types"""
    DOWNLOAD = "D"
    UPLOAD = "U"


class ErrorCode(Enum):
    """Protocol error codes"""
    TOO_BIG = "TOO BIG"
    LOCK = "LOCK"
    NOT_FOUND = "NOT FOUND"
    CONTROL_NOT_FOUND = "CONTROL NOT FOUND"
    UNID = "UNID"


class Message:
    """
    Class to handle messages.
    
    Format: {ack flag}{function flag}{sequence number}|{reference number}|{length}_{uuid}_{data}
    
    - ack flag: 1 = ACK, 0 = no ACK
    - function flag: 1 = end communication, 0 = normal
    - sequence number: message sequence number
    - reference number: reference number (for ACK)
    - length: data length in bytes
    - uuid: session identifier (optional)
    - data: message data (optional)
    """
    
    def __init__(self, 
                 ack_flag: bool = False,
                 function_flag: bool = False,
                 sequence_number: int = 0,
                 reference_number: int = 0,
                 length: int = 0,
                 session_uuid: Optional[str] = None,
                 data: Optional[str] = None):
        """
        Initialize a message.
        
        Args:
            ack_flag: True if it's an ACK, False otherwise
            function_flag: True if it ends communication, False otherwise
            sequence_number: Message sequence number
            reference_number: Reference number (used in ACKs)
            length: Data length in bytes
            session_uuid: Session UUID (optional)
            data: Message data (optional)
        """
        self.ack_flag = ack_flag
        self.function_flag = function_flag
        self.sequence_number = sequence_number
        self.reference_number = reference_number
        self.length = length
        self.session_uuid = session_uuid
        self.data = data
    
    def to_bytes(self) -> bytes:
        """Convert message to bytes for UDP transmission"""
        # Build header: {ack_flag}{function_flag}{seq_num}|{ref_num}|{length}
        header = f"{int(self.ack_flag)}{int(self.function_flag)}{self.sequence_number}|{self.reference_number}|{self.length}"
        
        # Build complete message using _ as separator
        parts = [header]
        
        if self.session_uuid:
            parts.append(self.session_uuid)
        
        if self.data:
            parts.append(self.data)
        
        return "_".join(parts).encode('utf-8')
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Message':
        """Create a UDP message from received bytes"""
        try:
            message_str = data.decode('utf-8')
            parts = message_str.split('_', 2)  # Maximum 3 parts: header, uuid, data
            
            # Parse header: {ack_flag}{function_flag}{seq_num}|{ref_num}|{length}
            header = parts[0]
            if header.count('|') != 2:
                raise ValueError("Invalid header format - expected 2 separators")
            
            ack_func_part, ref_part, length_part = header.split('|', 2)
            
            if len(ack_func_part) < 3:
                raise ValueError("Too short header")
            
            ack_flag = bool(int(ack_func_part[0]))
            function_flag = bool(int(ack_func_part[1]))
            sequence_number = int(ack_func_part[2:])
            reference_number = int(ref_part)
            length = int(length_part)
            
            # Parse UUID and data if they exist
            session_uuid = None
            data = None
            
            if len(parts) > 1:
                session_uuid = parts[1]
            if len(parts) > 2:
                data = parts[2]
            
            return cls(
                ack_flag=ack_flag,
                function_flag=function_flag,
                sequence_number=sequence_number,
                reference_number=reference_number,
                length=length,
                session_uuid=session_uuid,
                data=data
            )
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"Error parsing message: {e}")
    
    def is_ack(self) -> bool:
        """Returns True if it's an ACK message"""
        return self.ack_flag
    
    def is_finish(self) -> bool:
        """Returns True if it's an end of communication message"""
        return self.function_flag


class MessageBuilder:
    """
    Builder to create UDP messages in an easier and more readable way.
    """
    
    @staticmethod
    def create_handshake(protocol: ProtocolType, operation: OperationType, 
                        filename: str, file_size: Optional[str] = None) -> Message:
        """
        Create an initial handshake message.
        
        Args:
            protocol: Protocol type (STOP_AND_WAIT or GO_BACK_N)
            operation: Operation type (DOWNLOAD or UPLOAD)
            filename: File name
            file_size: File size (only for UPLOAD)
        
        Returns:
            Message configured for handshake
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not isinstance(protocol, ProtocolType):
            raise ValueError(f"protocol must be ProtocolType, received: {type(protocol)}")
        
        if not isinstance(operation, OperationType):
            raise ValueError(f"operation must be OperationType, received: {type(operation)}")
        
        if not isinstance(filename, str):
            raise ValueError(f"filename must be str, received: {type(filename)}")
        
        if filename.strip() == "":
            raise ValueError("filename cannot be empty")
        
        if file_size is not None and not isinstance(file_size, str):
            raise ValueError(f"file_size must be str, received: {type(file_size)}")
        
        # For handshake: ack=0, function=0, seq=random, ref=0
        # Initial sequence number is chosen randomly by the client
        initial_seq = random.randint(1, 1000)
        
        data_parts = [f"{protocol.value}{operation.value}", filename]
        
        if operation == OperationType.UPLOAD and file_size:
            data_parts.insert(1, file_size)
        
        data = " ".join(data_parts)
        data_length = len(data.encode('utf-8'))
        
        return Message(
            ack_flag=False,
            function_flag=False,
            sequence_number=initial_seq,
            reference_number=0,  # This reference number doesn't confirm any previous message
            length=data_length,
            data=data
        )
    
    @staticmethod
    def create_ack_for_message(original_message: 'Message', session_uuid: str) -> Message:
        """
        Create an ACK for a specific message, automatically calculating values.
        
        Args:
            original_message: The original message being confirmed
            session_uuid: Session UUID
        
        Returns:
            Message configured as ACK
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not isinstance(original_message, Message):
            raise ValueError(f"original_message should be Message, received: {type(original_message)}")
        
        if not isinstance(session_uuid, str):
            raise ValueError(f"session_uuid should be str, received: {type(session_uuid)}")
        
        if session_uuid.strip() == "":
            raise ValueError("session_uuid cannot be empty")
        
        # Calculate next expected sequence number
        next_seq = original_message.sequence_number + original_message.length
        
        return Message(
            ack_flag=True,
            function_flag=False,
            sequence_number=next_seq,  # Next expected SEQ
            reference_number=original_message.sequence_number,  # Confirm this message
            length=0,  # ACK has no data
            session_uuid=session_uuid
        )
    
    @staticmethod
    def create_data_message(sequence_number: int, data: str, 
                           session_uuid: str) -> Message:
        """
        Create a message with data.
        
        Args:
            sequence_number: Message sequence number
            data: Data to send
            session_uuid: Session UUID
        
        Returns:
            Message with data
        """
        data_length = len(data.encode('utf-8'))
        
        return Message(
            ack_flag=False,
            function_flag=False,
            sequence_number=sequence_number,
            reference_number=0,
            length=data_length,
            session_uuid=session_uuid,
            data=data
        )
    
    @staticmethod
    def create_fin_message(session_uuid: str) -> Message:
        """
        Create an end of communication message.
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            End of communication message
        """
        return Message(
            ack_flag=False,
            function_flag=True,
            sequence_number=0,
            reference_number=0,
            length=0,  # FIN has no data
            session_uuid=session_uuid
        )
    
    @staticmethod
    def create_error_message(error_code: ErrorCode) -> Message:
        """
        Create an error message.
        
        Args:
            error_code: Error code
        
        Returns:
            Error message
        """
        error_data = f"ERR:{error_code.value}"
        error_length = len(error_data.encode('utf-8'))
        
        return Message(
            ack_flag=False,
            function_flag=False,
            sequence_number=0,
            reference_number=0,
            length=error_length,
            data=error_data
        )
