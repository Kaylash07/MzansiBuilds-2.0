/**
 * MzansiBuilds API Client - Single Responsibility: handles all HTTP communication.
 */
const API_BASE = '/api';

class ApiClient {
  constructor() {
    this._token = localStorage.getItem('mzansi_token');
  }

  get token() {
    return this._token;
  }

  set token(val) {
    this._token = val;
    if (val) {
      localStorage.setItem('mzansi_token', val);
    } else {
      localStorage.removeItem('mzansi_token');
    }
  }

  get isLoggedIn() {
    return !!this._token;
  }

  async _request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this._token) {
      headers['Authorization'] = `Bearer ${this._token}`;
    }
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Something went wrong');
    }
    return data;
  }

  // Auth
  register(username, email, password, bio) {
    return this._request('POST', '/auth/register', { username, email, password, bio });
  }

  login(email, password) {
    return this._request('POST', '/auth/login', { email, password });
  }

  forgotPassword(email) {
    return this._request('POST', '/auth/forgot-password', { email });
  }

  resetPassword(email, code, new_password) {
    return this._request('POST', '/auth/reset-password', { email, code, new_password });
  }

  getMe() {
    return this._request('GET', '/auth/me');
  }

  updateProfile(data) {
    return this._request('PUT', '/auth/me', data);
  }

  getPublicProfile(userId) {
    return this._request('GET', `/auth/users/${userId}`);
  }

  async uploadAvatar(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    const headers = {};
    if (this._token) {
      headers['Authorization'] = `Bearer ${this._token}`;
    }
    const res = await fetch(`${API_BASE}/auth/upload-avatar`, {
      method: 'POST',
      headers,
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Upload failed');
    }
    return data;
  }

  // Projects
  createProject(data) {
    return this._request('POST', '/projects', data);
  }

  getProjects(page = 1, stage = '') {
    let url = `/projects?page=${page}`;
    if (stage) url += `&stage=${stage}`;
    return this._request('GET', url);
  }

  getMyProjects() {
    return this._request('GET', '/projects/my');
  }

  getProject(id) {
    return this._request('GET', `/projects/${id}`);
  }

  updateProject(id, data) {
    return this._request('PUT', `/projects/${id}`, data);
  }

  deleteProject(id) {
    return this._request('DELETE', `/projects/${id}`);
  }

  // Milestones
  addMilestone(projectId, data) {
    return this._request('POST', `/projects/${projectId}/milestones`, data);
  }

  getMilestones(projectId) {
    return this._request('GET', `/projects/${projectId}/milestones`);
  }

  updateMilestone(projectId, milestoneId, data) {
    return this._request('PUT', `/projects/${projectId}/milestones/${milestoneId}`, data);
  }

  // Feed
  getFeed(page = 1, stage = '', search = '', category = '') {
    let url = `/feed?page=${page}`;
    if (stage) url += `&stage=${encodeURIComponent(stage)}`;
    if (search) url += `&q=${encodeURIComponent(search)}`;
    if (category) url += `&category=${encodeURIComponent(category)}`;
    return this._request('GET', url);
  }

  // Comments
  getComments(projectId) {
    return this._request('GET', `/projects/${projectId}/comments`);
  }

  addComment(projectId, content) {
    return this._request('POST', `/projects/${projectId}/comments`, { content });
  }

  // Collaborations
  requestCollab(projectId, message) {
    return this._request('POST', `/projects/${projectId}/collaborate`, { message });
  }

  getCollabs(projectId) {
    return this._request('GET', `/projects/${projectId}/collaborate`);
  }

  respondCollab(collabId, status) {
    return this._request('PUT', `/collaborations/${collabId}`, { status });
  }

  // Celebration Wall
  getCelebrationWall() {
    return this._request('GET', '/celebration-wall');
  }

  // Support
  submitSupport(category, subject, description, priority) {
    return this._request('POST', '/support', { category, subject, description, priority });
  }

  // Notifications
  getNotifications() {
    return this._request('GET', '/notifications');
  }

  markAllNotificationsRead() {
    return this._request('PUT', '/notifications/read');
  }

  markNotificationRead(id) {
    return this._request('PUT', `/notifications/${id}/read`);
  }

  // Activities
  getActivities(projectId) {
    return this._request('GET', `/projects/${projectId}/activities`);
  }

  // Likes
  toggleLike(projectId) {
    return this._request('POST', `/projects/${projectId}/like`);
  }

  getLikeStatus(projectId) {
    return this._request('GET', `/projects/${projectId}/like/status`);
  }

  // Bookmarks
  toggleBookmark(projectId) {
    return this._request('POST', `/projects/${projectId}/bookmark`);
  }

  getBookmarkStatus(projectId) {
    return this._request('GET', `/projects/${projectId}/bookmark/status`);
  }

  getMyBookmarks() {
    return this._request('GET', '/bookmarks');
  }
}

const api = new ApiClient();
