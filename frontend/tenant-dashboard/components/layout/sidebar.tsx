"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { 
  Shield, 
  LayoutDashboard, 
  ListFilter, 
  History, 
  Key, 
  BookOpen, 
  Blocks, 
  Settings, 
  Sliders, 
  ChevronLeft, 
  ChevronRight, 
  LogOut,
  ChevronDown
} from "lucide-react";
import { getStoredTenant, removeStoredApiKey, getStoredApiKey } from "@/lib/api/client";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [tenant, setTenant] = useState({ id: "—", name: "Authenticated Tenant" });
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    const apiKey = getStoredApiKey();
    if (!apiKey) {
      router.push("/login");
      return;
    }
    const stored = getStoredTenant();
    if (stored) {
      setTimeout(() => {
        setTenant(stored);
      }, 0);
    }
  }, [pathname, router]);

  const navItems = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Moderation Queue", href: "/dashboard/queue", icon: ListFilter, badge: "Coming Soon" },
    { name: "Submissions", href: "/dashboard/submissions", icon: History },
    { name: "Rules & Thresholds", href: "/dashboard/rules", icon: Sliders },
    { name: "API Keys", href: "/dashboard/api-keys", icon: Key },
    { name: "Documentation", href: "/docs", icon: BookOpen },
    { name: "Integrations", href: "/dashboard/integrations", icon: Blocks },
    { name: "Settings", href: "/dashboard/settings", icon: Settings },
  ];

  const handleLogout = () => {
    removeStoredApiKey();
    router.push("/login");
  };

  return (
    <aside 
      className={`sticky top-0 h-screen flex flex-col bg-card-dark border-r border-border-dark transition-all duration-300 ${
        isCollapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border-dark">
        <Link href="/" className="flex items-center gap-2 overflow-hidden">
          <div className="p-1.5 bg-brand-purple/20 text-brand-purple rounded-lg brand-glow">
            <Shield className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <span className="font-semibold text-lg tracking-tight font-outfit text-white">
              Modera<span className="text-brand-purple">Shield</span>
            </span>
          )}
        </Link>
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="hidden md:flex p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* Tenant Selector */}
      {!isCollapsed ? (
        <div className="px-4 py-3 border-b border-border-dark">
          <label className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block mb-1">
            Tenant
          </label>
          <div className="flex items-center justify-between bg-slate-900/60 border border-border-dark rounded-md px-3 py-1.5 cursor-pointer hover:border-slate-700">
            <div className="flex flex-col overflow-hidden">
              <span className="text-xs font-semibold text-slate-200 truncate">{tenant.name}</span>
            </div>
            <ChevronDown className="h-3 w-3 text-slate-500 ml-2" />
          </div>
        </div>
      ) : (
        <div className="py-3 flex justify-center border-b border-border-dark">
          <div className="h-7 w-7 rounded-full bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-400">
            {tenant.name.substring(0, 2).toUpperCase()}
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all relative ${
                isActive 
                  ? "bg-brand-purple/10 text-white font-medium border-l-2 border-brand-purple" 
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/40"
              }`}
              title={isCollapsed ? item.name : undefined}
            >
              <Icon className={`h-4.5 w-4.5 flex-shrink-0 ${isActive ? "text-brand-purple" : "text-slate-400"}`} />
              {!isCollapsed && (
                <span className="truncate flex-1 font-inter">{item.name}</span>
              )}
              {!isCollapsed && item.badge && (
                <span className="text-[9px] bg-slate-800 text-slate-400 font-medium px-1.5 py-0.5 rounded">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="border-t border-border-dark p-3 relative">
        {showUserMenu && !isCollapsed && (
          <div className="absolute bottom-16 left-3 right-3 bg-slate-900 border border-border-dark rounded-lg p-1.5 shadow-xl z-50 animate-fade-in">
            <button 
              onClick={handleLogout}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-slate-800 rounded-md transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span>Log out</span>
            </button>
          </div>
        )}
        <div 
          onClick={() => !isCollapsed && setShowUserMenu(!showUserMenu)}
          className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
            isCollapsed ? "justify-center" : "hover:bg-slate-900/40"
          }`}
        >
          <div className="h-8 w-8 rounded-full bg-brand-purple/20 text-brand-purple flex items-center justify-center font-bold font-outfit border border-brand-purple/30">
            U
          </div>
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">Developer Admin</p>
              <p className="text-[10px] text-slate-500 truncate">admin@moderashield.dev</p>
            </div>
          )}
          {!isCollapsed && (
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          )}
        </div>
      </div>
    </aside>
  );
}
