import axios from "axios";

// 创建全局唯一的 Axios 实例
export const apiClient = axios.create({
  // 未来部署时，可以通过环境变量动态切换生产环境 API 域名
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  timeout: 15000, // 超时时间设为 15 秒（考虑到 AI Agent 响应可能较慢）
  headers: {
    "Content-Type": "application/json",
  },
});

// ==========================================
// 1. 请求拦截器 (Request Interceptor)
// ==========================================
apiClient.interceptors.request.use(
  (config) => {
    // 在发送请求前，从本地取出 Token 并塞入请求头
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("ai_bos_access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ==========================================
// 2. 响应拦截器 (Response Interceptor)
// ==========================================
apiClient.interceptors.response.use(
  (response) => {
    // 成功时：直接剥离 axios 默认的那层冗余的 `data` 包裹，让前端拿到的直接是业务数据
    return response.data;
  },
  (error) => {
    // 失败时：全局统一错误处理
    if (error.response) {
      const status = error.response.status;

      // 401 身份过期：直接踢回登录页并清空失效 Token
      if (status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("ai_bos_access_token");
          // 注意：由于多语言的存在，未来可能需要重定向到对应语言的 /login
          window.location.href = "/"; 
        }
      }
      
      // 可以在这里集成统一的全局 Toast 报错通知 (比如使用 sonner 或 Shadcn 的 useToast)
      console.error(`[API Error ${status}]:`, error.response.data?.detail || error.message);
    } else {
      // 网络断开或超时
      console.error("[Network Error]: Please check your connection.");
    }
    
    return Promise.reject(error);
  }
);