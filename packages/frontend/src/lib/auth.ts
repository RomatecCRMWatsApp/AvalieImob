export const getToken = (): string | null => localStorage.getItem("token");
export const setToken = (token: string): void => localStorage.setItem("token", token);
export const removeToken = (): void => {
  localStorage.removeItem("token");
  localStorage.removeItem("userId");
  localStorage.removeItem("user");
};
