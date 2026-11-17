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

const BACKEND_DOWN_MESSAGE =
  "Không kết nối được backend. Hãy kiểm tra API đang chạy tại localhost:8000 (và kết nối PostgreSQL) rồi thử lại."

const FIELD_LABELS = {
  username: "Tên người dùng",
  email: "Email",
  password: "Mật khẩu",
}

// Backend (Pydantic) trả thông báo lỗi validation bằng tiếng Anh; dịch các câu hay gặp.
const DETAIL_TRANSLATIONS = [
  [/special-use or reserved name/i, "tên miền không hợp lệ (không dùng được đuôi như .local, .test)"],
  [/should have a period|not valid\. It should have a period/i, "thiếu tên miền hợp lệ, ví dụ ten@gmail.com"],
  [/must have an @-sign|@-sign/i, "phải có ký tự @, ví dụ ten@gmail.com"],
  [/not a valid email address/i, "địa chỉ email không hợp lệ"],
  [/at least (\d+) characters/i, (match, count) => `cần ít nhất ${count} ký tự`],
  [/field required/i, "không được để trống"],
]

function translateDetail(text) {
  for (const [pattern, replacement] of DETAIL_TRANSLATIONS) {
    const match = text.match(pattern)
    if (match) return typeof replacement === "function" ? replacement(...match) : replacement
  }
  return text
}

function validationMessage(details) {
  return details
    .map((item) => {
      const field = String(item.loc || "").split("->").pop().trim()
      const raw = String(item.msg || item.message || "").replace(/^Value error,\s*/i, "")
      const text = translateDetail(raw)
      const label = FIELD_LABELS[field]
      return label && text ? `${label}: ${text}` : text
    })
    .filter(Boolean)
    .join("; ")
}

export function getApiErrorMessage(error, fallback) {
  const response = error?.response?.data
  const status = error?.response?.status
  const isApiPayload = Boolean(response) && typeof response === "object"

  if (isApiPayload) {
    const details = response.error?.details
    // Lỗi 422: `message` của backend chỉ là câu chung chung, lý do thật nằm trong error.details.
    if (response.error?.code === "VALIDATION_ERROR" && Array.isArray(details) && details.length) {
      const message = validationMessage(details)
      if (message) return message
    }
    // Lỗi 500 chung của backend: ở môi trường dev kèm nguyên nhân thật (error.details) để dễ tìm ra lỗi.
    if (import.meta.env.DEV && response.error?.code === "INTERNAL_SERVER_ERROR" && typeof details === "string" && details) {
      return `${response.message || "Lỗi hệ thống"} — chi tiết: ${details.slice(0, 300)}`
    }
    if (response.message) return response.message
    if (Array.isArray(details) && details.length) {
      return details.map((item) => item.msg || item.message).filter(Boolean).join("; ")
    }
    if (typeof details === "string" && details) return details
  }

  if (error?.code === "ECONNABORTED") return "Backend phản hồi quá chậm. Vui lòng thử lại sau."
  // Không có phản hồi, hoặc proxy trả 5xx dạng text/HTML khi backend chưa chạy.
  if (!error?.response || (!isApiPayload && status >= 500)) return BACKEND_DOWN_MESSAGE
  return fallback
}
