/* 校园快递驿站智能取件助手 - 原生 ES6 + Fetch，免构建 */
'use strict';

const $ = (id) => document.getElementById(id);

const STATUS_CN = { in_stock: '在库', picked_up: '已出库', exception: '异常件' };

function esc(s) {
  const v = (s === undefined || s === null) ? '' : String(s);
  return v.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function baseUrl() {
  return $('apiBase').value.trim().replace(/\/+$/, '');
}

async function api(method, path, body) {
  const opt = { method: method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) { opt.body = JSON.stringify(body); }
  try {
    const res = await fetch(baseUrl() + path, opt);
    const data = await res.json().catch(() => ({}));
    return { status: res.status, ok: res.ok, data: data };
  } catch (e) {
    return { status: 0, ok: false, data: { detail: '无法连接后端：' + e.message } };
  }
}

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 1800);
}

function renderKV(pairs) {
  const rows = pairs.map((p) =>
    '<tr><th>' + esc(p[0]) + '</th><td>' + esc(p[1]) + '</td></tr>'
  ).join('');
  return '<table class="kv">' + rows + '</table>';
}

function renderError(resp) {
  return '<p><span class="badge err">HTTP ' + esc(resp.status) + '</span> ' +
    esc((resp.data && resp.data.detail) || '请求失败') + '</p>';
}

function renderPackages(packages) {
  if (!packages || !packages.length) { return '<p class="empty">暂无包裹</p>'; }
  const head = '<thead><tr><th>运单号</th><th>取件码</th><th>货架位</th><th>尺寸</th><th>状态</th></tr></thead>';
  const body = packages.map((p) => {
    const shelf = p.shelf ? p.shelf.label : '';
    const st = STATUS_CN[p.status] || p.status;
    const cls = p.status === 'in_stock' ? 'ok' : (p.status === 'exception' ? 'warn' : '');
    return '<tr><td>' + esc(p.tracking_no) + '</td><td>' + esc(p.pickup_code) +
      '</td><td>' + esc(shelf) + '</td><td>' + esc(p.size) +
      '</td><td><span class="badge ' + cls + '">' + esc(st) + '</span></td></tr>';
  }).join('');
  return '<table>' + head + '<tbody>' + body + '</tbody></table>';
}

/* ---------------- 学生端 ---------------- */

async function doHealth() {
  const r = await api('GET', '/api/health');
  $('healthTip').textContent = r.ok
    ? '连接正常（' + esc(r.data.service) + ' v' + esc(r.data.version) + '）'
    : '后端未就绪：' + esc((r.data && r.data.detail) || r.status);
  return r;
}

async function doLookup() {
  const code = $('lookupCode').value.trim();
  const r = await api('GET', '/api/packages/lookup?code=' + encodeURIComponent(code));
  const el = $('lookupResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  const d = r.data;
  el.innerHTML =
    '<p><span class="badge ok">查询成功</span> 解析货架：' + esc(d.shelf.shelf) +
    ' · 学生：' + esc(d.student.name) + '（' + esc(d.student.id) + '）· 共 ' +
    esc(d.total) + ' 个包裹</p>' + renderPackages(d.packages);
}

async function doForecast() {
  const r = await api('GET', '/api/queue/forecast');
  const el = $('forecastResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  const d = r.data;
  el.innerHTML = renderKV([
    ['当前时段', d.current_hour + ':00'],
    ['待取件数', d.pending_count + ' 件'],
    ['取件窗口数', d.servers],
    ['平均单人时长', d.avg_service_minutes + ' 分钟'],
    ['预计等待', d.predicted_wait_minutes + ' 分钟'],
    ['拥挤等级', d.congestion_level],
    ['推荐错峰时段', d.recommended_offpeak_hour + ':00 - ' + d.recommended_offpeak_hour + ':59'],
    ['提示', d.recommendation],
    ['算法', d.algorithm]
  ]);
}

async function doAuthorize() {
  const body = {
    pickup_code: $('authPickupCode').value.trim(),
    delegate_name: $('authDelegate').value.trim(),
    delegate_phone: $('authPhone').value.trim(),
    ttl_minutes: Number($('authTtl').value || 0)
  };
  const r = await api('POST', '/api/packages/authorize', body);
  const el = $('authResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  $('outAuth').value = r.data.auth_code;   // 自动带入工作人员端出库框，便于演示
  el.innerHTML = '<p><span class="badge ok">授权成功</span></p>' + renderKV([
    ['取件码', r.data.pickup_code],
    ['代取人', r.data.delegate_name],
    ['授权码', r.data.auth_code],
    ['有效期至', r.data.expires_at],
    ['有效分钟', r.data.ttl_minutes]
  ]) + '<p class="hint">授权码已自动填入工作人员端「出库核验」。</p>';
  toast('代取授权已生成：' + r.data.auth_code);
}

async function doQueryAuth() {
  const code = $('authPickupCode').value.trim();
  const r = await api('GET', '/api/packages/authorize/' + encodeURIComponent(code));
  const el = $('authResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  const d = r.data;
  let html = renderKV([
    ['取件码', d.pickup_code],
    ['是否有授权记录', d.has_authorization ? '是' : '否'],
    ['当前有效授权', d.valid ? '有' : '无'],
    ['状态说明', d.reason]
  ]);
  if (d.active_authorization) {
    const a = d.active_authorization;
    html += '<p class="hint">有效授权码：' + esc(a.auth_code) + '（' +
      esc(a.delegate_name) + '，至 ' + esc(a.expires_at) + '）</p>';
  }
  el.innerHTML = html;
}

/* ---------------- 工作人员端 ---------------- */

async function doCheckin() {
  const body = {
    tracking_no: $('inTracking').value.trim(),
    student_id: $('inStudent').value.trim(),
    student_name: $('inName').value.trim(),
    phone: $('inPhone').value.trim(),
    size: $('inSize').value
  };
  const r = await api('POST', '/api/packages/checkin', body);
  const el = $('checkinResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  const d = r.data;
  el.innerHTML = '<p><span class="badge ' + (d.created ? 'ok' : 'warn') + '">' +
    esc(d.message) + '</span></p>' + renderKV([
    ['取件码', d.pickup_code],
    ['货架位', d.shelf.label],
    ['货架区', d.shelf.area],
    ['层 / 格', d.shelf.level + ' 层 / ' + d.shelf.slot + ' 格'],
    ['是否新建', d.created ? '是' : '否（幂等跳过）'],
    ['运单号', d.package.tracking_no]
  ]);
  toast(d.message);
}

function checkoutBody(exception) {
  const b = {
    pickup_code: $('outCode').value.trim(),
    operator: $('outOperator').value.trim(),
    note: $('outNote').value.trim(),
    report_exception: !!exception
  };
  const auth = $('outAuth').value.trim();
  if (auth) { b.auth_code = auth; }
  return b;
}

async function doCheckout(exception) {
  const r = await api('POST', '/api/packages/checkout', checkoutBody(exception));
  const el = $('checkoutResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  const d = r.data;
  if (d.exception_registered) {
    el.innerHTML = '<p><span class="badge warn">已登记异常件</span></p>' + renderKV([
      ['取件码', d.package.pickup_code],
      ['运单号', d.package.tracking_no],
      ['异常原因', d.reason],
      ['包裹状态', STATUS_CN[d.package.status] || d.package.status]
    ]);
  } else {
    el.innerHTML = '<p><span class="badge ok">出库核验通过</span></p>' + renderKV([
      ['取件码', d.pickup_code],
      ['出库方式', d.auth_code_used ? '代取（授权码 ' + d.auth_code_used + '）' : '本人取件'],
      ['操作员', d.operator],
      ['出库时间', d.picked_up_at],
      ['包裹状态', STATUS_CN[d.package.status] || d.package.status]
    ]);
  }
  toast(d.message);
}

async function doExceptions() {
  const r = await api('GET', '/api/packages/exceptions');
  const el = $('checkoutResult');
  if (!r.ok) { el.innerHTML = renderError(r); return; }
  const list = r.data.exceptions || [];
  if (!list.length) {
    el.innerHTML = '<p><span class="badge ok">暂无异常件</span>（共 ' +
      esc(r.data.total) + ' 条）</p>';
    return;
  }
  const head = '<thead><tr><th>#</th><th>取件码</th><th>运单号</th><th>原因</th><th>操作员</th><th>登记时间</th></tr></thead>';
  const body = list.map((x) => '<tr><td>' + esc(x.id) + '</td><td>' + esc(x.pickup_code) +
    '</td><td>' + esc(x.tracking_no) + '</td><td>' + esc(x.reason) +
    '</td><td>' + esc(x.operator) + '</td><td>' + esc(x.created_at) + '</td></tr>').join('');
  el.innerHTML = '<p>共 ' + esc(r.data.total) + ' 条异常件</p><table>' + head +
    '<tbody>' + body + '</tbody></table>';
}

/* ---------------- 事件绑定 ---------------- */

document.querySelectorAll('.tab').forEach((t) => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((x) => x.classList.remove('active'));
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    t.classList.add('active');
    $('tab-' + t.dataset.tab).classList.add('active');
  });
});

$('btnHealth').addEventListener('click', doHealth);
$('btnLookup').addEventListener('click', doLookup);
$('btnForecast').addEventListener('click', doForecast);
$('btnAuthorize').addEventListener('click', doAuthorize);
$('btnQueryAuth').addEventListener('click', doQueryAuth);
$('btnCheckin').addEventListener('click', doCheckin);
$('btnCheckout').addEventListener('click', () => doCheckout(false));
$('btnException').addEventListener('click', () => doCheckout(true));
$('btnExceptions').addEventListener('click', doExceptions);

// 打开页面即尝试拉取一次演示数据（后端未启动时给出友好提示）
doHealth();
doLookup();
doForecast();
