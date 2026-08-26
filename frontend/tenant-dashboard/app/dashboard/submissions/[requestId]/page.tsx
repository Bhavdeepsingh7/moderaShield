"use client";

import React, { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { 
  ArrowLeft, 
  ShieldAlert, 
  ShieldCheck, 
  Clock, 
  Cpu, 
  Hash, 
  AlertTriangle
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { apiClient, ModerationResultResponse } from "@/lib/api/client";

interface PageProps {
  params: Promise<{
    requestId: string;
  }>;
}

export default function SubmissionDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const requestId = resolvedParams.requestId;

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<ModerationResultResponse | null>(null);

  const fetchDetail = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.getRequestDetail(requestId);
      setDetail(res);
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setError(err.message || "Failed to load submission details.");
    } finally {
      setIsLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchDetail();
    }, 0);

    return () => clearTimeout(timer);
  }, [fetchDetail]);

  useEffect(() => {
    if (!detail) return;
    if (detail.status === "approved" || detail.status === "flagged" || detail.status === "failed") return;

    const timer = setTimeout(() => {
      apiClient.getRequestDetail(requestId).then((res) => {
        setDetail(res);
      }).catch(() => {});
    }, 1000);

    return () => clearTimeout(timer);
  }, [detail, requestId]);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Submission Inspection" 
        description={`Analyzing request ${requestId}`} 
      />

      <div className="p-6 space-y-6 flex-grow max-w-5xl w-full mx-auto">
        {/* Back Link */}
        <Link 
          href="/dashboard/submissions"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Submissions Log</span>
        </Link>

        {isLoading ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-96">
            <div className="h-6 w-6 border-2 border-brand-purple border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-slate-500 font-mono mt-3">Loading request metrics...</span>
          </div>
        ) : error ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-96">
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-4">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-bold font-outfit text-slate-300">Failed to fetch request</h4>
            <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">{error}</p>
            <button 
              onClick={fetchDetail}
              className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-1.5 px-4 rounded-lg text-xs"
            >
              Retry
            </button>
          </div>
        ) : !detail ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-96">
            <p className="text-xs text-slate-500">No details found for this request</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Left column: Summary Metadata */}
            <div className="lg:col-span-1 space-y-6">
              
              {/* Status Header */}
              <div className="dashboard-card p-5 text-center flex flex-col items-center">
                {detail.is_flagged ? (
                  <div className="p-3.5 bg-red-500/10 text-red-400 rounded-full border border-red-500/20 mb-3 animate-pulse">
                    <ShieldAlert className="h-8 w-8" />
                  </div>
                ) : (
                  <div className="p-3.5 bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20 mb-3">
                    <ShieldCheck className="h-8 w-8" />
                  </div>
                )}
                
                <h3 className="text-sm font-bold font-outfit text-slate-200">
                  {detail.is_flagged ? "Flagged / Abusive" : "Clean / Approved"}
                </h3>
                <p className="text-[10px] text-slate-500 mt-1 font-mono">{detail.id}</p>
                
                <div className="mt-4 pt-4 border-t border-border-dark w-full flex justify-between text-xs">
                  <span className="text-slate-500">Status Code:</span>
                  <span className={`font-bold uppercase ${
                    detail.status === "approved"
                      ? "text-emerald-400"
                      : detail.status === "flagged"
                      ? "text-red-400"
                      : "text-blue-400"
                  }`}>
                    {detail.status}
                  </span>
                </div>
              </div>

              {/* General Metadata */}
              <div className="dashboard-card p-5 space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-1">
                  Metadata
                </h4>
                
                <div className="space-y-2 text-xs font-inter">
                  <div className="flex justify-between py-1 border-b border-border-dark/30">
                    <span className="text-slate-500 flex items-center gap-1.5">
                      <Hash className="h-3.5 w-3.5" />
                      Content Type
                    </span>
                    <span className="text-slate-300 font-mono capitalize">{detail.content_type}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-border-dark/30">
                    <span className="text-slate-500 flex items-center gap-1.5">
                      <Cpu className="h-3.5 w-3.5" />
                      Active Model
                    </span>
                    <span className="text-slate-300 font-mono">{detail.model || "—"}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-border-dark/30">
                    <span className="text-slate-500 flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Submitted
                    </span>
                    <span className="text-slate-300 font-mono text-[10px]">
                      {new Date(detail.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500 flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Actioned
                    </span>
                    <span className="text-slate-300 font-mono text-[10px]">
                      {new Date(detail.updated_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              </div>

            </div>

            {/* Right column: Source content & score bars */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Content Panel */}
              <div className="dashboard-card p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter">
                    Moderated Content
                  </h4>
                  <span className="text-[10px] text-slate-500 font-mono">{detail.content_type}</span>
                </div>
                <div className="bg-slate-900/60 border border-border-dark rounded-xl p-4 min-h-[80px]">
                  <p className="text-xs leading-relaxed text-slate-300 font-inter whitespace-pre-wrap">
                    {detail.content || "[Content Body Not Logged]"}
                  </p>
                </div>
              </div>

              {/* Score Bars */}
              <div className="dashboard-card p-5 space-y-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter">
                  Safety Category Metrics
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  {Object.entries(detail.scores).map(([category, score]) => {
                    const percent = Math.round(score * 100);
                    const isHigh = score > 0.5; // Threshold check
                    return (
                      <div key={category} className="p-3 bg-slate-900/30 border border-border-dark/60 rounded-xl space-y-2">
                        <div className="flex justify-between text-xs font-inter">
                          <span className="capitalize text-slate-300 font-semibold">
                            {category.replace("_", " ")}
                          </span>
                          <span className={`font-mono font-bold ${isHigh ? "text-red-400" : "text-slate-400"}`}>
                            {score.toFixed(4)}
                          </span>
                        </div>
                        
                        {/* Progress slider bar */}
                        <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-border-dark">
                          <div 
                            className={`h-full rounded-full transition-all duration-500 ${
                              isHigh ? "bg-red-500 shadow-md shadow-red-500/20" : "bg-brand-purple"
                            }`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>

          </div>
        )}

      </div>
    </div>
  );
}
