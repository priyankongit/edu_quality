import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, open the app through your site's host name (e.g. http://dma.localhost:8080/school/)
// so Frappe can tell which site the proxied API calls are for.
const frappeUrl = process.env.FRAPPE_URL || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  base: "/school/",
  server: {
    port: 8080,
    host: true,
    proxy: {
      "^/(app|api|assets|files|private)": { target: frappeUrl },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "../edu_quality/public/school",
    emptyOutDir: true,
    target: ["es2020", "safari14"],
  },
});
