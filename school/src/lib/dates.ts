/** YYYY-MM-DD in the device's local time zone (toISOString would shift to UTC). */
export function localISO(date = new Date()) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseISO(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDay(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "short", day: "numeric", month: "short" }) {
  return parseISO(iso).toLocaleDateString(undefined, opts);
}

export function isToday(iso: string) {
  return iso === localISO();
}

/** Minutes since midnight for "HH:MM". */
export function minutesOf(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + (m || 0);
}
