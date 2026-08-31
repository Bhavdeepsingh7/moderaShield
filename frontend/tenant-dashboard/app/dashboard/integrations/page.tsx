"use client";

import React, { useState, useEffect } from "react";
import { 
  Blocks, 
  Copy, 
  Check,
  Zap,
  BookOpen,
  Trash2,
  AlertCircle,
  Eye,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
  ExternalLink
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { getStoredApiKey, apiClient, WebhookResponse, WebhookDeliveryResponse } from "@/lib/api/client";
import Link from "next/link";

export default function IntegrationsPage() {
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const userApiKey = getStoredApiKey() || "msk_your_key_here";

  // Webhooks State
  const [webhooks, setWebhooks] = useState<WebhookResponse[]>([]);
  const [newUrl, setNewUrl] = useState("");
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Deliveries State
  const [selectedWebhookId, setSelectedWebhookId] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDeliveryResponse[]>([]);
  const [isLoadingDeliveries, setIsLoadingDeliveries] = useState(false);

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.listWebhooks();
      setWebhooks(data);
    } catch (err: any) {
      setError(err.message || "Failed to load webhooks");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl) return;
    setIsLoading(true);
    setError(null);
    setCreatedSecret(null);
    try {
      const created = await apiClient.createWebhook(newUrl);
      setNewUrl("");
      setCreatedSecret(created.secret || null);
      await loadWebhooks();
    } catch (err: any) {
      setError(err.message || "Failed to create webhook");
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleWebhook = async (id: string, currentEnabled: boolean) => {
    try {
      setError(null);
      await apiClient.updateWebhook(id, !currentEnabled);
      await loadWebhooks();
    } catch (err: any) {
      setError(err.message || "Failed to update webhook");
    }
  };

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm("Are you sure you want to delete this webhook?")) return;
    try {
      setError(null);
      await apiClient.deleteWebhook(id);
      if (selectedWebhookId === id) {
        setSelectedWebhookId(null);
        setDeliveries([]);
      }
      await loadWebhooks();
    } catch (err: any) {
      setError(err.message || "Failed to delete webhook");
    }
  };

  const handleViewDeliveries = async (id: string) => {
    setSelectedWebhookId(id);
    setIsLoadingDeliveries(true);
    try {
      const data = await apiClient.getWebhookDeliveries(id);
      setDeliveries(data);
    } catch (err: any) {
      setError(err.message || "Failed to load deliveries");
    } finally {
      setIsLoadingDeliveries(false);
    }
  };

  const handleCopySecret = () => {
    if (!createdSecret) return;
    navigator.clipboard.writeText(createdSecret);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const handleCopyInstall = () => {
    navigator.clipboard.writeText("pip install moderashield");
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  const handleCopyCode = () => {
    const code = `from moderashield import Moderashield

client = Moderashield(api_key="${userApiKey}")
result = client.moderate_text("Content text to scan")

if result.is_flagged:
    print(f"Abuse detected: {result.categories}")`;
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const integrations = [
    { name: "Python SDK", status: "supported", lang: "python", icon: "🐍" },
    { name: "REST HTTP API", status: "supported", lang: "http", icon: "🌐" },
    { name: "Node.js / JS", status: "soon", lang: "javascript", icon: "🟨" },
    { name: "Go Lang", status: "soon", lang: "go", icon: "🔹" },
    { name: "Java SDK", status: "soon", lang: "java", icon: "☕" },
    { name: "Rust Crate", status: "soon", lang: "rust", icon: "🦀" }
  ];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Integrations & SDKs" 
        description="Connect your application streams to ModeraShield moderation workers" 
      />

      <div className="p-6 space-y-6 flex-grow max-w-6xl w-full mx-auto font-inter text-xs">
        
        {/* Languages Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {integrations.map((i) => (
            <div 
              key={i.name} 
              className={`dashboard-card p-4 text-center space-y-2 flex flex-col justify-between items-center ${
                i.status === "soon" ? "opacity-60 border-slate-900 bg-slate-950/20" : ""
              }`}
            >
              <div className="text-2xl">{i.icon}</div>
              <div className="space-y-0.5">
                <p className="font-bold text-slate-200">{i.name}</p>
                <span className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase ${
                  i.status === "supported" 
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                    : "bg-slate-900 text-slate-500 border border-slate-800"
                }`}>
                  {i.status === "supported" ? "Active" : "Coming Soon"}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* SDK Detail Card (col-span-2) */}
          <div className="dashboard-card p-6 lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-border-dark">
              <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <span>Python Integration Guide</span>
              </h3>
              <span className="text-[10px] bg-brand-purple/10 text-brand-purple-light font-bold px-2 py-0.5 rounded border border-brand-purple/20">
                Recommended
              </span>
            </div>

            {/* Install */}
            <div className="space-y-2">
              <p className="font-semibold text-slate-300">1. Install Package</p>
              <div className="bg-slate-950 p-3 rounded-lg border border-border-dark flex justify-between items-center font-mono">
                <span className="text-slate-300">pip install moderashield</span>
                <button 
                  onClick={handleCopyInstall}
                  className="p-1 rounded bg-slate-900 border border-border-dark text-slate-400 hover:text-white transition-colors"
                >
                  {copiedInstall ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>

            {/* Code Sample */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <p className="font-semibold text-slate-300">2. Implementation Example</p>
                <button 
                  onClick={handleCopyCode}
                  className="text-slate-500 hover:text-slate-300 flex items-center gap-1 font-semibold"
                >
                  {copiedCode ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                  <span>Copy Code</span>
                </button>
              </div>
              <div className="bg-slate-950 p-4 rounded-lg border border-border-dark font-mono leading-relaxed text-slate-300 overflow-x-auto">
                <pre>
{`from moderashield import Moderashield

# Initialize the client
client = Moderashield(api_key="${userApiKey}")

# Run moderation
result = client.moderate_text("This text is completely safe!")

if result.is_flagged:
    print(f"Content blocked: {result.categories}")
else:
    print("Content approved!")`}
                </pre>
              </div>
            </div>
          </div>

          {/* Quick links & tips (col-span-1) */}
          <div className="space-y-6 lg:col-span-1">
            <div className="dashboard-card p-5 space-y-4">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-inter">
                Integration Tips
              </h3>
              
              <div className="space-y-3 leading-relaxed text-slate-400">
                <div className="flex gap-2">
                  <Zap className="h-4 w-4 text-brand-purple flex-shrink-0 mt-0.5" />
                  <p>
                    <span className="font-bold text-slate-300">Fast Polling:</span> The SDK polls the async backend queue automatically to return results synchronously.
                  </p>
                </div>
                
                <div className="flex gap-2">
                  <Blocks className="h-4 w-4 text-brand-purple flex-shrink-0 mt-0.5" />
                  <p>
                    <span className="font-bold text-slate-300">Environment Keys:</span> You can omit the API key argument in python by setting the <code className="bg-slate-900 px-1 py-0.5 rounded text-brand-purple font-mono">MODERASHIELD_API_KEY</code> environment variable.
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-border-dark flex justify-center">
                <Link 
                  href="/docs" 
                  className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg text-xs w-full text-center inline-flex items-center justify-center gap-1.5"
                >
                  <BookOpen className="h-4 w-4" />
                  <span>View API Reference Docs</span>
                </Link>
              </div>
            </div>
          </div>

        </div>

        {/* WEBHOOKS MANAGEMENT SECTION */}
        <div className="dashboard-card p-6 space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-border-dark">
            <div>
              <h3 className="text-sm font-bold text-slate-200">Webhooks</h3>
              <p className="text-slate-400 text-[10px] mt-0.5">Configure webhooks to receive real-time, signed HTTP POST events on moderation completions or failures.</p>
            </div>
            <button 
              onClick={loadWebhooks}
              className="p-1.5 rounded bg-slate-900 border border-border-dark text-slate-400 hover:text-white transition-colors"
              title="Refresh webhooks list"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin text-brand-purple" : ""}`} />
            </button>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg flex items-center gap-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Webhook Secret Banner (Exposed only once upon creation) */}
          {createdSecret && (
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-4 rounded-lg space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-bold text-slate-200">Webhook Created Successfully!</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">Please copy this secret signature key now. For security reasons, you will not be able to see it again.</p>
                </div>
                <button 
                  onClick={() => setCreatedSecret(null)}
                  className="text-slate-400 hover:text-white text-xs font-bold"
                >
                  Dismiss
                </button>
              </div>
              <div className="bg-slate-950 p-2.5 rounded border border-border-dark flex justify-between items-center font-mono text-slate-200 overflow-x-auto text-[11px]">
                <span className="truncate mr-2">{createdSecret}</span>
                <button 
                  onClick={handleCopySecret}
                  className="p-1 rounded bg-slate-900 border border-border-dark text-slate-400 hover:text-white transition-colors flex-shrink-0"
                >
                  {copiedSecret ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
          )}

          {/* Create Webhook Form */}
          <form onSubmit={handleCreateWebhook} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end bg-slate-900/20 border border-border-dark p-4 rounded-lg">
            <div className="md:col-span-3 space-y-1">
              <label className="text-[10px] uppercase font-bold tracking-wider text-slate-500 block">
                Webhook URL
              </label>
              <input
                type="url"
                required
                placeholder="https://your-domain.com/webhook-receiver"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-slate-200 placeholder-slate-600 outline-none focus:border-brand-purple font-mono"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="bg-brand-purple hover:bg-brand-purple-dark disabled:opacity-50 text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center gap-1.5 transition-all w-full md:col-span-1 h-9"
            >
              <span>Add Webhook</span>
            </button>
          </form>

          {/* Webhooks List */}
          <div className="space-y-3">
            {webhooks.length === 0 ? (
              <div className="text-center p-6 text-slate-500 border border-dashed border-border-dark rounded-lg">
                No webhooks configured. Add a webhook URL to begin receiving automated event notifications.
              </div>
            ) : (
              webhooks.map((w) => (
                <div key={w.id} className="bg-slate-900/40 border border-border-dark rounded-lg p-4 space-y-3">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <p className="font-bold text-slate-200 font-mono truncate text-[11px] flex items-center gap-1.5">
                        <span>{w.url}</span>
                      </p>
                      <p className="text-[9px] text-slate-500 font-mono">
                        ID: {w.id} • Created: {new Date(w.created_at).toLocaleString()}
                      </p>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <button
                        onClick={() => handleToggleWebhook(w.id, w.enabled)}
                        className={`flex items-center gap-1 font-bold text-[10px] px-2 py-1 rounded transition-colors ${
                          w.enabled 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-slate-800 text-slate-400 border border-slate-700"
                        }`}
                      >
                        {w.enabled ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                        <span>{w.enabled ? "Enabled" : "Disabled"}</span>
                      </button>

                      <button
                        onClick={() => handleViewDeliveries(w.id)}
                        className={`flex items-center gap-1 font-bold text-[10px] px-2 py-1 rounded border transition-colors ${
                          selectedWebhookId === w.id 
                            ? "bg-brand-purple/10 border-brand-purple text-brand-purple-light"
                            : "bg-slate-900 border-border-dark text-slate-400 hover:text-white"
                        }`}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Deliveries</span>
                      </button>

                      <button
                        onClick={() => handleDeleteWebhook(w.id)}
                        className="p-1 rounded bg-slate-900 border border-border-dark text-red-400 hover:text-red-300 hover:border-red-500/30 transition-colors"
                        title="Delete Webhook"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Deliveries display */}
                  {selectedWebhookId === w.id && (
                    <div className="pt-3 border-t border-border-dark/60 space-y-2">
                      <h4 className="font-bold text-slate-400 text-[10px] uppercase tracking-wider flex items-center justify-between">
                        <span>Recent Deliveries Log</span>
                        {isLoadingDeliveries && <RefreshCw className="h-3 w-3 animate-spin text-brand-purple" />}
                      </h4>
                      
                      {isLoadingDeliveries ? (
                        <div className="text-center py-4 text-slate-500">Loading deliveries logs...</div>
                      ) : deliveries.length === 0 ? (
                        <div className="text-slate-500 text-[10px] py-1">No delivery logs for this webhook yet. Trigger a moderation request to send logs.</div>
                      ) : (
                        <div className="max-h-60 overflow-y-auto space-y-2 border border-border-dark bg-slate-950/40 p-2.5 rounded">
                          {deliveries.map((d) => (
                            <div key={d.id} className="text-[10px] font-mono flex flex-col md:flex-row md:items-start justify-between border-b border-border-dark/40 pb-2 last:border-b-0 last:pb-0 gap-2">
                              <div className="space-y-0.5">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ${
                                    d.status === "delivered" 
                                      ? "bg-emerald-500/10 text-emerald-400" 
                                      : d.status === "failed" 
                                        ? "bg-red-500/10 text-red-400" 
                                        : "bg-amber-500/10 text-amber-400 animate-pulse"
                                  }`}>
                                    {d.status}
                                  </span>
                                  <span className="text-slate-300 font-bold">{d.event_type}</span>
                                </div>
                                <div className="text-slate-500 text-[9px]">
                                  Request: {d.request_id} • EventID: {d.id}
                                </div>
                                {d.last_error && (
                                  <div className="text-red-400/80 text-[9px] max-w-lg break-all">
                                    Error: {d.last_error}
                                  </div>
                                )}
                              </div>
                              <div className="text-right text-slate-500 text-[9px] flex-shrink-0">
                                <p>Attempts: {d.attempt_count}</p>
                                <p>{new Date(d.created_at).toLocaleTimeString()}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
