import request from "@/utils/request";

export interface RbacUserItem {
  id: number;
  username: string;
  teacherId: number | null;
  roles: string[];
}

export interface RbacRoleItem {
  id: number;
  code: string;
  name: string;
  remark?: string;
}

export interface MenuTreeNode {
  id: number;
  parentId: number;
  title: string;
  type: number;
  perm?: string;
  children?: MenuTreeNode[];
}

const BASE = "/api/v1/system";

const RbacAPI = {
  getUsers(params: { pageNum?: number; pageSize?: number; keywords?: string }) {
    return request<any, { list: RbacUserItem[]; total: number }>({
      url: `${BASE}/users`,
      method: "get",
      params,
    });
  },
  createUser(data: {
    username: string;
    password: string;
    roleCodes: string[];
    teacherId?: number | null;
  }) {
    return request({ url: `${BASE}/users`, method: "post", data });
  },
  updateUser(
    id: number,
    data: {
      username: string;
      password?: string;
      roleCodes: string[];
      teacherId?: number | null;
    }
  ) {
    return request({ url: `${BASE}/users/${id}`, method: "put", data });
  },
  deleteUser(id: number) {
    return request({ url: `${BASE}/users/${id}`, method: "delete" });
  },
  getRoles() {
    return request<any, RbacRoleItem[]>({ url: `${BASE}/roles`, method: "get" });
  },
  getMenuTree() {
    return request<any, MenuTreeNode[]>({ url: `${BASE}/menus/tree`, method: "get" });
  },
  getRoleMenus(roleId: number) {
    return request<any, { roleId: number; roleCode: string; menuIds: number[] }>({
      url: `${BASE}/roles/${roleId}/menus`,
      method: "get",
    });
  },
  saveRoleMenus(roleId: number, menuIds: number[]) {
    return request({
      url: `${BASE}/roles/${roleId}/menus`,
      method: "put",
      data: { menuIds },
    });
  },
};

export default RbacAPI;
