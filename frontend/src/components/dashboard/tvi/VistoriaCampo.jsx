// @module VistoriaCampo — vistoria no celular, funciona sem internet.
// A vistoria é gravada no aparelho e enviada quando houver rede (lib/filaOffline).
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, CloudOff, CheckCircle2, AlertTriangle, RefreshCw, Trash2, ExternalLink,
} from 'lucide-react';
import { tviAPI } from '../../../lib/api';
import { useOfflineStorage } from '../../../hooks/useOfflineStorage';
import MobileVistoriaForm from '../../mobile/MobileVistoriaForm';
import OfflineBadge from '../../mobile/OfflineBadge';
import { useToast } from '../../../hooks/use-toast';

const STATUS = {
  pendente: { rotulo: 'Aguardando envio', cor: 'bg-amber-100 text-amber-800', Icone: CloudOff },
  enviado: { rotulo: 'Enviada', cor: 'bg-emerald-100 text-emerald-800', Icone: CheckCircle2 },
  falhou: { rotulo: 'Não enviada', cor: 'bg-red-100 text-red-700', Icone: AlertTriangle },
};

function ItemFila({ item, onTentar, onDescartar, onAbrir }) {
  const st = STATUS[item.status] || STATUS.pendente;
  const { Icone } = st;
  const fotosTotal = item.status === 'enviado'
    ? item.progresso?.fotosEnviadas?.length || 0
    : (item.fotos || []).length;
  return (
    <li className="rounded-xl border border-gray-200 bg-white p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-medium text-gray-900 break-words">
            {item.dados?.titulo || item.dados?.imovel_endereco || 'Vistoria de campo'}
          </div>
          <div className="text-xs text-gray-500">
            {new Date(item.criadoEm).toLocaleString('pt-BR')}
            {' · '}{fotosTotal} foto(s)
            {item.progresso?.numeroTvi ? ` · ${item.progresso.numeroTvi}` : ''}
          </div>
        </div>
        <span className={`shrink-0 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${st.cor}`}>
          <Icone className="w-3 h-3" /> {st.rotulo}
        </span>
      </div>
      {item.ultimoErro && item.status !== 'enviado' && (
        <p className="mt-2 text-xs text-red-700 break-words">Motivo: {item.ultimoErro}</p>
      )}
      <div className="mt-2 flex flex-wrap gap-2">
        {item.status === 'enviado' && item.progresso?.vistoriaId && (
          <button type="button" onClick={() => onAbrir(item.progresso.vistoriaId)}
            className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-3 py-1.5 text-xs text-emerald-800 hover:bg-emerald-50 min-h-[36px]">
            <ExternalLink className="w-3.5 h-3.5" /> Abrir vistoria
          </button>
        )}
        {item.status !== 'enviado' && (
          <button type="button" onClick={() => onTentar(item.localId)}
            className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 min-h-[36px]">
            <RefreshCw className="w-3.5 h-3.5" /> Tentar enviar
          </button>
        )}
        <button type="button" onClick={() => onDescartar(item)}
          className="inline-flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50 min-h-[36px]">
          <Trash2 className="w-3.5 h-3.5" /> {item.status === 'enviado' ? 'Tirar da lista' : 'Descartar'}
        </button>
      </div>
    </li>
  );
}

export default function VistoriaCampo() {
  const nav = useNavigate();
  const { toast } = useToast();
  const { itens, tentarDeNovo, descartar } = useOfflineStorage();
  const [modelos, setModelos] = useState([]);
  const [modelId, setModelId] = useState(() => {
    try { return localStorage.getItem('avalieimob_tvi_campo_modelo') || ''; } catch { return ''; }
  });
  const [chaveForm, setChaveForm] = useState(0);

  useEffect(() => {
    tviAPI.listModels()
      .then((r) => {
        const lista = Object.values(r?.categorias || {}).flat();
        setModelos(lista);
        try { localStorage.setItem('avalieimob_tvi_campo_modelos', JSON.stringify(lista)); } catch { /* */ }
      })
      .catch(() => {
        // sem internet: usa a lista guardada da última vez
        try { setModelos(JSON.parse(localStorage.getItem('avalieimob_tvi_campo_modelos') || '[]')); } catch { /* */ }
      });
  }, []);

  const escolherModelo = (id) => {
    setModelId(id);
    try { localStorage.setItem('avalieimob_tvi_campo_modelo', id); } catch { /* */ }
  };

  const aoConcluir = (resultado) => {
    if (resultado?.status === 'enviado') toast({ title: 'Vistoria enviada', description: resultado.progresso?.numeroTvi || '' });
    else if (resultado?.status === 'falhou') toast({ title: 'Vistoria não enviada', description: resultado.ultimoErro, variant: 'destructive' });
    else toast({ title: 'Vistoria salva no aparelho', description: 'Será enviada quando houver internet.' });
    setChaveForm((k) => k + 1);
  };

  const confirmarDescarte = (item) => {
    if (item.status !== 'enviado'
      && !window.confirm('Descartar esta vistoria? Ela ainda não foi enviada e será apagada do aparelho.')) return;
    descartar(item.localId);
  };

  return (
    <div className="max-w-xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <button type="button" onClick={() => nav('/dashboard/tvi')}
          className="inline-flex items-center gap-1 text-sm text-emerald-800 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Kit TVI
        </button>
        <OfflineBadge />
      </div>
      <div>
        <h1 className="font-display text-2xl font-bold text-[#0C3320] dark:text-[#C9A84C]">Vistoria de campo</h1>
        <p className="text-sm text-gray-500 mt-1">
          Funciona sem internet: a vistoria fica guardada no aparelho e é enviada quando a rede voltar.
        </p>
      </div>

      <label className="block">
        <span className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wide">Modelo de vistoria</span>
        <select value={modelId} onChange={(e) => escolherModelo(e.target.value)}
          className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm min-h-[48px]">
          <option value="">Selecione</option>
          {modelos.map((m) => <option key={m.id} value={m.id}>{m.nome || m.id}</option>)}
        </select>
      </label>

      {modelId ? (
        <div className="rounded-2xl border border-gray-200 bg-white">
          <MobileVistoriaForm key={chaveForm} modelId={modelId} onSuccess={aoConcluir} />
        </div>
      ) : (
        <p className="text-sm text-gray-500">Escolha um modelo para começar.</p>
      )}

      {itens.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-[#F2EFE6]">Neste aparelho</h2>
          <ul className="space-y-2">
            {itens.map((i) => (
              <ItemFila key={i.localId} item={i} onTentar={tentarDeNovo}
                onDescartar={confirmarDescarte} onAbrir={(vid) => nav(`/dashboard/tvi/${vid}`)} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
