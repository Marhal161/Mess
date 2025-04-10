from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        """Инициализация приложения при запуске"""
        # Для отладочной информации о загрузке моделей
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from . import models
            logger.info("Модели успешно загружены: %s", dir(models))
            logger.info("Like модель инициализирована: %s", hasattr(models, 'Like'))
        except Exception as e:
            logger.error("Ошибка при загрузке моделей: %s", e)
