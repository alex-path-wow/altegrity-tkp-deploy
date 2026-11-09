// TKP Generator Client App
// Auto-loads data from Bitrix24 iframe

const API_BASE = '';

let models = [];
let options = [];
let companies = [];
let managers = [];
let quoteData = null;

// BX24 integration
function initBX24() {
    if (typeof BX24 === 'undefined') {
        console.warn('BX24 not available, using fallback');
        loadFallbackData();
        return;
    }
    
    BX24.init(() => {
        const placement = BX24.placement.info();
        console.log('Placement:', placement);
        
        if (placement && placement.options && placement.options.ID) {
            const quoteId = placement.options.ID;
            loadQuoteData(quoteId);
        } else {
            loadFallbackData();
        }
    });
}

async function loadQuoteData(quoteId) {
    try {
        const resp = await fetch(`${API_BASE}/api/quote/${quoteId}`);
        quoteData = await resp.json();
        console.log('Quote data:', quoteData);
        
        fillFormFromQuote(quoteData);
    } catch (e) {
        console.error('Failed to load quote:', e);
        loadFallbackData();
    }
}

function fillFormFromQuote(data) {
    if (data.company && data.company.name) {
        document.getElementById('client_company').value = data.company.name;
    }
    if (data.contact && data.contact.name) {
        document.getElementById('client_contact').value = data.contact.name;
    }
    if (data.contact && data.contact.phone) {
        document.getElementById('client_phone').value = data.contact.phone;
    }
    if (data.manager && data.manager.name) {
        document.getElementById('manager_name').value = data.manager.name;
    }
    if (data.manager && data.manager.position) {
        document.getElementById('manager_position').value = data.manager.position;
    }
    if (data.manager && data.manager.email) {
        document.getElementById('manager_email').value = data.manager.email;
    }
    if (data.opportunity > 0) {
        document.getElementById('total_price').value = data.opportunity;
    }
    
    // Try to auto-select model from product rows
    if (data.product_rows && data.product_rows.length > 0) {
        const firstProduct = data.product_rows[0];
        const modelSelect = document.getElementById('model_id');
        for (let opt of modelSelect.options) {
            if (opt.text.includes(firstProduct.product_name) || 
                firstProduct.product_name.includes(opt.text)) {
                opt.selected = true;
                break;
            }
        }
    }
}

async function loadFallbackData() {
    try {
        const [modelsResp, optionsResp] = await Promise.all([
            fetch(`${API_BASE}/api/models`),
            fetch(`${API_BASE}/api/options`)
        ]);
        models = await modelsResp.json();
        options = await optionsResp.json();
        renderForm();
    } catch (e) {
        console.error('Fallback load failed:', e);
    }
}

function renderForm() {
    const modelSelect = document.getElementById('model_id');
    modelSelect.innerHTML = '<option value="">Выберите модель...</option>';
    for (const m of models) {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = `${m.name} — ${m.price.toLocaleString('ru-RU')} ₽`;
        modelSelect.appendChild(opt);
    }
    
    const optionsContainer = document.getElementById('options_container');
    optionsContainer.innerHTML = '';
    
    const sections = {};
    for (const o of options) {
        if (!sections[o.section_name]) sections[o.section_name] = [];
        sections[o.section_name].push(o);
    }
    
    for (const [secName, secOptions] of Object.entries(sections)) {
        const secDiv = document.createElement('div');
        secDiv.className = 'opt-section';
        secDiv.innerHTML = `<h4>${secName}</h4>`;
        
        for (const o of secOptions) {
            const item = document.createElement('label');
            item.className = 'opt-item';
            item.innerHTML = `
                <input type="checkbox" name="options" value="${o.id}">
                <div>
                    <div class="opt-name">${o.name}</div>
                    <div class="opt-desc">${o.description || ''}</div>
                </div>
            `;
            secDiv.appendChild(item);
        }
        
        optionsContainer.appendChild(secDiv);
    }
}

async function generatePDF() {
    const btn = document.getElementById('btn_pdf');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    
    btn.disabled = true;
    loading.classList.add('show');
    result.classList.remove('show');
    
    const formData = new FormData();
    formData.append('model_id', document.getElementById('model_id').value);
    formData.append('client_company', document.getElementById('client_company').value);
    formData.append('client_contact', document.getElementById('client_contact').value);
    formData.append('client_phone', document.getElementById('client_phone').value);
    formData.append('manager_name', document.getElementById('manager_name').value);
    formData.append('manager_position', document.getElementById('manager_position').value);
    formData.append('manager_email', document.getElementById('manager_email').value);
    formData.append('power_kw', document.getElementById('power_kw').value);
    formData.append('source', document.getElementById('source').value);
    formData.append('total_price', document.getElementById('total_price').value || '0');
    
    const checkedOptions = document.querySelectorAll('input[name="options"]:checked');
    for (const cb of checkedOptions) {
        formData.append('selected_options', cb.value);
    }
    
    try {
        const resp = await fetch(`${API_BASE}/generate/pdf`, {
            method: 'POST',
            body: formData
        });
        
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        
        result.innerHTML = `
            <p>PDF готов!</p>
            <a href="${url}" download="TKP_${new Date().toISOString().slice(0,10)}.pdf">Скачать PDF</a>
        `;
        result.classList.add('show');
    } catch (e) {
        result.innerHTML = `<p style="color:red">Ошибка: ${e.message}</p>`;
        result.classList.add('show');
    } finally {
        btn.disabled = false;
        loading.classList.remove('show');
    }
}

function previewHTML() {
    alert('HTML preview not implemented yet');
}

// Initialize
document.addEventListener('DOMContentLoaded', initBX24);
