from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_like
from model.departmentMdel import Department


class DepartmentDao(BaseDao[Department]):
    model = Department
    pk_field = "did"
    delete_field = "id_delete"

    def exists_dname(self, db: Session, dname: str) -> bool:
        return self.exists_by(db, "dname", dname)

    def build_list_query(
        self,
        db: Session,
        *,
        dname: str | None = None,
        manager: str | None = None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_like(query, Department, "dname", dname)
        query = apply_like(query, Department, "manager", manager)
        return query


department_dao = DepartmentDao()
