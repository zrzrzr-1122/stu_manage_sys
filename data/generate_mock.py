"""Generate mock JSON/SQL for empty/related tables based on existing student roster patterns."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JSON_DIR = ROOT / "json"
SQL_DIR = ROOT / "sql"
JSON_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)

PWD_MD5 = "e10adc3949ba59abbe56e057f20f883e"  # 123456
RNG = random.Random(20260828)

# Mirror existing student_base_info samples (stu_id 1..30) for score/employment linkage.
STUDENTS = []
base_names = [
    ("王小明", "男", 1, 101, 20),
    ("李小红", "女", 2, 102, 19),
    ("张伟", "男", 1, 101, 18),
    ("刘芳", "女", 3, 103, 21),
    ("陈强", "男", 2, 102, 20),
    ("赵敏", "女", 1, 101, 19),
    ("孙洋", "男", 3, 103, 20),
    ("周洁", "女", 2, 102, 22),
    ("吴刚", "男", 1, 101, 18),
    ("郑秀", "女", 3, 103, 20),
    ("钱进", "男", 2, 102, 19),
    ("冯雅", "女", 1, 101, 22),
]
extra_names = [
    "何磊", "罗倩", "高翔", "林娜", "梁涛", "宋婷", "唐宇", "许静",
    "邓凯", "曹雪", "彭飞", "萧然", "蒋雯", "韩旭", "谢琳", "董浩",
    "袁圆", "潘晨", "于帆", "蒋宁",
]
for i, (name, sex, class_id, counselor, age) in enumerate(base_names, start=1):
    STUDENTS.append(
        {
            "stu_id": i,
            "stu_name": name,
            "class_id": class_id,
            "address": RNG.choice(["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]),
            "graduateSchool": RNG.choice(["北京大学", "清华大学", "复旦大学", "浙江大学", "武汉大学", "四川大学"]),
            "major": RNG.choice(["计算机科学", "软件工程", "人工智能", "数据科学", "电子信息"]),
            "startTime": "2024-03-01",
            "endTime": "2025-03-01",
            "education": "本科",
            "counselor": counselor,
            "age": age,
            "sex": sex,
            "password_md5": PWD_MD5,
            "is_delete": 0,
        }
    )
for i, name in enumerate(extra_names, start=13):
    sex = "男" if i % 2 else "女"
    class_id = ((i - 1) % 7) + 1
    counselor = 101 + ((i - 1) % 3)
    STUDENTS.append(
        {
            "stu_id": i,
            "stu_name": name,
            "class_id": class_id,
            "address": RNG.choice(["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安"]),
            "graduateSchool": RNG.choice(["北京大学", "清华大学", "复旦大学", "浙江大学", "武汉大学", "四川大学"]),
            "major": RNG.choice(["计算机科学", "软件工程", "人工智能", "数据科学", "电子信息"]),
            "startTime": "2024-03-01",
            "endTime": "2025-03-01",
            "education": RNG.choice(["本科", "专科", "硕士"]),
            "counselor": counselor,
            "age": 18 + (i % 15),
            "sex": sex,
            "password_md5": PWD_MD5,
            "is_delete": 0,
        }
    )

COMPANIES = [
    ("字节跳动", 18000, 28000),
    ("阿里巴巴", 16000, 26000),
    ("腾讯科技", 17000, 27000),
    ("美团", 14000, 22000),
    ("京东", 13000, 21000),
    ("华为", 15000, 25000),
    ("小米科技", 12000, 20000),
    ("网易", 14000, 23000),
    ("滴滴出行", 13000, 21000),
    ("拼多多", 15000, 24000),
]


def write_json(name: str, table: str, description: str, rows: list) -> None:
    payload = {"table": table, "description": description, "rows": rows}
    (JSON_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


scores = []
sid = 1
for stu in STUDENTS:
    # exam 1
    s1 = round(RNG.uniform(45, 98), 1)
    # make a few intentional fails / high scorers for stats pages
    if stu["stu_id"] in {3, 7, 11}:
        s1 = round(RNG.uniform(40, 55), 1)
    if stu["stu_id"] in {1, 6, 12}:
        s1 = round(RNG.uniform(85, 98), 1)
    scores.append(
        {
            "id": sid,
            "stu_id": stu["stu_id"],
            "stu_name": stu["stu_name"],
            "exam_order": 1,
            "score": s1,
            "is_deleted": 0,
            "create_date": "2024-06-01 10:00:00",
            "update_date": "2024-06-01 10:00:00",
        }
    )
    sid += 1
    # exam 2
    s2 = round(min(100, max(35, s1 + RNG.uniform(-12, 15))), 1)
    if stu["stu_id"] in {3, 7}:
        s2 = round(RNG.uniform(45, 58), 1)  # fail twice
    scores.append(
        {
            "id": sid,
            "stu_id": stu["stu_id"],
            "stu_name": stu["stu_name"],
            "exam_order": 2,
            "score": s2,
            "is_deleted": 0,
            "create_date": "2024-09-01 10:00:00",
            "update_date": "2024-09-01 10:00:00",
        }
    )
    sid += 1

employments = []
eid = 1
for stu in STUDENTS:
    if stu["stu_id"] % 3 == 0:
        continue  # leave some students without employment
    company, lo, hi = RNG.choice(COMPANIES)
    open_d = f"2024-{RNG.randint(8, 11):02d}-{RNG.randint(1, 20):02d}"
    offer_month = RNG.randint(9, 12)
    offer_d = f"2024-{offer_month:02d}-{RNG.randint(1, 28):02d}"
    employments.append(
        {
            "id": eid,
            "stu_id": stu["stu_id"],
            "class_id": stu["class_id"],
            "open_time": open_d,
            "offer_time": offer_d,
            "company": company,
            "salary": round(RNG.uniform(lo, hi), 2),
            "is_delete": 0,
            "create_date": "2024-12-01 12:00:00",
            "update_date": "2024-12-01 12:00:00",
        }
    )
    eid += 1

logs = []
modules = [
    ("学生管理", "新增", "新增学生", "/api/v1/sms/students", "POST"),
    ("成绩管理", "修改", "修改成绩", "/api/v1/sms/scores/1", "PUT"),
    ("就业管理", "查询", "查询就业列表", "/api/v1/sms/employments", "GET"),
    ("认证登录", "登录", "管理员登录", "/api/v1/auth/login", "POST"),
    ("顾问管理", "删除", "删除顾问", "/api/v1/sms/consultants/105", "DELETE"),
]
for i, (module, action, title, uri, method) in enumerate(modules, start=1):
    logs.append(
        {
            "id": i,
            "module": module,
            "action_type": action,
            "title": title,
            "content": f"{title}成功",
            "operator_id": 1,
            "operator_name": "admin",
            "request_uri": uri,
            "request_method": method,
            "ip": "127.0.0.1",
            "browser": "Chrome",
            "os": "Windows",
            "status": 1 if i != 5 else 0,
            "execution_time": RNG.randint(20, 180),
            "error_msg": None if i != 5 else "顾问不存在或已删除",
            "create_time": f"2025-01-{i:02d} 10:30:00",
        }
    )

write_json(
    "student_base_info.json",
    "student_base_info",
    "学生 mock 样例（可覆盖/补齐 password_md5=123456）；库中若已有学生，导入脚本默认只补密码与关联表",
    STUDENTS,
)
write_json("score.json", "ai0720score", "成绩 mock：每人 2 次考核", scores)
write_json("employment.json", "ai0720_employment", "就业 mock：约 2/3 学生有就业记录", employments)
write_json("sys_operation_log.json", "sys_operation_log", "操作日志样例", logs)

print(f"students={len(STUDENTS)} scores={len(scores)} employments={len(employments)} logs={len(logs)}")
print("JSON generated under data/json/")
