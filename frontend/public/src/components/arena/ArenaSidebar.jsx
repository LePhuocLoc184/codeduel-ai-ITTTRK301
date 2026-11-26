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
  connection = "connected",
  events = [],
}) {
  const passed = Number(opponentProgress?.passed) || 0
  const total = Number(opponentProgress?.total) || 0
  const percent = total > 0 ? Math.min(100, Math.max(0, (passed / total) * 100)) : (Number(opponentProgress?.percent) || 0)

  let statusText = "Đối thủ đang suy nghĩ giải thuật..."
  if (connection === "reconnecting") statusText = "Mất kết nối, đang tự nối lại…"
  if (connection === "disconnected") statusText = "Mất kết nối với phòng. Hãy tải lại trang."
  else if (opponent?.left) statusText = "Đối thủ đã rời phòng."
  else if (opponentTyping) statusText = "Đang gõ phím liên tục…"

  return (
    <div className="arena-sidebar">
      <section className="side-card">
        <div className="side-card-head">
          <Swords size={14} />
          <span className="panel-label">ĐỐI THỦ</span>
          {opponentProgress && (
            <span className="opponent-score-badge">
              {passed}/{total} Passed
            </span>
          )}
        </div>

        <div className="side-card-body">
          {opponent ? (
            <div className="opponent-card">
              <Avatar url={opponent.avatar_url} name={opponent.username} className="avatar-lg" />
              <span>
                <span className="opponent-name-row">
                  <b title={opponent.username}>{opponent.username}</b>
                  <span
                    className={`opponent-typing-waveform${opponentTyping && connection === "connected" && !opponent.left ? " is-active" : ""}`}
                    aria-label={opponentTyping && connection === "connected" && !opponent.left ? "Đối thủ đang gõ code" : undefined}
                    aria-hidden={!(opponentTyping && connection === "connected" && !opponent.left)}
                  >
                    <i /><i /><i /><i /><i />
                  </span>
                </span>
                <small>{opponent.rating} ELO{opponent.left ? " · đã rời phòng" : ""}</small>
                <em className={`rank-chip rank-chip-${rankBadgeFor(Number(opponent.rating) || 0).toLowerCase()}`}>
                  <Shield size={11} /> {rankBadgeFor(Number(opponent.rating) || 0)}
                </em>
              </span>
            </div>
          ) : (
            "Đang chờ thông tin đối thủ…"
          )}

          {/* Segmented Testcase Progression */}
          {opponentProgress && total > 0 && (
            <div className="opponent-progress">
              <div className="segmented-progress-wrap" role="progressbar" aria-valuenow={passed} aria-valuemax={total} aria-label="Tiến độ testcase đối thủ">
                {Array.from({ length: total }, (_, i) => {
                  const isPassed = i < passed
                  return (
                    <div
                      key={i}
                      className={`progress-segment ${isPassed ? "segment-passed" : "segment-pending"}`}
                      title={`Testcase ${i + 1}: ${isPassed ? "Passed" : "Pending"}`}
                    />
                  )
                })}
              </div>
              <div className="progress-meta">
                <span>{passed}/{total} testcase</span>
                <span>{Math.round(percent)}% hoàn thành</span>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="side-card">
        <div className="side-card-head">
          <Clock size={14} />
          <span className="panel-label">THỜI GIAN THI ĐẤU</span>
        </div>
        <div className="side-card-body"><MatchClock deadline={deadline} /></div>
      </section>

      <section className="side-card">
        <div className="side-card-head">
          <Keyboard size={14} />
          <span className="panel-label">TRẠNG THÁI GÕ PHÍM</span>
        </div>
        <div className="side-card-body" aria-live="polite">
          <div className="typing-status-container">
            <span className={`typing-state-indicator${opponentTyping && connection === "connected" && !opponent?.left ? " is-active" : ""}`} />
            <span className="typing-text">{statusText}</span>
          </div>
        </div>
      </section>

      <section className="side-card">
        <div className="side-card-head">
          <ScrollText size={14} />
          <span className="panel-label">DIỄN BIẾN TRẬN ĐẤU</span>
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