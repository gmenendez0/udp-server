#!/usr/bin/env python3
"""
UDP session management for file transfer protocol.
"""

import uuid
from typing import Optional, Dict, Any
from .message import ProtocolType, OperationType


class SessionManager:
    """
    Manages UDP communication sessions.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}  # {uuid: session_info}
    
    def create_session(self, protocol: ProtocolType, operation: OperationType, 
                      initial_seq: int) -> str:
        """
        Create a new session.
        
        Args:
            protocol: Protocol type
            operation: Operation type
            initial_seq: Initial sequence number from client
        
        Returns:
            UUID of the new session
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Type validations
        if not isinstance(protocol, ProtocolType):
            raise ValueError(f"protocol must be ProtocolType, received: {type(protocol)}")
        
        if not isinstance(operation, OperationType):
            raise ValueError(f"operation must be OperationType, received: {type(operation)}")
        
        if not isinstance(initial_seq, int):
            raise ValueError(f"initial_seq must be int, received: {type(initial_seq)}")
        
        if initial_seq < 0:
            raise ValueError(f"initial_seq must be >= 0, received: {initial_seq}")
        
        session_uuid = str(uuid.uuid4())
        self.sessions[session_uuid] = {
            'protocol': protocol,
            'operation': operation,
            'initial_seq': initial_seq,  # Initial sequence number from client
            'expected_seq': initial_seq + 1,  # First data message will be seq=initial_seq+1
            'last_ack': initial_seq,
            'created_at': None  # TODO: We could add timestamp if needed
        }
        return session_uuid
    
    def get_session(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            Session information or None if it doesn't exist
            
        Raises:
            ValueError: If session_uuid is not a string
        """
        if not isinstance(session_uuid, str):
            raise ValueError(f"session_uuid must be str, received: {type(session_uuid)}")
        
        return self.sessions.get(session_uuid)
    
    def update_expected_seq(self, session_uuid: str, new_seq: int) -> None:
        """
        Update expected sequence number.
        
        Args:
            session_uuid: Session UUID
            new_seq: New expected sequence number
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not isinstance(session_uuid, str):
            raise ValueError(f"session_uuid must be str, received: {type(session_uuid)}")
        
        if not isinstance(new_seq, int):
            raise ValueError(f"new_seq must be int, received: {type(new_seq)}")
        
        if new_seq < 0:
            raise ValueError(f"new_seq must be >= 0, received: {new_seq}")
        
        if session_uuid in self.sessions:
            self.sessions[session_uuid]['expected_seq'] = new_seq
        else:
            raise ValueError(f"Session {session_uuid} does not exist")
    
    def update_last_ack(self, session_uuid: str, new_ack: int) -> None:
        """
        Update last ACK.
        
        Args:
            session_uuid: Session UUID
            new_ack: New ACK number
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not isinstance(session_uuid, str):
            raise ValueError(f"session_uuid must be str, received: {type(session_uuid)}")
        
        if not isinstance(new_ack, int):
            raise ValueError(f"new_ack must be int, received: {type(new_ack)}")
        
        if new_ack < 0:
            raise ValueError(f"new_ack must be >= 0, received: {new_ack}")
        
        if session_uuid in self.sessions:
            self.sessions[session_uuid]['last_ack'] = new_ack
        else:
            raise ValueError(f"Session {session_uuid} does not exist")
    
    def remove_session(self, session_uuid: str) -> None:
        """
        Remove a session.
        
        Args:
            session_uuid: Session UUID
            
        Raises:
            ValueError: If session_uuid is not a string
        """
        if not isinstance(session_uuid, str):
            raise ValueError(f"session_uuid must be str, received: {type(session_uuid)}")
        
        self.sessions.pop(session_uuid, None)
    
    def session_exists(self, session_uuid: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_uuid: Session UUID
        
        Returns:
            True if session exists, False otherwise
            
        Raises:
            ValueError: If session_uuid is not a string
        """
        if not isinstance(session_uuid, str):
            raise ValueError(f"session_uuid must be str, received: {type(session_uuid)}")
        
        return session_uuid in self.sessions
    
    def get_session_count(self) -> int:
        """
        Get number of active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.sessions)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            Dictionary with all sessions
        """
        return self.sessions.copy()
    
    def clear_all_sessions(self) -> None:
        """
        Remove all active sessions.
        """
        self.sessions.clear()
