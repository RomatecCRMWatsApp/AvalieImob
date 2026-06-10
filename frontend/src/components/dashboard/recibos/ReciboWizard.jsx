// @module recibos/ReciboWizard — Wizard com form à esquerda e preview PDF live à direita
//
// Padrão visual igual ao Gestão de Obras (ZAYRA), mas com cores Romatec AvalieImob:
//   - Form 2 colunas com campos: emitir como, tipo, categoria, serviço,
//     destinatário, WhatsApp, CPF/CNPJ, email, valor, forma pagamento,
//     validade, descrição.
//   - Preview do PDF à direita com refresh automático (debounce 600ms).
//   - 3 botões finais: Salvar rascunho, Salvar sem enviar, Salvar e enviar via WhatsApp.
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Receipt, Save, Send, Loader2, Building2, User as UserIcon,
  FileText, MessageCircle, Hourglass, Paperclip, X, Upload,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Textarea } from '../../ui/textarea';
import RichTextEditor from '../../ui/RichTextEditor';
import { paraEditorHtml } from '../../ui/RichField';
import { AiButton } from '../ptam/shared/primitives';
import { useToast } from '../../../hooks/use-toast';
import { useAuth } from '../../../contexts/AuthContext';
import { recibosAPI, perfilAPI, aiAPI } from '../../../lib/api';
import { useCatalogoServicos } from './useCatalogoServicos';

const ANEXO_TIPOS_OK = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const ANEXO_MAX_BYTES = 10 * 1024 * 1024;
const ANEXO_MAX = 5;
const fmtTam = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.round(b / 1024)} KB`);

const FORMAS_DEFAULT = ['PIX', 'Dinheiro', 'Transferência bancária', 'Boleto', 'Cartão de crédito', 'Cartão de débito', 'Cheque'];

const initialForm = {
  emitente_perfil: 'PJ',
  emitente_nome: '',
  emitente_documento: '',
  emitente_endereco: '',
  emitente_telefone: '',
  emitente_email: '',
  emitente_dados_bancarios: '',
  tipo: 'personalizado',
  categoria: '',
  servico: '',
  destinatario_nome: '',
  destinatario_whatsapp: '',
  destinatario_cpf_cnpj: '',
  destinatario_email: '',
  valor: '',
  forma_pagamento: 'PIX',
  validade_dias: 7,
  data_pagamento: new Date().toISOString().slice(0, 10),
  descricao: '',
  status: 'rascunho',
};


const ReciboWizard = () => {
  const nav = useNavigate();
  const { id } = useParams();
  const { user } = useAuth();
  const { toast } = useToast();
  const editing = id && id !== 'novo';

  const [form, setForm] = useState(initialForm);
  const [tipos, setTipos] = useState([]);
  const [formas, setFormas] = useState(FORMAS_DEFAULT);
  const [perfilUser, setPerfilUser] = useState(null);
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const debounceRef = useRef(null);
  const lastBlobRef = useRef(null);

  // Catálogo cascata categoria → serviço
  const { categorias, servicosDe, buscarServico } = useCatalogoServicos();
  const [catSel, setCatSel] = useState('');   // value da categoria selecionada
  const [servSel, setServSel] = useState(''); // value do serviço selecionado

  // Anexos: staged (File[] ainda não salvos) + existentes (na edição)
  const [anexosStaged, setAnexosStaged] = useState([]);
  const fileInputRef = useRef(null);

  // ── Carrega tipos disponíveis ──────────────────────────────────
  useEffect(() => {
    recibosAPI.tipos().then(d => {
      setTipos(d.tipos || []);
      if (d.formas_pagamento) setFormas(d.formas_pagamento);
    }).catch(() => {});
  }, []);

  // ── Carrega perfil do avaliador (pra hidratar emitente) ────────
  useEffect(() => {
    perfilAPI.get().then(p => {
      setPerfilUser(p);
      // Auto-preenche se estiver criando novo
      if (!editing) {
        setForm(prev => ({
          ...prev,
          emitente_perfil: p?.empresa_cnpj ? 'PJ' : 'PF',
          emitente_nome: p?.empresa_nome || p?.nome_completo || user?.name || '',
          emitente_documento: p?.empresa_cnpj || p?.cpf || '',
          emitente_endereco: p?.endereco_escritorio || '',
          emitente_telefone: p?.telefone || '',
          emitente_email: p?.email_profissional || user?.email || '',
        }));
      }
    }).catch(() => {});
  }, [editing, user]);

  // ── Carrega recibo existente (modo edição) ─────────────────────
  useEffect(() => {
    if (!editing) return;
    setLoading(true);
    recibosAPI.buscar(id).then(d => {
      setForm({
        ...initialForm,
        ...d,
        valor: d.valor != null ? String(d.valor) : '',
        data_pagamento: d.data_pagamento || new Date().toISOString().slice(0, 10),
      });
    }).catch(() => {
      toast({ title: 'Recibo não encontrado', variant: 'destructive' });
      nav('/dashboard/recibos');
    }).finally(() => setLoading(false));
  }, [editing, id, nav, toast]);

  // ── Reverse-map (edição): label salvo → value do select ────────
  useEffect(() => {
    if (!categorias.length) return;
    if (catSel) return;
    if (!form.categoria && !form.servico) return;
    const cat = categorias.find(c => c.label === form.categoria);
    if (cat) {
      setCatSel(cat.value);
      const serv = (cat.servicos || []).find(s => s.label === form.servico);
      if (serv) setServSel(serv.value);
    }
  }, [categorias, form.categoria, form.servico, catSel]);

  // ── Aperfeiçoar com IA (mesmo padrão do PTAM) ──────────────────
  const [aiLoading, setAiLoading] = useState(false);

  const handleAiDescricao = async () => {
    const atual = form.descricao || '';
    const prompt =
      'Aperfeiçoe tecnicamente este texto de descrição de serviço para um RECIBO de honorários/serviços. ' +
      'Mantenha tom formal, claro e profissional em português-BR. Seja conciso (2 a 4 frases). ' +
      'Retorne APENAS o texto aperfeiçoado, sem explicações, sem títulos e sem rótulos.\n\n' +
      `Tipo: ${form.servico || form.tipo || 'serviço'}\n` +
      `Texto atual:\n${atual || '(vazio — gere uma descrição inicial adequada ao serviço)'}`;
    setAiLoading(true);
    try {
      const session_id = `recibo_${id || 'draft'}_descricao_${Date.now()}`;
      const res = await aiAPI.chat(session_id, prompt);
      const texto = (res?.reply || '').trim();
      if (texto) setForm((f) => ({ ...f, descricao: texto }));
      toast({ title: 'Texto aperfeiçoado com IA' });
    } catch (err) {
      toast({
        title: 'Erro na IA',
        description: err.response?.data?.detail || 'Tente novamente',
        variant: 'destructive',
      });
    } finally {
      setAiLoading(false);
    }
  };

  // ── Handlers cascata ───────────────────────────────────────────
  const onCategoriaChange = (e) => {
    const v = e.target.value;
    setCatSel(v);
    setServSel('');
    const cat = categorias.find(c => c.value === v);
    setForm(prev => ({ ...prev, categoria: cat?.label || '', servico: '' }));
  };

  const onServicoChange = (e) => {
    const v = e.target.value;
    setServSel(v);
    const serv = buscarServico(catSel, v);
    if (!serv) {
      setForm(prev => ({ ...prev, servico: '' }));
      return;
    }
    setForm(prev => ({
      ...prev,
      servico: serv.label,
      tipo: serv.tipo || prev.tipo,
      // Auto-preenche a descrição só se estiver vazia ou for um template anterior
      descricao: (!prev.descricao || prev.descricao === prev._descTemplate)
        ? serv.descricao
        : prev.descricao,
      _descTemplate: serv.descricao,
    }));
  };

  // ── Handlers de anexos ─────────────────────────────────────────
  const totalAnexos = (form.anexos?.length || 0) + anexosStaged.length;

  const onPickAnexos = (e) => {
    const files = Array.from(e.target.files || []);
    if (e.target) e.target.value = '';
    let count = totalAnexos;  // saved + staged já existentes
    const aceitos = [];
    for (const f of files) {
      if (count >= ANEXO_MAX) {
        toast({ title: `Máximo de ${ANEXO_MAX} anexos`, variant: 'destructive' });
        break;
      }
      const ct = (f.type || '').toLowerCase();
      if (!ANEXO_TIPOS_OK.includes(ct)) {
        toast({ title: `Tipo não permitido: ${f.name}`, variant: 'destructive' });
        continue;
      }
      if (f.size > ANEXO_MAX_BYTES) {
        toast({ title: `${f.name} excede 10MB`, variant: 'destructive' });
        continue;
      }
      aceitos.push(f);
      count += 1;
    }
    if (aceitos.length) setAnexosStaged(prev => [...prev, ...aceitos]);
  };

  const removerStaged = (idx) =>
    setAnexosStaged(prev => prev.filter((_, i) => i !== idx));

  const removerAnexoSalvo = async (anexoId) => {
    if (!editing) return;
    try {
      await recibosAPI.removerAnexo(id, anexoId);
      setForm(prev => ({ ...prev, anexos: (prev.anexos || []).filter(a => a.id !== anexoId) }));
      toast({ title: 'Anexo removido' });
    } catch {
      toast({ title: 'Erro ao remover anexo', variant: 'destructive' });
    }
  };

  // ── Preview live (debounced) ───────────────────────────────────
  const buildPayload = useCallback(() => {
    const payload = { ...form };
    delete payload._descTemplate;  // campo auxiliar de UI, não persiste
    payload.valor = parseFloat(String(form.valor).replace(',', '.')) || 0;
    payload.validade_dias = parseInt(form.validade_dias, 10) || 7;
    return payload;
  }, [form]);

  const refreshPreview = useCallback(async () => {
    if (!form.destinatario_nome || !form.valor) {
      // Sem dados suficientes — não chama backend (evita PDF vazio com erro 422)
      setPreviewUrl(null);
      return;
    }
    setPreviewLoading(true);
    try {
      const blob = await recibosAPI.preview(buildPayload());
      // Limpa URL antiga
      if (lastBlobRef.current) {
        window.URL.revokeObjectURL(lastBlobRef.current);
      }
      const url = window.URL.createObjectURL(blob);
      lastBlobRef.current = url;
      setPreviewUrl(url);
    } catch (e) {
      // silencioso — preview é best-effort
    } finally {
      setPreviewLoading(false);
    }
  }, [form, buildPayload]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(refreshPreview, 600);
    return () => clearTimeout(debounceRef.current);
  }, [form, refreshPreview]);

  // Cleanup ao desmontar
  useEffect(() => () => {
    if (lastBlobRef.current) window.URL.revokeObjectURL(lastBlobRef.current);
  }, []);

  // ── Handlers ───────────────────────────────────────────────────
  const onChange = (field) => (e) => {
    const value = e?.target ? e.target.value : e;
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const validate = () => {
    if (!form.destinatario_nome.trim()) {
      toast({ title: 'Informe o nome do destinatário', variant: 'destructive' });
      return false;
    }
    const v = parseFloat(String(form.valor).replace(',', '.'));
    if (!v || v <= 0) {
      toast({ title: 'Informe um valor válido', variant: 'destructive' });
      return false;
    }
    return true;
  };

  const salvar = async (modo /* 'rascunho' | 'emitido' | 'enviar_whats' */) => {
    if (modo !== 'rascunho' && !validate()) return;
    setSaving(true);
    try {
      const payload = buildPayload();
      payload.status = modo === 'rascunho' ? 'rascunho' : 'emitido';

      let saved;
      if (editing) {
        saved = await recibosAPI.atualizar(id, payload);
      } else {
        saved = await recibosAPI.criar(payload);
      }

      // Faz upload dos anexos que ainda estavam só no navegador
      if (anexosStaged.length && saved?.id) {
        for (const f of anexosStaged) {
          try {
            await recibosAPI.adicionarAnexo(saved.id, f);
          } catch (err) {
            toast({ title: `Falha ao anexar ${f.name}`, variant: 'destructive' });
          }
        }
        setAnexosStaged([]);
      }

      toast({ title: modo === 'rascunho' ? 'Rascunho salvo' : `Recibo ${saved.numero} emitido` });

      if (modo === 'enviar_whats') {
        if (!saved.destinatario_whatsapp) {
          toast({ title: 'Informe o WhatsApp do destinatário antes de enviar', variant: 'destructive' });
          nav(`/dashboard/recibos/${saved.id}`);
          return;
        }
        try {
          await recibosAPI.enviarWhatsApp(saved.id);
          toast({ title: 'Recibo enviado via WhatsApp!' });
        } catch (err) {
          toast({
            title: err.response?.data?.detail || 'Recibo salvo, mas falha ao enviar',
            variant: 'destructive',
          });
        }
      }
      nav('/dashboard/recibos');
    } catch (e) {
      toast({ title: e.response?.data?.detail || 'Erro ao salvar', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const tipoSelecionado = useMemo(
    () => tipos.find(t => t.value === form.tipo) || null,
    [tipos, form.tipo],
  );

  if (loading) {
    return (
      <div className="py-16 flex justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-amber-600" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button
          onClick={() => nav('/dashboard/recibos')}
          className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
        >
          <ArrowLeft className="w-4 h-4" /> Voltar
        </button>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* ── COLUNA 1: FORM ─────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Receipt className="w-5 h-5 text-amber-600" />
            <h2 className="font-display text-2xl font-bold text-gray-900">
              {editing ? `Recibo ${form.numero || ''}` : 'Novo Recibo'}
            </h2>
          </div>

          {/* Emitir como */}
          <Field label="Emitir como *">
            <div className="space-y-2">
              <select
                value={form.emitente_perfil}
                onChange={onChange('emitente_perfil')}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
              >
                <option value="PJ">{form.emitente_perfil === 'PJ' && '🏢 '}PJ — e-CNPJ</option>
                <option value="PF">{form.emitente_perfil === 'PF' && '👤 '}PF — e-CPF</option>
              </select>
              <div className="text-xs text-gray-500 flex items-center gap-1">
                {form.emitente_perfil === 'PJ' ? <Building2 className="w-3 h-3" /> : <UserIcon className="w-3 h-3" />}
                {form.emitente_nome || '(sem nome)'}{form.emitente_documento && ` — ${form.emitente_documento}`}
              </div>
            </div>
          </Field>

          {/* Tipo */}
          <Field label="Tipo *">
            <select
              value={form.tipo}
              onChange={onChange('tipo')}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
            >
              {tipos.length === 0 ? (
                <option value="personalizado">Personalizado</option>
              ) : (
                tipos.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))
              )}
            </select>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Categoria de serviço">
              <select
                value={catSel}
                onChange={onCategoriaChange}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500 bg-white"
              >
                <option value="">— Selecione —</option>
                {categorias.map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Serviço específico">
              <select
                value={servSel}
                onChange={onServicoChange}
                disabled={!catSel}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500 bg-white disabled:bg-gray-50 disabled:text-gray-400"
              >
                <option value="">{catSel ? '— Selecione —' : 'Escolha a categoria'}</option>
                {servicosDe(catSel).map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </Field>
          </div>
          {form.servico && (
            <p className="text-xs text-amber-700 -mt-2">
              Selecionado: <strong>{form.servico}</strong> — a descrição foi preenchida automaticamente (você pode editar).
            </p>
          )}

          {/* Destinatário */}
          <Field label="Destinatário *">
            <Input
              value={form.destinatario_nome}
              onChange={onChange('destinatario_nome')}
              placeholder="Nome completo"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="WhatsApp *">
              <Input
                value={form.destinatario_whatsapp}
                onChange={onChange('destinatario_whatsapp')}
                placeholder="(99) 99999-9999"
              />
            </Field>
            <Field label="CPF/CNPJ (opcional)">
              <Input
                value={form.destinatario_cpf_cnpj}
                onChange={onChange('destinatario_cpf_cnpj')}
                placeholder="000.000.000-00"
              />
            </Field>
          </div>

          <Field label="Email (opcional)">
            <Input
              type="email"
              value={form.destinatario_email}
              onChange={onChange('destinatario_email')}
              placeholder="email@dominio.com"
            />
          </Field>

          <div className="grid grid-cols-3 gap-3">
            <Field label="Valor (R$) *">
              <Input
                type="text"
                inputMode="decimal"
                value={form.valor}
                onChange={onChange('valor')}
                placeholder="0,00"
              />
            </Field>
            <Field label="Forma de pagamento">
              <select
                value={form.forma_pagamento}
                onChange={onChange('forma_pagamento')}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-amber-500"
              >
                {formas.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </Field>
            <Field label="Validade (dias)">
              <Input
                type="number"
                min="1"
                value={form.validade_dias}
                onChange={onChange('validade_dias')}
              />
            </Field>
          </div>

          <Field label="Descrição do serviço/motivo (opcional)">
            <RichTextEditor
              value={paraEditorHtml(form.descricao)}
              onChange={(html) => setForm((f) => ({ ...f, descricao: html }))}
              onBlurHtml={(html) => setForm((f) => ({ ...f, descricao: html }))}
              placeholder="Ex: Mão de obra quinzena 06–20/maio, pagamento PIX"
              minHeight={96}
              showAiButton={false}
            />
            <div className="flex justify-end mt-1">
              <AiButton onClick={handleAiDescricao} loading={aiLoading} />
            </div>
          </Field>

          {form.ptam_link && (
            <Field label="Link do laudo (vinculado ao recibo)">
              <div className="flex gap-2">
                <Input value={form.ptam_link} readOnly className="text-xs" />
                <Button
                  type="button" variant="outline" size="sm"
                  onClick={() => {
                    navigator.clipboard?.writeText(form.ptam_link);
                    toast({ title: 'Link copiado' });
                  }}
                >
                  Copiar
                </Button>
              </div>
              <p className="text-[11px] text-gray-400 mt-1">
                Impresso no PDF e enviado na mensagem do WhatsApp do recibo.
              </p>
            </Field>
          )}

          {/* Anexos */}
          <Field label={`Documentos anexos (até ${ANEXO_MAX} · PDF/JPG/PNG/WebP · 10MB cada)`}>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={onPickAnexos}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={totalAnexos >= ANEXO_MAX}
              className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-amber-300 text-amber-700 text-sm hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Upload className="w-4 h-4" />
              {totalAnexos >= ANEXO_MAX ? 'Limite de anexos atingido' : 'Adicionar anexo'}
            </button>

            {(form.anexos?.length > 0 || anexosStaged.length > 0) && (
              <ul className="mt-2 space-y-1.5">
                {(form.anexos || []).map(a => (
                  <li key={a.id} className="flex items-center gap-2 text-xs bg-gray-50 rounded-lg px-3 py-2">
                    <Paperclip className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                    <span className="flex-1 truncate">{a.name}</span>
                    {a.size_bytes ? <span className="text-gray-400">{fmtTam(a.size_bytes)}</span> : null}
                    <button type="button" onClick={() => removerAnexoSalvo(a.id)} title="Remover">
                      <X className="w-3.5 h-3.5 text-red-500 hover:text-red-700" />
                    </button>
                  </li>
                ))}
                {anexosStaged.map((f, i) => (
                  <li key={`s-${i}`} className="flex items-center gap-2 text-xs bg-amber-50 rounded-lg px-3 py-2">
                    <Paperclip className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    <span className="flex-1 truncate">{f.name}</span>
                    <span className="text-amber-600">{fmtTam(f.size)} · pendente</span>
                    <button type="button" onClick={() => removerStaged(i)} title="Remover">
                      <X className="w-3.5 h-3.5 text-red-500 hover:text-red-700" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Field>

          <p className="text-xs text-gray-500 leading-relaxed pt-2 border-t border-gray-100">
            O recibo recebe número automático no formato <code className="bg-gray-100 px-1 rounded">REC-{tipoSelecionado?.abrev || 'XXX'}-{new Date().getFullYear()}-(seq)</code>.
            Após salvar, você poderá enviar pelo WhatsApp com 1 clique.
          </p>

          {/* Botões finais */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => salvar('rascunho')}
              disabled={saving}
              className="gap-1.5"
            >
              <Save className="w-4 h-4" />
              Salvar rascunho
            </Button>
            <Button
              type="button"
              onClick={() => salvar('emitido')}
              disabled={saving}
              className="bg-emerald-700 hover:bg-emerald-800 text-white gap-1.5"
            >
              <FileText className="w-4 h-4" />
              Salvar sem enviar
            </Button>
            <Button
              type="button"
              onClick={() => salvar('enviar_whats')}
              disabled={saving}
              className="bg-green-600 hover:bg-green-700 text-white gap-1.5"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <MessageCircle className="w-4 h-4" />}
              Salvar e enviar via WhatsApp
            </Button>
          </div>
        </div>

        {/* ── COLUNA 2: PREVIEW LIVE ────────────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
          <div className="px-5 py-3 border-b border-gray-100 bg-gradient-to-r from-amber-50 to-emerald-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-700" />
              <span className="font-semibold text-sm text-gray-900">PREVIEW DO RECIBO</span>
            </div>
            {previewLoading && (
              <span className="text-xs text-amber-700 flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> atualizando...
              </span>
            )}
          </div>
          <p className="px-5 py-2 text-xs text-gray-500 border-b border-gray-100">
            Atualiza automaticamente enquanto você preenche. É exatamente o PDF que será gerado.
          </p>
          <div className="flex-1 min-h-[600px] bg-gray-50 relative">
            {previewUrl ? (
              <iframe
                title="Preview do recibo"
                src={previewUrl}
                className="w-full h-full min-h-[600px] border-0"
              />
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 px-6 text-center">
                <Hourglass className="w-12 h-12 mb-3" />
                <p className="text-sm">Preencha os campos pra ver o preview</p>
                <p className="text-xs mt-1">(Mínimo: nome do destinatário e valor)</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const Field = ({ label, children }) => (
  <div>
    <label className="block text-xs font-semibold text-gray-700 mb-1">{label}</label>
    {children}
  </div>
);

export default ReciboWizard;
