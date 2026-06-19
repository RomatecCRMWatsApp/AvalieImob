// Página pública "Quanto vale meu imóvel?" — calculadora de estimativa de mercado
// + captura de lead (Z-API). Rota: /quanto-vale-meu-imovel (fora do guard).
// Topo de funil: estimativa preliminar (NÃO é PTAM/Laudo) → faixa → contato.
import React, { useState } from 'react';
import { avaliacaoPublicaAPI } from '../lib/api';

const VERDE = '#0C3320';
const VERDE_CLARO = '#0B6E4F';
const DOURADO = '#C9A84C';

const UFS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
  'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'];

const brl = (n) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(n || 0);

const maskFone = (v) => {
  const d = v.replace(/\D/g, '').slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
};

const serif = { fontFamily: "'Playfair Display', serif" };

export default function AvaliacaoPublica() {
  const [step, setStep] = useState('form'); // form | result | done
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [estimativa, setEstimativa] = useState(null);

  const [imovel, setImovel] = useState({
    uf: 'MA', cidade: '', tipo: 'apartamento', area: '',
    quartos: '', vagas: '', padrao: 'medio', conservacao: 'bom',
  });
  const [contato, setContato] = useState({ nome: '', whatsapp: '', email: '' });

  const set = (campo, valor) => setImovel((p) => ({ ...p, [campo]: valor }));

  const payloadImovel = () => ({
    uf: imovel.uf,
    cidade: imovel.cidade.trim(),
    tipo: imovel.tipo,
    area: Number(imovel.area),
    quartos: Number(imovel.quartos || 0),
    vagas: Number(imovel.vagas || 0),
    padrao: imovel.padrao,
    conservacao: imovel.conservacao,
  });

  async function calcular(e) {
    e.preventDefault();
    setErro('');
    if (!imovel.cidade.trim()) return setErro('Informe a cidade.');
    if (!imovel.area || Number(imovel.area) <= 0) return setErro('Informe a área em m².');
    setLoading(true);
    try {
      const data = await avaliacaoPublicaAPI.estimar(payloadImovel());
      setEstimativa(data);
      setStep('result');
    } catch (err) {
      setErro(err?.response?.data?.detail || 'Não foi possível calcular agora.');
    } finally {
      setLoading(false);
    }
  }

  async function enviarLead(e) {
    e.preventDefault();
    setErro('');
    if (contato.nome.trim().length < 2) return setErro('Informe seu nome.');
    if (contato.whatsapp.replace(/\D/g, '').length < 10) return setErro('Informe um WhatsApp válido.');
    setLoading(true);
    try {
      await avaliacaoPublicaAPI.lead({
        nome: contato.nome.trim(),
        whatsapp: contato.whatsapp,
        email: contato.email || null,
        imovel: payloadImovel(),
      });
      setStep('done');
    } catch (err) {
      setErro(err?.response?.data?.detail || 'Não foi possível enviar. Tente novamente.');
    } finally {
      setLoading(false);
    }
  }

  const inputCls =
    'w-full rounded-lg border border-gray-300 px-3 py-2.5 text-gray-800 ' +
    'focus:outline-none focus:ring-2 focus:ring-[#C9A84C] focus:border-transparent';
  const labelCls = 'block text-sm font-medium text-gray-700 mb-1';

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-7 text-center"
          style={{ background: `linear-gradient(135deg, ${VERDE}, ${VERDE_CLARO})` }}>
          <h1 className="text-2xl font-bold text-white" style={serif}>Quanto vale o seu imóvel?</h1>
          <p className="mt-1 text-sm" style={{ color: DOURADO }}>Estimativa de mercado em menos de 1 minuto</p>
        </div>

        <div className="p-6">
          {erro && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{erro}</div>
          )}

          {step === 'form' && (
            <form onSubmit={calcular} className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-1">
                  <label className={labelCls}>UF</label>
                  <select className={inputCls} value={imovel.uf} onChange={(e) => set('uf', e.target.value)}>
                    {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
                <div className="col-span-2">
                  <label className={labelCls}>Cidade</label>
                  <input className={inputCls} value={imovel.cidade}
                    onChange={(e) => set('cidade', e.target.value)} placeholder="Ex.: Açailândia" />
                </div>
              </div>

              <div>
                <label className={labelCls}>Tipo de imóvel</label>
                <select className={inputCls} value={imovel.tipo} onChange={(e) => set('tipo', e.target.value)}>
                  <option value="apartamento">Apartamento</option>
                  <option value="casa">Casa</option>
                  <option value="comercial">Comercial</option>
                  <option value="terreno">Terreno</option>
                  <option value="rural">Rural</option>
                </select>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelCls}>Área (m²)</label>
                  <input className={inputCls} type="number" min="1" value={imovel.area}
                    onChange={(e) => set('area', e.target.value)} placeholder="120" />
                </div>
                <div>
                  <label className={labelCls}>Quartos</label>
                  <input className={inputCls} type="number" min="0" value={imovel.quartos}
                    onChange={(e) => set('quartos', e.target.value)} placeholder="3" />
                </div>
                <div>
                  <label className={labelCls}>Vagas</label>
                  <input className={inputCls} type="number" min="0" value={imovel.vagas}
                    onChange={(e) => set('vagas', e.target.value)} placeholder="2" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Padrão</label>
                  <select className={inputCls} value={imovel.padrao} onChange={(e) => set('padrao', e.target.value)}>
                    <option value="popular">Popular</option>
                    <option value="medio">Médio</option>
                    <option value="alto">Alto</option>
                    <option value="luxo">Luxo</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Conservação</label>
                  <select className={inputCls} value={imovel.conservacao} onChange={(e) => set('conservacao', e.target.value)}>
                    <option value="novo">Novo</option>
                    <option value="bom">Bom</option>
                    <option value="regular">Regular</option>
                    <option value="reformar">A reformar</option>
                  </select>
                </div>
              </div>

              <button type="submit" disabled={loading}
                className="w-full rounded-lg py-3 font-semibold text-white transition disabled:opacity-60"
                style={{ backgroundColor: VERDE }}>
                {loading ? 'Calculando...' : 'Calcular estimativa'}
              </button>
            </form>
          )}

          {step === 'result' && estimativa && (
            <div className="space-y-5">
              <div className="text-center rounded-xl p-5 border-2" style={{ borderColor: DOURADO, backgroundColor: '#FBF8F0' }}>
                <p className="text-sm text-gray-600">Faixa estimada de mercado</p>
                <p className="mt-1 text-3xl font-bold" style={{ ...serif, color: VERDE }}>{brl(estimativa.valor_min)}</p>
                <p className="text-gray-500 text-sm">até</p>
                <p className="text-3xl font-bold" style={{ ...serif, color: VERDE }}>{brl(estimativa.valor_max)}</p>
                <p className="mt-2 text-xs text-gray-500">≈ {brl(estimativa.valor_m2)}/m²</p>
              </div>

              <p className="text-[11px] leading-snug text-gray-500 text-justify">{estimativa.aviso}</p>

              <div className="rounded-xl p-4" style={{ backgroundColor: '#F3F6F4' }}>
                <p className="font-semibold text-gray-800" style={serif}>Quer um valor oficial com validade técnica?</p>
                <p className="text-sm text-gray-600 mb-3">Receba um PTAM / Laudo conforme NBR 14.653 com um avaliador credenciado.</p>
                <form onSubmit={enviarLead} className="space-y-3">
                  <input className={inputCls} placeholder="Seu nome" value={contato.nome}
                    onChange={(e) => setContato((p) => ({ ...p, nome: e.target.value }))} />
                  <input className={inputCls} placeholder="WhatsApp" value={contato.whatsapp}
                    onChange={(e) => setContato((p) => ({ ...p, whatsapp: maskFone(e.target.value) }))} />
                  <input className={inputCls} type="email" placeholder="E-mail (opcional)" value={contato.email}
                    onChange={(e) => setContato((p) => ({ ...p, email: e.target.value }))} />
                  <button type="submit" disabled={loading}
                    className="w-full rounded-lg py-3 font-semibold transition disabled:opacity-60"
                    style={{ backgroundColor: DOURADO, color: VERDE }}>
                    {loading ? 'Enviando...' : 'Falar com um avaliador'}
                  </button>
                </form>
              </div>

              <button onClick={() => { setStep('form'); setEstimativa(null); }}
                className="w-full text-sm text-gray-500 underline">← Refazer simulação</button>
            </div>
          )}

          {step === 'done' && (
            <div className="text-center py-8">
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full" style={{ backgroundColor: VERDE }}>
                <span className="text-2xl text-white">✓</span>
              </div>
              <h2 className="text-xl font-bold" style={{ ...serif, color: VERDE }}>Recebido!</h2>
              <p className="mt-2 text-gray-600">Em breve um avaliador da Romatec entra em contato pelo seu WhatsApp.</p>
            </div>
          )}
        </div>

        <div className="px-6 py-3 text-center text-[11px] text-gray-400 border-t">
          AvalieImob • Romatec Consultoria Total • NBR 14.653 / COFECI 1.066/2007
        </div>
      </div>
    </div>
  );
}
