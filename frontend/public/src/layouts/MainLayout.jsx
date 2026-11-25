import { useEffect } from "react"
import { Outlet, useLocation } from "react-router-dom"
import Navbar from "../components/Navbar"
import Footer from "../components/Footer"

export default function MainLayout() {
  const { pathname, hash, key } = useLocation()
  // Điều hướng trong SPA không tự cuộn tới #anchor, nên xử lý ở đây.
  // Dùng thêm `key` (đổi sau mỗi lần bấm link, kể cả khi URL giữ nguyên) để bấm lại
  // "Tính năng" / "Bảng xếp hạng" / "Trang chủ" vẫn cuộn được dù người dùng đã tự cuộn đi chỗ khác.
  useEffect(() => {
    const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior })
    else window.scrollTo({ top: 0, behavior })
  }, [pathname, hash, key])
  return <div className="app-shell"><Navbar /><main className="page-main"><Outlet /></main><Footer /></div>
}