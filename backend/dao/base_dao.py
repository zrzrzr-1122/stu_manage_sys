"""DAO 基类：通用 CRUD 与分页。"""
from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

from sqlalchemy.orm import Query, Session

from dao.query_helpers import paginate

T = TypeVar("T")


class BaseDao(Generic[T]):
    """按 model / 主键 / 逻辑删除列配置，复用增删改查。"""

    model: type[T]
    pk_field: str = "id"
    delete_field: str | None = "is_delete"

    def _pk_column(self):
        return getattr(self.model, self.pk_field)

    def _delete_column(self):
        if not self.delete_field:
            return None
        return getattr(self.model, self.delete_field)

    def base_query(self, db: Session) -> Query:
        query = db.query(self.model)
        if self.delete_field:
            query = query.filter(self._delete_column() == 0)
        return query

    def get_by_id(self, db: Session, pk_id: Any) -> T | None:
        return self.base_query(db).filter(self._pk_column() == pk_id).first()

    def get_by_pk(self, db: Session, pk_id: Any) -> T | None:
        return self.get_by_id(db, pk_id)

    def exists_by(self, db: Session, field: str, value: Any) -> bool:
        column = getattr(self.model, field)
        return self.base_query(db).filter(column == value).first() is not None

    def page(self, query: Query, page_num: int, page_size: int):
        return paginate(query, page_num, page_size)

    def create(
        self,
        db: Session,
        data: dict,
        *,
        normalize: Callable[[dict], dict] | None = None,
    ) -> T:
        payload = normalize(data) if normalize else data
        row = self.model(**payload)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def update(
        self,
        db: Session,
        row: T,
        data: dict,
        *,
        refresh: bool = True,
        normalize: Callable[[dict], dict] | None = None,
    ) -> T:
        payload = normalize(data) if normalize else data
        for key, value in payload.items():
            setattr(row, key, value)
        db.commit()
        if refresh:
            db.refresh(row)
        return row

    def soft_delete(self, db: Session, row: T) -> None:
        if not self.delete_field:
            raise ValueError(f"{self.model.__name__} 未配置 delete_field")
        setattr(row, self.delete_field, 1)
        db.commit()
