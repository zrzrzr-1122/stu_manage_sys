from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_eq, apply_like
from model.teacher_model import Teacher


class TeacherDao(BaseDao[Teacher]):
    model = Teacher
    pk_field = "tid"
    delete_field = "if_delete"

    @staticmethod
    def _normalize(data: dict) -> dict:
        if "tphone" in data and data["tphone"] is not None:
            return {**data, "tphone": str(data["tphone"])}
        return data

    def build_list_query(
        self,
        db: Session,
        *,
        tid=None,
        tname: str | None = None,
        class_id=None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_eq(query, Teacher, "tid", tid)
        query = apply_like(query, Teacher, "tname", tname)
        query = apply_eq(query, Teacher, "class_id", class_id)
        return query

    def create(self, db: Session, data: dict, **kwargs) -> Teacher:
        return super().create(db, data, normalize=self._normalize)

    def update(self, db: Session, row: Teacher, data: dict, **kwargs) -> Teacher:
        return super().update(db, row, data, normalize=self._normalize, **kwargs)


teacher_dao = TeacherDao()
