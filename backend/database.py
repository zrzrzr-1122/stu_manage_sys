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
    except Exception:
        db.rollback()
        raise
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
        ("chat_conversations", "system_prompt",
         "ALTER TABLE `chat_conversations` ADD COLUMN `system_prompt` TEXT NULL COMMENT '会话级 System Prompt'"),
        ("chat_conversations", "max_tokens",
         "ALTER TABLE `chat_conversations` ADD COLUMN `max_tokens` INT NULL DEFAULT 2048"),
        ("chat_conversations", "temperature",
         "ALTER TABLE `chat_conversations` ADD COLUMN `temperature` FLOAT NULL DEFAULT 0.7"),
        ("chat_conversations", "stream_enabled",
         "ALTER TABLE `chat_conversations` ADD COLUMN `stream_enabled` INT NOT NULL DEFAULT 1 COMMENT '1流式 0非流式'"),
        ("chat_conversations", "thinking_enabled",
         "ALTER TABLE `chat_conversations` ADD COLUMN `thinking_enabled` INT NOT NULL DEFAULT 1 COMMENT '展示思维链'"),
        ("chat_conversations", "markdown_enabled",
         "ALTER TABLE `chat_conversations` ADD COLUMN `markdown_enabled` INT NOT NULL DEFAULT 1 COMMENT 'Markdown 渲染'"),
        ("chat_conversations", "memory_pinned",
         "ALTER TABLE `chat_conversations` ADD COLUMN `memory_pinned` INT NOT NULL DEFAULT 0 COMMENT '1=钉为跨会话记忆'"),
        ("chat_messages", "thinking_content",
         "ALTER TABLE `chat_messages` ADD COLUMN `thinking_content` TEXT NULL COMMENT 'reasoner 思维链'"),
        ("chat_messages", "prompt_tokens",
         "ALTER TABLE `chat_messages` ADD COLUMN `prompt_tokens` INT NULL"),
        ("chat_messages", "completion_tokens",
         "ALTER TABLE `chat_messages` ADD COLUMN `completion_tokens` INT NULL"),
        ("chat_messages", "total_tokens",
         "ALTER TABLE `chat_messages` ADD COLUMN `total_tokens` INT NULL"),
        ("chat_messages", "data_queries_json",
         "ALTER TABLE `chat_messages` ADD COLUMN `data_queries_json` TEXT NULL COMMENT 'NL2SQL data_queries JSON'"),
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


def _index_exists(conn, table_name: str, index_name: str) -> bool:
    row = conn.execute(text(
        """
        SELECT COUNT(1) FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
          AND INDEX_NAME = :index_name
        """
    ), {"table_name": table_name, "index_name": index_name}).scalar()
    return bool(row)


def ensure_indexes():
    """给已有表补齐业务热点索引（create_all 不会回填旧表）。"""
    indexes = [
        (
            "chat_messages",
            "idx_chat_msg_conv_created",
            "ALTER TABLE `chat_messages` ADD INDEX `idx_chat_msg_conv_created` (`conversation_id`, `created_at`)",
        ),
        (
            "chat_conversations",
            "idx_chat_conv_owner_updated",
            "ALTER TABLE `chat_conversations` ADD INDEX `idx_chat_conv_owner_updated` (`owner_type`, `owner_id`, `updated_at`)",
        ),
        (
            "chat_conversations",
            "idx_chat_conv_owner_pinned",
            "ALTER TABLE `chat_conversations` ADD INDEX `idx_chat_conv_owner_pinned` (`owner_type`, `owner_id`, `memory_pinned`)",
        ),
        (
            "student_base_info",
            "idx_student_class_delete",
            "ALTER TABLE `student_base_info` ADD INDEX `idx_student_class_delete` (`class_id`, `is_delete`)",
        ),
        (
            "ai0720_employment",
            "idx_emp_stu_delete",
            "ALTER TABLE `ai0720_employment` ADD INDEX `idx_emp_stu_delete` (`stu_id`, `is_delete`)",
        ),
        (
            "ai0720_employment",
            "idx_emp_class_delete",
            "ALTER TABLE `ai0720_employment` ADD INDEX `idx_emp_class_delete` (`class_id`, `is_delete`)",
        ),
        (
            "ai0720score",
            "idx_score_stu_deleted_exam",
            "ALTER TABLE `ai0720score` ADD INDEX `idx_score_stu_deleted_exam` (`stu_id`, `is_deleted`, `exam_order`)",
        ),
        (
            "chat_llm_logs",
            "idx_chat_llm_owner_created",
            "ALTER TABLE `chat_llm_logs` ADD INDEX `idx_chat_llm_owner_created` (`owner_type`, `owner_id`, `created_at`)",
        ),
        (
            "chat_llm_logs",
            "idx_chat_llm_conv_created",
            "ALTER TABLE `chat_llm_logs` ADD INDEX `idx_chat_llm_conv_created` (`conversation_id`, `created_at`)",
        ),
    ]
    # 复合索引就绪后，去掉删外键遗留的单列冗余索引
    drops = [
        ("ai0720score", "stu_id", "idx_score_stu_deleted_exam"),
    ]
    try:
        with engine.begin() as conn:
            tables = {
                r[0] for r in conn.execute(text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
                )).fetchall()
            }
            created = 0
            for table_name, index_name, ddl in indexes:
                if table_name not in tables:
                    continue
                if _index_exists(conn, table_name, index_name):
                    continue
                try:
                    conn.execute(text(ddl))
                    created += 1
                except SQLAlchemyError as e:
                    print(f"[database] 创建索引 {index_name} 失败: {e}")
            for table_name, index_name, require_index in drops:
                if table_name not in tables:
                    continue
                if not _index_exists(conn, table_name, require_index):
                    continue
                if not _index_exists(conn, table_name, index_name):
                    continue
                try:
                    conn.execute(text(f"ALTER TABLE `{table_name}` DROP INDEX `{index_name}`"))
                    print(f"[database] 已删除冗余索引 {table_name}.{index_name}")
                except SQLAlchemyError as e:
                    print(f"[database] 删除冗余索引 {index_name} 失败: {e}")
            if created:
                print(f"[database] 已补齐 {created} 个业务索引")
    except SQLAlchemyError as e:
        print(f"[database] 补齐索引失败: {e}")


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
    from model.chat_model import (  # noqa: F401
        ChatApiKey,
        ChatConversation,
        ChatMessage,
        ChatLlmLog,
        ChatUserMemory,
        ChatNl2SqlLog,
    )
    from model.rbac_model import (  # noqa: F401
        SysRole, SysMenu, SysUserRole, SysRoleMenu, TeacherClass,
    )

    drop_all_foreign_keys()
    Base.metadata.create_all(engine)
    ensure_extra_columns()
    ensure_indexes()
    drop_all_foreign_keys()
    seed_admin_user()
    seed_rbac_data()
