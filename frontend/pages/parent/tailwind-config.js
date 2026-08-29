/* ChemAI 家长端 — 共享 Tailwind 配置（各页在 tailwind CDN 之前引入） */
window.tailwind = {
  theme: { extend: {
    colors: {
      "oxford-blue": "#002147", "oxford-hover": "#001a38",
      "teal-accent": "#0d7377", "teal-hover": "#0a5c5f",
      "warm-paper": "#faf8f5", "warm-bg": "#f5f0e8",
      "text-primary": "#1a1a2e", "text-secondary": "#6b7280",
      "error-red": "#b43c28", "pass-green": "#2c6e49",
      "purple-bar": "#7B2D8E", "blue-bar": "#3B5BA5", "cyan-bar": "#00897B",
    },
    fontFamily: {
      "headline": ["Cormorant Garamond", "serif"],
      "body": ["IBM Plex Sans", "Noto Sans SC", "sans-serif"],
    },
  } },
};
