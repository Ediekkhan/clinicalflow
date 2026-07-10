'use client';

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '@/lib/auth';

type AuthState = {
  user: unknown;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

function FullScreenSkeleton() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50">
      <div className="w-full max-w-md rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="h-5 w-36 animate-pulse rounded bg-slate-100" />
        <div className="mt-5 h-24 animate-pulse rounded-xl bg-slate-100" />
        <div className="mt-4 h-10 animate-pulse rounded-xl bg-slate-100" />
      </div>
    </div>
  );
}

function AuthProvider({ endpoint, loginPath, children }: { endpoint: string; loginPath: string; children: ReactNode }) {
  const [user, setUser] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useMemo(
    () => async () => {
      setLoading(true);
      try {
        const data = await api.get(endpoint);
        setUser(data);
        setError(null);
      } catch (caught) {
        setUser(null);
        setError(caught instanceof Error ? caught.message : 'Authentication failed');
        if (typeof window !== 'undefined') window.location.href = loginPath;
      } finally {
        setLoading(false);
      }
    },
    [endpoint, loginPath],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading) return <FullScreenSkeleton />;

  return <AuthContext.Provider value={{ user, loading, error, refresh }}>{children}</AuthContext.Provider>;
}

export function PatientAuthProvider({ children }: { children: ReactNode }) {
  return <AuthProvider endpoint="/api/v1/auth/patient/me" loginPath="/login">{children}</AuthProvider>;
}

export function SpecialistAuthProvider({ children }: { children: ReactNode }) {
  return <AuthProvider endpoint="/api/v1/auth/specialist/me" loginPath="/specialist/login">{children}</AuthProvider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within an AuthProvider');
  return value;
}
