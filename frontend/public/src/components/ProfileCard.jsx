import { useEffect, useState } from "react"
import { ArrowRight, History, Shield, Target, Trophy } from "lucide-react"
import { Link } from "react-router-dom"
import api from "../api/axios"
import { useAuth } from "../context/AuthContext"
import useMotionPreference from "../hooks/useMotionPreference"
import "./ProfileCard.css"

// Cùng ngưỡng với backend (RankBadge): <1300 BRONZE, 1300-1499 SILVER, 1500-1699 GOLD, >=1700 DIAMOND.
const rankBadgeFor = (rating) => (rating >= 1700 ? "DIAMOND" : rating >= 1500 ? "GOLD" : rating >= 1300 ? "SILVER" : "BRONZE")
const winRateFor = (wins, games) => (games > 0 ? (wins / games) * 100 : 0)
const formatDate = (value) => {
  const time = value ? Date.parse(/(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`) : NaN
  return Number.isNaN(time) ? "—" : new Date(time).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
}
const MODE_LABELS = { RANKED_1V1: "Ranked", CUSTOM_1V1: "Phòng riêng" }
const formatPercent = (value) => `${Math.round(Number(value || 0) * 10) / 10}%`

export default function ProfileCard() {
  const { user } = useAuth()
  const viewTransition = useMotionPreference()
  const [profile, setProfile] = useState(null)
  const [brokenAvatar, setBrokenAvatar] = useState(null)
  const [historyFilter, setHistoryFilter] = useState("ALL")

  // User lưu lúc đăng nhập chưa có win_rate / rank_badge, nên lấy bản đầy đủ & mới nhất từ /users/me.
  useEffect(() => {
    if (!user?.id) return undefined
    let active = true
    api.get("/api/v1/users/me")
      .then(({ data }) => { if (active) setProfile(data.data) })
      .catch(() => {})
    return () => { active = false }
  }, [user?.id])

  if (!user) return null
  // avatar_url lấy từ user (được cập nhật ngay sau khi đổi ảnh) thay vì bản profile đã tải trước đó.
  const data = profile?.id === user.id ? { ...user, ...profile, avatar_url: user.avatar_url } : user
  const rating = Number(data.rating ?? 1200)
  const rank = String(data.rank_badge || rankBadgeFor(rating)).toUpperCase()
  const winRate = Math.min(100, Math.max(0, Number(data.win_rate ?? winRateFor(data.wins ?? 0, data.rated_games ?? 0))))
  const recent = profile?.id === user.id && Array.isArray(profile.recent_matches) ? profile.recent_matches : []
  const showImage = Boolean(data.avatar_url) && brokenAvatar !== data.avatar_url

  const filteredRecent = recent.filter((match) => {
    if (historyFilter === "ALL") return true
    return match.game_mode === historyFilter
  })

  const netElo = filteredRecent.reduce((sum, m) => sum + (Number(m.elo_change) || 0), 0)
  const emptyHistoryTitle = historyFilter === "ALL"
    ? "Chưa có trận đấu nào"
    : historyFilter === "RANKED_1V1"
      ? "Chưa có trận Ranked"
      : "Chưa có phòng riêng"
  const emptyHistoryDescription = historyFilter === "ALL"
    ? "Hoàn thành trận đầu tiên để lịch sử của bạn xuất hiện tại đây."
    : historyFilter === "RANKED_1V1"
      ? "Bạn chưa có trận xếp hạng nào trong lịch sử."
      : "Bạn chưa có trận phòng riêng nào trong lịch sử."

  return (
    <>
      <section className={`profile-card profile-rank-${rank.toLowerCase()}`} aria-label="Thẻ người chơi">
        <div className="profile-avatar">
          {showImage
            ? <img src={data.avatar_url} alt={`Avatar của ${data.username}`} onError={() => setBrokenAvatar(data.avatar_url)} />
            : <span aria-hidden="true">{data.username.slice(0, 1).toUpperCase()}</span>}
        </div>
        <div className="profile-id">
          <span className="profile-name" title={data.username}>{data.username}</span>
          <span className="profile-badge"><Shield size={12} /> {rank}</span>
        </div>
        <div className="profile-stats">
          <div className="profile-stat">
            <small><Trophy size={11} /> RATING</small>
            <b>{rating.toLocaleString()}</b>
          </div>
          <div className="profile-stat">
            <small><Target size={11} /> WIN RATE</small>
            <b>{formatPercent(winRate)}</b>
            <div className="winrate-bar" role="progressbar" aria-label="Tỷ lệ thắng" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(winRate)}><i style={{ width: `${winRate}%` }} /></div>
            <em>{data.wins ?? 0} thắng / {data.rated_games ?? 0} trận</em>
          </div>
        </div>
      </section>

      <section className="profile-history" aria-label="Trận đấu gần đây">
          <div
            className="profile-history-head"
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <History size={13} />
              <span>TRẬN GẦN ĐÂY ({filteredRecent.length})</span>
              {netElo !== 0 && (
                <span
                  style={{
                    fontSize: "12px",
                    padding: "2px 8px",
                    borderRadius: "999px",
                    background: netElo > 0 ? "rgba(180, 245, 102, 0.12)" : "rgba(255, 155, 145, 0.12)",
                    color: netElo > 0 ? "#b4f566" : "#ff9b91",
                    fontWeight: 600,
                  }}
                >
                  {netElo > 0 ? `+${netElo}` : netElo} ELO
                </span>
              )}
            </div>

            <div style={{ display: "flex", gap: "6px" }}>
              {[
                { key: "ALL", label: "Tất cả" },
                { key: "RANKED_1V1", label: "Ranked" },
                { key: "CUSTOM_1V1", label: "Phòng riêng" },
              ].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setHistoryFilter(tab.key)}
                  style={{
                    padding: "3px 10px",
                    fontSize: "12px",
                    borderRadius: "6px",
                    border: "1px solid",
                    borderColor: historyFilter === tab.key ? "#b4f566" : "#20252b",
                    background: historyFilter === tab.key ? "rgba(180, 245, 102, 0.12)" : "#101317",
                    color: historyFilter === tab.key ? "#b4f566" : "#858d98",
                    cursor: "pointer",
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {filteredRecent.length > 0 ? (
            <ul>
              {filteredRecent.map((match) => {
                const shortId = String(match.room_id || "").slice(0, 6).toUpperCase()
                const isRanked = match.game_mode === "RANKED_1V1"

                return (
                  <li
                    key={match.room_id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px 14px",
                    }}
                  >
                    {/* Bên trái: Badge Thắng/Thua + Tên chế độ + Mã trận & Giờ */}
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <span className={`history-result ${match.is_win ? "win" : "loss"}`}>
                        {match.is_win ? "THẮNG" : "THUA"}
                      </span>

                      <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ color: "#f1f2f4", fontSize: "13px", fontWeight: 600 }}>
                            {isRanked ? "Đấu Hạng 1v1" : "Phòng Tùy Chỉnh"}
                          </span>
                          {shortId && (
                            <span
                              style={{
                                fontSize: "11px",
                                fontFamily: "DM Mono, monospace",
                                padding: "1px 6px",
                                borderRadius: "4px",
                                background: "#13171c",
                                border: "1px solid #20252b",
                                color: "#858d98",
                              }}
                            >
                              #{shortId}
                            </span>
                          )}
                        </div>

                        <span style={{ color: "#858d98", fontSize: "12px" }}>
                          {MODE_LABELS[match.game_mode] || match.game_mode} • <time>{formatDate(match.finished_at)}</time>
                        </span>
                      </div>
                    </div>

                    {/* Bên phải: Biến động ELO */}
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <em
                        className={match.elo_change > 0 ? "up" : match.elo_change < 0 ? "down" : ""}
                        style={{ fontSize: "13px", fontWeight: 600 }}
                      >
                        {match.elo_change > 0 ? `+${match.elo_change}` : match.elo_change} điểm
                      </em>
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : (
            <div className="profile-history-empty">
              <span className="profile-history-empty-icon"><Trophy size={18} /></span>
              <div className="profile-history-empty-copy">
                <strong>{emptyHistoryTitle}</strong>
                <p>{emptyHistoryDescription}</p>
              </div>
              <Link className="button button-small" to="/arena" viewTransition={viewTransition}>
                Bắt đầu trận đầu tiên <ArrowRight size={14} />
              </Link>
            </div>
          )}
      </section>
    </>
  )
}