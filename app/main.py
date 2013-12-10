import jinja2
import logging
import os
import webapp2

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @classmethod
    def render_str(cls, template, *a, **params):
        template = JINJA_ENV.get_template(template)
        return template.render(params)

    def render(self, template, *a, **params):
        self.write(self.render_str(template, *a, **params))


class MainHandler(Handler):
    def get(self):
        greeting = "Go fuck yourself."
        logging.error("Random log passing through, do not mind.")
        self.write(greeting)

app = webapp2.WSGIApplication([
    ('/index', MainHandler),
    ('/.*', MainHandler)
], debug=True)
