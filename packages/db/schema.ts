import {
  mysqlTable,
  varchar,
  int,
  bigint,
  text,
  decimal,
  datetime,
  boolean,
  index,
  primaryKey,
  unique,
} from "drizzle-orm/mysql-core";
import { relations } from "drizzle-orm";

// ============================================================================
// USERS & AUTH
// ============================================================================

export const users = mysqlTable(
  "users",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    email: varchar("email", { length: 255 }).notNull().unique(),
    password_hash: varchar("password_hash", { length: 255 }).notNull(),
    nome: varchar("nome", { length: 255 }).notNull(),
    cpf: varchar("cpf", { length: 14 }).unique(),
    crea: varchar("crea", { length: 20 }), // CREA do avaliador
    incra: varchar("incra", { length: 20 }), // INCRA (agrimensura)
    telefone: varchar("telefone", { length: 20 }),
    endereco: text("endereco"),
    cidade: varchar("cidade", { length: 100 }),
    estado: varchar("estado", { length: 2 }),
    cep: varchar("cep", { length: 9 }),
    role: varchar("role", ["admin", "avaliador", "cliente"]).default("cliente"),
    ativo: boolean("ativo").default(true),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      emailIdx: index("idx_email").on(table.email),
      roleIdx: index("idx_role").on(table.role),
    };
  }
);

// ============================================================================
// SUBSCRIPTIONS & PAGAMENTO
// ============================================================================

export const subscriptions = mysqlTable(
  "subscriptions",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    user_id: varchar("user_id", { length: 36 })
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    plano: varchar("plano", ["mensal", "trimestral", "anual"]).notNull(),
    valor_centavos: bigint("valor_centavos").notNull(), // Armazenar em centavos
    mp_subscription_id: varchar("mp_subscription_id", { length: 100 }), // Mercado Pago ID
    status: varchar("status", ["ativa", "cancelada", "pendente"]).default(
      "pendente"
    ),
    data_inicio: datetime("data_inicio"),
    data_proxima_cobranca: datetime("data_proxima_cobranca"),
    data_cancelamento: datetime("data_cancelamento"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      userIdx: index("idx_user_id").on(table.user_id),
      statusIdx: index("idx_status").on(table.status),
      mpIdx: index("idx_mp_sub_id").on(table.mp_subscription_id),
    };
  }
);

// ============================================================================
// CLIENTES (SOLICITANTES PTAM)
// ============================================================================

export const clientes = mysqlTable(
  "clientes",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    user_id: varchar("user_id", { length: 36 })
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    razao_social: varchar("razao_social", { length: 255 }).notNull(),
    cnpj_cpf: varchar("cnpj_cpf", { length: 20 }).unique(),
    telefone: varchar("telefone", { length: 20 }),
    email: varchar("email", { length: 255 }),
    endereco: text("endereco"),
    cidade: varchar("cidade", { length: 100 }),
    estado: varchar("estado", { length: 2 }),
    cep: varchar("cep", { length: 9 }),
    contato: varchar("contato", { length: 255 }),
    obs: text("obs"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      userIdx: index("idx_cliente_user_id").on(table.user_id),
      cnpjCpfIdx: index("idx_cnpj_cpf").on(table.cnpj_cpf),
    };
  }
);

// ============================================================================
// IMÓVEIS
// ============================================================================

export const imoveis = mysqlTable(
  "imoveis",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    cliente_id: varchar("cliente_id", { length: 36 })
      .notNull()
      .references(() => clientes.id, { onDelete: "cascade" }),
    matricula: varchar("matricula", { length: 50 }).unique(),
    endereco: text("endereco").notNull(),
    latitude: decimal("latitude", { precision: 10, scale: 8 }),
    longitude: decimal("longitude", { precision: 11, scale: 8 }),
    cidade: varchar("cidade", { length: 100 }).notNull(),
    estado: varchar("estado", { length: 2 }).notNull(),
    cep: varchar("cep", { length: 9 }),
    tipo: varchar("tipo", ["urbano", "rural", "misto"]).default("urbano"),
    area_total_m2: decimal("area_total_m2", { precision: 12, scale: 2 }),
    area_total_ha: decimal("area_total_ha", { precision: 12, scale: 4 }),
    descricao_fisica: text("descricao_fisica"),
    topografia: varchar("topografia", { length: 100 }),
    acessibilidade: text("acessibilidade"),
    benfeitorias: text("benfeitorias"),
    estado_conservacao: varchar("estado_conservacao", [
      "otimo",
      "bom",
      "regular",
      "precario",
    ]),
    fotos_urls: text("fotos_urls"), // JSON array de URLs
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      clienteIdx: index("idx_imovel_cliente").on(table.cliente_id),
      matriculaIdx: index("idx_matricula").on(table.matricula),
      cidadeIdx: index("idx_imovel_cidade").on(table.cidade),
    };
  }
);

// ============================================================================
// AMOSTRAS (COMPARATIVAS PARA MERCADO)
// ============================================================================

export const amostras = mysqlTable(
  "amostras",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    avaliacao_id: varchar("avaliacao_id", { length: 36 }),
    descricao: text("descricao").notNull(),
    endereco: text("endereco"),
    cidade: varchar("cidade", { length: 100 }),
    estado: varchar("estado", { length: 2 }),
    tipo: varchar("tipo", ["urbano", "rural"]).default("urbano"),
    area_m2: decimal("area_m2", { precision: 12, scale: 2 }),
    area_ha: decimal("area_ha", { precision: 12, scale: 4 }),
    valor_total: decimal("valor_total", { precision: 14, scale: 2 }),
    valor_unitario_m2: decimal("valor_unitario_m2", { precision: 10, scale: 2 }),
    valor_unitario_ha: decimal("valor_unitario_ha", { precision: 10, scale: 2 }),
    data_oferta: datetime("data_oferta"),
    data_venda: datetime("data_venda"),
    fonte: varchar("fonte", { length: 100 }), // CRECI, Imobiliária, etc
    situacao: varchar("situacao", ["oferta", "vendido", "aluguel"]).default(
      "oferta"
    ),
    obs: text("obs"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
  },
  (table) => {
    return {
      avaliacaoIdx: index("idx_amostra_avaliacao").on(table.avaliacao_id),
      cidadeIdx: index("idx_amostra_cidade").on(table.cidade),
    };
  }
);

// ============================================================================
// AVALIAÇÕES (PTAM EM ANDAMENTO)
// ============================================================================

export const avaliacoes = mysqlTable(
  "avaliacoes",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    imovel_id: varchar("imovel_id", { length: 36 })
      .notNull()
      .references(() => imoveis.id, { onDelete: "cascade" }),
    avaliador_id: varchar("avaliador_id", { length: 36 })
      .notNull()
      .references(() => users.id),
    numero_ptam: varchar("numero_ptam", { length: 50 }).unique(),
    titulo: varchar("titulo", { length: 255 }).notNull(),
    finalidade: text("finalidade"),
    metodologia: varchar("metodologia", [
      "comparativo",
      "evolutivo",
      "misto",
    ]).default("comparativo"),
    status: varchar("status", ["rascunho", "em_andamento", "pronto", "emitido"]).default(
      "rascunho"
    ),
    notas_tecnicas: text("notas_tecnicas"),
    data_vistoria: datetime("data_vistoria"),
    data_criacao: datetime("data_criacao", { fsp: 3 }).defaultNow(),
    data_conclusao: datetime("data_conclusao"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      imovelIdx: index("idx_avaliacao_imovel").on(table.imovel_id),
      avaliadorIdx: index("idx_avaliador").on(table.avaliador_id),
      statusIdx: index("idx_avaliacao_status").on(table.status),
      numeroIdx: unique("idx_numero_ptam").on(table.numero_ptam),
    };
  }
);

// ============================================================================
// TRANSCRIÇÕES DE ÁUDIO (WHISPER)
// ============================================================================

export const audio_transcricoes = mysqlTable(
  "audio_transcricoes",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    avaliacao_id: varchar("avaliacao_id", { length: 36 })
      .notNull()
      .references(() => avaliacoes.id, { onDelete: "cascade" }),
    arquivo_url: text("arquivo_url"),
    duracao_segundos: int("duracao_segundos"),
    transcricao_texto: text("transcricao_texto"),
    confianca: decimal("confianca", { precision: 3, scale: 2 }), // 0-1
    idioma: varchar("idioma", { length: 10 }).default("pt-BR"),
    tipo: varchar("tipo", [
      "descricao_imovel",
      "condicoes_mercado",
      "observacoes",
    ]).default("descricao_imovel"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
  },
  (table) => {
    return {
      avaliacaoIdx: index("idx_audio_avaliacao").on(table.avaliacao_id),
    };
  }
);

// ============================================================================
// CÁLCULOS & METODOLOGIAS
// ============================================================================

export const calculos = mysqlTable(
  "calculos",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    avaliacao_id: varchar("avaliacao_id", { length: 36 })
      .notNull()
      .references(() => avaliacoes.id, { onDelete: "cascade" }),
    tipo: varchar("tipo", ["comparativo", "evolutivo"]).notNull(),
    area_impactada_m2: decimal("area_impactada_m2", { precision: 12, scale: 2 }),
    area_impactada_ha: decimal("area_impactada_ha", { precision: 12, scale: 4 }),
    valor_unitario: decimal("valor_unitario", { precision: 10, scale: 2 }),
    valor_total: decimal("valor_total", { precision: 14, scale: 2 }),
    margem_erro: decimal("margem_erro", { precision: 5, scale: 2 }),
    intervalo_minimo: decimal("intervalo_minimo", { precision: 10, scale: 2 }),
    intervalo_maximo: decimal("intervalo_maximo", { precision: 10, scale: 2 }),
    amostra_tamanho: int("amostra_tamanho"),
    desvio_padrao: decimal("desvio_padrao", { precision: 10, scale: 2 }),
    coeficiente_variacao: decimal("coeficiente_variacao", { precision: 5, scale: 2 }),
    dados_json: text("dados_json"), // Dados brutos do cálculo
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      avaliacaoIdx: index("idx_calculo_avaliacao").on(table.avaliacao_id),
      tipoIdx: index("idx_calculo_tipo").on(table.tipo),
    };
  }
);

// ============================================================================
// PTAM EMITIDOS (HISTÓRICO + DOCUMENTOS)
// ============================================================================

export const ptam_emitidos = mysqlTable(
  "ptam_emitidos",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    avaliacao_id: varchar("avaliacao_id", { length: 36 })
      .notNull()
      .unique()
      .references(() => avaliacoes.id, { onDelete: "cascade" }),
    numero_ptam: varchar("numero_ptam", { length: 50 }).notNull(),
    url_pdf: text("url_pdf"),
    url_docx: text("url_docx"),
    hash_pdf: varchar("hash_pdf", { length: 64 }),
    hash_docx: varchar("hash_docx", { length: 64 }),
    data_emissao: datetime("data_emissao", { fsp: 3 }).defaultNow(),
    data_assinatura: datetime("data_assinatura"),
    assinado_por: varchar("assinado_por", { length: 36 }).references(
      () => users.id
    ),
    assinatura_digital: text("assinatura_digital"), // BASE64 ou URL
    validade: datetime("validade"),
    enviado_para_email: boolean("enviado_para_email").default(false),
    data_envio_email: datetime("data_envio_email"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
  },
  (table) => {
    return {
      avaliacaoIdx: index("idx_ptam_avaliacao").on(table.avaliacao_id),
      numeroIdx: unique("idx_numero_ptam_emitido").on(table.numero_ptam),
      dataIdx: index("idx_ptam_data").on(table.data_emissao),
    };
  }
);

// ============================================================================
// LAUDOS (COMPLEMENTAR AO PTAM)
// ============================================================================

export const laudos = mysqlTable(
  "laudos",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    ptam_id: varchar("ptam_id", { length: 36 })
      .notNull()
      .references(() => ptam_emitidos.id, { onDelete: "cascade" }),
    titulo: varchar("titulo", { length: 255 }).notNull(),
    corpo_texto: text("corpo_texto"),
    url_pdf: text("url_pdf"),
    url_docx: text("url_docx"),
    tipo_laudo: varchar("tipo_laudo", [
      "completo",
      "simplificado",
      "pericial",
    ]).default("completo"),
    data_emissao: datetime("data_emissao", { fsp: 3 }).defaultNow(),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
  },
  (table) => {
    return {
      ptamIdx: index("idx_laudo_ptam").on(table.ptam_id),
    };
  }
);

// ============================================================================
// PORTAL DE AVALIADORES (LISTING PÚBLICO)
// ============================================================================

export const avaliadores_publico = mysqlTable(
  "avaliadores_publico",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    user_id: varchar("user_id", { length: 36 })
      .notNull()
      .unique()
      .references(() => users.id, { onDelete: "cascade" }),
    nome_completo: varchar("nome_completo", { length: 255 }).notNull(),
    bio: text("bio"),
    crea: varchar("crea", { length: 20 }),
    incra: varchar("incra", { length: 20 }),
    foto_url: text("foto_url"),
    cidades_atuacao: text("cidades_atuacao"), // JSON array
    especialidades: text("especialidades"), // JSON: urbano, rural, etc
    total_avaliacoes: int("total_avaliacoes").default(0),
    rating_media: decimal("rating_media", { precision: 3, scale: 2 }).default(
      0
    ),
    ativo: boolean("ativo").default(true),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
    atualizado_em: datetime("atualizado_em", { fsp: 3 })
      .defaultNow()
      .onUpdateNow(),
  },
  (table) => {
    return {
      userIdx: unique("idx_avaliador_publico_user").on(table.user_id),
      ativoIdx: index("idx_avaliador_ativo").on(table.ativo),
    };
  }
);

// ============================================================================
// RATINGS (AVALIAÇÕES DOS CLIENTES)
// ============================================================================

export const ratings = mysqlTable(
  "ratings",
  {
    id: varchar("id", { length: 36 }).primaryKey(),
    avaliacao_id: varchar("avaliacao_id", { length: 36 })
      .notNull()
      .references(() => avaliacoes.id, { onDelete: "cascade" }),
    cliente_id: varchar("cliente_id", { length: 36 })
      .notNull()
      .references(() => clientes.id),
    avaliador_id: varchar("avaliador_id", { length: 36 })
      .notNull()
      .references(() => users.id),
    estrelas: int("estrelas").notNull(), // 1-5
    comentario: text("comentario"),
    criado_em: datetime("criado_em", { fsp: 3 }).defaultNow(),
  },
  (table) => {
    return {
      avaliacaoIdx: index("idx_rating_avaliacao").on(table.avaliacao_id),
      avaliadorIdx: index("idx_rating_avaliador").on(table.avaliador_id),
    };
  }
);

// ============================================================================
// RELAÇÕES (DRIZZLE ORM)
// ============================================================================

export const usersRelations = relations(users, ({ many, one }) => ({
  subscriptions: many(subscriptions),
  clientes: many(clientes),
  avaliacoes: many(avaliacoes),
  avaliador_publico: one(avaliadores_publico),
}));

export const clientesRelations = relations(clientes, ({ one, many }) => ({
  user: one(users),
  imoveis: many(imoveis),
  ratings: many(ratings),
}));

export const imoveisRelations = relations(imoveis, ({ one, many }) => ({
  cliente: one(clientes),
  avaliacoes: many(avaliacoes),
}));

export const avaliacoesRelations = relations(
  avaliacoes,
  ({ one, many }) => ({
    imovel: one(imoveis),
    avaliador: one(users),
    amostras: many(amostras),
    audios: many(audio_transcricoes),
    calculos: many(calculos),
    ptam: one(ptam_emitidos),
  })
);

export const ptamRelations = relations(ptam_emitidos, ({ one, many }) => ({
  avaliacao: one(avaliacoes),
  laudos: many(laudos),
}));
