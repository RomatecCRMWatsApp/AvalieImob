/**
 * @module pages/VerificarContrato — Verificação pública de autenticidade
 * Rota: /verificar/:hash — consome /api/publico/contratos-exclusividade/verificar/:hash
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { contratosExclusividadeAPI } from '../lib/api';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const PAPEL_LABEL = { proprietario: 'Proprietário(a)', conjuge: 'Cônjuge/Companheiro(a)' };
const STATUS_LABEL = {
  rascunho: ['Rascunho', '#9ca3af'], enviado: ['Enviado', '#3b82f6'],
  parcialmente_assinado: ['Parcialmente assinado', '#d97706'],
  assinado: ['Assinado', '#16a34a'], expirado: ['Expirado', '#dc2626'],
  cancelado: ['Cancelado', '#dc2626'],
};

const fmtData = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return String(iso); }
};

const Shell = ({ children }) => (
  <div style={{ minHeight: '100vh', background: VERDE, color: '#f4efe2' }}
       className="flex flex-col items-center px-4 py-10">
    <div style={{ maxWidth: 640, width: '100%' }}>
      <div className="flex items-center gap-2 mb-6">
        <span style={{ color: DOURADO, fontFamily: '"Playfair Display", Georgia, serif', fontSize: 24, fontWeight: 700 }}>
          ROMATEC
        </span>
        <span style={{ opacity: 0.7, fontSize: 13 }}>Consultoria Total</span>
      </div>
      {children}
    </div>
  </div>
);

const Card = ({ children }) => (
  <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(201,168,76,0.25)',
                borderRadius: 16, padding: 24 }}>{children}</div>
);

export default function VerificarContrato() {
  const { hash } = useParams();
  const [estado, setEstado] = useState('loading');
  const [data, setData] = useState(null);

  useEffect(() => {
    let vivo = true;
    contratosExclusividadeAPI.verificar(hash)
      .then((d) => { if (vivo) { setData(d); setEstado('ok'); } })
      .catch(() => { if (vivo) setEstado('erro'); });
    return () => { vivo = false; };
  }, [hash]);

  if (estado === 'loading') return <Shell><Card><p>Verificando…</p></Card></Shell>;

  if (estado === 'erro' || !data?.valido) {
    return (
      <Shell>
        <Card>
          <h1 style={{ fontFamily: '"Playfair Display", Georgia, serif', color: '#f87171', fontSize: 22, margin: '0 0 8px' }}>
            ❌ Documento não encontrado
          </h1>
          <p style={{ opacity: 0.85 }}>
            {data?.mensagem || 'Nenhum contrato corresponde a este código de verificação.'}
          </p>
        </Card>
      </Shell>
    );
  }

  const [stLabel, stColor] = STATUS_LABEL[data.status] || [data.status, '#9ca3af'];

  return (
    <Shell>
      <Card>
        <h1 style={{ fontFamily: '"Playfair Display", Georgia, serif', color: DOURADO, fontSize: 22, margin: '0 0 14px' }}>
          ✓ Contrato verificado
        </h1>

        <div style={{ display: 'grid', gap: 10, fontSize: 14 }}>
          <Linha rotulo="Imóvel" valor={data.imovel} />
          <Linha rotulo="Cidade" valor={data.cidade} />
          <div>
            <span style={{ opacity: 0.6 }}>Status: </span>
            <span style={{ background: stColor, color: '#fff', padding: '2px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700 }}>
              {stLabel}
            </span>
          </div>
          <Linha rotulo="Assinado em" valor={fmtData(data.assinado_em)} />
        </div>

        <div style={{ marginTop: 18 }}>
          <div style={{ textTransform: 'uppercase', letterSpacing: 0.8, fontSize: 12, color: DOURADO, marginBottom: 8 }}>
            Signatários
          </div>
          {(data.signatarios || []).map((s, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 8,
                                   padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.08)', fontSize: 14 }}>
              <span>{s.nome} <span style={{ opacity: 0.6 }}>— {PAPEL_LABEL[s.papel] || s.papel}</span></span>
              <span style={{ color: s.status === 'aceito' ? '#86efac' : '#fbbf24' }}>
                {s.status === 'aceito' ? `aceito · ${fmtData(s.data_aceite)}` : 'pendente'}
              </span>
            </div>
          ))}
        </div>

        {data.pdf_final_url && (
          <a href={data.pdf_final_url} target="_blank" rel="noreferrer"
             style={{ display: 'block', textAlign: 'center', marginTop: 18, padding: 14, borderRadius: 12,
                      background: DOURADO, color: VERDE, fontWeight: 700, textDecoration: 'none' }}>
            ⬇ Baixar PDF assinado
          </a>
        )}

        <div style={{ marginTop: 16, opacity: 0.6, fontSize: 11 }}>
          <span style={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>Hash SHA-256:</span>
          <div style={{ wordBreak: 'break-all', fontFamily: 'monospace', marginTop: 4 }}>{data.hash_documento}</div>
        </div>
      </Card>
    </Shell>
  );
}

const Linha = ({ rotulo, valor }) => (
  <div><span style={{ opacity: 0.6 }}>{rotulo}: </span>{valor}</div>
);
