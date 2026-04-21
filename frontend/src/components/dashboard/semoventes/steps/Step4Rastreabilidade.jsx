// @module Semoventes/steps/Step4Rastreabilidade — Step 4 — Rastreabilidade SISBOV e Identificação

import React from 'react';
import { SectionTitle, Field, Inp, Sel, CheckRow } from './shared.js';

const Step4Rastreabilidade = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Rastreabilidade — SISBOV / IN MAPA 78/2022</SectionTitle>
    <div className="space-y-4">
      <CheckRow
        label="Brincos SISBOV (e-SISBOV)"
        checked={form.brincos_sisbov}
        onChange={(v) => set('brincos_sisbov', v)}
        hint="IN MAPA 78/2022 — Sistema Brasileiro de Identificação e Certificação de Bovinos"
      />
      {form.brincos_sisbov && (
        <div className="grid md:grid-cols-2 gap-4 ml-7">
          <Field label="Brinco Início (nº)">
            <Inp value={form.brinco_inicio} onChange={(e) => set('brinco_inicio', e.target.value)} placeholder="Ex.: 076-BR-XXXXXXX" />
          </Field>
          <Field label="Brinco Fim (nº)">
            <Inp value={form.brinco_fim} onChange={(e) => set('brinco_fim', e.target.value)} placeholder="Ex.: 076-BR-YYYYYYY" />
          </Field>
          <Field label="Situação no e-SISBOV" className="md:col-span-2">
            <Sel value={form.situacao_esisbov} onChange={(e) => set('situacao_esisbov', e.target.value)}>
              <option value="">Selecionar...</option>
              <option value="certificado">Certificado</option>
              <option value="em_processo">Em Processo de Certificação</option>
              <option value="nao_certificado">Não Certificado</option>
            </Sel>
          </Field>
        </div>
      )}

      <CheckRow
        label="Marcação a Ferro"
        checked={form.marcacao_ferro}
        onChange={(v) => set('marcacao_ferro', v)}
      />
      {form.marcacao_ferro && (
        <div className="ml-7">
          <Field label="Descrição da Marcação">
            <Inp value={form.marcacao_descricao} onChange={(e) => set('marcacao_descricao', e.target.value)} placeholder="Sigla, lado, posição..." />
          </Field>
        </div>
      )}

      <CheckRow
        label="Microchip / Transponder eletrônico"
        checked={form.microchip}
        onChange={(v) => set('microchip', v)}
      />
    </div>
  </div>
);

export default Step4Rastreabilidade;
