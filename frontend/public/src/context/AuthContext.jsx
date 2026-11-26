import { createContext, useContext, useEffect, useRef, useState } from "react"
import api, { clearSession, getToken, readCachedUser, saveCachedUser, saveSession } from "../api/axios"
import { useToast } from "./ToastContext"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const toast = useToast()
  const expirationNotified = useRef(false)
  // Khôi phục ngay user đã lưu để tải lại trang không bị "mất đăng nhập" trong lúc chờ /users/me.
  const [user, setUser] = useState(() => (getToken() ? readCachedUser() : null))
  const [loading, setLoading] = useState(Boolean(getToken()))

  useEffect(() => {
    const interceptorId = api.interceptors.response.use(
      (response) => response,
      (error) => {
        const requestUrl = error.config?.url || ""
        const isAuthRequest = /\/api\/v1\/auth\/(?:login|register)\/?$/.test(requestUrl)
        if (error.response?.status === 401 && !isAuthRequest && getToken() && !expirationNotified.current) {
          expirationNotified.current = true
          clearSession()
          setUser(null)
          toast.warning("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
        }
        return Promise.reject(error)
      },
    )
    return () => api.interceptors.response.eject(interceptorId)
  }, [toast])

  useEffect(() => {
    if (!getToken()) return
    api.get("/api/v1/users/me").then(({ data }) => {
      setUser(data.data)
      saveCachedUser(data.data)
    }).catch((error) => {
      // The response interceptor clears an invalid session; network and server errors preserve it.
      if (error.response?.status === 401) return
    }).finally(() => setLoading(false))
  }, [])
  const login = async (credentials) => {
    const { data } = await api.post("/api/v1/auth/login", credentials)
    saveSession(data.data.access_token, data.data.user)
    setUser(data.data.user)
    expirationNotified.current = false
    return data.data.user
  }
  const register = async (payload) => {
    const { data } = await api.post("/api/v1/auth/register", payload)
    saveSession(data.data.access_token, data.data.user)
    setUser(data.data.user)
    expirationNotified.current = false
    return data.data.user
  }
  const logout = () => {
    clearSession()
    setUser(null)
    toast.success("Bạn đã đăng xuất.")
  }
  // Gộp thông tin mới (vd. avatar_url sau khi PUT /users/me) vào user đang đăng nhập và cache lại.
  const updateUser = (patch) => {
    const next = { ...user, ...patch }
    saveCachedUser(next)
    setUser(next)
  }
  return <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)