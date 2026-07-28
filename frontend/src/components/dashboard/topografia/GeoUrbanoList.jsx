// @module topografia/GeoUrbanoList — Lista de projetos de Geo Urbano + criação.
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Plus, Trash2, MapPin, Sparkles, CheckCircle2, Clock, Send, Eye, RefreshCw, FolderOpen, ShieldCheck, Link2 } from 'lucide-react';
import { geoUrbanoAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { BrandSpinner } from '../../brand/BrandSpinner';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

// abre o PDF de uma peça (Dossiê) numa nova aba — mesmo padrão do módulo Documentos Externos
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

const Btn = ({ icon: Icon, label, onClick, cls }) => (
  <button onClick={onClick} className={`flex items-center justify-center gap-1.5 border rounded-lg py-2 text-xs font-medium ${cls}`}>
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);

export const TIPOS_SERVICO = [
  { value: 'georref_urbano', label: 'Georreferenciamento de lote urbano (localização e situação)', pronto: true },
  { value: 'remembramento', label: 'Remembramento (unificação de lotes)', pronto: true },
  { value: 'desdobro', label: 'Desdobro (fracionamento)', pronto: true },
  { value: 'retificacao', label: 'Retificação de área/registro', pronto: true },
  { value: 'usucapiao', label: 'Usucapião extrajudicial', pronto: true },
  { value: 'reurb', label: 'REURB (regularização fundiária urbana)', pronto: true },
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
  const [form, setForm] = useState({
    denominacao_imovel: '', tipo_servico: 'georref_urbano', tema: 'prime_i',
    finalidade: 'financiamento_bancario', instituicao_financeira: '', preset: 'BANCO',
  });
  const [criando, setCriando] = useState(false);
  const [opcoes, setOpcoes] = useState(null);   // catálogo georref (finalidades/presets)

  useEffect(() => {
    if (novo && !opcoes) {
      geoUrbanoAPI.georrefOpcoes().then(setOpcoes).catch(() => {});
    }
  }, [novo, opcoes]);
  const isGeorref = form.tipo_servico === 'georref_urbano';

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
      const p = await geoUrbanoAPI.criar({
        denominacao_imovel: form.denominacao_imovel, tipo_servico: form.tipo_servico, tema: form.tema,
      });
      if (form.tipo_servico === 'georref_urbano') {
        await geoUrbanoAPI.atualizar(p.id, {
          finalidade: form.finalidade,
          ...(form.instituicao_financeira ? { instituicao_financeira: form.instituicao_financeira } : {}),
        });
        await geoUrbanoAPI.georrefComposicao(p.id, { preset: form.preset });
      }
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

  const criarSeedUsucapiao = async () => {
    setCriando(true);
    try {
      const p = await geoUrbanoAPI.criarSeedUsucapiao();
      toast({ title: 'Projeto-teste Usucapião (herdeiro) criado' });
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

  const [wa, setWa] = useState(null);   // {id, nome} do projeto p/ enviar por WhatsApp
  const [waPeca, setWaPeca] = useState('dossie');
  const [waFone, setWaFone] = useState('');
  const [waEnviando, setWaEnviando] = useState(false);
  const abrirWa = (p, e) => { e.stopPropagation(); setWa({ id: p.id, nome: p.denominacao_imovel, tipo_servico: p.tipo_servico }); setWaPeca('dossie'); setWaFone(''); };
  const enviarWa = async () => {
    const fone = waFone.replace(/\D/g, '');
    if (fone.length < 10) { toast({ title: 'Informe um WhatsApp válido (55 + DDD + número)', variant: 'destructive' }); return; }
    setWaEnviando(true);
    try {
      await geoUrbanoAPI.enviarWhatsapp(wa.id, { peca: waPeca, telefone: fone });
      toast({ title: 'Enviado pelo WhatsApp ✓', description: `${fone}` });
      setWa(null);
    } catch (err) {
      toast({ title: 'Erro ao enviar', description: err?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setWaEnviando(false); }
  };

  const [linkBusy, setLinkBusy] = useState(null);
  const gerarLink = async (p, e) => {
    e.stopPropagation();
    setLinkBusy(p.id);
    try {
      const r = await geoUrbanoAPI.gerarLink(p.id);
      try { await navigator.clipboard.writeText(r.url); } catch { /* clipboard bloqueado */ }
      setProjetos((ps) => ps.map((x) => (x.id === p.id ? { ...x, link_publico_ativo: true, link_publico_token: r.token } : x)));
      toast({ title: 'Link do dossiê copiado ✓', description: r.url });
    } catch (err) {
      toast({ title: 'Erro ao gerar link', variant: 'destructive' });
    } finally { setLinkBusy(null); }
  };

  const [reenviando, setReenviando] = useState(null);
  const reenviarAssin = async (id, e) => {
    e.stopPropagation();
    setReenviando(id);
    try {
      const r = await geoUrbanoAPI.propReenviar(id);
      toast({ title: `Links reenviados: ${r.enviados || 0}`, description: r.falhas ? `${r.falhas} falha(s)` : '' });
    } catch (err) {
      toast({ title: 'Erro ao reenviar', description: err?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setReenviando(null); }
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
          <button
            onClick={criarSeedUsucapiao} disabled={criando}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border hover:bg-amber-50"
            style={{ borderColor: GOLD, color: GREEN }}
          >
            <Sparkles className="w-3.5 h-3.5" /> Projeto-teste Usucapião
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

            {/* Composição do dossiê — só no georref urbano, no TOPO ao criar */}
            {isGeorref && (
              <div className="sm:col-span-2 rounded-lg border border-amber-200 bg-amber-50/50 p-3">
                <div className="text-xs font-semibold mb-2" style={{ color: GREEN }}>
                  Composição do dossiê — escolha aqui ao criar
                </div>
                <div className="grid sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Finalidade</label>
                    <select
                      className="w-full border rounded-lg px-2.5 py-1.5 text-sm bg-white"
                      value={form.finalidade}
                      onChange={(e) => {
                        const fin = e.target.value;
                        setForm((f) => ({ ...f, finalidade: fin, preset: fin === 'financiamento_bancario' ? 'BANCO' : 'COMPLETO' }));
                      }}
                    >
                      {(opcoes?.finalidades || [{ codigo: 'financiamento_bancario', label: 'Financiamento bancário' }])
                        .map((o) => <option key={o.codigo} value={o.codigo}>{o.label}</option>)}
                    </select>
                  </div>
                  {form.finalidade === 'financiamento_bancario' && (
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Instituição</label>
                      <input list="georref-bancos"
                        className="w-full border rounded-lg px-2.5 py-1.5 text-sm bg-white"
                        placeholder="CAIXA ECONÔMICA FEDERAL"
                        value={form.instituicao_financeira}
                        onChange={(e) => setForm({ ...form, instituicao_financeira: e.target.value })} />
                      <datalist id="georref-bancos">
                        {(opcoes?.instituicoes || []).map((b) => <option key={b} value={b} />)}
                      </datalist>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Modelo (preset)</label>
                    <select
                      className="w-full border rounded-lg px-2.5 py-1.5 text-sm bg-white"
                      value={form.preset}
                      onChange={(e) => setForm({ ...form, preset: e.target.value })}
                    >
                      {(opcoes?.presets || ['COMPLETO', 'BANCO', 'SIMPLIFICADO']).map((p) => (
                        <option key={p} value={p}>{p === 'BANCO' ? 'Banco (localização + situação)'
                          : p === 'SIMPLIFICADO' ? 'Simplificado (mapa + memorial + ART)'
                          : p === 'COMPLETO' ? 'Completo' : p}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <p className="text-[11px] text-gray-500 mt-2">
                  As peças exatas do dossiê você ajusta depois, no passo <strong>Composição</strong> do projeto.
                </p>
              </div>
            )}
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projetos.map((p) => {
            const st = STATUS[p.status] || STATUS.rascunho;
            const tipo = TIPOS_SERVICO.find((t) => t.value === p.tipo_servico);
            const a = p.assinatura_prop;
            const temSig = a?.existe && a.total > 0;
            const todosSig = temSig && a.assinados >= a.total;
            return (
              <div key={p.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 flex flex-col">
                {/* cabeçalho: ícone + código + denominação + tipo */}
                <div className="flex items-start gap-2 mb-2">
                  <div className="w-9 h-9 rounded-lg bg-[rgba(201,168,76,0.16)] flex items-center justify-center flex-shrink-0">
                    <MapPin className="w-4 h-4 text-[#C9A84C]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[11px] text-gray-400">{p.numero || '—'}</div>
                    <div className="font-semibold text-sm text-gray-900 line-clamp-2" title={p.denominacao_imovel}>
                      {p.denominacao_imovel || 'Sem denominação'}
                    </div>
                    <div className="text-[11px] text-gray-400">
                      {tipo?.label || p.tipo_servico}
                      {' · '}{(p.matriculas?.length || 0)} matrícula(s)
                      {p.area_declarada_m2 ? ` · ${Number(p.area_declarada_m2).toLocaleString('pt-BR')} m²` : ''}
                    </div>
                  </div>
                </div>

                <div className={`text-[11px] font-medium mb-2 inline-block px-2 py-0.5 rounded-full self-start ${st.cls}`}>{st.label}</div>

                {/* progresso de preenchimento */}
                <div className="mb-2">
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${p.completude || 0}%`, background: GOLD }} />
                  </div>
                  <span className="text-[10px] text-gray-400">{p.completude || 0}% preenchido</span>
                </div>

                {/* assinatura do proprietário — chips + status (padrão doc-ext) */}
                {temSig && (
                  <>
                    <div className="text-[11px] text-gray-500 mb-1.5">Assinaturas · {a.assinados}/{a.total}</div>
                    <div className="flex flex-wrap gap-1 mb-1.5">
                      {(a.signatarios || []).map((s, i) => {
                        const ok = s.status === 'assinado';
                        const cls = ok ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : s.status === 'enviado' ? 'bg-sky-50 text-sky-700 border-sky-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200';
                        return (
                          <span key={i} title={`${s.nome} · ${s.papel || ''} · ${ok ? 'assinou' : 'pendente'}`}
                            className={`text-[10px] px-1.5 py-0.5 rounded-full border ${cls}`}>
                            {ok ? '✓' : s.status === 'enviado' ? '✈' : '⏳'} {(s.nome || '').split(' ')[0]}
                          </span>
                        );
                      })}
                    </div>
                    {todosSig ? (
                      <div className="text-[11px] font-semibold text-emerald-700 mb-1.5 inline-flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Proprietário assinou ✓
                      </div>
                    ) : (
                      <div className="text-[11px] font-semibold text-amber-700 mb-1.5 inline-flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" /> Aguardando assinaturas
                      </div>
                    )}
                  </>
                )}

                {/* assinatura ICP do técnico (Memorial/Mapa/ART) */}
                {p.assinatura_tecnico?.existe && (() => {
                  const t = p.assinatura_tecnico;
                  const todosT = t.total > 0 && t.assinados >= t.total;
                  return (
                    <div className="mb-1.5">
                      <div className="text-[11px] text-gray-500 mb-1 inline-flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Técnico (ICP) · {t.assinados}/{t.total}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {(t.pecas || []).map((pc, i) => (
                          <span key={i} title={`${pc.nome} · ${pc.assinado ? 'assinado (ICP)' : 'pendente'}`}
                            className={`text-[10px] px-1.5 py-0.5 rounded-full border ${pc.assinado ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-gray-50 text-gray-500 border-gray-200'}`}>
                            {pc.assinado ? '✓' : '⏳'} {(pc.nome || '').split(' ')[0].replace('Requerimento', 'Req.')}
                          </span>
                        ))}
                      </div>
                      {todosT && (
                        <div className="text-[11px] font-semibold text-emerald-700 mt-1 inline-flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Técnico assinou (ICP) ✓
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* ações — mesmo grid do módulo Documentos Externos */}
                <div className="grid grid-cols-2 gap-1.5 mt-auto">
                  <Btn icon={FolderOpen} label="Abrir" onClick={() => nav(`/dashboard/topografia/geo-urbano/${p.id}`)}
                    cls="border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100" />
                  <Btn icon={Eye} label="Ver Dossiê"
                    onClick={() => abrirBlob(p.tipo_servico === 'georref_urbano'
                      ? geoUrbanoAPI.georrefDossie(p.id, p.tema)
                      : geoUrbanoAPI.documento(p.id, 'dossie', p.tema), toast)}
                    cls="border-gray-200 text-gray-700 hover:bg-gray-50" />
                  <Btn icon={Send} label="Enviar por WhatsApp" onClick={(e) => abrirWa(p, e)}
                    cls="border-emerald-300 bg-emerald-600 text-white hover:bg-emerald-700 col-span-2" />
                  <Btn icon={Link2} label={linkBusy === p.id ? 'Gerando…' : (p.link_publico_ativo ? 'Copiar link do dossiê' : 'Gerar link do dossiê')}
                    onClick={(e) => gerarLink(p, e)}
                    cls="border-sky-300 text-sky-700 hover:bg-sky-50 col-span-2" />
                  {p.link_publico_ativo && (
                    <div className="col-span-2 text-[10px] text-gray-400 inline-flex items-center gap-1 -mt-0.5">
                      <Eye className="w-3 h-3" /> {p.link_views || 0} visualização(ões) · link público ativo
                    </div>
                  )}
                  {temSig && !todosSig && (
                    <Btn icon={RefreshCw} label={reenviando === p.id ? 'Reenviando…' : 'Reenviar assinatura'} onClick={(e) => reenviarAssin(p.id, e)}
                      cls="border-emerald-200 text-emerald-700 hover:bg-emerald-50 col-span-2" />
                  )}
                  <Btn icon={Trash2} label="Excluir" onClick={(e) => excluir(p.id, e)}
                    cls="border-red-200 text-red-600 hover:bg-red-50 col-span-2" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {wa && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4" onClick={() => !waEnviando && setWa(null)}>
          <div className="bg-white rounded-xl p-5 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold mb-1" style={{ color: GREEN }}>Enviar por WhatsApp</h3>
            <p className="text-xs text-gray-500 mb-3 line-clamp-1">{wa.nome}</p>
            <label className="block text-xs font-medium text-gray-600 mb-1">Peça</label>
            <select className="w-full border rounded-lg px-2.5 py-2 text-sm mb-3" value={waPeca} onChange={(e) => setWaPeca(e.target.value)}>
              <option value="dossie">Dossiê consolidado (com as assinaturas)</option>
              {wa.tipo_servico === 'georref_urbano' ? (
                <>
                  <option value="memorial_perimetrico">Memorial Perimétrico</option>
                  <option value="memorial_situacao">Memorial de Localização e Situação</option>
                  <option value="memorial_sucinto">Descrição Sucinta</option>
                  <option value="art_trt">ART / TRT</option>
                </>
              ) : wa.tipo_servico === 'usucapiao' ? (
                <>
                  <option value="requerimento_usucapiao">Requerimento de Usucapião (assinado)</option>
                  <option value="art_trt">ART / TRT</option>
                  <option value="memorial_descritivo">Memorial Descritivo</option>
                </>
              ) : wa.tipo_servico === 'reurb' ? (
                <>
                  <option value="requerimento_reurb">Requerimento de Reurb (Município)</option>
                  <option value="art_trt">ART / TRT</option>
                  <option value="memorial_descritivo">Memorial Descritivo</option>
                </>
              ) : (
                <>
                  <option value="requerimento_cartorio">Requerimento — Cartório de RI</option>
                  <option value="requerimento_superintendencia">Requerimento — Superintendência</option>
                  <option value="memorial_descritivo">Memorial Descritivo</option>
                  <option value="cadeia_dominical">Cadeia Dominical</option>
                </>
              )}
            </select>
            <label className="block text-xs font-medium text-gray-600 mb-1">WhatsApp do contato</label>
            <input className="w-full border rounded-lg px-2.5 py-2 text-sm mb-4" placeholder="55 + DDD + número (ex.: 5599999999999)"
              value={waFone} onChange={(e) => setWaFone(e.target.value)} />
            <div className="flex justify-end gap-2">
              <button onClick={() => setWa(null)} disabled={waEnviando} className="px-3 py-2 rounded-lg text-sm border">Cancelar</button>
              <button onClick={enviarWa} disabled={waEnviando}
                className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-1" style={{ background: GREEN }}>
                <Send className="w-4 h-4" /> {waEnviando ? 'Enviando…' : 'Enviar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
