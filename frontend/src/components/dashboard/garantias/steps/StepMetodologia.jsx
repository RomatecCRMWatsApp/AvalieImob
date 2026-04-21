// @module Garantias/steps/StepMetodologia — Bancário: Step 5 — Metodologia Avaliatória e Amostras

import React from 'react';
import { SectionTitle, Field, Input, Select, Textarea } from './shared.js';

const StepMetodologia = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Caracterização do Imóvel</SectionTitle>
    <Field label="Características Construtivas">
      <Textarea
        value={form.descricao_bem}
        onChange={(e) => set('descricao_bem', e.target.value)}
        rows={4}
        placeholder="Estrutura, alvenaria, cobertura, instalações, acabamentos..."
      />
    </Field>
    <Field label="Infraestrutura do Entorno">
      <Textarea
        value={form.infraestrutura_entorno}
        onChange={(e) => set('infraestrutura_entorno', e.target.value)}
        rows={3}
        placeholder="Ruas pavimentadas, iluminação, saneamento, transporte público, comércio, serviços..."
      />
    </Field>
    <Field label="Liquidez e Absorção de Mercado">
      <Textarea
        value={form.liquidez_mercado}
        onChange={(e) => set('liquidez_mercado', e.target.value)}
        rows={3}
        placeholder="Tempo médio de venda, demanda, oferta, tendência do mercado local..."
      />
    </Field>

    <SectionTitle>Metodologia Avaliatória (NBR 14653-1:2019)</SectionTitle>
    <Field label="Método Utilizado" required hint="Método Comparativo Direto é prioritário conforme CMN 4.676/2018">
      <Select value={form.metodologia} onChange={(e) => set('metodologia', e.target.value)}>
        <option value="">Selecionar...</option>
        <option value="comparativo_direto">Método Comparativo Direto de Dados de Mercado (prioritário)</option>
        <option value="evolutivo">Método Evolutivo / Custo de Reprodução</option>
        <option value="renda">Método da Renda</option>
        <option value="involutivo">Método Involutivo</option>
      </Select>
    </Field>
    <Field label="Fundamentação Legal">
      <Input value={form.fundamentacao_legal} onChange={(e) => set('fundamentacao_legal', e.target.value)} />
    </Field>

    <SectionTitle>Tratamento de Amostras</SectionTitle>
    <div className="grid md:grid-cols-3 gap-4">
      <Field label="Número de Amostras" hint="Mínimo 3 (Grau III) | 5+ (Grau II)">
        <Input type="number" value={form.num_amostras} onChange={(e) => set('num_amostras', parseInt(e.target.value) || 0)} />
      </Field>
      <Field label="Coeficiente de Variação (%)" hint="Máximo 30% (NBR 14653-2)">
        <Input
          type="number"
          value={form.coeficiente_variacao}
          onChange={(e) => set('coeficiente_variacao', parseFloat(e.target.value) || 0)}
          className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 bg-white ${
            form.coeficiente_variacao > 30 ? 'border-red-400 focus:ring-red-400' : 'border-gray-200 focus:ring-emerald-500'
          }`}
        />
        {form.coeficiente_variacao > 30 && (
          <p className="text-xs text-red-600 mt-1">Coeficiente superior a 30% — revisar amostragem (NBR 14653-2)</p>
        )}
      </Field>
      <Field label="Grau de Precisão" required>
        <Select value={form.grau_precisao} onChange={(e) => set('grau_precisao', e.target.value)}>
          <option value="II">Grau II</option>
          <option value="III">Grau III</option>
        </Select>
      </Field>
    </div>
    <Field label="Fatores de Homogeneização Aplicados">
      <Textarea
        value={form.fator_homogeneizacao}
        onChange={(e) => set('fator_homogeneizacao', e.target.value)}
        rows={3}
        placeholder="Fator área, padrão construtivo, localização, estado de conservação, fator de oferta..."
      />
    </Field>
    <Field label="Mercado de Referência / Fontes">
      <Textarea
        value={form.mercado_referencia}
        onChange={(e) => set('mercado_referencia', e.target.value)}
        rows={3}
        placeholder="Anúncios, negócios realizados, pesquisas de campo, portais imobiliários..."
      />
    </Field>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Grau de Fundamentação (NBR 14653-1)">
        <Select value={form.grau_fundamentacao} onChange={(e) => set('grau_fundamentacao', e.target.value)}>
          <option value="">Selecionar...</option>
          <option value="I">Grau I</option>
          <option value="II">Grau II</option>
          <option value="III">Grau III</option>
        </Select>
      </Field>
    </div>
  </div>
);

export default StepMetodologia;
