// @page VerificarLaudo — Página pública de verificação de autenticidade ICP-Brasil
// Rota: /v/laudo/v/:hash — destino do QR Code do bloco visual de assinatura.
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, FileCheck2, Loader2, ExternalLink, Calendar, User as UserIcon, Hash } from 'lucide-react';
import { api } from '../lib/api';

const VerificarLaudo = () => {
  const { hash } = useParams();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const verificar = async () => {
      try {
        const res = await api.get(`/assinatura/v/laudo/v/${hash}`);
        if (!cancelled) setData(res.data);
      } catch (err) {
        if (!cancelled) {
          if (err?.response?.status === 404) {
            setError('Hash não encontrado. Este documento pode ter sido modificado, removido, ou o hash informado está incorreto.');
          } else {
            setError(err?.response?.data?.detail || 'Erro ao verificar autenticidade.');
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    verificar();
    return () => { cancelled = true; };
  }, [hash]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-amber-50 flex items-start justify-center p-4 pt-12">
      <div className="w-full max-w-2xl">
        {/* Logo header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-block">
            <h1 className="font-display text-2xl font-bold text-emerald-900">Romatec AvalieImob</h1>
            <p className="text-xs text-gray-500 tracking-wider">VERIFICAÇÃO DE AUTENTICIDADE — ICP-BRASIL</p>
          </Link>
        </div>

        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
          {loading ? (
            <div className="p-12 flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-700" />
              <p className="text-gray-600 text-sm">Verificando assinatura digital...</p>
            </div>
          ) : error ? (
            <>
              <div className="bg-red-500 px-6 py-5 flex items-center gap-3">
                <ShieldAlert className="w-7 h-7 text-white" />
                <div>
                  <h2 className="text-white font-bold text-lg">Não autenticado</h2>
                  <p className="text-red-100 text-sm">Documento não pôde ser verificado</p>
                </div>
              </div>
              <div className="p-6">
                <p className="text-gray-700 text-sm leading-relaxed">{error}</p>
                <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Hash consultado</div>
                  <code className="text-xs text-gray-700 break-all font-mono">{hash}</code>
                </div>
              </div>
            </>
          ) : data?.autentico ? (
            <>
              <div className="bg-gradient-to-r from-emerald-600 to-emerald-700 px-6 py-5 flex items-center gap-3">
                <ShieldCheck className="w-9 h-9 text-white" />
                <div>
                  <h2 className="text-white font-bold text-xl">Documento autêntico</h2>
                  <p className="text-emerald-100 text-sm">Assinatura digital ICP-Brasil válida</p>
                </div>
              </div>

              <div className="p-6 space-y-4">
                <Field label="Tipo" icon={<FileCheck2 className="w-4 h-4" />}>
                  {(data.tipo || '').toUpperCase()} {data.numero && <strong>{data.numero}</strong>}
                </Field>
                {data.imovel && (
                  <Field label="Imóvel">{data.imovel}</Field>
                )}
                <Field label="Titular da assinatura" icon={<UserIcon className="w-4 h-4" />}>
                  <strong>{data.titular || '—'}</strong>
                  {data.documento && <div className="text-xs text-gray-500 mt-0.5">{data.documento}</div>}
                </Field>
                {data.emissor && (
                  <Field label="Emissor do certificado">{data.emissor}</Field>
                )}
                {data.assinado_em && (
                  <Field label="Assinado em" icon={<Calendar className="w-4 h-4" />}>
                    {new Date(data.assinado_em).toLocaleString('pt-BR')}
                  </Field>
                )}
                <Field label="Hash de autenticidade" icon={<Hash className="w-4 h-4" />}>
                  <code className="text-xs break-all font-mono text-emerald-900">{data.hash}</code>
                </Field>
              </div>

              <div className="px-6 pb-6 flex flex-col gap-2">
                <a
                  href="https://validar.iti.gov.br"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-2 text-sm text-emerald-700 hover:text-emerald-900 font-medium border border-emerald-200 rounded-lg py-2.5 hover:bg-emerald-50 transition"
                >
                  <ExternalLink className="w-4 h-4" />
                  Validar também em validar.iti.gov.br
                </a>
                <p className="text-[11px] text-center text-gray-500 leading-relaxed pt-2">
                  Esta verificação confirma que o PDF foi assinado com certificado
                  ICP-Brasil A1/A3 do titular e não foi alterado desde a assinatura.
                  Validade jurídica equivalente a firma reconhecida em cartório
                  (Lei 14.063/2020 + MP 2.200-2/2001).
                </p>
              </div>
            </>
          ) : null}
        </div>

        <div className="text-center mt-6 text-xs text-gray-500">
          <Link to="/" className="hover:text-emerald-700">← Voltar para Romatec AvalieImob</Link>
        </div>
      </div>
    </div>
  );
};

const Field = ({ label, children, icon }) => (
  <div>
    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-0.5 flex items-center gap-1.5">
      {icon}
      {label}
    </div>
    <div className="text-sm text-gray-800">{children}</div>
  </div>
);

export default VerificarLaudo;
