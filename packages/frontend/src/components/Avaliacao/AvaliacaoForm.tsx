import React, { useState } from "react";
import { z } from "zod";
import { trpc } from "../../lib/trpc";
import { Modal } from "../UI/Modal";
import { Input } from "../UI/Input";
import { Textarea } from "../UI/Textarea";
import { Button } from "../UI/Button";
import { useNotification } from "../../contexts/NotificationContext";

const schema = z.object({
  imovel_id: z.string().min(1, "Selecione um imóvel"),
  titulo: z.string().min(5, "Título mínimo 5 caracteres"),
});

type FieldErrors = Record<string, string>;

interface AvaliacaoFormProps {
  onClose: () => void;
}

export function AvaliacaoForm({ onClose }: AvaliacaoFormProps) {
  const { success, error: notify } = useNotification();
  const utils = trpc.useUtils();

  const [form, setForm] = useState({
    imovel_id: "",
    titulo: "",
    finalidade: "",
    metodologia: "comparativo" as "comparativo" | "evolutivo" | "misto",
    notas_tecnicas: "",
  });
  const [errors, setErrors] = useState<FieldErrors>({});

  const imoveis = trpc.imovel.listar.useQuery({ pagina: 1, limite: 1000 });

  const criarMutation = trpc.avaliacao.criar.useMutation({
    onSuccess: () => {
      success("Avaliação criada com sucesso!");
      void utils.avaliacao.listar.invalidate();
      onClose();
    },
    onError: (err) => notify(err.message),
  });

  const validate = (): boolean => {
    const result = schema.safeParse({ imovel_id: form.imovel_id, titulo: form.titulo });
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
      imovel_id: form.imovel_id,
      titulo: form.titulo,
      finalidade: form.finalidade || undefined,
      metodologia: form.metodologia,
      notas_tecnicas: form.notas_tecnicas || undefined,
    });
  };

  const set =
    (field: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const imovelList = imoveis.data?.imoveis ?? [];

  return (
    <Modal isOpen title="Nova Avaliação" onClose={onClose} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-300">Imóvel *</label>
          <select
            value={form.imovel_id}
            onChange={set("imovel_id")}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
          >
            <option value="">Selecione um imóvel</option>
            {imovelList.map((im) => (
              <option key={im.id} value={im.id}>
                {im.endereco} — {im.cidade}/{im.estado}
              </option>
            ))}
          </select>
          {errors.imovel_id && (
            <p className="text-red-400 text-xs">{errors.imovel_id}</p>
          )}
        </div>

        <Input
          label="Título *"
          value={form.titulo}
          onChange={set("titulo")}
          error={errors.titulo}
          placeholder="Ex: Avaliação Terreno Calhau - Jun/2026"
        />

        <Input
          label="Finalidade"
          value={form.finalidade}
          onChange={set("finalidade")}
          placeholder="Ex: Garantia bancária, compra e venda, judicial..."
        />

        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-300">Metodologia</label>
          <select
            value={form.metodologia}
            onChange={set("metodologia")}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
          >
            <option value="comparativo">Comparativo Direto de Mercado</option>
            <option value="evolutivo">Evolutivo</option>
            <option value="misto">Misto</option>
          </select>
        </div>

        <Textarea
          label="Notas Técnicas"
          value={form.notas_tecnicas}
          onChange={set("notas_tecnicas")}
          rows={4}
          placeholder="Observações técnicas, condições da vistoria..."
        />

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="ghost" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" loading={criarMutation.isPending} className="flex-1">
            Criar Avaliação
          </Button>
        </div>
      </form>
    </Modal>
  );
}
