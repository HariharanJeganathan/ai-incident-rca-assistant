const rcaOutput = document.getElementById('rcaOutput');
const impactOutput = document.getElementById('impactOutput');
const chatMessages = document.getElementById('chatMessages');
const apiStatus = document.getElementById('apiStatus');
let rcaContext = '';
let currentIncidentId = null;

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

const addMessage = (type, text) => {
  const div = document.createElement('div');
  div.className = `msg ${type}`;

  if (type === 'user') {
    div.textContent = `You: ${text}`;
  } else {
    div.appendChild(renderStructured(`Glow:\n${text}`));
  }

  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
};

const checkHealth = async () => {
  try {
    const res = await fetch('/health');
    if (!res.ok) throw new Error('Health failed');
    apiStatus.textContent = 'API Healthy';
  } catch {
    apiStatus.textContent = 'API Unreachable';
  }
};

const loadIncidentDetails = async (incidentId) => {
  const res = await fetch(`/incident/${incidentId}`);
  const data = await res.json();
  if (!res.ok) return;

  currentIncidentId = data.id;
  rcaContext = data.rca_report || '';
  rcaOutput.textContent = rcaContext;

  chatMessages.innerHTML = '';
  if (!data.chat_history.length) {
    addMessage('bot', 'No prior chat history found for this incident yet.');
    return;
  }

  data.chat_history.forEach((item) => {
    addMessage('user', item.question);
    addMessage('bot', item.answer);
  });
};

checkHealth();

document.getElementById('uploadBtn').onclick = async () => {
  const file = document.getElementById('excelFile').files[0];
  if (!file) return alert('Please select an Excel file');

  const formData = new FormData();
  formData.append('file', file);
  rcaOutput.textContent = 'Generating RCA...';

  const res = await fetch('/upload-excel', { method: 'POST', body: formData });
  const data = await res.json();
  if (!res.ok) return (rcaOutput.textContent = data.detail || 'Upload failed');

  currentIncidentId = data.incident_id;
  rcaContext = data.rca_report;
  rcaOutput.textContent = rcaContext;
  chatMessages.innerHTML = '';
  addMessage('bot', 'RCA generated successfully. Ask me anything about this incident.');
};

document.getElementById('impactBtn').onclick = async () => {
  if (!rcaContext) return alert('Please generate RCA first');

  impactOutput.textContent = 'Classifying impact...';
  const res = await fetch('/impact-classification', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rca_context: rcaContext }),
  });
  const data = await res.json();
  impactOutput.textContent = res.ok ? data.impact : data.detail || 'Failed';
};

document.getElementById('refreshPastBtn').onclick = async () => {
  const ul = document.getElementById('pastIncidents');
  ul.innerHTML = '';

  const res = await fetch('/past-incidents');
  const data = await res.json();
  if (!res.ok) return;

  data.forEach((i) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.textContent = `${i.incident_file} (${i.created_at})`;
    btn.className = 'list-btn';
    btn.onclick = () => loadIncidentDetails(i.id);
    li.appendChild(btn);
    ul.appendChild(li);
  });
};

document.getElementById('chatBtn').onclick = async () => {
  const question = document.getElementById('chatInput').value.trim();
  if (!question) return;
  if (!rcaContext) return alert('Please generate RCA first');

  addMessage('user', question);
  document.getElementById('chatInput').value = '';

  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, rca_context: rcaContext, incident_id: currentIncidentId }),
  });
  const data = await res.json();
  addMessage('bot', res.ok ? data.answer : data.detail || 'Failed');
};