/**
 * A tiny, safe Markdown renderer for chat replies: paragraphs, headings, **bold**, *italic*,
 * `code`, bullet and numbered lists, and pipe tables. Everything is HTML-escaped first; no raw
 * HTML passes through, so the output can go into v-html.
 */

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// a private-use code point that does not occur in prose, used to hold code spans while marks are applied
const HOLD = '\uE000'

/** Inline marks on already-escaped text: code first (its content takes no other marks). */
export function renderInline(escaped: string): string {
  const codes: string[] = []
  let s = escaped.replace(/`([^`\n]+)`/g, (_m, c: string) => {
    codes.push(`<code>${c}</code>`)
    return `${HOLD}${codes.length - 1}${HOLD}`
  })
  s = s.replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/(^|[\s(])\*(\S(?:[^*\n]*?\S)?)\*(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>')
  s = s.replace(/(^|[\s(])_(\S(?:[^_\n]*?\S)?)_(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>')
  return s.replace(/\uE000(\d+)\uE000/g, (_m, i: string) => codes[Number(i)] ?? '')
}

const isTableRow = (l: string) => /^\s*\|.*\|\s*$/.test(l)
const isTableSep = (l: string) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l)
const cells = (l: string) =>
  l
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim())

const BULLET = /^\s*[-*•]\s+(.*)$/
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/
const HEADING = /^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/

function startsTable(lines: string[], i: number) {
  return isTableRow(lines[i]!) && i + 1 < lines.length && isTableSep(lines[i + 1]!)
}

export function renderMarkdown(md: string): string {
  const lines = escapeHtml(md.replace(/\r\n?/g, '\n')).split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]!
    if (!line.trim()) {
      i++
      continue
    }
    if (startsTable(lines, i)) {
      const head = cells(line)
      i += 2
      const body: string[][] = []
      while (i < lines.length && isTableRow(lines[i]!) && !isTableSep(lines[i]!)) {
        body.push(cells(lines[i]!))
        i++
      }
      out.push('<table class="md-table"><thead><tr>')
      out.push(head.map((c) => `<th>${renderInline(c)}</th>`).join(''))
      out.push('</tr></thead><tbody>')
      for (const r of body)
        out.push(`<tr>${r.map((c) => `<td>${renderInline(c)}</td>`).join('')}</tr>`)
      out.push('</tbody></table>')
      continue
    }
    const h = HEADING.exec(line)
    if (h) {
      out.push(`<p class="md-h"><strong>${renderInline(h[2]!)}</strong></p>`)
      i++
      continue
    }
    if (BULLET.test(line)) {
      out.push('<ul>')
      while (i < lines.length && BULLET.test(lines[i]!)) {
        out.push(`<li>${renderInline(BULLET.exec(lines[i]!)![1]!)}</li>`)
        i++
      }
      out.push('</ul>')
      continue
    }
    if (NUMBERED.test(line)) {
      out.push('<ol>')
      while (i < lines.length && NUMBERED.test(lines[i]!)) {
        out.push(`<li>${renderInline(NUMBERED.exec(lines[i]!)![1]!)}</li>`)
        i++
      }
      out.push('</ol>')
      continue
    }
    // paragraph: consecutive non-blank lines that start no other block
    const para: string[] = []
    while (
      i < lines.length &&
      lines[i]!.trim() &&
      !BULLET.test(lines[i]!) &&
      !NUMBERED.test(lines[i]!) &&
      !HEADING.test(lines[i]!) &&
      !startsTable(lines, i)
    ) {
      para.push(lines[i]!.trim())
      i++
    }
    if (para.length) out.push(`<p>${renderInline(para.join(' '))}</p>`)
  }
  return out.join('')
}
