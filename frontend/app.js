const rcaOutput = document.getElementById('rcaOutput');
const impactOutput = document.getElementById('impactOutput');
const chatMessages = document.getElementById('chatMessages');
const apiStatus = document.getElementById('apiStatus');
let rcaContext = '';
let currentIncidentId = null;

// FastAPI returns text/plain on unhandled 500s, not JSON.
// This helper normalises both into a plain object so callers
// always get { detail } on errors instead of a SyntaxError.
const parseResponse = async (res) => {
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return { detail: await res.text() };
};

const addMessage = (type, text) => {
  const div = document.createElement('div');
  div.className = `msg ${type}`;

  if (type === 'user') {
    div.textContent = `You: ${text}`;
  } else {
    div.innerHTML = marked.parse(`**Glow:** ${text}`);
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
  try {
    const res = await fetch(`/incident/${incidentId}`);
    const data = await parseResponse(res);
    if (!res.ok) {
      rcaOutput.textContent = data.detail || 'Failed to load incident';
      return;
    }

    currentIncidentId = data.id;
    rcaContext = data.rca_report || '';
    rcaOutput.innerHTML = marked.parse(rcaContext);

    chatMessages.innerHTML = '';
    if (!data.chat_history.length) {
      addMessage('bot', 'No prior chat history found for this incident yet.');
      return;
    }

    data.chat_history.forEach((item) => {
      addMessage('user', item.question);
      addMessage('bot', item.answer);
    });
  } catch (err) {
    rcaOutput.textContent = `Error loading incident: ${err.message}`;
  }
};

checkHealth();

document.getElementById('uploadBtn').onclick = async () => {
  const file = document.getElementById('excelFile').files[0];
  if (!file) return alert('Please select an Excel file');

  const formData = new FormData();
  formData.append('file', file);
  rcaOutput.textContent = 'Generating RCA...';

  try {
    const res = await fetch('/upload-excel', { method: 'POST', body: formData });
    const data = await parseResponse(res);
    if (!res.ok) {
      rcaOutput.textContent = data.detail || 'Upload failed';
      return;
    }

    currentIncidentId = data.incident_id;
    rcaContext = data.rca_report;
    rcaOutput.innerHTML = marked.parse(rcaContext);
    chatMessages.innerHTML = '';
    addMessage('bot', 'RCA generated successfully. Ask me anything about this incident.');
  } catch (err) {
    rcaOutput.textContent = `Upload error: ${err.message}`;
  }
};

document.getElementById('impactBtn').onclick = async () => {
  if (!rcaContext) return alert('Please generate RCA first');

  impactOutput.textContent = 'Classifying impact...';
  try {
    const res = await fetch('/impact-classification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rca_context: rcaContext }),
    });
    const data = await parseResponse(res);
    impactOutput.textContent = res.ok ? data.impact : data.detail || 'Failed';
  } catch (err) {
    impactOutput.textContent = `Error: ${err.message}`;
  }
};

document.getElementById('refreshPastBtn').onclick = async () => {
  const ul = document.getElementById('pastIncidents');
  ul.innerHTML = '';

  try {
    const res = await fetch('/past-incidents');
    const data = await parseResponse(res);
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
  } catch (err) {
    ul.innerHTML = `<li style="color:#f87171">Error: ${err.message}</li>`;
  }
};

document.getElementById('chatBtn').onclick = async () => {
  const question = document.getElementById('chatInput').value.trim();
  if (!question) return;
  if (!rcaContext) return alert('Please generate RCA first');

  addMessage('user', question);
  document.getElementById('chatInput').value = '';

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, rca_context: rcaContext, incident_id: currentIncidentId }),
    });
    const data = await parseResponse(res);
    addMessage('bot', res.ok ? data.answer : data.detail || 'Request failed');
  } catch (err) {
    addMessage('bot', `Error reaching Glow: ${err.message}`);
  }
};
