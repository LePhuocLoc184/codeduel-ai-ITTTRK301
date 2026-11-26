import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, UserRound } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import { getApiErrorMessage } from "../api/axios"
import BrandLogo from "../components/BrandLogo"
import { useToast } from "../context/ToastContext"

export default function Register() {
  const { register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: "", email: "", password: "", confirmPassword: "" })
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const change = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const username = form.username.trim()
    const email = form.email.trim()
    if (!username || !email) {
      toast.warning("Vui lòng nhập tên người dùng và email.")
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.warning("Vui lòng nhập địa chỉ email hợp lệ.")
      return
    }
    if (!form.password || !form.confirmPassword) {
      toast.warning("Vui lòng nhập mật khẩu và xác nhận mật khẩu.")
      return
    }
    if (form.password !== form.confirmPassword) {
      toast.warning("Mật khẩu xác nhận không khớp.")
      return
    }
    if (form.password.length < 8) {
      toast.warning("Mật khẩu cần có ít nhất 8 ký tự.")
      return
    }
    if (!/[A-Z]/.test(form.password) || !/\d/.test(form.password)) {
      toast.warning("Mật khẩu cần có ít nhất 1 chữ hoa và 1 chữ số.")
      return
    }
    setBusy(true)
    try {
      await register({ username, email, password: form.password })
      toast.success("Tạo tài khoản thành công! Sẵn sàng bước vào đấu trường.")
      navigate("/home")
    } catch (err) {
      const detail = err.response?.data?.detail
      const message = typeof detail === "string" && detail.trim()
        ? detail
        : err.response?.status === 409
          ? "Tên người dùng hoặc email đã được sử dụng."
          : getApiErrorMessage(err, "Không thể tạo tài khoản. Vui lòng kiểm tra lại thông tin.")
      toast.error(message)
    } finally {
      setBusy(false)
    }
  }

  return <section className="auth-page">
    <Link to="/home" className="back-link"><ArrowLeft size={15}/> Về trang chủ</Link>
    <div className="auth-card">
      <Link className="brand auth-brand" to="/home"><BrandLogo size={32} /></Link>
      <div className="eyebrow"><span className="eyebrow-line"/> JOIN THE ARENA</div>
      <h1>Bắt đầu hành trình.</h1>
      <p className="auth-sub">Tạo tài khoản miễn phí và bước vào đấu trường.</p>
      <form onSubmit={submit} noValidate>
        <label>Tên người dùng<div className="input-wrap"><UserRound size={17}/><input name="username" autoComplete="username" placeholder="coder_vn" value={form.username} onChange={change}/></div></label>
        <label>Email<div className="input-wrap"><Mail size={17}/><input type="email" name="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={change}/></div></label>
        <label>Mật khẩu<div className="input-wrap"><LockKeyhole size={17}/><input type={showPassword ? "text" : "password"} name="password" autoComplete="new-password" minLength={8} placeholder="Ít nhất 8 ký tự, gồm chữ hoa và số" value={form.password} onChange={change}/><button type="button" className="password-toggle" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
        <label>Xác nhận mật khẩu<div className="input-wrap"><LockKeyhole size={17}/><input type={showPassword ? "text" : "password"} name="confirmPassword" autoComplete="new-password" placeholder="Nhập lại mật khẩu" value={form.confirmPassword} onChange={change}/></div></label>
        <button className="button auth-submit" disabled={busy}>{busy ? "Đang tạo tài khoản..." : <>Tạo tài khoản <ArrowRight size={16}/></>}</button>
      </form>
      <p className="auth-switch">Đã có tài khoản? <Link to="/login">Đăng nhập</Link></p>
    </div>
    <p className="auth-caption">CODE. COMPETE. CONQUER.</p>
  </section>
}
