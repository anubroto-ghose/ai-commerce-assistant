const rawApiBase = import.meta.env.VITE_API_BASE?.trim()

export const API_BASE = rawApiBase && rawApiBase.length > 0 ? rawApiBase : window.location.origin
