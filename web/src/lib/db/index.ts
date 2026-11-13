import { mkdirSync } from "node:fs";

import { PGlite } from "@electric-sql/pglite";
import { drizzle as drizzlePglite, type PgliteDatabase } from "drizzle-orm/pglite";
import { drizzle as drizzlePostgres } from "drizzle-orm/postgres-js";
import postgres from "postgres";

import { INIT_SQL } from "./init-sql";
import * as schema from "./schema";

export type Db = PgliteDatabase<typeof schema>;

/** True when no DATABASE_URL is set and the embedded local database is used. */
export const isLocalDb = () => !process.env.DATABASE_URL;

const globalForDb = globalThis as unknown as { __arcDb?: Promise<Db> };

async function createDb(): Promise<Db> {
  const url = process.env.DATABASE_URL;
  if (url) {
    // `prepare: false` is required for Supabase's transaction-mode pooler.
    const client = postgres(url, { prepare: false, max: 5 });
    // Both drivers expose the same query builder; share one type.
    return drizzlePostgres(client, { schema }) as unknown as Db;
  }

  // Local fallback: Postgres compiled to WASM, running in-process. Persisted
  // to disk in development; in-memory in tests and on read-only hosts.
  const ephemeral = process.env.NODE_ENV === "test" || Boolean(process.env.VERCEL);
  const dataDir = process.env.AGENTRECHECK_PGLITE_DIR ?? (ephemeral ? undefined : ".data/pglite");
  if (dataDir) mkdirSync(dataDir, { recursive: true });
  const pg = dataDir ? new PGlite(dataDir) : new PGlite();
  await pg.exec(INIT_SQL);
  const db = drizzlePglite(pg, { schema });

  if (process.env.NODE_ENV !== "test" && process.env.AGENTRECHECK_SEED !== "0") {
    const { seedDemoData } = await import("../seed");
    await seedDemoData(db);
  }
  return db;
}

export function getDb(): Promise<Db> {
  globalForDb.__arcDb ??= createDb().catch((error) => {
    // Don't cache a failed connection attempt.
    globalForDb.__arcDb = undefined;
    throw error;
  });
  return globalForDb.__arcDb;
}

/** Test helper: drop the cached connection so the next call starts fresh. */
export function resetDbForTests() {
  globalForDb.__arcDb = undefined;
}

export { schema };
