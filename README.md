# AgroNexus

A web app that helps farmers track their crops and make day-to-day decisions: growth
stages, weather with farming advisories, mandi price history, irrigation and fertilizer
timing, and a photo-based leaf disease check.

> Built with FastAPI, Angular, PostgreSQL and a TensorFlow Lite model.
> Guidance in the app is general decision support, **not professional agronomic advice**.

## Features

| Module | What it does |
|---|---|
| Accounts and profile | Registration, login with JWT, farm profile (village, district, state, farm size) |
| Crop management | A 21-crop catalog (seasonal and perennial), date-based growth stages, harvest and yield records |
| Weather | OpenWeatherMap current weather, 24-hour and 5-day forecasts, rule-based farming advisories (rain, heat, wind, spraying window, harvest-before-rain for your own crops) |
| Market prices | Mandi prices imported from Agmarknet data: price board, daily median trend, 7- and 30-day change, average-based signal |
| Water and fertilizer | FAO-56 style irrigation plan (Hargreaves ET0 x crop coefficient, effective rain, soil-water store) and stage-based fertilizer timing (no doses) |
| Disease check | Leaf photo to likely condition, with confidence levels, alternatives, a guide and history (tomato and maize) |

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, JWT (python-jose), pytest
- **Frontend:** Angular 22 (standalone components, signals), Angular Material, TypeScript
- **ML:** TensorFlow/Keras (training in Google Colab), TensorFlow Lite model run with `ai-edge-litert`
- **Infrastructure:** Docker and Docker Compose

## Architecture

```
Angular (browser)  --JSON/HTTPS-->  FastAPI  -->  PostgreSQL
                                       |--> OpenWeatherMap (weather, geocoding)
                                       |--> TFLite model (ml/disease_model.tflite)
CSV files (CEDA / Agmarknet) --importer--> market_prices table
```

All rule-based logic (growth stages, advisories, irrigation, thresholds) lives in pure
functions that are covered by tests without needing a database or the network.

## Getting started

Requirements: Docker Desktop, Node.js (built with Node 26 and Angular CLI 22).

```bash
cp .env.example .env            # then edit the values (add your OpenWeatherMap key)
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.db.seed       # crop catalog

cd frontend
npm install
npx ng serve                    # http://localhost:4200
```

The API documentation is at http://localhost:8000/docs.

### Market price data

Price data is imported from CSV files (see "Data sources"). Put files in `backend/data/` and run:

```bash
docker compose exec backend python -m app.services.market_import data/your_file.csv --state Kerala
docker compose exec backend python -m app.services.market_mapping    # which crops have data
```

Imports are safe to repeat: existing rows are updated, not duplicated.

### Disease model

The model files live in `backend/ml/` (`disease_model.tflite` and `labels.json`). They were
produced by the training notebook in `notebooks/` (MobileNetV2 transfer learning on the
PlantVillage tomato and maize classes). Without these files, the disease endpoints return 503.

### Tests

```bash
docker compose exec backend pytest
```

The tests use a separate `agronexus_test` database, never call the real weather API, and use a
fake classifier instead of the real model (plus one smoke test for the real model).

## Main API endpoints

| Area | Endpoints |
|---|---|
| Auth | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` |
| Profile | `GET/PUT /api/v1/users/me` |
| Crops | `GET /api/v1/crop-types`, `GET/POST /api/v1/crops`, `GET/PUT/DELETE /api/v1/crops/{id}`, `POST /api/v1/crops/{id}/harvest` |
| Weather | `GET /api/v1/weather` |
| Market | `GET /api/v1/market/crops`, `/market/prices`, `/market/trend` |
| Resources | `GET /api/v1/resources/plan` |
| Disease | `GET /api/v1/disease/crops`, `POST /api/v1/disease/predict`, `GET /api/v1/disease/history`, `DELETE /api/v1/disease/history/{id}` |

## Data sources and credits

- Weather: [OpenWeatherMap](https://openweathermap.org/) (free plan).
- Market prices: Agmarknet (Ministry of Agriculture and Farmers Welfare), obtained through the
  CEDA Agri Market data portal, Ashoka University, which is free for non-commercial use.
- Disease images: the PlantVillage dataset (Hughes and Salathe, 2015), used to train the model.
- Irrigation method: FAO Irrigation and Drainage Paper 56 (Allen et al., 1998) and the
  Hargreaves-Samani equation (1985).

## Known limitations

- **Market prices are historical.** The dataset used ends in October 2025, and the live data.gov.in
  API could not be reached from the development network. The app always shows the date of the
  latest prices and warns when they are old.
- **Disease model scope and accuracy.** Tomato and maize only. It scored 96.6% on a clean held-out
  test set and 92.8% on artificially degraded phone-like images, but the training images are
  lab photos, so accuracy on real field photos is lower and unmeasured. Results are suggestions,
  not diagnoses, and the app says so.
- **Irrigation advice is an estimate.** It assumes a starting soil moisture, ignores soil type and
  irrigation method, and uses approximate crop coefficients for spice and plantation crops.
- **Fertilizer guidance is timing only.** It gives no doses and does not track what has already
  been applied.
- **Security.** JWT access tokens are kept in `localStorage` (no refresh tokens, no password
  reset or email verification). Rate limiting is in memory and suits a single instance.
- **Language.** The interface is in English only.

## Roadmap

- Malayalam interface
- More crops in the disease model (rice, coconut, banana), using field photos
- Live price sync and price alerts
- "Mark fertilizer as applied" and irrigation logs
- Soil type and irrigation method per crop
- httpOnly cookies with refresh tokens, password reset