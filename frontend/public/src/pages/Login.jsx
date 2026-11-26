import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import { getApiErrorMessage } from "../api/axios"
import BrandLogo from "../components/BrandLogo"
import { useToast } from "../context/ToastContext"

export default function Login() {
  const { login } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: "", password: "" })
  const [busy, setBusy] = useState(false)
  const [show, setShow] = useState(false)
  const change = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const email = form.email.trim()
    if (!email || !form.password) {
      toast.warning("Vui lòng nhập đầy đủ email và mật khẩu.")
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.warning("Vui lòng nhập địa chỉ email hợp lệ.")
      return
    }
    setBusy(true)
    try {
      const user = await login({ ...form, email })
      toast.success(user?.username ? `Chào mừng trở lại, ${user.username}!` : "Đăng nhập thành công!")
      navigate("/home")
    } catch (err) {
      const detail = err.response?.data?.detail
      const message = typeof detail === "string" && detail.trim()
        ? detail
        : getApiErrorMessage(err, "Tên đăng nhập hoặc mật khẩu không chính xác.")
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  return <section className="auth-page">
    <Link to="/home" className="back-link"><ArrowLeft size={15}/> Về trang chủ</Link>
    <div className="auth-card">
      <Link className="brand auth-brand" to="/home"><BrandLogo size={32} /></Link>
      <div className="eyebrow"><span className="eyebrow-line"/> WELCOME BACK</div>
      <h1>Tiếp tục cuộc chơi.</h1>
      <p className="auth-sub">Đăng nhập để trở lại đấu trường của bạn.</p>
      <form onSubmit={submit} noValidate>
        <label>Email<div className="input-wrap"><Mail size={17}/><input type="email" name="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={change}/></div></label>
        <label>Mật khẩu<div className="input-wrap"><LockKeyhole size={17}/><input type={show ? "text" : "password"} name="password" autoComplete="current-password" placeholder="Nhập mật khẩu" value={form.password} onChange={change}/><button type="button" className="password-toggle" onClick={() => setShow(!show)} aria-label="Hiện hoặc ẩn mật khẩu">{show ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
        <button className="button auth-submit" disabled={busy}>{busy ? "Đang đăng nhập..." : <>Đăng nhập <ArrowRight size={16}/></>}</button>
      </form>
      <p className="auth-switch">Chưa có tài khoản? <Link to="/register">Tạo tài khoản</Link></p>
    </div>
    <p className="auth-caption">CODE. COMPETE. CONQUER.</p>
  </section>
}
