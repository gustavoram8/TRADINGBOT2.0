import { NextRequest, NextResponse } from "next/server";

const GEMINI_KEY = process.env.GEMINI_API_KEY ?? "";
const PYTHON_API = process.env.PYTHON_API_URL ?? "";

const SYSTEM_PROMPT = `Eres Chuky AI, analista cuantitativo especializado en trading algorítmico ICT (Inner Circle Trader) con enfoque en futuros MNQ/NAS100 y cuentas funded (OneUpTrader $50k).

REGLAS:
- Responde SIEMPRE en español, tono profesional pero directo.
- Usa SOLO los datos de contexto proporcionados. No inventes cifras.
- Diferencia entre hechos (datos del backtest) y recomendaciones (tus sugerencias).
- Estructura: resumen ejecutivo (1-2 líneas) → 3-6 bullets con evidencia numérica → 1-3 acciones concretas priorizadas.
- Foco: metodología ICT, riesgo de prop firm, validación cuantitativa (Sharpe, PF, expectancy, R:R).`;

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface RequestBody {
  message: string;
  history: ChatMessage[];
  context: string;
}

function fallbackResponse(message: string, context: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("rendimiento") || lower.includes("general")) {
    const sharpeMatch = context.match(/Sharpe: ([\d.]+)/);
    const pfMatch = context.match(/Profit Factor: ([\d.]+)/);
    const sharpe = sharpeMatch ? parseFloat(sharpeMatch[1]) : null;
    const pf = pfMatch ? parseFloat(pfMatch[1]) : null;
    return `**Análisis de Rendimiento General**\n\n${sharpe !== null ? `Sharpe Ratio: ${sharpe.toFixed(2)} — ${sharpe > 1 ? "Excelente" : sharpe > 0.5 ? "Aceptable" : "Necesita mejora"}.` : ""}\n${pf !== null ? `Profit Factor: ${pf.toFixed(2)} — ${pf > 1.5 ? "Sólido" : pf > 1 ? "Marginal" : "Deficitario"}.` : ""}\n\nPara un análisis más profundo, configura tu GEMINI_API_KEY en el panel de Vercel.`;
  }
  if (lower.includes("riesgo")) {
    return "Para el análisis de riesgo detallado, configura GEMINI_API_KEY en las variables de entorno de Vercel.";
  }
  return "Necesito que configures GEMINI_API_KEY en Vercel para darte un análisis completo. Ve a tu proyecto en Vercel → Settings → Environment Variables.";
}

export async function POST(req: NextRequest) {
  const { message, history, context } = await req.json() as RequestBody;

  // Try Python backend first (it may have its own Gemini integration)
  if (PYTHON_API) {
    try {
      const res = await fetch(`${PYTHON_API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history, context }),
      });
      if (res.ok) {
        const data = await res.json() as { reply: string };
        return NextResponse.json({ reply: data.reply });
      }
    } catch {
      // Fall through to direct Gemini call
    }
  }

  // Direct Gemini call from Next.js
  if (!GEMINI_KEY) {
    return NextResponse.json({ reply: fallbackResponse(message, context) });
  }

  try {
    const { GoogleGenerativeAI } = await import("@google/generative-ai");
    const genAI = new GoogleGenerativeAI(GEMINI_KEY);
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      systemInstruction: SYSTEM_PROMPT,
    });

    const chatSession = model.startChat({
      history: history.map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      })),
    });

    const fullMessage = `CONTEXTO DEL BACKTEST:\n${context}\n\nPREGUNTA: ${message}`;
    const result = await chatSession.sendMessage(fullMessage);
    const reply = result.response.text();

    return NextResponse.json({ reply });
  } catch (err) {
    return NextResponse.json(
      { reply: `Error con Gemini: ${String(err)}. Verifica tu API key.` },
      { status: 200 }
    );
  }
}
