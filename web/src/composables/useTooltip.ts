import { reactive } from 'vue'

export interface TooltipRow {
  label: string
  value: string
  swatch?: string
  kind?: 'line' | 'rect'
}
export interface TooltipState {
  visible: boolean
  x: number
  y: number
  title: string
  rows: TooltipRow[]
}

/** Shared tooltip state; positioned relative to the chart's own container. */
export function useTooltip() {
  const tip = reactive<TooltipState>({ visible: false, x: 0, y: 0, title: '', rows: [] })
  function show(x: number, y: number, title: string, rows: TooltipRow[]) {
    tip.visible = true
    tip.x = x
    tip.y = y
    tip.title = title
    tip.rows = rows
  }
  function move(x: number, y: number) {
    tip.x = x
    tip.y = y
  }
  function hide() {
    tip.visible = false
  }
  return { tip, show, move, hide }
}
