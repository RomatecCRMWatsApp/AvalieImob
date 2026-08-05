// @module dashboard/propostas/PropostaForm — Form de proposta (schema-driven) com preview ao vivo.
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader2, Calculator, FileText, ChevronRight, MapPin, Trash2 } from 'lucide-react';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { useToast } from '../../../hooks/use-toast';
import { propostasAPI, clientsAPI } from '../../../lib/api';
import EtapaConcluidaBox from '../ptam/EtapaConcluidaBox';
import { comodosPorCategoria, CATEGORIAS_LABEL, ORDEM_CATEGORIAS } from '../../../constants/comodosEdificacao';
import { PROJETOS_EXECUTIVO_DEFAULT } from '../../../constants/projetosExecutivo';
import ImageUploader from '../ptam/ImageUploader';

const fmtBRL = (v) => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum = (v, d = 2) => Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
const SUBTIPOS_DEMARCACAO = ['demarcacao_urbana', 'demarcacao_rural'];
const FORMATOS_COLETORA = [
  { value: 'csv', label: 'CSV / TXT (ponto;este;norte)' },
  { value: 'kml', label: 'KML (Google Earth)' },
];

// ── Schemas por subtipo (campos do dados_imovel) ──────────────────────────
const N = (key, label, def = 0) => ({ key, label, type: 'number', def });
const SEL = (key, label, options, def) => ({ key, label, type: 'select', options, def: def ?? options[0].value });
const BOOL = (key, label, def = false, labels = ['Não', 'Sim']) => ({
  key, label, type: 'select', def: String(def),
  options: [{ value: 'false', label: labels[0] }, { value: 'true', label: labels[1] }], _bool: true,
});

const CAMPOS_AVERBACAO = [
  N('area_construida', 'Área construída (m²)'),
  N('valor_venal_imovel', 'Valor venal do imóvel (R$)'),
  SEL('padrao_construtivo', 'Padrão construtivo', [
    { value: 'popular', label: 'Popular' }, { value: 'normal', label: 'Normal' }, { value: 'alto', label: 'Alto' }], 'normal'),
  SEL('responsavel', 'Responsável pela obra', [
    { value: 'PF', label: 'Pessoa Física' }, { value: 'PJ_sem_contabilidade', label: 'PJ sem contabilidade' },
    { value: 'PJ_com_contabilidade', label: 'PJ com contabilidade (sem SERO)' }], 'PF'),
  SEL('anotacao_tecnica', 'Anotação técnica', [
    { value: 'art_crea', label: 'ART CREA-MA' }, { value: 'rrt_cau', label: 'RRT CAU/MA' }, { value: 'trt_cft', label: 'TRT CFT/MA' }], 'art_crea'),
  BOOL('tem_alvara_construcao', 'Já possui alvará?', false, ['Não (cobra alvará)', 'Sim']),
  BOOL('parcelar_inss', 'Parcelar INSS/SERO?'),
  { ...N('numero_parcelas_inss', 'Nº de parcelas INSS (2–60)', 12), when: (d) => !!d.parcelar_inss },
];

const SCHEMAS = {
  averbacao_residencial: {
    titulo: 'Averbação Residencial',
    campos: [...CAMPOS_AVERBACAO.slice(0, 6),
      BOOL('apresentar_projetos_complementares', 'Projetos complementares (7 projetos)?'),
      ...CAMPOS_AVERBACAO.slice(6)],
  },
  averbacao_comercial: { titulo: 'Averbação Comercial', campos: CAMPOS_AVERBACAO },
  retificacao_area: {
    titulo: 'Retificação de Área',
    campos: [
      N('area_atual_matricula', 'Área atual (matrícula)'),
      N('area_real_levantada', 'Área real (levantada)'),
      N('valor_venal', 'Valor venal (R$)'),
      SEL('tipo_retificacao', 'Tipo', [
        { value: 'administrativa', label: 'Administrativa (Lei 10.931)' }, { value: 'judicial', label: 'Judicial (Lei 6.015)' }], 'administrativa'),
      BOOL('tem_anuencia_confrontantes', 'Tem anuência dos confrontantes?'),
      N('honorario_projeto_sm', 'Honorário projeto (em SM)', 1),
    ],
  },
  avaliacao_ptam: {
    titulo: 'Avaliação PTAM',
    campos: [
      SEL('tipo_imovel', 'Tipo de imóvel', [
        { value: 'urbano_residencial', label: 'Urbano residencial' }, { value: 'urbano_comercial', label: 'Urbano comercial' },
        { value: 'rural', label: 'Rural' }, { value: 'glebas', label: 'Glebas' }, { value: 'industrial', label: 'Industrial' }], 'urbano_residencial'),
      N('area_terreno', 'Área do terreno'),
      N('area_construida', 'Área construída'),
      SEL('finalidade', 'Finalidade', [
        { value: 'particular', label: 'Particular' }, { value: 'bancaria', label: 'Bancária' },
        { value: 'judicial', label: 'Judicial' }, { value: 'inventario', label: 'Inventário' }], 'particular'),
      SEL('nivel_precisao', 'Nível de precisão', [
        { value: 'expedita', label: 'Expedita (0,7×)' }, { value: 'normal', label: 'Normal (1×)' }, { value: 'rigorosa', label: 'Rigorosa (1,5×)' }], 'normal'),
      SEL('faixa_honorario', 'Faixa de honorário', [
        { value: '1_lote_urbano', label: 'Lote urbano (1 SM)' }, { value: '2_sitio_proximo', label: 'Sítio próximo (2 SM)' },
        { value: '3_rural_medio', label: 'Rural médio (3 SM)' }, { value: '4_fazenda_grande', label: 'Fazenda grande (4 SM)' },
        { value: 'outro', label: 'Outro (valor custom)' }], '1_lote_urbano'),
      { ...N('valor_outro', 'Valor customizado (R$)'), when: (d) => d.faixa_honorario === 'outro' },
    ],
  },
  georreferenciamento_rural: {
    titulo: 'Georreferenciamento Rural (INCRA/SIGEF)',
    campos: [
      N('area_hectares', 'Área (hectares)'),
      N('numero_vertices', 'Nº de vértices (mín. 3)', 3),
      N('numero_diarias', 'Diárias de campo'),
      N('distancia_km', 'Deslocamento (km)'),
      SEL('complexidade', 'Complexidade', [
        { value: 'simples', label: 'Simples (1,0×)' }, { value: 'media', label: 'Média (1,3×)' },
        { value: 'alta', label: 'Alta (1,6×)' }], 'media'),
      SEL('finalidade', 'Finalidade', [
        { value: 'CERTIFICACAO', label: 'Certificação' }, { value: 'DESMEMBRAMENTO', label: 'Desmembramento' },
        { value: 'REMEMBRAMENTO', label: 'Remembramento' }, { value: 'RETIFICACAO', label: 'Retificação' }], 'CERTIFICACAO'),
      BOOL('tem_matricula', 'Possui matrícula registrada?', true),
      N('valor_outros_servicos', 'Outros serviços / despesas (R$)'),
      BOOL('opc_ccir', 'Opcional: CCIR (INCRA)?'),
      BOOL('opc_car', 'Opcional: CAR (Cadastro Ambiental Rural)?'),
      BOOL('opc_itr', 'Opcional: ITR / DITR?'),
      BOOL('opc_anuencia', 'Opcional: Anuência de confrontantes?'),
      BOOL('opc_retificacao', 'Opcional: Retificação de área?'),
    ],
  },
  desmembramento: {
    titulo: 'Desmembramento',
    campos: [
      N('numero_lotes_resultantes', 'Nº de lotes resultantes (≥ 2)', 2),
      N('area_total_m2', 'Área total da matriz (m²)'),
      N('valor_venal_total', 'Valor venal total (R$)'),
      SEL('tipo_zona', 'Zona', [{ value: 'urbana', label: 'Urbana' }, { value: 'rural', label: 'Rural' }], 'urbana'),
      SEL('honorario_projeto_sm', 'Pacote (honorário/lote)', [
        { value: 0.5, label: 'Básico (0,5 SM/lote)' }, { value: 1, label: 'Completo (1 SM/lote)' }], 1),
      BOOL('iptu_em_dia', 'IPTU em dia?', true),
      BOOL('assessoria_tecnica_habilitada', 'Assessoria técnica (acompanhamento)?'),
      { ...N('assessoria_tecnica_valor', 'Valor da assessoria (R$)'), when: (d) => !!d.assessoria_tecnica_habilitada },
      BOOL('despesas_administrativas_habilitada', 'Despesas administrativas (à parte)?'),
      { ...N('despesas_administrativas_valor', 'Valor das despesas (R$)'), when: (d) => !!d.despesas_administrativas_habilitada },
    ],
  },
  remembramento: {
    titulo: 'Remembramento',
    campos: [
      N('numero_lotes_origem', 'Nº de matrículas a unificar (≥ 2)', 2),
      N('area_total_m2', 'Área total (m²)'),
      N('valor_venal_total', 'Valor venal total (R$)'),
      SEL('tipo_zona', 'Zona', [{ value: 'urbana', label: 'Urbana' }, { value: 'rural', label: 'Rural' }], 'urbana'),
      SEL('honorario_projeto_sm', 'Pacote (honorário/matrícula)', [
        { value: 0.5, label: 'Básico (0,5 SM)' }, { value: 1, label: 'Completo (1 SM)' }], 1),
      BOOL('iptu_em_dia', 'IPTU em dia?', true),
      BOOL('assessoria_tecnica_habilitada', 'Assessoria técnica (acompanhamento)?'),
      { ...N('assessoria_tecnica_valor', 'Valor da assessoria (R$)'), when: (d) => !!d.assessoria_tecnica_habilitada },
      BOOL('despesas_administrativas_habilitada', 'Despesas administrativas (à parte)?'),
      { ...N('despesas_administrativas_valor', 'Valor das despesas (R$)'), when: (d) => !!d.despesas_administrativas_habilitada },
    ],
  },
  demarcacao_urbana: {
    titulo: 'Demarcação de Lote Urbano',
    campos: [
      N('area_m2', 'Área do lote (m²)'),
      N('num_vertices', 'Nº de vértices (≥ 3)', 4),
      N('diarias_equipe', 'Diárias de equipe (≥ 1)', 1),
      N('km_deslocamento', 'Deslocamento (km)'),
      SEL('complexidade', 'Complexidade', [
        { value: 'simples', label: 'Simples (1,0×)' }, { value: 'media', label: 'Média (1,3×)' },
        { value: 'alta', label: 'Alta (1,6×)' }], 'media'),
      SEL('marco_tipo', 'Tipo de marco', [
        { value: 'concreto', label: 'Concreto (R$120)' }, { value: 'tubo_galvanizado', label: 'Tubo galvanizado (R$85)' },
        { value: 'madeira', label: 'Madeira (R$35)' }], 'concreto'),
      N('marco_quantidade', 'Qtd. de marcos'),
      N('adicional_campo_pct', 'Adicional de campo % (insal/peric, 0–40)'),
      N('desconto_pct', 'Desconto % (0–30)'),
      SEL('num_parcelas', 'Parcelamento', [{ value: 3, label: '3× (40/30/30)' }, { value: 2, label: '2× (50/50)' }], 3),
      BOOL('laudo_tecnico_direto_contratado', 'Laudo técnico (item direto, soma)?'),
      BOOL('alinhamento_cerca_contratado', 'Alinhamento de cerca (item direto, soma)?'),
      { ...N('alinhamento_cerca_metros', 'Metros de cerca'), when: (d) => !!d.alinhamento_cerca_contratado },
      BOOL('opc_croqui', 'Opcional: croqui assinado (à parte)?'),
      BOOL('opc_acompanhamento', 'Opcional: acompanhamento de obra (à parte)?'),
      { ...N('opc_acompanhamento_diarias', 'Diárias de acompanhamento'), when: (d) => !!d.opc_acompanhamento },
      BOOL('opc_juridica', 'Opcional: consultoria jurídica (à parte)?'),
    ],
  },
  demarcacao_rural: {
    titulo: 'Demarcação de Imóvel Rural',
    campos: [
      N('area_hectares', 'Área (hectares)'),
      N('num_vertices', 'Nº de vértices (≥ 3)', 4),
      N('diarias_equipe', 'Diárias de equipe (≥ 1)', 1),
      N('km_deslocamento', 'Deslocamento (km)'),
      SEL('complexidade', 'Complexidade', [
        { value: 'simples', label: 'Simples (1,0×)' }, { value: 'media', label: 'Média (1,3×)' },
        { value: 'alta', label: 'Alta (1,6×)' }], 'media'),
      SEL('marco_tipo', 'Tipo de marco', [
        { value: 'concreto', label: 'Concreto (R$120)' }, { value: 'tubo_galvanizado', label: 'Tubo galvanizado (R$85)' },
        { value: 'madeira', label: 'Madeira (R$35)' }], 'concreto'),
      N('marco_quantidade', 'Qtd. de marcos'),
      N('adicional_campo_pct', 'Adicional de campo % (insal/peric, 0–40)'),
      N('desconto_pct', 'Desconto % (0–30)'),
      SEL('num_parcelas', 'Parcelamento', [{ value: 3, label: '3× (40/30/30)' }, { value: 2, label: '2× (50/50)' }], 3),
      BOOL('laudo_tecnico_direto_contratado', 'Laudo técnico (item direto, soma)?'),
      BOOL('alinhamento_cerca_contratado', 'Alinhamento de cerca (item direto, soma)?'),
      { ...N('alinhamento_cerca_metros', 'Metros de cerca'), when: (d) => !!d.alinhamento_cerca_contratado },
      BOOL('opc_croqui', 'Opcional: croqui assinado (à parte)?'),
      BOOL('opc_acompanhamento', 'Opcional: acompanhamento de obra (à parte)?'),
      { ...N('opc_acompanhamento_diarias', 'Diárias de acompanhamento'), when: (d) => !!d.opc_acompanhamento },
      BOOL('opc_juridica', 'Opcional: consultoria jurídica (à parte)?'),
    ],
  },
  projeto_executivo: {
    titulo: 'Projeto Executivo',
    campos: [
      { ...N('area_construir', 'Área a construir (m²)'), grupo: 'parametros' },
      { ...N('area_terreno', 'Área do terreno (m²) — opcional'), grupo: 'parametros' },
      { ...N('valor_m2', 'Valor por m² (R$)', 25), grupo: 'parametros' },
      { ...N('desconto_honorarios', 'Desconto sobre honorários (R$)'), grupo: 'parametros' },
      { ...BOOL('responsabilidade_auto', 'ART/TRT automático por área?', true, ['Não (escolher)', 'Sim (> 80m² = ART)']), grupo: 'responsabilidade' },
      { ...SEL('responsabilidade_tipo', 'Responsabilidade técnica', [
        { value: 'ART', label: 'ART CREA-MA (R$ 233,94)' }, { value: 'TRT', label: 'TRT CFT/MA (R$ 93,40)' }], 'TRT'),
        when: (d) => d.responsabilidade_auto === false, grupo: 'responsabilidade' },
      SEL('forma_pagamento_tag', 'Forma de pagamento', [
        { value: 'sinal_mais_1', label: '50% sinal + 50% entrega' }, { value: 'integral', label: 'À vista (100%)' },
        { value: 'sinal_mais_2', label: 'Sinal + 2× na entrega' }, { value: 'duas_vezes', label: '2× iguais' },
        { value: 'personalizada', label: 'Personalizada' }], 'sinal_mais_1'),
      { ...BOOL('diligencia_incluir', 'Diligência na Secretaria (despesa)?'), grupo: 'despesas' },
      { ...N('diligencia_valor', 'Valor da diligência (R$)'), when: (d) => !!d.diligencia_incluir, grupo: 'despesas' },
      { ...BOOL('alvara_incluir', 'Taxa de Alvará de Construção (despesa)?'), grupo: 'despesas' },
      { ...N('alvara_valor', 'Valor do alvará (R$)'), when: (d) => !!d.alvara_incluir, grupo: 'despesas' },
      { ...BOOL('placa_incluir', 'Placa de Obra (despesa)?'), grupo: 'despesas' },
      { ...N('placa_valor', 'Valor da placa (R$)'), when: (d) => !!d.placa_incluir, grupo: 'despesas' },
    ],
  },
};

const PAGAMENTO_TAGS = [
  { tag: 'integral', label: 'À vista (100%)', icon: '💵' },
  { tag: 'sinal_mais_1', label: '50% sinal + 50% entrega', icon: '🤝' },
  { tag: 'sinal_mais_2', label: 'Sinal + 2× na entrega', icon: '📑' },
  { tag: 'duas_vezes', label: '2× (50% + 50%)', icon: '💳' },
  { tag: 'personalizada', label: 'Personalizada', icon: '✍️' },
];

const defaultsDe = (schema) => {
  const d = {};
  (schema?.campos || []).forEach((c) => { d[c.key] = c._bool ? (c.def === 'true') : c.def; });
  return d;
};

const Field = ({ label, children, className = '' }) => (
  <div className={`space-y-1 ${className}`}><label className="text-xs font-medium text-gray-600">{label}</label>{children}</div>
);

const PropostaForm = () => {
  const { subtipo: subtipoParam, id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const editing = !!id;

  const [subtipo, setSubtipo] = useState(subtipoParam || 'averbacao_residencial');
  const schema = SCHEMAS[subtipo] || SCHEMAS.averbacao_residencial;
  const [form, setForm] = useState({
    cliente_nome: '', cliente_cpf_cnpj: '', cliente_telefone: '', cliente_email: '',
    endereco_imovel: '', validade_dias: 15, observacoes: '',
    etapas_concluidas: {}, etapas_concluidas_em: {},
    dados_imovel: defaultsDe(SCHEMAS[subtipoParam] || SCHEMAS.averbacao_residencial),
  });
  const [preview, setPreview] = useState(null);
  const [calc, setCalc] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(editing);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [clientes, setClientes] = useState([]);
  const [step, setStep] = useState(0);
  // Demarcação — Pontos & Croqui
  const [coletoraTexto, setColetoraTexto] = useState('');
  const [coletoraFmt, setColetoraFmt] = useState('csv');
  const [importando, setImportando] = useState(false);
  const [geo, setGeo] = useState(null);        // {resumo:{area_m2, perimetro_m, lados[]}, alinhamento}
  const [croqui, setCroqui] = useState('');    // SVG (string) do preview
  const debRef = useRef(null);
  const geoRef = useRef(null);
  const pdfUrlRef = useRef(null);

  useEffect(() => () => { if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current); }, []);
  useEffect(() => { clientsAPI.list().then((d) => setClientes(Array.isArray(d) ? d : [])).catch(() => {}); }, []);

  const selecionarCliente = (cid) => {
    const c = clientes.find((x) => String(x.id) === String(cid));
    if (!c) return;
    setForm((f) => ({
      ...f,
      cliente_nome: c.name || c.nome || '',
      cliente_cpf_cnpj: c.doc || c.cpf_cnpj || '',
      cliente_telefone: c.phone || c.telefone || '',
      cliente_email: c.email || '',
      endereco_imovel: f.endereco_imovel || c.endereco || '',
      cliente_id: c.id,
    }));
  };

  useEffect(() => {
    if (!editing) return;
    propostasAPI.get(id).then((p) => {
      setSubtipo(p.subtipo);
      const sch = SCHEMAS[p.subtipo] || SCHEMAS.averbacao_residencial;
      setForm({
        cliente_nome: p.cliente_nome || '', cliente_cpf_cnpj: p.cliente_cpf_cnpj || '',
        cliente_telefone: p.cliente_telefone || '', cliente_email: p.cliente_email || '',
        endereco_imovel: p.endereco_imovel || '', validade_dias: p.validade_dias || 15,
        observacoes: p.observacoes || '', anexos: p.anexos || [], cliente_id: p.cliente_id || '',
        etapas_concluidas: p.etapas_concluidas || {}, etapas_concluidas_em: p.etapas_concluidas_em || {},
        dados_imovel: { ...defaultsDe(sch), ...(p.dados_imovel || {}) },
      });
    }).catch(() => { toast({ title: 'Proposta não encontrada', variant: 'destructive' }); nav('/dashboard/propostas'); })
      .finally(() => setLoading(false));
  }, [editing, id, nav, toast]);

  const setDado = (k, v) => setForm((f) => ({ ...f, dados_imovel: { ...f.dados_imovel, [k]: v } }));
  const setDados = (patch) => setForm((f) => ({ ...f, dados_imovel: { ...f.dados_imovel, ...patch } }));

  useEffect(() => {
    if (loading) return;
    if (debRef.current) clearTimeout(debRef.current);
    debRef.current = setTimeout(async () => {
      setCalc(true);
      let ok = false;
      try { setPreview(await propostasAPI.preview(subtipo, form.dados_imovel)); ok = true; }
      catch (e) { setPreview({ erro: e.response?.data?.detail || 'Erro no cálculo' }); }
      finally { setCalc(false); }
      if (ok) {
        try {
          const blob = await propostasAPI.previewPdf(subtipo, form.dados_imovel);
          const u = URL.createObjectURL(blob);
          if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current);
          pdfUrlRef.current = u; setPdfUrl(u);
        } catch { /* mantém o último PDF válido */ }
      }
    }, 700);
    return () => debRef.current && clearTimeout(debRef.current);
  }, [subtipo, form.dados_imovel, loading]);

  // Geometria + croqui ao vivo (só demarcação, a partir de 3 vértices)
  const ehDemarcacao = SUBTIPOS_DEMARCACAO.includes(subtipo);
  const pontos = useMemo(
    () => (Array.isArray(form.dados_imovel.pontos) ? form.dados_imovel.pontos : []), [form.dados_imovel.pontos]);
  const alinhaLados = useMemo(
    () => (Array.isArray(form.dados_imovel.alinhamento_lados) ? form.dados_imovel.alinhamento_lados.map(Number) : []),
    [form.dados_imovel.alinhamento_lados]);

  useEffect(() => {
    if (!ehDemarcacao || pontos.length < 3) { setGeo(null); setCroqui(''); return; }
    if (geoRef.current) clearTimeout(geoRef.current);
    geoRef.current = setTimeout(async () => {
      try { setGeo(await propostasAPI.geometria(pontos, alinhaLados)); } catch { setGeo(null); }
      try {
        const r = await propostasAPI.croquiSvg(pontos, alinhaLados,
          alinhaLados.length ? 'Cerca a ser alinhada' : null);
        setCroqui(r?.svg || '');
      } catch { setCroqui(''); }
    }, 500);
    return () => geoRef.current && clearTimeout(geoRef.current);
  }, [ehDemarcacao, pontos, alinhaLados]);

  const salvar = useCallback(async () => {
    setSaving(true);
    try {
      const payload = { ...form, subtipo };
      const r = editing ? await propostasAPI.atualizar(id, payload) : await propostasAPI.criar(payload);
      toast({ title: editing ? 'Proposta atualizada' : `Proposta ${r.numero} criada` });
      nav(`/dashboard/propostas/${r.id}`);
    } catch (e) { toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setSaving(false); }
  }, [form, subtipo, editing, id, nav, toast]);

  // "Etapa concluída" da proposta (marca + carimba; persiste na hora quando já existe)
  const marcarConcluida = (stepIndex, checked) => {
    const next = {
      ...form,
      etapas_concluidas: { ...(form.etapas_concluidas || {}), [stepIndex]: checked },
      etapas_concluidas_em: { ...(form.etapas_concluidas_em || {}), [stepIndex]: checked ? new Date().toISOString() : null },
    };
    setForm(next);
    if (editing) {
      propostasAPI.atualizar(id, { ...next, subtipo }).catch(() => {});
    }
  };

  const camposVisiveis = useMemo(
    () => (schema.campos || []).filter((c) => c.key !== 'forma_pagamento_tag' && (!c.when || c.when(form.dados_imovel))),
    [schema, form.dados_imovel]);
  const temPagamentoVisual = subtipo === 'projeto_executivo';
  const COMODOS = useMemo(() => comodosPorCategoria(), []);
  const programa = Array.isArray(form.dados_imovel.programa_necessidades) ? form.dados_imovel.programa_necessidades : [];
  const progMap = useMemo(() => Object.fromEntries(programa.map((p) => [p.codigo, p])), [programa]);
  const toggleComodo = (cm) => {
    const next = progMap[cm.codigo]
      ? programa.filter((p) => p.codigo !== cm.codigo)
      : [...programa, { codigo: cm.codigo, nome: cm.nome, nome_plural: cm.nome_plural, categoria: cm.categoria, ordem_pdf: cm.ordem_pdf, quantidade: 1 }];
    setDado('programa_necessidades', next);
  };
  const setQtd = (codigo, q) => setDado('programa_necessidades',
    programa.map((p) => (p.codigo === codigo ? { ...p, quantidade: Math.max(1, q) } : p)));

  const projetos = Array.isArray(form.dados_imovel.projetos_selecionados) ? form.dados_imovel.projetos_selecionados : PROJETOS_EXECUTIVO_DEFAULT;
  const [projEdit, setProjEdit] = useState(null);
  const updProjetos = (codigo, patch) => setDado('projetos_selecionados',
    projetos.map((p) => (p.codigo === codigo ? { ...p, ...patch } : p)));

  if (loading) return <div className="py-20 flex justify-center"><BrandSpinner label="Carregando…" /></div>;
  const c = preview?.custos;

  const renderCampo = (campo) => {
    const val = form.dados_imovel[campo.key];
    if (campo.type === 'number') {
      return <Input type="number" value={val ?? ''} onChange={(e) => setDado(campo.key, e.target.value === '' ? 0 : parseFloat(e.target.value))} />;
    }
    if (campo.type === 'select') {
      const cur = campo._bool ? String(!!val) : val;
      return (
        <select value={cur} onChange={(e) => setDado(campo.key, campo._bool ? e.target.value === 'true' : e.target.value)}
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400">
          {campo.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    return <Input value={val ?? ''} onChange={(e) => setDado(campo.key, e.target.value)} />;
  };

  const LABEL_CLS = 'text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1';
  const peGrupo = (g) => camposVisiveis.filter((x) => x.grupo === g);
  const gridCampos = (campos) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {campos.map((campo) => <Field key={campo.key} label={campo.label}>{renderCampo(campo)}</Field>)}
    </div>
  );

  // ── Conteúdo de cada etapa (seções) ──────────────────────────────────────
  const secCliente = (
    <div className="space-y-4">
      <div className={LABEL_CLS}>Cliente</div>
      <div className="flex items-end gap-2">
        <Field label="Selecionar cliente cadastrado" className="flex-1">
          <select value={form.cliente_id || ''} onChange={(e) => selecionarCliente(e.target.value)}
            className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400">
            <option value="">— Selecione (ou preencha manualmente) —</option>
            {clientes.map((cl) => (<option key={cl.id} value={cl.id}>{cl.name || cl.nome}{(cl.doc || cl.cpf_cnpj) ? ` · ${cl.doc || cl.cpf_cnpj}` : ''}</option>))}
          </select>
        </Field>
        <Button type="button" variant="outline" className="h-9 whitespace-nowrap" onClick={() => window.open('/dashboard/clientes', '_blank')}>+ Novo</Button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Nome / Razão social"><Input value={form.cliente_nome} onChange={(e) => setForm((f) => ({ ...f, cliente_nome: e.target.value }))} /></Field>
        <Field label="CPF / CNPJ"><Input value={form.cliente_cpf_cnpj} onChange={(e) => setForm((f) => ({ ...f, cliente_cpf_cnpj: e.target.value }))} /></Field>
        <Field label="Telefone"><Input value={form.cliente_telefone} onChange={(e) => setForm((f) => ({ ...f, cliente_telefone: e.target.value }))} /></Field>
        <Field label="E-mail"><Input value={form.cliente_email} onChange={(e) => setForm((f) => ({ ...f, cliente_email: e.target.value }))} /></Field>
        <Field label="Endereço do imóvel / obra" className="sm:col-span-2"><Input value={form.endereco_imovel} onChange={(e) => setForm((f) => ({ ...f, endereco_imovel: e.target.value }))} /></Field>
      </div>
    </div>
  );
  const secParametros = (
    <div>
      <div className={`${LABEL_CLS} mb-2`}>📐 Parâmetros do Imóvel / Obra</div>
      {gridCampos(peGrupo('parametros'))}
    </div>
  );
  const secServico = (
    <div>
      <div className={LABEL_CLS}>Dados do serviço (cálculo)</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
        {camposVisiveis.map((campo) => <Field key={campo.key} label={campo.label}>{renderCampo(campo)}</Field>)}
      </div>
    </div>
  );
  const secPrograma = (
    <div>
      <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-1">🏗 Programa de necessidades — cômodos da edificação</div>
      <p className="text-[11px] text-gray-400 mb-2">Marque os cômodos do projeto. {programa.length > 0 ? `${programa.reduce((s, p) => s + (p.quantidade || 1), 0)} cômodo(s) selecionado(s).` : 'Nenhum cômodo selecionado ainda.'}</p>
      <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
        {ORDEM_CATEGORIAS.map((cat) => (
          <div key={cat}>
            <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-wide mb-1">{CATEGORIAS_LABEL[cat]}</div>
            <div className="flex flex-wrap gap-1.5">
              {COMODOS[cat].map((cm) => {
                const sel = progMap[cm.codigo];
                return (
                  <span key={cm.codigo} className={`inline-flex items-center gap-1 rounded-full border text-[11px] font-medium transition ${sel ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-700 border-gray-200 hover:border-emerald-300'}`}>
                    <button type="button" onClick={() => toggleComodo(cm)} className="px-2.5 py-1">{cm.icone} {cm.nome}</button>
                    {sel && (
                      <span className="flex items-center gap-0.5 pr-1.5">
                        <button type="button" onClick={() => setQtd(cm.codigo, (sel.quantidade || 1) - 1)} className="w-4 h-4 leading-none rounded-full bg-white/25 hover:bg-white/40">−</button>
                        <span className="min-w-[14px] text-center">{sel.quantidade || 1}</span>
                        <button type="button" onClick={() => setQtd(cm.codigo, (sel.quantidade || 1) + 1)} className="w-4 h-4 leading-none rounded-full bg-white/25 hover:bg-white/40">+</button>
                      </span>
                    )}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
  const secProjetos = (
    <div>
      <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">📋 Projetos a entregar</div>
      <div className="space-y-1.5">
        {projetos.map((p) => (
          <div key={p.codigo} className="border border-gray-100 rounded-lg p-2">
            <div className="flex items-center gap-2">
              <input type="checkbox" checked={!!p.selecionado} onChange={(e) => updProjetos(p.codigo, { selecionado: e.target.checked })} className="w-4 h-4 accent-emerald-600" />
              <span className="text-sm font-medium text-gray-800 flex-1">{p.nome}</span>
              <button type="button" onClick={() => setProjEdit(projEdit === p.codigo ? null : p.codigo)} className="text-[11px] text-emerald-700 hover:underline">{projEdit === p.codigo ? 'fechar' : 'editar detalhamento'}</button>
            </div>
            {projEdit === p.codigo && (
              <textarea value={p.detalhamento_entrega || ''} onChange={(e) => updProjetos(p.codigo, { detalhamento_entrega: e.target.value })} rows={4} className="w-full mt-2 rounded-lg border border-gray-200 px-2 py-1.5 text-[12px] leading-snug" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
  const secResponsabilidade = (
    <div>
      <div className={`${LABEL_CLS} mb-2`}>⚖️ Responsabilidade Técnica</div>
      {gridCampos(peGrupo('responsabilidade'))}
    </div>
  );
  const secDespesas = (
    <div>
      <div className={`${LABEL_CLS} mb-2`}>💼 Despesas Administrativas (opcionais — pagas à parte, fora das parcelas 50/50)</div>
      {gridCampos(peGrupo('despesas'))}
    </div>
  );
  const secPagamento = (
    <div>
      <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">💳 Forma de pagamento dos honorários</div>
      <div className="flex flex-wrap gap-2">
        {PAGAMENTO_TAGS.map((p) => {
          const ativo = (form.dados_imovel.forma_pagamento_tag || 'sinal_mais_1') === p.tag;
          return (
            <button key={p.tag} type="button" onClick={() => setDado('forma_pagamento_tag', p.tag)} className={`px-3 py-2 rounded-xl text-xs font-semibold border transition ${ativo ? 'bg-emerald-600 text-white border-emerald-600 shadow' : 'bg-white text-gray-700 border-gray-200 hover:border-emerald-300'}`}>{p.icon} {p.label}</button>
          );
        })}
      </div>
      {(form.dados_imovel.forma_pagamento_tag === 'personalizada') && (
        <textarea value={form.dados_imovel.forma_pagamento_custom || ''} onChange={(e) => setDado('forma_pagamento_custom', e.target.value)} placeholder="Descreva a condição de pagamento combinada…" className="w-full mt-2 rounded-xl border border-gray-200 px-3 py-2 text-sm" rows={2} />
      )}
      {c?.condicoes_pagamento?.length > 0 && (
        <div className="mt-2 bg-emerald-50 border border-emerald-100 rounded-lg p-2 text-[11px] text-emerald-900">
          <span className="font-semibold">Pré-visualização: </span>
          {c.condicoes_pagamento.map((p, i) => (<span key={i}>{i > 0 ? ' · ' : ''}{p.rotulo.split('—')[0].trim()} {fmtBRL(p.valor)}</span>))}
        </div>
      )}
    </div>
  );
  // ── Demarcação: Pontos & Croqui ──────────────────────────────────────────
  const importarColetora = async () => {
    const txt = (coletoraTexto || '').trim();
    if (!txt) { toast({ title: 'Cole os pontos da coletora', variant: 'destructive' }); return; }
    setImportando(true);
    try {
      const r = await propostasAPI.coletoraParse(txt, coletoraFmt);
      const pts = Array.isArray(r.pontos) ? r.pontos : [];
      if (pts.length < 3) {
        toast({ title: 'Pontos insuficientes', description: 'São necessários ao menos 3 vértices.', variant: 'destructive' });
        return;
      }
      const res = r.resumo || {};
      // a geometria importada passa a ser a fonte dos parâmetros cobrados
      const patch = {
        pontos: pts, num_vertices: pts.length,
        alinhamento_lados: [], alinhamento_cerca_contratado: false, alinhamento_cerca_metros: 0,
      };
      if (subtipo === 'demarcacao_rural' && res.area_ha) patch.area_hectares = res.area_ha;
      if (subtipo === 'demarcacao_urbana' && res.area_m2) patch.area_m2 = res.area_m2;
      setDados(patch);
      setColetoraTexto('');
      toast({
        title: `${pts.length} pontos importados`,
        description: `Área ${fmtNum(res.area_m2)} m² · perímetro ${fmtNum(res.perimetro_m)} m — nº de vértices e área atualizados.`,
      });
      if ((r.avisos || []).length) toast({ title: 'Avisos da importação', description: r.avisos.join(' · ') });
    } catch (e) {
      toast({ title: 'Falha ao importar', description: e.response?.data?.detail || 'Verifique o formato do arquivo.', variant: 'destructive' });
    } finally { setImportando(false); }
  };

  const lados = geo?.resumo?.lados || [];
  const toggleLado = (ordem) => {
    const sel = alinhaLados.includes(ordem) ? alinhaLados.filter((o) => o !== ordem) : [...alinhaLados, ordem];
    sel.sort((a, b) => a - b);
    const metros = Math.round(lados.filter((l) => sel.includes(l.ordem))
      .reduce((s, l) => s + (l.distancia_m || 0), 0) * 100) / 100;
    setDados({ alinhamento_lados: sel, alinhamento_cerca_contratado: sel.length > 0, alinhamento_cerca_metros: metros });
  };
  const limparPontos = () => setDados({
    pontos: [], alinhamento_lados: [], alinhamento_cerca_contratado: false, alinhamento_cerca_metros: 0,
  });

  const secPontos = (
    <div className="space-y-4">
      <div className={LABEL_CLS}>📍 Pontos & Croqui</div>
      <p className="text-[11px] text-gray-400">
        Cole os pontos da coletora GNSS (ou o KML). O sistema calcula área, perímetro e lados, desenha o croqui
        e o embute no PDF da proposta (item 4.6). Marque os lados de cerca a alinhar para gerar o croqui de
        alinhamento (item 4.7) e cobrar a metragem.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-[1fr_240px] gap-3 items-end">
        <Field label="Pontos da coletora (colar)">
          <textarea value={coletoraTexto} onChange={(e) => setColetoraTexto(e.target.value)} rows={5}
            placeholder={'P1;224062.78;9450853.30\nP2;224087.78;9450853.30\nP3;224087.78;9450841.30'}
            className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm font-mono focus:outline-none focus:border-emerald-400" />
        </Field>
        <div className="space-y-2">
          <Field label="Formato">
            <select value={coletoraFmt} onChange={(e) => setColetoraFmt(e.target.value)}
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400">
              {FORMATOS_COLETORA.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Button type="button" onClick={importarColetora} disabled={importando}
            className="w-full bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
            {importando ? <Loader2 className="w-4 h-4 animate-spin" /> : <MapPin className="w-4 h-4" />} Importar pontos
          </Button>
        </div>
      </div>

      {pontos.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 p-4 text-center text-xs text-gray-400">
          Nenhum ponto importado — o croqui não sai no PDF.
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-semibold text-emerald-800">{pontos.length} vértice(s)</div>
            <Button type="button" variant="outline" className="h-8 text-xs gap-1" onClick={limparPontos}>
              <Trash2 className="w-3.5 h-3.5" /> Limpar pontos
            </Button>
          </div>

          {geo?.resumo && (
            <div className="grid grid-cols-3 gap-2">
              {[['Vértices', geo.resumo.num_vertices],
                ['Área', `${fmtNum(geo.resumo.area_m2)} m² (${fmtNum(geo.resumo.area_ha, 4)} ha)`],
                ['Perímetro', `${fmtNum(geo.resumo.perimetro_m)} m`]].map(([k, v]) => (
                  <div key={k} className="rounded-xl bg-emerald-50/60 border border-emerald-100 px-3 py-2">
                    <div className="text-[10px] uppercase tracking-wide text-emerald-700">{k}</div>
                    <div className="text-sm font-semibold text-gray-800">{v}</div>
                  </div>
                ))}
            </div>
          )}

          {croqui && (
            <div className="rounded-xl border border-gray-200 p-2 bg-white">
              <img src={`data:image/svg+xml;utf8,${encodeURIComponent(croqui)}`} alt="Croqui da poligonal"
                className="w-full h-auto" />
            </div>
          )}

          {lados.length > 0 && (
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">
                Alinhamento de cerca — marque os lados
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {lados.map((l) => {
                  const on = alinhaLados.includes(l.ordem);
                  return (
                    <button key={l.ordem} type="button" onClick={() => toggleLado(l.ordem)}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl border text-xs transition ${on ? 'bg-amber-50 border-amber-300 text-amber-900 font-semibold' : 'bg-white border-gray-200 text-gray-600 hover:border-amber-300'}`}>
                      <span>{on ? '✓ ' : ''}Lado {l.ordem} · {l.vertice_de} → {l.vertice_para}</span>
                      <span className="tabular-nums">{fmtNum(l.distancia_m)} m</span>
                    </button>
                  );
                })}
              </div>
              {geo?.alinhamento && (
                <div className="mt-2 rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900">
                  Cerca a alinhar: <strong>{fmtNum(geo.alinhamento.extensao_m)} m</strong> ×{' '}
                  {fmtBRL(geo.alinhamento.valor_unitario)}/m = <strong>{fmtBRL(geo.alinhamento.valor)}</strong>
                  <span className="text-amber-700"> — item direto, já somado no total.</span>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );

  const secPrazos = (
    <div>
      <div className={`${LABEL_CLS} mb-2`}>📋 Prazos e observações</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Field label="Validade da proposta (dias)">
          <Input type="number" value={form.validade_dias} onChange={(e) => setForm((f) => ({ ...f, validade_dias: parseInt(e.target.value) || 15 }))} />
        </Field>
      </div>
      <Field label="Observações (saem no rodapé do PDF)" className="mt-3">
        <textarea value={form.observacoes || ''} onChange={(e) => setForm((f) => ({ ...f, observacoes: e.target.value }))} rows={3} placeholder="Prazos de entrega, condições especiais, ressalvas…" className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400" />
      </Field>
    </div>
  );
  const secAnexos = (
    <div>
      <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">📎 Anexos da proposta</div>
      <p className="text-[11px] text-gray-400 mb-2">Croqui, imagens de referência, documentos. Saem anexados ao fim do PDF (JPG/PNG/WEBP/PDF).</p>
      <ImageUploader images={form.anexos || []} onImagesChange={(ids) => setForm((f) => ({ ...f, anexos: ids }))} maxImages={10} label="Anexos" accept="image/jpeg,image/jpg,image/png,image/webp,application/pdf" />
    </div>
  );

  const etapas = temPagamentoVisual ? [
    { key: 'cliente', label: 'Cliente', node: secCliente },
    { key: 'parametros', label: 'Parâmetros', node: secParametros },
    { key: 'programa', label: 'Programa', node: secPrograma },
    { key: 'projetos', label: 'Projetos', node: secProjetos },
    { key: 'responsabilidade', label: 'Resp. Técnica', node: secResponsabilidade },
    { key: 'despesas', label: 'Despesas', node: secDespesas },
    { key: 'pagamento', label: 'Pagamento', node: secPagamento },
    { key: 'prazos', label: 'Prazos & Obs.', node: secPrazos },
    { key: 'anexos', label: 'Anexos', node: secAnexos },
  ] : [
    { key: 'cliente', label: 'Cliente', node: secCliente },
    { key: 'servico', label: 'Serviço', node: secServico },
    ...(ehDemarcacao ? [{ key: 'pontos', label: 'Pontos & Croqui', node: secPontos }] : []),
    { key: 'prazos', label: 'Prazos & Obs.', node: secPrazos },
    { key: 'anexos', label: 'Anexos', node: secAnexos },
  ];
  const sClamp = Math.min(step, etapas.length - 1);
  const etapaAtual = etapas[sClamp];
  const ultimo = sClamp === etapas.length - 1;
  const pctEtapas = Math.round(((sClamp + 1) / etapas.length) * 100);

  return (
    <div className="max-w-5xl mx-auto pb-24 space-y-5">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => nav('/dashboard/propostas')}><ArrowLeft className="w-4 h-4 mr-1" /> Propostas</Button>
        <Button onClick={salvar} disabled={saving || !!preview?.erro} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} {editing ? 'Salvar' : 'Criar proposta'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-5">
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
          <div className="flex items-center justify-between gap-3">
            <div className="font-display text-xl font-bold text-gray-900">{schema.titulo}</div>
            <div className="text-[11px] font-semibold text-emerald-700 whitespace-nowrap">Etapa {sClamp + 1} de {etapas.length}</div>
          </div>

          {/* Barra de progresso + chips de etapa */}
          <div>
            <div className="h-1.5 w-full bg-emerald-50 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 transition-all duration-300" style={{ width: `${pctEtapas}%` }} />
            </div>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {etapas.map((et, i) => {
                const feito = !!(form.etapas_concluidas || {})[i];
                const ativo = i === sClamp;
                return (
                  <button key={et.key} type="button" onClick={() => setStep(i)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border transition ${ativo ? 'bg-emerald-600 text-white border-emerald-600' : feito ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-white text-gray-500 border-gray-200 hover:border-emerald-300'}`}>
                    {feito ? '✓ ' : ''}{i + 1}. {et.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="min-h-[280px]">{etapaAtual.node}</div>

          <EtapaConcluidaBox
            stepIndex={sClamp}
            label={`${etapaAtual.label} — ${schema.titulo}`}
            form={form}
            onToggle={marcarConcluida}
            entidade="proposta"
          />

          {/* Navegação do wizard */}
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <Button type="button" variant="outline" disabled={sClamp === 0}
              onClick={() => setStep((s) => Math.max(0, s - 1))} className="gap-1">
              <ArrowLeft className="w-4 h-4" /> Voltar
            </Button>
            {ultimo ? (
              <Button onClick={salvar} disabled={saving || !!preview?.erro} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} {editing ? 'Salvar' : 'Criar proposta'}
              </Button>
            ) : (
              <Button type="button" onClick={() => setStep((s) => Math.min(etapas.length - 1, s + 1))}
                className="bg-emerald-700 hover:bg-emerald-800 text-white gap-1">
                Avançar <ChevronRight className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Preview ao vivo */}
        <div className="space-y-3">
          <div className="bg-emerald-900 text-white rounded-xl p-5 sticky top-2">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-emerald-200">
              <Calculator className="w-4 h-4" /> Valor da proposta {calc && <Loader2 className="w-3 h-3 animate-spin" />}
            </div>
            {preview?.erro ? (
              <div className="text-amber-200 text-sm mt-2">{preview.erro}</div>
            ) : (
              <>
                <div className="font-display text-3xl font-bold mt-1">{fmtBRL(preview?.valor_total)}</div>
                {c && (
                  <div className="mt-3 space-y-2 text-xs">
                    {c.secao_2_taxas?.length > 0 && <div className="text-emerald-200 font-semibold uppercase">Taxas de terceiros</div>}
                    {(c.secao_2_taxas || []).map((i) => (
                      <div key={i.ordem} className="flex justify-between gap-2"><span className="text-emerald-100/80 truncate">{i.descricao.split('—')[0]}</span><span>{fmtBRL(i.valor)}</span></div>
                    ))}
                    <div className="text-emerald-200 font-semibold uppercase pt-1">Honorários Romatec</div>
                    {(c.secao_3_honorarios || []).map((i) => (
                      <div key={i.ordem} className="flex justify-between gap-2"><span className="text-emerald-100/80 truncate">{i.descricao.split('—')[0]}</span><span>{fmtBRL(i.valor)}</span></div>
                    ))}
                    {c.condicoes_pagamento?.length > 0 && (
                      <>
                        <div className="text-emerald-200 font-semibold uppercase pt-1">Condições</div>
                        {c.condicoes_pagamento.map((p, idx) => (
                          <div key={idx} className="flex justify-between gap-2"><span className="text-emerald-100/80 truncate">{p.rotulo.split('—')[0]}</span><span>{fmtBRL(p.valor)}</span></div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
          {c?.avisos?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-[11px] text-amber-800 max-h-48 overflow-y-auto">
              {c.avisos.slice(0, 2).map((a, i) => <p key={i} className="mb-1">{a.slice(0, 220)}{a.length > 220 ? '…' : ''}</p>)}
            </div>
          )}

          {/* Pré-visualização do PDF (ao vivo — é exatamente o PDF que será gerado) */}
          {!preview?.erro && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-emerald-800 px-3 py-2 border-b border-gray-100">
                <FileText className="w-3.5 h-3.5" /> Pré-visualização do PDF
              </div>
              {pdfUrl ? (
                <iframe title="Prévia da proposta" src={`${pdfUrl}#toolbar=0&navpanes=0`}
                  style={{ width: '100%', height: 460, border: 0 }} />
              ) : (
                <div className="h-[460px] flex items-center justify-center text-gray-400 text-xs">
                  <Loader2 className="w-4 h-4 animate-spin mr-2" /> Gerando prévia…
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PropostaForm;
