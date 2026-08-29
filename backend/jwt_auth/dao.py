from sqlalchemy.orm import Session
from model.user_model import SysUser


def get_user_by_username(db: Session, username: str):
    return db.query(SysUser).filter(SysUser.username == username, SysUser.is_delete == 0).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(SysUser).filter(SysUser.id == user_id, SysUser.is_delete == 0).first()
