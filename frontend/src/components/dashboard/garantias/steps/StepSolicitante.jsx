// @module Garantias/steps/StepSolicitante — Rural: Step 2 — Dados do Solicitante

import React from 'react';
import { SectionTitle, Field, Input } from './shared.js';

const StepSolicitante = ({ form, setNested }) => {
  const s = form.solicitante || {};
  return (
    <div className="space-y-6">
      <SectionTitle>Dados do Solicitante</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Nome / Razão Social" required>
          <Input value={s.nome} onChange={(e) => setNested('solicitante', 'nome', e.target.value)} placeholder="Ex.: João da Silva" />
        </Field>
        <Field label="CPF / CNPJ">
          <Input value={s.cpf_cnpj} onChange={(e) => setNested('solicitante', 'cpf_cnpj', e.target.value)} placeholder="000.000.000-00" />
        </Field>
        <Field label="Instituição Financeira">
          <Input value={s.instituicao_financeira} onChange={(e) => setNested('solicitante', 'instituicao_financeira', e.target.value)} placeholder="Ex.: Banco do Brasil S.A." />
        </Field>
        <Field label="Telefone">
          <Input value={s.telefone} onChange={(e) => setNested('solicitante', 'telefone', e.target.value)} placeholder="(00) 00000-0000" />
        </Field>
        <Field label="E-mail">
          <Input value={s.email} onChange={(e) => setNested('solicitante', 'email', e.target.value)} placeholder="email@exemplo.com" type="email" />
        </Field>
      </div>
    </div>
  );
};

export default StepSolicitante;
