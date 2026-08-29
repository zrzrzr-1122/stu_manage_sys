"""
将 data/json 下的 mock 数据导入 MySQL（yanjiusheng）。

用法（在仓库根目录或 data 目录）：
  python data/seed_mock.py
  python data/seed_mock.py --reset-related   # 先清空教师/成绩/就业/部门/顾问再导入

默认行为：
  - 不删除现有学生/班级
  - 部门/顾问/教师/成绩/就业：按主键 UPSERT
  - 更新班级展示字段（class_id 业务编号、班主任、授课老师）
  - 为学生补 password_md5（默认 123456）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent
JSON_DIR = ROOT / "json"
PWD_MD5 = "e10adc3949ba59abbe56e057f20f883e"

# 与 backend/database.py 保持一致
DB_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/yanjiusheng?charset=utf8mb4"


def load_rows(name: str) -> list[dict]:
    data = json.loads((JSON_DIR / name).read_text(encoding="utf-8"))
    return data["rows"]


def upsert(conn, sql: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    conn.execute(text(sql), rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="导入项目 mock 数据")
    parser.add_argument(
        "--reset-related",
        action="store_true",
        help="导入前清空 department/consultant/teacher/score/employment（不影响学生/班级/管理员）",
    )
    parser.add_argument("--db-url", default=DB_URL, help="SQLAlchemy 数据库 URL")
    args = parser.parse_args()

    engine = create_engine(args.db_url, pool_pre_ping=True)

    departments = load_rows("department.json")
    consultants = load_rows("consultant.json")
    classes = load_rows("class_info.json")
    teachers = load_rows("teacher.json")
    scores = load_rows("score.json")
    employments = load_rows("employment.json")
    logs = load_rows("sys_operation_log.json")
    students = load_rows("student_base_info.json")

    with engine.begin() as conn:
        if args.reset_related:
            for table in (
                "ai0720_employment",
                "ai0720score",
                "ai0720_teacher",
                "consultant",
                "department",
            ):
                conn.execute(text(f"DELETE FROM `{table}`"))
            print("[seed] cleared related tables")

        # department
        n = upsert(
            conn,
            """
            INSERT INTO department (did, dname, manager, phone, dstatus, create_time, update_time, id_delete)
            VALUES (:did, :dname, :manager, :phone, :dstatus, NOW(6), NOW(6), :id_delete)
            ON DUPLICATE KEY UPDATE
              dname=VALUES(dname), manager=VALUES(manager), phone=VALUES(phone),
              dstatus=VALUES(dstatus), id_delete=VALUES(id_delete), update_time=NOW(6)
            """,
            departments,
        )
        print(f"[seed] department: {n}")

        # consultant（显式 cid，对齐学生 counselor）
        n = upsert(
            conn,
            """
            INSERT INTO consultant
              (cid, cname, sex, phone, did, position, status, create_time, update_time, is_delete)
            VALUES
              (:cid, :cname, :sex, :phone, :did, :position, :status, NOW(6), NOW(6), :is_delete)
            ON DUPLICATE KEY UPDATE
              cname=VALUES(cname), sex=VALUES(sex), phone=VALUES(phone), did=VALUES(did),
              position=VALUES(position), status=VALUES(status), is_delete=VALUES(is_delete),
              update_time=NOW(6)
            """,
            consultants,
        )
        print(f"[seed] consultant: {n}")

        # class_info 展示字段
        for row in classes:
            conn.execute(
                text(
                    """
                    UPDATE class_info
                    SET class_id=:class_id, start_time=:start_time,
                        head_teacher=:head_teacher, teacher=:teacher, is_delete=:is_delete,
                        update_date=NOW(6)
                    WHERE id=:id
                    """
                ),
                row,
            )
        print(f"[seed] class_info updated: {len(classes)}")

        # teacher
        n = upsert(
            conn,
            """
            INSERT INTO ai0720_teacher
              (tid, tname, sex, class_id, tstatus, tphone, if_delete, create_date, update_date)
            VALUES
              (:tid, :tname, :sex, :class_id, :tstatus, :tphone, :if_delete, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
              tname=VALUES(tname), sex=VALUES(sex), class_id=VALUES(class_id),
              tstatus=VALUES(tstatus), tphone=VALUES(tphone), if_delete=VALUES(if_delete),
              update_date=NOW()
            """,
            teachers,
        )
        print(f"[seed] teacher: {n}")

        # score
        n = upsert(
            conn,
            """
            INSERT INTO ai0720score
              (id, stu_id, stu_name, exam_order, score, is_deleted, create_date, update_date)
            VALUES
              (:id, :stu_id, :stu_name, :exam_order, :score, :is_deleted, :create_date, :update_date)
            ON DUPLICATE KEY UPDATE
              stu_id=VALUES(stu_id), stu_name=VALUES(stu_name), exam_order=VALUES(exam_order),
              score=VALUES(score), is_deleted=VALUES(is_deleted), update_date=VALUES(update_date)
            """,
            scores,
        )
        print(f"[seed] score: {n}")

        # employment
        n = upsert(
            conn,
            """
            INSERT INTO ai0720_employment
              (id, stu_id, class_id, open_time, offer_time, company, salary, is_delete, create_date, update_date)
            VALUES
              (:id, :stu_id, :class_id, :open_time, :offer_time, :company, :salary, :is_delete, :create_date, :update_date)
            ON DUPLICATE KEY UPDATE
              stu_id=VALUES(stu_id), class_id=VALUES(class_id), open_time=VALUES(open_time),
              offer_time=VALUES(offer_time), company=VALUES(company), salary=VALUES(salary),
              is_delete=VALUES(is_delete), update_date=VALUES(update_date)
            """,
            employments,
        )
        print(f"[seed] employment: {n}")

        # operation log（仅插入不存在的 id）
        n = upsert(
            conn,
            """
            INSERT IGNORE INTO sys_operation_log
              (id, module, action_type, title, content, operator_id, operator_name,
               request_uri, request_method, ip, browser, os, status, execution_time, error_msg, create_time)
            VALUES
              (:id, :module, :action_type, :title, :content, :operator_id, :operator_name,
               :request_uri, :request_method, :ip, :browser, :os, :status, :execution_time, :error_msg, :create_time)
            """,
            logs,
        )
        print(f"[seed] operation_log: {n}")

        # 学生：补密码；若 stu_id 不存在则插入 mock 学生
        patched = 0
        inserted = 0
        for stu in students:
            exists = conn.execute(
                text("SELECT 1 FROM student_base_info WHERE stu_id=:stu_id"),
                {"stu_id": stu["stu_id"]},
            ).first()
            if exists:
                conn.execute(
                    text(
                        """
                        UPDATE student_base_info
                        SET password_md5=:password_md5
                        WHERE stu_id=:stu_id AND (password_md5 IS NULL OR password_md5='')
                        """
                    ),
                    {"stu_id": stu["stu_id"], "password_md5": PWD_MD5},
                )
                patched += 1
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO student_base_info
                          (stu_id, stu_name, class_id, address, graduateSchool, major,
                           startTime, endTime, education, counselor, age, sex, password_md5, is_delete)
                        VALUES
                          (:stu_id, :stu_name, :class_id, :address, :graduateSchool, :major,
                           :startTime, :endTime, :education, :counselor, :age, :sex, :password_md5, :is_delete)
                        """
                    ),
                    stu,
                )
                inserted += 1
        print(f"[seed] student password patched≈{patched}, inserted={inserted}")

        # admin
        conn.execute(
            text(
                """
                INSERT INTO sys_user (id, username, password_md5, is_delete)
                VALUES (1, 'admin', :pwd, 0)
                ON DUPLICATE KEY UPDATE password_md5=VALUES(password_md5), is_delete=0
                """
            ),
            {"pwd": PWD_MD5},
        )
        print("[seed] sys_user admin ensured")

    print("[seed] done")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[seed] failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
