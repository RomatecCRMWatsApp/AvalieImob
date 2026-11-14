// @module dashboard/AdminResumo — indicadores administrativos (só admin/owner/ceo).
// Mesma consulta e mesma regra do bloco que ficava dentro do hero (adminAPI.listUsers).
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { adminAPI } from '../../lib/api';

const isAdminRole = (role) => ['admin', 'owner', 'ceo'].includes(String(role || '').toLowerCase());

export default function AdminResumo() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const admin = isAdminRole(user?.role);

  useEffect(() => {
    if (!admin) return undefined;
    let vivo = true;
    adminAPI.listUsers()
      .then((us) => {
        const arr = Array.isArray(us) ? us : [];
        if (vivo) setData({ total: arr.length, ativas: arr.filter((u) => u.plan_status === 'active').length });
      })
      .catch(() => {});
    return () => { vivo = false; };
  }, [admin]);

  if (!admin || !data) return null;

  const Item = ({ Icon, valor, label }) => (
    <Link to="/dashboard/admin/usuarios" className="av-card flex items-center gap-3 px-4 py-3 min-h-[44px]" style={{ textDecoration: 'none', color: 'inherit' }}>
      <Icon size={18} aria-hidden="true" style={{ color: 'var(--av-brand)' }} />
      <span className="av-metric-value" style={{ fontSize: 20 }}>{valor.toLocaleString('pt-BR')}</span>
      <span style={{ fontSize: 13, color: 'var(--av-text-secondary)' }}>{label}</span>
    </Link>
  );

  return (
    <section aria-labelledby="av-admin" className="flex flex-wrap items-center gap-3">
      <h2 id="av-admin" style={{ fontSize: 13, fontWeight: 600, color: 'var(--av-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        Administração
      </h2>
      <Item Icon={Users} valor={data.total} label="usuários cadastrados" />
      <Item Icon={CheckCircle2} valor={data.ativas} label="assinaturas ativas" />
    </section>
  );
}
