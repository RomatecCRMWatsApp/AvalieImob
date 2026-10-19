// @module garantias/GarantiasList — lista de Avaliações de Garantia.
// O card tem TODAS as ações do card do PTAM: abrir, visualizar, PDF, clonar, assinar
// (ICP), posicionar, re-assinar, recibo, PDF assinado, zerar assinatura, WhatsApp,
// Telegram, e-mail, envio para assinatura externa, link público, DOCX e excluir.
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Loader2, Trash2, Calendar, Filter, Tractor, Wheat, Beef, Wrench, Car, Package, Shield,
  Building2, Edit3, Eye, FileDown, Download, Copy as CopyIcon, Lock, ShieldCheck, MapPin,
  RefreshCw, Receipt, MessageCircle, Send, Mail, Link2, User, Ruler,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { useToast } from '../../../hooks/use-toast';
import { garantiasAPI, assinaturaAPI } from '../../../lib/api';
import { fmtDataHora } from '../../../utils/datasServidor';
import AssinaturaDigital from '../ptam/AssinaturaDigital';
import AssinaturaPosicionadaModal from '../assinatura/AssinaturaPosicionadaModal';
import EnviarAssinaturaModal from '../assinatura/EnviarAssinaturaModal';
import {
  EmailModal, ShareModal, ReciboModal, TelegramModal, LinkEventosModal, PdfViewer, rotulo,
} from './GarantiaModais';

const MODALIDADE_CONFIG = {
  sfh_fgts:             { label: 'SFH/FGTS',              color: 'bg-blue-100 text-blue-800' },
  sfi_bancario:         { label: 'SFI/Bancário',           color: 'bg-indigo-100 text-indigo-800' },
  alienacao_fiduciaria: { label: 'Alienação Fiduciária',   color: 'bg-violet-100 text-violet-800' },
  hipoteca:             { label: 'Hipoteca',               color: 'bg-cyan-100 text-cyan-800' },
  credito_rural:        { label: 'Crédito Rural',          color: 'bg-lime-100 text-lime-800' },
};

const TIPO_CONFIG = {
  imovel_rural:  { label: 'Imóvel Rural',     icon: Tractor,   color: 'bg-green-100 text-green-800' },
  imovel_urbano: { label: 'Imóvel Urbano',    icon: Building2, color: 'bg-teal-100 text-teal-800' },
  apartamento:   { label: 'Apartamento',      icon: Building2, color: 'bg-teal-100 text-teal-800' },
  casa:          { label: 'Casa',             icon: Building2, color: 'bg-teal-100 text-teal-800' },
  comercial:     { label: 'Comercial',        icon: Building2, color: 'bg-teal-100 text-teal-800' },
  terreno:       { label: 'Terreno',          icon: Building2, color: 'bg-teal-100 text-teal-800' },
  graos_safra:   { label: 'Grãos / Safra',    icon: Wheat,     color: 'bg-yellow-100 text-yellow-800' },
  bovinos:       { label: 'Bovinos',          icon: Beef,      color: 'bg-orange-100 text-orange-800' },
  equipamentos:  { label: 'Equipamentos',     icon: Wrench,    color: 'bg-blue-100 text-blue-800' },
  veiculos:      { label: 'Veículos',         icon: Car,       color: 'bg-purple-100 text-purple-800' },
  outros:        { label: 'Outros',           icon: Package,   color: 'bg-gray-100 text-gray-700' },
};

const STATUS_CONFIG = {
  rascunho:     { label: 'Rascunho',     color: 'bg-gray-100 text-gray-700' },
  em_andamento: { label: 'Em Andamento', color: 'bg-amber-100 text-amber-800' },
  concluido:    { label: 'Concluído',    color: 'bg-emerald-100 text-emerald-800' },
};

const TIPO_OPTIONS = [
  { value: '', label: 'Todos os tipos' },
  { value: 'imovel_rural', label: 'Imóvel Rural' },
  { value: 'imovel_urbano', label: 'Imóvel Urbano' },
  { value: 'apartamento', label: 'Apartamento' },
  { value: 'casa', label: 'Casa' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'graos_safra', label: 'Grãos / Safra' },
  { value: 'bovinos', label: 'Bovinos' },
  { value: 'equipamentos', label: 'Equipamentos' },
  { value: 'veiculos', label: 'Veículos' },
  { value: 'outros', label: 'Outros' },
];

const MODALIDADE_OPTIONS = [
  { value: '', label: 'Todas as modalidades' },
  { value: 'sfh_fgts', label: 'SFH/FGTS' },
  { value: 'sfi_bancario', label: 'SFI/Bancário' },
  { value: 'alienacao_fiduciaria', label: 'Alienação Fiduciária' },
  { value: 'hipoteca', label: 'Hipoteca' },
  { value: 'credito_rural', label: 'Crédito Rural' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_andamento', label: 'Em Andamento' },
  { value: 'concluido', label: 'Concluído' },
];

// Foto de capa do card (fotos são ids de imagem).
function fotoCapa(g) {
  const f = (g.fotos || [])[0];
  if (!f) return null;
  const id = String(typeof f === 'string' ? f : (f.image_id || f.id || f.url || ''));
  if (!id) return null;
  return id.startsWith('http') || id.startsWith('/') ? id : `/api/upload/image/${id}`;
}

// Mesmo nome de arquivo do backend (services/garantia_assets.nome_arquivo).
const nomeArq = (g, sufixo = '', ext = 'pdf') =>
  `Laudo_Garantia_${String(g.numero || g.id || 'sem-numero').replace(/\//g, '-')}${sufixo}.${ext}`;

const baixarBlob = (blob, nome) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  a.click();
  window.URL.revokeObjectURL(url);
};

// O backend devolve o erro como Blob quando a resposta esperada era um arquivo.
const erroDe = async (e) => {
  try {
    const d = e?.response?.data;
    if (d instanceof Blob) {
      const t = await d.text();
      try { return JSON.parse(t)?.detail || t; } catch { return t; }
    }
    return d?.detail || e?.message || 'Tente novamente';
  } catch { return e?.message || 'Tente novamente'; }
};

const areaTxt = (g) => {
  const ha = Number(g.area_total_ha || 0);
  const m2 = Number(g.area_construida_m2 || g.area_privativa_nbr12721 || 0);
  if (g.tipo_garantia === 'imovel_rural' && ha > 0) return `${ha.toLocaleString('pt-BR', { maximumFractionDigits: 4 })} ha`;
  if (m2 > 0) return `${m2.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} m²`;
  return null;
};

const telSugerido = (g) => {
  const t = String(g.solicitante?.telefone || '').replace(/\D/g, '').replace(/^55/, '');
  return t ? `55${t}` : '55';
};

const GarantiasList = () => {
  const nav = useNavigate();
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterTipo, setFilterTipo] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterModalidade, setFilterModalidade] = useState('');
  const [busy, setBusy] = useState({}); // { `${id}:${acao}`: true }
  const [pdfModal, setPdfModal] = useState(null);
  const [emailModal, setEmailModal] = useState(null);
  const [shareModal, setShareModal] = useState(null);
  const [reciboModal, setReciboModal] = useState(null);
  const [telegramModal, setTelegramModal] = useState(null);
  const [eventosModal, setEventosModal] = useState(null);
  const [assinaturaModal, setAssinaturaModal] = useState(null);
  const [posicionarModal, setPosicionarModal] = useState(null);
  const [envioExternoModal, setEnvioExternoModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterTipo) params.tipo = filterTipo;
      if (filterStatus) params.status = filterStatus;
      setItems(await garantiasAPI.list(params));
    } catch (err) {
      console.warn(err);
      toast({ title: 'Erro ao carregar garantias', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast, filterTipo, filterStatus]);

  useEffect(() => { load(); }, [load]);

  const rodar = async (g, acao, fn) => {
    const k = `${g.id}:${acao}`;
    setBusy((b) => ({ ...b, [k]: true }));
    try { await fn(); } finally { setBusy((b) => ({ ...b, [k]: false })); }
  };
  const ocupado = (g, acao) => !!busy[`${g.id}:${acao}`];

  const remove = async (id) => {
    if (!window.confirm('Remover esta avaliação de garantia? Esta ação não pode ser desfeita.')) return;
    try {
      await garantiasAPI.remove(id);
      setItems(items.filter((g) => g.id !== id));
      toast({ title: 'Avaliação removida' });
    } catch {
      toast({ title: 'Erro ao remover', variant: 'destructive' });
    }
  };

  const visualizar = (g) => rodar(g, 'pdf', async () => {
    try {
      const blob = await garantiasAPI.downloadPdf(g.id);
      setPdfModal({ url: window.URL.createObjectURL(blob), titulo: `${rotulo(g)} — Avaliação de Garantia` });
    } catch (e) { toast({ title: 'Erro ao abrir PDF', description: await erroDe(e), variant: 'destructive' }); }
  });
  const fecharPdf = () => setPdfModal((m) => { if (m?.url) window.URL.revokeObjectURL(m.url); return null; });

  const baixarPdf = (g) => rodar(g, 'pdf', async () => {
    try { baixarBlob(await garantiasAPI.downloadPdf(g.id), nomeArq(g)); toast({ title: 'PDF gerado com sucesso' }); }
    catch (e) { toast({ title: 'Erro ao gerar PDF', description: await erroDe(e), variant: 'destructive' }); }
  });

  const baixarDocx = (g) => rodar(g, 'docx', async () => {
    try { baixarBlob(await garantiasAPI.downloadDocx(g.id), nomeArq(g, '', 'docx')); toast({ title: 'DOCX gerado com sucesso' }); }
    catch (e) { toast({ title: 'Erro ao baixar DOCX', description: await erroDe(e), variant: 'destructive' }); }
  });

  const baixarAssinado = (g) => rodar(g, 'pdf', async () => {
    try { baixarBlob(await assinaturaAPI.downloadIcp('garantia', g.id), nomeArq(g, '_ASSINADO_ICP')); toast({ title: 'PDF assinado baixado' }); }
    catch (e) { toast({ title: 'Erro ao baixar PDF assinado', description: await erroDe(e), variant: 'destructive' }); }
  });

  const zerarAssinatura = async (g) => {
    if (!window.confirm(`Zerar a assinatura do ${rotulo(g)}?\n\nO PDF assinado será removido e o laudo volta a "não assinado" para re-assinar.`)) return;
    try {
      await assinaturaAPI.resetarIcp('garantia', g.id);
      setItems((prev) => prev.map((x) => (x.id === g.id ? { ...x, icp_status: null, icp_signed_at: null } : x)));
      toast({ title: 'Assinatura zerada', description: 'Pode re-assinar agora.' });
    } catch (e) { toast({ title: 'Erro ao zerar assinatura', description: await erroDe(e), variant: 'destructive' }); }
  };

  const clonar = (g) => rodar(g, 'clone', async () => {
    try {
      const novo = await garantiasAPI.clonar(g.id);
      toast({ title: `Avaliação clonada: ${novo.numero}` });
      load();
    } catch (e) { toast({ title: 'Erro ao clonar', description: e.response?.data?.detail, variant: 'destructive' }); }
  });

  const linkUrl = (g) => `${window.location.origin}/api/garantias/publico/${g.link_publico_token}`;

  // Envio direto via Z-API ou Meta; sem integração, cai para o WhatsApp Web.
  const enviarWhatsApp = async (g) => {
    const phone = window.prompt('WhatsApp do destinatário (com DDI+DDD, só dígitos):', telSugerido(g));
    if (!phone) return;
    try {
      const res = await garantiasAPI.enviarWhatsApp(g.id, phone.trim());
      toast({ title: `Laudo enviado via ${res.provider === 'meta' ? 'Meta' : 'Z-API'}!` });
      load();
    } catch (e) {
      const detail = e.response?.data?.detail || '';
      if (/configurad|Cadastre/.test(detail)) {
        const texto = `Segue o laudo de avaliação de garantia ${g.numero || ''}` + (g.link_publico_ativo ? `\n${linkUrl(g)}` : '');
        toast({ title: 'Z-API/Meta não configurados', description: 'Abrindo no WhatsApp Web (modo manual). Configure em Configurações → Integrações.' });
        window.open(`https://wa.me/${phone.replace(/\D/g, '')}?text=${encodeURIComponent(texto)}`, '_blank');
      } else {
        toast({ title: detail || 'Erro ao enviar WhatsApp', variant: 'destructive' });
      }
    }
  };

  const compartilhar = (g) => rodar(g, 'link', async () => {
    if (g.link_publico_ativo && g.link_publico_token) { setShareModal(g); return; }
    try {
      const res = await garantiasAPI.compartilhar(g.id);
      try { await navigator.clipboard.writeText(res.url); } catch { /* navegador sem clipboard */ }
      toast({ title: 'Link gerado!', description: 'URL copiada para a área de transferência' });
      load();
    } catch (e) { toast({ title: 'Erro ao compartilhar', description: e.response?.data?.detail, variant: 'destructive' }); }
  });

  const desativarLink = async (g) => {
    try { await garantiasAPI.desativarCompartilhamento(g.id); toast({ title: 'Compartilhamento desativado' }); load(); }
    catch { toast({ title: 'Erro ao desativar', variant: 'destructive' }); }
  };

  const fmtCurrency = (v) =>
    Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 });

  // Filtro client-side por modalidade (campo novo)
  const filtered = filterModalidade
    ? items.filter((g) => g.modalidade_financeira === filterModalidade)
    : items;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-6 h-6 text-emerald-800" />
            <h1 className="font-display text-3xl font-bold text-[#B8860B] dark:text-amber-400">Avaliação de Garantias</h1>
          </div>
          <p className="text-gray-600">
            Laudos conforme Res. CMN 4.676/2018 | NBR 14.653 — rurais, bancários, alienação fiduciária e mais.
          </p>
        </div>
        <Button
          onClick={() => nav('/dashboard/garantias/nova')}
          className="bg-emerald-900 hover:bg-emerald-800 text-white"
        >
          <Plus className="w-4 h-4 mr-2" />Nova Avaliação
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white border border-gray-200 rounded-xl p-4">
        <Filter className="w-4 h-4 text-gray-400" />
        <select
          value={filterTipo}
          onChange={(e) => setFilterTipo(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {TIPO_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filterModalidade}
          onChange={(e) => setFilterModalidade(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {MODALIDADE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {(filterTipo || filterStatus || filterModalidade) && (
          <button
            onClick={() => { setFilterTipo(''); setFilterStatus(''); setFilterModalidade(''); }}
            className="text-xs text-red-500 hover:text-red-700 underline"
          >
            Limpar filtros
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="py-16 flex justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-800" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <div className="font-semibold text-gray-900">Nenhuma avaliação de garantia encontrada</div>
          <p className="text-sm text-gray-500 mt-1">
            {filterTipo || filterStatus || filterModalidade
              ? 'Tente outros filtros ou limpe a busca.'
              : 'Clique em "Nova Avaliação" para começar.'}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((g) => {
            const tipo = TIPO_CONFIG[g.tipo_garantia] || TIPO_CONFIG.outros;
            const status = STATUS_CONFIG[g.status] || STATUS_CONFIG.rascunho;
            const modalidade = g.modalidade_financeira ? MODALIDADE_CONFIG[g.modalidade_financeira] : null;
            const Icon = tipo.icon;
            const valorDisplay = g.valor_mercado || g.valor_total;
            const assinado = g.icp_status === 'assinado';
            const foto = fotoCapa(g);
            const area = areaTxt(g);
            const local = [g.endereco, [g.municipio, g.uf].filter(Boolean).join('/')].filter(Boolean).join(' · ');
            return (
              <div key={g.id} className="bg-white border-gray-200 dark:bg-[#0f1420] dark:border-white/10 rounded-xl border overflow-hidden hover:shadow-md transition flex flex-col">
                {/* Banner de foto */}
                <div className="relative h-[100px] bg-gray-100 dark:bg-[#141824]">
                  {foto ? (
                    <img src={foto} alt="Bem avaliado" className="w-full h-full object-cover" loading="lazy"
                      onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-300 dark:text-[#2d3348]"><Icon className="w-8 h-8" /></div>
                  )}
                  <div className="absolute top-2 right-2">
                    <Badge className={assinado ? 'bg-emerald-600 text-white' : status.color}>{assinado ? '✓ Assinado' : status.label}</Badge>
                  </div>
                  {(g.fotos?.length || 0) > 1 && (
                    <div className="absolute bottom-1.5 right-2 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded">{g.fotos.length} fotos</div>
                  )}
                </div>

                <div className="p-4 flex flex-col flex-1">
                  <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 tracking-wider">{g.numero || 'Sem número'}</div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    <Badge className={`${tipo.color} text-[10px]`}>{tipo.label}</Badge>
                    {modalidade && <Badge className={`${modalidade.color} text-[10px]`}>{modalidade.label}</Badge>}
                  </div>
                  <div className="font-semibold text-gray-900 dark:text-white mt-2 line-clamp-1">
                    {g.mutuario_nome || g.descricao_bem || g.municipio || '(sem descrição)'}
                  </div>
                  <div className="mt-2 space-y-1">
                    {(g.instituicao_financeira || g.solicitante?.nome) && (
                      <div className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-slate-300 line-clamp-1">
                        <User className="w-3 h-3 shrink-0 text-gray-400" />{g.instituicao_financeira || g.solicitante?.nome}
                      </div>
                    )}
                    {local && (
                      <div className="flex items-start gap-1.5 text-xs text-gray-500 dark:text-slate-400 line-clamp-2">
                        <MapPin className="w-3 h-3 shrink-0 mt-0.5 text-gray-400" />
                        <span>{local}{g.matricula ? ` · Matrícula ${g.matricula}` : ''}</span>
                      </div>
                    )}
                    {area && (
                      <div className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-slate-300">
                        <Ruler className="w-3 h-3 shrink-0 text-gray-400" />Área: {area}
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-4 border-t border-gray-100 dark:border-white/10">
                    <div className="text-xl font-bold text-gray-900 dark:text-white tabular-nums">{fmtCurrency(valorDisplay)}</div>
                    <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                      <Calendar className="w-3 h-3" />{fmtDataHora(g.updated_at) || '—'}
                    </div>
                  </div>

                  {/* Linha 1: ações principais */}
                  <div className="flex gap-2 mt-4 flex-wrap">
                    <Button size="sm" className="bg-amber-400 hover:bg-amber-500 text-emerald-950 font-semibold gap-1"
                      onClick={() => nav(`/dashboard/garantias/${g.id}`)} title="Abrir / Editar">
                      <Edit3 className="w-3.5 h-3.5" />Abrir
                    </Button>
                    <Button size="sm" variant="outline" title="Visualizar PDF no navegador" onClick={() => visualizar(g)}
                      disabled={ocupado(g, 'pdf')} className="gap-1 border-emerald-300 text-emerald-700 hover:bg-emerald-50">
                      {ocupado(g, 'pdf') ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Eye className="w-3.5 h-3.5" />}Visualizar
                    </Button>
                    <Button size="sm" variant="outline" title="Exportar PDF" onClick={() => baixarPdf(g)} disabled={ocupado(g, 'pdf')} className="gap-1">
                      <FileDown className="w-3.5 h-3.5" />PDF
                    </Button>
                    <Button size="sm" variant="outline" title="Clonar avaliação" onClick={() => clonar(g)} disabled={ocupado(g, 'clone')}
                      className="gap-1 text-amber-700 border-amber-200 hover:bg-amber-50">
                      {ocupado(g, 'clone') ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CopyIcon className="w-3.5 h-3.5" />}Clonar
                    </Button>
                  </div>

                  {/* Linha 2: assinatura e recibo */}
                  <div className="flex gap-2 mt-2 flex-wrap">
                    <Button size="sm" variant="outline" title={assinado ? 'Assinado com ICP-Brasil' : 'Assinar digitalmente'}
                      onClick={() => setAssinaturaModal(g)}
                      className={`gap-1 ${assinado ? 'text-emerald-700 border-emerald-300 bg-emerald-50 hover:bg-emerald-100' : 'text-emerald-700 border-emerald-200 hover:bg-emerald-50'}`}>
                      {assinado ? <ShieldCheck className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}{assinado ? 'Assinado' : 'Assinar'}
                    </Button>
                    <Button size="sm" variant="outline" title="Assinar ICP-Brasil posicionando o carimbo (arrastar na página)"
                      onClick={() => setPosicionarModal(g)} className="gap-1 text-emerald-700 border-emerald-200 hover:bg-emerald-50">
                      <MapPin className="w-3.5 h-3.5" />Posicionar
                    </Button>
                    {assinado && (
                      <Button size="sm" variant="outline" title="Reassinar (gera nova assinatura sobre a versão atual)"
                        onClick={() => setAssinaturaModal({ ...g, icp_status: null })} className="gap-1 text-blue-700 border-blue-200 hover:bg-blue-50">
                        <RefreshCw className="w-3.5 h-3.5" />Re-assinar
                      </Button>
                    )}
                    <Button size="sm" variant="outline" title={g.recibo_emitido ? 'Recibo de honorários emitido' : 'Recibo de honorários'}
                      onClick={() => setReciboModal(g)}
                      className={`gap-1 transition-colors ${g.recibo_emitido ? 'text-white border-transparent bg-green-600 hover:bg-green-700' : 'text-amber-800 border-amber-200 bg-amber-50 hover:bg-amber-100'}`}>
                      <Receipt className="w-3.5 h-3.5" />{g.recibo_emitido ? '✓ Recibo Emitido' : 'Recibo'}
                    </Button>
                    {g.recibo_assinado && (
                      <Button size="sm" variant="outline" title="Recibo assinado — abrir na aba Recibos"
                        onClick={() => nav(g.recibo_id ? `/dashboard/recibos/${g.recibo_id}` : '/dashboard/recibos')}
                        className="gap-1 text-white border-transparent bg-green-700 hover:bg-green-800">
                        <ShieldCheck className="w-3.5 h-3.5" />✓ Recibo Assinado
                      </Button>
                    )}
                    {assinado && (
                      <Button size="sm" variant="outline" title="Baixar PDF assinado (ICP-Brasil)" onClick={() => baixarAssinado(g)}
                        disabled={ocupado(g, 'pdf')} className="gap-1 text-emerald-700 border-emerald-300 bg-emerald-50 hover:bg-emerald-100">
                        <FileDown className="w-3.5 h-3.5" />PDF Assinado
                      </Button>
                    )}
                    {assinado && (
                      <Button size="sm" variant="outline" title="Zerar assinatura (remove o assinado para re-assinar)"
                        onClick={() => zerarAssinatura(g)} className="gap-1 text-red-700 border-red-200 bg-red-50 hover:bg-red-100">
                        <RefreshCw className="w-3.5 h-3.5" />Zerar assinatura
                      </Button>
                    )}
                  </div>

                  {/* Linha 3: envio */}
                  <div className="flex gap-2 mt-2 flex-wrap">
                    <Button size="sm" className="flex-1 bg-green-600 hover:bg-green-700 text-white gap-1" title="Enviar por WhatsApp" onClick={() => enviarWhatsApp(g)}>
                      <MessageCircle className="w-3.5 h-3.5" />WhatsApp
                    </Button>
                    <Button size="sm" className="flex-1 bg-sky-500 hover:bg-sky-600 text-white gap-1" title="Enviar via Telegram" onClick={() => setTelegramModal(g)}>
                      <Send className="w-3.5 h-3.5" />Telegram
                    </Button>
                    <Button size="sm" variant="outline" title="Enviar por E-mail" onClick={() => setEmailModal(g)} className="text-emerald-700 hover:bg-emerald-50 border-emerald-200">
                      <Mail className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="sm" variant="outline" title="Enviar para assinatura (D4Sign/Clicksign/Autentique)" onClick={() => setEnvioExternoModal(g)}
                      className="text-emerald-700 hover:bg-emerald-50 border-emerald-200">
                      <ShieldCheck className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="sm" variant="outline" title={g.link_publico_ativo ? 'Link ativo' : 'Compartilhar via link'} onClick={() => compartilhar(g)}
                      disabled={ocupado(g, 'link')} className={g.link_publico_ativo ? 'text-blue-600 border-blue-200 hover:bg-blue-50' : ''}>
                      {ocupado(g, 'link') ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Link2 className="w-3.5 h-3.5" />}
                    </Button>
                    <Button size="sm" variant="outline" title="Exportar DOCX" onClick={() => baixarDocx(g)} disabled={ocupado(g, 'docx')}>
                      {ocupado(g, 'docx') ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                    </Button>
                    <Button size="sm" variant="outline" className="text-red-600 hover:bg-red-50" onClick={() => remove(g.id)} title="Excluir">
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>

                  {/* Controle do link: visualizações + envios + histórico */}
                  {(g.link_publico_ativo || g.link_views > 0 || g.link_sends > 0) && (
                    <div className="flex items-center justify-between mt-2 px-1 text-xs text-gray-500">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1" title="Visualizações do cliente">
                          <Eye className="w-3.5 h-3.5 text-blue-500" /> {g.link_views || 0}
                        </span>
                        <span className="flex items-center gap-1" title="Envios realizados">
                          <Send className="w-3.5 h-3.5 text-emerald-600" /> {g.link_sends || 0}
                          {g.link_last_canal ? ` · ${g.link_last_canal}` : ''}
                        </span>
                      </div>
                      <button onClick={() => setEventosModal(g)} className="text-blue-600 hover:underline font-medium">Histórico</button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {pdfModal && <PdfViewer modal={pdfModal} onClose={fecharPdf} />}
      {emailModal && <EmailModal g={emailModal} onClose={() => setEmailModal(null)} onSent={load} />}
      {shareModal && (
        <ShareModal g={shareModal} url={linkUrl(shareModal)} onClose={() => { setShareModal(null); load(); }}
          onDesativar={() => desativarLink(shareModal)} />
      )}
      {reciboModal && <ReciboModal g={reciboModal} onClose={() => setReciboModal(null)} onGerado={load} />}
      {telegramModal && <TelegramModal g={telegramModal} onClose={() => { setTelegramModal(null); load(); }} />}
      {eventosModal && <LinkEventosModal g={eventosModal} onClose={() => setEventosModal(null)} />}
      {assinaturaModal && (
        <AssinaturaDigital
          tipo="garantia"
          docId={assinaturaModal.id}
          docData={{ ...assinaturaModal, number: assinaturaModal.numero }}
          onClose={() => { setAssinaturaModal(null); load(); }}
          onUpdate={(upd) => setItems((prev) => prev.map((x) => (x.id === assinaturaModal.id ? { ...x, ...upd } : x)))}
        />
      )}
      {posicionarModal && (
        <AssinaturaPosicionadaModal
          tipo="garantia"
          documentId={posicionarModal.id}
          onAssinado={() => {
            setItems((prev) => prev.map((x) => (x.id === posicionarModal.id
              ? { ...x, icp_status: 'assinado', icp_signed_at: new Date().toISOString() } : x)));
            setPosicionarModal(null);
          }}
          onFechar={() => setPosicionarModal(null)}
        />
      )}
      {envioExternoModal && (
        <EnviarAssinaturaModal
          origemTipo="garantia"
          origemId={envioExternoModal.id}
          origemLabel={rotulo(envioExternoModal)}
          onClose={() => setEnvioExternoModal(null)}
        />
      )}
    </div>
  );
};

export default GarantiasList;
