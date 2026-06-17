// @module dashboard/propostas/PropostaForm — Form de proposta (schema-driven) com preview ao vivo.
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader2, Calculator, FileText } from 'lucide-react';
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
    ],
  },
  projeto_executivo: {
    titulo: 'Projeto Executivo',
    campos: [
      N('area_construir', 'Área a construir (m²)'),
      N('area_terreno', 'Área do terreno (m²) — opcional'),
      N('valor_m2', 'Valor por m² (R$)', 25),
      BOOL('responsabilidade_auto', 'ART/TRT automático por área?', true, ['Não (escolher)', 'Sim (> 80m² = ART)']),
      { ...SEL('responsabilidade_tipo', 'Responsabilidade técnica', [
        { value: 'ART', label: 'ART CREA-MA (R$ 233,94)' }, { value: 'TRT', label: 'TRT CFT/MA (R$ 93,40)' }], 'TRT'),
        when: (d) => d.responsabilidade_auto === false },
      N('desconto_honorarios', 'Desconto sobre honorários (R$)'),
      SEL('forma_pagamento_tag', 'Forma de pagamento', [
        { value: 'sinal_mais_1', label: '50% sinal + 50% entrega' }, { value: 'integral', label: 'À vista (100%)' },
        { value: 'sinal_mais_2', label: 'Sinal + 2× na entrega' }, { value: 'duas_vezes', label: '2× iguais' },
        { value: 'personalizada', label: 'Personalizada' }], 'sinal_mais_1'),
      BOOL('diligencia_incluir', 'Diligência na Secretaria (despesa)?'),
      { ...N('diligencia_valor', 'Valor da diligência (R$)'), when: (d) => !!d.diligencia_incluir },
      BOOL('alvara_incluir', 'Taxa de Alvará de Construção (despesa)?'),
      { ...N('alvara_valor', 'Valor do alvará (R$)'), when: (d) => !!d.alvara_incluir },
      BOOL('placa_incluir', 'Placa de Obra (despesa)?'),
      { ...N('placa_valor', 'Valor da placa (R$)'), when: (d) => !!d.placa_incluir },
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
  const debRef = useRef(null);
  const pdfUrlRef = useRef(null);

  useEffect(() => () => { if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current); }, []);
  useEffect(() => { clientsAPI.list().then(setClientes).catch(() => {}); }, []);

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
  const programa = form.dados_imovel.programa_necessidades || [];
  const progMap = useMemo(() => Object.fromEntries(programa.map((p) => [p.codigo, p])), [programa]);
  const toggleComodo = (cm) => {
    const next = progMap[cm.codigo]
      ? programa.filter((p) => p.codigo !== cm.codigo)
      : [...programa, { codigo: cm.codigo, nome: cm.nome, nome_plural: cm.nome_plural, categoria: cm.categoria, ordem_pdf: cm.ordem_pdf, quantidade: 1 }];
    setDado('programa_necessidades', next);
  };
  const setQtd = (codigo, q) => setDado('programa_necessidades',
    programa.map((p) => (p.codigo === codigo ? { ...p, quantidade: Math.max(1, q) } : p)));

  const projetos = form.dados_imovel.projetos_selecionados || PROJETOS_EXECUTIVO_DEFAULT;
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

  return (
    <div className="max-w-5xl mx-auto pb-24 space-y-5">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => nav('/dashboard/propostas')}><ArrowLeft className="w-4 h-4 mr-1" /> Voltar</Button>
        <Button onClick={salvar} disabled={saving || !!preview?.erro} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} {editing ? 'Salvar' : 'Criar proposta'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-5">
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
          <div className="font-display text-xl font-bold text-gray-900">{schema.titulo}</div>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Cliente</div>
          <div className="flex items-end gap-2">
            <Field label="Selecionar cliente cadastrado" className="flex-1">
              <select
                value={form.cliente_id || ''}
                onChange={(e) => selecionarCliente(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400">
                <option value="">— Selecione (ou preencha manualmente) —</option>
                {clientes.map((c) => (
                  <option key={c.id} value={c.id}>{c.name || c.nome}{(c.doc || c.cpf_cnpj) ? ` · ${c.doc || c.cpf_cnpj}` : ''}</option>
                ))}
              </select>
            </Field>
            <Button type="button" variant="outline" className="h-9 whitespace-nowrap"
              onClick={() => window.open('/dashboard/clientes', '_blank')}>+ Novo</Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Nome / Razão social"><Input value={form.cliente_nome} onChange={(e) => setForm((f) => ({ ...f, cliente_nome: e.target.value }))} /></Field>
            <Field label="CPF / CNPJ"><Input value={form.cliente_cpf_cnpj} onChange={(e) => setForm((f) => ({ ...f, cliente_cpf_cnpj: e.target.value }))} /></Field>
            <Field label="Telefone"><Input value={form.cliente_telefone} onChange={(e) => setForm((f) => ({ ...f, cliente_telefone: e.target.value }))} /></Field>
            <Field label="E-mail"><Input value={form.cliente_email} onChange={(e) => setForm((f) => ({ ...f, cliente_email: e.target.value }))} /></Field>
            <Field label="Endereço do imóvel"><Input value={form.endereco_imovel} onChange={(e) => setForm((f) => ({ ...f, endereco_imovel: e.target.value }))} /></Field>
            <Field label="Validade (dias)"><Input type="number" value={form.validade_dias} onChange={(e) => setForm((f) => ({ ...f, validade_dias: parseInt(e.target.value) || 15 }))} /></Field>
          </div>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Dados do serviço (cálculo)</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {camposVisiveis.map((campo) => <Field key={campo.key} label={campo.label}>{renderCampo(campo)}</Field>)}
          </div>

          {temPagamentoVisual && (
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">Projetos a entregar</div>
              <div className="space-y-1.5">
                {projetos.map((p) => (
                  <div key={p.codigo} className="border border-gray-100 rounded-lg p-2">
                    <div className="flex items-center gap-2">
                      <input type="checkbox" checked={!!p.selecionado} onChange={(e) => updProjetos(p.codigo, { selecionado: e.target.checked })}
                        className="w-4 h-4 accent-emerald-600" />
                      <span className="text-sm font-medium text-gray-800 flex-1">{p.nome}</span>
                      <button type="button" onClick={() => setProjEdit(projEdit === p.codigo ? null : p.codigo)}
                        className="text-[11px] text-emerald-700 hover:underline">{projEdit === p.codigo ? 'fechar' : 'editar detalhamento'}</button>
                    </div>
                    {projEdit === p.codigo && (
                      <textarea value={p.detalhamento_entrega || ''} onChange={(e) => updProjetos(p.codigo, { detalhamento_entrega: e.target.value })}
                        rows={4} className="w-full mt-2 rounded-lg border border-gray-200 px-2 py-1.5 text-[12px] leading-snug" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {temPagamentoVisual && (
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-1">Programa de necessidades — cômodos da edificação</div>
              <p className="text-[11px] text-gray-400 mb-2">Marque os cômodos do projeto. {programa.length > 0 ? `${programa.reduce((s, p) => s + (p.quantidade || 1), 0)} cômodo(s) selecionado(s).` : 'Nenhum cômodo selecionado ainda.'}</p>
              <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                {ORDEM_CATEGORIAS.map((cat) => (
                  <div key={cat}>
                    <div className="text-[10px] font-bold text-emerald-700 uppercase tracking-wide mb-1">{CATEGORIAS_LABEL[cat]}</div>
                    <div className="flex flex-wrap gap-1.5">
                      {COMODOS[cat].map((cm) => {
                        const sel = progMap[cm.codigo];
                        return (
                          <span key={cm.codigo}
                            className={`inline-flex items-center gap-1 rounded-full border text-[11px] font-medium transition ${sel ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-700 border-gray-200 hover:border-emerald-300'}`}>
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
          )}

          {temPagamentoVisual && (
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">Forma de pagamento dos honorários</div>
              <div className="flex flex-wrap gap-2">
                {PAGAMENTO_TAGS.map((p) => {
                  const ativo = (form.dados_imovel.forma_pagamento_tag || 'sinal_mais_1') === p.tag;
                  return (
                    <button key={p.tag} type="button" onClick={() => setDado('forma_pagamento_tag', p.tag)}
                      className={`px-3 py-2 rounded-xl text-xs font-semibold border transition ${ativo ? 'bg-emerald-600 text-white border-emerald-600 shadow' : 'bg-white text-gray-700 border-gray-200 hover:border-emerald-300'}`}>
                      {p.icon} {p.label}
                    </button>
                  );
                })}
              </div>
              {(form.dados_imovel.forma_pagamento_tag === 'personalizada') && (
                <textarea
                  value={form.dados_imovel.forma_pagamento_custom || ''}
                  onChange={(e) => setDado('forma_pagamento_custom', e.target.value)}
                  placeholder="Descreva a condição de pagamento combinada…"
                  className="w-full mt-2 rounded-xl border border-gray-200 px-3 py-2 text-sm" rows={2} />
              )}
              {c?.condicoes_pagamento?.length > 0 && (
                <div className="mt-2 bg-emerald-50 border border-emerald-100 rounded-lg p-2 text-[11px] text-emerald-900">
                  <span className="font-semibold">Pré-visualização: </span>
                  {c.condicoes_pagamento.map((p, i) => (
                    <span key={i}>{i > 0 ? ' · ' : ''}{p.rotulo.split('—')[0].trim()} {fmtBRL(p.valor)}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          <div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1 mb-2">Anexos da proposta</div>
            <p className="text-[11px] text-gray-400 mb-2">Croqui, imagens de referência, documentos. Saem anexados ao fim do PDF (JPG/PNG/WEBP/PDF).</p>
            <ImageUploader
              images={form.anexos || []}
              onImagesChange={(ids) => setForm((f) => ({ ...f, anexos: ids }))}
              maxImages={10}
              label="Anexos"
              accept="image/jpeg,image/jpg,image/png,image/webp,application/pdf"
            />
          </div>

          <EtapaConcluidaBox
            stepIndex={0}
            label={schema.titulo || 'Proposta'}
            form={form}
            onToggle={marcarConcluida}
            entidade="proposta"
          />
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
