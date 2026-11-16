import { useState } from "react"
import { Link, NavLink, useNavigate } from "react-router-dom"
import { Code2, LogOut, UserRound } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import Avatar from "./Avatar"
import AccountPanel from "./AccountPanel"

export default function Navbar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const [accountOpen, setAccountOpen] = useState(false)
  return <header className="topbar"><Link className="brand" to="/home"><span className="brand-mark"><Code2 size={20} /></span><span>code<span className="brand-accent">duel</span><small>.dev</small></span></Link>
    <nav className="nav-links"><NavLink to="/home">Trang chủ</NavLink><Link to="/home#features">Tính năng</Link><Link to="/home#leaderboard">Bảng xếp hạng</Link></nav>
    <div className="nav-actions">{loading && !user ? null : user ? <><button type="button" className="user-chip user-chip-button" onClick={() => setAccountOpen(true)} aria-haspopup="dialog" aria-label="Mở thông tin tài khoản">{user.avatar_url ? <Avatar url={user.avatar_url} name={user.username} className="avatar-sm"/> : <UserRound size={15}/>}{user.username}</button><button className="icon-button" aria-label="Đăng xuất" onClick={() => { logout(); navigate("/") }}><LogOut size={17}/></button>{accountOpen && <AccountPanel onClose={() => setAccountOpen(false)} />}</> : <><Link className="nav-login" to="/login">Đăng nhập</Link><Link className="button button-small" to="/register">Bắt đầu <span>↗</span></Link></>}</div>
  </header>
}