# Build stage
FROM node:20-bullseye as build-stage

WORKDIR /usr/src/app

COPY package*.json ./

RUN npm ci

COPY . .

# Build the frontend app (vite, react, etc.)
RUN npm run build

# Production stage: serve static files with nginx
FROM nginx:stable-alpine as production-stage

# Copy built static files from build stage
COPY --from=build-stage /usr/src/app/dist /usr/share/nginx/html

# Copy custom nginx config if needed
# COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
