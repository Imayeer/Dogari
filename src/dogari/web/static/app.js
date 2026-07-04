const statusCards = document.getElementById("status-cards");
const usersTableBody = document.getElementById("users-table-body");
const logsTableBody = document.getElementById("logs-table-body");
const anomaliesList = document.getElementById("anomalies-list");
const recognizeBtn = document.getElementById("recognize-btn");
const recognizeResult = document.getElementById("recognize-result");
const addUserForm = document.getElementById("add-user-form");
const addUserResult = document.getElementById("add-user-result");
const reportForm = document.getElementById("report-form");
const reportResult = document.getElementById("report-result");
const reportCsvLink = document.getElementById("report-csv-link");
const reportTxtLink = document.getElementById("report-txt-link");
const cameraSelect = document.getElementById("camera-select");
const cameraSecondaryOption = document.getElementById("camera-secondary-option");
const searchForm = document.getElementById("search-form");
const searchResult = document.getElementById("search-result");
const searchTableBody = document.getElementById("search-table-body");
const searchCameraSecondaryOption = document.getElementById("search-camera-secondary-option");
const monitoringForm = document.getElementById("monitoring-form");
const monitoringResult = document.getElementById("monitoring-result");
const monitoringTableBody = document.getElementById("monitoring-table-body");
const monitoringCameraSecondaryOption = document.getElementById("monitoring-camera-secondary-option");
const securityEventsList = document.getElementById("security-events-list");

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
        <div class="card">Caméra secondaire<strong>${data.secondary_camera_source ?? "non configurée"}</strong></div>
    `;
    cameraSecondaryOption.disabled = !data.secondary_camera_source;
    searchCameraSecondaryOption.disabled = !data.secondary_camera_source;
    monitoringCameraSecondaryOption.disabled = !data.secondary_camera_source;
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

async function refreshAnomalies() {
    const response = await fetch("/api/access/anomalies");
    const anomalies = await response.json();
    anomaliesList.innerHTML = anomalies.length
        ? anomalies
              .map(
                  (anomaly) => `<li class="anomaly-${anomaly.severity}">${anomaly.message}</li>`
              )
              .join("")
        : "<li class=\"anomaly-none\">Aucune anomalie détectée.</li>";
}

async function refreshSearches() {
    const response = await fetch("/api/search");
    const searches = await response.json();
    searchTableBody.innerHTML = searches
        .map(
            (search) => `
        <tr>
            <td>${search.full_name}</td>
            <td>${search.camera_source}</td>
            <td>${formatDate(search.started_at)}</td>
            <td>${search.sightings_count}</td>
            <td>${search.last_error ? `Erreur : ${search.last_error}` : "En cours"}</td>
            <td><button data-action="stop-search" data-id="${search.search_id}">Arrêter</button></td>
        </tr>`
        )
        .join("");
}

async function refreshMonitors() {
    const response = await fetch("/api/monitoring");
    const monitors = await response.json();
    monitoringTableBody.innerHTML = monitors
        .map(
            (monitor) => `
        <tr>
            <td>${monitor.camera_source}</td>
            <td>${formatDate(monitor.started_at)}</td>
            <td>${monitor.last_error ? `Erreur : ${monitor.last_error}` : "En cours"}</td>
            <td><button data-action="stop-monitor" data-id="${monitor.monitor_id}">Arrêter</button></td>
        </tr>`
        )
        .join("");
}

async function refreshSecurityEvents() {
    const response = await fetch("/api/monitoring/events?limit=25");
    const events = await response.json();
    securityEventsList.innerHTML = events.length
        ? events
              .map(
                  (event) =>
                      `<li class="anomaly-${event.severity}">${formatDate(event.created_at)} — ${event.message}</li>`
              )
              .join("")
        : "<li class=\"anomaly-none\">Aucun événement de sécurité détecté.</li>";
}

async function refreshAll() {
    await Promise.all([
        refreshStatus(),
        refreshUsers(),
        refreshLogs(),
        refreshAnomalies(),
        refreshSearches(),
        refreshMonitors(),
        refreshSecurityEvents(),
    ]);
}

recognizeBtn.addEventListener("click", async () => {
    recognizeBtn.disabled = true;
    recognizeResult.textContent = "Reconnaissance en cours...";
    try {
        const camera = cameraSelect.value;
        const response = await fetch(`/api/access/recognize?camera=${camera}`, { method: "POST" });
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

reportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const days = new FormData(reportForm).get("days") || 7;
    reportCsvLink.href = `/api/reports/export.csv?days=${days}`;
    reportTxtLink.href = `/api/reports/export.txt?days=${days}`;
    reportResult.textContent = "Génération en cours...";
    try {
        const response = await fetch(`/api/reports/summary?days=${days}`);
        const data = await response.json();
        const usersLine = data.unique_users.length ? data.unique_users.join(", ") : "-";
        reportResult.innerHTML = `
            <p><strong>Période :</strong> ${data.period_start} au ${data.period_end}</p>
            <p><strong>Tentatives :</strong> ${data.total_attempts}
               (autorisées : ${data.granted}, refusées : ${data.denied}, erreurs : ${data.error})</p>
            <p><strong>Utilisateurs distincts :</strong> ${usersLine}</p>
            <p><strong>Anomalies :</strong> ${data.anomalies.length}</p>
        `;
    } catch (err) {
        reportResult.textContent = `Erreur réseau : ${err}`;
    }
});

searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(searchForm);
    searchResult.textContent = "Démarrage de la recherche...";
    try {
        const response = await fetch("/api/search/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ full_name: formData.get("full_name"), camera: formData.get("camera") }),
        });
        const data = await response.json();
        searchResult.textContent = response.ok
            ? `Recherche démarrée pour "${data.full_name}".`
            : `Erreur : ${data.detail ?? "inconnue"}`;
        if (response.ok) searchForm.reset();
    } catch (err) {
        searchResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshSearches();
    }
});

monitoringForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(monitoringForm);
    monitoringResult.textContent = "Démarrage de la surveillance...";
    try {
        const response = await fetch("/api/monitoring/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ camera: formData.get("camera") }),
        });
        const data = await response.json();
        monitoringResult.textContent = response.ok
            ? `Surveillance démarrée sur la caméra "${data.camera_source}".`
            : `Erreur : ${data.detail ?? "inconnue"}`;
    } catch (err) {
        monitoringResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshMonitors();
    }
});

searchTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='stop-search']");
    if (!button) return;
    await fetch(`/api/search/${button.dataset.id}/stop`, { method: "POST" });
    await refreshSearches();
});

monitoringTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='stop-monitor']");
    if (!button) return;
    await fetch(`/api/monitoring/${button.dataset.id}/stop`, { method: "POST" });
    await refreshMonitors();
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
