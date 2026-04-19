import React from "react";
import { trpc } from "../../lib/trpc";
import { Users, Building2, FileText, ClipboardList } from "lucide-react";

export function StatsCards() {
  const clientes = trpc.cliente.listar.useQuery();
  const imoveis = trpc.imovel.listar.useQuery({ pagina: 1, limite: 1000 });
  const avaliacoes = trpc.avaliacao.listar.useQuery({ pagina: 1, limite: 1000 });
  const ptams = trpc.ptam.listar.useQuery();

  const stats = [
    {
      label: "Clientes",
      value: clientes.data?.length ?? 0,
      icon: Users,
      loading: clientes.isLoading,
      color: "text-blue-400",
      bg: "bg-blue-700/20",
    },
    {
      label: "Imóveis",
      value: imoveis.data?.imoveis?.length ?? 0,
      icon: Building2,
      loading: imoveis.isLoading,
      color: "text-yellow-400",
      bg: "bg-yellow-700/20",
    },
    {
      label: "Avaliações",
      value: avaliacoes.data?.avaliacoes?.length ?? 0,
      icon: ClipboardList,
      loading: avaliacoes.isLoading,
      color: "text-purple-400",
      bg: "bg-purple-700/20",
    },
    {
      label: "PTAMs Emitidos",
      value: ptams.data?.length ?? 0,
      icon: FileText,
      loading: ptams.isLoading,
      color: "text-green-400",
      bg: "bg-green-700/20",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-gray-900 border border-gray-700/40 rounded-xl p-5 hover:border-gray-600/60 transition-colors"
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-gray-400 text-sm">{stat.label}</p>
            <div className={`w-9 h-9 ${stat.bg} rounded-lg flex items-center justify-center`}>
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">
            {stat.loading ? (
              <span className="inline-block w-8 h-8 bg-gray-700 rounded animate-pulse" />
            ) : (
              stat.value
            )}
          </p>
        </div>
      ))}
    </div>
  );
}
