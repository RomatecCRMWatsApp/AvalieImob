import React, { useState } from 'react';
import { uploadAPI } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import {
  TIPO_LOCACAO_OPTIONS,
  OBJETIVO_OPTIONS,
  GARANTIA_OPTIONS,
  IMOVEL_TIPO_OPTIONS,
  CONSERVACAO_OPTIONS,
  PADRAO_OPTIONS,
  fmtCurrency,
} from './locacaoHelpers';

// ─── Primitivos ───────────────────────────────────────────────────────────────
const Field = ({ label, children, className = '' }) => (
  <div className={`space-y-1.5 ${className}`}>
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    {children}
  </div>
);

const Input = ({ className = '', ...props }) => (
  <input
    className={`w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 ${className}`}
    {...props}
  />
);

const Textarea = ({ rows = 3, className = '', ...props }) => (
  <textarea
    rows={rows}
    className={`w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 resize-none ${className}`}
    {...props}
  />
);

const Select = ({ options, placeholder, className = '', ...props }) => (
  <select
    className={`w-full px-3 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:border-emerald-400 ${className}`}
    {...props}
  >
    {placeholder && <option value="">{placeholder}</option>}
    {options.map(o => (
      <option key={o.value} value={o.value}>{o.label}</option>
    ))}
  </select>
);

const SectionTitle = ({ children }) => (
  <h3 className="text-base font-semibold text-gray-900 border-b border-gray-100 pb-2 mb-4">{children}</h3>
);

const Grid = ({ cols = 2, children }) => (
  <div className={`grid grid-cols-1 ${cols === 2 ? 'md:grid-cols-2' : cols === 3 ? 'md:grid-cols-3' : ''} gap-4`}>
    {children}
  </div>
);

// ─── Step 1 — Solicitante ─────────────────────────────────────────────────────
export const StepSolicitante = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <SectionTitle>1. Identificação do Solicitante</SectionTitle>
      {form.numero_locacao && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-sm">
          <span className="text-blue-600 font-semibold">Número: </span>
          <span className="font-mono text-blue-900">{form.numero_locacao}</span>
        </div>
      )}
      <Grid cols={2}>
        <Field label="Nome / Razão Social" className="md:col-span-2">
          <Input value={form.solicitante_nome} onChange={e => set('solicitante_nome', e.target.value)} placeholder="Nome completo ou razão social" />
        </Field>
        <Field label="CPF / CNPJ">
          <Input value={form.solicitante_cpf} onChange={e => set('solicitante_cpf', e.target.value)} placeholder="000.000.000-00" />
        </Field>
        <Field label="Telefone">
          <Input value={form.solicitante_telefone} onChange={e => set('solicitante_telefone', e.target.value)} placeholder="(00) 00000-0000" />
        </Field>
        <Field label="E-mail" className="md:col-span-2">
          <Input type="email" value={form.solicitante_email} onChange={e => set('solicitante_email', e.target.value)} placeholder="email@exemplo.com" />
        </Field>
        <Field label="Endereço Completo" className="md:col-span-2">
          <Input value={form.solicitante_endereco} onChange={e => set('solicitante_endereco', e.target.value)} placeholder="Rua, número, complemento, cidade - UF" />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 2 — Objetivo ────────────────────────────────────────────────────────
export const StepObjetivo = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <SectionTitle>2. Objetivo da Avaliação</SectionTitle>
      <Grid cols={2}>
        <Field label="Finalidade">
          <Select
            value={form.objetivo}
            onChange={e => set('objetivo', e.target.value)}
            options={OBJETIVO_OPTIONS}
            placeholder="Selecione a finalidade"
          />
        </Field>
        <Field label="Tipo de Locação">
          <Select
            value={form.tipo_locacao}
            onChange={e => set('tipo_locacao', e.target.value)}
            options={TIPO_LOCACAO_OPTIONS}
          />
        </Field>
        {form.objetivo === 'outros' && (
          <Field label="Descreva o objetivo" className="md:col-span-2">
            <Textarea value={form.objetivo_outros} onChange={e => set('objetivo_outros', e.target.value)} placeholder="Descreva a finalidade..." />
          </Field>
        )}
        <Field label="Base Legal" className="md:col-span-2">
          <Textarea
            rows={2}
            value={form.base_legal_locacao}
            onChange={e => set('base_legal_locacao', e.target.value)}
            placeholder="Lei 8.245/1991..."
          />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 3 — Imóvel ─────────────────────────────────────────────────────────
export const StepImovel = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <SectionTitle>3. Identificação do Imóvel</SectionTitle>
      <Grid cols={2}>
        <Field label="Endereço" className="md:col-span-2">
          <Input value={form.imovel_endereco} onChange={e => set('imovel_endereco', e.target.value)} placeholder="Rua, número, complemento" />
        </Field>
        <Field label="Bairro">
          <Input value={form.imovel_bairro} onChange={e => set('imovel_bairro', e.target.value)} />
        </Field>
        <Field label="Cidade">
          <Input value={form.imovel_cidade} onChange={e => set('imovel_cidade', e.target.value)} />
        </Field>
        <Field label="Estado">
          <Input value={form.imovel_estado} onChange={e => set('imovel_estado', e.target.value)} placeholder="UF" maxLength={2} />
        </Field>
        <Field label="CEP">
          <Input value={form.imovel_cep} onChange={e => set('imovel_cep', e.target.value)} placeholder="00000-000" />
        </Field>
        <Field label="Matrícula">
          <Input value={form.imovel_matricula} onChange={e => set('imovel_matricula', e.target.value)} />
        </Field>
        <Field label="Cartório de Registro">
          <Input value={form.imovel_cartorio} onChange={e => set('imovel_cartorio', e.target.value)} />
        </Field>
        <Field label="Tipo do Imóvel" className="md:col-span-2">
          <Select
            value={form.imovel_tipo}
            onChange={e => set('imovel_tipo', e.target.value)}
            options={IMOVEL_TIPO_OPTIONS}
            placeholder="Selecione..."
          />
        </Field>
        <Field label="Área do Terreno (m²)">
          <Input type="number" value={form.imovel_area_terreno} onChange={e => set('imovel_area_terreno', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Área Construída (m²)">
          <Input type="number" value={form.imovel_area_construida} onChange={e => set('imovel_area_construida', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Idade Aparente (anos)">
          <Input type="number" value={form.imovel_idade} onChange={e => set('imovel_idade', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Nº de Quartos">
          <Input type="number" min={0} value={form.imovel_num_quartos} onChange={e => set('imovel_num_quartos', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Estado de Conservação">
          <Select value={form.imovel_estado_conservacao} onChange={e => set('imovel_estado_conservacao', e.target.value)} options={CONSERVACAO_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Padrão de Acabamento">
          <Select value={form.imovel_padrao_acabamento} onChange={e => set('imovel_padrao_acabamento', e.target.value)} options={PADRAO_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Nº de Banheiros">
          <Input type="number" min={0} value={form.imovel_num_banheiros} onChange={e => set('imovel_num_banheiros', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Vagas de Garagem">
          <Input type="number" min={0} value={form.imovel_num_vagas} onChange={e => set('imovel_num_vagas', parseInt(e.target.value) || 0)} />
        </Field>
        <Field label="Piscina" className="flex items-center gap-2 pt-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.imovel_piscina} onChange={e => set('imovel_piscina', e.target.checked)} className="w-4 h-4 accent-emerald-700" />
            <span className="text-sm text-gray-700">Possui piscina</span>
          </label>
        </Field>
        <Field label="Características Adicionais" className="md:col-span-2">
          <Textarea value={form.imovel_caracteristicas} onChange={e => set('imovel_caracteristicas', e.target.value)} placeholder="Churrasqueira, área de lazer, varanda..." />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 4 — Região ──────────────────────────────────────────────────────────
export const StepRegiao = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <SectionTitle>4. Caracterização da Região</SectionTitle>
      <Grid cols={2}>
        <Field label="Infraestrutura Urbana" className="md:col-span-2">
          <Textarea value={form.regiao_infraestrutura} onChange={e => set('regiao_infraestrutura', e.target.value)} placeholder="Pavimentação, iluminação, saneamento..." />
        </Field>
        <Field label="Serviços Públicos" className="md:col-span-2">
          <Textarea value={form.regiao_servicos_publicos} onChange={e => set('regiao_servicos_publicos', e.target.value)} placeholder="Transporte, saúde, educação..." />
        </Field>
        <Field label="Uso Predominante">
          <Input value={form.regiao_uso_predominante} onChange={e => set('regiao_uso_predominante', e.target.value)} placeholder="Residencial, Comercial, Misto..." />
        </Field>
        <Field label="Padrão Construtivo da Região">
          <Input value={form.regiao_padrao_construtivo} onChange={e => set('regiao_padrao_construtivo', e.target.value)} placeholder="Alto, Médio, Simples..." />
        </Field>
        <Field label="Tendência de Mercado">
          <Input value={form.regiao_tendencia_mercado} onChange={e => set('regiao_tendencia_mercado', e.target.value)} placeholder="Valorização, estabilidade, desvalorização..." />
        </Field>
        <Field label="Zoneamento">
          <Input value={form.zoneamento} onChange={e => set('zoneamento', e.target.value)} placeholder="ZR1, ZC2..." />
        </Field>
        <Field label="Observações da Região" className="md:col-span-2">
          <Textarea value={form.regiao_observacoes} onChange={e => set('regiao_observacoes', e.target.value)} rows={4} />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 5 — Pesquisa de Mercado ─────────────────────────────────────────────
export const StepPesquisaMercado = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const samples = form.market_samples || [];

  const addSample = () => {
    setForm(f => ({
      ...f,
      market_samples: [...(f.market_samples || []), {
        address: '', neighborhood: '', area: 0, valor_aluguel: 0,
        valor_por_m2: 0, source: '', collection_date: '', contact_phone: '', notes: '',
        tipo_amostra: 'oferta'
      }]
    }));
  };

  const removeSample = (idx) => {
    setForm(f => ({ ...f, market_samples: f.market_samples.filter((_, i) => i !== idx) }));
  };

  const updateSample = (idx, field, value) => {
    setForm(f => {
      const arr = [...f.market_samples];
      arr[idx] = { ...arr[idx], [field]: value };
      if (field === 'valor_aluguel' || field === 'area') {
        const aluguel = parseFloat(field === 'valor_aluguel' ? value : arr[idx].valor_aluguel) || 0;
        const area = parseFloat(field === 'area' ? value : arr[idx].area) || 1;
        arr[idx].valor_por_m2 = area > 0 ? parseFloat((aluguel / area).toFixed(2)) : 0;
      }
      return { ...f, market_samples: arr };
    });
  };

  return (
    <div className="space-y-6">
      <SectionTitle>5. Pesquisa de Mercado</SectionTitle>

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">{samples.length} amostra(s) cadastrada(s)</p>
        <button
          onClick={addSample}
          className="text-sm text-emerald-700 border border-emerald-300 rounded-xl px-3 py-1.5 hover:bg-emerald-50 transition"
        >
          + Adicionar Amostra
        </button>
      </div>

      {samples.map((s, idx) => (
        <div key={idx} className="border border-gray-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-700">Amostra {idx + 1}</span>
            <button onClick={() => removeSample(idx)} className="text-red-400 hover:text-red-600 text-xs transition">Remover</button>
          </div>
          <Grid cols={2}>
            <Field label="Endereço" className="md:col-span-2">
              <Input value={s.address} onChange={e => updateSample(idx, 'address', e.target.value)} />
            </Field>
            <Field label="Bairro">
              <Input value={s.neighborhood} onChange={e => updateSample(idx, 'neighborhood', e.target.value)} />
            </Field>
            <Field label="Área (m²)">
              <Input type="number" value={s.area} onChange={e => updateSample(idx, 'area', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Valor do Aluguel (R$)">
              <Input type="number" value={s.valor_aluguel} onChange={e => updateSample(idx, 'valor_aluguel', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="R$/m²">
              <Input readOnly value={s.valor_por_m2 || 0} className="bg-gray-50" />
            </Field>
            <Field label="Fonte / Anúncio">
              <Input value={s.source} onChange={e => updateSample(idx, 'source', e.target.value)} placeholder="Zap, VivaReal, Direto..." />
            </Field>
            <Field label="Data de Coleta">
              <Input type="date" value={s.collection_date} onChange={e => updateSample(idx, 'collection_date', e.target.value)} />
            </Field>
            <Field label="Contato">
              <Input value={s.contact_phone} onChange={e => updateSample(idx, 'contact_phone', e.target.value)} />
            </Field>
            <Field label="Observações" className="md:col-span-2">
              <Textarea rows={2} value={s.notes} onChange={e => updateSample(idx, 'notes', e.target.value)} />
            </Field>
            <Field label="Tipo da Amostra" className="md:col-span-2">
              <div className="space-y-1">
                <select
                  value={s.tipo_amostra || 'oferta'}
                  onChange={e => updateSample(idx, 'tipo_amostra', e.target.value)}
                  className="w-full text-sm rounded-md border border-gray-200 px-2 py-1.5 focus:outline-none focus:border-emerald-400"
                >
                  <option value="oferta">Oferta de Mercado</option>
                  <option value="consolidada">Consolidada / Comercializada</option>
                </select>
                {s.tipo_amostra === 'consolidada' ? (
                  <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-emerald-100 text-emerald-800 border-emerald-300">
                    Consolidada
                  </span>
                ) : (
                  <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-100 text-amber-800 border-amber-300">
                    Oferta
                  </span>
                )}
              </div>
            </Field>
          </Grid>
        </div>
      ))}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-1">
        Amostras consolidadas (locacao efetivada) tem maior peso na avaliacao conforme NBR 14653.
      </p>

      <Field label="Análise do Mercado">
        <Textarea rows={5} value={form.market_analysis} onChange={e => set('market_analysis', e.target.value)} placeholder="Descreva o comportamento do mercado, oferta e demanda, sazonalidade..." />
      </Field>
    </div>
  );
};

// ─── Step 6 — Cálculos ───────────────────────────────────────────────────────
export const StepCalculos = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const calcularEstatisticas = () => {
    const samples = form.market_samples || [];
    const valores = samples.map(s => s.valor_por_m2).filter(v => v > 0);
    if (valores.length === 0) return;
    const media = valores.reduce((a, b) => a + b, 0) / valores.length;
    const sorted = [...valores].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    const mediana = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    const desvio = Math.sqrt(valores.reduce((a, b) => a + Math.pow(b - media, 2), 0) / valores.length);
    const cv = (desvio / media) * 100;
    setForm(f => ({
      ...f,
      calc_media: parseFloat(media.toFixed(2)),
      calc_mediana: parseFloat(mediana.toFixed(2)),
      calc_desvio_padrao: parseFloat(desvio.toFixed(2)),
      calc_coef_variacao: parseFloat(cv.toFixed(2)),
    }));
  };

  return (
    <div className="space-y-6">
      <SectionTitle>6. Cálculos e Metodologia</SectionTitle>
      <Field label="Metodologia Aplicada">
        <Input value={form.methodology} onChange={e => set('methodology', e.target.value)} />
      </Field>
      <Field label="Justificativa da Metodologia">
        <Textarea value={form.methodology_justification} onChange={e => set('methodology_justification', e.target.value)} rows={3} />
      </Field>

      <div className="flex justify-end">
        <button
          onClick={calcularEstatisticas}
          className="text-sm bg-emerald-900 text-white px-4 py-2 rounded-xl hover:bg-emerald-800 transition"
        >
          Calcular Estatísticas das Amostras
        </button>
      </div>

      <Grid cols={2}>
        <Field label="Média R$/m²">
          <Input type="number" value={form.calc_media} onChange={e => set('calc_media', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Mediana R$/m²">
          <Input type="number" value={form.calc_mediana} onChange={e => set('calc_mediana', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Desvio Padrão">
          <Input type="number" value={form.calc_desvio_padrao} onChange={e => set('calc_desvio_padrao', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Coeficiente de Variação (%)">
          <Input type="number" value={form.calc_coef_variacao} onChange={e => set('calc_coef_variacao', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Grau de Fundamentação (NBR 14653)">
          <Select
            value={form.calc_grau_fundamentacao}
            onChange={e => set('calc_grau_fundamentacao', e.target.value)}
            options={[{ value: 'I', label: 'Grau I' }, { value: 'II', label: 'Grau II' }, { value: 'III', label: 'Grau III' }]}
            placeholder="Selecione..."
          />
        </Field>
        <Field label="Fatores de Homogeneização">
          <Input value={form.calc_fatores_homogeneizacao} onChange={e => set('calc_fatores_homogeneizacao', e.target.value)} placeholder="Fator localização, padrão, área..." />
        </Field>
        <Field label="Observações dos Cálculos" className="md:col-span-2">
          <Textarea rows={3} value={form.calc_observacoes} onChange={e => set('calc_observacoes', e.target.value)} />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 7 — Garantia ────────────────────────────────────────────────────────
export const StepGarantia = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <SectionTitle>7. Condições da Locação e Garantia</SectionTitle>
      <Grid cols={2}>
        <Field label="Garantia Locatícia">
          <Select value={form.garantia_locacao} onChange={e => set('garantia_locacao', e.target.value)} options={GARANTIA_OPTIONS} placeholder="Selecione..." />
        </Field>
        <Field label="Prazo Sugerido da Locação">
          <Input value={form.prazo_locacao} onChange={e => set('prazo_locacao', e.target.value)} placeholder="Ex: 30 meses" />
        </Field>
        <Field label="Fator de Locação (%)">
          <Input type="number" step="0.01" value={form.fator_locacao ?? ''} onChange={e => set('fator_locacao', e.target.value ? parseFloat(e.target.value) : null)} placeholder="Ex: 0.50" />
        </Field>
        <Field label="Grau de Precisão (NBR 14653)">
          <Select
            value={form.grau_precisao}
            onChange={e => set('grau_precisao', e.target.value)}
            options={[{ value: 'I', label: 'Grau I — 15%' }, { value: 'II', label: 'Grau II — 11,25%' }, { value: 'III', label: 'Grau III — 7,5%' }]}
          />
        </Field>
        <Field label="Campo Arbítrio — Mínimo (R$)">
          <Input type="number" value={form.campo_arbitrio_min} onChange={e => set('campo_arbitrio_min', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Campo Arbítrio — Máximo (R$)">
          <Input type="number" value={form.campo_arbitrio_max} onChange={e => set('campo_arbitrio_max', parseFloat(e.target.value) || 0)} />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 8 — Responsável Técnico ─────────────────────────────────────────────
export const StepResponsavel = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <div className="space-y-6">
      <SectionTitle>8. Responsável Técnico</SectionTitle>
      <Grid cols={2}>
        <Field label="Nome Completo" className="md:col-span-2">
          <Input value={form.responsavel_nome} onChange={e => set('responsavel_nome', e.target.value)} />
        </Field>
        <Field label="Tipo de Profissional">
          <Select
            value={form.tipo_profissional}
            onChange={e => set('tipo_profissional', e.target.value)}
            options={[
              { value: 'corretor', label: 'Corretor de Imóveis' },
              { value: 'engenheiro', label: 'Engenheiro Civil' },
              { value: 'arquiteto', label: 'Arquiteto e Urbanista' },
              { value: 'agrimensor', label: 'Agrimensor' },
              { value: 'perito', label: 'Perito Judicial' },
            ]}
          />
        </Field>
        <Field label="CRECI">
          <Input value={form.responsavel_creci} onChange={e => set('responsavel_creci', e.target.value)} placeholder="CRECI/SP 123456" />
        </Field>
        <Field label="CNAI">
          <Input value={form.responsavel_cnai} onChange={e => set('responsavel_cnai', e.target.value)} placeholder="CNAI 12345" />
        </Field>
        <Field label="Registro Profissional (CREA/CAU)">
          <Input value={form.registro_profissional} onChange={e => set('registro_profissional', e.target.value)} />
        </Field>
        <Field label="ART / RRT (número)">
          <Input value={form.art_rrt_numero} onChange={e => set('art_rrt_numero', e.target.value)} />
        </Field>
        <Field label="Prazo de Validade (meses)">
          <Input type="number" value={form.prazo_validade_meses} onChange={e => set('prazo_validade_meses', parseInt(e.target.value) || 6)} />
        </Field>
        <Field label="Cidade de Emissão">
          <Input value={form.conclusion_city} onChange={e => set('conclusion_city', e.target.value)} />
        </Field>
        <Field label="Data de Emissão">
          <Input type="date" value={form.conclusion_date} onChange={e => set('conclusion_date', e.target.value)} />
        </Field>
      </Grid>
    </div>
  );
};

// ─── Step 9 — Fotos ───────────────────────────────────────────────────────────
export const StepFotos = ({ form, setForm }) => {
  const { toast } = useToast();
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e, field) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    try {
      const urls = await Promise.all(files.map(f => uploadAPI.uploadImage(f).then(r => r.url || r.image_url || r.id)));
      setForm(prev => ({ ...prev, [field]: [...(prev[field] || []), ...urls] }));
    } catch {
      toast({ title: 'Erro ao fazer upload', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const removePhoto = (field, idx) => {
    setForm(prev => ({ ...prev, [field]: prev[field].filter((_, i) => i !== idx) }));
  };

  const PhotoGrid = ({ field, label }) => (
    <Field label={label}>
      <div className="flex flex-wrap gap-2 mb-2">
        {(form[field] || []).map((url, i) => (
          <div key={i} className="relative w-20 h-20 rounded-xl overflow-hidden border border-gray-200">
            <img src={url.startsWith('http') ? url : uploadAPI.getImageUrl(url)} alt="" className="w-full h-full object-cover" />
            <button
              onClick={() => removePhoto(field, i)}
              className="absolute top-0 right-0 bg-red-500 text-white text-xs w-5 h-5 flex items-center justify-center rounded-bl-xl"
            >×</button>
          </div>
        ))}
        <label className="w-20 h-20 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-emerald-400 transition text-gray-400 text-xs text-center">
          <span className="text-2xl leading-none">+</span>
          <input type="file" multiple accept="image/*" className="hidden" onChange={e => handleUpload(e, field)} />
        </label>
      </div>
    </Field>
  );

  return (
    <div className="space-y-6">
      <SectionTitle>9. Documentação Fotográfica</SectionTitle>
      {uploading && <p className="text-sm text-emerald-700 animate-pulse">Enviando imagens...</p>}
      <PhotoGrid field="fotos_imovel" label="Fotos do Imóvel" />
      <PhotoGrid field="fotos_documentos" label="Documentos Digitalizados" />
      <Field label="Documentos Analisados">
        <Textarea
          rows={3}
          value={(form.documentos_analisados || []).join('\n')}
          onChange={e => setForm(f => ({ ...f, documentos_analisados: e.target.value.split('\n').filter(Boolean) }))}
          placeholder="Um documento por linha&#10;Ex: Matrícula do Imóvel&#10;IPTU 2025"
        />
      </Field>
    </div>
  );
};

// ─── Step 10 — Resultado ──────────────────────────────────────────────────────
export const StepResultado = ({ form, setForm }) => {
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div className="space-y-6">
      <SectionTitle>10. Resultado — Valor de Locação</SectionTitle>

      {form.valor_locacao_estimado && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <p className="text-xs text-emerald-600 uppercase tracking-wider font-semibold mb-1">Valor Mensal Estimado</p>
          <p className="text-3xl font-bold text-emerald-900">{fmtCurrency(form.valor_locacao_estimado)}<span className="text-base font-medium text-emerald-600">/mês</span></p>
          {form.valor_locacao_por_extenso && <p className="text-xs text-emerald-700 mt-1">({form.valor_locacao_por_extenso})</p>}
        </div>
      )}

      <Grid cols={3}>
        <Field label="Valor Mensal Estimado (R$)" className="md:col-span-3">
          <Input
            type="number"
            value={form.valor_locacao_estimado ?? ''}
            onChange={e => set('valor_locacao_estimado', e.target.value ? parseFloat(e.target.value) : null)}
            placeholder="0,00"
            className="text-lg font-semibold"
          />
        </Field>
        <Field label="Valor Mínimo (R$)">
          <Input type="number" value={form.valor_locacao_minimo ?? ''} onChange={e => set('valor_locacao_minimo', e.target.value ? parseFloat(e.target.value) : null)} />
        </Field>
        <Field label="Valor Máximo (R$)">
          <Input type="number" value={form.valor_locacao_maximo ?? ''} onChange={e => set('valor_locacao_maximo', e.target.value ? parseFloat(e.target.value) : null)} />
        </Field>
        <Field label="Valor por Extenso" className="md:col-span-3">
          <Input value={form.valor_locacao_por_extenso} onChange={e => set('valor_locacao_por_extenso', e.target.value)} placeholder="Três mil reais por mês" />
        </Field>
        <Field label="Data de Referência">
          <Input type="date" value={form.resultado_data_referencia} onChange={e => set('resultado_data_referencia', e.target.value)} />
        </Field>
        <Field label="Prazo de Validade do Parecer" className="md:col-span-2">
          <Input value={form.resultado_prazo_validade} onChange={e => set('resultado_prazo_validade', e.target.value)} placeholder="6 meses a partir da data de emissão" />
        </Field>
      </Grid>

      <Field label="Conclusão / Parecer Técnico">
        <Textarea rows={5} value={form.conclusion_text} onChange={e => set('conclusion_text', e.target.value)} placeholder="Com base na pesquisa de mercado realizada, conclui-se que o valor de locação do imóvel avaliado é..." />
      </Field>

      <Grid cols={2}>
        <Field label="Pressupostos">
          <Textarea rows={3} value={form.consideracoes_pressupostos} onChange={e => set('consideracoes_pressupostos', e.target.value)} placeholder="Este parecer foi elaborado com base em..." />
        </Field>
        <Field label="Ressalvas e Limitações">
          <Textarea rows={3} value={form.consideracoes_ressalvas} onChange={e => set('consideracoes_ressalvas', e.target.value)} placeholder="Este parecer não considera..." />
        </Field>
      </Grid>

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
        <p className="font-semibold mb-1">Base Legal</p>
        <p>{form.base_legal_locacao || 'Lei 8.245/1991 — Art. 565 a 578 do Código Civil'}</p>
        <p className="mt-1 text-blue-600">NBR 14653-1 e 14653-2 — ABNT</p>
      </div>

      <div className="flex items-center gap-3">
        <Field label="Status do Parecer" className="flex-1">
          <Select
            value={form.status}
            onChange={e => set('status', e.target.value)}
            options={[
              { value: 'Rascunho', label: 'Rascunho' },
              { value: 'Em revisão', label: 'Em revisão' },
              { value: 'Emitido', label: 'Emitido' },
            ]}
          />
        </Field>
      </div>
    </div>
  );
};
