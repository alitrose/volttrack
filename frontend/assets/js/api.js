// VoltTrack API & Utility Client

const API_BASE = "/api";

function getToken() {
    return localStorage.getItem("volttrack_token");
}

function getUser() {
    const raw = localStorage.getItem("volttrack_user");
    return raw ? JSON.parse(raw) : null;
}

function setSession(token, user) {
    localStorage.setItem("volttrack_token", token);
    localStorage.setItem("volttrack_user", JSON.stringify(user));
}

function clearSession() {
    localStorage.removeItem("volttrack_token");
    localStorage.removeItem("volttrack_user");
    window.location.href = "/";
}

async function apiRequest(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = getToken();

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    options.headers = headers;

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);

        if (response.status === 401) {
            showToast("Session expired. Please log in again.", "error");
            setTimeout(() => {
                clearSession();
            }, 1200);
            throw new Error("Unauthorized");
        }

        const data = await response.json();
        if (!response.ok || data.success === false) {
            throw new Error(data.error || "Request failed");
        }

        return data;
    } catch (err) {
        console.error(`API Error [${endpoint}]:`, err);
        throw err;
    }
}

const api = {
    get: (endpoint) => apiRequest(endpoint, { method: "GET" }),
    post: (endpoint, body) => apiRequest(endpoint, { method: "POST", body: JSON.stringify(body) }),
    patch: (endpoint, body) => apiRequest(endpoint, { method: "PATCH", body: JSON.stringify(body) }),
    put: (endpoint, body) => apiRequest(endpoint, { method: "PUT", body: JSON.stringify(body) }),
    delete: (endpoint) => apiRequest(endpoint, { method: "DELETE" }),
};

// Toast Notifications
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = "toast";

    let bg = "bg-slate-800 text-slate-100 border border-slate-700";
    let icon = "ℹ️";

    if (type === "success") {
        bg = "bg-emerald-900 text-emerald-100 border border-emerald-700";
        icon = "✅";
    } else if (type === "error") {
        bg = "bg-rose-900 text-rose-100 border border-rose-700";
        icon = "⚠️";
    } else if (type === "warning") {
        bg = "bg-amber-900 text-amber-100 border border-amber-700";
        icon = "⚡";
    }

    toast.className = `toast ${bg}`;
    toast.innerHTML = `<span class="text-base">${icon}</span><span class="flex-1 font-medium">${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Formatters
function formatCurrency(val) {
    const num = parseFloat(val) || 0;
    return "₹" + num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function formatDateTime(dateStr) {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
