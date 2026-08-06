/**
 * @module contratos-exclusividade/ContratoExclusividadeList
 * Painel admin do Contrato de Exclusividade com aceite eletrônico via WhatsApp.
 * Lista (badges de status + ações) + criação em etapas (modal) com cônjuge condicional.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Send, Bell, Trash2, X, Check, FileSignature, Loader2, ShieldCheck } from 'lucide-react';
import EnviarAssinaturaModal from '../assinatura/EnviarAssinaturaModal';
import { BrandSpinner } from '../../brand/BrandSpinner';
import { contratosExclusividadeAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';

const EXIGE_CONJUGE = (ec, rb) =>
  (ec === 'casado' || ec === 'uniao_estavel') && rb !== 'separacao_total';

const STATUS = {
  rascunho: ['Rascunho', 'bg-gray-100 text-gray-700'],
  enviado: ['Enviado', 'bg-blue-100 text-blue-700'],
  parcialmente_assinado: ['Parcialmente assinado', 'bg-amber-100 text-amber-700'],
  assinado: ['Assinado', 'bg-emerald-100 text-emerald-700'],
  expirado: ['Expirado', 'bg-red-100 text-red-700'],
  cancelado: ['Cancelado', 'bg-red-100 text-red-700'],
};

const brl = (v) =>
  'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const VAZIO = {
  proprietario: { nome: '', cpf: '', rg: '', nacionalidade: 'brasileiro(a)', profissao: '', whatsapp: '', email: '' },
  estado_civil: 'solteiro',
  regime_bens: '',
  conjuge: { nome: '', cpf: '', rg: '', nacionalidade: 'brasileiro(a)', profissao: '', whatsapp: '', email: '' },
  imovel: { descricao: '', endereco: '', bairro: '', cidade: 'Açailândia', uf: 'MA', matricula: '', cartorio: '', area_total: '', valor_anunciado: '' },
  comissao_percentual: 6,
  prazo_meses: 6,
  observacoes: '',
  multa_incluir: true,
  multa_modo: 'percentual_comissao',
  multa_percentual: 50,
  multa_valor_fixo: '',
  reembolso_despesas: true,
};

const Input = ({ label, value, onChange, placeholder, required, type = 'text', hint }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {label}{required && <span className="text-red-500"> *</span>}
    </label>
    <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
           className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
    {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
  </div>
);

const Select = ({ label, value, onChange, options }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
    <select value={value} onChange={(e) => onChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

function CriarModal({ onClose, onCriado }) {
  const { toast } = useToast();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(VAZIO);
  const [salvando, setSalvando] = useState(false);

  const upd = (sec, key, val) => setForm((f) => ({ ...f, [sec]: { ...f[sec], [key]: val } }));
  const setTop = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const exigeConj = EXIGE_CONJUGE(form.estado_civil, form.regime_bens);
  const etapas = ['Proprietário', 'Imóvel', 'Condições', 'Revisão'];

  const podeAvancar = () => {
    if (step === 0) {
      if (!form.proprietario.nome || form.proprietario.cpf.replace(/\D/g, '').length !== 11 || !form.proprietario.whatsapp) return false;
      if (exigeConj && (!form.conjuge.nome || form.conjuge.cpf.replace(/\D/g, '').length !== 11 || !form.conjuge.whatsapp)) return false;
      return true;
    }
    if (step === 1) return form.imovel.descricao && form.imovel.endereco && Number(form.imovel.valor_anunciado) > 0;
    return true;
  };

  const montarPayload = () => {
    const p = {
      proprietario: { ...form.proprietario, cpf: form.proprietario.cpf.replace(/\D/g, ''), whatsapp: form.proprietario.whatsapp.replace(/\D/g, '') },
      estado_civil: form.estado_civil,
      regime_bens: (form.estado_civil === 'casado' || form.estado_civil === 'uniao_estavel') ? (form.regime_bens || null) : null,
      conjuge: exigeConj ? { ...form.conjuge, cpf: form.conjuge.cpf.replace(/\D/g, ''), whatsapp: form.conjuge.whatsapp.replace(/\D/g, '') } : null,
      imovel: { ...form.imovel, valor_anunciado: Number(form.imovel.valor_anunciado) },
      comissao_percentual: Number(form.comissao_percentual),
      prazo_meses: Number(form.prazo_meses),
      observacoes: form.observacoes || null,
      reembolso_despesas: !!form.reembolso_despesas,
      multa_rescisoria: form.multa_incluir
        ? (form.multa_modo === 'valor_fixo'
            ? { modo: 'valor_fixo', valor_fixo: Number(form.multa_valor_fixo) }
            : { modo: 'percentual_comissao', percentual: Number(form.multa_percentual) })
        : null,
    };
    return p;
  };

  const comissaoEstimada = Number(form.imovel.valor_anunciado || 0) * Number(form.comissao_percentual || 0) / 100;

  const criarEEnviar = async () => {
    setSalvando(true);
    try {
      const r = await contratosExclusividadeAPI.criar(montarPayload());
      try {
        await contratosExclusividadeAPI.enviar(r.id);
        toast({ title: 'Contrato criado e enviado pelo WhatsApp' });
      } catch (e) {
        toast({ title: 'Contrato criado', description: e.response?.data?.detail || 'Não foi possível enviar agora — use "Enviar" na lista.', variant: 'destructive' });
      }
      onCriado();
    } catch (e) {
      const d = e.response?.data?.detail;
      const msg = Array.isArray(d) ? d.map((x) => x.msg).join('; ') : (d || 'Erro ao criar contrato');
      toast({ title: 'Erro', description: msg, variant: 'destructive' });
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-bold text-gray-900">Novo Contrato de Exclusividade</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-500" /></button>
        </div>

        <div className="px-6 py-3 flex gap-1 flex-wrap border-b">
          {etapas.map((e, i) => (
            <span key={i} className={`text-xs px-3 py-1.5 rounded-lg font-medium ${i === step ? 'bg-emerald-700 text-white' : i < step ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
              {i + 1}. {e}
            </span>
          ))}
        </div>

        <div className="p-6 space-y-4">
          {step === 0 && (
            <>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input label="Nome completo" value={form.proprietario.nome} onChange={(v) => upd('proprietario', 'nome', v)} required />
                <Input label="CPF" value={form.proprietario.cpf} onChange={(v) => upd('proprietario', 'cpf', v)} placeholder="000.000.000-00" required />
                <Input label="RG" value={form.proprietario.rg} onChange={(v) => upd('proprietario', 'rg', v)} />
                <Input label="Profissão" value={form.proprietario.profissao} onChange={(v) => upd('proprietario', 'profissao', v)} />
                <Input label="WhatsApp" value={form.proprietario.whatsapp} onChange={(v) => upd('proprietario', 'whatsapp', v)} placeholder="5599999999999" required hint="Formato 55 + DDD + número" />
                <Input label="E-mail" value={form.proprietario.email} onChange={(v) => upd('proprietario', 'email', v)} type="email" />
                <Select label="Estado civil" value={form.estado_civil} onChange={(v) => setTop('estado_civil', v)}
                        options={[
                          { value: 'solteiro', label: 'Solteiro(a)' }, { value: 'casado', label: 'Casado(a)' },
                          { value: 'uniao_estavel', label: 'União estável' }, { value: 'divorciado', label: 'Divorciado(a)' },
                          { value: 'viuvo', label: 'Viúvo(a)' },
                        ]} />
                {(form.estado_civil === 'casado' || form.estado_civil === 'uniao_estavel') && (
                  <Select label="Regime de bens" value={form.regime_bens} onChange={(v) => setTop('regime_bens', v)}
                          options={[
                            { value: '', label: 'Selecione...' },
                            { value: 'comunhao_parcial', label: 'Comunhão parcial' },
                            { value: 'comunhao_universal', label: 'Comunhão universal' },
                            { value: 'separacao_total', label: 'Separação total' },
                            { value: 'participacao_final_aquestos', label: 'Participação final nos aquestos' },
                          ]} />
                )}
              </div>

              {exigeConj && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
                  <p className="text-sm font-semibold text-amber-800">⚠ O cônjuge/companheiro(a) também deverá assinar o contrato (link próprio no WhatsApp dele).</p>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Input label="Nome do cônjuge" value={form.conjuge.nome} onChange={(v) => upd('conjuge', 'nome', v)} required />
                    <Input label="CPF do cônjuge" value={form.conjuge.cpf} onChange={(v) => upd('conjuge', 'cpf', v)} placeholder="000.000.000-00" required />
                    <Input label="RG do cônjuge" value={form.conjuge.rg} onChange={(v) => upd('conjuge', 'rg', v)} />
                    <Input label="Profissão" value={form.conjuge.profissao} onChange={(v) => upd('conjuge', 'profissao', v)} />
                    <Input label="WhatsApp do cônjuge" value={form.conjuge.whatsapp} onChange={(v) => upd('conjuge', 'whatsapp', v)} placeholder="5599999999999" required />
                    <Input label="E-mail" value={form.conjuge.email} onChange={(v) => upd('conjuge', 'email', v)} type="email" />
                  </div>
                </div>
              )}
            </>
          )}

          {step === 1 && (
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <Input label="Descrição do imóvel" value={form.imovel.descricao} onChange={(v) => upd('imovel', 'descricao', v)} placeholder="Ex: Casa residencial com 3 quartos..." required />
              </div>
              <div className="sm:col-span-2">
                <Input label="Endereço" value={form.imovel.endereco} onChange={(v) => upd('imovel', 'endereco', v)} required />
              </div>
              <Input label="Bairro" value={form.imovel.bairro} onChange={(v) => upd('imovel', 'bairro', v)} />
              <Input label="Cidade" value={form.imovel.cidade} onChange={(v) => upd('imovel', 'cidade', v)} />
              <Input label="UF" value={form.imovel.uf} onChange={(v) => upd('imovel', 'uf', v)} />
              <Input label="Matrícula" value={form.imovel.matricula} onChange={(v) => upd('imovel', 'matricula', v)} />
              <Input label="Cartório" value={form.imovel.cartorio} onChange={(v) => upd('imovel', 'cartorio', v)} />
              <Input label="Área total" value={form.imovel.area_total} onChange={(v) => upd('imovel', 'area_total', v)} placeholder="Ex: 360 m²" />
              <Input label="Valor anunciado (R$)" value={form.imovel.valor_anunciado} onChange={(v) => upd('imovel', 'valor_anunciado', v)} type="number" required />
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
                <p className="text-sm font-semibold text-emerald-800 mb-3">Condições da Corretagem</p>
                <div className="grid sm:grid-cols-2 gap-3">
                  <div>
                    <Input label="Comissão (%)" value={form.comissao_percentual} onChange={(v) => setTop('comissao_percentual', v)} type="number" hint="Entre 0,5 e 10" />
                    <p className="text-xs text-emerald-700 mt-1">Comissão estimada: <b>{brl(comissaoEstimada)}</b></p>
                  </div>
                  <Input label="Prazo de exclusividade (meses)" value={form.prazo_meses} onChange={(v) => setTop('prazo_meses', v)} type="number" hint="Comissão devida integralmente no prazo, mesmo em venda direta (art. 726 CC)" />
                </div>
              </div>

              <div className="border border-gray-200 rounded-xl p-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.multa_incluir} onChange={(e) => setTop('multa_incluir', e.target.checked)}
                         className="w-4 h-4 accent-emerald-700" />
                  <span className="text-sm font-medium text-gray-800">Incluir multa rescisória</span>
                </label>
                <p className="text-xs text-gray-400 mt-1">Penalidade caso o proprietário rescinda sem motivo antes do fim do prazo.</p>
                {form.multa_incluir && (
                  <div className="grid sm:grid-cols-2 gap-3 mt-3">
                    <Select label="Modo" value={form.multa_modo} onChange={(v) => setTop('multa_modo', v)}
                            options={[
                              { value: 'percentual_comissao', label: '% da comissão estimada' },
                              { value: 'valor_fixo', label: 'Valor fixo (R$)' },
                            ]} />
                    {form.multa_modo === 'percentual_comissao' ? (
                      <div>
                        <Input label="Percentual (%)" value={form.multa_percentual} onChange={(v) => setTop('multa_percentual', v)} type="number" hint="Entre 1 e 100" />
                        <p className="text-xs text-emerald-700 mt-1">Multa: <b>{brl(comissaoEstimada * Number(form.multa_percentual || 0) / 100)}</b></p>
                      </div>
                    ) : (
                      <Input label="Valor fixo (R$)" value={form.multa_valor_fixo} onChange={(v) => setTop('multa_valor_fixo', v)} type="number" />
                    )}
                  </div>
                )}
              </div>

              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" checked={form.reembolso_despesas} onChange={(e) => setTop('reembolso_despesas', e.target.checked)}
                       className="w-4 h-4 mt-0.5 accent-emerald-700" />
                <span className="text-sm text-gray-700">Incluir cláusula de reembolso de despesas de divulgação comprovadas (anúncios, placas, fotos, tráfego pago) em caso de rescisão antecipada.</span>
              </label>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
                <textarea value={form.observacoes} onChange={(e) => setTop('observacoes', e.target.value)} rows={3}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3 text-sm">
              <div className="bg-gray-50 rounded-xl p-4 space-y-1">
                <p><b>Proprietário:</b> {form.proprietario.nome} — {form.proprietario.cpf}</p>
                <p><b>WhatsApp:</b> {form.proprietario.whatsapp}</p>
                {exigeConj && <p><b>Cônjuge:</b> {form.conjuge.nome} — {form.conjuge.cpf} ({form.conjuge.whatsapp})</p>}
                <p><b>Imóvel:</b> {form.imovel.descricao}</p>
                <p><b>Valor:</b> {brl(form.imovel.valor_anunciado)} · <b>Comissão:</b> {form.comissao_percentual}% · <b>Prazo:</b> {form.prazo_meses} meses</p>
              </div>
              <p className="text-gray-600">
                Serão criados <b>{exigeConj ? '2 links' : '1 link'}</b> de aceite e enviados por WhatsApp
                {exigeConj ? ' (proprietário + cônjuge, cada um no seu número).' : ' ao proprietário.'}
              </p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t sticky bottom-0 bg-white">
          <button onClick={() => (step === 0 ? onClose() : setStep((s) => s - 1))}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-sm">
            {step === 0 ? 'Cancelar' : 'Anterior'}
          </button>
          {step < 3 ? (
            <button onClick={() => podeAvancar() && setStep((s) => s + 1)} disabled={!podeAvancar()}
                    className={`px-5 py-2 rounded-lg text-sm font-semibold text-white ${podeAvancar() ? 'bg-emerald-700' : 'bg-gray-300 cursor-not-allowed'}`}>
              Próxima
            </button>
          ) : (
            <button onClick={criarEEnviar} disabled={salvando}
                    className="px-5 py-2 rounded-lg text-sm font-semibold text-white bg-emerald-700 flex items-center gap-2">
              {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Criar e enviar pelo WhatsApp
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ContratoExclusividadeList() {
  const { toast } = useToast();
  const nav = useNavigate();
  const [lista, setLista] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);  // legado (modal de criação substituído pelo wizard)
  const [envioExt, setEnvioExt] = useState(null);

  const carregar = async () => {
    setLoading(true);
    try { setLista(await contratosExclusividadeAPI.listar()); }
    catch { toast({ title: 'Erro ao carregar contratos', variant: 'destructive' }); }
    finally { setLoading(false); }
  };
  useEffect(() => { carregar(); }, []); // eslint-disable-line

  const enviar = async (c) => {
    try { await contratosExclusividadeAPI.enviar(c.id); toast({ title: 'Enviado pelo WhatsApp' }); carregar(); }
    catch (e) { toast({ title: 'Erro ao enviar', description: e.response?.data?.detail || '', variant: 'destructive' }); }
  };
  const reenviar = async (c, papel) => {
    try { await contratosExclusividadeAPI.reenviar(c.id, papel); toast({ title: 'Lembrete reenviado' }); }
    catch (e) { toast({ title: 'Erro', description: e.response?.data?.detail || '', variant: 'destructive' }); }
  };
  const cancelar = async (c) => {
    if (!window.confirm('Cancelar este contrato? Os links de aceite deixarão de funcionar.')) return;
    try { await contratosExclusividadeAPI.cancelar(c.id); toast({ title: 'Contrato cancelado' }); carregar(); }
    catch (e) { toast({ title: 'Erro', description: e.response?.data?.detail || '', variant: 'destructive' }); }
  };

  const pendentes = (c) => (c.signatarios || []).filter((s) => s.status !== 'aceito');
  const aceitos = (c) => (c.signatarios || []).filter((s) => s.status === 'aceito').length;
  const andamento = (c) => {
    const e = c.etapas || [];
    return e.length ? Math.round((e.filter((x) => x.concluida).length / e.length) * 100) : null;
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileSignature className="w-7 h-7 text-emerald-700" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Contratos de Exclusividade</h1>
            <p className="text-sm text-gray-500">Aceite eletrônico por WhatsApp (token por signatário)</p>
          </div>
        </div>
        <button onClick={() => nav('/dashboard/exclusividade/novo')}
                className="flex items-center gap-2 bg-emerald-700 text-white px-4 py-2.5 rounded-xl text-sm font-semibold">
          <Plus className="w-4 h-4" /> Novo contrato
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><BrandSpinner label="Carregando…" /></div>
      ) : lista.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <FileSignature className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>Nenhum contrato de exclusividade ainda.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {lista.map((c) => {
            const [label, cls] = STATUS[c.status] || [c.status, 'bg-gray-100 text-gray-700'];
            const total = (c.signatarios || []).length;
            return (
              <div key={c.id} className="bg-white border border-gray-200 rounded-xl p-4 flex flex-wrap items-center gap-3 justify-between">
                <div className="min-w-0 cursor-pointer" onClick={() => (c.status === 'rascunho' || c.status === 'enviado' || c.status === 'parcialmente_assinado') && nav(`/dashboard/exclusividade/${c.id}`)}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${cls}`}>{label}</span>
                    {(c.status === 'enviado' || c.status === 'parcialmente_assinado') && (
                      <span className="text-xs text-gray-500">{aceitos(c)}/{total} assinaturas</span>
                    )}
                    {c.status === 'rascunho' && andamento(c) !== null && (
                      <span className="text-xs text-gray-500">{andamento(c)}% preenchido</span>
                    )}
                  </div>
                  <p className="font-medium text-gray-900 mt-1 truncate">{c.imovel?.descricao_geral || c.imovel?.descricao || 'Imóvel'}</p>
                  <p className="text-sm text-gray-500 truncate">
                    {(c.proprietarios || []).map((p) => p.nome).filter(Boolean).join(', ') || '—'} · {brl(c.imovel?.valor_anunciado)} · {c.comissao_percentual}% · {c.prazo_meses} meses
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {(c.status === 'rascunho' || c.status === 'enviado') && (
                    <button onClick={() => enviar(c)} className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 font-medium">
                      <Send className="w-3.5 h-3.5" /> Enviar
                    </button>
                  )}
                  {(c.status === 'enviado' || c.status === 'parcialmente_assinado') &&
                    pendentes(c).map((s) => (
                      <button key={s.papel} onClick={() => reenviar(c, s.papel)} title={`Lembrar ${s.nome}`}
                              className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 font-medium">
                        <Bell className="w-3.5 h-3.5" /> {s.papel === 'proprietario' ? 'Proprietário' : 'Cônjuge'}
                      </button>
                    ))}
                  {c.status === 'assinado' && c.pdf_final_url && (
                    <a href={c.pdf_final_url} target="_blank" rel="noreferrer"
                       className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 font-medium">
                      <Check className="w-3.5 h-3.5" /> PDF assinado
                    </a>
                  )}
                  <button onClick={() => setEnvioExt(c)} title="Enviar para assinatura externa (D4Sign/Clicksign/Autentique)"
                          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 font-medium">
                    <ShieldCheck className="w-3.5 h-3.5" /> Assinatura externa
                  </button>
                  {c.status !== 'assinado' && c.status !== 'cancelado' && (
                    <button onClick={() => cancelar(c)} className="p-2 rounded-lg text-red-500 hover:bg-red-50" title="Cancelar">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {modal && <CriarModal onClose={() => setModal(false)} onCriado={() => { setModal(false); carregar(); }} />}
      {envioExt && (
        <EnviarAssinaturaModal
          origemTipo="contrato_exclusividade"
          origemId={envioExt.id}
          origemLabel={`Exclusividade — ${envioExt.imovel?.descricao_geral || envioExt.imovel?.descricao || 'Imóvel'}`}
          onClose={() => setEnvioExt(null)}
        />
      )}
    </div>
  );
}
