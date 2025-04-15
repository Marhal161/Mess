#!/bin/bash

# Переход в корневую директорию проекта
cd /mess

# Применение миграций
python manage.py migrate --noinput

# Сбор статических файлов
python manage.py collectstatic --noinput

# Запуск сервера Django
exec python manage.py runserver 0.0.0.0:8000