import { Link, NavLink, useNavigate } from "react-router-dom"
import { Code2, LogOut, UserRound } from "lucide-react"
import { useAuth } from "../context/AuthContext"

export default function Navbar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  return <header className="topbar"><Link className="brand" to="/home"><span className="brand-mark"><Code2 size={20} /></span><span>code<span className="brand-accent">duel</span><small>.dev</small></span></Link>
    <nav className="nav-links"><NavLink to="/home">Trang chủ</NavLink><Link to="/home#features">Tính năng</Link><Link to="/home#leaderboard">Bảng xếp hạng</Link></nav>
    <div className="nav-actions">{loading && !user ? null : user ? <><span className="user-chip"><UserRound size={15}/>{user.username}</span><button className="icon-button" aria-label="Đăng xuất" onClick={() => { logout(); navigate("/") }}><LogOut size={17}/></button></> : <><Link className="nav-login" to="/login">Đăng nhập</Link><Link className="button button-small" to="/register">Bắt đầu <span>↗</span></Link></>}</div>
  </header>
}