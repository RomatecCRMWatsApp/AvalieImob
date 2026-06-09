// @module dashboard/amostras/ModalNovaAmostraUrbana — Modal completo de amostra URBANA.
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Loader2, Upload, X, Home } from 'lucide-react';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { useToast } from '../../../hooks/use-toast';
import { amostrasAPI, uploadAPI } from '../../../lib/api';
import {
  TIPOS_URBANO, TIPO_AMOSTRA_URBANO, PADRAO_CONSTRUTIVO, ESTADO_CONSERVACAO,
  AMBIENTES, hoje, num, fmtBRL, calcRsM2,
} from './amostraOptions';

const Label = ({ children }) => (
  <label className="text-xs font-semibold text-gray-600">{children}</label>
);
const inputCls =
  'w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-emerald-600';

const TextField = ({ label, value, onChange, type = 'text', placeholder = '', req = false }) => (
  <div>
    <Label>{label}{req && <span className="text-red-500"> *</span>}</Label>
    <input type={type} value={value ?? ''} placeholder={placeholder}
      onChange={(e) => onChange(type === 'number' ? e.target.value : e.target.value)} className={inputCls} />
  </div>
);
const SelectField = ({ label, value, onChange, options, req = false }) => (
  <div>
    <Label>{label}{req && <span className="text-red-500"> *</span>}</Label>
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      <option value="">—</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  </div>
);
const COL_CLS = { 2: 'grid-cols-2', 3: 'grid-cols-3', 4: 'grid-cols-4' };
const Section = ({ title, children, cols = 2 }) => (
  <div className="space-y-2">
    <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1">{title}</div>
    <div className={`grid ${COL_CLS[cols] || 'grid-cols-2'} gap-3`}>{children}</div>
  </div>
);

const empty = () => ({
  referencia: '', tipo_imovel: 'Casa', tipo_amostra: 'Oferta de Mercado',
  endereco: '', bairro: '', municipio: 'Açailândia', uf: 'MA',
  area_total_m2: '', area_construida_m2: '', area_terreno_m2: '',
  padrao_construtivo: '', estado_conservacao: '', idade_anos: '',
  valor_rs: '', fonte: '', data_coleta: hoje(), telefone_fonte: '',
  foto_url: '', planta_baixa_url: '', link_anuncio: '',
  ...Object.fromEntries(AMBIENTES.map(([k]) => [k, 0])),
});

const ModalNovaAmostraUrbana = ({ open, onClose, onSalvar, referenciaSugerida }) => {
  const { toast } = useToast();
  const [form, setForm] = useState(empty());
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState('');

  useEffect(() => {
    if (open) setForm((f) => ({ ...empty(), referencia: referenciaSugerida || f.referencia }));
  }, [open, referenciaSugerida]);

  const set = useCallback((k, v) => setForm((f) => ({ ...f, [k]: v })), []);
  const rsM2 = useMemo(() => calcRsM2(form.valor_rs, form.area_total_m2), [form.valor_rs, form.area_total_m2]);

  const handleUpload = async (campo, file) => {
    if (!file) return;
    setUploading(campo);
    try {
      const res = await uploadAPI.uploadImage(file);
      const imgId = res?.id || res?.image_id || res?.imageId;
      set(campo, imgId ? uploadAPI.getImageUrl(imgId) : (res?.url || ''));
    } catch (e) {
      toast({ title: 'Falha no upload', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setUploading(''); }
  };

  const salvar = async () => {
    if (!form.referencia || !num(form.area_total_m2) || !num(form.valor_rs) || !form.data_coleta) {
      toast({ title: 'Preencha Referência, Área Total, Valor e Data', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...form, categoria: 'urbano',
        area_total_m2: num(form.area_total_m2),
        area_construida_m2: num(form.area_construida_m2) || null,
        area_terreno_m2: num(form.area_terreno_m2) || null,
        idade_anos: num(form.idade_anos) || null,
        valor_rs: num(form.valor_rs),
        ...Object.fromEntries(AMBIENTES.map(([k]) => [k, num(form[k])])),
      };
      const saved = await amostrasAPI.create(payload);
      toast({ title: 'Amostra urbana cadastrada' });
      onSalvar?.(saved);
      onClose?.();
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose?.()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-emerald-900">
            <Home className="w-5 h-5" /> Nova Amostra — Imóvel Urbano
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          <Section title="Identificação" cols={3}>
            <TextField label="Referência" value={form.referencia} onChange={(v) => set('referencia', v)} placeholder="AM-001" req />
            <SelectField label="Tipo de Imóvel" value={form.tipo_imovel} onChange={(v) => set('tipo_imovel', v)} options={TIPOS_URBANO} req />
            <SelectField label="Tipo da Amostra" value={form.tipo_amostra} onChange={(v) => set('tipo_amostra', v)} options={TIPO_AMOSTRA_URBANO} req />
          </Section>

          <Section title="Localização" cols={4}>
            <div className="col-span-2"><TextField label="Endereço" value={form.endereco} onChange={(v) => set('endereco', v)} /></div>
            <TextField label="Bairro/Localidade" value={form.bairro} onChange={(v) => set('bairro', v)} />
            <TextField label="Município" value={form.municipio} onChange={(v) => set('municipio', v)} />
            <TextField label="UF" value={form.uf} onChange={(v) => set('uf', v)} />
          </Section>

          <Section title="Área" cols={3}>
            <TextField label="Área Total (m²)" type="number" value={form.area_total_m2} onChange={(v) => set('area_total_m2', v)} req />
            <TextField label="Área Construída (m²)" type="number" value={form.area_construida_m2} onChange={(v) => set('area_construida_m2', v)} />
            <TextField label="Área do Terreno (m²)" type="number" value={form.area_terreno_m2} onChange={(v) => set('area_terreno_m2', v)} />
          </Section>

          <Section title="Características" cols={3}>
            <SelectField label="Padrão Construtivo" value={form.padrao_construtivo} onChange={(v) => set('padrao_construtivo', v)} options={PADRAO_CONSTRUTIVO} />
            <SelectField label="Estado de Conservação" value={form.estado_conservacao} onChange={(v) => set('estado_conservacao', v)} options={ESTADO_CONSERVACAO} />
            <TextField label="Idade (anos)" type="number" value={form.idade_anos} onChange={(v) => set('idade_anos', v)} />
          </Section>

          <div className="space-y-2">
            <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 border-b border-emerald-100 pb-1">Ambientes (qtd. — só vão ao laudo se &gt; 0)</div>
            <div className="grid grid-cols-3 gap-3">
              {AMBIENTES.map(([k, lbl]) => (
                <div key={k}>
                  <Label>{lbl}</Label>
                  <input type="number" min="0" value={form[k] ?? 0}
                    onChange={(e) => set(k, e.target.value)} className={inputCls} />
                </div>
              ))}
            </div>
          </div>

          <Section title="Transação" cols={2}>
            <TextField label="Valor (R$)" type="number" value={form.valor_rs} onChange={(v) => set('valor_rs', v)} req />
            <div>
              <Label>R$/m² (calculado)</Label>
              <div className="mt-1 px-3 py-2 text-sm font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg">
                {fmtBRL(rsM2)}/m²
              </div>
            </div>
            <TextField label="Fonte" value={form.fonte} onChange={(v) => set('fonte', v)} placeholder="Imobiliária, anúncio, proprietário..." />
            <TextField label="Data da Coleta" type="date" value={form.data_coleta} onChange={(v) => set('data_coleta', v)} req />
            <TextField label="Telefone da Fonte" value={form.telefone_fonte} onChange={(v) => set('telefone_fonte', v)} placeholder="(99) 99999-9999" />
            <TextField label="Link do Anúncio" value={form.link_anuncio} onChange={(v) => set('link_anuncio', v)} placeholder="ZAP, VivaReal, OLX..." />
          </Section>

          <Section title="Mídia" cols={2}>
            {[['foto_url', 'Foto da Amostra'], ['planta_baixa_url', 'Planta Baixa (PDF/Imagem)']].map(([campo, lbl]) => (
              <div key={campo}>
                <Label>{lbl}</Label>
                {form[campo] ? (
                  <div className="mt-1 flex items-center gap-2 px-3 py-2 text-xs border border-emerald-200 bg-emerald-50 rounded-lg">
                    <span className="truncate text-emerald-700 flex-1">Arquivo anexado</span>
                    <button onClick={() => set(campo, '')} className="text-red-500"><X className="w-4 h-4" /></button>
                  </div>
                ) : (
                  <label className="mt-1 flex items-center justify-center gap-2 px-3 py-2 text-xs border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-emerald-500 text-gray-500">
                    {uploading === campo ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                    Enviar arquivo
                    <input type="file" className="hidden" accept="image/*,application/pdf"
                      onChange={(e) => handleUpload(campo, e.target.files?.[0])} />
                  </label>
                )}
              </div>
            ))}
          </Section>
        </div>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={() => onClose?.()}>Cancelar</Button>
          <Button onClick={salvar} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white">
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}Salvar Amostra
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ModalNovaAmostraUrbana;
