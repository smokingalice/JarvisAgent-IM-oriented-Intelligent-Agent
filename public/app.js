const state = {
  users: [],
  currentUser: null,
  activeChatUser: null,
  conversations: [],
  messages: [],
  conversationQuery: "",
  messageQuery: "",
  replyToId: null,
  menuMessageId: null,
};

const viewerSelect = document.querySelector("#viewer-select");
const currentUserAvatar = document.querySelector("#current-user-avatar");
const currentUserName = document.querySelector("#current-user-name");
const currentUserStatus = document.querySelector("#current-user-status");
const conversationSearch = document.querySelector("#conversation-search");
const conversationList = document.querySelector("#conversation-list");
const chatTitle = document.querySelector("#chat-title");
const chatSubtitle = document.querySelector("#chat-subtitle");
const chatAvatar = document.querySelector("#chat-avatar");
const pinButton = document.querySelector("#pin-button");
const messageSearch = document.querySelector("#message-search");
const messageList = document.querySelector("#message-list");
const messageMenu = document.querySelector("#message-menu");
const composer = document.querySelector("#composer");
const messageInput = document.querySelector("#message-input");
const clearButton = document.querySelector("#clear-button");
const emojiButtons = document.querySelectorAll(".emoji-button");
const replyBanner = document.querySelector("#reply-banner");
const replyBannerName = document.querySelector("#reply-banner-name");
const replyBannerContent = document.querySelector("#reply-banner-content");
const cancelReplyButton = document.querySelector("#cancel-reply-button");
const conversationTemplate = document.querySelector("#conversation-template");
const timeDividerTemplate = document.querySelector("#time-divider-template");
const messageTemplate = document.querySelector("#message-template");

init();

async function init() {
  bindEvents();
  connectEvents();
  await refresh();
}

function bindEvents() {
  messageInput.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    event.preventDefault();
    await sendCurrentMessage();
  });

  messageInput.addEventListener("input", () => {
    saveDraft(messageInput.value);
  });

  viewerSelect.addEventListener("change", async () => {
    const nextViewerId = viewerSelect.value;
    const nextTargetId = firstAvailableChat(nextViewerId);
    clearReply();
    await refresh(nextViewerId, nextTargetId);
  });

  conversationSearch.addEventListener("input", () => {
    state.conversationQuery = conversationSearch.value.trim().toLowerCase();
    renderConversations();
  });

  messageSearch.addEventListener("input", () => {
    state.messageQuery = messageSearch.value.trim().toLowerCase();
    renderMessages();
  });

  pinButton.addEventListener("click", async () => {
    await fetch("/api/conversations/pin", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        viewerId: state.currentUser.id,
        targetId: state.activeChatUser.id,
        pinned: !activeConversation()?.pinned,
      }),
    });

    await refresh(state.currentUser.id, state.activeChatUser.id);
  });

  clearButton.addEventListener("click", async () => {
    await fetch("/api/messages", { method: "DELETE" });
    clearDeletedSet();
    clearReply();
    hideMessageMenu();
    await refresh(state.currentUser.id, state.activeChatUser.id);
  });

  cancelReplyButton.addEventListener("click", () => {
    clearReply();
  });

  composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    await sendCurrentMessage();
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("#message-menu")) {
      hideMessageMenu();
    }
  });

  document.addEventListener("scroll", () => {
    hideMessageMenu();
  }, true);

  window.addEventListener("resize", () => {
    hideMessageMenu();
  });

  messageMenu.addEventListener("click", async (event) => {
    const button = event.target.closest(".message-menu-item");
    if (!button || !state.menuMessageId) {
      return;
    }

    const message = findMessage(state.menuMessageId);
    hideMessageMenu();
    if (!message) {
      return;
    }

    await handleMessageAction(button.dataset.action, message);
  });

  emojiButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const emoji = button.dataset.emoji || "";
      const prefix = messageInput.value && !messageInput.value.endsWith(" ") ? " " : "";
      messageInput.value += `${prefix}${emoji}`;
      saveDraft(messageInput.value);
      messageInput.focus();
    });
  });
}

function connectEvents() {
  const stream = new EventSource("/api/events");
  const refreshCurrent = async () => {
    await refresh(state.currentUser?.id, state.activeChatUser?.id);
  };

  stream.addEventListener("message", refreshCurrent);
  stream.addEventListener("reset", refreshCurrent);
  stream.addEventListener("message-status", refreshCurrent);
  stream.addEventListener("conversation-updated", refreshCurrent);
  stream.addEventListener("message-recalled", refreshCurrent);
}

async function refresh(viewerId = state.currentUser?.id, targetId = state.activeChatUser?.id) {
  const query = new URLSearchParams();
  if (viewerId) query.set("viewerId", viewerId);
  if (targetId) query.set("targetId", targetId);

  const response = await fetch(`/api/bootstrap?${query.toString()}`);
  const data = await response.json();

  state.users = data.users;
  state.currentUser = data.currentUser;
  state.activeChatUser = data.activeChatUser;
  state.conversations = data.conversations;
  state.messages = data.messages;

  if (state.replyToId && !state.messages.find((message) => message.id === state.replyToId)) {
    clearReply();
  }

  render();
}

async function sendCurrentMessage() {
  const text = messageInput.value.trim();
  if (!text) {
    return;
  }

  await fetch("/api/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      senderId: state.currentUser.id,
      receiverId: state.activeChatUser.id,
      text,
      replyToId: state.replyToId,
    }),
  });

  messageInput.value = "";
  saveDraft("");
  clearReply();
  await refresh(state.currentUser.id, state.activeChatUser.id);
}

function render() {
  renderCurrentUser();
  renderConversations();
  renderHeader();
  renderReplyBanner();
  renderMessages();
  restoreDraft();
}

function renderCurrentUser() {
  viewerSelect.innerHTML = "";

  state.users.forEach((user) => {
    const option = document.createElement("option");
    option.value = user.id;
    option.textContent = user.name;
    option.selected = user.id === state.currentUser.id;
    viewerSelect.appendChild(option);
  });

  currentUserAvatar.textContent = initials(state.currentUser.name);
  currentUserName.textContent = state.currentUser.name;
  currentUserStatus.textContent = state.currentUser.status;
}

function renderConversations() {
  conversationList.innerHTML = "";

  const filtered = state.conversations.filter((conversation) => {
    if (!state.conversationQuery) {
      return true;
    }

    const haystack = [conversation.name, conversation.status, buildPreview(conversation)]
      .join(" ")
      .toLowerCase();
    return haystack.includes(state.conversationQuery);
  });

  if (!filtered.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "没有匹配的联系人或消息。";
    conversationList.appendChild(empty);
    return;
  }

  filtered.forEach((conversation) => {
    const item = conversationTemplate.content.firstElementChild.cloneNode(true);
    item.querySelector(".avatar").textContent = initials(conversation.name);
    item.querySelector(".conversation-name").textContent = conversation.name;
    item.querySelector(".conversation-time").textContent = conversation.lastMessage
      ? formatConversationTime(conversation.lastMessage.createdAt)
      : "";
    item.querySelector(".conversation-preview").textContent = buildPreview(conversation);

    const badge = item.querySelector(".conversation-badge");
    if (conversation.unreadCount > 0) {
      badge.textContent = conversation.unreadCount > 99 ? "99+" : String(conversation.unreadCount);
      badge.classList.add("visible");
    }

    if (conversation.id === state.activeChatUser.id) {
      item.classList.add("active");
    }

    if (conversation.pinned) {
      item.classList.add("pinned");
    }

    item.addEventListener("click", async () => {
      clearReply();
      await refresh(state.currentUser.id, conversation.id);
    });

    conversationList.appendChild(item);
  });
}

function renderHeader() {
  chatAvatar.textContent = initials(state.activeChatUser.name);
  chatTitle.textContent = state.activeChatUser.name;
  chatSubtitle.textContent = state.activeChatUser.status;
  pinButton.textContent = activeConversation()?.pinned ? "已置顶" : "置顶";
  pinButton.classList.toggle("active", Boolean(activeConversation()?.pinned));
}

function renderReplyBanner() {
  const replyTarget = findMessage(state.replyToId);
  if (!replyTarget) {
    replyBanner.classList.add("hidden");
    return;
  }

  const sender = findUser(replyTarget.senderId);
  replyBannerName.textContent = `回复 ${sender.name}`;
  replyBannerContent.textContent = previewText(replyTarget.text);
  replyBanner.classList.remove("hidden");
}

function renderMessages() {
  messageList.innerHTML = "";
  hideMessageMenu();

  const filteredMessages = visibleMessages().filter((message) => {
    if (!state.messageQuery) {
      return true;
    }

    const replySource = message.replyToId ? findMessage(message.replyToId)?.text || "" : "";
    return `${message.text} ${replySource}`.toLowerCase().includes(state.messageQuery);
  });

  if (!filteredMessages.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = state.messageQuery
      ? "当前会话里没有匹配的消息。"
      : "当前两人之间还没有消息，直接发送即可开始通信。";
    messageList.appendChild(empty);
    return;
  }

  filteredMessages.forEach((message, index) => {
    const previous = filteredMessages[index - 1];
    if (shouldInsertTimeDivider(previous, message)) {
      const divider = timeDividerTemplate.content.firstElementChild.cloneNode(true);
      divider.querySelector("span").textContent = formatTimeline(message.createdAt);
      messageList.appendChild(divider);
    }

    const node = messageTemplate.content.firstElementChild.cloneNode(true);
    const sender = findUser(message.senderId);
    node.querySelector(".avatar").textContent = initials(sender.name);
    node.querySelector(".message-sender").textContent = sender.name;
    node.querySelector(".message-time").textContent = formatTime(message.createdAt);
    node.querySelector(".message-body").textContent = message.text;
    node.querySelector(".message-status").textContent = buildMessageStatus(message);

    if (message.recalledAt) {
      node.classList.add("recalled");
    }

    if (state.messageQuery) {
      node.querySelector(".message-body").classList.add("marked");
    }

    const quote = node.querySelector(".reply-quote");
    const replySource = message.replyToId ? findMessage(message.replyToId) : null;
    if (replySource) {
      const quoteSender = findUser(replySource.senderId);
      quote.querySelector(".reply-quote-name").textContent = quoteSender.name;
      quote.querySelector(".reply-quote-content").textContent = previewText(replySource.text);
      quote.classList.remove("hidden");
    }

    if (message.senderId === state.currentUser.id) {
      node.classList.add("self");
    }

    node.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      openMessageMenu(event.clientX, event.clientY, message);
    });

    messageList.appendChild(node);
  });

  messageList.scrollTop = messageList.scrollHeight;
}

async function handleMessageAction(action, message) {
  if (action === "reply") {
    state.replyToId = message.id;
    renderReplyBanner();
    messageInput.focus();
    return;
  }

  if (action === "copy") {
    await copyText(message.text);
    return;
  }

  if (action === "delete") {
    hideMessageForCurrentUser(message.id);
    renderMessages();
    return;
  }

  if (action === "recall") {
    const response = await fetch("/api/messages/recall", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        viewerId: state.currentUser.id,
        messageId: message.id,
      }),
    });

    if (!response.ok) {
      window.alert("这条消息当前不能撤回。");
      return;
    }

    if (state.replyToId === message.id) {
      clearReply();
    }

    await refresh(state.currentUser.id, state.activeChatUser.id);
  }
}

function openMessageMenu(x, y, message) {
  state.menuMessageId = message.id;

  const recallItem = messageMenu.querySelector('[data-action="recall"]');
  recallItem.classList.toggle("hidden", !canRecall(message));

  messageMenu.classList.remove("hidden");
  messageMenu.style.left = "0px";
  messageMenu.style.top = "0px";

  const menuRect = messageMenu.getBoundingClientRect();
  const maxLeft = window.innerWidth - menuRect.width - 8;
  const maxTop = window.innerHeight - menuRect.height - 8;
  const left = Math.max(8, Math.min(x, maxLeft));
  const top = Math.max(8, Math.min(y, maxTop));

  messageMenu.style.left = `${left}px`;
  messageMenu.style.top = `${top}px`;
}

function hideMessageMenu() {
  state.menuMessageId = null;
  messageMenu.classList.add("hidden");
}

function visibleMessages() {
  const hidden = hiddenMessageIds();
  return state.messages.filter((message) => !hidden.has(message.id));
}

function hiddenMessageIds() {
  try {
    const raw = window.localStorage.getItem(hiddenKey());
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    return new Set();
  }
}

function hideMessageForCurrentUser(messageId) {
  const hidden = hiddenMessageIds();
  hidden.add(messageId);
  window.localStorage.setItem(hiddenKey(), JSON.stringify([...hidden]));
}

function clearDeletedSet() {
  if (!state.currentUser || !state.activeChatUser) {
    return;
  }

  window.localStorage.removeItem(hiddenKey());
}

function hiddenKey() {
  return `im-hidden:${state.currentUser.id}:${state.activeChatUser.id}`;
}

function clearReply() {
  state.replyToId = null;
  replyBanner.classList.add("hidden");
}

function shouldInsertTimeDivider(previous, current) {
  if (!previous) {
    return true;
  }

  const diff = Math.abs(Date.parse(current.createdAt) - Date.parse(previous.createdAt));
  return diff > 1000 * 60 * 5;
}

function buildMessageStatus(message) {
  if (message.senderId !== state.currentUser.id) {
    return "";
  }

  if (message.recalledAt) {
    return "已撤回";
  }

  if (message.readAt) {
    return "已读";
  }

  if (message.deliveredAt) {
    return "已送达";
  }

  return "发送中";
}

function canRecall(message) {
  if (message.senderId !== state.currentUser.id || message.recalledAt) {
    return false;
  }

  return Date.now() - Date.parse(message.createdAt) <= 1000 * 60 * 2;
}

function firstAvailableChat(viewerId) {
  const candidate = state.users.find((user) => user.id !== viewerId);
  return candidate ? candidate.id : "";
}

function findUser(userId) {
  return state.users.find((user) => user.id === userId);
}

function findMessage(messageId) {
  return state.messages.find((message) => message.id === messageId) || null;
}

function activeConversation() {
  return state.conversations.find((conversation) => conversation.id === state.activeChatUser.id);
}

function buildPreview(conversation) {
  if (!conversation.lastMessage) {
    return conversation.status;
  }

  if (conversation.lastMessage.recalledAt) {
    return conversation.lastMessage.senderId === state.currentUser.id
      ? "你撤回了一条消息"
      : `${conversation.name} 撤回了一条消息`;
  }

  const sender = conversation.lastMessage.senderId === state.currentUser.id ? "你" : conversation.name;
  return `${sender}: ${conversation.lastMessage.text}`;
}

function formatTime(isoString) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(isoString));
}

function formatConversationTime(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  if (sameDay) {
    return formatTime(isoString);
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function formatTimeline(isoString) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(isoString));
}

function initials(name) {
  return name.slice(0, 1).toUpperCase();
}

function previewText(text) {
  return text.length > 36 ? `${text.slice(0, 36)}...` : text;
}

function draftKey() {
  return `im-draft:${state.currentUser.id}:${state.activeChatUser.id}`;
}

function saveDraft(value) {
  if (!state.currentUser || !state.activeChatUser) {
    return;
  }

  window.localStorage.setItem(draftKey(), value);
}

function restoreDraft() {
  if (!state.currentUser || !state.activeChatUser) {
    return;
  }

  const draft = window.localStorage.getItem(draftKey()) || "";
  if (messageInput.value !== draft) {
    messageInput.value = draft;
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    window.prompt("复制下面的内容", text);
  }
}
