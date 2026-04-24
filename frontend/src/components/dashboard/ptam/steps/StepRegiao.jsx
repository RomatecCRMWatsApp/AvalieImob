// @module ptam/steps/StepRegiao — Step 4: Caracterização da Região (zoneamento, infraestrutura, mercado)
import React from 'react';
import { Textarea } from '../../../ui/textarea';
import { SectionHeader, AiButton } from '../shared/primitives';
import { SelectZoneamento } from '../../../common/SelectZoneamento';

const REGION_FIELDS = [
  { key: 'regiao_infraestrutura',    label: 'Infraestrutura Urbana', placeholder: 'Pavimentação, iluminação, calçadas, drenagem pluvial...' },
  { key: 'regiao_servicos_publicos', label: 'Serviços Públicos', placeholder: 'Água, esgoto, energia elétrica, coleta de lixo, transporte...' },
  { key: 'regiao_uso_predominante',  label: 'Uso Predominante do Solo', placeholder: 'Residencial unifamiliar, misto, comercial...' },
  { key: 'regiao_padrao_construtivo',label: 'Padrão Construtivo da Região', placeholder: 'Alto / médio / simples — características predominantes...' },
  { key: 'regiao_tendencia_mercado', label: 'Tendência de Mercado', placeholder: 'Valorização, estabilidade, desvalorização — fatores...' },
  { key: 'regiao_observacoes',       label: 'Observações Complementares', placeholder: 'Outros aspectos relevantes da região...' },
];

export const StepRegiao = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="4. Caracterização da Região"
      subtitle="Descreva as características do entorno e do mercado local."
    />

    <div className="mb-5">
      <label className="block text-sm font-medium text-gray-700 mb-1.5">
        Zoneamento (Plano Diretor) <span className="text-xs text-gray-400">— NBR 14653-2</span>
      </label>
      <div className="flex gap-2 items-center">
        <SelectZoneamento
          value={form.zoneamento || ''}
          onChange={(v) => setForm({ ...form, zoneamento: v })}
          municipio={form.property_city || ''}
        />
        <span className="text-xs text-gray-400">ou informe nas observações</span>
      </div>
    </div>

    <div className="space-y-5">
      {REGION_FIELDS.map((f) => (
        <div key={f.key}>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
          <Textarea
            value={form[f.key] || ''}
            onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
            rows={3}
            placeholder={f.placeholder}
          />
          <div className="mt-1 flex justify-end">
            <AiButton onClick={() => onAi(f.key)} loading={aiLoading === f.key} />
          </div>
        </div>
      ))}
    </div>
  </div>
);
