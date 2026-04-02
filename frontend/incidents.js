const apiStatus = document.getElementById('apiStatus');
const incidentList = document.getElementById('incidentList');
const incidentTitle = document.getElementById('incidentTitle');
const incidentRca = document.getElementById('incidentRca');
const incidentChatHistory = document.getElementById('incidentChatHistory');

const checkHealth = async () => {
  try {
    const res = await fetch('/health');
    if (!res.ok) throw new Error();
    apiStatus.textContent = 'API Healthy';
  } catch {
    apiStatus.textContent = 'API Unreachable';
  }
};

const renderStructured = (text) => {
  const wrapper = document.createElement('div');
  const lines = text.split('\n').filter(Boolean);
  lines.forEach((line) => {
    const p = document.createElement('p');
    p.textContent = line.replace(/^[-*]\s*/, '• ');
    wrapper.appendChild(p);
  });
  return wrapper;
};

const loadIncidentDetails = async (id, label) => {
  const res = await fetch(`/incident/${id}`);
  const data = await res.json();
  if (!res.ok) return;

  incidentTitle.textContent = `${label}`;
  incidentRca.textContent = data.rca_report || '';
  incidentChatHistory.innerHTML = '';

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
    a.appendChild(renderStructured(`Glow:\n${item.answer}`));

    incidentChatHistory.appendChild(q);
    incidentChatHistory.appendChild(a);
  });
};

const loadIncidents = async () => {
  incidentList.innerHTML = '';
  const res = await fetch('/past-incidents');
  const data = await res.json();
  if (!res.ok) return;

  data.forEach((item) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.textContent = `${item.incident_file} (${item.created_at})`;
    btn.className = 'list-btn';
    btn.onclick = () => loadIncidentDetails(item.id, item.incident_file);
    li.appendChild(btn);
    incidentList.appendChild(li);
  });
};

document.getElementById('refreshIncidentsBtn').onclick = loadIncidents;
checkHealth();
loadIncidents();