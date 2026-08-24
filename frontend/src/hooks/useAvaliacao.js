// Hook único da Calculadora pública — estado, validação e chamadas. Reusado
// pelas 3 apresentações (Clássica/Portal/Premium). Usa avaliacaoPublicaAPI
// (axios), NÃO import.meta.env/fetch (convenção CRA do AvalieImob).
import { useState } from 'react';
import { maskFone } from '../lib/format';
import { avaliacaoPublicaAPI } from '../lib/api';

// Extrai SEMPRE uma string de erro. O FastAPI devolve `detail` como ARRAY de objetos
// em validação (422); renderizar isso como filho React quebra a tela (React #31).
function msgErro(err, fallback) {
  const d = err?.response?.data?.detail;
  if (Array.isArray(d)) return d[0]?.msg || fallback;
  if (typeof d === 'string') return d;
  if (d && typeof d === 'object') return d.msg || fallback;
  return fallback;
}

// Marcação de origem capturada pelo App.js quando a página abre com ?utm_*.
// Sobrevive à navegação dentro do site (sessionStorage), então o lead sabe dizer
// de qual folder, QR ou link ele veio.
function utmSalva() {
  try {
    const d = JSON.parse(sessionStorage.getItem('utm_data') || '{}');
    return {
      utm_source: d.utm_source || null,
      utm_medium: d.utm_medium || null,
      utm_campaign: d.utm_campaign || null,
    };
  } catch { return {}; }
}

export function useAvaliacao(origem = 'calculadora_publica') {
  const [step, setStep] = useState('form'); // form | result | done
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [estimativa, setEstimativa] = useState(null);

  const [imovel, setImovel] = useState({
    uf: 'MA', cidade: '', tipo: 'apartamento', area: '',
    quartos: '', vagas: '', padrao: 'medio', conservacao: 'bom',
  });
  const [contato, setContato] = useState({ nome: '', whatsapp: '', email: '' });
  const [consentimento, setConsentimento] = useState(false);
  const [hp, setHp] = useState(''); // honeypot anti-bot (deve ficar vazio)

  const setCampo = (c, v) => setImovel((p) => ({ ...p, [c]: v }));
  const setContatoCampo = (c, v) =>
    setContato((p) => ({ ...p, [c]: c === 'whatsapp' ? maskFone(v) : v }));

  const payload = () => ({
    uf: imovel.uf,
    cidade: imovel.cidade.trim(),
    tipo: imovel.tipo,
    area: Number(imovel.area),
    quartos: Number(imovel.quartos || 0),
    vagas: Number(imovel.vagas || 0),
    padrao: imovel.padrao,
    conservacao: imovel.conservacao,
  });

  async function calcular(e) {
    e?.preventDefault();
    setErro('');
    if (!imovel.cidade.trim()) return setErro('Informe a cidade.');
    if (!imovel.area || Number(imovel.area) <= 0) return setErro('Informe a área em m².');
    setLoading(true);
    try {
      const data = await avaliacaoPublicaAPI.estimar(payload());
      setEstimativa(data);
      setStep('result');
    } catch (err) {
      setErro(msgErro(err, 'Não foi possível calcular agora.'));
    } finally {
      setLoading(false);
    }
  }

  async function enviarLead(e) {
    e?.preventDefault();
    setErro('');
    if (contato.nome.trim().length < 2) return setErro('Informe seu nome.');
    if (contato.whatsapp.replace(/\D/g, '').length < 10) return setErro('Informe um WhatsApp válido.');
    if (!consentimento) return setErro('É necessário autorizar o tratamento dos seus dados (LGPD).');
    setLoading(true);
    try {
      await avaliacaoPublicaAPI.lead({
        nome: contato.nome.trim(),
        whatsapp: contato.whatsapp,
        email: contato.email || null,
        imovel: payload(),
        origem,
        // De qual peça de divulgação o visitante veio (App.js guarda no
        // sessionStorage assim que a página abre com ?utm_*).
        ...utmSalva(),
        consentimento,
        website: hp,
      });
      setStep('done');
    } catch (err) {
      setErro(msgErro(err, 'Não foi possível enviar. Tente novamente.'));
    } finally {
      setLoading(false);
    }
  }

  const reset = () => { setStep('form'); setEstimativa(null); setErro(''); };

  return {
    step, loading, erro, estimativa, imovel, contato,
    consentimento, setConsentimento, hp, setHp,
    setCampo, setContatoCampo, calcular, enviarLead, reset,
  };
}
