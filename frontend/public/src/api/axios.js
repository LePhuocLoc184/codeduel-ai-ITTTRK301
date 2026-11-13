import axios from "axios"

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || "/").replace(/\/$/, ""),
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

export default api

export function getApiErrorMessage(error, fallback) {
  const response = error?.response?.data
  if (response?.message) return response.message
  const details = response?.error?.details
  if (Array.isArray(details) && details.length) {
    return details.map((item) => item.msg || item.message).filter(Boolean).join("; ")
  }
  if (typeof details === "string" && details) return details
  if (!error?.response) {
    return "Không kết nối được backend. Hãy kiểm tra API đang chạy tại localhost:8000 rồi thử lại."
  }
  return fallback
}
