import { useState } from "react"

// Ảnh đại diện tròn; nếu không có URL hoặc ảnh lỗi thì hiện chữ cái đầu của tên.
export default function Avatar({ url, name = "", className = "" }) {
  const [broken, setBroken] = useState(null)
  const showImage = Boolean(url) && broken !== url
  return <span className={`avatar ${className}`}>
    {showImage
      ? <img src={url} alt="" referrerPolicy="no-referrer" onError={() => setBroken(url)} />
      : <span aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>}
  </span>
}
