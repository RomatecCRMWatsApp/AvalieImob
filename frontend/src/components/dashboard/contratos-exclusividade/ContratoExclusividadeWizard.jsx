/**
 * @module contratos-exclusividade/ContratoExclusividadeWizard
 * Wizard do Contrato de Exclusividade (multiproprietários + ficha de imóvel padrão PTAM).
 * Reusa ImovelMap/StreetView/FotosLaudo/ImageUploader. Autosave (rascunho → PUT) + etapas.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Trash2, Send, Loader2, ChevronLeft, ChevronRight, Save, MapPin } from 'lucide-react';
import { contratosExclusividadeAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import ImovelMap from '../../maps/ImovelMap';
import StreetView from '../../maps/StreetView';
import FotosLaudo from '../ptam/FotosLaudo';
import ImageUploader from '../ptam/ImageUploader';

const CHECKLIST_ITENS = [
  ['matricula_do_imovel', 'Matrícula do imóvel'],
  ['carne_iptu', 'Carnê de IPTU'],
  ['planta_projeto_aprovado', 'Planta/projeto aprovado'],
  ['escritura_contrato', 'Escritura/contrato'],
  ['fotografias_do_imovel', 'Fotografias do imóvel'],
  ['habite_se_auto_conclusao', 'Habite-se/auto de conclusão'],
  ['georreferenciamento_sigef_incra', 'Georreferenciamento SIGEF/INCRA'],
  ['ccir_cadastro_imovel_rural', 'CCIR'],
  ['itr_imposto_territorial_rural', 'ITR'],
  ['car_cadastro_ambiental_rural', 'CAR'],
  ['nirf_cib_receita_federal', 'NIRF/CIB'],
  ['certidoes_negativas', 'Certidões negativas'],
  ['certidao_de_onus_reais', 'Certidão de ônus reais'],
  ['bci_boletim_cadastro_imobiliario', 'BCI'],
  ['memorial_descritivo', 'Memorial descritivo'],
  ['metragem_das_construcoes', 'Metragem das construções'],
  ['certidao_de_valor_venal', 'Certidão de valor venal'],
  ['licenca_ambiental', 'Licença ambiental'],
  ['art_trt', 'ART/TRT'],
  ['outros_documentos', 'Outros documentos'],
];

const ETAPAS = ['Proprietários', 'Imóvel', 'Fotos & Documentos', 'Condições', 'Revisão'];

const PROP_VAZIO = {
  nome: '', cpf_cnpj: '', rg: '', nacionalidade: 'brasileiro(a)', profissao: '',
  whatsapp: '', email: '', fracao_percentual: '', estado_civil: 'solteiro',
  regime_bens: '', conjuge: null,
};

const brl = (v) => 'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
const soDig = (v) => String(v || '').replace(/\D/g, '');

// "1/3" ou "33,33" ou "33%" → número (2 casas)
function parseFracao(v) {
  const s = String(v || '').trim().replace('%', '').replace(',', '.');
  if (s.includes('/')) {
    const [a, b] = s.split('/').map(Number);
    if (b) return Math.round((a / b) * 10000) / 100;
  }
  const n = parseFloat(s);
  return isNaN(n) ? 0 : n;
}

const exigeConjuge = (ec, rb) =>
  (ec === 'casado' || ec === 'uniao_estavel') && rb !== 'separacao_total';

const Input = ({ label, value, onChange, placeholder, type = 'text', required, hint }) => (
  <div>
    {label && <label className="block text-sm font-medium text-gray-700 mb-1">{label}{required && <span className="text-red-500"> *</span>}</label>}
    <input type={type} value={value ?? ''} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
           className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" />
    {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
  </div>
);

const Select = ({ label, value, onChange, options }) => (
  <div>
    {label && <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>}
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

export default function ContratoExclusividadeWizard() {
  const { id } = useParams();
  const nav = useNavigate();
  const { toast } = useToast();
  const isNew = !id || id === 'novo';

  const [contratoId, setContratoId] = useState(isNew ? null : id);
  const [form, setForm] = useState({
    proprietarios: [{ ...PROP_VAZIO }],
    imovel: { cidade: 'Açailândia', uf: 'MA', fotos: [], documentos: [], checklist_documentacao: {} },
    comissao_percentual: 6, prazo_meses: 6,
    multa_incluir: true, multa_modo: 'percentual_comissao', multa_percentual: 50, multa_valor_fixo: '',
    reembolso_despesas: true,
    assinatura_cidade: '', assinatura_data: '', foro_comarca: 'Açailândia/MA',
  });
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(!isNew);
  const [lastSaved, setLastSaved] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const formRef = useRef(form);
  const cidRef = useRef(contratoId);
  const dirtyRef = useRef(false);
  const debounceRef = useRef(null);
  const creatingRef = useRef(false);
  const skipRef = useRef(false);
  useEffect(() => { formRef.current = form; }, [form]);
  useEffect(() => { cidRef.current = contratoId; }, [contratoId]);

  // Load existente
  useEffect(() => {
    if (isNew) return;
    let vivo = true;
    contratosExclusividadeAPI.buscar(id).then((d) => {
      if (!vivo) return;
      skipRef.current = true;
      setForm((f) => ({
        ...f, ...d,
        proprietarios: (d.proprietarios && d.proprietarios.length) ? d.proprietarios : [{ ...PROP_VAZIO }],
        imovel: { ...f.imovel, ...(d.imovel || {}) },
      }));
      setLoading(false);
    }).catch(() => { toast({ title: 'Erro ao carregar', variant: 'destructive' }); nav('/dashboard/exclusividade'); });
    return () => { vivo = false; };
  }, [id, isNew]); // eslint-disable-line

  // Persistência
  const buildPayload = () => {
    const f = formRef.current;
    return {
      proprietarios: f.proprietarios.map((p) => ({
        ...p, cpf_cnpj: soDig(p.cpf_cnpj), whatsapp: soDig(p.whatsapp),
        fracao_percentual: parseFracao(p.fracao_percentual),
        regime_bens: (p.estado_civil === 'casado' || p.estado_civil === 'uniao_estavel') ? (p.regime_bens || null) : null,
        conjuge: exigeConjuge(p.estado_civil, p.regime_bens) && p.conjuge
          ? { ...p.conjuge, cpf: soDig(p.conjuge.cpf), whatsapp: soDig(p.conjuge.whatsapp) } : null,
      })),
      imovel: f.imovel,
      comissao_percentual: Number(f.comissao_percentual),
      prazo_meses: Number(f.prazo_meses),
      assinatura_cidade: f.assinatura_cidade, assinatura_data: f.assinatura_data || null,
      foro_comarca: f.foro_comarca,
    };
  };

  const persist = useCallback(async (silent = true) => {
    let cid = cidRef.current;
    try {
      if (!cid) {
        if (creatingRef.current) return;
        creatingRef.current = true;
        const r = await contratosExclusividadeAPI.criarRascunho();
        cid = r.id; setContratoId(cid); cidRef.current = cid;
        nav(`/dashboard/exclusividade/${cid}`, { replace: true });
      }
      await contratosExclusividadeAPI.atualizar(cid, buildPayload());
      dirtyRef.current = false;
      setLastSaved(new Date());
      if (!silent) toast({ title: 'Salvo ✓' });
    } catch (e) {
      if (!cid) creatingRef.current = false;
      if (!silent) toast({ title: 'Erro ao salvar', description: e.response?.data?.detail || '', variant: 'destructive' });
    }
  }, [nav, toast]);

  const flush = useCallback(() => { if (dirtyRef.current) persist(true); }, [persist]);

  // Autosave debounced
  useEffect(() => {
    if (skipRef.current) { skipRef.current = false; return; }
    dirtyRef.current = true;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => persist(true), 1500);
    return () => clearTimeout(debounceRef.current);
  }, [form, persist]);
  useEffect(() => () => { flush(); }, [flush]);

  const setImovel = (k, v) => setForm((f) => ({ ...f, imovel: { ...f.imovel, [k]: v } }));
  const setProp = (i, k, v) => setForm((f) => {
    const props = [...f.proprietarios]; props[i] = { ...props[i], [k]: v }; return { ...f, proprietarios: props };
  });
  const setConj = (i, k, v) => setForm((f) => {
    const props = [...f.proprietarios];
    props[i] = { ...props[i], conjuge: { ...(props[i].conjuge || { nome: '', cpf: '', whatsapp: '' }), [k]: v } };
    return { ...f, proprietarios: props };
  });
  const addProp = () => setForm((f) => ({ ...f, proprietarios: [...f.proprietarios, { ...PROP_VAZIO }] }));
  const rmProp = (i) => setForm((f) => ({ ...f, proprietarios: f.proprietarios.filter((_, j) => j !== i) }));

  const somaFracoes = form.proprietarios.reduce((s, p) => s + parseFracao(p.fracao_percentual), 0);
  const fracoesOk = Math.abs(somaFracoes - 100) <= 0.05;

  const goStep = (n) => { flush(); setStep(n); };
  const goNext = () => { flush(); setStep((s) => Math.min(s + 1, ETAPAS.length - 1)); };
  const goPrev = () => { flush(); setStep((s) => Math.max(s - 1, 0)); };

  const enviar = async () => {
    setEnviando(true);
    try {
      await persist(true);
      await contratosExclusividadeAPI.enviar(cidRef.current);
      toast({ title: 'Contrato enviado para assinatura pelo WhatsApp' });
      nav('/dashboard/exclusividade');
    } catch (e) {
      const d = e.response?.data?.detail;
      toast({ title: 'Não foi possível enviar', description: Array.isArray(d) ? d.map((x) => x.msg).join('; ') : (d || ''), variant: 'destructive' });
    } finally { setEnviando(false); }
  };

  if (loading) return <div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-emerald-700" /></div>;

  const im = form.imovel;
  const comissaoEstimada = Number(im.valor_anunciado || 0) * Number(form.comissao_percentual || 0) / 100;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-xl font-bold text-gray-900">Contrato de Exclusividade</h1>
        <button onClick={() => persist(false)} className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-emerald-700 text-white">
          <Save className="w-4 h-4" /> Salvar
        </button>
      </div>
      <p className="text-xs text-gray-400 mb-4">{lastSaved ? `Salvo ✓ ${lastSaved.toLocaleTimeString('pt-BR')}` : 'Não salvo'}</p>

      <div className="flex gap-1 flex-wrap mb-5">
        {ETAPAS.map((e, i) => (
          <button key={i} onClick={() => goStep(i)}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium ${i === step ? 'bg-emerald-700 text-white' : i < step ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
            {i + 1}. {e}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
        {/* ETAPA 1 — PROPRIETÁRIOS */}
        {step === 0 && (
          <>
            <div className="border border-amber-200 bg-amber-50/40 rounded-xl p-1">
              <p className="text-sm font-semibold text-amber-800 px-3 pt-2">Proprietário(s) do Imóvel</p>
              <p className="text-xs text-amber-700 px-3 pb-2">Para herdeiros e partilhas, adicione todos os proprietários.</p>
              {form.proprietarios.map((p, i) => (
                <div key={i} className="bg-white border border-gray-200 rounded-lg p-3 m-2 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-700">Proprietário {i + 1}</span>
                    {form.proprietarios.length > 1 && (
                      <button onClick={() => rmProp(i)} className="text-red-500 p-1"><Trash2 className="w-4 h-4" /></button>
                    )}
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Input label="Nome / Razão social" value={p.nome} onChange={(v) => setProp(i, 'nome', v)} required />
                    <Input label="CPF / CNPJ" value={p.cpf_cnpj} onChange={(v) => setProp(i, 'cpf_cnpj', v)} placeholder="CPF ou CNPJ" required />
                    <Input label="Fração / Percentual" value={p.fracao_percentual} onChange={(v) => setProp(i, 'fracao_percentual', v)} placeholder="33% ou 1/3" hint={`= ${parseFracao(p.fracao_percentual)}%`} />
                    <Input label="WhatsApp" value={p.whatsapp} onChange={(v) => setProp(i, 'whatsapp', v)} placeholder="5599999999999" required />
                    <Input label="RG" value={p.rg} onChange={(v) => setProp(i, 'rg', v)} />
                    <Input label="Profissão" value={p.profissao} onChange={(v) => setProp(i, 'profissao', v)} />
                  </div>
                  {soDig(p.cpf_cnpj).length !== 14 && (
                    <div className="grid sm:grid-cols-2 gap-3">
                      <Select label="Estado civil" value={p.estado_civil} onChange={(v) => setProp(i, 'estado_civil', v)}
                              options={[{ value: 'solteiro', label: 'Solteiro(a)' }, { value: 'casado', label: 'Casado(a)' }, { value: 'uniao_estavel', label: 'União estável' }, { value: 'divorciado', label: 'Divorciado(a)' }, { value: 'viuvo', label: 'Viúvo(a)' }]} />
                      {(p.estado_civil === 'casado' || p.estado_civil === 'uniao_estavel') && (
                        <Select label="Regime de bens" value={p.regime_bens} onChange={(v) => setProp(i, 'regime_bens', v)}
                                options={[{ value: '', label: 'Selecione...' }, { value: 'comunhao_parcial', label: 'Comunhão parcial' }, { value: 'comunhao_universal', label: 'Comunhão universal' }, { value: 'separacao_total', label: 'Separação total' }, { value: 'participacao_final_aquestos', label: 'Participação final nos aquestos' }]} />
                      )}
                    </div>
                  )}
                  {exigeConjuge(p.estado_civil, p.regime_bens) && soDig(p.cpf_cnpj).length !== 14 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
                      <p className="text-xs font-semibold text-amber-800">⚠ O cônjuge deste proprietário também assinará (link próprio).</p>
                      <div className="grid sm:grid-cols-2 gap-3">
                        <Input label="Nome do cônjuge" value={p.conjuge?.nome} onChange={(v) => setConj(i, 'nome', v)} required />
                        <Input label="CPF do cônjuge" value={p.conjuge?.cpf} onChange={(v) => setConj(i, 'cpf', v)} required />
                        <Input label="WhatsApp do cônjuge" value={p.conjuge?.whatsapp} onChange={(v) => setConj(i, 'whatsapp', v)} placeholder="5599999999999" required />
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <button onClick={addProp} className="flex items-center gap-1.5 text-sm text-emerald-700 font-medium px-3 py-2 m-2">
                <Plus className="w-4 h-4" /> Adicionar Proprietário
              </button>
              <div className={`text-sm font-semibold px-3 py-2 m-2 rounded-lg ${fracoesOk ? 'text-emerald-700 bg-emerald-50' : 'text-red-600 bg-red-50'}`}>
                Soma das frações: {somaFracoes.toFixed(2)}% {fracoesOk ? '✓' : '— deve totalizar 100%'}
              </div>
            </div>
          </>
        )}

        {/* ETAPA 2 — IMÓVEL */}
        {step === 1 && (
          <>
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2"><Input label="Endereço / Logradouro" value={im.endereco} onChange={(v) => setImovel('endereco', v)} required /></div>
              <Input label="Bairro" value={im.bairro} onChange={(v) => setImovel('bairro', v)} />
              <Input label="Cidade" value={im.cidade} onChange={(v) => setImovel('cidade', v)} />
              <Input label="UF" value={im.uf} onChange={(v) => setImovel('uf', v)} />
              <Input label="CEP" value={im.cep} onChange={(v) => setImovel('cep', v)} placeholder="00000-000" />
              <Input label="Matrícula" value={im.matricula} onChange={(v) => setImovel('matricula', v)} />
              <Input label="Cartório / Ofício de Registro" value={im.cartorio} onChange={(v) => setImovel('cartorio', v)} placeholder="Ex: 1º Ofício de Registro de Imóveis de..." />
              <Input label="Latitude (GPS)" value={im.latitude} onChange={(v) => setImovel('latitude', v)} type="number" />
              <Input label="Longitude (GPS)" value={im.longitude} onChange={(v) => setImovel('longitude', v)} type="number" />
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500"><MapPin className="w-4 h-4" /> Localização no mapa</div>
            <ImovelMap endereco={[im.endereco, im.bairro, im.cidade, im.uf].filter(Boolean).join(', ')} lat={im.latitude} lng={im.longitude} height={260} />
            {im.latitude && im.longitude && <StreetView lat={im.latitude} lng={im.longitude} endereco={im.endereco} height={240} />}
            <div className="grid sm:grid-cols-2 gap-3">
              <Input label="Área total (m²)" value={im.area_total_m2} onChange={(v) => { setImovel('area_total_m2', v); if (v && !im.area_hectares) setImovel('area_hectares', (Number(v) / 10000).toFixed(4)); }} type="number" />
              <Input label="Área (hectares)" value={im.area_hectares} onChange={(v) => setImovel('area_hectares', v)} type="number" hint="4 casas decimais" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confrontações / Limites</label>
              <textarea value={im.confrontacoes || ''} onChange={(e) => setImovel('confrontacoes', e.target.value)} rows={2} placeholder="Norte: ...; Sul: ...; Leste: ...; Oeste: ..." className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descrição geral do imóvel <span className="text-red-500">*</span></label>
              <textarea value={im.descricao_geral || ''} onChange={(e) => setImovel('descricao_geral', e.target.value)} rows={3} placeholder="Descrição literal do imóvel conforme a matrícula / SIGEF..." className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
            </div>
            <Input label="Valor anunciado (R$)" value={im.valor_anunciado} onChange={(v) => setImovel('valor_anunciado', v)} type="number" required />
          </>
        )}

        {/* ETAPA 3 — FOTOS & DOCUMENTOS & CHECKLIST */}
        {step === 2 && (
          <>
            <p className="text-sm font-semibold text-gray-700">Fotos do imóvel</p>
            <FotosLaudo value={im.fotos || []} onChange={(v) => setImovel('fotos', v)} maxImages={30} ptamId={contratoId} />
            <p className="text-sm font-semibold text-gray-700 mt-2">Documentos do imóvel (matrícula, IPTU, escritura)</p>
            <ImageUploader images={(im.documentos || []).map((d) => d.image_id || d)} onImagesChange={(ids) => setImovel('documentos', ids.map((x) => ({ image_id: x, nome_arquivo: '', tipo: 'outro' })))} maxImages={10} label="Documentos" accept="image/*,application/pdf" acceptPdf />
            <p className="text-sm font-semibold text-gray-700 mt-2">Documentação analisada (NBR 14653)</p>
            <div className="grid sm:grid-cols-2 gap-1">
              {CHECKLIST_ITENS.map(([k, lbl]) => (
                <label key={k} className="flex items-center gap-2 text-sm py-1 cursor-pointer">
                  <input type="checkbox" checked={!!(im.checklist_documentacao || {})[k]} onChange={(e) => setImovel('checklist_documentacao', { ...(im.checklist_documentacao || {}), [k]: e.target.checked })} className="w-4 h-4 accent-emerald-700" />
                  {lbl}
                </label>
              ))}
            </div>
          </>
        )}

        {/* ETAPA 4 — CONDIÇÕES */}
        {step === 3 && (
          <>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Input label="Comissão (%)" value={form.comissao_percentual} onChange={(v) => setForm((f) => ({ ...f, comissao_percentual: v }))} type="number" />
                <p className="text-xs text-emerald-700 mt-1">Comissão estimada: <b>{brl(comissaoEstimada)}</b></p>
              </div>
              <Input label="Prazo de exclusividade (meses)" value={form.prazo_meses} onChange={(v) => setForm((f) => ({ ...f, prazo_meses: v }))} type="number" />
            </div>
            <div className="border border-gray-200 rounded-xl p-3">
              <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={form.multa_incluir} onChange={(e) => setForm((f) => ({ ...f, multa_incluir: e.target.checked }))} className="w-4 h-4 accent-emerald-700" /><span className="text-sm font-medium">Incluir multa rescisória</span></label>
              {form.multa_incluir && (
                <div className="grid sm:grid-cols-2 gap-3 mt-3">
                  <Select label="Modo" value={form.multa_modo} onChange={(v) => setForm((f) => ({ ...f, multa_modo: v }))} options={[{ value: 'percentual_comissao', label: '% da comissão estimada' }, { value: 'valor_fixo', label: 'Valor fixo (R$)' }]} />
                  {form.multa_modo === 'percentual_comissao'
                    ? <div><Input label="Percentual (%)" value={form.multa_percentual} onChange={(v) => setForm((f) => ({ ...f, multa_percentual: v }))} type="number" /><p className="text-xs text-emerald-700 mt-1">Multa: <b>{brl(comissaoEstimada * Number(form.multa_percentual || 0) / 100)}</b></p></div>
                    : <Input label="Valor fixo (R$)" value={form.multa_valor_fixo} onChange={(v) => setForm((f) => ({ ...f, multa_valor_fixo: v }))} type="number" />}
                </div>
              )}
            </div>
            <label className="flex items-start gap-2 cursor-pointer"><input type="checkbox" checked={form.reembolso_despesas} onChange={(e) => setForm((f) => ({ ...f, reembolso_despesas: e.target.checked }))} className="w-4 h-4 mt-0.5 accent-emerald-700" /><span className="text-sm text-gray-700">Incluir reembolso de despesas de divulgação comprovadas em rescisão antecipada.</span></label>
            <div className="grid sm:grid-cols-3 gap-3 pt-2">
              <Input label="Cidade da assinatura" value={form.assinatura_cidade} onChange={(v) => setForm((f) => ({ ...f, assinatura_cidade: v }))} />
              <Input label="Data da assinatura" value={form.assinatura_data} onChange={(v) => setForm((f) => ({ ...f, assinatura_data: v }))} type="date" />
              <Input label="Foro (comarca)" value={form.foro_comarca} onChange={(v) => setForm((f) => ({ ...f, foro_comarca: v }))} />
            </div>
          </>
        )}

        {/* ETAPA 5 — REVISÃO */}
        {step === 4 && (
          <div className="space-y-3 text-sm">
            <div className="bg-gray-50 rounded-xl p-4 space-y-1">
              <p className="font-semibold text-gray-800">{form.proprietarios.length} proprietário(s) · soma {somaFracoes.toFixed(2)}%</p>
              {form.proprietarios.map((p, i) => (
                <p key={i}>• {p.nome || '—'} ({parseFracao(p.fracao_percentual)}%){exigeConjuge(p.estado_civil, p.regime_bens) ? ' + cônjuge' : ''}</p>
              ))}
              <p className="pt-2"><b>Imóvel:</b> {im.descricao_geral || '—'}</p>
              <p><b>Valor:</b> {brl(im.valor_anunciado)} · <b>Comissão:</b> {form.comissao_percentual}% · <b>Prazo:</b> {form.prazo_meses} meses</p>
            </div>
            {!fracoesOk && <p className="text-red-600">⚠ A soma das frações precisa ser 100% para enviar.</p>}
            <button onClick={enviar} disabled={enviando || !fracoesOk}
                    className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white ${(!enviando && fracoesOk) ? 'bg-emerald-700' : 'bg-gray-300 cursor-not-allowed'}`}>
              {enviando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Enviar para Assinatura (WhatsApp)
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-5">
        <button onClick={goPrev} disabled={step === 0} className="flex items-center gap-1 px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-40"><ChevronLeft className="w-4 h-4" /> Anterior</button>
        {step < ETAPAS.length - 1 && (
          <button onClick={goNext} className="flex items-center gap-1 px-5 py-2 rounded-lg bg-emerald-700 text-white text-sm font-semibold">Próximo <ChevronRight className="w-4 h-4" /></button>
        )}
      </div>
    </div>
  );
}
