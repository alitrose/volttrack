// VoltTrack Authentication & Route Protection

function requireRole(allowedRoles = []) {
    const user = getUser();
    const token = getToken();

    if (!token || !user) {
        window.location.href = "/";
        return null;
    }

    if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
        showToast(`Access restricted. Redirecting to your assigned dashboard...`, "warning");
        setTimeout(() => {
            redirectToDashboard(user.role);
        }, 1000);
        return null;
    }

    // Populate user profile info in navbar if elements exist
    const nameEl = document.getElementById("nav-user-name");
    const roleEl = document.getElementById("nav-user-role");
    if (nameEl) nameEl.textContent = user.display_name || user.username;
    if (roleEl) roleEl.textContent = user.role.replace("_", " ");

    return user;
}

function redirectToDashboard(role) {
    switch (role) {
        case "ADMIN":
            window.location.href = "/admin";
            break;
        case "CUSTOMER":
            window.location.href = "/customer";
            break;
        case "TECHNICIAN":
            window.location.href = "/technician";
            break;
        case "BILLING_OFFICER":
            window.location.href = "/billing";
            break;
        default:
            window.location.href = "/";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const logoutBtn = document.getElementById("btn-logout");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", (e) => {
            e.preventDefault();
            clearSession();
        });
    }
});
