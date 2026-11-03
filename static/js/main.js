// ============================================
// ГЛОБАЛЬНЫЕ ФУНКЦИИ
// ============================================

// Относительный путь — работает и на localhost, и на любом домене
const API_URL = '/api';

// Экранирование текста от сервера перед вставкой в innerHTML,
// чтобы название товара или адрес не выполнились как HTML
function esc(v) {
    return String(v == null ? '' : v)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Цвет статуса из базы попадает в style — пропускаем только настоящий #hex
function safeColor(c, fallback = '#6c757d') {
    return /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(c || '') ? c : fallback;
}

const DELIVERY_LABELS = { pickup: 'Самовывоз', courier: 'Курьер', post: 'Почта России' };
const PAYMENT_LABELS = { card: 'Картой онлайн', cash: 'Наличными при получении', card_delivery: 'Картой курьеру' };

// Получить токен из localStorage
function getToken() {
    return localStorage.getItem('access_token');
}

// Сохранить токен
function setToken(token) {
    localStorage.setItem('access_token', token);
}

// Удалить токен
function removeToken() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
}

// Получить пользователя
function getUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
}

// Сохранить пользователя
function setUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

// Проверить авторизацию
function isAuthenticated() {
    return !!getToken();
}

// ============================================
// ЗАПРОСЫ К API
// ============================================

async function apiRequest(endpoint, options = {}, _retried = false) {
    const url = `${API_URL}${endpoint}`;
    const headers = { ...options.headers };

    // Content-Type ставим сами, кроме FormData (браузер добавит boundary)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, { ...options, headers });

        // Токен истёк — пробуем обновить ОДИН раз
        if (response.status === 401 && token && !_retried) {
            const refreshed = await refreshToken();
            if (refreshed) {
                return apiRequest(endpoint, options, true);
            }
            // Обновить не вышло — сессия закончилась. Чистим токены и повторяем
            // запрос уже как гость: публичные страницы (каталог, товар, вход)
            // должны работать. На вход отправляем, только если и гостю нельзя
            // (фоновые запросы вроде счётчика корзины передают silent401: true).
            removeToken();
            const guestResult = await apiRequest(endpoint, options, true);
            if (guestResult && guestResult.status === 401 && !options.silent401) {
                window.location.href = '/login/';
                return null;
            }
            return guestResult;
        }

        // 204 No Content и пустые ответы
        let data = null;
        if (response.status !== 204) {
            const text = await response.text();
            if (text) {
                try { data = JSON.parse(text); } catch (e) { data = text; }
            }
        }
        if (response.status >= 500) notifySiteError();
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        console.error('API Error:', error);
        notifySiteError();
        return { ok: false, error: error.message };
    }
}

// Сбой сервера или нет связи: показываем контакты для обращения (не чаще раза в 20 секунд)
let lastSiteErrorAt = 0;
function notifySiteError() {
    const now = Date.now();
    if (now - lastSiteErrorAt < 20000) return;
    lastSiteErrorAt = now;
    let info = null;
    try { info = JSON.parse(document.getElementById('siteContact').textContent); } catch (e) {}
    if (!info) return;
    const c = info.contacts || {};
    const parts = [c.phone, c.email, c.telegram].filter(Boolean).join(' · ');
    showToast('Сайт работает с ошибкой', parts ? `${info.error_note} ${parts}` : info.error_note, 'error');
}

// Загрузка ВСЕХ страниц пагинированного списка (DRF отдаёт по 20 штук).
// Возвращает { ok, status, data: [...все элементы] } — как apiRequest, но data всегда массив.
async function apiRequestAll(endpoint, maxPages = 50) {
    let items = [];
    let next = endpoint;
    for (let i = 0; next && i < maxPages; i++) {
        const result = await apiRequest(next);
        if (!result || !result.ok) return result;

        const data = result.data;
        if (Array.isArray(data)) return { ok: true, status: result.status, data };

        items = items.concat(data.results || []);
        if (data.next) {
            // next приходит полным URL: http://host/api/orders/?page=2 → /orders/?page=2
            const u = new URL(data.next, window.location.origin);
            next = u.pathname.replace(/^\/api/, '') + u.search;
        } else {
            next = null;
        }
    }
    return { ok: true, status: 200, data: items };
}

// Обновление токена
async function refreshToken() {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) return false;

    try {
        const response = await fetch(`${API_URL}/auth/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh }),
        });

        if (response.ok) {
            const data = await response.json();
            setToken(data.access);
            return true;
        }
    } catch (e) {
        console.error('Refresh error:', e);
    }

    return false;
}

// ============================================
// УВЕДОМЛЕНИЯ (TOAST)
// ============================================

function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    // 'show' обязателен: Bootstrap скрывает .toast без него (display:none)
    toast.className = `toast show ${type}`;

    const titleEl = document.createElement('div');
    titleEl.className = 'toast-title';
    titleEl.textContent = title;

    const msgEl = document.createElement('div');
    msgEl.className = 'toast-message';
    msgEl.textContent = message;

    toast.append(titleEl, msgEl);

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// МОДАЛЬНОЕ ОКНО ПОДТВЕРЖДЕНИЯ
// ============================================

let confirmCallback = null;
let cancelCallback = null;

// onCancel — необязательный обработчик «Отмена» (например, вернуть select в прежнее значение)
function showConfirm(message, callback, title = 'Подтверждение', onCancel = null) {
    const modal = document.getElementById('confirmModal');
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalMessage').textContent = message;

    confirmCallback = callback;
    cancelCallback = onCancel;
    modal.classList.add('active');
}

function closeConfirm() {
    document.getElementById('confirmModal').classList.remove('active');
    confirmCallback = null;
    cancelCallback = null;
}

function cancelConfirm() {
    const cb = cancelCallback;
    closeConfirm();
    if (cb) cb();
}

// Обработчики кнопок модального окна
document.addEventListener('DOMContentLoaded', () => {
    const cancelBtn = document.getElementById('modalCancel');
    const confirmBtn = document.getElementById('modalConfirm');

    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelConfirm);
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            const cb = confirmCallback;
            closeConfirm();
            if (cb) cb();
        });
    }

    // Закрытие по клику вне окна = отмена
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) cancelConfirm();
        });
    }
});

// ============================================
// КОРЗИНА — ОБНОВЛЕНИЕ БЕЙДЖА
// ============================================

async function updateCartBadge() {
    const badge = document.getElementById('cartBadge');
    if (!badge) return;

    // Гость корзиной не пользуется: значок только у авторизованных
    if (!isAuthenticated()) {
        updateBadgeValue(badge, 0);
        return;
    }

    try {
        // фоновый запрос: если сессия истекла, не уводим со страницы на вход
        const result = await apiRequest('/cart/', { silent401: true });
        if (result && result.ok) {
            updateBadgeValue(badge, result.data.total_items || 0);
        } else {
            updateBadgeValue(badge, 0);
        }
    } catch (e) {
        console.error('Cart badge error:', e);
    }
}

function updateBadgeValue(badge, count) {
    badge.textContent = count;
    if (count > 0) {
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// ============================================
// ДОБАВЛЕНИЕ В КОРЗИНУ
// ============================================

async function addToCart(productId, quantity = 1, productName = '') {
    // Гость может только смотреть товары: для корзины нужен аккаунт
    if (!isAuthenticated()) {
        showToast('Нужен вход', 'Чтобы добавить товар в корзину, войдите в аккаунт', 'info');
        setTimeout(() => { window.location.href = '/login/'; }, 1200);
        return;
    }

    const message = `Добавить "${productName}" в корзину?`;

    showConfirm(message, async () => {
        const result = await apiRequest('/cart/add/', {
            method: 'POST',
            body: JSON.stringify({
                product_id: productId,
                quantity: quantity,
            }),
        });

        if (result && result.ok) {
            showToast('Успешно!', `"${productName}" добавлен в корзину`, 'success');
            updateCartBadge();
        } else {
            const error = result?.data?.error || 'Не удалось добавить товар';
            showToast('Ошибка', error, 'error');
        }
    }, 'Добавление в корзину');
}

// Выход — doLogout() в templates/base.html

// ============================================
// ЗАГРУЗКА КАТЕГОРИЙ
// ============================================

async function loadCategories() {
    const list = document.getElementById('categoriesList');
    if (!list) return;

    try {
        const result = await apiRequest('/categories/');

        if (!result || !result.ok) {
            console.warn('Не удалось загрузить категории:', result);
            return;
        }

        // Обрабатываем оба варианта ответа: массив или пагинированный объект
        let categories = [];

        if (Array.isArray(result.data)) {
            categories = result.data;
        } else if (result.data && Array.isArray(result.data.results)) {
            categories = result.data.results;
        } else {
            console.warn('Неожиданный формат ответа категорий:', result.data);
            return;
        }

        // Если категории уже загружены — не дублируем
        if (list.querySelectorAll('.category-link').length > 1) {
            return;
        }

        const current = new URLSearchParams(window.location.search).get('category');
        const all = list.querySelector('.category-link');
        if (all && !current && window.location.pathname === '/') all.classList.add('active');

        document.dispatchEvent(new CustomEvent('categories:loaded', { detail: categories }));

        categories.forEach(cat => {
            if (!cat || !cat.slug || !cat.name) return;

            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `/?category=${encodeURIComponent(cat.slug)}`;
            a.className = 'category-link';
            a.textContent = cat.name;
            if (current === cat.slug) a.classList.add('active');
            li.appendChild(a);
            list.appendChild(li);
        });
    } catch (e) {
        console.error('Ошибка загрузки категорий:', e);
    }
}

// ============================================
// УВЕДОМЛЕНИЯ В РЕАЛЬНОМ ВРЕМЕНИ (WebSocket /ws/notifications/)
// ============================================
// Сервер шлёт сюда «Заказ оформлен», смену статуса заказа и т.п.
// Показываем тост и рассылаем событие shop:notification — страницы
// (например, «Мои заказы») могут на него подписаться и обновиться.

let notifySocket = null;

function connectNotifications(attempt = 0) {
    const token = getToken();
    if (!token || !window.WebSocket) return;

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let ws;
    try {
        ws = new WebSocket(`${proto}://${window.location.host}/ws/notifications/?token=${encodeURIComponent(token)}`);
    } catch (e) {
        return;
    }
    notifySocket = ws;

    ws.onopen = () => { attempt = 0; };
    ws.onmessage = (e) => {
        let data;
        try { data = JSON.parse(e.data); } catch (err) { return; }
        if (data.type === 'notification') {
            showToast(data.title || 'Уведомление', data.message || '', data.level || 'info');
            document.dispatchEvent(new CustomEvent('shop:notification', { detail: data }));
        }
    };
    ws.onerror = () => {};
    ws.onclose = async () => {
        if (notifySocket !== ws || !isAuthenticated() || attempt >= 3) return;
        // соединение могло закрыться из-за истёкшего токена — обновляем и переподключаемся
        await refreshToken();
        setTimeout(() => connectNotifications(attempt + 1), 3000 * (attempt + 1));
    };
}

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

function initSearch() {
    const input = document.getElementById('searchInput');
    const btn = document.getElementById('searchBtn');
    if (!input || !btn) return;

    // Подставляем текущий запрос
    const q = new URLSearchParams(window.location.search).get('search');
    if (q) input.value = q;

    const go = () => {
        const query = input.value.trim();
        if (query) window.location.href = `/?search=${encodeURIComponent(query)}`;
    };
    btn.addEventListener('click', go);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
}

document.addEventListener('DOMContentLoaded', () => {
    initSearch();

    // Обновляем бейдж корзины при загрузке
    updateCartBadge();

    // Загружаем категории
    loadCategories();

    // Уведомления — только для вошедших
    connectNotifications();
});


// Скачивание PDF-чека по заказу (нужен токен, поэтому через fetch, а не простой ссылкой)
async function downloadReceipt(orderId, btn) {
    const original = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Готовлю чек...'; }
    try {
        const token = getToken();
        const response = await fetch(`${API_URL}/orders/${Number(orderId)}/receipt/`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `receipt-${Number(orderId)}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
        showToast('Ошибка', 'Не удалось скачать чек', 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = original; }
    }
}
