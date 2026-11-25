import { Code2, GraduationCap } from "lucide-react"
import { Link } from "react-router-dom"
import BrandLogo from "./BrandLogo"
import useMotionPreference from "../hooks/useMotionPreference"
import useScrollReveal from "../hooks/useScrollReveal"
import "./Footer.css"

const TEAM_MEMBERS = [
  { name: "Lê Phước Lộc", studentId: "[Điền MSSV]", role: "Full-stack / Frontend Lead" },
  { name: "[Thành viên 2 - Điền họ tên]", studentId: "[Điền MSSV]", role: "Backend & Judge Engine" },
  { name: "[Thành viên 3 - Điền họ tên]", studentId: "[Điền MSSV]", role: "AI Review & Database" },
  { name: "[Thành viên 4 - Điền họ tên]", studentId: "[Điền MSSV]", role: "UI/UX & Testing" },
]

export default function Footer() {
  const footerRef = useScrollReveal()
  const viewTransition = useMotionPreference()

  return (
    <footer ref={footerRef} className="site-footer scroll-reveal">
      <div className="site-footer-inner">
        <div className="site-footer-main">
          <section className="footer-platform" aria-labelledby="footer-platform-title">
            <Link className="footer-brand" to="/home" viewTransition={viewTransition} aria-label="CodeDuel.dev — Trang chủ">
              <BrandLogo size={34} />
            </Link>
            <h2 id="footer-platform-title">CodeDuel AI</h2>
            <p className="footer-description">
              Nền tảng thi đấu lập trình đối kháng 1v1 thời gian thực, tích hợp chấm code tự động và AI Code Review sau trận.
            </p>
            <div className="footer-academic">
              <GraduationCap size={17} aria-hidden="true" />
              <span>Đồ án môn học — Học viện Công nghệ Bưu chính Viễn thông (PTIT)</span>
            </div>
          </section>

          <nav className="footer-navigation" aria-label="Điều hướng chân trang">
            <h2>Khám phá</h2>
            <ul>
              <li><Link to="/home" viewTransition={viewTransition}>Trang chủ</Link></li>
              <li><Link to="/arena" viewTransition={viewTransition}>Sảnh đấu trường</Link></li>
              <li><Link to="/home#features" viewTransition={viewTransition}>Tính năng</Link></li>
              <li><Link to="/home#leaderboard" viewTransition={viewTransition}>Bảng xếp hạng</Link></li>
            </ul>
          </nav>

          <section className="footer-team" aria-labelledby="footer-team-title">
            <h2 id="footer-team-title">Nhóm phát triển</h2>
            <ul className="footer-team-list">
              {TEAM_MEMBERS.map((member, index) => (
                <li className="footer-team-member" key={member.name}>
                  <span className="footer-member-number">{String(index + 1).padStart(2, "0")}</span>
                  <span className="footer-member-details">
                    <strong>{member.name}</strong>
                    <small>{member.studentId}</small>
                    <span>{member.role}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="site-footer-bottom">
          <p>© 2026 CodeDuel AI. Phát triển bởi sinh viên Học viện Công nghệ Bưu chính Viễn thông (PTIT).</p>
          <span className="footer-tech" aria-label="Công nghệ cốt lõi">
            <Code2 size={14} aria-hidden="true" />
            React <i /> FastAPI <i /> AI Judge
          </span>
        </div>
      </div>
    </footer>
  )
}
