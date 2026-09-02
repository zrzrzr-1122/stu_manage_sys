<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="学号"><el-input v-model="queryParams.stu_id" clearable /></el-form-item>
        <el-form-item label="公司"><el-input v-model="queryParams.company" clearable @keyup.enter="handleQuery" /></el-form-item>
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
          <el-table-column prop="class_id" label="班级ID" width="90" />
          <el-table-column prop="company" label="公司" min-width="160" show-overflow-tooltip />
          <el-table-column prop="salary" label="薪资" width="110" />
          <el-table-column prop="open_time" label="开放时间" width="120">
            <template #default="{ row }">{{ formatDate(row.open_time) }}</template>
          </el-table-column>
          <el-table-column prop="offer_time" label="Offer时间" width="120">
            <template #default="{ row }">{{ formatDate(row.offer_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDelete(row.id)">删除</el-button>
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
    <el-dialog v-model="visible" :title="form.id ? '编辑就业' : '新增就业'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="学号" prop="stu_id"><el-input-number v-model="form.stu_id" :min="1" /></el-form-item>
        <el-form-item label="班级ID" prop="class_id"><el-input-number v-model="form.class_id" :min="1" /></el-form-item>
        <el-form-item label="公司"><el-input v-model="form.company" /></el-form-item>
        <el-form-item label="薪资"><el-input-number v-model="form.salary" :min="0" :step="1000" /></el-form-item>
        <el-form-item label="开放时间"><el-date-picker v-model="form.open_time" :value-format="DATE_FORMAT" /></el-form-item>
        <el-form-item label="Offer时间"><el-date-picker v-model="form.offer_time" :value-format="DATE_FORMAT" /></el-form-item>
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
import { DATE_FORMAT, formatDate } from "@/constants/date";
defineOptions({ name: "SmsEmployment" });
const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({ pageNum: 1, pageSize: 10, stu_id: "", company: "" });
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = {
  stu_id: [{ required: true, message: "请输入学号", trigger: "blur" }],
  class_id: [{ required: true, message: "请输入班级ID", trigger: "blur" }],
};
async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getEmployments({ ...queryParams });
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
  queryParams.company = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) Object.assign(form, { ...row });
  else Object.assign(form, { class_id: 1 });
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.id;
  if (form.id) await SmsAPI.updateEmployment(Number(form.id), payload);
  else await SmsAPI.createEmployment(payload);
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该就业记录？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteEmployment(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
onMounted(fetchData);
</script>
