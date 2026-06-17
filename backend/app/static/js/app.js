const API_BASE = '/api';

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

const STATUSES = ["novo", "não contatado", "contato iniciado", "aguardando resposta", "respondeu", "interessado", "reunião marcada", "proposta enviada", "negociação", "fechado", "recusado", "sem retorno", "lead inválido"];
const CHANNELS = ["WhatsApp", "Instagram", "ligação", "email", "presencial"];
const TEMPERATURES = ["frio", "morno", "quente"];

const api = async (url, opts = {}) => {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  if (opts.raw) return res;
  return res.json();
};

function showToast(msg, type = 'success') {
  const colors = { success: '#00c851', danger: '#ff4444', warning: '#ffaa00', info: '#33b5e5' };
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:20px;right:20px;background:${colors[type]||'#333'};color:white;padding:12px 24px;border-radius:6px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.2);font-size:14px;max-width:400px;`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

function showModal(id) { $(`#${id}`)?.classList.add('is-active'); }
function hideModal(id) { $(`#${id}`)?.classList.remove('is-active'); }

document.addEventListener('click', e => {
  if (e.target.matches('.modal-background, [data-dismiss="modal"], .modal-close, .delete')) {
    e.target.closest('.modal')?.classList.remove('is-active');
  }
});

// SPA Routing
function navigate(page) {
  window.location.hash = '#/' + page;
}

function getCurrentPage() {
  const hash = window.location.hash.replace('#/', '');
  if (!hash || hash === '') return 'search';
  return hash.split('/')[0];
}

function getLeadIdFromHash() {
  const parts = window.location.hash.replace('#/', '').split('/');
  if (parts[0] === 'lead' && parts[1]) return parts[1];
  return null;
}

function showPage(pageName) {
  $$('.page').forEach(p => p.style.display = 'none');
  const page = $(`#page-${pageName}`);
  if (page) page.style.display = 'block';
  $$('.navbar-item').forEach(n => n.classList.remove('is-active'));
  const navItem = document.querySelector(`[data-page="${pageName}"]`);
  if (navItem) navItem.classList.add('is-active');
}

function handleRoute() {
  const page = getCurrentPage();
  if (page === 'lead') {
    saveLeadsListState();
    showPage('lead-detail');
    const id = getLeadIdFromHash();
    if (id) loadLeadDetail(parseInt(id));
  } else {
    showPage(page);
    if (page === 'leads') { restoreLeadsListState(); loadLeads(); loadAddCampaignSelect(); }
    if (page === 'campaigns') loadCampaigns();
    if (page === 'dashboard') loadDashboard();
    if (page === 'search') { loadSearchHistory(); loadCampaignSelect(); }
  }
}

// Nav burger
$$('.navbar-burger').forEach(b => b.addEventListener('click', () => {
  b.classList.toggle('is-active');
  $(`#${b.dataset.target}`)?.classList.toggle('is-active');
}));

// Click nav
document.addEventListener('click', e => {
  const link = e.target.closest('[data-page]');
  if (link) {
    e.preventDefault();
    navigate(link.dataset.page);
  }
});

window.addEventListener('hashchange', handleRoute);
document.addEventListener('DOMContentLoaded', handleRoute);

// ======== SEARCH PAGE ========
if (document.getElementById('searchForm')) {
  let pollInterval = null;

  async function loadCampaignSelect() {
    try {
      const camps = await api('/campaigns');
      const sel = document.getElementById('campaignSelect');
      sel.innerHTML = '<option value="">Sem campanha</option>';
      camps.forEach(c => {
        const o = document.createElement('option');
        o.value = c.id; o.textContent = `${c.name} (${c.niche} - ${c.city})`;
        sel.appendChild(o);
      });
    } catch(e) {}
  }

  document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const niche = document.getElementById('niche').value.trim();
    const city = document.getElementById('city').value.trim();
    const country = document.getElementById('country').value.trim() || 'Brasil';
    const campaignId = document.getElementById('campaignSelect').value;
    const maxResults = parseInt(document.getElementById('maxResults').value) || 50;
    const sources = Array.from($$('.source-checkbox:checked')).map(c => c.value);

    if (!niche || !city) return showToast('Preencha nicho e cidade', 'warning');
    if (sources.length === 0) return showToast('Selecione ao menos uma fonte', 'warning');

    const btn = document.getElementById('searchBtn');
    btn.classList.add('is-loading'); btn.disabled = true;

    try {
      const result = await api('/search', { method: 'POST', body: JSON.stringify({ niche, city, country, sources, max_results: maxResults, campaign_id: campaignId || null }) });
      document.getElementById('progressSection').style.display = 'block';
      document.getElementById('resultsSection').style.display = 'none';
      addLog('info', `Busca iniciada #${result.search_id}: ${niche} / ${city} (${country})`);
      addLog('info', `Fontes: ${sources.join(', ')}`);

      if (pollInterval) clearInterval(pollInterval);
      let elapsed = 0;
      pollInterval = setInterval(async () => {
        elapsed++;
        try {
          const status = await api(`/search/${result.search_id}`);
          if (status.status === 'running') {
            document.getElementById('searchProgress').value = Math.min(elapsed * 8, 90);
            document.getElementById('progressText').textContent = `Buscando... (${elapsed}s)`;
          } else {
            clearInterval(pollInterval); pollInterval = null;
            document.getElementById('searchProgress').value = 100;
            document.getElementById('progressText').textContent = `Concluída! ${status.leads_found} leads.`;
            if (status.error_log) status.error_log.split(';').filter(Boolean).forEach(e => addLog('error', e.trim()));
            addLog('info', `Busca concluída: ${status.leads_found} leads salvos`);
            await loadLatestResults(niche, city);
            await loadSearchHistory();
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('resultCount').textContent = `${status.leads_found} leads`;
            btn.classList.remove('is-loading'); btn.disabled = false;
          }
        } catch(err) { addLog('error', `Erro: ${err.message}`); }
      }, 2000);
      setTimeout(() => {
        if (pollInterval) { clearInterval(pollInterval); pollInterval = null; btn.classList.remove('is-loading'); btn.disabled = false; }
      }, 120000);
    } catch(err) {
      showToast(`Erro: ${err.message}`, 'danger');
      btn.classList.remove('is-loading'); btn.disabled = false;
    }
  });

  function addLog(type, msg) {
    const box = document.getElementById('sourceLog');
    if (!box) return;
    const e = document.createElement('div');
    e.className = `log-entry log-${type}`;
    e.textContent = `[${new Date().toLocaleTimeString()}] [${type.toUpperCase()}] ${msg}`;
    box.appendChild(e);
    box.scrollTop = box.scrollHeight;
  }

  async function loadLatestResults(niche, city) {
    try {
      const data = await api(`/leads?niche=${encodeURIComponent(niche)}&city=${encodeURIComponent(city)}&page_size=20&sort_by=score&sort_order=desc`);
      const tbody = document.getElementById('resultsBody');
      tbody.innerHTML = '';
      (data.leads || []).forEach(l => {
        const tr = document.createElement('tr');
        tr.className = 'clickable-row';
        tr.addEventListener('click', () => navigate(`lead/${l.id}`));
        tr.innerHTML = `<td><strong>${esc(l.company_name||'-')}</strong></td>
          <td>${l.phone||'-'}</td>
          <td>${l.website ? `<a href="${l.website}" target="_blank" class="is-size-7">${new URL(l.website).hostname}</a>` : '-'}</td>
          <td><span class="tag">${l.source||'-'}</span></td>
          <td><span class="tag quality-${l.quality||'frio'}">${l.quality||'frio'}</span></td>
          <td><strong>${l.score||0}</strong></td>`;
        tbody.appendChild(tr);
      });
    } catch(e) {}
  }
}

async function loadSearchHistory() {
  try {
    const h = await api('/search');
    const tbody = document.getElementById('historyBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    (h||[]).forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${s.started_at?new Date(s.started_at).toLocaleString():'-'}</td>
        <td>${s.niche}</td><td>${s.city}</td>
        <td>${s.country||'Brasil'}</td>
        <td><strong>${s.leads_found||0}</strong></td>
        <td><span class="tag is-${s.status==='completed'?'success':s.status==='failed'?'danger':'info'}">${s.status}</span></td>`;
      tbody.appendChild(tr);
    });
  } catch(e) {}
}

// ======== LEADS PAGE ========
let currentPage = 1, totalPages = 1, selectedLeads = new Set();
let leadsFilterState = {};
let leadsListState = null;

function saveLeadsListState() {
  if (getCurrentPage() !== 'leads') return;
  leadsListState = { currentPage };
  ['filterSearch','filterNiche','filterCity','filterQuality','filterStatus','filterTemperature','filterCampaign'].forEach(id => {
    const el = document.getElementById(id);
    if (el) leadsListState[id] = el.value;
  });
}

function restoreLeadsListState() {
  if (!leadsListState) return;
  currentPage = leadsListState.currentPage || 1;
  ['filterSearch','filterNiche','filterCity','filterQuality','filterStatus','filterTemperature','filterCampaign'].forEach(id => {
    const el = document.getElementById(id);
    if (el && leadsListState[id] !== undefined) el.value = leadsListState[id];
  });
}

if (document.getElementById('leadsTable')) {
  loadFilterStatuses();
  loadCampaignsFilter();
  loadAddCampaignSelect();
  document.getElementById('applyFilters')?.addEventListener('click', () => { currentPage = 1; loadLeads(); });
  ['filterSearch','filterNiche','filterCity'].forEach(id => {
    document.getElementById(id)?.addEventListener('keyup', e => { if (e.key==='Enter') { currentPage=1; loadLeads(); }});
  });
  document.getElementById('prevPage')?.addEventListener('click', () => { if (currentPage>1) { currentPage--; loadLeads(); }});
  document.getElementById('nextPage')?.addEventListener('click', () => { if (currentPage<totalPages) { currentPage++; loadLeads(); }});
  document.getElementById('selectAll')?.addEventListener('change', e => {
    $$('.lead-checkbox').forEach(cb => {
      cb.checked = e.target.checked;
      if (e.target.checked) selectedLeads.add(cb.value);
      else selectedLeads.delete(cb.value);
    });
    updateBulkActions();
  });

  document.getElementById('exportExcelBtn')?.addEventListener('click', () => {
    const p = new URLSearchParams();
    ['filterCampaign','filterQuality','filterStatus'].forEach(id => {
      const v = document.getElementById(id)?.value;
      if (v) p.set(id.replace('filter','').toLowerCase(), v);
    });
    window.open(`/api/export/excel?${p.toString()}`,'_blank');
  });
  document.getElementById('exportCsvBtn')?.addEventListener('click', () => {
    const p = new URLSearchParams();
    ['filterCampaign','filterQuality','filterStatus'].forEach(id => {
      const v = document.getElementById(id)?.value;
      if (v) p.set(id.replace('filter','').toLowerCase(), v);
    });
    window.open(`/api/export/csv?${p.toString()}`,'_blank');
  });
  document.getElementById('importBtn')?.addEventListener('click', () => showModal('importModal'));
  document.getElementById('doImport')?.addEventListener('click', async () => {
    const fi = document.getElementById('importFile');
    if (!fi.files.length) return showToast('Selecione um arquivo', 'warning');
    const f = new FormData();
    f.append('file', fi.files[0]);
    try {
      const r = await fetch('/api/leads/import', { method:'POST', body: f });
      const d = await r.json();
      showToast(d.message, 'success');
      hideModal('importModal');
      loadLeads();
    } catch(err) { showToast(`Erro: ${err.message}`, 'danger'); }
  });

  async function loadAddCampaignSelect() {
    try {
      const camps = await api('/campaigns');
      const sel = document.getElementById('addCampaign');
      sel.innerHTML = '<option value="">Nenhuma</option>';
      camps.forEach(c => {
        const o = document.createElement('option');
        o.value = c.id;
        o.textContent = `${c.name} (${c.niche})`;
        sel.appendChild(o);
      });
    } catch (_) {}
  }

  function saveManualLead() {
    const data = {
      company_name: document.getElementById('addCompanyName').value.trim(),
      phone: document.getElementById('addPhone').value.trim(),
      website: document.getElementById('addWebsite').value.trim(),
      email: document.getElementById('addEmail').value.trim(),
      instagram: document.getElementById('addInstagram').value.trim(),
      address: document.getElementById('addAddress').value.trim(),
      lead_city: document.getElementById('addCity').value.trim(),
      state: document.getElementById('addState').value.trim(),
      niche: document.getElementById('addNiche').value.trim(),
      source: 'manual',
      commercial_status: 'novo',
      temperature: 'frio',
    };
    const campaignId = document.getElementById('addCampaign').value;
    if (campaignId) data.campaign_id = parseInt(campaignId);

    if (!data.company_name) return showToast('Nome da empresa é obrigatório', 'warning');

    api('/leads', { method: 'POST', body: JSON.stringify(data) })
      .then(() => {
        showToast('Lead adicionado com sucesso', 'success');
        hideModal('addLeadModal');
        loadLeads();
        document.getElementById('addCompanyName').closest('.modal').querySelectorAll('input').forEach(i => i.value = '');
      })
      .catch(err => {
        if (err.message.includes('409')) showToast('Lead já existe no banco de dados (duplicado)', 'warning');
        else showToast(`Erro: ${err.message}`, 'danger');
      });
  }

  function loadFilterStatuses() {
    const sel = document.getElementById('filterStatus');
    sel.innerHTML = '<option value="">Todos</option>';
    STATUSES.forEach(s => { const o=document.createElement('option'); o.value=s; o.textContent=s; sel.appendChild(o); });
  }

  async function loadCampaignsFilter() {
    try {
      const camps = await api('/campaigns');
      const sel = document.getElementById('filterCampaign');
      camps.forEach(c => { const o=document.createElement('option'); o.value=c.id; o.textContent=c.name; sel.appendChild(o); });
    } catch(e) {}
  }

  async function loadLeads() {
    const params = new URLSearchParams({ page: currentPage, page_size: 50, sort_by: 'score', sort_order: 'desc' });
    const fields = { search:'filterSearch', niche:'filterNiche', city:'filterCity', quality:'filterQuality', commercial_status:'filterStatus', temperature:'filterTemperature', campaign_id:'filterCampaign' };
    Object.entries(fields).forEach(([k,id]) => { const v = document.getElementById(id)?.value; if (v) params.set(k, v); });

    try {
      const data = await api(`/leads?${params.toString()}`);
      totalPages = data.total_pages;
      renderLeads(data.leads || []);
      renderPagination(data.page, data.total_pages, data.total);
      updateBulkActions();
    } catch(err) { showToast(`Erro: ${err.message}`, 'danger'); }
  }

  function renderLeads(leads) {
    const tbody = document.getElementById('leadsBody');
    tbody.innerHTML = '';
    if (!leads.length) { tbody.innerHTML = '<tr><td colspan="11" class="has-text-centered has-text-grey-light">Nenhum lead</td></tr>'; return; }
    leads.forEach(l => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><input type="checkbox" class="lead-checkbox" value="${l.id}"></td>
        <td><a href="#" onclick="navigate('lead/${l.id}');return false" class="has-text-weight-medium">${esc(l.company_name||'-')}</a></td>
        <td>${l.phone||'-'}</td>
        <td>${l.website?`<a href="${l.website}" target="_blank" class="is-size-7">${l.website.replace(/^https?:\/\//,'').replace(/\/.*$/,'').substring(0,20)}</a>`:'-'}</td>
        <td>${l.lead_city||'-'}</td>
        <td><span class="tag quality-${l.quality||'frio'} is-light">${l.quality||'frio'}</span></td>
        <td><strong>${l.score||0}</strong></td>
        <td><span class="tag is-info is-light is-small">${l.commercial_status||'novo'}</span></td>
        <td><span class="tag is-small ${l.temperature==='quente'?'is-danger':l.temperature==='morno'?'is-warning':'is-success'}">${l.temperature||'frio'}</span></td>
        <td>${l.source_url && l.source === 'google_maps' ? `<a href="${esc(l.source_url)}" target="_blank" title="Ver no Maps"><i class="fas fa-map-marker-alt has-text-danger"></i></a>` : '-'}</td>
        <td><div class="buttons are-small"><button class="button is-small is-info is-light" onclick="navigate('lead/${l.id}')"><i class="fas fa-edit"></i></button><button class="button is-small is-danger is-light" onclick="deleteLead(${l.id})"><i class="fas fa-trash"></i></button></div></td>`;
      tbody.appendChild(tr);
      const cb = tr.querySelector('.lead-checkbox');
      cb.addEventListener('change', () => {
        if (cb.checked) selectedLeads.add(cb.value);
        else selectedLeads.delete(cb.value);
        updateBulkActions();
      });
    });
  }

  function renderPagination(page, total, totalItems) {
    const info = document.getElementById('paginationInfo');
    if (info) info.textContent = `Página ${page} de ${total} (${totalItems} leads)`;
    const list = document.getElementById('paginationList');
    if (!list) return;
    list.innerHTML = '';
    const start = Math.max(1, page-2), end = Math.min(total, page+2);
    for (let i=start; i<=end; i++) {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.className = `pagination-link ${i===page?'is-current':''}`;
      btn.textContent = i;
      btn.addEventListener('click', () => { currentPage=i; loadLeads(); });
      li.appendChild(btn); list.appendChild(li);
    }
  }

  function updateBulkActions() {
    const el = document.getElementById('bulkActions');
    const ct = document.getElementById('selectedCount');
    if (!el||!ct) return;
    el.style.display = selectedLeads.size > 0 ? 'block' : 'none';
    ct.textContent = `${selectedLeads.size} selecionados`;
  }

  window.deleteLead = async (id) => {
    if (!confirm('Remover lead?')) return;
    try { await api(`/leads/${id}`, {method:'DELETE'}); showToast('Removido','success'); loadLeads(); }
    catch(err) { showToast(`Erro: ${err.message}`,'danger'); }
  };

  window.bulkUpdate = async (field, value) => {
    if (!selectedLeads.size) return showToast('Selecione leads','warning');
    const ids = Array.from(selectedLeads).map(Number);
    const updates = { [field]: value };
    if (field === 'contacted' && value === true) updates.first_contact_date = new Date().toISOString();
    try {
      const r = await api('/leads/batch', { method:'POST', body: JSON.stringify({ lead_ids: ids, updates }) });
      showToast(`${r.updated} atualizados`, 'success');
      selectedLeads.clear();
      loadLeads();
    } catch(err) { showToast(`Erro: ${err.message}`,'danger'); }
  };
}

// ======== LEAD DETAIL ========
async function loadLeadDetail(id) {
  try {
    const lead = await api(`/leads/${id}`);
    renderLeadDetail(lead);
  } catch(err) {
    document.getElementById('leadDetail').innerHTML = `<div class="box has-text-centered has-text-danger"><p>Erro: ${err.message}</p></div>`;
  }
}

function renderLeadDetail(lead) {
  document.getElementById('breadcrumbLead').textContent = lead.company_name || 'Lead';
  const h = esc;

  const html = `<div class="columns">
    <div class="column is-6">
      <div class="box lead-detail-section">
        <h3><span class="icon"><i class="fas fa-building"></i></span> Informações</h3>
        ${field('Empresa','company_name', lead.company_name)}
        ${field('Categoria','category', lead.category)}
        ${textarea('Descrição','description', lead.description, 3)}
        ${field('Site','website', lead.website, lead.has_website ? '<span class="tag is-success">Tem site</span>' : '<span class="tag is-light">Sem site</span>')}
        ${field('Telefone','phone', lead.phone, '', 'tel')}
        ${field('WhatsApp','whatsapp_link', lead.whatsapp_link, lead.whatsapp_link ? `<a class="button is-success is-small" href="${h(lead.whatsapp_link)}" target="_blank"><i class="fab fa-whatsapp"></i></a>` : '', 'tel')}
        ${field('Email','email', lead.email)}
        ${field('Instagram','instagram', lead.instagram, lead.instagram ? `<a class="button is-link is-small is-light" href="${h(lead.instagram)}" target="_blank"><i class="fab fa-instagram"></i></a>` : '')}
        ${field('Facebook','facebook', lead.facebook)}
        ${lead.source === 'google_maps' && lead.source_url ? field('Google Maps','source_url', lead.source_url, `<a class="button is-small is-danger is-light" href="${esc(lead.source_url)}" target="_blank"><i class="fas fa-map-marker-alt"></i> Ver no Maps</a>`) : ''}
      </div>
      <div class="box lead-detail-section">
        <h3><span class="icon"><i class="fas fa-map-marker-alt"></i></span> Endereço</h3>
        ${field('Endereço','address', lead.address)}
        ${field('Bairro','neighborhood', lead.neighborhood)}
        ${field('Cidade','lead_city', lead.lead_city)}
        ${field('Estado','state', lead.state)}
        ${field('CEP','zipcode', lead.zipcode)}
      </div>
    </div>
    <div class="column is-6">
      <div class="box lead-detail-section">
        <h3><span class="icon"><i class="fas fa-chart-line"></i></span> Classificação</h3>
        <div class="columns is-multiline">
          <div class="column is-4 has-text-centered"><p class="heading">Score</p><p class="title is-3 ${lead.score>=60?'has-text-danger':lead.score>=35?'has-text-warning':'has-text-success'}">${lead.score||0}</p></div>
          <div class="column is-4 has-text-centered"><p class="heading">Qualidade</p><p><span class="tag is-medium quality-${lead.quality||'frio'}">${lead.quality||'frio'}</span></p></div>
          <div class="column is-4 has-text-centered"><p class="heading">Temperatura</p><p><span class="select is-small"><select id="ed-temperature">${TEMPERATURES.map(t => `<option value="${t}" ${t===lead.temperature?'selected':''}>${t}</option>`).join('')}</select></span></p></div>
        </div>
        ${textarea('Motivo Score','score_reason', lead.score_reason, 3)}
        ${field('Oportunidade','opportunity', lead.opportunity)}
        ${field('Serviço Sugerido','suggested_service', lead.suggested_service)}
        <div class="field"><label class="label">Mensagem Sugerida</label><textarea class="textarea has-text-weight-medium" id="ed-suggested_message" rows="4" readonly style="background:#f5f5f5;border-left:3px solid #00d1b2;font-size:0.95em">${h(lead.suggested_message||'')}</textarea>
        <button class="button is-small is-light mt-1" onclick="copyMessage(${lead.id})">Copiar mensagem</button></div>
        ${textarea('Próxima Ação','next_action', lead.next_action, 2)}
        <div class="field is-grouped is-grouped-multiline">
          <div class="control"><label class="checkbox"><input type="checkbox" id="ed-has_website" ${lead.has_website?'checked':''}> Tem site?</label></div>
          <div class="control"><label class="checkbox"><input type="checkbox" id="ed-has_landing_page" ${lead.has_landing_page?'checked':''}> Landing page?</label></div>
          <div class="control"><label class="checkbox"><input type="checkbox" id="ed-has_whatsapp" ${lead.has_whatsapp?'checked':''}> WhatsApp?</label></div>
          <div class="control"><label class="checkbox"><input type="checkbox" id="ed-instagram_active" ${lead.instagram_active?'checked':''}> Instagram ativo?</label></div>
        </div>
      </div>
      <div class="box lead-detail-section">
        <h3><span class="icon"><i class="fas fa-phone"></i></span> Comercial</h3>
        <div class="field is-horizontal">
          <div class="field-label is-normal"><label class="label">Status</label></div>
          <div class="field-body"><div class="select"><select id="ed-commercial_status">${STATUSES.map(s => `<option value="${s}" ${s===lead.commercial_status?'selected':''}>${s}</option>`).join('')}</select></div></div>
        </div>
        <div class="field is-horizontal">
          <div class="field-label is-normal"><label class="label">Contato</label></div>
          <div class="field-body">
            <div class="control"><label class="checkbox mr-3"><input type="checkbox" id="ed-contacted" ${lead.contacted?'checked':''}> Realizado?</label></div>
            <div class="control"><div class="select is-small"><select id="ed-contact_channel"><option value="">Canal</option>${CHANNELS.map(c => `<option value="${c}" ${c===lead.contact_channel?'selected':''}>${c}</option>`).join('')}</select></div></div>
          </div>
        </div>
        <div class="field is-horizontal">
          <div class="field-label is-normal"><label class="label">Dono</label></div>
          <div class="field-body">
            <div class="control"><label class="checkbox mr-3"><input type="checkbox" id="ed-owner_identified" ${lead.owner_identified?'checked':''}> Identif.</label></div>
            <div class="control is-expanded"><input class="input" id="ed-owner_name" value="${h(lead.owner_name||'')}" placeholder="Nome"></div>
          </div>
        </div>
        <div class="field is-horizontal">
          <div class="field-label is-normal"><label class="label">Falou com</label></div>
          <div class="field-body"><div class="select"><select id="ed-spoke_with"><option value="">Selecione</option><option value="dono" ${lead.spoke_with==='dono'?'selected':''}>Dono</option><option value="intermediário" ${lead.spoke_with==='intermediário'?'selected':''}>Intermediário</option><option value="funcionário" ${lead.spoke_with==='funcionário'?'selected':''}>Funcionário</option><option value="não falou" ${lead.spoke_with==='não falou'?'selected':''}>Não falou</option></select></div></div>
        </div>
        ${textarea('Resposta','lead_response', lead.lead_response, 2)}
        <div class="columns">
          <div class="column"><label class="checkbox mr-2"><input type="checkbox" id="ed-interested" ${lead.interested?'checked':''}> Interessado</label>
            <label class="checkbox mr-2"><input type="checkbox" id="ed-refused" ${lead.refused?'checked':''}> Recusou</label>
            <label class="checkbox"><input type="checkbox" id="ed-proposal_sent" ${lead.proposal_sent?'checked':''}> Proposta</label></div>
        </div>
        ${field('Motivo Recusa','refusal_reason', lead.refusal_reason)}
        <div class="field is-horizontal">
          <div class="field-label is-normal"><label class="label">Follow-up</label></div>
          <div class="field-body">
            <label class="checkbox mr-3"><input type="checkbox" id="ed-follow_up_scheduled" ${lead.follow_up_scheduled?'checked':''}> Agendado</label>
            <div class="control"><input class="input" type="date" id="ed-follow_up_date" value="${lead.follow_up_date?lead.follow_up_date.substring(0,10):''}"></div>
          </div>
        </div>
        ${field('Valor Est.','estimated_value', lead.estimated_value ? `R$ ${lead.estimated_value}` : '', '', 'number')}
        ${field('Tags','tags', lead.tags, '', '', 'tag1, tag2, tag3')}
      </div>
      <div class="box lead-detail-section">
        <h3><span class="icon"><i class="fas fa-sticky-note"></i></span> Observações</h3>
        <div class="field"><label class="label">Automáticas</label><textarea class="textarea" id="ed-auto_notes" rows="2" readonly>${h(lead.auto_notes||'')}</textarea></div>
        <div class="field"><label class="label">Manuais</label><textarea class="textarea" id="ed-manual_notes" rows="3">${h(lead.manual_notes||'')}</textarea></div>
      </div>
      <div class="box has-text-centered"><p class="has-text-grey is-size-7">Fonte: ${lead.source||'-'} | Coletado: ${lead.collected_at?new Date(lead.collected_at).toLocaleString():'-'}</p></div>
      <div class="field"><div class="control"><button class="button is-primary is-fullwidth is-medium" onclick="saveLead(${lead.id})"><span class="icon"><i class="fas fa-save"></i></span><span>Salvar Alterações</span></button></div></div>
    </div>
  </div>`;

  document.getElementById('leadDetail').innerHTML = html;

  setupWhatsAppAutoConvert();
}

function setupWhatsAppAutoConvert() {
  const phoneInput = document.getElementById('ed-phone');
  const whatsappInput = document.getElementById('ed-whatsapp_link');

  if (phoneInput) {
    phoneInput.addEventListener('blur', function() {
      const digits = this.value.replace(/\D/g, '');
      if (digits.length >= 10) {
        const link = digits.startsWith('55') ? `https://wa.me/${digits}` : `https://wa.me/55${digits}`;
        if (whatsappInput && !whatsappInput.value.trim()) {
          whatsappInput.value = link;
        }
      }
    });
  }

  if (whatsappInput) {
    whatsappInput.addEventListener('blur', function() {
      const val = this.value.trim();
      if (val && !val.startsWith('http://') && !val.startsWith('https://')) {
        const digits = val.replace(/\D/g, '');
        if (digits.length >= 8) {
          const link = digits.startsWith('55') ? `https://wa.me/${digits}` : `https://wa.me/55${digits}`;
          this.value = link;
        }
      }
    });
  }
}

function field(label, id, value, extra, type, placeholder) {
  const val = esc(value||'');
  const ext = extra ? `<div class="control">${extra}</div>` : '';
  const inputType = type || 'text';
  const ph = placeholder || '';
  return `<div class="field is-horizontal">
    <div class="field-label is-normal"><label class="label">${label}</label></div>
    <div class="field-body"><div class="control is-expanded"><input class="input" id="ed-${id}" type="${inputType}" value="${val}" placeholder="${ph}"></div>${ext}</div>
  </div>`;
}

function textarea(label, id, value, rows) {
  return `<div class="field"><label class="label">${label}</label><textarea class="textarea" id="ed-${id}" rows="${rows||2}">${esc(value||'')}</textarea></div>`;
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

window.saveLead = async (id) => {
  const textFields = ['company_name','category','description','website','phone','whatsapp_link','email','instagram','facebook','address','neighborhood','lead_city','state','zipcode','score_reason','opportunity','suggested_service','next_action','auto_notes','manual_notes','commercial_status','lead_response','refusal_reason','owner_name','spoke_with','contact_channel','temperature','tags','owner_name'];
  const boolFields = ['has_website','has_landing_page','has_whatsapp','instagram_active','contacted','interested','refused','proposal_sent','follow_up_scheduled','owner_identified'];
  const updates = {};
  textFields.forEach(f => { const el = document.getElementById(`ed-${f}`); if (el) updates[f] = el.value; });
  boolFields.forEach(f => { const el = document.getElementById(`ed-${f}`); if (el) updates[f] = el.checked; });
  ['follow_up_date','first_contact_date','last_contact_date'].forEach(f => {
    const el = document.getElementById(`ed-${f}`);
    if (el && el.value) updates[f] = el.value;
  });
  const v = document.getElementById('ed-estimated_value');
  if (v && v.value) updates.estimated_value = parseFloat(v.value.replace('R$','').trim()) || null;

  if (updates.whatsapp_link && !updates.whatsapp_link.startsWith('http')) {
    const digits = updates.whatsapp_link.replace(/\D/g, '');
    if (digits.length >= 8) {
      updates.whatsapp_link = digits.startsWith('55') ? `https://wa.me/${digits}` : `https://wa.me/55${digits}`;
    }
  }
  if (!updates.whatsapp_link && updates.phone) {
    const digits = updates.phone.replace(/\D/g, '');
    if (digits.length >= 10) {
      updates.whatsapp_link = digits.startsWith('55') ? `https://wa.me/${digits}` : `https://wa.me/55${digits}`;
    }
  }

  try {
    await api(`/leads/${id}`, { method:'PUT', body: JSON.stringify(updates) });
    showToast('Lead atualizado!', 'success');
  } catch(err) { showToast(`Erro: ${err.message}`, 'danger'); }
};

// ======== CAMPAIGNS PAGE ========
if (document.getElementById('campaignsList')) {
  document.getElementById('newCampaignBtn')?.addEventListener('click', () => {
    document.getElementById('campaignForm').reset();
    showModal('campaignModal');
  });
  document.getElementById('saveCampaign')?.addEventListener('click', async () => {
    const name = document.getElementById('campaignName').value.trim();
    const niche = document.getElementById('campaignNiche').value.trim();
    const city = document.getElementById('campaignCity').value.trim();
    const notes = document.getElementById('campaignNotes').value.trim();
    if (!name||!niche||!city) return showToast('Preencha todos os campos','warning');
    try {
      await api('/campaigns', { method:'POST', body: JSON.stringify({name,niche,city,notes}) });
      showToast('Campanha criada!','success');
      hideModal('campaignModal');
      loadCampaigns();
    } catch(err) { showToast(`Erro: ${err.message}`,'danger'); }
  });
}

async function loadCampaigns() {
  try {
    const camps = await api('/campaigns');
    const container = document.getElementById('campaignsList');
    if (!container) return;
    container.innerHTML = '';
    if (!camps.length) {
      container.innerHTML = '<div class="column is-12"><div class="empty-state"><span class="icon"><i class="fas fa-folder-open"></i></span><p>Nenhuma campanha</p></div></div>';
      return;
    }
    camps.forEach(c => {
      const d = document.createElement('div');
      d.className = 'column is-4';
      d.innerHTML = `<div class="box campaign-card">
        <div class="level"><div class="level-left"><h3 class="title is-5 mb-0">${esc(c.name)}</h3></div>
        <div class="level-right"><span class="tag ${c.status==='active'?'is-success':'is-light'}">${c.status}</span></div></div>
        <p class="is-size-7 has-text-grey mt-2"><span class="icon is-small"><i class="fas fa-tag"></i></span> ${esc(c.niche)} <span class="icon is-small ml-3"><i class="fas fa-city"></i></span> ${esc(c.city)}</p>
        <p class="is-size-7 has-text-grey"><span class="icon is-small"><i class="fas fa-users"></i></span> ${c.lead_count||0} leads</p>
        <div class="buttons are-small mt-3">
          <button class="button is-small is-info is-light" onclick="navigate('leads');setTimeout(()=>{document.getElementById('filterCampaign').value=${c.id};document.getElementById('applyFilters').click()},100)"><i class="fas fa-eye"></i> Leads</button>
          <a class="button is-small is-success is-light" href="/api/export/excel?campaign_id=${c.id}"><i class="fas fa-file-excel"></i></a>
          <button class="button is-small is-danger is-light" onclick="deleteCampaign(${c.id})"><i class="fas fa-trash"></i></button>
        </div></div>`;
      container.appendChild(d);
    });
  } catch(e) {}
}

window.deleteCampaign = async (id) => {
  if (!confirm('Remover campanha e todos os leads?')) return;
  try { await api(`/campaigns/${id}`, {method:'DELETE'}); showToast('Removida','success'); loadCampaigns(); }
  catch(err) { showToast(`Erro: ${err.message}`,'danger'); }
};

// ======== DASHBOARD ========
let qualityChart, statusChart, sourceChart, websiteChart;

async function loadDashboard() {
  try {
    const s = await api('/leads/stats');
    updateMetrics(s);
    renderCharts(s);
  } catch(err) { showToast(`Erro: ${err.message}`,'danger'); }
}

function updateMetrics(s) {
  ['totalLeads','contactedCount','interestedCount','closedCount','proposalsCount','withWebsite','withoutWebsite'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = s[id.replace(/Count$/,'').replace(/([A-Z])/g,'_$1').toLowerCase().replace(/^_/,'')] || 0;
  });
  const cr = document.getElementById('conversionRate');
  if (cr) cr.textContent = `${s.conversion_rate||0}%`;
  // fix mapping
  document.getElementById('totalLeads').textContent = s.total_leads||0;
  document.getElementById('contactedCount').textContent = s.contacted||0;
  document.getElementById('interestedCount').textContent = s.interested||0;
  document.getElementById('closedCount').textContent = s.closed||0;
  document.getElementById('proposalsCount').textContent = s.proposals_sent||0;
  document.getElementById('withWebsite').textContent = s.with_website||0;
  document.getElementById('withoutWebsite').textContent = s.without_website||0;
}

function renderCharts(s) {
  const qCtx = document.getElementById('qualityChart')?.getContext('2d');
  if (qCtx) {
    if (qualityChart) qualityChart.destroy();
    qualityChart = new Chart(qCtx, { type:'doughnut', data: { labels:['Quente','Morno','Frio'], datasets:[{ data:[s.hot_leads||0, s.warm_leads||0, s.cold_leads||0], backgroundColor:['#ff4444','#ffaa00','#00c851'] }] }, options:{ responsive:true, plugins:{ legend:{ position:'bottom' } } } });
  }
  const sCtx = document.getElementById('statusChart')?.getContext('2d');
  if (sCtx && s.status_distribution) {
    if (statusChart) statusChart.destroy();
    const labels = Object.keys(s.status_distribution), values = Object.values(s.status_distribution);
    statusChart = new Chart(sCtx, { type:'bar', data: { labels, datasets:[{ label:'Leads', data:values, backgroundColor:['#485fc7','#00d1b2','#ffdd57','#ff3860','#23d160','#3273dc','#ff470f','#7a7a7a','#f14668','#48c78e','#3e8ed0','#ffa500','#ff0000'] }] }, options:{ responsive:true, indexAxis:'y', plugins:{ legend:{ display:false } }, scales:{ x:{ ticks:{ stepSize:1 } } } } });
  }
  const wCtx = document.getElementById('websiteChart')?.getContext('2d');
  if (wCtx) {
    if (websiteChart) websiteChart.destroy();
    websiteChart = new Chart(wCtx, { type:'doughnut', data: { labels:['Com Site','Sem Site'], datasets:[{ data:[s.with_website||0, s.without_website||0], backgroundColor:['#3273dc','#ff3860'] }] }, options:{ responsive:true, plugins:{ legend:{ position:'bottom' } } } });
  }
  fetchSourceChart();
}

async function fetchSourceChart() {
  try {
    const data = await api('/leads?page_size=1000&sort_by=id');
    const counts = {};
    (data.leads||[]).forEach(l => { const k = l.source||'desconhecida'; counts[k] = (counts[k]||0)+1; });
    const ctx = document.getElementById('sourceChart')?.getContext('2d');
    if (!ctx) return;
    if (sourceChart) sourceChart.destroy();
    sourceChart = new Chart(ctx, { type:'pie', data: { labels:Object.keys(counts), datasets:[{ data:Object.values(counts), backgroundColor:['#485fc7','#00d1b2','#ffdd57','#ff3860','#23d160','#3273dc','#ff470f','#7a7a7a'] }] }, options:{ responsive:true, plugins:{ legend:{ position:'bottom' } } } });
  } catch(e) {}
}

function copyMessage(id) {
  const el = document.getElementById('ed-suggested_message');
  if (!el) return;
  navigator.clipboard.writeText(el.value).then(() => {
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'Copiado!';
    btn.classList.add('is-success');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('is-success'); }, 2000);
  }).catch(() => {
    el.select();
    el.setSelectionRange(0, 99999);
    document.execCommand('copy');
  });
}
