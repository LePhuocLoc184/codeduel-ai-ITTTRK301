import { memo } from "react"
import ReactMarkdown from "react-markdown"
import { Clock, MemoryStick } from "lucide-react"
import SampleCases from "./SampleCases"

const DIFFICULTY_LABELS = {
  EASY: "Dễ",
  MEDIUM: "Trung bình",
  HARD: "Khó",
}

function ProblemPanel({ question }) {
  const difficulty = String(question.difficulty || "").toUpperCase()

  return (
    <div className="problem-panel">
      <div className="problem-scroll">
        <div className="problem-head">
          <span className="panel-label">ĐỀ BÀI</span>
          <h2 className="problem-title">{question.title}</h2>

          <div className="problem-meta">
            {difficulty && (
              <span className={`difficulty-badge difficulty-${difficulty.toLowerCase()}`}>
                {DIFFICULTY_LABELS[difficulty] || difficulty}
              </span>
            )}

            {question.time_limit != null && (
              <span className="meta-chip">
                <Clock size={13} />
                {question.time_limit}s
              </span>
            )}

            {question.memory_limit != null && (
              <span className="meta-chip">
                <MemoryStick size={13} />
                {question.memory_limit} MB
              </span>
            )}
          </div>
        </div>

        <div className="markdown-body">
          <ReactMarkdown>{question.description || ""}</ReactMarkdown>
        </div>
      </div>

      <SampleCases
        key={question.id}
        testcases={question.public_testcases || []}
      />
    </div>
  )
}

// memo: gõ code trong editor không làm render lại đề bài / console / cột phải.
export default memo(ProblemPanel)