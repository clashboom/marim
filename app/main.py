#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Happy Violence!
import jinja2
import logging
import os
import webapp2
import urllib

from google.appengine.runtime import apiproxy_errors
from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

import collections

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True)


class BaseTyre(ndb.Model):
    brand = ndb.StringProperty(required=True)
    model = ndb.StringProperty(required=True)
    price = ndb.StringProperty(required=True)

    size = ndb.StringProperty(required=True)

    lastModified = ndb.DateTimeProperty(auto_now=True)
    isHidden = ndb.BooleanProperty(default=False)

    @classmethod
    def queryTyres(cls):
        return cls.query()

    @classmethod
    def toggleVisibility(cls, itemID):
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
    season = ndb.StringProperty(default=None)
    speedIndex = ndb.StringProperty(default=None)
    loadIndex = ndb.StringProperty(default=None)
    image = ndb.BlobProperty(default=None)

    inStock = ndb.IntegerProperty(default=0)


class CarTyre(Tyre):
    pass


class UsedCarTyre(CarTyre):
    treadDepth = ndb.StringProperty()


class TruckTyre(Tyre):
    # loadIndexPaired = ndb.StringProperty('lip')
    axlePosition = ndb.StringProperty()


class UsedTruckTyre(TruckTyre):
    treadDepth = ndb.StringProperty()


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

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

    @classmethod
    def render_str(cls, template, *a, **params):
        template = JINJA_ENV.get_template(template)
        return template.render(params)

    def render(self, template, *a, **params):
        self.write(self.render_str(template, *a, **params))


class MainHandler(Handler):
    def get(self):
        self.render("home.html")


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


class SendMail(Handler):
    def post(self):
        user_name = self.request.get("name")
        user_info = self.request.get("cinfo")
        # TODO: Add rate limiting
        message = self.request.get("message")
        from_addr = "info@bropro.lv"
        to_addr = "nejeega@gmail.com"

        try:
            mail.send_mail(from_addr,
                           to_addr,
                           'Test mail',
                           'Vards: %(name)s \n Kontaktinfo: %(info)s\n \
                           Zinja: %(message)s' % {'name': user_name,
                                                  'info': user_info,
                                                  'message': message})
        except apiproxy_errors.OverQuotaError, message:
            # Log the error.
            logging.error(message)
            # Redirect (?) and
            # TODO: Display an informative message to the user.
            self.write('The email could not be sent. '
                       'Please try again later.')
        # TODO: Implement redirect with success message.
        self.write("Done?")


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

        a = [["195/70 R15", "10", "R", "Firestone",
              "MPS 530", "Ziemas", "50.00", 4],
             ["195/65 R15", "9", "T", "Goodyear",
              "MP 92", "Ziemas", "33.00", 3],
             ["205/55 R16", "9", "H", "Michelin",
              "MP 59", "Ziemas", "45.00", 3],
             ["205/55 R16", "9", "T", "Falken",
              "KW 22", "Ziemas", "50.00", 2],
             ["205/55 R16", "9", "T", "General",
              "Frigo 2", "Ziemas", "42.00", 1],
             ["235/75 R17", "13", "L", "Debica",
              "HN804", "Vissez.", "110.00", 0]]

        b = [["255/55 R18", "10", "H", "Dunlop",
              "Scop", "Vs.", "15.00", 3, "4.0"],
             ["220x508 R18", "8", "Q", "Bridgestone",
              "MI", "Vissez.", "15.00", 0, "5.0"]]

        c = [["385/65 R22.5", "13", "L", "Infinity",
              "M350", "V.", "290.0", 5, 'U'],
             ["385/55 R22.5", "13", "L", "Hankook",
              "HN809", "V.", "230.0", 0, "U"],
             ["385/65 R22.5", "13", "L", "Dayton",
              "HN805", "V.", "210.0", 6, "U"],
             ["385/65 R22.5", "13", "L", "BFGoodrich",
              "FH2", "V.", "250.0", 0, "U"],
             ["315/80 R22.5", "13", "L", "Fulda",
              "TB755", "V.", "175.0", 6, "U"],
             ["315/80 R22.5", "13", "L", "Tigar",
              "HN 355", "V.", "220.0", 2, "F"],
             ["315/70 R22.5", "13", "L", "Yokohama",
              "RS03", "Vi.", "250.0", 2, "F"],
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
             ["315/70 R22.5", "13", "L", "Kormoran",
              "R6", "V", "35.00", 0, 'U', "11"],
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

        self.redirect("/")


class TyreHandler(Handler):
    def get(self, kind=None, itemID=None):

        tyres = None

        if kind:
            if itemID:
                key = ndb.Key(self.tyrePaths[kind], int(itemID))
                tyres = [key.get()]
                self.render("riepas.html", Tyres=tyres)
                return
            else:
                if kind == 'lietotas':
                    tyres = list(UsedCarTyre.queryTyres()) + \
                        list(UsedTruckTyre.queryTyres())
                elif 'jaunas' or 'lietotas' in kind:
                    tyres = list(self.tyrePaths[kind].queryTyres())
                else:
                    # feed the dada
                    tyres = list(self.tyrePaths[kind].queryTyres()) + \
                        list(self.tyrePaths[kind + '/lietotas'].queryTyres())
                self.render("riepas.html", Tyres=tyres)
                return

        tyres = list(CarTyre.queryTyres()) + list(UsedCarTyre.queryTyres()) + \
            list(TruckTyre.queryTyres()) + list(UsedTruckTyre.queryTyres())
        self.render("riepas.html", Tyres=tyres)


class EntriesHandler(Handler, blobstore_handlers.BlobstoreUploadHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/add')
        self.render("manage.html", url=str(upload_url))

    def post(self):
        size = self.request.get('size')
        brand = self.request.get('brand')
        model = self.request.get('model')
        price = self.request.get('price')
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
        self.redirect('')


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
            img.resize(width=80, height=100)
            thumbnail = img.execute_transforms(
                output_encoding=images.JPEG)

            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(thumbnail)
            return

        # Either blob_key wasnt provided or there was no value with that ID
        # in the Blobstore
        self.error(404)


app = webapp2.WSGIApplication([
    ('/db', PopulateDB),
    ('/add', EntriesHandler),
    ('/diski', RimHandler),
    ('/meklet', SearchHandler),
    ('/par', AboutHandler),
    ('/l', SendMail),
    ('/riepas(?:/)?(?:([a-zA-Z]+(?:(?:/)?[a-zA-Z]+)?)?(?:/)?([0-9]+)?)?',
     TyreHandler),
    ('/serviss(?:/)?([a-zA-Z]+)?(?:/)?',
     ServiceHandler),
    ('/upload', UploadHandler),
    ('/serve/([^/]+)?', ServeHandler),
    ('/serve/th/([^/]+)?', ThumbnailHandler),
    ('/.*', MainHandler)
], debug=True)

# TODO: Implement feature to find product by car model.
