import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { LogOut, Swords, UserRound } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import Avatar from "./Avatar"
import AccountPanel from "./AccountPanel"
import BrandLogo from "./BrandLogo"
import api from "../api/axios"
import useMotionPreference from "../hooks/useMotionPreference"

const HOME_SECTIONS = ["features", "leaderboard"]

export default function Navbar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const viewTransition = useMotionPreference()
  const { pathname } = useLocation()
  const [section, setSection] = useState("home")
  const [activeRoom, setActiveRoom] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("codeduel_active_room") || "null")
      return saved?.room_code ? saved : null
    } catch {
      return null
    }
  })

  // Kiểm tra tính hợp lệ của activeRoom: nếu phòng đã kết thúc thì dọn cache
  useEffect(() => {
    if (!activeRoom?.room_code) return
    let active = true
    api.get(`/api/v1/rooms/${activeRoom.room_code}`)
      .then(({ data }) => {
        if (!active) return
        const status = data.data?.status
        if (status === "FINISHED" || status === "CANCELLED") {
          setActiveRoom(null)
          localStorage.removeItem("codeduel_active_room")
        }
      })
      .catch((err) => {
        if (!active) return
        if (err.response?.status === 404) {
          setActiveRoom(null)
          localStorage.removeItem("codeduel_active_room")
        }
      })
    return () => { active = false }
  }, [activeRoom?.room_code, pathname])

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

  const navClass = (name) => {
    if (name === "arena") return pathname === "/arena" || pathname === "/matchmaking" ? "active" : undefined
    return pathname === "/home" && section === name ? "active" : undefined
  }
  const [accountOpen, setAccountOpen] = useState(false)
  return <header className="topbar"><Link className="brand" to="/home" viewTransition={viewTransition}><BrandLogo size={32} /></Link>
    <nav className="nav-links">
      <Link className={navClass("home")} aria-current={navClass("home") ? "page" : undefined} to="/home" viewTransition={viewTransition}>Trang chủ</Link>
      <Link className={navClass("features")} aria-current={navClass("features") ? "location" : undefined} to="/home#features" viewTransition={viewTransition}>Tính năng</Link>
      <Link className={navClass("leaderboard")} aria-current={navClass("leaderboard") ? "location" : undefined} to="/home#leaderboard" viewTransition={viewTransition}>Bảng xếp hạng</Link>
      {user && <Link className={navClass("arena")} aria-current={navClass("arena") ? "page" : undefined} to="/arena" viewTransition={viewTransition}>Sảnh đấu</Link>}
    </nav>
    <div className="nav-actions">
      {activeRoom?.room_code && !pathname.startsWith("/room/") && (
        <Link to={`/room/${activeRoom.room_code}`} className="active-match-nav-chip" title="Quay lại trận đấu đang diễn ra" viewTransition={viewTransition}>
          <span className="active-match-pulse" />
          <Swords size={14} />
          <span>Vào lại trận (#{activeRoom.room_code})</span>
        </Link>
      )}
      {loading && !user ? null : user ? <><button type="button" className="user-chip user-chip-button" onClick={() => setAccountOpen(true)} aria-haspopup="dialog" aria-label="Mở thông tin tài khoản">{user.avatar_url ? <Avatar url={user.avatar_url} name={user.username} className="avatar-sm"/> : <UserRound size={15}/>}{user.username}</button><button className="icon-button" title="Đăng xuất" aria-label="Đăng xuất" onClick={() => { logout(); navigate("/", { viewTransition }) }}><LogOut size={17}/></button>{accountOpen && <AccountPanel onClose={() => setAccountOpen(false)} />}</> : <><Link className="nav-login" to="/login">Đăng nhập</Link><Link className="button button-small" to="/register">Bắt đầu <span>↗</span></Link></>}
    </div>
  </header>
}