from app import initialise_application
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.exceptions import NotFound
from werkzeug.middleware.proxy_fix import ProxyFix

_base = initialise_application()

#Mnt flask app at /maintenance so url_for() etc. generate correct paths
#NotFound() will 404 everywhere outside /maintenance
mounted = DispatcherMiddleware(NotFound(), {
    "/maintenace":_base
})

# Respect X-Forwarded-* from Caddy
app = ProxyFix(mounted, x_for=1, x_host=1, x_proto=1)