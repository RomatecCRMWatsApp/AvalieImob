// @page Privacidade — /privacidade: responsável pelo tratamento, canal do titular e cookies.
//
// O AVISO DE PRIVACIDADE COMPLETO ainda é minuta (docs/privacidade/minutas/) e só entra
// aqui depois da revisão jurídica (data/privacidade.json → aviso_completo_aprovado).
// Esta página publica apenas fatos já verificáveis + o canal para exercer direitos,
// que funciona também para quem não tem conta.
import React, { useState } from 'react';
import SEO from '../components/common/SEO';
import Navbar from '../components/landing/Navbar';
import Footer from '../components/landing/Footer';
import cfg from '../data/privacidade.json';
import { privacidadeAPI } from '../lib/api';
import { abrirPreferencias, trackersConfigurados } from '../lib/consentimento';

const VERDE = '#0C3320';
const TIPOS = [
  ['confirmacao_acesso', 'Saber se tenho dados no sistema e acessá-los'],
  ['correcao', 'Corrigir dados incompletos ou errados'],
  ['compartilhamento', 'Saber com quem meus dados são compartilhados'],
  ['revogacao', 'Revogar um consentimento que dei'],
  ['eliminacao', 'Pedir eliminação, anonimização ou bloqueio'],
  ['portabilidade', 'Portabilidade dos meus dados'],
  ['outro', 'Outro assunto de privacidade'],
];

function Secao({ titulo, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-xl font-bold mb-3" style={{ color: VERDE }}>{titulo}</h2>
      <div className="space-y-3 text-gray-700 leading-relaxed">{children}</div>
    </section>
  );
}

export default function Privacidade() {
  const [f, setF] = useState({ tipo: 'confirmacao_acesso', nome: '', email: '', telefone: '', relacao: 'titular', descricao: '', website: '' });
  const [enviando, setEnviando] = useState(false);
  const [protocolo, setProtocolo] = useState(null);
  const [erro, setErro] = useState('');
  const c = cfg.controlador;
  const temTrackers = trackersConfigurados().length > 0;

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const enviar = async (e) => {
    e.preventDefault();
    setErro('');
    setEnviando(true);
    try {
      const r = await privacidadeAPI.solicitar(f);
      setProtocolo(r.protocolo || 'registrado');
    } catch (err) {
      const d = err?.response?.data?.detail;
      setErro(typeof d === 'string' ? d : 'Não foi possível registrar agora. Escreva para ' + c.email + '.');
    } finally {
      setEnviando(false);
    }
  };
  const campo = 'w-full border border-gray-300 rounded-md px-3 py-2 text-sm min-h-[44px]';

  return (
    <>
      <SEO
        title="Privacidade e LGPD"
        description="Quem é o responsável pelos dados no AvalieImob e como pedir acesso, correção ou eliminação dos seus dados pessoais."
        url="https://www.romatecavalieimob.com.br/privacidade"
      />
      <div className="bg-white pt-28">
        <Navbar />
        <main className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          <h1 className="text-3xl font-extrabold mb-2" style={{ color: VERDE }}>Privacidade e LGPD</h1>
          <p className="text-gray-600 mb-8">Como falar com o responsável pelos seus dados e exercer os direitos da Lei 13.709/2018.</p>

          <Secao titulo="Quem é o responsável">
            <p><strong>{c.razao_social}</strong> — CNPJ {c.cnpj}<br />{c.endereco}<br />Contato de privacidade: <a className="underline" href={`mailto:${c.email}`}>{c.email}</a></p>
            <p className="text-sm text-gray-500">
              Quando você é cliente de um avaliador ou corretor que usa o AvalieImob, os seus dados
              (por exemplo, num laudo ou contrato) foram cadastrados por esse profissional. Você pode
              falar diretamente com ele ou usar o formulário abaixo — encaminharemos o pedido.
            </p>
          </Secao>

          {!cfg.aviso_completo_aprovado && (
            <Secao titulo="Aviso de privacidade">
              <p>O aviso completo — dados tratados, finalidades, fornecedores, prazos de guarda — está em revisão e será publicado nesta página. Enquanto isso, qualquer dúvida pode ser enviada pelo canal abaixo.</p>
            </Secao>
          )}

          <Secao titulo="Cookies e medição">
            {temTrackers ? (
              <p>Ferramentas de medição só são carregadas se você permitir. <button type="button" onClick={abrirPreferencias} className="underline font-semibold" style={{ color: VERDE }}>Ver ou mudar minhas preferências</button></p>
            ) : (
              <p>Este site usa apenas armazenamento necessário: o login de quem tem conta, a sessão do atendimento e preferências de tela. Não usamos cookies de publicidade.</p>
            )}
          </Secao>

          <Secao titulo="Exercer seus direitos">
            <p>Você pode pedir confirmação e acesso aos seus dados, correção, informação sobre compartilhamento, revogação de consentimento, eliminação, anonimização ou bloqueio. Não é preciso ter conta. Cada pedido recebe um protocolo; antes de entregar ou apagar dados, podemos pedir uma confirmação de identidade, para evitar que outra pessoa faça o pedido em seu nome.</p>
            <p>Quem tem conta também pode baixar os próprios dados em <a className="underline" href="/dashboard/config">Configurações ▸ Privacidade</a>.</p>

            {protocolo ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4" role="status">
                <p className="font-semibold" style={{ color: VERDE }}>Pedido registrado.</p>
                <p>Protocolo: <strong>{protocolo}</strong>. Guarde este número. A resposta vai para o e-mail informado.</p>
              </div>
            ) : (
              <form onSubmit={enviar} className="space-y-3 rounded-lg border border-gray-200 p-4">
                <label className="block">
                  <span className="text-sm font-medium">O que você precisa</span>
                  <select className={campo} value={f.tipo} onChange={set('tipo')}>
                    {TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </label>
                <div className="grid sm:grid-cols-2 gap-3">
                  <label className="block"><span className="text-sm font-medium">Nome completo</span>
                    <input className={campo} value={f.nome} onChange={set('nome')} required autoComplete="name" /></label>
                  <label className="block"><span className="text-sm font-medium">E-mail para resposta</span>
                    <input className={campo} type="email" value={f.email} onChange={set('email')} required autoComplete="email" /></label>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <label className="block"><span className="text-sm font-medium">Telefone (opcional)</span>
                    <input className={campo} value={f.telefone} onChange={set('telefone')} autoComplete="tel" /></label>
                  <label className="block"><span className="text-sm font-medium">Você é</span>
                    <select className={campo} value={f.relacao} onChange={set('relacao')}>
                      <option value="titular">O próprio titular dos dados</option>
                      <option value="representante">Representante do titular</option>
                    </select></label>
                </div>
                <label className="block"><span className="text-sm font-medium">Descreva o pedido</span>
                  <textarea className={`${campo} min-h-[110px]`} value={f.descricao} onChange={set('descricao')} required
                            placeholder="Ex.: sou cliente do avaliador Fulano e quero saber quais dados meus constam no laudo." /></label>
                {/* campo invisível para pessoas: robôs preenchem e o pedido é descartado */}
                <input type="text" name="website" value={f.website} onChange={set('website')} tabIndex={-1} autoComplete="off"
                       aria-hidden="true" style={{ position: 'absolute', left: '-9999px' }} />
                <p className="text-xs text-gray-500">Não envie documentos nem CPF por aqui. Se for preciso confirmar sua identidade, pediremos pelo e-mail informado.</p>
                {erro && <p className="text-sm text-red-700" role="alert">{erro}</p>}
                <button type="submit" disabled={enviando} className="px-5 py-2 rounded-md text-white font-semibold min-h-[44px]" style={{ background: VERDE }}>
                  {enviando ? 'Enviando…' : 'Enviar pedido'}
                </button>
              </form>
            )}
          </Secao>
        </main>
        <Footer />
      </div>
    </>
  );
}
