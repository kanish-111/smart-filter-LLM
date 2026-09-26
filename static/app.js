const state = {
  dataset: "work_orders",
  datasets: [],
  columns: [],
  page: 1,
  pageSize: 25,
  plan: null,
  total: 0,
  rows: [],
};

const $ = (selector) => document.querySelector(selector);

function showError(message) {
  const banner = $("#error-banner");
  banner.textContent = message;
  banner.classList.remove("hidden");
}

function clearError() {
  $("#error-banner").classList.add("hidden");
  $("#error-banner").textContent = "";
}

function setLoading(loading) {
  const button = $("#ask-ai");
  button.disabled = loading;
  button.innerHTML = loading ? "<span>◌</span> Planning query…" : "<span>✦</span> Apply smart filter";
  if (loading) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = Math.max(1, state.columns.length);
    cell.className = "loading-cell";
    cell.textContent = "Applying the smart filter to the selected table…";
    row.append(cell);
    $("#rows-body").replaceChildren(row);
  }
}

async function requestRows(newQuery) {
  clearError();
  setLoading(true);
  const body = {
    dataset: state.dataset,
    smart_query: newQuery === undefined ? "" : newQuery,
    smart_plan: newQuery === undefined ? state.plan : null,
    page: state.page,
    page_size: state.pageSize,
  };
  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The query failed.");
    state.plan = data.plan || null;
    state.rows = data.rows || [];
    state.total = data.total || 0;
    renderResults(data);
  } catch (error) {
    showError(error.message || "Could not reach the demo server.");
    state.rows = [];
    renderRows([]);
    $("#range-label").textContent = "Query failed";
  } finally {
    setLoading(false);
  }
}

function createCell(row, value, className) {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  cell.textContent = value == null || value === "" ? "—" : String(value);
  row.append(cell);
  return cell;
}

function createBadgeCell(row, value, prefix) {
  const cell = document.createElement("td");
  const badge = document.createElement("span");
  badge.className = "badge " + prefix + "-" + String(value || "").toLowerCase().replaceAll(" ", "-");
  badge.textContent = value || "—";
  cell.append(badge);
  row.append(cell);
}

function formatMoney(value) {
  return value == null ? "—" : new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
}

function formatDecimal(value) {
  return value == null ? "—" : new Intl.NumberFormat("en-IE", { maximumFractionDigits: 1 }).format(value);
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IE", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(value + "T12:00:00Z"));
}

function renderRows(rows) {
  const body = $("#rows-body");
  body.replaceChildren();
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = Math.max(1, state.columns.length);
    td.className = "empty-cell";
    td.textContent = "No records match this smart filter.";
    tr.append(td);
    body.append(tr);
    return;
  }
  for (const item of rows) {
    const tr = document.createElement("tr");
    for (const column of state.columns) {
      const value = item[column.field];
      const className = column.numeric ? "numeric" : column.format === "id" ? "ticket" : "";
      if (column.format === "badge") createBadgeCell(tr, value, column.class);
      else if (column.format === "date") createCell(tr, formatDate(value), className);
      else if (column.format === "money") createCell(tr, formatMoney(value), className);
      else if (column.format === "decimal") createCell(tr, formatDecimal(value), className);
      else {
        const cell = createCell(tr, value, className);
        if (column.format === "id") cell.title = value || "";
      }
    }
    body.append(tr);
  }
}

// Build the table from server-provided column metadata for the selected dataset.
function renderColumns() {
  const row = document.createElement("tr");
  for (const column of state.columns) {
    const heading = document.createElement("th");
    heading.textContent = column.label.toUpperCase();
    if (column.numeric) heading.className = "numeric";
    row.append(heading);
  }
  $("#columns-head").replaceChildren(row);
}

function renderResults(data) {
  renderRows(state.rows);
  const dataset = state.datasets.find((item) => item.key === state.dataset);
  const total = Number(data.total || 0);
  const start = total ? (state.page - 1) * state.pageSize + 1 : 0;
  const end = start ? start + state.rows.length - 1 : 0;
  const beforeLimit = data.matched_count !== total ? " (" + Number(data.matched_count).toLocaleString() + " matched before top limit)" : "";
  $("#range-label").textContent = "Showing " + start.toLocaleString() + "–" + end.toLocaleString() + " of " + total.toLocaleString() + beforeLimit;
  $("#page-label").textContent = "Page " + state.page;
  $("#prev-page").disabled = state.page <= 1;
  $("#next-page").disabled = end >= total || state.rows.length === 0;
  $("#result-subtitle").textContent = state.plan
    ? "Filtered results from the synthetic " + dataset.label.toLowerCase() + " dataset."
    : "Browse the synthetic " + dataset.label.toLowerCase() + " dataset.";

  const applied = $("#applied-bar");
  if (state.plan) {
    applied.classList.remove("hidden");
    $("#applied-text").textContent = state.plan.applied_filter_text || "Smart filter applied";
    $("#plan-details").classList.remove("hidden");
    $("#plan-json").textContent = JSON.stringify(state.plan, null, 2);
  } else {
    applied.classList.add("hidden");
    $("#plan-details").classList.add("hidden");
    $("#plan-details").open = false;
  }
}

async function initialize() {
  try {
    const response = await fetch("/api/meta");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load demo data.");
    state.datasets = data.datasets || [];
    const picker = $("#dataset-select");
    picker.replaceChildren();
    for (const dataset of state.datasets) {
      const option = document.createElement("option");
      option.value = dataset.key;
      option.textContent = dataset.label;
      picker.append(option);
    }
    state.dataset = picker.value || state.datasets[0].key;
    state.columns = state.datasets.find((item) => item.key === state.dataset).columns;
    $("#dataset-count").textContent = Number(state.datasets.find((item) => item.key === state.dataset).count).toLocaleString();
    $("#model-label").textContent = "Model: " + data.model;
    renderColumns();
    updateDatasetLabels();
    await requestRows("");
  } catch (error) {
    showError(error.message || "Could not load the demo.");
    renderRows([]);
  }
}

function updateDatasetLabels() {
  const dataset = state.datasets.find((item) => item.key === state.dataset);
  $("#dataset-title").textContent = dataset.label;
  $("#results-title").textContent = "All " + dataset.label.toLowerCase();
  $("#dataset-count").textContent = Number(dataset.count).toLocaleString();
  $("#dataset-subtitle").textContent = dataset.key === "work_orders"
    ? "Search and triage service work across your solar sites."
    : "Review safety, performance, and routine site checks.";
  $("#smart-query").placeholder = dataset.key === "work_orders"
    ? "e.g. Critical inverter jobs in Munster over EUR 5,000"
    : "e.g. Failed safety inspections in Munster with downtime over 5 hours";
}

$("#ask-ai").addEventListener("click", () => {
  const query = $("#smart-query").value.trim();
  if (!query) {
    if (state.plan) return requestRows("");
    return showError("Describe the records you want to find first.");
  }
  state.page = 1;
  requestRows(query);
});

$("#smart-query").addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") $("#ask-ai").click();
});
$("#prev-page").addEventListener("click", () => {
  state.page = Math.max(1, state.page - 1);
  requestRows();
});
$("#next-page").addEventListener("click", () => {
  state.page += 1;
  requestRows();
});
$("#clear-smart").addEventListener("click", () => {
  state.plan = null;
  $("#smart-query").value = "";
  state.page = 1;
  requestRows("");
});
$("#reset-all").addEventListener("click", () => $("#clear-smart").click());
$("#dataset-select").addEventListener("change", (event) => {
  state.dataset = event.target.value;
  const dataset = state.datasets.find((item) => item.key === state.dataset);
  state.columns = dataset.columns;
  state.plan = null;
  state.page = 1;
  $("#smart-query").value = "";
  renderColumns();
  updateDatasetLabels();
  requestRows("");
});

initialize();
