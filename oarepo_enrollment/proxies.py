from flask import current_app
from werkzeug.local import LocalProxy

current_enrollment = LocalProxy(lambda: current_app.extensions['oarepo-enrollment'])
