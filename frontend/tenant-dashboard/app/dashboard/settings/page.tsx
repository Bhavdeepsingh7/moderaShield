"use client";

import React, { useState, useEffect } from "react";
import { 
  User, 
  Building, 
  Lock, 
  Bell, 
  Save, 
  Check, 
  ChevronRight
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { getStoredTenant } from "@/lib/api/client";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"profile" | "org" | "security" | "notifications">("profile");
  const [tenant, setTenant] = useState({ id: "—", name: "Authenticated Tenant" });
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Settings State
  const [profile, setProfile] = useState({
    name: "Developer Admin",
    email: "admin@moderashield.dev"
  });

  const [notificationConfig, setNotificationConfig] = useState({
    moderationSpike: true,
    weeklyReport: false,
    systemAlerts: true
  });

  useEffect(() => {
    const storedTenant = getStoredTenant();
    setTimeout(() => {
      if (storedTenant) {
        setTenant(storedTenant);
      }
    }, 0);
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2500);
  };

  const tabs = [
    { id: "profile", name: "My Profile", icon: User },
    { id: "org", name: "Organization Settings", icon: Building },
    { id: "security", name: "Security & Credentials", icon: Lock },
    { id: "notifications", name: "Notification Preferences", icon: Bell }
  ];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Account Settings" 
        description="Configure your ModeraShield profile and workspace parameters" 
      />

      <div className="p-6 space-y-6 flex-grow max-w-5xl w-full mx-auto font-inter text-xs">
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
          
          {/* Settings Tabs Sidebar */}
          <div className="md:col-span-1 space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as "profile" | "org" | "security" | "notifications")}
                  className={`w-full text-left flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors font-semibold ${
                    activeTab === tab.id
                      ? "bg-brand-purple/15 text-white border-l-2 border-brand-purple"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4" />
                    <span>{tab.name}</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
                </button>
              );
            })}
          </div>

          {/* Form Panel */}
          <div className="md:col-span-3 dashboard-card p-6">
            <form onSubmit={handleSave} className="space-y-6">
              
              {/* PROFILE TAB */}
              {activeTab === "profile" && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-200 pb-2 border-b border-border-dark mb-4">
                    Profile Information
                  </h3>
                  
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400">Full Name</label>
                    <input
                      type="text"
                      value={profile.name}
                      onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                      className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400">Email Address</label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple"
                    />
                  </div>
                </div>
              )}

              {/* ORGANIZATION TAB */}
              {activeTab === "org" && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-200 pb-2 border-b border-border-dark mb-4">
                    Workspace Details
                  </h3>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400">Organization Name</label>
                    <input
                      type="text"
                      value={tenant.name}
                      onChange={(e) => setTenant({ ...tenant, name: e.target.value })}
                      className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-slate-200 outline-none focus:border-brand-purple"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-400">Tenant identifier ID (Read-only)</label>
                    <input
                      type="text"
                      readOnly
                      value={tenant.id}
                      className="w-full bg-slate-900/60 border border-border-dark text-slate-500 font-mono rounded-lg py-2 px-3 outline-none select-all"
                    />
                  </div>

                  <div className="p-3 bg-slate-900/50 rounded-lg text-slate-500 leading-normal border border-border-dark">
                    Your workspace plan is configured as <span className="font-bold text-slate-300">Developer Free tier</span>. Quotas and limit constraints are managed based on tenant subscription agreements.
                  </div>
                </div>
              )}

              {/* SECURITY TAB */}
              {activeTab === "security" && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-200 pb-2 border-b border-border-dark mb-4">
                    Credentials & Active Sessions
                  </h3>

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-400">Current Password</label>
                      <input
                        type="password"
                        placeholder="••••••••••••"
                        className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-slate-200 outline-none focus:border-brand-purple"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-semibold text-slate-400">New Password</label>
                      <input
                        type="password"
                        placeholder="••••••••••••"
                        className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-slate-200 outline-none focus:border-brand-purple"
                      />
                    </div>
                  </div>

                  <div className="pt-4 border-t border-border-dark/60 space-y-2">
                    <label className="text-xs font-semibold text-slate-400 block mb-1">Active Sessions</label>
                    <div className="bg-slate-900/40 border border-border-dark rounded-lg p-3 flex justify-between items-center">
                      <div>
                        <p className="font-bold text-slate-300">Windows Chrome — Delhi, IN</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">Current Session • 2026-08-26</p>
                      </div>
                      <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-bold uppercase">
                        Online
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* NOTIFICATIONS TAB */}
              {activeTab === "notifications" && (
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-200 pb-2 border-b border-border-dark mb-4">
                    Alert Settings
                  </h3>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-slate-900/40 border border-border-dark rounded-lg">
                      <div>
                        <p className="font-bold text-slate-200">Moderation Spike Alerts</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">Receive email alerts if the classification flag rate exceeds 5% in an hour.</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={notificationConfig.moderationSpike}
                        onChange={(e) => setNotificationConfig({ ...notificationConfig, moderationSpike: e.target.checked })}
                        className="h-4.5 w-4.5 text-brand-purple rounded bg-slate-950 border-border-dark focus:ring-0"
                      />
                    </div>

                    <div className="flex items-center justify-between p-3 bg-slate-900/40 border border-border-dark rounded-lg">
                      <div>
                        <p className="font-bold text-slate-200">System Telemetry Updates</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">Receive notifications regarding database replication delays, latency reports, and updates.</p>
                      </div>
                      <input
                        type="checkbox"
                        checked={notificationConfig.systemAlerts}
                        onChange={(e) => setNotificationConfig({ ...notificationConfig, systemAlerts: e.target.checked })}
                        className="h-4.5 w-4.5 text-brand-purple rounded bg-slate-950 border-border-dark focus:ring-0"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Save footer */}
              <div className="pt-4 border-t border-border-dark flex items-center justify-between">
                <div>
                  {saveSuccess && (
                    <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-xs animate-pulse">
                      <Check className="h-4 w-4" />
                      <span>Changes saved locally!</span>
                    </div>
                  )}
                </div>
                <button
                  type="submit"
                  className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg flex items-center gap-1.5 transition-all brand-glow-hover"
                >
                  <Save className="h-4 w-4" />
                  <span>Save Settings</span>
                </button>
              </div>

            </form>
          </div>

        </div>

      </div>
    </div>
  );
}
