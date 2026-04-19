import React from "react";
import { Link } from "react-router-dom";
import { trpc } from "../lib/trpc";
import { StatsCards } from "../components/Dashboard/StatsCards";
import {
  ClipboardList,
  FileText,
  Building2,
  Users,
  ArrowRight,
  CheckCircle,
  Zap,
  Shield,
} from "lucide-react";

const quickLinks = [
  { label: "Nova Avaliação", path: "/avaliacoes", icon: ClipboardList, desc: "Iniciar PTAM" },
  { label: "Clientes", path: "/clientes", icon: Users, desc: "Gerenciar base" },
  { label: "Imóveis", path: "/imoveis", icon: Building2, desc: "Cadastrar imóvel" },
  { label: "PTAMs", path: "/ptams", icon: FileText, desc: "Ver emitidos" },
];

const features = [
  { icon: CheckCircle, text: "ABNT NBR 14.653" },
  { icon: Zap, text: "IA para fundamentação" },
  { icon: Shield, text: "LGPD compliant" },
];

export function Dashboard() {
  const user = trpc.auth.me.useQuery();

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Welcome Banner */}
      <div className="relative bg-gradient-to-r from-gray-900 via-gray-900 to-green-950 border border-green-900/40 rounded-2xl p-6 overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-green-700/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="relative">
          <p className="text-green-400 text-sm font-medium mb-1">Bem-vindo de volta</p>
          <h1 className="text-2xl font-bold text-white mb-2">
            {user.data?.nome ?? "Avaliador"}
          </h1>
          <p className="text-gray-400 text-sm max-w-lg">
            Plataforma completa para emitir PTAM, Laudos e Avaliações de imóveis urbanos,
            rurais e outras garantias — com inteligência artificial.
          </p>
          <div className="flex items-center gap-6 mt-4">
            {features.map((f) => (
              <div key={f.text} className="flex items-center gap-1.5 text-xs text-gray-500">
                <f.icon className="w-3.5 h-3.5 text-green-600" />
                {f.text}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <StatsCards />

      {/* Quick Links */}
      <div>
        <h2 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">
          Acesso Rápido
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {quickLinks.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className="group bg-gray-900 border border-gray-700/40 rounded-xl p-4 hover:border-green-700/50 hover:bg-gray-800/60 transition-all"
            >
              <div className="w-10 h-10 bg-green-700/15 rounded-lg flex items-center justify-center mb-3 group-hover:bg-green-700/25 transition-colors">
                <item.icon className="w-5 h-5 text-green-400" />
              </div>
              <p className="text-sm font-semibold text-white">{item.label}</p>
              <div className="flex items-center gap-1 mt-1">
                <p className="text-xs text-gray-500">{item.desc}</p>
                <ArrowRight className="w-3 h-3 text-gray-600 group-hover:text-green-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Flow Info */}
      <div>
        <h2 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">
          Fluxo de Trabalho
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { num: "01", label: "Estruturação", desc: "Clientes · Imóveis · Amostras" },
            { num: "02", label: "Processamento", desc: "Cálculos · Método Comparativo" },
            { num: "03", label: "Emissão", desc: "PTAM · Laudos · Relatórios" },
            { num: "04", label: "Gestão", desc: "Histórico · Suporte técnico" },
          ].map((step) => (
            <div
              key={step.num}
              className="bg-gray-900 border border-gray-700/40 rounded-xl p-4"
            >
              <span className="text-xs font-bold text-green-700 bg-green-700/10 px-2 py-0.5 rounded-md">
                {step.num}
              </span>
              <p className="text-sm font-semibold text-white mt-3 mb-1">{step.label}</p>
              <p className="text-xs text-gray-500">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
