// @module utils/datasServidor — Parsing de datas vindas do backend (UTC naïve).
// O backend grava datetime.utcnow() e serializa SEM timezone (ex: "2026-06-07T16:05:00").
// new Date() interpretaria isso como horário LOCAL → erro de +3h em Açailândia (UTC-3).
// Aqui assumimos UTC quando não há fuso explícito e convertemos para o local do usuário.

export function parseServerDate(iso) {
  if (!iso) return null;
  if (iso instanceof Date) return Number.isNaN(iso.getTime()) ? null : iso;
  const s = String(iso).trim();
  if (!s) return null;
  const temTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(s);
  const d = new Date(temTz ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

// "07/06/2026 · 16:05"
export function fmtDataHora(iso) {
  const d = parseServerDate(iso);
  if (!d) return '';
  return `${d.toLocaleDateString('pt-BR')} · ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
}

// "07/06 · 16:05" (curta, para os círculos)
export function fmtDataHoraCurta(iso) {
  const d = parseServerDate(iso);
  if (!d) return '';
  return `${d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} · ${d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}`;
}
