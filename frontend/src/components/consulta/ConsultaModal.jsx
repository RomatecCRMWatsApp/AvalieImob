import { useCallback, useEffect, useState } from 'react';
import { consultaAPI } from '../../lib/api';
import './ConsultaModal.css';

function mascaraCNPJ(v) {
  return v
    .replace(/\D/g, '')
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2')
    .slice(0, 18);
}

function mascaraCPF(v) {
  return v
    .replace(/\D/g, '')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/(\d{3})\.(\d{3})\.(\d{3})(\d)/, '$1.$2.$3-$4')
    .slice(0, 14);
}

function formatarMoeda(v) {
  return Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function StatusBadge({ situacao }) {
  const ativa = (situacao || '').toUpperCase().includes('ATIVA');
  return (
    <span className={`status-badge ${ativa ? 'ativa' : 'inativa'}`}>
      {situacao || '—'}
    </span>
  );
}

// Barra de ações (visualizar / baixar / enviar) reutilizada nas abas CNPJ e CPF.
function AcoesConsulta({ tipo, dados }) {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [enviarOpen, setEnviarOpen] = useState(false);
  const [phone, setPhone] = useState('');
  const [chatId, setChatId] = useState('');
  const [envLoading, setEnvLoading] = useState('');
  const [envMsg, setEnvMsg] = useState(null);

  const ehCnpj = tipo === 'cnpj';
  const apiPdf = ehCnpj ? consultaAPI.pdf : consultaAPI.cpfPdf;
  const apiWpp = ehCnpj ? consultaAPI.whatsapp : consultaAPI.cpfWhatsapp;
  const apiTg = ehCnpj ? consultaAPI.telegram : consultaAPI.cpfTelegram;
  const docNum = ((ehCnpj ? dados.cnpj : dados.cpf) || '').replace(/\D/g, '') || 'consulta';
  const fileBase = ehCnpj ? 'CNPJ' : 'CPF';

  const blobUrl = async () => URL.createObjectURL(await apiPdf(dados));

  const visualizar = async () => {
    setPdfLoading(true);
    setEnvMsg(null);
    try {
      const url = await blobUrl();
      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      setEnvMsg({ tipo: 'erro', texto: 'Erro ao gerar o PDF.' });
    } finally {
      setPdfLoading(false);
    }
  };

  const baixar = async () => {
    setPdfLoading(true);
    setEnvMsg(null);
    try {
      const url = await blobUrl();
      const a = document.createElement('a');
      a.href = url;
      a.download = `${fileBase}_${docNum}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      setEnvMsg({ tipo: 'erro', texto: 'Erro ao baixar o PDF.' });
    } finally {
      setPdfLoading(false);
    }
  };

  const enviarWhatsApp = async () => {
    const tel = phone.replace(/\D/g, '');
    if (tel.length < 10) {
      setEnvMsg({ tipo: 'erro', texto: 'Informe o telefone com DDD (ex: 99 99999-9999).' });
      return;
    }
    setEnvLoading('whatsapp');
    setEnvMsg(null);
    try {
      await apiWpp(dados, tel);
      setEnvMsg({ tipo: 'ok', texto: 'PDF enviado por WhatsApp ✓' });
    } catch (err) {
      setEnvMsg({ tipo: 'erro', texto: err?.response?.data?.detail || 'Falha ao enviar por WhatsApp.' });
    } finally {
      setEnvLoading('');
    }
  };

  const enviarTelegram = async () => {
    setEnvLoading('telegram');
    setEnvMsg(null);
    try {
      await apiTg(dados, chatId);
      setEnvMsg({ tipo: 'ok', texto: 'PDF enviado por Telegram ✓' });
    } catch (err) {
      setEnvMsg({ tipo: 'erro', texto: err?.response?.data?.detail || 'Falha ao enviar por Telegram.' });
    } finally {
      setEnvLoading('');
    }
  };

  return (
    <>
      <div className="consulta-acoes">
        <button className="acao-btn" onClick={visualizar} disabled={pdfLoading}>
          {pdfLoading ? <span className="consulta-spinner dark" /> : '👁'} Visualizar
        </button>
        <button className="acao-btn" onClick={baixar} disabled={pdfLoading}>
          ⬇ Baixar PDF
        </button>
        <button
          className={`acao-btn enviar ${enviarOpen ? 'aberto' : ''}`}
          onClick={() => setEnviarOpen((o) => !o)}
        >
          📤 Enviar
        </button>
      </div>

      {enviarOpen && (
        <div className="consulta-enviar">
          <div className="enviar-linha">
            <input
              type="text"
              placeholder="WhatsApp: DDD + número"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <button className="enviar-btn wpp" onClick={enviarWhatsApp} disabled={envLoading === 'whatsapp'}>
              {envLoading === 'whatsapp' ? '...' : 'WhatsApp'}
            </button>
          </div>
          <div className="enviar-linha">
            <input
              type="text"
              placeholder="Telegram: chat_id (vazio = padrão)"
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
            />
            <button className="enviar-btn tg" onClick={enviarTelegram} disabled={envLoading === 'telegram'}>
              {envLoading === 'telegram' ? '...' : 'Telegram'}
            </button>
          </div>
          <div className="enviar-nota">
            Usa as integrações do seu perfil (Configurações → Integrações).
          </div>
        </div>
      )}

      {envMsg && <div className={`enviar-msg ${envMsg.tipo}`}>{envMsg.texto}</div>}
    </>
  );
}

export default function ConsultaModal({ onClose }) {
  const [aba, setAba] = useState('cnpj');

  // CNPJ
  const [cnpj, setCNPJ] = useState('');
  const [loadingCNPJ, setLoadingCNPJ] = useState(false);
  const [resultadoCNPJ, setResultadoCNPJ] = useState(null);
  const [erroCNPJ, setErroCNPJ] = useState('');

  // CPF
  const [cpf, setCPF] = useState('');
  const [dataNasc, setDataNasc] = useState('');
  const [loadingCPF, setLoadingCPF] = useState(false);
  const [resultadoCPF, setResultadoCPF] = useState(null);
  const [erroCPF, setErroCPF] = useState('');

  // Fechar com ESC
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const consultarCNPJ = useCallback(async () => {
    const num = cnpj.replace(/\D/g, '');
    if (num.length !== 14) {
      setErroCNPJ('CNPJ deve ter 14 dígitos.');
      return;
    }
    setLoadingCNPJ(true);
    setErroCNPJ('');
    setResultadoCNPJ(null);
    try {
      const data = await consultaAPI.cnpj(num);
      setResultadoCNPJ(data);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 400) setErroCNPJ('CNPJ inválido.');
      else if (status === 404) setErroCNPJ('CNPJ não encontrado.');
      else setErroCNPJ(err?.response?.data?.detail || 'Erro de conexão. Tente novamente.');
    } finally {
      setLoadingCNPJ(false);
    }
  }, [cnpj]);

  const consultarCPF = useCallback(async () => {
    const num = cpf.replace(/\D/g, '');
    if (num.length !== 11) {
      setErroCPF('CPF deve ter 11 dígitos.');
      return;
    }
    setLoadingCPF(true);
    setErroCPF('');
    setResultadoCPF(null);
    try {
      const data = await consultaAPI.validarCpf(num, dataNasc || undefined);
      setResultadoCPF(data);
    } catch (err) {
      setErroCPF(err?.response?.data?.detail || 'Erro de conexão. Tente novamente.');
    } finally {
      setLoadingCPF(false);
    }
  }, [cpf, dataNasc]);

  return (
    <div
      className="consulta-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="consulta-modal" role="dialog" aria-modal="true" aria-label="Consulta CNPJ/CPF">
        {/* Header */}
        <div className="consulta-header">
          <div className="consulta-header-title">
            <span className="consulta-header-icon">🔍</span>
            <span>Consulta Rápida</span>
          </div>
          <button className="consulta-close" onClick={onClose} aria-label="Fechar">✕</button>
        </div>

        {/* Abas */}
        <div className="consulta-abas">
          <button
            className={`consulta-aba ${aba === 'cnpj' ? 'ativa' : ''}`}
            onClick={() => { setAba('cnpj'); setResultadoCNPJ(null); setErroCNPJ(''); }}
          >
            🏢 CNPJ
          </button>
          <button
            className={`consulta-aba ${aba === 'cpf' ? 'ativa' : ''}`}
            onClick={() => { setAba('cpf'); setResultadoCPF(null); setErroCPF(''); }}
          >
            👤 CPF
          </button>
        </div>

        {/* Conteúdo */}
        <div className="consulta-body">
          {aba === 'cnpj' && (
            <div className="consulta-form">
              <div className="consulta-input-group">
                <label>CNPJ</label>
                <div className="consulta-input-row">
                  <input
                    type="text"
                    placeholder="00.000.000/0000-00"
                    value={cnpj}
                    onChange={(e) => setCNPJ(mascaraCNPJ(e.target.value))}
                    onKeyDown={(e) => e.key === 'Enter' && consultarCNPJ()}
                    maxLength={18}
                    autoFocus
                  />
                  <button className="consulta-btn-buscar" onClick={consultarCNPJ} disabled={loadingCNPJ}>
                    {loadingCNPJ ? <span className="consulta-spinner" /> : 'Buscar'}
                  </button>
                </div>
              </div>

              {erroCNPJ && <div className="consulta-erro">{erroCNPJ}</div>}

              {resultadoCNPJ && (
                <>
                <div className="consulta-resultado">
                  <div className="resultado-header">
                    <div>
                      <div className="resultado-razao">{resultadoCNPJ.razao_social}</div>
                      {resultadoCNPJ.nome_fantasia && (
                        <div className="resultado-fantasia">"{resultadoCNPJ.nome_fantasia}"</div>
                      )}
                      <div className="resultado-cnpj-num">{resultadoCNPJ.cnpj}</div>
                    </div>
                    <StatusBadge situacao={resultadoCNPJ.situacao} />
                  </div>

                  <div className="resultado-grid">
                    <div className="resultado-item">
                      <span className="resultado-label">Abertura</span>
                      <span>{resultadoCNPJ.data_abertura || '—'}</span>
                    </div>
                    <div className="resultado-item">
                      <span className="resultado-label">Porte</span>
                      <span>{resultadoCNPJ.porte || '—'}</span>
                    </div>
                    <div className="resultado-item">
                      <span className="resultado-label">Capital Social</span>
                      <span>{resultadoCNPJ.capital_social ? formatarMoeda(resultadoCNPJ.capital_social) : '—'}</span>
                    </div>
                    <div className="resultado-item">
                      <span className="resultado-label">Natureza Jurídica</span>
                      <span>{resultadoCNPJ.natureza_juridica || '—'}</span>
                    </div>
                    <div className="resultado-item resultado-full">
                      <span className="resultado-label">Atividade Principal</span>
                      <span>{resultadoCNPJ.atividade_principal || '—'}</span>
                    </div>
                    <div className="resultado-item resultado-full">
                      <span className="resultado-label">Endereço</span>
                      <span>
                        {[
                          resultadoCNPJ.logradouro,
                          resultadoCNPJ.numero,
                          resultadoCNPJ.bairro,
                          resultadoCNPJ.municipio,
                          resultadoCNPJ.uf,
                          resultadoCNPJ.cep,
                        ].filter(Boolean).join(', ') || '—'}
                      </span>
                    </div>
                    {resultadoCNPJ.telefone && (
                      <div className="resultado-item">
                        <span className="resultado-label">Telefone</span>
                        <span>{resultadoCNPJ.telefone}</span>
                      </div>
                    )}
                    {resultadoCNPJ.email && (
                      <div className="resultado-item">
                        <span className="resultado-label">E-mail</span>
                        <span>{resultadoCNPJ.email}</span>
                      </div>
                    )}
                  </div>

                  <div className="resultado-fonte">
                    Fonte:{' '}
                    {resultadoCNPJ.fonte === 'prospectabr'
                      ? 'ProspectaBR (base local)'
                      : resultadoCNPJ.fonte === 'cnpjws'
                      ? 'CNPJ.ws'
                      : 'ReceitaWS'}{' '}
                    — Receita Federal
                  </div>
                </div>

                <AcoesConsulta tipo="cnpj" dados={resultadoCNPJ} />
                </>
              )}
            </div>
          )}

          {aba === 'cpf' && (
            <div className="consulta-form">
              <div className="consulta-input-group">
                <label>CPF</label>
                <div className="consulta-input-row">
                  <input
                    type="text"
                    placeholder="000.000.000-00"
                    value={cpf}
                    onChange={(e) => setCPF(mascaraCPF(e.target.value))}
                    onKeyDown={(e) => e.key === 'Enter' && consultarCPF()}
                    maxLength={14}
                    autoFocus
                  />
                  <button className="consulta-btn-buscar" onClick={consultarCPF} disabled={loadingCPF}>
                    {loadingCPF ? <span className="consulta-spinner" /> : 'Validar'}
                  </button>
                </div>
              </div>

              <div className="consulta-input-group">
                <label>Data de Nascimento <span className="opcional">(opcional)</span></label>
                <input
                  type="date"
                  value={dataNasc}
                  onChange={(e) => setDataNasc(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>

              {erroCPF && <div className="consulta-erro">{erroCPF}</div>}

              {resultadoCPF && (
                <>
                <div className="consulta-resultado">
                  <div className="resultado-header">
                    <div>
                      <div className="resultado-razao">{resultadoCPF.cpf}</div>
                    </div>
                    <span className={`status-badge ${resultadoCPF.valido ? 'ativa' : 'inativa'}`}>
                      {resultadoCPF.valido ? '✓ Válido' : '✗ Inválido'}
                    </span>
                  </div>

                  <div className="resultado-grid">
                    <div className="resultado-item resultado-full">
                      <span className="resultado-label">Situação</span>
                      <span>{resultadoCPF.mensagem}</span>
                    </div>
                    {resultadoCPF.data_nascimento_informada && (
                      <div className="resultado-item">
                        <span className="resultado-label">Data de Nascimento</span>
                        <span>
                          {new Date(resultadoCPF.data_nascimento_informada + 'T00:00:00').toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                    )}
                    <div className="resultado-item resultado-full">
                      <span className="resultado-label">Observação</span>
                      <span>{resultadoCPF.observacao}</span>
                    </div>
                  </div>
                </div>

                <AcoesConsulta tipo="cpf" dados={resultadoCPF} />
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
