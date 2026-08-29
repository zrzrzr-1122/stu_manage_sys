# Mock 数据说明

本目录存放沃林学生管理系统的演示数据，可直接导入 MySQL 库 `yanjiusheng`。

## 目录结构

```
data/
├── README.md                 # 本说明
├── generate_mock.py          # 重新生成成绩/就业等 JSON
├── seed_mock.py              # 一键导入 JSON → MySQL
├── json/                     # 结构化 mock（推荐查看/编辑）
│   ├── sys_user.json
│   ├── department.json
│   ├── consultant.json
│   ├── class_info.json
│   ├── teacher.json
│   ├── student_base_info.json
│   ├── score.json
│   ├── employment.json
│   └── sys_operation_log.json
└── sql/
    └── mock_seed.sql         # 手工导入（部门/顾问/教师/班级等基础数据）
```

## 默认账号

| 端 | 账号 | 密码 |
|----|------|------|
| B 端 admin | `admin` | `123456` |
| C 端门户 | 学号（如 `1`） | `123456` |

密码 MD5：`e10adc3949ba59abbe56e057f20f883e`

## 导入方式（推荐）

在仓库根目录执行：

```bash
# 1）如需重生成成绩/就业 JSON
python data/generate_mock.py

# 2）导入到本地 MySQL
python data/seed_mock.py

# 可选：先清空教师/成绩/就业/部门/顾问再导入（不删学生/班级）
python data/seed_mock.py --reset-related
```

或用 MySQL 客户端导入基础 SQL（成绩/就业仍建议用上面的 Python 脚本）：

```bash
mysql -uroot -p123456 yanjiusheng < data/sql/mock_seed.sql
python data/seed_mock.py
```

## 数据关系约定

- `student_base_info.class_id` → `class_info.id`
- `student_base_info.counselor` → `consultant.cid`（101 / 102 / 103）
- `consultant.did` → `department.did`
- `ai0720score.stu_id` / `ai0720_employment.stu_id` → `student_base_info.stu_id`
- `ai0720_teacher.class_id` → `class_info.id`

## 数据规模（当前生成结果）

| 表 | 大约条数 | 说明 |
|----|----------|------|
| department | 4 | 含 1 个停用部门 |
| consultant | 6 | 对齐学生 counselor |
| class_info | 7 | 更新业务编号/班主任 |
| ai0720_teacher | 8 | 覆盖 7 个班 |
| student_base_info | 32 样例 | 导入时：已有学生只补密码 |
| ai0720score | 64 | 每人 2 次考核 |
| ai0720_employment | 22 | 约 2/3 学生有就业 |
| sys_operation_log | 5 | 样例日志 |

导入脚本会尽量 **UPSERT**，不会无故清空现有学生主表。
