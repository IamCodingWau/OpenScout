// OpenScout Frontend Logic

let currentProfile = null;
let allEvents = [];

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  setupEventListeners();
});

async function initApp() {
  await Promise.all([
    checkAIStatus(),
    loadProfile(),
    loadFeedbackStats(),
    loadEvents(),
    loadNotificationCount()
  ]);
}

function setupEventListeners() {
  document.getElementById('sync-fetch-btn').addEventListener('click', handleFetchEvents);
  document.getElementById('run-ai-btn').addEventListener('click', handleRunAI);

  document.getElementById('filter-select').addEventListener('change', () => {
    renderEvents();
  });

  const modal = document.getElementById('profile-modal');
  document.getElementById('edit-profile-btn').addEventListener('click', () => {
    populateProfileModal();
    modal.classList.remove('hidden');
  });
  document.getElementById('close-modal-btn').addEventListener('click', () => {
    modal.classList.add('hidden');
  });
  document.getElementById('cancel-profile-btn').addEventListener('click', () => {
    modal.classList.add('hidden');
  });
  document.getElementById('profile-form').addEventListener('submit', handleSaveProfile);

  const thresholdRange = document.getElementById('profile-threshold');
  thresholdRange.addEventListener('input', (e) => {
    document.getElementById('threshold-preview').textContent = parseFloat(e.target.value).toFixed(2);
  });

  const notifModal = document.getElementById('notifications-modal');
  document.getElementById('view-notifications-btn').addEventListener('click', async () => {
    await renderNotifications();
    notifModal.classList.remove('hidden');
  });
  document.getElementById('close-notif-btn').addEventListener('click', () => {
    notifModal.classList.add('hidden');
  });
}

async function checkAIStatus() {
  const badge = document.getElementById('ai-status-badge');
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const ai = data.ai_engine;

    if (ai.available && ai.model_ready) {
      badge.className = 'badge badge-success';
      badge.innerHTML = '<span class="status-dot"></span> Ollama (' + escapeHtml(ai.model) + ') Online';
    } else if (ai.available && !ai.model_ready) {
      badge.className = 'badge badge-warning';
      badge.innerHTML = '<span class="status-dot"></span> Ollama Running (Pull ' + escapeHtml(ai.model) + ')';
      badge.title = ai.status;
    } else {
      badge.className = 'badge badge-warning';
      badge.innerHTML = '<span class="status-dot"></span> Open AI Fallback (' + escapeHtml(ai.model) + ')';
      badge.title = ai.status;
    }
  } catch (err) {
    badge.className = 'badge badge-danger';
    badge.innerHTML = '<span class="status-dot"></span> Offline';
  }
}

async function loadProfile() {
  try {
    const res = await fetch('/api/profile');
    if (!res.ok) return;
    currentProfile = await res.json();

    document.getElementById('profile-name-display').textContent = currentProfile.name;
    document.getElementById('threshold-val').textContent = Math.round(currentProfile.notification_threshold * 100) + '%';

    const interestsContainer = document.getElementById('interests-chips');
    interestsContainer.innerHTML = currentProfile.interests.map(i => '<span class="chip">' + escapeHtml(i) + '</span>').join('');

    const locationsContainer = document.getElementById('locations-chips');
    locationsContainer.innerHTML = currentProfile.locations.map(l => '<span class="chip location">📍 ' + escapeHtml(l) + '</span>').join('');
  } catch (err) {
    console.error('Failed to load profile', err);
  }
}

function populateProfileModal() {
  if (!currentProfile) return;
  document.getElementById('profile-name').value = currentProfile.name;
  document.getElementById('profile-interests').value = currentProfile.interests.join(', ');
  document.getElementById('profile-locations').value = currentProfile.locations.join(', ');
  document.getElementById('profile-threshold').value = currentProfile.notification_threshold;
  document.getElementById('threshold-preview').textContent = currentProfile.notification_threshold.toFixed(2);
}

async function handleSaveProfile(e) {
  e.preventDefault();
  const name = document.getElementById('profile-name').value.trim();
  const interests = document.getElementById('profile-interests').value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const locations = document.getElementById('profile-locations').value
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const threshold = parseFloat(document.getElementById('profile-threshold').value);

  try {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        interests,
        locations,
        notification_threshold: threshold
      })
    });
    if (res.ok) {
      document.getElementById('profile-modal').classList.add('hidden');
      await loadProfile();
      if (confirm('Preferences updated! Would you like to run AI Relevance Analysis now?')) {
        handleRunAI();
      }
    }
  } catch (err) {
    alert('Error saving profile: ' + err.message);
  }
}

async function loadFeedbackStats() {
  try {
    const res = await fetch('/api/feedback/stats');
    if (!res.ok) return;
    const stats = await res.json();
    document.getElementById('interested-count').textContent = stats.interested;
    document.getElementById('not-interested-count').textContent = stats.not_interested;
  } catch (err) {
    console.error('Failed to load feedback stats', err);
  }
}

async function submitFeedback(eventId, status) {
  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_id: eventId, status })
    });
    if (res.ok) {
      await loadFeedbackStats();
      await loadEvents();
    }
  } catch (err) {
    alert('Error recording feedback: ' + err.message);
  }
}

async function loadEvents() {
  try {
    const res = await fetch('/api/events');
    if (!res.ok) return;
    allEvents = await res.json();
    renderEvents();
  } catch (err) {
    console.error('Failed to load events', err);
  }
}

async function handleFetchEvents() {
  const btn = document.getElementById('sync-fetch-btn');
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '🔄 Fetching...';
  try {
    const res = await fetch('/api/events/fetch', { method: 'POST' });
    const data = await res.json();
    await loadEvents();
    alert(data.message);
  } catch (err) {
    alert('Failed to fetch events: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

async function handleRunAI() {
  const btn = document.getElementById('run-ai-btn');
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '✨ Analyzing with Open AI...';
  try {
    const res = await fetch('/api/events/analyze', { method: 'POST' });
    const data = await res.json();
    await loadEvents();
    await loadNotificationCount();
    alert(data.message + '\nNotifications sent: ' + data.notifications_sent);
  } catch (err) {
    alert('Failed to analyze events: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

function renderEvents() {
  const filter = document.getElementById('filter-select').value;
  const feed = document.getElementById('events-feed');
  const countLabel = document.getElementById('events-count');

  let filtered = allEvents;
  if (filter === 'interested') {
    filtered = allEvents.filter(e => e.feedback && e.feedback.status === 'interested');
  } else if (filter === 'not_interested') {
    filtered = allEvents.filter(e => e.feedback && e.feedback.status === 'not_interested');
  } else if (filter === 'unreviewed') {
    filtered = allEvents.filter(e => !e.feedback);
  }

  countLabel.textContent = 'Showing ' + filtered.length + ' of ' + allEvents.length + ' events';

  if (filtered.length === 0) {
    feed.innerHTML = '<div class="card" style="text-align: center; padding: 3rem;"><p style="font-size: 1.1rem; color: #94a3b8;">No events found matching this filter.</p><button onclick="handleFetchEvents()" class="btn btn-primary" style="margin-top: 1rem;">Fetch Events Now</button></div>';
    return;
  }

  feed.innerHTML = filtered.map(ev => {
    const rel = ev.relevance;
    const scorePct = rel ? Math.round(rel.relevance_score * 100) : null;
    
    let matchClass = 'low-match';
    let badgeClass = 'match-low';
    if (scorePct !== null) {
      if (scorePct >= 80) {
        matchClass = 'high-match';
        badgeClass = 'match-high';
      } else if (scorePct >= 50) {
        matchClass = 'medium-match';
        badgeClass = 'match-med';
      }
    }

    const currentFeedback = ev.feedback ? ev.feedback.status : null;

    let matchedChipsHtml = '';
    if (rel && rel.matched_interests && rel.matched_interests.length > 0) {
      matchedChipsHtml = '<div class="matched-tags-row"><span class="matched-label">Matched interests:</span>' +
        rel.matched_interests.map(tag => '<span class="matched-chip">✓ ' + escapeHtml(tag) + '</span>').join('') +
        '</div>';
    }

    let aiBoxHtml = '';
    if (rel) {
      aiBoxHtml = '<div class="ai-reason-box">' +
        '<div class="ai-reason-header"><span>Why this matches:</span><span style="font-size: 0.75rem; color: #94a3b8; font-family: monospace;">' + escapeHtml(rel.model_name) + '</span></div>' +
        '<p class="ai-reason-text">' + escapeHtml(rel.reason) + '</p>' +
        matchedChipsHtml +
        '</div>';
    }

    const scoreBadge = scorePct !== null
      ? '<span class="match-badge ' + badgeClass + '">Match: ' + scorePct + '%</span>'
      : '<span class="match-badge match-low">Pending AI</span>';

    return '<article class="event-card ' + matchClass + '">' +
      '<div class="event-header-row">' +
        '<div><h3 class="event-title">' + escapeHtml(ev.title) + '</h3></div>' +
        '<div>' + scoreBadge + '</div>' +
      '</div>' +
      '<div class="event-meta">' +
        '<span>📅 ' + escapeHtml(ev.date) + '</span>' +
        '<span>📍 ' + escapeHtml(ev.location) + '</span>' +
        '<span>' + (ev.is_online ? '🌐 Online' : '🏢 In-Person') + '</span>' +
        '<span class="source-tag ' + (ev.is_demo ? 'demo-tag' : 'live-tag') + '">' +
          (ev.is_demo ? 'Demo Event' : 'Fetched External Event') + ' (' + escapeHtml(ev.source) + ')' +
        '</span>' +
      '</div>' +
      '<p class="event-description">' + escapeHtml(ev.description) + '</p>' +
      aiBoxHtml +
      '<div class="event-footer-row">' +
        '<div class="feedback-actions">' +
          '<button onclick="submitFeedback(' + ev.id + ', \'interested\')" class="btn btn-sm ' + (currentFeedback === 'interested' ? 'btn-success' : 'btn-secondary') + '">' +
            (currentFeedback === 'interested' ? '✓ Interested' : 'Interested') +
          '</button>' +
          '<button onclick="submitFeedback(' + ev.id + ', \'not_interested\')" class="btn btn-sm ' + (currentFeedback === 'not_interested' ? 'btn-danger' : 'btn-secondary') + '">' +
            (currentFeedback === 'not_interested' ? '✕ Not Interested' : 'Not Interested') +
          '</button>' +
        '</div>' +
        '<div>' +
          '<a href="' + escapeHtml(ev.url) + '" target="_blank" rel="noopener" class="btn btn-sm btn-outline">View Event ↗</a>' +
        '</div>' +
      '</div>' +
    '</article>';
  }).join('');
}

async function loadNotificationCount() {
  try {
    const res = await fetch('/api/notifications');
    if (!res.ok) return;
    const logs = await res.json();
    document.getElementById('notif-count-badge').textContent = logs.length;
  } catch (err) {
    console.error('Failed to load notification count', err);
  }
}

async function renderNotifications() {
  const container = document.getElementById('notifications-list');
  try {
    const res = await fetch('/api/notifications');
    const logs = await res.json();

    if (logs.length === 0) {
      container.innerHTML = '<p class="text-muted" style="padding: 1rem;">No high-relevance notifications triggered yet.</p>';
      return;
    }

    container.innerHTML = logs.map(l => '<div class="notif-item">' +
      '<h4>' + escapeHtml(l.subject) + '</h4>' +
      '<div class="notif-meta">Sent to: ' + escapeHtml(l.recipient) + ' • Channel: ' + escapeHtml(l.channel) + ' • Date: ' + new Date(l.sent_at).toLocaleString() + '</div>' +
      '<pre class="notif-body">' + escapeHtml(l.message) + '</pre>' +
      '</div>'
    ).join('');
  } catch (err) {
    container.innerHTML = '<p class="text-danger">Failed to load notifications.</p>';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}