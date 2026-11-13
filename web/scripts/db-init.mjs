// Apply the schema to the Postgres database in DATABASE_URL (e.g. Supabase).
// Usage: DATABASE_URL=postgres://... npm run db:init
import { readFileSync } from "node:fs";
import postgres from "postgres";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL is not set.");
  process.exit(1);
}

// The DDL lives in one place (src/lib/db/init-sql.ts); read it from there.
const source = readFileSync(new URL("../src/lib/db/init-sql.ts", import.meta.url), "utf8");
const ddl = source.slice(source.indexOf("`") + 1, source.lastIndexOf("`"));

const sql = postgres(url, { prepare: false, max: 1 });
try {
  await sql.unsafe(ddl);
  console.log("Schema applied.");
} finally {
  await sql.end();
}
