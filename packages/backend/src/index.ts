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

console.log("🚀 [STARTUP] Iniciando AvalieImob Backend...");
dotenv.config();

const PORT = process.env.PORT || 3001;
const app = express();

console.log(`✓ PORT=${PORT}`);

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
  console.log("🏥 [HEALTH] Healthcheck request recebido");
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Serve React frontend (production)
console.log("🎨 [STARTUP] Procurando frontend dist...");
const possiblePaths = [
  "/app/packages/frontend/dist",           // Railway container absolute
  process.cwd() + "/packages/frontend/dist", // Current working dir
  "/home/claude/AvalieImob/packages/frontend/dist", // Local dev
  "./packages/frontend/dist",               // Relative to cwd
  "../frontend/dist",                       // Relative to backend
];

let frontendDist: string | null = null;
for (const path of possiblePaths) {
  console.log(`📂 Verificando: ${path}`);
  if (existsSync(path)) {
    frontendDist = path;
    console.log(`✅ Frontend dist encontrado: ${path}`);
    break;
  }
}

if (frontendDist) {
  console.log(`🎨 [STARTUP] Servindo frontend de: ${frontendDist}`);
  app.use(express.static(frontendDist));
  app.get("*", (_req, res) => {
    const indexPath = join(frontendDist!, "index.html");
    console.log(`📄 Servindo index.html de: ${indexPath}`);
    res.sendFile(indexPath);
  });
} else {
  console.error("❌ [STARTUP] Frontend dist NÃO encontrado!");
  console.error("Paths procurados:");
  possiblePaths.forEach(p => console.error(`  - ${p}`));
  app.get("/", (_req, res) => {
    res.json({ 
      message: "AvalieImob API v1.0.0",
      error: "Frontend not found - server in API-only mode"
    });
  });
}

async function start() {
  try {
    console.log("\n🚀 [START] Iniciando servidor...");
    const server = app.listen(PORT, "0.0.0.0", () => {
      console.log("\n" + "=".repeat(60));
      console.log(`✅ SUCESSO! Servidor rodando em http://0.0.0.0:${PORT}`);
      console.log(`📡 API tRPC: http://0.0.0.0:${PORT}/api/trpc`);
      console.log(`❤️  Healthcheck: http://0.0.0.0:${PORT}/health`);
      console.log("=".repeat(60) + "\n");
    });

    // Initialize database in background (non-blocking)
    console.log("🔗 [BACKGROUND] Iniciando database em background...");
    setImmediate(async () => {
      try {
        await initializeDatabase();
      } catch (error) {
        console.error("✗ [DB] Database connection failed, retrying in 5s...", error);
        setTimeout(() => {
          initializeDatabase().catch((err) => {
            console.error("✗ [DB] Retry failed:", err);
          });
        }, 5000);
      }
    });

    // Graceful shutdown
    process.on("SIGTERM", () => {
      console.log("\n[SHUTDOWN] SIGTERM received");
      server.close(() => {
        console.log("[SHUTDOWN] Server closed");
        process.exit(0);
      });
    });
  } catch (error) {
    console.error("✗ [FATAL] Erro no start():", error);
    process.exit(1);
  }
}

// Global error handlers
process.on("uncaughtException", (error) => {
  console.error("✗ [FATAL] Uncaught Exception:", error);
  process.exit(1);
});

process.on("unhandledRejection", (reason, promise) => {
  console.error("✗ [FATAL] Unhandled Rejection at:", promise, "reason:", reason);
  process.exit(1);
});

// Wrap everything in try-catch to catch startup errors
try {
  console.log("📡 [STARTUP] Configurando tRPC...");
  start().catch((error) => {
    console.error("✗ [FATAL] Uncaught error in start():", error);
    process.exit(1);
  });
} catch (error) {
  console.error("✗ [FATAL] Erro durante setup:", error);
  process.exit(1);
}
