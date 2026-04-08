const apiStatus = document.getElementById('apiStatus');
const incidentList = document.getElementById('incidentList');
const incidentTitle = document.getElementById('incidentTitle');
const incidentRca = document.getElementById('incidentRca');
const incidentChatHistory = document.getElementById('incidentChatHistory');

const parseResponse = async (res) => {
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return { detail: await res.text() };
};

const checkHealth = async () => {
  try {
    const res = await fetch('/health');
    if (!res.ok) throw new Error();
    apiStatus.textContent = 'API Healthy';
  } catch {
    apiStatus.textContent = 'API Unreachable';
  }
};

const loadIncidentDetails = async (id, label) => {
  incidentTitle.textContent = `Loading ${label}…`;
  incidentRca.textContent = '';
  incidentChatHistory.innerHTML = '';

  try {
    const res = await fetch(`/incident/${id}`);
    const data = await parseResponse(res);
    if (!res.ok) {
      incidentTitle.textContent = 'Error loading incident';
      incidentRca.textContent = data.detail || 'Failed to load incident details';
      return;
    }

    incidentTitle.textContent = label;
    incidentRca.innerHTML = marked.parse(data.rca_report || '');

    if (!data.chat_history.length) {
      incidentChatHistory.textContent = 'No conversation saved yet for this incident.';
      return;
    }

    data.chat_history.forEach((item) => {
      const q = document.createElement('div');
      q.className = 'msg user';
      q.textContent = `You: ${item.question}`;

      const a = document.createElement('div');
      a.className = 'msg bot';
      a.innerHTML = marked.parse(`**Glow:** ${item.answer}`);

      incidentChatHistory.appendChild(q);
      incidentChatHistory.appendChild(a);
    });
  } catch (err) {
    incidentTitle.textContent = 'Error';
    incidentRca.textContent = `Failed to load incident: ${err.message}`;
  }
};

const loadIncidents = async () => {
  incidentList.innerHTML = '';
  try {
    const res = await fetch('/past-incidents');
    const data = await parseResponse(res);
    if (!res.ok) return;

    if (!data.length) {
      incidentList.innerHTML = '<li style="color:var(--muted)">No incidents found.</li>';
      return;
    }

    data.forEach((item) => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.textContent = `${item.incident_file} (${item.created_at})`;
      btn.className = 'list-btn';
      btn.onclick = () => loadIncidentDetails(item.id, item.incident_file);
      li.appendChild(btn);
      incidentList.appendChild(li);
    });
  } catch (err) {
    incidentList.innerHTML = `<li style="color:#f87171">Error: ${err.message}</li>`;
  }
};

document.getElementById('refreshIncidentsBtn').onclick = loadIncidents;
checkHealth();
loadIncidents();
