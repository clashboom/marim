import jinja2
import logging
import os
import webapp2

from google.appengine.runtime import apiproxy_errors
# from google.appengine.api import images
from google.appengine.api import mail
from google.appengine.ext import ndb

import collections

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True)


class Service(ndb.Model):
    name = ndb.StringProperty('n', required=True)
    category = ndb.StringProperty('cat', required=True)
    price = ndb.StringProperty('p', required=True)

    @classmethod
    def queryServices(cls):
        return cls.query()


class BaseTyre(ndb.Model):
    brand = ndb.StringProperty('b', required=True)
    loadIndex = ndb.StringProperty('li')
    model = ndb.StringProperty('m', required=True)
    price = ndb.StringProperty('p', required=True)
    season = ndb.StringProperty('se')
    size = ndb.StringProperty('sz', required=True)
    speedIndex = ndb.StringProperty('si')

    lastModified = ndb.DateTimeProperty('mod', auto_now=True)
    isHidden = ndb.BooleanProperty('h', default=False)

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


class CarTyre(BaseTyre):
    pass


class UsedCarTyre(CarTyre):
    treadDepth = ndb.StringProperty('td')


class TruckTyre(BaseTyre):
    # loadIndexPaired = ndb.StringProperty('lip')
    axlePosition = ndb.StringProperty('ap')


class UsedTruckTyre(TruckTyre):
    treadDepth = ndb.StringProperty('td')


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    paths = {'CarTyre': 'vieglo',
             'UsedCarTyre': 'lietotas/vieglo',
             'TruckTyre': 'kravas',
             'UsedTruckTyre': 'lietotas/kravas'}

    @classmethod
    def render_str(cls, template, *a, **params):
        template = JINJA_ENV.get_template(template)
        return template.render(params)

    def render(self, template, *a, **params):
        self.write(self.render_str(template, *a, **params))


class ManageTyres(Handler):
    def get(self):
        carTyres = list(CarTyre.queryTyres())
        uCarTyres = list(UsedCarTyre.queryTyres())
        truckTyres = list(TruckTyre.queryTyres())
        uTruckTyres = list(UsedTruckTyre.queryTyres())
        tyres = carTyres + uCarTyres + truckTyres + uTruckTyres
        self.render("manage.html", pathDict=self.paths, Tyres=tyres)

    def post(self):
        size = self.request.get('size')
        brand = self.request.get('brand')
        model = self.request.get('model')
        price = float(self.request.get('price'))
        season = self.request.get('season')
        li = self.request.get('loadIndex')
        si = self.request.get('speedIndex')

        isTruckTyre = self.request.get('isTruckTyre')
        axle = self.request.get('axle')
        # lip = self.request.get('loadIndexPaired')

        isUsed = self.request.get('isUsed')
        tread = self.request.get('tread')

        params = {"size": size, "brand": brand, "model": model, "price": price,
                  "season": season, "loadIndex": li, "speedIndex": si}

        if isTruckTyre:
            params["axlePosition"] = axle
            # params["loadIndexPaired"] = lip
            if isUsed:
                params["treadDepth"] = tread
                tyre = UsedTruckTyre(**params)
            else:
                tyre = TruckTyre(**params)
        else:
            if isUsed:
                params["treadDepth"] = tread
                tyre = UsedCarTyre(**params)
            else:
                tyre = CarTyre(**params)

        tyre.put()
        self.redirect('/manage')


class MainHandler(Handler):
    def get(self):
        self.render("home.html")


class TyreHandler(Handler):
    def get(self):
        carTyres = list(CarTyre.queryTyres())
        uCarTyres = list(UsedCarTyre.queryTyres())
        truckTyres = list(TruckTyre.queryTyres())
        uTruckTyres = list(UsedTruckTyre.queryTyres())
        tyres = carTyres + uCarTyres + truckTyres + uTruckTyres
        self.render("riepas.html", Tyres=tyres)


class RimHandler(Handler):
    def get(self):
        self.render("diski.html")


class ServiceHandler(Handler):
    def get(self):
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
        def generateDL(paramList, tyres):
            logging.error("Generating DL...")
            dl = []
            for tyre in tyres:
                tmpdict = collections.OrderedDict()
                for param, val in zip(paramList, tyre):
                    tmpdict[param] = val
                dl.append(tmpdict)
            return dl

        def addEntries(entityName, parameterDL):
            logging.error("Adding Entries...")
            for params in parameterDL:
                e = entityName(**params)
                if entityName == UsedTruckTyre:
                    logging.error(e.axlePosition)
                e.put()

        a = [["195/70 R15", "10", "R", "Matadr", "MPS 530", "Ziemas", "50.00"],
             ["195/65 R15", "9", "T", "Matador", "MP 92", "Ziemas", "33.00"],
             ["205/55 R16", "9", "H", "Matador", "MP 59", "Ziemas", "45.00"],
             ["205/55 R16", "9", "T", "Marshal", "KW 22", "Ziemas", "50.00"],
             ["205/55 R16", "9", "T", "Debica", "Frigo 2", "Ziemas", "42.00"],
             ["235/75 R17", "13", "L", "Aeolus", "HN804", "Vissez.", "110.00"]]

        b = [["255/55 R18", "10", "H", "Pirel", "Scop", "Vs.", "15.00", "4.0"],
             ["220x508 R18", "8", "Q", "GAZ", "MI", "Vissez.", "15.00", "5.0"]]

        c = [["385/65 R22.5", "13", "L", "Sempit", "M350", "V.", "290.0", 'U'],
             ["385/55 R22.5", "13", "L", "Aeol", "HN809", "V.", "230.0", "U"],
             ["385/65 R22.5", "13", "L", "Aeol", "HN805", "V.", "210.0", "U"],
             ["385/65 R22.5", "13", "L", "Matador", "FH2", "V.", "250.0", "U"],
             ["315/80 R22.5", "13", "L", "Fulln", "TB755", "V.", "175.0", "U"],
             ["315/80 R22.5", "13", "L", "Aeol", "HN 355", "V.", "220.0", "F"],
             ["315/70 R22.5", "13", "L", "Marsl", "RS03", "Vi.", "250.0", "F"],
             ["315/80 R22.5", "13", "L", "Firee", "XD2", "V.", "160.0", "U"],
             ["385/55 R22.5", "13", "J", "Kumho", "KLA1", "Vz.", "280.0", "U"],
             ["1R R22.5", "13", "L", "Rocks", "ST957", "V.", "185.0", "U"]]

        d = [["315/65 R2.5", "10", "R", "Marsal", "KW22", "Z", "37", "U", "5"],
             ["315/70 R22.5", "13", "L", "Cont", "X", "A.", "30.00", 'F', "5"],
             ["8.5 R17", "12", "L", "Michelin", "HT", "Va", "25.00", 'S', "4"],
             ["385/55 R22.5", "13", "L", "Co", "HT1", "V.", "45.00", 'U', "7"],
             ["315/70 R22.5", "13", "L", "Rou", "R6", "V", "35.00", 'U', "11"],
             ["11 R22.5", "13", "L", "Matador", "DR1", "V", "45.00", 'U', "5"]]

        paramList = ["size", "loadIndex", "speedIndex", "brand", "model",
                     "season", "price"]
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

        self.redirect("/manage")


class SingleTyreHandler(Handler):
    def get(self, isUsed, kind, itemID):
        self.write(isUsed)
        self.write("<br />")
        self.write(kind)
        self.write("<br />")
        self.write(itemID)
        self.write("<br />")
        revPaths = {v: k for k, v in self.paths.items()}
        self.write(revPaths)
        usedPrefix = 'Used' if isUsed else ''
        key = ndb.Key(usedPrefix + revPaths[kind], int(itemID))
        self.write("<br />")
        self.write(key)
        tyre = key.get()
        self.write("<br />")
        self.write(tyre)
        self.render("manageSingleTyre.html")


class TyreKindHandler(Handler):
    def get(self, tyreKind):
        tyres = globals()[tyreKind].queryTyres()
        self.render("manage.html", Tyres=tyres, pathDict=self.paths)


app = webapp2.WSGIApplication([
    # Repeating myself, because fuck redirects
    ('/db', PopulateDB),
    ('/manage', ManageTyres),
    ('/manage/riepas', ManageTyres),
    ('/riepas', TyreHandler),
    ('/diski', RimHandler),
    ('/serviss', ServiceHandler),
    ('/meklet', SearchHandler),
    ('/par', AboutHandler),
    ('/l', SendMail),
    ('/riepas/([a-z]+)', TyreKindHandler),
    ('/manage/riepas/(lietotas/)?([a-zA-Z]+)/([0-9]+)', SingleTyreHandler),
    ('/.*', MainHandler)
], debug=True)

# TODO: Implement feature to find product by car model.
