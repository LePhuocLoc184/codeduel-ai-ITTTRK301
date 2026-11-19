import { useEffect, useState } from "react"
import { History, Shield, Target, Trophy } from "lucide-react"
import api from "../api/axios"
import { useAuth } from "../context/AuthContext"
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
  const [profile, setProfile] = useState(null)
  const [brokenAvatar, setBrokenAvatar] = useState(null)

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

  return <>
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
  {recent.length > 0 && <section className="profile-history" aria-label="Trận đấu gần đây">
    <div className="profile-history-head"><History size={12} /> TRẬN GẦN ĐÂY</div>
    <ul>{recent.map((match) => <li key={match.room_id}>
      <span className={`history-result ${match.is_win ? "win" : "loss"}`}>{match.is_win ? "THẮNG" : "THUA"}</span>
      <span className="history-mode">{MODE_LABELS[match.game_mode] || match.game_mode}</span>
      <time>{formatDate(match.finished_at)}</time>
      <em className={match.elo_change > 0 ? "up" : match.elo_change < 0 ? "down" : ""}>{match.elo_change > 0 ? `+${match.elo_change}` : match.elo_change} điểm</em>
    </li>)}</ul>
  </section>}
  </>
}