# ZooLingo

An experimental animal-audio demo built for the Techfest IIT Bombay SARVAM AI hackathon. It accepts audio, estimates sound categories, and can render a human-readable interpretation as speech.

## How it works

1. The React/Vite frontend records or selects a clip.
2. FastAPI preprocesses the audio and calls classification services in [backend/services](backend/services).
3. Classification and confidence checks feed an experimental interpretation. Configured speech providers can read the result aloud.

The app’s emotion and intent labels are experimental. Treat them as demo output and consult a veterinarian for animal health concerns.

## Repository layout

| Path | Purpose |
| --- | --- |
| [frontend/src](frontend/src) | Recording interface, results, and pet-care views |
| [backend/app.py](backend/app.py) | FastAPI entry point |
| [backend/services](backend/services) | Audio preprocessing, classifiers, and language/speech integrations |
| [backend/petcare](backend/petcare) | Pet profiles and care features |
| [backend/tests](backend/tests) | API and service tests |
| [docker-compose.yml](docker-compose.yml) | Local two-service setup |

## Run locally

Install Docker with Compose, copy the example configuration, and set the provider keys needed for the speech features you intend to use.

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Open http://localhost:3000. The API exposes `/health` and `/docs` on port 8000. See [deployment notes](docs/DEPLOYMENT.md) for hosting details.

Sarvam AI provides language and speech integrations. The repository also includes integrations for Murf, Deepgram, and ElevenLabs.
