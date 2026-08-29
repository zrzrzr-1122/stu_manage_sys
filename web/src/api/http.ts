import axios from "axios";

const http = axios.create({
  baseURL: "/api/v1/portal",
  timeout: 20000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("portal_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body && body.code === "00000") {
      return body.data;
    }
    return Promise.reject(new Error(body?.msg || "请求失败"));
  },
  (error) => {
    if (!error.response) {
      return Promise.reject(new Error("后端未启动（http://127.0.0.1:8000），请先运行 FastAPI"));
    }
    const body = error.response.data;
    if (body?.code === "A0500") {
      return Promise.reject(new Error(body.msg || "后端未启动"));
    }
    const msg = body?.msg || error.message || "网络异常";
    if (error.response?.status === 401) {
      localStorage.removeItem("portal_token");
      if (location.pathname !== "/login") {
        location.href = "/login";
      }
    }
    return Promise.reject(new Error(msg));
  }
);

export default http;
