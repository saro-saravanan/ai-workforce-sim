import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/** Tracks the pixel size of an element via ResizeObserver. */
export function useSize(el: Ref<HTMLElement | null>, fallback = { width: 640, height: 360 }) {
  const width = ref(fallback.width)
  const height = ref(fallback.height)
  let ro: ResizeObserver | null = null

  onMounted(() => {
    if (!el.value) return
    const measure = () => {
      const host = el.value
      if (!host) return
      const r = host.getBoundingClientRect()
      // never wider than the nearest sized ancestor: a host inside a flex or grid cell that has not settled can report the
      // fallback width of its own svg, which on a phone is wider than the screen
      let cap = Number.POSITIVE_INFINITY
      for (let a = host.parentElement; a; a = a.parentElement) {
        const w = a.clientWidth
        if (w > 0) {
          cap = w
          break
        }
      }
      const w = Math.min(r.width > 0 ? r.width : cap, cap)
      if (Number.isFinite(w) && w > 0) {
        width.value = w
        height.value = r.height
      }
    }
    measure()
    if (typeof requestAnimationFrame !== 'undefined') requestAnimationFrame(measure)
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(measure)
      ro.observe(el.value)
    }
  })
  onBeforeUnmount(() => ro?.disconnect())
  return { width, height }
}
