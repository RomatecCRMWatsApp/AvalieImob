// @module pages/admin/NovidadesAdmin — Painel admin da Central de Novidades.
import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Loader2, CheckCircle2, BarChart3, Pencil, ArrowLeft, X } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { useToast } from '../../hooks/use-toast';
import { BrandSpinner } from '../../components/brand/BrandSpinner';
import { novidadesAPI } from '../../lib/api';
import MarkdownLite from '../../components/dashboard/novidades/MarkdownLite';

const TAGS = [['novidade', 'Novidade'], ['melhoria', 'Melhoria'], ['correcao', 'Correção'], ['aviso', 'Aviso']];
const ALVOS = [['todos', 'Todos'], ['novos', 'Só novos'], ['existentes', 'Só existentes']];
const VAZIO = {
  slug: '', versao: '', titulo: '', resumo: '', conteudo_md: '', tag: 'novidade',
  imagem_url: '', cta_label: '', cta_rota: '', bloqueante: false, publico_alvo: 'todos',
};

const Campo = ({ label, children }) => (
  <div className="space-y-1"><label className="text-xs font-medium text-gray-600">{label}</label>{children}</div>
);

const NovidadesAdmin = () => {
  const { toast } = useToast();
  const [lista, setLista] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('list');
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState(VAZIO);
  const [saving, setSaving] = useState(false);
  const [metricas, setMetricas] = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try { setLista(await novidadesAPI.adminListar()); }
    catch { toast({ title: 'Falha ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { carregar(); }, [carregar]);

  const abrirNovo = () => { setForm(VAZIO); setEditId(null); setView('form'); };
  const abrirEdit = (n) => { setForm({ ...VAZIO, ...n }); setEditId(n.id); setView('form'); };
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const salvar = async () => {
    if (!form.slug.trim() || !form.titulo.trim()) { toast({ title: 'Slug e título são obrigatórios', variant: 'destructive' }); return; }
    setSaving(true);
    try {
      if (editId) await novidadesAPI.adminEditar(editId, form);
      else await novidadesAPI.adminCriar(form);
      toast({ title: 'Salvo' }); setView('list'); carregar();
    } catch (e) { toast({ title: 'Falha ao salvar', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setSaving(false); }
  };
  const publicar = async (n) => {
    if (!window.confirm(`Publicar "${n.titulo}" para os usuários agora?`)) return;
    try { await novidadesAPI.adminPublicar(n.id); toast({ title: 'Publicada' }); carregar(); }
    catch { toast({ title: 'Falha ao publicar', variant: 'destructive' }); }
  };
  const verMetricas = async (n) => {
    try { setMetricas({ titulo: n.titulo, dados: await novidadesAPI.adminMetricas(n.id) }); }
    catch { toast({ title: 'Falha nas métricas', variant: 'destructive' }); }
  };

  if (loading) return <div className="py-20 flex justify-center"><BrandSpinner label="Carregando…" /></div>;

  if (view === 'form') {
    return (
      <div className="max-w-5xl mx-auto pb-24 space-y-4">
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => setView('list')}><ArrowLeft className="w-4 h-4 mr-1" /> Novidades</Button>
          <Button onClick={salvar} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Salvar
          </Button>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Campo label="Slug (único) *"><Input value={form.slug} onChange={(e) => set('slug', e.target.value)} disabled={!!editId} /></Campo>
              <Campo label="Versão"><Input value={form.versao} onChange={(e) => set('versao', e.target.value)} placeholder="1.12.0" /></Campo>
            </div>
            <Campo label="Título *"><Input value={form.titulo} onChange={(e) => set('titulo', e.target.value)} /></Campo>
            <Campo label="Resumo (1 linha — usada no sino)"><Input value={form.resumo} onChange={(e) => set('resumo', e.target.value)} /></Campo>
            <div className="grid grid-cols-2 gap-3">
              <Campo label="Tag">
                <select value={form.tag} onChange={(e) => set('tag', e.target.value)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm">
                  {TAGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </Campo>
              <Campo label="Público-alvo">
                <select value={form.publico_alvo} onChange={(e) => set('publico_alvo', e.target.value)} className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm">
                  {ALVOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </Campo>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Campo label="CTA — rótulo"><Input value={form.cta_label} onChange={(e) => set('cta_label', e.target.value)} placeholder="Configurar agora" /></Campo>
              <Campo label="CTA — rota"><Input value={form.cta_rota} onChange={(e) => set('cta_rota', e.target.value)} placeholder="/dashboard/…" /></Campo>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!form.bloqueante} onChange={(e) => set('bloqueante', e.target.checked)} className="w-4 h-4 accent-emerald-600" />
              Modal obrigatório (bloqueante) — senão só sino/toast
            </label>
            <Campo label="Conteúdo (markdown: ###, - lista, **negrito**)">
              <textarea value={form.conteudo_md} onChange={(e) => set('conteudo_md', e.target.value)} rows={12}
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm font-mono" />
            </Campo>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="text-[11px] font-bold uppercase text-emerald-800 mb-2">Pré-visualização</div>
            <div className="font-display text-lg font-bold text-gray-900 mb-2">{form.titulo || 'Título'}</div>
            <MarkdownLite text={form.conteudo_md} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto pb-24 space-y-4">
      <div className="flex items-center justify-between">
        <div className="font-display text-2xl font-bold text-gray-900">Novidades (admin)</div>
        <Button onClick={abrirNovo} className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1"><Plus className="w-4 h-4" /> Nova novidade</Button>
      </div>
      <div className="rounded-xl border border-gray-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="py-2 px-3 font-semibold">Título</th>
              <th className="py-2 px-3 font-semibold">Versão</th>
              <th className="py-2 px-3 font-semibold">Alvo</th>
              <th className="py-2 px-3 font-semibold">Status</th>
              <th className="py-2 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {lista.length === 0 ? (
              <tr><td colSpan={5} className="py-8 text-center text-gray-400 text-xs">Nenhuma novidade cadastrada.</td></tr>
            ) : lista.map((n) => (
              <tr key={n.id} className="border-b border-gray-50">
                <td className="py-2 px-3">
                  <div className="font-medium text-gray-800">{n.titulo}</div>
                  {n.bloqueante && <span className="text-[10px] text-amber-600 font-semibold">bloqueante</span>}
                </td>
                <td className="py-2 px-3 text-gray-500">{n.versao || '—'}</td>
                <td className="py-2 px-3 text-gray-500">{n.publico_alvo}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${n.publicada ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                    {n.publicada ? 'Publicada' : 'Rascunho'}
                  </span>
                </td>
                <td className="py-2 px-3 text-right whitespace-nowrap">
                  <button type="button" onClick={() => abrirEdit(n)} title="Editar" className="text-gray-500 hover:text-emerald-700 p-1"><Pencil className="w-4 h-4" /></button>
                  <button type="button" onClick={() => verMetricas(n)} title="Métricas" className="text-gray-500 hover:text-emerald-700 p-1"><BarChart3 className="w-4 h-4" /></button>
                  {!n.publicada && (
                    <button type="button" onClick={() => publicar(n)} title="Publicar" className="text-emerald-600 hover:text-emerald-800 p-1"><CheckCircle2 className="w-4 h-4" /></button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {metricas && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => setMetricas(null)}>
          <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl p-5 w-full max-w-sm shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <div className="font-semibold text-gray-800">Métricas</div>
              <button onClick={() => setMetricas(null)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <div className="text-xs text-gray-500 mb-3">{metricas.titulo}</div>
            <div className="grid grid-cols-2 gap-2">
              {[['Destinatários', metricas.dados.destinatarios], ['Vistos', metricas.dados.vistos],
                ['Dispensados', metricas.dados.dispensados], ['CTA clicados', metricas.dados.cta_clicados]].map(([k, v]) => (
                <div key={k} className="rounded-xl bg-emerald-50/60 border border-emerald-100 px-3 py-2">
                  <div className="text-[10px] uppercase text-emerald-700">{k}</div>
                  <div className="text-lg font-bold text-gray-800">{v ?? 0}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NovidadesAdmin;
