const API = '/api/v1';
const $ = (id) => document.getElementById(id);

let currentUser = null;

function showMessage(id, text, kind = '') {
  const el = $(id);
  el.textContent = text;
  el.className = `message ${kind}`.trim();
}

function authHeaders() {
  return {
    Authorization: `Bearer ${sessionStorage.getItem('waloma_token')}`,
    'Content-Type': 'application/json'
  };
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) }
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || 'Request failed');
  }

  return data;
}

function itemList(target, rows, formatter) {
  const el = $(target);
  el.replaceChildren();

  if (!rows.length) {
    el.textContent = 'No records found.';
    return;
  }

  rows.forEach(row => {
    const div = document.createElement('div');
    div.className = 'data-item';
    div.textContent = formatter(row);
    el.append(div);
  });
}

function activateWorkspace(user) {
  currentUser = user;

  $('workspace').classList.remove('hidden');

  const finance = ['admin', 'treasurer'].includes(user.role);
  const meetings = ['admin', 'secretary'].includes(user.role);
  const canViewMembers = ['admin', 'treasurer', 'secretary'].includes(user.role);

  $('finance-tools').classList.toggle('hidden', !finance);
  $('meeting-tools').classList.toggle('hidden', !meetings);
  $('load-members').classList.toggle('hidden', !canViewMembers);

  // Staff account management is restricted to administrators.
  $('staff-tools').classList.toggle('hidden', user.role !== 'admin');
  $('approval-tools').classList.toggle('hidden', user.role !== 'admin');

  if (user.role === 'admin') {
    loadStaff().catch(error => {
      $('staff-list').textContent = error.message;
    });
    loadPendingRegistrations().catch(error => {
      $('pending-list').textContent = error.message;
    });
  }
}

function showAccount(user) {
  $('account-panel').classList.remove('hidden');
  $('account-details').textContent =
    `${user.full_name} | ${user.member_id} | ${user.role} | ${user.status}`;

  $('login-form').classList.add('hidden');
  $('register-form').classList.add('hidden');

  activateWorkspace(user);
}

// Login
$('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  showMessage('login-message', 'Signing in...');

  const form = new FormData(event.currentTarget);

  try {
    const response = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: form.get('email'),
        password: form.get('password')
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Sign in failed');
    }

    sessionStorage.setItem('waloma_token', data.access_token);
    showAccount(data.user);
  } catch (error) {
    showMessage('login-message', error.message, 'error');
  }
});

// Member registration
$('register-form').addEventListener('submit', async event => {
  event.preventDefault();
  showMessage('register-message', 'Submitting registration...');

  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(
    ['full_name', 'email', 'phone', 'password'].map(
      key => [key, form.get(key)]
    )
  );

  try {
    const response = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed');
    }

    event.currentTarget.reset();

    showMessage(
      'register-message',
      `Registration received. Your Member ID is ${data.member_id}. Sign-in will be available after administrator approval.`,
      'success'
    );
  } catch (error) {
    showMessage('register-message', error.message, 'error');
  }
});

// Logout
$('logout-button').addEventListener('click', () => {
  sessionStorage.removeItem('waloma_token');
  location.reload();
});

// Restore existing login session
(async () => {
  const token = sessionStorage.getItem('waloma_token');

  if (!token) return;

  try {
    const response = await fetch(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!response.ok) {
      throw new Error('Session expired');
    }

    showAccount(await response.json());
  } catch {
    sessionStorage.removeItem('waloma_token');
  }
})();

// Members
$('load-members').addEventListener('click', async () => {
  try {
    const rows = await api('/members');

    itemList(
      'members-list',
      rows,
      row => `${row.full_name} | ${row.member_id} | ${row.email} | Status: ${row.status} | Role: ${row.role}`
    );
  } catch (error) {
    $('members-list').textContent = error.message;
  }
});

// Meetings
$('meeting-form').addEventListener('submit', async event => {
  event.preventDefault();

  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form);
  payload.starts_at = new Date(payload.starts_at).toISOString();

  try {
    await api('/meetings', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    event.currentTarget.reset();
    await loadMeetings();
  } catch (error) {
    alert(error.message);
  }
});

async function loadMeetings() {
  const rows = await api('/meetings');

  itemList(
    'meetings-list',
    rows,
    row => `${row.title} | ${new Date(row.starts_at).toLocaleString()} | ${row.location || 'No location'} | ID: ${row.id}`
  );
}

// Contributions
$('contribution-form').addEventListener('submit', async event => {
  event.preventDefault();

  const payload = Object.fromEntries(new FormData(event.currentTarget));
  payload.amount_due = Number(payload.amount_due);

  try {
    await api('/contributions', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    event.currentTarget.reset();
    alert('Contribution created.');
  } catch (error) {
    alert(error.message);
  }
});

// Payments
$('payment-form').addEventListener('submit', async event => {
  event.preventDefault();

  const payload = Object.fromEntries(new FormData(event.currentTarget));
  payload.amount = Number(payload.amount);

  try {
    const payment = await api('/payments', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    event.currentTarget.reset();

    $('finance-message').textContent =
      `Payment saved. Receipt: ${payment.receipt_number}`;

    const link = document.createElement('a');
    link.href = `${API}/receipts/${encodeURIComponent(payment.receipt_number)}.pdf`;
    link.textContent = 'Download PDF receipt';
    link.target = '_blank';
    link.rel = 'noopener';

    $('finance-message').append(' ', link);
  } catch (error) {
    $('finance-message').textContent = error.message;
  }
});

// Contribution history
$('load-contributions').addEventListener('click', async () => {
  try {
    const rows = await api('/contributions');

    itemList(
      'contributions-list',
      rows,
      row => `${row.period} | Due ${row.amount_due} | Paid ${row.amount_paid} | Balance ${row.balance} | Contribution ID: ${row.id}`
    );
  } catch (error) {
    $('contributions-list').textContent = error.message;
  }
});

// Payment history
$('load-payments').addEventListener('click', async () => {
  try {
    const rows = await api('/payments');
    const el = $('payments-list');

    el.replaceChildren();

    if (!rows.length) {
      el.textContent = 'No payments found.';
      return;
    }

    rows.forEach(row => {
      const div = document.createElement('div');
      div.className = 'data-item';

      div.textContent =
        `${row.receipt_number} | ${row.amount} | ${row.method} | ${row.period} | ${new Date(row.paid_at).toLocaleString()} `;

      const link = document.createElement('a');
      link.href = `${API}/receipts/${encodeURIComponent(row.receipt_number)}.pdf`;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = 'Download PDF';

      div.append(link);
      el.append(div);
    });
  } catch (error) {
    $('payments-list').textContent = error.message;
  }
});

// Password change - available to every authenticated role.
$('password-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const currentPassword = form.get('current_password');
  const newPassword = form.get('new_password');
  const confirmation = form.get('confirm_password');

  if (newPassword !== confirmation) {
    showMessage('password-message', 'New password and confirmation do not match.', 'error');
    return;
  }

  try {
    const result = await api('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
    event.currentTarget.reset();
    showMessage('password-message', result.message, 'success');
  } catch (error) {
    showMessage('password-message', error.message, 'error');
  }
});

// Member approval queue - Admin only.
async function loadPendingRegistrations() {
  if (!currentUser || currentUser.role !== 'admin') {
    throw new Error('Administrator permission is required.');
  }
  const rows = await api('/auth/registrations/pending');
  const target = $('pending-list');
  target.replaceChildren();
  if (!rows.length) {
    target.textContent = 'No pending registrations.';
    return;
  }
  rows.forEach(member => {
    const item = document.createElement('div');
    item.className = 'data-item';
    const details = document.createElement('p');
    details.textContent = `${member.full_name} | ${member.member_id} | ${member.email} | ${member.phone}`;
    const approve = document.createElement('button');
    approve.type = 'button';
    approve.textContent = 'Approve';
    approve.addEventListener('click', () => reviewMember(member.id, 'approved'));
    const reject = document.createElement('button');
    reject.type = 'button';
    reject.className = 'secondary';
    reject.textContent = 'Reject';
    reject.addEventListener('click', () => reviewMember(member.id, 'rejected'));
    item.append(details, approve, reject);
    target.append(item);
  });
}

async function reviewMember(memberId, status) {
  try {
    await api(`/auth/registrations/${encodeURIComponent(memberId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
    showMessage('approval-message', `Member registration ${status}.`, 'success');
    await loadPendingRegistrations();
    $('members-list').textContent = 'Select Load members to refresh the member directory.';
  } catch (error) {
    showMessage('approval-message', error.message, 'error');
  }
}

$('load-pending').addEventListener('click', async () => {
  try {
    await loadPendingRegistrations();
    showMessage('approval-message', 'Registration queue updated.', 'success');
  } catch (error) {
    showMessage('approval-message', error.message, 'error');
  }
});

// Staff account creation - Admin only
$('staff-form').addEventListener('submit', async event => {
  event.preventDefault();

  if (!currentUser || currentUser.role !== 'admin') {
    showMessage('staff-message', 'Administrator permission is required.', 'error');
    return;
  }

  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form);

  try {
    const staff = await api('/auth/staff', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    event.currentTarget.reset();

    showMessage(
      'staff-message',
      `${staff.role} account created successfully. Member ID: ${staff.member_id}`,
      'success'
    );

    await loadStaff();
  } catch (error) {
    showMessage('staff-message', error.message, 'error');
  }
});

// Staff directory - Admin only
async function loadStaff() {
  if (!currentUser || currentUser.role !== 'admin') {
    throw new Error('Administrator permission is required.');
  }

  const rows = await api('/auth/staff');

  itemList(
    'staff-list',
    rows,
    row => `${row.full_name} | ${row.member_id} | ${row.email} | ${row.phone} | Role: ${row.role} | Status: ${row.status}`
  );
}

$('load-staff').addEventListener('click', async () => {
  try {
    await loadStaff();
    showMessage('staff-message', 'Staff directory updated.', 'success');
  } catch (error) {
    $('staff-list').textContent = error.message;
  }
});

// Refresh
$('refresh-button').addEventListener('click', async () => {
  try {
    if (currentUser && ['admin', 'secretary'].includes(currentUser.role)) {
      await loadMeetings();
    }

    if (currentUser && currentUser.role === 'admin') {
      await loadStaff();
    }
  } catch (error) {
    alert(error.message);
  }
});
