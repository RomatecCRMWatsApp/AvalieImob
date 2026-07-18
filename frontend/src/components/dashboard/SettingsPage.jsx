import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Save, Building, Upload, X, Image, Lock, ShieldCheck, Trash2, Loader2, Plus, FileBadge, MessageCircle, Send, CheckCircle2, AlertCircle, RefreshCw, Eye } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Switch } from '../ui/switch';
import { useToast } from '../../hooks/use-toast';
import { useAuth } from '../../contexts/AuthContext';
import { authAPI, uploadAPI, certificadosAPI, integracoesAPI, perfilAPI } from '../../lib/api';

const MAX_LOGO_SIZE = 2 * 1024 * 1024; // 2 MB

// Abre as imagens (1+ páginas, data-uri base64) em uma nova aba para visualização ampliada.
const visualizarImagens = (imgs, titulo = 'Documento') => {
  const lista = (imgs || []).filter(Boolean);
  if (!lista.length) return;
  const win = window.open('', '_blank');
  if (!win) return;
  const tags = lista.map((s) => `<img src="${s}" alt="${titulo}"/>`).join('');
  win.document.write(
    `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${titulo}</title>` +
    `<style>body{margin:0;background:#525659;display:flex;flex-direction:column;align-items:center;gap:16px;padding:20px}` +
    `img{max-width:100%;width:920px;background:#fff;box-shadow:0 2px 14px rgba(0,0,0,.45);border-radius:4px}</style>` +
    `</head><body>${tags}</body></html>`
  );
  win.document.close();
};

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

  // ── Cartão de Regularidade Profissional (CRECI) ──
  const cartaoInputRef = useRef(null);
  const [cartaoPreview, setCartaoPreview] = useState(null);  // 1ª página (img) p/ pré-visualização
  const [cartaoImgs, setCartaoImgs] = useState([]);          // todas as páginas (p/ visualizar ampliado)
  const [cartaoPaginas, setCartaoPaginas] = useState(0);     // nº de páginas (quando PDF convertido)
  const [cartaoLink, setCartaoLink] = useState('');
  const [cartaoAnexar, setCartaoAnexar] = useState(true);
  const [savingCartao, setSavingCartao] = useState(false);

  const aplicaPerfilCartao = (p) => {
    const pags = p?.cartao_regularidade_paginas_b64 || [];
    setCartaoPreview(pags[0] || p?.cartao_regularidade_b64 || null);
    setCartaoImgs(pags.length ? pags : (p?.cartao_regularidade_b64 ? [p.cartao_regularidade_b64] : []));
    setCartaoPaginas(pags.length);
    if (typeof p?.cartao_regularidade_link === 'string') setCartaoLink(p.cartao_regularidade_link);
    if (typeof p?.cartao_regularidade_anexar === 'boolean') setCartaoAnexar(p.cartao_regularidade_anexar);
  };

  useEffect(() => {
    perfilAPI.get().then((p) => { if (p) aplicaPerfilCartao(p); }).catch(() => {});
  }, []);

  const persistCartao = async (patch) => {
    setSavingCartao(true);
    try {
      const p = await perfilAPI.setCartaoRegularidade(patch);
      if (p) aplicaPerfilCartao(p);
      return p;
    } catch (e) {
      toast({ title: 'Erro ao salvar o cartão', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingCartao(false); }
  };

  const handleCartaoFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const okTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf'];
    if (!okTypes.includes(file.type)) {
      toast({ title: 'Formato inválido', description: 'Envie uma imagem (PNG, JPG, WEBP) ou um PDF.', variant: 'destructive' });
      e.target.value = ''; return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast({ title: 'Arquivo muito grande', description: 'Tamanho máximo: 10MB.', variant: 'destructive' });
      e.target.value = ''; return;
    }
    setSavingCartao(true);
    try {
      const b64 = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result);
        r.onerror = rej;
        r.readAsDataURL(file);
      });
      const p = await perfilAPI.setCartaoRegularidade({ cartao_regularidade_b64: b64, cartao_regularidade_anexar: true });
      if (p) aplicaPerfilCartao(p);
      const npags = p?.cartao_regularidade_paginas_b64?.length || 0;
      toast({ title: 'Cartão de regularidade salvo!', description: npags > 1 ? `PDF com ${npags} páginas anexado.` : undefined });
    } catch (err) {
      toast({ title: 'Erro ao enviar o cartão', description: err.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingCartao(false); e.target.value = ''; }
  };

  const handleRemoveCartao = async () => {
    setCartaoPreview(null);
    setCartaoPaginas(0);
    await persistCartao({ cartao_regularidade_b64: '' });
    toast({ title: 'Cartão removido' });
  };

  // ── Certidão de Regularidade (CRECI) — gerada on-line, vale 30 dias ──
  const CRECI_CERTIDAO_URL = 'https://www.crecima.gov.br/2025/10/14/certidao-de-regularidade/';
  const certidaoInputRef = useRef(null);
  const [certidaoPreview, setCertidaoPreview] = useState(null);
  const [certidaoImgs, setCertidaoImgs] = useState([]);
  const [certidaoPaginas, setCertidaoPaginas] = useState(0);
  const [certidaoValidade, setCertidaoValidade] = useState('');
  const [certidaoLink, setCertidaoLink] = useState('');
  const [certidaoAnexar, setCertidaoAnexar] = useState(true);
  const [savingCertidao, setSavingCertidao] = useState(false);

  const aplicaPerfilCertidao = (p) => {
    const pags = p?.certidao_regularidade_paginas_b64 || [];
    setCertidaoPreview(pags[0] || p?.certidao_regularidade_b64 || null);
    setCertidaoImgs(pags.length ? pags : (p?.certidao_regularidade_b64 ? [p.certidao_regularidade_b64] : []));
    setCertidaoPaginas(pags.length);
    if (typeof p?.certidao_regularidade_validade === 'string') setCertidaoValidade(p.certidao_regularidade_validade);
    if (typeof p?.certidao_regularidade_link === 'string') setCertidaoLink(p.certidao_regularidade_link);
    if (typeof p?.certidao_regularidade_anexar === 'boolean') setCertidaoAnexar(p.certidao_regularidade_anexar);
  };

  // Estado da validade: 'sem' (não cadastrada) | 'vencida' | 'vencendo' (≤10 dias) | 'ok'
  const certidaoStatus = (() => {
    if (!certidaoValidade) return certidaoPreview ? 'sem_data' : 'sem';
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    const val = new Date(certidaoValidade + 'T00:00:00');
    if (isNaN(val.getTime())) return 'sem_data';
    const dias = Math.round((val - hoje) / 86400000);
    if (dias < 0) return 'vencida';
    if (dias <= 10) return 'vencendo';
    return 'ok';
  })();
  const certidaoValidadeBR = certidaoValidade
    ? certidaoValidade.split('-').reverse().join('/') : '';

  const persistCertidao = async (patch) => {
    setSavingCertidao(true);
    try {
      const p = await perfilAPI.setCertidaoRegularidade(patch);
      if (p) aplicaPerfilCertidao(p);
      return p;
    } catch (e) {
      toast({ title: 'Erro ao salvar a certidão', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingCertidao(false); }
  };

  const handleCertidaoFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const okTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf'];
    if (!okTypes.includes(file.type)) {
      toast({ title: 'Formato inválido', description: 'Envie uma imagem (PNG, JPG, WEBP) ou um PDF.', variant: 'destructive' });
      e.target.value = ''; return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast({ title: 'Arquivo muito grande', description: 'Tamanho máximo: 10MB.', variant: 'destructive' });
      e.target.value = ''; return;
    }
    setSavingCertidao(true);
    try {
      const b64 = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result);
        r.onerror = rej;
        r.readAsDataURL(file);
      });
      const p = await perfilAPI.setCertidaoRegularidade({ certidao_regularidade_b64: b64, certidao_regularidade_anexar: true });
      if (p) aplicaPerfilCertidao(p);
      toast({ title: 'Certidão de regularidade salva!', description: 'Informe a data de validade (a certidão CRECI vale 30 dias).' });
    } catch (err) {
      toast({ title: 'Erro ao enviar a certidão', description: err.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingCertidao(false); e.target.value = ''; }
  };

  const handleRemoveCertidao = async () => {
    setCertidaoPreview(null);
    setCertidaoPaginas(0);
    await persistCertidao({ certidao_regularidade_b64: '' });
    toast({ title: 'Certidão removida' });
  };

  const abrirRenovacaoCertidao = () =>
    window.open((certidaoLink || CRECI_CERTIDAO_URL).trim(), '_blank', 'noopener,noreferrer');

  // carrega a certidão no mount (perfil já é buscado uma vez; aqui aplicamos os campos da certidão)
  useEffect(() => {
    perfilAPI.get().then((p) => { if (p) aplicaPerfilCertidao(p); }).catch(() => {});
  }, []);

  // ── Certificado CNAI — miniatura no currículo do PTAM ──
  const cnaiInputRef = useRef(null);
  const [cnaiPreview, setCnaiPreview] = useState(null);
  const [cnaiImgs, setCnaiImgs] = useState([]);
  const [cnaiPaginas, setCnaiPaginas] = useState(0);
  const [cnaiAnexar, setCnaiAnexar] = useState(true);
  const [savingCnai, setSavingCnai] = useState(false);

  const aplicaPerfilCnai = (p) => {
    const pags = p?.certificado_cnai_paginas_b64 || [];
    setCnaiPreview(pags[0] || p?.certificado_cnai_b64 || null);
    setCnaiImgs(pags.length ? pags : (p?.certificado_cnai_b64 ? [p.certificado_cnai_b64] : []));
    setCnaiPaginas(pags.length);
    if (typeof p?.certificado_cnai_anexar === 'boolean') setCnaiAnexar(p.certificado_cnai_anexar);
  };

  useEffect(() => {
    perfilAPI.get().then((p) => { if (p) aplicaPerfilCnai(p); }).catch(() => {});
  }, []);

  const persistCnai = async (patch) => {
    setSavingCnai(true);
    try {
      const p = await perfilAPI.setCertificadoCnai(patch);
      if (p) aplicaPerfilCnai(p);
      return p;
    } catch (e) {
      toast({ title: 'Erro ao salvar o certificado CNAI', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingCnai(false); }
  };

  const handleCnaiFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const okTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf'];
    if (!okTypes.includes(file.type)) {
      toast({ title: 'Formato inválido', description: 'Envie uma imagem (PNG, JPG, WEBP) ou um PDF.', variant: 'destructive' });
      e.target.value = ''; return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast({ title: 'Arquivo muito grande', description: 'Tamanho máximo: 10MB.', variant: 'destructive' });
      e.target.value = ''; return;
    }
    setSavingCnai(true);
    try {
      const b64 = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(r.result);
        r.onerror = rej;
        r.readAsDataURL(file);
      });
      const p = await perfilAPI.setCertificadoCnai({ certificado_cnai_b64: b64, certificado_cnai_anexar: true });
      if (p) aplicaPerfilCnai(p);
      toast({ title: 'Certificado CNAI salvo!', description: 'Será exibido como miniatura no currículo do laudo.' });
    } catch (err) {
      toast({ title: 'Erro ao enviar o certificado', description: err.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingCnai(false); e.target.value = ''; }
  };

  const handleRemoveCnai = async () => {
    setCnaiPreview(null);
    setCnaiPaginas(0);
    await persistCnai({ certificado_cnai_b64: '' });
    toast({ title: 'Certificado CNAI removido' });
  };

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

  // ── Qualidades do carimbo do ICP (papéis em que assina) ──
  // NUNCA fixar CRECI/CNAI/CFT de ninguém aqui — esta tela é de todos os
  // assinantes, e o valor vai estampado no carimbo do ICP em documento com
  // valor jurídico. Cada usuário cadastra as próprias qualidades.
  const QUAL_DEFAULT = [];
  const [quals, setQuals] = useState(QUAL_DEFAULT);
  const [savingQuals, setSavingQuals] = useState(false);
  useEffect(() => {
    perfilAPI.get().then((p) => { if (p?.carimbo_qualidades?.length) setQuals(p.carimbo_qualidades); }).catch(() => {});
  }, []);
  const updQual = (i, campo, v) => setQuals((qs) => qs.map((q, k) => (k === i ? { ...q, [campo]: v } : q)));
  const addQual = () => setQuals((qs) => [...qs, { label: '', value: '' }]);
  const rmQual = (i) => setQuals((qs) => qs.filter((_, k) => k !== i));
  const salvarQuals = async () => {
    setSavingQuals(true);
    try {
      const limpos = quals.filter((q) => (q.label || '').trim());
      await perfilAPI.setCarimboQualidades(limpos);
      toast({ title: 'Qualidades do carimbo salvas', description: 'Disponíveis no seletor ao assinar com ICP.' });
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e.response?.data?.detail, variant: 'destructive' });
    } finally { setSavingQuals(false); }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="font-display text-3xl font-bold text-[#B8860B] dark:text-amber-400">Configurações</h1>
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
        <div className="flex items-center gap-2 mb-1">
          <FileBadge className="w-5 h-5 text-[#B8860B]" />
          <h3 className="font-semibold text-gray-900">Cartão de Regularidade (CRECI)</h3>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          Envie a <b>imagem</b> (PNG/JPG) ou o <b>PDF</b> do seu cartão de regularidade profissional.
          PDF com frente e verso é convertido automaticamente. Quando ativo, ele é anexado ao final dos
          <b> contratos</b> e dos <b>laudos (PTAM)</b> que você gerar.
        </p>

        <div className="flex flex-col sm:flex-row gap-4">
          {/* Pré-visualização */}
          <div className="w-full sm:w-56 flex-shrink-0">
            <div className="aspect-[16/10] rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-center overflow-hidden">
              {cartaoPreview ? (
                <img src={cartaoPreview} alt="Cartão de regularidade" className="w-full h-full object-contain" />
              ) : (
                <span className="text-xs text-gray-400 flex flex-col items-center gap-1">
                  <FileBadge className="w-7 h-7 text-gray-300" />
                  Nenhum cartão enviado
                </span>
              )}
            </div>
            {cartaoPaginas > 1 && (
              <p className="text-[11px] text-gray-500 text-center mt-1">PDF com {cartaoPaginas} páginas (frente/verso)</p>
            )}
          </div>

          {/* Controles */}
          <div className="flex-1 space-y-3">
            <input
              ref={cartaoInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
              className="hidden"
              onChange={handleCartaoFileChange}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => cartaoInputRef.current?.click()}
                disabled={savingCartao}
              >
                {savingCartao ? (
                  <span className="flex items-center gap-1"><Loader2 className="w-4 h-4 animate-spin" />Salvando...</span>
                ) : cartaoPreview ? (
                  <span className="flex items-center gap-1"><Image className="w-4 h-4" />Trocar arquivo</span>
                ) : (
                  <span className="flex items-center gap-1"><Upload className="w-4 h-4" />Enviar cartão (imagem ou PDF)</span>
                )}
              </Button>
              {cartaoPreview && (
                <Button variant="outline" size="sm" onClick={() => visualizarImagens(cartaoImgs, 'Cartão de Regularidade (CRECI)')}>
                  <Eye className="w-4 h-4 mr-1" />Visualizar
                </Button>
              )}
              {cartaoPreview && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveCartao}
                  className="text-red-500 hover:text-red-700 hover:bg-red-50"
                  disabled={savingCartao}
                >
                  <Trash2 className="w-4 h-4 mr-1" />Remover
                </Button>
              )}
            </div>

            <div>
              <label className="text-sm font-medium">Link de verificação on-line (opcional)</label>
              <div className="flex items-center gap-2">
                <Input
                  placeholder="https://app.conselho.net.br/..."
                  value={cartaoLink}
                  onChange={(e) => setCartaoLink(e.target.value)}
                  onBlur={() => persistCartao({ cartao_regularidade_link: cartaoLink })}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="flex-shrink-0 text-emerald-700 border-emerald-700/40 hover:bg-emerald-50"
                  disabled={!cartaoLink?.trim()}
                  onClick={() => window.open(cartaoLink.trim(), '_blank', 'noopener,noreferrer')}
                >
                  <ShieldCheck className="w-4 h-4 mr-1" />Verificar regularidade
                </Button>
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Aparece como selo <span className="text-emerald-700">✓ CRECI regular — verificar em [link]</span> junto à sua qualificação
                nos contratos/procuração e no currículo do laudo (verificação COFECI-CRECI).
              </p>
            </div>

            <div className="flex items-center justify-between py-2 border-t border-gray-100">
              <div>
                <div className="font-medium text-sm">Anexar aos documentos</div>
                <div className="text-xs text-gray-500">Inclui o cartão nos contratos e laudos gerados</div>
              </div>
              <Switch
                checked={cartaoAnexar}
                onCheckedChange={(v) => { setCartaoAnexar(v); persistCartao({ cartao_regularidade_anexar: v }); }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Certidão de Regularidade (CRECI) — gerada on-line, vale 30 dias ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="w-5 h-5 text-[#B8860B]" />
          <h3 className="font-semibold text-gray-900">Certidão de Regularidade (CRECI)</h3>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          Documento emitido on-line pelo CRECI (válido por <b>30 dias</b>). Gere a certidão no site do CRECI-MA,
          faça o upload aqui (imagem ou PDF) e informe a <b>validade</b>. O sistema avisa quando estiver vencida
          para você renovar.
        </p>

        {/* Aviso de validade */}
        {certidaoStatus === 'vencida' && (
          <div className="mb-4 flex flex-col sm:flex-row sm:items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <div className="flex-1 text-sm text-red-700">
              <b>Certidão vencida</b>{certidaoValidadeBR ? ` em ${certidaoValidadeBR}` : ''}. Emita uma nova no CRECI-MA e atualize aqui.
            </div>
            <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white flex-shrink-0" onClick={abrirRenovacaoCertidao}>
              <RefreshCw className="w-4 h-4 mr-1" />Renovar certidão
            </Button>
          </div>
        )}
        {certidaoStatus === 'vencendo' && (
          <div className="mb-4 flex flex-col sm:flex-row sm:items-center gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div className="flex-1 text-sm text-amber-700">
              Sua certidão vence em <b>{certidaoValidadeBR}</b>. Considere renová-la em breve.
            </div>
            <Button size="sm" variant="outline" className="border-amber-400 text-amber-700 flex-shrink-0" onClick={abrirRenovacaoCertidao}>
              <RefreshCw className="w-4 h-4 mr-1" />Renovar
            </Button>
          </div>
        )}
        {(certidaoStatus === 'sem' || certidaoStatus === 'sem_data') && (
          <div className="mb-4 flex flex-col sm:flex-row sm:items-center gap-2 p-3 rounded-lg bg-gray-50 border border-gray-200">
            <AlertCircle className="w-5 h-5 text-gray-500 flex-shrink-0" />
            <div className="flex-1 text-sm text-gray-600">
              {certidaoStatus === 'sem'
                ? 'Nenhuma certidão de regularidade cadastrada. Emita a sua no CRECI-MA.'
                : 'Informe a data de validade da certidão para receber o aviso de renovação.'}
            </div>
            <Button size="sm" variant="outline" className="flex-shrink-0" onClick={abrirRenovacaoCertidao}>
              <RefreshCw className="w-4 h-4 mr-1" />Emitir certidão
            </Button>
          </div>
        )}
        {certidaoStatus === 'ok' && (
          <div className="mb-4 text-sm text-emerald-700 flex items-center gap-1">
            <CheckCircle2 className="w-4 h-4" /> Certidão válida até <b>{certidaoValidadeBR}</b>.
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-4">
          {/* Pré-visualização */}
          <div className="w-full sm:w-56 flex-shrink-0">
            <div className="aspect-[16/10] rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-center overflow-hidden">
              {certidaoPreview ? (
                <img src={certidaoPreview} alt="Certidão de regularidade" className="w-full h-full object-contain" />
              ) : (
                <span className="text-xs text-gray-400 flex flex-col items-center gap-1">
                  <ShieldCheck className="w-7 h-7 text-gray-300" />
                  Nenhuma certidão enviada
                </span>
              )}
            </div>
            {certidaoPaginas > 1 && (
              <p className="text-[11px] text-gray-500 text-center mt-1">PDF com {certidaoPaginas} páginas</p>
            )}
          </div>

          {/* Controles */}
          <div className="flex-1 space-y-3">
            <input
              ref={certidaoInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
              className="hidden"
              onChange={handleCertidaoFileChange}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => certidaoInputRef.current?.click()} disabled={savingCertidao}>
                {savingCertidao ? (
                  <span className="flex items-center gap-1"><Loader2 className="w-4 h-4 animate-spin" />Salvando...</span>
                ) : certidaoPreview ? (
                  <span className="flex items-center gap-1"><Image className="w-4 h-4" />Trocar arquivo</span>
                ) : (
                  <span className="flex items-center gap-1"><Upload className="w-4 h-4" />Enviar certidão (imagem ou PDF)</span>
                )}
              </Button>
              {certidaoPreview && (
                <Button variant="outline" size="sm" onClick={() => visualizarImagens(certidaoImgs, 'Certidão de Regularidade (CRECI)')}>
                  <Eye className="w-4 h-4 mr-1" />Visualizar
                </Button>
              )}
              {certidaoPreview && (
                <Button variant="ghost" size="sm" onClick={handleRemoveCertidao} className="text-red-500 hover:text-red-700 hover:bg-red-50" disabled={savingCertidao}>
                  <Trash2 className="w-4 h-4 mr-1" />Remover
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Validade da certidão</label>
                <Input
                  type="date"
                  value={certidaoValidade}
                  onChange={(e) => setCertidaoValidade(e.target.value)}
                  onBlur={() => persistCertidao({ certidao_regularidade_validade: certidaoValidade })}
                />
                <p className="text-[11px] text-gray-400 mt-1">A certidão CRECI vale 30 dias a partir da emissão.</p>
              </div>
              <div>
                <label className="text-sm font-medium">Link de emissão/renovação</label>
                <Input
                  placeholder={CRECI_CERTIDAO_URL}
                  value={certidaoLink}
                  onChange={(e) => setCertidaoLink(e.target.value)}
                  onBlur={() => persistCertidao({ certidao_regularidade_link: certidaoLink })}
                />
                <p className="text-[11px] text-gray-400 mt-1">Em branco usa o site oficial do CRECI-MA.</p>
              </div>
            </div>

            <div className="flex items-center justify-between py-2 border-t border-gray-100">
              <div>
                <div className="font-medium text-sm">Anexar aos documentos</div>
                <div className="text-xs text-gray-500">Inclui a certidão nos contratos e laudos gerados</div>
              </div>
              <Switch
                checked={certidaoAnexar}
                onCheckedChange={(v) => { setCertidaoAnexar(v); persistCertidao({ certidao_regularidade_anexar: v }); }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Certificado CNAI — miniatura no currículo do PTAM ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-1">
          <FileBadge className="w-5 h-5 text-[#B8860B]" />
          <h3 className="font-semibold text-gray-900">Certificado CNAI</h3>
        </div>
        <p className="text-xs text-gray-500 mb-4">
          Certificado do <b>Cadastro Nacional de Avaliadores de Imóveis (CNAI)</b>. Envie a imagem ou o PDF —
          ele aparece como <b>miniatura no currículo</b> dos seus laudos PTAM (ANEXO IV).
        </p>

        <div className="flex flex-col sm:flex-row gap-4">
          <div className="w-full sm:w-44 flex-shrink-0">
            <div className="aspect-[3/4] rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-center overflow-hidden">
              {cnaiPreview ? (
                <img src={cnaiPreview} alt="Certificado CNAI" className="w-full h-full object-contain" />
              ) : (
                <span className="text-xs text-gray-400 flex flex-col items-center gap-1">
                  <FileBadge className="w-7 h-7 text-gray-300" />
                  Nenhum certificado
                </span>
              )}
            </div>
            {cnaiPaginas > 1 && (
              <p className="text-[11px] text-gray-500 text-center mt-1">PDF com {cnaiPaginas} páginas (usa a 1ª)</p>
            )}
          </div>

          <div className="flex-1 space-y-3">
            <input
              ref={cnaiInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
              className="hidden"
              onChange={handleCnaiFileChange}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => cnaiInputRef.current?.click()} disabled={savingCnai}>
                {savingCnai ? (
                  <span className="flex items-center gap-1"><Loader2 className="w-4 h-4 animate-spin" />Salvando...</span>
                ) : cnaiPreview ? (
                  <span className="flex items-center gap-1"><Image className="w-4 h-4" />Trocar arquivo</span>
                ) : (
                  <span className="flex items-center gap-1"><Upload className="w-4 h-4" />Enviar certificado (imagem ou PDF)</span>
                )}
              </Button>
              {cnaiPreview && (
                <Button variant="outline" size="sm" onClick={() => visualizarImagens(cnaiImgs, 'Certificado CNAI')}>
                  <Eye className="w-4 h-4 mr-1" />Visualizar
                </Button>
              )}
              {cnaiPreview && (
                <Button variant="ghost" size="sm" onClick={handleRemoveCnai} className="text-red-500 hover:text-red-700 hover:bg-red-50" disabled={savingCnai}>
                  <Trash2 className="w-4 h-4 mr-1" />Remover
                </Button>
              )}
            </div>
            <div className="flex items-center justify-between py-2 border-t border-gray-100">
              <div>
                <div className="font-medium text-sm">Exibir no currículo do PTAM</div>
                <div className="text-xs text-gray-500">Miniatura no ANEXO IV (Currículo do Avaliador)</div>
              </div>
              <Switch
                checked={cnaiAnexar}
                onCheckedChange={(v) => { setCnaiAnexar(v); persistCnai({ certificado_cnai_anexar: v }); }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Qualidades do carimbo do ICP (papéis em que assina) ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900">Qualidades para o carimbo do ICP</h3>
        <p className="text-xs text-gray-500 mb-4">Os papéis em que você pode assinar (TTI, Agrimensura, Edificações…). Aparecem num seletor toda vez que você assina com ICP-Brasil — escolha o adequado ao documento. O texto vai no carimbo da assinatura.</p>
        <div className="space-y-2">
          {quals.map((q, i) => (
            <div key={i} className="grid grid-cols-1 sm:grid-cols-[180px,1fr,auto] gap-2 items-center">
              <input className="border rounded-lg px-2.5 py-2 text-sm" placeholder="Rótulo (ex.: Técnico em Agrimensura)" value={q.label || ''} onChange={(e) => updQual(i, 'label', e.target.value)} />
              <input className="border rounded-lg px-2.5 py-2 text-sm" placeholder="Texto no carimbo (ex.: Técnico em Agrimensura — CFT/MA … · INCRA …)" value={q.value || ''} onChange={(e) => updQual(i, 'value', e.target.value)} />
              <button onClick={() => rmQual(i)} className="text-red-500 hover:text-red-700 text-sm px-2 py-1 justify-self-start">Remover</button>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 mt-3">
          <button onClick={addQual} className="text-sm text-emerald-700 hover:underline">+ Adicionar qualidade</button>
          <Button size="sm" onClick={salvarQuals} disabled={savingQuals}>{savingQuals ? 'Salvando…' : 'Salvar qualidades'}</Button>
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

  // Vindo do botao "Ir para Configuracoes" da assinatura (#certificados):
  // rola ate a secao e ja abre o formulario de cadastro.
  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.hash === '#certificados') {
      setShowForm(true);
      setTimeout(() => {
        document.getElementById('certificados')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 200);
    }
  }, []);

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
    <div id="certificados" className="bg-white rounded-xl border border-gray-200 p-6 scroll-mt-20">
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
