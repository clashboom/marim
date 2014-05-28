#!/usr/bin/env python
# -*- coding:utf-8 -*-
import jinja2
import logging
import os
import urllib
import webapp2

from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.api import memcache

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import ndb

from google.appengine.runtime import apiproxy_errors

from webapp2_extras import sessions
from webapp2_extras import sessions_memcache
# from webapp2_extras import sessions_ndb

from functools import wraps

# Jinja2 Config
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True)


def get_season(season):
    if season == "ms":
        return u"Vissezonas"
    elif season == "summer":
        return u"Vasaras"
    elif season == "winter":
        return u"Ziemas"
    elif season == "studded":
        return u"Ziemas, ar radzēm"
    elif season == "studdable":
        return u"Ziemas, radzējama"
    else:
        return


def get_axle_position(position):
    if position == "any":
        return u"Universāla"
    elif position == "front":
        return u"Stūrējošā"
    elif position == "drive":
        return u"Velkošā"
    elif position == "trailer":
        return u"Piekabes"
    else:
        return


def get_status(status):
    if status == "new":
        return u"Jauna"
    elif status == "renewed":
        return u"Atjaunota"
    elif status == "used":
        return u"Lietota"
    else:
        return

JINJA_ENV.filters["get_season"] = get_season
JINJA_ENV.filters["get_axle_position"] = get_axle_position
JINJA_ENV.filters["get_status"] = get_status


# Webapp2 Sessions config
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'my-super-secret-key',
    'name': 'bropro_session',
}


def rate_limit(seconds_per_request=1):
    def rate_limiter(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            added = memcache.add('%s:%s' %
                                 (self.__class__.__name__,
                                  self.request.remote_addr or ''), 1,
                                 time=seconds_per_request,
                                 namespace='rate_limiting')

            if not added:
                self.response.write(u'Darbība veikta pārāk bieži. Mēģiniet \
                                    vēlreiz pēc vienas minūtes')
                self.response.set_status(403)
                return
            return function(self, *args, **kwargs)
        return wrapper
    return rate_limiter


class BaseTyre(ndb.Model):
    brand = ndb.StringProperty(required=True)
    model = ndb.StringProperty(required=True)

    size = ndb.ComputedProperty(lambda self: "%s/%s %s%s" %
                                (self.width, self.aspectRatio,
                                 self.construction, self.diameter))

    width = ndb.IntegerProperty(required=True)
    aspectRatio = ndb.IntegerProperty(required=True)

    construction = ndb.StringProperty(default=u'R', required=True)
    diameter = ndb.FloatProperty(required=True)

    season = ndb.StringProperty()

    loadIndex = ndb.IntegerProperty()
    speedIndex = ndb.StringProperty()

    condition = ndb.StringProperty()

    @classmethod
    def queryTyres(cls):
        return cls.query()

    @classmethod
    def queryTyre(cls, itemID):
        return cls.get_by_id(int(itemID))

    @classmethod
    def toggleTyre(cls, itemID):
        tyre = cls.get_by_id(itemID)
        tyre.isHidden = False if tyre.isHidden else True
        # TODO: invalidate memcache or better yet, set in memcache, and add a
        # task to update db
        tyre.put()

    @classmethod
    def deleteTyre(cls, itemID):
        cls.get_by_id(itemID).key.delete()
        # TODO: invalidate memcache here as well


class Tyre(BaseTyre):
    image = ndb.BlobProperty()
    price = ndb.FloatProperty(required=True)
    inStock = ndb.IntegerProperty(default=0)

    EUwetGrip = ndb.StringProperty('EUwg')
    EUnoiseLevels = ndb.StringProperty('EUnl')
    EUfuelEfficiency = ndb.StringProperty('EUfe')

    lastModified = ndb.DateTimeProperty(auto_now=True)
    isHidden = ndb.BooleanProperty(default=False)


class CarTyre(Tyre):
    pass


class UsedCarTyre(CarTyre):
    treadDepth = ndb.IntegerProperty()


class TruckTyre(Tyre):
    loadIndexPaired = ndb.IntegerProperty()
    axlePosition = ndb.StringProperty()


class UsedTruckTyre(TruckTyre):
    treadDepth = ndb.IntegerProperty()


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    @classmethod
    def render_str(cls, template, *a, **params):
        template = JINJA_ENV.get_template(template)
        return template.render(params)

    def render(self, template, *a, **params):
        alert = self.session.get('alert')
        if alert:
            self.session.pop('alert')
        self.write(self.render_str(template,
                                   alert=alert,
                                   item_count=self.session.get('item_count'),
                                   *a, **params))

    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session(name='bropro_session',
                                              factory=sessions_memcache.
                                              MemcacheSessionFactory)


class MainHandler(Handler):
    def get(self):
        self.render("home.html")


class AddToCartHandler(Handler):
    def get(self):
        self.response.headers['Contenty-type'] = 'application/json'

        current_item_count = self.session.get('item_count')

        if not current_item_count:
            current_item_count = 0

        current_item_count = int(current_item_count) + 1

        key = self.request.get('key')
        item_list = self.session.get('item_list')
        if not item_list:
            item_list = []
        if key not in item_list:
            item_list.append(key)
            self.session['item_list'] = item_list
            self.session['item_count'] = current_item_count

        self.redirect('/grozs')


class ShowCartHandler(Handler):
    def get(self, modal=None):
        item_list = self.session.get('item_list')
        result = []
        if item_list:
            for key_str in item_list:
                key = ndb.Key(urlsafe=key_str)
                result.append(key.get())
        self.render('grozs.html', item_list=result)

    @rate_limit(seconds_per_request=15)
    def post(self):
        order = dict()
        order['tyres'] = []

        for key, value in self.request.POST.iteritems():
            try:
                k = ndb.Key(urlsafe=key)
                t = k.get()
                order['tyres'].append(("Riepas ID: %(id)s \
                                       Nosaukums: %(name)s \
                                       Skaits: %(count)s" %
                                       {'id': k.id(),
                                        'name': t.brand + " " + t.model +
                                        " " + t.size,
                                        'count': value}))
            except:
                order[key] = value

        from_addr = "bropro.tire@gmail.com"
        to_addr = "info@bropro.lv"

        try:
            msg = mail.EmailMessage()
            msg.sender = from_addr
            msg.to = to_addr
            msg.subject = "Pasutijums"
            msg.html = order
            msg.send()
        except apiproxy_errors.OverQuotaError, message:
            logging.error(message)

        self.session['alert'] = u'Pasūtījums veiksmīgs! Ar Jums sazināsies \
            mūsu pārstāvis!'
        self.redirect('/grozs/dzest')


class ClearCartHandler(Handler):
    def get(self, key_str=None):
        if key_str:
            item_list = self.session.get('item_list')
            item = next((x for x in item_list if x == key_str), None)
            if item:
                item_list.remove(item)
            self.session['item_list'] = item_list
            self.session['item_count'] -= 1
        else:
            self.session.pop('item_list')
            self.session.pop('item_count')
        self.redirect(self.request.referer)


class RimHandler(Handler):
    def get(self):
        self.render("diski.html")


class ServiceHandler(Handler):
    def get(self, kind=None):
        self.render("serviss.html")


class AboutHandler(Handler):
    def get(self):
        self.render("about.html")


class SearchHandler(Handler):
    def get(self):
        term = self.request.get("q")
        self.render("search.html", term=term)


class MailHandler(Handler):
    @rate_limit(seconds_per_request=15)
    def post(self):
        user_info = self.request.get("cinfo")
        message = self.request.get("message")
        # TODO: Add rate limiting
        from_addr = "bropro.tire@gmail.com"
        to_addr = "info@bropro.lv"

        try:
            mail.send_mail(from_addr,
                           to_addr,
                           'No BroPro lapas',
                           'Personas kontaktinfo: %(info)s\n \
                            Zina: %(message)s' % {'info': user_info,
                                                  'message': message})
            self.session['alert'] = u'Ziņa nosūtīta veiksmīgi!'
            self.redirect(self.request.referer)
        except apiproxy_errors.OverQuotaError, message:
            # Log the error.
            logging.error(message)
            # Redirect (?) and
            self.session['alert'] = u'Ziņu neizdevās nosūtīt. \
                Lūdzu, mēģiniet vēlāk.'
            self.redirect(self.request.referer)


class Utils(Handler):
    @staticmethod
    def getKindFromPath(path):
        tyrePaths = {'CarTyre': 'vieglo',
                     'UsedCarTyre': 'vieglo/lietotas',
                     'TruckTyre': 'kravas',
                     'UsedTruckTyre': 'kravas/lietotas',
                     'vieglo': CarTyre,
                     'vieglo/jaunas': CarTyre,
                     'vieglo/lietotas': UsedCarTyre,
                     'kravas': TruckTyre,
                     'kravas/jaunas': TruckTyre,
                     'kravas/lietotas': UsedTruckTyre}
        return tyrePaths[path]

    @staticmethod
    def addTyre(kind, **params):
        if kind == 'truck':
            if params['condition'] == 'used':
                tyre = UsedTruckTyre(**params)
            else:
                tyre = TruckTyre(**params)
        else:
            if params['condition'] == 'used':
                tyre = UsedCarTyre(**params)
            else:
                tyre = CarTyre(**params)
        if tyre:
            tyre.put()
        return


class TyresHandler(Handler):
    def get(self, path=None):
        tyres = None
        if path:
            if path == 'lietotas':
                tyres = list(UsedCarTyre.queryTyres()) + \
                    list(UsedTruckTyre.queryTyres())
            elif 'jaunas' or 'lietotas' in path:
                tyres = list(Utils.getKindFromPath(path).queryTyres())
            else:
                tyres = list(Utils.getKindFromPath(path).queryTyres()) + \
                    list(Utils.getKindFromPath(path +
                                               '/lietotas').queryTyres())
                self.render("riepas.html", Tyres=tyres)
                return
        else:
            tyres = list(CarTyre.queryTyres()) + list(UsedCarTyre.queryTyres()) + \
                list(TruckTyre.queryTyres()) + list(UsedTruckTyre.queryTyres())

        self.render("riepas.html", Tyres=tyres)


class SingleTyreHandler(Handler):
    def get(self, key_str=None):
        key = ndb.Key(urlsafe=key_str)
        if key:
            tyre = key.get()
        ajax = self.request.get('ajax')
        if ajax:
            self.render('riepa_ajax.html', tyre=tyre)
        else:
            self.render('riepa.html', tyre=tyre)


class EntriesHandler(Handler, blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/admin/add')
        self.render("manage.html", url=str(upload_url))

    def post(self):
        # Get tyre params
        kind = self.request.get('kind')
        brand = self.request.get('brand')
        model = self.request.get('model')
        width = int(self.request.get('width'))
        ratio = int(self.request.get('ratio'))
        construction = self.request.get('construction')
        diameter = float(self.request.get('diameter'))
        li = int(self.request.get('loadIndex'))
        si = self.request.get('speedIndex')
        condition = self.request.get('condition')
        season = self.request.get('season')
        price = float(self.request.get('price'))


        params = {'brand': brand, 'model': model, 'width': width,
                  'aspectRatio': ratio, 'construction': construction,
                  'diameter': diameter, 'loadIndex': li, 'speedIndex': si,
                  'condition': condition, 'season': season, 'price': price
                  }

        # Get the picture and upload it
        upload_files = self.get_uploads('file')
        # Get the key from blobstore for the first element
        if upload_files:
            blob_info = upload_files[0]
            img = blob_info.key()
            params['image'] = str(img)

        if condition == 'used':
            tread = int(self.request.get('tread'))
            params['treadDepth'] = tread

        if kind == 'truck':
            lip = int(self.request.get('loadIndexPaired'))
            params['loadIndexPaired'] = lip
            axle = self.request.get('axle')
            params['axlePosition'] = axle

        Utils.addTyre(kind, **params)
        self.redirect(self.request.referer)


# Blobstore
class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        # 'file' is file upload field in the form
        upload_files = self.get_uploads('file')
        blob_info = upload_files[0]
        self.redirect('/serve/%s' % blob_info.key())


class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)


class ThumbnailHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        dimensions = self.request.get('dimensions')
        size = int(dimensions) if dimensions else 100

        if blob_info:
            img = images.Image(blob_key=resource)
            img.resize(width=size, height=size)
            thumbnail = img.execute_transforms(
                output_encoding=images.JPEG)

            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(thumbnail)
            return

        # Either blob_key wasnt provided or there was no value with that ID
        # in the Blobstore
        self.error(404)


class SalidziniHandler(Handler):
    def get(self):
        tyres = list(CarTyre.queryTyres()) + list(UsedCarTyre.queryTyres()) + \
            list(TruckTyre.queryTyres()) + list(UsedTruckTyre.queryTyres())

        self.response.headers['Content-Type'] = "application/xml"
        self.render('salidzini.xml', tyres=tyres)


app = webapp2.WSGIApplication([
    ('/admin/add', EntriesHandler),
    ('/diski', RimHandler),
    ('/meklet', SearchHandler),
    ('/par', AboutHandler),
    ('/l', MailHandler),
    ('/riepa/(.*)?', SingleTyreHandler),
    ('/riepas(?:/)?(?:([a-zA-Z]+(?:(?:/)?[a-zA-Z]+)?)?(?:/)?)?',
     TyresHandler),
    ('/serviss(?:/)?([a-zA-Z]+)?(?:/)?',
     ServiceHandler),
    ('/upload', UploadHandler),
    ('/serve/([^/]+)?', ServeHandler),
    ('/serve/th/([^/]+)?', ThumbnailHandler),
    ('/pirkt.*', AddToCartHandler),
    ('/grozs', ShowCartHandler),
    ('/grozs/dzest(?:/)?(.*)?', ClearCartHandler),
    ('/salidzini', SalidziniHandler),
    ('/.*', MainHandler),
], config=config, debug=True)

# TODO: Implement feature to find product by car model.
