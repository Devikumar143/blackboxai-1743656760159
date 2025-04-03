document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const messagesContainer = document.getElementById('messages-container');
    const messageInput = document.getElementById('message-input');
    const sendMessageBtn = document.getElementById('send-message-btn');
    const createChannelBtn = document.getElementById('create-channel-btn');
    const channelName = document.getElementById('channel-name');

    let currentSuggestions = [];
    let selectedSuggestionIndex = -1;

    // Scroll to bottom of messages
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Handle sending messages
    if (sendMessageBtn && messageInput) {
        sendMessageBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    // Handle channel creation
    if (createChannelBtn) {
        createChannelBtn.addEventListener('click', () => {
            const name = prompt('Enter channel name:');
            if (name) {
                fetch('/api/channels', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    },
                    body: JSON.stringify({ name })
                })
                .then(response => response.json())
                .then(channel => {
                    window.location.href = `/channels/${channel.id}`;
                });
            }
        });
    }

    // Mention autocomplete
    function checkForMention() {
        const input = messageInput.value;
        const atPos = input.lastIndexOf('@');
        
        if (atPos >= 0 && (atPos === 0 || input[atPos-1] === ' ')) {
            const partial = input.substring(atPos + 1);
            fetch(`/api/users/search?q=${partial}`)
                .then(res => res.json())
                .then(users => {
                    const suggestions = document.getElementById('mention-suggestions');
                    suggestions.innerHTML = '';
                    suggestions.classList.remove('hidden');
                    currentSuggestions = users;
                    selectedSuggestionIndex = -1;
                    
                    users.forEach((user, index) => {
                        const div = document.createElement('div');
                        div.className = `p-2 hover:bg-gray-100 cursor-pointer ${index === selectedSuggestionIndex ? 'bg-blue-100' : ''}`;
                        div.textContent = `@${user.username}`;
                        div.onclick = () => selectSuggestion(index);
                        suggestions.appendChild(div);
                    });
                });
        } else {
            document.getElementById('mention-suggestions').classList.add('hidden');
            currentSuggestions = [];
        }
    }

    function selectSuggestion(index) {
        if (index >= 0 && index < currentSuggestions.length) {
            const input = messageInput.value;
            const atPos = input.lastIndexOf('@');
            messageInput.value = input.substring(0, atPos) + `@${currentSuggestions[index].username} `;
            document.getElementById('mention-suggestions').classList.add('hidden');
            messageInput.focus();
            currentSuggestions = [];
        }
    }

    // Handle keyboard navigation
    messageInput.addEventListener('keydown', (e) => {
        const suggestions = document.getElementById('mention-suggestions');
        if (!suggestions.classList.contains('hidden') && currentSuggestions.length > 0) {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedSuggestionIndex = Math.min(selectedSuggestionIndex + 1, currentSuggestions.length - 1);
                updateSuggestionsHighlight();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedSuggestionIndex = Math.max(selectedSuggestionIndex - 1, -1);
                updateSuggestionsHighlight();
            } else if (e.key === 'Enter' && selectedSuggestionIndex >= 0) {
                e.preventDefault();
                selectSuggestion(selectedSuggestionIndex);
            } else if (e.key === 'Escape') {
                suggestions.classList.add('hidden');
            }
        }
    });

    function updateSuggestionsHighlight() {
        const suggestions = document.getElementById('mention-suggestions');
        const items = suggestions.querySelectorAll('div');
        items.forEach((item, index) => {
            item.classList.toggle('bg-blue-100', index === selectedSuggestionIndex);
        });
    }

    // Socket.io event listeners
    socket.on('new_mention', (data) => {
        if (Notification.permission === 'granted') {
            new Notification('You were mentioned', {
                body: data.content.substring(0, 100)
            });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification('You were mentioned', {
                        body: data.content.substring(0, 100)
                    });
                }
            });
        }
    });

    socket.on('reaction_added', (data) => {
        const reactionBtns = document.querySelectorAll(`[data-message-id="${data.message_id}"]`);
        reactionBtns.forEach(btn => {
            if (btn.dataset.emoji === data.emoji) {
                btn.textContent = `${data.emoji} ${data.count}`;
            }
        });
    });

    function sendMessage() {
        const content = messageInput.value.trim();
        if (content && channelName.dataset.channelId) {
            socket.emit('send_message', {
                content,
                channel_id: channelName.dataset.channelId,
                user_id: localStorage.getItem('user_id')
            });
            messageInput.value = '';
        }
    }
});