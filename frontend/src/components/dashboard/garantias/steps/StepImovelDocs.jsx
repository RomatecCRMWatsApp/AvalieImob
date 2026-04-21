// @module Garantias/steps/StepImovelDocs — Bancário: Step 3 — Imóvel, Documentação e Regularidade

import React from 'react';
import { SectionTitle, Field, Input, Select, Textarea, Checkbox, UF_OPTIONS, isSfhFgts } from './shared.js';

const StepImovelDocs = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Endereço e Registro</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Endereço Completo" required className="md:col-span-2">
        <Input value={form.endereco} onChange={(e) => set('endereco', e.target.value)} placeholder="Rua, número, complemento..." />
      </Field>
      <Field label="Município" required>
        <Input value={form.municipio} onChange={(e) => set('municipio', e.target.value)} />
      </Field>
      <Field label="UF">
        <Select value={form.uf} onChange={(e) => set('uf', e.target.value)}>
          <option value="">Selecionar...</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="CEP">
        <Input value={form.cep} onChange={(e) => set('cep', e.target.value)} placeholder="00000-000" />
      </Field>
      <Field label="Matrícula do Imóvel" required hint="Certidão com no máximo 30 dias (CMN 4.676/2018)">
        <Input value={form.matricula} onChange={(e) => set('matricula', e.target.value)} />
      </Field>
      <Field label="Data da Certidão de Matrícula" hint="Máximo 30 dias de emissão">
        <Input type="date" value={form.data_matricula} onChange={(e) => set('data_matricula', e.target.value)} />
      </Field>
      <Field label="Cartório de Registro de Imóveis (CRI)" required>
        <Input value={form.cartorio} onChange={(e) => set('cartorio', e.target.value)} placeholder="Cartório de Registro de Imóveis de..." />
      </Field>
      <Field label="Número do CRI">
        <Input value={form.cri_numero} onChange={(e) => set('cri_numero', e.target.value)} />
      </Field>
    </div>

    <SectionTitle>Dados Fiscais</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Inscrição IPTU">
        <Input value={form.inscricao_iptu} onChange={(e) => set('inscricao_iptu', e.target.value)} />
      </Field>
      <Field label="Valor Venal (R$)" hint="Conforme carnê de IPTU">
        <Input type="number" value={form.valor_venal} onChange={(e) => set('valor_venal', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>

    <SectionTitle>Características Físicas (NBR 14653-2:2011)</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Área do Terreno (m²)">
        <Input type="number" value={form.area_total_ha} onChange={(e) => set('area_total_ha', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Área Construída Total (m²)">
        <Input type="number" value={form.area_construida_m2} onChange={(e) => set('area_construida_m2', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Área Privativa NBR 12.721 (m²)" required hint="Conforme memorial da incorporadora / CRI">
        <Input type="number" value={form.area_privativa_nbr12721} onChange={(e) => set('area_privativa_nbr12721', parseFloat(e.target.value) || 0)} />
      </Field>
      <Field label="Padrão Construtivo IBAPE" required>
        <Select value={form.padrao_construtivo_ibape} onChange={(e) => set('padrao_construtivo_ibape', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="baixo">Baixo</option>
          <option value="normal">Normal</option>
          <option value="alto">Alto</option>
          <option value="luxo">Luxo</option>
        </Select>
      </Field>
      <Field label="Idade Real (anos)">
        <Input type="number" value={form.idade_real_anos} onChange={(e) => set('idade_real_anos', parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Idade Aparente (anos)">
        <Input type="number" value={form.idade_aparente_anos} onChange={(e) => set('idade_aparente_anos', parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Estado de Conservação">
        <Select value={form.estado_conservacao} onChange={(e) => set('estado_conservacao', e.target.value)}>
          <option value="otimo">Ótimo</option>
          <option value="bom">Bom</option>
          <option value="regular">Regular</option>
          <option value="precario">Precário</option>
        </Select>
      </Field>
    </div>

    <SectionTitle>Regularidade Jurídica</SectionTitle>
    <div className="space-y-3">
      <Checkbox
        checked={form.habite_se}
        onChange={(v) => set('habite_se', v)}
        label="Imóvel possui Habite-se / Carta de Habitação (obrigatório SFH/FGTS)"
      />
      <Checkbox
        checked={form.onus_reais}
        onChange={(v) => set('onus_reais', v)}
        label="Existência de ônus reais na matrícula"
      />
      {form.onus_reais && (
        <Field label="Descrição dos Ônus Reais">
          <Textarea value={form.onus_descricao} onChange={(e) => set('onus_descricao', e.target.value)} placeholder="Descreva as gravames, hipotecas, penhoras, etc." />
        </Field>
      )}
      <Checkbox
        checked={form.conformidade_plano_diretor}
        onChange={(v) => set('conformidade_plano_diretor', v)}
        label="Imóvel em conformidade com o Plano Diretor Municipal"
      />
      <Checkbox
        checked={form.regularidade_construtiva}
        onChange={(v) => set('regularidade_construtiva', v)}
        label="Regularidade construtiva (construção conforme aprovação)"
      />
    </div>

    {isSfhFgts(form) && (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-800">
        <strong>SFH/FGTS:</strong> Imóvel não pode ter sido adquirido com FGTS nos últimos 3 anos (Lei 8.036/1990 art. 20). Matrícula não pode estar em nome de Pessoa Jurídica.
      </div>
    )}
  </div>
);

export default StepImovelDocs;
