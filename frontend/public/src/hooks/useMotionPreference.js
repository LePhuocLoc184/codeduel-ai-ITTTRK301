import { useEffect, useState } from "react"

export default function useMotionPreference() {
  const [enabled, setEnabled] = useState(() => (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: no-preference)").matches
  ))

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: no-preference)")
    const update = () => setEnabled(preference.matches)
    update()
    preference.addEventListener("change", update)
    return () => preference.removeEventListener("change", update)
  }, [])

  return enabled
}
