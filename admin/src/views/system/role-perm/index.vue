<template>
  <div class="page-container role-perm">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="never" header="角色列表">
          <el-table
            v-loading="loadingRoles"
            :data="roles"
            highlight-current-row
            border
            @current-change="onSelectRole"
          >
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="code" label="编码" width="140" />
          </el-table>
          <div class="hint">选中角色后，在右侧勾选菜单/按钮权限并保存。</div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>权限树{{ currentRole ? ` — ${currentRole.name}` : "" }}</span>
              <el-button
                v-hasPerm="'system:role:assign'"
                type="primary"
                :disabled="!currentRole || currentRole.code === 'SUPER_ADMIN'"
                :loading="saving"
                @click="save"
              >
                保存
              </el-button>
            </div>
          </template>
          <el-alert
            v-if="currentRole?.code === 'SUPER_ADMIN'"
            type="info"
            :closable="false"
            title="超级管理员拥有全部权限，请勿在此修改。"
            class="mb-3"
          />
          <el-tree
            v-if="currentRole"
            ref="treeRef"
            v-loading="loadingTree"
            :data="tree"
            node-key="id"
            show-checkbox
            default-expand-all
            :props="{ label: 'title', children: 'children' }"
          >
            <template #default="{ data }">
              <span>
                {{ data.title }}
                <el-tag v-if="data.type === 2" size="small" type="info" class="ml-1">按钮</el-tag>
                <el-tag v-else-if="data.perm" size="small" class="ml-1">{{ data.perm }}</el-tag>
              </span>
            </template>
          </el-tree>
          <el-empty v-else description="请选择左侧角色" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import type { ElTree } from "element-plus";
import RbacAPI, { type MenuTreeNode, type RbacRoleItem } from "@/api/system/rbac";

defineOptions({ name: "SysRolePerm" });

const loadingRoles = ref(false);
const loadingTree = ref(false);
const saving = ref(false);
const roles = ref<RbacRoleItem[]>([]);
const tree = ref<MenuTreeNode[]>([]);
const currentRole = ref<RbacRoleItem | null>(null);
const treeRef = ref<InstanceType<typeof ElTree>>();

async function loadRoles() {
  loadingRoles.value = true;
  try {
    roles.value = (await RbacAPI.getRoles()) || [];
  } finally {
    loadingRoles.value = false;
  }
}

async function loadTree() {
  loadingTree.value = true;
  try {
    tree.value = (await RbacAPI.getMenuTree()) || [];
  } finally {
    loadingTree.value = false;
  }
}

async function onSelectRole(row: RbacRoleItem | null) {
  currentRole.value = row;
  if (!row) return;
  const data = await RbacAPI.getRoleMenus(row.id);
  await nextTick();
  treeRef.value?.setCheckedKeys(data.menuIds || [], false);
}

async function save() {
  if (!currentRole.value || currentRole.value.code === "SUPER_ADMIN") return;
  const checked = treeRef.value?.getCheckedKeys(false) as number[];
  const half = treeRef.value?.getHalfCheckedKeys() as number[];
  const menuIds = [...new Set([...(checked || []), ...(half || [])])];
  saving.value = true;
  try {
    await RbacAPI.saveRoleMenus(currentRole.value.id, menuIds);
    ElMessage.success("已保存，相关用户重新登录后生效");
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadRoles(), loadTree()]);
});
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.mb-3 {
  margin-bottom: 12px;
}
.ml-1 {
  margin-left: 6px;
}
</style>
