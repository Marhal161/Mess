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
}); 