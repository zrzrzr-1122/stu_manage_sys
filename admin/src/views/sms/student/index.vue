<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="学号">
          <el-input
            v-model="queryParams.stu_id"
            placeholder="精确查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input
            v-model="queryParams.stu_name"
            placeholder="支持模糊查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="班级">
          <el-input
            v-model="queryParams.class_id"
            placeholder="支持模糊查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="籍贯">
          <el-input
            v-model="queryParams.address"
            placeholder="支持模糊查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="学历">
          <el-input
            v-model="queryParams.education"
            placeholder="支持模糊查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="专业">
          <el-input
            v-model="queryParams.major"
            placeholder="支持模糊查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="年龄">
          <el-input
            v-model="queryParams.age"
            placeholder="精确查询"
            clearable
            style="width: 130px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="queryParams.sex" placeholder="全部" clearable style="width: 100px">
            <el-option label="男" value="男" />
            <el-option label="女" value="女" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="page-content" shadow="never">
      <div class="page-toolbar">
        <div class="page-toolbar__left">
          <el-button v-hasPerm="'sms:student:create'" type="primary" @click="openDialog()">新增</el-button>
        </div>
      </div>
      <div class="page-table-wrapper">
        <el-table v-loading="loading" class="page-table" :data="list" height="100%" border>
          <el-table-column prop="stu_id" label="学号" width="80" />
          <el-table-column prop="stu_name" label="姓名" width="100" />
          <el-table-column prop="sex" label="性别" width="70" />
          <el-table-column prop="age" label="年龄" width="70" />
          <el-table-column prop="class_id" label="班级ID" width="90" />
          <el-table-column prop="education" label="学历" width="90" />
          <el-table-column prop="major" label="专业" min-width="120" show-overflow-tooltip />
          <el-table-column prop="address" label="籍贯" min-width="120" show-overflow-tooltip />
          <el-table-column prop="counselor" label="顾问编号" width="100" />
          <el-table-column label="操作" fixed="right" width="220">
            <template #default="{ row }">
              <el-button v-hasPerm="'sms:student:edit'" type="primary" link @click="openDialog(row)">编辑</el-button>
              <el-button v-hasPerm="'sms:student:reset_pwd'" type="primary" link @click="resetPwd(row.stu_id)">重置密码</el-button>
              <el-button v-hasPerm="'sms:student:delete'" type="danger" link @click="handleDelete(row.stu_id)">删除</el-button>
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

    <el-dialog v-model="visible" :title="form.stu_id ? '编辑学生' : '新增学生'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="姓名" prop="stu_name">
          <el-input v-model="form.stu_name" :disabled="!!form.stu_id && !canEditName" />
        </el-form-item>
        <el-form-item label="班级ID" prop="class_id">
          <el-input-number v-model="form.class_id" :min="1" class="w-full" />
        </el-form-item>
        <el-form-item label="性别" prop="sex">
          <el-radio-group v-model="form.sex">
            <el-radio value="男">男</el-radio>
            <el-radio value="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="年龄" prop="age">
          <el-input-number v-model="form.age" :min="1" />
        </el-form-item>
        <el-form-item label="籍贯" prop="address">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-form-item label="毕业学校">
          <el-input v-model="form.graduateSchool" />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="form.major" />
        </el-form-item>
        <el-form-item label="学历" prop="education">
          <el-input v-model="form.education" />
        </el-form-item>
        <el-form-item label="入学时间">
          <el-date-picker v-model="form.startTime" :value-format="DATE_FORMAT" />
        </el-form-item>
        <el-form-item label="毕业时间">
          <el-date-picker v-model="form.endTime" :value-format="DATE_FORMAT" />
        </el-form-item>
        <el-form-item label="顾问编号" prop="counselor">
          <el-input-number v-model="form.counselor" :min="1" />
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
import { hasPerm } from "@/utils/auth";
import { DATE_FORMAT } from "@/constants/date";

defineOptions({ name: "SmsStudent" });

const canEditName = computed(() => hasPerm("sms:student:edit_name"));

const loading = ref(false);
const list = ref<Record<string, unknown>[]>([]);
const total = ref(0);
const visible = ref(false);
const formRef = ref<FormInstance>();
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  stu_id: "",
  stu_name: "",
  class_id: "",
  address: "",
  education: "",
  major: "",
  age: "",
  sex: "",
});
const form = reactive<Record<string, unknown>>({});
const rules: FormRules = {
  stu_name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  class_id: [{ required: true, message: "请输入班级ID", trigger: "blur" }],
  address: [{ required: true, message: "请输入籍贯", trigger: "blur" }],
  education: [{ required: true, message: "请输入学历", trigger: "blur" }],
  counselor: [{ required: true, message: "请输入顾问编号", trigger: "blur" }],
  age: [{ required: true, message: "请输入年龄", trigger: "blur" }],
};

async function fetchData() {
  loading.value = true;
  try {
    const data = await SmsAPI.getStudents({ ...queryParams });
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
  queryParams.class_id = "";
  queryParams.address = "";
  queryParams.education = "";
  queryParams.major = "";
  queryParams.age = "";
  queryParams.sex = "";
  handleQuery();
}
function openDialog(row?: Record<string, unknown>) {
  Object.keys(form).forEach((k) => delete form[k]);
  if (row) {
    Object.assign(form, { ...row });
  } else {
    Object.assign(form, { sex: "男", age: 20, class_id: 1, counselor: 1 });
  }
  visible.value = true;
}
async function submit() {
  await formRef.value?.validate();
  const payload = { ...form };
  delete payload.stu_id;
  delete payload.password_md5;
  delete payload.is_delete;
  if (form.stu_id) {
    await SmsAPI.updateStudent(Number(form.stu_id), payload);
  } else {
    await SmsAPI.createStudent(payload);
  }
  ElMessage.success("保存成功");
  visible.value = false;
  fetchData();
}
function handleDelete(id: number) {
  ElMessageBox.confirm("确认删除该学生？", "提示", { type: "warning" }).then(async () => {
    await SmsAPI.deleteStudent(id);
    ElMessage.success("删除成功");
    fetchData();
  });
}
function resetPwd(id: number) {
  ElMessageBox.confirm("确认重置为默认密码 123456？", "提示").then(async () => {
    await SmsAPI.resetStudentPassword(id);
    ElMessage.success("已重置");
  });
}
onMounted(fetchData);
</script>
