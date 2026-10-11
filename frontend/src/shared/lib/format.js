const LOCALE = "vi-VN";

export const formatDateTime = (iso) => new Date(iso).toLocaleString(LOCALE);

/** 125 -> "02:05" */
export function formatMmSs(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
