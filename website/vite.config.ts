import { defineConfig } from "vite";

// Relative base so the build works at https://<user>.github.io/seedforge/ and from a local folder.
export default defineConfig({
  base: "./",
  build: { outDir: "dist", assetsInlineLimit: 0, chunkSizeWarningLimit: 900 },
});
