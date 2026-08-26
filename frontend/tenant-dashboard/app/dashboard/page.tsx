"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { 
  BarChart3, 
  Shield, 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  TrendingUp, 
  Clock, 
  ExternalLink,
  Loader2
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { 
  apiClient, 
  OverviewMetrics, 
  CategoryMetrics, 
  UsageMetrics, 
  RecentRequestsResponse,
  getStoredApiKey,
  removeStoredApiKey
} from "@/lib/api/client";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";

export default function DashboardOverview() {
  const router = useRouter();
  const [dateRange, setDateRange] = useState("7d");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Data States
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [categories, setCategories] = useState<CategoryMetrics | null>(null);
  const [usage, setUsage] = useState<UsageMetrics | null>(null);
  const [requests, setRequests] = useState<RecentRequestsResponse | null>(null);
  
  const fetchDashboardData = useCallback(async () => {
    const apiKey = getStoredApiKey();
    if (!apiKey) {
      router.push("/login");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      // Test backend connection
      const conn = await apiClient.testConnection();
      if (!conn.ok) {
        if (conn.message.includes("API key") || conn.message.includes("X-API-Key")) {
          removeStoredApiKey();
          router.push("/login");
          return;
        }
        throw new Error(conn.message || "Failed to load dashboard data.");
      }

      // Fetch all metrics concurrently
      const days = dateRange === "30d" ? 30 : dateRange === "14d" ? 14 : 7;
      const [ov, cat, us, req] = await Promise.all([
        apiClient.getOverview(),
        apiClient.getCategories(),
        apiClient.getUsage(days),
        apiClient.getRequests(1, 5)
      ]);

      setOverview(ov);
      setCategories(cat);
      setUsage(us);
      setRequests(req);
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setError(err.message || "Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  }, [dateRange, router]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchDashboardData();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchDashboardData]);

  // Formatter for numbers
  const formatNum = (num?: number) => {
    if (num === undefined) return "0";
    return new Intl.NumberFormat().format(num);
  };

  // Skeletons
  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
        <TopNav title="Overview" description="Monitor moderation activity and system health" showDateSelector dateRange={dateRange} setDateRange={setDateRange} />
        <div className="p-6 space-y-6 flex-grow flex flex-col justify-center items-center">
          <Loader2 className="h-8 w-8 text-brand-purple animate-spin" />
          <span className="text-xs text-slate-400 font-mono">Loading ModeraShield telemetry...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !overview) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
        <TopNav title="Overview" description="Monitor moderation activity and system health" />
        <div className="p-6 flex-grow flex flex-col justify-center items-center text-center">
          <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-4">
            <XCircle className="h-8 w-8" />
          </div>
          <h3 className="text-lg font-bold font-outfit">Unable to load metrics</h3>
          <p className="text-sm text-slate-400 max-w-sm mt-1 mb-4">{error}</p>
          <button 
            onClick={fetchDashboardData}
            className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg text-xs"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Render Charts Data
  const donutData = [
    { name: "Approved", value: overview?.approved_requests || 0, color: "#10b981" },
    { name: "Flagged", value: overview?.flagged_requests || 0, color: "#ef4444" },
    { name: "Failed", value: overview?.failed_requests || 0, color: "#3b82f6" }
  ].filter(d => d.value > 0);

  // Fallback if no requests recorded
  const isDataEmpty = !overview || overview.total_requests === 0;

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Overview" 
        description="Monitor moderation activity and system health" 
        showDateSelector 
        dateRange={dateRange} 
        setDateRange={setDateRange} 
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto">
        
        {/* KPI Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* Card 1: Total Submissions */}
          <div className="dashboard-card p-4">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider font-inter">Total Submissions</span>
              <BarChart3 className="h-4 w-4 text-slate-500" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold font-outfit text-white">
                {formatNum(overview?.total_requests)}
              </span>
            </div>
            <p className="text-[9px] text-slate-500 font-inter mt-1">Requests processed this period</p>
          </div>

          {/* Card 2: Auto Approved */}
          <div className="dashboard-card p-4">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider font-inter">Auto Actions</span>
              <CheckCircle className="h-4 w-4 text-emerald-500" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold font-outfit text-white">
                {formatNum(overview?.approved_requests)}
              </span>
            </div>
            <p className="text-[9px] text-slate-500 font-inter mt-1">Approved automatically by AI</p>
          </div>

          {/* Card 3: Escalated to Review */}
          <div className="dashboard-card p-4">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider font-inter">Escalated to Review</span>
              <AlertTriangle className="h-4 w-4 text-amber-500" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold font-outfit text-white">0</span>
            </div>
            <p className="text-[9px] text-slate-500 font-inter mt-1">Review workflow coming soon</p>
          </div>

          {/* Card 4: Blocked / Flagged */}
          <div className="dashboard-card p-4">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider font-inter">Blocked / Flagged</span>
              <XCircle className="h-4 w-4 text-red-500" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold font-outfit text-white">
                {formatNum(overview?.flagged_requests)}
              </span>
            </div>
            <p className="text-[9px] text-slate-500 font-inter mt-1">Content flagged as abusive</p>
          </div>

          {/* Card 5: Flag Rate */}
          <div className="dashboard-card p-4">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider font-inter">Flag Rate</span>
              <TrendingUp className="h-4 w-4 text-brand-purple" />
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold font-outfit text-white">
                {overview && overview.flag_rate !== undefined 
                  ? `${(overview.flag_rate * 100).toFixed(1)}%` 
                  : "0.0%"}
              </span>
            </div>
            <p className="text-[9px] text-slate-500 font-inter mt-1">Flagged / Total ratio</p>
          </div>
        </div>

        {isDataEmpty ? (
          <div className="dashboard-card p-12 text-center flex flex-col items-center justify-center">
            <Shield className="h-12 w-12 text-slate-600 mb-4 animate-pulse" />
            <h3 className="text-base font-bold font-outfit text-slate-300">No moderation requests yet</h3>
            <p className="text-xs text-slate-500 font-inter max-w-sm mt-1 mb-4">
              Get an API Key and send content requests to start visualizing real-time metrics.
            </p>
            <Link 
              href="/dashboard/api-keys" 
              className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg text-xs"
            >
              Generate API Key
            </Link>
          </div>
        ) : (
          <>
            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Pie/Donut Breakdown */}
              <div className="dashboard-card p-5 lg:col-span-1 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-4">
                    Moderation Breakdown
                  </h3>
                  <div className="h-56 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={donutData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={4}
                          dataKey="value"
                        >
                          {donutData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{ backgroundColor: "#0c0f1d", borderColor: "#1e2338", borderRadius: "8px" }}
                          itemStyle={{ color: "#f8fafc", fontSize: "12px" }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute flex flex-col items-center justify-center">
                      <span className="text-xs text-slate-500 uppercase tracking-wider font-bold">Total</span>
                      <span className="text-xl font-extrabold text-white font-outfit">
                        {formatNum(overview?.total_requests)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 mt-4 pt-4 border-t border-border-dark">
                  {donutData.map((d) => {
                    const pct = overview?.total_requests 
                      ? ((d.value / overview.total_requests) * 100).toFixed(1)
                      : "0.0";
                    return (
                      <div key={d.name} className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                          <span className="text-slate-300 font-semibold">{d.name}</span>
                        </div>
                        <span className="text-slate-400 font-mono">
                          {formatNum(d.value)} ({pct}%)
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Submissions Over Time */}
              <div className="dashboard-card p-5 lg:col-span-2 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter">
                      Submissions Over Time
                    </h3>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={usage?.days || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e2338" />
                        <XAxis 
                          dataKey="date" 
                          stroke="#64748b" 
                          fontSize={10} 
                          tickLine={false} 
                          tickFormatter={(str) => {
                            const date = new Date(str);
                            return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
                          }}
                        />
                        <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: "#0c0f1d", borderColor: "#1e2338", borderRadius: "8px" }}
                          labelStyle={{ color: "#94a3b8", fontSize: "11px", fontFamily: "monospace" }}
                          itemStyle={{ fontSize: "12px", color: "#f8fafc" }}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="requests" 
                          stroke="#8b5cf6" 
                          strokeWidth={2}
                          fillOpacity={1} 
                          fill="url(#colorRequests)" 
                          name="Requests"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Row Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Recent Submissions (col-span-2) */}
              <div className="dashboard-card p-5 lg:col-span-2 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter">
                      Recent Submissions
                    </h3>
                    <Link 
                      href="/dashboard/submissions" 
                      className="text-[10px] text-brand-purple font-semibold hover:underline flex items-center gap-1"
                    >
                      <span>View all</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-border-dark text-slate-500 uppercase tracking-wider">
                          <th className="py-2.5 font-bold">Request ID</th>
                          <th className="py-2.5 font-bold">Status</th>
                          <th className="py-2.5 font-bold">Categories</th>
                          <th className="py-2.5 font-bold">Model</th>
                          <th className="py-2.5 font-bold text-right">Time</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-dark/40">
                        {requests?.items.map((item) => (
                          <tr 
                            key={item.id} 
                            className="hover:bg-slate-900/20 cursor-pointer"
                            onClick={() => router.push(`/dashboard/submissions/${item.id}`)}
                          >
                            <td className="py-3 font-mono font-bold text-slate-300">
                              {item.id.substring(0, 12)}...
                            </td>
                            <td className="py-3">
                              <span className={`px-2 py-0.5 rounded-[4px] font-bold text-[10px] uppercase tracking-wide border ${
                                item.status === "approved"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : item.status === "flagged"
                                  ? "bg-red-500/10 text-red-400 border-red-500/20"
                                  : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                              }`}>
                                {item.status}
                              </span>
                            </td>
                            <td className="py-3 max-w-[150px] truncate text-slate-400 font-inter">
                              {item.categories.length > 0 
                                ? item.categories.join(", ") 
                                : <span className="text-slate-600">—</span>}
                            </td>
                            <td className="py-3 text-slate-500 font-mono text-[10px]">{item.model}</td>
                            <td className="py-3 text-right text-slate-500 font-inter">
                              {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Sidebar column: Health, Limits, Categories */}
              <div className="space-y-6 lg:col-span-1">
                
                {/* System Health */}
                <div className="dashboard-card p-5">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-3">
                    System Health
                  </h3>
                  
                  <div className="p-3 bg-slate-900/50 rounded-lg text-slate-500 text-xs font-inter border border-border-dark flex items-center gap-2">
                    <Clock className="h-4 w-4 text-slate-500 flex-shrink-0" />
                    <span>System health monitoring coming soon</span>
                  </div>
                </div>

                {/* Usage & Limits */}
                <div className="dashboard-card p-5">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-3">
                    Usage & Limits
                  </h3>
                  <div className="space-y-2 font-inter">
                    <div className="flex justify-between items-baseline">
                      <span className="text-xs text-slate-400">Requests this period:</span>
                      <span className="text-base font-extrabold text-white font-mono">
                        {formatNum(overview?.total_requests)}
                      </span>
                    </div>
                    <div className="p-2.5 bg-slate-900/50 rounded-lg text-[10px] text-slate-500 leading-normal border border-border-dark">
                      Usage limits will appear when plan limits are configured.
                    </div>
                  </div>
                </div>

                {/* Top Categories */}
                <div className="dashboard-card p-5">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-4">
                    Top Categories
                  </h3>
                  
                  <div className="space-y-3">
                    {categories && Object.keys(categories.categories).length > 0 ? (
                      Object.entries(categories.categories)
                        .sort((a, b) => b[1] - a[1])
                        .map(([catName, count]) => {
                          // Find total matching categories
                          const maxCount = Math.max(...Object.values(categories.categories));
                          const percent = maxCount > 0 ? (count / maxCount) * 100 : 0;
                          return (
                            <div key={catName} className="space-y-1">
                              <div className="flex justify-between text-xs font-inter">
                                <span className="capitalize text-slate-300 font-semibold">{catName.replace("_", " ")}</span>
                                <span className="font-mono text-slate-400">{formatNum(count)}</span>
                              </div>
                              <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden border border-border-dark">
                                <div 
                                  className="h-full bg-brand-purple rounded-full" 
                                  style={{ width: `${percent}%` }}
                                />
                              </div>
                            </div>
                          );
                        })
                    ) : (
                      <p className="text-xs text-slate-600">No categories flagged yet</p>
                    )}
                  </div>
                </div>

              </div>

            </div>
          </>
        )}

      </div>
    </div>
  );
}
