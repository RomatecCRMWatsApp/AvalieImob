# ✅ AvalieImob Deploy Checklist

**Status:** Aguardando healthcheck passar no Railway

---

## 🟢 FASE 1: Deploy Infrastructure (CURRENT)

- [ ] Railway build passa (<2 min)
- [ ] Healthcheck responde em <1s
- [ ] Server.js bundled 76kb+
- [ ] Frontend dist 404kb compilado
- [ ] Deployment successful badge 🟢

---

## 🔵 FASE 2: Backend Health Check

**URL:** `https://avaliemob-production.up.railway.app/health`

```bash
curl -X GET https://avaliemob-production.up.railway.app/health
# Expected: { "status": "ok" }
```

- [ ] GET /health → 200 OK
- [ ] Response time <100ms
- [ ] No 500 errors

---

## 🟣 FASE 3: API Testing

### Auth Endpoints
```bash
# Register
curl -X POST https://avaliemob-production.up.railway.app/api/trpc/auth.register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@romatec.com","password":"Test@123"}'

# Login
curl -X POST https://avaliemob-production.up.railway.app/api/trpc/auth.login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@romatec.com","password":"Test@123"}'
```

- [ ] Register works
- [ ] Login works
- [ ] JWT token returned
- [ ] Token valid for 24h

### Cliente Router
```bash
# Create client
curl -X POST https://avaliemob-production.up.railway.app/api/trpc/cliente.create \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"nome":"Cliente Test","cpf":"12345678901","email":"cliente@test.com"}'
```

- [ ] Cliente CRUD works
- [ ] Database writes successful
- [ ] Returns correct schema

### Imovel Router
- [ ] Create imóvel works
- [ ] List imóveis works
- [ ] Update imóvel works
- [ ] Delete imóvel works

### Avaliacao Router
- [ ] Create avaliação works
- [ ] List avaliações works
- [ ] Calculate PTAM works

---

## 🟠 FASE 4: Frontend Load Test

**URL:** `https://avaliemob-production.up.railway.app/`

- [ ] Page loads <2s
- [ ] No console errors
- [ ] Login form renders
- [ ] Dark mode verde active
- [ ] Logo displays correctly
- [ ] All SVG icons render

---

## 🟡 FASE 5: Database Connectivity

```sql
-- Test MySQL connection
SELECT DATABASE();
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM clientes;
SELECT COUNT(*) FROM imoveis;
```

- [ ] Database connected
- [ ] Tables created
- [ ] Drizzle ORM working
- [ ] Queries responding <500ms

---

## 🔴 FASE 6: Error Handling

### Test 404
```bash
curl -X GET https://avaliemob-production.up.railway.app/api/invalid
# Expected: 404
```

- [ ] 404 errors handled
- [ ] No stack traces exposed
- [ ] Proper error messages

### Test 500
```bash
# Try to access protected route without token
curl -X GET https://avaliemob-production.up.railway.app/api/trpc/cliente.list
# Expected: 401 Unauthorized
```

- [ ] Auth errors correct (401/403)
- [ ] Validation errors clear
- [ ] No sensitive data exposed

---

## 🟢 FASE 7: Performance Metrics

- [ ] Page load time <2s
- [ ] API response <200ms (avg)
- [ ] Bundle size: 404kb (frontend), 76kb (backend)
- [ ] Gzip: 111kb (frontend)

---

## 📊 FINAL STATUS

```
🟢 Infrastructure: READY
🟢 Backend: READY
🟢 Frontend: READY
🟢 Database: READY
🟢 API: READY
🟢 Production: LIVE
```

---

**Next:** Após passar, iniciar fase de features:
1. ✅ Whisper audio transcription
2. ✅ PTAM DOCX generator
3. ✅ Mercado Pago integration
4. ✅ Email notifications
