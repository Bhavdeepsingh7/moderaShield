"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { Shield, Lock, Mail, Loader, Key } from "lucide-react";
import { apiClient, setStoredApiKey, setStoredTenant, removeStoredApiKey } from "@/lib/api/client";

const loginSchema = zod.object({
  email: zod.string().optional(),
  password: zod.string().optional(),
  apiKey: zod.string().min(1, "API Key is required to authenticate")
});

type LoginFormValues = zod.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      apiKey: ""
    }
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("error") === "session_expired") {
        setTimeout(() => {
          setApiError("Your API key is invalid or expired. Please sign in with a valid key.");
        }, 0);
      }
    }
  }, []);

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true);
    setApiError(null);
    try {
      if (!data.apiKey || !data.apiKey.trim()) {
        throw new Error("API Key is required to authenticate.");
      }
      const key = data.apiKey.trim();
      if (!key.startsWith("msk_")) {
        throw new Error("Invalid key format. API keys must start with 'msk_'");
      }
      
      // Store API Key temporarily for verify call
      setStoredApiKey(key);
      
      // Verify key against backend
      const check = await apiClient.testConnection(key);
      if (!check.ok) {
        removeStoredApiKey();
        throw new Error(check.message || "Failed to verify API Key with backend");
      }
      
      if (check.tenant_id && check.tenant_name) {
        setStoredTenant(check.tenant_id, check.tenant_name);
      } else {
        setStoredTenant("dummy-tenant-id", "Authenticated Tenant");
      }
      
      router.push("/dashboard");
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setApiError(err.message || "Invalid credentials or API Key");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4 py-12 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-brand-purple/10 rounded-full blur-[100px] pointer-events-none -z-10" />

      <div className="w-full max-w-md bg-card-dark border border-border-dark rounded-2xl p-8 shadow-2xl">
        {/* Logo Header */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="p-3 bg-brand-purple/20 text-brand-purple rounded-xl brand-glow mb-3">
            <Shield className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold font-outfit text-white">Welcome back</h2>
          <p className="text-xs text-slate-400 font-inter mt-1">
            Sign in to access your ModeraShield developer dashboard
          </p>
        </div>

        {apiError && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-semibold leading-normal font-inter">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Email field */}
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-300 font-inter block">Email Address</label>
              <span className="text-[9px] text-slate-500 uppercase tracking-wider font-mono">Coming Soon</span>
            </div>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="email"
                disabled
                {...register("email")}
                placeholder="developer@company.com"
                className="w-full bg-slate-950/40 border border-border-dark text-slate-500 opacity-60 rounded-lg py-2 pl-10 pr-4 text-sm outline-none cursor-not-allowed"
              />
            </div>
          </div>

          {/* Password field */}
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-slate-300 font-inter">Password</label>
              <span className="text-[9px] text-slate-500 uppercase tracking-wider font-mono">Coming Soon</span>
            </div>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="password"
                disabled
                {...register("password")}
                placeholder="••••••••••••"
                className="w-full bg-slate-950/40 border border-border-dark text-slate-500 opacity-60 rounded-lg py-2 pl-10 pr-10 text-sm outline-none cursor-not-allowed"
              />
            </div>
          </div>

          {/* API Key (Required) */}
          <div className="space-y-1 border-t border-border-dark pt-3 mt-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Key className="h-3.5 w-3.5 text-brand-purple" />
              <label className="text-xs font-semibold text-slate-300 font-inter">
                API Key <span className="text-red-400">*</span>
              </label>
            </div>
            <input
              type="text"
              required
              {...register("apiKey")}
              placeholder="msk_..."
              className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple font-mono"
            />
            {errors.apiKey && (
              <span className="text-[10px] text-red-400 font-semibold">{errors.apiKey.message}</span>
            )}
            <p className="text-[9px] text-slate-500 font-inter">
              Supply your ModeraShield tenant API key to authenticate the session.
            </p>
          </div>

          {/* Buttons */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 rounded-lg text-sm transition-all brand-glow-hover flex items-center justify-center gap-2 mt-6 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                <span>Verifying Key...</span>
              </>
            ) : (
              <span>Sign In with API Key</span>
            )}
          </button>
        </form>

        <div className="relative flex py-4 items-center">
          <div className="flex-grow border-t border-border-dark"></div>
          <span className="flex-shrink mx-4 text-[10px] text-slate-500 font-bold uppercase tracking-wider font-inter">INFO</span>
          <div className="flex-grow border-t border-border-dark"></div>
        </div>

        {/* Info Banner */}
        <div className="p-3 bg-slate-900/50 border border-border-dark text-slate-400 rounded-lg text-[10px] leading-normal font-inter mb-4">
          💡 <strong>Real Gateway:</strong> The dashboard communicates directly with your FastAPI service. API keys are generated under your tenant workspace.
        </div>

        <div className="mt-6 text-center text-xs text-slate-400 font-inter">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-brand-purple hover:underline font-semibold">
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
}
