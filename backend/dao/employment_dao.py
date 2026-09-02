from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_eq, apply_like
from model.employment_model import Employment


class EmploymentDao(BaseDao[Employment]):
    model = Employment
    pk_field = "id"
    delete_field = "is_delete"

    def build_list_query(
        self,
        db: Session,
        *,
        stu_id=None,
        class_id=None,
        company: str | None = None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_eq(query, Employment, "stu_id", stu_id)
        query = apply_eq(query, Employment, "class_id", class_id)
        query = apply_like(query, Employment, "company", company)
        return query


employment_dao = EmploymentDao()
