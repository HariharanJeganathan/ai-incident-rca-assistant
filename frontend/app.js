const rcaOutput = document.getElementById('rcaOutput');
const impactOutput = document.getElementById('impactOutput');
const chatMessages = document.getElementById('chatMessages');
const apiStatus = document.getElementById('apiStatus');
let rcaContext = '';

const addMessage = (type, text) => {
  const div = document.createElement('div');
  div.className = `msg ${type}`;
  div.textContent = `${type === 'user' ? 'You' : 'Assistant'}: ${text}`;
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

  rcaContext = data.rca_report;
  rcaOutput.textContent = rcaContext;
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
    li.textContent = `${i.incident_file} (${i.created_at})`;
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
    body: JSON.stringify({ question, rca_context: rcaContext }),
  });
  const data = await res.json();
  addMessage('bot', res.ok ? data.answer : data.detail || 'Failed');
};