"""Web server package for RepoPilot and the legacy NEXORA dashboard."""


def create_app(*args, **kwargs):
	"""Create the legacy Flask app without forcing Flask on FastAPI imports."""
	from nexora.server.app import create_app as flask_create_app
	return flask_create_app(*args, **kwargs)


__all__ = ["create_app"]
