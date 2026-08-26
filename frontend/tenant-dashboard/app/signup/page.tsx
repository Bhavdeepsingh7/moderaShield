"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { Shield, Lock, Mail, User, Building, Eye, EyeOff, Loader } from "lucide-react";
import { apiClient, setStoredApiKey, setStoredTenant } from "@/lib/api/client";

const signupSchema = zod.object({
  name: zod.string().min(2, "Name must be at least 2 characters"),
  email: zod.string().email("Please enter a valid email address"),
  companyName: zod.string().min(2, "Company name must be at least 2 characters"),
  password: zod.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: zod.string().min(8, "Password confirmation is required"),
  terms: zod.boolean().refine(val => val === true, {
    message: "You must accept the terms and conditions"
  })
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"]
});

type SignupFormValues = zod.infer<typeof signupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors } } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      name: "",
      email: "",
      companyName: "",
      password: "",
      confirmPassword: "",
      terms: false
    }
  });

  const onSubmit = async (data: SignupFormValues) => {
    setIsLoading(true);
    setApiError(null);
    try {
      // 1. Create slug
      const slug = data.companyName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
      
      // 2. Call API to create Tenant
      const tenant = await apiClient.createTenant(data.companyName, slug || "company-tenant");
      
      // 3. Generate API Key
      const keyResult = await apiClient.createApiKey(tenant.id, "Default API Key");
      
      // 4. Store details
      setStoredApiKey(keyResult.key);
      setStoredTenant(tenant.id, tenant.name);
      
      // Redirect to dashboard
      router.push("/dashboard");
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setApiError(err.message || "Failed to create account. Please try again.");
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
        <div className="flex flex-col items-center mb-6 text-center">
          <div className="p-3 bg-brand-purple/20 text-brand-purple rounded-xl brand-glow mb-3">
            <Shield className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold font-outfit text-white">Create your account</h2>
          <p className="text-xs text-slate-400 font-inter mt-1">
            Start protecting your platform with AI moderation
          </p>
        </div>

        {apiError && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-semibold leading-normal font-inter">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name field */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 font-inter block">Full Name</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                {...register("name")}
                placeholder="John Doe"
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
              />
            </div>
            {errors.name && (
              <span className="text-[10px] text-red-400 font-semibold">{errors.name.message}</span>
            )}
          </div>

          {/* Email field */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 font-inter block">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="email"
                {...register("email")}
                placeholder="developer@company.com"
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
              />
            </div>
            {errors.email && (
              <span className="text-[10px] text-red-400 font-semibold">{errors.email.message}</span>
            )}
          </div>

          {/* Company field */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 font-inter block">Company / Organization</label>
            <div className="relative">
              <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                {...register("companyName")}
                placeholder="Acme Inc."
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
              />
            </div>
            {errors.companyName && (
              <span className="text-[10px] text-red-400 font-semibold">{errors.companyName.message}</span>
            )}
          </div>

          {/* Password field */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 font-inter block">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type={showPassword ? "text" : "password"}
                {...register("password")}
                placeholder="••••••••••••"
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 pl-10 pr-10 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && (
              <span className="text-[10px] text-red-400 font-semibold">{errors.password.message}</span>
            )}
          </div>

          {/* Confirm Password field */}
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300 font-inter block">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="password"
                {...register("confirmPassword")}
                placeholder="••••••••••••"
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
              />
            </div>
            {errors.confirmPassword && (
              <span className="text-[10px] text-red-400 font-semibold">{errors.confirmPassword.message}</span>
            )}
          </div>

          {/* Terms checkbox */}
          <div className="flex items-start gap-2 pt-2">
            <input
              type="checkbox"
              id="terms"
              {...register("terms")}
              className="mt-1 h-3.5 w-3.5 rounded border-border-dark bg-slate-900 text-brand-purple outline-none focus:ring-0"
            />
            <label htmlFor="terms" className="text-[11px] text-slate-400 leading-normal font-inter select-none">
              I agree to the{" "}
              <a href="#" className="text-brand-purple hover:underline font-semibold">Terms of Service</a>{" "}
              and{" "}
              <a href="#" className="text-brand-purple hover:underline font-semibold">Privacy Policy</a>.
            </label>
          </div>
          {errors.terms && (
            <span className="text-[10px] text-red-400 font-semibold block">{errors.terms.message}</span>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 rounded-lg text-sm transition-all brand-glow-hover flex items-center justify-center gap-2 mt-4 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                <span>Creating Account...</span>
              </>
            ) : (
              <span>Create Account</span>
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-slate-400 font-inter">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-purple hover:underline font-semibold">
            Log in
          </Link>
        </div>
      </div>
    </div>
  );
}
