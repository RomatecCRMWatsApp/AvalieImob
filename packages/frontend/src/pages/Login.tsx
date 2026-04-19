import React, { useState } from "react";
import { Link } from "react-router-dom";
import { z } from "zod";
import { trpc } from "../lib/trpc";
import { setToken } from "../lib/auth";
import { useNavigate } from "react-router-dom";
import { Input } from "../components/UI/Input";
import { Button } from "../components/UI/Button";
import { AlertCircle, Shield } from "lucide-react";

const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  senha: z.string().min(8, "Senha mínimo 8 caracteres"),
});

type FormErrors = Partial<Record<"email" | "senha", string>>;

export function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState("");

  const loginMutation = trpc.auth.login.useMutation({
    onSuccess: (data) => {
      setToken(data.token);
      localStorage.setItem("userId", data.userId);
      localStorage.setItem("user", JSON.stringify(data));
      navigate("/dashboard");
    },
    onError: (err) => setServerError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");

    const result = loginSchema.safeParse({ email, senha });
    if (!result.success) {
      const errs: FormErrors = {};
      result.error.errors.forEach((er) => {
        const field = er.path[0] as "email" | "senha";
        errs[field] = er.message;
      });
      setErrors(errs);
      return;
    }
    setErrors({});
    loginMutation.mutate({ email, senha });
  };

  return (
    <div className="min-h-screen bg-[#0f1419] flex items-center justify-center px-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-1/4 w-96 h-96 bg-green-700/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-1/4 w-96 h-96 bg-green-800/5 rounded-full blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-green-500 to-green-800 rounded-2xl shadow-2xl shadow-green-900/50 mb-4">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Entrar na plataforma</h1>
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
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="voce@email.com"
              error={errors.email}
            />
            <Input
              label="Senha"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="Mínimo 8 caracteres"
              error={errors.senha}
            />

            <Button
              type="submit"
              loading={loginMutation.isPending}
              className="w-full mt-2"
              size="lg"
            >
              Entrar
            </Button>
          </form>

          <p className="text-center text-gray-500 text-sm mt-6">
            Não tem conta?{" "}
            <Link to="/register" className="text-green-400 hover:text-green-300 font-medium">
              Criar conta
            </Link>
          </p>
        </div>

        <p className="text-center text-gray-600 text-xs mt-6">
          © 2026 RomaTec · ABNT NBR 14.653 · LGPD compliant
        </p>
      </div>
    </div>
  );
}
