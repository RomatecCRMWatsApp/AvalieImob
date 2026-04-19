# 🔴 COMO VER OS LOGS REAIS NO RAILWAY

## **PASSO 1: Abrir Railway Dashboard**

1. Acesse: https://railway.app
2. Login com sua conta
3. Clique no projeto **AvalieImob**
4. Vá para **Deployments** (aba superior)

---

## **PASSO 2: Selecionar o Deploy Atual**

Você verá uma lista de deploys. O mais recente é o que está falhando:

```
🔴 FAILED    Deployment 2026-04-19 03:32:55
             [Server] Deploy failed - Healthcheck timeout
```

Clique nele para expandir.

---

## **PASSO 3: Ver os Logs**

Dentro do deploy, você verá 2 abas:

### ✅ **Build Logs** (sempre passa)
```
[inf] Build time: 51.72 seconds
[inf] === Successfully Built! ===
```

### 🔴 **Runtime Logs** (AQUI ESTÁ O ERRO!)

Clique na aba **"Logs"** ou **"Runtime"**

Você vai ver algo como:

```
Error: Cannot find module '@trpc/server'
```

OU

```
Error: connect ECONNREFUSED 127.0.0.1:3306
```

OU

```
Error: ENOENT: no such file or directory...
```

**COPIE ESSE ERRO E MANDE PARA MIM!**

---

## **PASSO 4 (Alternativa): Via CLI**

Se preferir via terminal:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Connect ao projeto
railway link

# Ver logs (últimos 100 linhas)
railway logs --tail 100

# Ver logs em tempo real
railway logs -f
```

---

## **O QUE PROCURAR NOS LOGS:**

❌ **Error:**
```
Cannot find module
ECONNREFUSED
ENOENT
TypeError
SyntaxError
```

✅ **Sucesso:**
```
✅ Servidor rodando em http://0.0.0.0:3000
✓ Database conectado com sucesso
```

---

## **IMPORTANTE:**

**NÃO É** o Build Log que importa (esse sempre passa).

**É** o Runtime Log (stderr do container quando está rodando).

É lá que vamos ver por que o `node server.js` está crashando!

---

**Manda print do erro que você encontrar nos Runtime Logs!** 📸
