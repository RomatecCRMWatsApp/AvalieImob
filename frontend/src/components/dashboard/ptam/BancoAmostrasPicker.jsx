// @module ptam/BancoAmostrasPicker — Seletor de amostras já cadastradas no Banco Global
// (repositório de paradigmas). Permite escolher uma ou várias e inseri-las no PTAM já
// mapeadas para o formato de market_sample, trazendo foto e planta baixa quando houver.
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Loader2, Search, ImageIcon, FileText, Check } from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { useToast } from '../../../hooks/use-toast';
import { amostrasAPI } from '../../../lib/api';

const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };
const fmtBRL = (v) => num(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// Extrai o ID da imagem de uma foto_url (que pode ser URL completa ou já o próprio ID).
const extractImageId = (v) => {
  if (!v) return null;
  const s = String(v);
  const m = s.match(/\/upload\/image\/([^/?#]+)/);
  return m ? m[1] : s;
};

const mapTipoAmostra = (t) => (String(t || '').toLowerCase().includes('consolidada') ? 'consolidada' : 'oferta');

// Converte uma amostra do banco global -> objeto market_sample do PTAM.
const amostraParaMarketSample = (a, rural) => {
  const area = rural ? num(a.area_m2) : num(a.area_total_m2);
  const value = num(a.valor_rs);
  return {
    _key: `ms_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    address: (rural ? a.endereco_logradouro : a.endereco) || '',
    neighborhood: (rural ? a.bairro_localidade : a.bairro) || a.denominacao || '',
    municipio: a.municipio || '',
    uf: a.uf || '',
    area,
    value,
    value_per_sqm: area > 0 ? Math.round((value / area) * 100) / 100 : 0,
    source: a.fonte || '',
    collection_date: a.data_coleta || '',
    contact_phone: a.telefone_fonte || '',
    notes: '',
    tipo_amostra: mapTipoAmostra(a.tipo_amostra),
    foto: extractImageId(a.foto_url),
    planta_baixa: extractImageId(a.planta_baixa_url),
    // Características rurais
    topografia: a.topografia || '',
    solo: a.solo || '',
    recursos_hidricos: a.recursos_hidricos || '',
    vegetacao: a.vegetacao || '',
    atividade: a.atividade_principal || '',
    lotacao_ua_ha: num(a.lotacao_ua_ha),
    benfeitorias: a.benfeitorias || '',
    sede: a.sede_casa || '',
    // Características urbanas
    area_construida_m2: num(a.area_construida_m2),
    area_terreno_m2: num(a.area_terreno_m2),
    idade_anos: num(a.idade_anos),
    _amostra_origem_id: a.id,
  };
};

const BancoAmostrasPicker = ({ open, onClose, onImport, categoria = 'urbano', municipioDefault = '' }) => {
  const { toast } = useToast();
  const rural = categoria === 'rural';
  const [loading, setLoading] = useState(false);
  const [itens, setItens] = useState([]);
  const [busca, setBusca] = useState('');
  const [sel, setSel] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await amostrasAPI.list({ categoria, limit: 200 });
      setItens(Array.isArray(res?.amostras) ? res.amostras : []);
    } catch (e) {
      toast({ title: 'Erro ao carregar o banco de amostras', variant: 'destructive' });
    } finally { setLoading(false); }
  }, [categoria, toast]);

  useEffect(() => { if (open) { setSel({}); setBusca(''); load(); } }, [open, load]);

  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return itens;
    return itens.filter((a) =>
      [a.referencia, a.tipo_imovel, a.bairro, a.bairro_localidade, a.denominacao, a.municipio, a.fonte]
        .filter(Boolean).some((v) => String(v).toLowerCase().includes(q)));
  }, [itens, busca]);

  const toggle = (id) => setSel((s) => ({ ...s, [id]: !s[id] }));
  const totalSel = Object.values(sel).filter(Boolean).length;

  const confirmar = () => {
    const escolhidas = itens.filter((a) => sel[a.id]);
    if (escolhidas.length === 0) { toast({ title: 'Selecione ao menos uma amostra', variant: 'destructive' }); return; }
    onImport(escolhidas.map((a) => amostraParaMarketSample(a, rural)));
    onClose?.();
  };

  const areaTxt = (a) => (rural ? `${num(a.area_m2 / 10000).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ha` : `${num(a.area_total_m2).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} m²`);
  const unitTxt = (a) => fmtBRL(rural ? a.rs_ha_calculado : a.rs_m2_calculado) + (rural ? '/ha' : '/m²');

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose?.()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-emerald-900">
            Banco de Amostras — {rural ? 'Rural' : 'Urbano'}
          </DialogTitle>
        </DialogHeader>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input value={busca} onChange={(e) => setBusca(e.target.value)} className="pl-10" placeholder="Buscar por referência, tipo, bairro, fonte..." />
        </div>

        {loading ? (
          <div className="py-16 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-emerald-800" /></div>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden max-h-[55vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-[11px] uppercase tracking-wider text-gray-500 sticky top-0">
                <tr>
                  <th className="w-8 py-2 px-2"></th>
                  <th className="text-left py-2 px-2">Ref</th>
                  <th className="text-left py-2 px-2">Tipo</th>
                  <th className="text-left py-2 px-2">{rural ? 'Localidade' : 'Bairro'}</th>
                  <th className="text-right py-2 px-2">Área</th>
                  <th className="text-right py-2 px-2">Valor</th>
                  <th className="text-right py-2 px-2">{rural ? 'R$/ha' : 'R$/m²'}</th>
                  <th className="text-center py-2 px-2">Mídia</th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((a) => (
                  <tr key={a.id} onClick={() => toggle(a.id)}
                    className={`border-t border-gray-100 cursor-pointer ${sel[a.id] ? 'bg-emerald-50' : 'hover:bg-gray-50'}`}>
                    <td className="py-2 px-2 text-center">
                      <span className={`inline-flex items-center justify-center w-5 h-5 rounded border ${sel[a.id] ? 'bg-emerald-700 border-emerald-700 text-white' : 'border-gray-300'}`}>
                        {sel[a.id] && <Check className="w-3.5 h-3.5" />}
                      </span>
                    </td>
                    <td className="py-2 px-2 font-semibold text-emerald-800">{a.referencia}</td>
                    <td className="py-2 px-2">{a.tipo_imovel}</td>
                    <td className="py-2 px-2">{(rural ? (a.bairro_localidade || a.denominacao) : a.bairro) || '—'}</td>
                    <td className="py-2 px-2 text-right">{areaTxt(a)}</td>
                    <td className="py-2 px-2 text-right">{fmtBRL(a.valor_rs)}</td>
                    <td className="py-2 px-2 text-right font-semibold">{unitTxt(a)}</td>
                    <td className="py-2 px-2">
                      <div className="flex items-center justify-center gap-1.5 text-gray-400">
                        {a.foto_url && <ImageIcon className="w-3.5 h-3.5 text-emerald-600" title="Tem foto" />}
                        {a.planta_baixa_url && <FileText className="w-3.5 h-3.5 text-blue-600" title="Tem planta" />}
                        {!a.foto_url && !a.planta_baixa_url && <span className="text-xs">—</span>}
                      </div>
                    </td>
                  </tr>
                ))}
                {filtrados.length === 0 && (
                  <tr><td colSpan={8} className="text-center py-10 text-gray-400">Nenhuma amostra {rural ? 'rural' : 'urbana'} no banco</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={() => onClose?.()}>Cancelar</Button>
          <Button onClick={confirmar} className="bg-emerald-900 hover:bg-emerald-800 text-white">
            Inserir {totalSel > 0 ? `(${totalSel})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default BancoAmostrasPicker;
