document.addEventListener('DOMContentLoaded', function() {
    // Определяем, на какой странице мы находимся
    const isLoginPage = window.location.pathname.includes('/login');
    const isRegisterPage = window.location.pathname.includes('/register');
    
    // Получаем элементы форм
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const errorMessage = document.getElementById('error-message');
    const interestsErrorMessage = document.getElementById('interests-error-message');
    
    // Элементы для двухшаговой регистрации
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const interestsContainer = document.getElementById('interests-container');
    const skipInterestsBtn = document.getElementById('skip-interests');
    const submitInterestsBtn = document.getElementById('submit-interests');
    
    // Временно храним данные пользователя при регистрации
    let userData = {};
    let selectedInterests = [];
    
    // Функция для отображения ошибок
    function showError(message, element = errorMessage) {
        element.textContent = message;
        element.classList.add('show');
    }
    
    // Функция для очистки ошибок
    function clearError(element = errorMessage) {
        element.textContent = '';
        element.classList.remove('show');
    }
    
    // Функция для получения CSRF токена из кук
    function getCookie(name) {
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
    }
    
    // Функция для обработки входа
    async function handleLogin(e) {
        e.preventDefault();
        clearError();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        // Валидация на стороне клиента
        if (!email || !password) {
            showError('Пожалуйста, заполните все поля');
            return;
        }
        
        try {
            // Получаем CSRF токен
            const csrftoken = getCookie('csrftoken');
            
            const response = await fetch('/app/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ email, password }),
                credentials: 'include'
            });
            
            const data = await response.json();
            console.log('Ответ от сервера при входе:', data);
            
            if (response.ok && data.success) {
                console.log('Успешный вход, перенаправление на главную страницу');
                
                // Устанавливаем полученные токены в куки
                if (data.tokens && data.tokens.access) {
                    document.cookie = `access_token=${data.tokens.access}; path=/`;
                }
                if (data.tokens && data.tokens.refresh) {
                    document.cookie = `refresh_token=${data.tokens.refresh}; path=/`;
                }
                
                // Перенаправление на главную страницу после успешного входа
                window.location.href = '/app';
            } else {
                // Отображение ошибки
                showError(data.detail || data.message || 'Ошибка входа');
            }
        } catch (error) {
            showError('Произошла ошибка при отправке запроса');
            console.error(error);
        }
    }
    
    // Функция для обработки первого шага регистрации
    async function handleFirstStep(e) {
        e.preventDefault();
        clearError();
        
        // Получение данных формы
        userData = {
            first_name: document.getElementById('first_name').value,
            last_name: document.getElementById('last_name').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            gender: document.getElementById('gender').value,
            kurs: document.getElementById('kurs').value,
            password: document.getElementById('password').value,
            bio: document.getElementById('bio').value
        };
        
        // Валидация на стороне клиента
        if (!userData.first_name || !userData.last_name || !userData.email || 
            !userData.phone || !userData.password) {
            showError('Пожалуйста, заполните все обязательные поля');
            return;
        }
        
        // Проверка формата телефона
        if (!/^[0-9]{11}$/.test(userData.phone)) {
            showError('Номер телефона должен содержать 11 цифр');
            return;
        }
        
        // Проверка пароля на все требования
        const hasLength = userData.password.length >= 8;
        const hasLowercase = /[a-z]/.test(userData.password);
        const hasUppercase = /[A-Z]/.test(userData.password);
        const hasNumber = /[0-9]/.test(userData.password);
        const hasSpecial = /[^A-Za-z0-9]/.test(userData.password);
        
        if (!(hasLength && hasLowercase && hasUppercase && hasNumber && hasSpecial)) {
            showError('Пароль не соответствует всем требованиям безопасности');
            return;
        }
        
        // Переход ко второму шагу - выбор интересов
        step1.style.display = 'none';
        step2.style.display = 'block';
        step2.classList.add('fade-in');
        
        // Загружаем интересы с сервера
        loadInterests();
    }
    
    // Функция для загрузки интересов с сервера
    async function loadInterests() {
        try {
            // Получаем CSRF токен
            const csrftoken = getCookie('csrftoken');
            
            const response = await fetch('/app/api/interests/', {
                headers: {
                    'X-CSRFToken': csrftoken
                },
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('Не удалось загрузить интересы');
            }
            
            const interests = await response.json();
            
            if (interests.length === 0) {
                interestsContainer.innerHTML = '<p class="no-interests">Интересы еще не добавлены администратором.</p>';
                return;
            }
            
            // Отображаем интересы
            interestsContainer.innerHTML = interests.map(interest => {
                // Проверяем, есть ли иконка и как ее отображать
                let iconHtml;
                if (!interest.icon) {
                    // Если иконки нет, используем эмодзи по умолчанию
                    iconHtml = '<span class="interest-icon">🔍</span>';
                } else if (interest.icon.startsWith('http') || interest.icon.startsWith('/media/')) {
                    // Если это путь к изображению
                    iconHtml = `<img src="${interest.icon}" alt="${interest.name}" class="interest-icon-img">`;
                } else {
                    // Если это эмодзи или символ
                    iconHtml = `<span class="interest-icon">${interest.icon}</span>`;
                }
                
                return `
                    <div class="interest-item" data-id="${interest.id}">
                        ${iconHtml}
                        <div class="interest-name">${interest.name}</div>
                        <div class="interest-description">${interest.description || ''}</div>
                    </div>
                `;
            }).join('');
            
            // Добавляем обработчики событий для выбора интересов
            document.querySelectorAll('.interest-item').forEach(item => {
                item.addEventListener('click', function() {
                    const interestId = parseInt(this.dataset.id);
                    
                    if (this.classList.contains('selected')) {
                        // Убираем из выбранных
                        this.classList.remove('selected');
                        selectedInterests = selectedInterests.filter(id => id !== interestId);
                    } else {
                        // Добавляем к выбранным
                        this.classList.add('selected');
                        selectedInterests.push(interestId);
                    }
                });
            });
            
        } catch (error) {
            console.error('Ошибка при загрузке интересов:', error);
            interestsContainer.innerHTML = '<p class="error">Не удалось загрузить интересы. Попробуйте позже.</p>';
        }
    }
    
    // Функция для завершения регистрации пользователя с выбранными интересами
    async function completeRegistration(withInterests = true) {
        clearError(interestsErrorMessage);
        
        // Добавляем интересы к данным пользователя
        if (withInterests && selectedInterests.length > 0) {
            userData.interests = selectedInterests;
        }
        
        try {
            // Получаем CSRF токен
            const csrftoken = getCookie('csrftoken');
            
            const response = await fetch('/app/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(userData),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                console.log('Успешная регистрация, перенаправление на главную страницу');
                // Перенаправление на главную страницу после успешной регистрации
                window.location.href = '/app';  // Изменено с пустой строки на '/app'
            } else {
                // Отображение ошибки и возврат к первому шагу
                step2.style.display = 'none';
                step1.style.display = 'block';
                
                const errorMsg = data.errors 
                    ? (typeof data.errors === 'string' ? data.errors : Object.values(data.errors).flat().join(', '))
                    : (data.message || 'Ошибка регистрации');
                showError(errorMsg);
            }
        } catch (error) {
            step2.style.display = 'none';
            step1.style.display = 'block';
            showError('Произошла ошибка при отправке запроса');
            console.error(error);
        }
    }
    
    // Функция для обработки кнопки просмотра пароля
    function setupPasswordToggle() {
        const passwordToggle = document.getElementById('password-toggle');
        const passwordInput = document.getElementById('password');
        
        if (passwordToggle && passwordInput) {
            const showIcon = passwordToggle.querySelector('.show-password');
            const hideIcon = passwordToggle.querySelector('.hide-password');
            
            passwordToggle.addEventListener('click', function() {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    showIcon.style.display = 'none';
                    hideIcon.style.display = 'inline';
                } else {
                    passwordInput.type = 'password';
                    showIcon.style.display = 'inline';
                    hideIcon.style.display = 'none';
                }
            });
        }
    }
    
    // Функция для валидации пароля в реальном времени
    function setupPasswordValidation() {
        const passwordInput = document.getElementById('password');
        const strengthBar = document.getElementById('strength-bar');
        const requirements = document.getElementById('password-requirements');
        
        if (passwordInput && (strengthBar || requirements)) {
            // Начальная проверка (если поле уже заполнено)
            validatePassword(passwordInput.value);
            
            // Обработка ввода
            passwordInput.addEventListener('input', function() {
                validatePassword(this.value);
            });
            
            // Функция валидации пароля
            function validatePassword(password) {
                // Проверка требований
                const hasLength = password.length >= 8;
                const hasLowercase = /[а-яa-z]/.test(password);
                const hasUppercase = /[А-ЯA-Z]/.test(password);
                const hasNumber = /[0-9]/.test(password);
                const hasSpecial = /[^A-Za-zА-Яа-я0-9]/.test(password);
                
                // Обновление индикатора сложности
                if (strengthBar) {
                    // Расчет сложности
                    let strength = 0;
                    if (hasLength) strength += 1;
                    if (hasLowercase) strength += 1;
                    if (hasUppercase) strength += 1;
                    if (hasNumber) strength += 1;
                    if (hasSpecial) strength += 1;
                    
                    // Сначала очищаем все inline стили (если они были)
                    strengthBar.style.width = '';
                    strengthBar.style.backgroundColor = '';
                    
                    // Удаляем все предыдущие классы
                    strengthBar.className = 'strength-bar';
                    
                    // Добавляем новый класс в зависимости от сложности
                    if (password.length === 0) {
                        strengthBar.style.width = '0';
                    } else if (strength === 1) {
                        strengthBar.classList.add('strength-weak');
                    } else if (strength === 2) {
                        strengthBar.classList.add('strength-fair');
                    } else if (strength === 3) {
                        strengthBar.classList.add('strength-good');
                    } else if (strength === 4) {
                        strengthBar.classList.add('strength-strong');
                    } else {
                        strengthBar.classList.add('strength-very-strong');
                    }
                }
                
                // Обновление списка требований
                if (requirements) {
                    updateRequirementStatus('length', hasLength);
                    updateRequirementStatus('lowercase', hasLowercase);
                    updateRequirementStatus('uppercase', hasUppercase);
                    updateRequirementStatus('number', hasNumber);
                    updateRequirementStatus('special', hasSpecial);
                }
            }
        }
    }
    
    // Вспомогательная функция для обновления статуса требования
    function updateRequirementStatus(requirementName, isMet) {
        const requirement = document.querySelector(`.requirement[data-requirement="${requirementName}"]`);
        if (requirement) {
            if (isMet) {
                requirement.classList.add('met');
                requirement.classList.remove('not-met');
            } else {
                requirement.classList.add('not-met');
                requirement.classList.remove('met');
            }
        }
    }
    
    // Добавляем обработчики событий для форм и кнопок
    if (isLoginPage && loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (isRegisterPage) {
        if (registerForm) {
            registerForm.addEventListener('submit', handleFirstStep);
        }
        
        if (skipInterestsBtn) {
            skipInterestsBtn.addEventListener('click', function() {
                completeRegistration(false);
            });
        }
        
        if (submitInterestsBtn) {
            submitInterestsBtn.addEventListener('click', function() {
                completeRegistration(true);
            });
        }
        
        // Вызываем инициализацию валидации только на странице регистрации
        setupPasswordValidation();
    }
    
    // Если мы на странице регистрации и видим второй шаг, загрузим интересы
    if (isRegisterPage && step2 && step2.style.display !== 'none') {
        loadInterests();
    }
    
    // Вызываем инициализацию на всех страницах
    setupPasswordToggle();
});