import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// envDir '..' -> the dashboard reads VITE_API_BASE_URL from the project-root .env
export default defineConfig({
  plugins: [react()],
  envDir: "..",
  server: { port: 5173, strictPort: true },
  preview: { port: 5173 },
});
