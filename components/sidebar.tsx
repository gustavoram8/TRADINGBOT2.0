"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FlaskConical,
  CandlestickChart,
  Receipt,
  Shield,
  CheckCircle2,
  SlidersHorizontal,
  BrainCircuit,
  FileText,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Menu,
  X,
} from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/backtest", label: "Backtest Lab", icon: FlaskConical },
  { href: "/chart", label: "Price Chart", icon: CandlestickChart },
  { href: "/trades", label: "Trades", icon: Receipt },
  { href: "/risk", label: "Risk Center", icon: Shield },
  { href: "/validation", label: "Validation", icon: CheckCircle2 },
  { href: "/configurator", label: "Bot Builder", icon: SlidersHorizontal },
  { href: "/journal", label: "Trade Journal", icon: BookOpen },
  { href: "/ai", label: "AI Analyst", icon: BrainCircuit },
  { href: "/reports", label: "Reports", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarContent = (mobile = false) => (
    <>
      {/* Logo */}
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-4 border-b border-border",
          !mobile && collapsed && "justify-center"
        )}
      >
        <div className="flex-shrink-0 w-7 h-7 rounded-md bg-brand-dark flex items-center justify-center">
          <TrendingUp size={14} className="text-white" />
        </div>
        {(mobile || !collapsed) && (
          <div className="flex-1">
            <p className="text-sm font-bold text-text-primary leading-none">CHUKY BOT</p>
            <p className="text-[10px] text-text-muted mt-0.5">ICT · MNQ</p>
          </div>
        )}
        {mobile && (
          <button onClick={() => setMobileOpen(false)} className="text-text-muted hover:text-text-primary">
            <X size={18} />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 px-3 py-2 mx-2 rounded-md text-sm transition-colors mb-0.5",
                !mobile && collapsed && "justify-center px-2",
                active
                  ? "bg-brand-dark/20 text-brand-blue font-medium"
                  : "text-text-secondary hover:bg-bg-tertiary hover:text-text-primary"
              )}
              title={!mobile && collapsed ? label : undefined}
            >
              <Icon size={16} className="flex-shrink-0" />
              {(mobile || !collapsed) && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      {(mobile || !collapsed) && (
        <div className="px-4 py-3 border-t border-border">
          <p className="text-[10px] text-text-muted text-center leading-relaxed">
            MNQ Futures · $50k Funded
            <br />
            <span className="text-brand-blue">v2.0</span>
          </p>
        </div>
      )}

      {/* Collapse toggle — desktop only */}
      {!mobile && (
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="mx-auto mb-3 flex items-center justify-center w-6 h-6 rounded-full border border-border text-text-muted hover:text-text-primary hover:border-brand-blue transition-colors"
        >
          {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
        </button>
      )}
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        className="md:hidden fixed top-3 left-3 z-50 w-9 h-9 flex items-center justify-center rounded-md bg-bg-secondary/90 border border-border text-text-secondary hover:text-text-primary"
        onClick={() => setMobileOpen(true)}
      >
        <Menu size={18} />
      </button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={cn(
          "md:hidden fixed inset-y-0 left-0 z-50 w-64 flex flex-col bg-bg-secondary backdrop-blur-md border-r border-border transition-transform duration-200",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {sidebarContent(true)}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden md:flex flex-col h-screen bg-bg-secondary/75 backdrop-blur-md border-r border-border transition-all duration-200 sticky top-0 z-10",
          collapsed ? "w-14" : "w-56"
        )}
      >
        {sidebarContent(false)}
      </aside>
    </>
  );
}
