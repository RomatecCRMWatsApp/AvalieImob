// @module dashboard/assinatura/EnviarAssinaturaModal — Enviar documento para assinatura (3 passos).
import React, { useState, useEffect, useMemo } from 'react';
import { X, Loader2, ChevronRight, ArrowLeft, Plus, Trash2, Send } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { useToast } from '../../../hooks/use-toast';
import { assinaturaExternaAPI as API } from '../../../lib/api';

const PAPEIS = ['contratante', 'contratado', 'testemunha', 'avaliador', 'vendedor', 'comprador', 'signatário'];
const AUTHS = [['email', 'E-mail'], ['whatsapp', 'WhatsApp'], ['icp', 'ICP-Brasil']];
const novoSig = () => ({ nome: '', email: '', whatsapp: '', cpf_cnpj: '', papel: 'signatário', autenticacao: ['email'] });

const EnviarAssinaturaModal = ({ origemTipo, origemId, origemLabel, signatariosSugeridos = [], onClose, onEnviado }) => {
  const { toast } = useToast();
  const nav = useNavigate();
  const [provedores, setProvedores] = useState([]);
  const [creds, setCreds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1);
  const [provider, setProvider] = useState('');
  const [sigs, setSigs] = useState(signatariosSugeridos.length
    ? signatariosSugeridos.map((s) => ({ ...novoSig(), ...s })) : [novoSig()]);
  const [msg, setMsg] = useState('');
  const [prazo, setPrazo] = useState(15);
  const [ordemSeq, setOrdemSeq] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [p, c] = await Promise.all([API.provedores(), API.listar()]);
        setProvedores(Array.isArray(p) ? p : []);
        setCreds(Array.isArray(c) ? c : []);
        const pad = (c || []).find((x) => x.padrao) || (c || [])[0];
        if (pad) setProvider(pad.provider);
      } catch { toast({ title: 'Falha ao carregar provedores', variant: 'destructive' }); }
      finally { setLoading(false); }
    })();
  }, [toast]);

  const conectados = useMemo(
    () => creds.map((c) => ({ ...c, meta: provedores.find((p) => p.slug === c.provider) })).filter((c) => c.meta),
    [creds, provedores]);
  const provMeta = provedores.find((p) => p.slug === provider);
  const authsDisponiveis = AUTHS.filter(([a]) =>
    a === 'email' || (a === 'whatsapp' && provMeta?.suporta_whatsapp) || (a === 'icp' && provMeta?.suporta_icp_brasil));

  const setSig = (i, k, v) => setSigs((s) => s.map((x, idx) => (idx === i ? { ...x, [k]: v } : x)));
  const toggleAuth = (i, a) => setSigs((s) => s.map((x, idx) => {
    if (idx !== i) return x;
    const has = x.autenticacao.includes(a);
    return { ...x, autenticacao: has ? x.autenticacao.filter((z) => z !== a) : [...x.autenticacao, a] };
  }));
  const addSig = () => setSigs((s) => [...s, novoSig()]);
  const rmSig = (i) => setSigs((s) => (s.length > 1 ? s.filter((_, idx) => idx !== i) : s));

  const sigsValidos = sigs.filter((s) => (s.nome || '').trim() && ((s.email || '').trim() || (s.whatsapp || '').trim()));

  const enviar = async () => {
    setEnviando(true);
    try {
      const payload = {
        provider, origem_tipo: origemTipo, origem_id: origemId,
        signatarios: sigsValidos.map((s, i) => ({
          nome: s.nome, email: s.email || null, whatsapp: s.whatsapp || null, cpf_cnpj: s.cpf_cnpj || null,
          papel: s.papel, autenticacao: s.autenticacao, ordem: ordemSeq ? i + 1 : null,
        })),
        opcoes: { mensagem: msg, prazo_dias: Number(prazo) || null, ordem_sequencial: ordemSeq },
      };
      const r = await API.criarEnvio(payload);
      toast({ title: 'Enviado para assinatura', description: `${sigsValidos.length} signatário(s).` });
      onEnviado?.(r);
      onClose();
      nav('/dashboard/assinaturas');
    } catch (e) {
      const d = e.response?.data?.detail;
      toast({ title: 'Falha no envio', description: typeof d === 'string' ? d : (d?.mensagem || 'Erro'), variant: 'destructive' });
    } finally { setEnviando(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl">
        <div className="bg-emerald-900 text-white px-5 py-4 flex items-center justify-between">
          <div>
            <div className="font-display text-lg font-bold">Enviar para assinatura</div>
            {origemLabel && <div className="text-[11px] text-emerald-200">{origemLabel}</div>}
          </div>
          <button type="button" onClick={onClose}><X className="w-5 h-5" /></button>
        </div>

        <div className="px-5 pt-3">
          <div className="flex gap-1.5 text-[11px] font-semibold">
            {['Provedor', 'Signatários', 'Revisão'].map((t, i) => (
              <div key={t} className={`px-2.5 py-1 rounded-full ${step === i + 1 ? 'bg-emerald-600 text-white' : step > i + 1 ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-400'}`}>
                {i + 1}. {t}
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {loading ? (
            <div className="py-10 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-600" /></div>
          ) : step === 1 ? (
            conectados.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 p-6 text-center text-sm text-gray-500">
                Nenhum provedor conectado.
                <button type="button" onClick={() => { onClose(); nav('/dashboard/assinatura-digital'); }}
                  className="block mx-auto mt-2 text-emerald-700 font-semibold hover:underline">Configurar assinatura digital →</button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {conectados.map((c) => (
                  <button key={c.provider} type="button" onClick={() => setProvider(c.provider)}
                    className={`text-left rounded-xl border p-3 transition ${provider === c.provider ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 hover:border-emerald-300'}`}>
                    <div className="font-semibold text-gray-800">{c.meta.nome}</div>
                    <div className="text-[11px] text-gray-400">{c.ambiente === 'sandbox' ? 'Sandbox' : 'Produção'}{c.padrao ? ' · padrão' : ''}</div>
                  </button>
                ))}
              </div>
            )
          ) : step === 2 ? (
            <div className="space-y-3">
              {sigs.map((s, i) => (
                <div key={i} className="rounded-xl border border-gray-200 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-emerald-800">Signatário {i + 1}</span>
                    <button type="button" onClick={() => rmSig(i)} className="text-red-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <Input placeholder="Nome *" value={s.nome} onChange={(e) => setSig(i, 'nome', e.target.value)} />
                    <select value={s.papel} onChange={(e) => setSig(i, 'papel', e.target.value)}
                      className="rounded-xl border border-gray-200 px-3 py-2 text-sm">
                      {PAPEIS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <Input placeholder="E-mail" value={s.email} onChange={(e) => setSig(i, 'email', e.target.value)} />
                    <Input placeholder="WhatsApp (+55…)" value={s.whatsapp} onChange={(e) => setSig(i, 'whatsapp', e.target.value)} />
                    <Input placeholder="CPF/CNPJ" value={s.cpf_cnpj} onChange={(e) => setSig(i, 'cpf_cnpj', e.target.value)} />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {authsDisponiveis.map(([a, lbl]) => (
                      <button key={a} type="button" onClick={() => toggleAuth(i, a)}
                        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${s.autenticacao.includes(a) ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-500 border-gray-200'}`}>
                        {lbl}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <button type="button" onClick={addSig} className="inline-flex items-center gap-1 text-[12px] font-semibold text-emerald-700 hover:underline">
                <Plus className="w-4 h-4" /> adicionar signatário
              </button>
              {provMeta?.suporta_ordem_assinatura && (
                <label className="flex items-center gap-2 text-sm text-gray-700 pt-1">
                  <input type="checkbox" checked={ordemSeq} onChange={(e) => setOrdemSeq(e.target.checked)} className="w-4 h-4 accent-emerald-600" />
                  Assinatura em ordem (sequencial)
                </label>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-xl bg-gray-50 border border-gray-100 p-3 text-sm">
                <div><b>Provedor:</b> {provMeta?.nome}</div>
                <div><b>Documento:</b> {origemLabel || `${origemTipo} ${origemId}`}</div>
                <div><b>Signatários:</b> {sigsValidos.map((s) => s.nome).join(', ') || '—'}</div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Mensagem ao signatário</label>
                <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={3}
                  placeholder="Segue o documento para sua assinatura…"
                  className="w-full mt-1 rounded-xl border border-gray-200 px-3 py-2 text-sm" />
              </div>
              <div className="w-40">
                <label className="text-xs font-medium text-gray-600">Prazo (dias)</label>
                <Input type="number" value={prazo} onChange={(e) => setPrazo(e.target.value)} />
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-gray-100 px-5 py-3 flex items-center justify-between">
          <Button type="button" variant="outline" disabled={step === 1} onClick={() => setStep((s) => Math.max(1, s - 1))} className="gap-1">
            <ArrowLeft className="w-4 h-4" /> Voltar
          </Button>
          {step < 3 ? (
            <Button type="button" onClick={() => setStep((s) => s + 1)}
              disabled={(step === 1 && !provider) || (step === 2 && sigsValidos.length === 0)}
              className="bg-emerald-700 hover:bg-emerald-800 text-white gap-1">
              Avançar <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button type="button" onClick={enviar} disabled={enviando || sigsValidos.length === 0}
              className="bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Enviar
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnviarAssinaturaModal;
