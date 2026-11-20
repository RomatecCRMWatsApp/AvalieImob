// @page SolicitacaoTitular — /privacidade/solicitacao (canal público do titular, sem conta).
// Etapas: formulário → código enviado ao e-mail → confirmado (protocolo + prazo).
// Também permite consultar o andamento por protocolo + e-mail.
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { privacidadeAPI } from '../../lib/api';

const INPUT = 'w-full border rounded-lg px-3 py-2 text-sm';
const BTN = 'px-4 py-2 rounded-lg text-sm font-semibold bg-emerald-900 text-white disabled:opacity-50';
const RELACOES = [
  ['cliente_de_usuario', 'Sou cliente/parte de um avaliador ou corretor que usa o AvalieImob'],
  ['usuario', 'Tenho (ou tive) conta no AvalieImob'],
  ['lead', 'Usei a calculadora ou o atendimento do site'],
  ['outro', 'Outro'],
];

function erroMsg(e, padrao) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  if (e?.response?.status === 429) return 'Muitas tentativas. Aguarde e tente novamente mais tarde.';
  return padrao;
}

export default function SolicitacaoTitular() {
  const [cfg, setCfg] = useState(null);
  const [etapa, setEtapa] = useState('form');
  const [f, setF] = useState({ nome: '', email: '', relacao: 'cliente_de_usuario', tipo_direito: 'confirmacao_acesso', descricao: '', declaracao_veracidade: false, website: '' });
  const [protocolo, setProtocolo] = useState('');
  const [codigo, setCodigo] = useState('');
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { privacidadeAPI.config().then(setCfg).catch(() => setCfg({ recursos_ativos: false })); }, []);

  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  async function enviar(e) {
    e.preventDefault(); setErro(''); setEnviando(true);
    try {
      const r = await privacidadeAPI.abrirPedido(f);
      setProtocolo(r.protocolo); setEtapa('codigo');
    } catch (err) { setErro(erroMsg(err, 'Não foi possível registrar o pedido.')); }
    setEnviando(false);
  }

  async function confirmar(e) {
    e.preventDefault(); setErro(''); setEnviando(true);
    try {
      setResultado(await privacidadeAPI.verificarPedido(protocolo, f.email, codigo)); setEtapa('ok');
    } catch (err) { setErro(erroMsg(err, 'Código inválido.')); }
    setEnviando(false);
  }

  async function consultar(e) {
    e.preventDefault(); setErro('');
    try { setResultado(await privacidadeAPI.statusPedido(protocolo, f.email)); setEtapa('ok'); } catch (err) { setErro(erroMsg(err, 'Protocolo não encontrado.')); }
  }

  if (!cfg) return <main className="p-8">Carregando…</main>;
  const tipos = cfg.tipos_direito || {};

  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto px-4 py-10 text-gray-800">
        <Link to="/privacidade" className="text-sm text-emerald-700 underline">← Aviso de Privacidade</Link>
        <h1 className="text-2xl font-bold text-emerald-950 mt-4 mb-2">Solicitação sobre dados pessoais</h1>
        {!cfg.recursos_ativos ? (
          <p className="mt-4">Este canal está em implantação. Enquanto isso, use os contatos de atendimento informados no rodapé do site.</p>
        ) : (
          <>
            <p className="text-sm mb-6">Não é preciso ter conta. Enviaremos um código ao seu e-mail para confirmar que o pedido é seu. Prazo interno de resposta: {cfg.prazo_resposta_dias} dias.</p>
            {erro && <p role="alert" className="bg-red-50 border border-red-300 text-red-800 rounded p-2 text-sm mb-4">{erro}</p>}
            {etapa === 'form' && (
              <form onSubmit={enviar} className="space-y-3">
                <label className="block text-sm">Nome<input className={INPUT} value={f.nome} onChange={set('nome')} required maxLength={120} autoComplete="name" /></label>
                <label className="block text-sm">E-mail<input type="email" className={INPUT} value={f.email} onChange={set('email')} required autoComplete="email" /></label>
                <label className="block text-sm">Sua relação conosco
                  <select className={INPUT} value={f.relacao} onChange={set('relacao')}>{RELACOES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                </label>
                <label className="block text-sm">O que você quer solicitar
                  <select className={INPUT} value={f.tipo_direito} onChange={set('tipo_direito')}>{Object.entries(tipos).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                </label>
                <label className="block text-sm">Detalhes (opcional — não envie documentos aqui)<textarea className={INPUT} rows={4} maxLength={4000} value={f.descricao} onChange={set('descricao')} /></label>
                <input type="text" name="website" value={f.website} onChange={set('website')} tabIndex={-1} autoComplete="off" aria-hidden="true" style={{ position: 'absolute', left: '-9999px' }} />
                <label className="flex gap-2 text-sm"><input type="checkbox" checked={f.declaracao_veracidade} onChange={set('declaracao_veracidade')} required />
                  <span>Declaro que as informações são verdadeiras e que o pedido é meu ou de quem represento legalmente.</span></label>
                <button className={BTN} disabled={enviando}>Enviar pedido</button>
              </form>
            )}
            {etapa === 'codigo' && (
              <form onSubmit={confirmar} className="space-y-3">
                <p className="text-sm">Protocolo: <b>{protocolo}</b>. Digite o código de 6 dígitos enviado para {f.email}.</p>
                <input className={INPUT} inputMode="numeric" maxLength={6} value={codigo} onChange={(e) => setCodigo(e.target.value)} required aria-label="Código de confirmação" />
                <button className={BTN} disabled={enviando}>Confirmar</button>
              </form>
            )}
            {etapa === 'ok' && resultado && (
              <div className="bg-emerald-50 border border-emerald-200 rounded p-4 text-sm">
                <p>Protocolo <b>{resultado.protocolo}</b> — situação: <b>{resultado.status}</b>.</p>
                {resultado.prazo_em && <p>Prazo interno: {new Date(resultado.prazo_em + (String(resultado.prazo_em).endsWith('Z') ? '' : 'Z')).toLocaleDateString('pt-BR')}.</p>}
              </div>
            )}
            <details className="mt-8 text-sm">
              <summary className="cursor-pointer text-emerald-800">Já tenho um protocolo — consultar andamento</summary>
              <form onSubmit={consultar} className="space-y-2 mt-3">
                <input className={INPUT} placeholder="Protocolo (PRIV-…)" value={protocolo} onChange={(e) => setProtocolo(e.target.value)} required />
                <input type="email" className={INPUT} placeholder="E-mail usado no pedido" value={f.email} onChange={set('email')} required />
                <button className={BTN}>Consultar</button>
              </form>
            </details>
          </>
        )}
      </div>
    </main>
  );
}
