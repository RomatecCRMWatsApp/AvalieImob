// @module Garantias/steps/StepVistoria — Bancário: Step 4 — Vistoria Técnica e Fotos

import React from 'react';
import { SectionTitle, Field, Input, Textarea } from './shared.js';
import ImageUploader from '../../ptam/ImageUploader';

const StepVistoria = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Vistoria Técnica</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Data da Vistoria" required>
        <Input type="date" value={form.data_vistoria} onChange={(e) => set('data_vistoria', e.target.value)} />
      </Field>
      <Field label="Horário">
        <Input type="time" value={form.vistoria_horario} onChange={(e) => set('vistoria_horario', e.target.value)} />
      </Field>
      <Field label="Responsável pela Vistoria" required hint="CREA/CAU obrigatório">
        <Input
          value={form.vistoria_responsavel_nome}
          onChange={(e) => set('vistoria_responsavel_nome', e.target.value)}
          placeholder="Nome do Engenheiro / Arquiteto"
        />
      </Field>
    </div>
    <Field label="Condições e Observações da Vistoria">
      <Textarea
        value={form.vistoria_condicoes_obs}
        onChange={(e) => set('vistoria_condicoes_obs', e.target.value)}
        rows={4}
        placeholder="Descreva as condições de acesso, condições climáticas, presença do proprietário, etc."
      />
    </Field>
    <Field label="Observações Gerais">
      <Textarea
        value={form.observacoes}
        onChange={(e) => set('observacoes', e.target.value)}
        rows={3}
        placeholder="Outras observações relevantes para a vistoria..."
      />
    </Field>

    <SectionTitle>Fotos da Vistoria</SectionTitle>
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-3">
      Mínimo de 10 fotos obrigatórias: fachada, cômodos principais, área externa, entorno e número de RGI/matrícula.
    </div>
    <ImageUploader
      images={form.fotos}
      onImagesChange={(ids) => set('fotos', ids)}
      maxImages={20}
      label={`Fotos da Vistoria (${form.fotos?.length || 0}/20 — mínimo 10)`}
      accept="image/jpeg,image/jpg,image/png,image/webp"
    />
  </div>
);

export default StepVistoria;
