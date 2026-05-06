import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type SavedAddress = {
  id: string;
  address: string;
  roofId?: string;
  savedAt: string;
};

export type SolarUser = {
  nombre: string;
  apellidos: string;
  email: string;
  fechaNacimiento: string;
  codigoPostal: string;
  savedAddresses?: SavedAddress[];
};

type AuthContextValue = {
  user: SolarUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: Omit<SolarUser, "savedAddresses"> & { password: string }) => Promise<void>;
  logout: () => void;
  updateUser: (data: Partial<SolarUser>) => void;
  saveAddress: (address: string, roofId?: string) => void;
  removeAddress: (id: string) => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = "solarmap.user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SolarUser | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  const persist = (u: SolarUser | null) => {
    setUser(u);
    if (u) localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    else localStorage.removeItem(STORAGE_KEY);
  };

  const login = async (email: string, _password: string) => {
    const existing = user ?? {
      nombre: "Usuario",
      apellidos: "Demo",
      email,
      fechaNacimiento: "1990-01-01",
      codigoPostal: "28001",
      savedAddresses: [],
    };
    persist({ ...existing, email });
  };

  const register = async (data: Omit<SolarUser, "savedAddresses"> & { password: string }) => {
    const { password: _p, ...rest } = data;
    persist({ ...rest, savedAddresses: [] });
  };

  const logout = () => persist(null);

  const updateUser = (data: Partial<SolarUser>) => {
    if (!user) return;
    persist({ ...user, ...data });
  };

  const saveAddress = (address: string, roofId?: string) => {
    if (!user) return;
    const list = user.savedAddresses ?? [];
    if (list.some((a) => a.address === address && a.roofId === roofId)) return;
    persist({
      ...user,
      savedAddresses: [...list, { id: `addr_${Date.now()}`, address, roofId, savedAt: new Date().toISOString() }],
    });
  };

  const removeAddress = (id: string) => {
    if (!user) return;
    persist({ ...user, savedAddresses: (user.savedAddresses ?? []).filter((a) => a.id !== id) });
  };

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, login, register, logout, updateUser, saveAddress, removeAddress }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
