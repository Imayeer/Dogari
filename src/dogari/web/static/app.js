const WEEKDAY_NAMES = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

// ---------------------------------------------------------------------------
// Onglets
// ---------------------------------------------------------------------------

document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
});

// ---------------------------------------------------------------------------
// Références DOM
// ---------------------------------------------------------------------------

const statusCards = document.getElementById("status-cards");
const anomaliesList = document.getElementById("anomalies-list");

const addPortalForm = document.getElementById("add-portal-form");
const portalResult = document.getElementById("portal-result");
const portalsTableBody = document.getElementById("portals-table-body");
const recognizePortalSelect = document.getElementById("recognize-portal-select");
const recognizeBtn = document.getElementById("recognize-btn");
const recognizeResult = document.getElementById("recognize-result");
const logsTableBody = document.getElementById("logs-table-body");

const addUserForm = document.getElementById("add-user-form");
const addUserResult = document.getElementById("add-user-result");
const addUserRoleSelect = document.getElementById("add-user-role-select");
const usersTableBody = document.getElementById("users-table-body");

const addRoleForm = document.getElementById("add-role-form");
const roleResult = document.getElementById("role-result");
const rolesTableBody = document.getElementById("roles-table-body");
const addScheduleForm = document.getElementById("add-schedule-form");
const scheduleRoleSelect = document.getElementById("schedule-role-select");
const schedulePortalSelect = document.getElementById("schedule-portal-select");
const scheduleResult = document.getElementById("schedule-result");
const schedulesTableBody = document.getElementById("schedules-table-body");

const addIpCameraForm = document.getElementById("add-ip-camera-form");
const ipCameraResult = document.getElementById("ip-camera-result");
const ipCamerasTableBody = document.getElementById("ip-cameras-table-body");

const searchForm = document.getElementById("search-form");
const searchResult = document.getElementById("search-result");
const searchTableBody = document.getElementById("search-table-body");
const searchCameraSelect = document.getElementById("search-camera-select");

const monitoringForm = document.getElementById("monitoring-form");
const monitoringResult = document.getElementById("monitoring-result");
const monitoringTableBody = document.getElementById("monitoring-table-body");
const monitoringCameraSelect = document.getElementById("monitoring-camera-select");
const securityEventsList = document.getElementById("security-events-list");

const reportForm = document.getElementById("report-form");
const reportResult = document.getElementById("report-result");
const reportCsvLink = document.getElementById("report-csv-link");
const reportTxtLink = document.getElementById("report-txt-link");

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

function formatDate(value) {
    return value ? value.replace("T", " ") : "-";
}

async function getJson(url) {
    const response = await fetch(url);
    return response.json();
}

// ---------------------------------------------------------------------------
// Vue d'ensemble
// ---------------------------------------------------------------------------

async function refreshStatus() {
    const data = await getJson("/api/status");
    statusCards.innerHTML = `
        <div class="card">Utilisateurs<strong>${data.users_count}</strong></div>
        <div class="card">Actifs<strong>${data.active_users_count}</strong></div>
        <div class="card">Accès enregistrés<strong>${data.recent_access_count}</strong></div>
        <div class="card">Portails<strong>${data.portals_count}</strong></div>
        <div class="card">Caméras IP<strong>${data.ip_cameras_count}</strong></div>
        <div class="card">Rôles<strong>${data.roles_count}</strong></div>
    `;
}

async function refreshAnomalies() {
    const anomalies = await getJson("/api/access/anomalies");
    anomaliesList.innerHTML = anomalies.length
        ? anomalies.map((a) => `<li class="anomaly-${a.severity}">${a.message}</li>`).join("")
        : "<li class=\"anomaly-none\">Aucune anomalie détectée.</li>";
}

// ---------------------------------------------------------------------------
// Portails + reconnaissance + logs
// ---------------------------------------------------------------------------

async function refreshPortals() {
    const portals = await getJson("/api/portals");

    portalsTableBody.innerHTML = portals
        .map(
            (p) => `
        <tr>
            <td>${p.name}</td>
            <td>${p.camera_source}</td>
            <td>${p.camera_kind}</td>
            <td>${p.door_type}${p.gpio_relay_pin !== null ? ` (broche ${p.gpio_relay_pin})` : ""}</td>
            <td>${p.status}</td>
            <td><button data-action="delete-portal" data-id="${p.id}">Supprimer</button></td>
        </tr>`
        )
        .join("");

    const options = portals.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
    recognizePortalSelect.innerHTML = options || "<option value=\"\">Aucun portail configuré</option>";
    schedulePortalSelect.innerHTML = options || "<option value=\"\">Aucun portail configuré</option>";

    return portals;
}

async function refreshLogs() {
    const logs = await getJson("/api/access/logs?limit=25");
    logsTableBody.innerHTML = logs
        .map(
            (log) => `
        <tr>
            <td>${formatDate(log.created_at)}</td>
            <td>${log.full_name ?? "Inconnu"}</td>
            <td>${log.portal_name ?? "-"}</td>
            <td class="status-${log.status}">${log.status}</td>
            <td>${log.similarity_score !== null ? log.similarity_score.toFixed(2) : "-"}</td>
            <td>${log.message ?? ""}</td>
        </tr>`
        )
        .join("");
}

addPortalForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(addPortalForm);
    const gpioPin = formData.get("gpio_relay_pin");
    portalResult.textContent = "Création en cours...";
    try {
        const response = await fetch("/api/portals", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: formData.get("name"),
                camera_source: formData.get("camera_source"),
                camera_kind: formData.get("camera_kind"),
                door_type: formData.get("door_type"),
                gpio_relay_pin: gpioPin ? Number(gpioPin) : null,
            }),
        });
        const data = await response.json();
        portalResult.textContent = response.ok ? `Portail "${data.name}" créé.` : `Erreur : ${data.detail ?? "inconnue"}`;
        if (response.ok) addPortalForm.reset();
    } catch (err) {
        portalResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshPortals();
    }
});

portalsTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='delete-portal']");
    if (!button) return;
    if (!confirm("Supprimer définitivement ce portail ?")) return;
    await fetch(`/api/portals/${button.dataset.id}`, { method: "DELETE" });
    await refreshPortals();
});

recognizeBtn.addEventListener("click", async () => {
    const portalId = recognizePortalSelect.value;
    if (!portalId) {
        recognizeResult.textContent = "Créez d'abord un portail.";
        return;
    }
    recognizeBtn.disabled = true;
    recognizeResult.textContent = "Reconnaissance en cours...";
    try {
        const response = await fetch(`/api/access/recognize?portal_id=${portalId}`, { method: "POST" });
        const data = await response.json();
        recognizeResult.innerHTML = response.ok
            ? `<span class="status-${data.access_status}">${data.access_status.toUpperCase()}</span> — ${data.message}`
            : `Erreur : ${data.detail ?? "inconnue"}`;
    } catch (err) {
        recognizeResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        recognizeBtn.disabled = false;
        await refreshLogs();
        await refreshAnomalies();
    }
});

// ---------------------------------------------------------------------------
// Utilisateurs
// ---------------------------------------------------------------------------

async function refreshUsers() {
    const users = await getJson("/api/users");
    usersTableBody.innerHTML = users
        .map(
            (user) => `
        <tr>
            <td>${user.full_name}</td>
            <td>${user.role_name ?? "-"}</td>
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

addUserForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    addUserResult.textContent = "Ajout en cours...";
    const formData = new FormData(addUserForm);
    if (!formData.get("role_id")) formData.delete("role_id");
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
        await refreshUsers();
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

// ---------------------------------------------------------------------------
// Rôles + horaires
// ---------------------------------------------------------------------------

async function refreshRoles() {
    const roles = await getJson("/api/roles");

    rolesTableBody.innerHTML = roles
        .map(
            (role) => `
        <tr>
            <td>${role.name}</td>
            <td>${formatDate(role.created_at)}</td>
            <td><button data-action="delete-role" data-id="${role.id}">Supprimer</button></td>
        </tr>`
        )
        .join("");

    const options = roles.map((r) => `<option value="${r.id}">${r.name}</option>`).join("");
    scheduleRoleSelect.innerHTML = options || "<option value=\"\">Créez d'abord un rôle</option>";
    addUserRoleSelect.innerHTML = `<option value="">Aucun</option>${options}`;

    return roles;
}

async function refreshSchedules() {
    const [schedules, roles, portals] = await Promise.all([
        getJson("/api/roles/schedules"),
        getJson("/api/roles"),
        getJson("/api/portals"),
    ]);
    const roleNames = Object.fromEntries(roles.map((r) => [r.id, r.name]));
    const portalNames = Object.fromEntries(portals.map((p) => [p.id, p.name]));

    schedulesTableBody.innerHTML = schedules
        .map(
            (s) => `
        <tr>
            <td>${roleNames[s.role_id] ?? "?"}</td>
            <td>${portalNames[s.portal_id] ?? "?"}</td>
            <td>${WEEKDAY_NAMES[s.weekday]}</td>
            <td>${s.start_time}</td>
            <td>${s.end_time}</td>
            <td>
                <button data-action="delete-schedule" data-role-id="${s.role_id}" data-id="${s.id}">
                    Supprimer
                </button>
            </td>
        </tr>`
        )
        .join("");
}

addRoleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(addRoleForm);
    roleResult.textContent = "Création en cours...";
    try {
        const response = await fetch("/api/roles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: formData.get("name") }),
        });
        const data = await response.json();
        roleResult.textContent = response.ok ? `Rôle "${data.name}" créé.` : `Erreur : ${data.detail ?? "inconnue"}`;
        if (response.ok) addRoleForm.reset();
    } catch (err) {
        roleResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshRoles();
    }
});

rolesTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='delete-role']");
    if (!button) return;
    if (!confirm("Supprimer définitivement ce rôle ?")) return;
    const response = await fetch(`/api/roles/${button.dataset.id}`, { method: "DELETE" });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        alert(data.detail ?? "Suppression impossible.");
    }
    await refreshRoles();
    await refreshSchedules();
});

addScheduleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(addScheduleForm);
    scheduleResult.textContent = "Ajout en cours...";
    const roleId = formData.get("role_id");
    try {
        const response = await fetch(`/api/roles/${roleId}/schedules`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                portal_id: Number(formData.get("portal_id")),
                weekday: Number(formData.get("weekday")),
                start_time: formData.get("start_time"),
                end_time: formData.get("end_time"),
            }),
        });
        const data = await response.json();
        scheduleResult.textContent = response.ok ? "Horaire ajouté." : `Erreur : ${data.detail ?? "inconnue"}`;
    } catch (err) {
        scheduleResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshSchedules();
    }
});

schedulesTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='delete-schedule']");
    if (!button) return;
    await fetch(`/api/roles/${button.dataset.roleId}/schedules/${button.dataset.id}`, { method: "DELETE" });
    await refreshSchedules();
});

// ---------------------------------------------------------------------------
// Caméras IP + sélecteur combiné (portails + caméras IP)
// ---------------------------------------------------------------------------

async function refreshIpCameras() {
    const cameras = await getJson("/api/ip-cameras");
    ipCamerasTableBody.innerHTML = cameras
        .map(
            (c) => `
        <tr>
            <td>${c.name}</td>
            <td>${c.source}</td>
            <td>${c.status}</td>
            <td><button data-action="delete-ip-camera" data-id="${c.id}">Supprimer</button></td>
        </tr>`
        )
        .join("");
    return cameras;
}

async function refreshCombinedCameraSelectors() {
    const [portals, cameras] = await Promise.all([getJson("/api/portals"), getJson("/api/ip-cameras")]);
    const portalOptions = portals.map((p) => `<option value="portal:${p.id}">${p.name}</option>`).join("");
    const ipOptions = cameras.map((c) => `<option value="ip:${c.id}">${c.name}</option>`).join("");
    const html = `
        ${portals.length ? `<optgroup label="Portails">${portalOptions}</optgroup>` : ""}
        ${cameras.length ? `<optgroup label="Caméras IP">${ipOptions}</optgroup>` : ""}
    `;
    searchCameraSelect.innerHTML = html;
    monitoringCameraSelect.innerHTML = html;
}

function parseCameraSelector(value) {
    const [kind, id] = value.split(":");
    return kind === "portal" ? { portal_id: Number(id) } : { ip_camera_id: Number(id) };
}

addIpCameraForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(addIpCameraForm);
    ipCameraResult.textContent = "Ajout en cours...";
    try {
        const response = await fetch("/api/ip-cameras", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: formData.get("name"), source: formData.get("source") }),
        });
        const data = await response.json();
        ipCameraResult.textContent = response.ok
            ? `Caméra "${data.name}" ajoutée.`
            : `Erreur : ${data.detail ?? "inconnue"}`;
        if (response.ok) addIpCameraForm.reset();
    } catch (err) {
        ipCameraResult.textContent = `Erreur réseau : ${err}`;
    } finally {
        await refreshIpCameras();
        await refreshCombinedCameraSelectors();
    }
});

ipCamerasTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='delete-ip-camera']");
    if (!button) return;
    if (!confirm("Supprimer définitivement cette caméra IP ?")) return;
    await fetch(`/api/ip-cameras/${button.dataset.id}`, { method: "DELETE" });
    await refreshIpCameras();
    await refreshCombinedCameraSelectors();
});

// ---------------------------------------------------------------------------
// Recherche de personne
// ---------------------------------------------------------------------------

async function refreshSearches() {
    const searches = await getJson("/api/search");
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

searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(searchForm);
    if (!searchCameraSelect.value) {
        searchResult.textContent = "Créez d'abord un portail ou une caméra IP.";
        return;
    }
    searchResult.textContent = "Démarrage de la recherche...";
    try {
        const response = await fetch("/api/search/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                full_name: formData.get("full_name"),
                ...parseCameraSelector(searchCameraSelect.value),
            }),
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

searchTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='stop-search']");
    if (!button) return;
    await fetch(`/api/search/${button.dataset.id}/stop`, { method: "POST" });
    await refreshSearches();
});

// ---------------------------------------------------------------------------
// Surveillance sécurité
// ---------------------------------------------------------------------------

async function refreshMonitors() {
    const monitors = await getJson("/api/monitoring");
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
    const events = await getJson("/api/monitoring/events?limit=25");
    securityEventsList.innerHTML = events.length
        ? events
              .map((event) => `<li class="anomaly-${event.severity}">${formatDate(event.created_at)} — ${event.message}</li>`)
              .join("")
        : "<li class=\"anomaly-none\">Aucun événement de sécurité détecté.</li>";
}

monitoringForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!monitoringCameraSelect.value) {
        monitoringResult.textContent = "Créez d'abord un portail ou une caméra IP.";
        return;
    }
    monitoringResult.textContent = "Démarrage de la surveillance...";
    try {
        const response = await fetch("/api/monitoring/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(parseCameraSelector(monitoringCameraSelect.value)),
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

monitoringTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action='stop-monitor']");
    if (!button) return;
    await fetch(`/api/monitoring/${button.dataset.id}/stop`, { method: "POST" });
    await refreshMonitors();
});

// ---------------------------------------------------------------------------
// Rapports
// ---------------------------------------------------------------------------

reportForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const days = new FormData(reportForm).get("days") || 7;
    reportCsvLink.href = `/api/reports/export.csv?days=${days}`;
    reportTxtLink.href = `/api/reports/export.txt?days=${days}`;
    reportResult.textContent = "Génération en cours...";
    try {
        const data = await getJson(`/api/reports/summary?days=${days}`);
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

// ---------------------------------------------------------------------------
// Chargement initial
// ---------------------------------------------------------------------------

async function refreshAll() {
    await Promise.all([
        refreshStatus(),
        refreshAnomalies(),
        refreshPortals(),
        refreshLogs(),
        refreshUsers(),
        refreshRoles(),
        refreshIpCameras(),
        refreshSearches(),
        refreshMonitors(),
        refreshSecurityEvents(),
    ]);
    // Dépend des listes ci-dessus (rôles/portails/caméras déjà chargés)
    await Promise.all([refreshSchedules(), refreshCombinedCameraSelectors()]);
}

refreshAll();
