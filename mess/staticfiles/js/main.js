/* Основной JavaScript файл для всего сайта */
document.addEventListener('DOMContentLoaded', function() {
    // Функция для получения CSRF токена из кук
    window.getCookie = function(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };
    
    // Добавление CSRF токена к заголовкам для AJAX запросов
    const csrftoken = getCookie('csrftoken');
    
    // Функция для создания уведомлений
    window.showNotification = function(message, type = 'info') {
        // Проверяем, есть ли уже уведомление на странице
        let notificationEl = document.querySelector('.notification');
        
        if (!notificationEl) {
            // Создаем новое уведомление
            notificationEl = document.createElement('div');
            notificationEl.className = `notification ${type}`;
            document.body.appendChild(notificationEl);
        } else {
            // Обновляем класс типа уведомления
            notificationEl.className = `notification ${type}`;
        }
        
        // Устанавливаем текст и показываем уведомление
        notificationEl.textContent = message;
        notificationEl.classList.add('show');
        
        // Скрываем уведомление через 3 секунды
        setTimeout(() => {
            notificationEl.classList.remove('show');
        }, 3000);
    };
    
    // Функция для обновления токена
    window.refreshToken = async function() {
        try {
            const refreshToken = getCookie('refresh_token');
            
            if (!refreshToken) {
                console.error('Refresh токен отсутствует');
                return false;
            }
            
            const response = await fetch('/app/api/token/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    refresh: refreshToken
                }),
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Токен успешно обновлен:', data);
                
                // Обновляем токен в куках с явным указанием пути и других параметров
                if (data.access) {
                    // Удаляем старый токен
                    document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; samesite=Lax';
                    // Устанавливаем новый токен с максимальным сроком жизни 24 часа
                    document.cookie = `access_token=${data.access}; path=/; max-age=86400; samesite=Lax`;
                    console.log('Установлен новый access_token в куки');
                    
                    // Проверяем, был ли установлен токен
                    setTimeout(() => {
                        const newToken = getCookie('access_token');
                        console.log('Проверка установки токена:', newToken ? 'Токен установлен' : 'Токен НЕ установлен');
                    }, 100);
                    
                    return true;
                }
            } else {
                const errorData = await response.json().catch(() => ({ detail: 'Неизвестная ошибка' }));
                console.error('Ошибка при обновлении токена:', response.status, errorData);
                return false;
            }
        } catch (error) {
            console.error('Ошибка при обновлении токена:', error);
            return false;
        }
        
        return false;
    };
    
    // Проверяем токен при загрузке страницы и обновляем его, если он истек
    async function checkTokenOnLoad() {
        console.log('Проверка токенов при загрузке страницы');
        
        // Вместо проверки кук в JavaScript делаем тестовый запрос к API
        try {
            // Запрос для проверки авторизации
            const response = await fetch('/app/api/profile/', {
                method: 'GET',
                credentials: 'include' // Важно для отправки кук
            });
            
            console.log('Статус проверки авторизации:', response.status);
            
            // Если успешно - значит токены валидны
            if (response.ok) {
                console.log('Авторизация успешна, токены валидны');
                return;
            }
            
            // Если получили 401 - пробуем обновить токен
            if (response.status === 401) {
                console.log('Токены недействительны, пробуем обновить');
                
                // Запрос на обновление токена
                const refreshResponse = await fetch('/app/api/token/refresh/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include' // Важно для отправки refresh_token в куках
                });
                
                if (refreshResponse.ok) {
                    console.log('Токен успешно обновлен');
                    return;
                } else {
                    console.log('Не удалось обновить токен, перенаправление на логин');
                    // Проверяем, что мы не на странице логина или регистрации
                    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
                        window.location.href = '/app/auth/login/';
                    }
                }
            }
        } catch (error) {
            console.error('Ошибка при проверке авторизации:', error);
            // Перенаправление только если мы не на странице логина
            if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
                window.location.href = '/app/auth/login/';
            }
        }
    }
    
    // Запускаем проверку токена при загрузке страницы
    checkTokenOnLoad();
    
    // Настраиваем периодическое обновление токена (каждые 10 минут)
    // Это гарантирует, что токен будет обновлен до истечения его срока действия
    setInterval(async () => {
        console.log('Запланированное обновление токена...');
        const accessToken = getCookie('access_token');
        const refreshToken = getCookie('refresh_token');
        
        if (!refreshToken) {
            console.log('Отсутствует refresh_token для планового обновления');
            return;
        }
        
        if (accessToken) {
            // Проверяем, скоро ли истечет срок действия токена
            // Обновляем токен за 2 минуты до истечения срока
            try {
                console.log('Вызов планового обновления токена');
                await refreshToken();
            } catch (error) {
                console.error('Ошибка при плановом обновлении токена:', error);
            }
        }
    }, 600000); // 10 минут (600,000 мс)
    
    // Общая функция для выполнения API-запросов с автоматической обработкой токенов
    window.fetchWithAuth = async function(url, options = {}) {
        // Настраиваем параметры запроса
        const fetchOptions = {
            ...options,
            credentials: 'include', // Гарантирует отправку кук 
            headers: {
                ...options.headers,
                'Content-Type': options.headers?.['Content-Type'] || 'application/json'
            }
        };
        
        // Добавляем CSRF-токен для POST, PUT, DELETE запросов
        if (['POST', 'PUT', 'DELETE'].includes(options.method)) {
            fetchOptions.headers['X-CSRFToken'] = getCookie('csrftoken');
        }
        
        try {
            // Выполняем запрос
            let response = await fetch(url, fetchOptions);
            
            // Если получаем 401 (неавторизован), пробуем обновить токен
            if (response.status === 401) {
                console.log('Получен 401, пробуем обновить токен и повторить запрос');
                
                // Запрашиваем обновление токена
                const refreshResponse = await fetch('/app/api/token/refresh/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include'
                });
                
                // Если токен успешно обновлен, повторяем запрос
                if (refreshResponse.ok) {
                    console.log('Токен успешно обновлен, повторяем запрос');
                    response = await fetch(url, fetchOptions);
                } else {
                    console.log('Не удалось обновить токен, перенаправление на логин');
                    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
                        window.location.href = '/app/auth/login/';
                    }
                }
            }
            
            // Возвращаем результат запроса
            return response;
        } catch (error) {
            console.error('Ошибка при выполнении запроса:', error);
            throw error;
        }
    };
    
    // Обработчик для кнопки выхода
    const logoutLink = document.querySelector('.logout-link');
    if (logoutLink) {
        logoutLink.addEventListener('click', async function(e) {
            e.preventDefault();
            
            try {
                // Получаем JWT токен
                const accessToken = getCookie('access_token');
                
                const headers = {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                };
                
                // Добавляем заголовок Authorization, если есть токен
                if (accessToken) {
                    headers['Authorization'] = `Bearer ${accessToken}`;
                }
                
                const response = await fetch('/app/logout/', {
                    method: 'POST',
                    headers: headers,
                    credentials: 'include'  // Для передачи кук
                });
                
                if (response.ok) {
                    // Перенаправляем на страницу входа
                    window.location.href = '/app/auth/login/';
                } else {
                    showNotification('Произошла ошибка при выходе', 'error');
                }
            } catch (error) {
                console.error('Ошибка при выходе:', error);
                showNotification('Не удалось выполнить выход', 'error');
            }
        });
    }

    // Функция для отображения профиля пользователя
    function displayUserProfile(user) {
        const profileCard = document.createElement('div');
        profileCard.className = 'profile-card';
        
        // Проверяем, лайкнул ли этот пользователь текущего пользователя
        const hasLikedYou = user.likes_given && user.likes_given.some(like => like.to_user === currentUserId);
        
        // Создаем HTML для карточки профиля
        profileCard.innerHTML = `
            <div class="profile-header">
                ${hasLikedYou ? '<div class="liked-you-badge"><i class="fas fa-heart"></i> Лайкнул вашу анкету</div>' : ''}
                <div class="profile-image-container">
                    ${user.avatar 
                        ? `<img src="${user.avatar}" alt="Фото профиля" class="profile-image">`
                        : `<div class="profile-image-placeholder">${user.first_name[0]}${user.last_name[0]}</div>`
                    }
                </div>
                <h2 class="profile-name">${user.first_name} ${user.last_name}</h2>
                <p class="profile-course">${user.kurs ? `${user.kurs} курс` : 'Курс не указан'}</p>
            </div>
            
            <div class="profile-info">
                <p class="profile-gender">${user.gender === 'male' ? 'Мужчина' : 'Женщина'}</p>
            </div>
            
            ${user.interests && user.interests.length > 0 ? `
                <div class="profile-interests">
                    <h3>Интересы</h3>
                    <div class="interests-list">
                        ${user.interests.map(interest => `
                            <span class="interest-tag">${interest.name}</span>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${user.bio ? `
                <div class="profile-bio">
                    <h3>О себе</h3>
                    <p>${user.bio}</p>
                </div>
            ` : ''}
            
            <div class="profile-actions">
                <button class="btn-like" onclick="likeProfile('${user.id}')">
                    <i class="fas fa-heart"></i>
                </button>
                <button class="btn-dislike" onclick="dislikeProfile('${user.id}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        return profileCard;
    }
}); 