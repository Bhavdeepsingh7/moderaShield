"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as zod from "zod";
import { Shield, Mail, Loader, CheckCircle, ArrowLeft } from "lucide-react";

const forgotSchema = zod.object({
  email: zod.string().email("Please enter a valid email address")
});

type ForgotFormValues = zod.infer<typeof forgotSchema>;

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<ForgotFormValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: {
      email: ""
    }
  });

  const onSubmit = async () => {
    setIsLoading(true);
    // Simulate API request to reset password
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsLoading(false);
    setIsSent(true);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4 py-12 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-brand-purple/10 rounded-full blur-[100px] pointer-events-none -z-10" />

      <div className="w-full max-w-md bg-card-dark border border-border-dark rounded-2xl p-8 shadow-2xl animate-fade-in">
        {/* Logo Header */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="p-3 bg-brand-purple/20 text-brand-purple rounded-xl brand-glow mb-3">
            <Shield className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold font-outfit text-white">Reset your password</h2>
          <p className="text-xs text-slate-400 font-inter mt-1">
            We will send you an email with password recovery details
          </p>
        </div>

        {isSent ? (
          <div className="space-y-6 text-center font-inter">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl w-fit mx-auto flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              <span className="text-xs font-semibold">Recovery link sent!</span>
            </div>
            
            <p className="text-xs text-slate-400 leading-relaxed">
              If an account exists with that email address, you will receive instructions on how to reset your password shortly.
            </p>

            <Link 
              href="/login" 
              className="inline-flex items-center gap-2 text-xs font-semibold text-brand-purple hover:underline"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Login</span>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 rounded-lg text-sm transition-all brand-glow-hover flex items-center justify-center gap-2 mt-4 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader className="h-4 w-4 animate-spin" />
                  <span>Sending Link...</span>
                </>
              ) : (
                <span>Send Reset Link</span>
              )}
            </button>

            <div className="text-center pt-2">
              <Link 
                href="/login" 
                className="inline-flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Back to Login</span>
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
