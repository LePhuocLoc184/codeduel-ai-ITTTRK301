import { AlertTriangle, CheckCircle2, Info, Loader2 } from "lucide-react"
import "./ArenaExtras.css"

// AC 2.1: lớp phủ làm mờ với chữ số đếm ngược 3-2-1 ở giữa màn hình. Biến mất khi value = null (nhận START).
export function CountdownOverlay({ value }) {
  if (value == null) return null

  return (
    <div className="countdown-overlay" role="status" aria-live="assertive">
      <span className="countdown-digit" key={value}>{value}</span>
    </div>
  )
}

export function RoomEventToast({ event }) {
  if (!event) return null
  const icon = event.busy
    ? <Loader2 size={17} className="console-spin" />
    : event.tone === "success"
      ? <CheckCircle2 size={17} />
      : event.tone === "warning"
        ? <AlertTriangle size={17} />
        : <Info size={17} />
  const title = event.title || (event.busy ? "Đang chuẩn bị trận" : "Thông báo phòng")

  return (
    <div key={event.id} className={`room-event-toast room-event-${event.tone || "info"}${event.busy ? " is-busy" : ""}`} role={event.tone === "warning" ? "alert" : "status"} aria-live="polite">
      <div className="room-event-icon">{icon}</div>
      <div className="room-event-copy">
        <strong>{title}</strong>
        <span>{event.text}</span>
      </div>
      {!event.busy && <div className="room-event-progress" aria-hidden="true" />}
    </div>
  )
}

// AC 1.2: thông báo trạng thái kết nối ở góc màn hình (hiện cả khi đang thi đấu).
export function ConnectionToast({ state, attempt, max, failed }) {
  if (failed) {
    return (
      <div className="conn-toast conn-toast-failed" role="alert">
        <AlertTriangle size={15} /> Mất kết nối với máy chủ. Hãy tải lại trang.
      </div>
    )
  }

  if (state !== "reconnecting") return null

  return (
    <div className="conn-toast" role="status">
      <Loader2 size={15} className="console-spin" /> Đang thử kết nối lại... ({attempt}/{max})
    </div>
  )
}
