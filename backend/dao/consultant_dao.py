from sqlalchemy.orm import Query, Session

from dao.base_dao import BaseDao
from dao.query_helpers import apply_eq, apply_like
from model.consultantModel import Consultant


class ConsultantDao(BaseDao[Consultant]):
    model = Consultant
    pk_field = "cid"
    delete_field = "is_delete"

    @staticmethod
    def _normalize(data: dict) -> dict:
        if "phone" in data and data["phone"] is not None:
            return {**data, "phone": str(data["phone"])}
        return data

    def build_list_query(
        self,
        db: Session,
        *,
        cname: str | None = None,
        did=None,
        status=None,
    ) -> Query:
        query = self.base_query(db)
        query = apply_like(query, Consultant, "cname", cname)
        query = apply_eq(query, Consultant, "did", did)
        if status is not None:
            query = query.filter(Consultant.status == status)
        return query

    def create(self, db: Session, data: dict, **kwargs) -> Consultant:
        return super().create(db, data, normalize=self._normalize)

    def update(self, db: Session, row: Consultant, data: dict, **kwargs) -> Consultant:
        return super().update(db, row, data, normalize=self._normalize, **kwargs)


consultant_dao = ConsultantDao()
