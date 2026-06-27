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
  }

  if (data.type === "tool_start") {
    addTrace(`🔧 ${data.tool}`);
  }

  if (data.type === "tool_end") {
    addTrace(`✅ ${data.tool} (${Math.round(data.elapsed_ms)} ms)`);
    updateExecutionHeader();
  }

  if (data.type === "tool_error") {
    addTrace(`❌ ${data.tool}: ${data.error}`);
    updateExecutionHeader();
  }

  if (data.type === "llm_final_answer") {
    setAgentContent(data.content || "(sin respuesta)");
    currentAgentMessage = null;
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