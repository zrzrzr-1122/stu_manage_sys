<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="姓名">
          <el-input v-model="queryParams.tname" clearable @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="班级ID">
          <el-input v-model="queryParams.class_id" clearable />
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
          <el-table-column prop="tid" label="编号" width="80" />
          <el-table-column prop="tname" label="姓名" width="120" />
          <el-table-column prop="sex" label="性别" width="80" />
          <el-table-column prop="class_id" label="班级ID" width="90" />
          <el-table-column prop="tstatus" label="状态" width="90" />
          <el-table-column prop="tphone" label="电话" min-width="140" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDelete(row.tid)">删除</el-button>
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
    <el-dialog v-model="visible" :title="form.tid ? '编辑教师' : '新增教师'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="姓名" prop="tname"><el-input v-model="form.tname" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.sex">
            <el-radio value="男">男</el-radio>
            <el-radio value="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="班级ID" prop="class_id"><el-input-number v-model="form.class_id" :min="1" /></el-form-item>
        <el-form-item label="电话" prop="tphone"><el-input v-model="form.tphone" /></el-form-item>
        <el-form-item label="在职状态"><el-input v-model="form.tstatus" /></el-form-item>
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
defineOptions({ name: "SmsTeacher" });
const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({ pageNum: 1, pageSize: 10, tname: "", class_id: "" });
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = {
  tname: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  class_id: [{ required: true, message: "请输入班级ID", trigger: "blur" }],
  tphone: [{ required: true, message: "请输入电话", trigger: "blur" }],
};
async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getTeachers({ ...queryParams });
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
  queryParams.tname = "";
  queryParams.class_id = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) Object.assign(form, { ...row });
  else Object.assign(form, { sex: "男", tstatus: "在职", class_id: 1 });
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.tid;
  if (form.tid) await SmsAPI.updateTeacher(Number(form.tid), payload);
  else await SmsAPI.createTeacher(payload);
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该教师？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteTeacher(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
onMounted(fetchData);
</script>
