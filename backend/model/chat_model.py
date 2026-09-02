"""AI 聊天相关表（并入 yanjiusheng，无独立 chat 用户）。"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text, UniqueConstraint

from database import Base


class ChatApiKey(Base):
    """每位登录用户各自加密保存的 DeepSeek API Key。"""

    __tablename__ = "chat_api_keys"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", name="uk_chat_api_key_owner"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # admin = sys_user.id；student = student_base_info.stu_id
    owner_type = Column(String(20), nullable=False, comment="admin|student")
    owner_id = Column(Integer, nullable=False, comment="所属账号 ID")
    deepseek_api_key_enc = Column(Text, nullable=True, comment="Fernet 加密的 API Key")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
        onupdate=datetime.now,
    )


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("idx_chat_conv_owner_updated", "owner_type", "owner_id", "updated_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_type = Column(String(20), nullable=False, comment="admin|student")
    owner_id = Column(Integer, nullable=False, comment="所属账号 ID")
    title = Column(String(200), nullable=False, default="新对话")
    model = Column(String(50), nullable=False, default="deepseek-chat")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
        onupdate=datetime.now,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_msg_conv_created", "conversation_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger, nullable=False, comment="chat_conversations.id")
    role = Column(String(20), nullable=False, comment="user|assistant|system")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
