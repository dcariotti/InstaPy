from instapy import InstaPy

session = InstaPy(username='tct408', password='qwerty000', igbooster=False).login()

#session.like_by_locations(['249785880'], amount=500, list_of_tags=['spedizioni'])
#session.like_by_tags(['catania'], amount=10)
session.set_do_comment(enabled=True, percentage=100)
session.set_comments(['wow', 'ehehe'])
session.comment_by_locations(['224442573/salton-sea/'], amount=10)
session.end()
