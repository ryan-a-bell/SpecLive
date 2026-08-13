import type { Config } from "tailwindcss";

// Palette mirrors the prototype's CSS custom properties so the production UI
// keeps the reference visual language.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#09101d",
        panel: "#121b2d",
        panel2: "#0e1727",
        panel3: "#18243a",
        border: "#293a57",
        text: "#eef4fb",
        muted: "#9eb0c7",
        brand: {
          blue: "#67a8ff",
          green: "#64d69b",
          yellow: "#ffd36f",
          red: "#ff7f8f",
          purple: "#b693ff",
          orange: "#ffab68",
        },
      },
      boxShadow: {
        panel: "0 16px 42px rgba(0,0,0,.28)",
      },
      borderRadius: {
        panel: "14px",
      },
    },
  },
  plugins: [],
};

export default config;
