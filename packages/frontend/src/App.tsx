import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { TRPCProvider } from "./lib/trpc-provider";
import { NotificationProvider } from "./contexts/NotificationContext";
import { ToastContainer } from "./components/UI/Toast";
import { AuthGuard } from "./components/Auth/AuthGuard";
import { AppLayout } from "./components/Layout/AppLayout";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { Clientes } from "./pages/Clientes";
import { Imoveis } from "./pages/Imoveis";
import { Avaliacoes } from "./pages/Avaliacoes";
import { PTAMs } from "./pages/PTAMs";
import { Audios } from "./pages/Audios";
import { Calculos } from "./pages/Calculos";

function ProtectedRoutes() {
  return (
    <AuthGuard>
      <AppLayout />
    </AuthGuard>
  );
}

function App() {
  return (
    <TRPCProvider>
      <NotificationProvider>
        <Router>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected layout */}
            <Route element={<ProtectedRoutes />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/clientes" element={<Clientes />} />
              <Route path="/imoveis" element={<Imoveis />} />
              <Route path="/avaliacoes" element={<Avaliacoes />} />
              <Route path="/ptams" element={<PTAMs />} />
              <Route path="/audios" element={<Audios />} />
              <Route path="/calculos" element={<Calculos />} />
            </Route>

            {/* Fallback */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Router>
        <ToastContainer />
      </NotificationProvider>
    </TRPCProvider>
  );
}

export default App;
