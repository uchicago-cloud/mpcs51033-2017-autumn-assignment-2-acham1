from google.appengine.ext import ndb

class Photo(ndb.Model):
    """Models a user uploaded photo entry"""

    caption = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    labels = ndb.StringProperty(repeated=True)
    # instead of storing an image data blob or file name, this object's key will be used as the filename of the image in cloud storage

class User(ndb.Model):
    """Models a user account"""

    name = ndb.StringProperty()
    email = ndb.StringProperty()
    unique_id = ndb.KeyProperty()
    photos = ndb.KeyProperty(repeated=True)
    username = ndb.StringProperty()
    password = ndb.StringProperty()
    id_token = ndb.StringProperty() # a unique urlsafe string that anonymously identifies this user

    def query_user(self):
        """Return all photos for a given user"""
        return self.photos
