// @module Garantias/steps/StepAvaliacao — Rural: Step 5 — Metodologia e Avaliação
import React, { useCallback } from 'react';
import { SectionTitle, Field, Input, Select, Textarea } from './shared.js';
import MetodoEvolutivo from '../../ptam/MetodoEvolutivo';

const StepAvaliacao = ({ form, set }) => {
  // Adapta a interface do MetodoEvolutivo (que usa setForm(fn)) para o padrão de Garantias (set(field, val))
  const setFormAdapter = useCallback(
    (updater) => {
      if (typeof updater === 'function') {
        // MetodoEvolutivo passa uma função updater — aplicamos sobre form e extraímos os campos modificados
        const next = updater(form);
        Object.entries(next).forEach(([k, v]) => {
          if (v !== form[k]) set(k, v);
        });
      } else {
        Object.entries(updater).forEach(([k, v]) => set(k, v));
      }
    },
    [form, set]
  );

  return (
    <div className="space-y-6">
      <SectionTitle>Metodologia (NBR 14.653)</SectionTitle>
      <Field label="Metodologia Utilizada" required>
        <Select value={form.metodologia} onChange={(e) => set('metodologia', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="comparativo_direto">Método Comparativo Direto de Dados de Mercado</option>
          <option value="renda">Método da Renda</option>
          <option value="involutivo">Método Involutivo</option>
          <option value="evolutivo">Método Evolutivo / Custo de Reprodução</option>
          <option value="producao">Método da Capitalização da Renda (Agropecuária)</option>
          <option value="cotacao_mercado">Cotação de Mercado (grãos/bovinos)</option>
          <option value="outros">Outros</option>
        </Select>
      </Field>

      {/* Método Evolutivo — exibido quando selecionado */}
      {form.metodologia === 'evolutivo' && (
        <div className="mt-2">
          <MetodoEvolutivo form={form} setForm={setFormAdapter} />
        </div>
      )}

      {form.metodologia !== 'evolutivo' && (
        <>
          <Field label="Fundamentação Legal">
            <Input value={form.fundamentacao_legal} onChange={(e) => set('fundamentacao_legal', e.target.value)} />
          </Field>
          <Field label="Mercado de Referência">
            <Textarea value={form.mercado_referencia} onChange={(e) => set('mercado_referencia', e.target.value)} rows={3} />
          </Field>
          <Field label="Fatores de Depreciação / Homogeneização">
            <Textarea value={form.fatores_depreciacao} onChange={(e) => set('fatores_depreciacao', e.target.value)} rows={3} />
          </Field>
        </>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Grau de Fundamentação">
          <Select value={form.grau_fundamentacao} onChange={(e) => set('grau_fundamentacao', e.target.value)}>
            <option value="">Selecionar...</option>
            <option value="I">Grau I</option>
            <option value="II">Grau II</option>
            <option value="III">Grau III</option>
          </Select>
        </Field>
        <Field label="Estado de Conservação">
          <Select value={form.estado_conservacao} onChange={(e) => set('estado_conservacao', e.target.value)}>
            <option value="otimo">Ótimo</option>
            <option value="bom">Bom</option>
            <option value="regular">Regular</option>
            <option value="precario">Precário</option>
          </Select>
        </Field>
        <Field label="Data de Avaliação">
          <Input type="date" value={form.data_avaliacao} onChange={(e) => set('data_avaliacao', e.target.value)} />
        </Field>
        <Field label="Data de Validade">
          <Input type="date" value={form.data_validade} onChange={(e) => set('data_validade', e.target.value)} />
        </Field>
      </div>
    </div>
  );
};

export default StepAvaliacao;
