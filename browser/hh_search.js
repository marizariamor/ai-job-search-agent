// Запускается на открытой странице hh.ru (кандидат уже вошёл в аккаунт).
// Делает несколько поисковых запросов и возвращает компактный список вакансий.
// Используется агентом через инструмент выполнения JavaScript в браузере.

async function hhSearch(params) {
  const url = '/search/vacancy?' + new URLSearchParams(params);
  const html = await (await fetch(url)).text();
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const seen = new Set();
  const out = [];
  doc.querySelectorAll('[data-qa^="vacancy-serp__vacancy"]').forEach(card => {
    const link = card.querySelector('a[href*="/vacancy/"]');
    const id = link && (link.href.match(/vacancy\/(\d+)/) || [])[1];
    if (!id || seen.has(id)) return;
    seen.add(id);
    const q = sel => (card.querySelector(`[data-qa="${sel}"]`)?.innerText || '').trim();
    const salary = (card.innerText.match(/(от |до )?\d[\d\s ]*(–\s?\d[\d\s ]*)?\s?[₽$€]/) || [''])[0];
    out.push({ id, title: q('serp-item__title'), company: q('vacancy-serp__vacancy-employer'), salary: salary.replace(/\s+/g, ' ') });
  });
  return out;
}

const BASE = { schedule: 'remote', search_period: '7', area: '113', salary: '100000' };
const QUERIES = [
  'NAME:("AI" OR "ИИ" OR "LLM" OR "GenAI") AND NAME:(проект* OR project OR внедрен* OR delivery OR аналитик OR analyst)',
  'NAME:(внедрени* OR автоматизац*) AND NAME:(менеджер OR руководитель OR project OR проект* OR аналитик)',
  'NAME:("project manager" OR "менеджер проектов" OR "руководитель проектов" OR "delivery manager")',
  'NAME:("бизнес-аналитик" OR "business analyst" OR "операционный менеджер")',
];

(async () => {
  const results = new Map();
  for (const text of QUERIES) {
    for (const employment of [null, 'part', 'project']) {
      const params = { ...BASE, text };
      if (employment) params.employment = employment;
      for (const v of await hhSearch(params)) if (!results.has(v.id)) results.set(v.id, { ...v, employment: employment || 'full' });
    }
  }
  return [...results.values()];
})();
