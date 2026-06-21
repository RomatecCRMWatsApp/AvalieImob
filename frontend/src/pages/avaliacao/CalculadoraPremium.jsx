// Modelo 3 — Premium Escuro. Rota: /avaliacao/premium
import { useAvaliacao } from '../../hooks/useAvaliacao';
import AvalieIcon from '../../components/AvalieIcon';
import { brl } from '../../lib/format';

const serif = { fontFamily: "'Playfair Display', serif" };
const inp =
  'w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white ' +
  'placeholder:text-[#8fa79a] outline-none focus:border-[#C9A84C] focus:ring-2 focus:ring-[#C9A84C]/20';
const lab = 'block text-xs font-semibold text-[#cdd9d1] mb-1.5 text-left';

export default function CalculadoraPremium() {
  const v = useAvaliacao('calc_premium');
  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'radial-gradient(120% 90% at 50% 0%,#0f3d28,#07251A 70%)' }}>
      <div className="w-full max-w-md rounded-3xl border border-[#C9A84C]/30 bg-white/[0.045] p-8 text-center backdrop-blur-md shadow-[0_30px_80px_-40px_rgba(0,0,0,0.7)]">
        <div className="relative mx-auto mb-4 h-[78px] w-[78px]">
          <div className="absolute -inset-3 rounded-full"
            style={{ background: 'radial-gradient(circle,rgba(201,168,76,0.5),transparent 62%)' }} />
          <AvalieIcon size={78} className="relative" />
        </div>

        {v.erro && <div className="mb-3 rounded-lg bg-white/10 px-3 py-2 text-sm text-red-200">{v.erro}</div>}

        {v.step === 'form' && (
          <>
            <h1 className="text-[23px] font-bold text-white" style={serif}>Quanto vale o seu imóvel?</h1>
            <p className="text-[13px] text-[#E3C56B] mb-6 tracking-wide">Avaliação preliminar de mercado</p>
            <form onSubmit={v.calcular} className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div><label className={lab}>UF</label>
                  <select className={inp} value={v.imovel.uf} onChange={(e) => v.setCampo('uf', e.target.value)}>
                    {['MA', 'PA', 'TO', 'SP'].map((u) => <option key={u} className="text-gray-800">{u}</option>)}
                  </select></div>
                <div className="col-span-2"><label className={lab}>Cidade</label>
                  <input className={inp} value={v.imovel.cidade} onChange={(e) => v.setCampo('cidade', e.target.value)} placeholder="Açailândia" /></div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2"><label className={lab}>Tipo</label>
                  <select className={inp} value={v.imovel.tipo} onChange={(e) => v.setCampo('tipo', e.target.value)}>
                    {[['casa', 'Casa'], ['apartamento', 'Apartamento'], ['comercial', 'Comercial'], ['terreno', 'Terreno'], ['rural', 'Rural']]
                      .map(([k, l]) => <option key={k} value={k} className="text-gray-800">{l}</option>)}
                  </select></div>
                <div><label className={lab}>Área m²</label>
                  <input className={inp} type="number" min="1" value={v.imovel.area} onChange={(e) => v.setCampo('area', e.target.value)} placeholder="180" /></div>
              </div>
              <div><label className={lab}>Padrão</label>
                <select className={inp} value={v.imovel.padrao} onChange={(e) => v.setCampo('padrao', e.target.value)}>
                  {[['popular', 'Popular'], ['medio', 'Médio'], ['alto', 'Alto'], ['luxo', 'Luxo']]
                    .map(([k, l]) => <option key={k} value={k} className="text-gray-800">{l}</option>)}
                </select></div>
              <button disabled={v.loading} className="w-full rounded-lg py-3 font-semibold text-[#0C3320] transition hover:brightness-105 disabled:opacity-60"
                style={{ background: 'linear-gradient(120deg,#E3C56B,#C9A84C)', boxShadow: '0 12px 30px -12px rgba(201,168,76,0.6)' }}>
                {v.loading ? 'Calculando...' : 'Calcular estimativa'}
              </button>
            </form>
          </>
        )}

        {v.step === 'result' && v.estimativa && (
          <>
            <div className="mt-2 border-t border-[#C9A84C]/25 pt-5">
              <div className="text-[10.5px] uppercase tracking-[0.2em] text-[#9fb7aa]">Faixa estimada de mercado</div>
              <div className="mt-2 text-[26px] font-extrabold text-[#E3C56B]" style={serif}>
                {brl(v.estimativa.valor_min)} – {brl(v.estimativa.valor_max)}
              </div>
            </div>

            {v.estimativa.base_m2 != null && (
              <div className="mt-4 rounded-lg border border-[#C9A84C]/25 bg-white/[0.04] p-3 text-left text-[11px] leading-relaxed text-[#cdd9d1]">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#E3C56B] mb-1.5">Como calculamos</div>
                <div className="flex justify-between gap-2"><span className="text-[#9fb7aa] truncate">Base de mercado · {v.estimativa.regiao_base}</span><span className="font-semibold whitespace-nowrap">{brl(v.estimativa.base_m2)}/m²</span></div>
                {(v.estimativa.fatores || []).map((f, i) => (
                  <div key={i} className="flex justify-between gap-2"><span className="text-[#9fb7aa] truncate">{f.label}</span><span className="whitespace-nowrap">× {f.fator.toLocaleString('pt-BR')}</span></div>
                ))}
                <div className="flex justify-between gap-2 border-t border-white/10 mt-1.5 pt-1.5"><span className="text-[#9fb7aa]">Valor por m²</span><span className="font-semibold text-[#E3C56B] whitespace-nowrap">{brl(v.estimativa.valor_m2)}/m²</span></div>
                {v.estimativa.metodologia && <p className="mt-2 text-[#7e978a]">{v.estimativa.metodologia}</p>}
              </div>
            )}
            <form onSubmit={v.enviarLead} className="mt-5 space-y-2.5 text-left">
              <input className={inp} placeholder="Seu nome" value={v.contato.nome} onChange={(e) => v.setContatoCampo('nome', e.target.value)} />
              <input className={inp} placeholder="WhatsApp" value={v.contato.whatsapp} onChange={(e) => v.setContatoCampo('whatsapp', e.target.value)} />
              <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" value={v.hp} onChange={(e) => v.setHp(e.target.value)} style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, opacity: 0 }} />
              <label className="flex items-start gap-2 text-[10px] text-[#9fb7aa] leading-snug cursor-pointer">
                <input type="checkbox" checked={v.consentimento} onChange={(e) => v.setConsentimento(e.target.checked)} className="mt-0.5 accent-[#C9A84C]" />
                <span>Autorizo o contato e o tratamento dos meus dados conforme a <a href="/privacidade" target="_blank" rel="noreferrer" className="underline">Política de Privacidade</a> (LGPD).</span>
              </label>
              <button disabled={v.loading} className="w-full rounded-lg py-3 font-semibold text-[#0C3320] transition hover:brightness-105 disabled:opacity-60"
                style={{ background: 'linear-gradient(120deg,#E3C56B,#C9A84C)' }}>
                {v.loading ? 'Enviando...' : 'Solicitar avaliação oficial'}
              </button>
            </form>
            <p className="text-[10px] text-[#7e978a] mt-3">{v.estimativa.aviso}</p>
            <button onClick={v.reset} className="mt-3 text-xs text-[#9fb7aa] underline">← Refazer</button>
          </>
        )}

        {v.step === 'done' && (
          <div className="py-6">
            <h2 className="text-xl font-bold text-[#E3C56B]" style={serif}>Recebido!</h2>
            <p className="mt-2 text-[#cdd9d1]">Em breve um avaliador da Romatec entra em contato pelo seu WhatsApp.</p>
          </div>
        )}
      </div>
    </div>
  );
}
