import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  Ban,
  Check,
  Copy,
  Play,
  RotateCcw,
  Send,
  Swords,
  Trophy,
  Users,
} from "lucide-react"
import Editor from "@monaco-editor/react"
import api, { getApiErrorMessage } from "../api/axios"
import { useAuth } from "../context/AuthContext"
import ProblemPanel from "../components/arena/ProblemPanel"
import ConsolePanel from "../components/arena/ConsolePanel"
import ArenaSidebar from "../components/arena/ArenaSidebar"
import "./Room.css"

// Giữ cố định tham chiếu: nếu tạo object mới mỗi lần render, Monaco sẽ updateOptions sau mỗi phím gõ.
const EDITOR_OPTIONS = {
  fontSize: 14,
  minimap: { enabled: false },
  automaticLayout: true,
  tabSize: 4,
  insertSpaces: true,
  wordWrap: "on",
  scrollBeyondLastLine: false,
  suggestOnTriggerCharacters: true,
  quickSuggestions: true,
  formatOnPaste: true,
  formatOnType: false,
  padding: { top: 12 },
}

// Khớp MATCH_DURATION_SECONDS (15 phút) trong backend/app/services/match_timer.py.
// Chỉ dùng để tự đếm ngược khi chưa nhận được sự kiện TIME_SYNC từ server.
const MATCH_DURATION_MS = 15 * 60 * 1000
// Chạy / chấm code (compile + chạy testcase) lâu hơn các request thường (mặc định 10s).
const JUDGE_TIMEOUT_MS = 60000
const TYPING_IDLE_MS = 1500
const OPPONENT_TYPING_TTL_MS = 5000
const MAX_EVENTS = 40

// Server trả ISO có múi giờ; nếu thiếu thì coi là UTC để không lệch giờ theo máy người dùng.
const parseServerTime = (value) => {
  if (!value) return null
  const text = /(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
  const time = Date.parse(text)
  return Number.isNaN(time) ? null : time
}

const languageMap = {
  cpp: "cpp",
  python: "python",
  java: "java",
}

const languageNames = {
  cpp: "C++",
  python: "Python",
  java: "Java",
}

function MatchResult({ result, players, userId }) {
  const won = Boolean(userId) && result.winner_id === userId
  const winner = players.find((player) => player.user_id === result.winner_id)
  const winnerName = result.winner_username || winner?.username || "Đối thủ"

  const title = result.is_draw
    ? "Trận đấu hòa"
    : won
      ? "Bạn đã chiến thắng!"
      : "Bạn đã thua trận này"

  const subtitle = result.is_draw
    ? "Hết giờ mà chưa ai vượt qua tất cả testcase."
    : won
      ? "Bạn là người đầu tiên vượt qua tất cả testcase."
      : `${winnerName} đã vượt qua tất cả testcase trước bạn.`

  const seconds = Number(result.completion_time)

  return (
    <div className="arena-panel match-result">
      <div
        className={`feature-icon ${won ? "green" : result.is_draw ? "blue" : "purple"}`}
      >
        {won || result.is_draw ? <Trophy /> : <Swords />}
      </div>

      <h1>{title}</h1>

      <p>{subtitle}</p>

      <div className="result-players">
        {players.map((player) => {
          const delta = result.elo_change?.[player.user_id]

          return (
            <div className="result-player" key={player.user_id}>
              <span className="rank-avatar">
                {player.username?.slice(0, 1).toUpperCase()}
              </span>

              <span>
                <b>
                  {player.username}
                  {player.user_id === userId ? " (Bạn)" : ""}
                </b>

                <small>
                  {player.user_id === result.winner_id
                    ? "Người thắng"
                    : result.is_draw
                      ? "Hòa"
                      : "Người thua"}
                </small>
              </span>

              {typeof delta === "number" && (
                <em className={delta > 0 ? "up" : delta < 0 ? "down" : ""}>
                  {delta > 0 ? `+${delta}` : delta} điểm
                </em>
              )}
            </div>
          )
        })}
      </div>

      {Number.isFinite(seconds) && seconds > 0 && !result.is_draw && (
        <p className="result-time">
          Thời gian hoàn thành: {Math.floor(seconds / 60)}p{" "}
          {Math.round(seconds % 60)}s
        </p>
      )}

      <Link className="button" to="/arena">
        Về đấu trường <ArrowRight size={16} />
      </Link>
    </div>
  )
}

export default function Room() {
  const { roomCode } = useParams()
  const { user, loading } = useAuth()

  const socketRef = useRef(null)
  const editorRef = useRef(null)

  const [room, setRoom] = useState(null)
  const [error, setError] = useState("")
  const [connection, setConnection] = useState("connecting")
  const [countdown, setCountdown] = useState(null)
  const [copied, setCopied] = useState(false)

  const [language, setLanguage] = useState("cpp")
  const [theme, setTheme] = useState("vs-dark")
  // Mỗi ngôn ngữ giữ code riêng để đổi qua lại không mất bài đang gõ.
  const [codes, setCodes] = useState({ cpp: "", python: "", java: "" })
  const loadedQuestionRef = useRef(null)
  const [showResetConfirm, setShowResetConfirm] = useState(false)

  // Mốc kết thúc trận (ms) cập nhật theo TIME_SYNC của server.
  const [syncedDeadline, setSyncedDeadline] = useState(null)
  const [opponentTyping, setOpponentTyping] = useState(false)
  const [events, setEvents] = useState([])
  const [progress, setProgress] = useState({})
  // Kết quả trận nhận qua GAME_OVER / MATCH_DRAW.
  const [result, setResult] = useState(null)
  // busy: "run" | "submit" | null; output: kết quả hiển thị ở Console.
  const [judge, setJudge] = useState({ busy: null, output: null })

  const eventIdRef = useRef(0)
  const roomStatusRef = useRef(null)
  const typingTimerRef = useRef(null)
  const typingActiveRef = useRef(false)
  const opponentTypingTimerRef = useRef(null)

  const code = codes[language] ?? ""

  const pushEvent = (text, tone = "info") => {
    eventIdRef.current += 1
    const entry = { id: eventIdRef.current, at: Date.now(), text, tone }
    setEvents((current) => [entry, ...current].slice(0, MAX_EVENTS))
  }

  const sendSocket = (payload) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(payload))
    }
  }

  useEffect(() => {
    if (loading || !user) return undefined

    let active = true

    const connect = async () => {
      try {
        const { data } = await api.get(`/api/v1/rooms/${roomCode}`)

        if (!active) return

        const roomData = data.data
        setRoom(roomData)

        const token = localStorage.getItem("token")

        const configuredBase = api.defaults.baseURL || "/"

        const apiOrigin = /^https?:\/\//i.test(configuredBase)
          ? new URL(configuredBase).origin
          : window.location.origin

        const socketOrigin = apiOrigin.replace(/^http/i, "ws")

        const socket = new WebSocket(
          `${socketOrigin}/api/v1/rooms/ws/arena/${encodeURIComponent(
            roomCode,
          )}?token=${encodeURIComponent(token || "")}`,
        )

        socketRef.current = socket

        socket.onopen = () => {
          if (active) {
            setConnection("connected")
          }
        }

        socket.onclose = () => {
          if (active) {
            setConnection("disconnected")
          }
        }

        socket.onerror = () => {
          if (active) {
            setConnection("disconnected")
          }
        }

        socket.onmessage = (event) => {
          if (!active) return

          try {
            const message = JSON.parse(event.data)

            if (message.event === "ROOM_STATE") {
              setRoom(message.data)
            }

            if (
              message.event === "JOIN_ROOM" &&
              roomStatusRef.current === "PLAYING" &&
              message.data?.user_id !== user.id
            ) {
              pushEvent(
                `${message.data?.username || "Đối thủ"} đã vào lại phòng.`,
              )
            }

            if (
              ["JOIN_ROOM", "PLAYER_READY"].includes(message.event) &&
              message.data?.players
            ) {
              setRoom((current) =>
                current
                  ? {
                      ...current,
                      players: message.data.players,
                    }
                  : current,
              )
            }

            if (message.event === "PLAYER_LEFT") {
              const leftId = message.data.user_id
              const inMatch = roomStatusRef.current === "PLAYING"

              setRoom((current) =>
                current
                  ? {
                      ...current,
                      players: inMatch
                        ? (current.players || []).map((player) =>
                            player.user_id === leftId
                              ? { ...player, left: true }
                              : player,
                          )
                        : (current.players || []).filter(
                            (player) => player.user_id !== leftId,
                          ),
                    }
                  : current,
              )

              if (inMatch && leftId !== user.id) {
                setOpponentTyping(false)
                pushEvent(
                  `${message.data.username || "Đối thủ"} đã rời phòng.`,
                  "warn",
                )
              }
            }

            if (message.event === "ROOM_CANCELLED") {
              setCountdown(null)
              setRoom((current) =>
                current ? { ...current, status: "CANCELLED" } : current,
              )
            }

            if (message.event === "TIME_SYNC") {
              const left = Number(message.data?.remaining_seconds)

              if (Number.isFinite(left)) {
                setSyncedDeadline(Date.now() + left * 1000)
              }
            }

            if (message.event === "OPPONENT_TYPING") {
              const typing = Boolean(message.data?.is_typing)

              setOpponentTyping(typing)
              window.clearTimeout(opponentTypingTimerRef.current)

              // Phòng khi gói "ngừng gõ" bị mất, tự tắt chỉ báo sau một lúc.
              if (typing) {
                opponentTypingTimerRef.current = window.setTimeout(
                  () => setOpponentTyping(false),
                  OPPONENT_TYPING_TTL_MS,
                )
              }
            }

            if (message.event === "PROGRESS_UPDATE") {
              // Backend đặt các trường này ở cấp ngoài cùng, không nằm trong "data".
              const update = message.data ?? message

              if (update.user_id) {
                setProgress((current) => ({
                  ...current,
                  [update.user_id]: {
                    passed: update.passed,
                    total: update.total,
                    percent: update.progress_percent,
                  },
                }))

                if (update.user_id !== user.id) {
                  pushEvent(
                    `Đối thủ vượt ${update.passed}/${update.total} testcase.`,
                  )
                }
              }
            }

            if (message.event === "GAME_OVER") {
              const data = message.data || {}

              setResult({
                is_draw: false,
                winner_id: data.winner_id,
                winner_username: data.winner_username,
                elo_change: data.elo_change || {},
                completion_time: data.completion_time,
              })
              setOpponentTyping(false)
              setRoom((current) =>
                current
                  ? {
                      ...current,
                      status: "FINISHED",
                      winner_id: data.winner_id,
                      finished_at: data.finished_at,
                    }
                  : current,
              )
              pushEvent(
                data.winner_id === user.id
                  ? "Bạn đã vượt qua tất cả testcase và giành chiến thắng!"
                  : `${data.winner_username || "Đối thủ"} đã hoàn thành bài trước.`,
                data.winner_id === user.id ? "success" : "warn",
              )
            }

            if (message.event === "MATCH_DRAW") {
              const data = message.data || {}
              const eloChange = {}

              for (const player of data.players || []) {
                eloChange[player.user_id] = player.elo_change
              }

              setResult({
                is_draw: true,
                winner_id: null,
                elo_change: eloChange,
              })
              setOpponentTyping(false)
              setRoom((current) =>
                current
                  ? {
                      ...current,
                      status: "FINISHED",
                      winner_id: null,
                      finished_at: data.finished_at,
                    }
                  : current,
              )
              pushEvent(data.message || "Hết giờ, trận đấu hòa.", "warn")
            }

            if (message.event === "COUNTDOWN") {
              setCountdown(message.data.value)
            }

            if (
              ["COUNTDOWN_START", "COUNTDOWN_ABORTED"].includes(
                message.event,
              )
            ) {
              setCountdown(null)

              if (message.event === "COUNTDOWN_START") {
                setSyncedDeadline(null)
                pushEvent("Trận đấu bắt đầu. Chúc bạn may mắn!", "success")
                setRoom((current) =>
                  current
                    ? {
                        ...current,
                        status: "PLAYING",
                        question: message.data.question,
                      }
                    : current,
                )
              }
            }

            if (message.event === "ERROR") {
              setError(
                message.data?.message ||
                  "Phòng đã gặp lỗi.",
              )
            }
          } catch {
            setError(
              "Không đọc được dữ liệu phòng từ máy chủ.",
            )
          }
        }
      } catch (err) {
        if (active) {
          setError(
            err.response?.data?.message ||
              "Không thể tải phòng. Hãy kiểm tra mã phòng và đăng nhập lại.",
          )
        }
      }
    }

    connect()

    return () => {
      active = false
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [roomCode, user, loading])

  useEffect(() => {
    roomStatusRef.current = room?.status ?? null
  }, [room?.status])

  // Dọn timer chỉ báo gõ khi rời trang.
  useEffect(
    () => () => {
      window.clearTimeout(typingTimerRef.current)
      window.clearTimeout(opponentTypingTimerRef.current)
    },
    [],
  )

  // Chỉ nạp starter_code khi đổi sang câu hỏi mới (lần đầu vào trận / bắt đầu trận),
  // không nạp lại mỗi khi room cập nhật qua socket để tránh xóa code đang gõ.
  useEffect(() => {
    const starter = room?.question?.starter_code
    const questionId = room?.question?.id

    if (!starter || !questionId) return
    if (loadedQuestionRef.current === questionId) return

    loadedQuestionRef.current = questionId
    setCodes({
      cpp: starter.cpp ?? "",
      python: starter.python ?? "",
      java: starter.java ?? "",
    })
  }, [room?.question])

  const handleEditorMount = (editor) => {
    editorRef.current = editor
  }

  // Báo cho đối thủ biết mình đang gõ: gửi "đang gõ" ở phím đầu tiên, "ngừng gõ" sau khi im một lúc.
  const notifyTyping = () => {
    if (roomStatusRef.current !== "PLAYING") return

    if (!typingActiveRef.current) {
      typingActiveRef.current = true
      sendSocket({ action: "player_typing", is_typing: true })
    }

    window.clearTimeout(typingTimerRef.current)
    typingTimerRef.current = window.setTimeout(() => {
      typingActiveRef.current = false
      sendSocket({ action: "player_typing", is_typing: false })
    }, TYPING_IDLE_MS)
  }

  const handleEditorChange = (value) => {
    setCodes((current) => ({ ...current, [language]: value || "" }))
    notifyTyping()
  }

  // Chạy thử (public testcase, không ghi DB) hoặc nộp bài chính thức (toàn bộ testcase).
  const judgeCode = async (kind) => {
    if (judge.busy || !room?.question) return

    if (!code.trim()) {
      setJudge({
        busy: null,
        output: { kind, error: "Hãy viết code trước khi chạy thử hoặc nộp bài." },
      })
      return
    }

    setJudge({ busy: kind, output: null })

    const body = {
      question_id: room.question.id,
      language,
      code_content: code,
    }

    try {
      const { data } =
        kind === "run"
          ? await api.post("/api/v1/execute/run", body, {
              timeout: JUDGE_TIMEOUT_MS,
            })
          : await api.post(
              "/api/v1/execute/submit",
              { ...body, room_id: room.room_id },
              { timeout: JUDGE_TIMEOUT_MS },
            )

      setJudge({ busy: null, output: { kind, language, data: data.data } })

      if (kind === "submit") {
        const submitted = data.data

        pushEvent(
          `Bạn đã nộp bài: ${submitted.passed_test_cases}/${submitted.total_test_cases} testcase.`,
          submitted.status === "PASS" ? "success" : "info",
        )
      }
    } catch (err) {
      setJudge({
        busy: null,
        output: {
          kind,
          error: getApiErrorMessage(
            err,
            kind === "run"
              ? "Không thể chạy thử code. Vui lòng thử lại."
              : "Không thể nộp bài. Vui lòng thử lại.",
          ),
        },
      })
    }
  }

  const changeLanguage = (newLanguage) => {
    setLanguage(newLanguage)
  }

  const resetCode = () => {
    const starter =
      room?.question?.starter_code?.[language]

    if (starter !== undefined) {
      const editor = editorRef.current
      const model = editor?.getModel()

      if (editor && model) {
        // executeEdits giữ lịch sử Undo, người chơi vẫn Ctrl+Z để lấy lại code cũ.
        editor.pushUndoStop()
        editor.executeEdits("reset-code", [
          { range: model.getFullModelRange(), text: starter },
        ])
        editor.pushUndoStop()
      } else {
        setCodes((current) => ({ ...current, [language]: starter }))
      }

      setShowResetConfirm(false)
    }
  }

  const ready = () => {
    if (
      socketRef.current?.readyState ===
      WebSocket.OPEN
    ) {
      socketRef.current.send(
        JSON.stringify({
          action: "player_ready",
        }),
      )
    } else {
      setError(
        "Kết nối phòng chưa sẵn sàng. Vui lòng thử lại.",
      )
    }
  }

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(roomCode)

      setCopied(true)

      window.setTimeout(() => {
        setCopied(false)
      }, 1600)
    } catch {
      setError(
        "Trình duyệt không cho phép sao chép mã phòng.",
      )
    }
  }

  const currentPlayer = room?.players?.find(
    (player) => player.user_id === user?.id,
  )

  const question = room?.question
  const isPlaying = room?.status === "PLAYING" && Boolean(question)
  const opponent = room?.players?.find((player) => player.user_id !== user?.id)

  // Ưu tiên mốc từ TIME_SYNC; chưa có thì tính từ started_at + thời lượng trận.
  const matchDeadline = useMemo(() => {
    if (!isPlaying) return null
    if (syncedDeadline) return syncedDeadline

    const startedAt = parseServerTime(room?.started_at)

    return startedAt ? startedAt + MATCH_DURATION_MS : null
  }, [isPlaying, syncedDeadline, room?.started_at])

  // Vào lại phòng đã kết thúc thì không còn sự kiện GAME_OVER, nên dựng kết quả từ trạng thái phòng.
  const finalResult =
    result ??
    (room?.status === "FINISHED"
      ? { is_draw: !room.winner_id, winner_id: room.winner_id, elo_change: {} }
      : null)

  if (!user && !loading) {
    return (
      <section className="arena-page">
        <div className="arena-panel">
          <h1>Hãy đăng nhập để vào phòng.</h1>

          <Link
            className="button"
            to="/login"
          >
            Đăng nhập
          </Link>
        </div>
      </section>
    )
  }

  return (
    <section
      className={`arena-page room-arena-page${isPlaying ? " room-arena-playing" : ""}`}
    >
      {!isPlaying && (
      <div className="arena-heading">
        <Link
          className="watch-link"
          to="/arena"
        >
          <ArrowLeft size={16} />
          Quay lại đấu trường
        </Link>

        <div className="eyebrow">
          <span className="eyebrow-line" />
          CODEDUEL ROOM
        </div>

        <h1>
          Phòng <span>{roomCode}</span>
        </h1>

        <p>
          {connection === "connected"
            ? "Đã kết nối trực tiếp với phòng."
            : "Đang kết nối với phòng…"}
        </p>
      </div>
      )}

      {error && (
        <div
          className="arena-message"
          role="alert"
        >
          {error}
        </div>
      )}

      {room && (
        <>
          {room.status === "WAITING" && (
            <div className="arena-panel room-panel">
              <div className="leader-card-head">
                <span>
                  <Users size={17} />
                  NGƯỜI CHƠI
                </span>

                <button
                  className="watch-link"
                  type="button"
                  onClick={copyCode}
                >
                  {copied ? (
                    <Check size={15} />
                  ) : (
                    <Copy size={15} />
                  )}

                  {copied
                    ? "Đã sao chép"
                    : "Sao chép mã"}
                </button>
              </div>

              <div className="room-players">
                {(room.players || []).map(
                  (player) => (
                    <div
                      className="room-player"
                      key={player.user_id}
                    >
                      <span className="rank-avatar">
                        {player.username
                          ?.slice(0, 1)
                          .toUpperCase()}
                      </span>

                      <span>
                        <b>
                          {player.username}
                          {player.user_id ===
                          user?.id
                            ? " (Bạn)"
                            : ""}
                        </b>

                        <small>
                          {player.is_ready
                            ? "Đã sẵn sàng"
                            : "Đang chờ"}{" "}
                          · {player.rating} điểm
                        </small>
                      </span>

                      {player.is_ready && (
                        <Check size={17} />
                      )}
                    </div>
                  ),
                )}

                {(room.players || []).length <
                  2 && (
                  <div className="room-waiting">
                    <Users size={18} />
                    Đang chờ đối thủ tham gia…
                  </div>
                )}
              </div>

              <div className="room-controls">
                <p>
                  {countdown
                    ? `Trận đấu bắt đầu sau ${countdown}…`
                    : "Khi cả hai người chơi sẵn sàng, trận đấu sẽ bắt đầu."}
                </p>

                <button
                  className="button"
                  type="button"
                  onClick={ready}
                  disabled={
                    Boolean(
                      currentPlayer?.is_ready,
                    ) ||
                    connection !== "connected"
                  }
                >
                  {currentPlayer?.is_ready
                    ? "Bạn đã sẵn sàng"
                    : "Sẵn sàng"}

                  <Swords size={16} />
                </button>
              </div>
            </div>
          )}

          {room.status === "FINISHED" && finalResult && (
            <MatchResult
              result={finalResult}
              players={room.players || []}
              userId={user?.id}
            />
          )}

          {room.status === "CANCELLED" && (
            <div className="arena-panel match-result">
              <div className="feature-icon purple">
                <Ban />
              </div>

              <h1>Phòng đã bị hủy</h1>

              <p>
                Có người chơi đã rời phòng trước khi trận bắt đầu nên phòng
                không còn hoạt động.
              </p>

              <Link className="button" to="/arena">
                Về đấu trường <ArrowRight size={16} />
              </Link>
            </div>
          )}

          {isPlaying && (
            <div className="arena-grid">
              <aside className="arena-col arena-col-left">
                <ProblemPanel question={question} />
              </aside>

              <div className="arena-col arena-col-center">
                <div className="code-editor-panel">
                  <div className="code-editor-header">
                    <div className="code-editor-title">
                      <span className="feature-index">
                        {question.difficulty ||
                          "THỬ THÁCH"}
                      </span>

                      <span className="code-editor-question">
                        {question.title}
                      </span>
                    </div>

                    <div className="code-editor-settings">
                      <select
                        value={language}
                        onChange={(event) =>
                          changeLanguage(
                            event.target.value,
                          )
                        }
                      >
                        <option value="cpp">
                          C++
                        </option>

                        <option value="python">
                          Python
                        </option>

                        <option value="java">
                          Java
                        </option>
                      </select>

                      <select
                        value={theme}
                        onChange={(event) =>
                          setTheme(
                            event.target.value,
                          )
                        }
                      >
                        <option value="vs-dark">
                          Dark
                        </option>

                        <option value="light">
                          Light
                        </option>
                      </select>

                      <button
                        type="button"
                        className="editor-reset-button"
                        onClick={() =>
                          setShowResetConfirm(
                            true,
                          )
                        }
                      >
                        <RotateCcw size={14} />
                        Reset Code
                      </button>

                      <button
                        type="button"
                        className="editor-reset-button"
                        onClick={() => judgeCode("run")}
                        disabled={Boolean(judge.busy)}
                      >
                        <Play size={14} />
                        {judge.busy === "run" ? "Đang chạy..." : "Chạy thử"}
                      </button>

                      <button
                        type="button"
                        className="editor-submit-button"
                        onClick={() => judgeCode("submit")}
                        disabled={Boolean(judge.busy)}
                      >
                        <Send size={14} />
                        {judge.busy === "submit" ? "Đang chấm..." : "Nộp bài"}
                      </button>
                    </div>
                  </div>

                  <div className="editor-toolbar">
                    <span>
                      {languageNames[
                        language
                      ]}
                    </span>

                    <span>
                      Ctrl+/ comment
                    </span>

                    <span>
                      Tab = 4 spaces
                    </span>

                    <span>
                      Ctrl+F tìm kiếm
                    </span>
                  </div>

                  <div className="monaco-wrapper">
                    <Editor
                      height="100%"
                      path={`${question.id}-${language}`}
                      language={
                        languageMap[
                          language
                        ]
                      }
                      theme={theme}
                      value={code}
                      onChange={
                        handleEditorChange
                      }
                      onMount={
                        handleEditorMount
                      }
                      options={EDITOR_OPTIONS}
                    />
                  </div>

                  {showResetConfirm && (
                    <div className="reset-confirm-overlay">
                      <div className="reset-confirm">
                        <h3>
                          Reset Code?
                        </h3>

                        <p>
                          Toàn bộ code hiện tại
                          sẽ được thay bằng
                          starter code ban đầu.
                        </p>

                        <div className="reset-confirm-actions">
                          <button
                            type="button"
                            className="button-ghost"
                            onClick={() =>
                              setShowResetConfirm(
                                false,
                              )
                            }
                          >
                            Hủy
                          </button>

                          <button
                            type="button"
                            className="button"
                            onClick={
                              resetCode
                            }
                          >
                            Reset Code
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <ConsolePanel busy={judge.busy} output={judge.output} />
              </div>

              <aside className="arena-col arena-col-right">
                <ArenaSidebar
                  opponent={opponent}
                  opponentProgress={opponent ? progress[opponent.user_id] : null}
                  deadline={matchDeadline}
                  opponentTyping={opponentTyping}
                  connection={connection}
                  events={events}
                />
              </aside>
            </div>
          )}
        </>
      )}
    </section>
  )
}