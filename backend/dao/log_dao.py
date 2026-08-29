from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from model.log_model import OperationLog


def add_operation_log(db: Session, **fields) -> OperationLog:
    row = OperationLog(**fields)
    db.add(row)
    db.commit()
    return row


def page_operation_logs(
    db: Session,
    page_num: int,
    page_size: int,
    keywords: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    query = db.query(OperationLog)
    if keywords:
        like = f"%{keywords.strip()}%"
        query = query.filter(
            or_(
                OperationLog.ip.like(like),
                OperationLog.operator_name.like(like),
                OperationLog.title.like(like),
                OperationLog.request_uri.like(like),
            )
        )
    if start_time:
        query = query.filter(OperationLog.create_time >= start_time)
    if end_time:
        query = query.filter(OperationLog.create_time < end_time)
    total = query.count()
    rows = (
        query.order_by(OperationLog.id.desc())
        .offset((page_num - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total
