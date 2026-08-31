<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="学号"><el-input v-model="queryParams.stu_id" clearable /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="queryParams.stu_name" clearable @keyup.enter="handleQuery" /></el-form-item>
        <el-form-item label="考核序次"><el-input v-model="queryParams.exam_order" clearable /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card class="page-content" shadow="never">
      <div class="page-toolbar"><el-button type="primary" @click="openDialog()">新增</el-button></div>
      <div class="page-table-wrapper">
        <el-table v-loading="loading" class="page-table" :data="list" height="100%" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="stu_id" label="学号" width="90" />
          <el-table-column prop="stu_name" label="姓名" width="110" />
          <el-table-column prop="exam_order" label="考核序次" width="100" />
          <el-table-column prop="score" label="分数" width="90" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
              <el-button v-hasPerm="'sms:score:delete'" type="danger" link @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        class="page-pagination"
        @pagination="fetchData"
      />
    </el-card>
    <el-dialog v-model="visible" :title="form.id ? '编辑成绩' : '新增成绩'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="学号" prop="stu_id"><el-input-number v-model="form.stu_id" :min="1" /></el-form-item>
        <el-form-item label="姓名" prop="stu_name"><el-input v-model="form.stu_name" /></el-form-item>
        <el-form-item label="考核序次" prop="exam_order"><el-input-number v-model="form.exam_order" :min="1" /></el-form-item>
        <el-form-item label="分数" prop="score"><el-input-number v-model="form.score" :min="0" :max="100" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" @click="submit">确定</el-button>
        <el-button @click="visible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import type { FormInstance, FormRules } from "element-plus";
import SmsAPI from "@/api/sms";
defineOptions({ name: "SmsScore" });
const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({ pageNum: 1, pageSize: 10, stu_id: "", stu_name: "", exam_order: "" });
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = {
  stu_id: [{ required: true, message: "请输入学号", trigger: "blur" }],
  stu_name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  exam_order: [{ required: true, message: "请输入序次", trigger: "blur" }],
  score: [{ required: true, message: "请输入分数", trigger: "blur" }],
};
async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getScores({ ...queryParams });
    list.value = data.list || [];
    total.value = data.total || 0;
  } finally {
    loading.value = false;
  }
}
function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}
function handleReset() {
  queryParams.stu_id = "";
  queryParams.stu_name = "";
  queryParams.exam_order = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) Object.assign(form, { ...row });
  else Object.assign(form, { exam_order: 1, score: 0 });
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.id;
  if (form.id) await SmsAPI.updateScore(Number(form.id), payload);
  else await SmsAPI.createScore(payload);
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该成绩？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteScore(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
onMounted(fetchData);
</script>
