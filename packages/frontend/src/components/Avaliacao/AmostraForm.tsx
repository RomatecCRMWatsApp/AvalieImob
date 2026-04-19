import React, { useState } from "react";
import { z } from "zod";
import { trpc } from "../../lib/trpc";
import { Button } from "../UI/Button";
import { Input } from "../UI/Input";
import { Textarea } from "../UI/Textarea";
import { useNotification } from "../../contexts/NotificationContext";
import { Plus } from "lucide-react";

const schema = z.object({
  descricao: z.string().min(5, "Descrição mínimo 5 caracteres"),
  valor_total: z.number().positive("Valor deve ser positivo"),
});

type FieldErrors = Record<string, string>;

interface AmostraFormProps {
  avaliacaoId: string;
  onAdded: () => void;
}

export function AmostraForm({ avaliacaoId, onAdded }: AmostraFormProps) {
  const { success, error: notify } = useNotification();
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});

  const [form, setForm] = useState({
    descricao: "",
    endereco: "",
    cidade: "",
    estado: "",
    tipo: "urbano" as "urbano" | "rural",
    area_m2: "",
    valor_total: "",
    valor_unitario_m2: "",
    fonte: "",
    situacao: "oferta" as "oferta" | "vendido" | "aluguel",
    obs: "",
  });

  const criarMutation = trpc.amostra.criar.useMutation({
    onSuccess: () => {
      success("Amostra adicionada!");
      setForm({
        descricao: "",
        endereco: "",
        cidade: "",
        estado: "",
        tipo: "urbano",
        area_m2: "",
        valor_total: "",
        valor_unitario_m2: "",
        fonte: "",
        situacao: "oferta",
        obs: "",
      });
      setShow(false);
      onAdded();
    },
    onError: (err) => notify(err.message),
  });

  const validate = (): boolean => {
    const result = schema.safeParse({
      descricao: form.descricao,
      valor_total: form.valor_total ? parseFloat(form.valor_total) : 0,
    });
    if (result.success) {
      setErrors({});
      return true;
    }
    const errs: FieldErrors = {};
    result.error.errors.forEach((e) => {
      errs[e.path[0] as string] = e.message;
    });
    setErrors(errs);
    return false;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    criarMutation.mutate({
      avaliacao_id: avaliacaoId,
      descricao: form.descricao,
      endereco: form.endereco || undefined,
      cidade: form.cidade || undefined,
      estado: form.estado || undefined,
      tipo: form.tipo,
      area_m2: form.area_m2 ? parseFloat(form.area_m2) : undefined,
      valor_total: parseFloat(form.valor_total),
      valor_unitario_m2: form.valor_unitario_m2 ? parseFloat(form.valor_unitario_m2) : undefined,
      fonte: form.fonte || undefined,
      situacao: form.situacao,
      obs: form.obs || undefined,
    });
  };

  const set =
    (field: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  if (!show) {
    return (
      <Button onClick={() => setShow(true)} variant="outline" size="sm">
        <Plus className="w-4 h-4" />
        Adicionar Amostra
      </Button>
    );
  }

  return (
    <div className="bg-gray-800/50 border border-gray-700/40 rounded-xl p-4">
      <h4 className="text-sm font-semibold text-white mb-4">Nova Amostra de Mercado</h4>
      <form onSubmit={handleSubmit} className="space-y-3">
        <Input
          label="Descrição *"
          value={form.descricao}
          onChange={set("descricao")}
          error={errors.descricao}
          placeholder="Ex: Terreno comercial zona industrial BR-222"
        />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Valor Total (R$) *"
            type="number"
            value={form.valor_total}
            onChange={set("valor_total")}
            error={errors.valor_total}
            placeholder="150000"
          />
          <Input
            label="Valor R$/m²"
            type="number"
            value={form.valor_unitario_m2}
            onChange={set("valor_unitario_m2")}
            placeholder="300"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Área (m²)"
            type="number"
            value={form.area_m2}
            onChange={set("area_m2")}
            placeholder="500"
          />
          <Input
            label="Fonte"
            value={form.fonte}
            onChange={set("fonte")}
            placeholder="CRECI, Imobiliária..."
          />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <Input label="Cidade" value={form.cidade} onChange={set("cidade")} />
          <Input label="Estado" value={form.estado} onChange={set("estado")} maxLength={2} placeholder="MA" />
          <div className="space-y-1">
            <label className="block text-xs font-medium text-gray-400">Situação</label>
            <select
              value={form.situacao}
              onChange={set("situacao")}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
            >
              <option value="oferta">Oferta</option>
              <option value="vendido">Vendido</option>
              <option value="aluguel">Aluguel</option>
            </select>
          </div>
        </div>
        <Textarea label="Observações" value={form.obs} onChange={set("obs")} rows={2} />

        <div className="flex gap-2 pt-1">
          <Button type="button" variant="ghost" size="sm" onClick={() => setShow(false)}>
            Cancelar
          </Button>
          <Button type="submit" size="sm" loading={criarMutation.isPending}>
            Adicionar
          </Button>
        </div>
      </form>
    </div>
  );
}
