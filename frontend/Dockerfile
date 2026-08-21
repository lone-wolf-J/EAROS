# Build the EAROS React client with an explicit public API origin. Do not pass secrets here.
FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_BACKEND_URL
ARG VITE_EAROS_ALLOW_INSECURE_LOCAL_SMOKE
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
ENV VITE_EAROS_ALLOW_INSECURE_LOCAL_SMOKE=${VITE_EAROS_ALLOW_INSECURE_LOCAL_SMOKE}
COPY package.json yarn.lock ./
RUN corepack enable && yarn install --frozen-lockfile --ignore-engines --production=false
COPY . .
RUN yarn build

FROM nginx:1.27-alpine
ENV NODE_ENV=production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
