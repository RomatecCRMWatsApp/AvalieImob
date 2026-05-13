import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Save, Building, Upload, X, Image, Lock, ShieldCheck, Trash2, Loader2, Plus, FileBadge, MessageCircle, Send, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Switch } from '../ui/switch';
import { useToast } from '../../hooks/use-toast';
import { useAuth } from '../../contexts/AuthContext';
import { authAPI, uploadAPI, certificadosAPI, integracoesAPI } from '../../lib/api';

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

      <IntegracoesSection />

      <CertificadosICPSection />

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-emerald-900 hover:bg-emerald-800 text-white"><Save className="w-4 h-4 mr-2" />{saving ? 'Salvando...' : 'Salvar alterações'}</Button>
      </div>
    </div>
  );
};


// ════════════════════════════════════════════════════════════════════════════
// Integrações: WhatsApp (Z-API ou Meta) + Telegram
// ════════════════════════════════════════════════════════════════════════════
const IntegracoesSection = () => {
  const { toast } = useToast();
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [provider, setProvider] = useState('zapi');
  const [zapi, setZapi] = useState({ instance_id: '', token: '', security_token: '' });
  const [meta, setMeta] = useState({ phone_number_id: '', access_token: '', business_account_id: '' });
  const [tg, setTg] = useState({ bot_token: '', chat_id_default: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await integracoesAPI.get();
      setCfg(data);
      setProvider(data.whatsapp_provider || 'zapi');
      setZapi({
        instance_id: data.zapi_instance_id || '',
        token: data.zapi_token || '',
        security_token: data.zapi_security_token || '',
      });
      setMeta({
        phone_number_id: data.meta_phone_number_id || '',
        access_token: data.meta_access_token || '',
        business_account_id: data.meta_business_account_id || '',
      });
      setTg({
        bot_token: data.telegram_bot_token || '',
        chat_id_default: data.telegram_chat_id_default || '',
      });
    } catch (e) {
      console.warn(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSalvar = async () => {
    setSaving(true);
    try {
      const payload = {
        whatsapp_provider: provider,
        zapi_instance_id: zapi.instance_id,
        zapi_token: zapi.token,
        zapi_security_token: zapi.security_token,
        zapi_ativo: provider === 'zapi' && !!(zapi.instance_id && zapi.token),
        meta_phone_number_id: meta.phone_number_id,
        meta_access_token: meta.access_token,
        meta_business_account_id: meta.business_account_id,
        meta_ativo: provider === 'meta' && !!(meta.phone_number_id && meta.access_token),
        telegram_bot_token: tg.bot_token,
        telegram_chat_id_default: tg.chat_id_default,
        telegram_ativo: !!tg.bot_token,
      };
      await integracoesAPI.update(payload);
      toast({ title: 'Integrações salvas!' });
      await load();
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao salvar', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestarConexaoWA = async () => {
    try {
      if (provider === 'meta') {
        const res = await integracoesAPI.testarMeta();
        toast({
          title: 'Meta WhatsApp OK!',
          description: res.status?.display_phone_number ? `Conectado: ${res.status.display_phone_number}` : '',
        });
      } else {
        const res = await integracoesAPI.testarZapi();
        toast({
          title: 'Z-API OK!',
          description: res.status?.connected ? 'WhatsApp conectado' : 'Conectado mas WhatsApp desconectado',
        });
      }
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Falha na conexão', variant: 'destructive' });
    }
  };

  const handleEnviarTesteWA = async () => {
    const phone = window.prompt('Número de teste (com DDI+DDD, só dígitos. ex: 5599991234567):', '55');
    if (!phone) return;
    try {
      await integracoesAPI.enviarTesteWhatsApp(phone, 'Teste de integração WhatsApp — Romatec AvalieImob ✓');
      toast({ title: 'Mensagem de teste enviada!', description: `Para ${phone}` });
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao enviar teste', variant: 'destructive' });
    }
  };

  const handleTestarTelegram = async () => {
    const chatId = window.prompt('Chat ID de teste (deixe vazio pra usar o padrão configurado):', tg.chat_id_default || '');
    if (chatId === null) return;
    try {
      await integracoesAPI.testarTelegram(chatId.trim() || null, 'Teste de integração Telegram — Romatec AvalieImob ✓');
      toast({ title: 'Mensagem Telegram enviada!' });
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro no teste Telegram', variant: 'destructive' });
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Carregando integrações...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <div>
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <Send className="w-4 h-4 text-emerald-700" />
          Integrações
        </h3>
        <p className="text-xs text-gray-500 mt-1">
          Configure suas próprias credenciais de WhatsApp e Telegram. Cada conta usa as próprias chaves —
          não há cobrança no servidor central.
        </p>
      </div>

      {/* ── WhatsApp ──────────────────────────────────────────────── */}
      <div className="border border-gray-100 rounded-lg p-4 bg-emerald-50/30">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-4 h-4 text-green-700" />
            <span className="font-semibold text-gray-900 text-sm">WhatsApp</span>
            {(cfg?.has_zapi || cfg?.has_meta) && (
              <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-green-100 text-green-800 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> CONFIGURADO
              </span>
            )}
          </div>
        </div>

        <div className="flex gap-2 mb-3">
          <button
            type="button"
            onClick={() => setProvider('zapi')}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition border ${
              provider === 'zapi'
                ? 'bg-emerald-600 border-emerald-600 text-white'
                : 'bg-white border-gray-200 text-gray-700 hover:border-emerald-300'
            }`}
          >
            Z-API (não-oficial, mais barato)
          </button>
          <button
            type="button"
            onClick={() => setProvider('meta')}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition border ${
              provider === 'meta'
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'bg-white border-gray-200 text-gray-700 hover:border-blue-300'
            }`}
          >
            Meta Cloud API (oficial)
          </button>
        </div>

        {provider === 'zapi' ? (
          <div className="space-y-2">
            <Field label="Instance ID">
              <Input value={zapi.instance_id} onChange={(e) => setZapi({ ...zapi, instance_id: e.target.value })} placeholder="3D1AB..." />
            </Field>
            <Field label="Token">
              <Input
                type="password"
                value={zapi.token}
                onChange={(e) => setZapi({ ...zapi, token: e.target.value })}
                placeholder={cfg?.zapi_token ? '(salvo) — preencha pra alterar' : 'Token da instância'}
                autoComplete="new-password"
              />
            </Field>
            <Field label="Security Token (Client-Token, opcional)">
              <Input
                type="password"
                value={zapi.security_token}
                onChange={(e) => setZapi({ ...zapi, security_token: e.target.value })}
                placeholder={cfg?.zapi_security_token ? '(salvo) — preencha pra alterar' : 'Habilitado em Z-API'}
                autoComplete="new-password"
              />
            </Field>
          </div>
        ) : (
          <div className="space-y-2">
            <Field label="Phone Number ID">
              <Input value={meta.phone_number_id} onChange={(e) => setMeta({ ...meta, phone_number_id: e.target.value })} placeholder="123456789012345" />
            </Field>
            <Field label="Access Token (permanente)">
              <Input
                type="password"
                value={meta.access_token}
                onChange={(e) => setMeta({ ...meta, access_token: e.target.value })}
                placeholder={cfg?.meta_access_token ? '(salvo) — preencha pra alterar' : 'EAAxxx...'}
                autoComplete="new-password"
              />
            </Field>
            <Field label="Business Account ID (opcional)">
              <Input value={meta.business_account_id} onChange={(e) => setMeta({ ...meta, business_account_id: e.target.value })} placeholder="123456789012345" />
            </Field>
          </div>
        )}

        <div className="flex gap-2 mt-3">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleTestarConexaoWA}
            className="flex-1"
          >
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            Testar conexão
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleEnviarTesteWA}
            className="flex-1 text-green-700 border-green-200 hover:bg-green-50"
          >
            <Send className="w-3.5 h-3.5 mr-1" />
            Enviar msg de teste
          </Button>
        </div>
      </div>

      {/* ── Telegram ─────────────────────────────────────────────── */}
      <div className="border border-gray-100 rounded-lg p-4 bg-sky-50/30">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-sky-600" />
            <span className="font-semibold text-gray-900 text-sm">Telegram Bot</span>
            {cfg?.has_telegram && (
              <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-sky-100 text-sky-800 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> CONFIGURADO
              </span>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <Field label="Bot Token">
            <Input
              type="password"
              value={tg.bot_token}
              onChange={(e) => setTg({ ...tg, bot_token: e.target.value })}
              placeholder={cfg?.telegram_bot_token ? '(salvo) — preencha pra alterar' : 'Token do BotFather (123456:ABC...)'}
              autoComplete="new-password"
            />
          </Field>
          <Field label="Chat ID padrão (opcional)">
            <Input
              value={tg.chat_id_default}
              onChange={(e) => setTg({ ...tg, chat_id_default: e.target.value })}
              placeholder="@usuario, 123456789 ou -100... (grupo)"
            />
            <p className="text-[11px] text-gray-500 mt-1">
              Opcional — quando preenchido, aparece como destino padrão ao enviar laudos.
            </p>
          </Field>
        </div>

        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleTestarTelegram}
          className="w-full mt-3 text-sky-700 border-sky-200 hover:bg-sky-50"
        >
          <Send className="w-3.5 h-3.5 mr-1" />
          Enviar mensagem de teste
        </Button>
      </div>

      <Button
        onClick={handleSalvar}
        disabled={saving}
        className="w-full bg-emerald-900 hover:bg-emerald-800 text-white font-semibold"
      >
        {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Salvando...</> : <><Save className="w-4 h-4 mr-2" />Salvar integrações</>}
      </Button>
    </div>
  );
};

const Field = ({ label, children }) => (
  <div>
    <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
    {children}
  </div>
);


// ════════════════════════════════════════════════════════════════════════════
// Certificados Digitais ICP-Brasil A1 (.pfx)
// ════════════════════════════════════════════════════════════════════════════
const CertificadosICPSection = () => {
  const { toast } = useToast();
  const fileRef = useRef(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ label: '', perfil: 'PF', senha: '', file: null });
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await certificadosAPI.list();
      setItems(data || []);
    } catch (e) {
      toast({ title: 'Erro ao carregar certificados', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setForm(prev => ({ ...prev, file: f }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.file) {
      toast({ title: 'Escolha um arquivo .pfx', variant: 'destructive' });
      return;
    }
    if (!form.label.trim() || !form.senha) {
      toast({ title: 'Preencha rótulo e senha', variant: 'destructive' });
      return;
    }
    setUploading(true);
    try {
      await certificadosAPI.upload(form.file, {
        label: form.label.trim(),
        perfil: form.perfil,
        senha: form.senha,
      });
      toast({ title: 'Certificado cadastrado!' });
      setForm({ label: '', perfil: 'PF', senha: '', file: null });
      setShowForm(false);
      if (fileRef.current) fileRef.current.value = '';
      await load();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Falha ao cadastrar certificado';
      toast({ title: detail, variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const handleToggle = async (cert) => {
    try {
      await certificadosAPI.toggle(cert.id, !cert.ativo);
      await load();
    } catch (e) {
      toast({ title: 'Erro ao atualizar', variant: 'destructive' });
    }
  };

  const handleRemove = async (cert) => {
    if (!window.confirm(`Remover o certificado "${cert.label}"?`)) return;
    try {
      await certificadosAPI.remove(cert.id);
      toast({ title: 'Certificado removido' });
      await load();
    } catch (e) {
      toast({ title: 'Erro ao remover', variant: 'destructive' });
    }
  };

  const formatDate = (d) => {
    if (!d) return '—';
    try { return new Date(d).toLocaleDateString('pt-BR'); } catch { return d; }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <Lock className="w-4 h-4 text-emerald-700" />
          Certificados Digitais ICP-Brasil
        </h3>
        {!showForm && (
          <Button size="sm" onClick={() => setShowForm(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white">
            <Plus className="w-4 h-4 mr-1" />
            Adicionar certificado
          </Button>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-4 leading-relaxed">
        Cadastre o e-CNPJ A1 (PJ) ou e-CPF A1 (PF) pra assinar laudos com validade jurídica (PAdES).
        O <code className="bg-gray-100 px-1 rounded">.pfx</code> fica criptografado AES-256-GCM no banco.
      </p>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-emerald-50/40 border border-emerald-100 rounded-lg p-4 mb-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-sm flex items-center gap-2 text-emerald-900">
              <Lock className="w-4 h-4" /> Adicionar novo certificado
            </div>
            <button type="button" onClick={() => { setShowForm(false); setForm({ label: '', perfil: 'PF', senha: '', file: null }); }} className="text-gray-400 hover:text-gray-600">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Arquivo .pfx</label>
            <input
              ref={fileRef}
              type="file"
              accept=".pfx,.p12"
              onChange={handleFile}
              className="block w-full text-sm border border-gray-200 rounded-lg p-2 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:bg-emerald-100 file:text-emerald-800 file:font-medium hover:file:bg-emerald-200"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Senha do certificado</label>
            <Input
              type="password"
              autoComplete="new-password"
              value={form.senha}
              onChange={(e) => setForm({ ...form, senha: e.target.value })}
              placeholder="Senha que você criou ao emitir"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Perfil</label>
              <select
                value={form.perfil}
                onChange={(e) => setForm({ ...form, perfil: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="PJ">PJ — e-CNPJ</option>
                <option value="PF">PF — e-CPF</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Rótulo</label>
              <Input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                placeholder="ex: Romatec 2026"
              />
            </div>
          </div>

          <Button type="submit" disabled={uploading} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
            {uploading ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Enviando...</>
            ) : (
              <><Lock className="w-4 h-4 mr-2" />Cadastrar certificado</>
            )}
          </Button>
        </form>
      )}

      <div>
        <div className="text-xs uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-2">
          <FileBadge className="w-3.5 h-3.5" />
          Certificados cadastrados
        </div>

        {loading ? (
          <div className="py-6 flex justify-center"><Loader2 className="w-5 h-5 animate-spin text-emerald-700" /></div>
        ) : items.length === 0 ? (
          <div className="text-sm text-gray-500 py-6 text-center bg-gray-50 rounded-lg border border-dashed border-gray-200">
            Nenhum certificado cadastrado ainda.
          </div>
        ) : (
          <div className="space-y-2">
            {items.map(cert => (
              <div
                key={cert.id}
                className={`border rounded-lg p-3 flex items-start gap-3 ${cert.ativo ? 'border-gray-200 bg-white' : 'border-gray-100 bg-gray-50 opacity-60'}`}
              >
                <div className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${cert.ativo ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-gray-900 text-sm">{cert.perfil === 'PJ' ? 'e-CNPJ' : 'e-CPF'} — {cert.label}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${cert.perfil === 'PJ' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'}`}>{cert.perfil}</span>
                  </div>
                  {cert.titular && <div className="text-xs text-gray-700 mt-0.5"><span className="font-medium">Titular:</span> {cert.titular}</div>}
                  {cert.documento && <div className="text-xs text-gray-600"><span className="font-medium">Documento:</span> {cert.documento}</div>}
                  <div className="text-xs text-gray-500 mt-0.5">
                    Válido até <strong>{formatDate(cert.valido_ate)}</strong>
                    {cert.emissor && <> · Emissor: {cert.emissor}</>}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <Button type="button" size="sm" variant="outline" className="h-7 px-2 text-xs" onClick={() => handleToggle(cert)}>
                    {cert.ativo ? 'desativar' : 'ativar'}
                  </Button>
                  <Button type="button" size="sm" variant="outline" className="h-7 px-2 text-xs text-red-600 border-red-200 hover:bg-red-50" onClick={() => handleRemove(cert)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SettingsPage;
