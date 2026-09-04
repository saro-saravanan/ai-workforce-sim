/**
 * Plain-language number words, ported from `api/aiwsim_api/story.py` so the client-side outlook
 * and executive brief read exactly like the server's. Python's `f"{x:.0f}"` rounds exact ties to
 * even; JavaScript's `toFixed` rounds them up, so ties are handled explicitly.
 */

/**
 * True when `v` is exactly halfway between two numbers with `digits` decimals, i.e. when
 * `v × 2 × 10^digits` is an odd integer; read off the double's exact binary value so that a
 * near-tie such as 4.65 (stored slightly above 4.65) is not mistaken for one.
 */
function isTie(v: number, digits: number): boolean {
  const view = new DataView(new ArrayBuffer(8))
  view.setFloat64(0, Math.abs(v))
  const bits = view.getBigUint64(0)
  const expBits = Number((bits >> 52n) & 0x7ffn)
  let mant = bits & ((1n << 52n) - 1n)
  let exp: number
  if (expBits === 0) exp = -1074
  else {
    mant |= 1n << 52n
    exp = expBits - 1075
  }
  if (mant === 0n) return false
  // v × 2 × 10^digits = mant × 5^digits × 2^(exp + 1 + digits)
  const num = mant * 5n ** BigInt(digits)
  const e = exp + 1 + digits
  if (e > 0) return false
  let tz = 0
  let n = num
  while ((n & 1n) === 0n) {
    n >>= 1n
    tz++
  }
  return tz === -e
}

/**
 * Python `f"{v:.{digits}f}"`: `toFixed` (exact in V8) except on exact ties, which Python rounds
 * to even. A negative value that rounds to zero keeps its sign ("-0"), as Python prints it.
 */
export function pyFixed(v: number, digits = 0): string {
  if (!Number.isFinite(v) || !isTie(v, digits)) return v.toFixed(digits)
  const m = 10 ** digits
  const f = Math.floor(v * m)
  const n = f % 2 === 0 ? f : f + 1
  const out = (Math.abs(n) / m).toFixed(digits)
  return v < 0 ? `-${out}` : out
}

/** Python `f"{v:+.{digits}f}"` */
export function pySigned(v: number, digits = 0): string {
  const s = pyFixed(v, digits)
  return s.startsWith('-') ? s : `+${s}`
}

/** Python `round(v)` (ties to even) */
export function pyRound(v: number): number {
  return Number(pyFixed(v, 0))
}

/** Python `f"{v:,.0f}"` */
export function pyGrouped(v: number): string {
  const s = pyFixed(v, 0)
  const neg = s.startsWith('-')
  const digits = neg ? s.slice(1) : s
  return (neg ? '-' : '') + digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/** "8.6 million", "176,000", "42" (always unsigned, like story.py `_millions`) */
export function millions(x: number): string {
  x = Math.abs(x)
  if (x >= 1e9) return `${pyFixed(x / 1e9, 2)} billion`
  if (x >= 1e6) return `${pyFixed(x / 1e6, 1)} million`
  if (x >= 1e3) return `${pyFixed(x / 1e3, 0)},000`
  return pyFixed(x, 0)
}

/** Python `str.capitalize()` */
export function capitalize(s: string): string {
  return s ? s[0]!.toUpperCase() + s.slice(1).toLowerCase() : s
}
