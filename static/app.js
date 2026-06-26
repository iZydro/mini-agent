const sessionId = crypto.randomUUID();

const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("input");

function addMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  scrollToBottom();

  return bubble;
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function autoResize() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

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

  addMessage("user", text);
  const waitingBubble = addMessage("agent", "Pensando...");

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
    waitingBubble.textContent = data.answer || "(sin respuesta)";
  } catch (error) {
    waitingBubble.textContent = `Error: ${error.message}`;
  } finally {
    input.disabled = false;
    form.querySelector("button").disabled = false;
    input.focus();
    scrollToBottom();
  }
});