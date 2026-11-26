import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import "./Toast.css"

const ToastContext = createContext(null)

function ToastItem({ item, onDismiss }) {
  const { id, type, message } = item

  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(id), 3500)
    return () => window.clearTimeout(timer)
  }, [id, onDismiss])

  return (
    <div className={`toast-notification toast-${type}`} role={type === "error" || type === "warning" ? "alert" : "status"}>
      <span className="toast-message">{message}</span>
      <button type="button" className="toast-close" aria-label="Đóng thông báo" onClick={() => onDismiss(id)}>
        ×
      </button>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const nextId = useRef(0)

  const dismiss = useCallback((id) => {
    setItems((current) => current.filter((item) => item.id !== id))
  }, [])

  const show = useCallback((type, message) => {
    const text = String(message ?? "").trim()
    if (!text) throw new Error("Toast messages must not be empty.")
    const id = ++nextId.current
    setItems((current) => [...current.slice(-2), { id, type, message: text }])
    return id
  }, [])

  const toast = useMemo(() => ({
    success: (message) => show("success", message),
    error: (message) => show("error", message),
    warning: (message) => show("warning", message),
  }), [show])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-viewport" aria-label="Thông báo" aria-live="polite">
        {items.map((item) => <ToastItem key={item.id} item={item} onDismiss={dismiss} />)}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const toast = useContext(ToastContext)
  if (!toast) throw new Error("useToast must be used within a ToastProvider.")
  return toast
}
