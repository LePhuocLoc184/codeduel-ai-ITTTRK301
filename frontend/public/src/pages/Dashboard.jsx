import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowDown, ArrowRight, Braces, ChevronRight, CirclePlay, Code2, Crown, Flame, Swords, Trophy, Users, Zap } from "lucide-react"
import api from "../api/axios"
import { useAuth } from "../context/AuthContext"
import useMotionPreference from "../hooks/useMotionPreference"
import useScrollReveal from "../hooks/useScrollReveal"

const PREVIEW_CODE = [
  "def two_sum(nums, target):",
  "  seen = {}",
  "",
  "  for i, n in enumerate(nums):",
  "    complement = target - n",
  "    if complement in seen:",
  "      return [seen[complement], i]",
  "    seen[n] = i",
].join("\n")

const PYTHON_TOKENS = /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:def|for|in|if|return)\b|\b(?:enumerate|two_sum)\b|\b\d+(?:\.\d+)?\b/g

function renderHighlightedCode(source) {
  const parts = []
  let cursor = 0
  let match

  while ((match = PYTHON_TOKENS.exec(source)) !== null) {
    if (match.index > cursor) {
      parts.push(<span key={`text-${cursor}`}>{source.slice(cursor, match.index)}</span>)
    }

    const token = match[0]
    const className = token === "enumerate" || token === "two_sum"
      ? "syntax-blue"
      : token.startsWith("\"") || token.startsWith("'")
        ? "syntax-string"
        : /^\d/.test(token)
          ? "syntax-number"
          : "syntax-purple"

    parts.push(<span className={className} key={`token-${match.index}`}>{token}</span>)
    cursor = match.index + token.length
  }

  if (cursor < source.length) {
    parts.push(<span key={`text-${cursor}`}>{source.slice(cursor)}</span>)
  }

  return parts
}

function CodeWindow() {
  const [typedLength, setTypedLength] = useState(0)
  const complete = typedLength === PREVIEW_CODE.length
  const typedCode = PREVIEW_CODE.slice(0, typedLength)
  const lines = typedCode.split("\n")
  const currentLine = lines.length
  const currentColumn = Math.max(lines[lines.length - 1].length, 1)

  useEffect(() => {
    const timer = window.setTimeout(
      () => setTypedLength((length) => (length >= PREVIEW_CODE.length ? 0 : length + 1)),
      complete ? 2800 : 55,
    )
    return () => window.clearTimeout(timer)
  }, [typedLength, complete])

  return (
    <div className="code-window">
      <div className="window-bar">
        <div className="window-dots"><i /><i /><i /></div>
        <span>solution.py</span>
        <span className="window-live"><i /> LIVE MATCH</span>
      </div>
      <div className="code-body">
        <div className="code-gutter">
          {lines.map((_, index) => <span key={index}>{String(index + 1).padStart(2, "0")}</span>)}
        </div>
        <pre>{renderHighlightedCode(typedCode)}<span className="typing-you-tag" aria-hidden="true">you</span></pre>
      </div>
      <div className={`floating-result${complete ? " is-complete" : ""}`}>
        <span className="result-icon"><Zap size={15} /></span>
        <span><b>Accepted</b><small>Runtime 42ms</small></span>
        <span className="result-check">✓</span>
      </div>
      <div className="window-footer">
        <span><i /> Python 3.12</span>
        <span>Ln {String(currentLine).padStart(2, "0")}, Col {String(currentColumn).padStart(2, "0")}</span>
        <span>UTF-8</span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const viewTransition = useMotionPreference()
  const featuresHeadingRef = useScrollReveal()
  const featureOneRef = useScrollReveal()
  const featureTwoRef = useScrollReveal()
  const featureThreeRef = useScrollReveal()
  const leaderboardIntroRef = useScrollReveal()
  const leaderboardCardRef = useScrollReveal()
  const ctaRef = useScrollReveal()
  const [ranks, setRanks] = useState([])
  useEffect(() => { api.get("/api/v1/users/leaderboard").then(({ data }) => { if (Array.isArray(data.data) && data.data.length) setRanks(data.data.slice(0, 10)) }).catch(() => {}) }, [])
  return <>
    <section className="hero section-wrap"><div className="hero-copy"><div className="eyebrow"><span className="eyebrow-line"/> THE ARENA FOR DEVELOPERS</div><h1>Code. Compete.<br/><span>Conquer.</span></h1><p className="hero-description">Nâng trình lập trình của bạn qua những trận đấu 1v1. Giải thuật, tốc độ và bản lĩnh — tất cả trong một đấu trường.</p><div className="hero-actions"><Link className="button button-large" to={user ? "/arena" : "/login"} viewTransition={viewTransition}>Tham gia đấu <ArrowRight size={17}/></Link><a className="watch-link" href="#features"><span><CirclePlay size={18}/></span> Khám phá CodeDuel</a></div><div className="hero-proof"><div className="avatar-stack"><span>H</span><span>M</span><span>T</span><span>+</span></div><p><b>Cộng đồng coder</b> đang cùng bạn luyện tập</p></div></div><div className="hero-visual"><div className="visual-glow"/><div className="visual-grid"/><div className="terminal-tag"><span>●</span> MATCH FOUND <b>#2048</b></div><CodeWindow/><div className="elo-card"><span className="elo-icon"><Trophy size={16}/></span><span><small>RATING</small><b>1,284 <em>+24</em></b></span><span className="elo-spark">▁▃▂▅▄▇</span></div><div className="floating-braces"><Braces size={33}/></div></div><a className="scroll-note" href="#features"><ArrowDown size={13}/> SCROLL TO EXPLORE</a></section>
    <section id="features" className="features section-wrap"><div className="section-heading scroll-reveal" ref={featuresHeadingRef}><div><div className="eyebrow"><span className="eyebrow-line"/> WHY CODEDUEL</div><h2>Biến kỹ năng thành <span>lợi thế.</span></h2></div><p>Mỗi trận đấu là một cơ hội để bạn tiến bộ<br/>và chứng minh bản thân.</p></div><div className="feature-grid"><article ref={featureOneRef} className="feature-card scroll-reveal" style={{ "--scroll-reveal-delay": "0ms" }}><div className="feature-icon purple"><Swords size={20}/></div><span className="feature-index">01 / COMPETE</span><h3>Đấu 1v1 thời gian thực</h3><p>So tài giải thuật trực tiếp với đối thủ cùng trình độ. Mỗi giây đều tạo nên khác biệt.</p><Link to="/arena" viewTransition={viewTransition}>Tìm hiểu thêm <ChevronRight size={14}/></Link></article><article ref={featureTwoRef} className="feature-card scroll-reveal" style={{ "--scroll-reveal-delay": "90ms" }}><div className="feature-icon green"><Flame size={20}/></div><span className="feature-index">02 / IMPROVE</span><h3>Leo hạng, tăng rating</h3><p>Hệ thống xếp hạng minh bạch ghi nhận từng chiến thắng và hành trình của bạn.</p><a href="#leaderboard">Xem bảng xếp hạng <ChevronRight size={14}/></a></article><article ref={featureThreeRef} className="feature-card scroll-reveal" style={{ "--scroll-reveal-delay": "180ms" }}><div className="feature-icon blue"><Code2 size={20}/></div><span className="feature-index">03 / BUILD</span><h3>Giải thuật, thực chiến</h3><p>Thử thách đa dạng từ cấu trúc dữ liệu đến thuật toán trong môi trường thi đấu.</p><Link to="/arena" viewTransition={viewTransition}>Khám phá bài tập <ChevronRight size={14}/></Link></article></div></section>
    <section id="leaderboard" className="leaderboard section-wrap">
      <div ref={leaderboardIntroRef} className="leader-intro scroll-reveal">
        <div className="eyebrow"><span className="eyebrow-line" /> TOP PLAYERS</div>
        <h2>Những người<br />dẫn đầu <span>đấu trường.</span></h2>
        <p>Chinh phục bảng xếp hạng và ghi tên bạn vào danh sách những coder xuất sắc nhất.</p>
        <Link className="text-link" to={user ? "/arena" : "/login"} viewTransition={viewTransition}>Vào đấu trường <ArrowRight size={16} /></Link>
      </div>
      <div ref={leaderboardCardRef} className="leader-card scroll-reveal" style={{ "--scroll-reveal-delay": "90ms" }}>
        <div className="leader-card-head">
          <span><Trophy size={16} /> BẢNG XẾP HẠNG</span>
          <span className="season-tag">TOP 100</span>
        </div>
        {ranks.length ? ranks.map((player, index) => {
          const isCurrentUser = Boolean(user && player.username === user.username)
          const rankBadge = player.rank_badge || "BRONZE"
          return (
            <div className={`leader-row${isCurrentUser ? " leader-row-you" : ""}`} key={player.id || player.username}>
              <span className={`rank-num${index < 3 ? ` rank-${index + 1}` : ""}`}>{String(index + 1).padStart(2, "0")}</span>
              <span className={`rank-avatar${index < 3 ? ` avatar-${index + 1}` : ""}`}>{player.username.slice(0, 1).toUpperCase()}</span>
              <span className="rank-name">
                <span className="leader-player-name">
                  <b>{player.username}</b>
                  {isCurrentUser && <span className="leader-you-badge">BẠN</span>}
                </span>
                <small>
                  <span className={`leader-rank-badge leader-rank-${String(rankBadge).toLowerCase()}`}>{rankBadge}</span>
                  <span>{player.wins ?? 0}/{player.rated_games ?? 0} thắng · {Math.round(Number(player.win_rate) || 0)}%</span>
                </small>
              </span>
              <span className="rank-points">{Number(player.rating).toLocaleString()} <small>pts</small></span>
              {index === 0 && <Crown className="crown" size={17} />}
            </div>
          )
        }) : <div className="leader-empty">Bảng xếp hạng sẽ hiển thị khi có dữ liệu người chơi.</div>}
        <Link className="leader-card-foot" to={user ? "/arena" : "/login"} viewTransition={viewTransition}>
          <span>Vào đấu trường</span><ArrowRight size={15} />
        </Link>
      </div>
    </section>
    <section ref={ctaRef} className="cta-band section-wrap scroll-reveal"><div className="cta-mark"><Users size={21}/></div><div><h2>{user ? `Sẵn sàng cho trận tiếp theo, ${user.username}?` : "Trận đấu tiếp theo đang chờ bạn."}</h2><p>Tham gia cộng đồng lập trình viên và bắt đầu hành trình hôm nay.</p></div><Link className="button" to={user ? "/arena" : "/register"} viewTransition={viewTransition}>{user ? "Vào đấu trường" : "Tạo tài khoản miễn phí"}<ArrowRight size={16}/></Link></section>
  </>
}