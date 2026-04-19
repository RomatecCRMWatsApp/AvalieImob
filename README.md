# AvalieImob 🏢

## Sistema de Avaliação Imobiliária com Transcrição de Áudio

**Romatec Consultoria Imobiliária**

Um SaaS completo para emissão de **PTAM (Parecer Técnico de Avaliação Mercadológica)** e **Laudos Imobiliários** com suporte a:

- ✅ Transcrição de áudio em tempo real (OpenAI Whisper)
- ✅ Cálculos automáticos (Método Comparativo + Evolutivo ABNT NBR 14.653)
- ✅ Geração de PTAM em PDF + DOCX editável
- ✅ Portal de Avaliadores
- ✅ Autenticação JWT + Subscriptions (Mercado Pago)
- ✅ Dark Mode Verde Premium (Romatec Branding)

---

## 📋 Stack Tecnológico

### Backend
- **Node.js** + TypeScript
- **tRPC** (RPC type-safe)
- **Express** (servidor HTTP)
- **Drizzle ORM** (MySQL)
- **OpenAI Whisper** (transcrição de áudio)
- **JWT** (autenticação)
- **bcryptjs** (hash de senha)

### Frontend
- **React 18** + TypeScript
- **Vite** (build tool)
- **Tailwind CSS** (styling)
- **tRPC Client** (chamadas RPC)
- **React Router** (navegação)

### Banco de Dados
- **MySQL** no Railway
- **Drizzle Kit** (migrations)

---

## 🗄️ Estrutura do Projeto

```
AvalieImob/
├── packages/
│   ├── db/                    # Schema Drizzle + Migrations
│   │   ├── schema.ts          # Tabelas principais
│   │   └── drizzle.config.ts  # Configuração Drizzle
│   ├── backend/               # API tRPC + Express
│   │   ├── src/
│   │   │   ├── routers/
│   │   │   │   ├── auth.ts    # Autenticação
│   │   │   │   ├── cliente.ts # Clientes (CRUD)
│   │   │   │   ├── imovel.ts  # Imóveis (CRUD)
│   │   │   │   ├── amostra.ts # Amostras comparativas
│   │   │   │   ├── avaliacao.ts # PTAMs em andamento
│   │   │   │   ├── audio.ts   # Transcrição Whisper
│   │   │   │   ├── calculo.ts # Cálculos ABNT
│   │   │   │   └── index.ts   # Root router
│   │   │   ├── lib/trpc.ts    # Setup tRPC + contexto
│   │   │   └── index.ts       # Servidor principal
│   │   └── package.json
│   └── frontend/              # React + Tailwind
│       └── package.json
├── .env.example               # Variáveis de ambiente
├── tsconfig.json              # TypeScript config
└── package.json               # Monorepo root
```

---

## 📊 Schema do Banco de Dados

### Tabelas Principais

| Tabela | Descrição |
|--------|-----------|
| `users` | Avaliadores, clientes, admin |
| `subscriptions` | Planos (mensal/trimestral/anual) |
| `clientes` | Solicitantes de PTAM |
| `imoveis` | Cadastro de imóveis |
| `amostras` | Dados comparativos de mercado |
| `avaliacoes` | PTAMs em andamento |
| `audio_transcricoes` | Transcrições Whisper |
| `calculos` | Cálculos comparativo/evolutivo |
| `ptam_emitidos` | Histórico de PTAMs (PDF + DOCX) |
| `laudos` | Laudos complementares |
| `avaliadores_publico` | Portal de avaliadores |
| `ratings` | Avaliações de clientes |

---

## 🚀 Como Usar

### 1. Clonar o Repositório

```bash
git clone https://github.com/RomatecCRMWatsApp/AvalieImob.git
cd AvalieImob
```

### 2. Instalar Dependências

```bash
npm install
```

### 3. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
# Editar .env com suas credenciais
```

**Variáveis necessárias:**

```env
# Database
DATABASE_HOST=mainline.proxy.rlwy.net
DATABASE_PORT=56439
DATABASE_USER=root
DATABASE_PASSWORD=mzhpVamVFtfKDLkQtfxGnjnlVLrVEaAf
DATABASE_NAME=avaliacoes_db

# JWT
JWT_SECRET=sua-chave-secreta-minimo-32-caracteres

# OpenAI (Whisper)
OPENAI_API_KEY=sk-...

# Mercado Pago
MERCADO_PAGO_ACCESS_TOKEN=APP_USR_...
MERCADO_PAGO_PUBLIC_KEY=APP_USR_...

# URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:3001
```

### 4. Criar/Migrar Banco de Dados

```bash
npm run db:push
```

### 5. Iniciar em Desenvolvimento

```bash
npm run dev
```

- **Backend**: http://localhost:3001
- **Frontend**: http://localhost:5173
- **tRPC API**: http://localhost:3001/api/trpc

---

## 📡 API tRPC Endpoints

### Auth
- `auth.registro` - Criar conta (email, senha, nome)
- `auth.login` - Login (email, senha)
- `auth.me` - Dados do usuário logado

### Cliente
- `cliente.criar` - Criar cliente
- `cliente.listar` - Listar clientes
- `cliente.obter` - Obter cliente por ID
- `cliente.atualizar` - Atualizar cliente
- `cliente.deletar` - Deletar cliente

### Imóvel
- `imovel.criar` - Criar imóvel
- `imovel.listar` - Listar imóveis
- `imovel.obter` - Obter imóvel
- `imovel.atualizar` - Atualizar imóvel
- `imovel.deletar` - Deletar imóvel

### Amostra
- `amostra.criar` - Criar amostra comparativa
- `amostra.listarPorAvaliacao` - Listar amostras de uma avaliação
- `amostra.atualizar` - Atualizar amostra
- `amostra.deletar` - Deletar amostra

### Avaliação
- `avaliacao.criar` - Criar PTAM
- `avaliacao.listar` - Listar PTAMs
- `avaliacao.obter` - Obter PTAM
- `avaliacao.atualizar` - Atualizar PTAM
- `avaliacao.deletar` - Deletar PTAM

### Áudio
- `audio.transcrever` - Upload + transcrição Whisper
- `audio.listarPorAvaliacao` - Listar áudios de uma avaliação
- `audio.deletar` - Deletar áudio

### Cálculo
- `calculo.calcularComparativo` - Método Comparativo (ABNT)
- `calculo.calcularEvolutivo` - Método Evolutivo (ABNT)
- `calculo.listarPorAvaliacao` - Listar cálculos
- `calculo.deletar` - Deletar cálculo

---

## 🔐 Autenticação

O sistema usa **JWT (JSON Web Tokens)** para autenticação:

1. Usuário faz login com email/senha
2. Backend retorna token JWT válido por 30 dias
3. Token deve ser enviado no header: `Authorization: Bearer <token>`
4. tRPC valida automaticamente em procedimentos protegidos

---

## 💰 Modelo de Preço

Planos SaaS:

| Plano | Duração | Preço |
|-------|---------|-------|
| Mensal | 30 dias | R$ [A DEFINIR] |
| Trimestral | 90 dias | R$ [A DEFINIR] (-10%) |
| Anual | 365 dias | R$ [A DEFINIR] (-20%) |

**Pagamento:** Mercado Pago (cartão, Pix, boleto)

---

## 🎨 Design System

### Cores (Dark Mode Verde Premium)
- **Primária:** `#22c55e` (Verde)
- **Secundária:** `#15803d` (Verde Escuro)
- **Background:** `#0f172a` (Azul Escuro)
- **Text:** `#f1f5f9` (Branco)

### Tipografia
- **Font:** Inter, sans-serif
- **Heading:** Bold
- **Body:** Regular

---

## 📝 Métodos de Cálculo

### Método Comparativo Direto (ABNT NBR 14.653)

Usa amostras de mercado para:
- Calcular **média** dos valores
- **Desvio padrão** da amostra
- **Intervalo de confiança** (95%)
- **Coeficiente de variação**

Fórmula:
```
Valor Unitário = Média das Amostras
Valor Total = Valor Unitário × Área Impactada
```

### Método Evolutivo (ABNT NBR 14.653)

Baseado em componentes:

```
VT = (VTerreno + VBenfeitorias × (1 - Depreciação)) × FatorLocalizacao
```

---

## 🔧 Deploy no Railway

### 1. Conectar ao Railway

```bash
railway link
```

### 2. Configurar Variáveis de Ambiente

```bash
railway env add DATABASE_HOST mainline.proxy.rlwy.net
railway env add DATABASE_PASSWORD mzhpVamVFtfKDLkQtfxGnjnlVLrVEaAf
# ... adicionar outras vars
```

### 3. Deploy

```bash
git push
# Railway faz deploy automaticamente
```

---

## 📚 Documentação Adicional

- [ABNT NBR 14.653](https://www.abnt.org.br/) - Norma Técnica de Avaliação
- [OpenAI Whisper](https://openai.com/research/whisper) - Speech-to-Text
- [tRPC Documentation](https://trpc.io)
- [Drizzle ORM](https://orm.drizzle.team)

---

## 🤝 Contribuidores

- **José Romário** - CEO Romatec
- **Desenvolvimento** - tRPC + Node.js

---

## 📄 Licença

Proprietary - Romatec Consultoria Imobiliária

---

## 📞 Suporte

Email: dev@romatec.com.br
WhatsApp: +55 (98) 99XXX-XXXX

