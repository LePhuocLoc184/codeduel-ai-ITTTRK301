import React from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import { AuthProvider } from "./context/AuthContext"
import { ToastProvider } from "./context/ToastContext"
import "./index.css"

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ToastProvider><AuthProvider><App /></AuthProvider></ToastProvider>
  </React.StrictMode>,
)
