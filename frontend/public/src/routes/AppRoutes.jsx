import { Navigate, Route, Routes } from "react-router-dom"
import MainLayout from "../layouts/MainLayout"
import Dashboard from "../pages/Dashboard"
import Welcome from "../pages/Welcome"
import Login from "../pages/Login"
import Register from "../pages/Register"
import Arena from "../pages/Arena"
import Room from "../pages/Room"

export default function AppRoutes() {
  return <Routes>
    <Route element={<MainLayout />}>
      <Route path="/" element={<Welcome />} />
      <Route path="/home" element={<Dashboard />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/arena" element={<Arena />} />
      <Route path="/room/:roomCode" element={<Room />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  </Routes>
}
