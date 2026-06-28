// @module documentos-externos/DocumentosExternosList — Documentos Externos (doc-ext):
// upload de PDF → cadastrar N signatários → posicionar → WhatsApp → ICP opcional do RT.
import React, { useState, useEffect, useCallback } from 'react';
import { Send, Eye, Users, MapPin, ShieldCheck, RefreshCw, Trash2, FileText, Plus } from 'lucide-react';
import { documentosExternosAPI, testemunhasAssinaturaAPI, clientsAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Button } from '../../ui/button';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';
import { BrandSpinner } from '../../brand/BrandSpinner';
import ModalUpload from './ModalUpload';
import ModalSignatarios from './ModalSignatarios';
import PositionerDocExt from './PositionerDocExt';
import ModalEnviarFinal from './ModalEnviarFinal';

const fmtData = (d) => (d ? new Date(d).toLocaleDateString('pt-BR') : '');

const STATUS = {
  rascunho: { label: 'Rascunho', cls: 'bg-gray-100 text-gray-600' },
  aguardando: { label: 'Aguardando assinaturas', cls: 'bg-amber-50 text-amber-700' },
  parcial: { label: 'Parcialmente assinado', cls: 'bg-amber-100 text-amber-800' },
  clientes_ok: { label: 'Signatários OK — falta ICP', cls: 'bg-sky-50 text-sky-700' },
  finalizado: { label: 'Finalizado', cls: 'bg-emerald-50 text-emerald-700' },
  cancelado: { label: 'Cancelado', cls: 'bg-red-50 text-red-600' },
};

const visualizar = async (apiFn, id, toast) => {
  const win = window.open('', '_blank');
  try {
    const blob = await apiFn(id);
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/pdf' }));
    if (win) win.location.href = url; else window.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    if (win) win.close();
    toast({ title: 'Erro ao abrir o PDF', variant: 'destructive' });
  }
};

export default function DocumentosExternosList() {
  const { toast } = useToast();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [upload, setUpload] = useState(false);
  const [signatarios, setSignatarios] = useState(null);
  const [posicionar, setPosicionar] = useState(null);
  const [assinarIcp, setAssinarIcp] = useState(null);
  const [enviarFinal, setEnviarFinal] = useState(null);
  const [testemunhas, setTestemunhas] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try { setDocs(await documentosExternosAPI.listar()); }
    catch { toast({ title: 'Erro ao carregar documentos', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const excluir = async (d) => {
    if (!window.confirm(`Excluir "${d.titulo}"? O PDF e as assinaturas serão removidos.`)) return;
    try { await documentosExternosAPI.excluir(d.id); toast({ title: 'Documento excluído' }); load(); }
    catch { toast({ title: 'Erro ao excluir', variant: 'destructive' }); }
  };

  const reenviar = async (d) => {
    try {
      const r = await documentosExternosAPI.reenviar(d.id, {});
      if (r.falhas && r.falhas.length) {
        toast({ title: `Reenviado a ${r.reenviados} · falhou para ${r.falhas.length}`,
          description: r.falhas.map((f) => `${f.nome}: ${f.erro}`).join(' · '), variant: 'destructive' });
      } else {
        toast({ title: `Reenviado a ${r.reenviados} signatário(s)` });
      }
    } catch (e) { toast({ title: 'Erro ao reenviar', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Send className="w-6 h-6 text-[#C9A84C]" />
            <h1 className="font-display text-[34px] font-bold leading-tight text-[#C9A84C]">Documentos Externos</h1>
          </div>
          <p className="text-sm mt-1 text-[#5B7466] dark:text-[#9FB5A6]">
            Envie um PDF gerado fora do sistema, cadastre os signatários e colete a assinatura por WhatsApp (desenho no celular) + ICP-Brasil do RT.
          </p>
        </div>
        <Button onClick={() => setUpload(true)} className="bg-emerald-900 hover:bg-emerald-800 text-white">
          <Plus className="w-4 h-4 mr-2" /> Novo documento externo
        </Button>
      </div>

      {loading ? (
        <div className="py-16 flex justify-center"><BrandSpinner label="Carregando documentos…" /></div>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <FileText className="w-9 h-9 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Nenhum documento ainda. Clique em <b>Novo documento externo</b> para começar.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {docs.map((d) => {
            const st = STATUS[d.status] || STATUS.rascunho;
            const sigs = d.signatarios || [];
            const assinados = sigs.filter((s) => s.status === 'assinado').length;
            const podeIcp = d.requer_icp_rt && d.status === 'clientes_ok';
            return (
              <div key={d.id} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 flex flex-col">
                <div className="flex items-start gap-2 mb-2">
                  <div className="w-9 h-9 rounded-lg bg-[rgba(201,168,76,0.16)] flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-[#C9A84C]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[11px] text-gray-400">{d.codigo}</div>
                    <div className="font-semibold text-sm text-gray-900 truncate" title={d.titulo}>{d.titulo}</div>
                    <div className="text-[11px] text-gray-400">{fmtData(d.created_at)}</div>
                  </div>
                </div>
                <div className={`text-[11px] font-medium mb-1 inline-block px-2 py-0.5 rounded-full self-start ${st.cls}`}>{st.label}</div>
                <div className="text-[11px] text-gray-500 mb-1.5">Assinaturas · {assinados}/{sigs.length}</div>
                {sigs.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {sigs.map((s) => {
                      const ok = s.status === 'assinado';
                      const rec = s.status === 'recusado';
                      const cls = ok ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : rec ? 'bg-red-50 text-red-600 border-red-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200';
                      return (
                        <span key={s.id} title={`${s.nome} · ${s.papel} · ${ok ? 'assinou' : rec ? 'recusou' : 'pendente'}`}
                          className={`text-[10px] px-1.5 py-0.5 rounded-full border ${cls}`}>
                          {ok ? '✓' : rec ? '✕' : '⏳'} {(s.nome || '').split(' ')[0]}
                        </span>
                      );
                    })}
                  </div>
                )}
                {sigs.length > 0 && assinados === sigs.length ? (
                  <div className="text-[11px] font-semibold text-emerald-700 mb-3">✓ Todos os signatários assinaram</div>
                ) : <div className="mb-1" />}

                <div className="grid grid-cols-2 gap-1.5 mt-auto">
                  <Btn icon={Users} label="Signatários" onClick={() => setSignatarios(d)} cls="border-gray-200 text-gray-700 hover:bg-gray-50" />
                  <Btn icon={MapPin} label="Posicionar" onClick={() => setPosicionar(d)} cls="border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100" />
                  <Btn icon={Eye} label="Ver PDF" onClick={() => visualizar(documentosExternosAPI.pdfOriginal, d.id, toast)} cls="border-gray-200 text-gray-700 hover:bg-gray-50" />
                  {(d.status === 'finalizado' || d.pdf_key_intermediario) && (
                    <Btn icon={Eye} label="Ver final" onClick={() => visualizar(documentosExternosAPI.pdfFinal, d.id, toast)} cls="border-emerald-300 text-emerald-700 hover:bg-emerald-50" />
                  )}
                  {d.status === 'finalizado' && (
                    <Btn icon={Send} label="Enviar via final" onClick={() => setEnviarFinal(d)} cls="border-emerald-300 bg-emerald-600 text-white hover:bg-emerald-700 col-span-2" />
                  )}
                  {podeIcp && (
                    <Btn icon={ShieldCheck} label="Assinar ICP" onClick={() => setAssinarIcp(d)} cls="border-emerald-300 bg-emerald-600 text-white hover:bg-emerald-700 col-span-2" />
                  )}
                  {(d.status === 'aguardando' || d.status === 'parcial') && (
                    <Btn icon={RefreshCw} label="Reenviar" onClick={() => reenviar(d)} cls="border-emerald-200 text-emerald-700 hover:bg-emerald-50" />
                  )}
                  {(d.status === 'finalizado' || d.status === 'clientes_ok' || assinados >= sigs.length) && sigs.length > 0 && (
                    <Btn icon={Users} label="Testemunhas" onClick={() => setTestemunhas(d)} cls="border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100 col-span-2" />
                  )}
                  <Btn icon={Trash2} label="Excluir" onClick={() => excluir(d)} cls="border-red-200 text-red-600 hover:bg-red-50" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {upload && (
        <ModalUpload onClose={() => setUpload(false)}
          onCreated={(doc) => { setUpload(false); load(); setSignatarios(doc); }} />
      )}
      {signatarios && (
        <ModalSignatarios doc={signatarios} onClose={() => { setSignatarios(null); load(); }} onChanged={() => load()} />
      )}
      {posicionar && (
        <PositionerDocExt doc={posicionar}
          onEnviado={() => { setPosicionar(null); toast({ title: 'Links enviados por WhatsApp!' }); load(); }}
          onClose={() => setPosicionar(null)} />
      )}
      {assinarIcp && (
        <AssinaturaPosicionadaModal
          tipo="doc-ext"
          documentId={assinarIcp.id}
          onAssinado={async () => {
            const d = assinarIcp; setAssinarIcp(null);
            await load();
            // abre o envio da via final (ICP) com os números p/ revisar antes de mandar
            setEnviarFinal({ ...d, status: 'finalizado' });
          }}
          onFechar={() => setAssinarIcp(null)}
        />
      )}
      {enviarFinal && (
        <ModalEnviarFinal doc={enviarFinal} onClose={() => { setEnviarFinal(null); load(); }} />
      )}
      {testemunhas && (
        <ModalTestemunhas doc={testemunhas} onClose={() => { setTestemunhas(null); load(); }} />
      )}
    </div>
  );
}

const _MODULO = 'documentos-externos';
const _vinc = (sig) => {
  const p = (sig.posicoes && sig.posicoes[0]) || null;
  return p ? { pagina: p.pagina, x_pt: p.x_pt, y_pt: Math.max(8, p.y_pt - 70), larg_pt: p.larg_pt, alt_pt: p.alt_pt }
    : { pagina: 0, x_pt: 72, y_pt: 90, larg_pt: 160, alt_pt: 60 };
};

function ModalTestemunhas({ doc, onClose }) {
  const { toast } = useToast();
  const sigs = doc.signatarios || [];
  const [linhas, setLinhas] = useState([{ nome: '', cpf: '', telefone: '', parte_vinculada_id: sigs[0]?.id || '' }]);
  const [clientes, setClientes] = useState([]);
  const [status, setStatus] = useState([]);
  const [busy, setBusy] = useState(false);
  const [modoTeste, setModoTeste] = useState(false);
  const [foneTeste, setFoneTeste] = useState('');

  const recarregar = useCallback(async () => {
    try { const r = await testemunhasAssinaturaAPI.status(_MODULO, doc.id); setStatus(r.testemunhas || []); }
    catch { /* */ }
  }, [doc.id]);
  useEffect(() => { recarregar(); clientsAPI.list().then((d) => setClientes(Array.isArray(d) ? d : [])).catch(() => {}); }, [recarregar]);

  const upd = (i, patch) => setLinhas((ls) => ls.map((l, k) => (k === i ? { ...l, ...patch } : l)));
  const addLinha = () => setLinhas((ls) => [...ls, { nome: '', cpf: '', telefone: '', parte_vinculada_id: sigs[0]?.id || '' }]);
  const selCliente = (i, cid) => {
    const c = clientes.find((x) => (x.id || x._id) === cid);
    if (c) upd(i, { nome: c.name || c.nome || '', cpf: (c.doc || c.cpf || '').replace(/\D/g, ''), telefone: (c.phone || c.telefone || '').replace(/\D/g, '') });
  };

  const salvarEnviar = async () => {
    const validas = linhas.filter((l) => (l.nome || '').trim() && (l.telefone || '').replace(/\D/g, '').length >= 10 && l.parte_vinculada_id);
    if (!validas.length) { toast({ title: 'Preencha nome, WhatsApp e o vínculo de ao menos uma testemunha', variant: 'destructive' }); return; }
    setBusy(true);
    try {
      const payload = validas.map((l) => {
        const sig = sigs.find((s) => s.id === l.parte_vinculada_id) || {};
        return { nome: l.nome, cpf: l.cpf, telefone: l.telefone,
          vinculo: sig.papel || 'testemunha', parte_vinculada_id: sig.id, parte_vinculada_nome: sig.nome,
          posicoes: [_vinc(sig)] };
      });
      const fteste = modoTeste ? foneTeste.replace(/\D/g, '') : '';
      if (modoTeste && fteste.length < 10) { toast({ title: 'Informe o número de teste (55 + DDD + número)', variant: 'destructive' }); setBusy(false); return; }
      await testemunhasAssinaturaAPI.cadastrar(_MODULO, doc.id, payload);
      const r = await testemunhasAssinaturaAPI.enviarTodas(_MODULO, doc.id, fteste ? { telefone_teste: fteste } : {});
      toast({ title: modoTeste ? `Enviado p/ teste: ${r.enviadas || 0}` : `Links enviados: ${r.enviadas || 0}`, description: (r.falhas || []).length ? `${r.falhas.length} falha(s)` : '' });
      setLinhas([{ nome: '', cpf: '', telefone: '', parte_vinculada_id: sigs[0]?.id || '' }]);
      recarregar();
    } catch (e) {
      toast({ title: 'Erro', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const reenviar = async (tid) => {
    try { const r = await testemunhasAssinaturaAPI.reenviar(_MODULO, doc.id, tid); toast({ title: `Reenviado: ${r.enviadas || 0}` }); recarregar(); }
    catch (e) { toast({ title: 'Erro ao reenviar', variant: 'destructive' }); }
  };

  const BADGE = { pendente: 'bg-gray-100 text-gray-600', enviado: 'bg-sky-100 text-sky-700', assinado: 'bg-emerald-100 text-emerald-700', recusado: 'bg-red-100 text-red-700' };
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4" onClick={() => !busy && onClose()}>
      <div className="bg-white rounded-xl p-5 w-full max-w-lg max-h-[88vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-semibold text-lg" style={{ color: '#0C3320' }}>Testemunhas</h3>
        <p className="text-xs text-gray-500 mb-3">A testemunha assina por WhatsApp o documento já assinado pelas partes. Vincule cada uma a uma parte.</p>

        {status.length > 0 && (
          <div className="mb-3 border rounded-lg p-2 bg-gray-50">
            <div className="text-[11px] font-semibold text-gray-500 mb-1">Já cadastradas</div>
            {status.map((t) => (
              <div key={t.id} className="flex items-center justify-between gap-2 py-1 text-sm">
                <span>{t.nome} <span className="text-[11px] text-gray-400">· {t.parte_vinculada_nome || t.vinculo}</span></span>
                <span className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded ${BADGE[t.status] || BADGE.pendente}`}>{t.status}</span>
                  {t.status !== 'assinado' && <button onClick={() => reenviar(t.id)} className="text-[11px] text-emerald-700 hover:underline">reenviar</button>}
                </span>
              </div>
            ))}
          </div>
        )}

        {linhas.map((l, i) => (
          <div key={i} className="border rounded-lg p-3 mb-2 space-y-2">
            {clientes.length > 0 && (
              <select className="w-full border rounded-lg px-2 py-1.5 text-sm" value="" onChange={(e) => selCliente(i, e.target.value)}>
                <option value="">Usar cliente cadastrado…</option>
                {clientes.map((c) => <option key={c.id || c._id} value={c.id || c._id}>{c.name || c.nome}</option>)}
              </select>
            )}
            <input className="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="Nome da testemunha" value={l.nome} onChange={(e) => upd(i, { nome: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <input className="border rounded-lg px-2 py-1.5 text-sm" placeholder="CPF (opcional)" value={l.cpf} onChange={(e) => upd(i, { cpf: e.target.value.replace(/\D/g, '') })} />
              <input className="border rounded-lg px-2 py-1.5 text-sm" placeholder="WhatsApp 55DDDNUMERO" value={l.telefone} onChange={(e) => upd(i, { telefone: e.target.value.replace(/\D/g, '') })} />
            </div>
            <select className="w-full border rounded-lg px-2 py-1.5 text-sm" value={l.parte_vinculada_id} onChange={(e) => upd(i, { parte_vinculada_id: e.target.value })}>
              <option value="">Vincular à parte…</option>
              {sigs.map((s) => <option key={s.id} value={s.id}>{s.nome} ({s.papel})</option>)}
            </select>
          </div>
        ))}
        <button onClick={addLinha} className="text-xs text-emerald-700 hover:underline mb-3 inline-flex items-center gap-1"><Plus className="w-3 h-3" /> Adicionar testemunha</button>

        <div className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 mb-3">
          <label className="flex items-center gap-2 text-sm text-amber-900 cursor-pointer">
            <input type="checkbox" checked={modoTeste} onChange={(e) => setModoTeste(e.target.checked)} className="w-4 h-4 accent-amber-600" />
            🧪 Modo teste — <b>não enviar ao cliente</b>; mandar para outro número
          </label>
          {modoTeste && (
            <input className="mt-2 w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="Número de teste (55 + DDD + número)"
              value={foneTeste} onChange={(e) => setFoneTeste(e.target.value.replace(/\D/g, ''))} />
          )}
        </div>

        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={busy} className="px-3 py-2 rounded-lg text-sm border">Fechar</button>
          <button onClick={salvarEnviar} disabled={busy} className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-1" style={{ background: '#0C3320' }}>
            <Send className="w-4 h-4" /> {busy ? 'Enviando…' : 'Cadastrar e enviar'}
          </button>
        </div>
      </div>
    </div>
  );
}

const Btn = ({ icon: Icon, label, onClick, cls }) => (
  <button onClick={onClick} className={`flex items-center justify-center gap-1.5 border rounded-lg py-2 text-xs font-medium ${cls}`}>
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);
