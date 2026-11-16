import { Link } from "react-router-dom"
import { ArrowRight, Braces, Code2, Terminal } from "lucide-react"

export default function Welcome() {
  return <section className="welcome-page">
    <div className="welcome-orbit orbit-one"/><div className="welcome-orbit orbit-two"/>
    <div className="welcome-content">
      <div className="welcome-mark"><Code2 size={28}/></div>
      <div className="eyebrow"><span className="eyebrow-line"/> YOUR NEXT CHALLENGE STARTS HERE</div>
      <h1>Chào mừng đến<br/>với <span>CodeDuel.</span></h1>
      <p>Nơi những ý tưởng được viết thành code, kỹ năng được thử thách và mỗi trận đấu đưa bạn tiến xa hơn.</p>
      <div className="welcome-actions">
        <Link to="/login" className="button button-large">Đăng nhập <ArrowRight size={17}/></Link>
        <Link to="/home" className="welcome-home-link"><span><Terminal size={17}/></span> Khám phá trang chủ</Link>
      </div>
      <div className="welcome-meta"><span><i/> READY TO CODE</span><span>CODE · COMPETE · CONQUER</span></div>
    </div>
    <div className="welcome-art" aria-hidden="true"><div className="welcome-grid"/><div className="welcome-code-card"><div className="welcome-code-top"><span><i/><i/><i/></span><small>challenge.js</small><Braces size={15}/></div><div className="welcome-code"><span className="line-no">01</span><code><b>const</b> nextLevel = <em>(you)</em> =&gt; {'{'}</code><span className="line-no">02</span><code>&nbsp;&nbsp;<b>return</b> <i>compete</i>(you.skills);</code><span className="line-no">03</span><code>{'}'} <u>// your move</u></code></div><div className="welcome-code-bottom"><span><i/> SYSTEM READY</span><span>UTF-8</span></div></div><div className="welcome-float float-top">{'{'} <span>BUILD</span> {'}'}</div><div className="welcome-float float-bottom"><span>01</span> / 02 <i/></div></div>
  </section>
}
