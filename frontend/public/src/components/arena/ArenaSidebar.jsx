import { memo } from "react"
import { Clock, Keyboard, ScrollText, Swords } from "lucide-react"

// Cột phải: các khu vực đối thủ, đồng hồ, trạng thái gõ phím, sự kiện.
// Dữ liệu thật (socket, đồng hồ, ...) sẽ được nối ở AC4.
const SECTIONS = [
  { icon: Swords, label: "ĐỐI THỦ", text: "Đang chờ thông tin đối thủ…" },
  { icon: Clock, label: "THỜI GIAN", text: "--:--" },
  { icon: Keyboard, label: "TRẠNG THÁI", text: "Đối thủ chưa gõ code." },
  { icon: ScrollText, label: "SỰ KIỆN", text: "Chưa có sự kiện nào." },
]

function ArenaSidebar() {
  return (
    <div className="arena-sidebar">
      {SECTIONS.map(({ icon: Icon, label, text }) => (
        <section className="side-card" key={label}>
          <div className="side-card-head">
            <Icon size={14} />
            <span className="panel-label">{label}</span>
          </div>

          <div className="side-card-body">{text}</div>
        </section>
      ))}
    </div>
  )
}

// memo: gõ code trong editor không làm render lại đề bài / console / cột phải.
export default memo(ArenaSidebar)