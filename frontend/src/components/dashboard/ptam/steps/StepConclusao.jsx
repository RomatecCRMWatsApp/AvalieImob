// @module ptam/steps/StepConclusao — Step 12: Conclusão do Laudo (considerações, responsável, assinatura)
import React, { useState } from 'react';
import { PenLine, CheckCircle2 } from 'lucide-react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field, SectionHeader, AiButton } from '../shared/primitives';
import AssinaturaDigital from '../AssinaturaDigital';
import RichField from '../../../ui/RichField';

const CONCLUSION_FIELDS = [
  { key: 'consideracoes_ressalvas',    label: 'Ressalvas e Limitações',       placeholder: 'Fatores limitantes da avaliação, dados não disponíveis, restrições à vistoria...' },
  { key: 'consideracoes_pressupostos', label: 'Pressupostos Adotados',        placeholder: 'Premissas assumidas para a avaliação, condições normais de mercado...' },
  { key: 'consideracoes_limitacoes',   label: 'Limitações e Advertências',    placeholder: 'Advertências legais, validade do laudo, condições de uso...' },
  { key: 'conclusion_text',            label: 'Texto de Conclusão do Laudo',  placeholder: 'Redija o parágrafo final de conclusão do laudo técnico...' },
];

export const StepConclusao = ({ form, setForm, onAi, aiLoading, onSolicitarAssinatura, onSave }) => {
  const [showAssinatura, setShowAssinatura] = useState(false);
  const ptamId = form?.id || null;

  const handleSolicitarAssinatura = () => {
    if (onSolicitarAssinatura) {
      onSolicitarAssinatura();
    } else if (ptamId) {
      setShowAssinatura(true);
    }
  };

  return (
    <div>
      <SectionHeader
        title="12. Conclusão e Responsável Técnico"
        subtitle="Considerações finais e dados do profissional responsável pelo laudo."
      />

      {/* ── Conclusão MANUAL do laudo ─────────────────────────────────── */}
      <div className={`mb-6 rounded-xl border-2 p-4 transition ${
        form.concluido_manual === true ? 'border-emerald-300 bg-emerald-50' : 'border-amber-200 bg-amber-50'
      }`}>
        <label className="flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.concluido_manual === true}
            onChange={(e) => {
              setForm((f) => ({
                ...f,
                concluido_manual: e.target.checked,
                concluido_em: e.target.checked ? new Date().toISOString() : null,
              }));
              if (onSave) onSave();
            }}
            className="mt-0.5 w-5 h-5 accent-emerald-600"
          />
          <div>
            <div className="font-semibold text-gray-900 flex items-center gap-2">
              <CheckCircle2 className={`w-4 h-4 ${form.concluido_manual === true ? 'text-emerald-600' : 'text-amber-500'}`} />
              Marcar laudo como CONCLUÍDO
            </div>
            <p className="text-xs text-gray-600 mt-1 leading-relaxed">
              Marque quando todos os ajustes estiverem prontos — o card passa a exibir o status
              <strong> Concluído</strong>. A partir daí, o status só muda por assinatura digital.
              {form.concluido_manual === true && form.concluido_em
                ? ` Concluído em ${new Date(form.concluido_em).toLocaleString('pt-BR')}.`
                : ''}
            </p>
          </div>
        </label>
      </div>

      <div className="space-y-5">
        {CONCLUSION_FIELDS.map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
            <RichField form={form} setForm={setForm} field={key} minHeight={100} placeholder={placeholder} />
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

      {/* ── Assinatura Digital ───────────────────────────────────────── */}
      <div className="mt-8 border-t border-gray-100 pt-6">
        <div className="border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <PenLine className="w-4 h-4 text-emerald-700" />
            <span className="font-semibold text-gray-900">Assinatura Digital com Validade Juridica</span>
          </div>
          <button
            type="button"
            onClick={handleSolicitarAssinatura}
            disabled={!ptamId}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border-2 border-emerald-300 text-emerald-700 font-medium text-sm hover:bg-emerald-50 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <PenLine className="w-4 h-4" />
            Solicitar Assinatura Digital
          </button>
          <p className="text-xs text-center text-gray-400 mt-2">
            Lei 14.063/2020 · MP 2.200-2/2001 · D4Sign
          </p>
        </div>
      </div>

      {showAssinatura && ptamId && (
        <AssinaturaDigital
          tipo="ptam"
          docId={ptamId}
          docData={form}
          onClose={() => setShowAssinatura(false)}
          onUpdate={(updates) => setForm(f => ({ ...f, ...updates }))}
        />
      )}
    </div>
  );
};
