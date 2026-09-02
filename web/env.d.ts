/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_MOCK?: string
  readonly VITE_API_URL?: string
  /** "1": static demo, documents from `${BASE_URL}static/` (contracts §18) */
  readonly VITE_STATIC?: string
  /** Vite `base` for hosting under a path, e.g. "/ai-workforce-sim/" (GitHub Pages) */
  readonly VITE_BASE?: string
}
