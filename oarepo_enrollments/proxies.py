from flask import current_app
from werkzeug.local import LocalProxy

current_enrollments = LocalProxy(lambda: current_app.extensions['oarepo-enrollments'])
