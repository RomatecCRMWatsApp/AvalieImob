// @module Semoventes/steps/Step10Declaracoes — Step 10 — Declarações, Ressalvas e Responsável Técnico CRMV

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { SectionTitle, Field, Inp, Sel, Txta, CheckRow, UF_OPTIONS } from './shared.js';

const Step10Declaracoes = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Restrições e Ressalvas</SectionTitle>
    <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-900 space-y-2">
      <p><strong>Ressalvas padrão para laudos de semoventes:</strong></p>
      <ul className="list-disc list-inside space-y-1 text-xs">
        <li>O valor avaliado é válido na data da vistoria e sujeito a variações de mercado.</li>
        <li>Flutuações nas cotações de commodities podem afetar significativamente o valor do rebanho.</li>
        <li>Riscos sanitários (doenças, epidemias) não contemplados nesta avaliação.</li>
        <li>A avaliação não garante a existência futura dos animais nem sua condição de saúde.</li>
        <li>Validade: {form.validade_laudo_meses || 6} meses da data de emissão — após este prazo nova vistoria é necessária.</li>
      </ul>
    </div>
    <Field label="Restrições e Ressalvas Adicionais">
      <Txta
        value={form.restricoes_ressalvas}
        onChange={(e) => set('restricoes_ressalvas', e.target.value)}
        rows={4}
        placeholder="Insira restrições ou ressalvas específicas a este laudo..."
      />
    </Field>

    <SectionTitle>Declarações Obrigatórias</SectionTitle>
    <div className="space-y-4">
      <CheckRow
        label="Declaro que realizei contagem física presencial dos animais no local da vistoria"
        checked={form.declaracao_contagem_presencial}
        onChange={(v) => set('declaracao_contagem_presencial', v)}
        hint="Obrigatório — Dec.-Lei 167/1967 art. 9"
      />
      <CheckRow
        label="Declaro não possuir conflito de interesses com o devedor, credor ou intermediários"
        checked={form.declaracao_sem_conflito}
        onChange={(v) => set('declaracao_sem_conflito', v)}
      />
      <CheckRow
        label="Declaro que o penhor rural está registrado ou será registrado conforme a lei"
        checked={form.declaracao_penhor_registrado}
        onChange={(v) => set('declaracao_penhor_registrado', v)}
        hint="Lei 8.171/1991 · Dec.-Lei 167/1967 arts. 9-19"
      />
    </div>

    <SectionTitle>Responsável Técnico — CRMV Obrigatório</SectionTitle>
    <div className="flex items-start gap-3 bg-red-50 border-2 border-red-300 rounded-xl px-4 py-3 mb-4">
      <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-red-800">
        <strong>Laudo sem CRMV ativo é nulo</strong> para fins de penhor rural bancário.
        (CFMV Res. 722/2002 · Circ. BACEN 3.818/2016)
      </p>
    </div>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome do Médico Veterinário" required>
        <Inp value={form.responsavel_nome} onChange={(e) => set('responsavel_nome', e.target.value)} placeholder="Nome completo" />
      </Field>
      <Field label="CRMV Nº" required>
        <Inp value={form.crmv_numero} onChange={(e) => set('crmv_numero', e.target.value)} placeholder="00000" />
      </Field>
      <Field label="CRMV UF" required>
        <Sel value={form.crmv_uf} onChange={(e) => set('crmv_uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Sel>
      </Field>
      <Field label="Especialidade">
        <Inp value={form.especialidade} onChange={(e) => set('especialidade', e.target.value)} placeholder="Ex.: Clínica de Ruminantes, Sanidade Animal..." />
      </Field>
      <Field label="Nº ART/CRMV" hint="Art. de Responsabilidade Técnica">
        <Inp value={form.art_crmv_numero} onChange={(e) => set('art_crmv_numero', e.target.value)} placeholder="Nº ART" />
      </Field>
      <Field label="Data de Registro da ART">
        <Inp type="date" value={form.art_data_registro} onChange={(e) => set('art_data_registro', e.target.value)} />
      </Field>
    </div>
  </div>
);

export default Step10Declaracoes;
