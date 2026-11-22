import { useEffect, useMemo, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { loader } from "@monaco-editor/react"
import { Bot, Loader2, RefreshCw } from "lucide-react"
import { getAIConfig, isAIConfigured, reviewMatchMarkdown } from "../../api/aiClient"
import "./ArenaExtras.css"

const LANGUAGE_NAMES = { cpp: "C++", python: "Python 3", java: "Java" }

// Cache kết quả theo phòng + người chơi để mở lại tab không gọi AI trùng lặp.
const cacheKey = (roomCode, userId) => `codeduel_ai_review:${roomCode}:${userId}`
const readCache = (key) => { try { return localStorage.getItem(key) } catch { return null } }
const writeCache = (key, value) => { try { localStorage.setItem(key, value) } catch { /* bỏ qua */ } }

// Tô màu cú pháp bằng chính tokenizer của Monaco, không cần thêm thư viện.
function HighlightedCode({ code, language, theme }) {
  const [html, setHtml] = useState(null)

  useEffect(() => {
    let active = true
    loader.init()
      .then((monaco) => monaco.editor.colorize(code, language, { tabSize: 4 }))
      .then((result) => { if (active) setHtml(result) })
      .catch(() => {})
    return () => { active = false }
  }, [code, language])

  return (
    <pre className={`ai-code ai-code-${theme === "light" ? "light" : "dark"}`}>
      {html ? <code dangerouslySetInnerHTML={{ __html: html }} /> : <code>{code}</code>}
    </pre>
  )
}

export default function AIReviewPanel({ roomCode, userId, question, language, code, outcome, theme }) {
  const config = useMemo(getAIConfig, [])
  const key = cacheKey(roomCode, userId)
  const [state, setState] = useState(() => {
    const cached = readCache(key)
    return cached ? { status: "ready", text: cached } : { status: "loading", text: "" }
  })
  const startedRef = useRef(false)
  const mountedRef = useRef(false)

  const run = async () => {
    if (!code?.trim()) { setState({ status: "error", text: "Bạn chưa viết code nào để phân tích." }); return }
    if (!isAIConfigured(config)) { setState({ status: "error", text: "Chưa có API key. Thêm VITE_AI_API_KEY vào frontend/.env.local rồi chạy lại npm run dev." }); return }

    setState({ status: "loading", text: "" })
    try {
      const text = await reviewMatchMarkdown(config, { question, language: LANGUAGE_NAMES[language] || language, code, outcome })
      writeCache(key, text)
      if (mountedRef.current) setState({ status: "ready", text })
    } catch (err) {
      if (mountedRef.current) setState({ status: "error", text: err.message })
    }
  }

  useEffect(() => {
    mountedRef.current = true
    if (!startedRef.current && state.status === "loading") {
      startedRef.current = true
      run()
    }
    return () => { mountedRef.current = false }
    // Chỉ chạy một lần khi mở tab.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const components = useMemo(() => ({
    pre: ({ children }) => <>{children}</>,
    table: ({ children }) => <div className="ai-table-wrap"><table>{children}</table></div>,
    code: ({ className, children }) => {
      const match = /language-(\w+)/.exec(className || "")
      const text = String(children).replace(/\n$/, "")
      return match ? <HighlightedCode code={text} language={match[1]} theme={theme} /> : <code className="ai-inline-code">{children}</code>
    },
  }), [theme])

  if (state.status === "loading") {
    return (
      <div className="ai-loading" role="status" aria-live="polite">
        <span className="ai-loading-text"><Loader2 size={15} className="console-spin" /> Trọng tài AI đang phân tích thuật toán của bạn...</span>
        <div className="ai-skeleton short" /><div className="ai-skeleton" /><div className="ai-skeleton block" /><div className="ai-skeleton" /><div className="ai-skeleton short" />
      </div>
    )
  }

  if (state.status === "error") {
    return (
      <div className="ai-review-error" role="alert">
        {state.text}
        <div style={{ marginTop: 10 }}>
          <button type="button" className="button button-small" onClick={run}><RefreshCw size={13} /> Thử lại</button>
        </div>
      </div>
    )
  }

  return (
    <div className="ai-review">
      <div className="ai-review-head" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 14, color: "#717a83", font: "10px var(--mono)", letterSpacing: 1.2 }}>
        <Bot size={13} /> BÁO CÁO CỦA TRỌNG TÀI AI · {config.label.toUpperCase()}
      </div>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{state.text}</ReactMarkdown>
    </div>
  )
}