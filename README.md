# RomaTec AvalieImob

Sistema completo de avaliação imobiliária, PTAM (Parecer Técnico de Avaliação Mercadológica), laudos técnicos e avaliação de garantias (imóveis urbanos, rurais, safra, rebanho, equipamentos).

**Desenvolvido por:** José Romário Pinto Bezerra — RomaTec Consultoria Total
**Website:** https://romatecavalieimob.com.br

---

## 🏗️ Stack

- **Backend:** FastAPI (Python 3.11+) + MongoDB (Motor async)
- **Frontend:** React 19 + Tailwind CSS + shadcn/ui
- **Auth:** JWT + bcrypt
- **IA:** Emergent LLM Key (Claude/GPT/Gemini) ou chaves próprias OpenAI/Google/Anthropic
- **DOCX:** python-docx (geração de laudos editavel no Word)

---

## 🚀 Como rodar localmente (desenvolvimento)

### Pré-requisitos
- Python 3.11+
- Node.js 18+ e Yarn
- MongoDB (local ou [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edite .env com suas credenciais
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend
```bash
cd frontend
yarn install
cp .env.example .env
# Edite .env com a URL do backend
yarn start
```

Acesse: http://localhost:3000

### Automacao de build e deploy (Windows)
No diretorio raiz do projeto:

```powershell
# Valida frontend + backend automaticamente
npm run auto:build

# Valida e dispara deploy via Railway CLI
npm run auto:deploy
```

Opcionalmente, para deploy em um service especifico da Railway:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\deploy-automatic.ps1 -Deploy -Service "nome-do-service"
```

### Deploy automatico no GitHub Actions (Railway)
O repositório possui o workflow [deploy-railway.yml](.github/workflows/deploy-railway.yml), que:

- roda automaticamente apos o CI passar em `main`/`master`
- pode ser executado manualmente em `Actions > Deploy Railway > Run workflow`

Para funcionar, configure este secret no GitHub:

- `RAILWAY_DEPLOY_HOOK_URL`: URL do Deploy Hook gerado na Railway para o service

Como obter na Railway:

1. Abra o service na Railway.
2. Va em Settings.
3. Copie o Deploy Hook URL.
4. Adicione em GitHub: Settings > Secrets and variables > Actions > New repository secret.

---

## 🌐 Deploy em VPS próprio (produção)

### 1. Provisione um VPS Linux (Ubuntu 22.04 recomendado)
Provedores sugeridos: HostGator VPS, DigitalOcean, Vultr, Contabo (a partir de R$ 30/mês).

### 2. Instale dependências
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm nginx certbot python3-certbot-nginx
sudo npm install -g yarn pm2
```

### 3. MongoDB
Use [MongoDB Atlas free tier](https://www.mongodb.com/cloud/atlas) (512 MB grátis) — mais simples que self-hosted.

### 4. Clone o repositório
```bash
cd /var/www
git clone https://github.com/SEU-USUARIO/romatec-avalieimob.git
cd romatec-avalieimob
```

### 5. Configure o backend
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # edite com suas credenciais reais
```

### 6. Configure o frontend e faça build
```bash
cd ../frontend
yarn install
cp .env.example .env
nano .env  # edite REACT_APP_BACKEND_URL para sua URL de produção (ex: https://api.romatecavalieimob.com.br)
yarn build
```

### 7. PM2 para manter o backend rodando
```bash
cd ../backend
pm2 start "venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001" --name romatec-backend
pm2 save
pm2 startup
```

### 8. Nginx
Crie `/etc/nginx/sites-available/romatecavalieimob`:
```nginx
server {
    server_name romatecavalieimob.com.br www.romatecavalieimob.com.br;

    # Frontend (build do React)
    location / {
        root /var/www/romatec-avalieimob/frontend/build;
        try_files $uri /index.html;
    }

    # Backend API (proxy)
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 80;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/romatecavalieimob /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

### 9. SSL com Let's Encrypt (HTTPS grátis)
```bash
sudo certbot --nginx -d romatecavalieimob.com.br -d www.romatecavalieimob.com.br
```

### 10. Aponte o DNS da HostGator
No painel da HostGator, adicione:
- **Tipo A**, Host `@`, Valor: `<IP do seu VPS>`
- **Tipo A**, Host `www`, Valor: `<IP do seu VPS>`

Aguarde propagação (1-24h) e acesse https://romatecavalieimob.com.br ✅

---

## 🔑 Variáveis de ambiente

### Backend (`backend/.env`)
Veja `backend/.env.example`.

### Frontend (`frontend/.env`)
Veja `frontend/.env.example`.

---

## 🤖 Provedores de IA suportados

O backend aceita **qualquer um** destes (em ordem de prioridade):

1. `EMERGENT_LLM_KEY` — só funciona dentro da plataforma Emergent
2. `OPENAI_API_KEY` — obtenha em https://platform.openai.com/api-keys
3. `GOOGLE_API_KEY` (Gemini) — obtenha em https://aistudio.google.com/app/apikey (tier grátis generoso)
4. `ANTHROPIC_API_KEY` (Claude) — obtenha em https://console.anthropic.com/

Para produção fora do Emergent, **recomendo Google Gemini** — tem tier gratuito e funciona muito bem em português técnico.

---

## 📖 Funcionalidades

- **Landing page** profissional com hero, features, serviços, fluxo, planos, sobre, CEO, contato
- **Autenticação JWT** com registro/login
- **Dashboard** com estatísticas e gráficos
- **CRUD de Clientes, Imóveis, Amostras de Mercado**
- **Wizard de PTAM** com 6 etapas + múltiplas áreas de impacto + exportação DOCX
- **Assistente IA** especializado em NBR 14.653
- **Planos de assinatura** (Mensal, Trimestral, Anual) — mocked até integrar Stripe
- **PWA** (instalável em celular)
- **SEO otimizado** (Open Graph, Schema.org)
- **WhatsApp flutuante** para contato direto

---

## 📝 Licença

© 2026 José Romário Pinto Bezerra — RomaTec Consultoria Total. Todos os direitos reservados.
