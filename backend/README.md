# Backend API

```powershell
cd backend
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

The API runs at `http://127.0.0.1:5000`.

- `POST /api/optimizations` validates and saves form input, then returns up to 10 Pareto-optimal mix designs.
- `GET /api/optimizations` returns the 20 latest stored runs.

Each run is saved in `optimization.db`, created automatically. The API uses the included ANN model and NSGA-II optimiser; the first request may take a little longer while the model is loaded.
