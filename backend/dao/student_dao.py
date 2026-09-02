from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_eq, apply_like, apply_like_int
from model.student_model import Student


class StudentDao(BaseDao[Student]):
    model = Student
    pk_field = "stu_id"
    delete_field = "is_delete"

    def build_list_query(
        self,
        db: Session,
        *,
        stu_id=None,
        stu_name: str | None = None,
        class_id: str | None = None,
        address: str | None = None,
        education: str | None = None,
        major: str | None = None,
        age=None,
        sex: str | None = None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_eq(query, Student, "stu_id", stu_id)
        query = apply_like(query, Student, "stu_name", stu_name)
        query = apply_like_int(query, Student, "class_id", class_id)
        query = apply_like(query, Student, "address", address)
        query = apply_like(query, Student, "education", education)
        query = apply_like(query, Student, "major", major)
        query = apply_eq(query, Student, "age", age)
        query = apply_eq(query, Student, "sex", sex)
        return query

    def reset_password(self, db: Session, row: Student, password_hash: str) -> None:
        row.password_md5 = password_hash
        db.commit()


student_dao = StudentDao()
