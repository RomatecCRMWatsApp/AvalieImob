// @module ptam/steps/StepCaracterizacao — Step 5: Caracterização do Imóvel (dados físicos/construtivos)
import React, { useState } from 'react';
import { ClipboardCheck } from 'lucide-react';
import { ptamAPI } from '../../../../lib/api';
import ImportarVistoriaModal from '../ImportarVistoriaModal';
import { Button } from '../../../ui/button';
import { Input } from '../../../ui/input';
import { Textarea } from '../../../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { Field, SectionHeader, AiButton } from '../shared/primitives';
import { AreaConsideradaSelector } from '../shared/AreaConsideradaSelector';
import { AreaResumoPanel } from '../shared/AreaResumoPanel';
import RichField from '../../../ui/RichField';
import { isRuralImovel } from '../shared/amostraCategoria';
import BenfeitoriasRurais from '../BenfeitoriasRurais';

export const StepCaracterizacao = ({ form, setForm, onAi, aiLoading }) => {
  const [importOpen, setImportOpen] = useState(false);
  const recarregar = async () => {
    if (!form.id) return;
    try {
      const fresh = await ptamAPI.get(form.id);
      setForm((f) => ({ ...f, ...fresh }));
    } catch { /* ignora */ }
  };
  return (
  <div>
    <div className="flex items-start justify-between gap-2">
      <SectionHeader
        title="5. Caracterização do Imóvel"
        subtitle="Características físicas e construtivas do imóvel avaliando."
      />
      {form.id && (
        <Button type="button" size="sm" variant="outline"
          onClick={() => setImportOpen(true)}
          className="gap-1 text-emerald-700 border-emerald-200 hover:bg-emerald-50 flex-shrink-0">
          <ClipboardCheck className="w-4 h-4" /> Importar de Vistoria
        </Button>
      )}
    </div>
    {importOpen && form.id && (
      <ImportarVistoriaModal
        ptamId={form.id}
        onClose={() => setImportOpen(false)}
        onImported={recarregar}
      />
    )}
    <div className="grid grid-cols-2 gap-4">
      <Field label="Área do terreno (m²)">
        <Input type="number" step="0.01" value={form.imovel_area_terreno} onChange={(e) => setForm({ ...form, imovel_area_terreno: Number(e.target.value) })} />
      </Field>
      <Field label="Área construída (m²)">
        <Input type="number" step="0.01" value={form.imovel_area_construida} onChange={(e) => setForm({ ...form, imovel_area_construida: Number(e.target.value) })} />
      </Field>
      <AreaConsideradaSelector
        terrenoM2={Number(form.imovel_area_terreno) || 0}
        construidaM2={Number(form.imovel_area_construida) || 0}
        tipoImovel={form.property_type}
        value={Number(form.imovel_area_a_considerar) || 0}
        onChange={(m2) => setForm((f) => ({ ...f, imovel_area_a_considerar: m2 > 0 ? m2 : null }))}
        onOpcaoChange={(op) => {
          if (op === 'soma') setForm((f) => ({ ...f, methodology: 'Método Evolutivo' }));
        }}
      />
      <AreaResumoPanel
        value={Number(form.imovel_area_a_considerar) || 0}
        onChange={(m2) => setForm((f) => ({ ...f, imovel_area_a_considerar: m2 > 0 ? m2 : null }))}
        tipoImovel={form.property_type}
      />
      <div className="col-span-2 -mt-1">
        <p className="text-xs text-gray-500">
          Esta é a área que o sistema usará para calcular o valor final (Valor Total = Valor R$/m² × Área considerada).
          Pode ser igual à área do terreno, à área construída ou outro valor definido pelo avaliador.
        </p>
      </div>
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
      {/* Ambientes (quantidade) — mesmos campos das amostras; só vão ao laudo se > 0 */}
      <div className="col-span-2 mt-1">
        <span className="block text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-2">
          Ambientes (quantidade — só vai ao laudo se maior que 0)
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            ['imovel_sala_estar', 'Sala de estar'],
            ['imovel_sala_jantar', 'Sala de jantar/copa'],
            ['imovel_cozinha', 'Cozinha'],
            ['imovel_quarto_social', 'Quarto social'],
            ['imovel_suite_simples', 'Suíte simples'],
            ['imovel_suite_master', 'Suíte master'],
            ['imovel_banheiro_social', 'Banheiro social'],
            ['imovel_lavabo', 'Lavabo'],
            ['imovel_area_servico', 'Área de serviço'],
            ['imovel_varanda', 'Varanda/sacada'],
            ['imovel_varanda_gourmet', 'Varanda gourmet'],
            ['imovel_escritorio', 'Escritório'],
            ['imovel_despensa', 'Despensa'],
            ['imovel_num_piscinas', 'Piscina'],
            ['imovel_num_vagas', 'Garagem'],
          ].map(([k, lbl]) => (
            <Field key={k} label={lbl}>
              <Input type="number" min="0" value={form[k] || ''} onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })} />
            </Field>
          ))}
        </div>
      </div>
      <Field label="Características adicionais / benfeitorias" full>
        <RichField form={form} setForm={setForm} field="imovel_caracteristicas_adicionais" minHeight={100}
          placeholder="Descreva acabamentos, instalações, reformas, itens diferenciados..." />
        <div className="mt-1 flex justify-end">
          <AiButton onClick={() => onAi('imovel_caracteristicas_adicionais')} loading={aiLoading === 'imovel_caracteristicas_adicionais'} />
        </div>
      </Field>

      {/* Benfeitorias estruturadas — somente imóvel rural */}
      {isRuralImovel(form.property_type) && (
        <BenfeitoriasRurais form={form} setForm={setForm} />
      )}
    </div>
  </div>
  );
};
