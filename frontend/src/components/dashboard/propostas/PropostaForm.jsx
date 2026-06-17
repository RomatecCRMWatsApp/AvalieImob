// @module dashboard/propostas/PropostaForm — Form de proposta (schema-driven) com preview ao vivo.
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader2, Calculator } from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { useToast } from '../../../hooks/use-toast';
import { propostasAPI } from '../../../lib/api';
import EtapaConcluidaBox from '../ptam/EtapaConcluidaBox';

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

const defaultsDe = (schema) => {
  const d = {};
  (schema?.campos || []).forEach((c) => { d[c.key] = c._bool ? (c.def === 'true') : c.def; });
  return d;
};

const Field = ({ label, children }) => (
  <div className="space-y-1"><label className="text-xs font-medium text-gray-600">{label}</label>{children}</div>
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
  const debRef = useRef(null);

  useEffect(() => {
    if (!editing) return;
    propostasAPI.get(id).then((p) => {
      setSubtipo(p.subtipo);
      const sch = SCHEMAS[p.subtipo] || SCHEMAS.averbacao_residencial;
      setForm({
        cliente_nome: p.cliente_nome || '', cliente_cpf_cnpj: p.cliente_cpf_cnpj || '',
        cliente_telefone: p.cliente_telefone || '', cliente_email: p.cliente_email || '',
        endereco_imovel: p.endereco_imovel || '', validade_dias: p.validade_dias || 15,
        observacoes: p.observacoes || '',
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
      try { setPreview(await propostasAPI.preview(subtipo, form.dados_imovel)); }
      catch (e) { setPreview({ erro: e.response?.data?.detail || 'Erro no cálculo' }); }
      finally { setCalc(false); }
    }, 600);
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
    () => (schema.campos || []).filter((c) => !c.when || c.when(form.dados_imovel)),
    [schema, form.dados_imovel]);

  if (loading) return <div className="py-20 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-emerald-700" /></div>;
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
        </div>
      </div>
    </div>
  );
};

export default PropostaForm;
