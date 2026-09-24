/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        brand: token("brand"),
        "brand-soft": token("brand-soft"),
        "on-brand": token("on-brand"),
        bg: token("bg"),
        card: token("card"),
        ink: token("ink"),
        muted: token("muted"),
        line: token("line"),
        good: token("good"),
        warn: token("warn"),
        bad: token("bad"),
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans Variable"', "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      boxShadow: {
        card: "0 1px 2px rgb(0 0 0 / 0.04), 0 6px 20px -8px rgb(0 0 0 / 0.12)",
        float: "0 10px 30px -10px rgb(0 0 0 / 0.25)",
      },
    },
  },
  plugins: [],
};
