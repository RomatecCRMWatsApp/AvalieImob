# CLAUDE.md — Instruções permanentes para o Claude Code

## ⚠️ Versionamento — OBRIGATÓRIO a cada atualização/deploy

**SEMPRE que fizer qualquer alteração que vá para a `main` (deploy), ANTES do commit:**

1. **Incrementar `frontend/build-number.txt`** (+1 em relação ao valor atual). Este é o passo
   que faz o badge de versão mudar.
2. A versão exibida é `v{MAJOR}.{MINOR}.{build}`, gerada por `frontend/scripts/genversion.js`
   (prebuild) em `frontend/src/version.js`.
3. **Por que isso é necessário:** no build do Docker/Railway o `.git` NÃO existe
   (`.dockerignore` exclui `**/.git`), então `git rev-list` falha e o número vem **só** do
   `build-number.txt`. Um `git push` direto **não incrementa nada** — só o `DEPLOY.bat` ou
   esta regra incrementam. Se esquecer, o badge fica travado (ex.: ficou preso em v1.0.350).
4. **Subir o MINOR** (constante em `genversion.js`) em marcos/releases relevantes.
5. Após bumpar, rodar `node frontend/scripts/genversion.js` para regenerar o `version.js`
   (opcional — o Railway regenera no prebuild).
6. Registrar a atualização também no Obsidian (ver seção abaixo), nota de releases/changelog.

**Estado atual: v1.3.726** (MAJOR=1, MINOR=3) — release: NOVO módulo Propostas de Consultoria (independente, motor port FIEL da ZAYRA). Backend: services/pricing/ (params.py com tabelas SM/CUB/ART/TJMA/SERO/honorários, tjma.py tabelas 16.3/16.9 + calcular_emolumentos, sero.py INSS aferição indireta, prefeitura.py, averbacao.py engine residencial/comercial, __init__.py dispatcher + CATALOGO_CONSULTORIA 11 tipos com status disponível/em-breve). models/proposta.py (Mongo, extra=allow). routes/propostas.py (GET /propostas/catalogo, POST /preview, POST/GET/PUT/DELETE, numeração PROP-AAAA-NNNN via counters). Frontend: propostasAPI, rotas /dashboard/propostas[/nova/:subtipo|/:id], link "Propostas" no Sidebar, PropostasList (catálogo tema Romatec + lista) e PropostaForm (averbação com preview ao vivo via /preview). VERIFICADO: cálculo da averbação bate exatamente com averbacao.test.ts da ZAYRA. PENDENTE: engines georref/demarcação/desmembramento/remembramento/retificação/PTAM/projeto executivo/adicional de campo (mostram "Em breve") + PDF da proposta. Release anterior abaixo:

**v1.3.725** (MAJOR=1, MINOR=3) — release: restyle da página Kit TVI no tema Romatec (100% frontend, sem backend). ModelCard.jsx: ícones lucide monocromáticos por categoria (ShieldCheck/FileCheck2/HardHat/Scale/ClipboardList/KeyRound/TreePine/Store/Wrench/Layers, fallback ClipboardList), disco dourado #C9A84C, eyebrow categoria, título line-clamp-2, hover translateY + ChevronRight, focus ring, dark/light. TVIList.jsx: subtítulo dinâmico ({n} de {total}/{total} disponíveis), CTA dourado "Iniciar nova vistoria", busca dark/light com ring dourado, pills com contador por categoria e ativo dourado (aria-pressed), empty state (SearchX + Limpar busca), 8 skeletons com shimmer. Emojis removidos. Release anterior abaixo:

**v1.3.707** (MAJOR=1, MINOR=3) — release: fix contador de visualizações do link no card PTAM — model Ptam ganhou link_views/link_views_first/link_views_last/link_sends/link_last_sent/link_last_canal/link_last_destinatario/link_gerado_em (antes não declarados → response_model=Ptam os descartava e o card mostrava 👁 0 mesmo com views registradas; o modal Controle do Link lia o doc direto e mostrava o número certo). Release anterior abaixo:

**v1.3.706** (MAJOR=1, MINOR=3) — release: Kit TVI mostra o catálogo de modelos direto na página (TVIList.jsx incorpora useModels + ModelCard + tabs de categoria + busca de modelo + create on select), com "Minhas vistorias" acima quando houver. Antes os modelos só apareciam ao clicar em "Nova Vistoria" (removido o botão redundante; rota /tvi/nova mantida). Release anterior abaixo:

**v1.3.705** (MAJOR=1, MINOR=3) — release: (1) fotos por aba na Averbação (PhotoUploader nas abas Áreas e Sistemas/NC; tviAPI.listPhotos). (2) Parte B — Migração Vistoria→PTAM: backend services/vistoria_memorial.py (gera memorial de caracterização, exclui metodologia avaliatória); routes/tvi.py POST /tvi/vistoria/{id}/memorial; routes/ptam.py GET /ptam/{id}/vistorias-compativeis (ordena mesma matrícula/endereço) e POST /ptam/{id}/importar-vistoria/{vid} (memorial substituir/anexar em imovel_caracteristicas_adicionais + fotos idempotentes por origem_foto_id em fotos_imovel; 409 se assinado; 404 cross-user; vínculo bidirecional vistoria.vinculos + ptam.vistoria_origem_id; audit log). Frontend ImportarVistoriaModal.jsx (3 passos) + botão "Importar de Vistoria" no StepCaracterizacao; ptamExtrasAPI.vistoriasCompativeis/importarVistoria. Release anterior abaixo:

**v1.3.704** (MAJOR=1, MINOR=3) — release: Vistoria de Obra para Averbação (Fase 2 — frontend). NOVO componente tvi/VistoriaAverbacaoForm.jsx (6 abas: Dados/Áreas/Etapas/Sistemas/Documentos/Parecer; chips, sliders 0-100 passo 5, segmentado C/NC/NA e OK/PEND/NA, card de divergência ao vivo 3 estados, conclusão geral ponderada ao vivo; catálogos via tviAPI.catalogosAverbacao; autosave debounce 1,5s; export PDF/DOCX). TVIForm.jsx detecta model.modelo_especial==='averbacao' (ou id TVI-AVERB / tipo obra_averbacao) e renderiza o form próprio. PENDENTE: Parte B (import Vistoria→PTAM) e fotos por aba (PhotoGrid) na averbação. Release anterior abaixo:

**v1.3.703** (MAJOR=1, MINOR=3) — release: Vistoria de Obra para Averbação (Fase 1 — backend + PDF/DOCX, estende o Kit TVI sem módulo paralelo). NOVO: models/averbacao.py (DadosAverbacao/ConfrontoAreas/EtapaObra/SistemaAverbacao/DocumentoAverbacao + catálogos ETAPAS_OBRA/DOCS_AVERBACAO/SISTEMAS_AVERBACAO/PATOLOGIAS + TOLERANCIA_DIVERGENCIA + calcular_averbacao + MODELO_AVERBACAO + ensure_modelo_averbacao); campo averbacao opcional em VistoriaBase (tvi.py). services/vistoria_averbacao_relatorio.py (7 seções, frases por faixa, pendências impeditivas). pdf/vistoria_averbacao_pdf.py (3 quadros coloridos + galeria GPS + TA_JUSTIFY, reusa _TVIDoc). docx_gen/vistoria_averbacao_docx.py. routes/tvi.py: GET /tvi/catalogos/averbacao, POST /tvi/vistoria/{id}/relatorio, cálculo server-side no create/PUT, export PDF/DOCX roteado p/ gerador de averbação quando há averbacao, _resolve_photos_bytes (data-URI+bytes). server.py startup garante o modelo (idempotente). tviAPI: catalogosAverbacao/gerarRelatorio. PENDENTE Fase 2: frontend (form 6 abas) e Parte B (import Vistoria→PTAM). Release anterior abaixo:

**v1.3.702** (MAJOR=1, MINOR=3) — release: botão "Atualizar" no topo quando há nova versão — genversion.js publica public/version.json (build+versão); TopBar tem useUpdateAvailable (consulta /version.json?_=ts sem cache a cada 60s + no foco) e, se build publicado > BUILD_NUMBER carregado, mostra botão dourado "Atualizar" (aplicarAtualizacao: unregister SW + limpa caches + reload). Release anterior abaixo:

**v1.3.701** (MAJOR=1, MINOR=3) — release: abas laterais flutuantes uniformes — a aba "Roma_IA" (RomaIAWidget, estado oculto) agora usa o mesmo tamanho/tipografia das abas CNPJ/CPF (consulta-fab) e FOTOS (fotos-fab): text-xs/bold/uppercase, tracking 1.5px, padding 14px/7px, rounded-l-10px, rotate(180deg). Release anterior abaixo:

**v1.3.690** (MAJOR=1, MINOR=3) — release: exclusão de usuários no painel admin — backend admin.py ganha DELETE /admin/users/{id} (bloqueia excluir a própria conta) e POST /admin/users/excluir-inativos (apaga todos sem plan_status=active, exceto o próprio); adminAPI.excluirUsuario/excluirInativos; UsuariosAdmin.jsx com botão "Excluir inativos" + lixeira por linha (protege a própria conta). Release anterior abaixo:

**v1.3.689** (MAJOR=1, MINOR=3) — release: painel admin de Usuários — nova página /dashboard/admin/usuarios (UsuariosAdmin.jsx) consumindo GET /admin/users (já existia): resumo (cadastrados, assinaturas ativas, inativas, admins) + tabela com filtro/busca; adminAPI no api.js; link "Usuários" no Sidebar (admin/owner/ceo); DashboardHero ganha bloco só-admin com Usuários + Assinaturas ativas (clica e vai pra página). Release anterior abaixo:

**v1.3.688** (MAJOR=1, MINOR=3) — release: mensagem do cupom (WhatsApp) — (1) volta o valor "Economia de R$ X,XX na primeira cobrança!" no template do backend (montar_mensagem_whatsapp), igual à prévia; (2) nova linha "📧 No cadastro, use o seu e-mail: {email}" quando o cupom tem email_destinatario — backend + prévia (buildMensagem) alinhados. Release anterior abaixo:

**v1.3.687** (MAJOR=1, MINOR=3) — release: (1) white-label recibo_zayra.py — emitente do recibo do card PTAM agora vem 100% do perfil/user do avaliador logado (via resolver_dados_avaliador), com fallback Romatec SOMENTE para a conta OWNER_EMAIL (não vaza dados da Romatec p/ outros usuários); bloco bancário só renderiza se houver dados. (2) Cupons: botão WhatsApp agora abre prompt do número (pré-preenchido) p/ enviar a um nº de teste antes do cliente. (3) Cupons ganham Editar (PUT /cupons/{id}), Revalidar (PUT /cupons/{id}/revalidar, reativa+nova validade) e Excluir (DELETE /cupons/{id}); UI com Pencil/RefreshCw/Trash2. Release anterior abaixo:

**v1.3.686** (MAJOR=1, MINOR=3) — release: fix backend admin gate — dependencies.get_admin_user e o bypass de admin em get_active_subscriber agora são case-insensitive e aceitam admin/owner/ceo (antes role=="admin" exato barrava o CEO com role "Admin" → 403 "Acesso restrito" em Cupons). Release anterior abaixo:

**v1.3.666** (MAJOR=1, MINOR=3) — release: fix menu Cupons Promo — Sidebar.jsx isAdmin agora é case-insensitive e aceita admin/owner/ceo (antes exigia role==='admin' exato, e o CEO tem role "Admin", então o link ficava escondido). Rota /dashboard/admin/cupons já existia. Release anterior abaixo:

**v1.3.665** (MAJOR=1, MINOR=3) — release: botão "Visualizar" no card de recibo (abre o PDF inline) substitui o antigo "PDF" (download do recibo sem assinatura). Backend GET /recibos/{id}/pdf passa a servir o PDF ASSINADO (com anexos embutidos) quando icp_status=assinado, senão o recibo+anexos. Release anterior abaixo:

**v1.3.664** (MAJOR=1, MINOR=3) — release: WhatsApp do recibo envia o PDF ASSINADO quando o recibo está assinado (icp_status=assinado) — usa routes.assinatura._load_assinatura_bytes (R2/inline) em vez de gerar um PDF novo sem assinatura; como o assinado já embute os anexos, não reenvia os anexos avulsos. Release anterior abaixo:

**v1.3.663** (MAJOR=1, MINOR=3) — release: diagnóstico do 502 no envio WhatsApp do recibo — enviar_whatsapp passa a logar tipo da exceção + traceback (exc_info) e o detalhe HTTP agora inclui o nome da exceção mesmo quando str(e) vem vazio (típico de timeout/conexão httpx com a Z-API). Release anterior abaixo:

**v1.3.662** (MAJOR=1, MINOR=3) — release: PDF ASSINADO do recibo agora inclui os anexos — assinatura.py _gerar_pdf(tipo="recibo") mescla anexar_anexos_ao_pdf antes de assinar, então o preparar (páginas do posicionador) e o "Baixar PDF Assinado" já saem com os anexos. Release anterior abaixo:

**v1.3.661** (MAJOR=1, MINOR=3) — release: recibo assinado reflete no card do PTAM — backend assinatura.py (_propagar_recibo_assinado) seta recibo_assinado=True no PTAM vinculado (via recibo.ptam_id) ao concluir ICP nos endpoints /icp/{tipo}/{id}/assinar e /posicionado; model Ptam ganha recibo_id, recibo_assinado, recibo_assinado_em; PtamList mostra botão verde "✓ Recibo Assinado" (abre o recibo na aba Recibos). Release anterior abaixo:

**v1.3.660** (MAJOR=1, MINOR=3) — release: 3 fixes no recibo — (1) PDF baixado (GET /recibos/{id}/pdf) agora mescla os anexos ao final via services.recibo_anexos.anexar_anexos_ao_pdf (PDF append + imagens viram página A4, usa pypdf+PIL); (2) RecibosList limpa HTML cru da descrição no card (stripHtml); (3) enviarWA sempre abre prompt pré-preenchido p/ inserir/confirmar o número de WhatsApp (antes só pedia se vazio). Histórico abaixo:

**v1.3.659** (MAJOR=1, MINOR=3) — release: link público do laudo vinculado ao recibo (3 pontos) — (1) gerar_recibo_ptam gera o link_publico do PTAM automaticamente se não existir e grava em recibo.ptam_link; (2) ReciboWizard mostra campo read-only "Link do laudo" com botão Copiar; (3) legenda_recibo (WhatsApp) inclui o ptam_link + faz strip de HTML do servico/descricao. Histórico abaixo:

**v1.3.658** (MAJOR=1, MINOR=3) — release: bloco de assinatura do recibo (recibo_pdf.py) passa a usar a qualificação COMPLETA do avaliador via utils.avaliador.resolver_dados_avaliador (mesma fonte do PTAM): nome em maiúsculas + "Avaliador — CRECI/MA · CNAI · CFT/MA · ..." + endereço completo + telefone (substitui o antigo cargo "Admin" + 1º registro). Histórico abaixo:

**v1.3.657** (MAJOR=1, MINOR=3) — release: recibo ganha paridade com PTAM (tudo aditivo) — (A) campo Descrição com RichTextEditor + botão "Aperfeiçoar com IA" (aiAPI.chat) no ReciboWizard; recibo_pdf limpa HTML do descricao (_strip_html). (B) gerar_recibo_ptam grava ptam_link (link público do laudo) no recibo, exibido no PDF. (C) RecibosList ganha botão "Posicionar" abrindo AssinaturaPosicionadaModal tipo="recibo" (mesmo retângulo do PTAM; backend assinatura.py já suporta recibo). Histórico abaixo:

**v1.3.656** (MAJOR=1, MINOR=3) — release: recibo gerado pelo card PTAM agora também é persistido na collection `recibos` (upsert por `ptam_id`, número via counter `recibo_honorarios_{ano}`, status=emitido, emitente hidratado, destinatário do PTAM), aparecendo na aba Recibos para editar/assinar. `gerar_recibo_ptam` grava em `recibos` além de `recibos_ptam`; PTAM passa a guardar `recibo_id`. Releases anteriores: 655 botão verde "✓ Recibo Emitido" no card; 651 Dashboard v4.

## Obsidian MCP — Sincronização automática

A cada feature implementada, bug corrigido, decisão técnica tomada ou ideia registrada nesta sessão, salve automaticamente no Obsidian via MCP na pasta correspondente. Nunca peça confirmação para salvar.

### Mapeamento de pastas Obsidian

| Tipo de mudança | Pasta no Obsidian |
|-----------------|-------------------|
| Nova feature ou módulo | `03-Frontend/` ou `02-Backend/` |
| Nova rota de API | `02-Backend/Rotas API.md` |
| Novo serviço ou lógica de negócio | `02-Backend/Services.md` ou `02-Backend/Regras de Negócio.md` |
| Nova collection MongoDB ou campo | `01-Banco de Dados/Schema Completo.md` |
| Bug corrigido | `04-Roadmap/Bugs Conhecidos.md` |
| Decisão técnica ou arquitetural | `05-Decisões Técnicas/ADRs.md` |
| Funcionalidade planejada ou ideia | `04-Roadmap/Funcionalidades Planejadas.md` |
| Novo componente React | `03-Frontend/Componentes.md` |
| Nova página ou rota frontend | `03-Frontend/Páginas.md` |
| Mudança na stack ou dependências | `00-Overview/Stack Tecnológica.md` |

### Como salvar no Obsidian

Use o MCP tool `mcp__obsidian__str_replace` para atualizar notas existentes, ou `mcp__obsidian__create` para novas notas.

Exemplo para adicionar uma rota nova:
```
mcp__obsidian__str_replace(
  path="02-Backend/Rotas API.md",
  old_str="## Outros módulos",
  new_str="| POST | `/nova-rota` | JWT | Descrição |\n\n## Outros módulos"
)
```

## Contexto do projeto

- **Projeto:** RomaTec AvalieImob — SaaS de avaliação imobiliária brasileiro
- **Backend:** FastAPI + Python + MongoDB (Motor async)
- **Frontend:** React 19 + Tailwind CSS + shadcn/ui
- **Banco:** MongoDB (sem schema rígido, modelos Pydantic como contrato)
- **Auth:** JWT HS256, 168h, bcrypt
- **Pagamentos:** Mercado Pago (mensal R$89.90, trimestral R$239.90, anual R$849.90)
- **IA:** Roma_IA com cascata Groq → Gemini → Claude → OpenAI
- **Docs completos:** Vault Obsidian em `C:\Users\Ronicley Pinto\Documents\ROMATEC_AVALIEIMOB_\ROMATECAVALIEIMOB\`

## Convenções do projeto

- Rotas backend: todas com prefixo `/api`, arquivo em `backend/routes/`
- Modelos: Pydantic v2 em `backend/models/`, use `model_dump(mode="json")`
- Isolamento de dados: sempre inclua `{"user_id": uid}` nas queries MongoDB
- Numeração de documentos: use padrão `find_one_and_update` com `$inc` na collection `counters`
- Versionamento: PTAM e Contratos usam sistema de versões com SHA-256 + diff
- Rate limiting: `@limiter.limit()` nas rotas sensíveis
- Segurança: headers de segurança aplicados globalmente via `SecurityHeadersMiddleware`
