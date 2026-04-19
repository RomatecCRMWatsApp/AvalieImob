import React from "react";
import { trpc } from "../../lib/trpc";
import { MapPin, Ruler, Building2, Image } from "lucide-react";

interface ImovelDetailProps {
  id: string;
}

const conservacaoLabels: Record<string, string> = {
  otimo: "Ótimo",
  bom: "Bom",
  regular: "Regular",
  precario: "Precário",
};

export function ImovelDetail({ id }: ImovelDetailProps) {
  const { data, isLoading } = trpc.imovel.obter.useQuery({ id });

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-10 bg-gray-800 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data) return <p className="text-gray-400">Imóvel não encontrado.</p>;

  const row = (
    label: string,
    value: string | null | undefined,
    Icon?: React.FC<{ className?: string }>,
  ) => (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      {Icon && <Icon className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-sm text-white mt-0.5">{value || "—"}</p>
      </div>
    </div>
  );

  const fotos = Array.isArray(data.fotos_urls) ? (data.fotos_urls as string[]) : [];

  return (
    <div className="space-y-1">
      {row("Endereço", data.endereco, MapPin)}
      {row("Cidade / Estado", `${data.cidade} / ${data.estado}`, Building2)}
      {row("Tipo", data.tipo ? data.tipo.charAt(0).toUpperCase() + data.tipo.slice(1) : undefined)}
      {row(
        "Área Total",
        data.area_total_m2 ? `${parseFloat(data.area_total_m2).toLocaleString("pt-BR")} m²` : undefined,
        Ruler,
      )}
      {data.area_total_ha &&
        row(
          "Área (ha)",
          `${parseFloat(data.area_total_ha).toLocaleString("pt-BR")} ha`,
        )}
      {row("Matrícula", data.matricula)}
      {row("CEP", data.cep)}
      {row(
        "Estado de Conservação",
        data.estado_conservacao ? conservacaoLabels[data.estado_conservacao] : undefined,
      )}
      {row("Descrição Física", data.descricao_fisica)}
      {row("Topografia", data.topografia)}
      {row("Acessibilidade", data.acessibilidade)}
      {row("Benfeitorias", data.benfeitorias)}

      {fotos.length > 0 && (
        <div className="pt-3">
          <div className="flex items-center gap-2 mb-2">
            <Image className="w-4 h-4 text-gray-500" />
            <p className="text-xs text-gray-500 uppercase tracking-wide">Fotos</p>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {fotos.map((url, i) => (
              <img
                key={i}
                src={url}
                alt={`Foto ${i + 1}`}
                className="w-full h-24 object-cover rounded-lg bg-gray-800"
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
