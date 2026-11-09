// Data loader for TKP Generator
// Loads data from Bitrix24 REST API via webhook

const WEBHOOK = 'https://altegrity.bitrix24.ru/rest/1/6wde7t63hxqv5jhb/';

async function loadData() {
    const models = await loadModels();
    const options = await loadOptions();
    const functions = await loadFunctions();
    const components = await loadComponents();
    
    return { models, options, functions, components };
}

async function loadModels() {
    const resp = await fetch(WEBHOOK + 'crm.product.list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            filter: { SECTION_ID: 6055 },
            select: ['ID', 'NAME', 'PRICE', 'DESCRIPTION'],
            order: { NAME: 'ASC' },
            limit: 50
        })
    });
    const data = await resp.json();
    return (data.result || []).map(item => ({
        id: item.ID,
        name: item.NAME,
        price: parseFloat(item.PRICE) || 0
    }));
}

async function loadOptions() {
    const sections = {
        7089: 'Лазер листовой',
        7091: 'Труборез',
        7093: 'Листогиб',
        7095: 'Общие'
    };
    
    const options = [];
    for (const [secId, secName] of Object.entries(sections)) {
        const resp = await fetch(WEBHOOK + 'crm.product.list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filter: { SECTION_ID: secId },
                select: ['ID', 'NAME', 'PRICE', 'DESCRIPTION'],
                limit: 50
            })
        });
        const data = await resp.json();
        for (const item of (data.result || [])) {
            options.push({
                id: item.ID,
                name: item.NAME,
                price: parseFloat(item.PRICE) || 0,
                section_name: secName
            });
        }
    }
    return options;
}

async function loadFunctions() {
    const resp = await fetch(WEBHOOK + 'crm.item.list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            entityTypeId: 1164,
            select: ['id', 'title', 'ufCrm61ShortDesc', 'ufCrm61Category']
        })
    });
    const data = await resp.json();
    return (data.result?.items || []).map(item => ({
        id: item.id,
        name: item.title,
        description: item.ufCrm61ShortDesc || '',
        category: item.ufCrm61Category
    }));
}

async function loadComponents() {
    const resp = await fetch(WEBHOOK + 'crm.item.list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            entityTypeId: 1176,
            select: ['id', 'title', 'ufCrm67_1794089101']
        })
    });
    const data = await resp.json();
    return (data.result?.items || []).map(item => ({
        id: item.id,
        name: item.title,
        country: item.ufCrm67_1794089101 || ''
    }));
}

// Export for use in app.js
if (typeof window !== 'undefined') {
    window.tkpDataLoader = { loadData };
}
