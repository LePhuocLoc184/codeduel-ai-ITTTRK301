// AI cho phần luyện tập: ra đề, kiểm duyệt đề, chấm bài, nhận xét.
// Mọi dữ liệu AI trả về đều bị ép về ĐÚNG format mà backend đã định nghĩa:
//   - Câu hỏi        : backend/app/schemas/questions.py   (QuestionBase, AIQuestionGenerateRequest)
//   - Chạy thử / nộp : backend/app/schemas/submissions.py (CodeRunResponse, SubmissionResponse, SubmissionStatus)
//   - Luật chấm      : backend/app/services/judge.py      (so output sau khi bỏ khoảng trắng 2 đầu, dừng ở testcase sai đầu tiên)
//   - Nhận xét       : backend/app/schemas/rooms.py       (AIReviewReport)
// API key đặt trong frontend/.env.local, xem getAIConfig bên dưới.

const REQUEST_TIMEOUT_MS = 120000
const REVIEW_TIMEOUT_MS = 45000 // báo cáo sau trận cần nhanh; quá 45 giây thì báo lỗi để thử lại

// ===== Cấu hình AI (đọc từ frontend/.env.local, phải chạy lại `npm run dev` sau khi sửa) =====
//   VITE_AI_API_KEY   (bắt buộc)
//   VITE_AI_PROVIDER  openai | gemini | anthropic | openrouter | custom (mặc định openai)
//   VITE_AI_MODEL     (tùy chọn, mặc định theo nhà cung cấp)
//   VITE_AI_BASE_URL  (tùy chọn, bắt buộc với provider custom)
const PROVIDERS = {
  openai: { label: "OpenAI", kind: "openai", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  gemini: { label: "Google Gemini", kind: "openai", baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-3.5-flash" },
  anthropic: { label: "Anthropic Claude", kind: "anthropic", baseUrl: "https://api.anthropic.com", model: "claude-sonnet-5-5" },
  openrouter: { label: "OpenRouter", kind: "openai", baseUrl: "https://openrouter.ai/api/v1", model: "openai/gpt-4o-mini" },
  custom: { label: "Tùy chọn (tương thích OpenAI)", kind: "openai", baseUrl: "", model: "" },
}

export function getAIConfig() {
  const env = import.meta.env
  const provider = PROVIDERS[env.VITE_AI_PROVIDER] ? env.VITE_AI_PROVIDER : "openai"
  const preset = PROVIDERS[provider]
  return {
    provider,
    label: preset.label,
    apiKey: String(env.VITE_AI_API_KEY || "").trim(),
    model: String(env.VITE_AI_MODEL || "").trim() || preset.model,
    baseUrl: String(env.VITE_AI_BASE_URL || "").trim() || preset.baseUrl,
  }
}

export const isAIConfigured = (config) => Boolean(config?.apiKey && config?.model && config?.baseUrl)

// ===== Gọi API AI =====
async function sendChat(config, system, user, timeoutMs, lowEffort) {
  if (!isAIConfigured(config)) {
    throw new Error("Chưa cấu hình AI. Hãy thêm VITE_AI_API_KEY vào frontend/.env.local rồi chạy lại npm run dev.")
  }

  const base = config.baseUrl.replace(/\/+$/, "")
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  // Không gửi temperature / max_tokens cho giao thức OpenAI vì một số model mới từ chối các tham số này.
  const request =
    PROVIDERS[config.provider].kind === "anthropic"
      ? {
          url: `${base}/v1/messages`,
          headers: {
            "Content-Type": "application/json",
            "x-api-key": config.apiKey,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
          },
          body: { model: config.model, max_tokens: 8000, system, messages: [{ role: "user", content: user }] },
        }
      : {
          url: `${base}/chat/completions`,
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${config.apiKey}` },
          body: {
            model: config.model,
            messages: [{ role: "system", content: system }, { role: "user", content: user }],
            // Gemini hay "suy nghĩ" lâu; giảm mức suy luận để trả lời nhanh hơn.
            ...(lowEffort ? { reasoning_effort: "low" } : {}),
          },
        }

  let response
  try {
    response = await fetch(request.url, { method: "POST", headers: request.headers, body: JSON.stringify(request.body), signal: controller.signal })
  } catch (error) {
    if (error?.name === "AbortError") throw new Error(`AI phản hồi quá lâu (quá ${Math.round(timeoutMs / 1000)} giây). Hãy thử lại hoặc đổi sang model nhanh hơn (ví dụ gemini-3.5-flash-lite).`)
    throw new Error("Không gọi được API AI. Kiểm tra Base URL, mạng, hoặc nhà cung cấp có chặn gọi từ trình duyệt (CORS) không.")
  } finally {
    window.clearTimeout(timer)
  }

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.error?.message || data?.[0]?.error?.message || data?.message
    const failure = new Error(`AI báo lỗi (${response.status})${detail ? `: ${String(detail).slice(0, 300)}` : ""}`)
    failure.status = response.status
    throw failure
  }

  const text =
    PROVIDERS[config.provider].kind === "anthropic"
      ? (data?.content || []).filter((part) => part.type === "text").map((part) => part.text).join("")
      : data?.choices?.[0]?.message?.content
  if (!text) throw new Error("AI không trả về nội dung.")
  return text
}

async function chat(config, system, user, { timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  if (config.provider !== "gemini") return sendChat(config, system, user, timeoutMs, false)
  try {
    return await sendChat(config, system, user, timeoutMs, true)
  } catch (error) {
    // Model không nhận tham số reasoning_effort (lỗi 400) thì thử lại không kèm tham số.
    if (error.status !== 400) throw error
    return sendChat(config, system, user, timeoutMs, false)
  }
}

// Lấy object JSON đầu tiên trong câu trả lời (AI hay bọc trong ```json ... ```).
function extractJson(text) {
  const cleaned = text.replace(/```(?:json)?/gi, "")
  const start = cleaned.indexOf("{")
  const end = cleaned.lastIndexOf("}")
  if (start === -1 || end <= start) throw new Error("AI trả về dữ liệu không đúng định dạng. Hãy thử lại.")
  try {
    return JSON.parse(cleaned.slice(start, end + 1))
  } catch {
    throw new Error("Không đọc được JSON do AI trả về. Hãy thử lại.")
  }
}

const askJson = async (config, system, user) => extractJson(await chat(config, system, user))
const asText = (value) => (value == null ? "" : String(value))

// ===== Contract câu hỏi (schemas/questions.py) =====
export const DIFFICULTIES = ["EASY", "MEDIUM", "HARD"]
export const TOPIC_MIN = 2
export const TOPIC_MAX = 50
const LANGUAGES = ["cpp", "python", "java"]
const SAMPLE_TOPICS = ["Array", "String", "Math", "Sorting", "Hash Map", "Two Pointers", "Dynamic Programming", "Greedy", "Stack", "Binary Search"]

export const randomTopic = () => SAMPLE_TOPICS[Math.floor(Math.random() * SAMPLE_TOPICS.length)]

// StarterCodeSchema yêu cầu đủ cpp / python / java, mỗi bản không rỗng.
const DEFAULT_STARTER = {
  cpp: "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n\n    return 0;\n}\n",
  python: "import sys\n\ndef main():\n    data = sys.stdin.read().split()\n\nmain()\n",
  java: "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n    }\n}\n",
}

// TestCaseItem: input / expected_output là chuỗi đã strip, is_hidden là boolean.
function normalizeTestCases(list) {
  return (Array.isArray(list) ? list : [])
    .filter((item) => typeof item?.input === "string" && typeof item?.expected_output === "string")
    .map((item) => ({ input: item.input.trim(), expected_output: item.expected_output.trim(), is_hidden: item.is_hidden === true }))
    .filter((item) => item.input && item.expected_output)
}

// Ép dữ liệu AI về QuestionBase. Sai format thì ném lỗi liệt kê chỗ sai để yêu cầu AI làm lại.
function parseQuestion(raw, difficulty) {
  const errors = []
  const title = asText(raw?.title).trim()
  const description = asText(raw?.description)
  if (title.length < 3 || title.length > 255) errors.push("title phải dài 3 đến 255 ký tự")
  if (description.trim().length < 10) errors.push("description phải có ít nhất 10 ký tự")

  const testCases = normalizeTestCases(raw?.test_cases)
  if (testCases.length < 2) errors.push("test_cases phải có ít nhất 2 testcase, mỗi testcase có input và expected_output là chuỗi không rỗng")
  if (!testCases.some((item) => !item.is_hidden)) errors.push("phải có ít nhất 1 testcase công khai (is_hidden = false)")
  if (errors.length) throw new Error(errors.join("; "))

  const time = Number(raw?.time_limit)
  const memory = Math.round(Number(raw?.memory_limit))
  const starter = {}
  for (const lang of LANGUAGES) starter[lang] = asText(raw?.starter_code?.[lang]).trim() ? asText(raw.starter_code[lang]) : DEFAULT_STARTER[lang]

  return {
    title,
    description,
    difficulty, // luôn đúng độ khó người dùng chọn (QuestionDifficulty)
    time_limit: Number.isFinite(time) && time > 0 ? Math.min(time, 10) : 2.0, // gt 0, le 10
    memory_limit: Number.isFinite(memory) && memory > 0 ? Math.min(memory, 1024) : 128, // gt 0, le 1024
    starter_code: starter,
    test_cases: testCases,
    generated_by_ai: true,
  }
}

// Dạng câu hỏi mà phòng đấu nhận qua WebSocket (question_payload trong routers/arena.py):
// chỉ có testcase công khai, testcase ẩn không bao giờ đưa lên giao diện.
export function toRoomQuestion(question) {
  return {
    id: globalThis.crypto?.randomUUID?.() ?? `ai-${Date.now()}`,
    title: question.title,
    description: question.description,
    difficulty: question.difficulty,
    time_limit: question.time_limit,
    memory_limit: question.memory_limit,
    starter_code: question.starter_code,
    public_testcases: question.test_cases.filter((item) => item.is_hidden === false).map(({ input, expected_output }) => ({ input, expected_output })),
  }
}

const QUESTION_CONTRACT = `{
  "title": "tên bài, 3-255 ký tự",
  "description": "đề bài Markdown: mô tả, định dạng input, định dạng output, ràng buộc",
  "time_limit": 2.0,            // giây, > 0 và <= 10
  "memory_limit": 256,          // MB, số nguyên > 0 và <= 1024
  "starter_code": { "cpp": "...", "python": "...", "java": "..." },  // đủ 3 ngôn ngữ, đọc stdin, class Java tên Main
  "test_cases": [ { "input": "...", "expected_output": "...", "is_hidden": false } ],
  "reference_solution": "lời giải tham chiếu bằng Python (chỉ để kiểm duyệt, không lưu vào đề)"
}`

// ===== 1. AI ra đề (AIQuestionGenerateRequest: difficulty + topic) =====
export async function generateQuestion(config, { topic, difficulty }) {
  const system = "Bạn là giám khảo ra đề lập trình thi đấu. Chỉ trả về MỘT object JSON hợp lệ, không thêm chữ nào ngoài JSON. Nội dung viết bằng tiếng Việt."
  const base = `Hãy ra một bài lập trình thi đấu về chủ đề "${topic}", độ khó ${difficulty}.
Bài đọc dữ liệu từ stdin và in kết quả ra stdout. Đáp án phải duy nhất và xác định (không dùng số thực, không có nhiều đáp án đúng).
Trả về JSON đúng format backend CodeDuel sau:
${QUESTION_CONTRACT}
Yêu cầu test_cases: 6 testcase; 2 testcase đầu is_hidden=false (ví dụ trong đề), 4 testcase sau is_hidden=true gồm cả trường hợp biên. input/expected_output là văn bản đúng như stdin/stdout. Hãy tự chạy lời giải tham chiếu trên từng testcase để expected_output chính xác.`

  let previousError = ""
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const raw = await askJson(config, system, previousError ? `${base}\n\nLần trước bị backend từ chối vì: ${previousError}. Hãy sửa đúng các lỗi này.` : base)
    try {
      return { question: parseQuestion(raw, difficulty), reference_solution: asText(raw.reference_solution) }
    } catch (error) {
      previousError = error.message
    }
  }
  throw new Error(`AI tạo đề sai format của backend: ${previousError}`)
}

// ===== 2. AI kiểm duyệt đề (lượt gọi độc lập, sửa testcase sai) =====
export async function validateQuestion(config, { question, reference_solution }) {
  const system = "Bạn là người kiểm duyệt đề lập trình, độc lập với người ra đề và phải khắt khe. Chỉ trả về MỘT object JSON hợp lệ. Viết bằng tiếng Việt."
  const user = `Kiểm tra đề sau. Tự chạy lời giải tham chiếu trên TỪNG testcase để xác minh expected_output, và kiểm tra đề có mơ hồ, thiếu ràng buộc, nhiều đáp án đúng, hay input sai định dạng không.

ĐỀ:
${JSON.stringify({ title: question.title, description: question.description, time_limit: question.time_limit, memory_limit: question.memory_limit, test_cases: question.test_cases, reference_solution }, null, 2)}

Trả về JSON:
{
  "verdict": "OK" hoặc "FIX",
  "issues": ["mô tả ngắn từng vấn đề, để trống nếu không có"],
  "corrected_test_cases": [ { "input": "...", "expected_output": "...", "is_hidden": false } ]
}
Chỉ điền corrected_test_cases (danh sách ĐẦY ĐỦ sau khi sửa, giữ ít nhất 1 testcase is_hidden=false) khi verdict là "FIX" và có testcase sai; ngược lại để mảng rỗng.`

  const raw = await askJson(config, system, user)
  const corrected = normalizeTestCases(raw.corrected_test_cases)
  const usable = corrected.length >= 2 && corrected.some((item) => !item.is_hidden)
  return {
    verdict: String(raw.verdict).toUpperCase() === "OK" ? "OK" : "FIX",
    issues: (Array.isArray(raw.issues) ? raw.issues : []).map(asText).filter(Boolean),
    corrected_test_cases: usable ? corrected : [],
  }
}

// ===== 3. AI chấm bài =====
// AI chỉ mô phỏng việc biên dịch và chạy code (output thực tế, trạng thái từng testcase).
// Phần quyết định đúng/sai và tổng hợp kết quả làm bằng code, theo đúng luật của judge.py.
const CASE_STATUSES = ["PASS", "TLE", "MLE", "RUNTIME_ERROR"]
const HIDDEN_ERRORS = {
  FAIL: "Sai kết quả ở testcase ẩn",
  TLE: "Testcase ẩn vượt giới hạn thời gian",
  MLE: "Testcase ẩn vượt giới hạn bộ nhớ",
  RUNTIME_ERROR: "Lỗi thực thi ở testcase ẩn",
}
const nonNegative = (value) => (Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : 0)

// Tương đương evaluate_testcases: dừng ở testcase sai đầu tiên; chỉ testcase công khai mới có chi tiết.
function evaluateLikeBackend(cases, simulated) {
  const summary = { status: "FAIL", passed_count: 0, total_count: cases.length, execution_time_ms: 0, memory_used_mb: 0, error_message: null, results: [] }

  if (simulated.compile_error) {
    return { ...summary, status: "COMPILE_ERROR", error_message: simulated.compile_error, compile_error_message: simulated.compile_error }
  }

  for (let i = 0; i < cases.length; i += 1) {
    const testCase = cases[i]
    const sim = simulated.cases.find((item) => item.index === i + 1)
    const result = {
      status: CASE_STATUSES.includes(sim?.status) ? sim.status : sim ? "PASS" : "RUNTIME_ERROR",
      actual_output: sim ? asText(sim.actual_output) : "",
      error_message: sim ? sim.error_message || null : "Không mô phỏng được testcase này",
      execution_time_ms: nonNegative(sim?.execution_time_ms),
      memory_used_mb: nonNegative(sim?.memory_used_mb),
    }

    const passed = result.status === "PASS" && result.actual_output.trim() === testCase.expected_output.trim()
    if (result.status === "PASS" && !passed) {
      result.status = "FAIL"
      result.error_message = `Sai kết quả ở testcase ${i + 1}`
    }

    summary.execution_time_ms = Math.max(summary.execution_time_ms, result.execution_time_ms)
    summary.memory_used_mb = Math.max(summary.memory_used_mb, result.memory_used_mb)

    if (testCase.is_hidden === false) {
      summary.results.push({
        input: testCase.input,
        expected_output: testCase.expected_output,
        actual_output: result.actual_output,
        passed,
        status: result.status,
        error_message: result.error_message,
        execution_time_ms: result.execution_time_ms,
        execution_time: result.execution_time_ms / 1000,
        memory_used_mb: result.memory_used_mb,
      })
    } else if (result.error_message) {
      result.error_message = HIDDEN_ERRORS[result.status] || "Không chấm được testcase ẩn"
    }

    if (!passed) {
      summary.status = result.status
      summary.error_message = result.error_message
      return summary
    }
    summary.passed_count += 1
  }

  summary.status = "PASS"
  return summary
}

// kind "run"   -> chỉ testcase công khai, trả dạng CodeRunResponse (không ghi gì).
// kind "submit"-> toàn bộ testcase, trả dạng SubmissionResponse (không lộ input/output testcase ẩn).
export async function judgeSolution(config, { question, language, code, kind }) {
  const cases = kind === "run" ? question.test_cases.filter((item) => item.is_hidden === false) : question.test_cases
  const system = "Bạn là bộ chấm bài lập trình (online judge) nghiêm khắc. Hãy mô phỏng chính xác việc biên dịch và chạy code trên từng testcase. Chỉ trả về MỘT object JSON hợp lệ."
  const user = `Mô phỏng chạy bài làm bằng ${language}.

Giới hạn: ${question.time_limit} giây và ${question.memory_limit} MB cho mỗi testcase.
ĐỀ: ${question.title}
${question.description}

TESTCASE (index bắt đầu từ 1):
${JSON.stringify(cases.map((item, i) => ({ index: i + 1, input: item.input })), null, 2)}

CODE:
${code}

Nếu code không biên dịch được, đặt compile_error là thông báo lỗi ngắn. Nếu không, với MỖI testcase hãy lần theo code để ra đúng output thực tế (stdout) của chương trình, kể cả khi output sai. Đánh status: "PASS" nếu chạy xong bình thường, "TLE" nếu độ phức tạp chắc chắn vượt giới hạn thời gian, "MLE" nếu vượt bộ nhớ, "RUNTIME_ERROR" nếu crash / ngoài mảng / chia 0 / vòng lặp vô hạn. KHÔNG tự so với đáp án mong đợi.
Trả về JSON:
{
  "compile_error": null,
  "cases": [ { "index": 1, "status": "PASS", "actual_output": "...", "error_message": null, "execution_time_ms": 15, "memory_used_mb": 3.2 } ]
}`

  const raw = await askJson(config, system, user)
  const simulated = {
    compile_error: asText(raw.compile_error).trim() || null,
    cases: (Array.isArray(raw.cases) ? raw.cases : []).map((item) => ({
      index: Number(item?.index),
      status: String(item?.status || "").toUpperCase(),
      actual_output: item?.actual_output,
      error_message: asText(item?.error_message).trim() || null,
      execution_time_ms: item?.execution_time_ms,
      memory_used_mb: item?.memory_used_mb,
    })),
  }

  const summary = evaluateLikeBackend(cases, simulated)
  if (kind === "run") return summary
  return {
    status: summary.status,
    passed_test_cases: summary.passed_count,
    total_test_cases: summary.total_count,
    execution_time: summary.execution_time_ms / 1000,
    memory_used: summary.memory_used_mb,
    error_message: summary.error_message,
  }
}

// ===== 4. AI nhận xét sau khi nộp bài (AIReviewReport) =====
export async function reviewSolution(config, { question, language, code }) {
  const system = "Bạn là người hướng dẫn lập trình thi đấu. Chỉ trả về MỘT object JSON hợp lệ. Viết bằng tiếng Việt."
  const user = `Nhận xét bài làm ${language} cho đề "${question.title}".

ĐỀ:
${question.description}

CODE:
${code}

Trả về JSON đúng format AIReviewReport của backend:
{
  "time_complexity_analysis": "phân tích độ phức tạp thời gian",
  "space_complexity_analysis": "phân tích độ phức tạp bộ nhớ",
  "clean_code_evaluation": "đánh giá độ sạch của code",
  "optimized_solution": { "cpp": "code mẫu tối ưu", "python": "...", "java": "..." }
}`

  const raw = await askJson(config, system, user)
  const optimized = {}
  for (const lang of LANGUAGES) optimized[lang] = asText(raw.optimized_solution?.[lang])
  return {
    time_complexity_analysis: asText(raw.time_complexity_analysis),
    space_complexity_analysis: asText(raw.space_complexity_analysis),
    clean_code_evaluation: asText(raw.clean_code_evaluation),
    optimized_solution: optimized,
  }
}

// ===== 5. Báo cáo AI sau trận (Markdown, render bằng react-markdown) =====
// Backend chưa có endpoint ai-review và không trả code của đối thủ, nên báo cáo chỉ dựa trên code của chính bạn.
export async function reviewMatchMarkdown(config, { question, language, code, outcome }) {
  const system = "Bạn là Trọng tài AI của CodeDuel, chuyên phân tích thuật toán thi đấu. Trả lời bằng Markdown tiếng Việt, không bọc toàn bộ câu trả lời trong code block."
  const user = `Phân tích bài làm ${language} của người chơi vừa ${outcome} trận đấu.

ĐỀ: ${question.title}
${question.description}

VÍ DỤ:
${JSON.stringify(question.public_testcases || [], null, 2)}

CODE CỦA NGƯỜI CHƠI:
${code}

Viết NGẮN GỌN (tổng cộng dưới 300 từ, code mẫu tối đa 40 dòng). Trả về ĐÚNG 3 phần Markdown sau, theo thứ tự, đúng tiêu đề:

## 1. So sánh độ phức tạp thuật toán
Một bảng Markdown với cột: Tiêu chí | Bài của bạn | Lời giải tối ưu; hai hàng "Độ phức tạp thời gian" và "Độ phức tạp bộ nhớ", ghi dạng O(...). Sau bảng viết 1-2 câu kết luận.

## 2. Nhận xét độ sạch của code
Gạch đầu dòng về đặt tên biến, comment, chia hàm và các điểm cần cải thiện cụ thể.

## 3. Đoạn mã tối ưu mẫu
Một code block duy nhất, ghi rõ ngôn ngữ sau ba dấu huyền (\`\`\`${language === "C++" ? "cpp" : language === "Python 3" ? "python" : "java"}), là lời giải hoàn chỉnh đọc stdin / ghi stdout.`

  return (await chat(config, system, user, { timeoutMs: REVIEW_TIMEOUT_MS })).trim()
}