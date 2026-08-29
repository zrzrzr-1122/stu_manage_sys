<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="姓名"><el-input v-model="queryParams.cname" clearable @keyup.enter="handleQuery" /></el-form-item>
        <el-form-item label="部门ID"><el-input v-model="queryParams.did" clearable /></el-form-item>
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
          <el-table-column prop="cid" label="ID" width="80" />
          <el-table-column prop="cname" label="姓名" width="120" />
          <el-table-column prop="sex" label="性别" width="80" />
          <el-table-column prop="phone" label="电话" width="140" />
          <el-table-column prop="did" label="部门ID" width="90" />
          <el-table-column prop="position" label="职位" min-width="120" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 0 ? 'success' : 'info'">{{ row.status === 0 ? "在职" : "离职" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openDialog(row)">编辑</el-button>
              <el-button type="danger" link @click="handleDelete(row.cid)">删除</el-button>
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
    <el-dialog v-model="visible" :title="form.cid ? '编辑顾问' : '新增顾问'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="姓名" prop="cname"><el-input v-model="form.cname" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.sex">
            <el-radio value="男">男</el-radio>
            <el-radio value="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="电话" prop="phone"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="部门ID" prop="did"><el-input-number v-model="form.did" :min="1" /></el-form-item>
        <el-form-item label="职位"><el-input v-model="form.position" /></el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="0">在职</el-radio>
            <el-radio :value="1">离职</el-radio>
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
defineOptions({ name: "SmsConsultant" });
const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({ pageNum: 1, pageSize: 10, cname: "", did: "" });
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = {
  cname: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  phone: [{ required: true, message: "请输入电话", trigger: "blur" }],
  did: [{ required: true, message: "请输入部门ID", trigger: "blur" }],
};
async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getConsultants({ ...queryParams });
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
  queryParams.cname = "";
  queryParams.did = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) Object.assign(form, { ...row });
  else Object.assign(form, { sex: "男", status: 0, position: "初级顾问", did: 1 });
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.cid;
  if (form.cid) await SmsAPI.updateConsultant(Number(form.cid), payload);
  else await SmsAPI.createConsultant(payload);
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该顾问？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteConsultant(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
onMounted(fetchData);
</script>
