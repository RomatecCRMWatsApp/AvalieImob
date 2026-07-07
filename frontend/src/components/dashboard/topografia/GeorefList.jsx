// @module topografia/GeorefList — Lista de projetos de Georreferenciamento + criação.
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass, Plus, Trash2, FileText, MapPin, FolderOpen, Eye, FileDown, Send, X,
} from 'lucide-react';
import { georefAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

// Abre um blob (PDF) numa nova aba de forma síncrona (não bloqueia o popup).
const abrirBlob = async (apiPromise, toast) => {
  const win = window.open('', '_blank');
  try {
    const blob = await apiPromise;
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    if (win) win.close();
    toast({ title: 'Erro ao abrir o PDF', variant: 'destructive' });
  }
};

const baixarBlob = async (apiPromise, filename, toast) => {
  try {
    const blob = await apiPromise;
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
    const a = document.createElement('a');
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    toast({ title: 'Erro ao baixar o PDF', variant: 'destructive' });
  }
};

const Btn = ({ icon: Icon, label, onClick, cls, style }) => (
  <button
    onClick={onClick}
    style={style}
    className={`flex items-center justify-center gap-1.5 border rounded-lg py-2 text-xs font-medium ${cls}`}
  >
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);

export const TIPOS_SERVICO = [
  { value: 'georreferenciamento', label: 'Georreferenciamento (averbação)' },
  { value: 'desmembramento', label: 'Desmembramento' },
  { value: 'remembramento', label: 'Remembramento / Unificação' },
  { value: 'desdobro', label: 'Desdobro de área' },
  { value: 'retificacao', label: 'Retificação de área (art. 213)' },
  { value: 'certificacao', label: 'Certificação SIGEF/INCRA' },
];

const STATUS = {
  rascunho: { label: 'Rascunho', cls: 'bg-gray-100 text-gray-600' },
  extraido: { label: 'Extraído', cls: 'bg-blue-100 text-blue-700' },
  documentos_gerados: { label: 'Documentos gerados', cls: 'bg-amber-100 text-amber-800' },
  concluido: { label: 'Concluído', cls: 'bg-emerald-100 text-emerald-700' },
};

export default function GeorefList() {
  const nav = useNavigate();
  const { toast } = useToast();
  const [projetos, setProjetos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [novo, setNovo] = useState(false);
  const [form, setForm] = useState({ nome_projeto: '', tipo_servico: 'georreferenciamento', tema_pdf: 'prime_i' });
  const [criando, setCriando] = useState(false);

  // Envio por WhatsApp
  const [wa, setWa] = useState(null);      // {id, nome, tema}
  const [waPeca, setWaPeca] = useState('dossie');
  const [waFone, setWaFone] = useState('');
  const [enviandoWa, setEnviandoWa] = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const d = await georefAPI.listar();
      setProjetos(Array.isArray(d) ? d : []);
    } catch (e) {
      toast({ title: 'Erro ao carregar projetos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const criar = async () => {
    if (!form.nome_projeto.trim()) {
      toast({ title: 'Informe o nome do projeto', variant: 'destructive' });
      return;
    }
    setCriando(true);
    try {
      const p = await georefAPI.criar(form);
      nav(`/dashboard/topografia/georef/${p.id}`);
    } catch (e) {
      toast({ title: 'Erro ao criar projeto', variant: 'destructive' });
    } finally {
      setCriando(false);
    }
  };

  const excluir = async (id) => {
    if (!window.confirm('Excluir este projeto e seus documentos?')) return;
    try {
      await georefAPI.excluir(id);
      setProjetos((p) => p.filter((x) => x.id !== id));
      toast({ title: 'Projeto excluído' });
    } catch (err) {
      toast({ title: 'Erro ao excluir', variant: 'destructive' });
    }
  };

  const abrirWa = (p) => { setWa({ id: p.id, nome: p.nome_projeto, tema: p.tema_pdf }); setWaPeca('dossie'); setWaFone(''); };

  const enviarWa = async () => {
    const fone = waFone.replace(/\D/g, '');
    if (fone.length < 10) { toast({ title: 'Informe um WhatsApp válido (55 + DDD + número)', variant: 'destructive' }); return; }
    setEnviandoWa(true);
    try {
      await georefAPI.enviarWhatsapp(wa.id, { peca: waPeca, telefone: fone, tema: wa.tema });
      toast({ title: 'Enviado pelo WhatsApp ✓', description: fone });
      setWa(null);
    } catch (e) {
      toast({ title: 'Falha ao enviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally {
      setEnviandoWa(false);
    }
  };

  if (loading) return <div className="py-24"><BrandSpinner label="Carregando projetos…" /></div>;

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <header className="flex items-start justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: GREEN }}>
            <Compass className="w-6 h-6" style={{ color: GOLD }} />
          </div>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: GREEN }}>Topografia & Geo</h1>
            <p className="text-sm text-gray-500">
              Georreferenciamento · Memorial, Requerimento, DRL, Laudo Técnico, Shapefile SIG-RI e Dossiê.
            </p>
          </div>
        </div>
        <button
          onClick={() => setNovo(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-white shadow-sm hover:opacity-90"
          style={{ background: GREEN }}
        >
          <Plus className="w-4 h-4" /> Novo projeto
        </button>
      </header>

      {novo && (
        <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50/40 p-5">
          <h2 className="font-semibold mb-3" style={{ color: GREEN }}>Novo projeto de georreferenciamento</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome do projeto / imóvel</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Ex.: Fazenda Santa Maria — Matrícula 1234"
                value={form.nome_projeto}
                onChange={(e) => setForm({ ...form, nome_projeto: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de serviço</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                value={form.tipo_servico}
                onChange={(e) => setForm({ ...form, tipo_servico: e.target.value })}
              >
                {TIPOS_SERVICO.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tema do PDF</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                value={form.tema_pdf}
                onChange={(e) => setForm({ ...form, tema_pdf: e.target.value })}
              >
                <option value="prime_i">Prime I</option>
                <option value="prime_ii">Prime II</option>
                <option value="tradicional">Tradicional</option>
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
          <p>Nenhum projeto ainda. Crie o primeiro e suba o Memorial SIGEF para extrair os dados.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {projetos.map((p) => {
            const st = STATUS[p.status] || STATUS.rascunho;
            const tipo = TIPOS_SERVICO.find((t) => t.value === p.tipo_servico);
            const gerado = ['documentos_gerados', 'concluido'].includes(p.status);
            const nb = p.imovel?.matricula || p.numero || 'projeto';
            const im = p.imovel || {};
            const local = [im.municipio, im.uf].filter(Boolean).join('/');
            const cartorio = im.cartorio_nome || im.cartorio_municipio || '';
            return (
              <div key={p.id} className="rounded-xl border border-gray-200 bg-white p-5 flex flex-col">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${st.cls}`}>{st.label}</span>
                  <button onClick={() => excluir(p.id)} title="Excluir">
                    <Trash2 className="w-4 h-4 text-gray-300 hover:text-red-500 shrink-0" />
                  </button>
                </div>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <button
                      onClick={() => nav(`/dashboard/topografia/georef/${p.id}`)}
                      className="text-left group block w-full"
                    >
                      <div className="font-semibold text-gray-800 group-hover:text-emerald-800 line-clamp-2">
                        {p.nome_projeto || 'Sem nome'}
                      </div>
                    </button>
                    <div className="text-xs text-gray-500 mt-1">
                      {p.numero ? `${p.numero} · ` : ''}{tipo?.label || p.tipo_servico}
                    </div>
                    {p.imovel?.matricula && (
                      <div className="text-xs text-gray-400 mt-0.5">
                        <FileText className="w-3 h-3 inline mr-1" />
                        Matrícula {p.imovel.matricula}
                        {p.imovel.area_ha ? ` · ${p.imovel.area_ha} ha` : ''}
                      </div>
                    )}
                  </div>
                  {(local || cartorio) && (
                    <div className="text-right shrink-0 max-w-[48%]">
                      {local && (
                        <div className="inline-flex items-center gap-1 text-xs font-semibold" style={{ color: GREEN }}>
                          <MapPin className="w-3 h-3" /> {local}
                        </div>
                      )}
                      {cartorio && (
                        <>
                          <div className="text-[9px] uppercase tracking-wide text-gray-400 mt-1.5">Protocolo no cartório</div>
                          <div className="text-[10px] text-gray-600 leading-snug line-clamp-3" title={cartorio}>
                            {cartorio}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-3">
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${p.completude || 0}%`, background: GOLD }} />
                  </div>
                  <span className="text-[10px] text-gray-400">{p.completude || 0}% preenchido</span>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <Btn icon={FolderOpen} label="Abrir"
                    onClick={() => nav(`/dashboard/topografia/georef/${p.id}`)}
                    cls="text-gray-700 border-gray-200 hover:bg-gray-50" />
                  <Btn icon={Eye} label="Ver Dossiê"
                    onClick={() => abrirBlob(georefAPI.documento(p.id, 'dossie', 'pdf', p.tema_pdf), toast)}
                    cls="text-emerald-800 border-emerald-200 hover:bg-emerald-50" />
                  <Btn icon={FileDown} label="Baixar Dossiê"
                    onClick={() => baixarBlob(georefAPI.documento(p.id, 'dossie', 'download', p.tema_pdf), `Dossie_${nb}.pdf`, toast)}
                    cls="text-emerald-800 border-emerald-200 hover:bg-emerald-50" />
                  <Btn icon={Send} label="Enviar WhatsApp"
                    onClick={() => abrirWa(p)}
                    cls="text-white border-transparent hover:opacity-90" style={{ background: GREEN }} />
                </div>
                {!gerado && (
                  <p className="text-[10px] text-amber-600 mt-2">
                    ⚠️ Gere os documentos (aba Geração) para o Dossiê sair completo/assinado.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modal — Enviar por WhatsApp */}
      {wa && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={() => setWa(null)}>
          <div className="bg-white rounded-2xl max-w-md w-full p-5" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-1">
              <h3 className="font-semibold" style={{ color: GREEN }}>Enviar por WhatsApp</h3>
              <button onClick={() => setWa(null)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <p className="text-xs text-gray-500 mb-4">{wa.nome}</p>
            <label className="block text-xs font-medium text-gray-600 mb-1">Peça</label>
            <select value={waPeca} onChange={(e) => setWaPeca(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white mb-3">
              <option value="dossie">Dossiê consolidado (final, com as assinaturas)</option>
              <option value="requerimento">Requerimento ao Cartório</option>
              <option value="laudo_tecnico">Laudo Técnico de Agrimensura</option>
              <option value="memorial">Memorial Descritivo</option>
            </select>
            <label className="block text-xs font-medium text-gray-600 mb-1">WhatsApp do contato</label>
            <input value={waFone} onChange={(e) => setWaFone(e.target.value)}
              placeholder="55 + DDD + número (ex.: 5599999999999)"
              className="w-full border rounded-lg px-3 py-2 text-sm mb-4" />
            <div className="flex gap-2">
              <button onClick={enviarWa} disabled={enviandoWa}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
                style={{ background: GREEN }}>
                {enviandoWa ? 'Enviando…' : 'Enviar'}
              </button>
              <button onClick={() => setWa(null)} className="px-4 py-2 rounded-lg text-sm border">Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
