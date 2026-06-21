# CS360 Enhanced Inventory Web App

**CS499 Enhancement One**, rebuild of the CS360 Android Inventory App as a
full-stack web application.

**Author:** Sanjay Chauhan

## Tech Stack

| Layer    | Technology                                      |
| -------- | ----------------------------------------------- |
| Frontend | React 18, React Router 6, Vite                  |
| Backend  | Node.js, Express 4, ES modules                  |
| Database | SQLite via better-sqlite3 (embedded, no server)  |
| Auth     | bcrypt password hashing, JWT bearer tokens       |
| Validation | Zod schema validation on every endpoint        |

## Quick Start

### 1. Server

```bash
cd server
cp .env.example .env          # then edit JWT_SECRET
npm install
npm run seed                   # creates tables + demo data
npm start                      # listens on http://localhost:4000
```

Demo credentials (printed by the seed script):

| Role  | Username | Password  |
| ----- | -------- | --------- |
| Admin | admin    | admin123  |
| Staff | staff    | staff123  |

### 2. Client

```bash
cd client
npm install
npm run dev                    # Vite dev server on http://localhost:5173
```

The Vite dev server proxies `/api` requests to `localhost:4000` automatically.

### 3. Production Build (optional)

```bash
cd client
npm run build                  # outputs to client/dist/
```

## API Endpoints

All endpoints return JSON. Errors use `{ "error": "message" }`.

### Authentication

| Method | Path                  | Body                       | Response                              |
| ------ | --------------------- | -------------------------- | ------------------------------------- |
| POST   | `/api/auth/register`  | `{ username, password }`   | `{ token, user: {id,username,role} }` |
| POST   | `/api/auth/login`     | `{ username, password }`   | `{ token, user: {id,username,role} }` |

### Inventory (requires `Authorization: Bearer <token>`)

| Method | Path                 | Body                              | Access | Response                    |
| ------ | -------------------- | --------------------------------- | ------ | --------------------------- |
| GET    | `/api/inventory`     | none                                 | All    | `[{id,name,sku,...}]`       |
| POST   | `/api/inventory`     | `{ name, sku, quantity, location }` | All  | `{ item }`                  |
| PUT    | `/api/inventory/:id` | `{ name, sku, quantity, location }` | Admin  | `{ item }`                  |
| DELETE | `/api/inventory/:id` | none                                 | Admin  | `{ success: true }`         |

## Project Structure

```
CS360_Enhanced_WebApp/
├── client/               # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx       # Routes and auth wrapper
│   │   ├── auth.jsx      # Auth context (in-memory token)
│   │   ├── api.js        # Fetch wrapper with Bearer token
│   │   └── pages/        # Login, Inventory, ItemForm
│   └── vite.config.js    # Proxies /api to server
├── server/               # Node + Express backend
│   ├── index.js          # Entry point, CORS, error handler
│   ├── db.js             # SQLite connection + auto-schema
│   ├── schema.sql        # Table definitions
│   ├── seed.js           # Demo data loader
│   ├── eslint.config.js  # Lint rules (npm run lint)
│   ├── middleware/auth.js # JWT verify + role guard (requireAuth, requireRole)
│   ├── routes/           # HTTP boundary: auth.js, inventory.js (thin handlers)
│   └── services/         # Business logic + data access (single responsibility)
│       ├── authService.js      # Hashing, JWT, first-user-admin rule
│       ├── inventoryService.js # CRUD + SKU rules, all SQLite access
│       └── serviceError.js     # HTTP-agnostic business-rule error type
└── README.md
```

## Architecture Note: Separation of Concerns

The Express **routes** form a thin HTTP boundary: they validate the request with
Zod, enforce auth/role via middleware, call a **service** function, and shape the
response. All business rules and every SQLite call live in the **services**
layer, which has no knowledge of Express. Services raise a `ServiceError`
carrying an HTTP status; the single global error handler in `index.js` maps that
to a JSON response. This keeps the routing layer free of data-access logic and
makes the services independently testable.

## Linting

```bash
cd server
npm run lint                   # ESLint flat config; 0 errors expected
```
