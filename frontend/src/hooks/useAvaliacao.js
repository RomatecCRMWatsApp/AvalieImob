// Hook único da Calculadora pública — estado, validação e chamadas. Reusado
// pelas 3 apresentações (Clássica/Portal/Premium). Usa avaliacaoPublicaAPI
// (axios), NÃO import.meta.env/fetch (convenção CRA do AvalieImob).
import { useState } from 'react';
import { maskFone } from '../lib/format';
import { avaliacaoPublicaAPI } from '../lib/api';

export function useAvaliacao() {
  const [step, setStep] = useState('form'); // form | result | done
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState('');
  const [estimativa, setEstimativa] = useState(null);

  const [imovel, setImovel] = useState({
    uf: 'MA', cidade: '', tipo: 'apartamento', area: '',
    quartos: '', vagas: '', padrao: 'medio', conservacao: 'bom',
  });
  const [contato, setContato] = useState({ nome: '', whatsapp: '', email: '' });

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
      setErro(err?.response?.data?.detail || 'Não foi possível calcular agora.');
    } finally {
      setLoading(false);
    }
  }

  async function enviarLead(e) {
    e?.preventDefault();
    setErro('');
    if (contato.nome.trim().length < 2) return setErro('Informe seu nome.');
    if (contato.whatsapp.replace(/\D/g, '').length < 10) return setErro('Informe um WhatsApp válido.');
    setLoading(true);
    try {
      await avaliacaoPublicaAPI.lead({
        nome: contato.nome.trim(),
        whatsapp: contato.whatsapp,
        email: contato.email || null,
        imovel: payload(),
      });
      setStep('done');
    } catch (err) {
      setErro(err?.response?.data?.detail || 'Não foi possível enviar. Tente novamente.');
    } finally {
      setLoading(false);
    }
  }

  const reset = () => { setStep('form'); setEstimativa(null); setErro(''); };

  return {
    step, loading, erro, estimativa, imovel, contato,
    setCampo, setContatoCampo, calcular, enviarLead, reset,
  };
}
