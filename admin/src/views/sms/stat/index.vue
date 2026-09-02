<template>
  <div class="page-container">
    <el-row :gutter="16" class="mb-4">
      <el-col :span="6" v-for="item in cards" :key="item.label">
        <el-card shadow="never">
          <div class="stat-num">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mb-4">
      <template #header>超过 30 岁学员</template>
      <el-table :data="over30" border size="small">
        <el-table-column prop="stu_id" label="学号" width="90" />
        <el-table-column prop="stu_name" label="姓名" />
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column prop="class_id" label="班级" width="90" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="mb-4">
      <template #header>班级男女人数</template>
      <el-table :data="sexCount" border size="small">
        <el-table-column prop="class_id" label="班级" />
        <el-table-column prop="total_count" label="总人数" />
        <el-table-column prop="male_count" label="男生" />
        <el-table-column prop="female_count" label="女生" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="mb-4">
      <template #header>
        <span>班级平均分</span>
        <el-input-number v-model="examOrder" :min="1" size="small" class="ml-4" @change="loadExamAvg" />
      </template>
      <el-table :data="examAvg" border size="small">
        <el-table-column prop="class_id" label="班级" />
        <el-table-column prop="avg_score" label="平均分" />
      </el-table>
    </el-card>

    <el-card shadow="never" class="mb-4">
      <template #header>薪资 TOP5</template>
      <el-table :data="salaryTop" border size="small">
        <el-table-column prop="stu_name" label="姓名" />
        <el-table-column prop="class_id" label="班级" width="90" />
        <el-table-column prop="company" label="公司" />
        <el-table-column prop="salary" label="薪资" width="110" />
        <el-table-column prop="offer_time" label="Offer 时间" width="120">
          <template #default="{ row }">{{ formatDate(row.offer_time) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>班级平均就业时长（天）</template>
      <el-table :data="empAvg" border size="small">
        <el-table-column prop="class_id" label="班级" />
        <el-table-column prop="avg_duration_day" label="平均天数" />
      </el-table>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import SmsAPI from "@/api/sms";
import { formatDate } from "@/constants/date";
defineOptions({ name: "SmsStat" });

const cards = ref([
  { label: "在读学生", value: 0 },
  { label: "班级数", value: 0 },
  { label: "教师数", value: 0 },
  { label: "就业记录", value: 0 },
]);
const over30 = ref<Record<string, unknown>[]>([]);
const sexCount = ref<Record<string, unknown>[]>([]);
const examAvg = ref<Record<string, unknown>[]>([]);
const salaryTop = ref<Record<string, unknown>[]>([]);
const empAvg = ref<Record<string, unknown>[]>([]);
const examOrder = ref(1);

async function loadExamAvg() {
  examAvg.value = (await SmsAPI.getStat(`exam-avg/${examOrder.value}`)) as Record<string, unknown>[];
}

onMounted(async () => {
  const overview = await SmsAPI.getOverview();
  cards.value = [
    { label: "在读学生", value: overview.studentCount || 0 },
    { label: "班级数", value: overview.classCount || 0 },
    { label: "教师数", value: overview.teacherCount || 0 },
    { label: "就业记录", value: overview.employmentCount || 0 },
  ];
  over30.value = (await SmsAPI.getStat("over-30")) as Record<string, unknown>[];
  sexCount.value = (await SmsAPI.getStat("sex-count")) as Record<string, unknown>[];
  salaryTop.value = (await SmsAPI.getStat("salary-top5")) as Record<string, unknown>[];
  empAvg.value = (await SmsAPI.getStat("class-emp-avg")) as Record<string, unknown>[];
  await loadExamAvg();
});
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
.ml-4 {
  margin-left: 16px;
}
</style>
