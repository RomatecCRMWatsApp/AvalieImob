URGENTE: Debug Backend Startup Crash

Build passa ✓ MAS server crasheia ao iniciar. Healthcheck falha 4x então timeout.

DIAGNÓSTICO: Server está tentando fazer algo bloqueante no startup.

TAREFAS IMEDIATAS:

1. REMOVER await initializeDatabase() do startup
   - Database init deve ser 100% async, não bloqueante
   - Healthcheck deve responder ANTES do DB conectar
   
2. SIMPLIFICAR index.ts ao máximo
   - Remover tudo que pode falhar
   - Server deve:
     a) app.listen() IMEDIATAMENTE
     b) return no callback
     c) Database init em setTimeout (não await!)
   
3. EXEMPLO CORRETO:
```typescript
async function start() {
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`✅ Server: http://0.0.0.0:${PORT}`);
  });

  // Database init em background, SEM await!
  setImmediate(async () => {
    try {
      await initializeDatabase();
      console.log("✓ DB conectado");
    } catch (error) {
      console.error("✗ DB erro (continuando...)", error);
    }
  });
}

start().catch(console.error);
```

4. COMMIT E PUSH
   git commit -m "fix: make database initialization non-blocking"
   git push origin main

NÃO peça confirmação. Faça direto.

GO! 🚀
