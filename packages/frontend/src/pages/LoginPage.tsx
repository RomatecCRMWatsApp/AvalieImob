import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { trpc } from "../lib/trpc";
import { LogIn, AlertCircle } from "lucide-react";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [modo, setModo] = useState<"login" | "registro">("login");

  const loginMutation = trpc.auth.login.useMutation({
    onSuccess: (data) => {
      localStorage.setItem("token", data.token);
      localStorage.setItem("userId", data.userId);
      localStorage.setItem("user", JSON.stringify(data));
      navigate("/dashboard");
    },
    onError: (error) => {
      setErro(error.message || "Erro ao fazer login");
    },
  });

  const registroMutation = trpc.auth.registro.useMutation({
    onSuccess: (data) => {
      localStorage.setItem("token", data.token);
      localStorage.setItem("userId", data.userId);
      navigate("/dashboard");
    },
    onError: (error) => {
      setErro(error.message || "Erro ao registrar");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErro("");

    if (!email || !senha) {
      setErro("Preencha todos os campos");
      return;
    }

    if (modo === "login") {
      loginMutation.mutate({ email, senha });
    } else {
      registroMutation.mutate({
        email,
        senha,
        nome: email.split("@")[0],
        role: "avaliador",
      });
    }
  };

  const isLoading = loginMutation.isPending || registroMutation.isPending;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-green-950 to-gray-950 flex items-center justify-center px-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-20 w-72 h-72 bg-green-600/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 left-20 w-72 h-72 bg-yellow-600/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md">
        <div className="bg-gray-900 border border-green-700/30 rounded-2xl p-8 shadow-2xl">
          <div className="text-center mb-8">
            <div className="inline-block">
              <LogIn className="w-12 h-12 text-green-500 mb-4" />
            </div>
            <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-yellow-400">
              AvalieImob
            </h1>
            <p className="text-gray-400 text-sm mt-2">
              Avaliação Imobiliária Profissional
            </p>
          </div>

          <div className="flex gap-2 mb-6 bg-gray-800 p-1 rounded-lg">
            <button
              onClick={() => {
                setModo("login");
                setErro("");
              }}
              className={`flex-1 py-2 px-3 rounded-md font-medium transition ${
                modo === "login"
                  ? "bg-green-600 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => {
                setModo("registro");
                setErro("");
              }}
              className={`flex-1 py-2 px-3 rounded-md font-medium transition ${
                modo === "registro"
                  ? "bg-green-600 text-white"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Registrar
            </button>
          </div>

          {erro && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex gap-2">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-red-300 text-sm">{erro}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu@email.com"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Senha
              </label>
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-6 bg-gradient-to-r from-green-600 to-green-500 hover:from-green-700 hover:to-green-600 text-white font-semibold py-2 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Processando..." : modo === "login" ? "Entrar" : "Criar Conta"}
            </button>
          </form>

          <p className="text-center text-gray-500 text-xs mt-6">
            © 2025 Romatec Consultoria Imobiliária
          </p>
        </div>
      </div>
    </div>
  );
}
