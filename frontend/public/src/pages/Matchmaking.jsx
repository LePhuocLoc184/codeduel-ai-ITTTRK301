import { useEffect, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeft, ArrowRight, Loader2, Shield, Swords, Trophy, X } from "lucide-react"
import api, { getApiErrorMessage } from "../api/axios"
import { useAuth } from "../context/AuthContext"
import Avatar from "../components/Avatar"
import "./Matchmaking.css"

// Khớp backend/app/services/matchmaking_worker.py: biên độ rating ±150, mở rộng thành ±300 sau 30 giây chờ.
const BASE_RATING_GAP = 150
const EXPANDED_RATING_GAP = 300
const EXPAND_AFTER_SECONDS = 30
// Worker ghép trận quét hàng đợi mỗi 2 giây nên hỏi nhanh hơn cũng không có thêm kết quả.
const POLL_MS = 2000
const MAX_POLL_FAILURES = 3
const DEFAULT_COUNTDOWN_SECONDS = 5
const CANCEL_PATH = "/api/v1/matchmaking/cancel"

// Cùng ngưỡng với backend (RankBadge): <1300 BRONZE, 1300-1499 SILVER, 1500-1699 GOLD, >=1700 DIAMOND.
const rankBadgeFor = (rating) => (rating >= 1700 ? "DIAMOND" : rating >= 1500 ? "GOLD" : rating >= 1300 ? "SILVER" : "BRONZE")
const formatClock = (seconds) => `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`

function PlayerCard({ name, rating, avatarUrl, tag, found }) {
  return <div className={`mm-player${found ? " is-found" : ""}`}>
    <Avatar url={avatarUrl} name={name} className="avatar-xl" />
    <div className="mm-info">
      <b className="mm-name" title={name}>{name}</b>
      <span className="mm-rating"><Trophy size={12} /> {rating != null ? Number(rating).toLocaleString() : "—"} điểm</span>
      <span className="mm-badge"><Shield size={11} /> {rating != null ? rankBadgeFor(Number(rating)) : "—"}</span>
      <small className="mm-tag">{tag}</small>
    </div>
  </div>
}

// Phần "đối thủ" lúc đang tìm: dấu ? với hiệu ứng quét.
function UnknownCard() {
  return <div className="mm-player mm-player-unknown" aria-hidden="true">
    <span className="mm-unknown"><span>?</span></span>
    <div className="mm-info">
      <b className="mm-name">Đang tìm…</b>
      <span className="mm-rating">Chưa xác định</span>
      <span className="mm-badge mm-badge-muted">— — —</span>
      <small className="mm-tag">ĐỐI THỦ</small>
    </div>
  </div>
}

export default function Matchmaking() {
  const { user, loading } = useAuth()
  // Chỉ phụ thuộc id: object `user` bị thay mỗi khi /users/me trả về, làm effect hỏi trạng thái
  // chạy lại và đặt lại đồng hồ đếm ngược khi đã tìm thấy đối thủ.
  const userId = user?.id
  const navigate = useNavigate()
  // checking: hỏi trạng thái hàng đợi | searching | found | ended: lượt chờ đã kết thúc ngoài ý muốn | error
  const [phase, setPhaseState] = useState("checking")
  const [attempt, setAttempt] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [opponent, setOpponent] = useState(null)
  const [roomCode, setRoomCode] = useState("")
  const [countdown, setCountdown] = useState(DEFAULT_COUNTDOWN_SECONDS)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  const phaseRef = useRef("checking")
  const mountedRef = useRef(false)
  const startedAtRef = useRef(null)
  const setPhase = (next) => { phaseRef.current = next; setPhaseState(next) }

  // Hỏi trạng thái hàng đợi định kỳ. Trang này không tự "vào hàng đợi": việc đó làm ở Arena,
  // nên mở/tải lại trang vẫn nối lại đúng lượt đang chờ (hoặc quay về Arena nếu không có lượt nào).
  useEffect(() => {
    if (loading || !userId) return undefined
    let active = true
    let failures = 0
    let first = true
    let timer

    const check = async () => {
      try {
        const { data } = await api.get("/api/v1/matchmaking/status")
        if (!active) return false
        failures = 0
        const info = data.data || {}
        if (info.status === "matched" && info.room_code) {
          setOpponent(info.opponent || null)
          setRoomCode(info.room_code)
          setCountdown(Number(info.countdown_seconds) || DEFAULT_COUNTDOWN_SECONDS)
          setPhase("found")
          return false
        }
        if (info.status === "searching") {
          if (phaseRef.current !== "searching") setPhase("searching")
          return true
        }
        // idle: lần hỏi đầu = không có lượt chờ nào; các lần sau = lượt chờ đã bị kết thúc.
        if (first) navigate("/arena", { replace: true })
        else setPhase("ended")
        return false
      } catch (err) {
        if (!active) return false
        failures += 1
        if (failures >= MAX_POLL_FAILURES) {
          setNote(getApiErrorMessage(err, "Mất kết nối khi tìm trận. Vui lòng thử lại."))
          setPhase("error")
          return false
        }
        return true
      } finally {
        first = false
      }
    }

    const tick = async () => {
      const keepGoing = await check()
      if (active && keepGoing) timer = window.setTimeout(tick, POLL_MS)
    }
    tick()
    return () => { active = false; window.clearTimeout(timer) }
  }, [userId, loading, attempt, navigate])

  // Đếm thời gian đã chờ.
  useEffect(() => {
    if (phase !== "searching") return undefined
    if (startedAtRef.current === null) startedAtRef.current = Date.now()
    const update = () => setElapsed(Math.floor((Date.now() - startedAtRef.current) / 1000))
    update()
    const timer = window.setInterval(update, 1000)
    return () => window.clearInterval(timer)
  }, [phase])

  // Đã ghép được: đếm ngược rồi vào phòng (cả hai người chơi cùng được báo như vậy).
  useEffect(() => {
    if (phase !== "found") return undefined
    const timer = window.setInterval(() => setCountdown((value) => value - 1), 1000)
    return () => window.clearInterval(timer)
  }, [phase])

  useEffect(() => {
    if (phase === "found" && roomCode && countdown <= 0) navigate(`/room/${roomCode}`, { replace: true })
  }, [phase, roomCode, countdown, navigate])

  // Backend không tự xóa lượt chờ, nên rời trang / đóng tab mà không hủy sẽ để lại lượt "ma"
  // và người khác có thể bị ghép vào phòng không có ai. Vì vậy tự hủy khi rời đi.
  useEffect(() => {
    mountedRef.current = true
    const cancelSilently = () => { api.delete(CANCEL_PATH).catch(() => {}) }
    const onPageHide = () => {
      if (phaseRef.current !== "searching") return
      const token = localStorage.getItem("token")
      if (!token) return
      fetch(`${api.defaults.baseURL || ""}${CANCEL_PATH}`, { method: "DELETE", keepalive: true, headers: { Authorization: `Bearer ${token}` } }).catch(() => {})
    }
    window.addEventListener("pagehide", onPageHide)
    return () => {
      window.removeEventListener("pagehide", onPageHide)
      mountedRef.current = false
      // Hoãn một nhịp: React StrictMode (dev) tháo/gắn lại component ngay lập tức, khi đó không được hủy.
      window.setTimeout(() => { if (!mountedRef.current && phaseRef.current === "searching") cancelSilently() }, 50)
    }
  }, [])

  const cancel = async () => {
    setBusy(true)
    setNote("")
    try {
      await api.delete(CANCEL_PATH)
      phaseRef.current = "cancelled"
      navigate("/arena")
    } catch (err) {
      const status = err.response?.status
      if (status === 404) { phaseRef.current = "cancelled"; navigate("/arena"); return }
      // 400: trận vừa được ghép nên không hủy được; lần hỏi trạng thái kế tiếp sẽ chuyển sang màn "đã tìm thấy".
      setNote(getApiErrorMessage(err, "Không thể hủy lượt tìm trận. Vui lòng thử lại."))
    } finally {
      setBusy(false)
    }
  }

  const searchAgain = async () => {
    setBusy(true)
    setNote("")
    try {
      await api.post("/api/v1/matchmaking/join", { game_mode: "RANKED_1V1" })
      startedAtRef.current = null
      setElapsed(0)
      setPhase("checking")
      setAttempt((value) => value + 1)
    } catch (err) {
      setNote(getApiErrorMessage(err, "Không thể tìm trận. Vui lòng thử lại."))
    } finally {
      setBusy(false)
    }
  }

  const retryCheck = () => { setNote(""); setPhase("checking"); setAttempt((value) => value + 1) }

  if (loading && !user) return <section className="mm-page" />
  if (!user) return <section className="arena-page"><div className="arena-panel"><div className="feature-icon purple"><Swords /></div><h1>Đăng nhập để tìm trận.</h1><p>Bạn cần đăng nhập trước khi vào hàng đợi ghép trận.</p><Link className="button" to="/login">Đăng nhập để tiếp tục <ArrowRight size={16} /></Link></div></section>

  const found = phase === "found"
  const expanded = elapsed >= EXPAND_AFTER_SECONDS

  if (phase === "checking") return <section className="mm-page"><div className="mm-loading" role="status"><Loader2 size={18} className="mm-spin" /> Đang kiểm tra hàng đợi…</div></section>

  if (phase === "ended" || phase === "error") return <section className="mm-page">
    <div className="eyebrow"><span className="eyebrow-line" /> RANKED MATCH</div>
    <h1>{phase === "ended" ? <>Lượt tìm trận <span>đã kết thúc.</span></> : <>Mất <span>kết nối.</span></>}</h1>
    <p className="mm-sub">{phase === "ended" ? "Bạn không còn trong hàng đợi. Bạn có thể tìm trận lại hoặc quay về đấu trường." : note}</p>
    {phase === "ended" && note && <div className="arena-message" role="alert">{note}</div>}
    <div className="mm-actions">
      {phase === "ended" ? <button className="button" onClick={searchAgain} disabled={busy}>{busy ? "Đang kết nối..." : "Tìm trận lại"} <ArrowRight size={16} /></button> : <button className="button" onClick={retryCheck}>Thử lại <ArrowRight size={16} /></button>}
      <Link className="button button-ghost" to="/arena"><ArrowLeft size={15} /> Về đấu trường</Link>
    </div>
  </section>

  return <section className="mm-page">
    <div className="eyebrow"><span className="eyebrow-line" /> RANKED MATCH</div>
    <h1>{found ? <>Đã tìm thấy <span>đối thủ!</span></> : <>Đang tìm <span>đối thủ…</span></>}</h1>
    <p className="mm-sub" role="status" aria-live="polite">{found ? `Trận đấu bắt đầu sau ${Math.max(countdown, 0)} giây. Hãy chuẩn bị tinh thần!` : "Hệ thống đang ghép bạn với người chơi có trình độ tương đương."}</p>

    <div className="mm-versus">
      <PlayerCard name={user.username} rating={user.rating} avatarUrl={user.avatar_url} tag="BẠN" found={found} />
      <div className={`mm-vs${found ? " is-found" : ""}`} aria-hidden="true"><i /><i /><span>VS</span></div>
      {found && opponent
        ? <PlayerCard name={opponent.username} rating={opponent.rating} avatarUrl={opponent.avatar_url} tag="ĐỐI THỦ" found />
        : <UnknownCard />}
    </div>

    {found ? <div className="mm-actions"><button className="button" onClick={() => navigate(`/room/${roomCode}`, { replace: true })}>Vào phòng ngay <ArrowRight size={16} /></button></div> : <>
      <div className="mm-timer-box">
        <span className="mm-timer">{formatClock(elapsed)}</span>
        <small>THỜI GIAN CHỜ</small>
      </div>
      <p className="mm-range">Phạm vi ghép trận: <b>±{expanded ? EXPANDED_RATING_GAP : BASE_RATING_GAP}</b> rating{expanded ? " (đã mở rộng)" : ` — mở rộng lên ±${EXPANDED_RATING_GAP} sau ${EXPAND_AFTER_SECONDS} giây`}</p>
      {note && <div className="arena-message" role="alert">{note}</div>}
      <div className="mm-actions"><button className="button button-ghost" onClick={cancel} disabled={busy}><X size={15} /> {busy ? "Đang hủy..." : "Hủy tìm trận"}</button></div>
    </>}
  </section>
}