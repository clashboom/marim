# Happy Violence!
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


class BaseService(ndb.Model):
    name = ndb.StringProperty(required=True)
    lastModified = ndb.DateTimeProperty(auto_now=True)
    low = ndb.StringProperty()
    mid = ndb.StringProperty()
    high = ndb.StringProperty()

    @classmethod
    def queryServices(cls):
        return cls.query()


class CarService(BaseService):
    pass


class TruckService(BaseService):
    pass


class OffroadService(BaseService):
    pass


class CommercialService(BaseService):
    pass


class AgroService(BaseService):
    pass


class IndyService(BaseService):
    pass


class BaseTyre(ndb.Model):
    brand = ndb.StringProperty(required=True)
    loadIndex = ndb.StringProperty()
    model = ndb.StringProperty(required=True)
    price = ndb.StringProperty(required=True)
    season = ndb.StringProperty()
    size = ndb.StringProperty(required=True)
    speedIndex = ndb.StringProperty()

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


class CarTyre(BaseTyre):
    pass


class UsedCarTyre(CarTyre):
    treadDepth = ndb.StringProperty()


class TruckTyre(BaseTyre):
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

    servicePaths = {'vieglo': CarService,
                    'kravas': TruckService,
                    'apvidus': OffroadService,
                    'komerctransports': CommercialService,
                    'agro': AgroService,
                    'industrialais': IndyService}

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

        services = None

        if kind:
            services = list(self.servicePaths[kind].queryServices())
            self.render("serviss.html", Services=services)

        services = list(CarService.queryServices()) + \
            list(TruckService.queryServices()) + \
            list(OffroadService.queryServices()) + \
            list(AgroService.queryServices()) + \
            list(IndyService.queryServices()) + \
            list(CommercialService.queryServices()) \

        self.render("serviss.html", Services=services)


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

        # Populate Services
        serviceParams = ["name", "low", "mid", "high"]

        e = [[u"Nonemsana", "0.71", "0.71", "0.71"],
             [u"Uzliksana", "0.71", "0.71", "0.71"],
             [u"Montaza", "0.71", "1.42", "2.13"],
             [u"Demontaza", "0.71", "1.42", "2.13"],
             [u"Balansesana", "2.13", "2.13", "2.85"],
             [u"Pilns Cikls", "4.98", "6.40", "8.54"]]

        f = [[u"Nonemsana", "0.71", "0.71", "0.71"],
             [u"Uzliksana", "0.71", "0.71", "0.71"],
             [u"Montaza", "0.71", "1.42", "2.13"],
             [u"Demontaza", "0.71", "1.42", "2.13"],
             [u"Pilns Cikls", "4.98", "6.40", "8.54"],
             [u"Balansesana", "2.13", "2.13", "2.85"],
             [u"Protektora padzilginasana", "2.13", "2.13", "2.85"]]

        g = [[u"Nonemsana", "0.71", "0.71", "0.71"],
             [u"Uzliksana", "0.71", "0.71", "0.71"],
             [u"Montaza", "0.71", "1.42", "2.13"],
             [u"Demontaza", "0.71", "1.42", "2.13"],
             [u"Balansesana", "2.13", "2.13", "2.85"],
             [u"Pilns Cikls", "4.98", "6.40", "8.54"]]

        h = [[u"Nonemsana", "0.71", "", ""],
             [u"Uzliksana", "0.71", "", ""],
             [u"Montaza", "2.13", "", ""],
             [u"Demontaza", "2.13", "", ""],
             [u"Pilns Cikls", "8.54", "", ""]]

        i = [[u"Nonemsana", "0.71", "0.71", "0.71"],
             [u"Uzliksana", "0.71", "0.71", "0.71"],
             [u"Montaza", "0.71", "1.42", "2.13"],
             [u"Demontaza", "0.71", "1.42", "2.13"],
             [u"Pilns Cikls", "4.98", "6.40", "8.54"]]

        j = [[u"Nonemsana", "0.71", "0.71", "0.71"],
             [u"Uzliksana", "0.71", "0.71", "0.71"],
             [u"Montaza", "0.71", "1.42", "2.13"],
             [u"Demontaza", "0.71", "1.42", "2.13"],
             [u"Pilns Cikls", "4.98", "6.40", "8.54"]]

        carDL = generateDL(serviceParams, e)
        TruckDL = generateDL(serviceParams, f)
        OffroadDL = generateDL(serviceParams, g)
        CommercialDL = generateDL(serviceParams, h)
        AgroDL = generateDL(serviceParams, i)
        IndyDL = generateDL(serviceParams, j)

        addEntries(CarService, carDL)
        addEntries(TruckService, TruckDL)
        addEntries(OffroadService, OffroadDL)
        addEntries(CommercialService, CommercialDL)
        addEntries(AgroService, AgroDL)
        addEntries(IndyService, IndyDL)

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


app = webapp2.WSGIApplication([
    ('/db', PopulateDB),
    ('/diski', RimHandler),
    ('/meklet', SearchHandler),
    ('/par', AboutHandler),
    ('/l', SendMail),
    ('/riepas(?:/)?(?:([a-zA-Z]+(?:(?:/)?[a-zA-Z]+)?)?(?:/)?([0-9]+)?)?',
     TyreHandler),
    ('/serviss(?:/)?([a-zA-Z]+)?(?:/)?',
     ServiceHandler),
    ('/.*', MainHandler)
], debug=True)

# TODO: Implement feature to find product by car model.
