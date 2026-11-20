import axios from "axios"

const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || "/").replace(/\/$/, ""),
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = getToken()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

export default api

// ===== Phiên đăng nhập theo từng tab =====
// Phiên đăng nhập theo từng tab.
//
// Trước đây token và user chỉ nằm trong localStorage, thứ mà MỌI tab của cùng một trình duyệt dùng chung:
// đăng nhập tài khoản B ở tab 2 làm tab 1 (đang là A) cũng gửi request bằng token của B. Hai tab thành
// cùng một người nên hàng đợi ghép trận không bao giờ ghép được (backend không ghép một người với chính mình).
//
// Giờ mỗi tab giữ phiên riêng trong sessionStorage. localStorage chỉ còn là "phiên gần nhất" để tab mới mở
// hoặc lần mở trình duyệt sau vẫn đăng nhập sẵn; tab nhận phiên đó sẽ ghim vào sessionStorage ngay lập tức,
// nên đăng nhập tài khoản khác ở tab khác không còn làm đổi tài khoản của tab này.

const TOKEN_KEY = "token"
const USER_KEY = "user"

const read = (storage, key) => {
  try {
    return storage.getItem(key)
  } catch {
    return null
  }
}
const write = (storage, key, value) => {
  try {
    storage.setItem(key, value)
  } catch {
    // Trình duyệt chặn lưu trữ: bỏ qua, phiên chỉ sống trong bộ nhớ trang.
  }
}
const remove = (storage, key) => {
  try {
    storage.removeItem(key)
  } catch {
    // Không có gì để xóa.
  }
}

export function getToken() {
  const own = read(sessionStorage, TOKEN_KEY)
  if (own) return own

  const shared = read(localStorage, TOKEN_KEY)
  if (!shared) return null

  // Tab mới: nhận phiên gần nhất rồi ghim lại cho riêng tab này.
  write(sessionStorage, TOKEN_KEY, shared)
  const sharedUser = read(localStorage, USER_KEY)
  if (sharedUser) write(sessionStorage, USER_KEY, sharedUser)
  return shared
}

export function readCachedUser() {
  try {
    return JSON.parse(read(sessionStorage, USER_KEY) || read(localStorage, USER_KEY) || "null")
  } catch {
    return null
  }
}

export function saveSession(token, user) {
  const serialized = JSON.stringify(user)
  write(sessionStorage, TOKEN_KEY, token)
  write(sessionStorage, USER_KEY, serialized)
  write(localStorage, TOKEN_KEY, token)
  write(localStorage, USER_KEY, serialized)
}

// Cập nhật bản cache user của tab này; chỉ ghi vào localStorage khi nó đang giữ đúng tài khoản này,
// tránh đè thông tin của tài khoản khác đã đăng nhập ở tab khác.
export function saveCachedUser(user) {
  const serialized = JSON.stringify(user)
  write(sessionStorage, USER_KEY, serialized)

  if (read(localStorage, TOKEN_KEY) === read(sessionStorage, TOKEN_KEY)) {
    write(localStorage, USER_KEY, serialized)
  }
}

export function clearSession() {
  const own = read(sessionStorage, TOKEN_KEY)

  // Chỉ xóa phiên chia sẻ nếu nó là của chính tab này, không đăng xuất nhầm tài khoản của tab khác.
  if (!own || read(localStorage, TOKEN_KEY) === own) {
    remove(localStorage, TOKEN_KEY)
    remove(localStorage, USER_KEY)
  }

  remove(sessionStorage, TOKEN_KEY)
  remove(sessionStorage, USER_KEY)
}

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