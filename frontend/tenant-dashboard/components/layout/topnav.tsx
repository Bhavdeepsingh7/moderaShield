"use client";

import React, { useState, useEffect } from "react";
import { 
  Bell, 
  Wifi, 
  WifiOff, 
  Calendar,
  Info
} from "lucide-react";
import { apiClient } from "@/lib/api/client";

interface TopNavProps {
  title?: string;
  description?: string;
  dateRange?: string;
  setDateRange?: (range: string) => void;
  showDateSelector?: boolean;
}

export function TopNav({ 
  title, 
  description, 
  dateRange = "7d", 
  setDateRange,
  showDateSelector = false 
}: TopNavProps) {
  const [isLive, setIsLive] = useState<boolean | null>(null);
  const [notifications, setNotifications] = useState<string[]>([
    "Flag rate spiked above 5% on 2026-08-25",
    "Python SDK upgraded to v1.2.0",
    "New moderation request failure detected"
  ]);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    // Quick test connection
    apiClient.testConnection()
      .then(res => {
        setIsLive(res.ok);
      })
      .catch(() => {
        setIsLive(false);
      });
  }, []);

  return (
    <header className="h-16 border-b border-border-dark bg-background-dark/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-6">
      {/* Title / Info */}
      <div className="flex flex-col">
        <h1 className="text-base font-bold font-outfit text-white leading-tight">
          {title || "Dashboard"}
        </h1>
        {description && (
          <p className="text-[11px] text-slate-400 font-inter mt-0.5">
            {description}
          </p>
        )}
      </div>

      {/* Right side controls */}
      <div className="flex items-center gap-4">
        {/* Connection Status Badge */}
        {isLive !== null && (
          <div 
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold tracking-wide uppercase transition-all ${
              isLive 
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            }`}
            title={isLive ? "Connected to FastAPI backend" : "Offline. Running in high-fidelity mock mode"}
          >
            {isLive ? (
              <>
                <Wifi className="h-3 w-3 animate-pulse" />
                <span>Live Mode</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3" />
                <span>Demo Mode</span>
              </>
            )}
          </div>
        )}

        {/* Date Selector */}
        {showDateSelector && setDateRange && (
          <div className="flex items-center bg-slate-900 border border-border-dark rounded-md px-2.5 py-1 text-xs">
            <Calendar className="h-3.5 w-3.5 text-slate-400 mr-2" />
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="bg-transparent border-none text-slate-200 outline-none cursor-pointer pr-1"
            >
              <option value="7d">Last 7 Days</option>
              <option value="14d">Last 14 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
          </div>
        )}

        {/* Notification Bell */}
        <div className="relative">
          <button 
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors relative"
          >
            <Bell className="h-4.5 w-4.5" />
            {notifications.length > 0 && (
              <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-brand-purple" />
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-card-dark border border-border-dark rounded-lg shadow-2xl z-50 p-3 animate-fade-in">
              <div className="flex items-center justify-between pb-2 border-b border-border-dark mb-2">
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wide">Notifications</span>
                {notifications.length > 0 && (
                  <button 
                    onClick={() => setNotifications([])}
                    className="text-[10px] text-brand-purple hover:underline"
                  >
                    Clear All
                  </button>
                )}
              </div>
              <div className="space-y-2">
                {notifications.length > 0 ? (
                  notifications.map((n, idx) => (
                    <div key={idx} className="flex gap-2 p-2 hover:bg-slate-900/50 rounded-md">
                      <Info className="h-4 w-4 text-brand-purple flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-slate-300 leading-normal">{n}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 text-center py-4">No notifications</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
