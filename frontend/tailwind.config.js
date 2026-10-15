/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#14212b", 2: "#46535c", 3: "#6b7780" },
        paper: "#f6f7f5",
        panel: "#ffffff",
        rule: "#dfe3e1",
        petrol: { DEFAULT: "#0f5e6b", 50: "#e7f1f2", 100: "#cfe3e6", 700: "#0b4954" },
        good: "#0a7d0a",
        bad: "#c23434",
        warn: "#a86a00",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        figure: ['"IBM Plex Sans Condensed"', '"IBM Plex Sans"', "system-ui", "sans-serif"],
      },
      fontSize: {
        // modular scale (1.25) with comfortable line heights
        xs: ["0.75rem", { lineHeight: "1.1rem" }],
        sm: ["0.875rem", { lineHeight: "1.3rem" }],
        base: ["1rem", { lineHeight: "1.55rem" }],
        lg: ["1.25rem", { lineHeight: "1.75rem" }],
        xl: ["1.563rem", { lineHeight: "2.05rem" }],
        "2xl": ["1.953rem", { lineHeight: "2.4rem" }],
        "3xl": ["2.441rem", { lineHeight: "2.9rem" }],
      },
    },
  },
  plugins: [],
};
