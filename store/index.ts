import { create } from "zustand";
import type { BacktestResult, BotConfig, ChatMessage } from "@/lib/types";
import { MOCK_BACKTEST_RESULT, DEFAULT_CONFIG } from "@/lib/mock-data";

interface TradingStore {
  backtestResult: BacktestResult | null;
  activeConfig: BotConfig;
  chatHistory: ChatMessage[];
  isRunningBacktest: boolean;

  setBacktestResult: (result: BacktestResult) => void;
  setActiveConfig: (config: BotConfig) => void;
  addChatMessage: (msg: ChatMessage) => void;
  clearChat: () => void;
  setRunningBacktest: (v: boolean) => void;
  loadMockData: () => void;
}

export const useTradingStore = create<TradingStore>((set) => ({
  backtestResult: MOCK_BACKTEST_RESULT,
  activeConfig: DEFAULT_CONFIG,
  chatHistory: [],
  isRunningBacktest: false,

  setBacktestResult: (result) => set({ backtestResult: result }),
  setActiveConfig: (config) => set({ activeConfig: config }),
  addChatMessage: (msg) =>
    set((s) => ({ chatHistory: [...s.chatHistory, msg] })),
  clearChat: () => set({ chatHistory: [] }),
  setRunningBacktest: (v) => set({ isRunningBacktest: v }),
  loadMockData: () => set({ backtestResult: MOCK_BACKTEST_RESULT }),
}));
