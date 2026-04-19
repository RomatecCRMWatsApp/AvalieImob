import React, { useState, useRef } from 'react';
import { Save, Building, Upload, X, Image } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Switch } from '../ui/switch';
import { useToast } from '../../hooks/use-toast';
import { useAuth } from '../../contexts/AuthContext';
import { authAPI, uploadAPI } from '../../lib/api';

const MAX_LOGO_SIZE = 2 * 1024 * 1024; // 2 MB

const SettingsPage = () => {
  const { user, refreshUser } = useAuth();
  const { toast } = useToast();
  const fileInputRef = useRef(null);

  const [form, setForm] = useState({
    name: user?.name || '', crea: user?.crea || '', role: user?.role || '', company: user?.company || '', bio: user?.bio || '',
    notifyEmail: true, notifyWhats: false, aiAuto: true,
  });
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [logoId, setLogoId] = useState(user?.company_logo || null);

  const logoUrl = logoId ? uploadAPI.getImageUrl(logoId) : null;

  const save = async () => {
    setSaving(true);
    try {
      await authAPI.updateMe({ name: form.name, crea: form.crea, role: form.role, company: form.company, bio: form.bio });
      await refreshUser();
      toast({ title: 'Configurações salvas' });
    } catch (e) { toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' }); }
    finally { setSaving(false); }
  };

  const handleLogoFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!['image/png', 'image/jpeg', 'image/jpg'].includes(file.type)) {
      toast({ title: 'Formato inválido', description: 'Use PNG ou JPG.', variant: 'destructive' });
      return;
    }
    if (file.size > MAX_LOGO_SIZE) {
      toast({ title: 'Arquivo muito grande', description: 'Tamanho máximo: 2MB.', variant: 'destructive' });
      return;
    }

    setUploadingLogo(true);
    try {
      const result = await uploadAPI.uploadImage(file);
      const newLogoId = result.id;
      await authAPI.updateMe({ company_logo: newLogoId });
      setLogoId(newLogoId);
      await refreshUser();
      toast({ title: 'Logo enviada com sucesso!' });
    } catch (e) {
      toast({ title: 'Erro ao enviar logo', description: e.response?.data?.detail, variant: 'destructive' });
    } finally {
      setUploadingLogo(false);
      e.target.value = '';
    }
  };

  const handleRemoveLogo = async () => {
    try {
      await authAPI.updateMe({ company_logo: null });
      setLogoId(null);
      await refreshUser();
      toast({ title: 'Logo removida' });
    } catch (e) {
      toast({ title: 'Erro ao remover logo', variant: 'destructive' });
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="font-display text-3xl font-bold text-gray-900">Configurações</h1>
        <p className="text-gray-600 mt-1">Dados profissionais, preferências e personalização.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Dados profissionais</h3>
        <div className="grid grid-cols-2 gap-4">
          <div><label className="text-sm font-medium">Nome</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div><label className="text-sm font-medium">E-mail</label><Input type="email" value={user?.email || ''} disabled /></div>
          <div><label className="text-sm font-medium">Profissão</label><Input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} /></div>
          <div><label className="text-sm font-medium">CRECI / CREA</label><Input value={form.crea} onChange={(e) => setForm({ ...form, crea: e.target.value })} /></div>
          <div className="col-span-2"><label className="text-sm font-medium">Empresa</label><Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} /></div>
          <div className="col-span-2"><label className="text-sm font-medium">Biografia (aparece nos laudos)</label><Textarea value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} rows={3} /></div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Personalização de laudos</h3>
        <div className="flex items-center gap-4 p-4 bg-emerald-50/40 rounded-lg border border-emerald-900/10">
          {/* Logo preview or placeholder icon */}
          <div className="w-14 h-14 rounded-lg bg-white border border-emerald-900/10 flex items-center justify-center overflow-hidden flex-shrink-0">
            {logoUrl ? (
              <img
                src={logoUrl}
                alt="Logo da empresa"
                className="w-full h-full object-contain"
              />
            ) : (
              <Building className="w-6 h-6 text-emerald-700" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="font-semibold text-sm">Logo da empresa</div>
            <div className="text-xs text-gray-500">PNG ou JPG, até 2MB. Aparece no cabeçalho dos laudos.</div>
            {logoId && (
              <div className="text-xs text-emerald-700 mt-0.5">Logo carregada</div>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {logoId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRemoveLogo}
                className="text-red-500 hover:text-red-700 hover:bg-red-50"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg"
              className="hidden"
              onChange={handleLogoFileChange}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingLogo}
            >
              {uploadingLogo ? (
                <span className="flex items-center gap-1"><Upload className="w-4 h-4 animate-bounce" />Enviando...</span>
              ) : logoId ? (
                <span className="flex items-center gap-1"><Image className="w-4 h-4" />Trocar logo</span>
              ) : (
                <span className="flex items-center gap-1"><Upload className="w-4 h-4" />Fazer upload</span>
              )}
            </Button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Preferências</h3>
        <div className="space-y-4">
          {[
            { key: 'notifyEmail', label: 'Notificações por e-mail', desc: 'Receber atualizações e avisos de laudos' },
            { key: 'notifyWhats', label: 'Notificações WhatsApp', desc: 'Alertas importantes no seu WhatsApp' },
            { key: 'aiAuto', label: 'Sugerir melhorias com IA automaticamente', desc: 'IA analisa laudos ao salvar e sugere aperfeiçoamentos' },
          ].map(opt => (
            <div key={opt.key} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
              <div><div className="font-medium text-sm">{opt.label}</div><div className="text-xs text-gray-500">{opt.desc}</div></div>
              <Switch checked={form[opt.key]} onCheckedChange={(v) => setForm({ ...form, [opt.key]: v })} />
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Save className="w-4 h-4 mr-2" />{saving ? 'Salvando...' : 'Salvar alterações'}</Button>
      </div>
    </div>
  );
};

export default SettingsPage;
