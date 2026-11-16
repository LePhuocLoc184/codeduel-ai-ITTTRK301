import { Outlet } from "react-router-dom"
import Navbar from "../components/Navbar"
import Footer from "../components/Footer"

export default function MainLayout() {
  return <div className="app-shell"><Navbar /><main className="page-main"><Outlet /></main><Footer /></div>
}
