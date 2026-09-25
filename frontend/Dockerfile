FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV API_INTERNAL_URL=http://api:8000
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app ./
ENV API_INTERNAL_URL=http://api:8000
EXPOSE 3000
CMD ["npm", "run", "start"]
