import { createContext, useContext, useEffect, useState } from "react"
import api, { clearSession, getToken, readCachedUser, saveCachedUser, saveSession } from "../api/axios"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // Khôi phục ngay user đã lưu để tải lại trang không bị "mất đăng nhập" trong lúc chờ /users/me.
  const [user, setUser] = useState(() => (getToken() ? readCachedUser() : null))
  const [loading, setLoading] = useState(Boolean(getToken()))
  useEffect(() => {
    if (!getToken()) return
    api.get("/api/v1/users/me").then(({ data }) => {
      setUser(data.data)
      saveCachedUser(data.data)
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
    saveCachedUser(next)
    setUser(next)
  }
  return <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)