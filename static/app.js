const sessionId = crypto.randomUUID();

const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");

let currentAgentMessage = null;

const eventSource = new EventSource(`/api/events/${sessionId}`);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (!currentAgentMessage) return;

    if (data.type === "llm_request") {
        setAgentStatus("Pensando...");
        addTraceFromEvent(data, `🤔 Pensando...`);
    }

    if (data.type === "tool_start") {
        addTraceFromEvent(data, `🔧 ${data.tool}`);
    }

    if (data.type === "tool_end") {
        const elapsed = data.elapsed_ms != null
            ? `${Math.round(data.elapsed_ms)} ms`
            : "? ms";

        addTraceFromEvent(data, `✅ ${data.tool} (${elapsed})`);

        if (data.tool === "web_search" && data.ui) {
            if (data.ui.query) {
                addTraceFromEvent(data, `🌐 Consulta original: ${data.ui.query}`);
            }

            if (data.ui.web_calls?.length) {
                addTraceFromEvent(data, "🔎 Búsquedas web:");

                for (const call of data.ui.web_calls) {
                    if (call.type === "search") {
                        addTraceFromEvent(data, `   search → ${call.query || "(sin query)"}`);

                        if (call.queries?.length > 1) {
                            for (const q of call.queries) {
                                addTraceFromEvent(data, `      • ${q}`);
                            }
                        }
                    }

                    if (call.type === "open_page") {
                        addTraceFromEvent(data, `   open_page → ${call.url}`);
                    }
                }
            }

            if (data.ui.citations?.length) {
                addTraceFromEvent(data, "📄 Fuentes:");

                for (const citation of data.ui.citations) {
                    addTraceFromEvent(data, `   ${citation.title}`);
                }
            }
        }

        if (data.ui?.api_calls?.length) {
            addTraceFromEvent(data, "🌐 API calls:");

            for (const call of data.ui.api_calls) {
                addTraceFromEvent(data, `   ${call.method} ${call.host}${call.path} → ${call.status_code} (${call.elapsed_ms} ms)`);

                if (call.query && Object.keys(call.query).length) {
                    for (const [key, value] of Object.entries(call.query)) {
                        addTraceFromEvent(data, `      ${key}: ${value}`);
                    }
                }
            }
        }
        updateExecutionHeader();
    }

    if (data.type === "tool_error") {
        const elapsed = data.elapsed_ms != null
            ? `${Math.round(data.elapsed_ms)} ms`
            : "? ms";

        addTraceFromEvent(data, `❌ ${data.tool} (${elapsed}): ${data.error}`);
        updateExecutionHeader();
    }

    if (data.type === "llm_final_answer") {
        setAgentContent(data.content || "(sin respuesta)");
        currentAgentMessage = null;
    }

    if (data.type === "tool_info") {
    addTraceFromEvent(data, `ℹ️ ${data.message}`);
    }

    if (data.type === "tool_progress") {
    addTraceFromEvent(data, `📌 ${data.message}`);
    }

    if (data.type === "api_call_start") {
    const api = data.api;
    addTraceFromEvent(
        data,
        `🌐 ${api.method} ${api.host}${api.path}`
    );

    if (api.query && Object.keys(api.query).length) {
        for (const [key, value] of Object.entries(api.query)) {
        addTraceFromEvent(data, `   ${key}: ${value}`);
        }
    }
    }

    if (data.type === "api_call_end") {
    const api = data.api;
    addTraceFromEvent(
        data,
        `✅ ${api.status_code} · ${api.elapsed_ms} ms`
    );
    }
};

function addUserMessage(text) {
    const wrapper = document.createElement("div");
    wrapper.className = "message user";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "Tú";

    const content = document.createElement("div");
    content.textContent = text;

    bubble.appendChild(label);
    bubble.appendChild(content);
    wrapper.appendChild(bubble);
    messages.appendChild(wrapper);

    scrollToBottom();
}

function addAgentMessage() {
    const wrapper = document.createElement("div");
    wrapper.className = "message agent";

    const bubble = document.createElement("div");
    bubble.className = "bubble agent-bubble";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "Agente";

    const execution = document.createElement("div");
    execution.className = "execution";

    const executionHeader = document.createElement("div");
    executionHeader.className = "execution-header";
    executionHeader.textContent = "▼ Ejecución";

    const executionBody = document.createElement("div");
    executionBody.className = "execution-body";

    executionHeader.addEventListener("click", () => {
        execution.classList.toggle("collapsed");

        const prefix = execution.classList.contains("collapsed") ? "▶" : "▼";
        executionHeader.textContent = `${prefix} Ejecución`;
    });

    execution.appendChild(executionHeader);
    execution.appendChild(executionBody);

    const content = document.createElement("div");
    content.className = "agent-content";
    content.textContent = "Pensando...";

    bubble.appendChild(label);
    bubble.appendChild(execution);
    bubble.appendChild(content);
    wrapper.appendChild(bubble);
    messages.appendChild(wrapper);

    scrollToBottom();

    return {
        wrapper,
        bubble,
        execution,
        executionHeader,
        executionBody,
        content,
        toolCount: 0
    };
}

function formatTime(iso) {
  if (!iso) return "";

  const date = new Date(iso);

  return date.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3
  });
}

function addTraceFromEvent(event, text) {
  if (!currentAgentMessage) return;

  const div = document.createElement("div");
  div.className = "trace";

  const time = document.createElement("span");
  time.className = "trace-time";
  time.textContent = formatTime(event.timestamp);

  const body = document.createElement("span");
  body.className = "trace-body";
  body.textContent = text;

  div.appendChild(time);
  div.appendChild(body);

  currentAgentMessage.executionBody.appendChild(div);
  scrollToBottom();
}

function addTrace(text) {
    if (!currentAgentMessage) return;

    const div = document.createElement("div");
    div.className = "trace";
    div.textContent = text;

    currentAgentMessage.executionBody.appendChild(div);

    if (text.startsWith("🔧")) {
        currentAgentMessage.toolCount += 1;
        updateExecutionHeader();
    }

    scrollToBottom();
}

function updateExecutionHeader() {
    if (!currentAgentMessage) return;

    const count = currentAgentMessage.toolCount;
    currentAgentMessage.executionHeader.textContent =
        `▼ Ejecución${count ? ` (${count} tools)` : ""}`;
}

function setAgentStatus(text) {
    if (!currentAgentMessage) return;
    currentAgentMessage.content.textContent = text;
}

function setAgentContent(markdown) {
    if (!currentAgentMessage) return;

    currentAgentMessage.content.innerHTML = marked.parse(markdown);
    scrollToBottom();
}

function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
}

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
    }
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const text = input.value.trim();
    if (!text) return;

    input.value = "";

    addUserMessage(text);
    currentAgentMessage = addAgentMessage();

    input.disabled = true;
    form.querySelector("button").disabled = true;

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (currentAgentMessage) {
            setAgentContent(data.answer || "(sin respuesta)");
            currentAgentMessage = null;
        }
    } catch (error) {
        if (currentAgentMessage) {
            currentAgentMessage.content.textContent = `Error: ${error.message}`;
            currentAgentMessage = null;
        }
    } finally {
        input.disabled = false;
        form.querySelector("button").disabled = false;
        input.focus();
        scrollToBottom();
    }
});