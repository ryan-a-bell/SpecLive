export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export const DEMO_SESSION_ID = process.env.NEXT_PUBLIC_DEMO_SESSION_ID ?? "SESSION-DEMO";
