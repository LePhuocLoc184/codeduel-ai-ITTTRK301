import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeft, ArrowRight, Code2, Eye, EyeOff, LockKeyhole, Mail, UserRound } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import { getApiErrorMessage } from "../api/axios"

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: "", email: "", password: "" })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setError("")
    if (form.password.length < 8 || !/[A-Z]/.test(form.password) || !/\d/.test(form.password)) {
      setError("Mật khẩu cần ít nhất 8 ký tự, có ít nhất 1 chữ hoa và 1 chữ số.")
      return
    }
    setBusy(true)
    try {
      await register({ ...form, username: form.username.trim(), email: form.email.trim() })
      navigate("/home")
    } catch (err) {
      setError(getApiErrorMessage(err, "Không thể tạo tài khoản. Vui lòng kiểm tra lại thông tin."))
    } finally {
      setBusy(false)
    }
  }

  return <section className="auth-page">
    <Link to="/home" className="back-link"><ArrowLeft size={15}/> Về trang chủ</Link>
    <div className="auth-card">
      <Link className="brand auth-brand" to="/home"><span className="brand-mark"><Code2 size={20}/></span><span>code<span className="brand-accent">duel</span><small>.dev</small></span></Link>
      <div className="eyebrow"><span className="eyebrow-line"/> JOIN THE ARENA</div>
      <h1>Bắt đầu hành trình.</h1>
      <p className="auth-sub">Tạo tài khoản miễn phí và bước vào đấu trường.</p>
      <form onSubmit={submit}>
        <label>Tên người dùng<div className="input-wrap"><UserRound size={17}/><input name="username" autoComplete="username" placeholder="coder_vn" value={form.username} onChange={change} required/></div></label>
        <label>Email<div className="input-wrap"><Mail size={17}/><input type="email" name="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={change} required/></div></label>
        <label>Mật khẩu<div className="input-wrap"><LockKeyhole size={17}/><input type={showPassword ? "text" : "password"} name="password" autoComplete="new-password" minLength={8} placeholder="Ít nhất 8 ký tự, gồm chữ hoa và số" value={form.password} onChange={change} required/><button type="button" className="password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="button auth-submit" disabled={busy}>{busy ? "Đang tạo tài khoản..." : <>Tạo tài khoản <ArrowRight size={16}/></>}</button>
      </form>
      <p className="auth-switch">Đã có tài khoản? <Link to="/login">Đăng nhập</Link></p>
    </div>
    <p className="auth-caption">CODE. COMPETE. CONQUER.</p>
  </section>
}
