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
    let interestsLoaded = false;
    const completeButton = document.getElementById('complete-registration');
    
    // Создаем кнопку возврата на первый шаг, если её ещё нет
    if (isRegisterPage && step2 && !document.getElementById('back-to-step-1')) {
        const backButton = document.createElement('button');
        backButton.id = 'back-to-step-1';
        backButton.className = 'btn-back';
        backButton.innerHTML = '<i class="fas fa-arrow-left"></i> Вернуться к данным профиля';
        backButton.addEventListener('click', backToStep1);
        
        // Добавляем кнопку перед заголовком во втором шаге
        const step2Title = step2.querySelector('h1');
        if (step2Title) {
            step2Title.parentNode.insertBefore(backButton, step2Title);
        }
    }
    
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
                
                // Устанавливаем полученные токены в куки с сроком действия и другими параметрами
                if (data.tokens && data.tokens.access) {
                    // Устанавливаем access_token на 1 день
                    document.cookie = `access_token=${data.tokens.access}; path=/; max-age=86400; samesite=Lax`;
                    console.log('Установлен access_token в куки');
                }
                if (data.tokens && data.tokens.refresh) {
                    // Устанавливаем refresh_token на 30 дней
                    document.cookie = `refresh_token=${data.tokens.refresh}; path=/; max-age=2592000; samesite=Lax`;
                    console.log('Установлен refresh_token в куки');
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
    
    // Обработка первого шага регистрации
    function handleFirstStep(e) {
        if (e) {
            e.preventDefault();
        }
        
        clearError();
        
        const firstName = document.getElementById('first_name').value.trim();
        const lastName = document.getElementById('last_name').value.trim();
        const email = document.getElementById('email').value.trim();
        const phone = document.getElementById('phone').value.trim();
        const gender = document.getElementById('gender').value;
        const kurs = document.getElementById('kurs').value;
        const password = document.getElementById('password').value;
        const bio = document.getElementById('bio').value.trim();
        
        // Проверка валидности полей
        if (!firstName || !lastName || !email || !phone || !password) {
            showError('Пожалуйста, заполните все обязательные поля');
            return false;
        }
        
        // Валидация email с помощью регулярного выражения
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showError('Пожалуйста, введите корректный email');
            return false;
        }
        
        // Валидация телефона
        const phoneRegex = /^[0-9]{11}$/;
        if (!phoneRegex.test(phone)) {
            showError('Пожалуйста, введите корректный номер телефона (11 цифр)');
            return false;
        }
        
        // Сохраняем введенные данные
        userData = {
            first_name: firstName,
            last_name: lastName,
            username: email.split('@')[0], // Создаем имя пользователя из первой части email
            email,
            phone,
            gender,
            kurs,
            password,
            bio
        };
        
        // Если все поля валидны, показываем индикатор загрузки
        interestsContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Загрузка интересов...</div>';
        
        // Добавляем класс для анимации исчезновения
        step1.classList.add('fade-out');
        
        setTimeout(() => {
            // После исчезновения первого шага, скрываем его и показываем второй
            step1.style.display = 'none';
            step2.style.display = 'block';
            
            // После короткой задержки добавляем класс fade-in для анимации
            setTimeout(() => {
                step2.classList.add('fade-in');
                
                // Загружаем интересы, если они еще не загружены
                if (!interestsLoaded) {
                    loadInterests();
                } else {
                    // Если интересы уже загружены, обновим состояние кнопки завершения
                    updateCompleteButtonState();
                }
            }, 50);
        }, 400);
        
        return false;
    }
    
    // Загрузка списка интересов с сервера
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
                interestsContainer.innerHTML = '<div class="message info"><i class="fas fa-info-circle"></i> Интересы еще не добавлены администратором.</div>';
                // Если интересов нет, включаем кнопку для пропуска
                if (skipInterestsBtn) {
                    skipInterestsBtn.disabled = false;
                }
                return;
            }
            
            // Очищаем контейнер перед добавлением интересов
            interestsContainer.innerHTML = '';
            
            // Создаем подсказку для выбора интересов, если её еще нет
            if (!document.querySelector('.interests-hint')) {
                const interestsHint = document.createElement('div');
                interestsHint.className = 'interests-hint';
                interestsHint.innerHTML = '<i class="fas fa-info-circle"></i> Выберите интересы, которые вам нравятся. Минимум 1 интерес.';
                interestsContainer.insertAdjacentElement('beforebegin', interestsHint);
            }
            
            // Добавляем интересы с небольшой задержкой для лучшей анимации
            interests.forEach((interest, index) => {
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
                
                // Создаем элемент интереса
                const interestElement = document.createElement('div');
                interestElement.className = 'interest-item';
                interestElement.dataset.id = interest.id;
                interestElement.style.setProperty('--index', index);
                
                interestElement.innerHTML = `
                    ${iconHtml}
                    <div class="interest-name">${interest.name}</div>
                    <div class="interest-description">${interest.description || ''}</div>
                `;
                
                // Добавляем обработчик клика
                interestElement.addEventListener('click', function() {
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
                    
                    // Обновляем состояние кнопки завершения
                    updateCompleteButtonState();
                });
                
                // Добавляем элемент в контейнер
                interestsContainer.appendChild(interestElement);
            });
            
            // Отмечаем, что интересы загружены
            interestsLoaded = true;
            
        } catch (error) {
            console.error('Ошибка при загрузке интересов:', error);
            interestsContainer.innerHTML = '<div class="message error"><i class="fas fa-exclamation-circle"></i> Не удалось загрузить интересы. <button id="retry-interests" class="btn btn-text">Попробовать снова</button></div>';
            
            // Добавляем обработчик для повторной загрузки
            const retryButton = document.getElementById('retry-interests');
            if (retryButton) {
                retryButton.addEventListener('click', function() {
                    interestsContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Загрузка интересов...</div>';
                    loadInterests();
                });
            }
            
            // Разрешаем пропустить выбор интересов в случае ошибки
            if (skipInterestsBtn) {
                skipInterestsBtn.disabled = false;
            }
        }
    }
    
    // Обновление состояния кнопки завершения регистрации
    function updateCompleteButtonState() {
        // Обновляем состояние кнопки в зависимости от количества выбранных интересов
        if (submitInterestsBtn) {
            if (selectedInterests.length > 0) {
                submitInterestsBtn.disabled = false;
                submitInterestsBtn.classList.remove('btn-disabled');
                
                // Добавляем счетчик выбранных интересов
                let countElement = submitInterestsBtn.querySelector('.interest-count');
                if (countElement) {
                    countElement.textContent = selectedInterests.length;
                } else {
                    submitInterestsBtn.innerHTML = `Сохранить <span class="interest-count">${selectedInterests.length}</span>`;
                }
            } else {
                submitInterestsBtn.disabled = true;
                submitInterestsBtn.classList.add('btn-disabled');
                submitInterestsBtn.innerHTML = 'Сохранить';
            }
        }
    }
    
    // Функция для возврата к первому шагу
    function backToStep1() {
        // Удаляем класс fade-in
        step2.classList.remove('fade-in');
        
        setTimeout(() => {
            // Скрываем второй шаг
            step2.style.display = 'none';
            
            // Показываем первый шаг
            step1.style.display = 'block';
            
            // Удаляем класс fade-out для анимации появления
            setTimeout(() => {
                step1.classList.remove('fade-out');
            }, 50);
        }, 400);
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
                console.log('Успешная регистрация', data);
                
                // Сохраняем токены в куки, если они получены от сервера
                if (data.tokens && data.tokens.access) {
                    // Устанавливаем access_token на 1 день
                    document.cookie = `access_token=${data.tokens.access}; path=/; max-age=86400; samesite=Lax`;
                    console.log('Установлен access_token в куки');
                }
                if (data.tokens && data.tokens.refresh) {
                    // Устанавливаем refresh_token на 30 дней
                    document.cookie = `refresh_token=${data.tokens.refresh}; path=/; max-age=2592000; samesite=Lax`;
                    console.log('Установлен refresh_token в куки');
                }
                
                // Перенаправление на главную страницу после успешной регистрации
                window.location.href = '/app';
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
        
        // Инициализация валидации пароля
        setupPasswordValidation();
        setupPasswordToggle();
    }
    
    // Загружаем интересы только при необходимости
    if (isRegisterPage && step2 && window.location.hash === '#step-2') {
        // Если в URL есть хеш #step-2, переходим сразу ко второму шагу
        handleFirstStep();
    }
});

// Проверка email
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}