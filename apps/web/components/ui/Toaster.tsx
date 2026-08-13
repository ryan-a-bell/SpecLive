"use client";

import { useToast } from "@/lib/toast";

export function Toaster() {
  const message = useToast((s) => s.message);
  return <div className={`toast${message ? " show" : ""}`}>{message}</div>;
}
