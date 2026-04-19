import React, { useState, useEffect } from "react";
import { z } from "zod";
import { trpc } from "../../lib/trpc";
import { Modal } from "../UI/Modal";
import { Input } from "../UI/Input";
import { Textarea } from "../UI/Textarea";
import { Button } from "../UI/Button";
import { useNotification } from "../../contexts/NotificationContext";

const schema = z.object({
  razao_social: z.string().min(3, "Mínimo 3 caracteres"),
  email: z.union([z.string().email("Email inválido"), z.literal("")]),
});

type FieldErrors = Record<string, string>;

interface State {
  razao_social: string;
  cnpj_cpf: string;
  telefone: string;
  email: string;
  endereco: string;
  cidade: string;
  estado: string;
  cep: string;
  contato: string;
  obs: string;
}

const EMPTY: State = {
  razao_social: "",
  cnpj_cpf: "",
  telefone: "",
  email: "",
  endereco: "",
  cidade: "",
  estado: "",
  cep: "",
  contato: "",
  obs: "",
};

interface ClienteFormProps {
  editId: string | null;
  onClose: () => void;
}

export function ClienteForm({ editId, onClose }: ClienteFormProps) {
  const { success, error: notify } = useNotification();
  const utils = trpc.useUtils();
  const [form, setForm] = useState<State>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});

  const clienteQuery = trpc.cliente.obter.useQuery(
    { id: editId! },
    { enabled: !!editId },
  );

  useEffect(() => {
    if (clienteQuery.data) {
      const d = clienteQuery.data;
      setForm({
        razao_social: d.razao_social,
        cnpj_cpf: d.cnpj_cpf ?? "",
        telefone: d.telefone ?? "",
        email: d.email ?? "",
        endereco: d.endereco ?? "",
        cidade: d.cidade ?? "",
        estado: d.estado ?? "",
        cep: d.cep ?? "",
        contato: d.contato ?? "",
        obs: d.obs ?? "",
      });
    }
  }, [clienteQuery.data]);

  const criarMutation = trpc.cliente.criar.useMutation({
    onSuccess: () => {
      success("Cliente criado com sucesso!");
      void utils.cliente.listar.invalidate();
      onClose();
    },
    onError: (err) => notify(err.message),
  });

  const atualizarMutation = trpc.cliente.atualizar.useMutation({
    onSuccess: () => {
      success("Cliente atualizado!");
      void utils.cliente.listar.invalidate();
      onClose();
    },
    onError: (err) => notify(err.message),
  });

  const validate = (): boolean => {
    const result = schema.safeParse({ razao_social: form.razao_social, email: form.email });
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

    const payload = {
      razao_social: form.razao_social,
      cnpj_cpf: form.cnpj_cpf || undefined,
      telefone: form.telefone || undefined,
      email: form.email || undefined,
      endereco: form.endereco || undefined,
      cidade: form.cidade || undefined,
      estado: form.estado || undefined,
      cep: form.cep || undefined,
      contato: form.contato || undefined,
      obs: form.obs || undefined,
    };

    if (editId) {
      atualizarMutation.mutate({ id: editId, ...payload });
    } else {
      criarMutation.mutate(payload);
    }
  };

  const set =
    (field: keyof State) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const isLoading = criarMutation.isPending || atualizarMutation.isPending;

  return (
    <Modal
      isOpen
      title={editId ? "Editar Cliente" : "Novo Cliente"}
      onClose={onClose}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Razão Social *"
          value={form.razao_social}
          onChange={set("razao_social")}
          error={errors.razao_social}
          placeholder="Nome da empresa ou pessoa"
        />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="CNPJ / CPF"
            value={form.cnpj_cpf}
            onChange={set("cnpj_cpf")}
            placeholder="00.000.000/0001-00"
          />
          <Input
            label="Telefone"
            value={form.telefone}
            onChange={set("telefone")}
            placeholder="(98) 99999-0000"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={set("email")}
            error={errors.email}
            placeholder="contato@empresa.com"
          />
          <Input
            label="Contato"
            value={form.contato}
            onChange={set("contato")}
            placeholder="Nome do contato"
          />
        </div>
        <Input
          label="Endereço"
          value={form.endereco}
          onChange={set("endereco")}
          placeholder="Rua, número, complemento"
        />
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Input
              label="Cidade"
              value={form.cidade}
              onChange={set("cidade")}
              placeholder="São Luís"
            />
          </div>
          <Input
            label="Estado"
            value={form.estado}
            onChange={set("estado")}
            placeholder="MA"
            maxLength={2}
          />
        </div>
        <Input
          label="CEP"
          value={form.cep}
          onChange={set("cep")}
          placeholder="00000-000"
        />
        <Textarea
          label="Observações"
          value={form.obs}
          onChange={set("obs")}
          rows={3}
          placeholder="Notas adicionais..."
        />

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="ghost" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" loading={isLoading} className="flex-1">
            {editId ? "Atualizar" : "Criar"} Cliente
          </Button>
        </div>
      </form>
    </Modal>
  );
}
