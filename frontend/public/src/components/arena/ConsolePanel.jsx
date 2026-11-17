import { memo } from "react"
import { Terminal } from "lucide-react"

// Khung Console ở cột giữa. Kết quả chạy thử / nộp bài sẽ được gắn vào đây ở AC3.
function ConsolePanel() {
  return (
    <div className="console-panel">
      <div className="console-head">
        <Terminal size={14} />
        <span className="panel-label">CONSOLE</span>
      </div>

      <div className="console-body">
        Chưa có kết quả. Chạy thử code để xem đầu ra của từng testcase.
      </div>
    </div>
  )
}

// memo: gõ code trong editor không làm render lại đề bài / console / cột phải.
export default memo(ConsolePanel)