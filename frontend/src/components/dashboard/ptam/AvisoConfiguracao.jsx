// @component ptam/AvisoConfiguracao — avisa (sem impedir) que o laudo sairá com
// campos vazios por falta de configuração do perfil.
//
// Regra do produto: NUNCA bloquear a geração. O usuário decide — só não pode
// ser pego de surpresa depois, ao abrir o PDF e ver a assinatura em branco.
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, X } from 'lucide-react';

const GREEN = '#0C3320';
const GOLD = '#C9A84C';

/** Busca os essenciais faltantes. Falha na checagem NUNCA impede o download. */
export const faltandoEssenciais = async (perfilAPI) => {
  try {
    const c = await perfilAPI.completude();
    return (c.itens || []).filter((i) => i.essencial && !i.ok);
  } catch {
    return [];
  }
};

const AvisoConfiguracao = ({ itens, onProsseguir, onFechar }) => {
  const nav = useNavigate();
  if (!itens || !itens.length) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 relative">
        <button onClick={onFechar} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: GOLD }} />
          <div>
            <h3 className="font-display text-lg" style={{ color: GREEN }}>
              O laudo vai sair com campos vazios
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Faltam {itens.length} item(ns) na sua configuração:
            </p>
          </div>
        </div>

        <ul className="mt-4 space-y-2">
          {itens.map((i) => (
            <li key={i.chave} className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2">
              <div className="text-sm font-semibold text-amber-900">{i.titulo}</div>
              <div className="text-xs text-amber-700 mt-0.5">{i.impacto}</div>
            </li>
          ))}
        </ul>

        <div className="mt-5 flex flex-col sm:flex-row gap-2">
          <button
            onClick={() => nav('/dashboard/configuracao-inicial')}
            className="flex-1 px-4 py-2.5 rounded-lg text-white text-sm"
            style={{ background: GREEN }}
          >
            Preencher agora
          </button>
          <button
            onClick={onProsseguir}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 text-sm text-gray-700"
          >
            Gerar assim mesmo
          </button>
        </div>
      </div>
    </div>
  );
};

export default AvisoConfiguracao;
