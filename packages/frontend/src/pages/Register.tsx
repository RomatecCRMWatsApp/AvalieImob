import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { trpc } from "../lib/trpc";
import { setToken } from "../lib/auth";
import { Input } from "../components/UI/Input";
import { Button } from "../components/UI/Button";
import { AlertCircle, UserPlus } from "lucide-react";

const registerSchema = z.object({
  nome: z.string().min(3, "Nome mínimo 3 caracteres"),
  email: z.string().email("Email inválido"),
  senha: z.string().min(8, "Senha mínimo 8 caracteres"),
  role: z.enum(["avaliador", "cliente"]),
});

type FormErrors = Partial<Record<"nome" | "email" | "senha" | "role", string>>;

export function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    nome: "",
    email: "",
    senha: "",
    role: "avaliador" as "avaliador" | "cliente",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState("");

  const registerMutation = trpc.auth.registro.useMutation({
    onSuccess: (data) => {
      setToken(data.token);
      localStorage.setItem("userId", data.userId);
      navigate("/dashboard");
    },
    onError: (err) => setServerError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");

    const result = registerSchema.safeParse(form);
    if (!result.success) {
      const errs: FormErrors = {};
      result.error.errors.forEach((er) => {
        const field = er.path[0] as keyof FormErrors;
        errs[field] = er.message;
      });
      setErrors(errs);
      return;
    }
    setErrors({});
    registerMutation.mutate(form);
  };

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <div className="min-h-screen bg-[#0f1419] flex items-center justify-center px-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-1/4 w-96 h-96 bg-green-700/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-1/4 w-96 h-96 bg-green-800/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-green-500 to-green-800 rounded-2xl shadow-2xl shadow-green-900/50 mb-4">
            <UserPlus className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Criar conta</h1>
          <p className="text-gray-500 text-sm mt-1">AvalieImob · RomaTec</p>
        </div>

        <div className="bg-gray-900 border border-gray-700/50 rounded-2xl p-8 shadow-2xl">
          {serverError && (
            <div className="mb-4 p-3 bg-red-900/20 border border-red-700/40 rounded-lg flex gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-300 text-sm">{serverError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Nome completo"
              value={form.nome}
              onChange={set("nome")}
              placeholder="Seu nome"
              error={errors.nome}
            />
            <Input
              label="Email"
              type="email"
              value={form.email}
              onChange={set("email")}
              placeholder="voce@email.com"
              error={errors.email}
            />
            <Input
              label="Senha"
              type="password"
              value={form.senha}
              onChange={set("senha")}
              placeholder="Mínimo 8 caracteres"
              error={errors.senha}
            />

            <div className="space-y-1">
              <label className="block text-sm font-medium text-gray-300">Perfil</label>
              <select
                value={form.role}
                onChange={set("role")}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-green-600 focus:ring-1 focus:ring-green-600/30 transition-colors"
              >
                <option value="avaliador">Avaliador / Engenheiro</option>
                <option value="cliente">Cliente</option>
              </select>
            </div>

            <Button
              type="submit"
              loading={registerMutation.isPending}
              className="w-full mt-2"
              size="lg"
            >
              Criar conta
            </Button>
          </form>

          <p className="text-center text-gray-500 text-sm mt-6">
            Já tem conta?{" "}
            <Link to="/login" className="text-green-400 hover:text-green-300 font-medium">
              Entrar
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
