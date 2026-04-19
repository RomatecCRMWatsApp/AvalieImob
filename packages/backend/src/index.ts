import express from "express";
import cors from "cors";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { createContext } from "./lib/trpc";
import { appRouter } from "./routers";
import dotenv from "dotenv";
import mysql from "mysql2/promise";
import { drizzle } from "drizzle-orm/mysql2";
import { join } from "path";
import { existsSync } from "fs";

dotenv.config();

const PORT = process.env.PORT || 3001;
const app = express();

app.use(cors({ origin: process.env.CORS_ORIGIN || "*", credentials: true }));
app.use(express.json({ limit: "50mb" }));

async function initializeDatabase() {
  try {
    const pool = await mysql.createPool({
      host: process.env.DATABASE_HOST || "mainline.proxy.rlwy.net",
      port: parseInt(process.env.DATABASE_PORT || "56439"),
      user: process.env.DATABASE_USER || "root",
      password: process.env.DATABASE_PASSWORD || "",
      database: process.env.DATABASE_NAME || "avaliacoes_db",
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
    });
    const db = drizzle(pool);
    app.locals.db = db;
    console.log("✓ Database conectado");
    return db;
  } catch (error) {
    console.error("✗ Erro ao conectar database:", error);
    throw error;
  }
}

// tRPC
app.use(
  "/api/trpc",
  createExpressMiddleware({ router: appRouter, createContext })
);

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Serve React frontend (production)
// Tenta múltiplos caminhos para encontrar o frontend dist
const possiblePaths = [
  join(__dirname, "../frontend/dist"),           // Relative to bundled server.js
  join(__dirname, "packages/frontend/dist"),     // Relative to app root
  "/app/packages/frontend/dist",                 // Absolute path in container
  "./packages/frontend/dist",                    // Current working directory
];

let frontendDist: string | null = null;
for (const path of possiblePaths) {
  if (existsSync(path)) {
    frontendDist = path;
    console.log(`✓ Frontend dist encontrado em: ${path}`);
    break;
  }
}

if (frontendDist) {
  app.use(express.static(frontendDist));
  app.get("*", (_req, res) => {
    res.sendFile(join(frontendDist!, "index.html"));
  });
  console.log(`✓ Servindo React frontend de: ${frontendDist}`);
} else {
  console.log("⚠️  Frontend dist não encontrado, servindo apenas API");
  app.get("/", (_req, res) => {
    res.json({ message: "AvalieImob API v1.0.0" });
  });
}

async function start() {
  // Start server IMMEDIATELY so healthcheck passes
  const server = app.listen(PORT, "0.0.0.0", () => {
    console.log(`✅ Servidor rodando em http://0.0.0.0:${PORT}`);
    console.log(`📡 tRPC: http://0.0.0.0:${PORT}/api/trpc`);
    console.log(`❤️  Healthcheck: http://0.0.0.0:${PORT}/health`);
  });

  // Initialize database asynchronously (doesn't block server startup)
  try {
    await initializeDatabase();
  } catch (error) {
    console.error("✗ Erro ao conectar database (retrying...):", error);
    // Retry connection after 5 seconds
    setTimeout(() => {
      initializeDatabase().catch((err) => {
        console.error("✗ Database connection failed after retry:", err);
      });
    }, 5000);
  }

  // Graceful shutdown
  process.on("SIGTERM", () => {
    console.log("SIGTERM received, shutting down gracefully");
    server.close(() => {
      console.log("Server closed");
      process.exit(0);
    });
  });
}

start();
