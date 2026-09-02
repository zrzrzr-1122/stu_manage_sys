<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="班级编号">
          <el-input v-model="queryParams.class_id" clearable @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="班主任">
          <el-input v-model="queryParams.head_teacher" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card class="page-content" shadow="never">
      <div class="page-toolbar">
        <el-button type="primary" @click="openDialog()">新增</el-button>
      </div>
      <div class="page-table-wrapper">
        <el-table v-loading="loading" class="page-table" :data="list" height="100%" border>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="class_id" label="班级编号" min-width="120" />
          <el-table-column prop="start_time" label="开课时间" min-width="160">
            <template #default="{ row }">{{ formatDateTime(row.start_time) }}</template>
          </el-table-column>
          <el-table-column prop="head_teacher" label="班主任" width="120" />
          <el-table-column prop="teacher" label="授课老师" width="120" />
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
    <el-dialog v-model="visible" :title="form.id ? '编辑班级' : '新增班级'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="班级编号" prop="class_id"><el-input v-model="form.class_id" /></el-form-item>
        <el-form-item label="开课时间">
          <el-date-picker v-model="form.start_time" type="datetime" :value-format="DATETIME_FORMAT" />
        </el-form-item>
        <el-form-item label="班主任"><el-input v-model="form.head_teacher" /></el-form-item>
        <el-form-item label="授课老师"><el-input v-model="form.teacher" /></el-form-item>
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
import { DATETIME_FORMAT, formatDateTime } from "@/constants/date";
defineOptions({ name: "SmsClass" });
const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({ pageNum: 1, pageSize: 10, class_id: "", head_teacher: "" });
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = { class_id: [{ required: true, message: "请输入班级编号", trigger: "blur" }] };
async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getClasses({ ...queryParams });
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
  queryParams.class_id = "";
  queryParams.head_teacher = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) Object.assign(form, { ...row });
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.id;
  if (form.id) await SmsAPI.updateClass(Number(form.id), payload);
  else await SmsAPI.createClass(payload);
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该班级？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteClass(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
onMounted(fetchData);
</script>
