/**
 * MzansiBuilds App - Frontend Logic
 * Follows Separation of Concerns: UI rendering, navigation, and event handling.
 */

let currentUser = null;
let currentPage = 'home';
let feedCurrentPage = 1;
let feedCurrentStage = '';
let feedCurrentCategory = '';

// ===================== THEME =====================
(function initTheme() {
  const saved = localStorage.getItem('mzansi_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('mzansi_theme', next);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
}

// Update toggle icon on load
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? '☀️' : '🌙';
});

// ===================== MOBILE MENU =====================
function toggleMobileMenu() {
  const nav = document.getElementById('navbar-nav');
  const hamburger = document.getElementById('hamburger');
  nav.classList.toggle('open');
  hamburger.classList.toggle('active');
}

function closeMobileMenu() {
  const nav = document.getElementById('navbar-nav');
  const hamburger = document.getElementById('hamburger');
  if (nav) nav.classList.remove('open');
  if (hamburger) hamburger.classList.remove('active');
}

// Close mobile menu when a nav link is clicked
document.addEventListener('click', (e) => {
  if (e.target.closest('.navbar-nav a') || e.target.closest('.navbar-nav button:not(.theme-toggle)')) {
    closeMobileMenu();
  }
});

// ===================== NAVIGATION =====================
function navigate(page, data) {
  closeMobileMenu();
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.navbar-nav a').forEach(a => a.classList.remove('active'));

  const el = document.getElementById(`page-${page}`);
  if (el) {
    el.classList.add('active');
    currentPage = page;
    sessionStorage.setItem('mzansi_page', page);
    if (data) sessionStorage.setItem('mzansi_page_data', JSON.stringify(data));
    else sessionStorage.removeItem('mzansi_page_data');
  }

  const navLink = document.getElementById(`nav-${page}`);
  if (navLink) navLink.classList.add('active');

  window.scrollTo(0, 0);

  switch (page) {
    case 'home': loadHome(); break;
    case 'feed': loadFeed(); break;
    case 'profile': loadProfile(); break;
    case 'dashboard': loadDashboard(); break;
    case 'my-projects': loadMyProjects(); break;
    case 'new-project': openNewProjectModal(); navigate('my-projects'); break;
    case 'notifications': loadNotifications(); break;
    case 'celebration': loadCelebration(); break;
    case 'bookmarks': loadBookmarks(); break;
    case 'project': loadProjectDetail(data); break;
    case 'user': loadPublicProfile(data); break;
  }
}

// ===================== AUTH STATE =====================
function updateAuthUI() {
  const authLinks = document.getElementById('nav-auth-links');
  const userMenu = document.getElementById('nav-user-menu');
  const userBadge = document.getElementById('nav-user-badge');
  const logoutLi = document.getElementById('nav-logout-li');

  if (currentUser) {
    authLinks.style.display = 'none';
    userMenu.style.display = '';
    userBadge.style.display = '';
    logoutLi.style.display = '';
    const navAvatar = document.getElementById('nav-avatar');
    if (currentUser.avatar_url) {
      navAvatar.innerHTML = `<img src="${escapeHtml(currentUser.avatar_url)}" alt="avatar">`;
      navAvatar.style.background = 'none';
    } else {
      navAvatar.innerHTML = '';
      navAvatar.style.background = '';
      navAvatar.textContent = currentUser.username[0].toUpperCase();
    }
    document.getElementById('nav-username').textContent = currentUser.username;
  } else {
    authLinks.style.display = '';
    userMenu.style.display = 'none';
    userBadge.style.display = 'none';
    logoutLi.style.display = 'none';
  }
}

async function checkAuth() {
  if (api.isLoggedIn) {
    try {
      const data = await api.getMe();
      currentUser = data.user;
      updateAuthUI();
      refreshNotifBadge();
    } catch {
      api.token = null;
      currentUser = null;
      updateAuthUI();
    }
  }
}

function logout() {
  api.token = null;
  currentUser = null;
  updateAuthUI();
  navigate('home');
  showToast('Logged out successfully', 'success');
}

// ===================== REGISTER =====================
async function handleRegister(e) {
  e.preventDefault();
  const errEl = document.getElementById('register-error');
  errEl.classList.remove('show');

  const username = document.getElementById('reg-username').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const bio = document.getElementById('reg-bio').value.trim();

  try {
    const data = await api.register(username, email, password, bio);
    api.token = data.token;
    currentUser = data.user;
    updateAuthUI();
    showToast('Account created! Welcome to MzansiBuilds 🎉', 'success');
    navigate('dashboard');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

// ===================== LOGIN =====================
async function handleLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById('login-error');
  errEl.classList.remove('show');

  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const data = await api.login(email, password);
    api.token = data.token;
    currentUser = data.user;
    updateAuthUI();
    showToast('Welcome back! 👋', 'success');
    navigate('dashboard');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

// ===================== FORGOT PASSWORD =====================
let forgotEmail = '';

async function handleForgotPassword(e) {
  e.preventDefault();
  const errEl = document.getElementById('forgot-error');
  const successEl = document.getElementById('forgot-success');
  errEl.classList.remove('show');
  successEl.classList.remove('show');

  forgotEmail = document.getElementById('forgot-email').value.trim();

  try {
    const data = await api.forgotPassword(forgotEmail);
    // Show the code directly (no email service)
    successEl.textContent = `Your reset code is: ${data.reset_code} (valid for 15 minutes)`;
    successEl.classList.add('show');
    document.getElementById('forgot-step1').style.display = 'none';
    document.getElementById('forgot-step2').style.display = 'block';
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

async function handleResetPassword(e) {
  e.preventDefault();
  const errEl = document.getElementById('forgot-error');
  errEl.classList.remove('show');

  const code = document.getElementById('reset-code').value.trim();
  const newPassword = document.getElementById('reset-new-password').value;
  const confirmPassword = document.getElementById('reset-confirm-password').value;

  if (newPassword !== confirmPassword) {
    errEl.textContent = 'Passwords do not match';
    errEl.classList.add('show');
    return;
  }

  try {
    await api.resetPassword(forgotEmail, code, newPassword);
    showToast('Password reset successful! 🔓', 'success');
    // Reset the form state
    document.getElementById('forgot-step1').style.display = 'block';
    document.getElementById('forgot-step2').style.display = 'none';
    document.getElementById('forgot-success').classList.remove('show');
    navigate('login');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

// ===================== HOME =====================
async function loadHome() {
  try {
    const [feedData, celebData] = await Promise.all([
      api.getProjects(1),
      api.getCelebrationWall()
    ]);

    document.getElementById('stat-projects').textContent = feedData.total || 0;
    document.getElementById('stat-completed').textContent = celebData.projects?.length || 0;

    // Count unique builders
    const builders = new Set();
    const allProjects = [...(feedData.projects || []), ...(celebData.projects || [])];
    allProjects.forEach(p => { if (p.owner) builders.add(p.owner.id); });
    document.getElementById('stat-builders').textContent = builders.size;

    // Count collabs
    let totalCollabs = 0;
    allProjects.forEach(p => totalCollabs += (p.collab_count || 0));
    document.getElementById('stat-collabs').textContent = totalCollabs;

    // Render latest
    const container = document.getElementById('home-latest-projects');
    const latest = (feedData.projects || []).slice(0, 6);
    if (latest.length === 0) {
      container.innerHTML = `<div class="empty-state"><div class="icon">🏗️</div><h3>No projects yet</h3><p>Be the first to start building!</p></div>`;
    } else {
      container.innerHTML = latest.map(p => renderProjectCard(p)).join('');
    }
  } catch {
    // silently fail for home page stats
  }
}

// ===================== FEED =====================
let feedSearchQuery = '';
let _feedSearchTimer = null;

function debounceSearch() {
  clearTimeout(_feedSearchTimer);
  _feedSearchTimer = setTimeout(() => {
    feedSearchQuery = document.getElementById('feed-search').value.trim();
    loadFeed(1);
  }, 300);
}

async function loadFeed(page = 1) {
  feedCurrentPage = page;
  const list = document.getElementById('feed-list');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const data = await api.getFeed(page, feedCurrentStage, feedSearchQuery, feedCurrentCategory);
    if (!data.projects || data.projects.length === 0) {
      const msg = feedSearchQuery
        ? `No results for "${escapeHtml(feedSearchQuery)}"`
        : 'No projects found';
      list.innerHTML = `<div class="empty-state"><div class="icon">🔍</div><h3>${msg}</h3><p>Try a different search or filter.</p></div>`;
    } else {
      list.innerHTML = data.projects.map(p => renderProjectCard(p, true)).join('');
    }

    // Pagination
    const pagDiv = document.getElementById('feed-pagination');
    if (data.pages > 1) {
      const total = data.total || 0;
      const from = (page - 1) * 20 + 1;
      const to = Math.min(page * 20, total);
      let html = `<div class="pagination-info">${from}–${to} of ${total} projects</div>`;
      html += '<div class="pagination-btns">';

      // Prev
      html += `<button class="pagination-btn ${page === 1 ? 'disabled' : ''}" ${page > 1 ? `onclick="loadFeed(${page - 1})"` : ''}>← Prev</button>`;

      // Page numbers with ellipsis
      const pages = data.pages;
      const range = [];
      range.push(1);
      if (page > 3) range.push('...');
      for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) range.push(i);
      if (page < pages - 2) range.push('...');
      if (pages > 1) range.push(pages);

      range.forEach(r => {
        if (r === '...') {
          html += '<span class="pagination-ellipsis">…</span>';
        } else {
          html += `<button class="pagination-btn ${r === page ? 'active' : ''}" onclick="loadFeed(${r})">${r}</button>`;
        }
      });

      // Next
      html += `<button class="pagination-btn ${page === pages ? 'disabled' : ''}" ${page < pages ? `onclick="loadFeed(${page + 1})"` : ''}>Next →</button>`;
      html += '</div>';
      pagDiv.innerHTML = html;
    } else {
      pagDiv.innerHTML = '';
    }
  } catch {
    list.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading feed</h3></div>';
  }
}

function filterFeed(stage) {
  feedCurrentStage = stage;
  document.querySelectorAll('#feed-filters .filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  loadFeed(1);
}

function filterCategory(cat) {
  feedCurrentCategory = cat;
  document.querySelectorAll('#feed-category-filters .filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  loadFeed(1);
}

// ===================== DASHBOARD =====================
async function loadDashboard() {
  if (!currentUser) { navigate('login'); return; }

  const list = document.getElementById('my-projects-list');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const data = await api.getMyProjects();
    const projects = data.projects || [];

    document.getElementById('dash-total').textContent = projects.length;
    document.getElementById('dash-active').textContent = projects.filter(p => !p.is_completed).length;
    document.getElementById('dash-done').textContent = projects.filter(p => p.is_completed).length;

    if (projects.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="icon">🚀</div>
          <h3>No projects yet</h3>
          <p>Start your first build-in-public journey!</p>
          <button class="btn btn-primary" onclick="openNewProjectModal()">+ New Project</button>
        </div>`;
    } else {
      list.innerHTML = projects.map(p => renderMyProjectCard(p)).join('');
    }
  } catch {
    list.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading projects</h3></div>';
  }
}

// ===================== MY PROJECTS =====================
async function loadMyProjects() {
  if (!currentUser) { navigate('login'); return; }

  const list = document.getElementById('my-projects-page-list');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const data = await api.getMyProjects();
    const projects = data.projects || [];

    if (projects.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="icon">🚀</div>
          <h3>No projects yet</h3>
          <p>Start your first build-in-public journey!</p>
          <button class="btn btn-primary" onclick="openNewProjectModal()">+ New Project</button>
        </div>`;
    } else {
      list.innerHTML = projects.map(p => renderMyProjectCard(p)).join('');
    }
  } catch {
    list.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading projects</h3></div>';
  }
}

// ===================== PROJECT DETAIL =====================
async function loadProjectDetail(projectId) {
  if (!projectId) return;
  const container = document.getElementById('project-detail-content');
  container.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const [projData, msData, commentData, collabData, actData] = await Promise.all([
      api.getProject(projectId),
      api.getMilestones(projectId),
      api.getComments(projectId),
      api.getCollabs(projectId),
      api.getActivities(projectId)
    ]);

    const p = projData.project;
    const milestones = msData.milestones || [];
    const comments = commentData.comments || [];
    const collabs = collabData.collaborations || [];
    const activities = actData.activities || [];
    const isOwner = currentUser && currentUser.id === p.owner_id;

    const achievedCount = milestones.filter(m => m.is_achieved).length;
    const progress = milestones.length > 0 ? Math.round((achievedCount / milestones.length) * 100) : 0;

    container.innerHTML = `
      <button class="btn btn-ghost" onclick="navigate('feed')" style="margin-bottom:1rem;">← Back to Feed</button>

      <div class="card">
        <div class="project-detail-header">
          <div>
            <h2 style="font-size:1.5rem;font-weight:800;margin-bottom:0.5rem;">${escapeHtml(p.title)}</h2>
            <div class="project-meta">
              <span>${stageBadge(p.stage)} ${categoryBadge(p.category)}</span>
              ${p.owner ? `<span>by <strong style="cursor:pointer;" onclick="navigate('user', ${p.owner.id})">${escapeHtml(p.owner.username)}</strong></span>` : ''}
              <span>📅 ${formatDate(p.created_at)}</span>
              ${p.tech_stack ? `<div class="tech-tags" style="margin-top:0.25rem;">${p.tech_stack.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="tech-tag" onclick="searchByTag('${escapeHtml(t)}')">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
            </div>
          </div>
          <div style="display:flex;gap:0.5rem;">
            ${currentUser ? `<button class="btn btn-sm like-btn" id="like-btn-${p.id}" onclick="toggleLike(${p.id})">❤️ <span id="like-count-${p.id}">${p.like_count || 0}</span></button>` : `<span class="btn btn-sm btn-ghost" style="cursor:default;">❤️ ${p.like_count || 0}</span>`}
            ${currentUser ? `<button class="btn btn-sm bookmark-btn" id="bookmark-btn-${p.id}" onclick="toggleBookmark(${p.id})">🔖</button>` : ''}
            ${!isOwner && currentUser ? `<button class="btn btn-primary btn-sm" onclick="openCollabModal(${p.id})">🤝 Collaborate</button>` : ''}
            ${isOwner ? `
              <button class="btn btn-outline btn-sm" onclick="openEditProjectModal(${p.id})">✏️ Edit</button>
              <button class="btn btn-danger btn-sm" onclick="confirmDeleteProject(${p.id})">🗑️</button>
            ` : ''}
          </div>
        </div>

        <div class="card-body">
          <p style="white-space:pre-wrap;">${escapeHtml(p.description)}</p>
          ${p.repo_url ? `<p style="margin-top:0.75rem;"><strong>Repository:</strong> <a href="${escapeHtml(p.repo_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(p.repo_url)}</a></p>` : ''}
          ${p.support_needed ? `<p style="margin-top:0.75rem;"><strong>🙏 Support needed:</strong> ${escapeHtml(p.support_needed)}</p>` : ''}
        </div>
      </div>

      <!-- Milestones -->
      <div class="card" style="margin-top:1rem;">
        <div class="flex-between" style="margin-bottom:1rem;">
          <h3>📍 Milestones & Progress</h3>
          ${isOwner ? `<button class="btn btn-sm btn-outline" onclick="openMilestoneModal(${p.id})">+ Add Milestone</button>` : ''}
        </div>
        ${milestones.length > 0 ? `
          <div style="margin-bottom:1rem;">
            <div class="flex-between" style="margin-bottom:0.25rem;">
              <small>${achievedCount} / ${milestones.length} milestones</small>
              <small>${progress}%</small>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div>
          </div>
          ${milestones.map(m => `
            <div class="milestone-item">
              <div class="milestone-check ${m.is_achieved ? 'achieved' : ''}" 
                   ${isOwner && !m.is_achieved ? `onclick="toggleMilestone(${p.id}, ${m.id})" title="Mark as achieved"` : ''}
                   ${m.is_achieved ? 'title="Achieved!"' : ''}>
                ${m.is_achieved ? '✓' : ''}
              </div>
              <div class="milestone-info">
                <h4 class="${m.is_achieved ? 'achieved-text' : ''}">${escapeHtml(m.title)}</h4>
                ${m.description ? `<p>${escapeHtml(m.description)}</p>` : ''}
                ${m.achieved_at ? `<p style="color:var(--primary);font-size:0.75rem;">✅ Achieved ${formatDate(m.achieved_at)}</p>` : ''}
              </div>
            </div>
          `).join('')}
        ` : '<div class="empty-state" style="padding:1.5rem;"><p>No milestones yet</p></div>'}
      </div>

      <!-- Comments -->
      <div class="card" style="margin-top:1rem;">
        <h3 style="margin-bottom:0.5rem;">💬 Comments (${comments.length})</h3>
        <div class="comment-list" id="comments-${p.id}">
          ${comments.length > 0 ? comments.map(c => renderComment(c)).join('') : '<p style="color:var(--gray-400);padding:1rem 0;text-align:center;font-size:0.9rem;">No comments yet. Be the first!</p>'}
        </div>
        ${currentUser ? `
          <div class="comment-form">
            <input type="text" class="form-control" id="comment-input-${p.id}" placeholder="Write a comment..." onkeydown="if(event.key==='Enter')postComment(${p.id})">
            <button class="btn btn-primary btn-sm" onclick="postComment(${p.id})">Send</button>
          </div>
        ` : '<p style="font-size:0.85rem;color:var(--gray-400);margin-top:0.75rem;">Login to comment</p>'}
      </div>

      <!-- Collaborations -->
      <div class="card" style="margin-top:1rem;">
        <h3 style="margin-bottom:0.5rem;">🤝 Collaboration Requests (${collabs.length})</h3>
        ${collabs.length > 0 ? collabs.map(c => `
          <div class="collab-item">
            <div class="collab-info">
              <div class="user-avatar" style="cursor:pointer;" onclick="navigate('user', ${c.requester ? c.requester.id : 0})">${c.requester ? c.requester.username[0].toUpperCase() : '?'}</div>
              <div>
                <strong style="cursor:pointer;" onclick="navigate('user', ${c.requester ? c.requester.id : 0})">${c.requester ? escapeHtml(c.requester.username) : 'Unknown'}</strong>
                ${c.message ? `<p style="font-size:0.85rem;color:var(--gray-500);">${escapeHtml(c.message)}</p>` : ''}
                <span class="badge ${c.status === 'accepted' ? 'badge-completed' : c.status === 'declined' ? 'badge-idea' : 'badge-in-progress'}">${c.status}</span>
              </div>
            </div>
            ${isOwner && c.status === 'pending' ? `
              <div class="collab-actions">
                <button class="btn btn-sm btn-primary" onclick="respondCollab(${c.id}, 'accepted')">Accept</button>
                <button class="btn btn-sm btn-danger" onclick="respondCollab(${c.id}, 'declined')">Decline</button>
              </div>
            ` : ''}
          </div>
        `).join('') : '<p style="color:var(--gray-400);padding:1rem 0;text-align:center;font-size:0.9rem;">No collaboration requests yet</p>'}
      </div>

      <!-- Activity Timeline -->
      <div class="card" style="margin-top:1rem;">
        <h3 style="margin-bottom:1rem;">📋 Activity Timeline</h3>
        ${activities.length > 0 ? `
          <div class="activity-timeline">
            ${activities.map(a => {
              const icon = {created:'🚀', stage_change:'🔄', milestone_added:'📌', milestone_achieved:'✅', comment:'💬', collaboration:'🤝'}[a.type] || '📝';
              return `
                <div class="timeline-item">
                  <div class="timeline-dot">${icon}</div>
                  <div class="timeline-content">
                    <p class="timeline-message">${escapeHtml(a.message)}</p>
                    ${a.detail ? `<p class="timeline-detail">${escapeHtml(a.detail)}</p>` : ''}
                    <span class="timeline-date">${formatDate(a.created_at)}</span>
                  </div>
                </div>`;
            }).join('')}
          </div>
        ` : '<p style="color:var(--gray-400);padding:1rem 0;text-align:center;font-size:0.9rem;">No activity yet</p>'}
      </div>
    `;

    // Check if current user has liked/bookmarked this project
    checkLikeStatus(p.id);
    checkBookmarkStatus(p.id);
  } catch {
    container.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading project</h3></div>';
  }
}

// ===================== CELEBRATION WALL =====================
async function loadCelebration() {
  const list = document.getElementById('celebration-list');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const data = await api.getCelebrationWall();
    const projects = data.projects || [];

    if (projects.length === 0) {
      list.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><div class="icon">🏆</div><h3>No completed projects yet</h3><p>Complete your project to be featured here!</p></div>`;
    } else {
      list.innerHTML = projects.map(p => `
        <div class="celebration-card card" onclick="navigate('project', ${p.id})" style="cursor:pointer;">
          <div class="celebration-user">
            <div class="celebration-avatar" style="overflow:hidden;cursor:pointer;" onclick="event.stopPropagation();navigate('user', ${p.owner ? p.owner.id : 0})">${p.owner ? (p.owner.avatar_url ? `<img src="${escapeHtml(p.owner.avatar_url)}" alt="avatar">` : p.owner.username[0].toUpperCase()) : '?'}</div>
            <div>
              <div class="celebration-name" style="cursor:pointer;" onclick="event.stopPropagation();navigate('user', ${p.owner ? p.owner.id : 0})">${p.owner ? escapeHtml(p.owner.username) : 'Unknown'}</div>
              <div class="celebration-date">Completed ${formatDate(p.completed_at)}</div>
            </div>
          </div>
          <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">${escapeHtml(p.title)}</h3>
          <p style="color:var(--gray-600);font-size:0.9rem;line-height:1.5;">${escapeHtml(truncate(p.description, 120))}</p>
          ${p.tech_stack ? `<div class="tech-tags" style="margin-top:0.75rem;">${p.tech_stack.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="tech-tag" onclick="event.stopPropagation();searchByTag('${escapeHtml(t)}')">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
          <div style="margin-top:0.75rem;">
            <span class="badge badge-completed">✅ Completed</span>
            <span style="font-size:0.8rem;color:var(--gray-400);margin-left:0.5rem;">${p.milestone_count || 0} milestones</span>
          </div>
        </div>
      `).join('');
    }
  } catch {
    list.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading celebration wall</h3></div>';
  }
}

// ===================== PROJECT CARDS =====================
function renderProjectCard(p, showFull = false) {
  return `
    <div class="card" onclick="navigate('project', ${p.id})" style="cursor:pointer;">
      <div class="card-header">
        <h3>${escapeHtml(p.title)}</h3>
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap;">
          ${stageBadge(p.stage)}
          ${categoryBadge(p.category)}
        </div>
      </div>
      <div class="card-body">
        <p>${escapeHtml(truncate(p.description, showFull ? 150 : 100))}</p>
        ${p.tech_stack ? `<div class="tech-tags">${p.tech_stack.split(',').map(t => t.trim()).filter(Boolean).map(t => `<span class="tech-tag" onclick="event.stopPropagation();searchByTag('${escapeHtml(t)}')">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
        ${p.support_needed ? `<p style="margin-top:0.5rem;font-size:0.8rem;color:var(--warning);">🙏 ${escapeHtml(truncate(p.support_needed, 80))}</p>` : ''}
        ${stageProgress(p.stage)}
      </div>
      <div class="card-footer">
        ${p.owner ? `
          <div style="display:flex;align-items:center;gap:0.4rem;cursor:pointer;" onclick="event.stopPropagation();navigate('user', ${p.owner.id})">
            <div class="user-avatar" style="width:24px;height:24px;font-size:0.65rem;overflow:hidden;">${p.owner.avatar_url ? `<img src="${escapeHtml(p.owner.avatar_url)}" alt="avatar">` : p.owner.username[0].toUpperCase()}</div>
            <span style="font-size:0.8rem;font-weight:500;">${escapeHtml(p.owner.username)}</span>
          </div>
        ` : ''}
        <span style="font-size:0.8rem;color:var(--gray-400);">💬 ${p.comment_count || 0}</span>
        <span style="font-size:0.8rem;color:var(--gray-400);">🤝 ${p.collab_count || 0}</span>
        <span class="like-count-badge" style="font-size:0.8rem;color:var(--gray-400);">❤️ ${p.like_count || 0}</span>
        <span style="font-size:0.8rem;color:var(--gray-400);margin-left:auto;">📅 ${formatDate(p.created_at)}</span>
      </div>
    </div>
  `;
}

function renderMyProjectCard(p) {
  const milestoneProgress = p.milestone_count > 0 ? `${p.milestone_count} milestones` : 'No milestones';
  return `
    <div class="card">
      <div class="card-header">
        <div>
          <h3 style="cursor:pointer;" onclick="navigate('project', ${p.id})">${escapeHtml(p.title)}</h3>
          <p style="font-size:0.85rem;color:var(--gray-500);margin-top:0.25rem;">Updated ${formatDate(p.updated_at)}</p>
        </div>
        <div style="display:flex;gap:0.5rem;align-items:center;">
          ${stageBadge(p.stage)}
        </div>
      </div>
      <div class="card-body">
        <p>${escapeHtml(truncate(p.description, 120))}</p>
        ${stageProgress(p.stage)}
      </div>
      <div class="card-footer">
        <span style="font-size:0.8rem;color:var(--gray-400);">📍 ${milestoneProgress}</span>
        <span style="font-size:0.8rem;color:var(--gray-400);">💬 ${p.comment_count || 0}</span>
        <div style="margin-left:auto;display:flex;gap:0.5rem;">
          <button class="btn btn-sm btn-outline" onclick="event.stopPropagation();navigate('project', ${p.id})">View</button>
          <button class="btn btn-sm btn-primary" onclick="event.stopPropagation();openEditProjectModal(${p.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();confirmDeleteProject(${p.id})">Delete</button>
        </div>
      </div>
    </div>
  `;
}

function renderComment(c) {
  return `
    <div class="comment-item">
      <div class="user-avatar" style="width:32px;height:32px;font-size:0.75rem;flex-shrink:0;cursor:pointer;overflow:hidden;" onclick="navigate('user', ${c.author ? c.author.id : 0})">
        ${c.author ? (c.author.avatar_url ? `<img src="${escapeHtml(c.author.avatar_url)}" alt="avatar">` : c.author.username[0].toUpperCase()) : '?'}
      </div>
      <div class="comment-content">
        <span class="comment-author" style="cursor:pointer;" onclick="navigate('user', ${c.author ? c.author.id : 0})">${c.author ? escapeHtml(c.author.username) : 'Unknown'}</span>
        <span class="comment-time">${formatDate(c.created_at)}</span>
        <p class="comment-text">${escapeHtml(c.content)}</p>
      </div>
    </div>
  `;
}

// ===================== MODALS =====================
// ===================== PUBLIC PROFILE =====================
async function loadPublicProfile(userId) {
  if (!userId) { navigate('feed'); return; }

  // If viewing own profile, go to editable profile page
  if (currentUser && currentUser.id === userId) { navigate('profile'); return; }

  const list = document.getElementById('pub-projects-list');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const data = await api.getPublicProfile(userId);
    const u = data.user;
    const projects = data.projects || [];

    const avatar = document.getElementById('pub-avatar');
    if (u.avatar_url) {
      avatar.innerHTML = `<img src="${escapeHtml(u.avatar_url)}" alt="avatar">`;
      avatar.style.background = 'none';
    } else {
      avatar.innerHTML = '';
      avatar.style.background = '';
      avatar.textContent = u.username[0].toUpperCase();
    }
    document.getElementById('pub-display-name').textContent = u.username;
    document.getElementById('pub-display-joined').textContent = 'Member since ' + formatDate(u.created_at);
    document.getElementById('pub-display-bio').textContent = u.bio || 'No bio yet.';
    document.getElementById('pub-stat-projects').textContent = projects.length;
    document.getElementById('pub-stat-completed').textContent = projects.filter(p => p.stage === 'completed').length;

    if (projects.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="icon">📭</div><h3>No projects yet</h3></div>';
    } else {
      list.innerHTML = projects.map(p => {
        // Add owner info so renderProjectCard works
        p.owner = u;
        return renderProjectCard(p, true);
      }).join('');
    }
  } catch (err) {
    list.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><h3>${escapeHtml(err.message || 'User not found')}</h3></div>`;
  }
}

// ===================== TECH TAG INPUT =====================
let _currentTags = [];

function setTechTags(tags) {
  _currentTags = [...tags];
  renderTagInput();
}

function getTechTags() {
  return [..._currentTags];
}

function renderTagInput() {
  const container = document.getElementById('pm-techstack-tags');
  container.innerHTML = _currentTags.map((tag, i) =>
    `<span class="tag-input-tag">${escapeHtml(tag)}<span class="tag-remove" onclick="removeTag(${i})">&times;</span></span>`
  ).join('');
}

function addTag(text) {
  const tag = text.trim();
  if (tag && !_currentTags.some(t => t.toLowerCase() === tag.toLowerCase())) {
    _currentTags.push(tag);
    renderTagInput();
  }
}

function removeTag(index) {
  _currentTags.splice(index, 1);
  renderTagInput();
}

function handleTagKeydown(e) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault();
    const input = document.getElementById('pm-techstack');
    addTag(input.value.replace(',', ''));
    input.value = '';
  } else if (e.key === 'Backspace' && !e.target.value && _currentTags.length) {
    _currentTags.pop();
    renderTagInput();
  }
}

function searchByTag(tag) {
  navigate('feed');
  setTimeout(() => {
    const searchInput = document.getElementById('feed-search');
    searchInput.value = tag;
    feedSearchQuery = tag;
    loadFeed(1);
  }, 50);
}

// ===================== PROJECT MODALS =====================
function openNewProjectModal() {
  if (!currentUser) { navigate('login'); return; }
  document.getElementById('project-modal-title').textContent = 'New Project';
  document.getElementById('pm-submit-btn').textContent = 'Create Project';
  document.getElementById('pm-id').value = '';
  document.getElementById('pm-title').value = '';
  document.getElementById('pm-description').value = '';
  document.getElementById('pm-techstack').value = '';
  setTechTags([]);
  document.getElementById('pm-repo').value = '';
  document.getElementById('pm-category').value = '';
  document.getElementById('pm-stage').value = 'idea';
  document.getElementById('pm-support').value = '';
  document.getElementById('project-modal-error').classList.remove('show');
  document.getElementById('project-modal').classList.add('show');
}

async function openEditProjectModal(projectId) {
  try {
    const data = await api.getProject(projectId);
    const p = data.project;
    document.getElementById('project-modal-title').textContent = 'Edit Project';
    document.getElementById('pm-submit-btn').textContent = 'Update Project';
    document.getElementById('pm-id').value = p.id;
    document.getElementById('pm-title').value = p.title;
    document.getElementById('pm-description').value = p.description;
    document.getElementById('pm-techstack').value = '';
    setTechTags(p.tech_stack ? p.tech_stack.split(',').map(t => t.trim()).filter(Boolean) : []);
    document.getElementById('pm-repo').value = p.repo_url || '';
    document.getElementById('pm-category').value = p.category || '';
    document.getElementById('pm-stage').value = p.stage;
    document.getElementById('pm-support').value = p.support_needed || '';
    document.getElementById('project-modal-error').classList.remove('show');
    document.getElementById('project-modal').classList.add('show');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function closeProjectModal() {
  document.getElementById('project-modal').classList.remove('show');
}

async function handleProjectSubmit(e) {
  e.preventDefault();
  const errEl = document.getElementById('project-modal-error');
  errEl.classList.remove('show');

  const id = document.getElementById('pm-id').value;
  const payload = {
    title: document.getElementById('pm-title').value.trim(),
    description: document.getElementById('pm-description').value.trim(),
    tech_stack: getTechTags().join(', '),
    repo_url: document.getElementById('pm-repo').value.trim(),
    category: document.getElementById('pm-category').value,
    stage: document.getElementById('pm-stage').value,
    support_needed: document.getElementById('pm-support').value.trim()
  };

  try {
    if (id) {
      await api.updateProject(id, payload);
      showToast('Project updated!', 'success');
    } else {
      await api.createProject(payload);
      showToast('Project created! 🚀', 'success');
    }
    closeProjectModal();
    if (currentPage === 'dashboard') loadDashboard();
    else if (currentPage === 'project') loadProjectDetail(id);
    else if (currentPage === 'feed') loadFeed(feedCurrentPage);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

async function confirmDeleteProject(projectId) {
  if (!confirm('Are you sure you want to delete this project?')) return;
  try {
    await api.deleteProject(projectId);
    showToast('Project deleted', 'success');
    if (currentPage === 'dashboard') loadDashboard();
    else navigate('feed');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Milestone Modal
function openMilestoneModal(projectId) {
  document.getElementById('ms-project-id').value = projectId;
  document.getElementById('ms-title').value = '';
  document.getElementById('ms-description').value = '';
  document.getElementById('milestone-modal').classList.add('show');
}

function closeMilestoneModal() {
  document.getElementById('milestone-modal').classList.remove('show');
}

async function handleMilestoneSubmit(e) {
  e.preventDefault();
  const projectId = document.getElementById('ms-project-id').value;
  const title = document.getElementById('ms-title').value.trim();
  const description = document.getElementById('ms-description').value.trim();

  try {
    await api.addMilestone(projectId, { title, description });
    showToast('Milestone added! 📍', 'success');
    closeMilestoneModal();
    loadProjectDetail(projectId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function toggleMilestone(projectId, milestoneId) {
  try {
    await api.updateMilestone(projectId, milestoneId, { is_achieved: true });
    showToast('Milestone achieved! 🎯', 'success');
    loadProjectDetail(projectId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Collab Modal
function openCollabModal(projectId) {
  if (!currentUser) { navigate('login'); return; }
  document.getElementById('collab-project-id').value = projectId;
  document.getElementById('collab-message').value = '';
  document.getElementById('collab-modal').classList.add('show');
}

function closeCollabModal() {
  document.getElementById('collab-modal').classList.remove('show');
}

async function handleCollabSubmit(e) {
  e.preventDefault();
  const projectId = document.getElementById('collab-project-id').value;
  const message = document.getElementById('collab-message').value.trim();

  try {
    await api.requestCollab(projectId, message);
    showToast('Collaboration requested! 🤝', 'success');
    closeCollabModal();
    loadProjectDetail(projectId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function respondCollab(collabId, status) {
  try {
    const data = await api.respondCollab(collabId, status);
    showToast(`Request ${status}!`, 'success');
    // Reload current project detail
    if (data.collaboration && data.collaboration.project_id) {
      loadProjectDetail(data.collaboration.project_id);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Comment
async function postComment(projectId) {
  const input = document.getElementById(`comment-input-${projectId}`);
  const content = input.value.trim();
  if (!content) return;

  try {
    await api.addComment(projectId, content);
    input.value = '';
    loadProjectDetail(projectId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Like
async function toggleLike(projectId) {
  if (!currentUser) { navigate('login'); return; }
  try {
    const data = await api.toggleLike(projectId);
    const btn = document.getElementById(`like-btn-${projectId}`);
    const countEl = document.getElementById(`like-count-${projectId}`);
    if (countEl) countEl.textContent = data.like_count;
    if (btn) {
      btn.classList.toggle('liked', data.liked);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function checkLikeStatus(projectId) {
  if (!currentUser) return;
  try {
    const data = await api.getLikeStatus(projectId);
    const btn = document.getElementById(`like-btn-${projectId}`);
    if (btn && data.liked) {
      btn.classList.add('liked');
    }
  } catch {
    // ignore - user may not be logged in
  }
}

// Bookmark
async function toggleBookmark(projectId) {
  if (!currentUser) { navigate('login'); return; }
  try {
    const data = await api.toggleBookmark(projectId);
    const btn = document.getElementById(`bookmark-btn-${projectId}`);
    if (btn) {
      btn.classList.toggle('bookmarked', data.bookmarked);
    }
    showToast(data.bookmarked ? 'Project saved!' : 'Bookmark removed', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function checkBookmarkStatus(projectId) {
  if (!currentUser) return;
  try {
    const data = await api.getBookmarkStatus(projectId);
    const btn = document.getElementById(`bookmark-btn-${projectId}`);
    if (btn && data.bookmarked) {
      btn.classList.add('bookmarked');
    }
  } catch {
    // ignore
  }
}

async function loadBookmarks() {
  const list = document.getElementById('bookmarks-list');
  const empty = document.getElementById('bookmarks-empty');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';
  empty.style.display = 'none';
  try {
    const data = await api.getMyBookmarks();
    const bookmarks = data.bookmarks || [];
    if (bookmarks.length === 0) {
      list.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    list.innerHTML = bookmarks.map(b => {
      const p = b.project;
      return `
        <div class="card project-card" onclick="navigate('project', ${p.id})" style="cursor:pointer;">
          <div class="card-body">
            <h3>${escapeHtml(p.title)}</h3>
            <p class="text-muted">${escapeHtml((p.description || '').substring(0, 120))}${(p.description || '').length > 120 ? '...' : ''}</p>
            <div class="project-meta" style="margin-top:0.5rem;">
              ${stageBadge(p.stage)} ${categoryBadge(p.category)}
              ${p.owner ? `<span>by <strong>${escapeHtml(p.owner.username)}</strong></span>` : ''}
            </div>
          </div>
          <div class="card-footer">
            <span>❤️ ${p.like_count || 0}</span>
            <span>🔖 Saved ${formatDate(b.created_at)}</span>
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    list.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading bookmarks</h3></div>';
  }
}

// ===================== SUPPORT =====================
function openSupportModal() {
  if (!currentUser) { navigate('login'); return; }
  document.getElementById('support-category').value = '';
  document.getElementById('support-subject').value = '';
  document.getElementById('support-description').value = '';
  document.getElementById('support-priority').value = 'medium';
  document.getElementById('support-success').classList.remove('show');
  document.getElementById('support-error').classList.remove('show');
  document.getElementById('support-modal').classList.add('show');
}

function closeSupportModal() {
  document.getElementById('support-modal').classList.remove('show');
}

async function handleSupportSubmit(e) {
  e.preventDefault();
  const errEl = document.getElementById('support-error');
  const successEl = document.getElementById('support-success');
  errEl.classList.remove('show');
  successEl.classList.remove('show');

  const category = document.getElementById('support-category').value;
  const subject = document.getElementById('support-subject').value.trim();
  const description = document.getElementById('support-description').value.trim();
  const priority = document.getElementById('support-priority').value;

  try {
    await api.submitSupport(category, subject, description, priority);
    successEl.textContent = 'Report submitted successfully! We will review it shortly.';
    successEl.classList.add('show');
    document.getElementById('support-category').value = '';
    document.getElementById('support-subject').value = '';
    document.getElementById('support-description').value = '';
    document.getElementById('support-priority').value = 'medium';
    showToast('Support report submitted! 📧', 'success');
    setTimeout(() => closeSupportModal(), 2000);
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add('show');
  }
}

// ===================== NOTIFICATIONS =====================
async function refreshNotifBadge() {
  if (!currentUser) return;
  try {
    const data = await api.getNotifications();
    const badge = document.getElementById('notif-badge');
    if (data.unread_count > 0) {
      badge.textContent = data.unread_count;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  } catch {
    // silently fail
  }
}

// ===================== PROFILE =====================
function renderAvatar(el, user, size) {
  if (user.avatar_url) {
    el.innerHTML = `<img src="${escapeHtml(user.avatar_url)}" alt="avatar">`;
    el.style.background = 'none';
  } else {
    el.textContent = user.username[0].toUpperCase();
    el.style.background = '';
    const img = el.querySelector('img');
    if (img) img.remove();
  }
}

async function loadProfile() {
  if (!currentUser) { navigate('login'); return; }

  try {
    const data = await api.getMe();
    currentUser = data.user;
    updateAuthUI();

    const u = currentUser;
    renderAvatar(document.getElementById('profile-avatar'), u);
    document.getElementById('profile-display-name').textContent = u.username;
    document.getElementById('profile-display-email').textContent = u.email;
    document.getElementById('profile-display-joined').textContent = 'Member since ' + formatDate(u.created_at);
    document.getElementById('profile-display-bio').textContent = u.bio || 'No bio yet.';

    // Stats
    const pData = await api.getMyProjects();
    const projects = pData.projects || [];
    document.getElementById('profile-stat-projects').textContent = projects.length;
    document.getElementById('profile-stat-completed').textContent = projects.filter(p => p.stage === 'completed').length;
  } catch (err) {
    showToast(err.message || 'Failed to load profile', 'error');
  }
}

async function handleAvatarUpload(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  if (file.size > 2 * 1024 * 1024) {
    showToast('Image must be under 2MB', 'error');
    input.value = '';
    return;
  }
  try {
    showToast('Uploading...', 'success');
    const data = await api.uploadAvatar(file);
    currentUser = data.user;
    updateAuthUI();
    loadProfile();
    showToast('Profile picture updated!', 'success');
  } catch (err) {
    showToast(err.message || 'Upload failed', 'error');
  }
  input.value = '';
}

function openEditProfileModal() {
  document.getElementById('profile-modal-error').style.display = 'none';
  document.getElementById('profile-modal-success').style.display = 'none';
  document.getElementById('edit-username').value = currentUser.username || '';
  document.getElementById('edit-bio').value = currentUser.bio || '';
  document.getElementById('edit-avatar-file').value = '';
  renderAvatar(document.getElementById('edit-avatar-preview'), currentUser);
  document.getElementById('profile-modal').classList.add('show');
}

function closeEditProfileModal() {
  document.getElementById('profile-modal').classList.remove('show');
}

async function handleProfileUpdate(e) {
  e.preventDefault();
  const errEl = document.getElementById('profile-modal-error');
  const sucEl = document.getElementById('profile-modal-success');
  errEl.style.display = 'none';
  sucEl.style.display = 'none';

  try {
    // Upload avatar file if selected
    const fileInput = document.getElementById('edit-avatar-file');
    if (fileInput.files && fileInput.files[0]) {
      if (fileInput.files[0].size > 2 * 1024 * 1024) {
        errEl.textContent = 'Image must be under 2MB';
        errEl.style.display = 'block';
        return;
      }
      const uploadData = await api.uploadAvatar(fileInput.files[0]);
      currentUser = uploadData.user;
    }

    // Update text fields
    const payload = {
      username: document.getElementById('edit-username').value.trim(),
      bio: document.getElementById('edit-bio').value.trim()
    };
    const data = await api.updateProfile(payload);
    currentUser = data.user;
    updateAuthUI();
    sucEl.textContent = 'Profile updated!';
    sucEl.style.display = 'block';
    setTimeout(() => { closeEditProfileModal(); loadProfile(); }, 800);
  } catch (err) {
    errEl.textContent = err.message || 'Update failed';
    errEl.style.display = 'block';
  }
}

async function loadNotifications() {
  if (!currentUser) { navigate('login'); return; }

  const list = document.getElementById('notifications-list');
  list.innerHTML = '<div class="loading-center"><div class="spinner"></div></div>';

  try {
    const data = await api.getNotifications();
    const notifications = data.notifications || [];

    if (notifications.length === 0) {
      list.innerHTML = `<div class="empty-state"><div class="icon">🔔</div><h3>No notifications yet</h3><p>You'll be notified when someone comments on your project or requests to collaborate.</p></div>`;
    } else {
      list.innerHTML = notifications.map(n => {
        const icon = n.type === 'comment' ? '💬' : '🤝';
        const iconClass = n.type;
        const triggeredBy = n.triggered_by ? n.triggered_by.username[0].toUpperCase() : '?';
        return `
          <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="handleNotifClick(${n.id}, ${n.project_id})">
            <div class="notif-icon ${iconClass}">${icon}</div>
            <div style="flex:1;">
              <div class="notif-message">${escapeHtml(n.message)}</div>
              <div class="notif-time">${formatDate(n.created_at)}</div>
            </div>
            ${!n.is_read ? '<div style="width:8px;height:8px;border-radius:50%;background:var(--primary);flex-shrink:0;margin-top:6px;"></div>' : ''}
          </div>
        `;
      }).join('');
    }
  } catch {
    list.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading notifications</h3></div>';
  }
}

async function handleNotifClick(notifId, projectId) {
  try {
    await api.markNotificationRead(notifId);
    refreshNotifBadge();
    if (projectId) {
      navigate('project', projectId);
    }
  } catch {
    // ignore
  }
}

async function markAllRead() {
  try {
    await api.markAllNotificationsRead();
    showToast('All notifications marked as read', 'success');
    refreshNotifBadge();
    loadNotifications();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Refresh badge periodically
setInterval(() => { if (currentUser) refreshNotifBadge(); }, 30000);

// ===================== HELPERS =====================
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function truncate(str, len) {
  if (!str) return '';
  return str.length > len ? str.substring(0, len) + '...' : str;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now - d;
  const mins = Math.floor(diff / 60000);
  const hrs = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  if (hrs < 24) return `${hrs}h ago`;
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' });
}

function stageBadge(stage) {
  const labels = {
    'idea': '💡 Idea',
    'planning': '📋 Planning',
    'in-progress': '🔨 In Progress',
    'testing': '🧪 Testing',
    'completed': '✅ Completed'
  };
  return `<span class="badge badge-${stage}">${labels[stage] || stage}</span>`;
}

function categoryBadge(category) {
  if (!category) return '';
  const labels = {
    'web': '🌐 Web App', 'mobile': '📱 Mobile', 'api': '🔌 API',
    'data-science': '📊 Data Science', 'ai-ml': '🤖 AI/ML', 'devops': '⚙️ DevOps',
    'iot': '📡 IoT', 'fintech': '💰 FinTech', 'edtech': '📚 EdTech',
    'healthtech': '🏥 HealthTech', 'gaming': '🎮 Gaming', 'other': '🔧 Other'
  };
  return `<span class="badge badge-category">${labels[category] || category}</span>`;
}

function stageProgress(stage) {
  const stages = ['idea', 'planning', 'in-progress', 'testing', 'completed'];
  const labels = { 'idea': 'Idea', 'planning': 'Planning', 'in-progress': 'In Progress', 'testing': 'Testing', 'completed': 'Completed' };
  const idx = stages.indexOf(stage);
  const pct = idx >= 0 ? Math.round(((idx + 1) / stages.length) * 100) : 0;
  return `<div class="stage-progress-wrapper">
    <div class="stage-progress-label"><span>${labels[stage] || stage}</span><span>${pct}%</span></div>
    <div class="stage-progress"><div class="stage-progress-bar" style="width:${pct}%"></div></div>
  </div>`;
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ===================== INIT =====================
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuth();
  const savedPage = sessionStorage.getItem('mzansi_page') || 'home';
  const savedData = sessionStorage.getItem('mzansi_page_data');
  const data = savedData ? JSON.parse(savedData) : undefined;
  // Pages that require auth - fall back to home if not logged in
  const authPages = ['dashboard', 'my-projects', 'profile', 'notifications', 'bookmarks'];
  if (authPages.includes(savedPage) && !currentUser) {
    navigate('home');
  } else {
    navigate(savedPage, data);
  }
});
