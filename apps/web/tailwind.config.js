/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        overworld: {
          bg: "#13151f",         // Deep Midnight Charcoal canvas
          surface: "#1a1e2b",    // Elevated card/panel surface
          card: "#1e2333",       // Secondary elevated item
          hover: "#252b3d",      // Hover state
          border: "#293245",     // Hairline steel border
          text: "#e9ecee",       // Pale silver primary text
          secondary: "#aab9c7",  // Soft steel blue secondary accent
          gray: "#6e8799",       // Muted cool blue-gray
          dark: "#4c5e6b",       // Deep slate divider
          accent: "#aab9c7",     // Primary brand accent
          btn: "#e9ecee",        // High-contrast button
          btnText: "#13151f",    // High-contrast text
        }
      }
    },
  },
  plugins: [],
}
