import { useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft, Check, Copy, Swords, Users } from "lucide-react"
import api from "../api/axios"
import { useAuth } from "../context/AuthContext"

export default function Room() {
  const { roomCode } = useParams()
  const { user, loading } = useAuth()
  const socketRef = useRef(null)
  const [room, setRoom] = useState(null)
  const [error, setError] = useState("")
  const [connection, setConnection] = useState("connecting")
  const [countdown, setCountdown] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (loading || !user) return undefined
    let active = true
    const connect = async () => {
      try {
        const { data } = await api.get(`/api/v1/rooms/${roomCode}`)
        if (!active) return
        setRoom(data.data)
        const token = localStorage.getItem("token")
        const configuredBase = api.defaults.baseURL || "/"
        const apiOrigin = /^https?:\/\//i.test(configuredBase) ? new URL(configuredBase).origin : window.location.origin
        const socketOrigin = apiOrigin.replace(/^http/i, "ws")
        const socket = new WebSocket(`${socketOrigin}/api/v1/rooms/ws/arena/${encodeURIComponent(roomCode)}?token=${encodeURIComponent(token || "")}`)
        socketRef.current = socket
        socket.onopen = () => active && setConnection("connected")
        socket.onclose = () => active && setConnection("disconnected")
        socket.onerror = () => active && setConnection("disconnected")
        socket.onmessage = (event) => {
          if (!active) return
          try {
            const message = JSON.parse(event.data)
            if (message.event === "ROOM_STATE") setRoom(message.data)
            if (["JOIN_ROOM", "PLAYER_READY"].includes(message.event) && message.data?.players) {
              setRoom((current) => current ? { ...current, players: message.data.players } : current)
            }
            if (message.event === "PLAYER_LEFT") {
              setRoom((current) => current ? { ...current, players: (current.players || []).filter((player) => player.user_id !== message.data.user_id) } : current)
            }
            if (message.event === "COUNTDOWN") setCountdown(message.data.value)
            if (["COUNTDOWN_START", "COUNTDOWN_ABORTED"].includes(message.event)) {
              setCountdown(null)
              if (message.event === "COUNTDOWN_START") setRoom((current) => current ? { ...current, status: "PLAYING", question: message.data.question } : current)
            }
            if (message.event === "ERROR") setError(message.data?.message || "Phòng đã gặp lỗi.")
          } catch {
            setError("Không đọc được dữ liệu phòng từ máy chủ.")
          }
        }
      } catch (err) {
        if (active) setError(err.response?.data?.message || "Không thể tải phòng. Hãy kiểm tra mã phòng và đăng nhập lại.")
      }
    }
    connect()
    return () => {
      active = false
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [roomCode, user, loading])

  const ready = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) socketRef.current.send(JSON.stringify({ action: "player_ready" }))
    else setError("Kết nối phòng chưa sẵn sàng. Vui lòng thử lại.")
  }
  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(roomCode)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setError("Trình duyệt không cho phép sao chép mã phòng.")
    }
  }
  const currentPlayer = room?.players?.find((player) => player.user_id === user?.id)

  if (!user && !loading) return <section className="arena-page"><div className="arena-panel"><h1>Hãy đăng nhập để vào phòng.</h1><Link className="button" to="/login">Đăng nhập</Link></div></section>
  return <section className="arena-page">
    <div className="arena-heading"><Link className="watch-link" to="/arena"><ArrowLeft size={16}/> Quay lại đấu trường</Link><div className="eyebrow"><span className="eyebrow-line"/> CODEDUEL ROOM</div><h1>Phòng <span>{roomCode}</span></h1><p>{connection === "connected" ? "Đã kết nối trực tiếp với phòng." : "Đang kết nối với phòng…"}</p></div>
    {error && <div className="arena-message" role="alert">{error}</div>}
    {room && <div className="arena-panel room-panel">
      <div className="leader-card-head"><span><Users size={17}/> NGƯỜI CHƠI</span><button className="watch-link" type="button" onClick={copyCode}>{copied ? <Check size={15}/> : <Copy size={15}/>} {copied ? "Đã sao chép" : "Sao chép mã"}</button></div>
      <div className="room-players">{(room.players || []).map((player) => <div className="room-player" key={player.user_id}><span className="rank-avatar">{player.username?.slice(0, 1).toUpperCase()}</span><span><b>{player.username}{player.user_id === user?.id ? " (Bạn)" : ""}</b><small>{player.is_ready ? "Đã sẵn sàng" : "Đang chờ"} · {player.rating} điểm</small></span>{player.is_ready && <Check size={17}/>}</div>)}{(room.players || []).length < 2 && <div className="room-waiting"><Users size={18}/> Đang chờ đối thủ tham gia…</div>}</div>
      {room.status === "WAITING" && <div className="room-controls"><p>{countdown ? `Trận đấu bắt đầu sau ${countdown}…` : "Khi cả hai người chơi sẵn sàng, trận đấu sẽ bắt đầu."}</p><button className="button" type="button" onClick={ready} disabled={Boolean(currentPlayer?.is_ready) || connection !== "connected"}>{currentPlayer?.is_ready ? "Bạn đã sẵn sàng" : "Sẵn sàng"} <Swords size={16}/></button></div>}
      {room.status === "PLAYING" && room.question && <article className="room-question"><span className="feature-index">{room.question.difficulty || "THỬ THÁCH"}</span><h2>{room.question.title}</h2><p>{room.question.description}</p><p className="auth-sub">Phòng đã nhận đề bài. Phần nộp mã sẽ khả dụng khi backend cung cấp API submission.</p></article>}
    </div>}
  </section>
}
