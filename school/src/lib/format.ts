const formatters = new Map<string, Intl.NumberFormat>();

/** ₹12,500 — whole units, the way fee sheets are read. */
export function money(amount: number, currency: string) {
  let f = formatters.get(currency);
  if (!f) {
    try {
      f = new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 });
    } catch {
      f = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
    }
    formatters.set(currency, f);
  }
  return f.format(Math.round(amount));
}

/** Frappe datetimes ("2026-10-08 14:05:09.123") as a Date in local time. */
export function parseDateTime(value: string) {
  return new Date(value.replace(" ", "T"));
}

/** "14:05" today, "Mon" this week, else "8 Oct". */
export function shortWhen(value: string) {
  const d = parseDateTime(value);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  const days = (now.getTime() - d.getTime()) / 86_400_000;
  if (days < 6) return d.toLocaleDateString(undefined, { weekday: "short" });
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
