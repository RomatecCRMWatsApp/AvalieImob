// @module dashboard/AssinaturaExternaConfig — Configurações → Assinatura Digital (BYOK).
// Cards por provedor + drawer com formulário DINÂMICO a partir de /provedores.
import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck, Eye, EyeOff, X, Loader2, CheckCircle2, AlertTriangle, Trash2, Star,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { useToast } from '../../hooks/use-toast';
import { BrandSpinner } from '../brand/BrandSpinner';
import { assinaturaExternaAPI as API } from '../../lib/api';

const statusDe = (cred) => {
  if (!cred) return { label: 'Não configurado', cls: 'bg-gray-100 text-gray-500 border-gray-200' };
  if (cred.ultimo_teste_ok === true) return { label: 'Conectado', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
  if (cred.ultimo_teste_ok === false) return { label: 'Falha na conexão', cls: 'bg-red-50 text-red-600 border-red-200' };
  return { label: 'Configurado (teste pendente)', cls: 'bg-amber-50 text-amber-700 border-amber-200' };
};
const fmtData = (iso) => { try { return iso ? new Date(iso).toLocaleString('pt-BR') : ''; } catch { return ''; } };
const detalhe = (e) => { const d = e?.response?.data?.detail; return typeof d === 'string' ? d : (d?.mensagem || 'Erro inesperado'); };

const Drawer = ({ prov, cred, onClose, onSaved, toast }) => {
  const editing = !!cred;
  const camposSenha = prov.campos_credenciais.filter((c) => c.tipo !== 'select_cofre');
  const campoCofre = prov.campos_credenciais.find((c) => c.tipo === 'select_cofre');

  const [ambiente, setAmbiente] = useState(cred?.ambiente || 'producao');
  const [valores, setValores] = useState({});
  const [show, setShow] = useState({});
  const [teste, setTeste] = useState(cred?.ultimo_teste_ok === true ? { ok: true, mensagem: 'Conexão OK' } : null);
  const [cofres, setCofres] = useState([]);
  const [cofre, setCofre] = useState('');
  const [testando, setTestando] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [padrao, setPadrao] = useState(!!cred?.padrao);

  const setV = (k, v) => {
    setValores((s) => ({ ...s, [k]: v }));
    if (camposSenha.some((c) => c.key === k)) setTeste(null); // trocou credencial → re-testar
  };
  const montarCred = () => {
    const cr = {};
    camposSenha.forEach((c) => { if ((valores[c.key] || '').trim()) cr[c.key] = valores[c.key].trim(); });
    if (campoCofre && cofre) cr[campoCofre.key] = cofre;
    return cr;
  };
  const podeTestar = editing || camposSenha.filter((c) => c.obrigatorio).every((c) => (valores[c.key] || '').trim());

  const testar = async () => {
    setTestando(true); setTeste(null);
    try {
      await API.salvar({ provider: prov.slug, ambiente, credenciais: montarCred(), padrao });
      const r = await API.testar(prov.slug);
      setTeste(r);
      if (r.ok && campoCofre) setCofres(r.dados?.cofres || []);
      toast({ title: r.ok ? 'Conexão OK' : 'Falha na conexão', description: r.mensagem,
              variant: r.ok ? undefined : 'destructive' });
    } catch (e) {
      const msg = detalhe(e); setTeste({ ok: false, mensagem: msg });
      toast({ title: 'Erro no teste', description: msg, variant: 'destructive' });
    } finally { setTestando(false); }
  };

  const salvar = async () => {
    setSalvando(true);
    try {
      await API.salvar({ provider: prov.slug, ambiente, credenciais: montarCred(), padrao });
      toast({ title: 'Conexão salva' }); onSaved(); onClose();
    } catch (e) { toast({ title: 'Falha ao salvar', description: detalhe(e), variant: 'destructive' }); }
    finally { setSalvando(false); }
  };

  const remover = async () => {
    if (!window.confirm(`Remover a conexão com ${prov.nome}?`)) return;
    try { await API.remover(prov.slug); toast({ title: 'Conexão removida' }); onSaved(); onClose(); }
    catch (e) { toast({ title: 'Falha ao remover', description: detalhe(e), variant: 'destructive' }); }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white h-full overflow-y-auto shadow-xl">
        <div className="sticky top-0 bg-emerald-900 text-white px-5 py-4 flex items-center justify-between z-10">
          <div className="font-display text-lg font-bold">{prov.nome}</div>
          <button type="button" onClick={onClose}><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-600">Ambiente</label>
            <div className="flex gap-2 mt-1">
              {['producao', 'sandbox'].map((a) => (
                <button key={a} type="button" onClick={() => setAmbiente(a)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${ambiente === a ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200'}`}>
                  {a === 'producao' ? 'Produção' : 'Sandbox'}
                </button>
              ))}
            </div>
            {ambiente === 'sandbox' && <p className="text-[11px] text-amber-600 mt-1">Documentos em sandbox não têm validade jurídica.</p>}
          </div>

          {camposSenha.map((c) => (
            <div key={c.key}>
              <label className="text-xs font-medium text-gray-600">{c.label}{c.obrigatorio ? ' *' : ''}</label>
              <div className="relative mt-1">
                <Input type={show[c.key] ? 'text' : 'password'} value={valores[c.key] || ''}
                  placeholder={editing ? '•••••••• (mantém o atual)' : ''}
                  onChange={(e) => setV(c.key, e.target.value)} className="pr-9" />
                <button type="button" onClick={() => setShow((s) => ({ ...s, [c.key]: !s[c.key] }))}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" tabIndex={-1}>
                  {show[c.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {c.ajuda && <p className="text-[10px] text-gray-400 mt-0.5">{c.ajuda}</p>}
            </div>
          ))}

          <Button type="button" onClick={testar} disabled={testando || !podeTestar} variant="outline" className="w-full gap-1">
            {testando ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />} Testar conexão
          </Button>
          {teste && (
            <div className={`rounded-lg p-2 text-xs flex items-center gap-1.5 ${teste.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
              {teste.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />} {teste.mensagem}
            </div>
          )}

          {campoCofre && teste?.ok && (
            <div>
              <label className="text-xs font-medium text-gray-600">{campoCofre.label}</label>
              <select value={cofre} onChange={(e) => setCofre(e.target.value)}
                className="w-full mt-1 rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-emerald-400">
                <option value="">— selecione o cofre —</option>
                {cofres.map((cf) => <option key={cf.uuid} value={cf.uuid}>{cf.nome || cf.uuid}</option>)}
              </select>
              <p className="text-[10px] text-gray-400 mt-0.5">Necessário para enviar documentos.</p>
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={padrao} onChange={(e) => setPadrao(e.target.checked)} className="w-4 h-4 accent-emerald-600" />
            Usar como provedor padrão
          </label>

          {prov.ajuda?.length > 0 && (
            <div className="rounded-lg bg-gray-50 border border-gray-100 p-3">
              <div className="text-[11px] font-bold text-gray-600 uppercase mb-1">Como obter as chaves</div>
              <ol className="text-[11px] text-gray-500 list-decimal ml-4 space-y-0.5">
                {prov.ajuda.map((a, i) => <li key={i}>{a}</li>)}
              </ol>
              {prov.tutorial_url && (
                <a href={prov.tutorial_url} target="_blank" rel="noreferrer"
                  className="text-[11px] text-emerald-700 hover:underline mt-1 inline-block">Documentação oficial →</a>
              )}
            </div>
          )}

          <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
            <Button type="button" onClick={salvar} disabled={salvando || !teste?.ok}
              className="flex-1 bg-emerald-900 hover:bg-emerald-800 text-white gap-1">
              {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Salvar
            </Button>
            {editing && (
              <Button type="button" variant="outline" onClick={remover}
                className="text-red-500 border-red-200 hover:bg-red-50"><Trash2 className="w-4 h-4" /></Button>
            )}
          </div>
          <p className="text-[10px] text-gray-400">O botão “Salvar” habilita após o teste de conexão retornar OK.</p>
        </div>
      </div>
    </div>
  );
};

const AssinaturaExternaConfig = () => {
  const { toast } = useToast();
  const [provedores, setProvedores] = useState([]);
  const [creds, setCreds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawer, setDrawer] = useState(null);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([API.provedores(), API.listar()]);
      setProvedores(Array.isArray(p) ? p : []);
      setCreds(Array.isArray(c) ? c : []);
    } catch { toast({ title: 'Falha ao carregar', variant: 'destructive' }); }
    finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { carregar(); }, [carregar]);

  if (loading) return <div className="py-20 flex justify-center"><BrandSpinner label="Carregando…" /></div>;

  const credDe = (slug) => creds.find((c) => c.provider === slug);
  const prov = provedores.find((p) => p.slug === drawer);

  return (
    <div className="max-w-4xl mx-auto pb-24 space-y-5">
      <div>
        <div className="font-display text-2xl font-bold text-gray-900">Assinatura Digital</div>
        <p className="text-sm text-gray-500 mt-1">Conecte a sua própria conta nas plataformas de assinatura eletrônica.</p>
      </div>

      <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-4 text-[13px] text-emerald-900 flex gap-2">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
        <span>As assinaturas são processadas na <b>sua conta</b> da plataforma escolhida e consomem os créditos do seu plano com ela. O AvalieImob <b>não cobra por documento assinado</b> — a integração está inclusa no seu plano.</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {provedores.map((p) => {
          const c = credDe(p.slug); const st = statusDe(c);
          return (
            <button key={p.slug} type="button" onClick={() => setDrawer(p.slug)}
              className="text-left rounded-xl border border-gray-200 bg-white p-4 hover:border-emerald-300 hover:shadow-sm transition">
              <div className="flex items-center justify-between">
                <div className="font-semibold text-gray-800">{p.nome}</div>
                {c?.padrao && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-600">
                    <Star className="w-3 h-3 fill-amber-500 text-amber-500" /> PADRÃO
                  </span>
                )}
              </div>
              <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${st.cls}`}>{st.label}</span>
              {c?.ultimo_teste_em && <div className="text-[10px] text-gray-400 mt-1.5">testado em {fmtData(c.ultimo_teste_em)}</div>}
              <div className="text-[11px] text-emerald-700 mt-3 font-medium">{c ? 'Gerenciar →' : 'Configurar →'}</div>
            </button>
          );
        })}
      </div>

      {prov && (
        <Drawer prov={prov} cred={credDe(prov.slug)} onClose={() => setDrawer(null)} onSaved={carregar} toast={toast} />
      )}
    </div>
  );
};

export default AssinaturaExternaConfig;
