// @module components/dashboard/inferencia/InferenciaList — modelos de tratamento científico.
//
// Lista os modelos de regressão (MCDDM) do avaliador. O modelo é iterado dezenas
// de vezes antes do fechamento, por isso vive fora da avaliação.
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sigma, Plus, Trash2, Lock, FileText, Loader2, CheckCircle2 } from 'lucide-react';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { useToast } from '../../../hooks/use-toast';
import { inferenciaAPI } from '../../../lib/api';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const STATUS = {
  rascunho: { label: 'Rascunho', cls: 'bg-gray-100 text-gray-600 border-gray-200' },
  estimado: { label: 'Estimado', cls: 'bg-sky-50 text-sky-700 border-sky-200' },
  homologado: { label: 'Homologado', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
};

const GRAU = {
  III: 'bg-emerald-600', II: 'bg-amber-500', I: 'bg-orange-500', fora: 'bg-red-600',
};

const fmtData = (v) => {
  if (!v) return '—';
  const d = new Date(String(v).endsWith('Z') ? v : `${v}Z`);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('pt-BR');
};

const InferenciaList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [modelos, setModelos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [criando, setCriando] = useState(false);
  const [nome, setNome] = useState('');
  const [tipo, setTipo] = useState('urbano');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setModelos(await inferenciaAPI.listar());
    } catch (e) {
      toast({ title: 'Erro ao carregar modelos', description: e.response?.data?.detail,
              variant: 'destructive' });
    } finally { setLoading(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const criar = async () => {
    setCriando(true);
    try {
      const m = await inferenciaAPI.criar({ nome: nome || undefined, tipo_imovel: tipo });
      toast({ title: 'Modelo criado' });
      nav(`/dashboard/inferencia/${m.id}`);
    } catch (e) {
      toast({ title: 'Erro ao criar', description: e.response?.data?.detail,
              variant: 'destructive' });
    } finally { setCriando(false); }
  };

  const excluir = async (m) => {
    if (!window.confirm(`Excluir o modelo "${m.nome}"?`)) return;
    try {
      await inferenciaAPI.excluir(m.id);
      toast({ title: 'Modelo excluído' });
      load();
    } catch (e) {
      toast({ title: 'Não foi possível excluir', description: e.response?.data?.detail,
              variant: 'destructive' });
    }
  };

  if (loading) return <BrandSpinner label="Carregando modelos..." />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold flex items-center gap-2" style={{ color: VERDE }}>
          <Sigma className="w-6 h-6" style={{ color: DOURADO }} /> Tratamento Científico
        </h1>
        <p className="text-sm text-gray-500">
          Inferência estatística (MCDDM) — regressão sobre a amostra de mercado, com
          diagnóstico dos pressupostos e enquadramento na ABNT NBR 14.653. É o caminho
          que habilita <strong>Grau III</strong> de fundamentação.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-3">Novo modelo</p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[220px]">
            <label className="block text-xs text-gray-600 mb-1">Nome</label>
            <Input value={nome} onChange={(e) => setNome(e.target.value)}
                   placeholder="Modelo 01 — ln(VU)" />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Imóvel</label>
            <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg h-10"
                    value={tipo} onChange={(e) => setTipo(e.target.value)}>
              <option value="urbano">Urbano — NBR 14653-2</option>
              <option value="rural">Rural — NBR 14653-3</option>
            </select>
          </div>
          <Button onClick={criar} disabled={criando} style={{ background: VERDE }}
                  className="text-white">
            {criando ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                     : <Plus className="w-4 h-4 mr-2" />}
            Criar modelo
          </Button>
        </div>
      </div>

      {modelos.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
          Nenhum modelo ainda. Crie o primeiro e importe a amostra de mercado.
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {modelos.map((m) => {
            const s = STATUS[m.status] || STATUS.rascunho;
            const enq = m.enquadramento || {};
            return (
              <div key={m.id}
                   className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 transition">
                <div className="flex items-start justify-between gap-2">
                  <button className="text-left" onClick={() => nav(`/dashboard/inferencia/${m.id}`)}>
                    <div className="font-semibold text-gray-900 flex items-center gap-2">
                      {m.nome}
                      {m.status === 'homologado' && <Lock className="w-3.5 h-3.5 text-emerald-600" />}
                    </div>
                    <div className="text-xs text-gray-500">
                      {m.tipo_imovel === 'rural' ? 'Rural · NBR 14653-3' : 'Urbano · NBR 14653-2'}
                      {' · '}v{m.versao || 1} · criado em {fmtData(m.criado_em)}
                    </div>
                  </button>
                  <span className={`text-xs px-2 py-1 rounded-full border shrink-0 ${s.cls}`}>
                    {s.label}
                  </span>
                </div>

                {enq.grau_fundamentacao && (
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    <span className={`text-[11px] font-bold text-white px-2 py-0.5 rounded ${GRAU[enq.grau_fundamentacao] || 'bg-gray-400'}`}>
                      Fundamentação {enq.grau_fundamentacao}
                    </span>
                    <span className={`text-[11px] font-bold text-white px-2 py-0.5 rounded ${GRAU[enq.grau_precisao] || 'bg-gray-400'}`}>
                      Precisão {enq.grau_precisao}
                    </span>
                    {enq.amplitude_ip80 != null && (
                      <span className="text-[11px] text-gray-500">
                        IP 80% = {(enq.amplitude_ip80 * 100).toFixed(2).replace('.', ',')}%
                      </span>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 mt-4">
                  <Button size="sm" variant="outline"
                          onClick={() => nav(`/dashboard/inferencia/${m.id}`)}>
                    Abrir
                  </Button>
                  {m.status !== 'rascunho' && (
                    <Button size="sm" variant="outline"
                            onClick={() => window.open(`/api/inferencia/modelos/${m.id}/pdf`, '_blank')}>
                      <FileText className="w-4 h-4 mr-1.5" /> Laudo
                    </Button>
                  )}
                  {m.status === 'homologado' ? (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-700 px-2">
                      <CheckCircle2 className="w-3.5 h-3.5" /> congelado
                    </span>
                  ) : (
                    <Button size="sm" variant="outline" className="text-red-600"
                            onClick={() => excluir(m)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default InferenciaList;
