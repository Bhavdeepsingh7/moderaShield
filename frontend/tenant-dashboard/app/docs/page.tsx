"use client";

import React, { useState } from "react";
import Link from "next/link";
import { 
  Shield, 
  Terminal, 
  BookOpen, 
  Code, 
  Info, 
  Server, 
  Zap, 
  ArrowRight, 
  FileCode2, 
  Lock, 
  ArrowLeft
} from "lucide-react";
import { getStoredApiKey } from "@/lib/api/client";

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState("intro");
  const userApiKey = getStoredApiKey() || "msk_your_key_here";

  const docNavItems = [
    { id: "intro", title: "Introduction" },
    { id: "quickstart", title: "Quickstart" },
    { id: "auth", title: "Authentication" },
    { id: "text-mod", title: "Text Moderation" },
    { id: "python-sdk", title: "Python SDK" },
    { id: "errors", title: "Error Handling" },
    { id: "limits", title: "Rate Limits" },
    { id: "webhooks", title: "Webhooks" }
  ];

  return (
    <div className="min-h-screen bg-background-dark text-slate-100 flex flex-col font-sans">
      
      {/* Navigation Header */}
      <header className="h-16 border-b border-border-dark bg-background-dark/50 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="p-1.5 bg-brand-purple/20 text-brand-purple rounded-lg brand-glow">
              <Shield className="h-5 w-5" />
            </div>
            <span className="font-bold text-base tracking-tight font-outfit text-white">
              Modera<span className="text-brand-purple">Shield</span>
            </span>
          </Link>
          <span className="text-slate-500 font-bold text-xs uppercase tracking-wider font-mono">
            Docs v1.0
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link 
            href="/dashboard" 
            className="text-xs bg-slate-900 border border-border-dark hover:bg-slate-800 text-slate-200 font-bold py-1.5 px-3 rounded-lg transition-colors inline-flex items-center gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Console</span>
          </Link>
        </div>
      </header>

      {/* Workspace container */}
      <div className="flex flex-1 relative">
        
        {/* Left Side Navigation (Sticky) */}
        <aside className="hidden md:block w-64 border-r border-border-dark bg-card-dark p-4 sticky top-16 h-[calc(100vh-64px)] overflow-y-auto">
          <div className="space-y-4">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 font-inter px-3">
              Guides & API
            </div>
            <nav className="space-y-1">
              {docNavItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveSection(item.id);
                    document.getElementById(item.id)?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className={`w-full text-left px-3 py-2 text-xs rounded-lg transition-colors font-inter flex items-center justify-between ${
                    activeSection === item.id 
                      ? "bg-brand-purple/10 text-white font-semibold" 
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
                  }`}
                >
                  <span>{item.title}</span>
                </button>
              ))}
            </nav>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 md:p-12 overflow-y-auto max-w-4xl mx-auto space-y-16">
          
          {/* Introduction Section */}
          <section id="intro" className="space-y-4 pt-4">
            <h1 className="text-3xl font-extrabold font-outfit text-white tracking-tight">
              Moderate content with one API call.
            </h1>
            <p className="text-slate-400 font-inter text-sm leading-relaxed max-w-2xl">
              ModeraShield provides enterprise-grade content safety classification services. Incorporate our AI filter pipeline into chat systems, community forums, input boxes, and message streams to prevent abuse, hate, and harassment instantly.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <a 
                href="#quickstart" 
                className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg text-xs transition-all brand-glow-hover inline-flex items-center gap-1"
              >
                <span>Follow Quickstart</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </section>

          {/* Quickstart Section */}
          <section id="quickstart" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <Zap className="h-5 w-5 text-brand-purple" />
              <span>Quickstart Guide</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              Integrate ModeraShield into your application in three easy steps:
            </p>

            <div className="space-y-4 pl-2 font-inter text-xs">
              <div className="flex gap-3">
                <span className="h-5 w-5 bg-slate-900 border border-border-dark flex items-center justify-center font-bold font-mono rounded text-slate-300">1</span>
                <div>
                  <p className="font-semibold text-slate-200">Generate an API Key</p>
                  <p className="text-slate-400">Head over to the <Link href="/dashboard/api-keys" className="text-brand-purple hover:underline">API Keys console</Link> to generate your credential.</p>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="h-5 w-5 bg-slate-900 border border-border-dark flex items-center justify-center font-bold font-mono rounded text-slate-300">2</span>
                <div>
                  <p className="font-semibold text-slate-200">Install the Python SDK</p>
                  <p className="text-slate-400">Run the command: <code className="bg-slate-950 border border-border-dark px-1 py-0.5 rounded font-mono text-slate-200">pip install moderashield</code></p>
                </div>
              </div>

              <div className="flex gap-3">
                <span className="h-5 w-5 bg-slate-900 border border-border-dark flex items-center justify-center font-bold font-mono rounded text-slate-300">3</span>
                <div>
                  <p className="font-semibold text-slate-200">Submit Content for Classification</p>
                  <p className="text-slate-400">Call the text moderation method and read classification category scores.</p>
                </div>
              </div>
            </div>
          </section>

          {/* Authentication Section */}
          <section id="auth" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <Lock className="h-5 w-5 text-brand-purple" />
              <span>Authentication</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              API requests are authenticated using the custom HTTP Header <code className="bg-slate-950 border border-border-dark text-slate-200 font-mono px-1 py-0.5 rounded">X-API-Key</code>. Ensure you include this key header in all standard REST API requests.
            </p>

            <div className="bg-card-dark border border-border-dark p-4 rounded-xl space-y-2 font-inter text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 font-semibold">Your current console API key:</span>
              </div>
              <div className="bg-slate-950 p-2.5 rounded border border-border-dark font-mono text-[11px] text-brand-purple-light break-all select-all flex justify-between items-center">
                <span>{userApiKey}</span>
              </div>
            </div>
          </section>

          {/* Text Moderation Section */}
          <section id="text-mod" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-brand-purple" />
              <span>Text Moderation API</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              ModeraShield&apos;s text moderation is asynchronous under the hood, but our Python SDK handles polling automatically for synchronous wrappers.
            </p>

            <div className="space-y-2">
              <p className="text-xs font-bold text-slate-300 font-inter">HTTP Endpoint Definition</p>
              <div className="bg-slate-950 p-3 rounded-lg border border-border-dark font-mono text-xs text-slate-300 flex items-center gap-2">
                <span className="bg-emerald-500/10 text-emerald-400 font-bold px-1.5 py-0.5 rounded text-[10px]">POST</span>
                <span>/api/v1/moderate/</span>
              </div>
            </div>

            <div className="space-y-3 font-inter text-xs">
              <p className="font-semibold text-slate-300">Request Body Parameters</p>
              <table className="w-full text-left border-collapse border border-border-dark rounded-lg overflow-hidden">
                <thead>
                  <tr className="bg-slate-900 border-b border-border-dark text-slate-400 text-[10px] uppercase font-bold">
                    <th className="p-2.5">Field</th>
                    <th className="p-2.5">Type</th>
                    <th className="p-2.5">Required</th>
                    <th className="p-2.5">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/60 text-slate-300">
                  <tr>
                    <td className="p-2.5 font-mono text-brand-purple">content_type</td>
                    <td className="p-2.5 font-mono">string</td>
                    <td className="p-2.5 font-bold text-emerald-400">Yes</td>
                    <td className="p-2.5">Must be set to <code className="bg-slate-900 px-1 py-0.5 rounded text-slate-200">&quot;text&quot;</code></td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-mono text-brand-purple">content</td>
                    <td className="p-2.5 font-mono">string</td>
                    <td className="p-2.5 font-bold text-emerald-400">Yes</td>
                    <td className="p-2.5">The raw text payload to scan and moderate.</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Code Snippet block */}
            <div className="bg-card-dark border border-border-dark rounded-xl overflow-hidden font-mono text-xs">
              <div className="bg-slate-900 px-4 py-2 border-b border-border-dark text-slate-400 flex items-center gap-2">
                <Terminal className="h-4 w-4 text-brand-purple" />
                <span>cURL HTTP Example</span>
              </div>
              <pre className="p-4 bg-slate-950/40 text-slate-300 leading-relaxed overflow-x-auto">
{`curl -X POST http://localhost:8000/api/v1/moderate/ \\
  -H "X-API-Key: ${userApiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content_type": "text",
    "content": "Text to moderate"
  }'`}
              </pre>
            </div>
          </section>

          {/* Python SDK Section */}
          <section id="python-sdk" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <FileCode2 className="h-5 w-5 text-brand-purple" />
              <span>Python SDK Integration</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              Use our official Python SDK for clean, object-oriented syntax. It polls the async backend pipeline under the hood and executes with low-latency connection pools.
            </p>

            <div className="bg-card-dark border border-border-dark rounded-xl overflow-hidden font-mono text-xs">
              <div className="bg-slate-900 px-4 py-2 border-b border-border-dark text-slate-400 flex items-center gap-2">
                <Code className="h-4 w-4 text-brand-purple" />
                <span>Python SDK Example</span>
              </div>
              <pre className="p-4 bg-slate-950/40 text-slate-300 leading-relaxed overflow-x-auto">
{`from moderashield import Moderashield

# Initialize client
client = Moderashield(
    api_key="${userApiKey}"
)

# Submit request
result = client.moderate_text(
    "Text to moderate"
)

if result.is_flagged:
    print(f"Content Blocked! Triggered flags: {result.categories}")
    print(f"Toxic category score: {result.scores.get('toxic')}")
else:
    print("Content safe!")`}
              </pre>
            </div>
          </section>

          {/* Error Handling Section */}
          <section id="errors" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <Info className="h-5 w-5 text-brand-purple" />
              <span>Error Handling</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              Our API returns standard JSON error objects with detailed statuses:
            </p>

            <div className="space-y-3 font-inter text-xs">
              <table className="w-full text-left border-collapse border border-border-dark rounded-lg overflow-hidden">
                <thead>
                  <tr className="bg-slate-900 border-b border-border-dark text-slate-400 text-[10px] uppercase font-bold">
                    <th className="p-2.5">HTTP Code</th>
                    <th className="p-2.5">Name</th>
                    <th className="p-2.5">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/60 text-slate-300">
                  <tr>
                    <td className="p-2.5 font-mono text-red-400">400 Bad Request</td>
                    <td className="p-2.5 font-semibold">MalformedRequest</td>
                    <td className="p-2.5">Input query parameter or body payload syntax is invalid.</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-mono text-red-400">401 Unauthorized</td>
                    <td className="p-2.5 font-semibold">AuthenticationError</td>
                    <td className="p-2.5">The provided `X-API-Key` is missing, invalid, or revoked.</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-mono text-red-400">404 Not Found</td>
                    <td className="p-2.5 font-semibold">NotFoundError</td>
                    <td className="p-2.5">No moderation request matching the supplied ID exists.</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-mono text-red-400">422 Unprocessable</td>
                    <td className="p-2.5 font-semibold">ValidationError</td>
                    <td className="p-2.5">Input validation failed (e.g. content_type not supported).</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-mono text-red-400">500 Server Error</td>
                    <td className="p-2.5 font-semibold">ServerError</td>
                    <td className="p-2.5">ModeraShield encountered a database or backend processing worker failure.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Rate Limits */}
          <section id="limits" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <Server className="h-5 w-5 text-brand-purple" />
              <span>Rate Limits</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              Default rate limits are configured based on your tenant&apos;s plan:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-inter text-xs pt-1">
              <div className="bg-card-dark border border-border-dark p-3 rounded-lg">
                <span className="text-slate-500 font-bold block">Developer Plan</span>
                <span className="text-white text-base font-extrabold mt-1 block">60 requests/min</span>
              </div>
              <div className="bg-card-dark border border-border-dark p-3 rounded-lg">
                <span className="text-slate-500 font-bold block">Enterprise Plan</span>
                <span className="text-white text-base font-extrabold mt-1 block">Custom SLA</span>
              </div>
            </div>
          </section>

          {/* Webhooks Section */}
          <section id="webhooks" className="space-y-4 scroll-mt-20">
            <h2 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
              <Zap className="h-5 w-5 text-brand-purple" />
              <span>Webhooks</span>
            </h2>
            <p className="text-slate-400 font-inter text-xs leading-relaxed">
              Configure webhooks to receive real-time HTTP POST notifications on your server when a moderation request finishes processing (succeeds or fails).
            </p>

            <div className="space-y-3 font-inter text-xs">
              <p className="font-semibold text-slate-300">HTTP Headers sent to your server</p>
              <table className="w-full text-left border-collapse border border-border-dark rounded-lg overflow-hidden font-inter">
                <thead>
                  <tr className="bg-slate-900 border-b border-border-dark text-slate-400 text-[10px] uppercase font-bold">
                    <th className="p-2.5">Header</th>
                    <th className="p-2.5">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/60 text-slate-300">
                  <tr>
                    <td className="p-2.5 font-mono text-brand-purple">X-ModeraShield-Event-ID</td>
                    <td className="p-2.5">A unique UUID representing this event delivery task. Customers should use this ID to deduplicate deliveries and ensure idempotency.</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-mono text-brand-purple">X-ModeraShield-Signature</td>
                    <td className="p-2.5">Hex-encoded HMAC-SHA256 signature generated using the webhook secret over the raw HTTP request body bytes.</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-bold text-slate-300 font-inter">Payload Formats</p>
              
              <div className="bg-card-dark border border-border-dark rounded-xl overflow-hidden font-mono text-xs">
                <div className="bg-slate-900 px-4 py-2 border-b border-border-dark text-slate-400">
                  moderation.completed Event Payload
                </div>
                <pre className="p-4 bg-slate-950/40 text-slate-300 leading-relaxed overflow-x-auto">
{`{
  "event": "moderation.completed",
  "request_id": "82f7c229-3739-44b4-82ee-c1c5cb5a799a",
  "status": "flagged",
  "is_flagged": true,
  "categories": ["toxic"],
  "scores": {
    "toxic": 0.92
  },
  "model": "moderashield-text-v1"
}`}
                </pre>
              </div>

              <div className="bg-card-dark border border-border-dark rounded-xl overflow-hidden font-mono text-xs">
                <div className="bg-slate-900 px-4 py-2 border-b border-border-dark text-slate-400">
                  moderation.failed Event Payload
                </div>
                <pre className="p-4 bg-slate-950/40 text-slate-300 leading-relaxed overflow-x-auto">
{`{
  "event": "moderation.failed",
  "request_id": "82f7c229-3739-44b4-82ee-c1c5cb5a799a",
  "status": "failed"
}`}
                </pre>
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-bold text-slate-300 font-inter">Signature Verification Code (Python)</p>
              <p className="text-slate-400 font-inter text-xs leading-relaxed">
                To verify that a request was sent by ModeraShield and not tampered with, compute the HMAC-SHA256 signature using your webhook secret and verify it using constant-time comparison:
              </p>
              
              <div className="bg-card-dark border border-border-dark rounded-xl overflow-hidden font-mono text-xs">
                <div className="bg-slate-900 px-4 py-2 border-b border-border-dark text-slate-400">
                  Python Flask / FastAPI signature check
                </div>
                <pre className="p-4 bg-slate-950/40 text-slate-300 leading-relaxed overflow-x-auto">
{`import hmac
import hashlib

def verify_signature(raw_payload: bytes, signature_header: str, secret: str) -> bool:
    """
    raw_payload: Raw request body bytes (do not parse or format json before)
    signature_header: The value of X-ModeraShield-Signature header
    secret: The webhook secret generated in the dashboard
    """
    computed = hmac.new(
        secret.encode('utf-8'),
        raw_payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed, signature_header)
`}
                </pre>
              </div>
            </div>
          </section>

        </main>
      </div>
    </div>
  );
}
