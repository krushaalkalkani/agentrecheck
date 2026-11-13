import { createHash, randomBytes } from "node:crypto";

export const API_KEY_PREFIX = "ark_";

export function hashApiKey(key: string): string {
  return createHash("sha256").update(key).digest("hex");
}

/** Generate a new project API key. Only `hash` and `prefix` are persisted. */
export function generateApiKey() {
  const key = API_KEY_PREFIX + randomBytes(24).toString("hex");
  return { key, hash: hashApiKey(key), prefix: key.slice(0, 12) };
}

export function bearerToken(request: Request): string | null {
  const header = request.headers.get("authorization");
  if (!header) return null;
  const [scheme, token] = header.split(" ");
  return scheme?.toLowerCase() === "bearer" && token ? token.trim() : null;
}
