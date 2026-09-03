"""AI 聊天相关表（并入 yanjiusheng，无独立 chat 用户）。"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

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
    system_prompt = Column(Text, nullable=True, comment="会话级 System Prompt")
    max_tokens = Column(Integer, nullable=True, default=2048)
    temperature = Column(Float, nullable=True, default=0.7)
    stream_enabled = Column(Integer, nullable=False, default=1, comment="1流式 0非流式")
    thinking_enabled = Column(Integer, nullable=False, default=1, comment="展示思维链")
    markdown_enabled = Column(Integer, nullable=False, default=1, comment="Markdown 渲染")
    memory_pinned = Column(Integer, nullable=False, default=0, comment="1=钉为跨会话记忆")
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
    thinking_content = Column(Text, nullable=True, comment="reasoner 思维链")
    data_queries_json = Column(Text, nullable=True, comment="NL2SQL data_queries JSON")
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class ChatUserMemory(Base):
    """按账号隔离的跨会话记忆本。"""

    __tablename__ = "chat_user_memories"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", name="uk_chat_user_memory_owner"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_type = Column(String(20), nullable=False, comment="admin|student")
    owner_id = Column(Integer, nullable=False, comment="所属账号 ID")
    content = Column(Text, nullable=True, comment="记忆本文本")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
        onupdate=datetime.now,
    )


class ChatLlmLog(Base):
    """每次与 DeepSeek 的调用记录。"""

    __tablename__ = "chat_llm_logs"
    __table_args__ = (
        Index("idx_chat_llm_owner_created", "owner_type", "owner_id", "created_at"),
        Index("idx_chat_llm_conv_created", "conversation_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_type = Column(String(20), nullable=False)
    owner_id = Column(Integer, nullable=False)
    conversation_id = Column(BigInteger, nullable=True)
    message_id = Column(BigInteger, nullable=True)
    model = Column(String(50), nullable=False)
    stream = Column(Integer, nullable=False, default=1)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    request_preview = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ok")
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
