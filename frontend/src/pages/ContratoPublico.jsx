/**
 * @module pages/ContratoPublico
 * Portal público para visualização de contrato via token
 * Rota pública: /contrato/public/:token
 * Sem autenticação — acessível a qualquer pessoa com o link
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileSignature, MapPin, User, Users, DollarSign,
  AlertCircle, FileText, Calendar, Building2, Lock,
  CheckCircle2, Eye,
} from 'lucide-react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const COLORS = {
  primary: '#1B4D1B',
  gold: '#D4A830',
  bg: '#f8fafc',
};

const fmtCurrency = (v) => {
  if (!v && v !== 0) return '—';
  return Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

const fmtDate = (d) => {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
};

const TIPO_LABEL = {
  compra_venda: 'Compra e Venda',
  promessa_compra_venda: 'Promessa de Compra e Venda',
  permuta: 'Permuta',
  cessao_direitos: 'Cessão de Direitos',
  locacao_residencial: 'Locação Residencial',
  locacao_comercial: 'Locação Comercial',
  comodato: 'Comodato',
  arrendamento_rural: 'Arrendamento Rural',
  parceria_rural: 'Parceria Rural',
  doacao: 'Doação',
  arras: 'Arras / Sinal',
  intermediacao: 'Intermediação',
  usufruto: 'Usufruto',
  compra_venda_veiculo: 'C&V Veículo',
  distrato: 'Distrato',
};

const STATUS_CONFIG = {
  MINUTA:    { label: 'Minuta', bg: 'bg-gray-100', text: 'text-gray-700' },
  ATIVO:     { label: 'Ativo',  bg: 'bg-emerald-100', text: 'text-emerald-800' },
  ASSINADO:  { label: 'Assinado', bg: 'bg-blue-100', text: 'text-blue-800' },
  RESCINDIDO:{ label: 'Rescindido', bg: 'bg-red-100', text: 'text-red-800' },
  CONCLUIDO: { label: 'Concluído', bg: 'bg-emerald-100', text: 'text-emerald-800' },
};

const Skeleton = ({ className }) => (
  <div className={`animate-pulse bg-gray-200 rounded ${className}`} />
);

const ContratoPublico = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/contratos/public/${token}`);
        setData(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Contrato não encontrado ou link inativo');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  /* ── Estado de erro 404 ── */
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: COLORS.bg }}>
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <FileSignature className="w-10 h-10 text-gray-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Contrato não encontrado</h1>
          <p className="text-gray-600 mb-2">{error}</p>
          <p className="text-sm text-gray-400 mb-6">
            Este link pode ter expirado ou o contrato pode não estar mais disponível para acesso público.
          </p>
          <button
            onClick={() => navigate('/')}
            className="bg-emerald-800 hover:bg-emerald-900 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition"
          >
            Conhecer o AvalieImob
          </button>
        </div>
      </div>
    );
  }

  /* ── Loading skeleton ── */
  if (loading) {
    return (
      <div className="min-h-screen" style={{ backgroundColor: COLORS.bg }}>
        <div className="h-20" style={{ backgroundColor: COLORS.primary }} />
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
          <Skeleton className="h-40" />
          <Skeleton className="h-56" />
          <Skeleton className="h-32" />
        </div>
      </div>
    );
  }

  const tipoLabel = TIPO_LABEL[data?.tipo] || data?.tipo || '—';
  const statusCfg = STATUS_CONFIG[data?.status] || STATUS_CONFIG.MINUTA;

  /* Exibir apenas nomes, sem CPF */
  const vendedores = (data?.vendedores || []).map(v => v.nome || v.razao_social || '—');
  const compradores = (data?.compradores || []).map(c => c.nome || c.razao_social || '—');

  /* Endereço resumido do objeto */
  const obj = data?.objeto || {};
  const enderecoResumo = [
    obj.endereco || obj.descricao_veiculo,
    obj.bairro,
    obj.cidade,
    obj.uf,
  ].filter(Boolean).join(', ') || '—';

  return (
    <div className="min-h-screen pb-16" style={{ backgroundColor: COLORS.bg }}>

      {/* HEADER */}
      <header className="text-white py-5 px-4" style={{ backgroundColor: COLORS.primary }}>
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="/brand/logo_principal.png"
              alt="Romatec"
              className="h-11 object-contain"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <div className="hidden sm:block">
              <div className="text-xs font-bold tracking-wide opacity-90">AVALIEIMOB</div>
              <div className="text-xs opacity-60">RomaTec Consultoria Imobiliária</div>
            </div>
          </div>

          <div className="text-xs text-white/70 text-right">
            <div>Documento compartilhado via AvalieImob</div>
            <div className="text-white/40 mt-0.5 font-mono">{token?.substring(0, 16)}...</div>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">

        {/* HERO CARD */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden border-l-4" style={{ borderLeftColor: COLORS.gold }}>
          <div className="p-6 md:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-1">
                  <FileSignature className="w-5 h-5" style={{ color: COLORS.primary }} />
                  <span className="text-xs font-bold uppercase tracking-widest text-gray-400">Contrato</span>
                </div>
                <h2 className="text-2xl md:text-3xl font-bold" style={{ color: COLORS.primary }}>
                  {data?.numero_contrato || `Nº ${data?.id?.substring(0, 8)}`}
                </h2>
                <div className="text-base font-semibold text-gray-700">{tipoLabel}</div>
              </div>

              <span className={`px-3 py-1.5 rounded-full text-sm font-semibold ${statusCfg.bg} ${statusCfg.text}`}>
                {statusCfg.label}
              </span>
            </div>
          </div>
        </div>

        {/* Partes */}
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4" style={{ color: COLORS.primary }} />
            Partes Envolvidas
          </h3>

          <div className="space-y-3">
            {vendedores.length > 0 && (
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  {data?.tipo?.includes('locac') ? 'Locador(es)' : 'Vendedor(es)'}
                </div>
                {vendedores.map((nome, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-800 py-1">
                    <User className="w-3.5 h-3.5 text-gray-400" />
                    {nome}
                  </div>
                ))}
              </div>
            )}

            {compradores.length > 0 && (
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">
                  {data?.tipo?.includes('locac') ? 'Locatário(s)' : 'Comprador(es)'}
                </div>
                {compradores.map((nome, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-800 py-1">
                    <User className="w-3.5 h-3.5 text-gray-400" />
                    {nome}
                  </div>
                ))}
              </div>
            )}

            {data?.corretor?.incluir && data.corretor.nome && (
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Corretor</div>
                <div className="flex items-center gap-2 text-sm text-gray-800">
                  <User className="w-3.5 h-3.5 text-gray-400" />
                  {data.corretor.nome}
                  {data.corretor.creci && <span className="text-gray-400 text-xs">— {data.corretor.creci}</span>}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Objeto */}
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Building2 className="w-4 h-4" style={{ color: COLORS.primary }} />
            Objeto do Contrato
          </h3>

          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              <span className="text-gray-800">{enderecoResumo}</span>
            </div>
            {obj.tipo_bem && (
              <div className="text-xs text-gray-400 ml-6">
                {obj.tipo_bem === 'imovel_urbano' ? 'Imóvel Urbano' :
                 obj.tipo_bem === 'imovel_rural' ? 'Imóvel Rural' : 'Veículo'}
                {obj.area_total ? ` — ${obj.area_total} ${obj.tipo_bem === 'imovel_rural' ? 'ha' : 'm²'}` : ''}
                {obj.matricula ? ` — Mat. ${obj.matricula}` : ''}
              </div>
            )}
          </div>
        </section>

        {/* Pagamento resumido */}
        {data?.pagamento?.valor_total > 0 && (
          <section className="bg-emerald-50 rounded-xl p-6 border-2 border-emerald-100">
            <h3 className="text-base font-bold text-emerald-900 mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Valor do Negócio
            </h3>
            <p className="text-3xl font-bold" style={{ color: COLORS.primary }}>
              {fmtCurrency(data.pagamento.valor_total)}
            </p>
            {data.pagamento.arras_valor > 0 && (
              <p className="text-sm text-emerald-700 mt-1">
                Arras: {fmtCurrency(data.pagamento.arras_valor)} ({data.pagamento.arras_tipo === 'confirmatorias' ? 'confirmatórias' : 'penitenciais'})
              </p>
            )}
          </section>
        )}

        {/* Datas */}
        <section className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar className="w-4 h-4" style={{ color: COLORS.primary }} />
            Datas
          </h3>
          <div className="grid sm:grid-cols-2 gap-3 text-sm">
            {data?.data_assinatura && (
              <div>
                <div className="text-xs text-gray-400 uppercase mb-0.5">Assinatura</div>
                <div className="font-medium text-gray-800">{fmtDate(data.data_assinatura)}</div>
              </div>
            )}
            {data?.cidade_assinatura && (
              <div>
                <div className="text-xs text-gray-400 uppercase mb-0.5">Local</div>
                <div className="font-medium text-gray-800">{data.cidade_assinatura}</div>
              </div>
            )}
          </div>
        </section>

        {/* Lacre */}
        {data?.lacrado && (
          <section className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <Lock className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <div className="font-semibold text-blue-900 text-sm">Documento com Lacre Digital</div>
                <div className="text-xs text-blue-700 mt-0.5">
                  Versão lacrada com hash SHA-256. Autenticidade garantida.
                </div>
              </div>
              <CheckCircle2 className="w-5 h-5 text-blue-600 ml-auto" />
            </div>
          </section>
        )}
      </div>

      {/* FOOTER */}
      <footer className="text-white py-8 px-4 mt-8" style={{ backgroundColor: COLORS.primary }}>
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-sm opacity-90 mb-1">Documento compartilhado via AvalieImob</p>
          <p className="text-sm opacity-60 mb-1">RomaTec Consultoria Imobiliária</p>
          <p className="text-xs opacity-40 mt-3">
            Os dados exibidos neste portal são parciais para fins de compartilhamento.
            O documento completo está disponível apenas para as partes envolvidas.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default ContratoPublico;
