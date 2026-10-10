# Frontend image for QShield Twin (Vite dev server).
#
#   docker build -f frontend/Dockerfile -t qshield-frontend ./frontend
#
# For a production deployment, build the static bundle (`npm run build`) and
# serve `dist/` from a static web server / reverse proxy instead of running the
# dev server. See docs/ARCHITECTURE.md.

FROM node:22-alpine

WORKDIR /app

# Install dependencies reproducibly from the lockfile.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Vite must bind to 0.0.0.0 inside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
