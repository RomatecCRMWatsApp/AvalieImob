// @module ptam/ConsultaSIGEF — Consulta automatica SIGEF/INCRA para laudos rurais
import React, { useState, useRef } from 'react';
import {
  Search, CheckCircle, AlertCircle, Loader2, ExternalLink, RefreshCw,
  Upload, FileText, MapPin,
} from 'lucide-react';
import { sigefAPI } from '../../../lib/api';

const ESTADOS_BR = [
  'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT',
  'PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO',
];

const RURAL_TYPES = new Set(['rural', 'fazenda', 'sitio', 'chacara', 'terreno_rural']);

function maskCCIR(v) {
  const d = v.replace(/\D/g, '').slice(0, 15);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0,3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6)}`;
  if (d.length <= 10) return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9)}`;
  return `${d.slice(0,3)}.${d.slice(3,6)}.${d.slice(6,9)}-${d.slice(9,10)}${d.slice(10)}`;
}

function SituacaoBadge({ situacao }) {
  const cfg = {
    certificado:    { cls: 'bg-emerald-100 border-emerald-300 text-emerald-800', label: 'SIGEF Certificado' },
    em_certificacao:{ cls: 'bg-yellow-100 border-yellow-300 text-yellow-800',   label: 'Em Certificação' },
    nao_certificado:{ cls: 'bg-gray-100 border-gray-300 text-gray-600',         label: 'Não Certificado' },
  };
  const c = cfg[situacao] || cfg.nao_certificado;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${c.cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {c.label}
    </span>
  );
}

function ClassificacaoBadge({ classificacao }) {
  if (!classificacao) return null;
  const cores = {
    'Minifúndio':         'bg-red-100 border-red-300 text-red-800',
    'Pequena Propriedade':'bg-blue-100 border-blue-300 text-blue-800',
    'Média Propriedade':  'bg-orange-100 border-orange-300 text-orange-800',
    'Grande Propriedade': 'bg-purple-100 border-purple-300 text-purple-800',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full border text-xs font-semibold ${cores[classificacao] || 'bg-gray-100 border-gray-300 text-gray-600'}`}>
      {classificacao}
    </span>
  );
}

function CardResultado({ resultado, onPreencher, onNovaConsulta }) {
  const campos = [
    resultado.sigef_area_ha != null && { label: 'Área certificada', val: `${Number(resultado.sigef_area_ha).toFixed(4)} ha` },
    resultado.sigef_data_certificacao && { label: 'Data certificação', val: resultado.sigef_data_certificacao },
    resultado.modulo_fiscal_ha && { label: 'Módulo fiscal', val: `${resultado.modulo_fiscal_ha} ha` },
    resultado.numero_modulos_fiscais && { label: 'Nº módulos fiscais', val: resultado.numero_modulos_fiscais },
    resultado.sigef_vertices && { label: 'Vértices', val: resultado.sigef_vertices },
    resultado.sigef_datum && { label: 'Datum', val: resultado.sigef_datum },
    resultado.sigef_perimetro_m && { label: 'Perímetro', val: `${Number(resultado.sigef_perimetro_m).toFixed(2)} m` },
    resultado.fonte && { label: 'Fonte', val: resultado.fonte.replace(/_/g, ' ') },
    resultado.data_consulta && { label: 'Data consulta', val: resultado.data_consulta },
  ].filter(Boolean);

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="font-bold text-emerald-900 text-sm">Imóvel localizado no SIGEF</div>
          {resultado.denominacao && (
            <div className="text-base font-semibold text-gray-800 mt-0.5 truncate">{resultado.denominacao}</div>
          )}
          {(resultado.municipio || resultado.uf) && (
            <div className="flex items-center gap-1 text-sm text-gray-600 mt-0.5">
              <MapPin className="w-3 h-3" />
              {resultado.municipio}{resultado.uf ? ` / ${resultado.uf}` : ''}
            </div>
          )}
        </div>
        <SituacaoBadge situacao={resultado.sigef_situacao} />
      </div>

      {resultado.classificacao_fundiaria && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Classificação:</span>
          <ClassificacaoBadge classificacao={resultado.classificacao_fundiaria} />
        </div>
      )}

      {resultado.sigef_codigo && (
        <div className="text-xs text-gray-400 font-mono truncate">
          Código SIGEF: {resultado.sigef_codigo}
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm bg-white rounded-lg border border-emerald-200 px-4 py-3">
        {campos.map(({ label, val }) => (
          <div key={label}>
            <span className="text-gray-500 text-xs">{label}</span>
            <div className="font-semibold text-gray-800 text-sm">{val}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          onClick={onPreencher}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-700 text-white font-semibold text-sm hover:bg-emerald-800 transition-colors"
        >
          <CheckCircle className="w-4 h-4" />
          Preencher laudo com estes dados
        </button>
        <button
          onClick={onNovaConsulta}
          className="px-3 py-2.5 rounded-lg border border-emerald-300 text-emerald-700 text-sm hover:bg-emerald-100 transition-colors"
          title="Nova consulta"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ── Aba 1: Busca Automatica WFS ───────────────────────────────────────────────

function AbaWFS({ form, setForm, onSwitchToUpload }) {
  const [ccir, setCcir] = useState('');
  const [sigefCodigo, setSigefCodigo] = useState('');
  const [estado, setEstado] = useState(form.property_state || 'MA');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState('');

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

    const interval = setInterval(() => setProgress(p => Math.min(p + 5, 90)), 1000);

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
      const msg = ex?.response?.data?.detail || 'Erro ao consultar SIGEF/INCRA. Tente via importação de arquivo.';
      setErro(msg);
    } finally {
      setLoading(false);
    }
  };

  const handlePreencher = () => {
    if (!resultado?.encontrado) return;
    _aplicarResultado(resultado, form, setForm);
  };

  const handleNovaConsulta = () => { setResultado(null); setErro(''); setProgress(0); };

  return (
    <div className="space-y-3">
      {!loading && !resultado && (
        <>
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
                Consultar
              </button>
            </div>
          </div>

          {erro && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                {erro}
                <div className="flex flex-wrap gap-2 mt-2">
                  <button
                    onClick={onSwitchToUpload}
                    className="text-xs bg-white border border-red-300 rounded px-2 py-1 text-red-700 hover:bg-red-50"
                  >
                    Ir para importação de arquivo
                  </button>
                  <a
                    href="https://sigef.incra.gov.br" target="_blank" rel="noopener noreferrer"
                    className="text-xs bg-white border border-red-300 rounded px-2 py-1 text-red-700 hover:bg-red-50 inline-flex items-center gap-1"
                  >
                    Abrir SIGEF <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {loading && (
        <div className="py-4 space-y-3">
          <div className="flex items-center gap-2 text-emerald-800 font-medium text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Consultando WFS SIGEF/INCRA...
          </div>
          <div className="w-full bg-emerald-100 rounded-full h-2">
            <div className="bg-emerald-600 h-2 rounded-full transition-all duration-1000" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-xs text-emerald-600">Aguarde até 20 segundos. O serviço WFS pode apresentar instabilidade.</p>
        </div>
      )}

      {!loading && resultado?.encontrado && (
        <CardResultado resultado={resultado} onPreencher={handlePreencher} onNovaConsulta={handleNovaConsulta} />
      )}

      {!loading && resultado && !resultado.encontrado && (
        <div className="space-y-3">
          <div className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2.5 text-sm text-yellow-800">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              {resultado.erros?.[0] || 'Imóvel não localizado no SIGEF com os dados fornecidos.'}
              <div className="flex flex-wrap gap-2 mt-2">
                <button
                  onClick={onSwitchToUpload}
                  className="text-xs bg-white border border-yellow-300 rounded px-2 py-1 text-yellow-800 hover:bg-yellow-50"
                >
                  Ir para importação de arquivo
                </button>
                <a
                  href="https://sigef.incra.gov.br" target="_blank" rel="noopener noreferrer"
                  className="text-xs bg-white border border-yellow-300 rounded px-2 py-1 text-yellow-800 hover:bg-yellow-50 inline-flex items-center gap-1"
                >
                  Abrir SIGEF <ExternalLink className="w-3 h-3" />
                </a>
              </div>
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
  );
}

// ── Aba 2: Importar Arquivo KML/XML ──────────────────────────────────────────

function AbaArquivo({ form, setForm }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [erro, setErro] = useState('');
  const [nomeArquivo, setNomeArquivo] = useState('');

  const TIPOS_ACEITOS = '.kml,.xml,.gml,.json,.geojson';

  const processarArquivo = async (file) => {
    if (!file) return;
    setNomeArquivo(file.name);
    setErro('');
    setResultado(null);
    setLoading(true);
    try {
      const data = await sigefAPI.importarArquivo(file);
      setResultado(data);
    } catch (ex) {
      const msg = ex?.response?.data?.detail || `Erro ao processar o arquivo "${file.name}".`;
      setErro(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (file) processarArquivo(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) processarArquivo(file);
  };

  const handlePreencher = () => {
    if (!resultado?.encontrado) return;
    _aplicarResultado(resultado, form, setForm);
  };

  const handleNovaConsulta = () => { setResultado(null); setErro(''); setNomeArquivo(''); };

  return (
    <div className="space-y-3">
      <div className="bg-white border border-emerald-200 rounded-lg px-3 py-2.5 text-xs text-emerald-800">
        <p className="font-semibold mb-1">Como exportar do SIGEF:</p>
        <ol className="list-decimal list-inside space-y-0.5 text-emerald-700">
          <li>Acesse <a href="https://sigef.incra.gov.br" target="_blank" rel="noopener noreferrer" className="underline inline-flex items-center gap-0.5">sigef.incra.gov.br <ExternalLink className="w-3 h-3" /></a></li>
          <li>Pesquise seu imóvel pelo CCIR ou denominação</li>
          <li>Clique na parcela → botão "Exportar" ou "Download KML"</li>
          <li>Arraste ou selecione o arquivo baixado abaixo</li>
        </ol>
      </div>

      {!resultado && (
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-lg border-2 border-dashed px-4 py-8 flex flex-col items-center justify-center gap-2 transition-colors ${
            dragging ? 'border-emerald-500 bg-emerald-50' : 'border-emerald-200 bg-white hover:border-emerald-400 hover:bg-emerald-50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={TIPOS_ACEITOS}
            className="hidden"
            onChange={handleFile}
          />
          {loading ? (
            <>
              <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
              <p className="text-sm text-emerald-700 font-medium">Processando {nomeArquivo}...</p>
            </>
          ) : (
            <>
              <Upload className="w-8 h-8 text-emerald-400" />
              <p className="text-sm text-emerald-700 font-medium">Arraste o arquivo aqui ou clique para selecionar</p>
              <p className="text-xs text-gray-400">Suportados: KML, XML, GML, JSON, GeoJSON</p>
            </>
          )}
        </div>
      )}

      {erro && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 text-sm text-red-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            {erro}
            <div className="flex flex-wrap gap-2 mt-2">
              <button onClick={handleNovaConsulta} className="text-xs bg-white border border-red-300 rounded px-2 py-1 text-red-700 hover:bg-red-50">
                Tentar outro arquivo
              </button>
              <a
                href="https://sigef.incra.gov.br" target="_blank" rel="noopener noreferrer"
                className="text-xs bg-white border border-red-300 rounded px-2 py-1 text-red-700 hover:bg-red-50 inline-flex items-center gap-1"
              >
                Abrir SIGEF <ExternalLink className="w-3 h-3" />
              </a>
              <button
                onClick={() => { handleNovaConsulta(); }}
                className="text-xs bg-white border border-red-300 rounded px-2 py-1 text-red-700 hover:bg-red-50"
              >
                Preencher manualmente
              </button>
            </div>
          </div>
        </div>
      )}

      {!loading && resultado?.encontrado && (
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-medium">
            <FileText className="w-3.5 h-3.5" />
            {nomeArquivo}
          </div>
          <CardResultado resultado={resultado} onPreencher={handlePreencher} onNovaConsulta={handleNovaConsulta} />
        </div>
      )}

      {!loading && resultado && !resultado.encontrado && (
        <div className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2.5 text-sm text-yellow-800">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            {resultado.erro || 'Não foi possível extrair dados do arquivo.'}
            <button onClick={handleNovaConsulta} className="block mt-1 text-xs text-yellow-600 hover:underline">
              Tentar outro arquivo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Aplicar resultado ao form ─────────────────────────────────────────────────

function _aplicarResultado(resultado, form, setForm) {
  const now = new Date().toLocaleDateString('pt-BR');
  let campos = 0;

  const upd = { ...form };
  const set = (k, v) => { if (v != null && v !== '') { upd[k] = v; campos++; } };

  set('property_area_ha', resultado.sigef_area_ha);
  set('property_city', resultado.municipio);
  set('property_state', resultado.uf);
  set('denominacao', resultado.denominacao);
  set('sigef_codigo', resultado.sigef_codigo);
  set('certificacao_sigef', resultado.sigef_codigo);
  set('ccir_numero', resultado.ccir_numero);
  set('ccir', resultado.ccir_numero);
  set('sigef_situacao', resultado.sigef_situacao);
  set('sigef_data_certificacao', resultado.sigef_data_certificacao);
  set('sigef_area_ha', resultado.sigef_area_ha);
  set('sigef_perimetro_m', resultado.sigef_perimetro_m);
  set('sigef_vertices', resultado.sigef_vertices);
  set('sigef_datum', resultado.sigef_datum || 'SIRGAS 2000');
  set('modulo_fiscal_ha', resultado.modulo_fiscal_ha);
  set('numero_modulos_fiscais', resultado.numero_modulos_fiscais);
  set('municipio_incra', resultado.municipio);
  set('uf_incra', resultado.uf);
  upd.dados_incra_automaticos = true;
  upd.dados_incra_data_consulta = now;

  setForm(upd);

  window.dispatchEvent(new CustomEvent('avalieimob:toast', {
    detail: {
      message: `${campos} campos preenchidos automaticamente via SIGEF/INCRA`,
      type: 'success',
    },
  }));
}

// ── Componente principal ──────────────────────────────────────────────────────

export function ConsultaSIGEF({ form, setForm }) {
  const [aba, setAba] = useState('wfs');  // 'wfs' | 'arquivo'

  if (!RURAL_TYPES.has((form.property_type || '').toLowerCase())) return null;

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
            <div className="text-xs text-emerald-700">Busca dados oficiais do imóvel rural — WFS público + importação de arquivo</div>
          </div>
        </div>

        {/* Abas */}
        <div className="flex border-b border-emerald-200 mb-4">
          {[
            { id: 'wfs',    label: 'Busca Automática (WFS)', icon: Search },
            { id: 'arquivo',label: 'Importar Arquivo',       icon: Upload },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setAba(id)}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold border-b-2 -mb-px transition-colors ${
                aba === id
                  ? 'border-emerald-700 text-emerald-900 bg-white rounded-t-lg'
                  : 'border-transparent text-emerald-600 hover:text-emerald-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Conteudo da aba */}
        {aba === 'wfs' && (
          <AbaWFS form={form} setForm={setForm} onSwitchToUpload={() => setAba('arquivo')} />
        )}
        {aba === 'arquivo' && (
          <AbaArquivo form={form} setForm={setForm} />
        )}
      </div>
    </div>
  );
}

export default ConsultaSIGEF;
