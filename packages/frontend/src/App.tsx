import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { TRPCProvider } from "./lib/trpc-provider";
import { LoginPage } from "./pages/LoginPage";
import { DashboardLayout } from "./pages/DashboardPage";
import { CalculoComparativoPage } from "./pages/CalculoComparativoPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token");
  return token ? <>{children}</> : <Navigate to="/login" />;
}

function App() {
  return (
    <TRPCProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <DashboardLayout />
              </PrivateRoute>
            }
          />

          <Route
            path="/dashboard/calculos"
            element={
              <PrivateRoute>
                <DashboardLayout>
                  <CalculoComparativoPage />
                </DashboardLayout>
              </PrivateRoute>
            }
          />

          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </Router>
    </TRPCProvider>
  );
}

export default App;
