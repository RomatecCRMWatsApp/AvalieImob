// @module ptam/steps/StepConclusao — Step 12: Conclusão do Laudo (considerações, responsável, assinatura)
import React from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field, SectionHeader, AiButton } from '../shared/primitives';

const CONCLUSION_FIELDS = [
  { key: 'consideracoes_ressalvas',    label: 'Ressalvas e Limitações',       placeholder: 'Fatores limitantes da avaliação, dados não disponíveis, restrições à vistoria...' },
  { key: 'consideracoes_pressupostos', label: 'Pressupostos Adotados',        placeholder: 'Premissas assumidas para a avaliação, condições normais de mercado...' },
  { key: 'consideracoes_limitacoes',   label: 'Limitações e Advertências',    placeholder: 'Advertências legais, validade do laudo, condições de uso...' },
  { key: 'conclusion_text',            label: 'Texto de Conclusão do Laudo',  placeholder: 'Redija o parágrafo final de conclusão do laudo técnico...' },
];

export const StepConclusao = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="12. Conclusão e Responsável Técnico"
      subtitle="Considerações finais e dados do profissional responsável pelo laudo."
    />
    <div className="space-y-5">
      {CONCLUSION_FIELDS.map(({ key, label, placeholder }) => (
        <div key={key}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
          <Textarea
            value={form[key] || ''}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            rows={4}
            placeholder={placeholder}
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi(key)} loading={aiLoading === key} />
          </div>
        </div>
      ))}
    </div>

    <div className="mt-8 border-t border-gray-100 pt-6">
      <div className="text-sm font-semibold text-gray-900 mb-4">Dados do Profissional Responsável</div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Tipo de Profissional">
          <Select value={form.tipo_profissional || 'corretor'} onValueChange={(v) => setForm({ ...form, tipo_profissional: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="corretor">Corretor de Imóveis (CRECI/CNAI)</SelectItem>
              <SelectItem value="engenheiro">Engenheiro Civil (CREA)</SelectItem>
              <SelectItem value="arquiteto">Arquiteto e Urbanista (CAU)</SelectItem>
              <SelectItem value="agronomo">Engenheiro Agrônomo (CREA)</SelectItem>
              <SelectItem value="tecnico">Técnico em Transações Imobiliárias (CFT)</SelectItem>
            </SelectContent>
          </Select>
        </Field>
        <Field label="Nome do Responsável Técnico">
          <Input value={form.responsavel_nome || ''} onChange={(e) => setForm({ ...form, responsavel_nome: e.target.value })} placeholder="Nome completo" />
        </Field>
        <Field label="CRECI">
          <Input value={form.responsavel_creci || ''} onChange={(e) => setForm({ ...form, responsavel_creci: e.target.value })} placeholder="Ex: CRECI/MA 12345-F" />
        </Field>
        <Field label="CNAI">
          <Input value={form.responsavel_cnai || ''} onChange={(e) => setForm({ ...form, responsavel_cnai: e.target.value })} placeholder="Ex: CNAI 00000" />
        </Field>
        <Field label="Registro Profissional (CREA/CAU)">
          <Input value={form.registro_profissional || ''} onChange={(e) => setForm({ ...form, registro_profissional: e.target.value })} placeholder="Ex: CREA/MA 12345-D" />
        </Field>
        <Field label="ART / RRT">
          <Input value={form.art_rrt_numero || ''} onChange={(e) => setForm({ ...form, art_rrt_numero: e.target.value })} placeholder="Número da ART ou RRT" />
        </Field>
        <Field label="Cidade de emissão">
          <Input value={form.conclusion_city || ''} onChange={(e) => setForm({ ...form, conclusion_city: e.target.value })} placeholder="Cidade, UF" />
        </Field>
        <Field label="Data de emissão">
          <Input type="date" value={form.conclusion_date || ''} onChange={(e) => setForm({ ...form, conclusion_date: e.target.value })} />
        </Field>
      </div>
    </div>
  </div>
);
