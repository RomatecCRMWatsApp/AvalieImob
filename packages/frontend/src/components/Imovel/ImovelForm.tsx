import React, { useState, useEffect } from "react";
import { z } from "zod";
import { trpc } from "../../lib/trpc";
import { Modal } from "../UI/Modal";
import { Input } from "../UI/Input";
import { Textarea } from "../UI/Textarea";
import { Button } from "../UI/Button";
import { useNotification } from "../../contexts/NotificationContext";

const schema = z.object({
  cliente_id: z.string().min(1, "Selecione um cliente"),
  endereco: z.string().min(10, "Endereço muito curto"),
  cidade: z.string().min(3, "Informe a cidade"),
  estado: z.string().length(2, "2 caracteres"),
});

type FieldErrors = Record<string, string>;

interface State {
  cliente_id: string;
  matricula: string;
  endereco: string;
  latitude: string;
  longitude: string;
  cidade: string;
  estado: string;
  cep: string;
  tipo: "urbano" | "rural" | "misto";
  area_total_m2: string;
  area_total_ha: string;
  descricao_fisica: string;
  topografia: string;
  acessibilidade: string;
  benfeitorias: string;
  estado_conservacao: "" | "otimo" | "bom" | "regular" | "precario";
}

const EMPTY: State = {
  cliente_id: "",
  matricula: "",
  endereco: "",
  latitude: "",
  longitude: "",
  cidade: "",
  estado: "",
  cep: "",
  tipo: "urbano",
  area_total_m2: "",
  area_total_ha: "",
  descricao_fisica: "",
  topografia: "",
  acessibilidade: "",
  benfeitorias: "",
  estado_conservacao: "",
};

interface ImovelFormProps {
  editId: string | null;
  onClose: () => void;
}

export function ImovelForm({ editId, onClose }: ImovelFormProps) {
  const { success, error: notify } = useNotification();
  const utils = trpc.useUtils();
  const [form, setForm] = useState<State>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});

  const clientes = trpc.cliente.listar.useQuery();
  const imovelQuery = trpc.imovel.obter.useQuery(
    { id: editId! },
    { enabled: !!editId },
  );

  useEffect(() => {
    if (imovelQuery.data) {
      const d = imovelQuery.data;
      setForm({
        cliente_id: d.cliente_id,
        matricula: d.matricula ?? "",
        endereco: d.endereco,
        latitude: d.latitude ?? "",
        longitude: d.longitude ?? "",
        cidade: d.cidade,
        estado: d.estado,
        cep: d.cep ?? "",
        tipo: (d.tipo as "urbano" | "rural" | "misto") ?? "urbano",
        area_total_m2: d.area_total_m2 ?? "",
        area_total_ha: d.area_total_ha ?? "",
        descricao_fisica: d.descricao_fisica ?? "",
        topografia: d.topografia ?? "",
        acessibilidade: d.acessibilidade ?? "",
        benfeitorias: d.benfeitorias ?? "",
        estado_conservacao:
          (d.estado_conservacao as State["estado_conservacao"]) ?? "",
      });
    }
  }, [imovelQuery.data]);

  const criarMutation = trpc.imovel.criar.useMutation({
    onSuccess: () => {
      success("Imóvel criado com sucesso!");
      void utils.imovel.listar.invalidate();
      onClose();
    },
    onError: (err) => notify(err.message),
  });

  const atualizarMutation = trpc.imovel.atualizar.useMutation({
    onSuccess: () => {
      success("Imóvel atualizado!");
      void utils.imovel.listar.invalidate();
      onClose();
    },
    onError: (err) => notify(err.message),
  });

  const validate = (): boolean => {
    const result = schema.safeParse({
      cliente_id: form.cliente_id,
      endereco: form.endereco,
      cidade: form.cidade,
      estado: form.estado,
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

    const num = (v: string) => (v ? parseFloat(v) : undefined);

    if (editId) {
      atualizarMutation.mutate({
        id: editId,
        endereco: form.endereco,
        latitude: num(form.latitude),
        longitude: num(form.longitude),
        cidade: form.cidade,
        estado: form.estado,
        cep: form.cep || undefined,
        tipo: form.tipo,
        area_total_m2: num(form.area_total_m2),
        area_total_ha: num(form.area_total_ha),
        descricao_fisica: form.descricao_fisica || undefined,
        topografia: form.topografia || undefined,
        acessibilidade: form.acessibilidade || undefined,
        benfeitorias: form.benfeitorias || undefined,
        estado_conservacao: form.estado_conservacao || undefined,
      });
    } else {
      criarMutation.mutate({
        cliente_id: form.cliente_id,
        matricula: form.matricula || undefined,
        endereco: form.endereco,
        latitude: num(form.latitude),
        longitude: num(form.longitude),
        cidade: form.cidade,
        estado: form.estado,
        cep: form.cep || undefined,
        tipo: form.tipo,
        area_total_m2: num(form.area_total_m2),
        area_total_ha: num(form.area_total_ha),
        descricao_fisica: form.descricao_fisica || undefined,
        topografia: form.topografia || undefined,
        acessibilidade: form.acessibilidade || undefined,
        benfeitorias: form.benfeitorias || undefined,
        estado_conservacao: form.estado_conservacao || undefined,
      });
    }
  };

  const set =
    (field: keyof State) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const isLoading = criarMutation.isPending || atualizarMutation.isPending;

  return (
    <Modal
      isOpen
      title={editId ? "Editar Imóvel" : "Novo Imóvel"}
      onClose={onClose}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {!editId && (
          <div className="space-y-1">
            <label className="block text-sm font-medium text-gray-300">Cliente *</label>
            <select
              value={form.cliente_id}
              onChange={set("cliente_id")}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600/30 transition-colors"
            >
              <option value="">Selecione um cliente</option>
              {clientes.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.razao_social}
                </option>
              ))}
            </select>
            {errors.cliente_id && (
              <p className="text-red-400 text-xs">{errors.cliente_id}</p>
            )}
          </div>
        )}

        <Input
          label="Endereço *"
          value={form.endereco}
          onChange={set("endereco")}
          error={errors.endereco}
          placeholder="Rua, número, bairro"
        />

        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Input
              label="Cidade *"
              value={form.cidade}
              onChange={set("cidade")}
              error={errors.cidade}
              placeholder="São Luís"
            />
          </div>
          <Input
            label="Estado *"
            value={form.estado}
            onChange={set("estado")}
            error={errors.estado}
            placeholder="MA"
            maxLength={2}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input label="CEP" value={form.cep} onChange={set("cep")} placeholder="00000-000" />
          <Input
            label="Matrícula"
            value={form.matricula}
            onChange={set("matricula")}
            placeholder="Nº matrícula"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-300">Tipo</label>
          <select
            value={form.tipo}
            onChange={set("tipo")}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
          >
            <option value="urbano">Urbano</option>
            <option value="rural">Rural</option>
            <option value="misto">Misto</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Área Total (m²)"
            type="number"
            value={form.area_total_m2}
            onChange={set("area_total_m2")}
            placeholder="0.00"
          />
          <Input
            label="Área Total (ha)"
            type="number"
            value={form.area_total_ha}
            onChange={set("area_total_ha")}
            placeholder="0.00"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Latitude"
            type="number"
            value={form.latitude}
            onChange={set("latitude")}
            placeholder="-2.530"
          />
          <Input
            label="Longitude"
            type="number"
            value={form.longitude}
            onChange={set("longitude")}
            placeholder="-44.300"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm font-medium text-gray-300">Estado de Conservação</label>
          <select
            value={form.estado_conservacao}
            onChange={set("estado_conservacao")}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-600 transition-colors"
          >
            <option value="">Não informado</option>
            <option value="otimo">Ótimo</option>
            <option value="bom">Bom</option>
            <option value="regular">Regular</option>
            <option value="precario">Precário</option>
          </select>
        </div>

        <Textarea
          label="Descrição Física"
          value={form.descricao_fisica}
          onChange={set("descricao_fisica")}
          rows={3}
          placeholder="Descreva as características físicas do imóvel..."
        />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Topografia" value={form.topografia} onChange={set("topografia")} />
          <Input
            label="Acessibilidade"
            value={form.acessibilidade}
            onChange={set("acessibilidade")}
          />
        </div>
        <Textarea
          label="Benfeitorias"
          value={form.benfeitorias}
          onChange={set("benfeitorias")}
          rows={2}
          placeholder="Construções, plantações, cercas..."
        />

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="ghost" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" loading={isLoading} className="flex-1">
            {editId ? "Atualizar" : "Criar"} Imóvel
          </Button>
        </div>
      </form>
    </Modal>
  );
}
