import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "@rdc/domain": path.resolve(__dirname, "../../packages/domain/src/index.ts"),
      "@rdc/client": path.resolve(__dirname, "../../packages/client/src/index.ts"),
      "@rdc/ui": path.resolve(__dirname, "../../packages/ui/src/index.ts"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
  },
});
