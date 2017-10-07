import cgi
import datetime
import urllib
import webapp2
import json
import logging

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import images

from models import *

################################################################################
"""The home page of the app"""
class HomeHandler(webapp2.RequestHandler):

    """Show the webform when the user is on the home page"""
    def get(self):
        self.response.out.write('<html><body>')

        # Print out some stats on caching
        stats = memcache.get_stats()
        self.response.write('<b>Cache Hits:{}</b><br>'.format(stats['hits']))
        self.response.write('<b>Cache Misses:{}</b><br><br>'.format(
                            stats['misses']))

        # user = self.request.get('user')
        # user_key = ndb.Key("User", user or "*notitle*")
        # # Query the datastore
        # photos = user_key.get().photos


        self.response.out.write("""
        <form action="/post/default/" enctype="multipart/form-data" method="post">
        <div><textarea name="caption" rows="3" cols="60"></textarea></div>
        <div><label>Photo:</label></div>
        <div><input type="file" name="image"/></div>
        <div>User <input value="default" name="user"></div>
        <div><input type="submit" value="Post"></div>
        </form>
        <hr>
        </body>
        </html>""")


################################################################################
"""Handle activities associated with a given user"""
class UserHandler(webapp2.RequestHandler):

    """Print json or html version of the users photos"""
    def get(self,user,type):
        photo_keys = self.get_data(user)
        if type == "json":
            output = self.json_results(user,photo_keys)
        else:
            output = self.web_results(user,photo_keys)
        self.response.out.write(output)

    def json_results(self,user,photo_keys):
        """Return formatted json from the datastore query"""
        json_array = []
        for key in photo_keys:
            photo = key.get()
            dict = {}
            dict['image_url'] = "image/%s/" % key.urlsafe()
            dict['caption'] = photo.caption
            dict['user'] = user
            dict['date'] = str(photo.date)
            json_array.append(dict)
        return json.dumps({'results' : json_array})

    def web_results(self,user,photo_keys):
        """Return html formatted json from the datastore query"""
        html = ""
        for key in photo_keys:
            photo = key.get()
            html += '<div><hr><div><img src="/image/%s/" width="200" border="1"/></div>' % key.urlsafe()
            html += '<div><blockquote>Caption: %s<br>User: %s<br>Date:%s</blockquote></div></div>' % (cgi.escape(photo.caption),user,str(photo.date))
        return html

    @staticmethod
    def get_data(user):
        """Get data from the datastore only if we don't have it cached"""
        key = user
        data = memcache.get(user)
        if data is not None:
            logging.info("Found in cache")
            return data
        else:
            logging.info("Cache miss")
            user_key = ndb.Key("User", user)
            data = user_key.get().photos
            if not memcache.add(key, data, 3600):
                logging.info("Memcache failed")
        return data

################################################################################
"""Handle requests for an image ebased on its key"""
class ImageHandler(webapp2.RequestHandler):

    def get(self,key):
        """Write a response of an image (or 'no image') based on a key"""
        photo = ndb.Key(urlsafe=key).get()
        if photo.image:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.out.write(photo.image)
        else:
            self.response.out.write('No image')


################################################################################
class PostHandler(webapp2.RequestHandler):
    def post(self,user):

        # If we are submitting from the web form, we will be passing
        # the user from the textbox.  If the post is coming from the
        # API then the username will be embedded in the URL
        if self.request.get('user'):
            user = self.request.get('user')

        # Be nice to our quotas
        thumbnail = images.resize(self.request.get('image'), 30,30)

        # Create and add a new Photo entity
        #
        # We set a parent key on the 'Photos' to ensure that they are all
        # in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate should be limited to
        # ~1/second.
        photo = Photo(parent=ndb.Key("User", user),
                caption=self.request.get('caption'),
                image=thumbnail)
        photo_key = photo.put()

        # Add photo key to user's photos property
        user_key = ndb.Key("User", user)
        user_model = user_key.get()
        if user_model is None and (user == "default" or user == None):
            user_model = User(username = "default",
                photos = [])
            user_model.key = ndb.Key("User", "default")
            user_model.put()
        user_model.photos.append(photo_key)
        user_model.put()


        # Clear the cache (the cached version is going to be outdated)
        key = user
        memcache.delete(key)

        # Redirect to print out JSON
        self.redirect('/user/%s/json/' % user)



class LoggingHandler(webapp2.RequestHandler):
    """Demonstrate the different levels of logging"""

    def get(self):
        logging.debug('This is a debug message')
        logging.info('This is an info message')
        logging.warning('This is a warning message')
        logging.error('This is an error message')
        logging.critical('This is a critical message')

        try:
            raise ValueError('This is a sample value error.')
        except ValueError:
            logging.exception('A example exception log.')

        self.response.out.write('Logging example.')


################################################################################

app = webapp2.WSGIApplication([
    ('/', HomeHandler),
    webapp2.Route('/logging/', handler=LoggingHandler),
    webapp2.Route('/image/<key>/', handler=ImageHandler),
    webapp2.Route('/post/<user>/', handler=PostHandler),
    webapp2.Route('/user/<user>/<type>/',handler=UserHandler)
    ],
    debug=True)
