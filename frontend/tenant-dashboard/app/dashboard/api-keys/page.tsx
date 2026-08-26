"use client";

import React, { useState, useEffect } from "react";
import { 
  Key, 
  Plus, 
  Trash2, 
  Copy, 
  Check, 
  AlertTriangle, 
  Loader2,
  X
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { 
  apiClient, 
  ApiKeyResponse, 
  ApiKeyCreatedResponse,
  getStoredTenant,
  getStoredApiKey
} from "@/lib/api/client";

export default function ApiKeysPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [keys, setKeys] = useState<ApiKeyResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  
  // Show key once state
  const [createdKeyData, setCreatedKeyData] = useState<ApiKeyCreatedResponse | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // Revoke state
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyResponse | null>(null);
  const [isRevoking, setIsRevoking] = useState(false);

  const fetchKeys = React.useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activeTenant = getStoredTenant() || { id: "—", name: "Authenticated Tenant" };
      const list = await apiClient.listApiKeys(activeTenant.id);
      setKeys(list);
    } catch {
      // Gracefully fall back to showing the active session key
      const sessionKey = getStoredApiKey();
      if (sessionKey) {
        setKeys([{
          id: "session-key",
          name: "Active Session Key",
          created_at: new Date().toISOString(),
          is_active: true,
          last_used_at: new Date().toISOString()
        }]);
      } else {
        setKeys([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchKeys();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchKeys]);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    setIsCreating(true);
    try {
      const activeTenant = getStoredTenant() || { id: "—", name: "Authenticated Tenant" };
      const newKey = await apiClient.createApiKey(activeTenant.id, newKeyName.trim());
      setCreatedKeyData(newKey);
      
      // refresh key list (will use our fallback if list is unsupported)
      fetchKeys();
      setNewKeyName("");
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      alert(err.message || "Failed to create API key");
    } finally {
      setIsCreating(false);
    }
  };

  const handleCopyKey = () => {
    if (!createdKeyData) return;
    navigator.clipboard.writeText(createdKeyData.key);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleRevokeKey = async () => {
    if (!keyToRevoke) return;
    setIsRevoking(true);
    try {
      const activeTenant = getStoredTenant() || { id: "—", name: "Authenticated Tenant" };
      await apiClient.revokeApiKey(activeTenant.id, keyToRevoke.id);
      
      // refresh
      fetchKeys();
      setKeyToRevoke(null);
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      alert(err.message || "Failed to revoke API key");
      setKeyToRevoke(null);
    } finally {
      setIsRevoking(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="API Keys" 
        description="Credentials for authenticating moderation requests" 
      />

      <div className="p-6 space-y-6 flex-grow max-w-6xl w-full mx-auto">
        
        {/* Intro Box */}
        <div className="dashboard-card p-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 max-w-xl font-inter">
            <h3 className="text-sm font-bold text-slate-200">Connect to ModeraShield</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Use API keys to authenticate moderation requests from your services. Add the <code className="bg-slate-900 border border-border-dark px-1.5 py-0.5 rounded font-mono text-brand-purple">X-API-Key</code> header to your HTTP requests to begin.
            </p>
          </div>
          <button
            onClick={() => {
              setCreatedKeyData(null);
              setShowCreateModal(true);
            }}
            className="flex-shrink-0 bg-brand-purple hover:bg-brand-purple-dark text-white font-bold text-xs px-4 py-2 rounded-lg transition-all brand-glow-hover flex items-center gap-1.5"
          >
            <Plus className="h-4 w-4" />
            <span>Create API Key</span>
          </button>
        </div>

        {/* Warning Note */}
        <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-xs leading-normal font-inter flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>Note: Key listing and revocation are not supported by the backend API yet. Only the active session key is displayed in this list. Newly created keys will be shown only once upon generation.</span>
        </div>

        {/* Keys List */}
        {isLoading ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <Loader2 className="h-6 w-6 text-brand-purple animate-spin" />
            <span className="text-xs text-slate-500 font-mono mt-3">Loading credentials...</span>
          </div>
        ) : error ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-4">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-bold font-outfit text-slate-300">Error loading keys</h4>
            <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
            <button 
              onClick={fetchKeys}
              className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-1.5 px-4 rounded-lg text-xs"
            >
              Retry
            </button>
          </div>
        ) : keys.length === 0 ? (
          <div className="dashboard-card p-12 text-center flex flex-col justify-center items-center h-80">
            <div className="p-3 bg-slate-900 border border-border-dark text-slate-500 rounded-xl mb-3">
              <Key className="h-6 w-6" />
            </div>
            <h4 className="text-sm font-bold font-outfit text-slate-300">No API keys generated</h4>
            <p className="text-xs text-slate-500 max-w-xs mt-1">
              Create an API key above to start integrating the ModeraShield platform.
            </p>
          </div>
        ) : (
          <div className="dashboard-card p-5">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border-dark text-slate-500 uppercase tracking-wider font-inter">
                    <th className="py-2.5 font-bold">Name</th>
                    <th className="py-2.5 font-bold">Prefix</th>
                    <th className="py-2.5 font-bold">Created</th>
                    <th className="py-2.5 font-bold">Status</th>
                    <th className="py-2.5 font-bold">Last Used</th>
                    <th className="py-2.5 font-bold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/40 font-inter text-slate-300">
                  {keys.map((key) => (
                    <tr key={key.id} className="hover:bg-slate-900/10">
                      <td className="py-3.5 font-semibold">{key.name}</td>
                      <td className="py-3.5 font-mono text-slate-400">
                        msk_...
                      </td>
                      <td className="py-3.5 text-slate-400">
                        {new Date(key.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5">
                        <span className={`px-2 py-0.5 rounded-[4px] font-bold text-[9px] uppercase tracking-wide border ${
                          key.is_active
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-slate-800 text-slate-500 border-slate-700"
                        }`}>
                          {key.is_active ? "Active" : "Revoked"}
                        </span>
                      </td>
                      <td className="py-3.5 text-slate-400">
                        {key.last_used_at ? (
                          <span>{new Date(key.last_used_at).toLocaleDateString()}</span>
                        ) : (
                          <span className="text-slate-600">Never</span>
                        )}
                      </td>
                      <td className="py-3.5 text-right">
                        {key.is_active && (
                          <button
                            onClick={() => setKeyToRevoke(key)}
                            className="text-red-400 hover:text-red-300 p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                            title="Revoke key"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* CREATE KEY MODAL */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-card-dark border border-border-dark rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-fade-in">
              <div className="flex justify-between items-center pb-2 border-b border-border-dark">
                <h3 className="text-base font-bold font-outfit text-white">Create API Key</h3>
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="h-4.5 w-4.5" />
                </button>
              </div>

              {!createdKeyData ? (
                <form onSubmit={handleCreateKey} className="space-y-4 font-inter">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-300">Key Name</label>
                    <input
                      type="text"
                      required
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      placeholder="e.g. Production Backend"
                      className="w-full bg-slate-900 border border-border-dark rounded-lg py-2 px-3 text-xs text-slate-200 outline-none focus:border-brand-purple"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="w-full bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 rounded-lg text-xs transition-all brand-glow-hover flex items-center justify-center gap-1.5 disabled:opacity-50"
                  >
                    {isCreating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                    <span>Generate Key</span>
                  </button>
                </form>
              ) : (
                <div className="space-y-4 font-inter">
                  <div className="p-3 bg-brand-purple/10 border border-brand-purple/20 text-brand-purple rounded-lg text-xs font-semibold flex items-center gap-2">
                    <Key className="h-4.5 w-4.5 flex-shrink-0 animate-pulse" />
                    <span>Your key has been created successfully</span>
                  </div>

                  <p className="text-[11px] text-slate-400 leading-normal">
                    This is your secret key. For security, we won&apos;t show it again. Copy and store it immediately in a safe location.
                  </p>

                  <div className="flex items-center bg-slate-900 border border-border-dark rounded-lg p-2.5 justify-between">
                    <span className="font-mono text-xs select-all break-all text-white font-bold">
                      {createdKeyData.key}
                    </span>
                    <button
                      onClick={handleCopyKey}
                      className="ml-2 p-1.5 rounded-lg border border-border-dark bg-slate-950 text-slate-400 hover:text-white transition-colors"
                      title="Copy to clipboard"
                    >
                      {isCopied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                    </button>
                  </div>

                  <button
                    onClick={() => {
                      setShowCreateModal(false);
                      setCreatedKeyData(null);
                    }}
                    className="w-full bg-slate-900 hover:bg-slate-800 border border-border-dark text-slate-300 font-bold py-2 rounded-lg text-xs transition-colors"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* REVOKE CONFIRM MODAL */}
        {keyToRevoke && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-card-dark border border-border-dark rounded-xl max-w-sm w-full p-6 shadow-2xl space-y-4 animate-fade-in text-center">
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-full w-fit mx-auto">
                <AlertTriangle className="h-6 w-6" />
              </div>
              
              <div className="space-y-1">
                <h3 className="text-sm font-bold font-outfit text-slate-200">Revoke API Key?</h3>
                <p className="text-xs text-slate-400 leading-relaxed font-inter">
                  Are you sure you want to revoke <span className="font-semibold text-slate-200">&quot;{keyToRevoke.name}&quot;</span>? 
                  Any active service using this key will immediately receive 401 Unauthorized errors. This action cannot be undone.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2 font-inter">
                <button
                  onClick={() => setKeyToRevoke(null)}
                  disabled={isRevoking}
                  className="bg-slate-900 hover:bg-slate-800 border border-border-dark text-slate-300 font-bold py-2 rounded-lg text-xs transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRevokeKey}
                  disabled={isRevoking}
                  className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 rounded-lg text-xs transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  {isRevoking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                  <span>Revoke Key</span>
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
