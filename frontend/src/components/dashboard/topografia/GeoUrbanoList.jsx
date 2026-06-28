// @module topografia/GeoUrbanoList — Lista de projetos de Geo Urbano + criação.
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Plus, Trash2, ChevronRight, MapPin, Sparkles } from 'lucide-react';
import { geoUrbanoAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

export const TIPOS_SERVICO = [
  { value: 'remembramento', label: 'Remembramento (unificação de lotes)', pronto: true },
  { value: 'desdobro', label: 'Desdobro (fracionamento)', pronto: true },
  { value: 'retificacao', label: 'Retificação de área/registro', pronto: true },
  { value: 'reurb', label: 'REURB (regularização fundiária urbana)', pronto: false },
  { value: 'usucapiao', label: 'Usucapião extrajudicial', pronto: false },
];

const STATUS = {
  rascunho: { label: 'Rascunho', cls: 'bg-gray-100 text-gray-600' },
  extracao: { label: 'Extração', cls: 'bg-blue-100 text-blue-700' },
  conferencia: { label: 'Conferência', cls: 'bg-indigo-100 text-indigo-700' },
  assinatura: { label: 'Assinatura', cls: 'bg-amber-100 text-amber-800' },
  concluido: { label: 'Concluído', cls: 'bg-emerald-100 text-emerald-700' },
};

export default function GeoUrbanoList() {
  const nav = useNavigate();
  const { toast } = useToast();
  const [projetos, setProjetos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [novo, setNovo] = useState(false);
  const [form, setForm] = useState({ denominacao_imovel: '', tipo_servico: 'remembramento', tema: 'prime_i' });
  const [criando, setCriando] = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const d = await geoUrbanoAPI.listar();
      setProjetos(Array.isArray(d) ? d : []);
    } catch (e) {
      toast({ title: 'Erro ao carregar projetos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const criar = async () => {
    if (!form.denominacao_imovel.trim()) {
      toast({ title: 'Informe a denominação do imóvel', variant: 'destructive' });
      return;
    }
    setCriando(true);
    try {
      const p = await geoUrbanoAPI.criar(form);
      nav(`/dashboard/topografia/geo-urbano/${p.id}`);
    } catch (e) {
      toast({ title: 'Erro ao criar projeto', variant: 'destructive' });
    } finally {
      setCriando(false);
    }
  };

  const criarSeed = async () => {
    setCriando(true);
    try {
      const p = await geoUrbanoAPI.criarSeed();
      toast({ title: 'Projeto-teste J&G criado' });
      nav(`/dashboard/topografia/geo-urbano/${p.id}`);
    } catch (e) {
      toast({ title: 'Erro ao criar projeto-teste', variant: 'destructive' });
    } finally {
      setCriando(false);
    }
  };

  const excluir = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Excluir este projeto e seus documentos?')) return;
    try {
      await geoUrbanoAPI.excluir(id);
      setProjetos((p) => p.filter((x) => x.id !== id));
      toast({ title: 'Projeto excluído' });
    } catch (err) {
      toast({ title: 'Erro ao excluir', variant: 'destructive' });
    }
  };

  if (loading) return <div className="py-24"><BrandSpinner label="Carregando projetos…" /></div>;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <header className="flex items-start justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
            <Building2 className="w-6 h-6" style={{ color: GOLD }} />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: GREEN }}>Geo Urbano</h1>
            <p className="text-sm text-gray-500">
              Remembramento de lotes urbanos · Requerimento (2 vias), Memorial, Cadeia Dominical e Dossiê.
            </p>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <button
            onClick={() => setNovo(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-white shadow-sm hover:opacity-90"
            style={{ background: GREEN }}
          >
            <Plus className="w-4 h-4" /> Novo projeto
          </button>
          <button
            onClick={criarSeed} disabled={criando}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border hover:bg-amber-50"
            style={{ borderColor: GOLD, color: GREEN }}
          >
            <Sparkles className="w-3.5 h-3.5" /> Projeto-teste J&G
          </button>
        </div>
      </header>

      {novo && (
        <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50/40 p-5">
          <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Novo projeto urbano</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Denominação do imóvel</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Ex.: Lote 01 (remembrado) — Quadra 41 — Parque das Nações"
                value={form.denominacao_imovel}
                onChange={(e) => setForm({ ...form, denominacao_imovel: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de serviço</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                value={form.tipo_servico}
                onChange={(e) => setForm({ ...form, tipo_servico: e.target.value })}
              >
                {TIPOS_SERVICO.map((t) => (
                  <option key={t.value} value={t.value} disabled={!t.pronto}>
                    {t.label}{t.pronto ? '' : ' (em breve)'}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tema do PDF</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                value={form.tema}
                onChange={(e) => setForm({ ...form, tema: e.target.value })}
              >
                <option value="prime_i">Prime I — Elegante (claro, dourado)</option>
                <option value="prime_ii">Prime II — Editorial (verde, faixas)</option>
                <option value="tradicional">Tradicional — Sóbrio (branco)</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={criar} disabled={criando}
              className="px-4 py-2 rounded-lg text-sm font-semibold text-white" style={{ background: GREEN }}>
              {criando ? 'Criando…' : 'Criar e abrir'}
            </button>
            <button onClick={() => setNovo(false)} className="px-4 py-2 rounded-lg text-sm border">Cancelar</button>
          </div>
        </div>
      )}

      {projetos.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <MapPin className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>Nenhum projeto ainda. Crie o primeiro — ou abra o <strong>projeto-teste J&G</strong> para ver tudo pronto.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {projetos.map((p) => {
            const st = STATUS[p.status] || STATUS.rascunho;
            const tipo = TIPOS_SERVICO.find((t) => t.value === p.tipo_servico);
            return (
              <button
                key={p.id}
                onClick={() => nav(`/dashboard/topografia/geo-urbano/${p.id}`)}
                className="text-left rounded-xl border border-gray-200 bg-white p-5 hover:shadow-md hover:border-emerald-300 transition group"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${st.cls}`}>{st.label}</span>
                  <Trash2 onClick={(e) => excluir(p.id, e)}
                    className="w-4 h-4 text-gray-300 hover:text-red-500 shrink-0" />
                </div>
                <div className="font-semibold text-gray-800 group-hover:text-emerald-800 line-clamp-2">
                  {p.denominacao_imovel || 'Sem denominação'}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {p.numero ? `${p.numero} · ` : ''}{tipo?.label || p.tipo_servico}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">
                  {(p.matriculas?.length || 0)} matrícula(s)
                  {p.area_declarada_m2 ? ` · ${Number(p.area_declarada_m2).toLocaleString('pt-BR')} m²` : ''}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex-1 mr-3">
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${p.completude || 0}%`, background: GOLD }} />
                    </div>
                    <span className="text-[10px] text-gray-400">{p.completude || 0}% preenchido</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-emerald-600" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
