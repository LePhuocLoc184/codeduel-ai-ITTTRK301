import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { Code2, LogOut, UserRound } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import Avatar from "./Avatar"
import AccountPanel from "./AccountPanel"

const HOME_SECTIONS = ["features", "leaderboard"]

export default function Navbar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [section, setSection] = useState("home")

  // Làm sáng đúng mục menu theo vị trí cuộn trên trang chủ, không phụ thuộc vào #hash trên URL.
  useEffect(() => {
    if (pathname !== "/home") return undefined
    const update = () => {
      const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2
      let current = "home"
      for (const id of HOME_SECTIONS) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top <= 120) current = id
      }
      if (atBottom && current !== "home") current = HOME_SECTIONS[HOME_SECTIONS.length - 1]
      setSection(current)
    }
    update()
    window.addEventListener("scroll", update, { passive: true })
    window.addEventListener("resize", update)
    return () => {
      window.removeEventListener("scroll", update)
      window.removeEventListener("resize", update)
    }
  }, [pathname])

  const navClass = (name) => (pathname === "/home" && section === name ? "active" : undefined)
  const [accountOpen, setAccountOpen] = useState(false)
  return <header className="topbar"><Link className="brand" to="/home"><span className="brand-mark"><Code2 size={20} /></span><span>code<span className="brand-accent">duel</span><small>.dev</small></span></Link>
    <nav className="nav-links"><Link className={navClass("home")} to="/home">Trang chủ</Link><Link className={navClass("features")} to="/home#features">Tính năng</Link><Link className={navClass("leaderboard")} to="/home#leaderboard">Bảng xếp hạng</Link></nav>
    <div className="nav-actions">{loading && !user ? null : user ? <><button type="button" className="user-chip user-chip-button" onClick={() => setAccountOpen(true)} aria-haspopup="dialog" aria-label="Mở thông tin tài khoản">{user.avatar_url ? <Avatar url={user.avatar_url} name={user.username} className="avatar-sm"/> : <UserRound size={15}/>}{user.username}</button><button className="icon-button" aria-label="Đăng xuất" onClick={() => { logout(); navigate("/") }}><LogOut size={17}/></button>{accountOpen && <AccountPanel onClose={() => setAccountOpen(false)} />}</> : <><Link className="nav-login" to="/login">Đăng nhập</Link><Link className="button button-small" to="/register">Bắt đầu <span>↗</span></Link></>}</div>
  </header>
}