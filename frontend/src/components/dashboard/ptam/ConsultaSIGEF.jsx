// @module ptam/ConsultaSIGEF — Consulta automatica SIGEF/INCRA para laudos rurais
import React, { useState } from 'react';
import { Search, CheckCircle, AlertCircle, Loader2, ExternalLink, RefreshCw } from 'lucide-react';
import { sigefAPI } from '../../../../lib/api';

const ESTADOS_BR = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
  'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO',
];

const RURAL_TYPES = new Set(['rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural']);

function maskCCIR(v) {
  const d = v.replace(/\D/g, '').slice(0, 15);
  // Formata primeiros 10 como XXX.XXX.XXX-X, restante aparece junto
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0,3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`;
  if (d.length <= 10) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`;
  return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9,10)}${d.slice(10)}`;
}

function SituacaoBadge({ situacao }) {
  const cfg = {
    certificado: { cls: 'bg-emerald-100 border-emerald-300 text-emerald-800', label: 'SIGEF Certificado' },
    em_certificacao: { cls: 'bg-yellow-100 border-yellow-300 text-yellow-800', label: 'Em Certificação' },
    nao_certificado: { cls: 'bg-gray-100 border-gray-300 text-gray-600', label: 'Não Certificado' },
  };
  const c = cfg[situacao] || cfg.nao_certificado;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${c.cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {c.label}
    </span>
  );
}

export function ConsultaSIGEF({ form, setForm }) {
  const [ccir, setCcir] = useState('');
  const [sigefCodigo, setSigefCodigo] = useState('');
  const [estado, setEstado] = useState(form.property_state || 'MA');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [resultado, setResultado] = useState(null);  // null | { encontrado, ...dados }
  const [erro, setErro] = useState('');

  // Só renderiza para imóveis rurais
  if (!RURAL_TYPES.has((form.property_type || '').toLowerCase())) return null;

  const handleBuscar = async () => {
    const ccirDigits = ccir.replace(/\D/g, '');
    if (!ccirDigits && !sigefCodigo.trim()) {
      setErro('Informe o CCIR (15 dígitos) ou o código UUID SIGEF.');
      return;
    }
    if (ccirDigits && ccirDigits.length !== 15) {
      setErro(`CCIR inválido: ${ccirDigits.length} dígitos encontrados, esperado 15.`);
      return;
    }
    setErro('');
    setResultado(null);
    setLoading(true);
    setProgress(0);

    // Barra de progresso simulada (20s max)
    const interval = setInterval(() => {
      setProgress(p => Math.min(p + 5, 90));
    }, 1000);

    try {
      const data = await sigefAPI.consultar({
        ccir: ccirDigits || undefined,
        sigef_codigo: sigefCodigo.trim() || undefined,
        estado,
      });
      clearInterval(interval);
      setProgress(100);
      setResultado(data);
    } catch (ex) {
      clearInterval(interval);
      const msg = ex?.response?.data?.detail || 'Erro ao consultar SIGEF/INCRA. Tente novamente ou preencha manualmente.';
      setErro(msg);
    } finally {
      setLoading(false);
    }
  };

  const handlePreencher = () => {
    if (!resultado || !resultado.encontrado) return;
    const now = new Date().toLocaleDateString('pt-BR');
    setForm(prev => ({
      ...prev,
      // Área e localização
      property_area_ha: resultado.sigef_area_ha ?? prev.property_area_ha,
      property_city: resultado.municipio || prev.property_city,
      property_state: resultado.uf || prev.property_state,
      // Identificação rural
      denominacao: resultado.denominacao || prev.denominacao,
      sigef_codigo: resultado.sigef_codigo || prev.sigef_codigo,
      certificacao_sigef: resultado.sigef_codigo || prev.certificacao_sigef,
      ccir_numero: resultado.ccir_numero || prev.ccir_numero,
      ccir: resultado.ccir_numero || prev.ccir,
      // SIGEF
      sigef_situacao: resultado.sigef_situacao || prev.sigef_situacao,
      sigef_data_certificacao: resultado.sigef_data_certificacao || prev.sigef_data_certificacao,
      sigef_area_ha: resultado.sigef_area_ha ?? prev.sigef_area_ha,
      sigef_perimetro_m: resultado.sigef_perimetro_m ?? prev.sigef_perimetro_m,
      sigef_vertices: resultado.sigef_vertices ?? prev.sigef_vertices,
      sigef_datum: resultado.sigef_datum || 'SIRGAS 2000',
      // Módulo fiscal
      modulo_fiscal_ha: resultado.modulo_fiscal_ha ?? prev.modulo_fiscal_ha,
      numero_modulos_fiscais: resultado.numero_modulos_fiscais ?? prev.numero_modulos_fiscais,
      municipio_incra: resultado.municipio || prev.municipio_incra,
      uf_incra: resultado.uf || prev.uf_incra,
      // Metadados
      dados_incra_automaticos: true,
      dados_incra_data_consulta: now,
    }));

    // Toast nativo via dispatchEvent (compatível com o sistema existente)
    window.dispatchEvent(new CustomEvent('avalieimob:toast', {
      detail: {
        message: '12 campos preenchidos automaticamente via SIGEF/INCRA',
        type: 'success',
      },
    }));
  };

  const handleNovaConsulta = () => {
    setResultado(null);
    setErro('');
    setProgress(0);
  };

  return (
    <div className="col-span-2 mb-2">
      <div className="rounded-xl border-2 border-emerald-300 bg-emerald-50 p-5">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <div className="w-9 h-9 rounded-lg bg-emerald-700 flex items-center justify-center flex-shrink-0">
            <Search className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-bold text-emerald-900 text-sm">Consulta Automática SIGEF/INCRA</div>
            <div className="text-xs text-emerald-700">Busca dados oficiais do imóvel rural pelo CCIR ou código SIGEF</div>
          </div>
        </div>

        {/* Estado: Busca */}
        {!loading && !resultado && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-emerald-800 mb-1">
                  CCIR <span className="text-emerald-600 font-normal">(15 dígitos)</span>
                </label>
                <input
                  value={ccir}
                  onChange={e => setCcir(maskCCIR(e.target.value))}
                  placeholder="XXX.XXX.XXX-XXXXXX"
                  className="w-full px-3 py-2 rounded-lg border border-emerald-200 bg-white text-sm focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-emerald-800 mb-1">
                  Código SIGEF <span className="text-emerald-600 font-normal">(UUID)</span>
                </label>
                <input
                  value={sigefCodigo}
                  onChange={e => setSigefCodigo(e.target.value)}
                  placeholder="b533967e-f6b0-4b19-..."
                  className="w-full px-3 py-2 rounded-lg border border-emerald-200 bg-white text-sm focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-emerald-800 mb-1">Estado (UF)</label>
                <select
                  value={estado}
                  onChange={e => setEstado(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-emerald-200 bg-white text-sm focus:outline-none focus:border-emerald-500"
                >
                  {ESTADOS_BR.map(uf => <option key={uf}>{uf}</option>)}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleBuscar}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-emerald-700 text-white font-semibold text-sm hover:bg-emerald-800 transition-colors"
                >
                  <Search className="w-4 h-4" />
                  Buscar
                </button>
              </div>
            </div>
            {erro && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 text-sm text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  {erro}
                  <a href="https://sigef.incra.gov.br" target="_blank" rel="noopener noreferrer"
                    className="block mt-1 text-xs text-red-500 hover:underline flex items-center gap-1">
                    Consultar manualmente em sigef.incra.gov.br <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Estado: Loading */}
        {loading && (
          <div className="py-4 space-y-3">
            <div className="flex items-center gap-2 text-emerald-800 font-medium text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Consultando SIGEF/INCRA...
            </div>
            <div className="w-full bg-emerald-100 rounded-full h-2">
              <div
                className="bg-emerald-600 h-2 rounded-full transition-all duration-1000"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-emerald-600">Aguarde até 20 segundos. A API SIGEF pode apresentar instabilidade.</p>
          </div>
        )}

        {/* Estado: Sucesso */}
        {!loading && resultado?.encontrado && (
          <div className="space-y-4">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="font-bold text-emerald-900 text-sm">Imóvel localizado no SIGEF</div>
                {resultado.denominacao && (
                  <div className="text-base font-semibold text-gray-800 mt-0.5">{resultado.denominacao}</div>
                )}
                {(resultado.municipio || resultado.uf) && (
                  <div className="text-sm text-gray-600">{resultado.municipio}{resultado.uf ? ` / ${resultado.uf}` : ''}</div>
                )}
              </div>
              <SituacaoBadge situacao={resultado.sigef_situacao} />
            </div>

            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm bg-white rounded-lg border border-emerald-200 px-4 py-3">
              {resultado.sigef_area_ha && (
                <div>
                  <span className="text-gray-500 text-xs">Área certificada</span>
                  <div className="font-semibold text-gray-800">{Number(resultado.sigef_area_ha).toFixed(4)} ha</div>
                </div>
              )}
              {resultado.sigef_data_certificacao && (
                <div>
                  <span className="text-gray-500 text-xs">Data certificação</span>
                  <div className="font-semibold text-gray-800">{resultado.sigef_data_certificacao}</div>
                </div>
              )}
              {resultado.modulo_fiscal_ha && (
                <div>
                  <span className="text-gray-500 text-xs">Módulo fiscal</span>
                  <div className="font-semibold text-gray-800">{resultado.modulo_fiscal_ha} ha</div>
                </div>
              )}
              {resultado.numero_modulos_fiscais && (
                <div>
                  <span className="text-gray-500 text-xs">Nº módulos fiscais</span>
                  <div className="font-semibold text-gray-800">{resultado.numero_modulos_fiscais}</div>
                </div>
              )}
              {resultado.sigef_vertices && (
                <div>
                  <span className="text-gray-500 text-xs">Vértices</span>
                  <div className="font-semibold text-gray-800">{resultado.sigef_vertices}</div>
                </div>
              )}
              {resultado.sigef_datum && (
                <div>
                  <span className="text-gray-500 text-xs">Datum</span>
                  <div className="font-semibold text-gray-800">{resultado.sigef_datum}</div>
                </div>
              )}
              {resultado.sigef_codigo && (
                <div className="col-span-2">
                  <span className="text-gray-500 text-xs">Código SIGEF</span>
                  <div className="font-mono text-xs text-gray-700 truncate">{resultado.sigef_codigo}</div>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button
                onClick={handlePreencher}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-700 text-white font-semibold text-sm hover:bg-emerald-800 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                Preencher campos do laudo
              </button>
              <button
                onClick={handleNovaConsulta}
                className="px-3 py-2.5 rounded-lg border border-emerald-300 text-emerald-700 text-sm hover:bg-emerald-100 transition-colors"
                title="Nova consulta"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Estado: Não encontrado */}
        {!loading && resultado && !resultado.encontrado && (
          <div className="space-y-3">
            <div className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2.5 text-sm text-yellow-800">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                {resultado.erros?.[0] || 'Imóvel não localizado no SIGEF com os dados fornecidos.'}
                <a href="https://sigef.incra.gov.br" target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 mt-1 text-xs text-yellow-600 hover:underline">
                  Consultar em sigef.incra.gov.br <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
            <button
              onClick={handleNovaConsulta}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 text-gray-600 text-sm hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Nova consulta
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConsultaSIGEF;
