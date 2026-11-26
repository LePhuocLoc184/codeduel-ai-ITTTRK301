import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom"
import MainLayout from "../layouts/MainLayout"
import Dashboard from "../pages/Dashboard"
import Welcome from "../pages/Welcome"
import Login from "../pages/Login"
import Register from "../pages/Register"
import Arena from "../pages/Arena"
import Room from "../pages/Room"
import Matchmaking from "../pages/Matchmaking"

const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <Welcome /> },
      { path: "/home", element: <Dashboard /> },
      { path: "/login", element: <Login /> },
      { path: "/register", element: <Register /> },
      { path: "/arena", element: <Arena /> },
      { path: "/matchmaking", element: <Matchmaking /> },
    ],
  },
  // Combat Zen Mode: /room/:roomCode is outside MainLayout to use the full viewport.
  { path: "/room/:roomCode", element: <Room /> },
  { path: "*", element: <Navigate to="/" replace /> },
])

export default function AppRoutes() {
  return <RouterProvider router={router} />
}