/**
 * Shared ESLint preset for RDC TypeScript packages.
 * Consumed by apps/packages via `extends`.
 */
module.exports = {
  extends: ["next/core-web-vitals"],
  rules: {
    "no-console": ["warn", { allow: ["warn", "error"] }],
  },
};
