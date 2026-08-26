"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  History, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw,
  X
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { apiClient, RecentRequestsResponse } from "@/lib/api/client";

export default function SubmissionsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // State
  const [data, setData] = useState<RecentRequestsResponse | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const [searchId, setSearchId] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const fetchRequests = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Get requests (page, page_size)
      const res = await apiClient.getRequests(page, pageSize);
      setData(res);
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setError(err.message || "Failed to load submissions.");
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchRequests();
    }, 0);

    return () => clearTimeout(timer);
  }, [fetchRequests]);

  // Handle Search and local filters
  const filteredItems = useMemo(() => {
    if (!data) return [];

    let items = [...data.items];

    // Filter by ID
    if (searchId.trim()) {
      items = items.filter(item => 
        item.id.toLowerCase().includes(searchId.toLowerCase().trim())
      );
    }

    // Filter by Status
    if (statusFilter !== "all") {
      items = items.filter(item => item.status === statusFilter);
    }

    return items;
  }, [searchId, statusFilter, data]);

  const handleClearFilters = () => {
    setSearchId("");
    setStatusFilter("all");
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Submissions Log" 
        description="Verify raw API moderation history, status, and classification details" 
      />

      <div className="p-6 space-y-6 flex-grow max-w-7xl w-full mx-auto">
        
        {/* Controls Card */}
        <div className="dashboard-card p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex flex-1 w-full md:w-auto items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 md:max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={searchId}
                onChange={(e) => setSearchId(e.target.value)}
                placeholder="Search by Request ID..."
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-1.5 pl-10 pr-4 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
              />
            </div>

            {/* Status Filter */}
            <div className="relative">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900 border border-border-dark text-slate-300 text-xs rounded-lg py-1.5 px-3 outline-none cursor-pointer focus:border-brand-purple"
              >
                <option value="all">All Statuses</option>
                <option value="approved">Approved</option>
                <option value="flagged">Flagged</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {(searchId || statusFilter !== "all") && (
              <button 
                onClick={handleClearFilters}
                className="text-slate-500 hover:text-slate-300 p-1.5 rounded-lg border border-border-dark bg-slate-900 text-xs flex items-center gap-1"
                title="Clear Filters"
              >
                <X className="h-3 w-3" />
                <span className="hidden sm:inline">Clear</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto justify-end">
            <button 
              onClick={fetchRequests}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white border border-border-dark bg-slate-900 text-xs flex items-center gap-1"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Table Container */}
        {isLoading ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <Loader2Icon className="h-6 w-6 text-brand-purple animate-spin" />
            <span className="text-xs text-slate-500 font-mono mt-3">Fetching log database...</span>
          </div>
        ) : error ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-4">
              <X className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-bold font-outfit text-slate-300">Error loading submissions</h4>
            <p className="text-xs text-slate-500 max-w-sm mt-1 mb-4">{error}</p>
            <button 
              onClick={fetchRequests}
              className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-1.5 px-4 rounded-lg text-xs"
            >
              Retry
            </button>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <History className="h-8 w-8 text-slate-600 mb-3" />
            <h4 className="text-sm font-bold font-outfit text-slate-300">No submissions found</h4>
            <p className="text-xs text-slate-500 max-w-xs mt-1">
              There are no content logs matching your active search filters.
            </p>
          </div>
        ) : (
          <div className="dashboard-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border-dark bg-slate-900/40 text-slate-500 uppercase tracking-wider font-inter">
                    <th className="py-3 px-4 font-bold">Request ID</th>
                    <th className="py-3 px-4 font-bold">Content Type</th>
                    <th className="py-3 px-4 font-bold">Status</th>
                    <th className="py-3 px-4 font-bold">Categories</th>
                    <th className="py-3 px-4 font-bold">Model</th>
                    <th className="py-3 px-4 font-bold">Created At</th>
                    <th className="py-3 px-4 font-bold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/30 font-inter">
                  {filteredItems.map((item) => (
                    <tr 
                      key={item.id} 
                      className="hover:bg-slate-900/40 cursor-pointer"
                      onClick={() => router.push(`/dashboard/submissions/${item.id}`)}
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-300">
                        {item.id}
                      </td>
                      <td className="py-3 px-4 text-slate-400 capitalize">
                        {item.content_type}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-[4px] font-bold text-[9px] uppercase tracking-wide border ${
                          item.status === "approved"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : item.status === "flagged"
                            ? "bg-red-500/10 text-red-400 border-red-500/20"
                            : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                        }`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-[200px] truncate text-slate-300 font-semibold">
                        {item.categories.length > 0 
                          ? item.categories.join(", ") 
                          : <span className="text-slate-600 font-normal">—</span>}
                      </td>
                      <td className="py-3 px-4 text-slate-500 font-mono text-[10px]">
                        {item.model || "—"}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link 
                          href={`/dashboard/submissions/${item.id}`}
                          className="text-[10px] text-brand-purple hover:underline font-semibold"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Details →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination controls */}
            <div className="p-4 border-t border-border-dark flex items-center justify-between bg-slate-900/20 text-xs">
              <span className="text-slate-500">
                Showing <span className="text-slate-300 font-semibold">{filteredItems.length}</span> of{" "}
                <span className="text-slate-300 font-semibold">{data?.total || 0}</span> logs
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1 rounded bg-slate-900 border border-border-dark text-slate-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-slate-400">
                  Page <span className="text-slate-200 font-bold">{page}</span> of{" "}
                  <span className="text-slate-200 font-bold">{totalPages}</span>
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1 rounded bg-slate-900 border border-border-dark text-slate-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// Inline Loader Icon to avoid dynamic loading issues
function Loader2Icon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}
