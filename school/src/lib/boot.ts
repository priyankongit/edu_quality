import type { Branding } from "./types";

type Boot = {
  branding?: Branding;
  csrf_token?: string;
  user?: string;
};

/** Data the server renders into the page (see edu_quality/www/school.py). Empty in `vite dev`. */
function readBoot(): Boot {
  const el = document.getElementById("school-boot");
  if (!el?.textContent) return {};
  try {
    return JSON.parse(el.textContent) as Boot;
  } catch {
    return {};
  }
}

export const boot = readBoot();
