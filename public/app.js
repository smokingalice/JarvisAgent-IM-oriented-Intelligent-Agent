const API_BASE = '';
const WS_BASE = `ws://${location.host}`;

const state = {
  currentUser: 'alice',
  activeChat: null,
  chats: [],
  messages: [],
  documents: [],
  presentations: [],
  ws: null,
};

// ==================== Init ====================
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initUserSelect();
  initComposer();
  connectWebSocket();
  loadChats();
  loadDocuments();
  loadPresentations();
});

// ==================== Navigation ====================
function initNav() {
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`view-${tab.dataset.view}`).classList.add('active');
    });
  });
}

function initUserSelect() {
  const select = document.getElementById('viewer-select');
  const users = ['alice', 'bob', 'charlie', 'diana'];
  users.forEach(u => {
    const opt = document.createElement('option');
    opt.value = u;
    opt.textContent = u.charAt(0).toUpperCase() + u.slice(1);
    select.appendChild(opt);
  });
  select.value = state.currentUser;
  select.addEventListener('change', e => {
    state.currentUser = e.target.value;
    loadChats();
  });
}

// ==================== WebSocket ====================
function connectWebSocket() {
  state.ws = new WebSocket(`${WS_BASE}/ws`);
  state.ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleWsMessage(msg);
  };
  state.ws.onclose = () => {
    setTimeout(connectWebSocket, 2000);
  };
}

function handleWsMessage(msg) {
  switch (msg.type) {
    case 'new_message':
      handleNewMessage(msg.data);
      break;
    case 'task_progress':
      handleTaskProgress(msg.data);
      break;
    case 'task_update':
      break;
    case 'document_updated':
      loadDocuments();
      break;
    case 'presentation_updated':
      loadPresentations();
      break;
  }
}

function handleNewMessage(message) {
  if (message.chat_id === state.activeChat) {
    state.messages.push(message);
    renderMessages();
    scrollToBottom();
  }
  loadChats();
}

function handleTaskProgress(data) {
  const progressEl = document.getElementById(`progress-${data.task_id}`);
  if (progressEl) {
    progressEl.style.width = `${data.progress}%`;
  }
}

// ==================== IM - Chats ====================
async function loadChats() {
  try {
    const res = await fetch(`${API_BASE}/api/chats?user_id=${state.currentUser}`);
    state.chats = await res.json();
    renderChats();
  } catch (e) {
    console.error('Failed to load chats:', e);
  }
}

function renderChats() {
  const list = document.getElementById('conversation-list');
  list.innerHTML = '';
  state.chats.forEach(chat => {
    const item = document.createElement('div');
    item.className = `conversation-item${chat.id === state.activeChat ? ' active' : ''}`;
    const initial = (chat.name || '?').charAt(0);
    const isAgent = chat.name === 'Agent-Pilot';
    const preview = chat.last_message ? chat.last_message.content.slice(0, 30) : '';
    const time = chat.last_message ? formatTime(chat.last_message.created_at) : '';
    item.innerHTML = `
      <div class="avatar${isAgent ? ' agent-avatar' : ''}">${isAgent ? '🤖' : initial}</div>
      <div class="conv-info">
        <span class="conv-name">${chat.name || chat.id}</span>
        <span class="conv-preview">${escapeHtml(preview)}</span>
      </div>
      <div class="conv-meta">
        <span class="conv-time">${time}</span>
      </div>
    `;
    item.addEventListener('click', () => openChat(chat.id, chat.name));
    list.appendChild(item);
  });
}

async function openChat(chatId, chatName) {
  state.activeChat = chatId;
  document.getElementById('chat-title').textContent = chatName || chatId;
  document.getElementById('chat-subtitle').textContent = '';
  renderChats();
  await loadMessages(chatId);
}

// ==================== IM - Messages ====================
async function loadMessages(chatId) {
  try {
    const res = await fetch(`${API_BASE}/api/chats/${chatId}/messages`);
    state.messages = await res.json();
    renderMessages();
    scrollToBottom();
  } catch (e) {
    console.error('Failed to load messages:', e);
  }
}

function renderMessages() {
  const list = document.getElementById('message-list');
  list.innerHTML = '';
  if (state.messages.length === 0) {
    list.innerHTML = '<div class="empty-state">暂无消息</div>';
    return;
  }
  state.messages.forEach(msg => {
    const isSelf = msg.sender_id === state.currentUser;
    const isAgent = msg.sender_id === 'agent';
    const div = document.createElement('div');
    div.className = `message${isSelf ? ' self' : ''}${isAgent ? ' agent' : ''}`;

    const avatarText = isAgent ? '🤖' : msg.sender_id.charAt(0).toUpperCase();
    const avatarClass = isAgent ? 'avatar agent-avatar' : 'avatar';

    let bodyHtml;
    if (msg.msg_type === 'agent_card' && msg.card_data) {
      bodyHtml = renderAgentCard(msg);
    } else {
      bodyHtml = `<div class="message-body">${formatMessageContent(msg.content)}</div>`;
    }

    div.innerHTML = `
      <div class="${avatarClass}">${avatarText}</div>
      <div class="message-content">
        ${!isSelf ? `<div class="message-sender">${msg.sender_id}</div>` : ''}
        ${bodyHtml}
        <div class="message-time">${formatTime(msg.created_at)}</div>
      </div>
    `;
    list.appendChild(div);
  });
}

function renderAgentCard(msg) {
  const card = msg.card_data;
  if (!card) return `<div class="message-body">${escapeHtml(msg.content)}</div>`;

  let headerIcon = '🤖';
  let headerTitle = 'Agent-Pilot';
  let bodyContent = formatMessageContent(msg.content);
  let extra = '';

  if (card.type === 'plan') {
    headerIcon = '📋';
    headerTitle = '执行计划';
  } else if (card.type === 'delivery') {
    headerIcon = '✅';
    headerTitle = '任务完成';
    if (card.results && card.results.artifacts) {
      extra = card.results.artifacts.map(art => {
        const viewName = art.type === 'document' ? '文档' : '演示稿';
        return `<span class="artifact-link" onclick="viewArtifact('${art.type}','${art.id}')"">查看${viewName}: ${art.title}</span>`;
      }).join(' ');
    }
  } else if (card.type === 'clarification') {
    headerIcon = '❓';
    headerTitle = '需要确认';
  }

  let progressHtml = '';
  if (card.task_id && card.type === 'plan') {
    progressHtml = `<div class="progress-bar"><div class="progress-fill" id="progress-${card.task_id}" style="width: 0%"></div></div>`;
  }

  return `
    <div class="agent-card">
      <div class="agent-card-header">
        <span class="icon">${headerIcon}</span>
        <span class="title">${headerTitle}</span>
      </div>
      <div class="agent-card-body">${bodyContent}</div>
      ${extra}
      ${progressHtml}
    </div>
  `;
}

function viewArtifact(type, id) {
  if (type === 'document') {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelector('[data-view="documents"]').classList.add('active');
    document.getElementById('view-documents').classList.add('active');
    loadDocumentContent(id);
  } else if (type === 'presentation') {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelector('[data-view="slides"]').classList.add('active');
    document.getElementById('view-slides').classList.add('active');
    loadSlidesContent(id);
  }
}

// ==================== Composer ====================
function initComposer() {
  const form = document.getElementById('composer');
  const input = document.getElementById('message-input');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = input.value.trim();
    if (!content || !state.activeChat) return;
    input.value = '';
    await sendMessage(content);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit'));
    }
  });
}

async function sendMessage(content) {
  try {
    await fetch(`${API_BASE}/api/chats/${state.activeChat}/messages?user_id=${state.currentUser}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, msg_type: 'text' }),
    });

    const isAgentChat = state.chats.find(c => c.id === state.activeChat)?.name === 'Agent-Pilot';
    const hasCommand = /帮我|生成|创建|写一|做一|总结|整理/.test(content);
    if (isAgentChat || hasCommand) {
      await fetch(`${API_BASE}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          chat_id: state.activeChat,
          user_id: state.currentUser,
        }),
      });
    }
  } catch (e) {
    console.error('Failed to send message:', e);
  }
}

// ==================== Documents ====================
async function loadDocuments() {
  try {
    const res = await fetch(`${API_BASE}/api/documents`);
    state.documents = await res.json();
    renderDocumentList();
  } catch (e) {
    console.error('Failed to load documents:', e);
  }
}

function renderDocumentList() {
  const list = document.getElementById('document-list');
  list.innerHTML = '';
  if (state.documents.length === 0) {
    list.innerHTML = '<div style="padding:20px;color:var(--text-secondary);font-size:13px;">暂无文档。在 IM 中对 Agent 说「帮我写一份...」即可生成。</div>';
    return;
  }
  state.documents.forEach(doc => {
    const item = document.createElement('div');
    item.className = 'doc-item';
    item.innerHTML = `
      <div class="avatar" style="background:#6366f1;">📄</div>
      <div class="conv-info">
        <span class="conv-name">${escapeHtml(doc.title)}</span>
        <span class="conv-preview">${doc.status} · ${formatTime(doc.updated_at)}</span>
      </div>
    `;
    item.addEventListener('click', () => loadDocumentContent(doc.id));
    list.appendChild(item);
  });
}

async function loadDocumentContent(docId) {
  try {
    const res = await fetch(`${API_BASE}/api/documents/${docId}`);
    const doc = await res.json();
    const container = document.getElementById('doc-content');
    container.innerHTML = renderMarkdown(doc.content || `# ${doc.title}\n\n文档内容加载中...`);

    document.querySelectorAll('.doc-item').forEach(el => el.classList.remove('active'));
  } catch (e) {
    console.error('Failed to load document:', e);
  }
}

// ==================== Presentations ====================
async function loadPresentations() {
  try {
    const res = await fetch(`${API_BASE}/api/presentations`);
    state.presentations = await res.json();
    renderSlidesList();
  } catch (e) {
    console.error('Failed to load presentations:', e);
  }
}

function renderSlidesList() {
  const list = document.getElementById('slides-list');
  list.innerHTML = '';
  if (state.presentations.length === 0) {
    list.innerHTML = '<div style="padding:20px;color:var(--text-secondary);font-size:13px;">暂无演示稿。在 IM 中对 Agent 说「帮我做一个PPT」即可生成。</div>';
    return;
  }
  state.presentations.forEach(pres => {
    const slides = typeof pres.slides === 'string' ? JSON.parse(pres.slides) : (pres.slides || []);
    const item = document.createElement('div');
    item.className = 'slides-item';
    item.innerHTML = `
      <div class="avatar" style="background:#8b5cf6;">📊</div>
      <div class="conv-info">
        <span class="conv-name">${escapeHtml(pres.title)}</span>
        <span class="conv-preview">${slides.length} 页 · ${formatTime(pres.updated_at)}</span>
      </div>
    `;
    item.addEventListener('click', () => loadSlidesContent(pres.id));
    list.appendChild(item);
  });
}

async function loadSlidesContent(presId) {
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}`);
    const pres = await res.json();
    const slides = typeof pres.slides === 'string' ? JSON.parse(pres.slides) : (pres.slides || []);
    const container = document.getElementById('slides-content');
    container.innerHTML = '';

    if (slides.length === 0) {
      container.innerHTML = '<div class="empty-state">演示稿暂无内容</div>';
      return;
    }

    slides.forEach((slide, idx) => {
      const el = document.createElement('div');
      el.className = `slide layout-${slide.layout}`;
      el.innerHTML = renderSlide(slide, idx + 1, slides.length);
      container.appendChild(el);
    });
  } catch (e) {
    console.error('Failed to load slides:', e);
  }
}

function renderSlide(slide, num, total) {
  const d = slide.data || {};
  const numHtml = `<div class="slide-number">${num} / ${total}</div>`;

  switch (slide.layout) {
    case 'title':
      return `<h1>${escapeHtml(d.title || '')}</h1><p>${escapeHtml(d.subtitle || '')}</p>${numHtml}`;
    case 'content':
      const points = (d.points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('');
      return `<h2>${escapeHtml(d.title || '')}</h2><ul>${points}</ul>${numHtml}`;
    case 'two_column':
      const lp = (d.left_points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('');
      const rp = (d.right_points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('');
      return `
        <h2>${escapeHtml(d.title || '')}</h2>
        <div class="columns">
          <div class="column"><h3>${escapeHtml(d.left_title || '左栏')}</h3><ul>${lp}</ul></div>
          <div class="column"><h3>${escapeHtml(d.right_title || '右栏')}</h3><ul>${rp}</ul></div>
        </div>${numHtml}`;
    case 'summary':
      const sp = (d.points || []).map(p => `<li>${escapeHtml(p)}</li>`).join('');
      return `<h2>${escapeHtml(d.title || '')}</h2><ul>${sp}</ul>${numHtml}`;
    case 'image_text':
      return `<h2>${escapeHtml(d.title || '')}</h2><p>${escapeHtml(d.text || '')}</p>${numHtml}`;
    default:
      return `<h2>${escapeHtml(d.title || '幻灯片')}</h2><p>${JSON.stringify(d)}</p>${numHtml}`;
  }
}

// ==================== Utilities ====================
function formatTime(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatMessageContent(content) {
  if (!content) return '';
  let html = escapeHtml(content);
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\n/g, '<br>');
  return html;
}

function renderMarkdown(md) {
  if (!md) return '';
  let html = escapeHtml(md);
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
  html = html.replace(/<\/ul>\s*<ul>/g, '');
  html = html.replace(/\n\n/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');
  html = `<p>${html}</p>`;
  html = html.replace(/<p><h([123])>/g, '<h$1>');
  html = html.replace(/<\/h([123])><\/p>/g, '</h$1>');
  html = html.replace(/<p><ul>/g, '<ul>');
  html = html.replace(/<\/ul><\/p>/g, '</ul>');
  return html;
}

function scrollToBottom() {
  const list = document.getElementById('message-list');
  setTimeout(() => { list.scrollTop = list.scrollHeight; }, 50);
}
