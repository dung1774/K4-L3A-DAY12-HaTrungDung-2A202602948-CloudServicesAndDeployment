const form = document.querySelector("#chat-form");
const questionInput = document.querySelector("#question");
const userIdInput = document.querySelector("#user-id");
const accessKeyInput = document.querySelector("#access-key");
const conversation = document.querySelector("#conversation");
const statusLine = document.querySelector("#status");
const sendButton = document.querySelector("#send-button");

function addMessage(role, text, meta = "") {
  conversation.querySelector(".welcome")?.remove();
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;

  if (meta) {
    const details = document.createElement("small");
    details.className = "meta";
    details.textContent = meta;
    message.append(details);
  }

  conversation.append(message);
  conversation.scrollTop = conversation.scrollHeight;
}

async function sendQuestion() {
  const question = questionInput.value.trim();
  if (!question) return;

  addMessage("user", question);
  questionInput.value = "";
  statusLine.textContent = "Đang trả lời...";
  statusLine.className = "status";
  sendButton.disabled = true;

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": accessKeyInput.value,
        "X-User-Id": userIdInput.value.trim() || "demo-user",
      },
      body: JSON.stringify({ question }),
    });

    let body = {};
    try {
      body = await response.json();
    } catch (_) {
      // A proxy may return a non-JSON error page. The generic message below is enough.
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${body.detail || "Không thể xử lý yêu cầu"}`);
    }

    const meta = `history: ${body.history_length} · tokens: ${body.tokens.in}/${body.tokens.out} · cost: $${Number(body.cost_usd).toFixed(8)}`;
    addMessage("assistant", body.answer, meta);
    statusLine.textContent = "";
  } catch (error) {
    statusLine.textContent = error.message || "Đã xảy ra lỗi. Vui lòng thử lại.";
    statusLine.className = "status error";
  } finally {
    sendButton.disabled = false;
    questionInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendQuestion();
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
