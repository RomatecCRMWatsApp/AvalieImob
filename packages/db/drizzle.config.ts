import type { Config } from "drizzle-kit";

export default {
  schema: "./schema.ts",
  driver: "mysql2",
  dbCredentials: {
    host: process.env.DATABASE_HOST || "mainline.proxy.rlwy.net",
    port: parseInt(process.env.DATABASE_PORT || "56439"),
    user: process.env.DATABASE_USER || "root",
    password: process.env.DATABASE_PASSWORD || "",
    database: process.env.DATABASE_NAME || "avaliacoes_db",
  },
  migrations: {
    schema: "drizzle",
    table: "__drizzle_migrations",
    prefix: "drizzle",
  },
  tablesFilter: ["avaliacoes_*"],
  casing: "snake_case",
} satisfies Config;
