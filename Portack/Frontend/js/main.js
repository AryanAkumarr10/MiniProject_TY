const API = "http://127.0.0.1:5000/api";
let currentUser = null;

// ---------- helpers ----------
async function apiFetch(path, options = {}) {
  const res = await fetch(API + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    credentials: "include"
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function showMsg(el, text, type) {
  el.textContent = text;
  el.className = "form-msg " + (type || "");
}

function statusBadge(status) {
  const map = {
    scheduled: "badge-neutral", berthed: "badge-progress", departed: "badge-good",
    loaded: "badge-neutral", unloaded: "badge-progress", in_yard: "badge-progress", dispatched: "badge-good",
    unpaid: "badge-bad", paid: "badge-good",
    pending: "badge-neutral", under_review: "badge-progress", cleared: "badge-good", rejected: "badge-bad"
  };
  const cls = map[status] || "badge-neutral";
  const label = (status || "").replace(/_/g, " ");
  return `<span class="badge ${cls}">${label}</span>`;
}

function emptyRow(colspan, text) {
  return `<tr class="table-empty"><td colspan="${colspan}">${text}</td></tr>`;
}

async function withLoading(form, fn) {
  const btn = form.querySelector("button[type=submit], button:not([type])");
  const original = btn ? btn.textContent : null;
  if (btn) { btn.disabled = true; btn.textContent = "Working…"; }
  try {
    await fn();
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = original; }
  }
}

// ---------- navigation ----------
document.querySelectorAll(".nav-link").forEach(btn => {
  btn.addEventListener("click", () => switchSection(btn.dataset.section));
});

function switchSection(name) {
  document.querySelectorAll(".module").forEach(m => m.classList.remove("active"));
  document.getElementById("section-" + name).classList.add("active");
  document.querySelectorAll(".nav-link").forEach(b => b.classList.toggle("active", b.dataset.section === name));
  if (name === "dashboard") loadDashboard();
  if (name === "vessels") { loadBerths(); loadVessels(); }
  if (name === "cargo") { loadVesselOptions("cargoVesselSelect"); loadCargo(); }
  if (name === "billing") { loadVesselOptions("invoiceVesselSelect"); loadInvoices(); }
  if (name === "customs") { loadCargoOptions(); loadCustoms(); }
}

document.getElementById("authToggleBtn").addEventListener("click", () => {
  if (currentUser) { logout(); } else { switchSection("auth"); document.querySelectorAll(".nav-link").forEach(b=>b.classList.remove("active")); }
});

// ---------- auth ----------
async function checkAuth() {
  try {
    const data = await apiFetch("/auth/me");
    currentUser = data.user;
  } catch { currentUser = null; }
  updateAccountBox();
}

function updateAccountBox() {
  const status = document.getElementById("accountStatus");
  const btn = document.getElementById("authToggleBtn");
  if (currentUser) {
    status.textContent = `${currentUser.name} (${currentUser.role})`;
    btn.textContent = "Sign out";
  } else {
    status.textContent = "Not signed in";
    btn.textContent = "Sign in";
  }
}

document.getElementById("loginForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("loginMsg");
  const form = new FormData(e.target);
  await withLoading(e.target, async () => {
    try {
      const data = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
      currentUser = data.user;
      updateAccountBox();
      showMsg(msg, "Signed in.", "success");
      switchSection("dashboard");
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

document.getElementById("registerForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("registerMsg");
  const form = new FormData(e.target);
  await withLoading(e.target, async () => {
    try {
      await apiFetch("/auth/register", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) });
      showMsg(msg, "Account created. You can sign in now.", "success");
      e.target.reset();
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

async function logout() {
  await apiFetch("/auth/logout", { method: "POST" });
  currentUser = null;
  updateAccountBox();
  switchSection("auth");
  document.querySelectorAll(".nav-link").forEach(b=>b.classList.remove("active"));
}

// ---------- dashboard ----------
async function loadDashboard() {
  try {
    const d = await apiFetch("/reports/dashboard");
    document.getElementById("statBerths").textContent = d.berths.free;
    document.getElementById("statVessels").textContent = d.vessels.scheduled;
    document.getElementById("statCargo").textContent = d.cargo.total_weight_tons;
    document.getElementById("statUnpaid").textContent = d.billing.unpaid_invoices;
    document.getElementById("statRevenue").textContent = "₹" + d.billing.total_revenue;
  } catch (err) { console.error(err); }
}
document.getElementById("refreshDashboard").addEventListener("click", loadDashboard);

// ---------- berths & vessels ----------
document.getElementById("berthForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("berthMsg");
  const form = Object.fromEntries(new FormData(e.target));
  form.capacity_tons = Number(form.capacity_tons) || 0;
  await withLoading(e.target, async () => {
    try {
      await apiFetch("/berths", { method: "POST", body: JSON.stringify(form) });
      showMsg(msg, "Berth added.", "success");
      e.target.reset();
      loadBerths();
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

async function loadBerths() {
  const data = await apiFetch("/berths");
  const tbody = document.querySelector("#berthTable tbody");
  tbody.innerHTML = data.length
    ? data.map(b => `<tr><td>${b.code}</td><td>${b.capacity_tons}</td></tr>`).join("")
    : emptyRow(2, "No berths added yet.");

  const select = document.getElementById("berthSelect");
  select.innerHTML = `<option value="">No berth yet</option>` +
    data.map(b => `<option value="${b.id}">${b.code}</option>`).join("");
}

document.getElementById("vesselForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("vesselMsg");
  const form = Object.fromEntries(new FormData(e.target));
  if (!form.berth_id) delete form.berth_id; else form.berth_id = Number(form.berth_id);
  await withLoading(e.target, async () => {
    try {
      await apiFetch("/vessels", { method: "POST", body: JSON.stringify(form) });
      showMsg(msg, "Vessel scheduled.", "success");
      e.target.reset();
      loadVessels();
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

async function loadVessels() {
  const data = await apiFetch("/vessels");
  const tbody = document.querySelector("#vesselTable tbody");
  tbody.innerHTML = data.length ? data.map(v => `
    <tr>
      <td>${v.name}</td><td>${v.vessel_type}</td><td>${v.berth_code || "—"}</td>
      <td>${new Date(v.arrival_time).toLocaleString()}</td>
      <td>${new Date(v.departure_time).toLocaleString()}</td>
      <td>${statusBadge(v.status)}</td>
      <td>
        <select onchange="updateVesselStatus(${v.id}, this.value)">
          <option value="">Set status</option>
          <option value="scheduled">Scheduled</option>
          <option value="berthed">Berthed</option>
          <option value="departed">Departed</option>
        </select>
      </td>
    </tr>`).join("") : emptyRow(7, "No vessels scheduled yet.");
}

async function updateVesselStatus(id, status) {
  if (!status) return;
  await apiFetch(`/vessels/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
  loadVessels();
  loadDashboard();
}

async function loadVesselOptions(selectId) {
  const data = await apiFetch("/vessels");
  document.getElementById(selectId).innerHTML = data.length
    ? data.map(v => `<option value="${v.id}">${v.name}</option>`).join("")
    : `<option value="">No vessels yet</option>`;
}

// ---------- cargo ----------
document.getElementById("cargoForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("cargoMsg");
  const form = Object.fromEntries(new FormData(e.target));
  form.vessel_id = Number(form.vessel_id);
  form.weight_tons = Number(form.weight_tons);
  await withLoading(e.target, async () => {
    try {
      await apiFetch("/cargo", { method: "POST", body: JSON.stringify(form) });
      showMsg(msg, "Cargo recorded.", "success");
      e.target.reset();
      loadCargo();
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

async function loadCargo() {
  const data = await apiFetch("/cargo");
  const tbody = document.querySelector("#cargoTable tbody");
  tbody.innerHTML = data.length ? data.map(c => `
    <tr>
      <td>${c.container_number || "—"}</td><td>${c.description}</td><td>${c.vessel_name}</td>
      <td>${c.weight_tons}</td><td>${c.yard_location || "—"}</td><td>${statusBadge(c.status)}</td>
      <td>
        <select onchange="updateCargoStatus(${c.id}, this.value)">
          <option value="">Set status</option>
          <option value="loaded">Loaded</option>
          <option value="unloaded">Unloaded</option>
          <option value="in_yard">In yard</option>
          <option value="dispatched">Dispatched</option>
        </select>
      </td>
    </tr>`).join("") : emptyRow(7, "No cargo recorded yet.");
}

async function updateCargoStatus(id, status) {
  if (!status) return;
  await apiFetch(`/cargo/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
  loadCargo();
  loadDashboard();
}

// ---------- billing ----------
document.getElementById("invoiceForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("invoiceMsg");
  const form = Object.fromEntries(new FormData(e.target));
  form.vessel_id = Number(form.vessel_id);
  await withLoading(e.target, async () => {
    try {
      await apiFetch("/invoices/generate", { method: "POST", body: JSON.stringify(form) });
      showMsg(msg, "Invoice generated.", "success");
      loadInvoices();
      loadDashboard();
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

async function loadInvoices() {
  const data = await apiFetch("/invoices");
  const tbody = document.querySelector("#invoiceTable tbody");
  tbody.innerHTML = data.length ? data.map(i => `
    <tr>
      <td>${i.vessel_name}</td><td>₹${i.berth_hire_charge}</td><td>₹${i.cargo_handling_charge}</td>
      <td>₹${i.storage_charge}</td><td>₹${i.total_amount}</td><td>${statusBadge(i.status)}</td>
      <td>${i.status === "unpaid" ? `<button class="btn btn-ghost" onclick="payInvoice(${i.id})">Mark paid</button>` : ""}</td>
    </tr>`).join("") : emptyRow(7, "No invoices generated yet.");
}

async function payInvoice(id) {
  await apiFetch(`/invoices/${id}/pay`, { method: "PATCH" });
  loadInvoices();
  loadDashboard();
}

// ---------- customs ----------
document.getElementById("customsForm").addEventListener("submit", async e => {
  e.preventDefault();
  e.stopPropagation();
  const msg = document.getElementById("customsMsg");
  const form = Object.fromEntries(new FormData(e.target));
  form.cargo_id = Number(form.cargo_id);
  await withLoading(e.target, async () => {
    try {
      await apiFetch("/customs", { method: "POST", body: JSON.stringify(form) });
      showMsg(msg, "Clearance opened.", "success");
      e.target.reset();
      loadCustoms();
    } catch (err) { showMsg(msg, err.message, "error"); }
  });
});

async function loadCargoOptions() {
  const data = await apiFetch("/cargo");
  document.getElementById("customsCargoSelect").innerHTML = data.length
    ? data.map(c => `<option value="${c.id}">${c.description} (${c.container_number || "no container #"})</option>`).join("")
    : `<option value="">No cargo yet</option>`;
}

async function loadCustoms() {
  const data = await apiFetch("/customs");
  const tbody = document.querySelector("#customsTable tbody");
  tbody.innerHTML = data.length ? data.map(c => `
    <tr>
      <td>${c.cargo_description}</td><td>${c.shipping_bill_number || "—"}</td><td>${c.manifest_number || "—"}</td>
      <td>${statusBadge(c.status)}</td>
      <td>
        <select onchange="updateCustomsStatus(${c.id}, this.value)">
          <option value="">Set status</option>
          <option value="pending">Pending</option>
          <option value="under_review">Under review</option>
          <option value="cleared">Cleared</option>
          <option value="rejected">Rejected</option>
        </select>
      </td>
    </tr>`).join("") : emptyRow(5, "No clearances opened yet.");
}

async function updateCustomsStatus(id, status) {
  if (!status) return;
  await apiFetch(`/customs/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
  loadCustoms();
  loadCargo();
  loadDashboard();
}

// ---------- init ----------
checkAuth().then(() => {
  if (currentUser) switchSection("dashboard");
  else switchSection("auth");
});