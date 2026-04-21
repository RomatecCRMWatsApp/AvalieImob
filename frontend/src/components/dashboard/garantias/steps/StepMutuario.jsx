// @module Garantias/steps/StepMutuario — Bancário: Step 2 — Dados do Mutuário e Solicitante

import React from 'react';
import { SectionTitle, Field, Input } from './shared.js';

const StepMutuario = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Dados do Mutuário / Garantidor</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome do Mutuário / Garantidor" required>
        <Input
          value={form.mutuario_nome}
          onChange={(e) => set('mutuario_nome', e.target.value)}
          placeholder="Nome completo ou Razão Social"
        />
      </Field>
      <Field label="CPF / CNPJ" required>
        <Input
          value={form.mutuario_cpf_cnpj}
          onChange={(e) => set('mutuario_cpf_cnpj', e.target.value)}
          placeholder="000.000.000-00"
        />
      </Field>
    </div>

    <SectionTitle>Solicitante / Contato</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Nome do Solicitante">
        <Input
          value={form.solicitante?.nome}
          onChange={(e) => set('solicitante', { ...form.solicitante, nome: e.target.value })}
          placeholder="Ex.: Gerente de Crédito"
        />
      </Field>
      <Field label="Telefone">
        <Input
          value={form.solicitante?.telefone}
          onChange={(e) => set('solicitante', { ...form.solicitante, telefone: e.target.value })}
          placeholder="(00) 00000-0000"
        />
      </Field>
      <Field label="E-mail">
        <Input
          type="email"
          value={form.solicitante?.email}
          onChange={(e) => set('solicitante', { ...form.solicitante, email: e.target.value })}
          placeholder="email@banco.com.br"
        />
      </Field>
      <Field label="CPF/CNPJ do Solicitante">
        <Input
          value={form.solicitante?.cpf_cnpj}
          onChange={(e) => set('solicitante', { ...form.solicitante, cpf_cnpj: e.target.value })}
        />
      </Field>
    </div>
  </div>
);

export default StepMutuario;
