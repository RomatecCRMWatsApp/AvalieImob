// @module Semoventes/steps/Step7Vistoria — Step 7 — Vistoria Técnica Presencial e Fotos

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { SectionTitle, Field, Inp, CheckRow } from './shared.js';
import ImageUploader from '../../../ptam/ImageUploader';

const Step7Vistoria = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Vistoria Técnica Presencial</SectionTitle>

    <div className="flex items-start gap-3 bg-amber-50 border border-amber-300 rounded-xl px-4 py-3">
      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-amber-800">
        A contagem física presencial do rebanho é <strong>obrigatória</strong> para laudos de penhor rural
        conforme Dec.-Lei 167/1967 art. 9 e MCR BACEN Cap. 6.
      </p>
    </div>

    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Data da Vistoria" required>
        <Inp type="date" value={form.vistoria_data} onChange={(e) => set('vistoria_data', e.target.value)} />
      </Field>
      <Field label="Horário">
        <Inp type="time" value={form.vistoria_horario} onChange={(e) => set('vistoria_horario', e.target.value)} />
      </Field>
    </div>

    <CheckRow
      label="Contagem Física Presencial Realizada"
      checked={form.contagem_fisica_presencial}
      onChange={(v) => set('contagem_fisica_presencial', v)}
      hint="Obrigatória — o Médico Veterinário deve ter contado fisicamente os animais no local"
    />

    <Field label={`Condição Corporal Média: ${form.condicao_corporal_media || 3}/5`} hint="Escala de 1 (muito magro) a 5 (obeso)">
      <input
        type="range"
        min="1"
        max="5"
        step="0.5"
        value={form.condicao_corporal_media || 3}
        onChange={(e) => set('condicao_corporal_media', parseFloat(e.target.value))}
        className="w-full accent-emerald-700"
      />
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>1 — Muito Magro</span>
        <span>3 — Médio</span>
        <span>5 — Obeso</span>
      </div>
    </Field>

    <Field
      label="Fotos da Vistoria"
      required
      hint="Mínimo de 20 fotos exigido: geral do rebanho, marcações, instalações, documentos sanitários"
    >
      <div className={`mb-2 text-xs font-semibold ${(form.fotos || []).length < 20 ? 'text-amber-600' : 'text-emerald-700'}`}>
        {(form.fotos || []).length}/20 fotos{' '}
        {(form.fotos || []).length < 20
          ? `— adicione mais ${20 - (form.fotos || []).length} para cumprir o mínimo`
          : '— mínimo atingido ✓'}
      </div>
      <ImageUploader
        images={form.fotos || []}
        onImagesChange={(ids) => set('fotos', ids)}
        maxImages={60}
        label=""
      />
    </Field>
  </div>
);

export default Step7Vistoria;
