import { createContext, useContext, useState, ReactNode } from "react";

// ----------------------------------------------------------------------------
// Configuracion
// ----------------------------------------------------------------------------
const API_URL = "http://localhost:8002";

// ----------------------------------------------------------------------------
// Tipos
// ----------------------------------------------------------------------------

export type SavedAddress = {
  id: string;
  address: string;
  roofId?: string;
  savedAt: string;
};

export type SolarUser = {
  id_usuario?: string;
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
  register: (data: Omit<SolarUser, "savedAddresses" | "id_usuario"> & { password: string }) => Promise<void>;
  logout: () => void;
  updateUser: (data: Partial<SolarUser>) => void;
  saveAddress: (address: string, roofId?: string) => void;
  removeAddress: (id: string) => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = "solarmap.user";

// ----------------------------------------------------------------------------
// Lee el usuario de localStorage de forma SINCRONA.
// Asi el primer render ya tiene el usuario (evita parpadeo y redireccion a login).
// ----------------------------------------------------------------------------
function leerUsuarioInicial(): SolarUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

// ----------------------------------------------------------------------------
// Provider
// ----------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  // Inicializacion sincrona desde localStorage
  const [user, setUser] = useState<SolarUser | null>(() => leerUsuarioInicial());

  const persist = (u: SolarUser | null) => {
    setUser(u);
    if (u) localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    else localStorage.removeItem(STORAGE_KEY);
  };

  // --- Login: llama a POST /api/auth/login ---
  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Error desconocido" }));
      throw new Error(err.detail || "No se pudo iniciar sesion");
    }

    const data = await res.json();
    persist({
      id_usuario: data.id_usuario,
      nombre: data.nombre,
      apellidos: data.apellidos,
      email: data.email,
      fechaNacimiento: data.fechaNacimiento,
      codigoPostal: data.codigoPostal,
      savedAddresses: [],
    });
  };

  // --- Register: llama a POST /api/auth/register ---
  const register = async (
    data: Omit<SolarUser, "savedAddresses" | "id_usuario"> & { password: string }
  ) => {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nombre: data.nombre,
        apellidos: data.apellidos,
        email: data.email,
        password: data.password,
        fechaNacimiento: data.fechaNacimiento,
        codigoPostal: data.codigoPostal,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Error desconocido" }));
      throw new Error(err.detail || "No se pudo crear la cuenta");
    }

    const out = await res.json();
    persist({
      id_usuario: out.id_usuario,
      nombre: out.nombre,
      apellidos: out.apellidos,
      email: out.email,
      fechaNacimiento: out.fechaNacimiento,
      codigoPostal: out.codigoPostal,
      savedAddresses: [],
    });
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
