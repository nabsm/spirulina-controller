/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,jsx}"],
    theme: {
      extend: {
        colors: {
          primary: "#60a5fa",        // Blue-400 (bright on dark)
          primaryHover: "#3b82f6",   // Blue-500
          accent: "#D4AF37",         // Gold
          accentHover: "#c8a52e",
          bg: "#0f172a",             // Slate-900 (page background)
          panel: "#1e293b",          // Slate-800 (card background)
          surface: "#334155",        // Slate-700 (input/button bg)
          surfaceHover: "#475569",   // Slate-600
          line: "#475569",           // Slate-600 (borders)
          text: "#f1f5f9",           // Slate-100 (primary text)
          text2: "#94a3b8",          // Slate-400 (secondary text)
        },
        boxShadow: {
          soft: "0 8px 20px rgba(0, 0, 0, 0.3)",
        },
        borderRadius: {
          xl2: "1rem",
        },
      },
    },
    plugins: [],
  };
