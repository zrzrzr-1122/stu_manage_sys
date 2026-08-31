<template>
  <div class="page-container">
    <el-card class="page-search" shadow="never">
      <el-form :inline="true" :model="query">
        <el-form-item label="关键字">
          <el-input v-model="query.keywords" clearable placeholder="用户名" @keyup.enter="fetchData" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">搜索</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="page-content" shadow="never">
      <div class="page-toolbar">
        <el-button v-hasPerm="'system:user:create'" type="primary" @click="openDialog()">新增用户</el-button>
      </div>
      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r" class="mr-1" size="small">{{ roleLabel(r) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="teacherId" label="教师ID" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-hasPerm="'system:user:edit'" type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button
              v-hasPerm="'system:user:delete'"
              type="danger"
              link
              :disabled="row.username === 'admin'"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="query.pageNum"
        v-model:limit="query.pageSize"
        class="page-pagination"
        @pagination="fetchData"
      />
    </el-card>

    <el-dialog v-model="visible" :title="form.id ? '编辑用户' : '新增用户'" width="480px">
      <el-form label-width="100px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item :label="form.id ? '新密码' : '密码'" :required="!form.id">
          <el-input v-model="form.password" type="password" show-password :placeholder="form.id ? '不填则不修改' : ''" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.roleCodes" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.code" :label="r.name" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="教师ID">
          <el-input-number v-model="form.teacherId" :min="0" controls-position="right" />
          <div class="tip">老师角色建议填写 ai0720_teacher.tid，用于本班数据范围</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
        <el-button @click="visible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import RbacAPI, { type RbacRoleItem, type RbacUserItem } from "@/api/system/rbac";

defineOptions({ name: "SysAccount" });

const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const list = ref<RbacUserItem[]>([]);
const total = ref(0);
const roles = ref<RbacRoleItem[]>([]);
const query = reactive({ pageNum: 1, pageSize: 10, keywords: "" });
const form = reactive<{
  id?: number;
  username: string;
  password: string;
  roleCodes: string[];
  teacherId: number | undefined;
}>({
  username: "",
  password: "",
  roleCodes: [],
  teacherId: undefined,
});

const roleMap: Record<string, string> = {
  SUPER_ADMIN: "超级管理员",
  DIRECTOR: "教导主任",
  TEACHER: "老师",
  ROOT: "超级管理员",
};

function roleLabel(code: string) {
  return roleMap[code] || code;
}

async function fetchData() {
  loading.value = true;
  try {
    const data = await RbacAPI.getUsers({ ...query });
    list.value = data.list || [];
    total.value = data.total || 0;
  } finally {
    loading.value = false;
  }
}

async function loadRoles() {
  roles.value = (await RbacAPI.getRoles()) || [];
}

function openDialog(row?: RbacUserItem) {
  form.id = row?.id;
  form.username = row?.username || "";
  form.password = "";
  form.roleCodes = [...(row?.roles || [])].filter((c) => c !== "ROOT");
  form.teacherId = row?.teacherId ?? undefined;
  visible.value = true;
}

async function submit() {
  if (!form.username.trim()) {
    ElMessage.warning("请输入用户名");
    return;
  }
  if (!form.id && !form.password) {
    ElMessage.warning("请设置密码");
    return;
  }
  if (!form.roleCodes.length) {
    ElMessage.warning("请选择角色");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      username: form.username.trim(),
      password: form.password || undefined,
      roleCodes: form.roleCodes,
      teacherId: form.teacherId || null,
    };
    if (form.id) {
      await RbacAPI.updateUser(form.id, payload as any);
    } else {
      await RbacAPI.createUser(payload as any);
    }
    ElMessage.success("保存成功");
    visible.value = false;
    fetchData();
  } finally {
    saving.value = false;
  }
}

function handleDelete(row: RbacUserItem) {
  ElMessageBox.confirm(`确认删除用户 ${row.username}？`, "提示", { type: "warning" }).then(async () => {
    await RbacAPI.deleteUser(row.id);
    ElMessage.success("已删除");
    fetchData();
  });
}

onMounted(async () => {
  await loadRoles();
  fetchData();
});
</script>

<style scoped>
.mr-1 {
  margin-right: 4px;
}
.tip {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
