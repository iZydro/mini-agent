const sessionId = crypto.randomUUID();

const eventSource = new EventSource(`/api/events/${sessionId}`);

let currentAgentBubble = null;
let currentAgentMessage = null;

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (!currentAgentMessage) return;

  if (data.type === "llm_request") {
    currentAgentMessage.content.textContent = "Pensando...";
  }

  if (data.type === "tool_start") {
    addTrace(`🔧 ${data.tool}`);
  }

  if (data.type === "tool_end") {
    addTrace(`✅ ${data.tool} (${Math.round(data.elapsed_ms)} ms)`);
  }

  if (data.type === "tool_error") {
    addTrace(`❌ ${data.tool}: ${data.error}`);
  }

  if (data.type === "llm_final_answer") {
    currentAgentMessage.content.textContent = data.content || "(sin respuesta)";
  }
};

const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");

const source = new EventSource("/api/events");

function addTrace(text) {
  if (!currentAgentMessage) return;

  const div = document.createElement("div");
  div.className = "trace";
  div.textContent = text;

  currentAgentMessage.trace.appendChild(div);
  scrollToBottom();
}

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

  const trace = document.createElement("div");
  trace.className = "agent-trace";

  const content = document.createElement("div");
  content.className = "agent-content";
  content.textContent = "Pensando...";

  bubble.appendChild(label);
  bubble.appendChild(trace);
  bubble.appendChild(content);
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  scrollToBottom();

  return { wrapper, bubble, trace, content };
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function autoResize() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

source.onmessage = (event) => {

    const data = JSON.parse(event.data);

    console.log(data);

};

input.addEventListener("input", autoResize);

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
  autoResize();

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
        currentAgentMessage.content.textContent = data.answer || "(sin respuesta)";
        currentAgentMessage = null;
    }

  } catch (error) {
    waitingBubble.textContent = `Error: ${error.message}`;
  } finally {
    input.disabled = false;
    form.querySelector("button").disabled = false;
    input.focus();
    scrollToBottom();
  }
});