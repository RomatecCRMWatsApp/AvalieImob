# AvalieImob - Romatec Avaliação Imobiliária

Sistema completo de PTAM (Parecer Técnico de Avaliação Mercadológica) com transcrição de áudio, métodos comparativo e evolutivo, e emissão automática de laudos em PDF/DOCX.

## 🚀 Stack Tecnológico

- **Backend:** Node.js + tRPC + Express
- **Frontend:** React + TypeScript + Tailwind CSS (em desenvolvimento)
- **Banco:** MySQL + Drizzle ORM
- **Hosting:** Railway
- **Transcrição:** OpenAI Whisper
- **Documentos:** docx library

## 📋 Funcionalidades

### ✅ Implementado (Fase 1)

- [x] Schema MySQL completo com Drizzle ORM
- [x] Autenticação JWT com bcryptjs
- [x] Routers tRPC:
  - [x] `auth` - Login/Registro
  - [x] `cliente` - CRUD de clientes
  - [x] `imovel` - CRUD de imóveis (urbano/rural/misto)
  - [x] `amostra` - Dados comparativos dinâmicos
  - [x] `avaliacao` - Gerenciamento de PTAMs
  - [x] `audio` - Upload e transcrição com Whisper
  - [x] `calculo` - Método Comparativo + Evolutivo (ABNT NBR 14.653)
  - [x] `ptam` - Geração automática de DOCX
- [x] Validações Zod em todos os endpoints
- [x] Suporte a múltiplas amostras e estatísticas

### 🔄 Em Desenvolvimento (Fase 2)

- [ ] Frontend React (login, dashboard, forms)
- [ ] Geração de PDF (usando pdfkit)
- [ ] Portal de avaliadores público
- [ ] Email com SendGrid
- [ ] Pagamento com Mercado Pago

### 📅 Planejado (Fase 3)

- [ ] Assinatura digital com certificado
- [ ] Upload para S3/Cloudinary
- [ ] Portal para clientes visualizarem PTAM
- [ ] Sistema de ratings e avaliações

## 🛠️ Setup Local

### Pré-requisitos

- Node.js 18+
- npm ou yarn
- MySQL 8.0+

### Instalação

```bash
git clone https://github.com/RomatecCRMWatsApp/AvalieImob.git
cd AvalieImob
npm install
cp .env.example .env
npm run db:push
npm run dev
```

## 💚 Branding

- **Cores:** Verde (#228B22) + Ouro
- **Logo:** Romatec AVALIEIMOB
- **UI:** Dark mode premium

---

**Desenvolvido para o mercado imobiliário brasileiro** 🇧🇷
