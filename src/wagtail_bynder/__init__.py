from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_video_model_string():
    """
    Get the dotted ``app.Model`` name for the video model as a string.
    """
    return getattr(settings, "BYNDER_VIDEO_MODEL", None)


def get_video_model():
    """
    Get the video model from the ``BYNDER_VIDEO_MODEL`` setting.
    """
    from django.apps import apps

    model_string = get_video_model_string()
    if model_string is None:
        return None

    try:
        return apps.get_model(model_string, require_ready=False)
    except ValueError as e:
        raise ImproperlyConfigured(
            "BYNDER_VIDEO_MODEL must be of the form 'app_label.Model'"
        ) from e
    except LookupError as e:
        raise ImproperlyConfigured(
            "BYNDER_VIDEO_MODEL refers to model '%s' that has not been installed"
            % model_string
        ) from e


VERSION = (0, 1, 0)
__version__ = ".".join(map(str, VERSION))
