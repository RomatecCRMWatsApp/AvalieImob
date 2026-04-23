// @module ptam/AssinaturaDigital — Modal de assinatura digital com validade juridica via D4Sign
// Lei 14.063/2020 + MP 2.200-2/2001
import React, { useState, useEffect, useRef } from 'react';
import { PenLine, X, Plus, Loader2, RefreshCw, Download, Mail, Trash2 } from 'lucide-react';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { api } from '../../../lib/api';

const TIPO_LABELS = {
  '1': 'Assinar',
  '2': 'Aprovar',
  '4': 'Testemunha',
};

const AssinaturaDigital = ({ tipo = 'ptam', docId, docData, onClose, onUpdate }) => {
  const { toast } = useToast();
  const [status, setStatus] = useState(docData?.d4sign_status || null);
  const [signatarios, setSignatarios] = useState(docData?.d4sign_signatarios || []);
  const [mensagem, setMensagem] = useState(
    `Prezado(a),\n\nSolicito a assinatura digital do laudo ${tipo.toUpperCase()} com validade juridica conforme Lei 14.063/2020.\n\nAtenciosamente.`
  );
  const [novosSigs, setNovosSigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const pollingRef = useRef(null);

  // Auto-polling a cada 30s enquanto aguardando
  useEffect(() => {
    if (status === 'aguardando') {
      pollingRef.current = setInterval(() => {
        handleAtualizarStatus(true);
      }, 30000);
    }
    return () => clearInterval(pollingRef.current);
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const addSignatario = () => {
    if (novosSigs.length >= 4) return; // max 4 extras (1 fixo = avaliador)
    setNovosSigs([...novosSigs, { nome: '', email: '', tipo: '1' }]);
  };

  const removeSignatario = (idx) => {
    setNovosSigs(novosSigs.filter((_, i) => i !== idx));
  };

  const updateSig = (idx, field, value) => {
    setNovosSigs(novosSigs.map((s, i) => i === idx ? { ...s, [field]: value } : s));
  };

  const handleEnviar = async () => {
    // Signatario 1 = avaliador logado (email do docData ou do perfil)
    const emailAvaliador = docData?.solicitante_email || docData?.responsavel?.email || '';
    const nomeAvaliador = docData?.responsavel_nome || docData?.responsavel?.nome || 'Avaliador';
    const sigsPayload = [
      { email: emailAvaliador, nome: nomeAvaliador, tipo: '1' },
      ...novosSigs.filter(s => s.email && s.nome),
    ];
    if (sigsPayload.length === 0 || !sigsPayload[0].email) {
      toast({ title: 'Informe pelo menos o e-mail do avaliador responsavel', variant: 'destructive' });
      return;
    }
    setLoading(true);
    try {
      const res = await api.post(`/assinatura/${tipo}/${docId}/iniciar`, {
        signatarios: sigsPayload,
        mensagem,
      });
      setStatus(res.data.status);
      setSignatarios(res.data.signatarios);
      toast({ title: 'Enviado para assinatura!', description: 'Os signatarios receberao o convite por e-mail.' });
      if (onUpdate) onUpdate({ d4sign_status: res.data.status, d4sign_signatarios: res.data.signatarios });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Erro ao enviar para assinatura';
      toast({ title: detail, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleAtualizarStatus = async (silent = false) => {
    if (!silent) setStatusLoading(true);
    try {
      const res = await api.get(`/assinatura/${tipo}/${docId}/status`);
      setStatus(res.data.status);
      setSignatarios(res.data.signatarios || []);
      if (onUpdate) onUpdate({ d4sign_status: res.data.status, d4sign_signatarios: res.data.signatarios });
      if (!silent) toast({ title: 'Status atualizado' });
      if (res.data.status === 'assinado') clearInterval(pollingRef.current);
    } catch (err) {
      if (!silent) toast({ title: 'Erro ao atualizar status', variant: 'destructive' });
    } finally {
      if (!silent) setStatusLoading(false);
    }
  };

  const handleCancelar = async () => {
    if (!window.confirm('Cancelar o processo de assinatura? Esta acao nao pode ser desfeita.')) return;
    setCancelLoading(true);
    try {
      await api.delete(`/assinatura/${tipo}/${docId}/cancelar`);
      setStatus('cancelado');
      if (onUpdate) onUpdate({ d4sign_status: 'cancelado' });
      toast({ title: 'Processo de assinatura cancelado' });
    } catch (err) {
      toast({ title: 'Erro ao cancelar', variant: 'destructive' });
    } finally {
      setCancelLoading(false);
    }
  };

  const handleDownload = () => {
    const url = `/api/assinatura/${tipo}/${docId}/download`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tipo.toUpperCase()}_ASSINADO.pdf`;
    a.click();
  };

  const handleEmail = async () => {
    const email = window.prompt('E-mail do destinatario:');
    if (!email) return;
    try {
      await api.post(`/${tipo === 'ptam' ? 'ptam' : tipo}/${docId}/email`, {
        destinatario: email,
        mensagem_extra: 'Segue o laudo com assinaturas digitais ICP-Brasil.',
      });
      toast({ title: 'E-mail enviado!' });
    } catch {
      toast({ title: 'Erro ao enviar e-mail', variant: 'destructive' });
    }
  };

  const formatDate = (dt) => {
    if (!dt) return null;
    try { return new Date(dt).toLocaleString('pt-BR'); } catch { return dt; }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <PenLine className="w-5 h-5 text-emerald-700" />
            <h2 className="font-bold text-gray-900 text-lg">
              {status === 'assinado'
                ? 'Laudo Assinado Digitalmente'
                : status === 'aguardando'
                ? 'Aguardando Assinaturas'
                : 'Solicitar Assinatura Digital'}
            </h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* ── Estado 1: Configurar ───────────────────────────────── */}
          {!status && (
            <>
              {/* Aviso legal */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm text-blue-800 leading-relaxed">
                  <strong>Validade juridica garantida.</strong> A assinatura digital e equivalente
                  a firma reconhecida em cartorio, conforme{' '}
                  <strong>Lei 14.063/2020</strong> e{' '}
                  <strong>MP 2.200-2/2001</strong>.
                </p>
              </div>

              {/* Mensagem */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Mensagem para os signatarios
                </label>
                <textarea
                  rows={4}
                  value={mensagem}
                  onChange={(e) => setMensagem(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm resize-none focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200"
                />
              </div>

              {/* Signatario 1 fixo */}
              <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
                <div className="font-medium text-gray-800 mb-0.5">Signatario 1 (Avaliador — fixo)</div>
                <div>{docData?.responsavel_nome || 'Nome do avaliador'}</div>
                <div className="text-xs text-gray-500">{docData?.responsavel?.email || docData?.solicitante_email || 'e-mail do perfil'} — Assinar</div>
              </div>

              {/* Signatarios extras */}
              {novosSigs.map((sig, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-700">Signatario {idx + 2}</span>
                    <button onClick={() => removeSignatario(idx)} className="text-red-400 hover:text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      placeholder="Nome completo"
                      value={sig.nome}
                      onChange={(e) => updateSig(idx, 'nome', e.target.value)}
                      className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500"
                    />
                    <select
                      value={sig.tipo}
                      onChange={(e) => updateSig(idx, 'tipo', e.target.value)}
                      className="px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500"
                    >
                      <option value="1">Assinar</option>
                      <option value="2">Aprovar</option>
                      <option value="4">Testemunha</option>
                    </select>
                    <input
                      placeholder="E-mail"
                      type="email"
                      value={sig.email}
                      onChange={(e) => updateSig(idx, 'email', e.target.value)}
                      className="col-span-2 px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
              ))}

              {novosSigs.length < 4 && (
                <Button variant="outline" size="sm" onClick={addSignatario} className="w-full gap-1.5">
                  <Plus className="w-4 h-4" />
                  Adicionar signatario
                </Button>
              )}

              {/* Custo estimado */}
              <p className="text-xs text-gray-500 text-center">
                Custo estimado: <strong>R$ 1,50 por documento assinado</strong> (cobrado via D4Sign)
              </p>

              <Button
                onClick={handleEnviar}
                disabled={loading}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-2"
              >
                {loading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />Enviando para D4Sign...</>
                ) : (
                  <><PenLine className="w-4 h-4" />Enviar para assinatura</>
                )}
              </Button>
            </>
          )}

          {/* ── Estado 2: Aguardando ───────────────────────────────── */}
          {status === 'aguardando' && (
            <>
              <div className="space-y-2">
                {signatarios.map((s, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="text-sm font-medium text-gray-800">{s.nome || s.email}</div>
                      <div className="text-xs text-gray-500">{s.email} — {TIPO_LABELS[s.tipo] || 'Assinar'}</div>
                    </div>
                    {s.assinado ? (
                      <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-1 rounded-full">
                        Assinado em {formatDate(s.assinado_em)}
                      </span>
                    ) : (
                      <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-1 rounded-full">
                        Aguardando — convite enviado
                      </span>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => handleAtualizarStatus(false)}
                  disabled={statusLoading}
                  className="flex-1 gap-1.5"
                >
                  {statusLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  Atualizar status
                </Button>
                <Button
                  variant="outline"
                  onClick={handleCancelar}
                  disabled={cancelLoading}
                  className="flex-1 gap-1.5 border-red-200 text-red-600 hover:bg-red-50"
                >
                  {cancelLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                  Cancelar processo
                </Button>
              </div>
              <p className="text-xs text-center text-gray-400">
                Atualizacao automatica a cada 30 segundos
              </p>
            </>
          )}

          {/* ── Estado 3: Assinado ────────────────────────────────── */}
          {status === 'assinado' && (
            <>
              <div className="text-center py-2">
                <div className="inline-flex items-center gap-2 bg-emerald-600 text-white font-bold px-5 py-2.5 rounded-full text-sm shadow">
                  ASSINADO COM VALIDADE JURIDICA
                </div>
              </div>

              <div className="space-y-2">
                {signatarios.map((s, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg">
                    <div>
                      <div className="text-sm font-medium text-gray-800">{s.nome || s.email}</div>
                      <div className="text-xs text-gray-500">{s.email}</div>
                    </div>
                    <span className="text-xs font-medium text-emerald-700">
                      Assinado {formatDate(s.assinado_em) ? `em ${formatDate(s.assinado_em)}` : ''}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleDownload}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
                >
                  <Download className="w-4 h-4" />
                  Baixar PDF Assinado
                </Button>
                <Button
                  variant="outline"
                  onClick={handleEmail}
                  className="flex-1 gap-2"
                >
                  <Mail className="w-4 h-4" />
                  Enviar por e-mail
                </Button>
              </div>

              <p className="text-xs text-center text-gray-500">
                Este PDF contem assinaturas digitais ICP-Brasil verificaveis em qualquer leitor PDF.
              </p>
            </>
          )}

          {/* Estado cancelado */}
          {status === 'cancelado' && (
            <div className="text-center py-4">
              <p className="text-gray-600 mb-4">Processo de assinatura cancelado.</p>
              <Button
                variant="outline"
                onClick={() => setStatus(null)}
                className="gap-2"
              >
                <PenLine className="w-4 h-4" />
                Iniciar nova assinatura
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssinaturaDigital;
