import { createClient } from "@rdc/client";
import { API_BASE_URL } from "./config";

export const api = createClient({ baseUrl: API_BASE_URL });
