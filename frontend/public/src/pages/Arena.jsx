import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight, Search, Swords, Users, Zap } from "lucide-react"
import api, { getApiErrorMessage } from "../api/axios"
import { useAuth } from "../context/AuthContext"
import ProfileCard from "../components/ProfileCard"
import useMotionPreference from "../hooks/useMotionPreference"
import useScrollReveal from "../hooks/useScrollReveal"

export default function Arena() {
  const navigate = useNavigate()
  const viewTransition = useMotionPreference()
  const headingRef = useScrollReveal()
  const rankedRef = useScrollReveal()
  const customRef = useScrollReveal()
  const joinRef = useScrollReveal()
  const { user, loading } = useAuth()
  const [code, setCode] = useState("")
  const [message, setMessage] = useState("")
  const [busy, setBusy] = useState(false)
  // Tự động kiểm tra xem người dùng có đang ở trong phòng nào không (qua cache localStorage)
  const [stuckRoom, setStuckRoom] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("codeduel_active_room") || "null")
      if (saved?.room_code && (saved.status === "PLAYING" || saved.status === "WAITING")) {
        return saved.room_code
      }
    } catch {}
    return ""
  })
  const showError = (e, fallback) => {
    const details = e.response?.data?.error?.details
    if (e.response?.status === 409 && details?.room_code) setStuckRoom(details.room_code)
    setMessage(getApiErrorMessage(e, fallback))
  }
  const createRoom = async () => { setBusy(true); setMessage(""); setStuckRoom(""); try { const { data } = await api.post("/api/v1/rooms/create", {}); navigate(`/room/${data.data.room_code}`) } catch (e) { showError(e, "Không thể tạo phòng. Hãy thử lại.") } finally { setBusy(false) } }
  const joinRoom = async (e) => { e.preventDefault(); setBusy(true); setMessage(""); setStuckRoom(""); try { const { data } = await api.post("/api/v1/rooms/join", { room_code: code }); navigate(`/room/${data.data.room_code}`) } catch (err) { showError(err, "Không tìm thấy phòng. Kiểm tra mã và thử lại.") } finally { setBusy(false) } }
  // Tìm trận: vào hàng đợi rồi chuyển sang màn hình chờ /matchmaking (ở đó hỏi trạng thái + cho phép hủy).
  const findMatch = async () => {
    setBusy(true); setMessage(""); setStuckRoom("")
    try {
      // Đã có lượt chờ / trận được ghép (vd. mở từ tab khác) thì nối lại, vì join lần nữa backend sẽ báo trùng.
      const { data: current } = await api.get("/api/v1/matchmaking/status")
      if (!["searching", "matched"].includes(current.data?.status)) await api.post("/api/v1/matchmaking/join", { game_mode: "RANKED_1V1" })
      navigate("/matchmaking", { viewTransition })
    } catch (e) { showError(e, "Không thể tìm trận. Vui lòng thử lại.") } finally { setBusy(false) }
  }
  if (loading && !user) return <section className="arena-page" />
  if (!user) return <section className="arena-page"><div className="arena-panel"><div className="feature-icon purple"><Swords/></div><h1>Đấu trường đang chờ.</h1><p>Đăng nhập để tạo phòng, mời đối thủ và bắt đầu trận đấu.</p><Link className="button" to="/login">Đăng nhập để tiếp tục <ArrowRight size={16}/></Link></div></section>
  return <section className="arena-page">
    {stuckRoom && (
      <div className="active-match-banner" role="status">
        <div className="active-match-info">
          <span className="active-match-pulse" />
          <Swords size={18} />
          <div>
            <strong>Trận đấu đang diễn ra</strong>
            <p>Bạn đang có một phòng thi đấu (#{stuckRoom}) chưa kết thúc.</p>
          </div>
        </div>
        <Link className="button button-small active-match-btn" to={`/room/${stuckRoom}`} viewTransition={viewTransition}>
          Quay lại phòng đấu <ArrowRight size={15}/>
        </Link>
      </div>
    )}
    <div className="arena-heading scroll-reveal" ref={headingRef}><div className="eyebrow"><span className="eyebrow-line"/> CODEDUEL ARENA</div><h1>Chọn cách <span>thi đấu.</span></h1><p>Chào {user?.username || ""}, sẵn sàng so tài hôm nay chưa?</p></div><ProfileCard/><div className="arena-options arena-options-hierarchical"><article ref={rankedRef} className="arena-option arena-hero-option scroll-reveal" style={{ "--scroll-reveal-delay": "0ms" }}><div className="hero-option-glow"/><div className="feature-icon purple"><Zap size={24}/></div><div className="hero-option-body"><span className="feature-index">CHẾ ĐỘ CHÍNH · RANKED 1V1</span><h2>Đấu Xếp Hạng</h2><p>Ghép trận 1v1 theo thuật toán ELO với các lập trình viên cùng trình độ. Tính điểm xếp hạng và thăng hạng danh giá.</p></div><button className="button button-large hero-action-btn" onClick={findMatch} disabled={busy}>{busy ? "Đang kết nối..." : "Tìm trận đấu ngay"} <ArrowRight size={18}/></button></article><div className="arena-secondary-grid"><article ref={customRef} className="arena-option scroll-reveal" style={{ "--scroll-reveal-delay": "90ms" }}><div className="feature-icon green"><Users size={20}/></div><span className="feature-index">CUSTOM ROOM</span><h2>Tạo phòng riêng</h2><p>Tạo phòng thi đấu tùy chọn và chia sẻ liên kết trực tiếp với bạn bè.</p><button className="button" onClick={createRoom} disabled={busy}>{busy ? "Đang tạo..." : "Tạo phòng"} <ArrowRight size={16}/></button></article><article ref={joinRef} className="arena-option scroll-reveal" style={{ "--scroll-reveal-delay": "180ms" }}><div className="feature-icon blue"><Search size={20}/></div><span className="feature-index">JOIN A ROOM</span><h2>Vào phòng có sẵn</h2><p>Nhập mã phòng 6 ký tự để bước vào trận đấu giao hữu.</p><form className="join-form" onSubmit={joinRoom}><input value={code} maxLength={6} onChange={e => setCode(e.target.value.toUpperCase())} placeholder="MÃ PHÒNG (VD: AB12CD)" aria-label="Mã phòng" required/><button className="button" disabled={busy}>Vào phòng</button></form></article></div></div>{message && <div className="arena-message" role="alert">{message}{stuckRoom && <> <Link className="text-link" to={`/room/${stuckRoom}`} viewTransition={viewTransition}>Vào lại phòng {stuckRoom} <ArrowRight size={14}/></Link></>}</div>}</section>
}