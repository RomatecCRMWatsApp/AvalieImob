/**
 * @module pages/AceiteContrato — Página pública de aceite eletrônico (link/WhatsApp)
 * Rota: /aceite/:token (fora do guard de autenticação)
 * Consome /api/publico/contratos-exclusividade/aceite/:token
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { contratosExclusividadeAPI } from '../lib/api';

const VERDE = '#0C3320';
const DOURADO = '#C9A84C';

const brl = (v) =>
  'R$ ' + Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const Shell = ({ children }) => (
  <div style={{ minHeight: '100vh', background: VERDE, color: '#f4efe2' }}
       className="flex flex-col items-center px-4 py-8">
    <div style={{ maxWidth: 720, width: '100%' }}>
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

const Card = ({ children, style }) => (
  <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(201,168,76,0.25)',
                borderRadius: 16, padding: 22, marginBottom: 16, ...style }}>
    {children}
  </div>
);

const Titulo = ({ children }) => (
  <h1 style={{ fontFamily: '"Playfair Display", Georgia, serif', color: DOURADO,
               fontSize: 22, fontWeight: 700, margin: '0 0 10px' }}>{children}</h1>
);

const LegalFooter = ({ hash }) => {
  const [copiado, setCopiado] = useState(false);
  const copiar = () => {
    navigator.clipboard?.writeText(hash || '').then(() => {
      setCopiado(true); setTimeout(() => setCopiado(false), 1500);
    });
  };
  return (
    <div style={{ opacity: 0.7, fontSize: 11.5, lineHeight: 1.6, marginTop: 8 }}>
      {hash && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>Hash SHA-256: </span>
          <code style={{ fontSize: 11 }}>{hash.slice(0, 24)}…</code>
          <button onClick={copiar} style={{ marginLeft: 8, color: DOURADO, background: 'none', border: 'none', cursor: 'pointer' }}>
            {copiado ? 'copiado ✓' : 'copiar'}
          </button>
        </div>
      )}
      Aceite eletrônico com validade jurídica nos termos da MP 2.200-2/2001 (art. 10, §2º),
      Lei 14.063/2020, Código Civil art. 726 e Resolução COFECI 458/1995.
    </div>
  );
};

const PAPEL_LABEL = { proprietario: 'Proprietário(a)', conjuge: 'Cônjuge/Companheiro(a)' };

export default function AceiteContrato() {
  const { token } = useParams();
  const [estado, setEstado] = useState('loading'); // loading | ok | erro | enviado
  const [erro, setErro] = useState(null);           // {status, msg}
  const [data, setData] = useState(null);
  const [scrolledEnd, setScrolledEnd] = useState(false);
  const [concordo, setConcordo] = useState(false);
  const [nome, setNome] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    let vivo = true;
    contratosExclusividadeAPI.obterPorToken(token)
      .then((d) => { if (!vivo) return; setData(d); setEstado(d.signatario?.status === 'aceito' ? 'ja_aceito' : 'ok'); })
      .catch((e) => {
        if (!vivo) return;
        const status = e.response?.status;
        const msg = e.response?.data?.detail || 'Não foi possível carregar o contrato.';
        setErro({ status, msg }); setEstado('erro');
      });
    return () => { vivo = false; };
  }, [token]);

  const onScroll = useCallback((e) => {
    const el = e.target;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) setScrolledEnd(true);
  }, []);

  const podeAceitar = concordo && nome.trim().length > 2 && scrolledEnd && !enviando;

  const confirmar = async () => {
    setEnviando(true);
    try {
      const r = await contratosExclusividadeAPI.confirmarAceite(token, { concordo: true, nome_digitado: nome.trim() });
      setResultado(r); setEstado('enviado');
    } catch (e) {
      const msg = e.response?.data?.detail || 'Não foi possível registrar o aceite.';
      alert(msg);
      if (e.response?.status === 409) setEstado('ja_aceito');
    } finally {
      setEnviando(false);
    }
  };

  if (estado === 'loading') {
    return <Shell><Card><p>Carregando contrato…</p></Card></Shell>;
  }

  if (estado === 'erro') {
    const titulo = erro?.status === 410 ? 'Link indisponível' : 'Link inválido';
    return (
      <Shell>
        <Card>
          <Titulo>{titulo}</Titulo>
          <p style={{ opacity: 0.85 }}>{erro?.msg}</p>
          <p style={{ opacity: 0.6, fontSize: 13, marginTop: 8 }}>
            Em caso de dúvida, solicite um novo link ao corretor responsável.
          </p>
        </Card>
      </Shell>
    );
  }

  if (estado === 'ja_aceito') {
    return (
      <Shell>
        <Card>
          <Titulo>Aceite já registrado</Titulo>
          <p style={{ opacity: 0.9 }}>
            Você já confirmou o aceite deste contrato como <b>{PAPEL_LABEL[data?.signatario?.papel] || ''}</b>.
            O documento final será (ou já foi) enviado ao seu WhatsApp.
          </p>
        </Card>
        <LegalFooter hash={data?.hash_documento} />
      </Shell>
    );
  }

  if (estado === 'enviado') {
    const todos = resultado?.todos_assinaram;
    return (
      <Shell>
        <Card>
          <Titulo>{todos ? '✅ Contrato assinado por todas as partes!' : '✅ Aceite registrado!'}</Titulo>
          <p style={{ opacity: 0.9 }}>
            {todos
              ? 'O PDF final foi enviado ao seu WhatsApp. Obrigado!'
              : 'Aguardando a assinatura do(s) demais signatário(s). Você receberá o PDF final no WhatsApp assim que todos assinarem.'}
          </p>
          {data?.hash_documento && (
            <a href={`/verificar/${data.hash_documento}`} target="_blank" rel="noreferrer"
               style={{ color: DOURADO, display: 'inline-block', marginTop: 10 }}>
              Verificar autenticidade →
            </a>
          )}
        </Card>
        <LegalFooter hash={data?.hash_documento} />
      </Shell>
    );
  }

  // estado === 'ok'
  const im = data.imovel || {};
  return (
    <Shell>
      <Card>
        <Titulo>Assinatura eletrônica do contrato</Titulo>
        <p style={{ opacity: 0.85, fontSize: 14 }}>
          Você está assinando como <b style={{ color: DOURADO }}>{PAPEL_LABEL[data.signatario?.papel] || data.signatario?.papel}</b>.
        </p>
        <div style={{ marginTop: 12, display: 'grid', gap: 6, fontSize: 14 }}>
          <div><span style={{ opacity: 0.6 }}>Imóvel: </span>{im.descricao}</div>
          <div><span style={{ opacity: 0.6 }}>Endereço: </span>{[im.endereco, im.bairro, im.cidade, im.uf].filter(Boolean).join(', ')}</div>
          <div><span style={{ opacity: 0.6 }}>Valor anunciado: </span>{brl(im.valor_anunciado)}</div>
          <div><span style={{ opacity: 0.6 }}>Comissão: </span>{String(data.comissao_percentual).replace('.', ',')}%</div>
          <div><span style={{ opacity: 0.6 }}>Prazo de exclusividade: </span>{data.prazo_meses} meses</div>
        </div>
      </Card>

      <Card>
        <div style={{ textTransform: 'uppercase', letterSpacing: 0.8, fontSize: 12, color: DOURADO, marginBottom: 8 }}>
          Leia o contrato integralmente
        </div>
        <div ref={scrollRef} onScroll={onScroll}
             style={{ maxHeight: 320, overflowY: 'auto', whiteSpace: 'pre-wrap',
                      fontFamily: 'Georgia, serif', fontSize: 13.5, lineHeight: 1.6,
                      background: 'rgba(0,0,0,0.18)', border: '1px solid rgba(201,168,76,0.2)',
                      borderRadius: 10, padding: 16 }}>
          {data.texto_contrato}
        </div>
        {!scrolledEnd && (
          <div style={{ opacity: 0.6, fontSize: 12, marginTop: 8 }}>
            ↓ Role até o final do contrato para habilitar o aceite.
          </div>
        )}
      </Card>

      <Card>
        <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer', fontSize: 14 }}>
          <input type="checkbox" checked={concordo} onChange={(e) => setConcordo(e.target.checked)}
                 style={{ marginTop: 3, width: 18, height: 18, accentColor: DOURADO }} />
          <span>Li e concordo integralmente com os termos do contrato acima.</span>
        </label>
        <div style={{ marginTop: 14 }}>
          <label style={{ display: 'block', fontSize: 13, opacity: 0.8, marginBottom: 6 }}>
            Digite seu nome completo para confirmar
          </label>
          <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome completo"
                 style={{ width: '100%', padding: '12px 14px', borderRadius: 10, border: '1px solid rgba(201,168,76,0.35)',
                          background: 'rgba(0,0,0,0.2)', color: '#fff', fontSize: 15 }} />
        </div>
        <button onClick={confirmar} disabled={!podeAceitar}
                style={{ width: '100%', marginTop: 16, padding: 16, borderRadius: 12, border: 'none',
                         fontSize: 16, fontWeight: 700, cursor: podeAceitar ? 'pointer' : 'not-allowed',
                         background: podeAceitar ? DOURADO : 'rgba(201,168,76,0.3)',
                         color: podeAceitar ? VERDE : 'rgba(255,255,255,0.5)' }}>
          {enviando ? 'Registrando…' : 'ACEITO E CONCORDO'}
        </button>
      </Card>

      <LegalFooter hash={data.hash_documento} />
    </Shell>
  );
}
