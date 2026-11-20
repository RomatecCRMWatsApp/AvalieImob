// @module components/dashboard/PrivacidadeConta — Configurações ▸ Privacidade.
// Exportar os dados da PRÓPRIA conta e abrir pedidos (inclusive encerramento da conta).
// Encerrar a conta NÃO apaga nada automaticamente: vira pedido com protocolo, porque laudos,
// contratos assinados e recibos podem ter guarda obrigatória e precisam de análise.
import React, { useEffect, useState } from 'react';
import { privacidadeAPI } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';

const ROTULO = {
  recebida: 'Recebido', verificando_identidade: 'Verificando identidade', em_analise: 'Em análise',
  atendida: 'Atendido', indeferida: 'Não atendido',
};

export default function PrivacidadeConta() {
  const { toast } = useToast();
  const [lista, setLista] = useState([]);
  const [baixando, setBaixando] = useState(false);
  const [encerrar, setEncerrar] = useState(false);
  const [motivo, setMotivo] = useState('');

  const carregar = () => privacidadeAPI.minhas().then((r) => setLista(r.solicitacoes || [])).catch(() => {});
  useEffect(() => { carregar(); }, []);

  const exportar = async () => {
    setBaixando(true);
    try {
      const r = await privacidadeAPI.exportarMeusDados();
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `avalieimob-meus-dados-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      toast({ title: 'Não foi possível gerar o arquivo agora', variant: 'destructive' });
    } finally {
      setBaixando(false);
    }
  };

  const pedirEncerramento = async () => {
    try {
      const r = await privacidadeAPI.solicitarDaConta('exclusao_conta', motivo.trim() || 'Quero encerrar minha conta.');
      toast({ title: 'Pedido registrado', description: `Protocolo ${r.protocolo}` });
      setEncerrar(false);
      setMotivo('');
      carregar();
    } catch (e) {
      toast({ title: 'Não foi possível registrar', description: e?.response?.data?.detail || '', variant: 'destructive' });
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="font-semibold text-gray-900 mb-1">Privacidade</h3>
      <p className="text-sm text-gray-600 mb-4">
        Baixe uma cópia dos dados vinculados à sua conta ou faça um pedido sobre eles.{' '}
        <a href="/privacidade" target="_blank" rel="noreferrer" className="underline">Como tratamos seus dados</a>.
      </p>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={exportar} disabled={baixando}
                className="px-4 py-2 rounded-md border border-emerald-800 text-emerald-900 text-sm font-semibold min-h-[44px]">
          {baixando ? 'Gerando…' : 'Baixar meus dados (JSON)'}
        </button>
        <button type="button" onClick={() => setEncerrar(true)}
                className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 text-sm min-h-[44px]">
          Pedir encerramento da conta
        </button>
      </div>
      <p className="text-xs text-gray-500 mt-2">
        O arquivo não inclui senha, certificados digitais nem chaves de integração. Imagens e PDFs aparecem
        como referência; baixe-os pelo próprio documento. Os cadastros de clientes são dados de outras pessoas:
        trate o arquivo com o mesmo cuidado.
      </p>

      {encerrar && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
          <p className="font-semibold text-amber-900">Antes de pedir</p>
          <p className="text-amber-900 mt-1">
            O encerramento não é imediato: laudos, contratos assinados e recibos podem ter prazo legal de guarda.
            O pedido é analisado e você recebe a resposta por e-mail. Para não ser cobrado de novo, basta não renovar
            o plano — não há renovação automática.
          </p>
          <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={1000}
                    placeholder="Opcional: conte o motivo ou o que deseja fazer com seus documentos."
                    className="w-full mt-3 border border-amber-200 rounded-md p-2 min-h-[80px] bg-white" />
          <div className="flex gap-2 mt-2">
            <button type="button" onClick={pedirEncerramento} className="px-4 py-2 rounded-md bg-amber-700 text-white font-semibold min-h-[44px]">Registrar pedido</button>
            <button type="button" onClick={() => setEncerrar(false)} className="px-4 py-2 rounded-md border border-gray-300 min-h-[44px]">Cancelar</button>
          </div>
        </div>
      )}

      {lista.length > 0 && (
        <div className="mt-5">
          <p className="text-sm font-medium text-gray-800 mb-2">Meus pedidos</p>
          <ul className="divide-y divide-gray-100 text-sm">
            {lista.map((p) => (
              <li key={p.protocolo} className="py-2 flex flex-wrap justify-between gap-2">
                <span><strong>{p.protocolo}</strong> · {p.tipo_label}</span>
                <span className="text-gray-600">{ROTULO[p.status] || p.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
