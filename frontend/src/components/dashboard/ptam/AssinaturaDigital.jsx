// @module ptam/AssinaturaDigital — Modal de assinatura digital com 2 modalidades
//
//   1. ICP-Brasil A1 (PAdES, certificado .pfx local) — assina na hora,
//      validade jurídica equivalente ao Adobe Reader e gov.br/validar.
//      Lei 14.063/2020 + MP 2.200-2/2001.
//
//   2. D4Sign (assinatura eletrônica via e-mail) — fluxo legado,
//      válido para múltiplos signatários remotos.
//
// O usuário escolhe o método pelas tabs no topo do modal.
import React, { useState, useEffect, useRef } from 'react';
import {
  PenLine, X, Plus, Loader2, RefreshCw, Download, Mail, Trash2,
  Lock, ShieldCheck, ExternalLink, Settings as SettingsIcon,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../ui/button';
import { useToast } from '../../../hooks/use-toast';
import { api, certificadosAPI, assinaturaAPI } from '../../../lib/api';

const TIPO_LABELS = {
  '1': 'Assinar',
  '2': 'Aprovar',
  '4': 'Testemunha',
};

const AssinaturaDigital = ({ tipo = 'ptam', docId, docData, onClose, onUpdate }) => {
  const { toast } = useToast();
  const nav = useNavigate();

  // Aba ativa: 'icp' (default — recomendado) ou 'd4sign'
  const [aba, setAba] = useState(docData?.d4sign_status ? 'd4sign' : 'icp');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <PenLine className="w-5 h-5 text-emerald-700" />
            <h2 className="font-bold text-gray-900 text-lg">Assinatura Digital</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100 bg-gray-50">
          <button
            onClick={() => setAba('icp')}
            className={`flex-1 px-4 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition ${
              aba === 'icp'
                ? 'text-emerald-700 border-b-2 border-emerald-600 bg-white'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Lock className="w-4 h-4" />
            ICP-Brasil (A1)
          </button>
          <button
            onClick={() => setAba('d4sign')}
            className={`flex-1 px-4 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition ${
              aba === 'd4sign'
                ? 'text-emerald-700 border-b-2 border-emerald-600 bg-white'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Mail className="w-4 h-4" />
            D4Sign (e-mail)
          </button>
        </div>

        <div className="p-6">
          {aba === 'icp' ? (
            <AssinaturaICP
              tipo={tipo}
              docId={docId}
              docData={docData}
              onUpdate={onUpdate}
              onClose={onClose}
              toast={toast}
              nav={nav}
            />
          ) : (
            <AssinaturaD4Sign
              tipo={tipo}
              docId={docId}
              docData={docData}
              onUpdate={onUpdate}
              toast={toast}
            />
          )}
        </div>
      </div>
    </div>
  );
};


// ════════════════════════════════════════════════════════════════════════════
// ABA 1: ICP-Brasil A1 (PAdES) — assinatura local com certificado .pfx
// ════════════════════════════════════════════════════════════════════════════
const AssinaturaICP = ({ tipo, docId, docData, onUpdate, onClose, toast, nav }) => {
  const [certs, setCerts] = useState([]);
  const [loadingCerts, setLoadingCerts] = useState(true);
  const [selectedCert, setSelectedCert] = useState('');
  const [signing, setSigning] = useState(false);
  const [icpStatus, setIcpStatus] = useState(docData?.icp_status || null);
  const [icpHash, setIcpHash] = useState(docData?.icp_hash || null);
  const [verificacaoUrl, setVerificacaoUrl] = useState(docData?.icp_verificacao_url || null);

  useEffect(() => {
    const load = async () => {
      setLoadingCerts(true);
      try {
        const data = await certificadosAPI.list();
        const ativos = (data || []).filter(c => c.ativo);
        setCerts(ativos);
        if (ativos.length === 1) setSelectedCert(ativos[0].id);
      } catch (e) {
        console.warn(e);
      } finally {
        setLoadingCerts(false);
      }
    };
    load();
  }, []);

  const handleAssinar = async () => {
    if (!selectedCert) {
      toast({ title: 'Selecione um certificado', variant: 'destructive' });
      return;
    }
    setSigning(true);
    try {
      const res = await assinaturaAPI.assinarIcp(tipo, docId, selectedCert);
      setIcpStatus('assinado');
      setIcpHash(res.hash);
      setVerificacaoUrl(res.verificacao_url);
      toast({ title: 'Documento assinado com sucesso!', description: 'Validade jurídica ICP-Brasil garantida.' });
      if (onUpdate) onUpdate({
        icp_status: 'assinado',
        icp_hash: res.hash,
        icp_pdf_url: res.download_url,
        icp_verificacao_url: res.verificacao_url,
      });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Falha ao assinar com ICP-Brasil';
      toast({ title: detail, variant: 'destructive' });
    } finally {
      setSigning(false);
    }
  };

  const handleDownload = async () => {
    try {
      const blob = await assinaturaAPI.downloadIcp(tipo, docId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const numero = docData?.numero_ptam || docData?.number || docId;
      a.download = `${tipo.toUpperCase()}_${String(numero).replace(/\//g, '-')}_ASSINADO_ICP.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: 'Erro ao baixar PDF assinado', variant: 'destructive' });
    }
  };

  // Estado: já assinado
  if (icpStatus === 'assinado') {
    return (
      <div className="space-y-4">
        <div className="text-center py-2">
          <div className="inline-flex items-center gap-2 bg-emerald-600 text-white font-bold px-5 py-2.5 rounded-full text-sm shadow">
            <ShieldCheck className="w-4 h-4" />
            ASSINADO COM ICP-BRASIL
          </div>
        </div>

        <div className="bg-emerald-50 rounded-lg p-4 space-y-2 text-sm">
          {docData?.icp_titular && (
            <div><span className="font-semibold">Titular:</span> {docData.icp_titular}</div>
          )}
          {docData?.icp_documento && (
            <div><span className="font-semibold">Documento:</span> {docData.icp_documento}</div>
          )}
          {docData?.icp_emissor && (
            <div><span className="font-semibold">Emissor:</span> {docData.icp_emissor}</div>
          )}
          {docData?.icp_signed_at && (
            <div><span className="font-semibold">Assinado em:</span> {new Date(docData.icp_signed_at).toLocaleString('pt-BR')}</div>
          )}
          {icpHash && (
            <div className="pt-1 border-t border-emerald-200">
              <span className="font-semibold">Hash:</span>
              <code className="text-xs block mt-0.5 break-all text-emerald-900">{icpHash}</code>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            onClick={handleDownload}
            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
          >
            <Download className="w-4 h-4" />
            Baixar PDF Assinado
          </Button>
          {verificacaoUrl && (
            <Button
              variant="outline"
              onClick={() => window.open(verificacaoUrl, '_blank')}
              className="flex-1 gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Verificar
            </Button>
          )}
        </div>

        <p className="text-xs text-center text-gray-500">
          Validade jurídica equivalente a firma reconhecida em cartório.
          Verificável em qualquer PDF reader e em <strong>validar.iti.gov.br</strong>.
        </p>
      </div>
    );
  }

  // Estado: configurar
  return (
    <div className="space-y-4">
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
        <p className="text-sm text-emerald-900 leading-relaxed">
          <strong>ICP-Brasil A1 (PAdES).</strong> Assina o PDF localmente com seu certificado
          digital. Validade jurídica equivalente a firma reconhecida em cartório
          (Lei 14.063/2020 + MP 2.200-2/2001). Reconhecido por Adobe Reader e
          <strong> validar.iti.gov.br</strong>.
        </p>
      </div>

      {loadingCerts ? (
        <div className="py-6 flex justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-emerald-700" />
        </div>
      ) : certs.length === 0 ? (
        <div className="text-center py-6 bg-amber-50 border border-amber-200 rounded-lg">
          <Lock className="w-8 h-8 text-amber-600 mx-auto mb-2" />
          <p className="text-sm font-semibold text-gray-900 mb-1">Nenhum certificado ativo</p>
          <p className="text-xs text-gray-600 mb-3">
            Cadastre seu e-CPF ou e-CNPJ A1 (.pfx) em Configurações.
          </p>
          <Button
            size="sm"
            variant="outline"
            onClick={() => { onClose(); nav('/dashboard/configuracoes'); }}
            className="gap-2"
          >
            <SettingsIcon className="w-4 h-4" />
            Ir para Configurações
          </Button>
        </div>
      ) : (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Selecione o certificado
            </label>
            <div className="space-y-2">
              {certs.map(cert => (
                <label
                  key={cert.id}
                  className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition ${
                    selectedCert === cert.id
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="cert"
                    value={cert.id}
                    checked={selectedCert === cert.id}
                    onChange={() => setSelectedCert(cert.id)}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm text-gray-900">
                        {cert.perfil === 'PJ' ? 'e-CNPJ' : 'e-CPF'} — {cert.label}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                        cert.perfil === 'PJ' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                      }`}>{cert.perfil}</span>
                    </div>
                    {cert.titular && (
                      <div className="text-xs text-gray-600 mt-0.5">{cert.titular}</div>
                    )}
                    {cert.documento && (
                      <div className="text-xs text-gray-500">{cert.documento}</div>
                    )}
                    <div className="text-xs text-gray-500 mt-0.5">
                      Válido até {cert.valido_ate ? new Date(cert.valido_ate).toLocaleDateString('pt-BR') : '—'}
                      {cert.emissor && <> · {cert.emissor}</>}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <Button
            onClick={handleAssinar}
            disabled={signing || !selectedCert}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-2"
          >
            {signing ? (
              <><Loader2 className="w-4 h-4 animate-spin" />Assinando com ICP-Brasil...</>
            ) : (
              <><Lock className="w-4 h-4" />Assinar com ICP-Brasil agora</>
            )}
          </Button>
        </>
      )}
    </div>
  );
};


// ════════════════════════════════════════════════════════════════════════════
// ABA 2: D4Sign (assinatura eletrônica via e-mail) — fluxo legado
// ════════════════════════════════════════════════════════════════════════════
const AssinaturaD4Sign = ({ tipo, docId, docData, onUpdate, toast }) => {
  const [status, setStatus] = useState(docData?.d4sign_status || null);
  const [signatarios, setSignatarios] = useState(docData?.d4sign_signatarios || []);
  const [mensagem, setMensagem] = useState(
    `Prezado(a),\n\nSolicito a assinatura digital do laudo ${tipo.toUpperCase()} com validade jurídica conforme Lei 14.063/2020.\n\nAtenciosamente.`
  );
  const [novosSigs, setNovosSigs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const pollingRef = useRef(null);

  useEffect(() => {
    if (status === 'aguardando') {
      pollingRef.current = setInterval(() => {
        handleAtualizarStatus(true);
      }, 30000);
    }
    return () => clearInterval(pollingRef.current);
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const addSignatario = () => {
    if (novosSigs.length >= 4) return;
    setNovosSigs([...novosSigs, { nome: '', email: '', tipo: '1' }]);
  };

  const removeSignatario = (idx) => setNovosSigs(novosSigs.filter((_, i) => i !== idx));
  const updateSig = (idx, field, value) =>
    setNovosSigs(novosSigs.map((s, i) => i === idx ? { ...s, [field]: value } : s));

  const handleEnviar = async () => {
    const emailAvaliador = docData?.solicitante_email || docData?.responsavel?.email || '';
    const nomeAvaliador = docData?.responsavel_nome || docData?.responsavel?.nome || 'Avaliador';
    const sigsPayload = [
      { email: emailAvaliador, nome: nomeAvaliador, tipo: '1' },
      ...novosSigs.filter(s => s.email && s.nome),
    ];
    if (sigsPayload.length === 0 || !sigsPayload[0].email) {
      toast({ title: 'Informe pelo menos o e-mail do avaliador responsável', variant: 'destructive' });
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
      toast({ title: 'Enviado para assinatura!', description: 'Os signatários receberão o convite por e-mail.' });
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
    if (!window.confirm('Cancelar o processo de assinatura? Esta ação não pode ser desfeita.')) return;
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

  const formatDate = (dt) => {
    if (!dt) return null;
    try { return new Date(dt).toLocaleString('pt-BR'); } catch { return dt; }
  };

  // ── Estado 1: Configurar ──
  if (!status) {
    return (
      <div className="space-y-5">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800 leading-relaxed">
            <strong>Assinatura eletrônica via e-mail.</strong> Os signatários recebem
            convite e assinam pelo navegador. Validade jurídica conforme Lei 14.063/2020.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Mensagem para os signatários
          </label>
          <textarea
            rows={4}
            value={mensagem}
            onChange={(e) => setMensagem(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm resize-none focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-200"
          />
        </div>

        <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
          <div className="font-medium text-gray-800 mb-0.5">Signatário 1 (Avaliador — fixo)</div>
          <div>{docData?.responsavel_nome || 'Nome do avaliador'}</div>
          <div className="text-xs text-gray-500">{docData?.responsavel?.email || docData?.solicitante_email || 'e-mail do perfil'} — Assinar</div>
        </div>

        {novosSigs.map((sig, idx) => (
          <div key={idx} className="border border-gray-200 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-700">Signatário {idx + 2}</span>
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
            Adicionar signatário
          </Button>
        )}

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
      </div>
    );
  }

  // ── Estado 2: Aguardando ──
  if (status === 'aguardando') {
    return (
      <div className="space-y-5">
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
            {statusLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
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
          Atualização automática a cada 30 segundos
        </p>
      </div>
    );
  }

  // ── Estado 3: Assinado ──
  if (status === 'assinado') {
    return (
      <div className="space-y-5">
        <div className="text-center py-2">
          <div className="inline-flex items-center gap-2 bg-emerald-600 text-white font-bold px-5 py-2.5 rounded-full text-sm shadow">
            ASSINADO COM VALIDADE JURÍDICA
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
        <Button
          onClick={handleDownload}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
        >
          <Download className="w-4 h-4" />
          Baixar PDF Assinado
        </Button>
      </div>
    );
  }

  // ── Estado: Cancelado ──
  return (
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
  );
};

export default AssinaturaDigital;
