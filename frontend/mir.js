// ── Helpers ───────────────────────────────────────────────────────────────────

const parseResponse = async (res) => {
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return { detail: await res.text() };
};

const checkHealth = async () => {
  try {
    const res = await fetch('/health');
    if (!res.ok) throw new Error();
    document.getElementById('apiStatus').textContent = 'API Healthy';
  } catch {
    document.getElementById('apiStatus').textContent = 'API Unreachable';
  }
};

// Copy-to-clipboard for all .copy-btn elements
document.querySelectorAll('.copy-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.target;
    const el = document.getElementById(targetId);
    const text = el.tagName === 'OL'
      ? Array.from(el.querySelectorAll('li')).map((li, i) => `${i + 1}. ${li.textContent}`).join('\n')
      : el.value || el.textContent;
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = 'Copied!';
      setTimeout(() => (btn.textContent = 'Copy'), 1500);
    });
  });
});

// ── State ──────────────────────────────────────────────────────────────────────
let mirState = {};

// ── Parse MIR .docx ───────────────────────────────────────────────────────────
document.getElementById('parseMirBtn').onclick = async () => {
  const file = document.getElementById('mirDocFile').files[0];
  if (!file) return;
  const status = document.getElementById('parseStatus');
  status.textContent = 'Parsing document…';

  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch('/mir/parse-doc', { method: 'POST', body: form });
    const data = await parseResponse(res);
    if (!res.ok) { status.textContent = data.detail || 'Parse failed'; return; }

    const m = data.metadata || {};
    if (m.inc_number) document.getElementById('incNumber').value = m.inc_number;
    if (m.prb_number) document.getElementById('prbNumber').value = m.prb_number;
    if (m.title) document.getElementById('incTitle').value = m.title;
    if (m.description) document.getElementById('incDescription').value = m.description;
    if (m.resolution) document.getElementById('incResolution').value = m.resolution;
    if (m.business_impact) document.getElementById('incBizImpact').value = m.business_impact;

    status.textContent = `Parsed: ${Object.keys(m).filter(k => m[k]).length} fields filled`;
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
};

// ── Parse Whiteboard Excel ────────────────────────────────────────────────────
document.getElementById('parseExcelBtn').onclick = async () => {
  const file = document.getElementById('whiteboardFile').files[0];
  if (!file) return;
  const preview = document.getElementById('attendeePreview');
  preview.textContent = 'Extracting…';

  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch('/mir/parse-excel', { method: 'POST', body: form });
    const data = await parseResponse(res);
    if (!res.ok) { preview.textContent = data.detail || 'Failed'; return; }

    const participants = data.participants || [];
    if (!participants.length) { preview.textContent = 'No Key Participants found'; return; }

    preview.innerHTML = '';
    participants.forEach(p => {
      const row = document.createElement('div');
      row.className = 'attendee-row';
      row.innerHTML = `<strong>${p.team}</strong><span>${p.emails.join(', ')}</span>`;
      preview.appendChild(row);
    });
  } catch (err) {
    preview.textContent = `Error: ${err.message}`;
  }
};

// ── Generate MIR ──────────────────────────────────────────────────────────────
document.getElementById('generateBtn').onclick = async () => {
  const status = document.getElementById('generateStatus');
  const required = ['incNumber', 'prbNumber', 'incTitle', 'incDescription', 'incResolution'];
  for (const id of required) {
    if (!document.getElementById(id).value.trim()) {
      status.textContent = `Please fill in: ${id.replace(/([A-Z])/g, ' $1').trim()}`;
      return;
    }
  }

  status.textContent = 'Generating MIR draft… (this may take 20–30 seconds)';
  document.getElementById('generateBtn').disabled = true;

  const form = new FormData();
  form.append('inc_number', document.getElementById('incNumber').value.trim());
  form.append('prb_number', document.getElementById('prbNumber').value.trim());
  form.append('ci', document.getElementById('ci').value.trim());
  form.append('title', document.getElementById('incTitle').value.trim());
  form.append('description', document.getElementById('incDescription').value.trim());
  form.append('resolution', document.getElementById('incResolution').value.trim());
  form.append('business_impact', document.getElementById('incBizImpact').value.trim());
  form.append('is_sco', document.getElementById('isSco').checked);
  form.append('inc_opened', document.getElementById('incOpened').value.trim());
  form.append('inc_resolved', document.getElementById('incResolved').value.trim());
  form.append('duration_degraded', document.getElementById('incDuration').value.trim());

  const wbFile = document.getElementById('whiteboardFile').files[0];
  if (wbFile) form.append('whiteboard_file', wbFile);

  try {
    const res = await fetch('/mir/generate', { method: 'POST', body: form });
    const data = await parseResponse(res);
    if (!res.ok) {
      status.textContent = data.detail || 'Generation failed';
      document.getElementById('generateBtn').disabled = false;
      return;
    }

    mirState = data;
    renderOutput(data);
    status.textContent = 'Done!';
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
  document.getElementById('generateBtn').disabled = false;
};

function renderOutput(data) {
  document.getElementById('mirOutput').style.display = 'block';
  document.getElementById('mirOutput').scrollIntoView({ behavior: 'smooth' });

  // Impact heading
  document.getElementById('headingOut').textContent = data.impact_heading || '';

  // Questions
  const ol = document.getElementById('questionsOut');
  ol.innerHTML = '';
  const groups = [
    { range: [0, 4], label: '5 Whys' },
    { range: [5, 5], label: 'Corrective Action' },
    { range: [6, 6], label: 'Preventive Action' },
    { range: [7, 9], label: 'Gap Analysis' },
  ];
  (data.questions || []).forEach((q, i) => {
    const li = document.createElement('li');
    li.textContent = q;
    // Add group label at start of each group
    const group = groups.find(g => i === g.range[0]);
    if (group) {
      const divider = document.createElement('li');
      divider.className = 'q-group-label';
      divider.textContent = group.label;
      ol.appendChild(divider);
    }
    ol.appendChild(li);
  });

  // Meeting prep
  document.getElementById('meetingSubject').value = data.meeting_subject || '';
  document.getElementById('meetingTo').value = (data.to_list || []).join('\n');
  document.getElementById('meetingCc').value = (data.cc_list || []).join('\n');
  document.getElementById('meetingEmail').value = data.email_body || '';
}

// ── Download .docx ────────────────────────────────────────────────────────────
document.getElementById('downloadBtn').onclick = async () => {
  if (!mirState.inc_number) return alert('Generate the MIR draft first');

  const payload = {
    ...mirState,
    root_cause_summary: document.getElementById('rcaSummary').value.trim(),
    capa: document.getElementById('capaText').value.trim(),
  };

  try {
    const res = await fetch('/mir/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) { alert('Download failed'); return; }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MIR_${mirState.inc_number}.docx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Download error: ${err.message}`);
  }
};

// ── Timeline Checker ──────────────────────────────────────────────────────────
document.getElementById('checkTimelineBtn').onclick = async () => {
  const file = document.getElementById('timelineFile').files[0];
  if (!file) return alert('Please select a timeline screenshot');

  const results = document.getElementById('timelineResults');
  results.innerHTML = '<p class="hint">Analysing timeline… (10–20 seconds)</p>';

  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch('/mir/timeline-check', { method: 'POST', body: form });
    const data = await parseResponse(res);
    if (!res.ok) { results.innerHTML = `<p style="color:#f87171">${data.detail || 'Failed'}</p>`; return; }

    renderTimelineResults(data, results);
  } catch (err) {
    results.innerHTML = `<p style="color:#f87171">Error: ${err.message}</p>`;
  }
};

function renderTimelineResults(data, container) {
  const statusIcon = { PASS: '✅', FAIL: '❌', MISSING: '⚠️', NEEDS_REVIEW: '🔍' };

  let html = `<div class="timeline-summary ${data.overall?.toLowerCase()}">${statusIcon[data.overall] || '🔍'} ${data.summary || ''}</div>`;

  html += '<table class="timeline-table"><thead><tr><th>#</th><th>Criterion</th><th>Status</th><th>Note</th></tr></thead><tbody>';
  (data.criteria || []).forEach(c => {
    const cls = c.status === 'PASS' ? 'pass' : c.status === 'FAIL' ? 'fail' : 'warn';
    html += `<tr class="${cls}"><td>${c.id}</td><td>${c.name}</td><td>${statusIcon[c.status] || c.status}</td><td>${c.note || ''}</td></tr>`;
  });
  html += '</tbody></table>';

  if (data.gaps_over_30min?.length) {
    html += '<div class="gap-warnings"><strong>Gaps over 30 minutes — action required:</strong><ul>';
    data.gaps_over_30min.forEach(g => {
      html += `<li><span class="gap-between">${g.between}</span> — ${g.duration} — <em>${g.action}</em></li>`;
    });
    html += '</ul></div>';
  }

  container.innerHTML = html;
}

// ── Stakeholder Settings ──────────────────────────────────────────────────────
const loadStakeholders = async () => {
  try {
    const res = await fetch('/mir/stakeholders');
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('ccAlways').value = (data.cc_always || []).join('\n');
    document.getElementById('scoDl').value = data.sco_dl || '';
    document.getElementById('nonScoCc').value = (data.non_sco_cc || []).join('\n');
  } catch { /* no stakeholders saved yet */ }
};

document.getElementById('saveStakeholdersBtn').onclick = async () => {
  const toLines = (id) => document.getElementById(id).value
    .split('\n').map(s => s.trim()).filter(Boolean);

  const payload = {
    cc_always: toLines('ccAlways'),
    sco_dl: document.getElementById('scoDl').value.trim(),
    non_sco_cc: toLines('nonScoCc'),
  };

  const status = document.getElementById('stakeholderStatus');
  try {
    const res = await fetch('/mir/stakeholders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    status.textContent = res.ok ? 'Saved!' : 'Save failed';
    setTimeout(() => (status.textContent = ''), 2000);
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  }
};

// ── Init ──────────────────────────────────────────────────────────────────────
checkHealth();
loadStakeholders();
