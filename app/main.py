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

import collections
from functools import wraps


# Jinja2 Config
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True)


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
                self.response.write(u'Rate limit exceeded.')
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

    width = ndb.IntegerProperty()
    aspectRatio = ndb.IntegerProperty()

    construction = ndb.StringProperty(default=u'R')
    diameter = ndb.FloatProperty()

    season = ndb.StringProperty(default=None)

    speedIndex = ndb.StringProperty(default=None)
    loadIndex = ndb.StringProperty(default=None)


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
    image = ndb.BlobProperty(default=None)
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
    treadDepth = ndb.StringProperty()


class TruckTyre(Tyre):
    loadIndexPaired = ndb.StringProperty()
    axlePosition = ndb.StringProperty()


class UsedTruckTyre(TruckTyre):
    treadDepth = ndb.StringProperty()


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

        from_addr = "info@bropro.lv"
        to_addr = "nejeega@gmail.com"

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
        from_addr = "info@bropro.lv"
        to_addr = "nejeega@gmail.com"

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
        # TODO: Implement redirect with success message.


class PopulateDB(Handler):
    def get(self):
        def generateDL(paramList, entries):
            logging.error("Generating DL...")
            dl = []
            for entry in entries:
                tmpdict = collections.OrderedDict()
                for param, val in zip(paramList, entry):
                    tmpdict[param] = val
                dl.append(tmpdict)
            return dl

        def addEntries(entityName, parameterDL):
            logging.error("Adding Entries...")
            for params in parameterDL:
                e = entityName(**params)
                e.put()

        a = [["205/55 R16", "91", "H", "StarFire",
              "RS-C 2.0", "Ziemas", "50.00", 4],
             ["235/75 R17", "9", "T", "Aeolus",
              "HN804", "Ziemas", "33.00", 3],
             ["255/75 R18", "9", "H", "Goodyear",
              "Wrangler S4", "Ziemas", "45.00", 3],
             ["255/55 R18", "9", "T", "Pirelli",
              "Scorpion", "Ziemas", "50.00", 2],
             ["205/55 R16", "9", "T", "General",
              "Frigo 2", "Ziemas", "42.00", 1],
             ["235/75 R17", "13", "L", "Debica",
              "HN804", "Vissez.", "110.00", 0]]

        b = [["255/55 R18", "10", "H", "Dayton",
              "DW510", "Vs.", "15.00", 3, "4.0"],
             ["220x508 R18", "8", "Q", "Bridgestone",
              "Wrangler Yada", "Vissez.", "15.00", 0, "5.0"]]

        c = [["385/65 R22.5", "13", "L", "Antyre",
              "TB1000", "V.", "290.0", 5, 'U'],
             ["385/55 R22.5", "13", "L", "Yokohama",
              "HN809", "V.", "230.0", 0, "U"],
             ["385/65 R22.5", "13", "L", "Dayton",
              "HN805", "V.", "210.0", 6, "U"],
             ["385/65 R22.5", "13", "L", "BFGoodrich",
              "FH2", "V.", "250.0", 0, "U"],
             ["315/80 R22.5", "13", "L", "Matador",
              "Silent", "V.", "175.0", 6, "U"],
             ["315/80 R22.5", "13", "L", "Tigar",
              "HN 355", "V.", "220.0", 2, "F"],
             ["315/70 R22.5", "13", "L", "Kormoran",
              "LHT", "Vi.", "250.0", 2, "F"],
             ["315/80 R22.5", "13", "L", "Nankang",
              "XD2", "V.", "160.0", 1, "U"],
             ["385/55 R22.5", "13", "J", "Kumho",
              "KLA1", "Vz.", "280.0", 5, "U"],
             ["1R R22.5", "13", "L", "Kingstar",
              "ST957", "V.", "185.0", 3, "U"]]

        d = [["315/65 R2.5", "10", "R", "Bridgestone",
              "KW22", "Z", "37", 3, "U", "5"],
             ["315/70 R22.5", "13", "L", "Tracmax",
              "X", "A.", "30.00", 0, 'F', "5"],
             ["8.5 R17", "12", "L", "Michelin", "HT",
              "Va", "25.00", 4, 'S', "4"],
             ["385/55 R22.5", "13", "L", "Pirelli",
              "HT1", "V.", "45.00", 6, 'U', "7"],
             ["315/70 R22.5", "13", "L", "Continental",
              "Earthmover", "V", "35.00", 0, 'U', "11"],
             ["11 R22.5", "13", "L", "Kormoran",
              "DR1", "V", "45.00", 2, 'U', "5"]]

        paramList = ["size", "loadIndex", "speedIndex", "brand", "model",
                     "season", "price", "inStock"]
        usedCarParamList = paramList[:]
        usedCarParamList.append("treadDepth")
        truckParamList = paramList[:]
        truckParamList.append("axlePosition")
        usedTruckParamList = truckParamList[:]
        usedTruckParamList.append("treadDepth")

        carTyreDL = generateDL(paramList, a)
        usedCarTyreDL = generateDL(usedCarParamList, b)
        truckTyreDL = generateDL(truckParamList, c)
        usedTruckTyreDL = generateDL(usedTruckParamList, d)

        addEntries(CarTyre, carTyreDL)
        addEntries(UsedCarTyre, usedCarTyreDL)
        addEntries(TruckTyre, truckTyreDL)
        addEntries(UsedTruckTyre, usedTruckTyreDL)

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
        self.write(tyre)


class EntriesHandler(Handler, blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/add')
        self.render("manage.html", url=str(upload_url))

    def post(self):
        size = self.request.get('size')
        brand = self.request.get('brand')
        model = self.request.get('model')
        price = float(self.request.get('price'))
        isUsed = self.request.get('isUsed')

        # Get the file and upload it
        upload_files = self.get_uploads('file')
        # Get the key from blobstore for the first element
        blob_info = upload_files[0]
        # Get the key
        img = blob_info.key()

        params = {'size': size, 'brand': brand, 'model': model,
                  'price': price, 'image': str(img)}

        if isUsed:
            tread = self.request.get('tread')
            params['treadDepth'] = tread

        tyre = CarTyre(**params)

        tyre.put()
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

        if blob_info:
            img = images.Image(blob_key=resource)
            img.resize(width=100, height=100)
            thumbnail = img.execute_transforms(
                output_encoding=images.JPEG)

            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(thumbnail)
            return

        # Either blob_key wasnt provided or there was no value with that ID
        # in the Blobstore
        self.error(404)


class NoiceHandler(Handler):
    def get(self):
        self.write("NOICE!")


app = webapp2.WSGIApplication([
    ('/admin/.*', NoiceHandler),
    ('/db', PopulateDB),
    ('/add', EntriesHandler),
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
    ('/.*', MainHandler),
], config=config, debug=True)

# TODO: Implement feature to find product by car model.
