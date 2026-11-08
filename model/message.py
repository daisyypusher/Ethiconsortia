"""
model/message.py
─────────────────────────────────────────────────────────────
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    message_id: int
    sender_id: int
    receiver_id: int
    content: str
    sent_at: datetime
