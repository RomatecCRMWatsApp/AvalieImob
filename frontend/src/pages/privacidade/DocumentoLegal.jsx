// @page DocumentoLegal — /privacidade e /termos.
// O texto vem do backend (MINUTA versionada, com hash). Enquanto a flag
// PRIVACIDADE_MINUTAS_ATIVAS estiver desligada, a página NÃO publica a minuta: mostra
// que o documento está em revisão e aponta o canal do titular. Os links "Política de
// Privacidade" do site (calculadora, rodapé) deixam de cair em 404.
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { privacidadeAPI } from '../../lib/api';
import { abrirPreferencias } from '../../lib/consentimentoCookies';

const TITULOS = { privacidade: 'Aviso de Privacidade', termos: 'Termos de Uso' };

// Markdown mínimo (títulos, listas, parágrafos, tabelas simples) sem HTML injetado.
function Markdown({ texto }) {
  const blocos = texto.replace(/\r/g, '').split(/\n{2,}/);
  return blocos.map((b, i) => {
    const linhas = b.split('\n');
    if (/^versao:/i.test(b)) return null;
    if (b.startsWith('# ')) return <h1 key={i} className="text-2xl font-bold text-emerald-950 mb-3">{b.slice(2)}</h1>;
    if (b.startsWith('## ')) return <h2 key={i} className="text-lg font-semibold text-emerald-900 mt-6 mb-2">{b.slice(3)}</h2>;
    if (b.startsWith('> ')) return <p key={i} className="bg-amber-50 border-l-4 border-amber-500 p-3 my-3 text-sm">{b.replace(/^> ?/gm, '').replace(/\*\*/g, '')}</p>;
    if (linhas.every((l) => /^(\d+\.|-) /.test(l.trim()) || l.startsWith('   '))) {
      return <ul key={i} className="list-disc pl-6 space-y-1 my-2">{linhas.filter((l) => /^(\d+\.|-) /.test(l.trim())).map((l, j) => <li key={j}>{l.trim().replace(/^(\d+\.|-) /, '').replace(/\*\*/g, '')}</li>)}</ul>;
    }
    if (linhas[0].startsWith('|')) {
      const rows = linhas.filter((l) => !/^\|[-| ]+\|$/.test(l)).map((l) => l.split('|').slice(1, -1).map((c) => c.trim()));
      return (
        <div key={i} className="overflow-x-auto my-3"><table className="text-sm border">
          <tbody>{rows.map((r, j) => <tr key={j} className={j === 0 ? 'bg-emerald-50 font-semibold' : ''}>{r.map((c, k) => <td key={k} className="border px-2 py-1 align-top">{c.replace(/\*\*/g, '')}</td>)}</tr>)}</tbody>
        </table></div>
      );
    }
    return <p key={i} className="my-2 leading-relaxed">{b.replace(/\*\*/g, '').replace(/`/g, '')}</p>;
  });
}

export default function DocumentoLegal({ tipo }) {
  const [doc, setDoc] = useState(null);
  const [estado, setEstado] = useState('carregando');

  useEffect(() => {
    let vivo = true;
    privacidadeAPI.documento(tipo)
      .then((d) => { if (vivo) { setDoc(d); setEstado('ok'); } })
      .catch(() => { if (vivo) setEstado('revisao'); });
    return () => { vivo = false; };
  }, [tipo]);

  return (
    <main className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-4 py-10 text-gray-800">
        <Link to="/" className="text-sm text-emerald-700 underline">← Voltar ao início</Link>
        {estado === 'carregando' && <p className="mt-6">Carregando…</p>}
        {estado === 'revisao' && (
          <section className="mt-6">
            <h1 className="text-2xl font-bold text-emerald-950 mb-3">{TITULOS[tipo]}</h1>
            <p className="mb-3">Este documento está em revisão e será publicado em breve.</p>
            <p className="mb-3">
              Para pedidos sobre dados pessoais (acesso, correção, eliminação, revogação de
              consentimento e outros), use a página{' '}
              <Link to="/privacidade/solicitacao" className="underline text-emerald-800">Solicitação sobre dados pessoais</Link>.
            </p>
          </section>
        )}
        {estado === 'ok' && doc && (
          <article className="mt-6">
            <Markdown texto={doc.texto} />
            <p className="text-xs text-gray-500 mt-8">Versão {doc.versao} · código {doc.hash.slice(0, 12)}</p>
          </article>
        )}
        <div className="mt-8 flex flex-wrap gap-4 text-sm">
          <Link to="/privacidade/solicitacao" className="underline text-emerald-800">Solicitação sobre dados pessoais</Link>
          <button type="button" onClick={() => abrirPreferencias()} className="underline text-emerald-800">Preferências de cookies</button>
        </div>
      </div>
    </main>
  );
}
