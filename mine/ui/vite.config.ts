import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Kyzyl-Tas Mine UI - Vite config.
// No CDN usage anywhere: all JS/CSS/fonts are bundled by this build.
// The app is served as static files by nginx (see ../Dockerfile); it talks
// to the platform only via same-origin paths proxied by the mine-ui nginx
// (see NOTES.md for the exact paths assumed).
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    target: "es2022",
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
    chunkSizeWarningLimit: 1600
  },
  server: {
    port: 5173
  }
});
