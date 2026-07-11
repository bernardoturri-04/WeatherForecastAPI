# WeatherForecast API
## Bernardo Turri

WeatherForecast API è un'API RESTful basata su Flask che fornisce previsioni meteo. Include autenticazione tramite JWT, ruoli e permessi (anonimo / utente free / utente premium / admin), limiti giornalieri di richieste e una history delle query salvate per gli utenti premium.</br>
<u></u>

## Link di Deploy

[WeatherForecast API](https://weather-forecast-api-rho.vercel.app/)

## Struttura del Progetto

Il progetto è organizzato in moduli/blueprint Flask:

- `main.py`: entry point dell'applicazione (crea l'app, inizializza il DB, registra i blueprint).
- `extensions.py`: istanza condivisa di `SQLAlchemy`.
- `models.py`: modelli del database (`Place`, `Condition`, `Forecast`, `User`, `RequestLog`, `SavedQuery`).
- `helpers.py`: funzioni condivise (hashing password, generazione/verifica JWT, rate limiting, conversione a orario italiano).
- `db_utils.py`: funzione per fare il reset del database e popolarlo con dati ed account demo.
- `blueprints/web.py`: blueprint con le pagine web (home, login, dashboard, ecc.), basate su sessione.
- `blueprints/api.py`: blueprint con le risorse REST (`/api/...`), implementate come class-based view (`flask.views.MethodView`).
- `templates/`: template HTML.
- `static/`: file CSS.
- `instance/db.db`: database SQLite pre-popolato, incluso nel repo (vedi sezione dedicata sotto).
- `sample_requests.py`: esempi di codice per effettuare richieste all'API (login + chiamate autenticate).

## Dipendenze

Le dipendenze del progetto sono elencate nel file `requirements.txt` (include `PyJWT` per l'autenticazione a token).

## Installazione ed esecuzione locale

```bash
git clone <repo-url>
cd myweather-api
python -m venv venv
source venv/bin/activate      
pip install -r requirements.txt
python main.py
```

Al primo avvio, se il database è vuoto, viene automaticamente popolato con dati di esempio e i 3 account demo elencati sotto (vedi `db_utils.py`).

## Database SQLite incluso

Il repository include un database **già popolato** in `instance/db.db`, così l'app è esplorabile subito senza dover creare nulla a mano. Contiene:
- 12 condizioni meteo (Clear, Rain, Snow, ecc.)
- 4 luoghi (Bruxelles, Lubiana, Faenza, Roma)
- 9 previsioni di esempio (01-03 luglio 2026)
- 3 account demo (vedi sotto)

Se il file `instance/db.db` viene cancellato, al riavvio dell'app (`python main.py`) viene ricreato automaticamente e ripopolato con gli stessi dati, tramite `db_utils.reset_db()` (che scatta solo se il database risulta vuoto).

## Account demo

| Username | Password | Ruolo |
|---|---|---|
| `admin_demo` | `admin12345` | Amministratore — può creare/modificare/cancellare luoghi (`/api/places` PUT/DELETE) e previsioni (`/api/forecast` PUT/DELETE)|
| `premium_demo` | `premium12345` | Utente premium — richieste illimitate su `/api/forecast` + history delle query salvate |
| `user_demo` | `user12345` | Utente standard/free — richieste limitate su `/api/forecast`, nessuna history |

Per ottenere un token di accesso per uno di questi account:
```bash
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"premium_demo\", \"password\":\"premium12345\"}"
```


## Modello del Database

### Place
Rappresenta un luogo geografico.

| Colonna | Tipo        | Descrizione           |
| ------- | ----------- | --------------------- |
| id      | Integer     | ID del luogo (Chiave) |
| name    | String(50)  | Nome del luogo        |
| lat     | Float       | Latitudine del luogo  |
| lon     | Float       | Longitudine del luogo |

### Condition
Rappresenta le condizioni meteo.

| Colonna     | Tipo       | Descrizione                        |
| ----------- | ---------- | ----------------------------------- |
| id          | Integer    | ID della condizione meteo (Chiave) |
| description | String(50) | Descrizione della condizione meteo |

### Forecast
Rappresenta una previsione meteo per un luogo e una data specifici.

| Colonna        | Tipo        | Descrizione                                          |
| -------------- | ----------- | ----------------------------------------------------- |
| id             | Integer     | ID della previsione (Chiave)  |
| placeid        | Integer     | ID del luogo (riferimento a Place)   |
| date           | DateTime    | Data (e opzionalmente ora) della previsione          |
| condition      | Integer     | ID della condizione meteo (riferimento a Condition) |
| temperature    | Float       | Temperatura                                 |
| rain           | Float       | Quantità di pioggia                         |
| humidity       | Integer     | Percentuale di umidità                      |
| wind           | Integer     | Velocità del vento                          |
| wind_direction | String(5)   | Direzione del vento                         |

### User
Rappresenta un utente del sistema.

| Colonna    | Tipo       | Descrizione                                  |
| ---------- | ---------- | --------------------------------------------- |
| id         | Integer    | ID dell'utente (chiave)                      |
| username   | String(50) | Nome utente (unico e non nullo)               |
| hashed_pw  | String(64) | Password criptata (SHA-256)                   |
| is_premium | Boolean    | Se True, l'utente ha il piano premium (richieste illimitate + history delle query) |
| is_admin   | Boolean    | Se True, l'utente può gestire i luoghi (`PUT`/`DELETE` su `/api/places` e su `/api/forecast`) |

### RequestLog
Tiene traccia del numero di richieste giornaliere fatte a `/api/forecast` (GET), per applicare i limiti giornalieri.

| Colonna    | Tipo       | Descrizione                                                        |
| ---------- | ---------- | ------------------------------------------------------------------- |
| id         | Integer    | ID del log (Chiave)                                                |
| identifier | String(100)| Identificativo del chiamante: `user:<id>` per utenti autenticati, `ip:<indirizzo>` per anonimi |
| day        | Date       | Giorno a cui si riferisce il conteggio                             |
| count      | Integer    | Numero di richieste effettuate in quel giorno                      |

### SavedQuery
Rappresenta una query di previsione salvata nella history di un utente premium.

| Colonna      | Tipo       | Descrizione                                                 |
| ------------ | ---------- | ------------------------------------------------------------- |
| id           | Integer    | ID della query salvata (Chiave)                              |
| user_id      | Integer    | ID dell'utente proprietario (Chiave Esterna di User)         |
| placeid      | Integer    | ID del luogo richiesto                                       |
| date         | DateTime   | Data (e ora) richiesta                                       |
| requested_at | DateTime   | Timestamp di quando la richiesta è stata effettuata           |
| result_json  | Text       | Snapshot (in formato JSON) del risultato restituito           |


# Autenticazione

L'API usa **JWT (JSON Web Token)**

1. **Login**: `POST /api/auth/login` con `username` e `password` (JSON o form-data). (eseguire il comando `curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"yourUserName\",\"password\":\"yourPassword\"}"`) Risposta:
   ```json
   {
     "token": "eyJhbGciOiJIUzI1NiIs...",
     "token_type": "Bearer",
     "expires_in": 86400,
     "username": "premium_demo",
     "role": "premium"
   }
   ```
   Il token è valido 24 ore (`expires_in` in secondi).

2. **Uso del token**: ogni richiesta autenticata deve includere l'header:
   ```
   Authorization: Bearer <token>
   ```

3. Se si è loggati nel sito via browser (sessione), puoi anche ottenere un nuovo token senza reinserire la password tramite `GET /generatetoken` (usato dal bottone "Generate" nella dashboard).

4. Se il token manca, è scaduto o non è valido, l'API risponde `401 Unauthorized` con un messaggio esplicito.


# Documentazione API

## Limiti di richiesta giornalieri

`/api/forecast` (GET) è raggiungibile da chiunque, ma è soggetto a un limite giornaliero di richieste che dipende dal chiamante:

- **Anonimo** (nessun header `Authorization`): 2 richieste al giorno, tracciate per indirizzo IP.
- **Free** (utente autenticato, non premium): 100 richieste al giorno, tracciate per id utente.
- **Premium** (utente autenticato con piano premium): richieste illimitate. Inoltre, ogni query effettuata viene automaticamente salvata nella history dell'utente, consultabile con `/api/queries`.

Se il limite viene superato, l'endpoint risponde con `429 Too Many Requests`.

Ogni risposta di `/api/forecast` (GET) include il campo `requests_remaining_today` (un intero, oppure la stringa `"unlimited"` per i premium).

## Tabella endpoint

| Metodo | URL | Autenticazione | Ruolo richiesto | Descrizione |
|---|---|---|---|---|
| POST | `/api/auth/login` | No | Chiunque | Login, restituisce un token JWT |
| GET | `/api/forecast` | Opzionale | Chiunque (limiti diversi per anonimo/free/premium) | Interroga una previsione per luogo/data/ora |
| PUT | `/api/forecast` | Sì | Solo admin | Crea/aggiorna una previsione |
| DELETE | `/api/forecast` | Sì | Solo admin | Cancella una previsione |
| GET | `/api/places` | Sì | Qualsiasi utente autenticato | Recupera un luogo |
| PUT | `/api/places` | Sì | Solo admin | Crea/aggiorna un luogo |
| DELETE | `/api/places` | Sì | Solo admin | Cancella un luogo |
| GET | `/api/conditions` | Sì | Qualsiasi utente autenticato | Recupera una o tutte le condizioni meteo |
| GET | `/api/queries` | Sì | Solo premium | Lista delle query salvate dell'utente |
| GET | `/api/queries/<id>` | Sì | Solo premium | Dettaglio di una query salvata |
| GET | `/api/alltables` | No | Chiunque | Dump di debug di tutte le tabelle |

### `POST /api/auth/login`

**Request body** (JSON o form-data):
```json
{"username": "premium_demo", "password": "premium12345"}
```

**Risposte:**
- 200 OK: credenziali corrette, restituisce il token.
- 400 Bad Request: `username`/`password` mancanti.
- 401 Unauthorized: credenziali errate.

### `/api/forecast`

#### GET

Recupera una singola previsione meteo in base ai parametri specificati. Non richiede autenticazione (vedi i limiti sopra), ma se viene fornito un token valido abilita il tier free/premium.

**Parametri (query string):**
- `placename` o `placeid`: Specifica il nome del luogo o l'ID del luogo.
- `date` (opzionale): Data per la quale è richiesta la previsione (formato: `yyyy-mm-dd` o `yyyymmdd`). Default: oggi.
- `time` (opzionale): Ora del giorno, formato `HH:MM`, da combinare con `date`.
- `details` (opzionale): True o False per includere informazioni dettagliate sulla previsione.

**Esempio di risposta:**
```json
{
  "id": 1, "placeid": 1, "date": "Wed, 19 Jun 2024 00:00:00 GMT",
  "condition": 1, "temperature": 31.3, "rain": 0.0, "humidity": 30,
  "wind": 3, "wind_direction": "N", "requests_remaining_today": 1
}
```

**Risposte:**
- 200 OK / 400 Bad Request / 401 Unauthorized (token non valido) / 404 Not Found / 429 Too Many Requests

#### PUT

Richiede l'header `Authorization: Bearer <token>`, con token di un utente amministratore. Se esiste già una previsione per quel `placeid`+`date`, la aggiorna (`200 OK`, `"message": "Forecast updated successfully"`); altrimenti ne crea una nuova (`201 Created`, `"message": "Forecast created successfully"`). Parametri form-data: `placeid`, `date` (obbligatori), `condition`, `temperature`, `rain`, `humidity`, `wind`, `wind_direction` (opzionali).

#### DELETE

Richiede l'header `Authorization: Bearer <token>`, con token di un utente amministratore. Parametro form-data: `forecastid`.

### `/api/places`

#### GET
Richiede un token valido (qualsiasi ruolo). Parametri: `placename` o `placeid`.

#### PUT
**Richiede un token admin**. Aggiorna se il luogo esiste già, altrimenti lo crea (`201 Created`).

#### DELETE
**Richiede un token admin**. Cancella il luogo e, a cascata, tutte le previsioni collegate a quel `placeid` (al fine di evitare righe non raggiungibili). La risposta include `"forecasts_deleted"` con il numero di previsioni rimosse insieme al luogo, es.:
```json
{"message": "Place deleted successfully", "forecasts_deleted": 3}
```

Come diventare admin: non esiste un endpoint pubblico di auto-promozione (sarebbe un buco di sicurezza). L'account `admin_demo` è già admin di default; per promuoverne un altro, da shell Python:
```python
from main import app
from extensions import db
from models import User
with app.app_context():
    user = User.query.filter_by(username="tuo_username").first()
    user.is_admin = True
    db.session.commit()
```

### `/api/conditions`

**GET**: richiede un token valido. Parametro opzionale `id`.

### `/api/queries`

**GET**: solo premium. Restituisce la history delle query salvate dall'utente autenticato (JSON, più recente prima). Un utente free riceve `403 Forbidden`.

### `/api/queries/<id>`

**GET**: solo premium. Restituisce il dettaglio completo di una query salvata, incluso il risultato originale della previsione.

## Gestione dell'account (premium/free)

Per creare un nuovo account è rischiesta la sessione web tramite il bottone "manage Profiles" e la scelta di username e password, schiacciando infine "Register"
- `/upgrade` (GET, richiede sessione web, esiste un bottone dedicato): imposta `is_premium = True` sull'account loggato.
- `/downgrade` (GET, richiede sessione web esiste un bottone dedicato): imposta `is_premium = False` sull'account loggato.


## Esempi riproducibili (curl)

Si possono eseguire questi esempi sia con server locale sia con la versione deployata, cambiando solo `BASE`:

In locale:
BASE=http://localhost:5000

Oppure con il deploy:
BASE=https://weather-forecast-api-rho.vercel.app/
## Esempio n.1
```bash
# 1. chiamata come utente anonimo (max 2 al giorno)
curl "$BASE/api/forecast?placeid=1&date=2026-07-01"

# 2. Login come utente premium
curl -X POST $BASE/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"premium_demo\", \"password\":\"premium12345\"}"
# -> si consiglia di copiare il campo "token" dalla risposta

# 3. Chiamata autenticata (da account premium "premium_demo")
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/forecast?placeid=1&date=2026-07-03"
# 3a. Chiamata autenticata 
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/forecast?placename=Faenza&date=2026-07-03"

# 4. Vedi la history delle query salvate
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/queries"
#4a Vedi La prima chiamata che è stata fatta dall'utente corrente (con token di "premium_demo")
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/queries/1"

# 5. Azione Vietata: Crea una nuova previsione 
curl -X PUT -H "Authorization: Bearer $TOKEN" "$BASE/api/forecast" -d "placeid=1&date=2026-07-04&condition=1&temperature=30&rain=0&humidity=40&wind=5&wind_direction=N"
#il terminale risponderà: 403 "managing forecasts requires an admin account"
```
## Esempio n.2

```bash
# 1. Accediamo come admin con le credenziali fornite sopra:
curl -X POST $BASE/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin_demo\", \"password\":\"admin12345\"}"

# 2. Ora possiamo, con il token generato dell'utente admin, aggiungere, rimuovere places e previsioni
curl -X PUT -H "Authorization: Bearer $TOKEN" "$BASE/api/forecast" -d "placeid=1&date=2026-07-04&condition=1&temperature=30&rain=0&humidity=40&wind=5&wind_direction=N"
#dato che non ci sono previsioni per il 4 luglio 2026, crea una previsione per il placeid=1, ovvero Bruxelles

# 2a. Possiamo cancellare la previsione appena fatta:
curl -X DELETE -H "Authorization: Bearer $TOKEN" "$BASE/api/forecast" -d "forecastid=<ID_RESTITUITO_AL_PUNTO_2>"

# 2b. Possiamo creare una nuova città:
curl -X PUT -H "Authorization: Bearer $TOKEN" "$BASE/api/places" -d "placename=Milano&lat=45.4685&lon=9.1824"

# 2c. Per eliminare una città:
curl -X DELETE -H "Authorization: Bearer $TOKEN" "$BASE/api/places" -d "placename=Milano"

# NOTA IMPORTANTE se viene eliminata una città verranno eliminate anche le previsioni ad essa associate. 
#Verranno ripotate a schermo il numero delle previsioni eliminate a cascata
```
## Esempio n.3
```bash
# 1. Azione vietata: un utente free prova a gestire i luoghi (admin only) -> 403 Forbidden
curl -X POST $BASE/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"user_demo\", \"password\":\"user12345\"}"
#utilizzando il token fornito dal comando sopra:
curl -X PUT -H "Authorization: Bearer $FREE_TOKEN" "$BASE/api/places" -d "placename=Gotham&lat=0&lon=0"
# -> {"errorcode":403,"message":"Managing places requires an admin account."}
```
