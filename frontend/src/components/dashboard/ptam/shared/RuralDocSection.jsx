// @module ptam/shared/RuralDocSection — Documentação específica de imóvel rural (SIGEF, INCRA, CCIR, CAR, ITR)
import React from 'react';
import { Input } from '../../../ui/input';
import { Field } from './primitives';
import ImageUploader from '../ImageUploader';

const RURAL_TYPES = new Set(['rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural']);
export const isRural = (tipo) => RURAL_TYPES.has((tipo || '').toLowerCase());

const RuralDocSection = ({ form, setForm }) => {
  if (!isRural(form.property_type)) return null;
  return (
    <div className="col-span-2 mt-2">
      <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50/50 p-5">
        <div className="text-sm font-semibold text-emerald-800 mb-4 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
          Registros Rurais
          <span className="text-xs font-normal text-emerald-600 ml-1">— documentação específica de imóvel rural</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Certificacao SIGEF (UUID)">
            <Input
              value={form.certificacao_sigef || ''}
              onChange={(e) => setForm({ ...form, certificacao_sigef: e.target.value })}
              placeholder="b533967e-f6b0-4b19-b4a1-fc834e1f9ebb"
            />
          </Field>
          <Field label="Codigo do Imovel Rural (INCRA)">
            <Input
              value={form.cadastro_incra || ''}
              onChange={(e) => setForm({ ...form, cadastro_incra: e.target.value })}
              placeholder="950.203.934.550-0"
            />
          </Field>
          <Field label="Numero do CCIR">
            <Input
              value={form.ccir || ''}
              onChange={(e) => setForm({ ...form, ccir: e.target.value })}
              placeholder="76280733267"
            />
          </Field>
          <Field label="CIB / NIRF">
            <Input
              value={form.nirf_cib || ''}
              onChange={(e) => setForm({ ...form, nirf_cib: e.target.value })}
              placeholder="5.690.070-8"
            />
          </Field>
          <Field label="Registro no CAR" full>
            <Input
              value={form.car || ''}
              onChange={(e) => setForm({ ...form, car: e.target.value })}
              placeholder="MA-2100055-F942.2E73.176D.42D5.B1C6.6A2F.01F5.B64F"
            />
          </Field>
          <Field label="Perímetro (m)">
            <Input
              type="number"
              step="0.01"
              value={form.perimetro_m ?? ''}
              onChange={(e) => setForm({ ...form, perimetro_m: e.target.value === '' ? null : Number(e.target.value) })}
              placeholder="Perímetro total em metros"
            />
          </Field>
        </div>

        <div className="mt-5 space-y-5">
          <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">Documentos Rurais — Upload</div>

          <ImageUploader
            label="Mapa Georreferenciado / Certificado SIGEF"
            images={form.doc_mapa_sigef || []}
            onImagesChange={(ids) => setForm({ ...form, doc_mapa_sigef: ids })}
            maxImages={3}
          />

          <ImageUploader
            label="Memorial Descritivo Topográfico / SIGEF"
            images={form.doc_memorial_descritivo || []}
            onImagesChange={(ids) => setForm({ ...form, doc_memorial_descritivo: ids })}
            maxImages={3}
          />

          <ImageUploader
            label="CCIR — Certificado de Cadastro de Imóvel Rural"
            images={form.doc_ccir || []}
            onImagesChange={(ids) => setForm({ ...form, doc_ccir: ids })}
            maxImages={3}
          />

          <div>
            <ImageUploader
              label="ITR — Imposto Territorial Rural"
              images={form.doc_itr || []}
              onImagesChange={(ids) => setForm({ ...form, doc_itr: ids })}
              maxImages={5}
            />
            <p className="text-xs text-emerald-700 mt-1">Envie os últimos 5 exercícios (máx. 5 arquivos)</p>
          </div>

          <ImageUploader
            label="CAR — Cadastro Ambiental Rural"
            images={form.doc_car || []}
            onImagesChange={(ids) => setForm({ ...form, doc_car: ids })}
            maxImages={3}
          />
        </div>
      </div>
    </div>
  );
};

export default RuralDocSection;
