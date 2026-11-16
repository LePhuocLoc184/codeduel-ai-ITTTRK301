import { createContext, useContext, useEffect, useState } from "react"
import api from "../api/axios"

const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(localStorage.getItem("token")))
  useEffect(() => {
    if (!localStorage.getItem("token")) return
    api.get("/api/v1/users/me").then(({ data }) => setUser(data.data)).catch((error) => {
      if (error.response?.status === 401) localStorage.removeItem("token")
      setUser(null)
    }).finally(() => setLoading(false))
  }, [])
  const login = async (credentials) => {
    const { data } = await api.post("/api/v1/auth/login", credentials)
    localStorage.setItem("token", data.data.access_token)
    setUser(data.data.user)
    return data.data.user
  }
  const register = async (payload) => {
    const { data } = await api.post("/api/v1/auth/register", payload)
    localStorage.setItem("token", data.data.access_token)
    setUser(data.data.user)
    return data.data.user
  }
  const logout = () => { localStorage.removeItem("token"); setUser(null) }
  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)
