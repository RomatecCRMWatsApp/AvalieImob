// Modelo 1 — Cartório Técnico. Rota: /avaliacao/classica
import { useAvaliacao } from '../../hooks/useAvaliacao';
import AvalieIcon from '../../components/AvalieIcon';
import { brl } from '../../lib/format';

const serif = { fontFamily: "'Playfair Display', serif" };
const inp =
  'w-full rounded-lg border border-[#d4dad4] bg-[#fcfdfc] px-3 py-2.5 text-sm ' +
  'text-gray-800 outline-none focus:border-[#C9A84C] focus:ring-2 focus:ring-[#C9A84C]/20';
const lab = 'block text-xs font-semibold text-[#41504a] mb-1.5';

export default function CalculadoraClassica() {
  const v = useAvaliacao('calc_classica');
  return (
    <div className="min-h-screen bg-[#EEF1ED] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white border border-[#dfe4df] border-t-4 border-t-[#C9A84C] rounded-md shadow-[0_14px_40px_-28px_rgba(12,51,32,0.5)]">
        <div className="flex items-center gap-3 px-6 py-5 border-b border-[#eceee9]">
          <AvalieIcon size={44} />
          <div className="leading-none">
            <div className="text-xl font-bold text-[#0C3320]" style={serif}>AvalieImob</div>
            <div className="mt-1.5 text-[10.5px] font-medium tracking-[0.14em] uppercase text-[#B8860B]">
              Romatec · NBR 14.653
            </div>
          </div>
        </div>

        <div className="px-6 py-6">
          {v.erro && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{v.erro}</div>
          )}

          {v.step === 'form' && (
            <form onSubmit={v.calcular} className="space-y-3.5">
              <div className="text-xl font-bold text-gray-800" style={serif}>Quanto vale o seu imóvel?</div>
              <p className="text-[13px] text-[#6b7770] -mt-2">Estimativa preliminar por análise comparativa.</p>

              <div className="grid grid-cols-3 gap-3">
                <div><label className={lab}>UF</label>
                  <select className={inp} value={v.imovel.uf} onChange={(e) => v.setCampo('uf', e.target.value)}>
                    {['MA', 'PA', 'TO', 'SP'].map((u) => <option key={u}>{u}</option>)}
                  </select></div>
                <div className="col-span-2"><label className={lab}>Cidade</label>
                  <input className={inp} value={v.imovel.cidade} onChange={(e) => v.setCampo('cidade', e.target.value)} placeholder="Açailândia" /></div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2"><label className={lab}>Tipo</label>
                  <select className={inp} value={v.imovel.tipo} onChange={(e) => v.setCampo('tipo', e.target.value)}>
                    <option value="casa">Casa</option><option value="apartamento">Apartamento</option>
                    <option value="comercial">Comercial</option><option value="terreno">Terreno</option><option value="rural">Rural</option>
                  </select></div>
                <div><label className={lab}>Área m²</label>
                  <input className={inp} type="number" min="1" value={v.imovel.area} onChange={(e) => v.setCampo('area', e.target.value)} placeholder="180" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className={lab}>Padrão</label>
                  <select className={inp} value={v.imovel.padrao} onChange={(e) => v.setCampo('padrao', e.target.value)}>
                    <option value="popular">Popular</option><option value="medio">Médio</option><option value="alto">Alto</option><option value="luxo">Luxo</option>
                  </select></div>
                <div><label className={lab}>Conservação</label>
                  <select className={inp} value={v.imovel.conservacao} onChange={(e) => v.setCampo('conservacao', e.target.value)}>
                    <option value="novo">Novo</option><option value="bom">Bom</option><option value="regular">Regular</option><option value="reformar">A reformar</option>
                  </select></div>
              </div>
              <button disabled={v.loading} className="w-full rounded-lg bg-[#0C3320] py-3 font-semibold text-white transition hover:brightness-110 disabled:opacity-60">
                {v.loading ? 'Calculando...' : 'Calcular estimativa'}
              </button>
            </form>
          )}

          {v.step === 'result' && v.estimativa && (
            <div className="space-y-4">
              <div className="relative rounded border-[1.5px] border-[#C9A84C] p-5 text-center"
                style={{ background: 'repeating-linear-gradient(45deg,#fcfaf3,#fcfaf3 10px,#faf6ea 10px,#faf6ea 20px)' }}>
                <div className="text-[10.5px] font-semibold uppercase tracking-[0.18em] text-[#B8860B]">Valor de referência</div>
                <div className="mt-2 text-2xl font-extrabold text-[#0C3320]" style={serif}>
                  {brl(v.estimativa.valor_min)} – {brl(v.estimativa.valor_max)}
                </div>
                <div className="mt-1 text-xs text-[#7c8a80]">≈ {brl(v.estimativa.valor_m2)}/m²</div>
              </div>

              {v.estimativa.base_m2 != null && (
                <div className="rounded-lg border border-[#e6e0cf] bg-[#fcfaf3] p-3 text-[11px] leading-relaxed text-[#5b665e]">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#B8860B] mb-1.5">Como calculamos</div>
                  <div className="flex justify-between gap-2"><span className="truncate">Base de mercado · {v.estimativa.regiao_base}</span><span className="font-semibold text-[#0C3320] whitespace-nowrap">{brl(v.estimativa.base_m2)}/m²</span></div>
                  {(v.estimativa.fatores || []).map((f, i) => (
                    <div key={i} className="flex justify-between gap-2"><span className="truncate">{f.label}</span><span className="whitespace-nowrap">× {f.fator.toLocaleString('pt-BR')}</span></div>
                  ))}
                  <div className="flex justify-between gap-2 border-t border-[#e6e0cf] mt-1.5 pt-1.5"><span>Valor por m²</span><span className="font-semibold text-[#0C3320] whitespace-nowrap">{brl(v.estimativa.valor_m2)}/m²</span></div>
                  {v.estimativa.metodologia && <p className="mt-2 text-[#8a958d]">{v.estimativa.metodologia}</p>}
                </div>
              )}

              <p className="text-[10.5px] leading-relaxed text-[#8a958d] text-justify">{v.estimativa.aviso}</p>
              <div className="rounded-lg bg-[#F3F6F4] p-4">
                <p className="font-semibold text-gray-800" style={serif}>Quer o valor oficial com validade técnica?</p>
                <p className="text-sm text-gray-600 mb-3">PTAM / Laudo conforme NBR 14.653 com avaliador credenciado.</p>
                <form onSubmit={v.enviarLead} className="space-y-2.5">
                  <input className={inp} placeholder="Seu nome" value={v.contato.nome} onChange={(e) => v.setContatoCampo('nome', e.target.value)} />
                  <input className={inp} placeholder="WhatsApp" value={v.contato.whatsapp} onChange={(e) => v.setContatoCampo('whatsapp', e.target.value)} />
                  <input className={inp} type="email" placeholder="E-mail (opcional)" value={v.contato.email} onChange={(e) => v.setContatoCampo('email', e.target.value)} />
                  <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" value={v.hp} onChange={(e) => v.setHp(e.target.value)} style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, opacity: 0 }} />
                  <label className="flex items-start gap-2 text-[10px] text-[#7c8a80] leading-snug cursor-pointer">
                    <input type="checkbox" checked={v.consentimento} onChange={(e) => v.setConsentimento(e.target.checked)} className="mt-0.5 accent-[#0C3320]" />
                    <span>Autorizo o contato e o tratamento dos meus dados conforme a <a href="/privacidade" target="_blank" rel="noreferrer" className="underline">Política de Privacidade</a> (LGPD).</span>
                  </label>
                  <button disabled={v.loading} className="w-full rounded-lg bg-[#C9A84C] py-3 font-semibold text-[#0C3320] transition hover:brightness-105 disabled:opacity-60">
                    {v.loading ? 'Enviando...' : 'Quero o PTAM oficial'}
                  </button>
                </form>
              </div>
              <button onClick={v.reset} className="w-full text-sm text-gray-500 underline">← Refazer simulação</button>
            </div>
          )}

          {v.step === 'done' && <Done />}
        </div>
      </div>
    </div>
  );
}

function Done() {
  return (
    <div className="text-center py-8">
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#0C3320]">
        <span className="text-2xl text-white">✓</span>
      </div>
      <h2 className="text-xl font-bold text-[#0C3320]" style={{ fontFamily: "'Playfair Display', serif" }}>Recebido!</h2>
      <p className="mt-2 text-gray-600">Em breve um avaliador da Romatec entra em contato pelo seu WhatsApp.</p>
    </div>
  );
}
