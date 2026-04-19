import React from "react";
import { trpc } from "../../lib/trpc";
import { Building2, Mail, Phone, MapPin, FileText } from "lucide-react";

interface ClienteDetailProps {
  id: string;
}

export function ClienteDetail({ id }: ClienteDetailProps) {
  const { data, isLoading } = trpc.cliente.obter.useQuery({ id });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-10 bg-gray-800 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data) return <p className="text-gray-400">Cliente não encontrado.</p>;

  const row = (label: string, value: string | null | undefined, Icon?: React.FC<{ className?: string }>) => (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      {Icon && <Icon className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />}
      <div className={Icon ? "" : "pl-7"}>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-sm text-white mt-0.5">{value || "—"}</p>
      </div>
    </div>
  );

  return (
    <div className="space-y-1">
      {row("Razão Social", data.razao_social, Building2)}
      {row("CNPJ/CPF", data.cnpj_cpf, FileText)}
      {row("Email", data.email, Mail)}
      {row("Telefone", data.telefone, Phone)}
      {row(
        "Endereço",
        [data.endereco, data.cidade, data.estado].filter(Boolean).join(", "),
        MapPin,
      )}
      {row("CEP", data.cep)}
      {row("Contato", data.contato)}
      {data.obs && (
        <div className="mt-3 p-3 bg-gray-800/50 rounded-lg">
          <p className="text-xs text-gray-500 mb-1">Observações</p>
          <p className="text-sm text-gray-300">{data.obs}</p>
        </div>
      )}
    </div>
  );
}
