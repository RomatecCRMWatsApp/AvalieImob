import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  UploadCloud, Trash2, RotateCcw, Save, Loader2, Eye, Palette,
  Type as TypeIcon, ImageIcon,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Textarea } from '../../ui/textarea';
import { Switch } from '../../ui/switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../ui/tabs';
import { useToast } from '../../../hooks/use-toast';
import { brandingAPI } from '../../../lib/api';

const DEFAULTS = {
  color_primary: '#0d4f3c',
  color_secondary: '#c9a84c',
  color_text: '#1a1a1a',
  color_background: '#ffffff',
  color_footer_bg: '#0d4f3c',
  color_footer_text: '#ffffff',
  font_title: 'Montserrat',
  font_body: 'Inter',
};

const COLOR_FIELDS = [
  { key: 'color_primary', label: 'Primária (faixa/cabeçalho)' },
  { key: 'color_secondary', label: 'Secundária (detalhes)' },
  { key: 'color_text', label: 'Texto' },
  { key: 'color_footer_bg', label: 'Fundo do rodapé' },
  { key: 'color_footer_text', label: 'Texto do rodapé' },
  { key: 'color_background', label: 'Fundo do documento' },
];

const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

const BrandingWizard = () => {
  const { toast } = useToast();
  const fileRef = useRef(null);
  const previewUrlRef = useRef(null);

  const [branding, setBranding] = useState(null);
  const [form, setForm] = useState({ ...DEFAULTS });
  const [useDefault, setUseDefault] = useState(true);
  const [logoUrl, setLogoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [previewSrc, setPreviewSrc] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const hydrate = useCallback((data) => {
    setBranding(data);
    setUseDefault(data.use_default !== false);
    setLogoUrl(data.logo_url || null);
    setForm({
      color_primary: data.color_primary || DEFAULTS.color_primary,
      color_secondary: data.color_secondary || DEFAULTS.color_secondary,
      color_text: data.color_text || DEFAULTS.color_text,
      color_background: data.color_background || DEFAULTS.color_background,
      color_footer_bg: data.color_footer_bg || DEFAULTS.color_footer_bg,
      color_footer_text: data.color_footer_text || DEFAULTS.color_footer_text,
      font_title: data.font_title || DEFAULTS.font_title,
      font_body: data.font_body || DEFAULTS.font_body,
      footer_line1: data.footer_line1 || '',
      footer_line2: data.footer_line2 || '',
      footer_line3: data.footer_line3 || '',
      stamp_name: data.stamp_name || '',
      stamp_credentials: data.stamp_credentials || '',
    });
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      hydrate(await brandingAPI.get());
    } catch (err) {
      toast({ title: 'Erro ao carregar a marca', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [hydrate, toast]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => () => {
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
  }, []);

  const setField = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  // ── Logo upload ────────────────────────────────────────────────────────────
  const doUpload = useCallback(async (file) => {
    if (!file) return;
    const okType = ['image/png', 'image/svg+xml', 'image/jpeg'].includes(file.type);
    if (!okType) {
      toast({ title: 'Formato inválido', description: 'Use PNG, SVG ou JPG.', variant: 'destructive' });
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast({ title: 'Arquivo muito grande', description: 'Máximo 2MB.', variant: 'destructive' });
      return;
    }
    setUploading(true);
    try {
      const data = await brandingAPI.uploadLogo(file);
      hydrate(data);
      toast({ title: 'Logo enviado', description: 'Já aparece nos seus documentos.' });
    } catch (err) {
      toast({ title: 'Falha no upload', description: err.response?.data?.detail || 'Tente novamente.', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  }, [hydrate, toast]);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.[0]) doUpload(e.dataTransfer.files[0]);
  };

  const removeLogo = async () => {
    try {
      hydrate(await brandingAPI.deleteLogo());
      toast({ title: 'Logo removido' });
    } catch (err) {
      toast({ title: 'Erro ao remover', description: err.response?.data?.detail, variant: 'destructive' });
    }
  };

  // ── Salvar tudo ──────────────────────────────────────────────────────────────
  const saveAll = async () => {
    for (const f of COLOR_FIELDS) {
      if (form[f.key] && !HEX_RE.test(form[f.key])) {
        toast({ title: 'Cor inválida', description: `${f.label}: use #RRGGBB`, variant: 'destructive' });
        return;
      }
    }
    setSaving(true);
    try {
      await brandingAPI.setUseDefault(useDefault);
      const data = await brandingAPI.updateColors({
        color_primary: form.color_primary,
        color_secondary: form.color_secondary,
        color_text: form.color_text,
        color_background: form.color_background,
        color_footer_bg: form.color_footer_bg,
        color_footer_text: form.color_footer_text,
      });
      await brandingAPI.updateTypography({ font_title: form.font_title, font_body: form.font_body });
      const finalData = await brandingAPI.updateFooter({
        footer_line1: form.footer_line1,
        footer_line2: form.footer_line2,
        footer_line3: form.footer_line3,
        stamp_name: form.stamp_name,
        stamp_credentials: form.stamp_credentials,
      });
      hydrate(finalData || data);
      toast({ title: 'Marca salva', description: 'Aplicada a PTAM, contratos, recibos e laudos.' });
    } catch (err) {
      toast({ title: 'Erro ao salvar', description: err.response?.data?.detail || 'Tente novamente.', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const doReset = async () => {
    setSaving(true);
    try {
      hydrate(await brandingAPI.reset());
      toast({ title: 'Padrão restaurado', description: 'Voltou ao padrão AvalieImob.' });
    } catch (err) {
      toast({ title: 'Erro ao restaurar', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const loadPreview = useCallback(async () => {
    setPreviewLoading(true);
    try {
      const blob = await brandingAPI.preview();
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
      const url = URL.createObjectURL(blob);
      previewUrlRef.current = url;
      setPreviewSrc(url);
    } catch (err) {
      toast({ title: 'Erro no preview', description: err.response?.data?.detail, variant: 'destructive' });
    } finally {
      setPreviewLoading(false);
    }
  }, [toast]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500">
        <Loader2 className="w-5 h-5 mr-2 animate-spin" /> Carregando marca…
      </div>
    );
  }

  const fieldsDisabled = useDefault;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Palette className="w-6 h-6" /> Personalização da Marca
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Logo, cores e rodapé aplicados a todos os documentos: PTAM, contratos, recibos, laudos e TVI.
          </p>
        </div>
        <Button variant="outline" onClick={doReset} disabled={saving}>
          <RotateCcw className="w-4 h-4 mr-2" /> Restaurar padrão
        </Button>
      </div>

      <div className="flex items-center gap-3 mb-6 p-4 rounded-lg border bg-gray-50">
        <Switch checked={useDefault} onCheckedChange={setUseDefault} id="use-default" />
        <Label htmlFor="use-default" className="cursor-pointer">
          Usar o padrão AvalieImob (desativa a marca personalizada abaixo)
        </Label>
      </div>

      <Tabs defaultValue="logo" className="w-full">
        <TabsList className="grid grid-cols-4 w-full">
          <TabsTrigger value="logo"><ImageIcon className="w-4 h-4 mr-1" /> Logo</TabsTrigger>
          <TabsTrigger value="cores"><Palette className="w-4 h-4 mr-1" /> Cores</TabsTrigger>
          <TabsTrigger value="rodape"><TypeIcon className="w-4 h-4 mr-1" /> Rodapé</TabsTrigger>
          <TabsTrigger value="preview" onClick={loadPreview}><Eye className="w-4 h-4 mr-1" /> Preview</TabsTrigger>
        </TabsList>

        {/* ── Aba Logo ── */}
        <TabsContent value="logo" className="mt-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl py-12 px-6 cursor-pointer transition
              ${dragging ? 'border-emerald-600 bg-emerald-50' : 'border-gray-300 hover:border-gray-400'}
              ${fieldsDisabled ? 'opacity-50 pointer-events-none' : ''}`}
          >
            {uploading ? (
              <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
            ) : logoUrl ? (
              <img src={logoUrl} alt="Logo atual" className="max-h-24 object-contain mb-3" />
            ) : (
              <UploadCloud className="w-10 h-10 text-gray-400 mb-3" />
            )}
            <p className="text-sm text-gray-600 font-medium">Clique ou arraste seu logo aqui</p>
            <p className="text-xs text-gray-400 mt-1">PNG, SVG ou JPG · máx 2MB · 200×60 a 2000×600px</p>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/svg+xml,image/jpeg"
              className="hidden"
              onChange={(e) => doUpload(e.target.files?.[0])}
            />
          </div>
          {logoUrl && (
            <div className="flex justify-end mt-3">
              <Button variant="ghost" size="sm" onClick={removeLogo} disabled={fieldsDisabled}>
                <Trash2 className="w-4 h-4 mr-2 text-red-500" /> Remover logo
              </Button>
            </div>
          )}
        </TabsContent>

        {/* ── Aba Cores ── */}
        <TabsContent value="cores" className="mt-4">
          <div className="grid sm:grid-cols-2 gap-4">
            {COLOR_FIELDS.map(({ key, label }) => (
              <div key={key} className={fieldsDisabled ? 'opacity-50' : ''}>
                <Label className="text-sm">{label}</Label>
                <div className="flex items-center gap-2 mt-1">
                  <input
                    type="color"
                    value={HEX_RE.test(form[key]) ? form[key] : '#000000'}
                    onChange={(e) => setField(key, e.target.value)}
                    disabled={fieldsDisabled}
                    className="h-10 w-12 rounded border cursor-pointer disabled:cursor-not-allowed"
                  />
                  <Input
                    value={form[key] || ''}
                    onChange={(e) => setField(key, e.target.value)}
                    disabled={fieldsDisabled}
                    placeholder="#000000"
                    className="font-mono"
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="grid sm:grid-cols-2 gap-4 mt-6">
            <div className={fieldsDisabled ? 'opacity-50' : ''}>
              <Label className="text-sm">Fonte dos títulos</Label>
              <Input value={form.font_title || ''} onChange={(e) => setField('font_title', e.target.value)} disabled={fieldsDisabled} className="mt-1" placeholder="Montserrat" />
            </div>
            <div className={fieldsDisabled ? 'opacity-50' : ''}>
              <Label className="text-sm">Fonte do corpo</Label>
              <Input value={form.font_body || ''} onChange={(e) => setField('font_body', e.target.value)} disabled={fieldsDisabled} className="mt-1" placeholder="Inter" />
            </div>
          </div>
        </TabsContent>

        {/* ── Aba Rodapé ── */}
        <TabsContent value="rodape" className="mt-4 space-y-4">
          <div className={fieldsDisabled ? 'opacity-50' : ''}>
            <Label className="text-sm">Rodapé — linha 1 (endereço)</Label>
            <Input value={form.footer_line1 || ''} onChange={(e) => setField('footer_line1', e.target.value)} disabled={fieldsDisabled} className="mt-1" placeholder="Av. Getúlio Vargas, 123 — Açailândia/MA" />
          </div>
          <div className={fieldsDisabled ? 'opacity-50' : ''}>
            <Label className="text-sm">Rodapé — linha 2 (registros)</Label>
            <Input value={form.footer_line2 || ''} onChange={(e) => setField('footer_line2', e.target.value)} disabled={fieldsDisabled} className="mt-1" placeholder="CRECI/MA 9.999 · CNAI 099999" />
          </div>
          <div className={fieldsDisabled ? 'opacity-50' : ''}>
            <Label className="text-sm">Rodapé — linha 3 (contato)</Label>
            <Input value={form.footer_line3 || ''} onChange={(e) => setField('footer_line3', e.target.value)} disabled={fieldsDisabled} className="mt-1" placeholder="Tel: (99) 9 9999-9999 · email@escritorio.com" />
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className={fieldsDisabled ? 'opacity-50' : ''}>
              <Label className="text-sm">Responsável técnico (carimbo)</Label>
              <Input value={form.stamp_name || ''} onChange={(e) => setField('stamp_name', e.target.value)} disabled={fieldsDisabled} className="mt-1" placeholder="José Romário Pinto Bezerra" />
            </div>
            <div className={fieldsDisabled ? 'opacity-50' : ''}>
              <Label className="text-sm">Credenciais</Label>
              <Textarea value={form.stamp_credentials || ''} onChange={(e) => setField('stamp_credentials', e.target.value)} disabled={fieldsDisabled} className="mt-1" rows={2} placeholder="CNAI 031161 · CRECI/MA 4.705 · CFT/MA 01209185369" />
            </div>
          </div>
        </TabsContent>

        {/* ── Aba Preview ── */}
        <TabsContent value="preview" className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-500">Amostra do cabeçalho e rodapé com a marca atual (salve antes para refletir mudanças).</p>
            <Button variant="outline" size="sm" onClick={loadPreview} disabled={previewLoading}>
              {previewLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
              <span className="ml-2">Atualizar</span>
            </Button>
          </div>
          <div className="border rounded-lg bg-gray-100 min-h-[400px] flex items-center justify-center overflow-hidden">
            {previewLoading ? (
              <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
            ) : previewSrc ? (
              <img src={previewSrc} alt="Preview do documento" className="max-w-full max-h-[640px] object-contain shadow" />
            ) : (
              <p className="text-gray-400 text-sm">Clique em “Atualizar” para gerar o preview.</p>
            )}
          </div>
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t">
        <Button onClick={saveAll} disabled={saving}>
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
          Salvar marca
        </Button>
      </div>
    </div>
  );
};

export default BrandingWizard;
