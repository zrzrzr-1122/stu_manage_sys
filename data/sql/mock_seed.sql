-- 沃林学生管理系统 mock 数据（可手工导入）
-- 用法：
--   mysql -uroot -p123456 yanjiusheng < data/sql/mock_seed.sql
-- 或：
--   python data/seed_mock.py
--
-- 密码明文均为 123456，MD5 = e10adc3949ba59abbe56e057f20f883e
-- 说明：本 SQL 使用 UPSERT；不会删除现有学生主数据。

SET NAMES utf8mb4;

-- 管理员
INSERT INTO sys_user (id, username, password_md5, is_delete)
VALUES (1, 'admin', 'e10adc3949ba59abbe56e057f20f883e', 0)
ON DUPLICATE KEY UPDATE password_md5=VALUES(password_md5), is_delete=0;

-- 部门
INSERT INTO department (did, dname, manager, phone, dstatus, create_time, update_time, id_delete) VALUES
(1, '就业指导部', '王建国', '010-88880001', 1, NOW(6), NOW(6), 0),
(2, '学员服务部', '李秀英', '010-88880002', 1, NOW(6), NOW(6), 0),
(3, '教学管理部', '赵明辉', '010-88880003', 1, NOW(6), NOW(6), 0),
(4, '市场运营部', '陈雅琴', '010-88880004', 0, NOW(6), NOW(6), 0)
ON DUPLICATE KEY UPDATE
  dname=VALUES(dname), manager=VALUES(manager), phone=VALUES(phone),
  dstatus=VALUES(dstatus), id_delete=VALUES(id_delete), update_time=NOW(6);

-- 顾问（cid 对齐学生 counselor=101/102/103）
INSERT INTO consultant (cid, cname, sex, phone, did, position, status, create_time, update_time, is_delete) VALUES
(101, '周顾问', '女', '13800000101', 1, '高级顾问', 0, NOW(6), NOW(6), 0),
(102, '吴顾问', '男', '13800000102', 1, '中级顾问', 0, NOW(6), NOW(6), 0),
(103, '郑顾问', '女', '13800000103', 2, '初级顾问', 0, NOW(6), NOW(6), 0),
(104, '冯顾问', '男', '13800000104', 2, '初级顾问', 0, NOW(6), NOW(6), 0),
(105, '韩顾问', '女', '13800000105', 3, '中级顾问', 1, NOW(6), NOW(6), 0),
(106, '曹顾问', '男', '13800000106', 3, '高级顾问', 0, NOW(6), NOW(6), 0)
ON DUPLICATE KEY UPDATE
  cname=VALUES(cname), sex=VALUES(sex), phone=VALUES(phone), did=VALUES(did),
  position=VALUES(position), status=VALUES(status), is_delete=VALUES(is_delete), update_time=NOW(6);

-- 班级展示信息（按主键 id 更新）
UPDATE class_info SET class_id='AI0720-01', start_time='2024-03-01 09:00:00', head_teacher='张班主任', teacher='刘老师', is_delete=0, update_date=NOW(6) WHERE id=1;
UPDATE class_info SET class_id='AI0720-02', start_time='2024-03-15 09:00:00', head_teacher='李班主任', teacher='陈老师', is_delete=0, update_date=NOW(6) WHERE id=2;
UPDATE class_info SET class_id='AI0720-03', start_time='2024-04-01 09:00:00', head_teacher='王班主任', teacher='赵老师', is_delete=0, update_date=NOW(6) WHERE id=3;
UPDATE class_info SET class_id='AI0720-04', start_time='2024-05-01 09:00:00', head_teacher='孙班主任', teacher='周老师', is_delete=0, update_date=NOW(6) WHERE id=4;
UPDATE class_info SET class_id='AI0720-05', start_time='2024-06-01 09:00:00', head_teacher='钱班主任', teacher='吴老师', is_delete=0, update_date=NOW(6) WHERE id=5;
UPDATE class_info SET class_id='AI0720-06', start_time='2024-07-01 09:00:00', head_teacher='郑班主任', teacher='冯老师', is_delete=0, update_date=NOW(6) WHERE id=6;
UPDATE class_info SET class_id='AI0720-07', start_time='2024-08-01 09:00:00', head_teacher='韩班主任', teacher='曹老师', is_delete=0, update_date=NOW(6) WHERE id=7;

-- 教师
INSERT INTO ai0720_teacher (tid, tname, sex, class_id, tstatus, tphone, if_delete, create_date, update_date) VALUES
(1, '刘老师', '男', 1, '在职', '13900001001', 0, NOW(), NOW()),
(2, '陈老师', '女', 2, '在职', '13900001002', 0, NOW(), NOW()),
(3, '赵老师', '男', 3, '在职', '13900001003', 0, NOW(), NOW()),
(4, '周老师', '女', 4, '在职', '13900001004', 0, NOW(), NOW()),
(5, '吴老师', '男', 5, '在职', '13900001005', 0, NOW(), NOW()),
(6, '冯老师', '女', 6, '休假', '13900001006', 0, NOW(), NOW()),
(7, '曹老师', '男', 7, '在职', '13900001007', 0, NOW(), NOW()),
(8, '沈助教', '女', 1, '在职', '13900001008', 0, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  tname=VALUES(tname), sex=VALUES(sex), class_id=VALUES(class_id),
  tstatus=VALUES(tstatus), tphone=VALUES(tphone), if_delete=VALUES(if_delete), update_date=NOW();

-- 成绩 / 就业请优先用：python data/seed_mock.py
-- （完整 64 条成绩 + 22 条就业在 data/json/score.json、employment.json）

-- 学生缺省密码补齐
UPDATE student_base_info
SET password_md5 = 'e10adc3949ba59abbe56e057f20f883e'
WHERE password_md5 IS NULL OR password_md5 = '';
