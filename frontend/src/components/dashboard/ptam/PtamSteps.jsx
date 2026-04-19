import React from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Textarea } from '../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Plus, Trash2, Sparkles } from 'lucide-react';
import { emptyImpactArea, emptySample } from './ptamHelpers';

const Field = ({ label, children, full }) => (
  <div className={full ? 'col-span-2' : ''}>
    <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
    {children}
  </div>
);

const AiButton = ({ onClick, loading }) => (
  <Button type="button" size="sm" variant="ghost" className="text-emerald-700 hover:text-emerald-900 hover:bg-emerald-50" onClick={onClick} disabled={loading}>
    <Sparkles className="w-3.5 h-3.5 mr-1" /> {loading ? '...' : 'Aperfeiçoar com IA'}
  </Button>
);

export const StepIdentification = ({ form, setForm, onAi, aiLoading }) => (
  <div className="space-y-5">
    <div>
      <h2 className="font-display text-xl font-bold text-gray-900">Identificação do PTAM</h2>
      <p className="text-sm text-gray-600 mt-1">Dados do processo, solicitante e base legal.</p>
    </div>
    <div className="grid grid-cols-2 gap-4">
      <Field label="Número do PTAM"><Input value={form.number} onChange={(e) => setForm({ ...form, number: e.target.value })} placeholder="7010" /></Field>
      <Field label="Solicitante"><Input value={form.solicitante} onChange={(e) => setForm({ ...form, solicitante: e.target.value })} placeholder="Nome do solicitante" /></Field>
      <Field label="Processo judicial"><Input value={form.judicial_process} onChange={(e) => setForm({ ...form, judicial_process: e.target.value })} placeholder="Nº do processo" /></Field>
      <Field label="Ação"><Input value={form.judicial_action} onChange={(e) => setForm({ ...form, judicial_action: e.target.value })} placeholder="Ex: Servidão Administrativa" /></Field>
      <Field label="Fórum/Vara"><Input value={form.forum} onChange={(e) => setForm({ ...form, forum: e.target.value })} /></Field>
      <Field label="Juiz"><Input value={form.judge} onChange={(e) => setForm({ ...form, judge: e.target.value })} /></Field>
      <Field label="Requerente" full><Input value={form.requerente} onChange={(e) => setForm({ ...form, requerente: e.target.value })} /></Field>
      <Field label="Requerido" full><Input value={form.requerido} onChange={(e) => setForm({ ...form, requerido: e.target.value })} /></Field>
      <Field label="Finalidade do laudo" full>
        <Textarea value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} rows={4} placeholder="Descreva a finalidade do parecer técnico..." />
        <div className="mt-1 flex justify-end"><AiButton onClick={() => onAi('purpose')} loading={aiLoading === 'purpose'} /></div>
      </Field>
    </div>
  </div>
);

export const StepProperty = ({ form, setForm }) => (
  <div className="space-y-5">
    <div>
      <h2 className="font-display text-xl font-bold text-gray-900">Imóvel Avaliando</h2>
      <p className="text-sm text-gray-600 mt-1">Dados do imóvel objeto da avaliação.</p>
    </div>
    <div className="grid grid-cols-2 gap-4">
      <Field label="Rótulo/Título do imóvel" full><Input value={form.property_label} onChange={(e) => setForm({ ...form, property_label: e.target.value })} placeholder="Ex: GLEBA PEQUIÁ-BREJÃO, PARTE DO LOTE 78" /></Field>
      <Field label="Endereço completo" full><Input value={form.property_address} onChange={(e) => setForm({ ...form, property_address: e.target.value })} /></Field>
      <Field label="Cidade/UF"><Input value={form.property_city} onChange={(e) => setForm({ ...form, property_city: e.target.value })} /></Field>
      <Field label="Matrícula"><Input value={form.property_matricula} onChange={(e) => setForm({ ...form, property_matricula: e.target.value })} /></Field>
      <Field label="Proprietário" full><Input value={form.property_owner} onChange={(e) => setForm({ ...form, property_owner: e.target.value })} /></Field>
      <Field label="Área (hectares)"><Input type="number" step="0.0001" value={form.property_area_ha} onChange={(e) => setForm({ ...form, property_area_ha: Number(e.target.value) })} /></Field>
      <Field label="Área (m²)"><Input type="number" value={form.property_area_sqm} onChange={(e) => setForm({ ...form, property_area_sqm: Number(e.target.value) })} /></Field>
      <Field label="Confrontações" full><Textarea value={form.property_confrontations} onChange={(e) => setForm({ ...form, property_confrontations: e.target.value })} rows={3} /></Field>
      <Field label="Descrição geral" full><Textarea value={form.property_description} onChange={(e) => setForm({ ...form, property_description: e.target.value })} rows={5} /></Field>
    </div>
  </div>
);

export const StepVistoria = ({ form, setForm, onAi, aiLoading }) => {
  const fields = [
    { key: 'vistoria_objective', label: 'Objetivo da Vistoria' },
    { key: 'vistoria_methodology', label: 'Metodologia Adotada' },
    { key: 'topography', label: 'Topografia' },
    { key: 'soil_vegetation', label: 'Solo e Cobertura Vegetal' },
    { key: 'benfeitorias', label: 'Benfeitorias Existentes' },
    { key: 'accessibility', label: 'Acessibilidade e Infraestrutura' },
    { key: 'urban_context', label: 'Contexto Urbano e Mercadológico' },
    { key: 'conservation_state', label: 'Estado Geral de Conservação' },
    { key: 'vistoria_synthesis', label: 'Síntese Conclusiva da Vistoria' },
  ];
  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-xl font-bold text-gray-900">Vistoria</h2>
        <p className="text-sm text-gray-600 mt-1">Caracterização física e técnica do imóvel vistoriado.</p>
      </div>
      <Field label="Data da vistoria">
        <Input type="date" value={form.vistoria_date} onChange={(e) => setForm({ ...form, vistoria_date: e.target.value })} className="max-w-xs" />
      </Field>
      <div className="space-y-4">
        {fields.map((f) => (
          <Field key={f.key} label={f.label} full>
            <Textarea value={form[f.key] || ''} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} rows={3} />
            <div className="mt-1 flex justify-end"><AiButton onClick={() => onAi(f.key)} loading={aiLoading === f.key} /></div>
          </Field>
        ))}
      </div>
    </div>
  );
};

export const StepMethodology = ({ form, setForm, onAi, aiLoading }) => (
  <div className="space-y-5">
    <div>
      <h2 className="font-display text-xl font-bold text-gray-900">Metodologia Utilizada</h2>
      <p className="text-sm text-gray-600 mt-1">Conforme ABNT NBR 14.653.</p>
    </div>
    <Field label="Método escolhido">
      <Select value={form.methodology} onValueChange={(v) => setForm({ ...form, methodology: v })}>
        <SelectTrigger><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="Método Comparativo Direto de Dados de Mercado">Método Comparativo Direto</SelectItem>
          <SelectItem value="Método Evolutivo">Método Evolutivo</SelectItem>
          <SelectItem value="Método Involutivo">Método Involutivo</SelectItem>
          <SelectItem value="Método da Renda">Método da Renda</SelectItem>
          <SelectItem value="Método do Custo de Reprodução">Método do Custo de Reprodução</SelectItem>
        </SelectContent>
      </Select>
    </Field>
    <Field label="Justificativa e fundamentação do método" full>
      <Textarea value={form.methodology_justification} onChange={(e) => setForm({ ...form, methodology_justification: e.target.value })} rows={5} />
      <div className="mt-1 flex justify-end"><AiButton onClick={() => onAi('methodology_justification')} loading={aiLoading === 'methodology_justification'} /></div>
    </Field>
    <Field label="Análise mercadológica (região, oferta, demanda)" full>
      <Textarea value={form.market_analysis} onChange={(e) => setForm({ ...form, market_analysis: e.target.value })} rows={5} />
      <div className="mt-1 flex justify-end"><AiButton onClick={() => onAi('market_analysis')} loading={aiLoading === 'market_analysis'} /></div>
    </Field>
  </div>
);

const SampleRow = ({ s, onChange, onRemove }) => (
  <tr className="border-t border-gray-100">
    <td className="p-2"><Input value={s.neighborhood} onChange={(e) => onChange({ ...s, neighborhood: e.target.value })} placeholder="Bairro" /></td>
    <td className="p-2"><Input type="number" value={s.area_total} onChange={(e) => { const v = Number(e.target.value); onChange({ ...s, area_total: v, value_per_sqm: v ? Math.round((s.value || 0) / v * 100) / 100 : 0 }); }} placeholder="m²" /></td>
    <td className="p-2"><Input type="number" value={s.value} onChange={(e) => { const v = Number(e.target.value); onChange({ ...s, value: v, value_per_sqm: s.area_total ? Math.round(v / s.area_total * 100) / 100 : 0 }); }} placeholder="R$" /></td>
    <td className="p-2 text-sm text-center">R$ {Number(s.value_per_sqm || 0).toFixed(2)}</td>
    <td className="p-2"><Input value={s.source} onChange={(e) => onChange({ ...s, source: e.target.value })} placeholder="Fonte" /></td>
    <td className="p-2"><button onClick={onRemove} className="text-red-600 hover:bg-red-50 p-1.5 rounded" type="button"><Trash2 className="w-4 h-4" /></button></td>
  </tr>
);

const ImpactAreaEditor = ({ area, onChange, onRemove, onAi, aiLoading, idx }) => {
  const updateSample = (sIdx, newS) => {
    const samples = area.samples.map((s, i) => (i === sIdx ? newS : s));
    onChange({ ...area, samples });
  };
  const addSample = () => onChange({ ...area, samples: [...(area.samples || []), emptySample()] });
  const removeSample = (sIdx) => onChange({ ...area, samples: area.samples.filter((_, i) => i !== sIdx) });
  const total = Number(area.area_sqm || 0) * Number(area.unit_value || 0);
  const avg = area.samples?.length ? area.samples.reduce((a, b) => a + Number(b.value_per_sqm || 0), 0) / area.samples.length : 0;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex-1 grid grid-cols-2 gap-3">
          <Field label="Nome da área"><Input value={area.name} onChange={(e) => onChange({ ...area, name: e.target.value })} /></Field>
          <Field label="Classificação">
            <Select value={area.classification} onValueChange={(v) => onChange({ ...area, classification: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Rural">Rural</SelectItem>
                <SelectItem value="Urbana">Urbana</SelectItem>
                <SelectItem value="Industrial">Industrial</SelectItem>
                <SelectItem value="Mista">Mista</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </div>
        <button onClick={onRemove} type="button" className="ml-3 p-2 text-red-600 hover:bg-red-50 rounded self-start"><Trash2 className="w-4 h-4" /></button>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Field label="Área impactada (m²)"><Input type="number" value={area.area_sqm} onChange={(e) => onChange({ ...area, area_sqm: Number(e.target.value) })} /></Field>
        <Field label="Valor unitário (R$/m²)"><Input type="number" step="0.01" value={area.unit_value} onChange={(e) => onChange({ ...area, unit_value: Number(e.target.value) })} /></Field>
        <Field label="Total calculado"><div className="h-9 flex items-center font-bold brand-green">R$ {total.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}</div></Field>
      </div>
      <Field label="Majoração aplicada (ex: produção florestal)" full><Input value={area.majoration_note || ''} onChange={(e) => onChange({ ...area, majoration_note: e.target.value })} /></Field>
      <Field label="Observações / fundamentação específica" full>
        <Textarea value={area.notes || ''} onChange={(e) => onChange({ ...area, notes: e.target.value })} rows={3} />
        <div className="mt-1 flex justify-end"><AiButton onClick={() => onAi(`impact_${idx}_notes`)} loading={aiLoading === `impact_${idx}_notes`} /></div>
      </Field>

      <div className="border-t border-gray-100 pt-4">
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="font-semibold text-sm text-gray-900">Amostras de mercado</div>
            {area.samples?.length > 0 && <div className="text-xs text-gray-500">Média: R$ {avg.toFixed(2)}/m²</div>}
          </div>
          <Button type="button" size="sm" variant="outline" onClick={addSample}><Plus className="w-3.5 h-3.5 mr-1" />Amostra</Button>
        </div>
        {area.samples?.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500"><tr><th className="p-2 text-left">Bairro</th><th className="p-2 text-left">Área (m²)</th><th className="p-2 text-left">Valor (R$)</th><th className="p-2 text-center">R$/m²</th><th className="p-2 text-left">Fonte</th><th /></tr></thead>
              <tbody>
                {area.samples.map((s, i) => (
                  <SampleRow key={i} s={s} onChange={(ns) => updateSample(i, ns)} onRemove={() => removeSample(i)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export const StepImpactAreas = ({ form, setForm, onAi, aiLoading }) => {
  const addArea = () => setForm({ ...form, impact_areas: [...(form.impact_areas || []), { ...emptyImpactArea(), name: `Área de Impacto ${String((form.impact_areas?.length || 0) + 1).padStart(2, '0')}` }] });
  const updateArea = (idx, newA) => setForm({ ...form, impact_areas: form.impact_areas.map((a, i) => (i === idx ? newA : a)) });
  const removeArea = (idx) => setForm({ ...form, impact_areas: form.impact_areas.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-display text-xl font-bold text-gray-900">Áreas de Impacto</h2>
          <p className="text-sm text-gray-600 mt-1">Adicione uma ou mais áreas de impacto com amostragens e valores próprios.</p>
        </div>
        <Button type="button" onClick={addArea} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Plus className="w-4 h-4 mr-2" />Nova área</Button>
      </div>
      {(!form.impact_areas || form.impact_areas.length === 0) && (
        <div className="text-center py-10 bg-emerald-50/40 rounded-xl border border-dashed border-emerald-900/20 text-gray-500">Nenhuma área de impacto cadastrada.</div>
      )}
      <div className="space-y-4">
        {(form.impact_areas || []).map((a, i) => (
          <ImpactAreaEditor key={i} area={a} onChange={(na) => updateArea(i, na)} onRemove={() => removeArea(i)} onAi={onAi} aiLoading={aiLoading} idx={i} />
        ))}
      </div>
    </div>
  );
};

export const StepConclusion = ({ form, setForm, onAi, aiLoading }) => {
  const total = (form.impact_areas || []).reduce((acc, a) => acc + Number(a.area_sqm || 0) * Number(a.unit_value || 0), 0);
  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-display text-xl font-bold text-gray-900">Conclusão</h2>
        <p className="text-sm text-gray-600 mt-1">Valor final consolidado.</p>
      </div>
      <div className="bg-gradient-to-br from-emerald-900 to-emerald-950 text-white rounded-xl p-6">
        <div className="text-xs text-emerald-200 uppercase tracking-wider mb-1">Valor total consolidado</div>
        <div className="font-display text-4xl font-bold">R$ {total.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        <div className="text-xs text-emerald-200 mt-2">Soma automática das áreas de impacto</div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Valor total (sobrescrever se necessário)"><Input type="number" step="0.01" value={form.total_indemnity || total} onChange={(e) => setForm({ ...form, total_indemnity: Number(e.target.value) })} /></Field>
        <Field label="Cidade"><Input value={form.conclusion_city} onChange={(e) => setForm({ ...form, conclusion_city: e.target.value })} placeholder="Açailândia/MA" /></Field>
      </div>
      <Field label="Valor por extenso" full>
        <Input value={form.total_indemnity_words} onChange={(e) => setForm({ ...form, total_indemnity_words: e.target.value })} placeholder="Ex: onze milhões, trezentos e dezessete mil reais" />
      </Field>
      <Field label="Data"><Input type="date" value={form.conclusion_date} onChange={(e) => setForm({ ...form, conclusion_date: e.target.value })} className="max-w-xs" /></Field>
      <Field label="Texto de conclusão técnica" full>
        <Textarea value={form.conclusion_text} onChange={(e) => setForm({ ...form, conclusion_text: e.target.value })} rows={6} />
        <div className="mt-1 flex justify-end"><AiButton onClick={() => onAi('conclusion_text')} loading={aiLoading === 'conclusion_text'} /></div>
      </Field>
    </div>
  );
};
