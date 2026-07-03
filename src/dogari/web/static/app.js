const statusCards = document.getElementById("status-cards");
const usersTableBody = document.getElementById("users-table-body");
const logsTableBody = document.getElementById("logs-table-body");
const recognizeBtn = document.getElementById("recognize-btn");
const recognizeResult = document.getElementById("recognize-result");
const addUserForm = document.getElementById("add-user-form");
const addUserResult = document.getElementById("add-user-result");

function formatDate(value) {
    return value ? value.replace("T", " ") : "-";
}

async function refreshStatus() {
    const response = await fetch("/api/status");
    const data = await response.json();
    statusCards.innerHTML = `
        <div class="card">Utilisateurs<strong>${data.users_count}</strong></div>
        <div class="card">Actifs<strong>${data.active_users_count}</strong></div>
        <div class="card">Accès enregistrés<strong>${data.recent_access_count}</strong></div>
        <div class="card">Mode porte<strong>${data.door_mode}</strong></div>
        <div class="card">Caméra<strong>${data.camera_source}</strong></div>
    `;
}

async function refreshUsers() {
    const response = await fetch("/api/users");
    const users = await response.json();
    usersTableBody.innerHTML = users
        .map(
            (user) => `
        <tr>
            <td>${user.full_name}</td>
            <td>${user.role ?? "-"}</td>
            <td>${user.status}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>
                <button data-action="deactivate" data-id="${user.id}">Désactiver</button>
                <button data-action="delete" data-id="${user.id}">Supprimer</button>
            </td>
        </tr>`
        )
        .join("");
}

async function refreshLogs() {
    const response = await fetch("/api/access/logs?limit=25");
    const logs = await response.json();
    logsTableBody.innerHTML = logs
        .map(
            (log) => `
        <tr>
            <td>${formatDate(log.created_at)}</td>
            <td>${log.full_name ?? "Inconnu"}</td>
            <td class="status-${log.status}">${log.status}</td>
            <td>${log.similarity_score !== null ? log.similarity_score.toFixed(2) : "-"}</td>
            <td>${log.message ?? ""}</td>
        </tr>`
        )
        .join("");
}

async function refreshAll() {
    await Promise.all([refreshStatus(), refreshUsers(), refreshLogs()]);
}

recognizeBtn.addEventListener("click", async () => {
    recognizeBtn.disabled = true;
    recognizeResult.textContent = "Reconnaissance en cours...";
    try {
        const response = await fetch("/api/access/recognize", { method: "POST" });
        const data = await response.json();
        if (!response.ok) {
            recognizeResult.textContent = `Erreur : ${data.detail ?? "inconnue"}`;
        } else {
            recognizeResult.innerHTML = `<span class="status-${data.access_status}">${data.access_status.toUpperCase()}</span> — ${data.message}`;
        }
    } catch (err) {
        recognizeResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        recognizeBtn.disabled = false;
        await refreshAll();
    }
});

addUserForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    addUserResult.textContent = "Ajout en cours...";
    const formData = new FormData(addUserForm);
    try {
        const response = await fetch("/api/users", { method: "POST", body: formData });
        const data = await response.json();
        if (!response.ok) {
            addUserResult.textContent = `Erreur : ${data.detail ?? "inconnue"}`;
        } else {
            addUserResult.textContent = `Utilisateur "${data.full_name}" ajouté avec succès.`;
            addUserForm.reset();
        }
    } catch (err) {
        addUserResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshAll();
    }
});

usersTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const { action, id } = button.dataset;
    if (action === "delete" && !confirm("Supprimer définitivement cet utilisateur ?")) return;

    const url = action === "deactivate" ? `/api/users/${id}/deactivate` : `/api/users/${id}`;
    const method = action === "deactivate" ? "PATCH" : "DELETE";
    await fetch(url, { method });
    await refreshUsers();
});

refreshAll();
