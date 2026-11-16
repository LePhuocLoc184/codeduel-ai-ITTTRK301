import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowRight, Search, Swords, Users, Zap } from "lucide-react"
import api from "../api/axios"
import { useAuth } from "../context/AuthContext"

export default function Arena() {
  const navigate = useNavigate()
  const { user } = useAuth(); const [code, setCode] = useState(""); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false)
  const [queueing, setQueueing] = useState(false)
  useEffect(() => {
    if (!queueing) return undefined
    let active = true
    const poll = async () => {
      try {
        const { data } = await api.get("/api/v1/matchmaking/status")
        if (!active) return
        if (data.data?.status === "matched") { setQueueing(false); navigate(`/room/${data.data.room_code}`) }
        else if (data.data?.status === "idle") { setQueueing(false); setMessage("Lượt tìm trận đã kết thúc.") }
      } catch { if (active) { setQueueing(false); setMessage("Mất kết nối khi tìm trận. Vui lòng thử lại.") } }
    }
    poll()
    const timer = window.setInterval(poll, 2500)
    return () => { active = false; window.clearInterval(timer) }
  }, [queueing, navigate])
  const createRoom = async () => { setBusy(true); setMessage(""); try { const { data } = await api.post("/api/v1/rooms/create", {}); navigate(`/room/${data.data.room_code}`) } catch (e) { setMessage(e.response?.data?.message || "Không thể tạo phòng. Hãy thử lại.") } finally { setBusy(false) } }
  const joinRoom = async (e) => { e.preventDefault(); setBusy(true); setMessage(""); try { const { data } = await api.post("/api/v1/rooms/join", { room_code: code }); navigate(`/room/${data.data.room_code}`) } catch (err) { setMessage(err.response?.data?.message || "Không tìm thấy phòng. Kiểm tra mã và thử lại.") } finally { setBusy(false) } }
  const findMatch = async () => { setBusy(true); setMessage(""); try { const { data } = await api.post("/api/v1/matchmaking/join", { game_mode: "RANKED_1V1" }); if (data.data?.status === "matched" && data.data.room_code) navigate(`/room/${data.data.room_code}`); else { setQueueing(true); setMessage("Đang tìm đối thủ phù hợp…") } } catch (e) { setMessage(e.response?.data?.message || "Không thể tìm trận. Vui lòng thử lại.") } finally { setBusy(false) } }
  const cancelMatch = async () => { setBusy(true); try { await api.post("/api/v1/matchmaking/cancel"); setQueueing(false); setMessage("Đã hủy tìm trận.") } catch (e) { setMessage(e.response?.data?.message || "Không thể hủy lượt tìm trận.") } finally { setBusy(false) } }
  if (!user) return <section className="arena-page"><div className="arena-panel"><div className="feature-icon purple"><Swords/></div><h1>Đấu trường đang chờ.</h1><p>Đăng nhập để tạo phòng, mời đối thủ và bắt đầu trận đấu.</p><Link className="button" to="/login">Đăng nhập để tiếp tục <ArrowRight size={16}/></Link></div></section>
  return <section className="arena-page"><div className="arena-heading"><div className="eyebrow"><span className="eyebrow-line"/> CODEDUEL ARENA</div><h1>Chọn cách <span>thi đấu.</span></h1><p>Chào {user.username}, sẵn sàng so tài hôm nay chưa?</p></div><div className="arena-options"><article className="arena-option"><div className="feature-icon purple"><Zap/></div><span className="feature-index">RANKED MATCH</span><h2>Tìm đối thủ</h2><p>Ghép trận 1v1 với lập trình viên có cùng trình độ và leo hạng.</p><button className="button" onClick={queueing ? cancelMatch : findMatch} disabled={busy}>{queueing ? "Hủy tìm trận" : busy ? "Đang kết nối..." : "Tìm trận"} <ArrowRight size={16}/></button></article><article className="arena-option"><div className="feature-icon green"><Users/></div><span className="feature-index">CUSTOM ROOM</span><h2>Tạo phòng đấu</h2><p>Tạo phòng riêng và chia sẻ mã phòng với bạn bè.</p><button className="button" onClick={createRoom} disabled={busy}>{busy ? "Đang tạo..." : "Tạo phòng"} <ArrowRight size={16}/></button></article><article className="arena-option"><div className="feature-icon blue"><Search/></div><span className="feature-index">JOIN A ROOM</span><h2>Vào phòng</h2><p>Nhập mã phòng được chia sẻ để tham gia trận đấu.</p><form className="join-form" onSubmit={joinRoom}><input value={code} maxLength={6} onChange={e => setCode(e.target.value.toUpperCase())} placeholder="Mã phòng" aria-label="Mã phòng" required/><button className="button" disabled={busy}>Vào phòng</button></form></article></div>{message && <div className="arena-message">{message}</div>}</section>
}
