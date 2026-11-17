import { useEffect, useState } from "react"
import { createPortal } from "react-dom"
import { Check, Eye, EyeOff, ImageIcon, KeyRound, Link2, LockKeyhole, Mail, Trash2, UserRound, X } from "lucide-react"
import api, { getApiErrorMessage } from "../api/axios"
import { useAuth } from "../context/AuthContext"
import Avatar from "./Avatar"

// Cột users.avatar_url ở backend là String(255) nên chỉ lưu được đường dẫn ảnh, không lưu được dữ liệu ảnh.
const AVATAR_URL_MAX_LENGTH = 255
const PRESET_STYLES = ["adventurer", "avataaars", "bottts", "fun-emoji", "lorelei", "pixel-art", "thumbs", "initials"]
const presetUrl = (style, seed) => `https://api.dicebear.com/9.x/${style}/svg?seed=${encodeURIComponent(seed)}`

const TABS = [
  { id: "info", label: "Thông tin", icon: UserRound },
  { id: "avatar", label: "Ảnh đại diện", icon: ImageIcon },
  { id: "password", label: "Mật khẩu", icon: KeyRound },
]

function Note({ note }) {
  if (!note) return null
  return <div className={note.type === "ok" ? "form-success" : "form-error"} role={note.type === "ok" ? "status" : "alert"}>{note.text}</div>
}

function InfoTab({ user, onChangePassword }) {
  return <div className="account-info">
    <div className="account-row"><span className="account-row-icon"><UserRound size={16}/></span><span><small>TÊN NGƯỜI DÙNG</small><b>{user.username}</b></span></div>
    <div className="account-row"><span className="account-row-icon"><Mail size={16}/></span><span><small>EMAIL</small><b>{user.email}</b></span></div>
    <div className="account-row"><span className="account-row-icon"><LockKeyhole size={16}/></span><span><small>MẬT KHẨU</small><b className="account-mask">••••••••••</b><em>Mật khẩu được mã hóa nên không thể hiển thị lại.</em></span><button type="button" className="account-link" onClick={onChangePassword}>Đổi mật khẩu</button></div>
  </div>
}

function AvatarTab({ user, updateUser }) {
  const [value, setValue] = useState(user.avatar_url || "")
  const [note, setNote] = useState(null)
  const [busy, setBusy] = useState(false)
  const trimmed = value.trim()
  const unchanged = trimmed === (user.avatar_url || "")

  const save = async (url) => {
    if (url && !/^https?:\/\//i.test(url)) { setNote({ type: "error", text: "Đường dẫn ảnh phải bắt đầu bằng http:// hoặc https://." }); return }
    if (url.length > AVATAR_URL_MAX_LENGTH) { setNote({ type: "error", text: `Đường dẫn ảnh quá dài (tối đa ${AVATAR_URL_MAX_LENGTH} ký tự).` }); return }
    setBusy(true)
    setNote(null)
    try {
      const { data } = await api.put("/api/v1/users/me", { avatar_url: url })
      const saved = data.data?.avatar_url || ""
      updateUser({ avatar_url: saved })
      setValue(saved)
      setNote({ type: "ok", text: saved ? "Đã cập nhật ảnh đại diện." : "Đã xóa ảnh đại diện." })
    } catch (err) {
      setNote({ type: "error", text: getApiErrorMessage(err, "Không thể cập nhật ảnh đại diện. Vui lòng thử lại.") })
    } finally {
      setBusy(false)
    }
  }

  return <div className="account-form">
    <div className="account-preview"><Avatar url={trimmed} name={user.username} className="avatar-xl"/><p>Xem trước ảnh đại diện</p></div>
    <label>Đường dẫn ảnh (URL)<div className="input-wrap"><Link2 size={17}/><input type="url" value={value} onChange={(event) => setValue(event.target.value)} placeholder="https://example.com/avatar.png" maxLength={AVATAR_URL_MAX_LENGTH} autoComplete="off"/></div></label>
    <div className="account-presets" role="group" aria-label="Chọn nhanh ảnh đại diện">
      <span className="account-presets-title">HOẶC CHỌN NHANH</span>
      <div>{PRESET_STYLES.map((style) => { const url = presetUrl(style, user.username); return <button key={style} type="button" className={`preset${trimmed === url ? " selected" : ""}`} onClick={() => setValue(url)} aria-label={`Ảnh kiểu ${style}`} aria-pressed={trimmed === url}><Avatar url={url} name={user.username}/></button> })}</div>
    </div>
    <Note note={note}/>
    <div className="account-actions">
      <button type="button" className="button" disabled={busy || unchanged || !trimmed} onClick={() => save(trimmed)}>{busy ? "Đang lưu..." : <>Lưu ảnh <Check size={16}/></>}</button>
      {user.avatar_url ? <button type="button" className="button button-ghost" disabled={busy} onClick={() => save("")}><Trash2 size={15}/> Xóa ảnh</button> : null}
    </div>
  </div>
}

function PasswordTab() {
  const [form, setForm] = useState({ old_password: "", new_password: "", confirm: "" })
  const [show, setShow] = useState(false)
  const [note, setNote] = useState(null)
  const [busy, setBusy] = useState(false)
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setNote(null)
    const next = form.new_password
    // Cùng quy tắc với form đăng ký (backend chỉ kiểm tra độ mạnh lúc đăng ký).
    if (next.length < 8 || !/[A-Z]/.test(next) || !/\d/.test(next)) { setNote({ type: "error", text: "Mật khẩu mới cần ít nhất 8 ký tự, có ít nhất 1 chữ hoa và 1 chữ số." }); return }
    if (next !== form.confirm) { setNote({ type: "error", text: "Mật khẩu nhập lại không khớp." }); return }
    if (next === form.old_password) { setNote({ type: "error", text: "Mật khẩu mới phải khác mật khẩu hiện tại." }); return }
    setBusy(true)
    try {
      await api.put("/api/v1/users/me", { old_password: form.old_password, new_password: next })
      setForm({ old_password: "", new_password: "", confirm: "" })
      setNote({ type: "ok", text: "Đã đổi mật khẩu thành công." })
    } catch (err) {
      setNote({ type: "error", text: getApiErrorMessage(err, "Không thể đổi mật khẩu. Vui lòng thử lại.") })
    } finally {
      setBusy(false)
    }
  }

  const field = (name, label, autoComplete, withToggle) => <label>{label}<div className="input-wrap"><LockKeyhole size={17}/><input type={show ? "text" : "password"} name={name} value={form[name]} onChange={change} autoComplete={autoComplete} required/>{withToggle ? <button type="button" className="password-toggle" onClick={() => setShow((visible) => !visible)} aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>{show ? <EyeOff size={17}/> : <Eye size={17}/>}</button> : null}</div></label>

  return <form className="account-form" onSubmit={submit}>
    {field("old_password", "Mật khẩu hiện tại", "current-password", true)}
    {field("new_password", "Mật khẩu mới", "new-password", false)}
    {field("confirm", "Nhập lại mật khẩu mới", "new-password", false)}
    <Note note={note}/>
    <div className="account-actions"><button className="button" disabled={busy}>{busy ? "Đang đổi..." : <>Đổi mật khẩu <KeyRound size={16}/></>}</button></div>
  </form>
}

export default function AccountPanel({ onClose }) {
  const { user, updateUser } = useAuth()
  const [tab, setTab] = useState("info")

  useEffect(() => {
    const onKey = (event) => { if (event.key === "Escape") onClose() }
    const previousOverflow = document.body.style.overflow
    document.addEventListener("keydown", onKey)
    document.body.style.overflow = "hidden"
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = previousOverflow }
  }, [onClose])

  if (!user) return null
  // Dùng portal vì .topbar có backdrop-filter, sẽ làm position:fixed bị tính theo thanh điều hướng thay vì cả màn hình.
  return createPortal(
    <div className="account-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <div className="account-dialog" role="dialog" aria-modal="true" aria-label="Thông tin tài khoản">
        <div className="account-head">
          <Avatar url={user.avatar_url} name={user.username} className="avatar-lg"/>
          <span className="account-id"><b>{user.username}</b><small>{user.email}</small></span>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Đóng"><X size={17}/></button>
        </div>
        <div className="account-tabs" role="tablist">
          {TABS.map(({ id, label, icon: Icon }) => <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon size={14}/> {label}</button>)}
        </div>
        <div className="account-body">
          {tab === "info" && <InfoTab user={user} onChangePassword={() => setTab("password")}/>}
          {tab === "avatar" && <AvatarTab user={user} updateUser={updateUser}/>}
          {tab === "password" && <PasswordTab/>}
        </div>
      </div>
    </div>,
    document.body,
  )
}