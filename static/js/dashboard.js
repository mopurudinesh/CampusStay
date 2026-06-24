// CampusStay Global Dashboard Controller

document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupChatbot();
    setupLogout();
});

// Toast notification helper
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    
    const toast = document.createElement("div");
    const isWarning = type === "warning";
    const textClass = isWarning ? "text-dark" : "text-white";
    const closeBtnClass = isWarning ? "btn-close" : "btn-close btn-close-white";
    
    toast.className = `toast align-items-center ${textClass} bg-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : 'success'} border-0 show fade-in m-2`;
    toast.role = "alert";
    toast.style.minWidth = "280px";
    
    const icon = type === 'error' ? 'fa-circle-exclamation' : type === 'warning' ? 'fa-triangle-exclamation' : 'fa-circle-check';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fa-solid ${icon} me-2"></i> ${message}
            </div>
            <button type="button" class="${closeBtnClass} me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 500);
    }, 4500);
}

// Global Auth Header retrieval
function getAuthHeaders() {
    const token = localStorage.getItem("token");
    return {
        "Content-Type": "application/json",
        "Authorization": token ? `Bearer ${token}` : ""
    };
}

// Initialize Application UI State
function initApp() {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const username = localStorage.getItem("username");
    
    const navUserInfo = document.getElementById("nav-user-info");
    const navUsername = document.getElementById("nav-username");
    const navRole = document.getElementById("nav-role");
    const logoutBtn = document.getElementById("logout-btn");
    const loginNavBtn = document.getElementById("login-nav-btn");
    
    const sidebarPanel = document.getElementById("sidebar-panel");
    const mainContainer = document.getElementById("main-container");
    const studentLinks = document.getElementById("student-links");
    const adminLinks = document.getElementById("admin-links");
    
    if (token) {
        if (navUserInfo) navUserInfo.classList.remove("d-none");
        if (navUsername) navUsername.textContent = username;
        if (navRole) {
            navRole.textContent = role;
            navRole.className = `badge bg-${role === 'ADMIN' ? 'danger' : 'primary'} text-xs`;
        }
        
        if (logoutBtn) logoutBtn.classList.remove("d-none");
        if (loginNavBtn) loginNavBtn.classList.add("d-none");
        
        if (sidebarPanel) {
            sidebarPanel.classList.remove("d-none");
            if (mainContainer) mainContainer.className = "col-12 col-lg-10 p-4 main-content";
        }
        
        if (role === "STUDENT") {
            if (studentLinks) studentLinks.classList.remove("d-none");
            if (adminLinks) adminLinks.classList.add("d-none");
        } else if (role === "ADMIN") {
            if (adminLinks) adminLinks.classList.remove("d-none");
            if (studentLinks) studentLinks.classList.add("d-none");
        }
    } else {
        if (navUserInfo) navUserInfo.classList.add("d-none");
        if (logoutBtn) logoutBtn.classList.add("d-none");
        if (loginNavBtn) loginNavBtn.classList.remove("d-none");
        
        if (sidebarPanel) {
            sidebarPanel.classList.add("d-none");
            if (mainContainer) mainContainer.className = "col-12 p-4 main-content";
        }
    }
}

// Setup User Logout Action
function setupLogout() {
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            localStorage.clear();
            showToast("Successfully logged out.", "success");
            setTimeout(() => {
                window.location.href = "/login/";
            }, 1000);
        });
    }
}

// Floating Chatbot UI Handlers
function setupChatbot() {
    const toggleBtn = document.getElementById("chatbot-toggle-btn");
    const chatbotPanel = document.getElementById("chatbot-panel");
    const closeBtn = document.getElementById("chatbot-close-btn");
    
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send-btn");
    const chatMessages = document.getElementById("chat-messages");
    
    if (!toggleBtn || !chatbotPanel) return;
    
    toggleBtn.addEventListener("click", () => {
        chatbotPanel.classList.toggle("active");
    });
    
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            chatbotPanel.classList.remove("active");
        });
    }
    
    function appendMessage(text, role) {
        const messageDiv = document.createElement("div");
        messageDiv.className = `chat-message ${role}`;
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;
        
        appendMessage(text, "user");
        chatInput.value = "";
        
        // Show bot typing or processing state
        const typingDiv = document.createElement("div");
        typingDiv.className = "chat-message bot text-muted";
        typingDiv.textContent = "...";
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        try {
            const token = localStorage.getItem("token");
            if (!token) {
                typingDiv.remove();
                appendMessage("Please log in to converse with the hostel chatbot.", "bot");
                return;
            }
            
            const response = await fetch("/api/chatbot/", {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ message: text })
            });
            
            typingDiv.remove();
            if (response.ok) {
                const resData = await response.json();
                appendMessage(resData.response, "bot");
            } else {
                appendMessage("Unable to connect to the bot assistant right now.", "bot");
            }
        } catch (error) {
            typingDiv.remove();
            appendMessage("An error occurred during communication.", "bot");
        }
    }
    
    if (sendBtn) {
        sendBtn.addEventListener("click", sendMessage);
    }
    
    if (chatInput) {
        chatInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }
}
