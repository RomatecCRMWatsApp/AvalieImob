// @module Garantias/steps/StepDeclaracoes — Bancário: Step 7 — Declarações, Responsável Técnico e ART

import React from 'react';
import { AlertaCRECI, SectionTitle, Field, Input, Select, Textarea, Checkbox, UF_OPTIONS } from './shared.js';

const StepDeclaracoes = ({ form, set }) => (
  <div className="space-y-6">
    <AlertaCRECI />

    <SectionTitle>Responsável Técnico (CREA/CAU obrigatório)</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Tipo de Profissional" required>
        <Select value={form.responsavel_tipo} onChange={(e) => set('responsavel_tipo', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="engenheiro">Engenheiro Civil (CREA)</option>
          <option value="arquiteto">Arquiteto e Urbanista (CAU)</option>
        </Select>
      </Field>
      <Field label="Nome do Profissional" required>
        <Input
          value={form.responsavel?.nome}
          onChange={(e) => set('responsavel', { ...form.responsavel, nome: e.target.value })}
          placeholder="Nome completo"
        />
      </Field>
      <Field label="Número CREA ou CAU" required>
        <Input
          value={form.responsavel_crea_cau}
          onChange={(e) => set('responsavel_crea_cau', e.target.value)}
          placeholder="CREA-SP 123456789 ou CAU A000000-0"
        />
      </Field>
      <Field label="UF do Registro">
        <Select value={form.responsavel_uf} onChange={(e) => set('responsavel_uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="Empresa / CPF" hint="Razão Social ou CPF do responsável">
        <Input value={form.responsavel_empresa_cpf} onChange={(e) => set('responsavel_empresa_cpf', e.target.value)} />
      </Field>
    </div>

    <SectionTitle>ART / RRT (Res. CONFEA 1.025/2009)</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Número da ART / RRT" required hint="Obrigatória para fins bancários">
        <Input
          value={form.art_numero}
          onChange={(e) => set('art_numero', e.target.value)}
          placeholder="Número do registro"
        />
      </Field>
      <Field label="Data de Registro da ART / RRT">
        <Input type="date" value={form.art_data_registro} onChange={(e) => set('art_data_registro', e.target.value)} />
      </Field>
    </div>

    <SectionTitle>Validade e Prazo</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Validade do Laudo (meses)" hint="12 meses para SFH/FGTS (Circ. BACEN 3.818/2016)">
        <Input
          type="number"
          value={form.validade_laudo_meses}
          onChange={(e) => set('validade_laudo_meses', parseInt(e.target.value) || 12)}
        />
      </Field>
    </div>

    <SectionTitle>Declarações Obrigatórias</SectionTitle>
    <div className="space-y-3">
      <Checkbox
        checked={form.declaracao_conflito_interesse}
        onChange={(v) => set('declaracao_conflito_interesse', v)}
        label="Declaro que não há conflito de interesse entre o profissional avaliador e as partes envolvidas na operação."
      />
    </div>
    <Field label="Declaração de Impedimentos / Restrições">
      <Textarea
        value={form.declaracao_impedimentos}
        onChange={(e) => set('declaracao_impedimentos', e.target.value)}
        rows={3}
        placeholder="Descreva impedimentos legais, relações de parentesco, vínculos ou restrições conhecidas. Se não houver, registre 'Nada a declarar'."
      />
    </Field>

    <SectionTitle>Ressalvas e Considerações Finais</SectionTitle>
    <Field label="Considerações">
      <Textarea
        value={form.consideracoes}
        onChange={(e) => set('consideracoes', e.target.value)}
        rows={3}
        placeholder="Pressupostos, limitações e considerações finais conforme NBR 14653-1:2019..."
      />
    </Field>
    <Field label="Ressalvas">
      <Textarea
        value={form.ressalvas}
        onChange={(e) => set('ressalvas', e.target.value)}
        rows={2}
        placeholder="Ressalvas aplicáveis..."
      />
    </Field>

    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Status do Laudo">
        <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
          <option value="rascunho">Rascunho</option>
          <option value="em_andamento">Em Andamento</option>
          <option value="concluido">Concluído</option>
        </Select>
      </Field>
    </div>
  </div>
);

export default StepDeclaracoes;
