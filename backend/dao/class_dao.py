from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_like
from model.class_model import ClassInfo


class ClassDao(BaseDao[ClassInfo]):
    model = ClassInfo
    pk_field = "id"
    delete_field = "is_delete"

    def exists_class_id(self, db: Session, class_id: str) -> bool:
        return self.exists_by(db, "class_id", class_id)

    def build_list_query(
        self,
        db: Session,
        *,
        class_id: str | None = None,
        head_teacher: str | None = None,
        teacher: str | None = None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_like(query, ClassInfo, "class_id", class_id)
        query = apply_like(query, ClassInfo, "head_teacher", head_teacher)
        query = apply_like(query, ClassInfo, "teacher", teacher)
        return query


class_dao = ClassDao()
