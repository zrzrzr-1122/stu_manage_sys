<template>
  <div class="page-container" v-loading="loading">
    <el-row :gutter="16" class="mb-4">
      <el-col :span="6" v-for="item in cards" :key="item.label">
        <el-card shadow="never">
          <div class="stat-num">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="学生" name="student">
          <el-card shadow="never" class="mb-4" header="超过 30 岁学员">
            <el-table :data="over30" border size="small" empty-text="暂无数据">
              <el-table-column prop="stu_id" label="学号" width="90" />
              <el-table-column prop="stu_name" label="姓名" />
              <el-table-column prop="age" label="年龄" width="80" />
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
          <el-card shadow="never" header="班级男女人数">
            <el-table :data="sexCount" border size="small" empty-text="暂无数据">
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column prop="total_count" label="总人数" />
              <el-table-column prop="male_count" label="男生" />
              <el-table-column prop="female_count" label="女生" />
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="成绩" name="score">
          <el-card shadow="never" class="mb-4">
            <template #header>
              <div class="card-header">
                <span>班级平均分</span>
                <el-input-number
                  v-model="examOrder"
                  :min="1"
                  size="small"
                  @change="loadExamAvg"
                />
              </div>
            </template>
            <el-table :data="examAvg" border size="small" empty-text="暂无数据" v-loading="examLoading">
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column prop="avg_score" label="平均分">
                <template #default="{ row }">{{ formatNum(row.avg_score) }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="mb-4" header="全科成绩 ≥ 80">
            <el-table :data="scoreAbove80" border size="small" empty-text="暂无数据">
              <el-table-column prop="stu_id" label="学号" width="90" />
              <el-table-column prop="stu_name" label="姓名" />
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column label="成绩明细" min-width="220">
                <template #default="{ row }">{{ formatScores(row.scores) }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" header="两次及以上不及格">
            <el-table :data="failMoreTwice" border size="small" empty-text="暂无数据">
              <el-table-column prop="stu_id" label="学号" width="90" />
              <el-table-column prop="stu_name" label="姓名" />
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column label="不及格记录" min-width="220">
                <template #default="{ row }">{{ formatScores(row.fail_records) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="就业" name="employment">
          <el-card shadow="never" class="mb-4" header="薪资 TOP5">
            <el-table :data="salaryTop" border size="small" empty-text="暂无数据">
              <el-table-column prop="stu_name" label="姓名" />
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column prop="company" label="公司" />
              <el-table-column prop="salary" label="薪资" width="110">
                <template #default="{ row }">{{ formatNum(row.salary) }}</template>
              </el-table-column>
              <el-table-column prop="offer_time" label="Offer 时间" width="120" />
            </el-table>
          </el-card>

          <el-card shadow="never" class="mb-4" header="班级平均就业时长（天）">
            <el-table :data="empAvg" border size="small" empty-text="暂无数据">
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column prop="avg_duration_day" label="平均天数">
                <template #default="{ row }">{{ formatNum(row.avg_duration_day) }}</template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" header="学生就业时长">
            <el-table :data="empDuration" border size="small" empty-text="暂无数据">
              <el-table-column prop="stu_id" label="学号" width="90" />
              <el-table-column prop="stu_name" label="姓名" />
              <el-table-column label="班级" min-width="120">
                <template #default="{ row }">{{ classLabel(row) }}</template>
              </el-table-column>
              <el-table-column prop="open_time" label="开放时间" width="120" />
              <el-table-column prop="offer_time" label="Offer 时间" width="120" />
              <el-table-column prop="duration_day" label="天数" width="90" />
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import SmsAPI, { type StatRow } from "@/api/sms";
import { ElMessage } from "element-plus";

defineOptions({ name: "SmsStat" });

const loading = ref(false);
const examLoading = ref(false);
const activeTab = ref("student");
const examOrder = ref(1);

const cards = ref([
  { label: "学生总数", value: 0 },
  { label: "班级数", value: 0 },
  { label: "教师数", value: 0 },
  { label: "就业记录", value: 0 },
]);

const over30 = ref<StatRow[]>([]);
const sexCount = ref<StatRow[]>([]);
const examAvg = ref<StatRow[]>([]);
const scoreAbove80 = ref<StatRow[]>([]);
const failMoreTwice = ref<StatRow[]>([]);
const salaryTop = ref<StatRow[]>([]);
const empAvg = ref<StatRow[]>([]);
const empDuration = ref<StatRow[]>([]);

function classLabel(row: StatRow) {
  return row.class_no || row.class_id || "-";
}

function formatNum(value: number | undefined | null) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(2).replace(/\.00$/, "");
}

function formatScores(rows?: { exam_order: number; score: number }[]) {
  if (!rows?.length) return "-";
  return rows.map((r) => `第${r.exam_order}次:${r.score}`).join("；");
}

async function loadExamAvg() {
  examLoading.value = true;
  try {
    examAvg.value = await SmsAPI.getStat<StatRow[]>(`exam-avg/${examOrder.value}`);
  } catch (e: any) {
    ElMessage.error(e?.message || "加载班级平均分失败");
  } finally {
    examLoading.value = false;
  }
}

async function loadAll() {
  loading.value = true;
  try {
    const [
      overview,
      over30Rows,
      sexRows,
      examRows,
      above80Rows,
      failRows,
      salaryRows,
      empAvgRows,
      empDurationRows,
    ] = await Promise.all([
      SmsAPI.getOverview(),
      SmsAPI.getStat<StatRow[]>("over-30"),
      SmsAPI.getStat<StatRow[]>("sex-count"),
      SmsAPI.getStat<StatRow[]>(`exam-avg/${examOrder.value}`),
      SmsAPI.getStat<StatRow[]>("score-above-80"),
      SmsAPI.getStat<StatRow[]>("fail-more-twice"),
      SmsAPI.getStat<StatRow[]>("salary-top5"),
      SmsAPI.getStat<StatRow[]>("class-emp-avg"),
      SmsAPI.getStat<StatRow[]>("emp-duration"),
    ]);

    cards.value = [
      { label: "学生总数", value: overview.studentCount || 0 },
      { label: "班级数", value: overview.classCount || 0 },
      { label: "教师数", value: overview.teacherCount || 0 },
      { label: "就业记录", value: overview.employmentCount || 0 },
    ];
    over30.value = over30Rows || [];
    sexCount.value = sexRows || [];
    examAvg.value = examRows || [];
    scoreAbove80.value = above80Rows || [];
    failMoreTwice.value = failRows || [];
    salaryTop.value = salaryRows || [];
    empAvg.value = empAvgRows || [];
    empDuration.value = empDurationRows || [];
  } catch (e: any) {
    ElMessage.error(e?.message || "加载统计数据失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.stat-num {
  font-size: 28px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.stat-label {
  color: var(--el-text-color-secondary);
  margin-top: 6px;
}
.mb-4 {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
