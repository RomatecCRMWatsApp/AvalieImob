// @module ptam/steps/StepCaracterizacao — Step 5: Caracterização do Imóvel (dados físicos/construtivos)
import React from 'react';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field, SectionHeader, AiButton } from '../shared/primitives';

export const StepCaracterizacao = ({ form, setForm, onAi, aiLoading }) => (
  <div>
    <SectionHeader
      title="5. Caracterização do Imóvel"
      subtitle="Características físicas e construtivas do imóvel avaliando."
    />
    <div className="grid grid-cols-2 gap-4">
      <Field label="Área do terreno (m²)">
        <Input type="number" step="0.01" value={form.imovel_area_terreno} onChange={(e) => setForm({ ...form, imovel_area_terreno: Number(e.target.value) })} />
      </Field>
      <Field label="Área construída (m²)">
        <Input type="number" step="0.01" value={form.imovel_area_construida} onChange={(e) => setForm({ ...form, imovel_area_construida: Number(e.target.value) })} />
      </Field>
      <Field label="Área a ser considerada no cálculo (m²) *" full>
        <Input
          type="number"
          step="0.01"
          required
          value={form.imovel_area_a_considerar ?? ''}
          onChange={(e) => setForm({ ...form, imovel_area_a_considerar: e.target.value === '' ? null : Number(e.target.value) })}
          placeholder="Ex: 150 — informe a área que será usada para calcular o valor total"
          className="border-emerald-400 focus:ring-emerald-600"
        />
        <p className="mt-1 text-xs text-gray-500">
          Esta é a área que o sistema usará para calcular o valor final (Valor Total = Valor R$/m² × Área considerada).
          Pode ser igual à área do terreno, à área construída ou outro valor definido pelo avaliador.
        </p>
      </Field>
      <Field label="Idade do imóvel (anos)">
        <Input type="number" min="0" value={form.imovel_idade} onChange={(e) => setForm({ ...form, imovel_idade: Number(e.target.value) })} />
      </Field>
      <Field label="Estado de conservação">
        <Select value={form.imovel_estado_conservacao} onValueChange={(v) => setForm({ ...form, imovel_estado_conservacao: v })}>
          <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="otimo">Ótimo</SelectItem>
            <SelectItem value="bom">Bom</SelectItem>
            <SelectItem value="regular">Regular</SelectItem>
            <SelectItem value="ruim">Ruim</SelectItem>
            <SelectItem value="pessimo">Péssimo</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Padrão de acabamento">
        <Select value={form.imovel_padrao_acabamento} onValueChange={(v) => setForm({ ...form, imovel_padrao_acabamento: v })}>
          <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="alto">Alto</SelectItem>
            <SelectItem value="medio">Médio</SelectItem>
            <SelectItem value="simples">Simples</SelectItem>
            <SelectItem value="minimo">Mínimo</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Número de quartos">
        <Input type="number" min="0" value={form.imovel_num_quartos} onChange={(e) => setForm({ ...form, imovel_num_quartos: Number(e.target.value) })} />
      </Field>
      <Field label="Número de banheiros">
        <Input type="number" min="0" value={form.imovel_num_banheiros} onChange={(e) => setForm({ ...form, imovel_num_banheiros: Number(e.target.value) })} />
      </Field>
      <Field label="Vagas de garagem">
        <Input type="number" min="0" value={form.imovel_num_vagas} onChange={(e) => setForm({ ...form, imovel_num_vagas: Number(e.target.value) })} />
      </Field>
      <Field label="Piscina">
        <Select value={form.imovel_piscina ? 'sim' : 'nao'} onValueChange={(v) => setForm({ ...form, imovel_piscina: v === 'sim' })}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="nao">Não</SelectItem>
            <SelectItem value="sim">Sim</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field label="Características adicionais / benfeitorias" full>
        <Textarea
          value={form.imovel_caracteristicas_adicionais || ''}
          onChange={(e) => setForm({ ...form, imovel_caracteristicas_adicionais: e.target.value })}
          rows={4}
          placeholder="Descreva acabamentos, instalações, reformas, itens diferenciados..."
        />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('imovel_caracteristicas_adicionais')} loading={aiLoading === 'imovel_caracteristicas_adicionais'} />
        </div>
      </Field>
    </div>
  </div>
);
