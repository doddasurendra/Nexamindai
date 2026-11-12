/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7fb",
          100: "#eceef7",
          200: "#d6dae9",
          300: "#b3bad2",
          400: "#8993b4",
          500: "#66739a",
          600: "#4d587d",
          700: "#3c4564",
          800: "#2a3149",
          900: "#1b2033",
          950: "#111422"
        },
        accent: {
          50: "#eef6ff",
          100: "#d9ecff",
          200: "#bcdcff",
          300: "#8ec5ff",
          400: "#59a4ff",
          500: "#3382ff",
          600: "#1b63f5",
          700: "#164ee1",
          800: "#1841b6",
          900: "#1a3c8f"
        },
        mint: { 400: "#37d6b2", 500: "#13b996", 600: "#0d967b" },
        amberish: { 400: "#ffb547", 500: "#f59e0b" }
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        display: ["Sora", "Inter", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Cascadia Code", "Consolas", "monospace"]
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(51,130,255,.25), 0 12px 40px -12px rgba(51,130,255,.45)",
        card: "0 1px 0 rgba(255,255,255,.04) inset, 0 20px 40px -24px rgba(2,6,23,.55)"
      },
      keyframes: {
        floaty: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-4px)" } },
        fadeup: { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "translateY(0)" } }
      },
      animation: { floaty: "floaty 6s ease-in-out infinite", fadeup: "fadeup .35s ease-out both" }
    }
  },
  plugins: []
};
