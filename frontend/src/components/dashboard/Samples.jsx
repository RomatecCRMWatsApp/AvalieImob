// @module dashboard/Samples — Amostras de Mercado v2 (Banco Global de Paradigmas).
// Tabs Urbano/Rural, estatísticas (R$/m² ↔ R$/ha), filtros e tabela com origem PTAM.
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { TrendingUp, Loader2, Trash2, Home, Wheat, Link2, FileText } from 'lucide-react';
import { Button } from '../ui/button';
import { useToast } from '../../hooks/use-toast';
import { amostrasAPI } from '../../lib/api';
import ModalNovaAmostraUrbana from './amostras/ModalNovaAmostraUrbana';
import ModalNovaAmostraRural from './amostras/ModalNovaAmostraRural';
import { fmtBRL, fmtNum, m2ToHa } from './amostras/amostraOptions';

const inputCls = 'px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600';

const Samples = () => {
  const { toast } = useToast();
  const [categoria, setCategoria] = useState('urbano');
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ media: 0, minimo: 0, maximo: 0, total: 0, unidade: 'R$/m²' });
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({ bairro: '', tipo_amostra: '', data_de: '', data_ate: '' });
  const [modalUrbano, setModalUrbano] = useState(false);
  const [modalRural, setModalRural] = useState(false);
  const [refSugerida, setRefSugerida] = useState('');

  const isRural = categoria === 'rural';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { categoria, limit: 200 };
      if (filtros.bairro) params.bairro = filtros.bairro;
      if (filtros.tipo_amostra) params.tipo_amostra = filtros.tipo_amostra;
      if (filtros.data_de) params.data_de = filtros.data_de;
      if (filtros.data_ate) params.data_ate = filtros.data_ate;
      const [list, est] = await Promise.all([
        amostrasAPI.list(params),
        amostrasAPI.estatisticas({ categoria }),
      ]);
      setItems(Array.isArray(list?.amostras) ? list.amostras : []);
      setStats(est || { media: 0, minimo: 0, maximo: 0, total: 0, unidade: isRural ? 'R$/ha' : 'R$/m²' });
    } catch (err) {
      console.warn('Falha ao carregar amostras', err);
      toast({ title: 'Erro ao carregar', variant: 'destructive' });
    } finally { setLoading(false); }
  }, [categoria, filtros, isRural, toast]);

  useEffect(() => { load(); }, [load]);

  const abrirModal = async (cat) => {
    try {
      const { referencia } = await amostrasAPI.proximaReferencia(cat);
      setRefSugerida(referencia || '');
    } catch { setRefSugerida(''); }
    if (cat === 'rural') setModalRural(true); else setModalUrbano(true);
  };

  const onSalvar = () => { load(); };

  const remove = async (id) => {
    try {
      await amostrasAPI.remove(id);
      setItems((arr) => arr.filter((s) => s.id !== id));
      toast({ title: 'Amostra removida' });
      load();
    } catch { toast({ title: 'Erro ao remover', variant: 'destructive' }); }
  };

  const unidade = stats.unidade || (isRural ? 'R$/ha' : 'R$/m²');
  const areaDe = (s) => (isRural ? `${fmtNum(m2ToHa(s.area_m2), 2)} ha` : `${fmtNum(s.area_total_m2, 0)} m²`);
  const precoUnit = (s) => (isRural ? s.rs_ha_calculado : s.rs_m2_calculado);
  const bairroDe = (s) => (isRural ? (s.bairro_localidade || s.denominacao) : s.bairro);

  const TipoAmostraOptions = useMemo(
    () => (isRural ? ['Oferta de Mercado', 'Consolidada / Comercializada']
                   : ['Oferta de Mercado', 'Consolidada / Comercializada', 'Aluguel']),
    [isRural],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-[#B8860B] dark:text-amber-400">Amostras de Mercado</h1>
          <p className="text-gray-600 mt-1">Elementos comparativos — Método Comparativo Direto (NBR 14653).</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => abrirModal('urbano')}
            className="flex items-center gap-2 px-5 py-3 bg-white border-2 border-emerald-800 text-emerald-800 rounded-xl hover:bg-emerald-800 hover:text-white transition-all font-medium">
            <Home className="w-4 h-4" /> Imóvel Urbano
          </button>
          <button onClick={() => abrirModal('rural')}
            className="flex items-center gap-2 px-5 py-3 bg-white border-2 border-amber-600 text-amber-600 rounded-xl hover:bg-amber-600 hover:text-white transition-all font-medium">
            <Wheat className="w-4 h-4" /> Imóvel Rural
          </button>
        </div>
      </div>

      {/* Tabs categoria */}
      <div className="flex gap-2 border-b border-gray-200">
        {[['urbano', 'Urbano', Home], ['rural', 'Rural', Wheat]].map(([key, label, Icon]) => (
          <button key={key} onClick={() => setCategoria(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors ${
              categoria === key ? 'border-emerald-700 text-emerald-800' : 'border-transparent text-gray-400 hover:text-gray-600'
            }`}>
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>

      {/* Estatísticas */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1"><TrendingUp className="w-3.5 h-3.5" />PREÇO MÉDIO</div>
          <div className="font-display text-2xl font-bold text-emerald-800">{fmtBRL(stats.media)}<span className="text-sm font-normal text-gray-400">/{unidade.replace('R$/', '')}</span></div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">MÍNIMO</div>
          <div className="font-display text-2xl font-bold text-gray-900">{fmtBRL(stats.minimo)}<span className="text-sm font-normal text-gray-400">/{unidade.replace('R$/', '')}</span></div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">MÁXIMO</div>
          <div className="font-display text-2xl font-bold text-gray-900">{fmtBRL(stats.maximo)}<span className="text-sm font-normal text-gray-400">/{unidade.replace('R$/', '')}</span></div>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-end gap-3 bg-white p-4 rounded-xl border border-gray-200">
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-gray-500 mb-1">{isRural ? 'Localidade' : 'Bairro'}</label>
          <input className={inputCls} value={filtros.bairro} onChange={(e) => setFiltros((f) => ({ ...f, bairro: e.target.value }))} placeholder="Filtrar..." />
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-gray-500 mb-1">Tipo da Amostra</label>
          <select className={inputCls} value={filtros.tipo_amostra} onChange={(e) => setFiltros((f) => ({ ...f, tipo_amostra: e.target.value }))}>
            <option value="">Todas</option>
            {TipoAmostraOptions.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-gray-500 mb-1">De</label>
          <input type="date" className={inputCls} value={filtros.data_de} onChange={(e) => setFiltros((f) => ({ ...f, data_de: e.target.value }))} />
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-gray-500 mb-1">Até</label>
          <input type="date" className={inputCls} value={filtros.data_ate} onChange={(e) => setFiltros((f) => ({ ...f, data_ate: e.target.value }))} />
        </div>
        {(filtros.bairro || filtros.tipo_amostra || filtros.data_de || filtros.data_ate) && (
          <Button variant="outline" onClick={() => setFiltros({ bairro: '', tipo_amostra: '', data_de: '', data_ate: '' })}>Limpar</Button>
        )}
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {loading ? (
          <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
        ) : (
          <table className="w-full text-sm min-w-[860px]">
            <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="text-left py-3 px-4">Ref</th>
                <th className="text-left py-3 px-4">Tipo</th>
                <th className="text-left py-3 px-4">{isRural ? 'Localidade' : 'Bairro'}</th>
                <th className="text-right py-3 px-4">Área</th>
                <th className="text-right py-3 px-4">Valor</th>
                <th className="text-right py-3 px-4">{unidade}</th>
                <th className="text-left py-3 px-4">Fonte</th>
                <th className="text-left py-3 px-4">Data</th>
                <th className="text-left py-3 px-4">Origem</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id} className="border-t border-gray-100 hover:bg-emerald-50/30">
                  <td className="py-3 px-4 font-semibold text-emerald-800">{s.referencia}</td>
                  <td className="py-3 px-4">{s.tipo_imovel}</td>
                  <td className="py-3 px-4">{bairroDe(s) || '—'}</td>
                  <td className="py-3 px-4 text-right">{areaDe(s)}</td>
                  <td className="py-3 px-4 text-right">{fmtBRL(s.valor_rs)}</td>
                  <td className="py-3 px-4 text-right font-semibold">{fmtBRL(precoUnit(s))}</td>
                  <td className="py-3 px-4 text-xs text-gray-500">{s.fonte || '—'}</td>
                  <td className="py-3 px-4 text-xs text-gray-500">{s.data_coleta ? String(s.data_coleta).slice(0, 10).split('-').reverse().join('/') : '—'}</td>
                  <td className="py-3 px-4">
                    {s.origem === 'ptam' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                        <Link2 className="w-3 h-3" />{s.ptam_origem_numero || 'PTAM'}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <FileText className="w-3 h-3" />Direto
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-2">
                    <button onClick={() => remove(s.id)} className="p-1.5 hover:bg-red-50 rounded text-red-600" title="Excluir">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td colSpan={10} className="text-center py-10 text-gray-400">Nenhuma amostra {isRural ? 'rural' : 'urbana'} cadastrada</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <ModalNovaAmostraUrbana open={modalUrbano} onClose={() => setModalUrbano(false)} onSalvar={onSalvar} referenciaSugerida={refSugerida} />
      <ModalNovaAmostraRural open={modalRural} onClose={() => setModalRural(false)} onSalvar={onSalvar} referenciaSugerida={refSugerida} />
    </div>
  );
};

export default Samples;
