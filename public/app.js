const API_BASE = '';
const WS_BASE = `ws://${location.host}`;

const state = {
  token: localStorage.getItem('jarvis_token') || null,
  currentUser: JSON.parse(localStorage.getItem('jarvis_user') || 'null'),
  activeChat: null,
  chats: [],
  messages: [],
  documents: [],
  presentations: [],
  friends: [],
  ws: null,
};

// ==================== Init ====================
document.addEventListener('DOMContentLoaded', () => {
  if (state.token && state.currentUser) {
    showMainApp();
  } else {
    showAuthPage();
  }
});

// ==================== Auth ====================
function showAuthPage() {
  document.getElementById('auth-page').style.display = 'flex';
  document.getElementById('main-app').style.display = 'none';
}

function showMainApp() {
  document.getElementById('auth-page').style.display = 'none';
  document.getElementById('main-app').style.display = 'flex';
  document.getElementById('nav-username').textContent = state.currentUser.name || state.currentUser.id;
  initNav();
  initComposer();
  initVoiceInput();
  connectWebSocket();
  loadChats();
  loadDocuments();
  loadPresentations();
  loadFriends();
  loadFriendRequests();
}

function showLogin() {
  document.getElementById('auth-form-login').style.display = 'block';
  document.getElementById('auth-form-register').style.display = 'none';
}

function showRegister() {
  document.getElementById('auth-form-login').style.display = 'none';
  document.getElementById('auth-form-register').style.display = 'block';
}

async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errorEl = document.getElementById('login-error');
  errorEl.style.display = 'none';

  if (!username || !password) { errorEl.textContent = '请填写用户名和密码'; errorEl.style.display = 'block'; return; }

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      errorEl.textContent = err.detail || '登录失败';
      errorEl.style.display = 'block';
      return;
    }
    const data = await res.json();
    state.token = data.token;
    state.currentUser = data.user;
    localStorage.setItem('jarvis_token', data.token);
    localStorage.setItem('jarvis_user', JSON.stringify(data.user));
    showMainApp();
  } catch (e) {
    errorEl.textContent = '网络错误，请重试';
    errorEl.style.display = 'block';
  }
}

async function doRegister() {
  const username = document.getElementById('reg-username').value.trim();
  const name = document.getElementById('reg-name').value.trim();
  const password = document.getElementById('reg-password').value;
  const errorEl = document.getElementById('reg-error');
  errorEl.style.display = 'none';

  if (!username || !password) { errorEl.textContent = '请填写必填字段'; errorEl.style.display = 'block'; return; }

  try {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, name: name || username }),
    });
    if (!res.ok) {
      const err = await res.json();
      errorEl.textContent = err.detail || '注册失败';
      errorEl.style.display = 'block';
      return;
    }
    const data = await res.json();
    state.token = data.token;
    state.currentUser = data.user;
    localStorage.setItem('jarvis_token', data.token);
    localStorage.setItem('jarvis_user', JSON.stringify(data.user));
    showMainApp();
    showToast('注册成功！', 'success');
  } catch (e) {
    errorEl.textContent = '网络错误，请重试';
    errorEl.style.display = 'block';
  }
}

function doLogout() {
  state.token = null;
  state.currentUser = null;
  localStorage.removeItem('jarvis_token');
  localStorage.removeItem('jarvis_user');
  if (state.ws) { state.ws.close(); state.ws = null; }
  showAuthPage();
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  return headers;
}

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

// ==================== WebSocket ====================
function connectWebSocket() {
  const url = state.token ? `${WS_BASE}/ws?token=${state.token}` : `${WS_BASE}/ws`;
  state.ws = new WebSocket(url);
  state.ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleWsMessage(msg);
  };
  state.ws.onclose = () => {
    setTimeout(connectWebSocket, 3000);
  };
  state.ws.onerror = () => {};
}

function handleWsMessage(msg) {
  switch (msg.type) {
    case 'new_message':
      handleNewMessage(msg.data);
      break;
    case 'message_recalled':
      if (msg.data.chat_id === state.activeChat) {
        loadMessages(state.activeChat);
      }
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
    case 'friend_request':
      loadFriendRequests();
      showToast('收到新的好友请求！');
      break;
    case 'friend_accepted':
      loadFriends();
      loadChats();
      showToast(`${msg.data.user_name || '好友'} 接受了你的好友请求！`, 'success');
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

  // Trigger agent summary only for messages received from others (not self, not agent)
  if (message.sender_id !== state.currentUser.id && message.sender_id !== 'agent') {
    triggerAgentSummary(message);
  }
}

async function triggerAgentSummary(message) {
  try {
    const res = await fetch(`${API_BASE}/api/agent/chat`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        message: message.content,
        chat_id: message.chat_id,
        user_id: state.currentUser.id,
        mode: 'summary',
      }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.summary) {
        showAgentHint(message.chat_id, data.summary);
      }
    }
  } catch (e) {
    console.error('Agent summary failed:', e);
  }
}

function showAgentHint(chatId, summary) {
  if (chatId !== state.activeChat) return;
  const list = document.getElementById('message-list');
  const hint = document.createElement('div');
  hint.className = 'agent-hint';
  hint.textContent = `✨ ${summary}`;
  list.appendChild(hint);
  scrollToBottom();
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
    const res = await fetch(`${API_BASE}/api/chats`, { headers: authHeaders() });
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
    const displayName = chat.display_name || chat.name || '?';
    const initial = displayName.charAt(0);
    const isAgent = displayName === 'JarvisAgent';
    const preview = chat.last_message ? chat.last_message.content.slice(0, 30) : '';
    const time = chat.last_message ? formatTime(chat.last_message.created_at) : '';
    item.innerHTML = `
      <div class="avatar${isAgent ? ' agent-avatar' : ''}">${isAgent ? '🤖' : initial}</div>
      <div class="conv-info">
        <span class="conv-name">${escapeHtml(displayName)}</span>
        <span class="conv-preview">${escapeHtml(preview)}</span>
      </div>
      <div class="conv-meta">
        <span class="conv-time">${time}</span>
        ${chat.unread_count > 0 ? `<span class="conv-badge">${chat.unread_count}</span>` : ''}
      </div>
    `;
    item.addEventListener('click', () => openChat(chat.id, displayName));
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
    const res = await fetch(`${API_BASE}/api/chats/${chatId}/messages`, { headers: authHeaders() });
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
    const isSelf = msg.sender_id === state.currentUser.id;
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
        ${!isSelf ? `<div class="message-sender">${escapeHtml(msg.sender_id)}</div>` : ''}
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
  let headerTitle = 'JarvisAgent';
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
        return `<span class="artifact-link" onclick="viewArtifact('${art.type}','${art.id}')">查看${viewName}: ${escapeHtml(art.title)}</span>`;
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
    switchView('documents');
    loadDocumentContent(id);
  } else if (type === 'presentation') {
    switchView('slides');
    loadSlidesContent(id);
  }
}

function switchView(viewName) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelector(`[data-view="${viewName}"]`).classList.add('active');
  document.getElementById(`view-${viewName}`).classList.add('active');
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
    await fetch(`${API_BASE}/api/chats/${state.activeChat}/messages`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ content, msg_type: 'text' }),
    });
  } catch (e) {
    console.error('Failed to send message:', e);
    showToast('发送失败，请重试', 'error');
  }
}

// ==================== Friends ====================
async function loadFriends() {
  try {
    const res = await fetch(`${API_BASE}/api/friends`, { headers: authHeaders() });
    state.friends = await res.json();
    renderFriendsList();
  } catch (e) {
    console.error('Failed to load friends:', e);
  }
}

function renderFriendsList() {
  const list = document.getElementById('friends-list');
  list.innerHTML = '';
  if (state.friends.length === 0) {
    list.innerHTML = '<div style="padding:20px;color:var(--text-secondary);font-size:13px;">暂无好友。在右侧搜索添加好友。</div>';
    return;
  }
  state.friends.forEach(friend => {
    const item = document.createElement('div');
    item.className = 'friend-item';
    item.innerHTML = `
      <div class="avatar">${friend.name.charAt(0)}</div>
      <div class="conv-info">
        <span class="conv-name">${escapeHtml(friend.name)}</span>
        <span class="conv-preview">@${escapeHtml(friend.id)}</span>
      </div>
    `;
    list.appendChild(item);
  });
}

async function loadFriendRequests() {
  try {
    const res = await fetch(`${API_BASE}/api/friends/requests`, { headers: authHeaders() });
    const data = await res.json();
    renderFriendRequests(data);
  } catch (e) {
    console.error('Failed to load friend requests:', e);
  }
}

function renderFriendRequests(data) {
  const container = document.getElementById('friend-requests');
  container.innerHTML = '';

  if (data.incoming.length === 0 && data.outgoing.length === 0) {
    container.innerHTML = '<div style="color:var(--text-secondary);font-size:13px;">暂无好友请求</div>';
    return;
  }

  data.incoming.forEach(req => {
    const div = document.createElement('div');
    div.className = 'friend-request-item';
    div.innerHTML = `
      <div class="avatar">${(req.from_name || req.from_user_id).charAt(0)}</div>
      <div class="conv-info">
        <span class="conv-name">${escapeHtml(req.from_name || req.from_user_id)}</span>
        <span class="conv-preview">请求添加你为好友</span>
      </div>
      <div class="actions">
        <button class="btn-accept" onclick="acceptFriend('${req.id}')">接受</button>
        <button class="btn-reject" onclick="rejectFriend('${req.id}')">拒绝</button>
      </div>
    `;
    container.appendChild(div);
  });

  data.outgoing.forEach(req => {
    const div = document.createElement('div');
    div.className = 'friend-request-item';
    div.innerHTML = `
      <div class="avatar">${(req.to_name || req.to_user_id).charAt(0)}</div>
      <div class="conv-info">
        <span class="conv-name">${escapeHtml(req.to_name || req.to_user_id)}</span>
        <span class="conv-preview">等待对方接受</span>
      </div>
    `;
    container.appendChild(div);
  });
}

async function searchAndAddFriend() {
  const input = document.getElementById('add-friend-input');
  const q = input.value.trim();
  if (!q) return;

  try {
    const res = await fetch(`${API_BASE}/api/users/search?q=${encodeURIComponent(q)}`, { headers: authHeaders() });
    const users = await res.json();
    const container = document.getElementById('search-results');
    container.innerHTML = '';

    if (users.length === 0) {
      container.innerHTML = '<div style="color:var(--text-secondary);font-size:13px;padding:8px 0;">未找到用户</div>';
      return;
    }

    users.forEach(user => {
      const div = document.createElement('div');
      div.className = 'friend-request-item';
      div.innerHTML = `
        <div class="avatar">${user.name.charAt(0)}</div>
        <div class="conv-info">
          <span class="conv-name">${escapeHtml(user.name)}</span>
          <span class="conv-preview">@${escapeHtml(user.id)}</span>
        </div>
        <div class="actions">
          <button class="btn-accept" onclick="sendFriendRequest('${user.id}')">添加</button>
        </div>
      `;
      container.appendChild(div);
    });
  } catch (e) {
    showToast('搜索失败', 'error');
  }
}

async function sendFriendRequest(targetId) {
  try {
    const res = await fetch(`${API_BASE}/api/friends/request?target_user_id=${targetId}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (res.ok) {
      showToast('好友请求已发送！', 'success');
      loadFriendRequests();
    } else {
      const err = await res.json();
      showToast(err.detail || '发送失败', 'error');
    }
  } catch (e) {
    showToast('网络错误', 'error');
  }
}

async function acceptFriend(friendshipId) {
  try {
    const res = await fetch(`${API_BASE}/api/friends/accept/${friendshipId}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (res.ok) {
      showToast('已接受好友请求', 'success');
      loadFriends();
      loadFriendRequests();
      loadChats();
    }
  } catch (e) {
    showToast('操作失败', 'error');
  }
}

async function rejectFriend(friendshipId) {
  try {
    await fetch(`${API_BASE}/api/friends/reject/${friendshipId}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    loadFriendRequests();
  } catch (e) {
    showToast('操作失败', 'error');
  }
}

// ==================== Documents ====================
async function loadDocuments() {
  try {
    const res = await fetch(`${API_BASE}/api/documents`, { headers: authHeaders() });
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
    const res = await fetch(`${API_BASE}/api/documents/${docId}`, { headers: authHeaders() });
    const doc = await res.json();
    const container = document.getElementById('doc-content');
    container.innerHTML = `
      <div class="doc-toolbar">
        <h2>${escapeHtml(doc.title)}</h2>
        <div class="export-btns">
          <button onclick="exportDocument('${docId}','md')" title="导出 Markdown">📥 MD</button>
          <button onclick="exportDocument('${docId}','html')" title="导出 HTML">📥 HTML</button>
        </div>
      </div>
      <div class="doc-body">${renderMarkdown(doc.content || '文档内容加载中...')}</div>
    `;
  } catch (e) {
    console.error('Failed to load document:', e);
  }
}

// ==================== Presentations ====================
async function loadPresentations() {
  try {
    const res = await fetch(`${API_BASE}/api/presentations`, { headers: authHeaders() });
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
    const res = await fetch(`${API_BASE}/api/presentations/${presId}`, { headers: authHeaders() });
    const pres = await res.json();
    const slides = typeof pres.slides === 'string' ? JSON.parse(pres.slides) : (pres.slides || []);
    const container = document.getElementById('slides-content');
    container.innerHTML = '';

    if (slides.length === 0) {
      container.innerHTML = '<div class="empty-state">演示稿暂无内容</div>';
      return;
    }

    const toolbar = document.createElement('div');
    toolbar.className = 'doc-toolbar';
    toolbar.innerHTML = `
      <h2>${escapeHtml(pres.title)}</h2>
      <div class="export-btns">
        <button onclick="exportPresentation('${presId}','json')" title="导出 JSON">📥 JSON</button>
        <button onclick="exportPresentation('${presId}','html')" title="导出 HTML">📥 HTML</button>
      </div>
    `;
    container.appendChild(toolbar);

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

function showToast(message, type = '') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ==================== Voice Input (Web Speech API) ====================
function initVoiceInput() {
  const voiceBtn = document.getElementById('voice-btn');
  if (!voiceBtn) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceBtn.style.display = 'none';
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  let isListening = false;

  voiceBtn.addEventListener('click', () => {
    if (isListening) {
      recognition.stop();
      return;
    }
    isListening = true;
    voiceBtn.classList.add('listening');
    voiceBtn.textContent = '⏹️';
    recognition.start();
  });

  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript;
    const input = document.getElementById('message-input');
    input.value = text;
    input.focus();
  };

  recognition.onend = () => {
    isListening = false;
    voiceBtn.classList.remove('listening');
    voiceBtn.textContent = '🎤';
  };

  recognition.onerror = () => {
    isListening = false;
    voiceBtn.classList.remove('listening');
    voiceBtn.textContent = '🎤';
  };
}

// ==================== Export Functions ====================
async function exportDocument(docId, format) {
  try {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/export?format=${format}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `document.${format === 'html' ? 'html' : 'md'}`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('导出成功', 'success');
  } catch (e) {
    showToast('导出失败', 'error');
  }
}

async function exportPresentation(presId, format) {
  try {
    const res = await fetch(`${API_BASE}/api/presentations/${presId}/export?format=${format}`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `presentation.${format === 'html' ? 'html' : 'json'}`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('导出成功', 'success');
  } catch (e) {
    showToast('导出失败', 'error');
  }
}
