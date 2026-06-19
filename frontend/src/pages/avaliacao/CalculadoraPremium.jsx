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
  const v = useAvaliacao();
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
            <form onSubmit={v.enviarLead} className="mt-5 space-y-2.5 text-left">
              <input className={inp} placeholder="Seu nome" value={v.contato.nome} onChange={(e) => v.setContatoCampo('nome', e.target.value)} />
              <input className={inp} placeholder="WhatsApp" value={v.contato.whatsapp} onChange={(e) => v.setContatoCampo('whatsapp', e.target.value)} />
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
