import { memo } from "react"
import { Loader2, Terminal } from "lucide-react"

// Nhãn + tông màu cho trạng thái chấm bài của backend (SubmissionStatus).
const STATUS_META = {
  PASS: { label: "Chính xác", tone: "pass" },
  FAIL: { label: "Sai đáp án", tone: "fail" },
  WRONG_ANSWER: { label: "Sai đáp án", tone: "fail" },
  TLE: { label: "Quá thời gian", tone: "warn" },
  TIME_LIMIT_EXCEEDED: { label: "Quá thời gian", tone: "warn" },
  MLE: { label: "Quá bộ nhớ", tone: "warn" },
  MEMORY_LIMIT_EXCEEDED: { label: "Quá bộ nhớ", tone: "warn" },
  COMPILE_ERROR: { label: "Lỗi biên dịch", tone: "fail" },
  RUNTIME_ERROR: { label: "Lỗi khi chạy", tone: "fail" },
  PENDING: { label: "Đang chờ", tone: "warn" },
}

const statusMeta = (status) =>
  STATUS_META[status] || { label: status || "Không rõ", tone: "warn" }

const formatMs = (ms) => {
  const value = Number(ms) || 0
  return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${Math.round(value)}ms`
}

const formatMemory = (mb) => `${(Number(mb) || 0).toFixed(1)} MB`

function StatusChip({ status }) {
  const { label, tone } = statusMeta(status)
  return <span className={`console-status console-status-${tone}`}>{label}</span>
}

// AC 3.1: nhãn xanh/đỏ Passed / Failed cho từng testcase (kèm lý do cụ thể nếu là TLE/MLE/lỗi chạy).
function CaseChip({ item }) {
  if (item.passed) return <span className="console-status console-status-pass">Passed</span>
  const { label, tone } = statusMeta(item.status)
  return <span className={`console-status console-status-${tone}`}>{tone === "fail" ? `Failed · ${label}` : label}</span>
}

// AC 3.3: lỗi biên dịch / lỗi khi chạy.
const isCodeError = (status) => status === "COMPILE_ERROR" || status === "RUNTIME_ERROR"

function RunResult({ data }) {
  const results = data.results || []

  return (
    <>
      <div className="console-summary">
        <StatusChip status={data.status} />
        <span>
          Đạt {data.passed_count}/{data.total_count} testcase mẫu
        </span>
        <span>{formatMs(data.execution_time_ms)}</span>
        <span>{formatMemory(data.memory_used_mb)}</span>
      </div>

      {data.compile_error_message && (
        <pre className="console-error console-error-strong">{data.compile_error_message}</pre>
      )}

      {/* Lỗi tổng hợp (runtime...) in nguyên văn ở đầu console; lỗi riêng từng case vẫn hiện trong case đó. */}
      {!data.compile_error_message && data.error_message && (results.length === 0 || isCodeError(data.status)) && (
        <pre className="console-error console-error-strong">{data.error_message}</pre>
      )}

      {results.map((item, index) => (
        <details
          className="console-case"
          key={index}
          open={!item.passed || Boolean(item.error_message)}
        >
          <summary>
            <span>Case {index + 1}</span>
            <CaseChip item={item} />
            <span className="console-case-meta">
              {formatMs(item.execution_time_ms)} · {formatMemory(item.memory_used_mb)}
            </span>
          </summary>

          <div className="console-io">
            <div>
              <small>INPUT</small>
              <pre>{item.input}</pre>
            </div>
            <div>
              <small>KỲ VỌNG</small>
              <pre>{item.expected_output}</pre>
            </div>
            <div>
              <small>KẾT QUẢ CỦA BẠN</small>
              <pre>{item.actual_output ?? "—"}</pre>
            </div>
          </div>

          {item.error_message && <pre className="console-error">{item.error_message}</pre>}
        </details>
      ))}
    </>
  )
}

// Bài nộp chính thức chỉ trả số liệu tổng hợp, không có input/output của testcase ẩn.
function SubmitResult({ data }) {
  const passed = data.status === "PASS"

  return (
    <>
      <div className="console-summary">
        <StatusChip status={data.status} />
        <span>
          Đạt {data.passed_test_cases}/{data.total_test_cases} testcase
        </span>
        {data.execution_time != null && <span>{formatMs(data.execution_time * 1000)}</span>}
        {data.memory_used != null && <span>{formatMemory(data.memory_used)}</span>}
      </div>

      <p className="console-note">
        {passed
          ? "Bạn đã vượt qua tất cả testcase."
          : "Chưa đạt toàn bộ testcase. Hãy sửa code rồi nộp lại."}
      </p>

      {data.error_message && (
        <pre className={`console-error${isCodeError(data.status) ? " console-error-strong" : ""}`}>{data.error_message}</pre>
      )}
    </>
  )
}

// Khung Console ở cột giữa: hiển thị kết quả chạy thử / nộp bài trả về từ backend.
function ConsolePanel({ busy = null, output = null }) {
  const data = output?.data
  const hasCodeError = !busy && Boolean(data) && (isCodeError(data.status) || Boolean(data.compile_error_message))

  return (
    <div className={`console-panel${hasCodeError ? " console-panel-error" : ""}`}>
      <div className="console-head">
        <Terminal size={14} />
        <span className="panel-label">CONSOLE</span>
        {output && !busy && (
          <span className="console-kind">{output.kind === "run" ? "CHẠY THỬ" : "NỘP BÀI"}</span>
        )}
      </div>

      <div className="console-body">
        {busy ? (
          <div className="console-loading" role="status">
            <span className="console-loading-text">
              <Loader2 size={15} className="console-spin" />
              {busy === "run" ? "Đang chạy thử code…" : "Đang chấm bài…"}
            </span>
            {busy === "submit" && (
              <div className="grading-bar" role="progressbar" aria-label="Tiến độ chấm bài"><i /></div>
            )}
          </div>
        ) : output?.error ? (
          <div className="console-failure" role="alert">{output.error}</div>
        ) : output?.data ? (
          output.kind === "run" ? <RunResult data={output.data} /> : <SubmitResult data={output.data} />
        ) : (
          "Chưa có kết quả. Chạy thử code để xem đầu ra của từng testcase."
        )}
      </div>
    </div>
  )
}

// memo: gõ code trong editor không làm render lại đề bài / console / cột phải.
export default memo(ConsolePanel)