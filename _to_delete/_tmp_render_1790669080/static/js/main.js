// ============================================
// ГЛОБАЛЬНЫЕ ФУНКЦИИ
// ============================================

// Относительный путь — работает и на localhost, и на любом домене
const API_URL = '/api';

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
            removeToken();
            window.location.href = '/login/';
            return null;
        }

        // 204 No Content и пустые ответы
        let data = null;
        if (response.status !== 204) {
            const text = await response.text();
            if (text) {
                try { data = JSON.parse(text); } catch (e) { data = text; }
            }
        }
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        console.error('API Error:', error);
        return { ok: false, error: error.message };
    }
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

function showConfirm(message, callback, title = 'Подтверждение') {
    const modal = document.getElementById('confirmModal');
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalMessage').textContent = message;

    confirmCallback = callback;
    modal.classList.add('active');
}

function closeConfirm() {
    document.getElementById('confirmModal').classList.remove('active');
    confirmCallback = null;
}

// Обработчики кнопок модального окна
document.addEventListener('DOMContentLoaded', () => {
    const cancelBtn = document.getElementById('modalCancel');
    const confirmBtn = document.getElementById('modalConfirm');

    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeConfirm);
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            if (confirmCallback) confirmCallback();
            closeConfirm();
        });
    }

    // Закрытие по клику вне окна
    const modal = document.getElementById('confirmModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeConfirm();
        });
    }
});

// ============================================
// КОРЗИНА — ОБНОВЛЕНИЕ БЕЙДЖА
// ============================================

async function updateCartBadge() {
    const badge = document.getElementById('cartBadge');
    if (!badge) return;

    if (!isAuthenticated()) {
        // Для гостя — берём из localStorage
        const guestCart = JSON.parse(localStorage.getItem('guest_cart') || '[]');
        const count = guestCart.reduce((sum, item) => sum + item.quantity, 0);
        updateBadgeValue(badge, count);
        return;
    }

    try {
        const result = await apiRequest('/cart/');
        if (result && result.ok) {
            updateBadgeValue(badge, result.data.total_items || 0);
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
    const message = `Добавить "${productName}" в корзину?`;

    showConfirm(message, async () => {
        if (!isAuthenticated()) {
            // Для гостя — в localStorage
            addToGuestCart(productId, quantity, productName);
            return;
        }

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

function addToGuestCart(productId, quantity, productName) {
    const cart = JSON.parse(localStorage.getItem('guest_cart') || '[]');
    const existing = cart.find(item => item.product_id === productId);

    if (existing) {
        existing.quantity += quantity;
    } else {
        cart.push({ product_id: productId, quantity, product_name: productName });
    }

    localStorage.setItem('guest_cart', JSON.stringify(cart));
    showToast('Успешно!', `"${productName}" добавлен в корзину`, 'success');
    updateCartBadge();
}

// Перенос гостевой корзины на сервер после входа/регистрации
async function mergeGuestCart() {
    let cart = [];
    try { cart = JSON.parse(localStorage.getItem('guest_cart') || '[]'); } catch (e) {}
    if (!cart.length) return;

    for (const item of cart) {
        await apiRequest('/cart/add/', {
            method: 'POST',
            body: JSON.stringify({ product_id: item.product_id, quantity: item.quantity }),
        });
    }
    localStorage.removeItem('guest_cart');
}

// ============================================
// ВЫХОД ИЗ СИСТЕМЫ
// ============================================

function logout(event) {
    event.preventDefault();

    showConfirm('Вы точно хотите выйти?', () => {
        removeToken();
        showToast('Выход', 'Вы вышли из системы', 'info');
        setTimeout(() => {
            window.location.href = '/';
        }, 500);
    }, 'Выход из системы');
}

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
});
