import { memo, useEffect, useState } from "react"
import { Clock, Keyboard, ScrollText, Shield, Swords } from "lucide-react"
import Avatar from "../Avatar"

// Cùng ngưỡng với backend (RankBadge): <1300 BRONZE, 1300-1499 SILVER, 1500-1699 GOLD, >=1700 DIAMOND.
// Phòng chỉ trả rating của người chơi nên badge được suy ra từ rating.
const rankBadgeFor = (rating) =>
  rating >= 1700 ? "DIAMOND" : rating >= 1500 ? "GOLD" : rating >= 1300 ? "SILVER" : "BRONZE"

const pad = (value) => String(value).padStart(2, "0")

// Đồng hồ tự đếm mỗi giây nên tách riêng: chỉ phần này render lại, không kéo theo cả phòng.
function MatchClock({ deadline }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!deadline) return undefined
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [deadline])

  if (!deadline) return <span className="match-clock">--:--</span>

  const left = Math.max(0, Math.ceil((deadline - now) / 1000))
  const urgent = left <= 60

  return (
    <>
      <span className={`match-clock${urgent ? " warn" : ""}`}>
        {pad(Math.floor(left / 60))}:{pad(left % 60)}
      </span>
      {left === 0 && <small className="match-clock-note">Đã hết giờ</small>}
    </>
  )
}

const formatEventTime = (at) =>
  new Date(at).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })

// Cột phải: đối thủ, đồng hồ, trạng thái gõ phím, sự kiện (dữ liệu từ socket của phòng).
function ArenaSidebar({
  opponent = null,
  opponentProgress = null,
  deadline = null,
  opponentTyping = false,
  connection = "connecting",
  events = [],
}) {
  const percent = Math.min(100, Math.max(0, Number(opponentProgress?.percent) || 0))

  let status = "Đối thủ chưa gõ code."
  if (connection === "disconnected") status = "Mất kết nối với phòng. Hãy tải lại trang để vào lại."
  else if (opponent?.left) status = "Đối thủ đã rời phòng."
  else if (opponentTyping) status = "Đối thủ đang gõ code…"

  return (
    <div className="arena-sidebar">
      <section className="side-card">
        <div className="side-card-head">
          <Swords size={14} />
          <span className="panel-label">ĐỐI THỦ</span>
        </div>

        <div className="side-card-body">
          {opponent ? (
            <div className="opponent-card">
              <Avatar url={opponent.avatar_url} name={opponent.username} className="avatar-lg" />
              <span>
                <b title={opponent.username}>{opponent.username}</b>
                <small>{opponent.rating} điểm{opponent.left ? " · đã rời phòng" : ""}</small>
                <em className={`rank-chip rank-chip-${rankBadgeFor(Number(opponent.rating) || 0).toLowerCase()}`}>
                  <Shield size={11} /> {rankBadgeFor(Number(opponent.rating) || 0)}
                </em>
              </span>
            </div>
          ) : (
            "Đang chờ thông tin đối thủ…"
          )}

          {opponentProgress && (
            <div className="opponent-progress">
              <div
                className="progress-bar"
                role="progressbar"
                aria-label="Tiến độ của đối thủ"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(percent)}
              >
                <i style={{ width: `${percent}%` }} />
              </div>
              <small>{opponentProgress.passed}/{opponentProgress.total} testcase</small>
            </div>
          )}
        </div>
      </section>

      <section className="side-card">
        <div className="side-card-head">
          <Clock size={14} />
          <span className="panel-label">THỜI GIAN</span>
        </div>
        <div className="side-card-body"><MatchClock deadline={deadline} /></div>
      </section>

      <section className="side-card">
        <div className="side-card-head">
          <Keyboard size={14} />
          <span className="panel-label">TRẠNG THÁI</span>
        </div>
        <div className="side-card-body" aria-live="polite">
          {opponentTyping && connection !== "disconnected" && !opponent?.left && <i className="typing-dot" />}
          {status}
        </div>
      </section>

      <section className="side-card">
        <div className="side-card-head">
          <ScrollText size={14} />
          <span className="panel-label">SỰ KIỆN</span>
        </div>

        <div className="side-card-body">
          {events.length ? (
            <ul className="event-list">
              {events.map((event) => (
                <li key={event.id} className={`event-item event-${event.tone}`}>
                  <time>{formatEventTime(event.at)}</time>
                  <span>{event.text}</span>
                </li>
              ))}
            </ul>
          ) : (
            "Chưa có sự kiện nào."
          )}
        </div>
      </section>
    </div>
  )
}

// memo: gõ code trong editor không làm render lại đề bài / console / cột phải.
export default memo(ArenaSidebar)