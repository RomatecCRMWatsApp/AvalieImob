// @module ptam/steps/StepRegiao — Step 4: Caracterização da Região (zoneamento, infraestrutura, mercado)
import React from 'react';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { SectionHeader, AiButton } from '../shared/primitives';

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
        <Select value={form.zoneamento || ''} onValueChange={(v) => setForm({ ...form, zoneamento: v })}>
          <SelectTrigger className="max-w-xs"><SelectValue placeholder="Selecione o zoneamento..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="ZR1">ZR1 — Zona Residencial 1</SelectItem>
            <SelectItem value="ZR2">ZR2 — Zona Residencial 2</SelectItem>
            <SelectItem value="ZR3">ZR3 — Zona Residencial 3</SelectItem>
            <SelectItem value="ZC">ZC — Zona Comercial</SelectItem>
            <SelectItem value="ZCI">ZCI — Zona Comercial e Industrial</SelectItem>
            <SelectItem value="ZI">ZI — Zona Industrial</SelectItem>
            <SelectItem value="ZEI">ZEI — Zona de Expansão Industrial</SelectItem>
            <SelectItem value="ZRu">ZRu — Zona Rural</SelectItem>
            <SelectItem value="ZEIS">ZEIS — Zona Especial de Interesse Social</SelectItem>
            <SelectItem value="outro">Outro (especificar nas observações)</SelectItem>
          </SelectContent>
        </Select>
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
