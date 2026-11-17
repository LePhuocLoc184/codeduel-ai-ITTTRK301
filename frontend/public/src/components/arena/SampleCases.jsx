import { useState } from "react"

export default function SampleCases({ testcases }) {
  const [active, setActive] = useState(0)
  const current = testcases[Math.min(active, testcases.length - 1)]

  return (
    <div className="sample-cases">
      <div className="sample-tabs" role="tablist" aria-label="Testcase mẫu">
        <span className="panel-label">TESTCASE MẪU</span>

        {testcases.map((_, index) => (
          <button
            key={index}
            type="button"
            role="tab"
            aria-selected={index === active}
            className={index === active ? "active" : ""}
            onClick={() => setActive(index)}
          >
            Case {index + 1}
          </button>
        ))}
      </div>

      {current ? (
        <div className="sample-body">
          <div>
            <small>INPUT</small>
            <pre>{current.input}</pre>
          </div>

          <div>
            <small>OUTPUT KỲ VỌNG</small>
            <pre>{current.expected_output}</pre>
          </div>
        </div>
      ) : (
        <p className="sample-empty">Bài này chưa có testcase mẫu.</p>
      )}
    </div>
  )
}