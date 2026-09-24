// Frappe serves /school from edu_quality/www/school.html (rendered through Jinja with
// school.py), so copy the built entry point there after every build.
import { copyFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const from = fileURLToPath(new URL("../../edu_quality/public/school/index.html", import.meta.url));
const to = fileURLToPath(new URL("../../edu_quality/www/school.html", import.meta.url));

copyFileSync(from, to);
console.log("Copied school entry to edu_quality/www/school.html");
