from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_eq, apply_like
from model.score_model import Score


class ScoreDao(BaseDao[Score]):
    model = Score
    pk_field = "id"
    delete_field = "is_deleted"

    def build_list_query(
        self,
        db: Session,
        *,
        stu_id=None,
        stu_name: str | None = None,
        exam_order=None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_eq(query, Score, "stu_id", stu_id)
        query = apply_like(query, Score, "stu_name", stu_name)
        query = apply_eq(query, Score, "exam_order", exam_order)
        return query


score_dao = ScoreDao()
