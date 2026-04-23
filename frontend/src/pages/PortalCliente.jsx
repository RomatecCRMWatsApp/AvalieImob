/**
 * @module pages/PortalCliente
 * Portal público do cliente — visualização profissional de laudo PTAM
 * Rota pública: /laudo/:token
 * Sem autenticação — acessível a qualquer pessoa com o link
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { 
  Download, 
  Share2, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle,
  Lock,
  FileText,
  Eye,
  MapPin,
  Building,
  Ruler,
  DollarSign,
  User,
  Award,
  Calendar,
  ExternalLink,
  Copy,
  X
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { valorExtenso } from '../utils/valorExtenso';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Cores do sistema
const COLORS = {
  primary: '#1B4D1B',
  gold: '#D4A830',
  bg: '#f8fafc',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
};

const formatCurrency = (value) => {
  if (!value && value !== 0) return '—';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
};

const formatNumber = (value, decimals = 2) => {
  if (!value && value !== 0) return '—';
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
};

// Skeleton para loading
const Skeleton = ({ className }) => (
  <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
);

// Modal de verificação de autenticidade
const VerificarModal = ({ token, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const verificar = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/ptam/public/${token}/verificar`);
        setResult(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Erro na verificação');
      } finally {
        setLoading(false);
      }
    };
    verificar();
  }, [token]);

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">Verificação de Autenticidade</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin w-10 h-10 border-3 border-emerald-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-600">Verificando hash SHA-256...</p>
          </div>
        ) : error ? (
          <div className="text-center py-6">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <p className="text-red-600">{error}</p>
          </div>
        ) : result ? (
          <div className="space-y-4">
            <div className={`p-4 rounded-xl ${result.integro ? 'bg-emerald-50 border-2 border-emerald-200' : 'bg-red-50 border-2 border-red-200'}`}>
              <div className="flex items-center gap-3 mb-2">
                {result.integro ? (
                  <CheckCircle className="w-8 h-8 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-8 h-8 text-red-600" />
                )}
                <div>
                  <p className={`font-bold text-lg ${result.integro ? 'text-emerald-800' : 'text-red-800'}`}>
                    {result.integro ? 'Documento Íntegro' : 'Integridade Comprometida'}
                  </p>
                  <p className="text-sm text-gray-600">
                    {result.integro 
                      ? 'O hash SHA-256 corresponde ao documento original.'
                      : 'O documento pode ter sido alterado desde o lacre.'}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Número de Lacre</p>
              <p className="font-mono font-bold text-gray-800">{result.numero_lacre}</p>
            </div>

            <div className="space-y-2">
              <div className="bg-gray-50 rounded p-2">
                <p className="text-xs text-gray-500 mb-1">Hash Armazenado</p>
                <code className="text-xs font-mono break-all text-gray-700">{result.hash_armazenado}</code>
              </div>
              <div className="bg-gray-50 rounded p-2">
                <p className="text-xs text-gray-500 mb-1">Hash Calculado</p>
                <code className="text-xs font-mono break-all text-gray-700">{result.hash_calculado}</code>
              </div>
            </div>
          </div>
        ) : null}

        <Button className="w-full mt-4" onClick={onClose}>
          Fechar
        </Button>
      </div>
    </div>
  );
};

// Modal de compartilhamento
const ShareModal = ({ url, onClose }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleWhatsApp = () => {
    const text = `Segue o laudo de avaliação do imóvel: ${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">Compartilhar Laudo</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-2">Link do laudo</p>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={url} 
                readOnly 
                className="flex-1 bg-white border rounded px-3 py-2 text-sm font-mono text-gray-600"
              />
              <Button variant="outline" size="sm" onClick={handleCopy}>
                {copied ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </Button>
            </div>
          </div>

          <Button 
            className="w-full bg-green-600 hover:bg-green-700 text-white"
            onClick={handleWhatsApp}
          >
            <Share2 className="w-4 h-4 mr-2" />
            Enviar por WhatsApp
          </Button>

          <Button 
            variant="outline" 
            className="w-full"
            onClick={() => window.open(url, '_blank')}
          >
            <ExternalLink className="w-4 h-4 mr-2" />
            Abrir em nova aba
          </Button>
        </div>
      </div>
    </div>
  );
};

const PortalCliente = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [showVerificar, setShowVerificar] = useState(false);
  const [showShare, setShowShare] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  const currentUrl = window.location.href;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/ptam/public/${token}`);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Erro ao carregar laudo');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const handleDownloadPDF = async () => {
    setPdfLoading(true);
    try {
      const res = await axios.get(`${API_URL}/api/ptam/public/${token}/pdf`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `PTAM_${data?.number?.replace('/', '-') || 'laudo'}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Erro ao baixar PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  // Estado de erro/404
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: COLORS.bg }}>
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <FileText className="w-10 h-10 text-gray-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Laudo não encontrado</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <Button 
            className="bg-emerald-800 hover:bg-emerald-900 text-white"
            onClick={() => navigate('/')}
          >
            Conhecer o AvalieImob
          </Button>
        </div>
      </div>
    );
  }

  // Loading skeleton
  if (loading) {
    return (
      <div className="min-h-screen" style={{ backgroundColor: COLORS.bg }}>
        {/* Header skeleton */}
        <div className="h-20" style={{ backgroundColor: COLORS.primary }} />
        
        <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-64" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  const valorExtensoText = valorExtenso(data?.resultado_valor_total || 0);

  return (
    <div className="min-h-screen pb-12" style={{ backgroundColor: COLORS.bg }}>
      {/* HEADER */}
      <header className="text-white py-5 px-4" style={{ backgroundColor: COLORS.primary }}>
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img 
              src="/brand/logo_principal.png" 
              alt="AvalieImob" 
              className="h-12 object-contain"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          </div>
          
          <h1 className="hidden md:block text-sm font-bold tracking-wide text-center flex-1 px-4">
            PARECER TÉCNICO DE AVALIAÇÃO MERCADOLÓGICA
          </h1>
          
          <div>
            {data?.lacrado ? (
              <Badge className="bg-amber-400 text-emerald-950 font-bold px-3 py-1">
                <Lock className="w-3 h-3 mr-1 inline" />
                Documento Oficial
              </Badge>
            ) : (
              <Badge className="bg-white/20 text-white px-3 py-1">
                <FileText className="w-3 h-3 mr-1 inline" />
                Laudo Técnico
              </Badge>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* HERO CARD */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden border-l-4" style={{ borderLeftColor: COLORS.gold }}>
          <div className="p-6 md:p-8">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Coluna esquerda */}
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Número do Laudo</p>
                  <h2 className="text-2xl md:text-3xl font-bold" style={{ color: COLORS.primary }}>
                    PTAM Nº {data?.number}
                  </h2>
                </div>
                
                <div className="flex items-start gap-2">
                  <MapPin className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-gray-900">{data?.property_address}</p>
                    <p className="text-sm text-gray-500">
                      {data?.property_neighborhood}{data?.property_city && `, ${data.property_city}`}
                      {data?.property_state && ` - ${data.property_state}`}
                    </p>
                  </div>
                </div>
                
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="text-gray-600">
                    <Building className="w-3 h-3 mr-1" />
                    {data?.property_type || 'Imóvel'}
                  </Badge>
                  <Badge variant="outline" className="text-gray-600">
                    <Ruler className="w-3 h-3 mr-1" />
                    {formatNumber(data?.property_area_sqm || data?.property_area_terreno)} m²
                  </Badge>
                </div>
              </div>
              
              {/* Coluna direita - Valor */}
              <div className="bg-emerald-50 rounded-xl p-6 border-2 border-emerald-100">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                  Valor de Mercado
                </p>
                <p className="text-3xl md:text-4xl font-bold" style={{ color: COLORS.primary }}>
                  {formatCurrency(data?.resultado_valor_total)}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  {formatCurrency(data?.resultado_valor_unitario)}/m²
                </p>
                
                {data?.fundamentacao_grau && (
                  <Badge className="mt-3 bg-emerald-600 text-white">
                    Grau {data.fundamentacao_grau} — Fundamentação 
                    {data.fundamentacao_grau === 'III' ? 'Máxima' : data.fundamentacao_grau === 'II' ? 'Intermediária' : 'Mínima'}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* BARRA DE AÇÕES STICKY */}
        <div className="sticky top-4 z-40 bg-white rounded-xl shadow-lg p-4 border">
          <div className="flex flex-wrap gap-2 justify-center">
            <Button 
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={handleDownloadPDF}
              disabled={pdfLoading}
            >
              <Download className="w-4 h-4 mr-2" />
              {pdfLoading ? 'Gerando PDF...' : 'Baixar PDF'}
            </Button>
            
            <Button 
              variant="outline"
              onClick={() => setShowShare(true)}
            >
              <Share2 className="w-4 h-4 mr-2" />
              Compartilhar
            </Button>
            
            {data?.lacrado && (
              <Button 
                variant="outline"
                className="border-blue-300 text-blue-700 hover:bg-blue-50"
                onClick={() => setShowVerificar(true)}
              >
                <ShieldCheck className="w-4 h-4 mr-2" />
                Verificar Autenticidade
              </Button>
            )}
          </div>
        </div>

        {/* SEÇÃO: Identificação do Imóvel */}
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Building className="w-5 h-5" style={{ color: COLORS.primary }} />
            Identificação do Imóvel
          </h3>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase">Matrícula</p>
              <p className="font-medium">{data?.property_matricula || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Cartório</p>
              <p className="font-medium">{data?.property_cartorio || '—'}</p>
            </div>
            <div className="md:col-span-2">
              <p className="text-xs text-gray-500 uppercase">Endereço Completo</p>
              <p className="font-medium">{data?.property_address}</p>
              <p className="text-gray-600">
                {data?.property_neighborhood}{data?.property_city && `, ${data.property_city}`}
                {data?.property_state && ` - ${data.property_state}`}
                {data?.property_cep && `, CEP ${data.property_cep}`}
              </p>
            </div>
            
            <div>
              <p className="text-xs text-gray-500 uppercase">Área do Terreno</p>
              <p className="font-medium">{formatNumber(data?.property_area_terreno || data?.property_area_sqm)} m²</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Área Construída</p>
              <p className="font-medium">{formatNumber(data?.property_area_construida)} m²</p>
            </div>
          </div>
        </section>

        {/* SEÇÃO: Metodologia */}
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Award className="w-5 h-5" style={{ color: COLORS.primary }} />
            Metodologia e Fundamentação
          </h3>
          
          <div className="space-y-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 uppercase mb-1">Método Utilizado</p>
              <p className="font-medium text-gray-900">{data?.methodology || 'Método Comparativo Direto de Dados de Mercado'}</p>
            </div>
            
            <div className="flex flex-wrap gap-4">
              {data?.fundamentacao_grau && (
                <div className="flex-1 min-w-[200px] p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                  <p className="text-xs text-gray-500 uppercase mb-1">Grau de Fundamentação</p>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-emerald-600 text-white text-lg px-3 py-1">
                      {data.fundamentacao_grau}
                    </Badge>
                    <span className="text-sm text-gray-600">
                      {data.fundamentacao_grau === 'III' ? 'Máxima' : data.fundamentacao_grau === 'II' ? 'Intermediária' : 'Mínima'}
                    </span>
                  </div>
                </div>
              )}
              
              {data?.precisao_grau && (
                <div className="flex-1 min-w-[200px] p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="text-xs text-gray-500 uppercase mb-1">Grau de Precisão</p>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-blue-600 text-white text-lg px-3 py-1">
                      {data.precisao_grau}
                    </Badge>
                    <span className="text-sm text-gray-600">
                      {data.precisao_grau === 'III' ? 'Máxima' : data.precisao_grau === 'II' ? 'Intermediária' : data.precisao_grau === 'I' ? 'Mínima' : 'Fora dos limites'}
                    </span>
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 uppercase mb-1">Amostras Pesquisadas</p>
              <p className="font-medium">{data?.calc_n_validas || data?.market_samples?.length || 0} dados de mercado</p>
            </div>
          </div>
        </section>

        {/* SEÇÃO: Amostras de Mercado */}
        {data?.market_samples?.length > 0 && (
          <section className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5" style={{ color: COLORS.primary }} />
              Amostras de Mercado
            </h3>
            
            {/* Desktop: Tabela */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Nº</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Endereço</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Bairro</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Área (m²)</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Valor Total</th>
                    <th className="px-3 py-2 text-right font-medium text-gray-600">Valor/m²</th>
                    <th className="px-3 py-2 text-left font-medium text-gray-600">Tipo</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.market_samples.map((sample, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-500">{idx + 1}</td>
                      <td className="px-3 py-2">{sample.address || '—'}</td>
                      <td className="px-3 py-2">{sample.neighborhood || '—'}</td>
                      <td className="px-3 py-2 text-right">{formatNumber(sample.area, 0)}</td>
                      <td className="px-3 py-2 text-right">{formatCurrency(sample.value)}</td>
                      <td className="px-3 py-2 text-right font-medium">{formatCurrency(sample.value_per_sqm)}</td>
                      <td className="px-3 py-2">
                        <Badge variant={sample.tipo_amostra === 'consolidada' ? 'default' : 'secondary'} className="text-xs">
                          {sample.tipo_amostra === 'consolidada' ? 'Consolidada' : 'Oferta'}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-emerald-50 font-bold">
                    <td colSpan={5} className="px-3 py-2 text-right" style={{ color: COLORS.primary }}>
                      Média Adotada
                    </td>
                    <td className="px-3 py-2 text-right" style={{ color: COLORS.primary }}>
                      {formatCurrency(data.calc_media_final)}
                    </td>
                    <td />
                  </tr>
                </tbody>
              </table>
            </div>
            
            {/* Mobile: Cards */}
            <div className="md:hidden space-y-3">
              {data.market_samples.map((sample, idx) => (
                <div key={idx} className="border rounded-lg p-3 bg-gray-50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-gray-500">Amostra {idx + 1}</span>
                    <Badge variant={sample.tipo_amostra === 'consolidada' ? 'default' : 'secondary'} className="text-xs">
                      {sample.tipo_amostra === 'consolidada' ? 'Consolidada' : 'Oferta'}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-1">{sample.address}</p>
                  <p className="text-sm text-gray-500">{sample.neighborhood}</p>
                  <div className="flex justify-between mt-2 pt-2 border-t">
                    <span className="text-sm">{formatNumber(sample.area, 0)} m²</span>
                    <span className="font-bold" style={{ color: COLORS.primary }}>{formatCurrency(sample.value_per_sqm)}/m²</span>
                  </div>
                </div>
              ))}
              
              <div className="bg-emerald-50 border-2 border-emerald-200 rounded-lg p-4">
                <p className="text-sm text-gray-600">Média Adotada</p>
                <p className="text-2xl font-bold" style={{ color: COLORS.primary }}>
                  {formatCurrency(data.calc_media_final)}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* SEÇÃO: Resultado da Avaliação */}
        <section className="bg-emerald-50 rounded-xl p-6 md:p-8 border-2 border-emerald-200">
          <div className="text-center">
            <p className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">
              Valor de Mercado Determinado
            </p>
            
            <p className="text-4xl md:text-5xl font-bold mb-2" style={{ color: COLORS.primary }}>
              {formatCurrency(data?.resultado_valor_total)}
            </p>
            
            <p className="text-lg text-gray-600 italic mb-4">
              {valorExtensoText}
            </p>
            
            {data?.resultado_data_referencia && (
              <p className="text-sm text-gray-500">
                Data de referência: {formatDate(data.resultado_data_referencia)}
              </p>
            )}
            
            {(data?.resultado_intervalo_inf || data?.resultado_intervalo_sup) && (
              <div className="mt-4 p-3 bg-white rounded-lg inline-block">
                <p className="text-xs text-gray-500 mb-1">Intervalo de Valores (±5%)</p>
                <p className="text-sm font-medium">
                  Limite inferior: {formatCurrency(data.resultado_intervalo_inf)} — 
                  Limite superior: {formatCurrency(data.resultado_intervalo_sup)}
                </p>
              </div>
            )}
          </div>
        </section>

        {/* SEÇÃO: Responsável Técnico */}
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <User className="w-5 h-5" style={{ color: COLORS.primary }} />
            Responsável Técnico
          </h3>
          
          <div className="flex items-start gap-4">
            {data?.perfil_avaliador?.foto_perfil ? (
              <img 
                src={data.perfil_avaliador.foto_perfil} 
                alt={data.responsavel_nome}
                className="w-20 h-20 rounded-full object-cover border-2" style={{ borderColor: COLORS.gold }}
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center">
                <User className="w-10 h-10 text-gray-400" />
              </div>
            )}
            
            <div className="flex-1">
              <p className="text-xl font-bold text-gray-900">{data?.responsavel_nome}</p>
              
              <div className="flex flex-wrap gap-2 mt-2">
                {data?.responsavel_creci && (
                  <Badge variant="outline" className="text-emerald-700 border-emerald-300">
                    {data.responsavel_creci}
                  </Badge>
                )}
                {data?.responsavel_cnai && (
                  <Badge variant="outline" className="text-blue-700 border-blue-300">
                    {data.responsavel_cnai}
                  </Badge>
                )}
                {data?.registro_profissional && (
                  <Badge variant="outline" className="text-purple-700 border-purple-300">
                    {data.registro_profissional}
                  </Badge>
                )}
                {data?.perfil_avaliador?.registros?.map((reg, idx) => (
                  <Badge key={idx} variant="outline" className="text-gray-600">
                    {reg.tipo} {reg.numero}{reg.uf && `/${reg.uf}`}
                  </Badge>
                ))}
              </div>
              
              <p className="text-sm text-gray-500 mt-3">
                <Calendar className="w-4 h-4 inline mr-1" />
                Laudo emitido em: {formatDate(data?.conclusion_date || data?.updated_at)}
                {data?.conclusion_city && ` — ${data.conclusion_city}`}
              </p>
            </div>
          </div>
        </section>

        {/* SEÇÃO: Autenticidade (apenas se lacrado) */}
        {data?.lacrado && (
          <section className="bg-blue-50 rounded-xl p-6 border-2 border-blue-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                <Lock className="w-6 h-6 text-blue-600" />
              </div>
              
              <div className="flex-1">
                <h3 className="text-lg font-bold text-blue-900 mb-2">
                  Documento com Verificação Criptográfica
                </h3>
                
                <p className="text-sm text-blue-700 mb-4">
                  Este laudo possui versão lacrada com hash SHA-256 para garantia de autenticidade.
                </p>
                
                <div className="grid md:grid-cols-2 gap-4 mb-4">
                  <div className="bg-white rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-1">Número de Lacre</p>
                    <code className="font-mono font-bold text-blue-800">{data.versao_lacrada}</code>
                  </div>
                  
                  <div className="bg-white rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-1">Hash SHA-256</p>
                    <code className="font-mono text-xs text-gray-600 break-all">
                      {data.hash_lacrado?.substring(0, 32)}...
                    </code>
                  </div>
                </div>
                
                <div className="flex flex-wrap items-center gap-4">
                  <div className="bg-white p-2 rounded-lg">
                    <QRCodeSVG value={currentUrl} size={100} level="M" />
                  </div>
                  
                  <div className="flex-1">
                    <Button 
                      variant="outline"
                      className="border-blue-300 text-blue-700 hover:bg-blue-100"
                      onClick={() => setShowVerificar(true)}
                    >
                      <ShieldCheck className="w-4 h-4 mr-2" />
                      Verificar Integridade
                    </Button>
                    <p className="text-xs text-gray-500 mt-2">
                      Escaneie o QR Code ou clique no botão para verificar a autenticidade deste documento.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}
      </div>

      {/* FOOTER */}
      <footer className="text-white py-8 px-4 mt-12" style={{ backgroundColor: COLORS.primary }}>
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm opacity-90 mb-2">
            Documento gerado pela plataforma AvalieImob
          </p>
          
          <p className="text-sm opacity-75 mb-2">
            RomaTec Consultoria Imobiliária — Açailândia, MA
          </p>
          
          <p className="text-sm opacity-75 mb-4">
            www.romatecavalieimob.com.br
          </p>
          
          <div className="flex items-center justify-center gap-2 text-sm opacity-75">
            <Eye className="w-4 h-4" />
            <span>Este laudo foi visualizado {data?.visualizacoes || 1} vez(es)</span>
          </div>
          
          <p className="text-xs opacity-50 mt-4">
            Este documento tem validade técnica conforme NBR 14.653 e Resolução COFECI 1.066/2007
          </p>
        </div>
      </footer>

      {/* Modais */}
      {showVerificar && (
        <VerificarModal token={token} onClose={() => setShowVerificar(false)} />
      )}
      
      {showShare && (
        <ShareModal url={currentUrl} onClose={() => setShowShare(false)} />
      )}
    </div>
  );
};

export default PortalCliente;
