/**
 * CheziousBot API Client
 * Handles all API communication including SSE streaming
 */

class CheziousBotAPI {
    constructor(baseURL = 'http://localhost:8000/api/v1', apiKey = '') {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
    }

    /**
     * Get headers for requests
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        return headers;
    }

    /**
     * Health check
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            return await response.json();
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'error' };
        }
    }

    /**
     * Readiness check
     */
    async checkReady() {
        try {
            const response = await fetch(`${this.baseURL}/health/ready`);
            return await response.json();
        } catch (error) {
            console.error('Readiness check failed:', error);
            return { status: 'not_ready' };
        }
    }

    /**
     * Create a new session
     */
    async createSession(userId, name = null, location = null) {
        try {
            const body = { user_id: userId };
            if (name) body.name = name;
            if (location) body.location = location;

            const response = await fetch(`${this.baseURL}/sessions`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to create session:', error);
            throw error;
        }
    }


    /**
     * Get session details
     */
    async getSession(sessionId) {
        try {
            const response = await fetch(`${this.baseURL}/sessions/${sessionId}`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to get session:', error);
            throw error;
        }
    }

    /**
     * Get all messages for a session
     */
    async getSessionMessages(sessionId) {
        try {
            const response = await fetch(`${this.baseURL}/sessions/${sessionId}/messages`, {
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to get session messages:', error);
            throw error;
        }
    }

    /**
     * Delete a session
     */
    async deleteSession(sessionId) {
        try {
            const response = await fetch(`${this.baseURL}/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return true;
        } catch (error) {
            console.error('Failed to delete session:', error);
            throw error;
        }
    }

    /**
     * Get all sessions for a user
     */
    async getUserSessions(userId) {
        try {
            const response = await fetch(`${this.baseURL}/users/${userId}/sessions`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to get user sessions:', error);
            throw error;
        }
    }


    /**
     * Create or update a user
     */
    async createUser(userId, name, city = null) {
        try {
            const body = { user_id: userId, name: name };
            if (city) body.city = city;

            const response = await fetch(`${this.baseURL}/users/`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body),
            });

            if (!response.ok) {
                const errorData = await response.json();
                if (response.status === 409) {
                    throw new Error('Username already exists. Please choose a different name.');
                }
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to create/update user:', error);
            throw error;
        }
    }

    /**
     * Update an existing user's profile
     */
    async updateUser(userId, name = null, city = null) {
        try {
            const body = {};
            if (name !== null) body.name = name;
            if (city !== null) body.city = city;

            const response = await fetch(`${this.baseURL}/users/${userId}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify(body),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to update user:', error);
            throw error;
        }
    }

    /**
     * Delete a user and all their sessions
     */
    async deleteUser(userId) {
        try {
            const response = await fetch(`${this.baseURL}/users/${userId}`, {
                method: 'DELETE',
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return true;
        } catch (error) {
            console.error('Failed to delete user:', error);
            throw error;
        }
    }

    /**
     * Send a chat message with SSE streaming
     * Returns an async generator that yields tokens as they arrive
     */
    async *streamChat(sessionId, message, userId) {
        try {
            const response = await fetch(`${this.baseURL}/chat`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    session_id: sessionId,
                    message: message,
                    user_id: userId,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    // Process any remaining data in buffer before exiting
                    if (buffer.trim()) {
                        const remainingLines = buffer.split('\n');
                        for (const line of remainingLines) {
                            if (!line.trim()) continue;
                            if (line.startsWith('data:')) {
                                const data = line.substring(5).trim();
                                if (data) {
                                    try {
                                        const parsed = JSON.parse(data);
                                        if (parsed.token) {
                                            yield parsed.token;
                                        }
                                    } catch (e) {
                                        // Ignore parse errors for remaining buffer
                                    }
                                }
                            }
                        }
                    }
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                // Keep the last incomplete line in the buffer
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.trim()) continue;

                    // Parse SSE format
                    if (line.startsWith('event:')) {
                        const eventType = line.substring(6).trim();

                        if (eventType === 'done') {
                            return; // Stream complete
                        }

                        if (eventType === 'error') {
                            // Next line should have the error data
                            continue;
                        }
                    }

                    if (line.startsWith('data:')) {
                        const data = line.substring(5).trim();

                        if (data) {
                            try {
                                const parsed = JSON.parse(data);

                                if (parsed.token) {
                                    yield parsed.token;
                                }

                                if (parsed.error) {
                                    throw new Error(parsed.error);
                                }
                            } catch (e) {
                                if (e.message !== 'Unexpected end of JSON input') {
                                    console.error('Failed to parse SSE data:', e);
                                }
                            }
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Chat streaming failed:', error);
            throw error;
        }
    }
}

// Create global API instance
// NOTE: in a real production app, the API key should not be hardcoded in client-side code
// It should be injected via environment variables during build or handled via a backend proxy
const API_KEY = 'sk_7d2f8a1c9e4b6d0f5a3c2e1b8d7f9a0c';
const api = new CheziousBotAPI('http://localhost:8000/api/v1', API_KEY);
