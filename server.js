const http = require("http");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, "public");
const RECALL_WINDOW_MS = 1000 * 60 * 2;

const users = [
  { id: "alice", name: "Alice", status: "手机在线" },
  { id: "bob", name: "Bob", status: "刚刚在线" },
  { id: "charlie", name: "Charlie", status: "忙碌中" },
  { id: "diana", name: "Diana", status: "桌面在线" },
];

const messages = createSeedMessages();
const sseClients = new Set();
const pinnedByUser = new Map();

function createSeedMessages() {
  const now = Date.now();
  return [
    seedMessage("bob", "alice", "今天版本我已经看过了，聊天主流程没有问题。", now - 1000 * 60 * 55, true),
    seedMessage("alice", "bob", "好，我等下把输入区和会话列表再 polish 一下。", now - 1000 * 60 * 52, true),
    seedMessage("charlie", "alice", "明早我们可以一起过一下演示流程。", now - 1000 * 60 * 33, false),
    seedMessage("diana", "alice", "UI 这版已经比之前更像 IM 了。", now - 1000 * 60 * 15, false),
  ];
}

function seedMessage(senderId, receiverId, text, timestamp, read) {
  const iso = new Date(timestamp).toISOString();
  return {
    id: `msg_${Math.random().toString(36).slice(2, 10)}`,
    senderId,
    receiverId,
    text,
    createdAt: iso,
    deliveredAt: iso,
    readAt: read ? iso : null,
    replyToId: null,
    recalledAt: null,
  };
}

function json(res, statusCode, payload) {
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(JSON.stringify(payload));
}

function notFound(res) {
  res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("Not Found");
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";

    req.on("data", (chunk) => {
      raw += chunk;
    });

    req.on("end", () => {
      if (!raw) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });

    req.on("error", reject);
  });
}

function createMessage(senderId, receiverId, text, replyToId = null) {
  return {
    id: `msg_${Math.random().toString(36).slice(2, 10)}`,
    senderId,
    receiverId,
    text,
    createdAt: new Date().toISOString(),
    deliveredAt: null,
    readAt: null,
    replyToId,
    recalledAt: null,
  };
}

function getUser(userId) {
  return users.find((user) => user.id === userId);
}

function getPinnedSet(viewerId) {
  if (!pinnedByUser.has(viewerId)) {
    pinnedByUser.set(viewerId, new Set());
  }

  return pinnedByUser.get(viewerId);
}

function setConversationPinned(viewerId, targetId, pinned) {
  const set = getPinnedSet(viewerId);
  if (pinned) {
    set.add(targetId);
  } else {
    set.delete(targetId);
  }
}

function listMessages(viewerId, targetId) {
  const related = messages.filter((message) => {
    return (
      (message.senderId === viewerId && message.receiverId === targetId) ||
      (message.senderId === targetId && message.receiverId === viewerId)
    );
  });

  return related.sort((left, right) => Date.parse(left.createdAt) - Date.parse(right.createdAt));
}

function markMessagesRead(viewerId, targetId) {
  const readAt = new Date().toISOString();
  let changed = false;

  for (const message of messages) {
    const shouldMarkRead =
      message.senderId === targetId &&
      message.receiverId === viewerId &&
      !message.readAt &&
      !message.recalledAt;

    if (shouldMarkRead) {
      message.deliveredAt ||= readAt;
      message.readAt = readAt;
      changed = true;
    }
  }

  if (changed) {
    sendEvent("message-status", { viewerId, targetId, at: readAt });
  }
}

function unreadCount(viewerId, targetId) {
  return messages.filter((message) => {
    return (
      message.senderId === targetId &&
      message.receiverId === viewerId &&
      !message.readAt &&
      !message.recalledAt
    );
  }).length;
}

function latestActivityTime(viewerId, targetId) {
  const related = listMessages(viewerId, targetId);
  if (!related.length) {
    return 0;
  }

  return Date.parse(related[related.length - 1].createdAt);
}

function listConversations(viewerId) {
  const pinnedSet = getPinnedSet(viewerId);

  return users
    .filter((user) => user.id !== viewerId)
    .map((user) => {
      const related = listMessages(viewerId, user.id);
      const lastMessage = related[related.length - 1] || null;
      return {
        ...user,
        lastMessage,
        pinned: pinnedSet.has(user.id),
        unreadCount: unreadCount(viewerId, user.id),
        latestActivityAt: lastMessage ? lastMessage.createdAt : null,
      };
    })
    .sort((left, right) => {
      if (left.pinned !== right.pinned) {
        return left.pinned ? -1 : 1;
      }

      const timeDiff = latestActivityTime(viewerId, right.id) - latestActivityTime(viewerId, left.id);
      if (timeDiff !== 0) {
        return timeDiff;
      }

      return left.name.localeCompare(right.name);
    });
}

function bootstrap(viewerId, targetId) {
  const fallbackViewer = getUser(viewerId)?.id || users[0].id;
  const fallbackTarget =
    getUser(targetId)?.id || users.find((user) => user.id !== fallbackViewer).id;

  markMessagesRead(fallbackViewer, fallbackTarget);

  return {
    users,
    currentUser: getUser(fallbackViewer),
    activeChatUser: getUser(fallbackTarget),
    conversations: listConversations(fallbackViewer),
    messages: listMessages(fallbackViewer, fallbackTarget),
  };
}

function sendEvent(eventName, payload) {
  const data = `event: ${eventName}\ndata: ${JSON.stringify(payload)}\n\n`;
  for (const client of sseClients) {
    client.write(data);
  }
}

function scheduleDelivery(message) {
  setTimeout(() => {
    const current = messages.find((item) => item.id === message.id);
    if (!current || current.deliveredAt || current.recalledAt) {
      return;
    }

    current.deliveredAt = new Date().toISOString();
    sendEvent("message-status", { messageId: current.id, type: "delivered" });
  }, 350);
}

function serveStaticFile(filePath, res) {
  fs.readFile(filePath, (error, content) => {
    if (error) {
      notFound(res);
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = {
      ".html": "text/html; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".js": "application/javascript; charset=utf-8",
    }[ext] || "application/octet-stream";

    res.writeHead(200, { "Content-Type": contentType });
    res.end(content);
  });
}

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = requestUrl.pathname;

  if (pathname === "/api/bootstrap" && req.method === "GET") {
    json(
      res,
      200,
      bootstrap(
        requestUrl.searchParams.get("viewerId"),
        requestUrl.searchParams.get("targetId")
      )
    );
    return;
  }

  if (pathname === "/api/events" && req.method === "GET") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    });
    res.write(": connected\n\n");
    sseClients.add(res);

    req.on("close", () => {
      sseClients.delete(res);
    });
    return;
  }

  if (pathname === "/api/messages" && req.method === "POST") {
    try {
      const body = await parseBody(req);
      const senderId = String(body.senderId || "").trim();
      const receiverId = String(body.receiverId || "").trim();
      const text = String(body.text || "").trim();
      const replyToId = body.replyToId ? String(body.replyToId).trim() : null;

      if (!senderId || !receiverId || !text) {
        json(res, 400, { error: "senderId, receiverId and text are required" });
        return;
      }

      if (!getUser(senderId) || !getUser(receiverId)) {
        json(res, 400, { error: "invalid sender or receiver" });
        return;
      }

      if (senderId === receiverId) {
        json(res, 400, { error: "sender and receiver must be different" });
        return;
      }

      if (replyToId && !messages.find((message) => message.id === replyToId)) {
        json(res, 400, { error: "reply target not found" });
        return;
      }

      const message = createMessage(senderId, receiverId, text, replyToId);
      messages.push(message);
      scheduleDelivery(message);
      sendEvent("message", message);

      json(res, 201, { ok: true, message });
      return;
    } catch (error) {
      json(res, 400, { error: "invalid_json", detail: error.message });
      return;
    }
  }

  if (pathname === "/api/messages/recall" && req.method === "POST") {
    try {
      const body = await parseBody(req);
      const viewerId = String(body.viewerId || "").trim();
      const messageId = String(body.messageId || "").trim();
      const message = messages.find((item) => item.id === messageId);

      if (!viewerId || !message || message.senderId !== viewerId) {
        json(res, 400, { error: "message not recallable" });
        return;
      }

      if (message.recalledAt) {
        json(res, 400, { error: "message already recalled" });
        return;
      }

      if (Date.now() - Date.parse(message.createdAt) > RECALL_WINDOW_MS) {
        json(res, 400, { error: "recall window expired" });
        return;
      }

      const recalledAt = new Date().toISOString();
      message.recalledAt = recalledAt;
      message.text = "你撤回了一条消息";
      message.deliveredAt ||= recalledAt;
      message.readAt ||= recalledAt;
      sendEvent("message-recalled", { messageId, recalledAt });

      json(res, 200, { ok: true });
      return;
    } catch (error) {
      json(res, 400, { error: "invalid_json", detail: error.message });
      return;
    }
  }

  if (pathname === "/api/conversations/pin" && req.method === "POST") {
    try {
      const body = await parseBody(req);
      const viewerId = String(body.viewerId || "").trim();
      const targetId = String(body.targetId || "").trim();
      const pinned = Boolean(body.pinned);

      if (!getUser(viewerId) || !getUser(targetId) || viewerId === targetId) {
        json(res, 400, { error: "invalid viewer or target" });
        return;
      }

      setConversationPinned(viewerId, targetId, pinned);
      sendEvent("conversation-updated", { viewerId, targetId, pinned });
      json(res, 200, { ok: true });
      return;
    } catch (error) {
      json(res, 400, { error: "invalid_json", detail: error.message });
      return;
    }
  }

  if (pathname === "/api/messages" && req.method === "DELETE") {
    messages.length = 0;
    sendEvent("reset", { ok: true });
    json(res, 200, { ok: true });
    return;
  }

  const safePath = pathname === "/" ? "/index.html" : pathname;
  const filePath = path.join(PUBLIC_DIR, safePath);

  if (!filePath.startsWith(PUBLIC_DIR)) {
    notFound(res);
    return;
  }

  serveStaticFile(filePath, res);
});

server.listen(PORT, () => {
  console.log(`IM demo is running at http://localhost:${PORT}`);
});
