import type { Branding } from "./types";

function hexToRgb(hex: string): [number, number, number] | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!match) return null;
  const n = parseInt(match[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function luminance([r, g, b]: [number, number, number]) {
  const [R, G, B] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

const triplet = (rgb: [number, number, number]) => rgb.join(" ");

/** Push the school's colours into the CSS tokens that Tailwind's brand classes read. */
export function applyBranding(branding: Branding) {
  const root = document.documentElement.style;
  const primary = hexToRgb(branding.colors.primary);
  const secondary = hexToRgb(branding.colors.secondary);
  const ink = hexToRgb(branding.colors.ink);

  if (primary) {
    root.setProperty("--brand", triplet(primary));
    root.setProperty("--on-brand", luminance(primary) > 0.45 ? "17 17 17" : "255 255 255");
  }
  if (secondary) root.setProperty("--brand-soft", triplet(secondary));
  if (ink) root.setProperty("--ink-light", triplet(ink));

  document.title = branding.app_name;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", branding.colors.primary);
}
