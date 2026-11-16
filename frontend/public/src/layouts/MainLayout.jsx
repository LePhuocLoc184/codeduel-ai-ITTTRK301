import { useEffect } from "react"
import { Outlet, useLocation } from "react-router-dom"
import Navbar from "../components/Navbar"
import Footer from "../components/Footer"

export default function MainLayout() {
  const { pathname, hash } = useLocation()
  // Điều hướng trong SPA không tự cuộn tới #anchor, nên xử lý ở đây.
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" })
    else window.scrollTo(0, 0)
  }, [pathname, hash])
  return <div className="app-shell"><Navbar /><main className="page-main"><Outlet /></main><Footer /></div>
}