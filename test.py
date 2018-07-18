from instapy import InstaPy

session = InstaPy(username='tct408', password='qwerty000', igbooster=False).login()

session.set_do_follow(enabled=True, percentage=100)
session.like_by_tags(['rome', 'berlin'], amount=10, tags2=['italy'])
session.end()
