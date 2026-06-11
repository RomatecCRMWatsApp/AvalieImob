// @module dashboard/propostas/PropostaForm — Form de proposta (averbação) com preview ao vivo.
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Loader2, Calculator } from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { useToast } from '../../../hooks/use-toast';
import { propostasAPI } from '../../../lib/api';

const fmtBRL = (v) => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const Field = ({ label, children }) => (
  <div className="space-y-1">
    <label className="text-xs font-medium text-gray-600">{label}</label>
    {children}
  </div>
);
const Sel = ({ value, onChange, options }) => (
  <select value={value} onChange={(e) => onChange(e.target.value)}
    className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400">
    {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
  </select>
);

const DEFAULT_DADOS = {
  area_construida: 0, valor_venal_imovel: 0, padrao_construtivo: 'normal',
  responsavel: 'PF', apresentar_projetos_complementares: false,
  tem_alvara_construcao: false, anotacao_tecnica: 'art_crea',
  parcelar_inss: false, numero_parcelas_inss: 12,
};

const PropostaForm = () => {
  const { subtipo: subtipoParam, id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const editing = !!id;

  const [subtipo, setSubtipo] = useState(subtipoParam || 'averbacao_residencial');
  const [form, setForm] = useState({
    cliente_nome: '', cliente_cpf_cnpj: '', cliente_telefone: '', cliente_email: '',
    endereco_imovel: '', validade_dias: 15, observacoes: '',
    dados_imovel: { ...DEFAULT_DADOS },
  });
  const [preview, setPreview] = useState(null);
  const [calc, setCalc] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(editing);
  const debRef = useRef(null);

  const isComercial = subtipo === 'averbacao_comercial';

  // Carrega proposta existente (edição)
  useEffect(() => {
    if (!editing) return;
    propostasAPI.get(id).then((p) => {
      setSubtipo(p.subtipo);
      setForm({
        cliente_nome: p.cliente_nome || '', cliente_cpf_cnpj: p.cliente_cpf_cnpj || '',
        cliente_telefone: p.cliente_telefone || '', cliente_email: p.cliente_email || '',
        endereco_imovel: p.endereco_imovel || '', validade_dias: p.validade_dias || 15,
        observacoes: p.observacoes || '', dados_imovel: { ...DEFAULT_DADOS, ...(p.dados_imovel || {}) },
      });
    }).catch(() => { toast({ title: 'Proposta não encontrada', variant: 'destructive' }); nav('/dashboard/propostas'); })
      .finally(() => setLoading(false));
  }, [editing, id, nav, toast]);

  const setDado = (k, v) => setForm((f) => ({ ...f, dados_imovel: { ...f.dados_imovel, [k]: v } }));

  // Preview ao vivo (debounce 600ms)
  useEffect(() => {
    if (loading) return;
    if (debRef.current) clearTimeout(debRef.current);
    debRef.current = setTimeout(async () => {
      setCalc(true);
      try {
        const r = await propostasAPI.preview(subtipo, form.dados_imovel);
        setPreview(r);
      } catch (e) {
        setPreview({ erro: e.response?.data?.detail || 'Erro no cálculo' });
      } finally { setCalc(false); }
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
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  }, [form, subtipo, editing, id, nav, toast]);

  if (loading) return <div className="py-20 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-emerald-700" /></div>;

  const c = preview?.custos;

  return (
    <div className="max-w-5xl mx-auto pb-24 space-y-5">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => nav('/dashboard/propostas')}><ArrowLeft className="w-4 h-4 mr-1" /> Voltar</Button>
        <Button onClick={salvar} disabled={saving || !!preview?.erro} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} {editing ? 'Salvar' : 'Criar proposta'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-5">
        {/* Form */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
          <div>
            <div className="font-display text-xl font-bold text-gray-900">{isComercial ? 'Averbação Comercial' : 'Averbação Residencial'}</div>
            <div className="text-sm text-gray-500">Honorários R$ {isComercial ? '25' : '15'}/m² + assessoria 1 SM. Taxas TJMA + INSS/SERO calculadas.</div>
          </div>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Cliente</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Nome / Razão social"><Input value={form.cliente_nome} onChange={(e) => setForm((f) => ({ ...f, cliente_nome: e.target.value }))} /></Field>
            <Field label="CPF / CNPJ"><Input value={form.cliente_cpf_cnpj} onChange={(e) => setForm((f) => ({ ...f, cliente_cpf_cnpj: e.target.value }))} /></Field>
            <Field label="Telefone"><Input value={form.cliente_telefone} onChange={(e) => setForm((f) => ({ ...f, cliente_telefone: e.target.value }))} /></Field>
            <Field label="E-mail"><Input value={form.cliente_email} onChange={(e) => setForm((f) => ({ ...f, cliente_email: e.target.value }))} /></Field>
            <Field label="Endereço do imóvel"><Input value={form.endereco_imovel} onChange={(e) => setForm((f) => ({ ...f, endereco_imovel: e.target.value }))} /></Field>
            <Field label="Validade (dias)"><Input type="number" value={form.validade_dias} onChange={(e) => setForm((f) => ({ ...f, validade_dias: parseInt(e.target.value) || 15 }))} /></Field>
          </div>

          <div className="text-[11px] font-bold uppercase tracking-wide text-emerald-800 border-b border-emerald-100 pb-1">Dados da obra (cálculo)</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Área construída (m²)"><Input type="number" value={form.dados_imovel.area_construida} onChange={(e) => setDado('area_construida', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Valor venal do imóvel (R$)"><Input type="number" value={form.dados_imovel.valor_venal_imovel} onChange={(e) => setDado('valor_venal_imovel', parseFloat(e.target.value) || 0)} /></Field>
            <Field label="Padrão construtivo">
              <Sel value={form.dados_imovel.padrao_construtivo} onChange={(v) => setDado('padrao_construtivo', v)}
                options={[{ value: 'popular', label: 'Popular' }, { value: 'normal', label: 'Normal' }, { value: 'alto', label: 'Alto' }]} />
            </Field>
            <Field label="Responsável pela obra">
              <Sel value={form.dados_imovel.responsavel} onChange={(v) => setDado('responsavel', v)}
                options={[{ value: 'PF', label: 'Pessoa Física' }, { value: 'PJ_sem_contabilidade', label: 'PJ sem contabilidade' }, { value: 'PJ_com_contabilidade', label: 'PJ com contabilidade (sem SERO)' }]} />
            </Field>
            <Field label="Anotação técnica">
              <Sel value={form.dados_imovel.anotacao_tecnica} onChange={(v) => setDado('anotacao_tecnica', v)}
                options={[{ value: 'art_crea', label: 'ART CREA-MA' }, { value: 'rrt_cau', label: 'RRT CAU/MA' }, { value: 'trt_cft', label: 'TRT CFT/MA' }]} />
            </Field>
            <Field label="Já possui alvará de construção?">
              <Sel value={String(form.dados_imovel.tem_alvara_construcao)} onChange={(v) => setDado('tem_alvara_construcao', v === 'true')}
                options={[{ value: 'false', label: 'Não (cobra alvará)' }, { value: 'true', label: 'Sim' }]} />
            </Field>
            {!isComercial && (
              <Field label="Projetos complementares (pacote completo)?">
                <Sel value={String(form.dados_imovel.apresentar_projetos_complementares)} onChange={(v) => setDado('apresentar_projetos_complementares', v === 'true')}
                  options={[{ value: 'false', label: 'Não (2 projetos)' }, { value: 'true', label: 'Sim (7 projetos)' }]} />
              </Field>
            )}
            <Field label="Parcelar INSS/SERO com a Receita?">
              <Sel value={String(form.dados_imovel.parcelar_inss)} onChange={(v) => setDado('parcelar_inss', v === 'true')}
                options={[{ value: 'false', label: 'Não' }, { value: 'true', label: 'Sim' }]} />
            </Field>
            {form.dados_imovel.parcelar_inss && (
              <Field label="Nº de parcelas INSS (2–60)"><Input type="number" min={2} max={60} value={form.dados_imovel.numero_parcelas_inss} onChange={(e) => setDado('numero_parcelas_inss', parseInt(e.target.value) || 12)} /></Field>
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
                    <div className="text-emerald-200 font-semibold uppercase">Taxas de terceiros</div>
                    {c.secao_2_taxas.map((i) => (
                      <div key={i.ordem} className="flex justify-between gap-2"><span className="text-emerald-100/80 truncate">{i.descricao.split('—')[0]}</span><span>{fmtBRL(i.valor)}</span></div>
                    ))}
                    <div className="text-emerald-200 font-semibold uppercase pt-1">Honorários Romatec</div>
                    {c.secao_3_honorarios.map((i) => (
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
