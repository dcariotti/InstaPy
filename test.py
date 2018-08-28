from instapy import InstaPy

session = InstaPy(username='tct408', password='qwerty000', nogui=True, igbooster=False).login()

#session.like_by_locations(['249785880'], amount=500, list_of_tags=['spedizioni'])
session.like_by_tags(['catania'], amount=10, locations=['213830427'])
session.end()
