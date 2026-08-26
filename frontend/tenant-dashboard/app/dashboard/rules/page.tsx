"use client";

import React from "react";
import { 
  Info, 
  ArrowRight
} from "lucide-react";
import { TopNav } from "@/components/layout/topnav";
import Link from "next/link";

export default function RulesPage() {
  const rules = [
    { category: "toxic", name: "Toxic Content", threshold: 0.85, description: "Rude, disrespectful, or unreasonable content that is likely to make users leave a discussion." },
    { category: "insult", name: "Insult", threshold: 0.80, description: "Inflammatory, degrading, or mocking language targeted at individuals or groups." },
    { category: "threat", name: "Threat", threshold: 0.70, description: "Statements expressing intent to inflict pain, injury, damage, or other hostile action on someone." },
    { category: "obscene", name: "Obscene", threshold: 0.80, description: "Vulgar, profane, or sexually explicit comments inappropriate for general audience channels." },
    { category: "severe_toxic", name: "Severe Toxic", threshold: 0.75, description: "Extremely offensive or hateful expressions including extreme profanity or violent harassment." },
    { category: "identity_hate", name: "Identity Hate", threshold: 0.75, description: "Hate speech, bias, or slurs targeting race, gender, religion, sexual orientation, or disability." }
  ];

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-background-dark text-slate-100">
      <TopNav 
        title="Rules & Thresholds" 
        description="Configuration parameters for the active AI text moderation model" 
      />

      <div className="p-6 space-y-6 flex-grow max-w-5xl w-full mx-auto font-inter text-xs">
        
        {/* Info Disclaimer Banner */}
        <div className="bg-slate-900/60 border border-border-dark p-5 rounded-xl flex gap-4 items-start relative overflow-hidden">
          <div className="p-2 bg-slate-950 border border-border-dark text-slate-400 rounded-lg flex-shrink-0 mt-0.5">
            <Info className="h-4.5 w-4.5" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-slate-200">Read-only configuration</h4>
            <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
              Model thresholds are determined at the organization tenant level to ensure uniform safety controls. 
              To request adjustments to your active classification weights, contact security policy administration.
            </p>
          </div>
        </div>

        {/* Rules Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {rules.map((rule) => {
            const pct = Math.round(rule.threshold * 100);
            return (
              <div key={rule.category} className="dashboard-card p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="font-bold text-slate-200 text-sm capitalize">{rule.name}</span>
                    <p className="text-[10px] text-slate-500 font-mono">category: {rule.category}</p>
                  </div>
                  
                  {/* Threshold Badge */}
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Threshold</span>
                    <span className="text-sm font-extrabold text-brand-purple-light font-mono">{rule.threshold.toFixed(2)}</span>
                  </div>
                </div>

                <p className="text-slate-400 leading-relaxed text-xs">
                  {rule.description}
                </p>

                {/* Progress bar visualizing threshold */}
                <div className="space-y-1.5 pt-2">
                  <div className="flex justify-between text-[10px] text-slate-500 font-semibold">
                    <span>Classification Sensitivity</span>
                    <span>{pct}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden border border-border-dark">
                    <div 
                      className="h-full bg-brand-purple rounded-full" 
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Callout */}
        <div className="dashboard-card p-6 flex flex-col sm:flex-row justify-between items-center gap-6 bg-gradient-to-r from-slate-950 to-slate-900">
          <div className="space-y-1 text-center sm:text-left">
            <h4 className="font-bold text-slate-200 text-sm">Need a custom safety configuration?</h4>
            <p className="text-slate-400 leading-normal">
              Enterprise subscribers can define custom categories, customize thresholds, and support manual human overrides.
            </p>
          </div>
          <Link 
            href="/docs" 
            className="bg-brand-purple hover:bg-brand-purple-dark text-white font-bold py-2 px-4 rounded-lg flex items-center gap-1.5 transition-all flex-shrink-0"
          >
            <span>Read Policy Docs</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

      </div>
    </div>
  );
}
