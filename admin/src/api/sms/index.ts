import request from "@/utils/request";
import type { PageResult } from "@/api/common";

export interface PageQuery {
  pageNum: number;
  pageSize: number;
  [key: string]: unknown;
}

function cleanParams(params: Record<string, unknown>) {
  const out: Record<string, unknown> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value === "" || value === null || value === undefined) return;
    out[key] = value;
  });
  return out;
}

function toPageParams(params: PageQuery) {
  const { pageNum, pageSize, ...rest } = params;
  return cleanParams({ page: pageNum, limit: pageSize, ...rest });
}

const SmsAPI = {
  getStudents(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/students",
      method: "get",
      params: toPageParams(params),
    });
  },
  createStudent(data: Record<string, unknown>) {
    return request({ url: "/api/v2/students", method: "post", data });
  },
  updateStudent(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/students/${id}`, method: "put", data });
  },
  deleteStudent(id: number) {
    return request({ url: `/api/v2/students/${id}`, method: "delete" });
  },
  resetStudentPassword(id: number) {
    return request({ url: `/api/v2/students/${id}/password-resets`, method: "post" });
  },

  getClasses(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/classes",
      method: "get",
      params: toPageParams(params),
    });
  },
  createClass(data: Record<string, unknown>) {
    return request({ url: "/api/v2/classes", method: "post", data });
  },
  updateClass(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/classes/${id}`, method: "put", data });
  },
  deleteClass(id: number) {
    return request({ url: `/api/v2/classes/${id}`, method: "delete" });
  },

  getTeachers(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/teachers",
      method: "get",
      params: toPageParams(params),
    });
  },
  createTeacher(data: Record<string, unknown>) {
    return request({ url: "/api/v2/teachers", method: "post", data });
  },
  updateTeacher(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/teachers/${id}`, method: "put", data });
  },
  deleteTeacher(id: number) {
    return request({ url: `/api/v2/teachers/${id}`, method: "delete" });
  },

  getScores(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/scores",
      method: "get",
      params: toPageParams(params),
    });
  },
  createScore(data: Record<string, unknown>) {
    return request({ url: "/api/v2/scores", method: "post", data });
  },
  updateScore(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/scores/${id}`, method: "put", data });
  },
  deleteScore(id: number) {
    return request({ url: `/api/v2/scores/${id}`, method: "delete" });
  },

  getEmployments(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/employments",
      method: "get",
      params: toPageParams(params),
    });
  },
  createEmployment(data: Record<string, unknown>) {
    return request({ url: "/api/v2/employments", method: "post", data });
  },
  updateEmployment(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/employments/${id}`, method: "put", data });
  },
  deleteEmployment(id: number) {
    return request({ url: `/api/v2/employments/${id}`, method: "delete" });
  },

  getDepartments(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/departments",
      method: "get",
      params: toPageParams(params),
    });
  },
  createDepartment(data: Record<string, unknown>) {
    return request({ url: "/api/v2/departments", method: "post", data });
  },
  updateDepartment(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/departments/${id}`, method: "put", data });
  },
  deleteDepartment(id: number) {
    return request({ url: `/api/v2/departments/${id}`, method: "delete" });
  },

  getConsultants(params: PageQuery) {
    return request<unknown, PageResult<Record<string, unknown>>>({
      url: "/api/v2/consultants",
      method: "get",
      params: toPageParams(params),
    });
  },
  createConsultant(data: Record<string, unknown>) {
    return request({ url: "/api/v2/consultants", method: "post", data });
  },
  updateConsultant(id: number, data: Record<string, unknown>) {
    return request({ url: `/api/v2/consultants/${id}`, method: "put", data });
  },
  deleteConsultant(id: number) {
    return request({ url: `/api/v2/consultants/${id}`, method: "delete" });
  },

  getOverview() {
    return request<unknown, Record<string, number>>({ url: "/api/v1/sms/overview", method: "get" });
  },
  getStat(path: string, params?: Record<string, unknown>) {
    return request<unknown, unknown[]>({ url: `/api/v1/sms/stats/${path}`, method: "get", params });
  },
};

export default SmsAPI;
