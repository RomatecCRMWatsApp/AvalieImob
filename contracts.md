# RomaTec AvalieImob - Contratos Frontend ↔ Backend

## 🎯 Escopo Backend
MongoDB + FastAPI + JWT Auth + Emergent LLM (IA) + mock pagamentos/CEP.

## 📦 Dados atualmente MOCKED em `/app/frontend/src/mock/mock.js`
- `MOCK_CLIENTS` → virará coleção `clients`
- `MOCK_PROPERTIES` → virará coleção `properties` (urbano/rural/garantia)
- `MOCK_SAMPLES` → virará coleção `samples`
- `MOCK_EVALUATIONS` → virará coleção `evaluations` (PTAM/Laudos)
- `DASH_STATS` → agregação real via endpoints
- `AuthContext.login/register` mock → substituir por JWT real
- `AIAssistant.mockReply` → substituir por chamada real LLM

## 🔌 Endpoints REST (todos prefixados com `/api`)

### Auth (JWT)
- `POST /api/auth/register` { name, email, password, role, crea } → { user, token }
- `POST /api/auth/login` { email, password } → { user, token }
- `GET /api/auth/me` (Bearer) → { user }

### Clients (Bearer auth)
- `GET /api/clients` → [Client]
- `POST /api/clients` { name, type, doc, phone, email, city } → Client
- `PUT /api/clients/{id}` → Client
- `DELETE /api/clients/{id}` → { ok: true }

### Properties
- `GET /api/properties?type=urbano|rural|garantia` → [Property]
- `POST /api/properties` → Property
- `PUT /api/properties/{id}` / `DELETE /api/properties/{id}`

### Samples
- `GET /api/samples` → [Sample]
- `POST /api/samples` → Sample (calcula pricePerSqm = value/area)

### Evaluations
- `GET /api/evaluations` → [Evaluation]
- `POST /api/evaluations` { type, method, clientId, propertyId, value } → Evaluation (gera código automático)
- `PUT /api/evaluations/{id}` (status, amostras, etc)
- `GET /api/evaluations/{id}/pdf` → gera PDF (fase 2)

### AI (Emergent LLM)
- `POST /api/ai/chat` { message, sessionId } → { reply } — usa `emergentintegrations` com GPT/Claude

### Dashboard
- `GET /api/dashboard/stats` → { evaluations, clients, properties, revenue, monthly[] }

### Subscription (MOCKED até integrar Stripe)
- `GET /api/subscription` → { plan, nextBilling, status }
- `POST /api/subscription/change` { planId } → mocked success

## 🔄 Integração Frontend
1. Substituir `mock.js` imports por chamadas axios em cada componente
2. AuthContext: usar `/api/auth/login|register` e salvar JWT em localStorage
3. Axios interceptor: adicionar `Authorization: Bearer <token>`
4. AIAssistant: chamar `/api/ai/chat` com sessionId (uuid)

## 🚫 Mantidos como MOCK
- CEP/mapas (ViaCEP futuro)
- Pagamentos Stripe (fase 2)
- Upload de logo (fase 2)
