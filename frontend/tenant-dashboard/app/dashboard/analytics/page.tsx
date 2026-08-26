"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  BarChart, 
  Bar,
  LineChart,
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { 
  Loader2,
  XCircle
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { apiClient, OverviewMetrics, UsageMetrics, CategoryMetrics } from "@/lib/api/client";

export default function AnalyticsPage() {
  const [dateRange, setDateRange] = useState("30d");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // States
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [usage, setUsage] = useState<UsageMetrics | null>(null);
  const [categories, setCategories] = useState<CategoryMetrics | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const days = dateRange === "90d" ? 90 : dateRange === "30d" ? 30 : dateRange === "14d" ? 14 : 7;
      
      const [ov, us, cat] = await Promise.all([
        apiClient.getOverview(),
        apiClient.getUsage(days),
        apiClient.getCategories()
      ]);

      setOverview(ov);
      setUsage(us);
      setCategories(cat);
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setError(err.message || "Failed to fetch analytics metrics.");
    } finally {
      setIsLoading(false);
    }
  }, [dateRange]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAnalytics();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchAnalytics]);

  const formatNum = (num?: number) => {
    if (num === undefined) return "0";
    return new Intl.NumberFormat().format(num);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
        <TopNav title="Analytics" description="Deep historical reporting and trends analysis" showDateSelector dateRange={dateRange} setDateRange={setDateRange} />
        <div className="p-6 space-y-6 flex-grow flex flex-col justify-center items-center">
          <Loader2 className="h-8 w-8 text-brand-purple animate-spin" />
          <span className="text-xs text-slate-400 font-mono">Compiling analytics reports...</span>
        </div>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
        <TopNav title="Analytics" description="Deep historical reporting and trends analysis" />
        <div className="p-6 flex-grow flex flex-col justify-center items-center text-center">
          <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-4">
            <XCircle className="h-8 w-8" />
          </div>
          <h3 className="text-lg font-bold font-outfit">Failed to load analytics</h3>
          <p className="text-sm text-slate-400 max-w-sm mt-1 mb-4">{error}</p>
          <button 
            onClick={fetchAnalytics}
            className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg text-xs"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Distribution chart data
  const categoryData = categories 
    ? Object.entries(categories.categories).map(([name, val]) => ({
        name: name.replace("_", " "),
        count: val
      })).sort((a, b) => b.count - a.count)
    : [];

  const donutData = [
    { name: "Approved", value: overview?.approved_requests || 0, color: "#10b981" },
    { name: "Flagged", value: overview?.flagged_requests || 0, color: "#ef4444" },
    { name: "Failed", value: overview?.failed_requests || 0, color: "#3b82f6" }
  ].filter(d => d.value > 0);

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Analytics" 
        description="Deep historical reporting and trends analysis" 
        showDateSelector 
        dateRange={dateRange} 
        setDateRange={setDateRange} 
      />

      <div className="p-6 space-y-6 flex-1 max-w-7xl w-full mx-auto font-inter text-xs">
        
        {/* KPI Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="dashboard-card p-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Scan Volume</span>
            <span className="text-xl font-extrabold text-white font-outfit mt-1.5 block">
              {formatNum(overview?.total_requests)}
            </span>
          </div>

          <div className="dashboard-card p-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Average Flag Rate</span>
            <span className="text-xl font-extrabold text-white font-outfit mt-1.5 block">
              {overview && overview.flag_rate !== undefined 
                ? `${(overview.flag_rate * 100).toFixed(2)}%` 
                : "0.0%"}
            </span>
          </div>

          <div className="dashboard-card p-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Failed Scan Ratio</span>
            <span className="text-xl font-extrabold text-white font-outfit mt-1.5 block">
              {overview && overview.total_requests 
                ? `${((overview.failed_requests / overview.total_requests) * 100).toFixed(1)}%` 
                : "0.0%"}
            </span>
          </div>

          <div className="dashboard-card p-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Processing Latency</span>
            <span className="text-xl font-extrabold text-white font-outfit mt-1.5 block">
              12ms <span className="text-[10px] text-slate-500 font-normal">avg</span>
            </span>
          </div>
        </div>

        {/* Top Historical Trend Chart */}
        <div className="dashboard-card p-5">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-4">
            Historical Requests Volume
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={usage?.days || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2338" />
                <XAxis 
                  dataKey="date" 
                  stroke="#64748b" 
                  fontSize={10} 
                  tickLine={false}
                />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#0c0f1d", borderColor: "#1e2338", borderRadius: "8px" }}
                  labelStyle={{ color: "#94a3b8", fontSize: "11px", fontFamily: "monospace" }}
                  itemStyle={{ fontSize: "12px", color: "#f8fafc" }}
                />
                <Line type="monotone" dataKey="requests" stroke="#8b5cf6" strokeWidth={2.5} name="Total Requests" dot={false} />
                <Line type="monotone" dataKey="flagged" stroke="#ef4444" strokeWidth={1.5} name="Flagged" dot={false} />
                <Line type="monotone" dataKey="approved" stroke="#10b981" strokeWidth={1.5} name="Approved" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Distribution row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Category Distribution (Horizontal bars) */}
          <div className="dashboard-card p-5">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-4">
              Category Distribution (Total Count)
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2338" horizontal={false} />
                  <XAxis type="number" stroke="#64748b" fontSize={10} tickLine={false} />
                  <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={10} tickLine={false} width={80} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#0c0f1d", borderColor: "#1e2338", borderRadius: "8px" }}
                    itemStyle={{ fontSize: "12px", color: "#f8fafc" }}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} name="Count" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Outcome Breakdown (Donut) */}
          <div className="dashboard-card p-5 flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter mb-4">
                Scan Outcomes Ratio
              </h3>
              <div className="h-52 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={donutData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={70}
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
              </div>
            </div>

            <div className="space-y-2 pt-4 border-t border-border-dark">
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

        </div>

      </div>
    </div>
  );
}
