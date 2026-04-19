import { useNavigate } from "react-router-dom";
import { trpc } from "../lib/trpc";
import { setToken, removeToken } from "../lib/auth";

export function useAuth() {
  const navigate = useNavigate();
  const me = trpc.auth.me.useQuery();
  const utils = trpc.useUtils();

  const loginMutation = trpc.auth.login.useMutation({
    onSuccess: (data) => {
      setToken(data.token);
      localStorage.setItem("userId", data.userId);
      localStorage.setItem("user", JSON.stringify(data));
      void utils.auth.me.invalidate();
      navigate("/dashboard");
    },
  });

  const registerMutation = trpc.auth.registro.useMutation({
    onSuccess: (data) => {
      setToken(data.token);
      localStorage.setItem("userId", data.userId);
      void utils.auth.me.invalidate();
      navigate("/dashboard");
    },
  });

  const logout = () => {
    removeToken();
    void utils.auth.me.reset();
    navigate("/login");
  };

  return {
    user: me.data,
    isLoading: me.isLoading,
    login: loginMutation.mutate,
    loginPending: loginMutation.isPending,
    loginError: loginMutation.error?.message ?? null,
    register: registerMutation.mutate,
    registerPending: registerMutation.isPending,
    registerError: registerMutation.error?.message ?? null,
    logout,
  };
}
