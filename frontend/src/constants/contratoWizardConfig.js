// @module constants/contratoWizardConfig — ÚNICA fonte de verdade do wizard por tipo.
// Define título, etapas (ordem = numeração 1..N, N varia), papéis e rótulos.
// Barra, chips e conteúdo derivam TODOS daqui (elimina o off-by-one).

// papel.dataKey: chave no form onde a lista de pessoas é armazenada.
const papel = (id, label, labelSingular, dataKey, descricao, opts = {}) => ({
  id, label, labelSingular, dataKey, descricao,
  multiplo: opts.multiplo !== false,
  opcional: !!opts.opcional,
  conjugeObrigatorioSeCasado: !!opts.conjuge,
});

// Cauda comum a todos os tipos (após partes + corretor).
const cauda = (objetoLabel = 'Objeto', condicoesLabel = 'Pagamento') => ([
  { kind: 'objeto', label: objetoLabel },
  { kind: 'condicoes', label: condicoesLabel },
  { kind: 'clausulas', label: 'Cláusulas' },
  { kind: 'validacao', label: 'Validação' },
  { kind: 'testemunhas', label: 'Testemunhas' },
  { kind: 'revisao', label: 'Revisão' },
  { kind: 'exportar', label: 'Exportar' },
]);

const D = {
  vendedor: 'Informe os dados de quem vende/aliena o bem.',
  comprador: 'Informe os dados de quem adquire o bem.',
  proprietario: 'Informe os dados do(s) proprietário(s) do imóvel que outorga(m) a exclusividade.',
  contratante: 'Informe os dados do(s) contratante(s).',
  locador: 'Informe os dados de quem loca (proprietário) o imóvel.',
  locatario: 'Informe os dados de quem aluga o imóvel.',
  fiador: 'Informe os dados do(s) fiador(es) — opcional (garantia).',
  permutanteA: 'Informe os dados do primeiro permutante.',
  permutanteB: 'Informe os dados do segundo permutante.',
  cedente: 'Informe os dados de quem cede os direitos.',
  cessionario: 'Informe os dados de quem recebe os direitos.',
  comodante: 'Informe os dados de quem empresta o bem.',
  comodatario: 'Informe os dados de quem recebe o bem em comodato.',
  arrendador: 'Informe os dados de quem arrenda (proprietário) a terra.',
  arrendatario: 'Informe os dados de quem explora a terra arrendada.',
  outorgante: 'Informe os dados do(s) parceiro(s) outorgante(s) (proprietário).',
  outorgado: 'Informe os dados do(s) parceiro(s) outorgado(s).',
  doador: 'Informe os dados de quem doa o bem.',
  donatario: 'Informe os dados de quem recebe a doação.',
  instituidor: 'Informe os dados do(s) nu-proprietário(s)/instituidor(es).',
  usufrutuario: 'Informe os dados de quem recebe o usufruto.',
  distratanteA: 'Informe os dados da primeira parte do distrato.',
  distratanteB: 'Informe os dados da segunda parte do distrato.',
  corretorContratado: 'Dados do corretor/escritório responsável pela intermediação (parte contratada).',
};

const tipo = { kind: 'tipo', label: 'Tipo' };
const corretor = (label = 'Corretor') => ({ kind: 'corretor', label });
const fiadorOpcional = () => ({ kind: 'partes',
  papel: papel('fiador', 'Fiador(es)', 'Fiador', 'fiadores', D.fiador, { opcional: true }) });

const p = (id, label, sing, key, desc, opts) => ({ kind: 'partes', papel: papel(id, label, sing, key, desc, opts) });

export const WIZARD_CONFIG = {
  compra_venda: {
    tituloHeader: 'Contrato de Compra e Venda',
    etapas: [tipo,
      p('vendedor', 'Vendedor(es)', 'Vendedor', 'vendedores', D.vendedor, { conjuge: true }),
      p('comprador', 'Comprador(es)', 'Comprador', 'compradores', D.comprador),
      corretor(), ...cauda('Objeto', 'Pagamento')],
  },
  promessa_compra_venda: {
    tituloHeader: 'Contrato de Promessa de Compra e Venda',
    etapas: [tipo,
      p('vendedor', 'Promitente(s) Vendedor(es)', 'Promitente Vendedor', 'vendedores', D.vendedor, { conjuge: true }),
      p('comprador', 'Promissário(s) Comprador(es)', 'Promissário Comprador', 'compradores', D.comprador),
      corretor(), ...cauda('Objeto', 'Pagamento')],
  },
  permuta: {
    tituloHeader: 'Contrato de Permuta',
    etapas: [tipo,
      p('permutante_a', 'Permutante(s) 1º', 'Permutante A', 'vendedores', D.permutanteA, { conjuge: true }),
      p('permutante_b', 'Permutante(s) 2º', 'Permutante B', 'compradores', D.permutanteB, { conjuge: true }),
      corretor(), ...cauda('Objetos & Torna', 'Pagamento')],
  },
  cessao_direitos: {
    tituloHeader: 'Contrato de Cessão de Direitos',
    etapas: [tipo,
      p('cedente', 'Cedente(s)', 'Cedente', 'vendedores', D.cedente, { conjuge: true }),
      p('cessionario', 'Cessionário(s)', 'Cessionário', 'compradores', D.cessionario),
      corretor(), ...cauda('Direitos de Origem', 'Pagamento')],
  },
  locacao_residencial: {
    tituloHeader: 'Contrato de Locação Residencial',
    etapas: [tipo,
      p('locador', 'Locador(es)', 'Locador', 'vendedores', D.locador, { conjuge: true }),
      p('locatario', 'Locatário(s)', 'Locatário', 'compradores', D.locatario),
      fiadorOpcional(), corretor(), ...cauda('Imóvel', 'Aluguel & Garantia')],
  },
  locacao_comercial: {
    tituloHeader: 'Contrato de Locação Comercial',
    etapas: [tipo,
      p('locador', 'Locador(es)', 'Locador', 'vendedores', D.locador, { conjuge: true }),
      p('locatario', 'Locatário(s)', 'Locatário', 'compradores', D.locatario),
      fiadorOpcional(), corretor(), ...cauda('Imóvel & Atividade', 'Aluguel & Garantia')],
  },
  comodato: {
    tituloHeader: 'Contrato de Comodato',
    etapas: [tipo,
      p('comodante', 'Comodante(s)', 'Comodante', 'vendedores', D.comodante, { conjuge: true }),
      p('comodatario', 'Comodatário(s)', 'Comodatário', 'compradores', D.comodatario),
      ...cauda('Bem & Uso', 'Encargos')],
  },
  arrendamento_rural: {
    tituloHeader: 'Contrato de Arrendamento Rural',
    etapas: [tipo,
      p('arrendador', 'Arrendador(es)', 'Arrendador', 'vendedores', D.arrendador, { conjuge: true }),
      p('arrendatario', 'Arrendatário(s)', 'Arrendatário', 'compradores', D.arrendatario),
      corretor(), ...cauda('Imóvel Rural', 'Preço & Safra')],
  },
  parceria_rural: {
    tituloHeader: 'Contrato de Parceria Rural',
    etapas: [tipo,
      p('outorgante', 'Parceiro(s) Outorgante(s)', 'Outorgante', 'vendedores', D.outorgante, { conjuge: true }),
      p('outorgado', 'Parceiro(s) Outorgado(s)', 'Outorgado', 'compradores', D.outorgado),
      corretor(), ...cauda('Imóvel & Atividade', 'Partilha de Frutos')],
  },
  doacao: {
    tituloHeader: 'Contrato de Doação',
    etapas: [tipo,
      p('doador', 'Doador(es)', 'Doador', 'vendedores', D.doador, { conjuge: true }),
      p('donatario', 'Donatário(s)', 'Donatário', 'compradores', D.donatario),
      ...cauda('Bem & Encargos', 'Cláusulas Restritivas')],
  },
  arras: {
    tituloHeader: 'Recibo de Arras / Sinal',
    etapas: [tipo,
      p('vendedor', 'Promitente Vendedor(es)', 'Promitente Vendedor', 'vendedores', D.vendedor, { conjuge: true }),
      p('comprador', 'Promitente Comprador(es)', 'Promitente Comprador', 'compradores', D.comprador),
      ...cauda('Negócio Prometido', 'Arras')],
  },
  intermediacao: {
    tituloHeader: 'Contrato de Intermediação Imobiliária',
    etapas: [tipo,
      p('contratante', 'Contratante(s)', 'Contratante', 'vendedores', D.contratante, { conjuge: true }),
      corretor('Corretor (Contratado)'), ...cauda('Imóvel', 'Comissão')],
  },
  exclusividade: {
    tituloHeader: 'Contrato de Exclusividade',
    etapas: [tipo,
      p('contratante', 'Contratante (Proprietário)', 'Contratante', 'vendedores', D.proprietario, { conjuge: true }),
      corretor('Corretor (Contratado)'),
      { kind: 'objeto', label: 'Imóvel' },
      { kind: 'condicoes', label: 'Comissão & Prazo' },
      { kind: 'clausulas', label: 'Cláusulas' },
      { kind: 'validacao', label: 'Validação' },
      { kind: 'testemunhas', label: 'Testemunhas' },
      { kind: 'procuracao', label: 'Procuração' },
      { kind: 'revisao', label: 'Revisão' },
      { kind: 'exportar', label: 'Exportar' },
    ],
  },
  usufruto: {
    tituloHeader: 'Instrumento de Instituição de Usufruto',
    etapas: [tipo,
      p('instituidor', 'Instituidor(es)/Nu-proprietário(s)', 'Instituidor', 'vendedores', D.instituidor, { conjuge: true }),
      p('usufrutuario', 'Usufrutuário(s)', 'Usufrutuário', 'compradores', D.usufrutuario),
      ...cauda('Bem & Registro', 'Condições')],
  },
  compra_venda_veiculo: {
    tituloHeader: 'Contrato de Compra e Venda de Veículo',
    etapas: [tipo,
      p('vendedor', 'Vendedor(es)', 'Vendedor', 'vendedores', D.vendedor),
      p('comprador', 'Comprador(es)', 'Comprador', 'compradores', D.comprador),
      ...cauda('Veículo', 'Pagamento')],
  },
  distrato: {
    tituloHeader: 'Instrumento de Distrato',
    etapas: [tipo,
      p('distratante_a', 'Distratante(s) 1º', 'Distratante A', 'vendedores', D.distratanteA),
      p('distratante_b', 'Distratante(s) 2º', 'Distratante B', 'compradores', D.distratanteB),
      ...cauda('Contrato de Origem', 'Devoluções')],
  },
};

export const DEFAULT_TIPO = 'compra_venda';

export const getWizardConfig = (tipoContrato) =>
  WIZARD_CONFIG[tipoContrato] || WIZARD_CONFIG[DEFAULT_TIPO];

// Rótulo de uma etapa (chip e barra usam ISTO — fonte única).
export const etapaLabel = (etapa) => {
  if (!etapa) return '';
  if (etapa.kind === 'partes') return etapa.papel.label;
  return etapa.label || etapa.kind;
};
