from flask import Flask, request, redirect, render_template, session

from tinydb import TinyDB, Query
import random
import math
import requests

app = Flask('__name__')

app.secret_key = 'PdFry9LqXm40HstIGjmWgdfAJUTaQcnf'

# Ustvarjanje in povezovanje z bazami podatkov
db_users = TinyDB('userData.json')  # Baza podatkov za uporabnike
db_data = TinyDB('appData.json')  # Baza podatkov za aplikacijske podatke
db_pics = TinyDB('picsData.json')  # Baza podatkov za slike

slika = ""
uporabljene_slike = []
rounds_played = 0
all_score = 0


def randomPicture():
  """
    Generiranje naključnega imena slike.
    """
  global uporabljene_slike
  st = random.randint(1, 10)  # Naključno izbere številko slike med 1 in 7
  a = "slika" + str(st) + ".png"  # Sestavi ime slike

  # Preveri, ali je slika že bila uporabljena v trenutni igri
  while a in uporabljene_slike:
    st = random.randint(
      1,
      10)  # Če je bila slika že uporabljena, izbere drugo naključno številko
    a = "slika" + str(st) + ".png"  # Sestavi ime slike

  uporabljene_slike.append(a)  # Dodaj ime slike v seznam uporabljenih slik
  print(uporabljene_slike)
  return a


@app.route('/')
def first():
  """
    Obisk prve strani.
    """
  session.pop('lUsername', None)
  return render_template("index.html")


@app.route('/registerMenu')
def registracijaTemp():
  """
    Prikaz obrazca za registracijo.
    """
  return render_template("register.html")


@app.route('/loginMenu')
def loginTemp():
  """
    Prikaz obrazca za prijavo.
    """
  return render_template("login.html")


@app.route('/umes')
def umes():
  """
    Ponastavi vse rezultate in preusmeri na igro.
    """
  global all_score
  all_score = 0
  return redirect('/game')


@app.route("/register", methods=["POST", "GET"])
def registracija():
  """
    Registracija novega uporabnika.
    """
  global api_link

  api_link = requests.get(
    "https://randomuser.me/api/")  # Pridobitev podatkov o uporabniku API-ja
  data = api_link.json()
  picture_url = data['results'][0]['picture'][
    'medium']  # Pridobitev URL-ja profilske slike uporabnika

  # Prebere podatke iz obrazca registracije
  username = request.form.get("uporabniskoIme")
  uIme = request.form.get("ime")
  uPriimek = request.form.get("priimek")
  uEmail = request.form.get("email")
  uGeslo = request.form.get("geslo")
  uConfGeslo = request.form.get("potrditevGesla")

  if uGeslo == uConfGeslo:
    userData = Query()

    # Preveri, ali že obstaja uporabnik s podanim uporabniškim imenom ali e-pošto
    if db_users.search(userData.uEmail == uEmail) or db_users.search(
        userData.username == username):
      return render_template(
        'register.html'
      )  # Prikaz obrazca za registracijo v primeru že obstoječega uporabnika
    else:
      print("dodajanje v bazo")
      # Vstavi novega uporabnika v bazo
      db_users.insert({
        "username": username,
        "uIme": uIme,
        "uPriimek": uPriimek,
        "uEmail": uEmail,
        "uGeslo": uGeslo,
        "profileImg": picture_url
      })
      return redirect('/loginMenu')  # Preusmeritev na stran za prijavo
  else:
    return render_template(
      'register.html'
    )  # Prikaz obrazca za registracijo v primeru neusklajenih gesel


@app.route("/login", methods=["POST", "GET"])
def login():
  """
    Prijava uporabnika.
  """
  lUsername = request.form.get("username")
  uGeslo = request.form.get("geslo")
  userData = Query()

  # Preveri, ali obstaja uporabnik s podanim uporabniškim imenom in geslom v bazi
  search_result = db_users.search((userData.username == lUsername)
                                  & (userData.uGeslo == uGeslo))

  session['lUsername'] = request.form['username']

  if search_result:
    return redirect('/main')  # Preusmeritev na glavno stran po uspešni prijavi
  else:
    return redirect(
      '/registerMenu'
    )  # Preusmeritev na stran za registracijo v primeru neveljavnih prijavnih podatkov


@app.route('/main', methods=['GET', 'POST'])
def main():
  """
    Prikaz glavne strani z rezultati in najboljšimi igralci.
    """
  global rounds_played, uporabljene_slike
  rounds_played = 0
  uporabljene_slike = []
  top_players = leaderboard()  # Pridobitev najboljših igralcev
  return render_template("main.html",
                         top_players=top_players,
                         me=session['lUsername'])


@app.route('/result', methods=['POST', 'GET'])
def game_result():
  """
    Prikaz rezultatov igre.
    """
  global uporabljene_slike, all_score
  uporabljene_slike = []
  return render_template("game-result.html", all_score=all_score)


@app.route('/coordinates', methods=['POST', "GET"])
def coordinates():
  """
    Obdelava koordinat in izračun rezultata igre.
  """
  global rounds_played, slikaIme, all_score
  lat1 = request.form.get('lat', 0)
  lng1 = request.form.get('lng', 0)
  year = request.form.get('year', 0)

  score = calculate_score(
    lat1, lng1, year, slikaIme)  # Izračun rezultata glede na podane koordinate

  # Posodobi skupni rezultat
  all_score += score

  return "a"


@app.route('/game', methods=['GET', 'POST'])
def game():
  """
    Prikaz igre s sliko.
  """
  global slikaIme, uporabljene_slike, rounds_played, slika, all_score
  if rounds_played != 5:
    slika = randomPicture()  # Generiranje nove slike
    slikaIme = slika
    # Posodobi število odigranih krogov
    rounds_played += 1
  else:
    rounds_played = 0
    db_data.insert({
      "username": session['lUsername'],
      "score": round(all_score, 0)
    })

    return redirect('/result')  # Preusmeritev na stran z rezultati igre

  return render_template("game.html", uporabljene_slike=uporabljene_slike)


def calculate_distance(lat1, lng1, image_lat, image_lng):
  """
    Izračuna razdaljo med dvema točkama na podlagi njunih geografskih koordinat.
    """
  R = 6371
  dlat = math.radians(float(image_lat) - float(lat1))
  dlng = math.radians(float(image_lng) - float(lng1))
  a = math.sin(float(dlat) / 2) * math.sin(float(dlat) / 2) + math.cos(
    math.radians(float(lat1))) * math.cos(math.radians(float(
      image_lat))) * math.sin(float(dlng) / 2) * math.sin(float(dlng) / 2)
  c = 2 * math.atan2(math.sqrt(float(a)), math.sqrt(1 - float(a)))
  distance = R * float(c) * 1000
  return distance


def calculate_score(lat1, lng1, year, slikaIme):
  """
    Izračuna rezultat igre na podlagi podanih koordinat, leta in imena slike.
    """
  picsData = Query()
  search_result = db_pics.search(picsData.imeSlike == slikaIme)
  score = []
  image_lat = 0
  image_lng = 0
  for image_data in search_result:
    image_lat = image_data['latSlika']
    image_lng = image_data['lngSlika']
    image_year = image_data['year']

  distance = calculate_distance(lat1, lng1, image_lat, image_lng)
  yearC = calculate_year(image_year, year)

  score.append(distance)
  score.append(yearC)

  max_score = 5000

  if score[0] < 250:
    round_score = (max_score - score[0] + 250) - (score[1] * 100)
  else:
    round_score = (max_score - score[0]) - (score[1] * 100)

  if round_score < 0:
    round_score = 0
  elif round_score > 5000:
    round_score = 5000

  round_score = round(round_score, 0)

  return round_score


def calculate_year(image_year, year):
  """
    Izračuna razliko med leti.
    """
  if int(image_year) > int(year):
    missed_year = (int(image_year) - int(year))
  else:
    missed_year = (int(year) - int(image_year))

  return missed_year


def leaderboard():
  """
    Pridobi podatke o najboljših igralcih iz baze.
  """
  User = Query()

  top_players = db_data.search(User.score.exists())

  top_players = sorted(top_players, key=lambda x: x['score'], reverse=True)

  top_players_dict = {}

  for player_data in top_players:
    username = player_data['username']
    score = int(player_data['score'])

    if username not in top_players_dict or score > top_players_dict[username][
        'score']:
      top_players_dict[username] = {'score': score, 'profileImg': None}

  for username, player_data in top_players_dict.items():
    user = db_users.get(User.username == username)
    if user:
      player_data['profileImg'] = user.get('profileImg')

  print(top_players_dict)
  return top_players_dict


if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)