document.addEventListener('DOMContentLoaded', function() {
    // Элементы страницы профиля
    const profileView = document.getElementById('profile-view');
    const profileEdit = document.getElementById('profile-edit');
    const editProfileBtn = document.getElementById('edit-profile-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const changePasswordBtn = document.getElementById('change-password-btn');
    const deleteAccountBtn = document.getElementById('delete-account-btn');
    
    // Элементы модальных окон
    const passwordModal = document.getElementById('password-modal');
    const closePasswordModal = document.getElementById('close-password-modal');
    const deleteModal = document.getElementById('delete-modal');
    const closeDeleteModal = document.getElementById('close-delete-modal');
    const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    
    // Элементы модального окна редактирования аватара
    const avatarModal = document.getElementById('avatar-edit-modal');
    const closeAvatarModal = document.getElementById('close-avatar-modal');
    const cancelAvatarBtn = document.getElementById('cancel-avatar-btn');
    const saveAvatarBtn = document.getElementById('save-avatar-btn');
    const avatarEditorContainer = document.getElementById('avatar-editor-container');
    
    // Формы
    const profileEditForm = document.getElementById('profile-edit-form');
    const changePasswordForm = document.getElementById('change-password-form');
    
    // Загрузка аватара
    const avatarUpload = document.getElementById('avatar-upload');
    const avatarPreview = document.getElementById('avatar-preview');
    
    // Глобальные переменные для редактора аватара
    let profileData = {};
    let availableInterests = [];
    let editedAvatarData = null;
    let avatarZoomLevel = 100;
    let imageRotation = 0; // Добавляем глобальную переменную для хранения угла поворота
    
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
    
    // Функция для отображения уведомлений
    function showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = 'notification';
        notification.classList.add(type);
        notification.style.display = 'block';
        
        setTimeout(function() {
            notification.style.display = 'none';
        }, 3000);
    }
    
    // Функция для валидации пароля
    function validatePassword(password) {
        const hasLength = password.length >= 8;
        const hasLowercase = /[а-яa-z]/.test(password);
        const hasUppercase = /[А-ЯA-Z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        const hasSpecial = /[^A-Za-zА-Яа-я0-9]/.test(password);
        
        updateRequirementStatus('length', hasLength);
        updateRequirementStatus('lowercase', hasLowercase);
        updateRequirementStatus('uppercase', hasUppercase);
        updateRequirementStatus('number', hasNumber);
        updateRequirementStatus('special', hasSpecial);
        
        // Обновление индикатора сложности
        const strengthBar = document.getElementById('strength-bar');
        if (strengthBar) {
            let strength = 0;
            if (hasLength) strength += 1;
            if (hasLowercase) strength += 1;
            if (hasUppercase) strength += 1;
            if (hasNumber) strength += 1;
            if (hasSpecial) strength += 1;
            
            strengthBar.style.width = '';
            strengthBar.style.backgroundColor = '';
            strengthBar.className = 'strength-bar';
            
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
        
        return hasLength && hasLowercase && hasUppercase && hasNumber && hasSpecial;
    }
    
    // Функция для обновления статуса требования
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
    
    // Функция для загрузки данных профиля
    async function loadProfileData() {
        try {
            console.log('Загрузка данных профиля...');
            
            // Используем новую функцию fetchWithAuth для запроса профиля
            const response = await window.fetchWithAuth('/app/api/profile/', {
                method: 'GET'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    console.log('Ошибка авторизации при загрузке профиля');
                    window.location.href = '/app/auth/login/';
                    return;
                }
                throw new Error('Ошибка загрузки профиля: ' + response.status);
            }
            
            const data = await response.json();
            console.log('Данные профиля получены:', data);
            
            // Загружаем количество лайков
            const likesResponse = await window.fetchWithAuth('/app/api/profile/likes-count/');
            
            if (likesResponse.ok) {
                const likesData = await likesResponse.json();
                console.log('Данные о лайках:', likesData);
                // Добавляем количество лайков к данным профиля
                data.likes_count = likesData.count;
            } else {
                console.error('Ошибка при загрузке лайков:', likesResponse.status);
            }
            
            profileData = data;
            console.log('Обработанные данные профиля:', profileData);
            
            // Заполняем данные на странице
            updateProfileView();
            
            // Загружаем интересы для формы редактирования
            await loadInterests();
            
        } catch (error) {
            console.error('Ошибка при загрузке профиля:', error);
            showNotification('Не удалось загрузить данные профиля', 'error');
        }
    }
    
    // Функция для обновления отображения профиля
    function updateProfileView() {
        console.log('Полные данные профиля:', profileData);

        // Имя и фамилия
        document.getElementById('profile-name').textContent = `${profileData.first_name} ${profileData.last_name}`;
        
        // Username
        document.getElementById('profile-username').textContent = `@${profileData.username}`;
        
        // Email
        document.getElementById('profile-email').textContent = profileData.email;
        
        // Телефон
        document.getElementById('profile-phone').textContent = profileData.phone ? formatPhoneNumber(profileData.phone) : 'Не указан';
        
        // Пол
        const genderText = profileData.gender === 'male' ? 'Мужчина' : 
                          profileData.gender === 'female' ? 'Женщина' : 'Не указан';
        document.getElementById('profile-gender').textContent = genderText;
        
        // Курс
        const kursText = profileData.kurs ? `${profileData.kurs} курс` : 'Не указан';
        document.getElementById('profile-kurs').textContent = kursText;
        
        // Количество лайков
        const likesElement = document.getElementById('profile-likes-count');
        if (likesElement) {
            let likesCount = 0;
            
            // Проверяем все возможные форматы данных о лайках
            if (typeof profileData.likes_count === 'number') {
                likesCount = profileData.likes_count;
            } else if (typeof profileData.likes_received_count === 'number') {
                likesCount = profileData.likes_received_count;
            } else if (Array.isArray(profileData.likes_received)) {
                likesCount = profileData.likes_received.length;
            } else if (profileData.likes && typeof profileData.likes === 'number') {
                likesCount = profileData.likes;
            }
            
            console.log('Подсчитанное количество лайков:', likesCount);
            
            likesElement.innerHTML = `
                <div class="likes-info">
                    <i class="fas fa-heart"></i>
                    <span>${likesCount} ${getLikesWordForm(likesCount)}</span>
                </div>
            `;
        }
        
        // Био
        const bioElement = document.getElementById('profile-bio');
        if (profileData.bio) {
            bioElement.textContent = profileData.bio;
        } else {
            bioElement.innerHTML = '<p class="placeholder">Информация о себе не указана</p>';
        }
        
        // Аватар
        const avatarElement = document.getElementById('profile-avatar');
        if (profileData.avatar) {
            avatarElement.innerHTML = `<img src="${profileData.avatar}" alt="Фото профиля">`;
        } else {
            const initials = `${profileData.first_name.charAt(0)}${profileData.last_name.charAt(0)}`;
            avatarElement.innerHTML = `<div class="avatar-placeholder">${initials}</div>`;
        }
        
        // Интересы
        const interestsElement = document.getElementById('profile-interests');
        if (profileData.interests && profileData.interests.length > 0) {
            interestsElement.innerHTML = profileData.interests.map(interest => 
                `<span class="interest-tag">${interest.name}</span>`
            ).join('');
        } else {
            interestsElement.innerHTML = '<p class="placeholder">Интересы не указаны</p>';
        }
        
        // Заполняем форму редактирования
        document.getElementById('edit-first-name').value = profileData.first_name || '';
        document.getElementById('edit-last-name').value = profileData.last_name || '';
        document.getElementById('edit-email').value = profileData.email || '';
        document.getElementById('edit-phone').value = profileData.phone || '';
        document.getElementById('edit-bio').value = profileData.bio || '';
        document.getElementById('edit-gender').value = profileData.gender || '';
        document.getElementById('edit-kurs').value = profileData.kurs || '';
        
        // Предпросмотр аватара
        if (profileData.avatar) {
            avatarPreview.innerHTML = `<img src="${profileData.avatar}" alt="Аватар">`;
        } else {
            avatarPreview.innerHTML = '<div class="placeholder">Нет фото</div>';
        }
    }
    
    // Функция для правильного склонения слова "лайк"
    function getLikesWordForm(number) {
        const cases = [2, 0, 1, 1, 1, 2];
        const titles = ['лайк', 'лайка', 'лайков'];
        return titles[(number % 100 > 4 && number % 100 < 20) ? 2 : cases[(number % 10 < 5) ? number % 10 : 5]];
    }
    
    // Функция для загрузки интересов с сервера
    async function loadInterests() {
        try {
            console.log('Загрузка доступных интересов...');
            
            // Используем fetchWithAuth для запроса интересов
            const response = await window.fetchWithAuth('/app/api/interests/');
            
            if (!response.ok) {
                throw new Error('Ошибка загрузки интересов: ' + response.status);
            }
            
            availableInterests = await response.json();
            console.log('Интересы загружены:', availableInterests);
            
            // Обновляем отображение интересов в профиле
            updateInterestsView();
            
        } catch (error) {
            console.error('Ошибка при загрузке интересов:', error);
            showNotification('Не удалось загрузить список интересов', 'error');
        }
    }
    
    // Функция для обновления отображения интересов в форме редактирования
    function updateInterestsView() {
        const interestsContainer = document.getElementById('edit-interests');
        
        // Получаем ID интересов пользователя
        const userInterestIds = profileData.interests ? profileData.interests.map(i => i.id) : [];
        
        interestsContainer.innerHTML = availableInterests.map(interest => {
            const isSelected = userInterestIds.includes(interest.id);
            const selectedClass = isSelected ? 'selected' : '';
            
            let iconHtml;
            if (!interest.icon) {
                iconHtml = '<span class="interest-icon">🔍</span>';
            } else if (interest.icon.startsWith('http') || interest.icon.startsWith('/media/')) {
                iconHtml = `<img src="${interest.icon}" alt="${interest.name}" class="interest-icon-img">`;
            } else {
                iconHtml = `<span class="interest-icon">${interest.icon}</span>`;
            }
            
            return `
                <div class="interest-item ${selectedClass}" data-id="${interest.id}">
                    ${iconHtml}
                    <div class="interest-name">${interest.name}</div>
                </div>
            `;
        }).join('');
        
        // Добавляем обработчики событий для выбора интересов
        document.querySelectorAll('#edit-interests .interest-item').forEach(item => {
            item.addEventListener('click', function() {
                this.classList.toggle('selected');
            });
        });
    }
    
    // Функция для форматирования номера телефона
    function formatPhoneNumber(phone) {
        if (!phone) return '';
        
        // Форматирование: +7 (XXX) XXX-XX-XX
        if (phone.length === 11) {
            return `+7 (${phone.substr(1, 3)}) ${phone.substr(4, 3)}-${phone.substr(7, 2)}-${phone.substr(9, 2)}`;
        }
        
        return phone;
    }
    
    // Обработчик для предпросмотра загружаемой фотографии
    if (avatarUpload) {
        avatarUpload.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    // Открываем модальное окно редактирования аватара
                    openAvatarEditor(e.target.result);
                }
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Функция для открытия модального окна с редактором аватара
    function openAvatarEditor(imageSrc) {
        // Сбрасываем значения при каждом открытии редактора
        imageRotation = 0;
        avatarZoomLevel = 45;

        // Создаем HTML для редактора
        const editorHtml = `
            <div class="avatar-editor-wrapper">
                <div class="avatar-image-container">
                    <img src="${imageSrc}" alt="Аватар" id="avatar-editor-image">
                    <div class="avatar-crop-area" id="avatar-crop-area">
                        <div class="avatar-circle-overlay"></div>
                </div>
            </div>
            <div class="avatar-editor-controls">
                <div class="avatar-editor-slider">
                        <label for="avatar-zoom">Размер области выделения</label>
                        <input type="range" id="avatar-zoom" min="30" max="70" value="45">
                </div>
                    <button type="button" id="avatar-rotate-btn" class="btn-secondary">
                    <i class="fas fa-sync-alt"></i> Повернуть
                </button>
                </div>
            </div>
        `;
        
        // Добавляем HTML в контейнер
        avatarEditorContainer.innerHTML = editorHtml;
        
        // Инициализируем редактор
        initAvatarEditor(imageSrc);
        
        // Открываем модальное окно
        avatarModal.classList.add('show');
    }
    
    /**
     * Инициализирует редактор аватара
     * Позволяет загружать, вращать и обрезать изображение аватара
     */
    function initAvatarEditor(imageSrc) {
        let imageElement = document.getElementById('avatar-editor-image');
        let cropArea = document.getElementById('avatar-crop-area');
        let zoomSlider = document.getElementById('avatar-zoom');
        let rotateBtn = document.getElementById('avatar-rotate-btn');
        let container = document.querySelector('.avatar-image-container');
        
        let isDragging = false;
        let lastX = 0;
        let lastY = 0;
        let cropX = 0;
        let cropY = 0;
        let cropSize = 180; // начальный размер круга обрезки
        
        // Устанавливаем начальные значения
        avatarZoomLevel = parseInt(zoomSlider.value); // используем для хранения размера круга в процентах
        
        // Установить источник изображения
        if (imageElement && imageSrc) {
            imageElement.src = imageSrc;
            
            // Предзагрузка изображения для получения размеров
            const img = new Image();
            img.onload = function() {
                const imgWidth = this.width;
                const imgHeight = this.height;
                
                // Адаптируем изображение к контейнеру с сохранением пропорций
                const containerWidth = container.offsetWidth;
                const containerHeight = container.offsetHeight;
                
                // Устанавливаем начальный размер круга обрезки
                updateCropSize(avatarZoomLevel);
                
                // Центрируем область обрезки
                cropX = (containerWidth - cropSize) / 2;
                cropY = (containerHeight - cropSize) / 2;
                updateCropPosition();
            };
            img.src = imageSrc;
            
            // Ждем загрузки изображения, чтобы инициализировать редактор
            imageElement.onload = function() {
                // Центрировать область обрезки изначально
                const containerRect = container.getBoundingClientRect();
                cropX = (containerRect.width - cropSize) / 2;
                cropY = (containerRect.height - cropSize) / 2;
                updateCropPosition();
            };
        }
        
        // Функция для обновления размера круга обрезки
        function updateCropSize(percent) {
            avatarZoomLevel = percent; // сохраняем значение для использования в других функциях
            const containerWidth = container.offsetWidth;
            cropSize = Math.round(containerWidth * (percent / 100));
            
            if (cropArea) {
            cropArea.style.width = `${cropSize}px`;
            cropArea.style.height = `${cropSize}px`;
                
                // Корректируем позицию, чтобы круг не выходил за границы
                constrainCropPosition();
                updateCropPosition();
            }
        }
        
        // Функция для обновления позиции области обрезки
        function updateCropPosition() {
            if (cropArea) {
                // Устанавливаем позицию через left/top, а не через transform,
                // так как transform уже используется для центрирования
                cropArea.style.left = `${cropX + cropSize/2}px`;
                cropArea.style.top = `${cropY + cropSize/2}px`;
            }
        }
        
        // Ограничить позицию кропа внутри контейнера
        function constrainCropPosition() {
            const containerWidth = container.offsetWidth;
            const containerHeight = container.offsetHeight;
            
            // Ограничиваем перемещение области кропа внутри контейнера
            cropX = Math.max(0, Math.min(containerWidth - cropSize, cropX));
            cropY = Math.max(0, Math.min(containerHeight - cropSize, cropY));
        }
        
        // Обработчики для перетаскивания области обрезки
        if (cropArea) {
        cropArea.addEventListener('mousedown', function(e) {
            isDragging = true;
                lastX = e.clientX;
                lastY = e.clientY;
                cropArea.style.cursor = 'grabbing';
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            
                const deltaX = e.clientX - lastX;
                const deltaY = e.clientY - lastY;
            
            cropX += deltaX;
            cropY += deltaY;
            
                constrainCropPosition();
                updateCropPosition();
                
                lastX = e.clientX;
                lastY = e.clientY;
        });
        
        document.addEventListener('mouseup', function() {
            isDragging = false;
                if (cropArea) {
                    cropArea.style.cursor = 'grab';
                }
            });
            
            // Добавляем поддержку сенсорных устройств
            cropArea.addEventListener('touchstart', function(e) {
                isDragging = true;
                lastX = e.touches[0].clientX;
                lastY = e.touches[0].clientY;
                cropArea.style.cursor = 'grabbing';
                e.preventDefault();
            });
            
            document.addEventListener('touchmove', function(e) {
                if (!isDragging) return;
                
                const deltaX = e.touches[0].clientX - lastX;
                const deltaY = e.touches[0].clientY - lastY;
                
                cropX += deltaX;
                cropY += deltaY;
                
                constrainCropPosition();
                updateCropPosition();
                
                lastX = e.touches[0].clientX;
                lastY = e.touches[0].clientY;
                
                e.preventDefault();
            });
            
            document.addEventListener('touchend', function() {
                isDragging = false;
                if (cropArea) {
                    cropArea.style.cursor = 'grab';
                }
            });
        }
        
        // Обработчик для слайдера изменения размера круга
        if (zoomSlider) {
            zoomSlider.addEventListener('input', function() {
                updateCropSize(parseInt(this.value));
            });
        }
        
        // Обработчик для кнопки поворота
        if (rotateBtn) {
            rotateBtn.addEventListener('click', function() {
                imageRotation = (imageRotation + 90) % 360;
                if (imageElement) {
                    imageElement.style.transform = `rotate(${imageRotation}deg)`;
                }
            });
        }
    }
    
    // Функция для получения отредактированного аватара
    async function getEditedAvatarData() {
        const avatarEditorImage = document.getElementById('avatar-editor-image');
        const cropArea = document.getElementById('avatar-crop-area');
        const container = document.querySelector('.avatar-image-container');
        
        if (!avatarEditorImage || !cropArea || !container) {
            throw new Error('Элементы редактора не найдены');
        }
        
        try {
            // Создаем канвас для обрезки изображения
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            // Устанавливаем размер канваса равным размеру кропа
            const cropSize = cropArea.offsetWidth;
            canvas.width = cropSize;
            canvas.height = cropSize;
            
            // Получаем размеры и позиции
            const containerRect = container.getBoundingClientRect();
            const cropRect = cropArea.getBoundingClientRect();
            const imgRect = avatarEditorImage.getBoundingClientRect();
            
            // Вычисляем масштаб изображения
            const scaleX = avatarEditorImage.naturalWidth / imgRect.width;
            const scaleY = avatarEditorImage.naturalHeight / imgRect.height;
            
            // Вычисляем позицию области обрезки относительно изображения
            const cropLeft = (cropRect.left - imgRect.left) * scaleX;
            const cropTop = (cropRect.top - imgRect.top) * scaleY;
            
            // Размеры области обрезки в реальных пикселях
            const sourceCropWidth = cropRect.width * scaleX;
            const sourceCropHeight = cropRect.height * scaleY;
            
            // Очищаем канвас
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Сохраняем контекст для применения поворота
            ctx.save();
            
            // Если есть поворот, применяем его
            if (imageRotation) {
                ctx.translate(canvas.width / 2, canvas.height / 2);
                ctx.rotate((imageRotation * Math.PI) / 180);
                ctx.translate(-canvas.width / 2, -canvas.height / 2);
            }
            
            // Рисуем изображение с учетом обрезки
            ctx.drawImage(
                avatarEditorImage,
                cropLeft, cropTop,
                sourceCropWidth, sourceCropHeight,
                0, 0,
                canvas.width, canvas.height
            );
            
            // Восстанавливаем контекст
            ctx.restore();
            
            // Создаем круглую маску
            ctx.globalCompositeOperation = 'destination-in';
            ctx.beginPath();
            ctx.arc(canvas.width / 2, canvas.height / 2, canvas.width / 2, 0, Math.PI * 2);
            ctx.closePath();
            ctx.fill();
            
            // Возвращаем данные изображения в формате base64
            return canvas.toDataURL('image/png', 1.0);
        } catch (error) {
            console.error('Ошибка при создании обрезанного изображения:', error);
            throw error;
        }
    }
    
    // Функция для сохранения отредактированного аватара
    async function saveEditedAvatar() {
        try {
            // Показываем индикатор загрузки
            saveAvatarBtn.disabled = true;
            saveAvatarBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
            
            // Получаем данные отредактированного аватара
            editedAvatarData = await getEditedAvatarData();
            
            if (!editedAvatarData) {
                throw new Error('Не удалось получить данные изображения');
            }
            
            // Проверяем размер изображения
            const base64Size = editedAvatarData.length * 0.75; // приблизительный размер в байтах
            const maxSize = 5 * 1024 * 1024; // 5MB
            
            if (base64Size > maxSize) {
                throw new Error('Размер изображения превышает 5MB');
            }
            
            // Показываем предпросмотр отредактированного аватара
            avatarPreview.innerHTML = `<img src="${editedAvatarData}" alt="Аватар">`;
            
            // Закрываем модальное окно
            avatarModal.classList.remove('show');
            
            // Показываем уведомление об успехе
            showNotification('Изображение успешно отредактировано', 'success');
            
        } catch (error) {
            showNotification(error.message || 'Ошибка при обработке изображения', 'error');
            console.error('Ошибка при сохранении аватара:', error);
        } finally {
            // Восстанавливаем кнопку
            saveAvatarBtn.disabled = false;
            saveAvatarBtn.innerHTML = 'Сохранить';
        }
    }
    
    // Функция для сохранения профиля
    async function saveProfile() {
        try {
            const csrftoken = getCookie('csrftoken');
            const accessToken = getCookie('access_token');
            
            // Получаем данные формы
            const formData = new FormData(profileEditForm);
            
            // Добавляем выбранные интересы
            const selectedInterests = Array.from(document.querySelectorAll('#edit-interests .interest-item.selected'))
                .map(item => item.dataset.id);
            
            formData.delete('interests'); // Удаляем существующее поле, если оно есть
            selectedInterests.forEach(id => {
                formData.append('interests', id);
            });
            
            // Если есть отредактированный аватар, добавляем его в formData
            if (editedAvatarData) {
                try {
                    // Удаляем префикс data:image/png;base64,
                    const base64Data = editedAvatarData.split(',')[1];
                    // Конвертируем base64 в бинарные данные
                    const binaryData = atob(base64Data);
                    // Создаем массив с бинарными данными
                    const byteArray = new Uint8Array(binaryData.length);
                    for (let i = 0; i < binaryData.length; i++) {
                        byteArray[i] = binaryData.charCodeAt(i);
                    }
                    // Создаем Blob из бинарных данных
                    const blob = new Blob([byteArray], { type: 'image/png' });
                    
                    // Создаем уникальное имя файла
                    const fileName = `avatar_${Date.now()}.png`;
                    
                    // Создаем File объект из Blob
                    const avatarFile = new File([blob], fileName, { type: 'image/png' });
                    
                    // Заменяем аватар в formData
                    formData.delete('avatar');
                    formData.append('avatar', avatarFile);
                    
                    // Сбрасываем временные данные
                    editedAvatarData = null;
                } catch (error) {
                    console.error('Ошибка при обработке аватара:', error);
                    throw new Error('Не удалось обработать изображение аватара');
                }
            }
            
            const headers = {
                'X-CSRFToken': csrftoken
            };
            
            if (accessToken) {
                headers['Authorization'] = `Bearer ${accessToken}`;
            }
            
            const response = await fetch('/app/api/profile/', {
                method: 'PUT',
                headers: headers,
                body: formData,
                credentials: 'include'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/app/auth/login/';
                    return;
                }
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка сохранения профиля');
            }
            
            // Обновляем данные профиля
            await loadProfileData();
            
            // Переключаемся на просмотр
            showProfileView();
            
            showNotification('Профиль успешно обновлен', 'success');
            
        } catch (error) {
            console.error('Ошибка при сохранении профиля:', error);
            showNotification(error.message || 'Не удалось сохранить профиль', 'error');
        }
    }
    
    // Функция для смены пароля
    async function changePassword(formData) {
        try {
            const csrftoken = getCookie('csrftoken');
            const accessToken = getCookie('access_token');
            
            const headers = {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json'
            };
            
            if (accessToken) {
                headers['Authorization'] = `Bearer ${accessToken}`;
            }
            
            const data = {
                current_password: formData.get('current_password'),
                new_password: formData.get('new_password')
            };
            
            const response = await fetch('/app/api/change-password/', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(data),
                credentials: 'include'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/app/auth/login/';
                    return;
                }
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка смены пароля');
            }
            
            // Закрываем модальное окно
            passwordModal.classList.remove('show');
            changePasswordForm.reset();
            
            showNotification('Пароль успешно изменен', 'success');
            
        } catch (error) {
            console.error('Ошибка при смене пароля:', error);
            showNotification(error.message || 'Не удалось изменить пароль', 'error');
        }
    }
    
    // Функция для удаления аккаунта
    async function deleteAccount() {
        try {
            const csrftoken = getCookie('csrftoken');
            const accessToken = getCookie('access_token');
            
            const headers = {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json'
            };
            
            if (accessToken) {
                headers['Authorization'] = `Bearer ${accessToken}`;
            }
            
            const response = await fetch('/app/api/profile/', {
                method: 'DELETE',
                headers: headers,
                credentials: 'include'
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/app/auth/login/';
                    return;
                }
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка удаления аккаунта');
            }
            
            // Перенаправление на страницу входа
            showNotification('Аккаунт успешно деактивирован', 'success');
            setTimeout(() => {
                window.location.href = '/app/auth/login/';
            }, 2000);
            
        } catch (error) {
            console.error('Ошибка при удалении аккаунта:', error);
            showNotification(error.message || 'Не удалось удалить аккаунт', 'error');
        }
    }
    
    // Функция для отображения формы редактирования
    function showProfileEdit() {
        profileView.classList.add('hidden');
        profileEdit.classList.remove('hidden');
    }
    
    // Функция для отображения просмотра профиля
    function showProfileView() {
        profileEdit.classList.add('hidden');
        profileView.classList.remove('hidden');
    }
    
    // Обработчик для кнопки редактирования профиля
    if (editProfileBtn) {
        editProfileBtn.addEventListener('click', showProfileEdit);
    }
    
    // Обработчик для кнопки отмены редактирования
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', showProfileView);
    }
    
    // Обработчик для кнопки смены пароля
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', function() {
            passwordModal.classList.add('show');
        });
    }
    
    // Обработчик для закрытия модального окна смены пароля
    if (closePasswordModal) {
        closePasswordModal.addEventListener('click', function() {
            passwordModal.classList.remove('show');
            changePasswordForm.reset();
        });
    }
    
    // Обработчик для кнопки удаления аккаунта
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', function() {
            deleteModal.classList.add('show');
        });
    }
    
    // Обработчики для модального окна удаления аккаунта
    if (closeDeleteModal) {
        closeDeleteModal.addEventListener('click', function() {
            deleteModal.classList.remove('show');
        });
    }
    
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', function() {
            deleteModal.classList.remove('show');
        });
    }
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', deleteAccount);
    }
    
    // Обработчик для формы смены пароля
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;
            
            // Проверка совпадения паролей
            if (newPassword !== confirmPassword) {
                showNotification('Пароли не совпадают', 'error');
                return;
            }
            
            // Проверка сложности пароля
            if (!validatePassword(newPassword)) {
                showNotification('Пароль не соответствует требованиям безопасности', 'error');
                return;
            }
            
            // Отправка запроса на смену пароля
            const formData = new FormData(changePasswordForm);
            changePassword(formData);
        });
    }
    
    // Обработчик для валидации нового пароля
    const newPasswordInput = document.getElementById('new-password');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            validatePassword(this.value);
        });
    }
    
    // Обработчик для формы редактирования профиля
    if (profileEditForm) {
        profileEditForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveProfile();
        });
    }
    
    // Добавляем обработчики для модального окна редактирования аватара
    if (closeAvatarModal) {
        closeAvatarModal.addEventListener('click', function() {
            avatarModal.classList.remove('show');
        });
    }
    
    if (cancelAvatarBtn) {
        cancelAvatarBtn.addEventListener('click', function() {
            avatarModal.classList.remove('show');
        });
    }
    
    if (saveAvatarBtn) {
        saveAvatarBtn.addEventListener('click', saveEditedAvatar);
    }
    
    // Загружаем данные профиля при загрузке страницы
    loadProfileData();
    
    // Закрытие модальных окон при клике вне их содержимого
    window.addEventListener('click', function(e) {
        if (e.target === passwordModal) {
            passwordModal.classList.remove('show');
        }
        if (e.target === deleteModal) {
            deleteModal.classList.remove('show');
        }
        if (e.target === avatarModal) {
            avatarModal.classList.remove('show');
        }
    });
}); 