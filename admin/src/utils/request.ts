import axios, { type InternalAxiosRequestConfig, type AxiosResponse } from "axios";
import qs from "qs";

import { ApiCodeEnum } from "@/enums/api";
import { useUserStoreHook } from "@/stores/user";
import { usePermissionStoreHook } from "@/stores/permission";
import { AuthStorage, redirectToLogin } from "@/utils/auth";
import type { ApiResult } from "@/api/common";

// 防止同一请求在 token 刷新后重复进入重试，导致死循环
const retriedRequests = new WeakSet<InternalAxiosRequestConfig>();

let lastErrorToastAt = 0;
let lastErrorToastMsg = "";

function toastError(message: string) {
  const now = Date.now();
  if (message === lastErrorToastMsg && now - lastErrorToastAt < 4000) {
    return;
  }
  lastErrorToastAt = now;
  lastErrorToastMsg = message;
  ElMessage.error(message);
}

function backendDownMessage() {
  const apiUrl = import.meta.env.VITE_APP_API_URL || "http://127.0.0.1:8000";
  return `后端未启动（${apiUrl}），请先运行 FastAPI`;
}

const http = axios.create({
  baseURL: import.meta.env.VITE_APP_BASE_API,
  timeout: 50000,
  headers: { "Content-Type": "application/json;charset=utf-8" },
  // 数组参数序列化为 ids=1&ids=2，而非 ids[]=1&ids[]=2
  paramsSerializer: (params) => qs.stringify(params, { arrayFormat: "repeat" }),
});

http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = AuthStorage.getAccessToken();

    // 约定：调用方设置 Authorization 为 "no-auth" 即跳过 token 注入
    if (config.headers.Authorization === "no-auth") {
      delete config.headers.Authorization;
    } else if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

http.interceptors.response.use(
  (response: AxiosResponse<ApiResult>): AxiosResponse | any => {
    const { responseType } = response.config;

    // 二进制数据直接透传
    if (responseType === "blob" || responseType === "arraybuffer") {
      return response;
    }

    const { code, data, msg } = response.data;

    if (code === ApiCodeEnum.SUCCESS) {
      return data;
    }

    const errorMessage =
      code === ApiCodeEnum.BACKEND_UNAVAILABLE ? msg || backendDownMessage() : msg || "系统出错";
    toastError(errorMessage);
    return Promise.reject(new Error(errorMessage));
  },

  async (error) => {
    const { config, response } = error;

    if (!response) {
      toastError(backendDownMessage());
      return Promise.reject(error);
    }

    const { code, msg } = (response.data || {}) as ApiResult;

    if (code === ApiCodeEnum.BACKEND_UNAVAILABLE) {
      toastError(msg || backendDownMessage());
      return Promise.reject(new Error(msg || backendDownMessage()));
    }

    // Token 过期
    if (code === ApiCodeEnum.ACCESS_TOKEN_INVALID) {
      if (!config || retriedRequests.has(config)) {
        await redirectToLogin("登录已过期，请重新登录");
        return Promise.reject(new Error("Token Invalid"));
      }

      retriedRequests.add(config);

      try {
        const userStore = useUserStoreHook();
        await userStore.refreshTokenOnce();

        const token = AuthStorage.getAccessToken();
        if (token) {
          config.headers.set("Authorization", `Bearer ${token}`);
        }

        return http(config);
      } catch {
        await redirectToLogin("登录已过期，请重新登录");
        return Promise.reject(new Error("Token refresh failed"));
      }
    }

    // Refresh token 失效
    if (code === ApiCodeEnum.REFRESH_TOKEN_INVALID) {
      await redirectToLogin("登录已过期，请重新登录", false);
      return Promise.reject(new Error("Token Invalid"));
    }

    // 权限不足
    if (code === ApiCodeEnum.PERMISSION_DENIED) {
      const permissionStore = usePermissionStoreHook();
      await permissionStore.refreshPermissions();
      toastError(msg || "权限不足");
      return Promise.reject(new Error(msg || "权限不足"));
    }

    toastError(msg || "请求失败");
    return Promise.reject(new Error(msg || "请求失败"));
  }
);

export default http;
