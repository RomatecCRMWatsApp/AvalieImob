// @module ptam/steps/StepSolicitante — Step 1: Identificação do Solicitante
import React from 'react';
import { Input } from '../../../ui/input';
import { Field, SectionHeader } from '../shared/primitives';

export const StepSolicitante = ({ form, setForm }) => (
  <div>
    <SectionHeader
      title="1. Identificação do Solicitante"
      subtitle="Dados da parte que solicita a avaliação."
    />
    <div className="grid grid-cols-2 gap-4">
      <Field label="Número do PTAM">
        <Input
          value={form.numero_ptam || ''}
          readOnly
          disabled
          placeholder="Será gerado ao salvar"
          className="bg-gray-100 text-gray-500 cursor-not-allowed"
        />
      </Field>
      <Field label="Nome do Solicitante">
        <Input value={form.solicitante_nome} onChange={(e) => setForm({ ...form, solicitante_nome: e.target.value })} placeholder="Nome completo ou razão social" />
      </Field>
      <Field label="CPF / CNPJ">
        <Input value={form.solicitante_cpf_cnpj} onChange={(e) => setForm({ ...form, solicitante_cpf_cnpj: e.target.value })} placeholder="000.000.000-00" />
      </Field>
      <Field label="Telefone">
        <Input value={form.solicitante_telefone} onChange={(e) => setForm({ ...form, solicitante_telefone: e.target.value })} placeholder="(99) 99999-9999" />
      </Field>
      <Field label="E-mail">
        <Input type="email" value={form.solicitante_email} onChange={(e) => setForm({ ...form, solicitante_email: e.target.value })} placeholder="email@exemplo.com.br" />
      </Field>
      <Field label="Endereço do Solicitante" full>
        <Input value={form.solicitante_endereco} onChange={(e) => setForm({ ...form, solicitante_endereco: e.target.value })} placeholder="Rua, número, bairro, cidade – UF, CEP" />
      </Field>
    </div>
  </div>
);
