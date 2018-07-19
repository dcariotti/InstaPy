from instapy import InstaPy

session = InstaPy(username='tct408', password='qwerty000', nogui=True, igbooster=False).login()

#session.like_by_locations(['249785880'], amount=500, list_of_tags=['spedizioni'])
session.like_by_tags(['catania'], amount=10000, tags2=['saper','prezz','info@','informazion','store','sale','saldi','shipping','worldwide','spedizion','deliver','express','shop','online','24','giornata','spediamo','7/7','promo','saldi','consegn','site','sito','compra','buy','commerce','%','www','paypal','postepay','catalogo','negozi','corrier','made','acquist'])
session.end()
