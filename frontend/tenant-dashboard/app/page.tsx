"use client";

import React, { useState } from "react";
import Link from "next/link";
import { 
  Shield, 
  ArrowRight, 
  Cpu, 
  Lock, 
  BarChart3, 
  Volume2, 
  Image as ImageIcon,
  MessageSquare,
  Sparkles
} from "lucide-react";
import { apiClient } from "@/lib/api/client";

interface SimResult {
  status: string;
  is_flagged: boolean | null;
  model: string;
  latency: string;
  scores: Record<string, number>;
}

export default function LandingPage() {
  const [inputText, setInputText] = useState("Let's build a safe, respectful community together!");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simResult, setSimResult] = useState<SimResult>({
    status: "approved",
    is_flagged: false,
    model: "moderashield-text-v1",
    latency: "14ms",
    scores: {
      toxic: 0.012,
      insult: 0.008,
      threat: 0.001,
      obscene: 0.004,
      severe_toxic: 0.0002,
      identity_hate: 0.0005
    }
  });

  const [activeTab, setActiveTab] = useState<"python" | "curl">("python");

  const runSimulation = async () => {
    setIsSimulating(true);
    const start = performance.now();
    try {
      const res = await apiClient.createModerationRequest(inputText);
      
      let detail = await apiClient.getRequestDetail(res.id);
      let attempts = 0;
      const maxAttempts = 10;
      
      while (
        detail.status !== "approved" && 
        detail.status !== "flagged" && 
        detail.status !== "failed" && 
        attempts < maxAttempts
      ) {
        await new Promise(r => setTimeout(r, 500));
        detail = await apiClient.getRequestDetail(res.id);
        attempts++;
      }
      
      const end = performance.now();
      
      setSimResult({
        status: detail.status,
        is_flagged: detail.is_flagged ?? (detail.status === "flagged"),
        model: detail.model || "moderashield-text-v1",
        latency: `${Math.round(end - start)}ms`,
        scores: detail.scores
      });
    } catch {
      // Offline fallback
      const isToxic = /toxic|hate|kill|idiot|stupid|hurt|threat/i.test(inputText);
      await new Promise(r => setTimeout(r, 500));
      setSimResult({
        status: isToxic ? "flagged" : "approved",
        is_flagged: isToxic,
        model: "moderashield-text-v1",
        latency: "18ms",
        scores: {
          toxic: isToxic ? 0.94 : 0.03,
          insult: isToxic && inputText.includes("idiot") ? 0.91 : 0.01,
          threat: isToxic && inputText.includes("kill") ? 0.97 : 0.002,
          obscene: isToxic ? 0.45 : 0.005,
          severe_toxic: isToxic ? 0.12 : 0.001,
          identity_hate: isToxic ? 0.08 : 0.002
        }
      });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-background-dark text-slate-100 selection:bg-brand-purple/30 selection:text-white">
      {/* Navigation Header */}
      <header className="h-20 border-b border-border-dark bg-background-dark/50 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6 md:px-12">
        <Link href="/" className="flex items-center gap-2">
          <div className="p-1.5 bg-brand-purple/20 text-brand-purple rounded-lg brand-glow">
            <Shield className="h-6 w-6" />
          </div>
          <span className="font-bold text-xl tracking-tight font-outfit text-white">
            Modera<span className="text-brand-purple">Shield</span>
          </span>
        </Link>
        
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm text-slate-300 hover:text-white transition-colors">Features</a>
          <a href="#simulator" className="text-sm text-slate-300 hover:text-white transition-colors">Simulator</a>
          <a href="#sdk" className="text-sm text-slate-300 hover:text-white transition-colors">Developer SDK</a>
          <Link href="/docs" className="text-sm text-slate-300 hover:text-white transition-colors">API Docs</Link>
        </div>

        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm text-slate-300 hover:text-white font-medium px-4 py-2">
            Sign In
          </Link>
          <Link 
            href="/signup" 
            className="text-sm bg-brand-purple hover:bg-brand-purple-dark text-white font-semibold px-4 py-2 rounded-lg transition-all brand-glow-hover flex items-center gap-1.5"
          >
            <span>Get Started</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-24 pb-20 px-6 md:px-12 text-center max-w-5xl mx-auto flex flex-col items-center">
        {/* Glow effect */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-brand-purple/10 rounded-full blur-[120px] pointer-events-none -z-10" />

        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-border-dark text-[11px] font-semibold tracking-wide uppercase text-slate-400 mb-6">
          <Sparkles className="h-3 w-3 text-brand-purple" />
          <span>Production-Ready Content Moderation API</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight font-outfit text-white max-w-3xl leading-[1.15] mb-6">
          AI-Powered Content Moderation for Modern Apps
        </h1>
        
        <p className="text-base md:text-lg text-slate-400 max-w-2xl font-inter leading-relaxed mb-8">
          Protect your platform from toxic content, insult, threat, obscene language, and hate speech.
          Integrate our high-speed API in minutes. Text moderation is live today; image and audio moderation are coming soon.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-16">
          <Link 
            href="/signup" 
            className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold px-6 py-3 rounded-lg transition-all flex items-center justify-center gap-2 brand-glow-hover text-base"
          >
            <span>Create Free Account</span>
            <ArrowRight className="h-4.5 w-4.5" />
          </Link>
          <Link 
            href="/docs" 
            className="bg-slate-900 hover:bg-slate-800 border border-border-dark text-slate-200 font-bold px-6 py-3 rounded-lg transition-all text-base"
          >
            Read API Documentation
          </Link>
        </div>
      </section>

      {/* Simulator Section */}
      <section id="simulator" className="py-16 px-6 md:px-12 bg-slate-950/40 border-y border-border-dark relative">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold font-outfit text-white mb-4">
              Try ModeraShield Live
            </h2>
            <p className="text-slate-400 font-inter mb-6 leading-relaxed">
              Test how our AI model classifies text. Type a custom phrase or select a preset, then run the simulation. 
              Observe latency metrics and visual safety category scores below.
            </p>
            
            {/* Presets */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span className="text-xs text-slate-500 font-semibold self-center mr-1">Presets:</span>
              <button 
                onClick={() => setInputText("You are such a stupid idiot and I hate you.")}
                className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-2.5 py-1 rounded border border-border-dark"
              >
                Toxic Insult
              </button>
              <button 
                onClick={() => setInputText("I will hunt you down and destroy you.")}
                className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-2.5 py-1 rounded border border-border-dark"
              >
                Threat
              </button>
              <button 
                onClick={() => setInputText("Thank you so much for this amazing platform!")}
                className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-2.5 py-1 rounded border border-border-dark"
              >
                Clean Text
              </button>
            </div>

            {/* Input Box */}
            <div className="bg-card-dark border border-border-dark rounded-xl p-3 shadow-lg">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="w-full bg-slate-900/40 text-slate-200 p-3 rounded-lg text-sm border border-border-dark outline-none focus:border-brand-purple min-h-[120px] resize-none font-inter"
                placeholder="Type something to moderate..."
              />
              <div className="flex justify-between items-center mt-3">
                <span className="text-[11px] text-slate-500 font-inter">
                  Character count: {inputText.length}
                </span>
                <button
                  onClick={runSimulation}
                  disabled={isSimulating || !inputText.trim()}
                  className="bg-brand-purple hover:bg-brand-purple-dark text-white font-semibold text-xs px-4 py-2 rounded-lg transition-all brand-glow-hover flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSimulating ? "Analyzing..." : "Test Moderation API"}
                </button>
              </div>
            </div>
          </div>

          {/* Results Display */}
          <div className="bg-card-dark border border-border-dark rounded-xl p-6 shadow-2xl relative overflow-hidden">
            <div className="flex items-center justify-between pb-4 border-b border-border-dark mb-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">API Response</span>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-slate-500 font-mono">Model: {simResult.model}</span>
                <span className="text-[11px] bg-slate-800 text-slate-300 font-mono px-2 py-0.5 rounded">{simResult.latency}</span>
              </div>
            </div>

            {/* Status Indicator */}
            <div className="flex items-center justify-between p-3 rounded-lg mb-6 bg-slate-900/60 border border-border-dark">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-inter">Overall Safety Status:</span>
                <span className={`text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded ${
                  simResult.is_flagged 
                    ? "bg-red-500/10 text-red-400 border border-red-500/20" 
                    : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                }`}>
                  {simResult.is_flagged ? "Flagged / Blocked" : "Approved"}
                </span>
              </div>
              <span className="text-xs font-semibold text-slate-500 font-mono">
                Flagged: {simResult.is_flagged ? "True" : "False"}
              </span>
            </div>

            {/* Score List */}
            <div className="space-y-4">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Category Scores</span>
              {Object.entries(simResult.scores).map(([category, score]: [string, number]) => {
                const percent = Math.round(score * 100);
                const isHigh = score > 0.5;
                return (
                  <div key={category} className="space-y-1">
                    <div className="flex justify-between text-xs font-inter">
                      <span className="capitalize text-slate-300 font-semibold">{category.replace("_", " ")}</span>
                      <span className={`font-mono font-bold ${isHigh ? "text-red-400" : "text-slate-400"}`}>
                        {score.toFixed(4)}
                      </span>
                    </div>
                    {/* Score Bar */}
                    <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-border-dark">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          isHigh ? "bg-red-500 shadow-md shadow-red-500/30" : "bg-brand-purple"
                        }`}
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Why Section */}
      <section id="features" className="py-20 px-6 md:px-12 max-w-6xl mx-auto">
        <h2 className="text-center text-2xl md:text-3xl font-bold font-outfit text-white mb-16">
          API-First Architecture Built for Scale
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-card-dark border border-border-dark p-6 rounded-xl hover:border-slate-700 transition-colors">
            <div className="p-3 bg-brand-purple/10 text-brand-purple rounded-lg w-fit mb-4">
              <Cpu className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg text-slate-200 mb-2 font-outfit">Asynchronous Processing</h3>
            <p className="text-sm text-slate-400 font-inter leading-relaxed">
              Requests are received instantly and processed via distributed Kafka pipelines to assure zero-blocking execution.
            </p>
          </div>

          <div className="bg-card-dark border border-border-dark p-6 rounded-xl hover:border-slate-700 transition-colors">
            <div className="p-3 bg-brand-purple/10 text-brand-purple rounded-lg w-fit mb-4">
              <Lock className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg text-slate-200 mb-2 font-outfit">Developer-First Security</h3>
            <p className="text-sm text-slate-400 font-inter leading-relaxed">
              Authenticate easily using secure X-API-Keys. Manage permission structures and regenerate credentials on the fly.
            </p>
          </div>

          <div className="bg-card-dark border border-border-dark p-6 rounded-xl hover:border-slate-700 transition-colors">
            <div className="p-3 bg-brand-purple/10 text-brand-purple rounded-lg w-fit mb-4">
              <BarChart3 className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-lg text-slate-200 mb-2 font-outfit">Realtime Telemetry</h3>
            <p className="text-sm text-slate-400 font-inter leading-relaxed">
              Track requests, classification breakdowns, and flag rates down to the second with SQL database backing.
            </p>
          </div>
        </div>
      </section>

      {/* Code SDK Section */}
      <section id="sdk" className="py-16 px-6 md:px-12 bg-slate-950/40 border-t border-border-dark">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold font-outfit text-white mb-4 text-center">
            Integrate ModeraShield in 3 Lines of Code
          </h2>
          <p className="text-slate-400 font-inter text-center mb-8 max-w-xl mx-auto">
            Use our official Python SDK or execute standard HTTP requests to check your content immediately.
          </p>

          <div className="bg-card-dark border border-border-dark rounded-xl overflow-hidden shadow-2xl">
            {/* Tabs */}
            <div className="flex border-b border-border-dark bg-slate-900/60 px-4">
              <button 
                onClick={() => setActiveTab("python")}
                className={`py-3 px-4 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all ${
                  activeTab === "python" 
                    ? "border-brand-purple text-white" 
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                Python SDK
              </button>
              <button 
                onClick={() => setActiveTab("curl")}
                className={`py-3 px-4 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all ${
                  activeTab === "curl" 
                    ? "border-brand-purple text-white" 
                    : "border-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                cURL HTTP API
              </button>
            </div>

            {/* Code Content */}
            <div className="p-6 font-mono text-sm leading-relaxed overflow-x-auto text-slate-300 bg-slate-950/40">
              {activeTab === "python" ? (
                <pre>
{`# Install the SDK: pip install moderashield
from moderashield import Moderashield

# Initialize the client
client = Moderashield(api_key="msk_your_key_here")

# Moderate a text string (synchronous wrapper around async queue)
result = client.moderate_text("This text is completely safe!")

if result.is_flagged:
    print(f"Content flagged: {result.categories}")
else:
    print("Content approved!")`}
                </pre>
              ) : (
                <pre>
{`curl -X POST http://localhost:8000/api/v1/moderate/ \\
  -H "X-API-Key: msk_your_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "content_type": "text",
    "content": "This text is completely safe!"
  }'`}
                </pre>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Multimodal Roadmap Section */}
      <section className="py-20 px-6 md:px-12 max-w-5xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold font-outfit text-white mb-4 text-center">
          Multimodal Classification Pipeline
        </h2>
        <p className="text-slate-400 font-inter text-center mb-12 max-w-lg mx-auto">
          One unified security standard for all your application&apos;s communication mediums.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Text */}
          <div className="bg-card-dark border border-border-dark rounded-xl p-5 relative overflow-hidden flex flex-col justify-between h-48">
            <div className="flex items-center justify-between">
              <div className="p-2 bg-brand-purple/10 text-brand-purple rounded-md">
                <MessageSquare className="h-5 w-5" />
              </div>
              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 font-bold px-2 py-0.5 rounded border border-emerald-500/20 uppercase tracking-wide">
                Production
              </span>
            </div>
            <div>
              <h4 className="font-semibold text-slate-200 mb-1 font-outfit">Text Moderation</h4>
              <p className="text-xs text-slate-400 font-inter leading-relaxed">
                Filter comments, forums, logs, and metadata for toxic text and abuse.
              </p>
            </div>
          </div>

          {/* Image */}
          <div className="bg-slate-950/30 border border-slate-900 rounded-xl p-5 relative overflow-hidden flex flex-col justify-between h-48 opacity-70">
            <div className="flex items-center justify-between">
              <div className="p-2 bg-slate-900 text-slate-500 rounded-md">
                <ImageIcon className="h-5 w-5" />
              </div>
              <span className="text-[10px] bg-indigo-500/10 text-indigo-400 font-bold px-2 py-0.5 rounded border border-indigo-500/20 uppercase tracking-wide">
                In Development
              </span>
            </div>
            <div>
              <h4 className="font-semibold text-slate-400 mb-1 font-outfit">Image Moderation</h4>
              <p className="text-xs text-slate-500 font-inter leading-relaxed">
                Detect inappropriate imagery, violence, weapons, and brand risks. Coming soon.
              </p>
            </div>
          </div>

          {/* Audio */}
          <div className="bg-slate-950/30 border border-slate-900 rounded-xl p-5 relative overflow-hidden flex flex-col justify-between h-48 opacity-70">
            <div className="flex items-center justify-between">
              <div className="p-2 bg-slate-900 text-slate-500 rounded-md">
                <Volume2 className="h-5 w-5" />
              </div>
              <span className="text-[10px] bg-indigo-500/10 text-indigo-400 font-bold px-2 py-0.5 rounded border border-indigo-500/20 uppercase tracking-wide">
                In Development
              </span>
            </div>
            <div>
              <h4 className="font-semibold text-slate-400 mb-1 font-outfit">Audio Moderation</h4>
              <p className="text-xs text-slate-500 font-inter leading-relaxed">
                Analyze speech-to-text streams and audio logs for abusive language. Coming soon.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Footer Section */}
      <footer className="border-t border-border-dark bg-slate-950/80 py-12 px-6 md:px-12 mt-auto">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-brand-purple" />
            <span className="font-bold text-sm text-white font-outfit">ModeraShield © 2026</span>
          </div>
          
          <div className="flex gap-6 text-xs text-slate-500 font-inter">
            <a href="#" className="hover:text-slate-300">Privacy Policy</a>
            <a href="#" className="hover:text-slate-300">Terms of Service</a>
            <a href="mailto:support@moderashield.dev" className="hover:text-slate-300">Contact Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
