// @module documentos-externos/DocumentosExternosList — Documentos Externos (doc-ext):
// upload de PDF → cadastrar N signatários → posicionar → WhatsApp → ICP opcional do RT.
import React, { useState, useEffect, useCallback } from 'react';
import { Send, Eye, Users, MapPin, ShieldCheck, RefreshCw, Trash2, FileText, Plus, Pencil } from 'lucide-react';
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
            const tests = d.testemunhas || [];
            const testPendentes = tests.some((t) => t.status !== 'assinado');
            // ICP do RT é o SELO FINAL — disponível quando os signatários assinaram E não
            // há testemunha pendente (senão a assinatura da testemunha seguinte refaria a
            // revisão e o selo precisaria ser refeito). Posiciona nas páginas que quiser.
            const podeIcp = d.requer_icp_rt && ['clientes_ok', 'finalizado'].includes(d.status) && !testPendentes;
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
                  <div className="text-[11px] font-semibold text-emerald-700 mb-1.5">✓ Todos os signatários assinaram</div>
                ) : <div className="mb-1" />}

                {(d.testemunhas || []).length > 0 && (
                  <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50/60 p-2">
                    <div className="text-[11px] font-semibold text-amber-800 mb-1">
                      Testemunhas · {(d.testemunhas || []).filter((t) => t.status === 'assinado').length}/{d.testemunhas.length} assinaram
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {d.testemunhas.map((t) => {
                        const ok = t.status === 'assinado';
                        const cls = ok ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : t.status === 'enviado' ? 'bg-sky-50 text-sky-700 border-sky-200'
                          : 'bg-white text-gray-500 border-gray-200';
                        return (
                          <span key={t.id} title={`${t.nome} · testemunha de ${t.parte_vinculada_nome || t.vinculo || ''} · ${t.status}`}
                            className={`text-[10px] px-1.5 py-0.5 rounded-full border ${cls}`}>
                            {ok ? '✓' : t.status === 'enviado' ? '✈' : '⏳'} {(t.nome || '').split(' ')[0]}
                            <span className="opacity-60"> (test. {(t.parte_vinculada_nome || t.vinculo || '').split(' ')[0]})</span>
                          </span>
                        );
                      })}
                    </div>
                    {d.testemunhas.length > 0 && d.testemunhas.every((t) => t.status === 'assinado') && (
                      <div className="text-[11px] font-semibold text-emerald-700 mt-1.5">✓ Todas as testemunhas assinaram</div>
                    )}
                  </div>
                )}

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

const T_BOX_W = 170, T_BOX_H = 52;   // caixa da assinatura da testemunha (pt)

function ModalTestemunhas({ doc, onClose }) {
  const { toast } = useToast();
  const sigs = doc.signatarios || [];
  const [step, setStep] = useState('cadastro');   // cadastro | posicionar
  const [linhas, setLinhas] = useState([{ nome: '', cpf: '', telefone: '', email: '', parte_vinculada_id: sigs[0]?.id || '' }]);
  const [clientes, setClientes] = useState([]);
  const [status, setStatus] = useState([]);
  const [busy, setBusy] = useState(false);
  const [modoTeste, setModoTeste] = useState(false);
  const [foneTeste, setFoneTeste] = useState('');
  const [prep, setPrep] = useState(null);          // {paginas, testemunhas}
  const [ativoTid, setAtivoTid] = useState(null);
  const [posBox, setPosBox] = useState({});        // {tid: [{pagina,x_pt,y_pt,larg_pt,alt_pt}]}

  const recarregar = useCallback(async () => {
    try { const r = await testemunhasAssinaturaAPI.status(_MODULO, doc.id); setStatus(r.testemunhas || []); }
    catch { /* */ }
  }, [doc.id]);
  useEffect(() => { recarregar(); clientsAPI.list().then((d) => setClientes(Array.isArray(d) ? d : [])).catch(() => {}); }, [recarregar]);

  const upd = (i, patch) => setLinhas((ls) => ls.map((l, k) => (k === i ? { ...l, ...patch } : l)));
  const addLinha = () => setLinhas((ls) => [...ls, { nome: '', cpf: '', telefone: '', email: '', parte_vinculada_id: sigs[0]?.id || '' }]);
  const composEndereco = (c) => [c.endereco, c.numero && `nº ${c.numero}`, c.complemento, c.bairro,
    (c.city && c.uf) ? `${c.city}/${c.uf}` : (c.city || c.uf), c.cep && `CEP ${c.cep}`].filter(Boolean).join(', ');
  const selCliente = (i, cid) => {
    const c = clientes.find((x) => (x.id || x._id) === cid);
    if (c) upd(i, {
      nome: c.name || c.nome || '', cpf: (c.doc || c.cpf || '').replace(/\D/g, ''),
      telefone: (c.phone || c.telefone || '').replace(/\D/g, ''), email: c.email || '',
      rg: c.rg || '', orgao_emissor: c.orgao_emissor || '', nacionalidade: c.nacionalidade || '',
      estado_civil: c.estado_civil || '', profissao: c.profissao || '', endereco: composEndereco(c),
      _qualif: true,
    });
  };

  // PASSO 1: cadastra (sem enviar) e vai para o posicionador
  const cadastrarEPosicionar = async () => {
    const validas = linhas.filter((l) => (l.nome || '').trim() && (l.telefone || '').replace(/\D/g, '').length >= 10 && l.parte_vinculada_id);
    // se NÃO há novas e tampouco já cadastradas → exige preencher; senão segue (posiciona as existentes)
    if (!validas.length && !status.length) { toast({ title: 'Preencha nome, WhatsApp e o vínculo de ao menos uma testemunha', variant: 'destructive' }); return; }
    setBusy(true);
    try {
      if (validas.length) {
        const payload = validas.map((l) => {
          const sig = sigs.find((s) => s.id === l.parte_vinculada_id) || {};
          return { nome: l.nome, cpf: l.cpf, rg: l.rg, orgao_emissor: l.orgao_emissor,
            nacionalidade: l.nacionalidade, estado_civil: l.estado_civil, profissao: l.profissao,
            endereco: l.endereco, telefone: l.telefone, email: l.email,
            vinculo: sig.papel || 'testemunha', parte_vinculada_id: sig.id, parte_vinculada_nome: sig.nome };
        });
        await testemunhasAssinaturaAPI.cadastrar(_MODULO, doc.id, payload);
      }
      const p = await testemunhasAssinaturaAPI.preparar(_MODULO, doc.id);
      setPrep(p);
      const init = {};
      (p.testemunhas || []).forEach((t) => { if ((t.posicoes || []).length) init[t.id] = t.posicoes; });
      setPosBox(init);
      setAtivoTid((p.testemunhas || []).find((t) => !init[t.id])?.id || (p.testemunhas || [])[0]?.id || null);
      setStep('posicionar');
      recarregar();
    } catch (e) {
      toast({ title: 'Erro', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const clicarPagina = (e, pg) => {
    if (!ativoTid) { toast({ title: 'Selecione uma testemunha' }); return; }
    const r = e.currentTarget.getBoundingClientRect();
    const cx = e.clientX - r.left, cy = e.clientY - r.top;
    const escX = pg.largura_pt / r.width, escY = pg.altura_pt / r.height;
    const x_pt = Math.max(0, Math.min(pg.largura_pt - T_BOX_W, cx * escX));
    const y_pt = Math.max(0, pg.altura_pt - cy * escY - T_BOX_H);
    setPosBox((p) => ({ ...p, [ativoTid]: [{ pagina: pg.pagina, x_pt, y_pt, larg_pt: T_BOX_W, alt_pt: T_BOX_H }] }));
  };

  // PASSO 2: salva posições e envia (com modo teste)
  const posicionarEEnviar = async () => {
    const semPos = (prep.testemunhas || []).filter((t) => !(posBox[t.id] || []).length);
    if (semPos.length) { toast({ title: 'Posicione a assinatura de todas as testemunhas', description: semPos.map((t) => t.nome).join(', '), variant: 'destructive' }); return; }
    const fteste = modoTeste ? foneTeste.replace(/\D/g, '') : '';
    if (modoTeste && fteste.length < 10) { toast({ title: 'Informe o número de teste (55 + DDD + número)', variant: 'destructive' }); return; }
    setBusy(true);
    try {
      await testemunhasAssinaturaAPI.posicionar(_MODULO, doc.id, posBox);
      const r = await testemunhasAssinaturaAPI.enviarTodas(_MODULO, doc.id, fteste ? { telefone_teste: fteste } : {});
      toast({ title: modoTeste ? `Enviado p/ teste: ${r.enviadas || 0}` : `Links enviados: ${r.enviadas || 0}`, description: (r.falhas || []).length ? `${r.falhas.length} falha(s)` : '' });
      onClose();
    } catch (e) {
      toast({ title: 'Erro ao enviar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    } finally { setBusy(false); }
  };

  const reenviar = async (tid) => {
    try { const r = await testemunhasAssinaturaAPI.reenviar(_MODULO, doc.id, tid); toast({ title: `Reenviado: ${r.enviadas || 0}` }); recarregar(); }
    catch (e) { toast({ title: 'Erro ao reenviar', variant: 'destructive' }); }
  };

  const lerImg = (file) => new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => { const img = new Image(); img.onload = () => {
      const max = 1600; let w = img.width, h = img.height;
      if (w > max || h > max) { const s = Math.min(max / w, max / h); w = Math.round(w * s); h = Math.round(h * s); }
      const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
      cv.getContext('2d').drawImage(img, 0, 0, w, h); res(cv.toDataURL('image/jpeg', 0.82));
    }; img.onerror = rej; img.src = fr.result; };
    fr.onerror = rej; fr.readAsDataURL(file);
  });
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [editThumb, setEditThumb] = useState('');
  const iniciarEdicao = (t) => {
    setEditId(t.id);
    setEditForm({ nome: t.nome || '', cpf: t.cpf || '', telefone: t.telefone || '', email: t.email || '', parte_vinculada_id: t.parte_vinculada_id || '', docTipo: t.documento_tipo || 'CNH', docFrente: '', docVerso: '', docPdf: '', docNome: '', docEnviado: !!t.documento_enviado, docPdfEnviado: !!t.documento_pdf });
    setEditThumb('');
    if (t.documento_enviado) {
      testemunhasAssinaturaAPI.documentoPreview(_MODULO, doc.id, t.id)
        .then((blob) => setEditThumb(URL.createObjectURL(blob))).catch(() => {});
    }
  };
  const removerDoc = async () => {
    if (!window.confirm('Remover o documento (CNH/RG) anexado desta testemunha?')) return;
    try { await testemunhasAssinaturaAPI.removerDocumento(_MODULO, doc.id, editId); toast({ title: 'Documento removido' }); setEditThumb(''); setEditForm((f) => ({ ...f, docEnviado: false, docPdfEnviado: false, docPdf: '', docFrente: '', docVerso: '' })); recarregar(); }
    catch (e) { toast({ title: 'Erro ao remover documento', variant: 'destructive' }); }
  };
  const lerArquivo = (file) => new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(file); });
  // aceita PDF (CNH-e) OU foto — PDF vai direto, imagem é comprimida
  const pickArquivo = (campo) => async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    try {
      if (f.type === 'application/pdf') { const b = await lerArquivo(f); setEditForm((s) => ({ ...s, docPdf: b, docNome: f.name, docFrente: '', docVerso: '' })); }
      else { const b = await lerImg(f); setEditForm((s) => ({ ...s, [campo]: b, docPdf: '' })); }
    } catch { /* */ }
  };
  const salvarEdicao = async () => {
    try {
      const sig = sigs.find((s) => s.id === editForm.parte_vinculada_id) || {};
      await testemunhasAssinaturaAPI.editar(_MODULO, doc.id, editId, { nome: editForm.nome, cpf: editForm.cpf, telefone: editForm.telefone, email: editForm.email, parte_vinculada_id: editForm.parte_vinculada_id, vinculo: sig.papel || undefined, parte_vinculada_nome: sig.nome || undefined });
      if (editForm.docPdf || editForm.docFrente || editForm.docVerso) {
        await testemunhasAssinaturaAPI.enviarDocumento(_MODULO, doc.id, editId, { tipo: editForm.docTipo, pdf_base64: editForm.docPdf, frente_base64: editForm.docFrente, verso_base64: editForm.docVerso });
      }
      toast({ title: 'Testemunha atualizada' }); setEditId(null); recarregar();
    } catch (e) { toast({ title: 'Erro ao salvar', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
  };
  const excluirT = async (t) => {
    if (!window.confirm(`Excluir a testemunha ${t.nome}?`)) return;
    try { await testemunhasAssinaturaAPI.excluir(_MODULO, doc.id, t.id); toast({ title: 'Testemunha excluída' }); recarregar(); }
    catch (e) { toast({ title: 'Erro ao excluir', description: e?.response?.data?.detail || '', variant: 'destructive' }); }
  };

  const BADGE = { pendente: 'bg-gray-100 text-gray-600', enviado: 'bg-sky-100 text-sky-700', assinado: 'bg-emerald-100 text-emerald-700', recusado: 'bg-red-100 text-red-700' };
  const COR = ['#0C3320', '#0B6E4F', '#8A2BE2', '#B8860B'];
  const corTid = (tid) => COR[Math.max(0, (prep?.testemunhas || []).findIndex((t) => t.id === tid)) % COR.length];

  // ── PASSO 2: posicionador ──
  if (step === 'posicionar' && prep) {
    return (
      <div className="fixed inset-0 bg-black/80 flex flex-col z-[1000]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3" style={{ background: '#0C3320' }}>
          <h2 className="text-white font-semibold text-sm">Posicionar a assinatura das testemunhas</h2>
          <button onClick={onClose} className="text-white"><Trash2 className="w-0 h-0" /><span className="text-xl leading-none">×</span></button>
        </div>
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
          <div className="md:w-72 shrink-0 bg-white p-3 overflow-y-auto space-y-2">
            <div className="text-xs text-gray-500">Selecione a testemunha e clique na página onde ela assina (ex.: abaixo da parte vinculada).</div>
            {(prep.testemunhas || []).map((t) => (
              <button key={t.id} onClick={() => setAtivoTid(t.id)}
                className={`w-full text-left rounded-lg border p-2 ${ativoTid === t.id ? 'ring-2' : ''}`}
                style={{ borderColor: corTid(t.id), ...(ativoTid === t.id ? { boxShadow: `0 0 0 2px ${corTid(t.id)}` } : {}) }}>
                <div className="text-sm font-medium" style={{ color: corTid(t.id) }}>{t.nome}</div>
                <div className="text-[11px] text-gray-500">Testemunha de {t.parte_vinculada_nome || t.vinculo} {(posBox[t.id] || []).length ? '· ✓ posicionada' : '· posicionar'}</div>
              </button>
            ))}
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 mt-2">
              <label className="flex items-center gap-2 text-xs text-amber-900 cursor-pointer">
                <input type="checkbox" checked={modoTeste} onChange={(e) => setModoTeste(e.target.checked)} className="w-4 h-4 accent-amber-600" />
                🧪 Modo teste — não enviar ao cliente
              </label>
              {modoTeste && <input className="mt-2 w-full border rounded px-2 py-1 text-xs" placeholder="Número de teste 55DDDNUMERO" value={foneTeste} onChange={(e) => setFoneTeste(e.target.value.replace(/\D/g, ''))} />}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto bg-gray-800 p-3 space-y-2">
            {(prep.paginas || []).map((pg) => (
              <TPagina key={pg.pagina} pg={pg} posBox={posBox} corTid={corTid} onClick={(e) => clicarPagina(e, pg)} />
            ))}
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-4 py-3 bg-white">
          <button onClick={() => setStep('cadastro')} disabled={busy} className="px-4 py-2 rounded-lg text-sm border">Voltar</button>
          <button onClick={posicionarEEnviar} disabled={busy} className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-2" style={{ background: '#0C3320' }}>
            <Send className="w-4 h-4" /> {busy ? 'Enviando…' : (modoTeste ? 'Enviar p/ teste' : 'Enviar links')}
          </button>
        </div>
      </div>
    );
  }

  // ── PASSO 1: cadastro ──
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4" onClick={() => !busy && onClose()}>
      <div className="bg-white rounded-xl p-5 w-full max-w-lg max-h-[88vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-semibold text-lg" style={{ color: '#0C3320' }}>Testemunhas</h3>
        <p className="text-xs text-gray-500 mb-3">Cadastre, posicione a assinatura no documento e envie o link por WhatsApp. A testemunha assina o documento já firmado pelas partes.</p>

        {status.length > 0 && (
          <div className="mb-3 border rounded-lg p-2 bg-gray-50">
            <div className="text-[11px] font-semibold text-gray-500 mb-1">Já cadastradas</div>
            {status.map((t) => (editId === t.id ? (
              <div key={t.id} className="border rounded-lg p-2 mb-1 bg-white space-y-1.5">
                <input className="w-full border rounded-lg px-2 py-1 text-sm" placeholder="Nome" value={editForm.nome} onChange={(e) => setEditForm((f) => ({ ...f, nome: e.target.value }))} />
                <div className="grid grid-cols-2 gap-1.5">
                  <input className="border rounded-lg px-2 py-1 text-sm" placeholder="CPF" value={editForm.cpf} onChange={(e) => setEditForm((f) => ({ ...f, cpf: e.target.value.replace(/\D/g, '') }))} />
                  <input className="border rounded-lg px-2 py-1 text-sm" placeholder="WhatsApp" value={editForm.telefone} onChange={(e) => setEditForm((f) => ({ ...f, telefone: e.target.value.replace(/\D/g, '') }))} />
                </div>
                <input className="w-full border rounded-lg px-2 py-1 text-sm" type="email" placeholder="E-mail" value={editForm.email} onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))} />
                <select className="w-full border rounded-lg px-2 py-1 text-sm" value={editForm.parte_vinculada_id} onChange={(e) => setEditForm((f) => ({ ...f, parte_vinculada_id: e.target.value }))}>
                  <option value="">Vincular à parte…</option>
                  {sigs.map((s) => <option key={s.id} value={s.id}>{s.nome} ({s.papel})</option>)}
                </select>
                <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50/60 p-2">
                  <div className="text-[11px] font-semibold text-amber-800 mb-1">Documento de identidade — CNH/RG (PDF ou foto){editForm.docEnviado ? ` · ✓ anexado (${editForm.docPdfEnviado ? 'PDF' : 'foto'})` : ''}</div>
                  {editForm.docEnviado && !editForm.docPdf && !editForm.docFrente && !editForm.docVerso && (
                    <div className="flex items-center gap-2 mb-2 p-1.5 bg-white rounded border">
                      {editThumb
                        ? <img src={editThumb} alt="documento" className="w-14 h-20 object-cover rounded border" />
                        : <div className="w-14 h-20 rounded border bg-gray-100 flex items-center justify-center text-[9px] text-gray-400">prévia</div>}
                      <div className="flex-1 text-[11px] text-gray-600">
                        <div>1 documento anexado ({editForm.docPdfEnviado ? 'PDF' : 'foto'}).</div>
                        <button onClick={removerDoc} className="mt-1 inline-flex items-center gap-1 text-red-600 hover:underline"><Trash2 className="w-3 h-3" /> Remover documento</button>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                    <select className="border rounded px-1.5 py-1 text-xs" value={editForm.docTipo} onChange={(e) => setEditForm((f) => ({ ...f, docTipo: e.target.value }))}>
                      <option value="CNH">CNH</option><option value="RG">RG</option><option value="OUTRO">Outro</option>
                    </select>
                    <label className={`flex-1 text-center text-[11px] rounded border-2 border-dashed py-1.5 cursor-pointer ${(editForm.docPdf || editForm.docFrente) ? 'border-emerald-400 text-emerald-700' : 'border-amber-300 text-amber-700'}`}>
                      {editForm.docPdf ? `✓ ${editForm.docNome || 'PDF anexado'}` : editForm.docFrente ? '✓ Frente' : '📎 Anexar PDF / 📷 Frente'}
                      <input type="file" accept="image/*,application/pdf" onChange={pickArquivo('docFrente')} className="hidden" />
                    </label>
                    {!editForm.docPdf && (
                      <label className={`text-center text-[11px] rounded border-2 border-dashed py-1.5 px-2 cursor-pointer ${editForm.docVerso ? 'border-emerald-400 text-emerald-700' : 'border-amber-300 text-amber-700'}`}>
                        {editForm.docVerso ? '✓ Verso' : '📷 Verso'}
                        <input type="file" accept="image/*" capture="environment" onChange={pickArquivo('docVerso')} className="hidden" />
                      </label>
                    )}
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-0.5">
                  <button onClick={() => setEditId(null)} className="text-[11px] text-gray-500 hover:underline">cancelar</button>
                  <button onClick={salvarEdicao} className="text-[11px] font-semibold text-emerald-700 hover:underline">salvar</button>
                </div>
              </div>
            ) : (
              <div key={t.id} className="flex items-center justify-between gap-2 py-1 text-sm">
                <span className="truncate">{t.nome} <span className="text-[11px] text-gray-400">· {t.parte_vinculada_nome || t.vinculo}</span>{t.documento_enviado && <span title="CNH/RG anexada" className="text-[10px] text-emerald-700"> · 📎 doc</span>}</span>
                <span className="flex items-center gap-2 shrink-0">
                  <span className={`text-[10px] px-2 py-0.5 rounded ${BADGE[t.status] || BADGE.pendente}`}>{t.status}</span>
                  {t.status !== 'assinado' && <>
                    <button onClick={() => iniciarEdicao(t)} title="Editar" className="text-gray-500 hover:text-emerald-700"><Pencil className="w-3.5 h-3.5" /></button>
                    <button onClick={() => reenviar(t.id)} className="text-[11px] text-emerald-700 hover:underline">reenviar</button>
                    <button onClick={() => excluirT(t)} title="Excluir" className="text-gray-400 hover:text-red-600"><Trash2 className="w-3.5 h-3.5" /></button>
                  </>}
                </span>
              </div>
            )))}
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
              <input className="border rounded-lg px-2 py-1.5 text-sm" placeholder="CPF" value={l.cpf} onChange={(e) => upd(i, { cpf: e.target.value.replace(/\D/g, '') })} />
              <input className="border rounded-lg px-2 py-1.5 text-sm" placeholder="WhatsApp 55DDDNUMERO" value={l.telefone} onChange={(e) => upd(i, { telefone: e.target.value.replace(/\D/g, '') })} />
            </div>
            <input className="w-full border rounded-lg px-2 py-1.5 text-sm" type="email" placeholder="E-mail" value={l.email} onChange={(e) => upd(i, { email: e.target.value })} />
            <select className="w-full border rounded-lg px-2 py-1.5 text-sm" value={l.parte_vinculada_id} onChange={(e) => upd(i, { parte_vinculada_id: e.target.value })}>
              <option value="">Vincular à parte…</option>
              {sigs.map((s) => <option key={s.id} value={s.id}>{s.nome} ({s.papel})</option>)}
            </select>
          </div>
        ))}
        <button onClick={addLinha} className="text-xs text-emerald-700 hover:underline mb-3 inline-flex items-center gap-1"><Plus className="w-3 h-3" /> Adicionar testemunha</button>

        <div className="flex justify-end gap-2">
          <button onClick={onClose} disabled={busy} className="px-3 py-2 rounded-lg text-sm border">Fechar</button>
          <button onClick={cadastrarEPosicionar} disabled={busy} className="px-4 py-2 rounded-lg text-sm font-semibold text-white inline-flex items-center gap-1" style={{ background: '#0C3320' }}>
            <MapPin className="w-4 h-4" /> {busy ? 'Preparando…' : 'Cadastrar e posicionar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function TPagina({ pg, posBox, corTid, onClick }) {
  const ref = React.useRef(null);
  const [rect, setRect] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const u = () => { if (ref.current) setRect({ w: ref.current.clientWidth, h: ref.current.clientHeight }); };
    u(); window.addEventListener('resize', u); return () => window.removeEventListener('resize', u);
  }, []);
  return (
    <div className="relative inline-block w-full max-w-[820px] mb-2" style={{ cursor: 'crosshair' }}>
      <img ref={ref} src={`data:image/png;base64,${pg.imagem_b64}`} alt={`pág ${pg.pagina + 1}`}
        className="w-full rounded border border-gray-600" onClick={onClick} draggable={false} />
      {Object.entries(posBox).map(([tid, boxes]) => (boxes || []).filter((b) => b.pagina === pg.pagina).map((b, i) => {
        const c = { left: (b.x_pt / pg.largura_pt) * rect.w, top: ((pg.altura_pt - b.y_pt - b.alt_pt) / pg.altura_pt) * rect.h,
          width: (b.larg_pt / pg.largura_pt) * rect.w, height: (b.alt_pt / pg.altura_pt) * rect.h };
        return <div key={tid + i} className="absolute pointer-events-none rounded"
          style={{ left: c.left, top: c.top, width: c.width, height: c.height, border: `2px solid ${corTid(tid)}`, background: `${corTid(tid)}22` }}>
          <span className="text-[9px] px-1" style={{ color: corTid(tid) }}>testemunha</span>
        </div>;
      }))}
    </div>
  );
}

const Btn = ({ icon: Icon, label, onClick, cls }) => (
  <button onClick={onClick} className={`flex items-center justify-center gap-1.5 border rounded-lg py-2 text-xs font-medium ${cls}`}>
    <Icon className="w-3.5 h-3.5" /> {label}
  </button>
);
