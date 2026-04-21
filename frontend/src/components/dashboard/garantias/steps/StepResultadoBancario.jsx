// @module Garantias/steps/StepResultadoBancario — Bancário: Step 6 — Resultado, Valores e Alienação Fiduciária

import React, { useEffect } from 'react';
import { SectionTitle, Field, Input, Select, Textarea, isAlienacao } from './shared.js';

const StepResultadoBancario = ({ form, set }) => {
  const vm      = Number(form.valor_mercado) || 0;
  const ltv     = Number(form.ltv_maximo) || 80;
  const descVlf = Number(form.fator_desconto_vlf) || 0;

  const valorMaxGarantia = vm * (ltv / 100);
  const vlf       = vm * (1 - descVlf / 100);
  const v1Leilao  = vm * 0.90; // Art. 27 §1 Lei 9.514/97 — não inferior a 90% do valor avaliação
  const v2Leilao  = Math.max(vlf, vm * 0.50); // Art. 27 §2 — não inferior ao valor da dívida

  useEffect(() => {
    if (vm > 0) {
      set('valor_maximo_garantia', parseFloat(valorMaxGarantia.toFixed(2)));
      set('campo_arbitrio_min', parseFloat((vm * 0.85).toFixed(2)));
      set('campo_arbitrio_max', parseFloat((vm * 1.15).toFixed(2)));
    }
    if (isAlienacao(form) && vm > 0) {
      set('valor_liquidacao_forcada', parseFloat(vlf.toFixed(2)));
      set('valor_1o_leilao', parseFloat(v1Leilao.toFixed(2)));
      set('valor_2o_leilao', parseFloat(v2Leilao.toFixed(2)));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vm, ltv, descVlf]);

  const fmt = (v) => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  return (
    <div className="space-y-6">
      <SectionTitle>Resultado da Avaliação</SectionTitle>
      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Valor de Mercado (R$)" required>
          <input
            type="number"
            value={form.valor_mercado}
            onChange={(e) => set('valor_mercado', parseFloat(e.target.value) || 0)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
          />
        </Field>
        <Field label="Valor por Extenso" required>
          <Input
            value={form.resultado_em_extenso}
            onChange={(e) => set('resultado_em_extenso', e.target.value)}
            placeholder="Ex.: Um milhão e duzentos mil reais"
          />
        </Field>
        <Field label="Intervalo Inferior — Campo de Arbítrio −15% (R$)">
          <Input type="number" value={form.campo_arbitrio_min} onChange={(e) => set('campo_arbitrio_min', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Intervalo Superior — Campo de Arbítrio +15% (R$)">
          <Input type="number" value={form.campo_arbitrio_max} onChange={(e) => set('campo_arbitrio_max', parseFloat(e.target.value) || 0)} />
        </Field>
      </div>

      {vm > 0 && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 space-y-3">
          <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider">Resumo dos Valores</div>
          <div className="grid md:grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-gray-500">Valor de Mercado</div>
              <div className="text-2xl font-bold text-emerald-900">{fmt(vm)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Valor Máximo de Garantia ({ltv}% LTV)</div>
              <div className="text-lg font-bold text-emerald-800">{fmt(valorMaxGarantia)}</div>
            </div>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Valor Máximo de Garantia — LTV (R$)" hint={`${ltv}% do valor de mercado`}>
          <Input type="number" value={form.valor_maximo_garantia} onChange={(e) => set('valor_maximo_garantia', parseFloat(e.target.value) || 0)} />
        </Field>
        <Field label="Grau de Precisão (NBR 14653-1)" required>
          <Select value={form.grau_precisao} onChange={(e) => set('grau_precisao', e.target.value)}>
            <option value="II">Grau II</option>
            <option value="III">Grau III</option>
          </Select>
        </Field>
      </div>

      {isAlienacao(form) && (
        <div className="space-y-4">
          <SectionTitle>Alienação Fiduciária — Lei 9.514/1997</SectionTitle>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
            Valores calculados automaticamente com base no valor de mercado e fator de desconto. Revise e ajuste se necessário.
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Fator de Desconto VLF (%)" hint="Justifique tecnicamente o desconto aplicado">
              <Input type="number" value={form.fator_desconto_vlf} onChange={(e) => set('fator_desconto_vlf', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Valor de Liquidação Forçada — VLF (R$)" required>
              <Input type="number" value={form.valor_liquidacao_forcada} onChange={(e) => set('valor_liquidacao_forcada', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Valor do 1º Leilão (R$)" hint="Art. 27 Lei 9.514/97 — mínimo 90% do valor de avaliação">
              <Input type="number" value={form.valor_1o_leilao} onChange={(e) => set('valor_1o_leilao', parseFloat(e.target.value) || 0)} />
            </Field>
            <Field label="Valor do 2º Leilão (R$)" hint="Art. 27 §2 Lei 9.514/97 — mínimo valor da dívida ou VLF">
              <Input type="number" value={form.valor_2o_leilao} onChange={(e) => set('valor_2o_leilao', parseFloat(e.target.value) || 0)} />
            </Field>
          </div>
          {form.valor_mercado > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 grid grid-cols-3 gap-4 text-center text-xs">
              <div>
                <div className="text-gray-500 mb-1">VLF</div>
                <div className="font-bold text-amber-900">{fmt(form.valor_liquidacao_forcada)}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">1º Leilão</div>
                <div className="font-bold text-amber-900">{fmt(form.valor_1o_leilao)}</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">2º Leilão</div>
                <div className="font-bold text-amber-900">{fmt(form.valor_2o_leilao)}</div>
              </div>
            </div>
          )}
          <Field label="Justificativa do Fator de Desconto VLF">
            <Textarea
              value={form.fatores_depreciacao}
              onChange={(e) => set('fatores_depreciacao', e.target.value)}
              rows={3}
              placeholder="Justifique tecnicamente o fator de desconto aplicado (liquidez, restrições, mercado, etc.)"
            />
          </Field>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <Field label="Data de Avaliação" required>
          <Input type="date" value={form.data_avaliacao} onChange={(e) => set('data_avaliacao', e.target.value)} />
        </Field>
        <Field label="Data de Validade do Laudo" hint="12 meses para SFH/FGTS (Circ. BACEN 3.818/2016)">
          <Input type="date" value={form.data_validade} onChange={(e) => set('data_validade', e.target.value)} />
        </Field>
      </div>
    </div>
  );
};

export default StepResultadoBancario;
