import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  text: string
  kind: 'info' | 'warn'
}

/** Small, transient notices (e.g. "mock: run reused the parent's results"). */
export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])
  let next = 1

  function push(text: string, kind: Toast['kind'] = 'info', ms = 4500) {
    const id = next++
    toasts.value.push({ id, text, kind })
    setTimeout(() => dismiss(id), ms)
    return id
  }
  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }
  return { toasts, push, dismiss }
})
