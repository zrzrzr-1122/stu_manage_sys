import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# 数据库连接：优先环境变量 DATABASE_URL
db_url = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:123456@127.0.0.1:3306/yanjiusheng?charset=utf8mb4",
)

engine = create_engine(
    db_url,
    pool_size=10,
    echo=False,
    pool_pre_ping=True,
)

Session = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


def drop_all_foreign_keys():
    """去掉当前库全部外键约束，关联关系改由业务层维护。"""
    sql = """
        SELECT TABLE_NAME, CONSTRAINT_NAME
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    """
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(sql)).fetchall()
            for table_name, constraint_name in rows:
                conn.execute(text(
                    f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`"
                ))
            if rows:
                print(f"[database] 已删除 {len(rows)} 条外键约束")
    except SQLAlchemyError as e:
        print(f"[database] 删除外键失败（可忽略若库尚未创建）: {e}")


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    row = conn.execute(text(
        """
        SELECT COUNT(1) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND COLUMN_NAME = :column_name
        """
    ), {"table_name": table_name, "column_name": column_name}).scalar()
    return bool(row)


def ensure_extra_columns():
    """给已有表补齐重构新增字段，避免只 create_all 时旧表缺列。"""
    alters = [
        ("student_base_info", "password_md5",
         "ALTER TABLE `student_base_info` ADD COLUMN `password_md5` VARCHAR(128) NULL COMMENT 'C端登录密码'"),
        ("sys_user", "teacher_id",
         "ALTER TABLE `sys_user` ADD COLUMN `teacher_id` INT NULL COMMENT '关联教师tid'"),
        ("department", "phone",
         "ALTER TABLE `department` ADD COLUMN `phone` VARCHAR(20) NULL COMMENT '联系电话'"),
        ("department", "dstatus",
         "ALTER TABLE `department` ADD COLUMN `dstatus` INT NOT NULL DEFAULT 1 COMMENT '部门状态'"),
        ("consultant", "phone",
         "ALTER TABLE `consultant` MODIFY COLUMN `phone` VARCHAR(20) NOT NULL COMMENT '联系电话'"),
    ]
    widen = [
        ("sys_user", "password_md5",
         "ALTER TABLE `sys_user` MODIFY COLUMN `password_md5` VARCHAR(128) NOT NULL COMMENT '密码哈希'"),
        ("student_base_info", "password_md5",
         "ALTER TABLE `student_base_info` MODIFY COLUMN `password_md5` VARCHAR(128) NULL COMMENT 'C端登录密码'"),
    ]
    try:
        with engine.begin() as conn:
            tables = {
                r[0] for r in conn.execute(text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
                )).fetchall()
            }
            for table_name, column_name, ddl in alters:
                if table_name not in tables:
                    continue
                if column_name == "phone" and table_name == "consultant":
                    try:
                        conn.execute(text(ddl))
                    except SQLAlchemyError:
                        pass
                    continue
                if not _column_exists(conn, table_name, column_name):
                    conn.execute(text(ddl))
            for table_name, column_name, ddl in widen:
                if table_name in tables and _column_exists(conn, table_name, column_name):
                    try:
                        conn.execute(text(ddl))
                    except SQLAlchemyError:
                        pass
    except SQLAlchemyError as e:
        print(f"[database] 补齐字段失败: {e}")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def seed_admin_user():
    from model.user_model import SysUser
    from utils.password_util import hash_password

    allow = _env_flag("ALLOW_DEFAULT_ADMIN", default=True)
    if not allow:
        print("[database] 已跳过默认管理员种子（ALLOW_DEFAULT_ADMIN=0）")
        return

    db = Session()
    try:
        exists = db.query(SysUser).filter(SysUser.username == "admin", SysUser.is_delete == 0).first()
        if not exists:
            db.add(SysUser(username="admin", password_md5=hash_password("123456"), is_delete=0))
            db.commit()
            print("[database] 已初始化管理员 admin / 123456（bcrypt）")
        else:
            # 旧 MD5 密码在首次登录时自动升级；此处不强制改写
            db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        print(f"[database] 初始化管理员失败: {e}")
    finally:
        db.close()


def seed_rbac_data():
    from jwt_auth.rbac_seed import seed_rbac

    allow_demo = _env_flag("ALLOW_DEFAULT_ADMIN", default=True)
    db = Session()
    try:
        seed_rbac(db, allow_demo_users=allow_demo)
        print("[database] RBAC 角色/菜单种子已就绪")
    except Exception as e:
        db.rollback()
        print(f"[database] RBAC 种子失败: {e}")
    finally:
        db.close()


def init_database():
    import model  # noqa: F401
    from model.log_model import OperationLog  # noqa: F401
    from model.chat_model import ChatApiKey, ChatConversation, ChatMessage  # noqa: F401
    from model.rbac_model import (  # noqa: F401
        SysRole, SysMenu, SysUserRole, SysRoleMenu, TeacherClass,
    )

    drop_all_foreign_keys()
    Base.metadata.create_all(engine)
    ensure_extra_columns()
    drop_all_foreign_keys()
    seed_admin_user()
    seed_rbac_data()
