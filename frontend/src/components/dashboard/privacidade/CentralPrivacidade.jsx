// @module components/dashboard/privacidade/CentralPrivacidade — /dashboard/privacidade
// Aceites (Termos/Aviso, versionados), consentimentos opcionais de marketing,
// exportação dos dados da conta (link de uso único e curta duração), pedidos de
// privacidade e informação clara sobre a assinatura (sem renovação automática).
// Nada aqui exclui dados automaticamente: exclusão de conta é um pedido analisado.
import React, { useCallback, useEffect, useState } from 'react';
import { privacidadeAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const CARD = 'bg-white border rounded-xl p-4 mb-4';
const BTN = 'px-3 py-2 rounded-lg text-sm font-semibold border border-emerald-900 text-emerald-950 hover:bg-emerald-50 disabled:opacity-50';
const NOMES = { termos: 'Termos de Uso', privacidade: 'Aviso de Privacidade' };

const fmt = (d) => (d ? new Date(String(d).endsWith('Z') ? d : `${d}Z`).toLocaleString('pt-BR') : '—');

export default function CentralPrivacidade() {
  const { toast } = useToast();
  const [dados, setDados] = useState(null);
  const [assin, setAssin] = useState(null);
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setDados(await privacidadeAPI.me());
      setAssin(await privacidadeAPI.assinatura());
    } catch (e) {
      setErro(e?.response?.status === 404 ? 'A Central de Privacidade está em implantação.' : 'Não foi possível carregar.');
    }
  }, []);
  useEffect(() => { carregar(); }, [carregar]);

  async function aceitar(tipo) {
    try {
      const doc = await privacidadeAPI.documento(tipo);
      if (!window.confirm(`Confirmar aceite de "${NOMES[tipo]}" versão ${doc.versao}? Leia o texto em /${tipo === 'termos' ? 'termos' : 'privacidade'}.`)) return;
      await privacidadeAPI.aceitar(tipo, doc.versao, doc.hash);
      toast({ title: 'Aceite registrado.' });
      carregar();
    } catch (e) { toast({ title: e?.response?.data?.detail || 'Documento indisponível.' }); }
  }

  async function consentir(fin, valor) {
    await privacidadeAPI.consentir(fin, valor);
    carregar();
  }

  async function exportar(formato) {
    setOcupado(true);
    try {
      const r = await privacidadeAPI.criarExportacao(formato);
      const blob = await privacidadeAPI.baixarExportacao(r.url);
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `meus-dados-avalieimob.${formato}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    } catch (e) { toast({ title: 'Falha ao exportar.' }); }
    setOcupado(false);
  }

  async function pedido(tipo) {
    const descricao = window.prompt('Descreva o pedido (opcional):') ?? null;
    if (descricao === null) return;
    const r = await privacidadeAPI.pedidoConta(tipo, descricao);
    toast({ title: `Pedido ${r.protocolo} registrado.` });
    carregar();
  }

  async function arrependimento() {
    if (!window.confirm('Registrar pedido de arrependimento? Ele será analisado pelo atendimento; nada é cobrado ou estornado automaticamente.')) return;
    const r = await privacidadeAPI.arrependimento();
    toast({ title: `Pedido ${r.protocolo} registrado.` });
    carregar();
  }

  if (erro) return <div className="p-6 text-sm">{erro}</div>;
  if (!dados) return <div className="p-6 text-sm">Carregando…</div>;

  return (
    <div className="max-w-3xl mx-auto p-4 text-sm text-gray-800">
      <h1 className="text-xl font-bold text-emerald-950 mb-4">Central de Privacidade</h1>

      <section className={CARD}>
        <h2 className="font-semibold mb-2">Termos e Aviso de Privacidade</h2>
        {Object.entries(dados.aceites).map(([tipo, a]) => (
          <div key={tipo} className="flex flex-wrap items-center justify-between gap-2 py-1">
            <span>{NOMES[tipo]} {a.versao_atual ? `— versão ${a.versao_atual}` : '— em revisão'}
              {a.aceito_em ? ` · aceito em ${fmt(a.aceito_em)}` : ''}</span>
            {a.pendente && a.versao_atual && <button type="button" className={BTN} onClick={() => aceitar(tipo)}>Ler e aceitar</button>}
          </div>
        ))}
      </section>

      <section className={CARD}>
        <h2 className="font-semibold mb-2">Comunicações opcionais</h2>
        <p className="mb-2 text-gray-600">Independentes do uso do sistema. Você pode mudar a qualquer momento.</p>
        {Object.entries(dados.consentimentos).map(([fin, c]) => (
          <label key={fin} className="flex items-center gap-2 py-1">
            <input type="checkbox" checked={c.concedido} onChange={(e) => consentir(fin, e.target.checked)} />
            <span>{c.rotulo}{c.atualizado_em ? ` (atualizado em ${fmt(c.atualizado_em)})` : ''}</span>
          </label>
        ))}
      </section>

      <section className={CARD}>
        <h2 className="font-semibold mb-2">Meus dados</h2>
        <p className="mb-2 text-gray-600">Baixa os dados da sua conta. Clientes e outras pessoas cadastradas por você aparecem só como contagem.</p>
        <div className="flex gap-2">
          <button type="button" className={BTN} disabled={ocupado} onClick={() => exportar('json')}>Exportar (JSON)</button>
          <button type="button" className={BTN} disabled={ocupado} onClick={() => exportar('csv')}>Exportar (CSV)</button>
        </div>
      </section>

      <section className={CARD}>
        <h2 className="font-semibold mb-2">Pedidos sobre meus dados</h2>
        <div className="flex flex-wrap gap-2 mb-3">
          <button type="button" className={BTN} onClick={() => pedido('correcao')}>Pedir correção</button>
          <button type="button" className={BTN} onClick={() => pedido('anonimizacao_bloqueio_eliminacao')}>Pedir exclusão da conta</button>
          <button type="button" className={BTN} onClick={() => pedido('informacao_compartilhamento')}>Com quem meus dados são compartilhados</button>
        </div>
        <p className="text-gray-600 mb-2">Excluir a conta não apaga automaticamente laudos, contratos e clientes cadastrados — o destino desses registros é tratado no pedido.</p>
        {dados.pedidos.length > 0 && (
          <ul className="space-y-1">{dados.pedidos.map((p) => <li key={p.protocolo}>{p.protocolo} — {p.tipo_direito} — <b>{p.status}</b></li>)}</ul>
        )}
      </section>

      {assin && (
        <section className={CARD}>
          <h2 className="font-semibold mb-2">Assinatura</h2>
          <p>Plano: {assin.plano || '—'} · situação: {assin.status || '—'} · acesso até {fmt(assin.acesso_ate)}</p>
          <p className="mt-1">{assin.como_cancelar}</p>
          {assin.dentro_prazo_arrependimento_7_dias && (
            <button type="button" className={`${BTN} mt-2`} onClick={arrependimento}>Desistir da contratação (7 dias)</button>
          )}
          <p className="mt-2 text-gray-600">{assin.observacao}</p>
        </section>
      )}
    </div>
  );
}
