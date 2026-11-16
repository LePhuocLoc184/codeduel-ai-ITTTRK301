import { useEffect, useState } from "react"
import { Shield, Target, Trophy } from "lucide-react"
import api from "../api/axios"
import { useAuth } from "../context/AuthContext"
import "./ProfileCard.css"

// Cùng ngưỡng với backend (RankBadge): <1300 BRONZE, 1300-1499 SILVER, 1500-1699 GOLD, >=1700 DIAMOND.
const rankBadgeFor = (rating) => (rating >= 1700 ? "DIAMOND" : rating >= 1500 ? "GOLD" : rating >= 1300 ? "SILVER" : "BRONZE")
const winRateFor = (wins, games) => (games > 0 ? (wins / games) * 100 : 0)
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
  const showImage = Boolean(data.avatar_url) && brokenAvatar !== data.avatar_url

  return <section className={`profile-card profile-rank-${rank.toLowerCase()}`} aria-label="Thẻ người chơi">
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
}