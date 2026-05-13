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
  FileText, MessageCircle, Hourglass,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Textarea } from '../../ui/textarea';
import { useToast } from '../../../hooks/use-toast';
import { useAuth } from '../../../contexts/AuthContext';
import { recibosAPI, perfilAPI } from '../../../lib/api';

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

  // ── Preview live (debounced) ───────────────────────────────────
  const buildPayload = useCallback(() => {
    const payload = { ...form };
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
              <Input value={form.categoria} onChange={onChange('categoria')} placeholder="ex: Avaliação Imobiliária" />
            </Field>
            <Field label="Serviço específico">
              <Input value={form.servico} onChange={onChange('servico')} placeholder="ex: PTAM rural" />
            </Field>
          </div>

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
            <Textarea
              rows={3}
              value={form.descricao}
              onChange={onChange('descricao')}
              placeholder="Ex: Mão de obra quinzena 06–20/maio, pagamento PIX"
            />
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
