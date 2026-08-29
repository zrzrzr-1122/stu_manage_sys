<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="部门名称"><el-input v-model="queryParams.dname" clearable @keyup.enter="handleQuery" /></el-form-item>
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
          <el-table-column prop="did" label="ID" width="80" />
          <el-table-column prop="dname" label="部门名称" min-width="160" />
          <el-table-column prop="manager" label="负责人" width="120" />
          <el-table-column prop="phone" label="电话" width="140" />
          <el-table-column prop="dstatus" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.dstatus === 1 ? 'success' : 'info'">{{ row.dstatus === 1 ? "启用" : "停用" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDelete(row.did)">删除</el-button>
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
    <el-dialog v-model="visible" :title="form.did ? '编辑部门' : '新增部门'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="部门名称" prop="dname"><el-input v-model="form.dname" /></el-form-item>
        <el-form-item label="负责人" prop="manager"><el-input v-model="form.manager" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.dstatus">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
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
defineOptions({ name: "SmsDepartment" });
const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({ pageNum: 1, pageSize: 10, dname: "" });
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = {
  dname: [{ required: true, message: "请输入部门名称", trigger: "blur" }],
  manager: [{ required: true, message: "请输入负责人", trigger: "blur" }],
};
async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getDepartments({ ...queryParams });
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
  queryParams.dname = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) Object.assign(form, { ...row });
  else Object.assign(form, { dstatus: 1 });
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.did;
  if (form.did) await SmsAPI.updateDepartment(Number(form.did), payload);
  else await SmsAPI.createDepartment(payload);
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该部门？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteDepartment(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
onMounted(fetchData);
</script>
