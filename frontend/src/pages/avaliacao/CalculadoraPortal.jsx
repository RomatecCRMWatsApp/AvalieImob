// Modelo 2 — Portal Moderno (principal). Rota: /quanto-vale-meu-imovel
import { useAvaliacao } from '../../hooks/useAvaliacao';
import AvalieIcon from '../../components/AvalieIcon';
import { brl } from '../../lib/format';

const serif = { fontFamily: "'Playfair Display', serif" };
const inp =
  'w-full rounded-lg border-[1.5px] border-[#e6ebe7] bg-[#fafbfa] px-3 py-2.5 text-sm ' +
  'text-gray-800 outline-none focus:border-[#0B6E4F] focus:ring-2 focus:ring-[#0B6E4F]/15';
const lab = 'block text-xs font-semibold text-[#52615a] mb-1.5';

export default function CalculadoraPortal() {
  const v = useAvaliacao('calc_portal');
  return (
    <div className="min-h-screen bg-[#F6F8F7] flex items-center justify-center p-4">
      <div className="w-full max-w-3xl bg-white rounded-3xl shadow-[0_30px_70px_-40px_rgba(12,51,32,0.45)] overflow-hidden grid md:grid-cols-2">
        {/* Esquerda — formulário */}
        <div className="p-7">
          <div className="flex items-center gap-2.5 mb-5">
            <AvalieIcon size={38} />
            <b className="text-[17px] text-[#0C3320]" style={serif}>AvalieImob</b>
          </div>

          {v.step === 'done' ? <Done /> : (
            <>
              <h1 className="text-[25px] font-extrabold text-[#172a20] leading-tight tracking-tight" style={serif}>
                Descubra o valor do seu imóvel
              </h1>
              <p className="text-[13.5px] text-[#67756c] mt-1 mb-5">Estimativa de mercado em menos de 1 minuto.</p>

              {v.erro && <div className="mb-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">{v.erro}</div>}

              {v.step === 'form' && (
                <form onSubmit={v.calcular} className="space-y-3.5">
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
                  <div><label className={lab}>Padrão construtivo</label>
                    <select className={inp} value={v.imovel.padrao} onChange={(e) => v.setCampo('padrao', e.target.value)}>
                      <option value="popular">Popular</option><option value="medio">Médio</option><option value="alto">Alto</option><option value="luxo">Luxo</option>
                    </select></div>
                  <button disabled={v.loading} className="w-full rounded-lg bg-[#0C3320] py-3 font-semibold text-white transition hover:brightness-110 disabled:opacity-60">
                    {v.loading ? 'Calculando...' : 'Calcular estimativa'}
                  </button>
                </form>
              )}

              {v.step === 'result' && (
                <div className="text-sm text-gray-600 space-y-1.5">
                  <p className="font-semibold text-gray-800" style={serif}>Resumo</p>
                  <p>{v.imovel.tipo} · {v.imovel.area} m² · {v.imovel.cidade}/{v.imovel.uf}</p>
                  <p>Padrão {v.imovel.padrao} · conservação {v.imovel.conservacao}</p>
                  <button onClick={v.reset} className="mt-2 text-gray-500 underline">← Refazer</button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Direita — painel verde */}
        {v.step !== 'done' && (
          <div className="p-7 text-white flex flex-col justify-center"
            style={{ background: 'linear-gradient(160deg,#0B6E4F,#0C3320 72%)' }}>
            {v.step === 'form' ? (
              <div className="text-center">
                <AvalieIcon size={56} className="mx-auto mb-4 opacity-90" />
                <p className="text-[#E3C56B] text-sm">Preencha ao lado e veja a faixa estimada do seu imóvel na hora.</p>
              </div>
            ) : v.estimativa && (
              <>
                <div className="text-[11px] uppercase tracking-[0.16em] text-[#E3C56B] font-semibold">Faixa estimada</div>
                <div className="text-[27px] font-extrabold leading-tight my-2.5" style={serif}>
                  {brl(v.estimativa.valor_min)}<br />a {brl(v.estimativa.valor_max)}
                </div>
                <div className="h-1.5 rounded-full my-3" style={{ background: 'linear-gradient(90deg,#B8860B,#E3C56B)' }} />
                <div className="flex justify-between text-[11px] text-[#bfd2c8]"><span>mín.</span><span>máx.</span></div>

                {v.estimativa.base_m2 != null && (
                  <div className="mt-4 rounded-lg bg-white/10 p-3 text-[11px] leading-relaxed">
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-[#E3C56B] mb-1.5">Como calculamos</div>
                    <div className="flex justify-between gap-2"><span className="text-[#bfd2c8] truncate">Base de mercado · {v.estimativa.regiao_base}</span><span className="font-semibold whitespace-nowrap">{brl(v.estimativa.base_m2)}/m²</span></div>
                    {(v.estimativa.fatores || []).map((f, i) => (
                      <div key={i} className="flex justify-between gap-2"><span className="text-[#bfd2c8] truncate">{f.label}</span><span className="whitespace-nowrap">× {f.fator.toLocaleString('pt-BR')}</span></div>
                    ))}
                    <div className="flex justify-between gap-2 border-t border-white/15 mt-1.5 pt-1.5"><span className="text-[#bfd2c8]">Valor por m²</span><span className="font-semibold text-[#E3C56B] whitespace-nowrap">{brl(v.estimativa.valor_m2)}/m²</span></div>
                    {v.estimativa.metodologia && <p className="text-[#a9c0b4] mt-2">{v.estimativa.metodologia}</p>}
                  </div>
                )}

                <p className="text-[11px] text-[#a9c0b4] mt-4 leading-relaxed">{v.estimativa.aviso}</p>

                {v.erro && <div className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-sm text-red-200">{v.erro}</div>}
                <form onSubmit={v.enviarLead} className="mt-4 space-y-2.5">
                  <input className="w-full rounded-lg bg-white/95 px-3 py-2.5 text-sm text-gray-800 outline-none" placeholder="Seu nome" value={v.contato.nome} onChange={(e) => v.setContatoCampo('nome', e.target.value)} />
                  <input className="w-full rounded-lg bg-white/95 px-3 py-2.5 text-sm text-gray-800 outline-none" placeholder="WhatsApp" value={v.contato.whatsapp} onChange={(e) => v.setContatoCampo('whatsapp', e.target.value)} />
                  <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" value={v.hp} onChange={(e) => v.setHp(e.target.value)} style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, opacity: 0 }} />
                  <label className="flex items-start gap-2 text-[10px] text-[#bfd2c8] leading-snug cursor-pointer">
                    <input type="checkbox" checked={v.consentimento} onChange={(e) => v.setConsentimento(e.target.checked)} className="mt-0.5 accent-[#C9A84C]" />
                    <span>Autorizo o contato e o tratamento dos meus dados conforme a <a href="/privacidade" target="_blank" rel="noreferrer" className="underline">Política de Privacidade</a> (LGPD).</span>
                  </label>
                  <button disabled={v.loading} className="w-full rounded-lg bg-[#C9A84C] py-3 font-semibold text-[#0C3320] transition hover:brightness-105 disabled:opacity-60">
                    {v.loading ? 'Enviando...' : 'Falar com um avaliador'}
                  </button>
                </form>
              </>
            )}
          </div>
        )}
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
      <p className="mt-2 text-gray-600">Em breve um avaliador da Romatec fala com você no WhatsApp.</p>
    </div>
  );
}
