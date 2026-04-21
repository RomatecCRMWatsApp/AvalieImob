// @module Semoventes/steps/Step2Devedor — Step 2 — Dados do Devedor e Propriedade Rural

import React from 'react';
import { SectionTitle, Field, Inp, Sel, UF_OPTIONS } from './shared.js';

const Step2Devedor = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Dados do Devedor</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome / Razão Social" required>
        <Inp value={form.devedor_nome} onChange={(e) => set('devedor_nome', e.target.value)} placeholder="Nome completo ou razão social" />
      </Field>
      <Field label="CPF / CNPJ">
        <Inp value={form.devedor_cpf_cnpj} onChange={(e) => set('devedor_cpf_cnpj', e.target.value)} placeholder="000.000.000-00" />
      </Field>
    </div>

    <SectionTitle>Propriedade Rural</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome da Fazenda / Propriedade" required>
        <Inp value={form.propriedade_nome} onChange={(e) => set('propriedade_nome', e.target.value)} placeholder="Ex.: Fazenda Santa Rosa" />
      </Field>
      <Field label="Município" required>
        <Inp value={form.propriedade_municipio} onChange={(e) => set('propriedade_municipio', e.target.value)} placeholder="Ex.: Sorriso" />
      </Field>
      <Field label="UF">
        <Sel value={form.propriedade_uf} onChange={(e) => set('propriedade_uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Sel>
      </Field>
      <Field label="Matrícula do Imóvel" hint="Res. CMN 4.676/2018 — informação obrigatória para penhor">
        <Inp value={form.matricula_imovel} onChange={(e) => set('matricula_imovel', e.target.value)} placeholder="Nº matrícula" />
      </Field>
      <Field label="CRI / Cartório de Registro">
        <Inp value={form.cri_cartorio} onChange={(e) => set('cri_cartorio', e.target.value)} placeholder="Ex.: 1º CRI de Sorriso/MT" />
      </Field>
    </div>
  </div>
);

export default Step2Devedor;
