const API_BASE = "http://127.0.0.1:8000";
let currentConversationId = null;
let toastTimer;

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[char]));

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const text = await response.text();
  let body;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) throw new Error(body?.detail || `요청 실패 (${response.status})`);
  return body;
}

function addBubble(role, content) {
  const node = document.createElement("div");
  node.className = `bubble ${role}`;
  node.textContent = content;
  $("chatMessages").appendChild(node);
  $("chatMessages").scrollTop = $("chatMessages").scrollHeight;
}

function renderMessages(messages) {
  const box = $("chatMessages");
  box.replaceChildren();
  if (!messages.length) {
    addBubble("assistant", "안녕하세요! 저장된 판매 데이터를 바탕으로 답변할게요. 예: ‘피스타치오 초콜릿 소 판매량은 어때?’");
    return;
  }
  messages.forEach((message) => addBubble(message.role === "user" ? "user" : "assistant", message.content));
}

async function loadConversations() {
  const list = await api("/api/conversations");
  const box = $("conversationList");
  box.replaceChildren();
  if (!list.length) {
    box.innerHTML = '<p class="muted">저장된 대화가 아직 없습니다.</p>';
    return;
  }
  list.forEach((conversation) => {
    const button = document.createElement("button");
    button.className = "conversation-item";
    button.type = "button";
    const title = document.createElement("strong");
    title.textContent = conversation.title || "새 대화";
    const meta = document.createElement("span");
    meta.textContent = `${conversation.message_count ?? 0}개 메시지 · ${(conversation.updated_at || "").slice(0, 10)}`;
    button.append(title, meta);
    button.addEventListener("click", () => openConversation(conversation.id));
    box.appendChild(button);
  });
}

async function openConversation(id) {
  try {
    const conversation = await api(`/api/conversations/${encodeURIComponent(id)}`);
    currentConversationId = conversation.id;
    renderMessages(conversation.messages || []);
  } catch (error) {
    showToast(error.message);
  }
}

async function loadData() {
  const [summary, records] = await Promise.all([
    api("/api/data/summary"),
    api("/api/data"),
  ]);
  $("recordCount").textContent = `${summary.count ?? 0}건`;
  $("recordPeriod").textContent = summary.period || "기록 없음";

  const itemSummary = $("itemSummary");
  itemSummary.replaceChildren();
  const entries = Object.entries(summary.by_item || {});
  if (!entries.length) {
    itemSummary.innerHTML = '<p class="muted">요약할 판매 기록이 없습니다.</p>';
  } else {
    entries.forEach(([item, metrics]) => {
      const card = document.createElement("div");
      card.className = "item-card";
      card.innerHTML = `<strong>${escapeHtml(item)}</strong><span>총 ${escapeHtml(metrics.total)}개 · 평균 ${escapeHtml(metrics.average)}개<br>최고 ${escapeHtml(metrics.max)}개 · 최저 ${escapeHtml(metrics.min)}개</span>`;
      itemSummary.appendChild(card);
    });
  }

  const rows = $("dataRows");
  rows.replaceChildren();
  const sorted = [...records].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  const visible = sorted.slice(0, 30);
  if (!visible.length) {
    rows.innerHTML = '<tr><td colspan="5" class="muted">등록된 데이터가 없습니다.</td></tr>';
  } else {
    visible.forEach((record) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${escapeHtml(record.date)}</td><td>${escapeHtml(record.item)}</td><td>${record.value == null ? "미상" : `${escapeHtml(record.value)}개`}</td><td>${escapeHtml(record.memo)}</td><td><button class="delete-btn" data-id="${escapeHtml(record.id)}">삭제</button></td>`;
      tr.querySelector(".delete-btn").addEventListener("click", () => deleteRecord(record.id));
      rows.appendChild(tr);
    });
  }
  $("listNote").textContent = records.length > 30 ? `최근 30건 표시 · 전체 ${records.length}건` : `전체 ${records.length}건`;
}

async function deleteRecord(id) {
  if (!confirm("이 판매 기록을 삭제할까요?")) return;
  try {
    await api(`/api/data/${encodeURIComponent(id)}`, { method: "DELETE" });
    showToast("데이터를 삭제했어요.");
    await loadData();
  } catch (error) { showToast(error.message); }
}

$("chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("chatInput");
  const message = input.value.trim();
  if (!message) return;
  const button = $("sendBtn");
  button.disabled = true;
  button.textContent = "답변 생성 중…";
  addBubble("user", message);
  input.value = "";
  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, ...(currentConversationId ? { conversation_id: currentConversationId } : {}) }),
    });
    currentConversationId = result.conversation_id;
    addBubble("assistant", result.answer);
    await loadConversations();
  } catch (error) {
    addBubble("assistant", `요청을 처리하지 못했어요: ${error.message}`);
    showToast(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "보내기";
    input.focus();
  }
});

$("newChatBtn").addEventListener("click", () => {
  currentConversationId = null;
  renderMessages([]);
  $("chatInput").focus();
});

$("dataForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const record = {
    date: $("dataDate").value,
    item: $("dataItem").value,
    value: Number($("dataValue").value),
    memo: $("dataMemo").value.trim(),
  };
  try {
    await api("/api/data", { method: "POST", body: JSON.stringify(record) });
    event.target.reset();
    $("dataDate").value = new Date().toISOString().slice(0, 10);
    showToast("판매 데이터를 추가했어요.");
    await loadData();
  } catch (error) { showToast(error.message); }
});

$("refreshBtn").addEventListener("click", async () => {
  try { await loadData(); showToast("데이터를 새로고침했어요."); }
  catch (error) { showToast(error.message); }
});

async function init() {
  $("dataDate").value = new Date().toISOString().slice(0, 10);
  try {
    await api("/");
    $("apiStatus").textContent = "백엔드 연결됨";
    $("apiStatus").classList.add("online");
    await Promise.all([loadData(), loadConversations()]);
  } catch (error) {
    $("apiStatus").textContent = "백엔드 연결 안 됨";
    $("apiStatus").classList.add("offline");
    $("itemSummary").innerHTML = '<p class="muted">백엔드 서버가 켜져 있는지 확인해 주세요.</p>';
    $("dataRows").innerHTML = `<tr><td colspan="5" class="muted">${escapeHtml(error.message)}</td></tr>`;
  }
}

init();
