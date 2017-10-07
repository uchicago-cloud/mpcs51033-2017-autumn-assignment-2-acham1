import cgi
import datetime
import urllib
import webapp2
import json
import logging
import os
import cloudstorage as gcs

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.api import app_identity

from models import *

################################################################################
class BaseHandler(webapp2.RequestHandler):
    """Common request handling helper methods"""

    """Check that id_token exists and matches user"""
    def validate(self, user):
        user_model = self.parseID()
        if user_model.username != user:
            logging.info('ID token does not match user: %s' % user)
            self.abort(401)
        return user_model

    def parseID(self):
        try:
            id_token = self.request.get("id_token")
            if not id_token:
                logging.info('No ID token provided')
                return self.abort(401)
            user_key = ndb.Key(urlsafe=id_token)
            user_model = user_key.get()
            if user_model is None:
                logging.info('ID token does not match any user')
                self.abort(401)
            return user_model
        except:
            logging.exception('ID token is not a valid id token')
            return self.abort(401)

    def bucketName(self):
        return os.environ.get('BUCKET_NAME',
            app_identity.get_default_gcs_bucket_name())


################################################################################
"""The home page of the app"""
class HomeHandler(BaseHandler):

    """Show the webform when the user is on the home page"""
    def get(self):
        self.response.out.write('<html><body>')

        # Print out some stats on caching
        stats = memcache.get_stats()
        self.response.write('<b>Cache Hits:{}</b><br>'.format(stats['hits']))
        self.response.write('<b>Cache Misses:{}</b><br><br>'.format(stats['misses']))

        # Write html response
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
class UserHandler(BaseHandler):

    """Print json or html version of the users photos"""
    def get(self, user, type):
        user = self.validate(user)
        photo_keys = self.get_data(user)
        if type == "json":
            output = self.json_results(user, photo_keys)
        else:
            output = self.web_results(user, photo_keys)
        self.response.out.write(output)

    def json_results(self, user, photo_keys):
        """Return formatted json from the datastore query"""
        json_array = []
        for key in photo_keys:
            photo = key.get()
            dict = {}
            dict['image_url'] = "image/%s/" % key.urlsafe()
            dict['caption'] = photo.caption
            dict['user'] = user.username
            dict['date'] = str(photo.date)
            json_array.append(dict)
        return json.dumps({'results' : json_array})

    def web_results(self, user, photo_keys):
        """Return html formatted json from the datastore query"""
        html = ""
        for key in photo_keys:
            photo = key.get()
            html += '<div><hr><div><img src="/image/%s/?id_token=%s" width="200" border="1"/></div>' % (key.urlsafe(), user.id_token)
            html += '<div><blockquote>Caption: %s<br>User: %s<br>Date:%s</blockquote></div></div>' % (cgi.escape(photo.caption),user.username,str(photo.date))
        return html

    @staticmethod
    def get_data(user):
        """Get data from the datastore only if we don't have it cached"""
        key = user.username + "_photos"
        data = memcache.get(key)
        if data is not None:
            logging.info("Found in cache")
            return data
        else:
            logging.info("Cache miss")
            data = user.photos
            if not memcache.add(key, data, 3600):
                logging.info("Memcache failed")
        return data

################################################################################
"""Handle requests for an image ebased on its key"""
class ImageHandler(BaseHandler):

    def get(self, key):
        """Write a response of an image (or 'no image') based on a key"""
        user = self.parseID()
        photo_key = ndb.Key(urlsafe=key)
        if photo_key not in user.photos:
            return self.abort(401)
        photo = photo_key.get()
        if photo:
            self.response.headers['Content-Type'] = 'image/png'
            gcs_file = gcs.open("/" + self.bucketName() + "/" + key)
            self.response.write(gcs_file.read())
            gcs_file.close()
        else:
            self.response.out.write('No image')


################################################################################
class PostHandler(BaseHandler):

    def post(self, user):

        # If we are submitting from the web form, we will be passing
        # the user from the textbox.  If the post is coming from the
        # API then the username will be embedded in the URL
        user = self.validate(user)

        # Be nice to our quotas
        thumbnail = images.resize(self.request.get('image'), 30,30)

        # Create and add a new Photo entity
        #
        # We set a parent key on the 'Photos' to ensure that they are all
        # in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate should be limited to
        # ~1/second.
        photo = Photo(parent=ndb.Key("User", user.username), 
            caption=self.request.get('caption'))
        photo_key = photo.put()

        gcs_file = gcs.open("/" + self.bucketName() + "/" + photo_key.urlsafe(), 'w')
        gcs_file.write(thumbnail)
        gcs_file.close()

        # Add photo key to user's photos property
        user.photos.append(photo_key)
        user.put()

        # Clear the cache (the cached version is going to be outdated)
        memcache.delete(user.username + "_photos")

        # Redirect to print out JSON
        self.redirect('/user/%s/json/?id_token=%s' % (user.username, user.id_token))


################################################################################
class DeleteHandler(BaseHandler):
    """ Authenticate the user """

    def get(self):
        return


################################################################################
class AuthenticationHandler(BaseHandler):
    """ Authenticate the user """

    def get(self):
        # get username and pw params from request url
        username = self.request.get('username')
        password = self.request.get('password')

        # find corresponding user or create if none found
        user_key = ndb.Key("User", username)
        user = user_key.get()
        if user is None:
            logging.info("Creating new user " + username)
            user = User(username = username, 
                password = password,
                unique_id = user_key,
                id_token = user_key.urlsafe())
            user.key = user_key
            user.put()

        self.response.out.write(user.id_token)


################################################################################
class LoggingHandler(BaseHandler):
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
    webapp2.Route('/image/<key>/delete/', handler=DeleteHandler),
    webapp2.Route('/image/<key>/', handler=ImageHandler),
    webapp2.Route('/post/<user>/', handler=PostHandler),
    webapp2.Route('/user/authenticate/', handler=AuthenticationHandler),
    webapp2.Route('/user/<user>/<type>/', handler=UserHandler)
    ],
    debug=True)
