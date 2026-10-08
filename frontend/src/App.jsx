import { useEffect, useRef, useState } from "react";

const API_URL = "http://127.0.0.1:8000/api";

async function sendMessage(path, text) {
  const response = await fetch(`${API_URL}/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || "NOVA could not process that request.");
  }
  return result.response;
}

function Orb({ mood, label = `NOVA is ${mood}` }) {
  return (
    <div className={`orb-stage mood-${mood}`} aria-label={label}>
      <div className="star-field" aria-hidden="true">
        {Array.from({ length: 42 }, (_, index) => (
          <i
            key={index}
            style={{
              left: `${(index * 43 + 13) % 97}%`,
              top: `${(index * 67 + 9) % 91}%`,
              animationDuration: `${1.8 + (index % 5) * 0.45}s`,
              animationDelay: `${index * -0.13}s`,
            }}
          />
        ))}
      </div>
      <div className="orb-halo orb-halo-one" />
      <div className="orb-halo orb-halo-two" />
      <div className="orb-orbit orbit-one" />
      <div className="orb-orbit orbit-two" />
      <div className="orb-core">
        <div className="orb-liquid orb-liquid-one" />
        <div className="orb-liquid orb-liquid-two" />
        <div className="orb-liquid orb-liquid-three" />
        <div className="orb-shimmer" />
      </div>
      <div className="waveform" aria-hidden="true">
        {Array.from({ length: 39 }, (_, index) => (
          <i key={index} style={{ "--bar": index, "--height": `${5 + (index % 5) * 3}px` }} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [intro, setIntro] = useState(true);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState("Nova is ready. Ask me anything.");
  const [mood, setMood] = useState("ready");
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(false);
  const [aiConfigured, setAiConfigured] = useState(false);
  const messageEndRef = useRef(null);

  useEffect(() => {
    const introTimer = window.setTimeout(() => setIntro(false), 2400);
    const controller = new AbortController();

    async function startNova() {
      try {
        const healthResponse = await fetch(`${API_URL}/health`, {
          signal: controller.signal,
        });
        if (!healthResponse.ok) throw new Error("NOVA backend is unavailable.");
        const health = await healthResponse.json();
        setOnline(true);
        setAiConfigured(health.ai_configured);
        if (!health.speech_available) {
          throw new Error("NOVA's speech engine is unavailable.");
        }

        const greetingResponse = await fetch(`${API_URL}/greeting`, {
          method: "POST",
          signal: controller.signal,
        });
        const greetingResult = await greetingResponse.json();
        if (!greetingResponse.ok) {
          throw new Error(
            greetingResult.detail || "Could not play the welcome greeting.",
          );
        }

        setStatus(
          health.ai_configured
            ? "NOVA is ready. Speak naturally; I'm listening."
            : "Listening. AI answers need GEMINI_API_KEY; basic commands still work.",
        );
        setMood("listening");
        while (!controller.signal.aborted) {
          try {
            const response = await fetch(`${API_URL}/listen`, {
              method: "POST",
              signal: controller.signal,
            });
            const result = await response.json();
            if (response.status === 409) {
              await new Promise((resolve) => window.setTimeout(resolve, 1000));
              continue;
            }
            if (!response.ok) {
              throw new Error(result.detail || "NOVA could not listen for speech.");
            }

            if (result.recognized && result.heard) {
              setMessages((current) => [
                ...current,
                { role: "user", text: result.heard },
              ]);
              setMood("thinking");
              setStatus("NOVA is processing what you said...");
              let commandResponse;
              let commandResult;
              while (!controller.signal.aborted) {
                commandResponse = await fetch(`${API_URL}/command`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ text: result.heard }),
                  signal: controller.signal,
                });
                commandResult = await commandResponse.json();
                if (commandResponse.status !== 409) break;
                await new Promise((resolve) => window.setTimeout(resolve, 500));
              }
              if (controller.signal.aborted) return;
              if (!commandResponse.ok) {
                throw new Error(
                  commandResult.detail || "NOVA could not process what you said.",
                );
              }
              setMood(commandResult.spoken ? "speaking" : "ready");
              setStatus(
                commandResult.spoken
                  ? "NOVA replied. I'm listening for your next message."
                  : "Command completed. I'm listening for your next message.",
              );
              await new Promise((resolve) => window.setTimeout(resolve, 1200));
            } else {
              setMood("listening");
              setStatus("I'm listening. Speak naturally to NOVA.");
            }
          } catch (error) {
            if (controller.signal.aborted) return;
            setMood("attention");
            setStatus(error.message || "NOVA lost the microphone connection.");
            await new Promise((resolve) => window.setTimeout(resolve, 1500));
            setMood("listening");
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        setOnline(false);
        setMood("attention");
        setStatus(error.message || "Connect to the NOVA Python backend to get started.");
      }
    }

    const startTimer = window.setTimeout(startNova, 500);

    return () => {
      window.clearTimeout(introTimer);
      window.clearTimeout(startTimer);
      controller.abort();
    };
  }, []);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function submitMessage(text, mode = "ask") {
    const cleanText = text.trim();
    if (!cleanText || busy) return;

    setMessages((current) => [...current, { role: "user", text: cleanText }]);
    setQuestion("");
    setBusy(true);
    setMood("thinking");
    setStatus(mode === "ask" ? "Thinking through your question..." : "Working on your command...");

    try {
      await sendMessage(mode, cleanText);
      setStatus("NOVA has replied. I'm listening for your next message.");
      setMood("speaking");
      window.setTimeout(() => setMood("listening"), 1800);
    } catch (error) {
      setStatus(error.message);
      setMood("attention");
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitMessage(question, "ask");
  }

  return (
    <>
      {intro && (
        <section className="intro-screen" aria-label="NOVA opening animation">
          <div className="intro-brand"><span>N</span> NOVA</div>
          <Orb mood="listening" label="NOVA opening animation; microphone is not active" />
          <div className="intro-copy">
            <span className="eyebrow">YOUR PERSONAL AI</span>
            <p>{online ? "A little closer to the future." : "Connecting to your universe."}</p>
          </div>
        </section>
      )}

      <main className={`app-shell${intro ? " app-shell-entering" : ""}`}>
        <header className="topbar">
          <a className="brand" href="/" aria-label="NOVA home">
            <span className="brand-mark">N</span>
            <span className="brand-name">NOVA</span>
          </a>
          <div className={`connection-pill ${online ? "is-online" : ""}`}>
            <i />
            {online ? "ONLINE" : "OFFLINE"}
          </div>
        </header>

        <section className="welcome">
          <span className="eyebrow">YOUR VOICE, AMPLIFIED</span>
          <h1>Ready when<br /><span>you are.</span></h1>
          <p>Your voice assistant is here.</p>
          <p className="talk-hint">
            {online
              ? "I'm listening. Speak naturally, or type below."
              : "Connect to the Python backend to start NOVA."}
          </p>
          {online && !aiConfigured && (
            <p className="setup-hint">
              Add GEMINI_API_KEY to enable AI answers. Basic voice commands still work.
            </p>
          )}
        </section>

        <section className={`orb-panel${mood !== "ready" ? " orb-panel-active" : ""}`} aria-label="Voice assistant">
          <Orb mood={mood} />
          <div className="orb-state" aria-live="polite">
            <i />
            {mood === "listening"
              ? "LISTENING"
              : mood === "thinking"
                ? "THINKING"
                : mood === "speaking"
                  ? "NOVA IS SPEAKING"
                  : mood === "attention"
                    ? "NEEDS YOUR ATTENTION"
                    : "READY WHEN YOU ARE"}
          </div>
          <p className="sr-only" aria-live="polite">{status}</p>
        </section>

        <section className="interaction-area">
          <section className="conversation" aria-label="Conversation">
            {messages.map((message, index) => (
              <article
                className="message message-user"
                key={`${index}-user`}
              >
                <span>YOU</span>
                <p>{message.text}</p>
              </article>
            ))}
            <div ref={messageEndRef} />
          </section>

          <form className="ask-card" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="question">Ask Nova a question</label>
            <input
              id="question"
              autoComplete="off"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Message Nova..."
              maxLength={2000}
              disabled={busy}
            />
            <button
              className="submit-button"
              type="submit"
              disabled={busy || !online || !question.trim()}
              aria-label="Send question"
            >
              {busy ? "…" : "↑"}
            </button>
          </form>
          <footer className="footer">
            <span>POWERED BY NOVA</span>
            <button
              type="button"
              onClick={() => {
                setMessages([]);
                setStatus("Nova is ready. Ask me anything.");
                setMood("ready");
              }}
              disabled={!messages.length}
            >
              CLEAR CHAT
            </button>
          </footer>
        </section>
      </main>
    </>
  );
}
