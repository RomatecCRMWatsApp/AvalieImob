import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { trpc } from "../lib/trpc";

export interface User {
  id: string;
  email: string;
  nome: string;
  role: "admin" | "avaliador" | "cliente";
  crea?: string;
  incra?: string;
}

export function useAuth() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const meQuery = trpc.auth.me.useQuery();

  useEffect(() => {
    if (meQuery.data) {
      setUser(meQuery.data as User);
    } else if (!meQuery.isLoading && !meQuery.data) {
      setUser(null);
    }
    setLoading(meQuery.isLoading);
  }, [meQuery.data, meQuery.isLoading]);

  const login = async (email: string, senha: string) => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:3001/api/trpc"}/auth.login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, senha }),
        }
      );

      if (!response.ok) throw new Error("Login failed");

      const data = await response.json();
      const token = data.result.data.token;

      localStorage.setItem("token", token);
      setUser(data.result.data);
      navigate("/dashboard");
      return { success: true };
    } catch (error) {
      return { success: false, error: String(error) };
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
    navigate("/login");
  };

  return { user, loading, login, logout, isAuthenticated: !!user };
}
