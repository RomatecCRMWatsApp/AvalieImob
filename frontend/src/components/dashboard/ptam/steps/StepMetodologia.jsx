// @module ptam/steps/StepMetodologia — Step 7: Metodologia (método avaliativo ABNT NBR 14653)
import React from 'react';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { SectionHeader, AiButton } from '../shared/primitives';

export const StepMetodologia = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="7. Metodologia"
      subtitle="Método avaliativo adotado conforme ABNT NBR 14.653."
    />
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Método escolhido</label>
        <Select value={form.methodology} onValueChange={(v) => setForm({ ...form, methodology: v })}>
          <SelectTrigger className="max-w-md"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="Método Comparativo Direto de Dados de Mercado">Método Comparativo Direto de Dados de Mercado</SelectItem>
            <SelectItem value="Método Evolutivo">Método Evolutivo</SelectItem>
            <SelectItem value="Método Involutivo">Método Involutivo</SelectItem>
            <SelectItem value="Método da Renda">Método da Renda</SelectItem>
            <SelectItem value="Método do Custo de Reprodução">Método do Custo de Reprodução</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Justificativa e fundamentação do método</label>
        <Textarea
          value={form.methodology_justification || ''}
          onChange={(e) => setForm({ ...form, methodology_justification: e.target.value })}
          rows={6}
          placeholder="Justifique tecnicamente a escolha do método conforme as características do imóvel e disponibilidade de dados..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('methodology_justification')} loading={aiLoading === 'methodology_justification'} />
        </div>
      </div>
    </div>
  </div>
);
