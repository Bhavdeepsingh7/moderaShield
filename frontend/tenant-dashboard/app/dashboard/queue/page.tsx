"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { 
  ListFilter, 
  ShieldAlert, 
  ExternalLink, 
  Loader2, 
  Sparkles,
  Clock
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { apiClient, RecentRequestItem } from "@/lib/api/client";

export default function QueuePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [flaggedItems, setFlaggedItems] = useState<RecentRequestItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchFlagged = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.getRequests(1, 100);
      const flagged = res.items.filter(item => item.status === "flagged" || item.is_flagged === true);
      setFlaggedItems(flagged);
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setError(err.message || "Failed to load flagged queue.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchFlagged();
    }, 0);

    return () => clearTimeout(timer);
  }, [fetchFlagged]);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Moderation Queue" 
        description="Verify and audit flagged content items" 
      />

      <div className="p-6 space-y-6 flex-grow max-w-6xl w-full mx-auto">
        
        {/* Human Review Disclaimer Banner */}
        <div className="bg-brand-purple/10 border border-brand-purple/20 p-5 rounded-xl flex gap-4 items-start relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-brand-purple/5 rounded-full blur-xl" />
          <div className="p-2 bg-brand-purple/20 text-brand-purple rounded-lg flex-shrink-0 mt-0.5">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="space-y-1 z-10 font-inter">
            <h4 className="text-sm font-bold text-slate-200">Human review workflow coming soon</h4>
            <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
              We are developing a state-of-the-art interface that will allow moderators to assign cases, escalate, 
              and manually override automated moderation actions. For now, automatically flagged items are displayed below for audit purposes.
            </p>
          </div>
        </div>

        {/* Flagged Items */}
        {isLoading ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <Loader2 className="h-6 w-6 text-brand-purple animate-spin" />
            <span className="text-xs text-slate-500 font-mono mt-3">Loading flagged submissions...</span>
          </div>
        ) : error ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-4">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-bold font-outfit text-slate-300">Error loading queue</h4>
            <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">{error}</p>
            <button 
              onClick={fetchFlagged}
              className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-1.5 px-4 rounded-lg text-xs"
            >
              Retry
            </button>
          </div>
        ) : flaggedItems.length === 0 ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <div className="p-3 bg-slate-900 border border-border-dark text-slate-500 rounded-xl mb-3">
              <ListFilter className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-bold font-outfit text-slate-300">Queue is clean</h4>
            <p className="text-xs text-slate-500 max-w-xs mt-1">
              There are no flagged items awaiting review or audit in your system history.
            </p>
          </div>
        ) : (
          <div className="dashboard-card p-5">
            <div className="flex items-center justify-between pb-4 border-b border-border-dark mb-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter">
                Flagged Requests ({flaggedItems.length})
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border-dark text-slate-500 uppercase tracking-wider font-inter">
                    <th className="py-2.5 font-bold">Request ID</th>
                    <th className="py-2.5 font-bold">Content Type</th>
                    <th className="py-2.5 font-bold">Flags Triggered</th>
                    <th className="py-2.5 font-bold">Model</th>
                    <th className="py-2.5 font-bold">Time Detected</th>
                    <th className="py-2.5 font-bold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/40 font-inter">
                  {flaggedItems.map((item) => (
                    <tr 
                      key={item.id}
                      className="hover:bg-slate-900/20 cursor-pointer"
                      onClick={() => router.push(`/dashboard/submissions/${item.id}`)}
                    >
                      <td className="py-3.5 font-mono font-bold text-slate-300">
                        {item.id}
                      </td>
                      <td className="py-3.5 text-slate-400 capitalize">
                        {item.content_type}
                      </td>
                      <td className="py-3.5">
                        <div className="flex flex-wrap gap-1">
                          {item.categories.map((cat, idx) => (
                            <span 
                              key={idx} 
                              className="px-2 py-0.5 rounded-[4px] font-bold text-[9px] bg-red-500/10 text-red-400 border border-red-500/20 capitalize"
                            >
                              {cat.replace("_", " ")}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3.5 text-slate-500 font-mono text-[10px]">
                        {item.model}
                      </td>
                      <td className="py-3.5 text-slate-400">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5 text-slate-600" />
                          <span>{new Date(item.created_at).toLocaleString()}</span>
                        </div>
                      </td>
                      <td className="py-3.5 text-right">
                        <Link 
                          href={`/dashboard/submissions/${item.id}`}
                          className="text-[10px] text-brand-purple hover:underline font-semibold flex items-center justify-end gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <span>Inspect</span>
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
