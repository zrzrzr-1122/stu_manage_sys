from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from database import Base


class OperationLog(Base):
    """后台写操作审计日志，字段对齐 B 端系统日志页。"""

    __tablename__ = "sys_operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(50), comment="业务模块")
    action_type = Column(String(20), comment="操作类型")
    title = Column(String(120), nullable=False, comment="操作标题")
    content = Column(String(500), comment="摘要")
    operator_id = Column(Integer, comment="操作人ID")
    operator_name = Column(String(50), comment="操作人")
    request_uri = Column(String(255), comment="请求路径")
    request_method = Column(String(10), comment="请求方法")
    ip = Column(String(64), comment="IP")
    browser = Column(String(50), comment="浏览器")
    os = Column(String(50), comment="操作系统")
    status = Column(Integer, default=1, nullable=False, comment="1成功 0失败")
    execution_time = Column(Integer, comment="耗时毫秒")
    error_msg = Column(Text, comment="错误信息")
    create_time = Column(DateTime, default=datetime.now, comment="操作时间")

    __table_args__ = (
        Index("idx_log_create_time", "create_time"),
        Index("idx_log_operator_name", "operator_name"),
        Index("idx_log_ip", "ip"),
    )
