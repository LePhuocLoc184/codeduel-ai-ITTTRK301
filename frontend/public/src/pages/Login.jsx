import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeft, ArrowRight, Code2, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import { getApiErrorMessage } from "../api/axios"

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: "", password: "" })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [show, setShow] = useState(false)
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setError("")
    setBusy(true)
    try {
      await login({ ...form, email: form.email.trim() })
      navigate("/home")
    } catch (err) {
      setError(getApiErrorMessage(err, "Không thể đăng nhập. Hãy kiểm tra email và mật khẩu."))
    } finally {
      setBusy(false)
    }
  }

  return <section className="auth-page">
    <Link to="/home" className="back-link"><ArrowLeft size={15}/> Về trang chủ</Link>
    <div className="auth-card">
      <Link className="brand auth-brand" to="/home"><span className="brand-mark"><Code2 size={20}/></span><span>code<span className="brand-accent">duel</span><small>.dev</small></span></Link>
      <div className="eyebrow"><span className="eyebrow-line"/> WELCOME BACK</div>
      <h1>Tiếp tục cuộc chơi.</h1>
      <p className="auth-sub">Đăng nhập để trở lại đấu trường của bạn.</p>
      <form onSubmit={submit}>
        <label>Email<div className="input-wrap"><Mail size={17}/><input type="email" name="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={change} required/></div></label>
        <label>Mật khẩu<div className="input-wrap"><LockKeyhole size={17}/><input type={show ? "text" : "password"} name="password" autoComplete="current-password" placeholder="Nhập mật khẩu" value={form.password} onChange={change} required/><button type="button" className="password-toggle" onClick={() => setShow(!show)} aria-label="Hiện hoặc ẩn mật khẩu">{show ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="button auth-submit" disabled={busy}>{busy ? "Đang đăng nhập..." : <>Đăng nhập <ArrowRight size={16}/></>}</button>
      </form>
      <p className="auth-switch">Chưa có tài khoản? <Link to="/register">Tạo tài khoản</Link></p>
    </div>
    <p className="auth-caption">CODE. COMPETE. CONQUER.</p>
  </section>
}
