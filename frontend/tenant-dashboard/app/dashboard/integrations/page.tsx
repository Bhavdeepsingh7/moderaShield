"use client";

import React, { useState } from "react";
import { 
  Blocks, 
  Copy, 
  Check,
  Zap,
  BookOpen
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import { getStoredApiKey } from "@/lib/api/client";
import Link from "next/link";

export default function IntegrationsPage() {
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const userApiKey = getStoredApiKey() || "msk_your_key_here";

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

      </div>
    </div>
  );
}
