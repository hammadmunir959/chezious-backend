/**
 * CheziousBot Main Application - Lazy Session Creation
 * Sessions are only created when user sends their first message
 */

// ===== Initialization =====

document.addEventListener('DOMContentLoaded', async () => {
    await initializeApp();
});

async function initializeApp() {
    // Check for existing user
    const userId = localStorage.getItem('user_id');
    const userName = localStorage.getItem('user_name');
    const userCity = localStorage.getItem('user_city');

    if (userId && userName) {
        // Hide modal for existing users
        const modal = document.getElementById('userModal');
        if (modal) {
            modal.classList.add('hidden');
        }

        appState.setState({
            user: { id: userId, name: userName, city: userCity }
        });
        updateUserNameDisplay(userName);
        await startApp();
    } else {
        showUserModal();
    }

    // Setup event listeners
    setupEventListeners();

    // Start health monitoring
    startHealthMonitoring();
}

function setupEventListeners() {
    // Enter key to send message
    const messageInput = document.getElementById('messageInput');
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });

    // Save user name on Enter
    document.getElementById('userName').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            saveUserName();
        }
    });
}

// ===== User Management =====

function showUserModal() {
    const modal = document.getElementById('userModal');
    modal.classList.remove('hidden');
    document.getElementById('userName').focus();
}

function hideUserModal() {
    const modal = document.getElementById('userModal');
    modal.classList.add('hidden');
}

async function saveUserName() {
    const nameInput = document.getElementById('userName');
    const citySelect = document.getElementById('userCity');
    const name = nameInput.value.trim();
    const city = citySelect ? citySelect.value : null;

    if (!name) {
        alert('Please enter your name');
        return;
    }

    const userId = name.toLowerCase().replace(/\s+/g, '_');

    // Create user in backend
    try {
        await api.createUser(userId, name, city);
    } catch (e) {
        console.error('Failed to create user in backend', e);
        alert(e.message);
        return;
    }

    localStorage.setItem('user_id', userId);
    localStorage.setItem('user_name', name);
    if (city) {
        localStorage.setItem('user_city', city);
    }

    appState.setState({
        user: { id: userId, name: name, city: city }
    });

    updateUserNameDisplay(name);
    hideUserModal();

    await startApp();
}

document.getElementById('saveUserName').onclick = saveUserName;

// ===== App Startup =====

async function startApp() {
    const state = appState.getState();

    try {
        // 1. Try to load cached sessions for instant sidebar
        const cachedSessions = localStorage.getItem(`sessions_${state.user.id}`);
        if (cachedSessions) {
            try {
                const parsedSessions = JSON.parse(cachedSessions);
                appState.setState({ sessions: parsedSessions });
                renderSessionsList(parsedSessions, state.currentSession.id);
            } catch (e) {
                console.error('Failed to parse cached sessions');
            }
        }

        // 2. Fetch fresh sessions from API
        const sessionsData = await api.getUserSessions(state.user.id);
        const validSessions = (sessionsData.sessions || []).filter(s => s.message_count > 0);

        // 3. Update state and cache
        appState.setState({ sessions: validSessions });
        localStorage.setItem(`sessions_${state.user.id}`, JSON.stringify(validSessions));

        // 4. Try to load last session if it exists and has messages
        const lastSessionId = localStorage.getItem('last_session_id');

        if (lastSessionId && validSessions.some(s => s.id === lastSessionId)) {
            await loadSession(lastSessionId);
        } else {
            // No active session - show welcome without creating session
            clearMessages();
            addWelcomeMessage(state.user.name);
            scrollToBottom();

            // Set session state to null (will be created on first message)
            appState.setState({
                currentSession: {
                    id: null,
                    created_at: null,
                    message_count: 0,
                    status: 'pending'
                }
            });
            updateSessionInfo(null);
        }

        // 5. Re-render with fresh data
        renderSessionsList(validSessions, state.currentSession.id);

    } catch (error) {
        console.error('Failed to start app:', error);
        // Show welcome message even on error
        clearMessages();
        addWelcomeMessage(state.user.name);
        scrollToBottom();
    }
}

// ===== Session Management =====

async function createNewChat() {
    const state = appState.getState();

    // Just clear the UI and reset state - don't create session yet
    clearMessages();
    addWelcomeMessage(state.user.name);
    scrollToBottom();

    appState.setState({
        currentSession: {
            id: null,
            created_at: null,
            message_count: 0,
            status: 'pending'
        },
        messages: [],
    });

    localStorage.removeItem('last_session_id');
    updateSessionInfo(null);

    // Reload sessions list
    try {
        const sessionsData = await api.getUserSessions(state.user.id);
        const validSessions = (sessionsData.sessions || []).filter(s => s.message_count > 0);

        appState.setState({ sessions: validSessions });
        localStorage.setItem(`sessions_${state.user.id}`, JSON.stringify(validSessions));

        renderSessionsList(validSessions, null);
    } catch (error) {
        console.error('Failed to reload sessions:', error);
    }
}

async function loadSession(sessionId) {
    try {
        const messagesData = await api.getSessionMessages(sessionId);

        // Try to find session in state first to avoid API call
        let session = appState.getState().sessions.find(s => s.id === sessionId);
        if (!session) {
            session = await api.getSession(sessionId);
        }

        appState.setState({
            currentSession: session,
            messages: messagesData.messages || [],
        });

        localStorage.setItem('last_session_id', sessionId);

        // Clear and render messages
        clearMessages();

        if (messagesData.messages && messagesData.messages.length > 0) {
            renderMessages(messagesData.messages);
        } else {
            addWelcomeMessage(appState.getState().user.name);
        }

        scrollToBottom();

        // Update UI
        updateSessionInfo(sessionId);

        // Update sessions list
        const state = appState.getState();
        renderSessionsList(state.sessions, sessionId);

    } catch (error) {
        console.error('Failed to load session:', error);
        alert('Failed to load session. Please try again.');
    }
}

// ===== Chat Functionality =====

async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (!message) return;

    const state = appState.getState();

    if (state.ui.isSending) {
        return; // Prevent multiple sends
    }

    // Disable input
    appState.setState({ ui: { isSending: true } });
    messageInput.disabled = true;
    document.getElementById('sendBtn').disabled = true;

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Add user message to UI
    const messagesArea = document.getElementById('messagesArea');
    const userMessage = renderUserMessage(message);
    messagesArea.appendChild(userMessage);
    scrollToBottom();

    try {
        // Generate session ID client-side if it doesn't exist
        let sessionId = state.currentSession.id;

        if (!sessionId) {
            console.log('Generating new session ID for first message...');
            // Generate UUID v4 client-side
            sessionId = crypto.randomUUID();

            appState.setState({
                currentSession: {
                    id: sessionId,
                    created_at: new Date().toISOString(),
                    message_count: 0,
                    status: 'active'
                }
            });

            localStorage.setItem('last_session_id', sessionId);
            updateSessionInfo(sessionId);
        }

        // Show typing indicator
        const typingIndicator = renderTypingIndicator();
        messagesArea.appendChild(typingIndicator);
        scrollToBottom();

        // Create bot message bubble for streaming
        removeTypingIndicator();
        const botMessage = renderBotMessage('');
        messagesArea.appendChild(botMessage);
        const botBubble = botMessage.querySelector('.message-bubble');

        let fullResponse = '';

        // Stream the response token by token - use sessionId variable
        for await (const token of api.streamChat(sessionId, message, state.user.id)) {
            fullResponse += token;
            // Render markdown in real-time as tokens arrive
            if (typeof renderMarkdown === 'function') {
                botBubble.innerHTML = renderMarkdown(fullResponse);
            } else {
                botBubble.textContent = fullResponse;
            }
            scrollToBottom();
        }

        // Update message count
        appState.setState({
            currentSession: {
                message_count: state.currentSession.message_count + 2
            }
        });

        // Reload sessions list to show the new session
        const sessionsData = await api.getUserSessions(state.user.id);
        const validSessions = (sessionsData.sessions || []).filter(s => s.message_count > 0);

        appState.setState({ sessions: validSessions });
        localStorage.setItem(`sessions_${state.user.id}`, JSON.stringify(validSessions));

        renderSessionsList(validSessions, state.currentSession.id);

    } catch (error) {
        console.error('Failed to send message:', error);
        removeTypingIndicator();

        const errorMessage = renderBotMessage(
            '❌ Oops! Something went wrong. Let\'s try that again! 🍕'
        );
        messagesArea.appendChild(errorMessage);
        scrollToBottom();
    } finally {
        // Re-enable input
        appState.setState({ ui: { isSending: false } });
        messageInput.disabled = false;
        document.getElementById('sendBtn').disabled = false;
        messageInput.focus();
    }
}

// ===== Sidebar =====

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');

    const state = appState.getState();
    appState.setState({
        ui: { sidebarOpen: !state.ui.sidebarOpen }
    });
}

// ===== Settings =====

function openSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.remove('hidden');

    const state = appState.getState();
    document.getElementById('settingsUserName').value = state.user.name || '';

    // Set city dropdown value
    const citySelect = document.getElementById('settingsUserCity');
    if (citySelect && state.user.city) {
        citySelect.value = state.user.city;
    }
}

function closeSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.add('hidden');
}

async function updateUserProfile() {
    const newName = document.getElementById('settingsUserName').value.trim();
    const citySelect = document.getElementById('settingsUserCity');
    const newCity = citySelect ? citySelect.value : null;

    if (!newName) {
        alert('Please enter a name');
        return;
    }

    const state = appState.getState();
    const userId = state.user.id; // Keep original user_id

    // Update backend via PUT
    try {
        await api.updateUser(userId, newName, newCity);
    } catch (e) {
        console.error('Failed to update user in backend', e);
        alert(e.message);
        return;
    }

    localStorage.setItem('user_name', newName);
    if (newCity) {
        localStorage.setItem('user_city', newCity);
    }

    appState.setState({
        user: { id: userId, name: newName, city: newCity }
    });

    updateUserNameDisplay(newName);
    closeSettings();

    alert('Profile updated successfully!');
}


async function clearAllHistory() {
    if (!confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
        return;
    }

    const state = appState.getState();

    try {
        // Delete all sessions
        for (const session of state.sessions) {
            await api.deleteSession(session.id);
        }

        localStorage.removeItem('last_session_id');

        appState.setState({
            sessions: [],
            messages: [],
        });
        localStorage.removeItem(`sessions_${state.user.id}`);

        closeSettings();
        await createNewChat();

    } catch (error) {
        console.error('Failed to clear history:', error);
        alert('Failed to clear history. Please try again.');
    }
}

// ===== Health Monitoring =====

async function checkHealth() {
    try {
        const health = await api.checkHealth();
        const isConnected = health.status === 'healthy';

        appState.setState({
            ui: { isConnected }
        });

        updateConnectionStatus(isConnected);

        return isConnected;
    } catch (error) {
        appState.setState({
            ui: { isConnected: false }
        });
        updateConnectionStatus(false);
        return false;
    }
}

function startHealthMonitoring() {
    // Initial check
    checkHealth();

    // Check every 30 seconds
    setInterval(checkHealth, 30000);
}

// ===== Responsive Handling =====

window.addEventListener('resize', () => {
    const state = appState.getState();

    if (window.innerWidth > 1024) {
        document.getElementById('sidebar').classList.remove('collapsed');
        appState.setState({ ui: { sidebarOpen: true } });
    } else if (!state.ui.sidebarOpen) {
        document.getElementById('sidebar').classList.add('collapsed');
    }
});

// ===== Delete Session =====

async function deleteSession(sessionId) {
    if (!confirm('Delete this conversation? This cannot be undone.')) {
        return;
    }

    const state = appState.getState();

    try {
        // Delete the session
        await api.deleteSession(sessionId);

        // If it's the current session, create a new one
        if (state.currentSession.id === sessionId) {
            await createNewChat();
        }

        // Reload sessions list
        const sessionsData = await api.getUserSessions(state.user.id);
        const validSessions = (sessionsData.sessions || []).filter(s => s.message_count > 0);

        appState.setState({ sessions: validSessions });
        localStorage.setItem(`sessions_${state.user.id}`, JSON.stringify(validSessions));

        renderSessionsList(validSessions, state.currentSession.id);

    } catch (error) {
        console.error('Failed to delete session:', error);
        alert('Failed to delete session. Please try again.');
    }
}
