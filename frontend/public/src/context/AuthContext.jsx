import { createContext, useContext, useEffect, useState } from "react"
import api from "../api/axios"

const AuthContext = createContext(null)

const readCachedUser = () => {
  try {
    return JSON.parse(localStorage.getItem("user") || "null")
  } catch {
    return null
  }
}
const saveSession = (token, user) => {
  localStorage.setItem("token", token)
  localStorage.setItem("user", JSON.stringify(user))
}
const clearSession = () => {
  localStorage.removeItem("token")
  localStorage.removeItem("user")
}

export function AuthProvider({ children }) {
  // Khôi phục ngay user đã lưu để tải lại trang không bị "mất đăng nhập" trong lúc chờ /users/me.
  const [user, setUser] = useState(() => (localStorage.getItem("token") ? readCachedUser() : null))
  const [loading, setLoading] = useState(Boolean(localStorage.getItem("token")))
  useEffect(() => {
    if (!localStorage.getItem("token")) return
    api.get("/api/v1/users/me").then(({ data }) => {
      setUser(data.data)
      localStorage.setItem("user", JSON.stringify(data.data))
    }).catch((error) => {
      // Chỉ đăng xuất khi server xác nhận token không hợp lệ (401).
      // Lỗi mạng / 5xx / timeout chỉ là tạm thời nên giữ nguyên phiên đăng nhập.
      if (error.response?.status === 401) { clearSession(); setUser(null) }
    }).finally(() => setLoading(false))
  }, [])
  const login = async (credentials) => {
    const { data } = await api.post("/api/v1/auth/login", credentials)
    saveSession(data.data.access_token, data.data.user)
    setUser(data.data.user)
    return data.data.user
  }
  const register = async (payload) => {
    const { data } = await api.post("/api/v1/auth/register", payload)
    saveSession(data.data.access_token, data.data.user)
    setUser(data.data.user)
    return data.data.user
  }
  const logout = () => { clearSession(); setUser(null) }
  // Gộp thông tin mới (vd. avatar_url sau khi PUT /users/me) vào user đang đăng nhập và cache lại.
  const updateUser = (patch) => {
    const next = { ...user, ...patch }
    localStorage.setItem("user", JSON.stringify(next))
    setUser(next)
  }
  return <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)