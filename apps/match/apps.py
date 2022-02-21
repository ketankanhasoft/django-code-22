from django.apps import AppConfig


class MatchConfig(AppConfig):
    name = "match"

    def ready(self):
        from match import signals
