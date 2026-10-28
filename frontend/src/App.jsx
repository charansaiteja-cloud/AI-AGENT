import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import { api, getErrorMessage } from "./api";
import ChatHeader from "./components/ChatHeader";
import Composer from "./components/Composer";
import ConfirmDialog from "./components/ConfirmDialog";
import CustomerModal from "./components/CustomerModal";
import Icon from "./components/Icon";
import MemoryPanel from "./components/MemoryPanel";
import MessageList from "./components/MessageList";
import Sidebar from "./components/Sidebar";
import Toast from "./components/Toast";
import Welcome from "./components/Welcome";

const DEMO_FIRST_MESSAGE =
  "My name is Sarah. I work at Acme Corp. I use Ubuntu 24.04 on a Dell XPS 15, and my Wi-Fi keeps disconnecting.";
const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;

function readStoredCustomerId() {
  try {
    const value = Number(window.localStorage.getItem("supportai.customer"));
    return Number.isInteger(value) && value > 0 ? value : null;
  } catch {
    return null;
  }
}

function emptyMemoryState() {
  return { loading: false, available: true, error: null };
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [activeCustomerId, setActiveCustomerId] = useState(readStoredCustomerId);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [memories, setMemories] = useState([]);
  const [memoryState, setMemoryState] = useState(emptyMemoryState);
  const [loading, setLoading] = useState({
    customers: true,
    conversations: false,
    messages: false,
  });
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [composerText, setComposerText] = useState("");
  const [composerFocus, setComposerFocus] = useState(0);
  const [draftAttachments, setDraftAttachments] = useState([]);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [customerModal, setCustomerModal] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [clearingMemory, setClearingMemory] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoScenario, setDemoScenario] = useState(null);
  const [lastTurn, setLastTurn] = useState(null);

  const conversationRequest = useRef(0);
  const messageRequest = useRef(0);
  const memoryRequest = useRef(0);
  const skipMessageLoad = useRef(false);

  const activeCustomer = useMemo(
    () => customers.find((customer) => customer.id === activeCustomerId) || null,
    [customers, activeCustomerId],
  );
  const activeConversation = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.id === activeConversationId,
      ) || null,
    [conversations, activeConversationId],
  );

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api.health());
    } catch {
      setHealth({
        status: "degraded",
        ollama: "unavailable",
        hindsight: "unavailable",
        model: "qwen3:8b",
      });
    }
  }, []);

  const loadCustomers = useCallback(async ({ selectId } = {}) => {
    setLoading((previous) => ({ ...previous, customers: true }));
    try {
      const data = await api.customers.list();
      setCustomers(data);
      setActiveCustomerId((previous) => {
        const wanted = selectId !== undefined ? selectId : previous;
        if (wanted != null && data.some((customer) => customer.id === wanted)) {
          return wanted;
        }
        return data[0]?.id ?? null;
      });
      return data;
    } catch (loadError) {
      setError(getErrorMessage(loadError));
      return [];
    } finally {
      setLoading((previous) => ({ ...previous, customers: false }));
    }
  }, []);

  const loadConversations = useCallback(async (customerId, { selectId } = {}) => {
    if (!customerId) {
      conversationRequest.current += 1;
      setConversations([]);
      setActiveConversationId(null);
      return [];
    }

    const requestId = ++conversationRequest.current;
    setLoading((previous) => ({ ...previous, conversations: true }));

    try {
      const data = await api.customers.conversations(customerId);
      if (requestId !== conversationRequest.current) {
        return data;
      }

      setConversations(data);
      setActiveConversationId((previous) => {
        const wanted = selectId !== undefined ? selectId : previous;
        if (wanted != null && data.some((item) => item.id === wanted)) {
          return wanted;
        }
        return data[0]?.id ?? null;
      });
      return data;
    } catch (loadError) {
      if (requestId === conversationRequest.current) {
        setConversations([]);
        setError(getErrorMessage(loadError));
      }
      return [];
    } finally {
      if (requestId === conversationRequest.current) {
        setLoading((previous) => ({ ...previous, conversations: false }));
      }
    }
  }, []);

  const loadMessages = useCallback(async (conversationId) => {
    if (!conversationId) {
      messageRequest.current += 1;
      setMessages([]);
      setLoading((previous) => ({ ...previous, messages: false }));
      return;
    }

    const requestId = ++messageRequest.current;
    setLoading((previous) => ({ ...previous, messages: true }));

    try {
      const data = await api.conversations.messages(conversationId);
      if (requestId === messageRequest.current) {
        setMessages(data.messages || []);
      }
    } catch (loadError) {
      if (requestId === messageRequest.current) {
        setMessages([]);
        setError(getErrorMessage(loadError));
      }
    } finally {
      if (requestId === messageRequest.current) {
        setLoading((previous) => ({ ...previous, messages: false }));
      }
    }
  }, []);

  const loadMemories = useCallback(async (customerId) => {
    if (!customerId) {
      memoryRequest.current += 1;
      setMemories([]);
      setMemoryState(emptyMemoryState());
      return;
    }

    const requestId = ++memoryRequest.current;
    setMemoryState((previous) => ({ ...previous, loading: true, error: null }));

    try {
      const data = await api.customers.memories(customerId);
      if (requestId !== memoryRequest.current) {
        return;
      }
      setMemories(data.memories || []);
      setMemoryState({
        loading: false,
        available: Boolean(data.available),
        error: data.error || null,
      });
    } catch (loadError) {
      if (requestId === memoryRequest.current) {
        setMemories([]);
        setMemoryState({
          loading: false,
          available: false,
          error: getErrorMessage(loadError),
        });
      }
    }
  }, []);

  useEffect(() => {
    loadCustomers();
    api.demo
      .scenario()
      .then(setDemoScenario)
      .catch(() => setDemoScenario(null));
  }, [loadCustomers]);

  useEffect(() => {
    refreshHealth();
    const timer = window.setInterval(refreshHealth, 30_000);
    return () => window.clearInterval(timer);
  }, [refreshHealth]);

  useEffect(() => {
    if (!activeCustomerId) {
      setConversations([]);
      setActiveConversationId(null);
      setMemories([]);
      setMemoryState(emptyMemoryState());
      return;
    }

    try {
      window.localStorage.setItem("supportai.customer", String(activeCustomerId));
    } catch {
      // Local persistence is a convenience, not a requirement.
    }

    setActiveConversationId(null);
    setLastTurn(null);
    setDraftAttachments([]);
    setError("");
    loadConversations(activeCustomerId);
    loadMemories(activeCustomerId);
  }, [activeCustomerId, loadConversations, loadMemories]);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    if (skipMessageLoad.current) {
      skipMessageLoad.current = false;
      setLoading((previous) => ({ ...previous, messages: false }));
      return;
    }
    loadMessages(activeConversationId);
  }, [activeConversationId, loadMessages]);

  const ensureConversation = useCallback(async () => {
    if (activeConversationId) {
      return activeConversationId;
    }
    if (!activeCustomerId) {
      throw new Error("Select a customer before starting a conversation.");
    }

    const created = await api.conversations.create(activeCustomerId, {
      title: "New conversation",
    });
    setConversations((previous) => [
      {
        ...created,
        message_count: 0,
        last_message: null,
        last_message_at: null,
      },
      ...previous.filter((item) => item.id !== created.id),
    ]);
    setActiveConversationId(created.id);
    return created.id;
  }, [activeConversationId, activeCustomerId]);

  const handleAttach = useCallback(
    async (files) => {
      if (!activeCustomerId) {
        setToast({
          type: "error",
          message: "Select a customer before attaching files.",
        });
        return;
      }

      const slots = MAX_ATTACHMENTS - draftAttachments.length;
      if (slots <= 0) {
        setToast({
          type: "error",
          message: `You can attach up to ${MAX_ATTACHMENTS} files per message.`,
        });
        return;
      }

      const selected = files.slice(0, slots);
      if (files.length > slots) {
        setToast({
          type: "error",
          message: `Only ${slots} more attachment${slots === 1 ? "" : "s"} can be added.`,
        });
      }

      const oversized = selected.find((file) => file.size > MAX_ATTACHMENT_BYTES);
      if (oversized) {
        setToast({
          type: "error",
          message: `${oversized.name} is larger than the 10 MB limit.`,
        });
        return;
      }

      setUploading(true);
      try {
        const conversationId = await ensureConversation();
        const uploaded = [];

        for (const file of selected) {
          try {
            const attachment = await api.conversations.upload(conversationId, file);
            uploaded.push(attachment);
          } catch (uploadError) {
            setToast({
              type: "error",
              message: `${file.name}: ${getErrorMessage(uploadError)}`,
            });
          }
        }

        if (uploaded.length) {
          setDraftAttachments((previous) => [...previous, ...uploaded]);
          setToast({
            type: "success",
            message: `${uploaded.length} file${uploaded.length === 1 ? "" : "s"} attached.`,
          });
          loadConversations(activeCustomerId, { selectId: conversationId });
        }
      } catch (uploadError) {
        setToast({ type: "error", message: getErrorMessage(uploadError) });
      } finally {
        setUploading(false);
      }
    },
    [
      activeCustomerId,
      draftAttachments.length,
      ensureConversation,
      loadConversations,
    ],
  );

  const handleRemoveAttachment = useCallback(async (attachment) => {
    try {
      await api.conversations.deleteAttachment(attachment.id);
      setDraftAttachments((previous) =>
        previous.filter((item) => item.id !== attachment.id),
      );
    } catch (removeError) {
      setToast({ type: "error", message: getErrorMessage(removeError) });
    }
  }, []);

  const handleSend = useCallback(async () => {
    if (sending || uploading) {
      return;
    }

    const text = composerText.trim();
    if (!text) {
      return;
    }

    if (!activeCustomerId) {
      setToast({ type: "error", message: "Add a customer before chatting." });
      setCustomerModal({ mode: "create", customer: null });
      return;
    }

    const optimisticId = `temp-${Date.now()}`;
    const optimistic = {
      id: optimisticId,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
      attachments: draftAttachments,
      memory_count: 0,
      model: null,
    };

    setMessages((previous) => [...previous, optimistic]);
    setComposerText("");
    setError("");
    setSending(true);

    try {
      let conversationId = activeConversationId;
      if (!conversationId && draftAttachments.length) {
        conversationId = await ensureConversation();
      }

      const data = await api.chat({
        message: text,
        customer_id: activeCustomerId,
        conversation_id: conversationId,
        attachment_ids: draftAttachments.map((attachment) => attachment.id),
      });

      const now = new Date().toISOString();
      const userMessage = {
        ...optimistic,
        id: data.user_message_id,
        attachments: draftAttachments.map((attachment) => ({
          ...attachment,
          message_id: data.user_message_id,
        })),
      };
      const assistantMessage = {
        id: data.assistant_message_id,
        conversation_id: data.conversation_id,
        role: "assistant",
        content: data.response,
        model: data.model,
        memory_count: (data.memories || []).length,
        created_at: now,
        attachments: [],
      };

      setMessages((previous) => [
        ...previous.filter((message) => message.id !== optimisticId),
        userMessage,
        assistantMessage,
      ]);
      setConversations((previous) => {
        const existing = previous.find(
          (item) => item.id === data.conversation_id,
        );
        return [
          {
            id: data.conversation_id,
            customer_id: activeCustomerId,
            title: data.conversation_title,
            status: existing?.status || "active",
            created_at: existing?.created_at || now,
            updated_at: now,
            message_count: (existing?.message_count || 0) + 2,
            last_message: data.response,
            last_message_at: now,
          },
          ...previous.filter((item) => item.id !== data.conversation_id),
        ];
      });
      setLastTurn({
        conversationId: data.conversation_id,
        memories: data.memories || [],
        memoryUsed: data.memory_used,
        memorySaved: data.memory_saved,
        latencyMs: data.latency_ms,
      });
      setDraftAttachments([]);

      if (activeConversationId !== data.conversation_id) {
        skipMessageLoad.current = true;
        setActiveConversationId(data.conversation_id);
      }

      if (data.memory_saved && data.memory_used) {
        setToast({
          type: "success",
          message: `Reply ready · ${data.memories.length} memories recalled, new context saved`,
        });
      } else if (data.memory_saved) {
        setToast({ type: "success", message: "Reply ready · context saved to memory" });
      } else if (data.memory_used) {
        setToast({
          type: "success",
          message: `Reply ready · ${data.memories.length} memories recalled`,
        });
      } else {
        setToast({ type: "success", message: "Reply ready" });
      }

      // The reply is already on screen. Refresh the sidebar, memory panel, and
      // service status in the background instead of blocking the send state.
      void Promise.all([
        loadConversations(activeCustomerId, {
          selectId: data.conversation_id,
        }),
        loadMemories(activeCustomerId),
        refreshHealth(),
      ]);
    } catch (sendError) {
      setMessages((previous) =>
        previous.filter((message) => message.id !== optimisticId),
      );
      setComposerText(text);
      const message = getErrorMessage(sendError);
      setError(message);
      setToast({ type: "error", message });
    } finally {
      setSending(false);
    }
  }, [
    sending,
    uploading,
    composerText,
    activeCustomerId,
    activeConversationId,
    draftAttachments,
    ensureConversation,
    loadConversations,
    loadMemories,
    refreshHealth,
  ]);

  const handleNewConversation = useCallback(() => {
    setActiveConversationId(null);
    setMessages([]);
    setLastTurn(null);
    setDraftAttachments([]);
    setComposerText("");
    setError("");
    setSidebarOpen(false);
    setComposerFocus((value) => value + 1);
  }, []);

  const handleSelectCustomer = useCallback((customerId) => {
    setActiveCustomerId(customerId);
    setComposerText("");
    setComposerFocus((value) => value + 1);
    setSidebarOpen(false);
  }, []);

  const handleSelectConversation = useCallback((conversationId) => {
    setActiveConversationId(conversationId);
    setLastTurn(null);
    setError("");
    setSidebarOpen(false);
  }, []);

  const handlePrompt = useCallback((text) => {
    setComposerText(text);
    setComposerFocus((value) => value + 1);
  }, []);

  const handleCopy = useCallback(async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setToast({ type: "success", message: "Reply copied to clipboard" });
    } catch {
      setToast({ type: "error", message: "Could not copy this reply." });
    }
  }, []);

  const handleLoadDemo = useCallback(async () => {
    setDemoBusy(true);
    try {
      const demo = await api.demo.seed();
      await loadCustomers({ selectId: demo.id });
      setActiveConversationId(null);
      setMessages([]);
      setLastTurn(null);
      setDraftAttachments([]);
      setComposerText(demoScenario?.first_message || DEMO_FIRST_MESSAGE);
      setComposerFocus((value) => value + 1);
      setSidebarOpen(false);
      setToast({
        type: "success",
        message: "Demo customer ready. Send the introduction to begin.",
      });
    } catch (demoError) {
      setToast({ type: "error", message: getErrorMessage(demoError) });
    } finally {
      setDemoBusy(false);
    }
  }, [demoScenario, loadCustomers]);

  const handleCustomerSubmit = useCallback(
    async (payload) => {
      if (customerModal?.mode === "edit" && activeCustomer) {
        const updated = await api.customers.update(activeCustomer.id, payload);
        await loadCustomers({ selectId: updated.id });
        setCustomerModal(null);
        setToast({ type: "success", message: "Customer updated" });
        return;
      }

      const created = await api.customers.create(payload);
      await loadCustomers({ selectId: created.id });
      setCustomerModal(null);
      setToast({ type: "success", message: "Customer created" });
    },
    [customerModal, activeCustomer, loadCustomers],
  );

  const handleDeleteCustomer = useCallback(() => {
    if (!activeCustomer) {
      return;
    }

    setConfirm({
      title: "Delete this customer?",
      description: `This permanently removes ${activeCustomer.name}, all conversations, attachments, and their Hindsight memory bank. This cannot be undone.`,
      confirmLabel: "Delete customer",
      danger: true,
      action: async () => {
        await api.customers.remove(activeCustomer.id);
        setComposerText("");
        await loadCustomers();
        setToast({ type: "success", message: "Customer deleted" });
      },
    });
  }, [activeCustomer, loadCustomers]);

  const handleClearMemory = useCallback(() => {
    if (!activeCustomer) {
      return;
    }

    setConfirm({
      title: "Clear customer memory?",
      description:
        "This deletes every remembered fact in this customer's Hindsight bank. Conversations and attachments remain. Future replies will start without long-term context.",
      confirmLabel: "Clear memory",
      danger: true,
      action: async () => {
        setClearingMemory(true);
        try {
          await api.customers.clearMemories(activeCustomer.id);
          await loadMemories(activeCustomer.id);
          setLastTurn(null);
          setToast({ type: "success", message: "Customer memory cleared" });
        } finally {
          setClearingMemory(false);
        }
      },
    });
  }, [activeCustomer, loadMemories]);

  const handleConfirm = useCallback(async () => {
    if (!confirm?.action) {
      return;
    }

    setConfirmBusy(true);
    try {
      await confirm.action();
      setConfirm(null);
    } catch (confirmError) {
      setToast({ type: "error", message: getErrorMessage(confirmError) });
    } finally {
      setConfirmBusy(false);
    }
  }, [confirm]);

  useEffect(() => {
    function handleShortcut(event) {
      if (
        (event.metaKey || event.ctrlKey) &&
        event.key.toLowerCase() === "k"
      ) {
        event.preventDefault();
        handleNewConversation();
      }
      if (event.key === "Escape") {
        setSidebarOpen(false);
        setMemoryOpen(false);
      }
    }

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [handleNewConversation]);

  const showWelcome = !loading.messages && !messages.length && !sending;
  const memoryAvailable = health ? health.hindsight === "available" : true;

  return (
    <div className="app-shell">
      <Sidebar
        customers={customers}
        activeCustomerId={activeCustomerId}
        onSelectCustomer={handleSelectCustomer}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onAddCustomer={() =>
          setCustomerModal({ mode: "create", customer: null })
        }
        onLoadDemo={handleLoadDemo}
        onClose={() => setSidebarOpen(false)}
        isOpen={sidebarOpen}
        loading={loading}
        memoryAvailable={memoryAvailable}
        demoBusy={demoBusy}
      />

      <main className="workspace">
        <ChatHeader
          customer={activeCustomer}
          conversation={activeConversation}
          health={health}
          memoryOpen={memoryOpen}
          onToggleSidebar={() => setSidebarOpen(true)}
          onToggleMemory={() => setMemoryOpen((value) => !value)}
          onEditCustomer={() =>
            activeCustomer &&
            setCustomerModal({ mode: "edit", customer: activeCustomer })
          }
          onDeleteCustomer={handleDeleteCustomer}
        />

        {error ? (
          <div className="app-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{error}</span>
            <button
              type="button"
              className="icon-button icon-button-small"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              ×
            </button>
          </div>
        ) : null}

        <div className="chat-content">
          {showWelcome ? (
            <div className="welcome-scroll">
              <Welcome
                customer={activeCustomer}
                scenario={demoScenario}
                health={health}
                onPrompt={handlePrompt}
                onAddCustomer={() =>
                  setCustomerModal({ mode: "create", customer: null })
                }
                onLoadDemo={handleLoadDemo}
                demoBusy={demoBusy}
              />
            </div>
          ) : (
            <MessageList
              messages={messages}
              loading={loading.messages}
              sending={sending}
              customer={activeCustomer}
              lastTurn={lastTurn}
              onCopy={handleCopy}
            />
          )}
        </div>

        <Composer
          value={composerText}
          onChange={setComposerText}
          onSend={handleSend}
          onAttach={handleAttach}
          attachments={draftAttachments}
          onRemoveAttachment={handleRemoveAttachment}
          disabled={!activeCustomer}
          sending={sending}
          uploading={uploading}
          placeholder={
            activeCustomer
              ? `Message ${activeCustomer.name.split(/\s+/)[0]}…`
              : "Add a customer to start chatting"
          }
          focusToken={composerFocus}
        />
      </main>

      <MemoryPanel
        open={memoryOpen}
        onClose={() => setMemoryOpen(false)}
        customer={activeCustomer}
        memories={memories}
        loading={memoryState.loading}
        available={memoryState.available}
        error={memoryState.error}
        onRefresh={() => activeCustomerId && loadMemories(activeCustomerId)}
        onClear={handleClearMemory}
        clearing={clearingMemory}
      />

      {customerModal ? (
        <CustomerModal
          mode={customerModal.mode}
          customer={customerModal.customer}
          onClose={() => setCustomerModal(null)}
          onSubmit={handleCustomerSubmit}
        />
      ) : null}

      {confirm ? (
        <ConfirmDialog
          title={confirm.title}
          description={confirm.description}
          confirmLabel={confirm.confirmLabel}
          danger={confirm.danger}
          busy={confirmBusy || clearingMemory}
          onConfirm={handleConfirm}
          onCancel={() => setConfirm(null)}
        />
      ) : null}

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
