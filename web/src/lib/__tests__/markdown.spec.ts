import { describe, expect, it } from 'vitest'
import { escapeHtml, renderInline, renderMarkdown } from '../markdown'

describe('escapeHtml', () => {
  it('escapes the five HTML metacharacters', () => {
    expect(escapeHtml(`<a href="x">&'</a>`)).toBe(
      '&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;',
    )
  })
})

describe('renderInline', () => {
  it('renders bold, italic and code', () => {
    expect(renderInline('a **b** *c* `d`')).toBe('a <strong>b</strong> <em>c</em> <code>d</code>')
  })
  it('does not apply marks inside code spans and keeps digits next to code intact', () => {
    expect(renderInline('`**x**` 1 `y` 2')).toBe('<code>**x**</code> 1 <code>y</code> 2')
  })
  it('leaves multiplication asterisks alone', () => {
    expect(renderInline('2 * 3 * 4')).toBe('2 * 3 * 4')
  })
})

describe('renderMarkdown', () => {
  it('escapes HTML so scripts never reach the DOM', () => {
    const html = renderMarkdown('<script>alert(1)</script> **ok**')
    expect(html).not.toContain('<script>')
    expect(html).toBe('<p>&lt;script&gt;alert(1)&lt;/script&gt; <strong>ok</strong></p>')
  })
  it('joins consecutive lines into one paragraph and splits on blank lines', () => {
    expect(renderMarkdown('one\ntwo\n\nthree')).toBe('<p>one two</p><p>three</p>')
  })
  it('renders pipe tables with a header row', () => {
    const html = renderMarkdown(
      '| Lever | From → To |\n|---|---|\n| `a.b` | 5 → **4** |\n| c | d |',
    )
    expect(html).toBe(
      '<table class="md-table"><thead><tr><th>Lever</th><th>From → To</th></tr></thead><tbody>' +
        '<tr><td><code>a.b</code></td><td>5 → <strong>4</strong></td></tr><tr><td>c</td><td>d</td></tr></tbody></table>',
    )
  })
  it('renders bullet and numbered lists', () => {
    expect(renderMarkdown('- a\n- b\n\n1. x\n2. y')).toBe(
      '<ul><li>a</li><li>b</li></ul><ol><li>x</li><li>y</li></ol>',
    )
  })
  it('renders headings as emphasised paragraphs', () => {
    expect(renderMarkdown('## Findings\ntext')).toBe(
      '<p class="md-h"><strong>Findings</strong></p><p>text</p>',
    )
  })
  it('a table directly after a paragraph starts a new block', () => {
    const html = renderMarkdown('Here:\n| a | b |\n|---|---|\n| 1 | 2 |')
    expect(html.startsWith('<p>Here:</p><table')).toBe(true)
  })
  it('handles CRLF and empty input', () => {
    expect(renderMarkdown('a\r\n\r\nb')).toBe('<p>a</p><p>b</p>')
    expect(renderMarkdown('')).toBe('')
  })
})
