import express from "express";
import cors from "cors";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { createContext } from "../lib/trpc";
import { appRouter } from "../routers";
import dotenv from "dotenv";
import mysql from "mysql2/promise";
import { drizzle } from "drizzle-orm/mysql2";

dotenv.config();

const PORT = process.env.PORT || 3001;
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Inicializar banco de dados
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

    // Armazenar db no contexto Express
    app.locals.db = db;

    console.log("✓ Database conectado");
    return db;
  } catch (error) {
    console.error("✗ Erro ao conectar database:", error);
    throw error;
  }
}

// tRPC middleware
app.use(
  "/api/trpc",
  createExpressMiddleware({
    router: appRouter,
    createContext,
  })
);

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Root endpoint
app.get("/", (req, res) => {
  res.json({ message: "AvalieImob API v1.0.0" });
});

// Inicializar servidor
async function start() {
  try {
    await initializeDatabase();

    app.listen(PORT, () => {
      console.log(`🚀 Server rodando em http://localhost:${PORT}`);
      console.log(`📡 tRPC API: http://localhost:${PORT}/api/trpc`);
    });
  } catch (error) {
    console.error("✗ Erro ao iniciar servidor:", error);
    process.exit(1);
  }
}

start();
