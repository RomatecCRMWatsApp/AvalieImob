// @module ptam/steps/StepAmostras — Step 6: Amostras de Mercado (cards dinâmicos por tipo de imóvel)
import React, { useState, useMemo } from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Button } from '../../../ui/button';
import { Plus, Trash2, Search, AlertTriangle } from 'lucide-react';
import { SectionHeader, AiButton } from '../shared/primitives';
import { emptyMarketSample, computeStatsNBR } from '../ptamHelpers';
import ImageUploader from '../ImageUploader';
import { BuscaAmostras } from '../BuscaAmostras';
import BancoAmostrasPicker from '../BancoAmostrasPicker';
import { Database } from 'lucide-react';
import RichField, { paraEditorHtml } from '../../../ui/RichField';
import RichTextEditor from '../../../ui/RichTextEditor';
import { aiAPI } from '../../../../lib/api';
import { useToast } from '../../../../hooks/use-toast';
import {
  amostraCategoria,
  isRuralImovel,
  valorUnitario,
  unidadeValorLabel,
  conversoesArea,
} from '../shared/amostraCategoria';

const fmtUnit = (n) => Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 });

const FieldLabel = ({ children }) => (
  <label className="block text-[11px] font-medium text-gray-500 mb-1">{children}</label>
);

// Campo de texto/numérico rotulado, no padrão visual do step.
const Labeled = ({ label, children }) => (
  <div>
    <FieldLabel>{label}</FieldLabel>
    {children}
  </div>
);

// Campo "select" estilizado igual ao seletor de tipo de amostra.
const SelectField = ({ label, value, onChange, options }) => (
  <Labeled label={label}>
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      className="w-full h-9 rounded-md border border-gray-200 px-2 text-sm bg-white focus:outline-none focus:border-emerald-400"
    >
      <option value="">—</option>
      {options.map((o) => {
        const val = typeof o === 'string' ? o : o.value;
        const lbl = typeof o === 'string' ? o : o.label;
        return <option key={val} value={val}>{lbl}</option>;
      })}
    </select>
  </Labeled>
);

// Caixa de valor calculado (somente leitura) com destaque emerald.
const ComputedBox = ({ label, children }) => (
  <Labeled label={label}>
    <div className="h-9 flex items-center px-2 rounded-md border border-emerald-300 bg-emerald-50 text-sm font-medium text-emerald-800">
      {children}
    </div>
  </Labeled>
);

const numHandler = (onChange) => (e) => onChange(parseFloat(e.target.value) || 0);
const intHandler = (onChange) => (e) => onChange(parseInt(e.target.value, 10) || 0);

// ── Campos extras por categoria de imóvel ──────────────────────────────────
const ExtraFields = ({ categoria, s, set }) => {
  switch (categoria) {
    case 'terreno_urbano':
      return (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Labeled label="Testada (m)">
              <Input type="number" min={0} step="any" value={s.testada_m || ''} onChange={numHandler((v) => set('testada_m', v))} className="h-9" placeholder="0" />
            </Labeled>
            <Labeled label="Zoneamento">
              <Input value={s.zoneamento || ''} onChange={(e) => set('zoneamento', e.target.value)} className="h-9" placeholder="ZR-1, ZC..." />
            </Labeled>
            <Labeled label="Uso permitido">
              <Input value={s.uso_permitido || ''} onChange={(e) => set('uso_permitido', e.target.value)} className="h-9" placeholder="Residencial, misto..." />
            </Labeled>
          </div>
        </>
      );

    case 'casa_apto':
      return (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Labeled label="Área construída (m²)">
              <Input type="number" min={0} step="any" value={s.area_construida_m2 || ''} onChange={numHandler((v) => set('area_construida_m2', v))} className="h-9" placeholder="0" />
            </Labeled>
            <Labeled label="Área do terreno (m²)">
              <Input type="number" min={0} step="any" value={s.area_terreno_m2 || ''} onChange={numHandler((v) => set('area_terreno_m2', v))} className="h-9" placeholder="0" />
            </Labeled>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <SelectField label="Padrão" value={s.padrao} onChange={(v) => set('padrao', v)} options={[{ value: 'baixo', label: 'Baixo' }, { value: 'normal', label: 'Normal' }, { value: 'alto', label: 'Alto' }, { value: 'luxo', label: 'Luxo' }]} />
            <SelectField label="Conservação" value={s.conservacao} onChange={(v) => set('conservacao', v)} options={[{ value: 'novo', label: 'Novo' }, { value: 'bom', label: 'Bom' }, { value: 'regular', label: 'Regular' }, { value: 'ruim', label: 'Ruim' }]} />
            <Labeled label="Idade (anos)">
              <Input type="number" min={0} value={s.idade_anos || ''} onChange={intHandler((v) => set('idade_anos', v))} className="h-9" placeholder="0" />
            </Labeled>
          </div>
          {/* Ambientes (quantidade) — só vão ao laudo se > 0 */}
          <div className="mt-1">
            <span className="block text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">
              Ambientes (quantidade — só vai ao laudo se maior que 0)
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                ['sala_estar', 'Sala de estar'],
                ['sala_jantar', 'Sala de jantar/copa'],
                ['cozinha', 'Cozinha'],
                ['quarto_social', 'Quarto social'],
                ['suite_simples', 'Suíte simples'],
                ['suite_master', 'Suíte master'],
                ['banheiro_social', 'Banheiro social'],
                ['lavabo', 'Lavabo'],
                ['area_servico', 'Área de serviço'],
                ['varanda', 'Varanda/sacada'],
                ['varanda_gourmet', 'Varanda gourmet'],
                ['escritorio', 'Escritório'],
                ['despensa', 'Despensa'],
                ['piscina', 'Piscina'],
                ['vagas', 'Garagem'],
              ].map(([k, lbl]) => (
                <Labeled key={k} label={lbl}>
                  <Input type="number" min={0} value={s[k] || ''} onChange={intHandler((v) => set(k, v))} className="h-9" placeholder="0" />
                </Labeled>
              ))}
            </div>
          </div>
        </>
      );

    case 'galpao_comercial':
      return (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Labeled label="Área construída (m²)">
              <Input type="number" min={0} step="any" value={s.area_construida_m2 || ''} onChange={numHandler((v) => set('area_construida_m2', v))} className="h-9" placeholder="0" />
            </Labeled>
            <Labeled label="Área do terreno (m²)">
              <Input type="number" min={0} step="any" value={s.area_terreno_m2 || ''} onChange={numHandler((v) => set('area_terreno_m2', v))} className="h-9" placeholder="0" />
            </Labeled>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Labeled label="Pé-direito (m)">
              <Input type="number" min={0} step="0.1" value={s.pe_direito_m || ''} onChange={numHandler((v) => set('pe_direito_m', v))} className="h-9" placeholder="0" />
            </Labeled>
            <Labeled label="Vão livre (m)">
              <Input type="number" min={0} step="0.1" value={s.vao_livre_m || ''} onChange={numHandler((v) => set('vao_livre_m', v))} className="h-9" placeholder="0" />
            </Labeled>
            <Labeled label="Docas">
              <Input type="number" min={0} value={s.docas || ''} onChange={intHandler((v) => set('docas', v))} className="h-9" placeholder="0" />
            </Labeled>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <SelectField label="Padrão" value={s.padrao} onChange={(v) => set('padrao', v)} options={[{ value: 'baixo', label: 'Baixo' }, { value: 'normal', label: 'Normal' }, { value: 'alto', label: 'Alto' }]} />
            <SelectField label="Conservação" value={s.conservacao} onChange={(v) => set('conservacao', v)} options={[{ value: 'novo', label: 'Novo' }, { value: 'bom', label: 'Bom' }, { value: 'regular', label: 'Regular' }, { value: 'ruim', label: 'Ruim' }]} />
          </div>
        </>
      );

    case 'terreno_rural':
    case 'fazenda_sitio':
      return (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <SelectField label="Topografia" value={s.topografia} onChange={(v) => set('topografia', v)} options={['Plano', 'Suave ondulado', 'Ondulado', 'Forte ondulado', 'Montanhoso']} />
            <SelectField label="Solo" value={s.solo} onChange={(v) => set('solo', v)} options={['Argiloso', 'Arenoso', 'Misto', 'Latossolo', 'Rochoso']} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <SelectField label="Recursos hídricos" value={s.recursos_hidricos} onChange={(v) => set('recursos_hidricos', v)} options={['Sem', 'Rio / córrego', 'Lagoa', 'Irrigação / pivô']} />
            <SelectField label="Vegetação" value={s.vegetacao} onChange={(v) => set('vegetacao', v)} options={['Pastagem', 'Lavoura', 'Cerrado', 'Mata']} />
          </div>
          {categoria === 'fazenda_sitio' && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <SelectField label="Atividade principal" value={s.atividade} onChange={(v) => set('atividade', v)} options={['Pecuária', 'Lavoura anual', 'Lavoura perene', 'Mista', 'Reflorestamento']} />
                <Labeled label="Lotação (UA/ha)">
                  <Input type="number" min={0} step="0.1" value={s.lotacao_ua_ha || ''} onChange={numHandler((v) => set('lotacao_ua_ha', v))} className="h-9" placeholder="0" />
                </Labeled>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <SelectField label="Benfeitorias" value={s.benfeitorias} onChange={(v) => set('benfeitorias', v)} options={['Sem', 'Simples', 'Médio', 'Completo']} />
                <SelectField label="Sede / casa" value={s.sede} onChange={(v) => set('sede', v)} options={['Não', 'Simples', 'Boa']} />
              </div>
            </>
          )}
        </>
      );

    default:
      return null;
  }
};

const ExtraSection = ({ categoria, s, set }) => {
  if (categoria === 'outros' || !categoria) return null;
  const titulo = {
    terreno_urbano: 'Dimensões e uso',
    casa_apto: 'Características',
    galpao_comercial: 'Especificações técnicas',
    terreno_rural: 'Características rurais',
    fazenda_sitio: 'Características rurais',
  }[categoria];
  const rural = categoria === 'terreno_rural' || categoria === 'fazenda_sitio';
  return (
    <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
      <span className={`text-[10px] font-semibold uppercase tracking-wide ${rural ? 'text-emerald-700' : 'text-gray-400'}`}>
        {titulo}
      </span>
      <ExtraFields categoria={categoria} s={s} set={set} />
    </div>
  );
};

const MarketSampleCard = ({ s, onChange, onRemove, idx, isSaneada, tipoImovel }) => {
  const rural = isRuralImovel(tipoImovel);
  const categoria = amostraCategoria(tipoImovel);
  const conv = conversoesArea(s.area);
  const vUnit = valorUnitario(s.area, s.value, rural);
  const vUnitLabel = unidadeValorLabel(rural);

  // set genérico que também mantém value_per_sqm (R$/m²) para o computeStatsNBR.
  const set = (field, raw) => {
    const next = { ...s, [field]: raw };
    if (field === 'area' || field === 'value') {
      const area = Number(next.area || 0);
      const value = Number(next.value || 0);
      next.value_per_sqm = area > 0 ? Math.round((value / area) * 100) / 100 : 0;
    }
    onChange(next);
  };
  const setNum = (field) => (e) => set(field, Number(e.target.value));

  // Gera um memorial descritivo da amostra a partir dos campos preenchidos.
  const { toast } = useToast();
  const [aiBusy, setAiBusy] = useState(false);
  const gerarMemorial = async () => {
    const ptbr = (n) => Number(n || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 });
    const linhas = [];
    const push = (lbl, v) => { if (v !== undefined && v !== null && v !== '' && v !== 0) linhas.push(`${lbl}: ${v}`); };
    push('Tipo de imóvel', tipoImovel);
    push('Endereço', s.address);
    push('Bairro', s.neighborhood);
    push('Município/UF', [s.municipio, s.uf].filter(Boolean).join('/'));
    push('Área', s.area ? `${ptbr(s.area)} m²` : '');
    push('Valor', s.value ? `R$ ${ptbr(s.value)}` : '');
    push('Situação', s.tipo_amostra === 'consolidada' ? 'venda consolidada/comercializada' : 'oferta de mercado');
    if (categoria === 'terreno_urbano') {
      push('Testada', s.testada_m ? `${ptbr(s.testada_m)} m` : '');
      push('Zoneamento', s.zoneamento);
      push('Uso permitido', s.uso_permitido);
    } else if (categoria === 'casa_apto') {
      push('Área construída', s.area_construida_m2 ? `${ptbr(s.area_construida_m2)} m²` : '');
      push('Área do terreno', s.area_terreno_m2 ? `${ptbr(s.area_terreno_m2)} m²` : '');
      push('Padrão construtivo', s.padrao);
      push('Estado de conservação', s.conservacao);
      push('Idade', s.idade_anos ? `${s.idade_anos} anos` : '');
      const AMB = [
        ['sala_estar', 'sala de estar'], ['sala_jantar', 'sala de jantar/copa'], ['cozinha', 'cozinha'],
        ['quarto_social', 'quarto'], ['suite_simples', 'suíte'], ['suite_master', 'suíte master'],
        ['banheiro_social', 'banheiro'], ['lavabo', 'lavabo'], ['area_servico', 'área de serviço'],
        ['varanda', 'varanda/sacada'], ['varanda_gourmet', 'varanda gourmet'], ['escritorio', 'escritório'],
        ['despensa', 'despensa'], ['piscina', 'piscina'], ['vagas', 'vaga de garagem'],
      ];
      const comodos = AMB.filter(([k]) => Number(s[k] || 0) > 0).map(([k, l]) => `${s[k]} ${l}`);
      if (comodos.length) push('Cômodos', comodos.join(', '));
    } else if (categoria === 'galpao_comercial') {
      push('Área construída', s.area_construida_m2 ? `${ptbr(s.area_construida_m2)} m²` : '');
      push('Pé-direito', s.pe_direito_m ? `${ptbr(s.pe_direito_m)} m` : '');
      push('Vão livre', s.vao_livre_m ? `${ptbr(s.vao_livre_m)} m` : '');
      push('Docas', s.docas);
      push('Padrão', s.padrao);
      push('Conservação', s.conservacao);
    } else if (categoria === 'terreno_rural' || categoria === 'fazenda_sitio') {
      push('Topografia', s.topografia);
      push('Solo', s.solo);
      push('Recursos hídricos', s.recursos_hidricos);
      push('Vegetação', s.vegetacao);
      push('Atividade principal', s.atividade);
      push('Benfeitorias', s.benfeitorias);
    }
    const prompt =
      'Redija um MEMORIAL DESCRITIVO conciso e técnico (2 a 4 frases, português-BR formal, ' +
      'no espírito da ABNT NBR 14653) de uma amostra de mercado imobiliário, a partir dos dados abaixo. ' +
      'Quando houver cômodos, descreva-os de forma natural. Não invente dados que não constam. ' +
      'Retorne APENAS o texto, sem títulos, rótulos ou explicações.\n\nDados da amostra:\n' +
      (linhas.join('\n') || '(poucos dados — gere uma descrição genérica adequada ao tipo do imóvel)');
    setAiBusy(true);
    try {
      const res = await aiAPI.chat(`amostra_memorial_${Date.now()}`, prompt);
      const texto = (res?.reply || '').trim();
      if (texto) set('notes', texto);
      else toast({ title: 'A IA não retornou texto', variant: 'destructive' });
    } catch (e) {
      toast({ title: 'Erro na IA', description: e.response?.data?.detail || 'Tente novamente', variant: 'destructive' });
    } finally {
      setAiBusy(false);
    }
  };

  const tipoLabel = s.tipo_amostra === 'consolidada' ? 'Consolidada' : 'Oferta';
  const tipoBadge = s.tipo_amostra === 'consolidada'
    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
    : 'bg-amber-100 text-amber-800 border-amber-300';

  return (
    <div className={`rounded-xl border p-4 transition ${isSaneada ? 'border-red-200 bg-red-50/60' : 'border-gray-200 bg-white hover:border-emerald-200'}`}>
      {/* Cabeçalho do card */}
      <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-gray-100">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-semibold ${isSaneada ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-800'}`}>
            {idx + 1}
          </span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${tipoBadge}`}>{tipoLabel}</span>
          {isSaneada && (
            <span className="flex items-center gap-1 text-xs text-red-600">
              <AlertTriangle className="w-3.5 h-3.5" /> Eliminada pelo saneamento (±10% da média)
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wide text-gray-400">{vUnitLabel}</div>
            <div className={`text-base font-bold ${isSaneada ? 'text-red-600 line-through' : 'text-emerald-800'}`}>
              {vUnit > 0 ? `R$ ${fmtUnit(vUnit)}` : '—'}
            </div>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
            title="Remover amostra"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Corpo: campos rotulados + foto */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1 space-y-3">
          {/* Localização */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Labeled label="Endereço">
              <Input value={s.address || ''} onChange={(e) => set('address', e.target.value)} placeholder="Rua, número, referência" className="h-9" />
            </Labeled>
            <Labeled label="Bairro / localidade">
              <Input value={s.neighborhood || ''} onChange={(e) => set('neighborhood', e.target.value)} placeholder="Bairro" className="h-9" />
            </Labeled>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <Labeled label="Município">
                <Input value={s.municipio || ''} onChange={(e) => set('municipio', e.target.value)} placeholder="Município" className="h-9" />
              </Labeled>
            </div>
            <Labeled label="UF">
              <Input value={s.uf || ''} maxLength={2} onChange={(e) => set('uf', e.target.value.toUpperCase())} placeholder="MA" className="h-9" />
            </Labeled>
          </div>

          {/* Área — urbana simples */}
          {!rural && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Labeled label="Área (m²)">
                <Input type="number" min={0} step="any" value={s.area || ''} onChange={setNum('area')} placeholder="0" className="h-9" />
              </Labeled>
              <ComputedBox label={`${vUnitLabel} (calculado)`}>
                {vUnit > 0 ? `R$ ${fmtUnit(vUnit)}` : '—'}
              </ComputedBox>
            </div>
          )}

          {/* Área — rural com conversão em tempo real */}
          {rural && (
            <div>
              <span className="block text-[10px] font-semibold uppercase tracking-wide text-emerald-700 mb-2">Área rural</span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Labeled label="Área (m²)">
                  <Input type="number" min={0} step="any" value={s.area || ''} onChange={setNum('area')} placeholder="0" className="h-9 border-emerald-400" />
                </Labeled>
                <ComputedBox label="→ hectares">{conv.ha} ha</ComputedBox>
                <ComputedBox label="→ alqueires min.">{conv.alq} alq</ComputedBox>
              </div>
            </div>
          )}

          {/* Campos específicos por tipo */}
          <ExtraSection categoria={categoria} s={s} set={set} />

          {/* Transação */}
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Transação</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Labeled label="Valor (R$)">
                <Input type="number" min={0} step="any" value={s.value || ''} onChange={setNum('value')} placeholder="0" className="h-9" />
              </Labeled>
              <ComputedBox label={`${vUnitLabel} (calculado)`}>
                {vUnit > 0 ? `R$ ${fmtUnit(vUnit)}` : '—'}
              </ComputedBox>
              <Labeled label="Tipo da amostra">
                <select
                  value={s.tipo_amostra || 'oferta'}
                  onChange={(e) => set('tipo_amostra', e.target.value)}
                  className="w-full h-9 rounded-md border border-gray-200 px-2 text-sm bg-white focus:outline-none focus:border-emerald-400"
                >
                  <option value="oferta">Oferta de Mercado</option>
                  <option value="consolidada">Consolidada / Comercializada</option>
                </select>
              </Labeled>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Labeled label="Fonte">
                <Input value={s.source || ''} onChange={(e) => set('source', e.target.value)} placeholder="Imobiliária, portal..." className="h-9" />
              </Labeled>
              <Labeled label="Data da coleta">
                <Input type="date" value={s.collection_date || ''} onChange={(e) => set('collection_date', e.target.value)} className="h-9" />
              </Labeled>
              <Labeled label="Telefone">
                <Input value={s.contact_phone || ''} onChange={(e) => set('contact_phone', e.target.value)} placeholder="(00) 00000-0000" className="h-9" />
              </Labeled>
            </div>
          </div>

          {/* Descrição / memorial da amostra */}
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                Descrição / memorial da amostra
              </span>
              <AiButton onClick={gerarMemorial} loading={aiBusy} />
            </div>
            <RichTextEditor
              value={paraEditorHtml(s.notes)}
              onChange={(html) => set('notes', html)}
              showAiButton={false}
              minHeight={110}
              placeholder="Descreva a amostra: características construtivas, cômodos (para residências), padrão, conservação, localização e condições de oferta/venda. Use o botão de IA para gerar um memorial a partir dos dados preenchidos."
            />
          </div>
        </div>

        {/* Foto da amostra + Planta baixa */}
        <div className="lg:w-56 shrink-0 space-y-4">
          <div>
            <FieldLabel>Foto da amostra</FieldLabel>
            <ImageUploader
              images={s.foto ? [s.foto] : []}
              onImagesChange={(ids) => onChange({ ...s, foto: ids[0] || null })}
              maxImages={1}
              single
              label=""
            />
          </div>

          {/* Planta baixa — aceita PDF (convertido p/ PNG 300 DPI no upload) */}
          <div>
            <FieldLabel>Planta baixa (PDF/imagem)</FieldLabel>
            <ImageUploader
              images={s.planta_baixa ? [s.planta_baixa] : []}
              onImagesChange={(ids) => onChange({ ...s, planta_baixa: ids[0] || null })}
              maxImages={1}
              single
              label=""
              previewClass="h-96"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export const StepAmostras = ({ form, setForm, onAi, aiLoading }) => {
  const samples = useMemo(() => form.market_samples ?? [], [form.market_samples]);
  const [showBusca, setShowBusca] = useState(false);
  const [showBanco, setShowBanco] = useState(false);
  const tipoImovel = form.property_type;
  const categoriaBanco = isRuralImovel(tipoImovel) ? 'rural' : 'urbano';
  const add = () => setForm({ ...form, market_samples: [...samples, emptyMarketSample()] });
  const update = (i, ns) => setForm({ ...form, market_samples: samples.map((s, idx) => idx === i ? ns : s) });
  const remove = (i) => setForm({ ...form, market_samples: samples.filter((_, idx) => idx !== i) });

  // Calcular estatísticas NBR para destacar amostras saneadas
  const stats = useMemo(() => computeStatsNBR(samples), [samples]);

  const handleImport = (novasAmostras) => {
    const amostrasFormatadas = novasAmostras.map(a => ({
      ...emptyMarketSample(),
      address: a.address,
      neighborhood: a.neighborhood,
      area: a.area,
      value: a.value,
      value_per_sqm: a.value_per_sqm,
      source: a.source,
      collection_date: a.collection_date,
      contact_phone: a.contact_phone,
      notes: a.notes,
      tipo_amostra: a.tipo_amostra,
      foto: a.thumbnail,
    }));
    setForm({ ...form, market_samples: [...samples, ...amostrasFormatadas] });
    setShowBusca(false);
  };

  // Importar amostras já cadastradas no Banco Global (com foto/planta).
  const handleImportBanco = (novas) => {
    setForm({ ...form, market_samples: [...samples, ...novas] });
    setShowBanco(false);
  };

  const validCount = samples.filter((s) => (s.value_per_sqm || 0) > 0).length;
  const saneadasCount = stats.indices_saneadas.length;

  return (
    <div>
      <SectionHeader
        title="6. Amostras de Mercado"
        subtitle="Cadastre as amostras coletadas para a pesquisa de mercado (mínimo 3)."
      />

      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm text-gray-500">{samples.length} amostra(s) cadastrada(s)</span>
          {validCount < 3 && (
            <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-0.5">
              Adicione pelo menos 3 amostras com área e valor
            </span>
          )}
          {validCount >= 3 && (
            <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-0.5">
              {validCount} amostras com {unidadeValorLabel(isRuralImovel(tipoImovel))}
            </span>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button
            type="button"
            variant="outline"
            onClick={() => setShowBanco(true)}
            className="border-emerald-700 text-emerald-800 hover:bg-emerald-50 text-sm"
          >
            <Database className="w-4 h-4 mr-1" /> Banco de Amostras
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => setShowBusca(true)}
            className="border-emerald-300 text-emerald-700 hover:bg-emerald-50 text-sm"
          >
            <Search className="w-4 h-4 mr-1" /> Buscar no ZAP / VivaReal
          </Button>
          <Button type="button" onClick={add} className="bg-emerald-900 hover:bg-emerald-800 text-white text-sm">
            <Plus className="w-4 h-4 mr-1" /> Nova amostra
          </Button>
        </div>
      </div>

      {/* Resumo de Saneamento */}
      {stats.n_total > 0 && (
        <div className={`mb-4 p-3 rounded-lg border ${
          stats.n_validas < 3
            ? 'bg-red-50 border-red-200'
            : saneadasCount > 0
              ? 'bg-amber-50 border-amber-200'
              : 'bg-emerald-50 border-emerald-200'
        }`}>
          <div className="flex items-center gap-2">
            {stats.n_validas < 3 ? (
              <AlertTriangle className="w-4 h-4 text-red-500" />
            ) : saneadasCount > 0 ? (
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            ) : null}
            <span className={`text-sm font-medium ${
              stats.n_validas < 3 ? 'text-red-700' : saneadasCount > 0 ? 'text-amber-700' : 'text-emerald-700'
            }`}>
              {stats.n_validas} amostra(s) válida(s) de {stats.n_total} inserida(s)
              {saneadasCount > 0 && ` — ${saneadasCount} eliminada(s) pelo saneamento`}
            </span>
          </div>
          {stats.n_validas < 3 && (
            <p className="text-xs text-red-600 mt-1">
              Mínimo 3 amostras válidas necessárias para PTAM conforme NBR 14653-2
            </p>
          )}
          {saneadasCount > 0 && (
            <p className="text-xs text-amber-600 mt-1">
              Amostras eliminadas por estarem fora do intervalo de saneamento (±10% da média inicial)
            </p>
          )}
        </div>
      )}

      <BuscaAmostras
        open={showBusca}
        onClose={() => setShowBusca(false)}
        onImport={handleImport}
        cidadeDefault={form.property_city || ''}
        estadoDefault={form.property_state || ''}
      />

      <BancoAmostrasPicker
        open={showBanco}
        onClose={() => setShowBanco(false)}
        onImport={handleImportBanco}
        categoria={categoriaBanco}
        municipioDefault={form.property_city || ''}
      />

      {samples.length === 0 ? (
        <div className="text-center py-12 bg-emerald-50/40 rounded-xl border-2 border-dashed border-emerald-200 text-gray-500">
          Nenhuma amostra cadastrada. Clique em "Nova amostra" para começar.
        </div>
      ) : (
        <div className="space-y-4">
          {samples.map((s, i) => (
            <MarketSampleCard
              key={s._key || `ms-${i}`}
              s={s}
              idx={i}
              tipoImovel={tipoImovel}
              onChange={(ns) => update(i, ns)}
              onRemove={() => remove(i)}
              isSaneada={stats.indices_saneadas.includes(i)}
            />
          ))}
        </div>
      )}

      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2 mt-3">
        Amostras consolidadas (venda/locacao efetivada) tem maior peso na avaliacao conforme NBR 14653.
      </p>

      <div className="mt-6">
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Análise de mercado (texto descritivo)</label>
        <RichField form={form} setForm={setForm} field="market_analysis" minHeight={110}
          placeholder="Descreva o comportamento do mercado imobiliário local, oferta, demanda, liquidez..." />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('market_analysis')} loading={aiLoading === 'market_analysis'} />
        </div>
      </div>
    </div>
  );
};
