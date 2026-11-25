import { useCallback, useEffect, useState } from "react"

export default function useScrollReveal() {
  const [element, setElement] = useState(null)
  const ref = useCallback(setElement, [])

  useEffect(() => {
    if (!element) return undefined

    if (!("IntersectionObserver" in window)) {
      element.classList.add("is-revealed")
      return undefined
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return
      element.classList.add("is-revealed")
      observer.unobserve(element)
    }, { threshold: 0.12 })

    observer.observe(element)
    return () => observer.disconnect()
  }, [element])

  return ref
}
