// @module Garantias/steps/StepLocalizacao — Rural: Step 4 — Localização, GPS e Vistoria

import React from 'react';
import { SectionTitle, Field, Input, Select, Textarea, UF_OPTIONS } from './shared.js';

const StepLocalizacao = ({ form, set }) => (
  <div className="space-y-6">
    <SectionTitle>Localização</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Endereço">
        <Input value={form.endereco} onChange={(e) => set('endereco', e.target.value)} placeholder="Rua, número, complemento..." />
      </Field>
      <Field label="Município" required>
        <Input value={form.municipio} onChange={(e) => set('municipio', e.target.value)} />
      </Field>
      <Field label="UF">
        <Select value={form.uf} onChange={(e) => set('uf', e.target.value)}>
          <option value="">Selecionar UF</option>
          {UF_OPTIONS.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
        </Select>
      </Field>
      <Field label="CEP">
        <Input value={form.cep} onChange={(e) => set('cep', e.target.value)} placeholder="00000-000" />
      </Field>
      <Field label="Matrícula / NIRF">
        <Input value={form.matricula} onChange={(e) => set('matricula', e.target.value)} />
      </Field>
      <Field label="Cartório de Registro">
        <Input value={form.cartorio} onChange={(e) => set('cartorio', e.target.value)} />
      </Field>
    </div>

    <SectionTitle>Coordenadas GPS</SectionTitle>
    <div className="grid md:grid-cols-2 gap-4">
      <Field label="Latitude">
        <Input value={form.gps_lat} onChange={(e) => set('gps_lat', e.target.value)} placeholder="-12.345678" />
      </Field>
      <Field label="Longitude">
        <Input value={form.gps_lng} onChange={(e) => set('gps_lng', e.target.value)} placeholder="-55.123456" />
      </Field>
    </div>

    <SectionTitle>Vistoria</SectionTitle>
    <Field label="Data da Vistoria">
      <Input type="date" value={form.data_vistoria} onChange={(e) => set('data_vistoria', e.target.value)} />
    </Field>
    <Field label="Observações da Vistoria">
      <Textarea value={form.observacoes} onChange={(e) => set('observacoes', e.target.value)} rows={3} />
    </Field>
  </div>
);

export default StepLocalizacao;
