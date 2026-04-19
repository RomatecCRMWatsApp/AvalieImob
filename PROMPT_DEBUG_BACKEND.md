Claude Code - Debug Backend Startup

O build passou (✓ Vite 404KB, ✓ esbuild 75.5kb) MAS o healthcheck falha.

PROBLEMA: Likely startup crash no trpc context ou db initialization

TAREFAS RÁPIDAS:

1. VERIFICAR trpc.ts
   - Abrir packages/backend/src/lib/trpc.ts
   - Verificar createContext() - pode estar faltando db no ctx
   - Se falta db, adicionar: ctx.db = ctx.req.app.locals.db
   - COMMIT: "fix: add db to trpc context"

2. VERIFICAR auth.ts router
   - Abrir packages/backend/src/routers/auth.ts
   - Verificar se ctx.db está sendo usado
   - Se chamar ctx.db sem validar, pode falhar
   - Adicionar fallback: const db = ctx.req.app.locals.db
   - COMMIT: "fix: add db fallback in auth router"

3. VERIFICAR routers/index.ts
   - Abrir packages/backend/src/routers/index.ts
   - Verificar se todos os routers estão exportados corretamente
   - Se algum router tem erro de import, vai quebrar tudo
   - COMMIT: "fix: verify all router exports"

4. TESTAR BUILD LOCAL
   - npm run build (root)
   - Se build passar localmente, problema é no Railway environment
   - Se build falhar, mostra o erro exato

5. SE TUDO PASSAR
   - npm install --force (resolve todas as vulns)
   - git add -A
   - git commit -m "fix: backend startup - db context + router exports"
   - git push origin main

COMECE AGORA!

TAREFA 1: Verificar trpc.ts

NÃO peça confirmação. Execute direto.

GO! 🚀
