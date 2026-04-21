// @module Semoventes/steps/Step5Sanitaria — Step 5 — Situação Sanitária (vacinações, testes, GTA)

import React from 'react';
import { SectionTitle, Field, Inp, Sel, CheckRow } from './shared.js';

const Step5Sanitaria = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Situação Sanitária — IN MAPA 48/2020</SectionTitle>

    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Data Vacina Aftosa" hint="Obrigatória em todo o território nacional">
        <Inp type="date" value={form.vacina_aftosa_data} onChange={(e) => set('vacina_aftosa_data', e.target.value)} />
      </Field>
      <Field label="Órgão / Campanha Aftosa">
        <Inp value={form.vacina_aftosa_orgao} onChange={(e) => set('vacina_aftosa_orgao', e.target.value)} placeholder="Ex.: INDEA-MT Campanha Mai/2024" />
      </Field>
      <Field label="Data Vacina Brucelose">
        <Inp type="date" value={form.vacina_brucelose_data} onChange={(e) => set('vacina_brucelose_data', e.target.value)} />
      </Field>
      <Field label="Teste de Tuberculose">
        <Sel value={form.teste_tuberculose} onChange={(e) => set('teste_tuberculose', e.target.value)}>
          <option value="nao_realizado">Não Realizado</option>
          <option value="negativo">Negativo</option>
          <option value="positivo">Positivo</option>
          <option value="inconclusivo">Inconclusivo</option>
        </Sel>
      </Field>
      {form.teste_tuberculose !== 'nao_realizado' && (
        <Field label="Data do Teste de Tuberculose">
          <Inp type="date" value={form.teste_tuberculose_data} onChange={(e) => set('teste_tuberculose_data', e.target.value)} />
        </Field>
      )}
      <Field label="Data Vermifugação">
        <Inp type="date" value={form.vermifugacao_data} onChange={(e) => set('vermifugacao_data', e.target.value)} />
      </Field>
      <Field label="Produto Vermífugo">
        <Inp value={form.vermifugacao_produto} onChange={(e) => set('vermifugacao_produto', e.target.value)} placeholder="Nome comercial / princípio ativo" />
      </Field>
      <Field label="Mortalidade Estimada (%)" hint="Nos últimos 12 meses">
        <Inp type="number" value={form.mortalidade_percentual} onChange={(e) => set('mortalidade_percentual', parseFloat(e.target.value) || 0)} />
      </Field>
    </div>

    <div className="space-y-3">
      <CheckRow
        label="Área Livre de Febre Aftosa"
        checked={form.area_livre_aftosa}
        onChange={(v) => set('area_livre_aftosa', v)}
        hint="Conforme portaria estadual vigente"
      />
      <CheckRow
        label="GTA (Guia de Trânsito Animal) em dia"
        checked={form.gta_em_dia}
        onChange={(v) => set('gta_em_dia', v)}
        hint="Obrigatória para movimentação e penhor"
      />
    </div>
  </div>
);

export default Step5Sanitaria;
