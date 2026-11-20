import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  Ban,
  Check,
  Copy,
  Play,
  RotateCcw,
  Send,
  X,
  Swords,
  Trophy,
  Users,
} from "lucide-react"
import Editor from "@monaco-editor/react"
import api, { getToken, getApiErrorMessage } from "../api/axios"
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
// AC 4.2: chỉ báo "đối thủ đang gõ" tự biến mất sau 2 giây nếu không có gói mới.
const OPPONENT_TYPING_TTL_MS = 2000
// Khi đang gõ liên tục, gửi lại gói "đang gõ" mỗi giây để phía nhận không tự tắt chỉ báo.
const TYPING_HEARTBEAT_MS = 1000
// AC 3.2: chống spam, khóa nút Nộp bài tối thiểu 5 giây sau mỗi lần bấm.
const SUBMIT_COOLDOWN_MS = 5000
// Số lần tự nối lại WebSocket tối đa khi mất kết nối giữa chừng.
const MAX_RECONNECT_ATTEMPTS = 8
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

// Pháo giấy cho người thắng: vị trí, độ trễ, màu và độ dài rơi được tính cố định từ chỉ số
// (không dùng Math.random trong render để hiệu ứng không đổi mỗi lần component render lại).
const CONFETTI_COUNT = 42
const confettiPieces = Array.from({ length: CONFETTI_COUNT }, (_, index) => ({
  id: index,
  left: (index * 37) % 100,
  delay: ((index * 53) % 18) / 10,
  duration: 3.2 + ((index * 29) % 22) / 10,
  drift: ((index * 17) % 9) - 4,
  hue: index % 5,
}))

function Confetti() {
  return (
    <div className="confetti" aria-hidden="true">
      {confettiPieces.map((piece) => (
        <i
          key={piece.id}
          className={`confetti-piece confetti-${piece.hue}`}
          style={{
            left: `${piece.left}%`,
            animationDelay: `${piece.delay}s`,
            animationDuration: `${piece.duration}s`,
            "--drift": `${piece.drift * 18}px`,
          }}
        />
      ))}
    </div>
  )
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

  const myDelta = result.elo_change?.[userId]

  return (
    <div className={`arena-panel match-result${won ? " match-result-won" : ""}`}>
      {won && <Confetti />}

      {won && <span className="victory-banner">CHIẾN THẮNG</span>}

      <div
        className={`feature-icon ${won ? "green" : result.is_draw ? "blue" : "purple"}`}
      >
        {won || result.is_draw ? <Trophy /> : <Swords />}
      </div>

      <h1>{title}</h1>

      {won && typeof myDelta === "number" && myDelta > 0 && (
        <p className="victory-elo">+{myDelta} điểm xếp hạng</p>
      )}

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
  const navigate = useNavigate()
  const { user, loading } = useAuth()

  const socketRef = useRef(null)
  const editorRef = useRef(null)

  const [room, setRoom] = useState(null)
  const [error, setError] = useState("")
  const [connection, setConnection] = useState("connecting")
  const [countdown, setCountdown] = useState(null)
  const [copied, setCopied] = useState(false)

  const [language, setLanguage] = useState(() => {
    try {
      const saved = localStorage.getItem("codeduel_language")
      return saved && languageNames[saved] ? saved : "cpp"
    } catch {
      return "cpp"
    }
  })
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
  // Mốc (ms) nút Nộp bài được bấm lại; cooldownLeft đếm ngược cho nhãn nút.
  const [submitLockedUntil, setSubmitLockedUntil] = useState(0)
  const [cooldownLeft, setCooldownLeft] = useState(0)

  const eventIdRef = useRef(0)
  const roomStatusRef = useRef(null)
  const typingTimerRef = useRef(null)
  const typingActiveRef = useRef(false)
  const lastTypingSentRef = useRef(0)
  const opponentTypingTimerRef = useRef(null)

  const code = codes[language] ?? ""

  // Chỉ phụ thuộc vào id: AuthContext thay object `user` mỗi khi /users/me trả về hay đổi avatar,
  // nếu phụ thuộc cả object thì socket bị đóng rồi mở lại (và có thể làm backend hủy phòng đang chờ).
  const userId = user?.id
  // true khi chính người chơi chủ động đóng socket (Hủy đấu) -> không tự kết nối lại.
  const manualCloseRef = useRef(false)

  useEffect(() => {
    if (!submitLockedUntil) return undefined

    const tick = () => {
      const left = Math.max(0, Math.ceil((submitLockedUntil - Date.now()) / 1000))
      setCooldownLeft(left)
      return left
    }

    if (tick() === 0) return undefined

    const timer = window.setInterval(() => {
      if (tick() === 0) window.clearInterval(timer)
    }, 250)

    return () => window.clearInterval(timer)
  }, [submitLockedUntil])

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
    if (loading || !userId) return undefined

    let active = true
    let reconnectTimer = null
    let attempts = 0
    manualCloseRef.current = false

    const connect = async () => {
      try {
        const { data } = await api.get(`/api/v1/rooms/${roomCode}`)

        if (!active) return

        const roomData = data.data
        setRoom(roomData)

        const token = getToken()

        const configuredBase = api.defaults.baseURL || "/"

        const apiOrigin = /^https?:\/\//i.test(configuredBase)
          ? new URL(configuredBase).origin
          : window.location.origin

        const socketOrigin = apiOrigin.replace(/^http/i, "ws")

        const openSocket = () => {
          const socket = new WebSocket(
            `${socketOrigin}/api/v1/rooms/ws/arena/${encodeURIComponent(
              roomCode,
            )}?token=${encodeURIComponent(token || "")}`,
          )

          socketRef.current = socket

          socket.onopen = () => {
            if (active) {
              attempts = 0
              setConnection("connected")
            }
          }

          socket.onclose = (closeEvent) => {
            if (!active) return

            setConnection("disconnected")

            // Mất mạng / backend khởi động lại giữa chừng: tự nối lại để không mất trận.
            // Không nối lại khi: tự đóng chủ động, bị backend từ chối (4001/4003/4004) hoặc trận đã kết thúc.
            const refused = [4001, 4003, 4004].includes(closeEvent.code)
            const roomOver = ["FINISHED", "CANCELLED"].includes(roomStatusRef.current)

            if (!refused && !roomOver && !manualCloseRef.current && attempts < MAX_RECONNECT_ATTEMPTS) {
              attempts += 1
              setConnection("reconnecting")
              reconnectTimer = window.setTimeout(() => {
                if (active && !manualCloseRef.current) openSocket()
              }, Math.min(1000 * attempts, 5000))
            }

            // Mã đóng do backend đặt trong arena_websocket.
            if (closeEvent.code === 4003) {
              setError("Bạn không có quyền vào phòng này hoặc phiên đăng nhập đã hết hạn.")
            } else if (closeEvent.code === 4004) {
              setRoom((current) =>
                current ? { ...current, status: "CANCELLED" } : current,
              )
            } else if (closeEvent.code === 4001) {
              setError("Phòng này đang được mở ở một tab khác nên kết nối ở đây đã bị đóng.")
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
                message.data?.user_id !== userId
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

                if (inMatch && leftId !== userId) {
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

                  if (update.user_id !== userId) {
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
                  data.winner_id === userId
                    ? "Bạn đã vượt qua tất cả testcase và giành chiến thắng!"
                    : `${data.winner_username || "Đối thủ"} đã hoàn thành bài trước.`,
                  data.winner_id === userId ? "success" : "warn",
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
        }

        openSocket()
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
      window.clearTimeout(reconnectTimer)
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [roomCode, userId, loading])

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

    // Tải lại trang giữa trận thì khôi phục code đã gõ thay vì quay về starter_code.
    let draft = null

    try {
      draft = JSON.parse(localStorage.getItem(`codeduel_draft:${userId}:${roomCode}:${questionId}`) || "null")
    } catch {
      draft = null
    }

    setCodes({
      cpp: draft?.cpp ?? starter.cpp ?? "",
      python: draft?.python ?? starter.python ?? "",
      java: draft?.java ?? starter.java ?? "",
    })
  }, [room?.question, roomCode, userId])

  // Lưu nháp code trong lúc đang thi đấu; xóa khi trận kết thúc.
  useEffect(() => {
    const questionId = room?.question?.id

    if (!questionId || loadedQuestionRef.current !== questionId) return undefined

    const key = `codeduel_draft:${userId}:${roomCode}:${questionId}`

    try {
      if (room?.status === "FINISHED" || room?.status === "CANCELLED") {
        localStorage.removeItem(key)
        return undefined
      }
    } catch {
      return undefined
    }

    const timer = window.setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(codes))
      } catch {
        // Hết dung lượng hoặc bị chặn lưu trữ: bỏ qua, chỉ mất tính năng khôi phục nháp.
      }
    }, 500)

    return () => window.clearTimeout(timer)
  }, [codes, room?.question?.id, room?.status, roomCode, userId])

  const handleEditorMount = (editor) => {
    editorRef.current = editor
  }

  // Báo cho đối thủ biết mình đang gõ: gửi "đang gõ" ở phím đầu tiên, "ngừng gõ" sau khi im một lúc.
  const notifyTyping = () => {
    if (roomStatusRef.current !== "PLAYING") return

    const now = Date.now()

    if (!typingActiveRef.current || now - lastTypingSentRef.current >= TYPING_HEARTBEAT_MS) {
      typingActiveRef.current = true
      lastTypingSentRef.current = now
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
    if (kind === "submit" && Date.now() < submitLockedUntil) return

    if (!code.trim()) {
      setJudge({
        busy: null,
        output: { kind, error: "Hãy viết code trước khi chạy thử hoặc nộp bài." },
      })
      return
    }

    setJudge({ busy: kind, output: null })
    if (kind === "submit") setSubmitLockedUntil(Date.now() + SUBMIT_COOLDOWN_MS)

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

    try {
      localStorage.setItem("codeduel_language", newLanguage)
    } catch {
      // Trình duyệt chặn lưu trữ thì chỉ không nhớ lựa chọn cho lần sau.
    }
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

  // Hủy đấu khi phòng còn đang chờ. Backend không có API hủy phòng riêng: khi người chơi ngắt
  // WebSocket lúc phòng ở trạng thái WAITING, backend tự đặt phòng CANCELLED (và báo cho đối thủ).
  // Việc đó xảy ra trễ một nhịp, nên phải đợi backend xác nhận rồi mới về Arena; nếu không,
  // bấm "Tạo phòng" ngay sau đó sẽ bị báo "đang ở trong một phòng đang hoạt động" (409).
  const [cancelling, setCancelling] = useState(false)

  const waitRoomLeftWaiting = async (tries = 6, delayMs = 350) => {
    for (let i = 0; i < tries; i += 1) {
      try {
        const { data } = await api.get(`/api/v1/rooms/${roomCode}`)

        if (data.data?.status !== "WAITING") return true
      } catch (err) {
        // 404: không còn thấy phòng với mình nữa, coi như đã rời xong.
        if (err.response?.status === 404) return true
      }

      await new Promise((resolve) => window.setTimeout(resolve, delayMs))
    }

    return false
  }

  // Dự phòng: nếu socket cũ chưa từng được backend ghi nhận (đóng quá sớm) thì phòng vẫn WAITING.
  // Mở một kết nối mới rồi đóng ngay để backend chạy lại luồng "người chơi thoát -> hủy phòng".
  const reconnectAndLeave = () =>
    new Promise((resolve) => {
      const configuredBase = api.defaults.baseURL || "/"
      const apiOrigin = /^https?:\/\//i.test(configuredBase)
        ? new URL(configuredBase).origin
        : window.location.origin
      const token = getToken() || ""
      const socket = new WebSocket(
        `${apiOrigin.replace(/^http/i, "ws")}/api/v1/rooms/ws/arena/${encodeURIComponent(roomCode)}?token=${encodeURIComponent(token)}`,
      )
      const finish = () => resolve()

      socket.onopen = () => window.setTimeout(() => socket.close(), 300)
      socket.onclose = finish
      socket.onerror = finish
      window.setTimeout(finish, 3000)
    })

  const cancelWaitingRoom = async () => {
    if (cancelling) return

    const hasOpponent = (room?.players || []).length >= 2

    if (
      hasOpponent &&
      !window.confirm("Hủy đấu sẽ đóng phòng và đối thủ cũng bị đưa ra khỏi phòng. Bạn chắc chứ?")
    ) {
      return
    }

    setCancelling(true)
    manualCloseRef.current = true
    setError("")
    window.clearTimeout(typingTimerRef.current)
    window.clearTimeout(opponentTypingTimerRef.current)
    socketRef.current?.close()
    socketRef.current = null

    let done = await waitRoomLeftWaiting()

    if (!done) {
      await reconnectAndLeave()
      done = await waitRoomLeftWaiting()
    }

    if (!done) {
      setError("Chưa hủy được phòng. Hãy bấm Hủy đấu lần nữa.")
      setCancelling(false)
      manualCloseRef.current = false
      return
    }

    navigate("/arena")
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

  // Phòng đã FINISHED mà chưa có kết quả từ socket (vào lại / tải lại trang): /rooms/{code} không trả
  // elo_change, nên lấy phần của chính mình từ lịch sử 10 trận gần nhất (/users/{id}/history).
  const [restoredElo, setRestoredElo] = useState({})
  const needsEloRestore = room?.status === "FINISHED" && !result
  const restoreRoomId = room?.room_id

  useEffect(() => {
    if (!needsEloRestore || !user?.id || !restoreRoomId) return undefined

    let active = true

    api
      .get(`/api/v1/users/${user.id}/history`)
      .then(({ data }) => {
        if (!active) return

        const match = (data.data || []).find((item) => item.room_id === restoreRoomId)

        if (match && typeof match.elo_change === "number") {
          setRestoredElo({ [user.id]: match.elo_change })
        }
      })
      .catch(() => {})

    return () => {
      active = false
    }
  }, [needsEloRestore, user?.id, restoreRoomId])

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
      ? { is_draw: !room.winner_id, winner_id: room.winner_id, elo_change: restoredElo }
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
            : connection === "reconnecting"
              ? "Mất kết nối, đang tự nối lại…"
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

              <div className="room-setup">
                <span className="panel-label">NGÔN NGỮ CỦA BẠN</span>

                <div className="lang-options" role="radiogroup" aria-label="Chọn ngôn ngữ lập trình">
                  {Object.entries(languageNames).map(([key, name]) => (
                    <button
                      key={key}
                      type="button"
                      role="radio"
                      aria-checked={language === key}
                      className={language === key ? "active" : ""}
                      onClick={() => changeLanguage(key)}
                    >
                      {name}
                    </button>
                  ))}
                </div>

                <small>Mỗi người tự chọn ngôn ngữ của mình. Vào trận vẫn đổi được.</small>
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

                <button
                  className="room-cancel-button"
                  type="button"
                  onClick={cancelWaitingRoom}
                  disabled={cancelling}
                >
                  <X size={15} />
                  {cancelling ? "Đang hủy..." : "Hủy đấu"}
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
                        disabled={Boolean(judge.busy) || cooldownLeft > 0}
                      >
                        <Send size={14} />
                        {judge.busy === "submit"
                          ? "Đang chấm..."
                          : cooldownLeft > 0
                            ? `Nộp lại sau ${cooldownLeft}s`
                            : "Nộp bài"}
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